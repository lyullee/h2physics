"""Conditional rigid-fragment flight under caller-supplied aerodynamic fields.

This model begins after a separate rupture owner has supplied fragment mass,
projected reference area, drag coefficient and launch state. It integrates the
point-mass equations with gravity and quadratic aerodynamic drag; it does not
predict fragment formation or launch conditions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import math

import numpy as np
from scipy.integrate import solve_ivp

from .core import finite, immutable_array


def _vec3(value, name):
    array = np.asarray(value, dtype=float)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite three-vector in SI units")
    return immutable_array(array, name=name)


@dataclass(frozen=True, slots=True)
class FragmentLaunch:
    """Caller-supplied rigid fragment mass, geometry and initial kinematics."""

    fragment_id: str
    mass_kg: float
    reference_area_m2: float
    drag_coefficient: float
    position_m: np.ndarray
    velocity_m_s: np.ndarray
    ground_z_m: float
    frame_id: str
    evidence_id: str

    def __post_init__(self):
        for name, value in (("fragment_id", self.fragment_id), ("frame_id", self.frame_id),
                            ("evidence_id", self.evidence_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        for name in ("mass_kg", "reference_area_m2", "drag_coefficient"):
            finite(getattr(self, name), name, positive=True)
        object.__setattr__(self, "position_m", _vec3(self.position_m, "position_m"))
        object.__setattr__(self, "velocity_m_s", _vec3(self.velocity_m_s, "velocity_m_s"))
        ground = finite(self.ground_z_m, "ground_z_m")
        if self.position_m[2] <= ground:
            raise ValueError("Fragment must begin above the declared horizontal ground plane")
        object.__setattr__(self, "ground_z_m", ground)


@dataclass(frozen=True, slots=True)
class HydrostaticIdealGasDensityProfile:
    """Caller-parameterized hydrostatic ideal-gas density over one lapse layer.

    The layer has a constant temperature gradient and constant gravity. It is
    suitable as a bounded density callback for fragment flight, not as a
    weather forecast or a universal standard atmosphere.
    """

    base_altitude_m: float
    base_pressure_pa: float
    base_temperature_k: float
    lapse_rate_k_m: float
    molecular_mass_kg_mol: float
    gravity_m_s2: float
    minimum_altitude_m: float
    maximum_altitude_m: float
    evidence_id: str

    def __post_init__(self):
        base = finite(self.base_altitude_m, "base_altitude_m")
        finite(self.base_pressure_pa, "base_pressure_pa", positive=True)
        finite(self.base_temperature_k, "base_temperature_k", positive=True)
        lapse = finite(self.lapse_rate_k_m, "lapse_rate_k_m")
        finite(self.molecular_mass_kg_mol, "molecular_mass_kg_mol", positive=True)
        finite(self.gravity_m_s2, "gravity_m_s2", positive=True)
        lower = finite(self.minimum_altitude_m, "minimum_altitude_m")
        upper = finite(self.maximum_altitude_m, "maximum_altitude_m")
        if lower >= upper or not lower <= base <= upper:
            raise ValueError("Atmosphere altitude bounds must increase and contain the base altitude")
        for altitude in (lower, upper):
            temperature = self.base_temperature_k - lapse * (altitude - base)
            if not math.isfinite(temperature) or temperature <= 0.0:
                raise ValueError("Lapse layer must keep temperature positive over its full altitude bounds")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("evidence_id must identify the caller-owned atmosphere parameters")
        for altitude in (lower, upper):
            self.pressure_at(altitude)

    @property
    def specific_gas_constant_j_kg_k(self) -> float:
        return 8.31446261815324 / self.molecular_mass_kg_mol

    @property
    def signature(self) -> tuple:
        """Scalar parameter lineage used when a profile is retained as a callback."""
        return (
            self.base_altitude_m, self.base_pressure_pa, self.base_temperature_k,
            self.lapse_rate_k_m, self.molecular_mass_kg_mol, self.gravity_m_s2,
            self.minimum_altitude_m, self.maximum_altitude_m, self.evidence_id,
        )

    def temperature_at(self, altitude_m: float) -> float:
        altitude = finite(altitude_m, "altitude_m")
        if not self.minimum_altitude_m <= altitude <= self.maximum_altitude_m:
            raise ValueError("Altitude lies outside the declared lapse-layer domain")
        return finite(
            self.base_temperature_k - self.lapse_rate_k_m * (altitude - self.base_altitude_m),
            "profile temperature", positive=True,
        )

    def pressure_at(self, altitude_m: float) -> float:
        altitude = finite(altitude_m, "altitude_m")
        temperature = self.temperature_at(altitude)
        delta_z = altitude - self.base_altitude_m
        if self.lapse_rate_k_m == 0.0:
            exponent = -self.gravity_m_s2 * delta_z / (
                self.specific_gas_constant_j_kg_k * self.base_temperature_k)
        else:
            exponent = self.gravity_m_s2 / (
                self.specific_gas_constant_j_kg_k * self.lapse_rate_k_m
            ) * math.log(temperature / self.base_temperature_k)
        try:
            pressure = self.base_pressure_pa * math.exp(exponent)
        except OverflowError as error:
            raise ValueError("Atmosphere pressure exceeds the finite model domain") from error
        return finite(pressure, "profile pressure", positive=True)

    def density_kg_m3(self, altitude_m: float) -> float:
        temperature = self.temperature_at(altitude_m)
        density = self.pressure_at(altitude_m) / (
            self.specific_gas_constant_j_kg_k * temperature)
        return finite(density, "profile density", positive=True)

    def __call__(self, altitude_m: float) -> float:
        return self.density_kg_m3(altitude_m)


@dataclass(frozen=True, slots=True)
class FragmentFlightEnvironment:
    """Explicit callback owners for air density, wind and gravity."""

    density_kg_m3: Callable[[float], float]
    wind_velocity_m_s: Callable[[np.ndarray, float], np.ndarray]
    gravity_m_s2: np.ndarray
    frame_id: str
    evidence_id: str
    density_evidence_id: str
    wind_evidence_id: str

    def __post_init__(self):
        if not callable(self.density_kg_m3) or not callable(self.wind_velocity_m_s):
            raise TypeError("Supply density and wind callbacks")
        for name in ("frame_id", "evidence_id", "density_evidence_id", "wind_evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must identify the environmental source")
        gravity = _vec3(self.gravity_m_s2, "gravity_m_s2")
        if np.linalg.norm(gravity) <= 0:
            raise ValueError("Gravity vector must be nonzero")
        object.__setattr__(self, "gravity_m_s2", gravity)


@dataclass(frozen=True, slots=True)
class FragmentFlightSettings:
    """Integrator controls and accepted output clock for one flight."""

    clock_id: str
    time_s: np.ndarray
    relative_tolerance: float = 1e-8
    absolute_tolerance: float = 1e-10
    maximum_step_s: float = 0.02
    momentum_tolerance_kg_m_s: float = 1e-6
    mechanical_energy_tolerance_j: float = 1e-5

    def __post_init__(self):
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("clock_id must identify the flight time axis")
        time = np.asarray(self.time_s, dtype=float)
        if (time.ndim != 1 or len(time) < 2 or not np.all(np.isfinite(time))
                or np.any(np.diff(time) <= 0.)):
            raise ValueError("time_s must be a finite, strictly increasing output grid")
        for name in ("relative_tolerance", "absolute_tolerance", "maximum_step_s",
                     "momentum_tolerance_kg_m_s", "mechanical_energy_tolerance_j"):
            finite(getattr(self, name), name, positive=True)
        object.__setattr__(self, "time_s", immutable_array(time, name="time_s"))


@dataclass(frozen=True, slots=True)
class FragmentFlightResult:
    """Trajectory, impact event and independent force/energy residuals."""

    launch: FragmentLaunch
    environment: FragmentFlightEnvironment
    settings: FragmentFlightSettings
    time_s: np.ndarray
    position_m: np.ndarray
    velocity_m_s: np.ndarray
    impact_time_s: float | None
    impact_position_m: np.ndarray | None
    impact_velocity_m_s: np.ndarray | None
    drag_impulse_kg_m_s: np.ndarray
    drag_work_j: float
    momentum_residual_kg_m_s: np.ndarray
    mechanical_energy_residual_j: float
    solver_message: str
    _signature: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if (type(self.launch) is not FragmentLaunch
                or type(self.environment) is not FragmentFlightEnvironment
                or type(self.settings) is not FragmentFlightSettings
                or self.launch.frame_id != self.environment.frame_id):
            raise TypeError("Result inputs must retain one typed, frame-compatible flight contract")
        time = np.asarray(self.time_s, dtype=float)
        pos = np.asarray(self.position_m, dtype=float)
        vel = np.asarray(self.velocity_m_s, dtype=float)
        impulse = _vec3(self.drag_impulse_kg_m_s, "drag_impulse_kg_m_s")
        momentum = _vec3(self.momentum_residual_kg_m_s, "momentum_residual_kg_m_s")
        if (time.ndim != 1 or pos.shape != (len(time), 3) or vel.shape != pos.shape
                or len(time) < 2 or np.any(np.diff(time) <= 0.)
                or not np.all(np.isfinite(pos)) or not np.all(np.isfinite(vel))):
            raise ValueError("Trajectory arrays must share one finite ordered time axis")
        if (time[0] != self.settings.time_s[0]
                or time[-1] > self.settings.time_s[-1]
                or not np.array_equal(pos[0], self.launch.position_m)
                or not np.array_equal(vel[0], self.launch.velocity_m_s)):
            raise ValueError("Trajectory start or support differs from its launch/settings")
        if self.impact_time_s is not None:
            finite(self.impact_time_s, "impact_time_s")
            if self.impact_position_m is None or self.impact_velocity_m_s is None:
                raise ValueError("An impact time requires retained impact position and velocity")
            object.__setattr__(self, "impact_position_m", _vec3(self.impact_position_m,
                                                                 "impact_position_m"))
            object.__setattr__(self, "impact_velocity_m_s", _vec3(self.impact_velocity_m_s,
                                                                   "impact_velocity_m_s"))
            if (time[-1] != self.impact_time_s
                    or abs(self.impact_position_m[2]-self.launch.ground_z_m) > 1e-7
                    or self.impact_velocity_m_s[2] >= 0.):
                raise ValueError("Impact must be the retained descending ground-plane crossing")
        elif self.impact_position_m is not None or self.impact_velocity_m_s is not None:
            raise ValueError("Impact state is available only after the ground event")
        elif time[-1] != self.settings.time_s[-1]:
            raise ValueError("Nonimpact flight must reach the declared time horizon")
        object.__setattr__(self, "time_s", immutable_array(time, name="time_s"))
        object.__setattr__(self, "position_m", immutable_array(pos, name="position_m"))
        object.__setattr__(self, "velocity_m_s", immutable_array(vel, name="velocity_m_s"))
        object.__setattr__(self, "drag_impulse_kg_m_s", impulse)
        object.__setattr__(self, "momentum_residual_kg_m_s", momentum)
        object.__setattr__(self, "drag_work_j", finite(self.drag_work_j, "drag_work_j"))
        object.__setattr__(self, "mechanical_energy_residual_j",
                           finite(self.mechanical_energy_residual_j,
                                  "mechanical_energy_residual_j"))
        if not isinstance(self.solver_message, str):
            raise TypeError("Retain the solver termination message")
        object.__setattr__(self, "_signature", self._digest())

    def _digest(self):
        density_profile_signature = getattr(self.environment.density_kg_m3, "signature", None)
        digest = hashlib.sha256(repr((self.launch, self.environment.evidence_id,
            self.environment.density_evidence_id, self.environment.wind_evidence_id,
            id(self.environment.density_kg_m3), id(self.environment.wind_velocity_m_s),
            density_profile_signature,
            self.environment.gravity_m_s2.tobytes(), self.settings,
            self.impact_time_s, self.drag_work_j, self.mechanical_energy_residual_j,
            self.solver_message)).encode("utf-8"))
        for value in (self.time_s, self.position_m, self.velocity_m_s,
                      self.impact_position_m, self.impact_velocity_m_s,
                      self.drag_impulse_kg_m_s, self.momentum_residual_kg_m_s):
            if value is not None:
                array = np.ascontiguousarray(value)
                digest.update(array.dtype.str.encode("ascii"))
                digest.update(repr(array.shape).encode("ascii"))
                digest.update(array.tobytes())
        return digest.hexdigest()

    def require_current(self):
        if self._digest() != self._signature:
            raise ValueError("Fragment flight result or retained input changed")
        if (np.max(np.abs(self.momentum_residual_kg_m_s))
                > self.settings.momentum_tolerance_kg_m_s
                or abs(self.mechanical_energy_residual_j)
                > self.settings.mechanical_energy_tolerance_j):
            raise ValueError("Fragment flight force or mechanical-energy balance exceeds budget")
        return self


class FragmentFlightError(RuntimeError):
    def __init__(self, cause, *, launch, environment, solver_result=None):
        self.cause = cause
        self.launch = launch
        self.environment = environment
        self.solver_result = solver_result
        super().__init__("Conditional rigid-fragment flight integration failed")


def integrate_fragment_flight(launch: FragmentLaunch,
                              environment: FragmentFlightEnvironment,
                              settings: FragmentFlightSettings) -> FragmentFlightResult:
    """Integrate a caller-defined fragment until ground impact or time horizon.

    Drag uses ``-0.5*rho*Cd*A*|v-w|*(v-w)``. Density depends on height and
    wind may vary with position and time. No default atmospheric or launch model
    is inferred. The augmented state integrates aerodynamic impulse and work for
    independent momentum and mechanical-energy checks.
    """
    if type(launch) is not FragmentLaunch or type(environment) is not FragmentFlightEnvironment:
        raise TypeError("Use explicit FragmentLaunch and FragmentFlightEnvironment inputs")
    if type(settings) is not FragmentFlightSettings:
        raise TypeError("Use explicit FragmentFlightSettings")
    if launch.frame_id != environment.frame_id:
        raise ValueError("Launch, gravity, wind and ground plane must share one declared frame")
    t_eval = settings.time_s
    if t_eval[0] < 0.:
        raise ValueError("Flight time must be nonnegative")
    mass, cd_area = launch.mass_kg, launch.drag_coefficient*launch.reference_area_m2
    gravity = environment.gravity_m_s2

    def rhs(time, state):
        position, velocity = state[:3], state[3:6]
        density = finite(environment.density_kg_m3(float(position[2])),
                         "air density kg/m3", positive=True)
        wind = _vec3(environment.wind_velocity_m_s(position.copy(), float(time)),
                     "wind velocity m/s")
        relative = velocity-wind
        drag = -.5*density*cd_area*np.linalg.norm(relative)*relative
        acceleration = gravity+drag/mass
        drag_work_rate = float(np.dot(drag, velocity))
        return np.concatenate((velocity, acceleration, drag, [drag_work_rate]))

    def ground_event(time, state):
        return float(state[2]-launch.ground_z_m)

    ground_event.terminal = True
    ground_event.direction = -1.
    initial = np.concatenate((launch.position_m, launch.velocity_m_s,
                              np.zeros(4)))
    solution = None
    try:
        solution = solve_ivp(
            rhs, (float(t_eval[0]), float(t_eval[-1])), initial, method="DOP853",
            t_eval=t_eval, dense_output=True, events=ground_event,
            rtol=settings.relative_tolerance, atol=settings.absolute_tolerance,
            max_step=settings.maximum_step_s,
        )
        if not solution.success or solution.sol is None:
            raise RuntimeError(solution.message)
        impact_time = (float(solution.t_events[0][0]) if len(solution.t_events[0]) else None)
        end_time = impact_time if impact_time is not None else float(solution.t[-1])
        sampled_times = t_eval[t_eval <= end_time]
        if len(sampled_times) == 0 or sampled_times[-1] < end_time:
            sampled_times = np.append(sampled_times, end_time)
        states = solution.sol(sampled_times)
        pos, vel = states[:3].T, states[3:6].T
        endpoint = states[:, -1]
        impact_position = endpoint[:3] if impact_time is not None else None
        impact_velocity = endpoint[3:6] if impact_time is not None else None
        impulse = endpoint[6:9]
        drag_work = float(endpoint[9])
        delta_momentum = mass*(endpoint[3:6]-launch.velocity_m_s)
        momentum_residual = delta_momentum-mass*gravity*(end_time-float(t_eval[0]))-impulse
        def mechanical_energy(position, velocity):
            return .5*mass*float(np.dot(velocity, velocity))-mass*float(np.dot(gravity, position))
        energy_residual = (mechanical_energy(endpoint[:3], endpoint[3:6])
                           - mechanical_energy(launch.position_m, launch.velocity_m_s)
                           - drag_work)
        result = FragmentFlightResult(
            launch, environment, settings, sampled_times, pos, vel,
            impact_time, impact_position, impact_velocity, impulse,
            drag_work, momentum_residual, energy_residual, solution.message,
        )
        return result.require_current()
    except Exception as cause:
        raise FragmentFlightError(cause, launch=launch, environment=environment,
                                  solver_result=solution) from cause


__all__ = ["FragmentLaunch", "HydrostaticIdealGasDensityProfile",
           "FragmentFlightEnvironment", "FragmentFlightSettings",
           "FragmentFlightResult", "FragmentFlightError", "integrate_fragment_flight"]
