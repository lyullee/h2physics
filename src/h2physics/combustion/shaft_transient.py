"""Transient single-spool angular momentum and energy balance.

The gas path remains owned by its component models. This module accepts
time-aligned turbine/compressor shaft-power schedules or the existing mapped
native gas-path feedback, plus load torque, then integrates the rotor's finite
kinetic-energy inventory. It adds no map, combustion, thermodynamic, controller,
or equipment correlation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

import numpy as np
from scipy.integrate import solve_ivp

from ..core import finite
from .shaft_brayton_feedback import (
    MapMatchedBraytonShaftFeedback,
    MapMatchedShaftPowerEvaluation,
    ShaftFeedbackEvaluationError,
)


def _vector(values, name, *, minimum=2):
    raw = np.asarray(values)
    if raw.dtype.kind not in "iuf" or raw.dtype.kind == "b":
        raise TypeError(f"{name} must contain real numeric values")
    result = np.array(raw, dtype=float, copy=True)
    if result.ndim != 1 or result.size < minimum or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite vector with at least {minimum} values")
    result.setflags(write=False)
    return result


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name} identity")
    return value.strip()


def _fingerprint(*arrays):
    digest = sha256()
    for array in arrays:
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
        digest.update(np.asarray(array, dtype="<f8").tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ShaftTransientInputs:
    """Caller-owned powers and load torque over one finite rotor window.

    Power histories use piecewise-linear interpolation between strictly
    increasing absolute times. Positive turbine power drives the shaft;
    compressor power, load torque and loss parameters oppose it. Load torque
    may be signed to represent motoring. ``output_time_s`` is a reporting grid;
    the ODE solver controls its own internal steps and terminates at speed
    bounds rather than clipping the rotor state.
    """

    time_s: np.ndarray
    turbine_power_w: np.ndarray
    compressor_power_w: np.ndarray
    load_torque_nm: np.ndarray
    output_time_s: np.ndarray
    rotor_inertia_kg_m2: float
    initial_speed_rad_s: float
    minimum_speed_rad_s: float
    maximum_speed_rad_s: float
    coulomb_loss_torque_nm: float
    viscous_loss_nm_per_rad_s: float
    relative_tolerance: float
    absolute_energy_tolerance_j: float
    maximum_step_s: float
    shaft_id: str
    power_basis_id: str
    load_basis_id: str
    inertia_evidence_id: str
    _signature: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        time = _vector(self.time_s, "time_s")
        turbine = _vector(self.turbine_power_w, "turbine_power_w")
        compressor = _vector(self.compressor_power_w, "compressor_power_w")
        torque = _vector(self.load_torque_nm, "load_torque_nm")
        output = _vector(self.output_time_s, "output_time_s")
        if any(v.shape != time.shape for v in (turbine, compressor, torque)):
            raise ValueError("Power and torque histories must align with time_s")
        if np.any(np.diff(time) <= 0.) or np.any(np.diff(output) <= 0.):
            raise ValueError("Input and output clocks must increase strictly")
        if output[0] < time[0] or output[-1] > time[-1]:
            raise ValueError("Output clock must remain inside the supplied schedule")
        for name, value in (("time_s", time), ("turbine_power_w", turbine),
                            ("compressor_power_w", compressor),
                            ("load_torque_nm", torque), ("output_time_s", output)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "rotor_inertia_kg_m2", finite(
            self.rotor_inertia_kg_m2, "rotor inertia", positive=True))
        initial = finite(self.initial_speed_rad_s, "initial rotor speed", positive=True)
        lower = finite(self.minimum_speed_rad_s, "minimum rotor speed", positive=True)
        upper = finite(self.maximum_speed_rad_s, "maximum rotor speed", positive=True)
        if not lower < initial < upper:
            raise ValueError("Initial speed must lie strictly inside the rotor speed bounds")
        object.__setattr__(self, "initial_speed_rad_s", initial)
        object.__setattr__(self, "minimum_speed_rad_s", lower)
        object.__setattr__(self, "maximum_speed_rad_s", upper)
        for name in ("coulomb_loss_torque_nm", "viscous_loss_nm_per_rad_s"):
            value = finite(getattr(self, name), name)
            if value < 0.:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        for name in ("relative_tolerance", "absolute_energy_tolerance_j", "maximum_step_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        for name in ("shaft_id", "power_basis_id", "load_basis_id", "inertia_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "_signature", _fingerprint(
            time, turbine, compressor, torque, output))

    def require_current(self):
        if self._signature != _fingerprint(
                self.time_s, self.turbine_power_w, self.compressor_power_w,
                self.load_torque_nm, self.output_time_s):
            raise ValueError("Shaft transient schedule changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class ShaftTransientTrace:
    """Sampled rotor response, cumulative shaft work, and solver/event status."""

    inputs: ShaftTransientInputs = field(repr=False, compare=False)
    time_s: np.ndarray
    speed_rad_s: np.ndarray
    kinetic_energy_j: np.ndarray
    cumulative_turbine_work_j: np.ndarray
    cumulative_compressor_work_j: np.ndarray
    cumulative_load_work_j: np.ndarray
    cumulative_coulomb_loss_j: np.ndarray
    cumulative_viscous_loss_j: np.ndarray
    energy_residual_j: np.ndarray
    termination: str
    solver_success: bool
    solver_status: int
    solver_message: str
    function_evaluations: int
    gas_path_feedback: MapMatchedBraytonShaftFeedback | None = field(
        default=None, repr=False, compare=False)
    gas_path_evaluations: tuple[MapMatchedShaftPowerEvaluation, ...] = field(
        default=(), repr=False, compare=False)
    _signature: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.inputs) is not ShaftTransientInputs:
            raise TypeError("Retain the original admitted shaft inputs")
        self.inputs.require_current()
        if self.gas_path_feedback is not None:
            if type(self.gas_path_feedback) is not MapMatchedBraytonShaftFeedback:
                raise TypeError("Retain the original mapped gas-path feedback")
            self.gas_path_feedback.require_current()
            if not self.gas_path_evaluations:
                raise ValueError("A coupled shaft trace must retain its actual gas-path evaluations")
            if any(type(v) is not MapMatchedShaftPowerEvaluation for v in self.gas_path_evaluations):
                raise TypeError("Retain actual mapped power evaluation objects")
            for value in self.gas_path_evaluations:
                value.require_current()
        elif self.gas_path_evaluations:
            raise ValueError("Scheduled shaft traces cannot claim gas-path evaluations")
        arrays = {}
        for name in ("time_s", "speed_rad_s", "kinetic_energy_j",
                     "cumulative_turbine_work_j", "cumulative_compressor_work_j",
                     "cumulative_load_work_j", "cumulative_coulomb_loss_j",
                     "cumulative_viscous_loss_j", "energy_residual_j"):
            arrays[name] = _vector(getattr(self, name), name, minimum=1)
        shape = arrays["time_s"].shape
        if any(array.shape != shape for array in arrays.values()):
            raise ValueError("Every shaft history must share one time axis")
        if np.any(np.diff(arrays["time_s"]) <= 0.) or arrays["time_s"][0] != self.inputs.time_s[0]:
            raise ValueError("Retain an increasing result clock beginning at the initial state")
        if np.any(arrays["speed_rad_s"] <= 0.) or np.any(arrays["kinetic_energy_j"] < 0.):
            raise ValueError("Rotor speed and kinetic energy must remain physical")
        if self.termination not in {"completed", "minimum_speed", "maximum_speed", "solver_failed"}:
            raise ValueError("Unknown shaft integration termination state")
        if self.solver_success is not (self.termination != "solver_failed"):
            raise ValueError("Solver status and termination label disagree")
        if not isinstance(self.solver_message, str) or not self.solver_message:
            raise ValueError("Retain the numerical solver message")
        if (isinstance(self.solver_status, bool) or not isinstance(self.solver_status, int)
                or isinstance(self.function_evaluations, bool)
                or not isinstance(self.function_evaluations, int)
                or self.function_evaluations < 0):
            raise ValueError("Retain solver status and function-evaluation count")
        for name, array in arrays.items():
            object.__setattr__(self, name, array)
        object.__setattr__(self, "_signature", self._payload())

    def _payload(self):
        return (id(self.inputs), self.inputs._signature, self.termination,
                self.solver_success, self.solver_status, self.solver_message,
                self.function_evaluations, id(self.gas_path_feedback),
                tuple((id(v), id(v.native_run), id(v.native_phase), v.time_s, v.speed_rad_s,
                       v.compressor_corrected_speed, v.turbine_corrected_speed,
                       v.speed_mapping_evidence_id) for v in self.gas_path_evaluations),
                tuple((name, _fingerprint(getattr(self, name))) for name in (
                    "time_s", "speed_rad_s", "kinetic_energy_j",
                    "cumulative_turbine_work_j", "cumulative_compressor_work_j",
                    "cumulative_load_work_j", "cumulative_coulomb_loss_j",
                    "cumulative_viscous_loss_j", "energy_residual_j")))

    def require_current(self):
        self.inputs.require_current()
        if self.gas_path_feedback is not None:
            self.gas_path_feedback.require_current()
            for value in self.gas_path_evaluations:
                value.require_current()
        if not self._signature or self._payload() != self._signature:
            raise ValueError("Shaft transient result changed after issuance")
        return self


def integrate_shaft_transient(
    inputs: ShaftTransientInputs,
    *,
    gas_path_feedback: MapMatchedBraytonShaftFeedback | None = None,
) -> ShaftTransientTrace:
    """Integrate a single-spool rotor using explicit boundary power/torque inputs.

    The state is rotational kinetic energy, which avoids division by angular
    velocity at the stalled condition. Input histories are linearly interpolated;
    energy terms enter the same ODE as additional integral states. Solver failure
    returns its accepted dense-output prefix with an explicit ``solver_failed``
    status. Speed limits terminate at the event and are never clipped. Optional
    mapped gas-path feedback replaces the two scheduled power channels at every
    ODE trial using that trial's physical speed. Their schedules must then be zero;
    load torque and rotor losses retain their original meanings.
    """
    if type(inputs) is not ShaftTransientInputs:
        raise TypeError("Supply ShaftTransientInputs")
    inputs.require_current()
    if gas_path_feedback is not None:
        if type(gas_path_feedback) is not MapMatchedBraytonShaftFeedback:
            raise TypeError("Supply MapMatchedBraytonShaftFeedback")
        gas_path_feedback.require_current()
        if (gas_path_feedback.shaft_id != inputs.shaft_id
                or gas_path_feedback.power_basis_id != inputs.power_basis_id):
            raise ValueError("Gas path and rotor must share shaft and power-basis identities")
        if np.any(inputs.turbine_power_w != 0.) or np.any(inputs.compressor_power_w != 0.):
            raise ValueError("Use zero scheduled powers when native gas-path feedback supplies them")
    gas_path_evaluations = []
    gas_path_phase_ids = set()
    t0, tf = float(inputs.time_s[0]), float(inputs.time_s[-1])
    inertia = inputs.rotor_inertia_kg_m2
    initial_energy = 0.5 * inertia * inputs.initial_speed_rad_s**2
    minimum_energy = 0.5 * inertia * inputs.minimum_speed_rad_s**2
    maximum_energy = 0.5 * inertia * inputs.maximum_speed_rad_s**2

    def rates(time_s, energy):
        load = float(np.interp(time_s, inputs.time_s, inputs.load_torque_nm))
        speed = np.sqrt(max(2. * energy, 0.) / inertia)
        if gas_path_feedback is None:
            turbine = float(np.interp(time_s, inputs.time_s, inputs.turbine_power_w))
            compressor = float(np.interp(time_s, inputs.time_s, inputs.compressor_power_w))
        else:
            try:
                if len(gas_path_evaluations) >= gas_path_feedback.maximum_evaluations:
                    raise ValueError("Declared gas-path evaluation budget exhausted")
                point = gas_path_feedback.evaluate(
                    time_s, float(speed), previous_phase_ids=gas_path_phase_ids)
                turbine, compressor = point.turbine_power_w, point.compressor_power_w
                gas_path_evaluations.append(point)
                gas_path_phase_ids.add(id(point.native_phase))
            except Exception as cause:
                raise ShaftFeedbackEvaluationError(
                    time_s, float(speed), gas_path_evaluations, cause) from cause
        coulomb_power = inputs.coulomb_loss_torque_nm * speed
        viscous_power = inputs.viscous_loss_nm_per_rad_s * speed**2
        load_power = load * speed
        return turbine, compressor, load_power, coulomb_power, viscous_power

    def rhs(time_s, state):
        energy = max(float(state[0]), 0.)
        turbine, compressor, load, coulomb, viscous = rates(time_s, energy)
        return (turbine-compressor-load-coulomb-viscous,
                turbine, compressor, load, coulomb, viscous)

    def minimum_event(_time_s, state):
        return state[0] - minimum_energy

    def maximum_event(_time_s, state):
        return maximum_energy - state[0]

    minimum_event.terminal = True
    minimum_event.direction = -1
    maximum_event.terminal = True
    maximum_event.direction = -1
    solution = solve_ivp(
        rhs, (t0, tf), (initial_energy, 0., 0., 0., 0., 0.),
        method="RK45", dense_output=True, max_step=inputs.maximum_step_s,
        rtol=inputs.relative_tolerance,
        atol=(inputs.absolute_energy_tolerance_j,)*6,
        events=(minimum_event, maximum_event),
    )
    termination = "completed"
    end_time = float(solution.t[-1])
    event_state = None
    for index, label in enumerate(("minimum_speed", "maximum_speed")):
        if solution.t_events[index].size:
            termination = label
            end_time = float(solution.t_events[index][-1])
            event_state = solution.y_events[index][-1]
            break
    if not solution.success:
        termination = "solver_failed"
        end_time = float(solution.t[-1])
    times = inputs.output_time_s[inputs.output_time_s <= end_time]
    times = np.asarray(times, dtype=float)
    if times.size == 0 or times[0] != t0:
        times = np.insert(times, 0, t0)
    if times[-1] != end_time:
        times = np.append(times, end_time)
    if event_state is None:
        state = solution.sol(times)
    else:
        state = solution.sol(times)
        state[:, -1] = event_state
    energy = np.maximum(state[0], 0.)
    speed = np.sqrt(2. * energy / inertia)
    residual = (energy-initial_energy-state[1]+state[2]+state[3]+state[4]+state[5])
    if np.max(np.abs(residual)) > max(
            inputs.absolute_energy_tolerance_j,
            inputs.relative_tolerance * max(float(np.max(energy)), 1.)):
        termination = "solver_failed"
    return ShaftTransientTrace(
        inputs, times, speed, energy, state[1], state[2], state[3], state[4], state[5],
        residual, termination, bool(solution.success and termination != "solver_failed"),
        int(solution.status), str(solution.message), int(solution.nfev),
        gas_path_feedback, tuple(gas_path_evaluations),
    )


__all__ = ["ShaftTransientInputs", "ShaftTransientTrace", "integrate_shaft_transient"]
