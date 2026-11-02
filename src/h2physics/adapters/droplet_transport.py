"""Saturated spherical parcel flight with native drag and explicit boiling heat.

This coding-only model has not been executed. Heat-transfer applicability is a
required caller boundary; atmospheric cryogenic condensation is not supplied.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from math import isclose, isfinite, pi

from ..core import finite
from .result_provenance import recorded_content_sha256


_PENDING_PARCEL_TRACE_ISSUERS = set()


def _native_solution_token(native):
    if native is None:
        return None
    return (
        id(native),
        bool(native.success),
        tuple(float(x) for x in native.t),
        tuple(tuple(float(x) for x in row) for row in native.y),
        tuple(tuple(float(x) for x in event) for event in native.t_events),
        tuple(tuple(tuple(float(x) for x in row) for row in event) for event in native.y_events),
    )


def _vector(value, name):
    result = tuple(float(x) for x in value)
    if len(result) != 3 or not all(isfinite(x) for x in result):
        raise ValueError(f"{name} must contain three finite SI components")
    return result


@dataclass(frozen=True)
class ParcelBoundary:
    clock_id: str
    frame_id: str
    evidence_id: str
    carrier_density_kg_m3: float
    carrier_viscosity_pa_s: float
    carrier_velocity_m_s: tuple
    gravity_m_s2: tuple
    maximum_reynolds: float
    maximum_weber: float
    surface_tension_n_m: float
    maximum_laplace_pressure_fraction: float

    def __post_init__(self):
        if not all((self.clock_id, self.frame_id, self.evidence_id)):
            raise ValueError("Clock, frame and boundary evidence are required")
        for name in ("carrier_density_kg_m3", "carrier_viscosity_pa_s",
                     "maximum_reynolds", "maximum_weber", "surface_tension_n_m",
                     "maximum_laplace_pressure_fraction"):
            finite(getattr(self, name), name, positive=True)
        if self.maximum_reynolds > 1e6:
            raise ValueError("Native automatic sphere drag is limited to Re <= 1e6")
        if self.maximum_laplace_pressure_fraction >= 1:
            raise ValueError("Neglected capillary pressure needs a fractional budget below one")
        object.__setattr__(self, "carrier_velocity_m_s", _vector(self.carrier_velocity_m_s, "carrier velocity"))
        object.__setattr__(self, "gravity_m_s2", _vector(self.gravity_m_s2, "gravity"))


@dataclass(frozen=True)
class ParcelState:
    time_s: float
    position_m: tuple
    velocity_m_s: tuple
    mass_kg: float
    diameter_m: float
    reynolds: float
    weber: float
    liquid_state: object
    vapor_state: object


@dataclass(frozen=True)
class ParcelInitialFlash:
    """Isenthalpic equilibrium partition immediately before parcel flight."""

    total_release_mass_kg: float
    upstream_state: object
    downstream_equilibrium_state: object
    saturated_liquid_state: object
    saturated_vapor_state: object
    liquid_mass_kg: float
    flashed_vapor_mass_kg: float
    phase_equilibrium_evidence_id: str
    mass_residual_kg: float
    enthalpy_residual_j: float

    def __post_init__(self):
        from ..core import ThermoState

        states = (self.upstream_state, self.downstream_equilibrium_state,
                  self.saturated_liquid_state, self.saturated_vapor_state)
        if any(type(state) is not ThermoState for state in states):
            raise TypeError("Initial flash retains four typed thermodynamic endpoint states")
        total = finite(self.total_release_mass_kg, "total_release_mass_kg", positive=True)
        liquid = finite(self.liquid_mass_kg, "liquid_mass_kg")
        vapor = finite(self.flashed_vapor_mass_kg, "flashed_vapor_mass_kg")
        if liquid < 0. or vapor < 0.:
            raise ValueError("Initial flash phase masses cannot be negative")
        if (not isinstance(self.phase_equilibrium_evidence_id, str)
                or not self.phase_equilibrium_evidence_id.strip()):
            raise ValueError("Initial equilibrium flash requires explicit phase-evidence identity")
        finite(self.mass_residual_kg, "mass_residual_kg")
        finite(self.enthalpy_residual_j, "enthalpy_residual_j")
        if not self.upstream_state.basis == self.downstream_equilibrium_state.basis:
            raise ValueError("Initial flash changes property or energy-reference basis")
        self.upstream_state.basis.require_compatible(self.saturated_liquid_state.basis)
        self.upstream_state.basis.require_compatible(self.saturated_vapor_state.basis)
        if (self.downstream_equilibrium_state.phase != "two_phase"
                or self.downstream_equilibrium_state.vapor_mass_fraction is None
                or self.saturated_liquid_state.vapor_mass_fraction != 0.
                or self.saturated_vapor_state.vapor_mass_fraction != 1.):
            raise ValueError("Initial flash endpoints must retain two-phase and saturated endpoint identities")
        if not isclose(self.vapor_mass_fraction,
                       self.downstream_equilibrium_state.vapor_mass_fraction,
                       rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Initial flash phase masses differ from the native PH quality")
        downstream_pressure = self.downstream_equilibrium_state.pressure_pa
        if (self.upstream_state.phase not in {"liquid", "two_phase"}
                or self.upstream_state.vapor_mass_fraction not in (None, 0.)):
            raise ValueError("Initial liquid flash requires a liquid-only upstream state")
        if downstream_pressure >= self.upstream_state.pressure_pa:
            raise ValueError("Initial liquid flash requires a strictly decreasing pressure")
        if not isclose(self.downstream_equilibrium_state.enthalpy_j_kg,
                       self.upstream_state.enthalpy_j_kg,
                       rel_tol=1e-9, abs_tol=1e-5):
            raise ValueError("Native PH flash did not retain upstream specific enthalpy")
        if (not isclose(self.saturated_liquid_state.pressure_pa, downstream_pressure,
                        rel_tol=1e-12, abs_tol=1e-8)
                or not isclose(self.saturated_vapor_state.pressure_pa, downstream_pressure,
                               rel_tol=1e-12, abs_tol=1e-8)):
            raise ValueError("Flash equilibrium and saturated endpoints must share one pressure")
        if not isclose(total, liquid+vapor, rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Initial flash phase masses do not close to the released mass")
        if not isclose(total-liquid-vapor, self.mass_residual_kg,
                       rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Initial flash mass residual differs from its phase ledger")
        expected_energy = total*self.upstream_state.enthalpy_j_kg
        partition_energy = (
            liquid*self.saturated_liquid_state.enthalpy_j_kg
            + vapor*self.saturated_vapor_state.enthalpy_j_kg
        )
        if not isclose(expected_energy-partition_energy, self.enthalpy_residual_j,
                       rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Initial flash enthalpy residual differs from its phase ledger")
        energy_scale = max(abs(expected_energy), abs(partition_energy), total)
        if abs(self.enthalpy_residual_j) > max(total*1e-5, energy_scale*1e-9):
            raise ValueError("Initial flash saturated endpoints fail enthalpy closure")

    @property
    def vapor_mass_fraction(self):
        return self.flashed_vapor_mass_kg/self.total_release_mass_kg

    @property
    def launch_liquid_mass_kg(self):
        """Liquid mass available to the subsequent isolated-parcel flight model."""
        return self.liquid_mass_kg


def flash_initial_liquid_release(properties, upstream_state, *, downstream_pressure_pa,
                                 total_release_mass_kg, phase_equilibrium_evidence_id):
    """Partition a finite liquid release by a native isenthalpic equilibrium flash.

    This supplies an initial liquid mass to ``SaturatedParcelFlight``. It does not
    represent the flashing jet, phase slip, flash-vapor momentum, or subsequent
    aerosol formation; those remain caller-owned boundary conditions.
    """
    from ..core import ThermoState

    if type(upstream_state) is not ThermoState:
        raise TypeError("Initial flash requires one typed upstream ThermoState")
    if (not isinstance(phase_equilibrium_evidence_id, str)
            or not phase_equilibrium_evidence_id.strip()):
        raise ValueError("Supply evidence for the equilibrium-throttling assumption")
    total = finite(total_release_mass_kg, "total_release_mass_kg", positive=True)
    downstream_pressure = finite(downstream_pressure_pa, "downstream_pressure_pa", positive=True)
    if (upstream_state.phase not in {"liquid", "two_phase"}
            or upstream_state.vapor_mass_fraction not in (None, 0.)):
        raise ValueError("Initial liquid flash requires a liquid-only upstream state")
    if downstream_pressure >= upstream_state.pressure_pa:
        raise ValueError("Initial liquid flash requires a strictly decreasing pressure")
    properties.basis.require_compatible(upstream_state.basis)
    equilibrium = properties.state_ph(downstream_pressure, upstream_state.enthalpy_j_kg)
    properties.basis.require_compatible(equilibrium.basis)
    if (equilibrium.phase != "two_phase" or equilibrium.vapor_mass_fraction is None
            or not 0. <= equilibrium.vapor_mass_fraction <= 1.):
        raise ValueError("Initial flash state must be inside a resolved two-phase equilibrium domain")
    liquid_state = properties.saturated(downstream_pressure, 0.)
    vapor_state = properties.saturated(downstream_pressure, 1.)
    properties.basis.require_compatible(liquid_state.basis)
    properties.basis.require_compatible(vapor_state.basis)
    quality = equilibrium.vapor_mass_fraction
    liquid_mass = total*(1.-quality)
    vapor_mass = total*quality
    mass_residual = total-liquid_mass-vapor_mass
    energy_residual = (
        total*upstream_state.enthalpy_j_kg
        - liquid_mass*liquid_state.enthalpy_j_kg
        - vapor_mass*vapor_state.enthalpy_j_kg
    )
    return ParcelInitialFlash(
        total_release_mass_kg=total,
        upstream_state=upstream_state,
        downstream_equilibrium_state=equilibrium,
        saturated_liquid_state=liquid_state,
        saturated_vapor_state=vapor_state,
        liquid_mass_kg=liquid_mass,
        flashed_vapor_mass_kg=vapor_mass,
        phase_equilibrium_evidence_id=phase_equilibrium_evidence_id,
        mass_residual_kg=mass_residual,
        enthalpy_residual_j=energy_residual,
    )


@dataclass(frozen=True)
class BoilingHeat:
    heat_into_liquid_w: float
    evidence_id: str
    raw_result: object = None

    def __post_init__(self):
        finite(self.heat_into_liquid_w, "heat_into_liquid_w")
        if self.heat_into_liquid_w < 0 or not self.evidence_id:
            raise ValueError("Saturated boiling requires nonnegative heat and qualified evidence")


@dataclass(frozen=True)
class ParcelTrial:
    state: ParcelState
    heat: BoilingHeat
    drag_coefficient: float
    drag_force_n: tuple


@dataclass(frozen=True)
class ParcelTrace:
    boundary: ParcelBoundary
    native_result: object
    trials: tuple
    states: tuple
    end_reason: str
    evaporated_mass_kg: float
    heat_into_liquid_j: float
    drag_work_j: float
    vapor_total_energy_out_j: float
    vapor_momentum_out_kg_m_s: tuple
    ambient_pressure_work_into_j: float
    mass_residual_kg: float
    total_energy_residual_j: float
    momentum_residual_kg_m_s: tuple
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PARCEL_TRACE_ISSUERS:
            raise ValueError("Parcel traces are issued only by a completed native flight run")
        _PENDING_PARCEL_TRACE_ISSUERS.remove(self._issuer_token)
        if self.native_result is None or not getattr(self.native_result, "success", False):
            raise ValueError("Parcel trace requires a completed successful native solution")
        object.__setattr__(self, "trials", tuple(self.trials))
        object.__setattr__(self, "states", tuple(self.states))
        object.__setattr__(self, "vapor_momentum_out_kg_m_s",
                           tuple(self.vapor_momentum_out_kg_m_s))
        object.__setattr__(self, "momentum_residual_kg_m_s",
                           tuple(self.momentum_residual_kg_m_s))
        if len(self.states) < 2 or len(self.vapor_momentum_out_kg_m_s) != 3 or len(self.momentum_residual_kg_m_s) != 3:
            raise ValueError("Parcel trace requires accepted states and three-axis momentum ledgers")
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self):
        return recorded_content_sha256((
            self._issuer_token, id(self.boundary), self.boundary, _native_solution_token(self.native_result),
            self.trials, self.states, self.end_reason, self.evaporated_mass_kg,
            self.heat_into_liquid_j, self.drag_work_j, self.vapor_total_energy_out_j,
            self.vapor_momentum_out_kg_m_s, self.ambient_pressure_work_into_j,
            self.mass_residual_kg, self.total_energy_residual_j,
            self.momentum_residual_kg_m_s,
        ))

    def require_current(self):
        if self._content_fingerprint() != self._seal:
            raise ValueError("Parcel trace or retained native solution changed after issuance")
        native = self.native_result
        if (not native.success or len(native.t) != len(self.states)
                or native.y.shape[1] != len(self.states)):
            raise ValueError("Parcel trace no longer matches its accepted native solution")
        first, last = self.states[0], self.states[-1]
        final = native.y[:, -1]
        expected_mass = last.mass_kg + float(final[7]) - first.mass_kg
        pressure_work = -last.liquid_state.pressure_pa * (
            last.mass_kg-first.mass_kg
        ) / last.liquid_state.density_kg_m3
        potential_first = -sum(g*x for g, x in zip(self.boundary.gravity_m_s2, first.position_m))
        potential_last = -sum(g*x for g, x in zip(self.boundary.gravity_m_s2, last.position_m))
        total_first = first.mass_kg * (
            first.liquid_state.internal_energy_j_kg
            + sum(v*v for v in first.velocity_m_s)/2 + potential_first
        )
        total_last = last.mass_kg * (
            last.liquid_state.internal_energy_j_kg
            + sum(v*v for v in last.velocity_m_s)/2 + potential_last
        )
        expected_energy = total_last-total_first+float(final[10]-final[8]-final[9])-pressure_work
        expected_momentum = tuple(
            last.mass_kg*v-first.mass_kg*u+float(final[11+i]-final[14+i])
            for i, (u, v) in enumerate(zip(first.velocity_m_s, last.velocity_m_s))
        )
        if not isclose(self.evaporated_mass_kg, float(final[7]), rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Parcel evaporation summary differs from its native output ledger")
        if not isclose(self.heat_into_liquid_j, float(final[8]), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Parcel heat summary differs from its native output ledger")
        if not isclose(self.drag_work_j, float(final[9]), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Parcel drag work differs from its native output ledger")
        if not isclose(self.vapor_total_energy_out_j, float(final[10]), rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Parcel vapor energy differs from its native output ledger")
        if any(not isclose(actual, float(final[11+i]), rel_tol=1e-12, abs_tol=1e-12)
               for i, actual in enumerate(self.vapor_momentum_out_kg_m_s)):
            raise ValueError("Parcel vapor momentum differs from its native output ledger")
        if not isclose(self.ambient_pressure_work_into_j, pressure_work,
                       rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Parcel pressure work differs from its endpoint states")
        if not isclose(self.mass_residual_kg, expected_mass, rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("Parcel mass residual differs from retained endpoints")
        if not isclose(self.total_energy_residual_j, expected_energy, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Parcel energy residual differs from retained native ledgers")
        if any(not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
               for actual, expected in zip(self.momentum_residual_kg_m_s, expected_momentum)):
            raise ValueError("Parcel momentum residual differs from retained native ledgers")
        if any(float(native.t[i]) != state.time_s
               or tuple(float(x) for x in native.y[:3, i]) != state.position_m
               or tuple(float(x) for x in native.y[3:6, i]) != state.velocity_m_s
               or float(native.y[6, i]) != state.mass_kg
               for i, state in enumerate(self.states)):
            raise ValueError("Parcel accepted states differ from the original native solution")
        if self.end_reason == "incident_ground_crossing":
            if len(native.t_events) != 2 or float(native.t[-1]) not in native.t_events[1]:
                raise ValueError("Ground-crossing end reason differs from the native event")
        elif self.end_reason == "residual_mass_floor":
            if not native.t_events or float(native.t[-1]) not in native.t_events[0]:
                raise ValueError("Depletion end reason differs from the native event")
        elif self.end_reason == "time_limit":
            if any(len(event) for event in native.t_events):
                raise ValueError("Time-limit end reason masks a native terminal event")
        else:
            raise ValueError("Unknown native parcel terminal reason")
        return self


class ParcelFlightError(RuntimeError):
    def __init__(self, cause, trials, native_result=None):
        super().__init__(str(cause))
        self.cause = cause
        self.trials = tuple(trials)
        self.native_result = native_result


class SaturatedParcelFlight:
    """One isolated parcel; constant saturation pressure and fixed carrier field.

    Isotropic evaporation leaves with parcel velocity. Added mass, buoyancy,
    breakup, collisions and gas back-reaction are excluded by the supplied
    dilute/high-density-ratio boundary qualification. No air phase model is
    inferred from a heat callback. Positive residual mass is always retained.
    """

    def __init__(self, properties, pressure_pa, boundary: ParcelBoundary,
                 boiling_heat: Callable[[ParcelState], BoilingHeat], *,
                 force_approximation_evidence_id: str):
        if not force_approximation_evidence_id:
            raise ValueError("Qualify isolated heavy-particle force approximations explicitly")
        self.properties = properties
        self.boundary = boundary
        self.boiling_heat = boiling_heat
        self.force_approximation_evidence_id = force_approximation_evidence_id
        self.pressure_pa = finite(pressure_pa, "pressure_pa", positive=True)
        self.liquid = properties.saturated(self.pressure_pa, 0.)
        self.vapor = properties.saturated(self.pressure_pa, 1.)
        self.liquid.basis.require_compatible(self.vapor.basis)
        self.latent_heat_j_kg = self.vapor.enthalpy_j_kg-self.liquid.enthalpy_j_kg
        finite(self.latent_heat_j_kg, "latent_heat_j_kg", positive=True)

    def _state(self, time, y):
        mass = finite(float(y[6]), "trial parcel mass", positive=True)
        diameter = (6*mass/(pi*self.liquid.density_kg_m3))**(1/3)
        velocity = _vector(y[3:6], "trial velocity")
        relative = tuple(u-v for u, v in zip(self.boundary.carrier_velocity_m_s, velocity))
        speed2 = sum(x*x for x in relative)
        re = self.boundary.carrier_density_kg_m3*diameter*speed2**.5/self.boundary.carrier_viscosity_pa_s
        we = self.boundary.carrier_density_kg_m3*diameter*speed2/self.boundary.surface_tension_n_m
        if re > self.boundary.maximum_reynolds or we > self.boundary.maximum_weber:
            raise ValueError("Trial leaves qualified drag/spherical-drop domain")
        laplace_fraction = 4*self.boundary.surface_tension_n_m/diameter/self.pressure_pa
        if laplace_fraction > self.boundary.maximum_laplace_pressure_fraction:
            raise ValueError("Trial exceeds neglected Laplace-pressure budget")
        return ParcelState(float(time), _vector(y[:3], "trial position"), velocity,
                           mass, diameter, re, we, self.liquid, self.vapor)

    def run(self, *, start_s, end_s, position_m, velocity_m_s, mass_kg,
            residual_mass_floor_kg, maximum_step_s, relative_tolerance,
            absolute_tolerances, ground_z_m=None):
        """Integrate with SciPy, retaining native trials and original failures.

        Absolute tolerances have 17 entries in the order documented with the
        state vector below. Trial excursions are rejected, never clipped.
        Ground crossing reports incident liquid only, never deposited liquid.
        """
        import numpy as np
        from fluids.drag import drag_sphere
        from scipy.integrate import solve_ivp

        start = finite(start_s, "start_s")
        end = finite(end_s, "end_s")
        mass = finite(mass_kg, "mass_kg", positive=True)
        floor = finite(residual_mass_floor_kg, "residual_mass_floor_kg", positive=True)
        step = finite(maximum_step_s, "maximum_step_s", positive=True)
        rtol = finite(relative_tolerance, "relative_tolerance", positive=True)
        atol = tuple(absolute_tolerances)
        if end <= start or floor >= mass or len(atol) != 17:
            raise ValueError("Require positive interval, smaller positive floor and 17 tolerances")
        for tolerance in atol:
            finite(tolerance, "absolute tolerance", positive=True)
        position = _vector(position_m, "position_m")
        velocity = _vector(velocity_m_s, "velocity_m_s")
        if ground_z_m is not None:
            ground_z_m = finite(ground_z_m, "ground_z_m")
            if position[2] <= ground_z_m:
                raise ValueError("Initial parcel must be above the ground plane")
        # x[3], v[3], m, evaporated m, Q, drag work, vapor H+K+PE,
        # vapor momentum[3], integrated external force[3].
        initial = np.array((*position, *velocity, mass, *([0.]*10)), dtype=float)
        trials = []
        gravity = self.boundary.gravity_m_s2
        binding = (self.boundary, self.liquid, self.vapor, self.boiling_heat,
                   self.properties, self.pressure_pa, self.latent_heat_j_kg)

        def guard():
            current = (self.boundary, self.liquid, self.vapor, self.boiling_heat,
                       self.properties, self.pressure_pa, self.latent_heat_j_kg)
            if any(a is not b for a, b in zip(current[:5], binding[:5])) or current[5:] != binding[5:]:
                raise ValueError("Parcel owner configuration changed during integration")

        def rhs(time, y):
            guard()
            state = self._state(time, y)
            heat = self.boiling_heat(state)
            guard()
            if not isinstance(heat, BoilingHeat):
                raise TypeError("Heat closure must return BoilingHeat with original evidence")
            relative = tuple(u-v for u, v in zip(self.boundary.carrier_velocity_m_s, state.velocity_m_s))
            speed = sum(x*x for x in relative)**.5
            cd = 0. if speed == 0 else float(drag_sphere(state.reynolds))
            finite(cd, "native drag coefficient")
            if cd < 0:
                raise ValueError("Native drag coefficient is negative")
            coefficient = .5*self.boundary.carrier_density_kg_m3*pi*state.diameter_m**2/4*cd*speed
            force = tuple(coefficient*x for x in relative)
            trials.append(ParcelTrial(state, heat, cd, force))
            rate = heat.heat_into_liquid_w/self.latent_heat_j_kg
            external = tuple(f+state.mass_kg*g for f, g in zip(force, gravity))
            potential = -sum(g*x for g, x in zip(gravity, state.position_m))
            vapor_energy = self.vapor.enthalpy_j_kg+sum(v*v for v in state.velocity_m_s)/2+potential
            return (*state.velocity_m_s, *(f/state.mass_kg for f in external), -rate,
                    rate, heat.heat_into_liquid_w,
                    sum(f*v for f, v in zip(force, state.velocity_m_s)), rate*vapor_energy,
                    *(rate*v for v in state.velocity_m_s), *external)

        def depleted(time, y):
            return y[6]-floor

        depleted.terminal, depleted.direction = True, -1
        events = [depleted]
        if ground_z_m is not None:
            def ground(time, y):
                return y[2]-ground_z_m
            ground.terminal, ground.direction = True, -1
            events.append(ground)
        native = None
        try:
            self._state(start, initial)
            native = solve_ivp(rhs, (start, end), initial, events=events,
                               rtol=rtol, atol=atol, max_step=step)
            if not native.success:
                raise RuntimeError(native.message)
            guard()
            states = tuple(self._state(t, y) for t, y in zip(native.t, native.y.T))
            first, last = states[0], states[-1]
            final = native.y[:, -1]

            def total(state):
                potential = -sum(g*x for g, x in zip(gravity, state.position_m))
                return state.mass_kg*(self.liquid.internal_energy_j_kg+
                    sum(v*v for v in state.velocity_m_s)/2+potential)

            reason = "time_limit"
            if len(native.t_events[0]):
                reason = "residual_mass_floor"
            elif ground_z_m is not None and len(native.t_events[1]):
                reason = "incident_ground_crossing"
            momentum = tuple(last.mass_kg*v-first.mass_kg*u+final[11+i]-final[14+i]
                             for i, (u, v) in enumerate(zip(first.velocity_m_s, last.velocity_m_s)))
            pressure_work = -self.pressure_pa*(last.mass_kg-first.mass_kg)/self.liquid.density_kg_m3
            token = object()
            _PENDING_PARCEL_TRACE_ISSUERS.add(token)
            try:
                return ParcelTrace(self.boundary, native, tuple(trials), states, reason,
                    float(final[7]), float(final[8]), float(final[9]), float(final[10]),
                    tuple(float(x) for x in final[11:14]),
                    pressure_work,
                    last.mass_kg+float(final[7])-first.mass_kg,
                    total(last)-total(first)+float(final[10]-final[8]-final[9])-pressure_work, momentum,
                    _issuer_token=token).require_current()
            except Exception:
                _PENDING_PARCEL_TRACE_ISSUERS.discard(token)
                raise
        except Exception as error:
            raise ParcelFlightError(error, trials, native) from error
