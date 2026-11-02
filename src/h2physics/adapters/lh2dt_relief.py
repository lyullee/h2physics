"""Transactional native pressure-relief state and finite native tank events.

Native LH2DT owns the binary set/reseat policy, tank equations and RK4 steps.
The existing shared nozzle owns every flow solution. This adapter owns accepted
state transactions, bracketed event localization and independent boundary audits.
Native public API: https://github.com/lyullee/lh2dt_models
"""

import copy
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..core import immutable_array, ThermoState, finite
from ..release import HomogeneousIsentropicNozzle, NozzleOpening
from .lh2dt import Lh2dtProperties, to_lh2dt_state
from .lh2dt_equipment import Lh2dtSharedValve, SharedValveEvaluation


class ReliefCapabilityError(RuntimeError):
    """The requested native capability cannot preserve this protection contract."""


def shared_native_relief(*, native_valve_type, native_relief_factory,
                         result_factory: Callable, nozzle: HomogeneousIsentropicNozzle,
                         bridge: Lh2dtProperties, opening: NozzleOpening,
                         set_pressure_pa_absolute: float, reseat_pressure_pa_absolute: float,
                         native_source_id: str):
    """Construct an actual native Valve subclass and PressureReliefValve.

    Only public Valve.evaluate is specialized; it delegates the existing shared
    valve, with no copied native flow equations. The native isinstance(Valve)
    contract is honored. This binary, forward-only level has no seat leakage.
    """
    for value in (set_pressure_pa_absolute, reseat_pressure_pa_absolute):
        finite(value, "absolute protection pressure", positive=True)
    if reseat_pressure_pa_absolute >= set_pressure_pa_absolute:
        raise ValueError("This binary event level requires strict set/reseat hysteresis")
    nozzle.properties.basis.require_compatible(bridge.basis)
    views = {fraction: Lh2dtSharedValve(nozzle, bridge, opening,
        result_factory=result_factory, opening_fraction=fraction, allow_reverse=False)
        for fraction in (0., 1.)}

    class NativeSharedNozzleValve(native_valve_type):
        def __init__(self):
            super().__init__(opening.nominal_area_m2, opening.effective_area_factor,
                properties=bridge.native, pressure_samples=12, allow_reverse=False,
                closed_leakage_CdA_m2=0.)

        def evaluate(self, left, right, opening=1.):
            value = finite(opening, "native binary relief opening")
            if value not in views:
                raise ValueError("This native relief flow bridge supports binary opening only")
            return views[value].evaluate(left, right)

    try:
        valve = NativeSharedNozzleValve()
        native = native_relief_factory(valve, set_pressure_pa_absolute, reseat_pressure_pa_absolute)
    except (TypeError, AttributeError) as exc:
        raise ReliefCapabilityError("Native public Valve/PressureReliefValve capabilities are unavailable") from exc
    return Lh2dtReliefProtection(native, bridge=bridge, opening=opening,
                                 native_source_id=native_source_id)


class Lh2dtReliefProtection:
    """Accepted protection state separated from arbitrary physical trial probes.

    Probes evaluate the underlying actual native valve at the accepted binary
    opening. Native latch logic runs only on a shallow copy at commit, promoted
    atomically after successful evaluation. The original and every promoted copy
    remain actual native objects; no protected latch field is assigned here.
    """

    def __init__(self, native, *, bridge: Lh2dtProperties, opening: NozzleOpening,
                 native_source_id: str):
        if not isinstance(native_source_id, str) or not native_source_id.strip():
            raise ValueError("Declare the separately installed native source identity")
        for name in ("is_open", "set_pressure_Pa", "reseat_pressure_Pa", "valve", "evaluate", "reset"):
            if not hasattr(native, name):
                raise ReliefCapabilityError(f"Native relief lacks public {name}")
        if not isinstance(native.is_open, bool):
            raise ReliefCapabilityError("Native relief must expose a binary latch")
        if (native.valve.properties is not bridge.native or native.valve.allow_reverse
                or native.valve.closed_leakage_CdA_m2 != 0.):
            raise ReliefCapabilityError("Relief requires shared properties, forward-only flow and zero seat leakage")
        if not 0 < native.reseat_pressure_Pa < native.set_pressure_Pa:
            raise ValueError("This binary event level requires strict set/reseat hysteresis")
        self.native_origin, self.native = native, copy.copy(native)
        if self.native is native or self.native.valve is not native.valve:
            raise ReliefCapabilityError("Native relief cannot be shallow-copied with a shared stateless flow strategy")
        self.bridge, self.opening, self.native_source_id = bridge, opening, native_source_id
        self.set_pressure_pa = float(native.set_pressure_Pa)
        self.reseat_pressure_pa = float(native.reseat_pressure_Pa)
        self._accepted_open = native.is_open
        self._clock_id = None
        self._accepted_time_s = None

    @property
    def is_open(self):
        self._require_unchanged()
        return self._accepted_open

    def _require_unchanged(self):
        if (self.native.is_open != self._accepted_open
                or self.native.set_pressure_Pa != self.set_pressure_pa
                or self.native.reseat_pressure_Pa != self.reseat_pressure_pa):
            raise ReliefCapabilityError("Accepted native protection state or thresholds were externally modified")

    def evaluate(self, left, right) -> SharedValveEvaluation:
        self._require_unchanged()
        result = self.native.valve.evaluate(left, right, opening=float(self._accepted_open))
        if not isinstance(result, SharedValveEvaluation):
            raise ReliefCapabilityError("Relief flow must retain actual shared-nozzle and native valve results")
        if result.mass_flow_kg_s < 0:
            raise ReliefCapabilityError("Relief flow reversed despite the one-way contract")
        return result

    def commit(self, time_s, left, right, *, clock_id):
        """Apply native latch policy to an explicitly accepted physical state."""
        self._require_unchanged()
        time = finite(time_s, "accepted protection time")
        if (not isinstance(clock_id, str) or not clock_id.strip()
                or (self._clock_id is not None and clock_id != self._clock_id)):
            raise ValueError("Accepted protection clock identities differ")
        if self._accepted_time_s is not None and time < self._accepted_time_s:
            raise ValueError("Accepted protection time cannot move backwards")
        candidate = copy.copy(self.native)
        if candidate is self.native or candidate.valve is not self.native.valve:
            raise ReliefCapabilityError("Native latch copy changed the flow strategy")
        result = candidate.evaluate(left, right)
        if not isinstance(result, SharedValveEvaluation) or result.mass_flow_kg_s < 0:
            raise ReliefCapabilityError("Native relief commit returned an unavailable or reversed flow")
        before = self.native
        self.native = candidate
        self._accepted_open = candidate.is_open
        self._accepted_time_s, self._clock_id = time, clock_id
        return before, candidate, result


@dataclass(frozen=True, slots=True)
class ReliefTankBoundary:
    clock_id: str
    support_start_s: float
    support_end_s: float
    downstream: ThermoState
    ambient_temperature_k: Callable
    direct_wall_heat_w: Callable
    source_id: str

    def __post_init__(self):
        finite(self.support_start_s, "boundary support start")
        finite(self.support_end_s, "boundary support end")
        if self.support_start_s >= self.support_end_s:
            raise ValueError("Relief boundary clock support must increase")
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not isinstance(self.source_id, str) or not self.source_id.strip()
                or not callable(self.ambient_temperature_k) or not callable(self.direct_wall_heat_w)):
            raise ValueError("Explicit clock/source and ambient/wall-heat callbacks are required")

    def require_time(self, time):
        if not self.support_start_s <= time <= self.support_end_s:
            raise ValueError("Native relief trial exceeded boundary clock support")


@dataclass(frozen=True, slots=True)
class ReliefEventSettings:
    time_tolerance_s: float = 1e-8
    pressure_tolerance_pa: float = .001
    mass_tolerance_kg: float = 1e-12
    minimum_native_interval_s: float = 1e-9
    maximum_iterations: int = 80
    maximum_events: int = 1000

    def __post_init__(self):
        for name in ("time_tolerance_s", "pressure_tolerance_pa", "mass_tolerance_kg",
                     "minimum_native_interval_s"):
            finite(getattr(self, name), name, positive=True)
        if self.minimum_native_interval_s < 1e-9 or self.time_tolerance_s < self.minimum_native_interval_s:
            raise ValueError("Native tank intervals need a declared >=1e-9 s clock floor")
        for value in (self.maximum_iterations, self.maximum_events):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Relief event iteration/count limits must be positive integers")


@dataclass(frozen=True, slots=True)
class ReliefStage:
    time_s: float
    native_thermo: object
    wall_temperature_k: float
    source: SharedValveEvaluation
    external_heat_w: float


@dataclass(frozen=True, slots=True)
class ReliefNativeInterval:
    start_time_s: float
    end_time_s: float
    native_step: object
    stages: tuple[ReliefStage, ...]
    interval_is_open: bool
    released_mass_kg: float
    released_enthalpy_j: float
    external_heat_j: float
    source_at_start: SharedValveEvaluation
    source_at_end: SharedValveEvaluation


@dataclass(frozen=True, slots=True)
class ReliefTransition:
    time_s: float
    kind: str
    pressure_pa: float
    threshold_pa: float
    lower_bracket_time_s: float
    upper_bracket_time_s: float
    native_before: object
    native_after: object
    source_before: SharedValveEvaluation
    source_after: SharedValveEvaluation
    native_tank_state: object


@dataclass(frozen=True, slots=True)
class ReliefInventoryTermination:
    time_s: float
    mass_kg: float
    minimum_inventory_kg: float
    lower_bracket_time_s: float
    upper_bracket_time_s: float
    native_tank_state: object
    source_at_limit: SharedValveEvaluation


@dataclass(frozen=True, slots=True)
class ReliefTankTrace:
    clock_id: str
    initial_state: object
    initial_source: SharedValveEvaluation
    intervals: tuple[ReliefNativeInterval, ...]
    transitions: tuple[ReliefTransition, ...]
    time_s: np.ndarray
    mass_residual_kg: np.ndarray
    energy_residual_j: np.ndarray
    released_mass_kg: np.ndarray
    released_enthalpy_j: np.ndarray
    external_heat_j: np.ndarray
    native_tank: object
    native_relief_origin: object
    native_relief_final: object
    termination: str
    minimum_inventory_kg: float
    trial_interval_count: int
    event_settings: ReliefEventSettings
    inventory_event: ReliefInventoryTermination | None
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RELIEF_TRACE_ISSUERS:
            raise TypeError("Create relief tank traces through Lh2dtReliefTankDriver.run")
        _PENDING_RELIEF_TRACE_ISSUERS.remove(self._issuer_token)
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Relief trace needs an explicit clock identity")
        for name in ("time_s", "mass_residual_kg", "energy_residual_j", "released_mass_kg",
                     "released_enthalpy_j", "external_heat_j"):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            values = immutable_array(values, name="values")
            object.__setattr__(self, name, values)
        names = ("time_s", "mass_residual_kg", "energy_residual_j", "released_mass_kg",
                 "released_enthalpy_j", "external_heat_j")
        arrays = [getattr(self, name) for name in names]
        if (any(value.ndim != 1 or not np.all(np.isfinite(value)) for value in arrays)
                or len(arrays[0]) < 1
                or any(value.shape != arrays[0].shape for value in arrays[1:])):
            raise ValueError("Relief trace ledgers must be finite aligned one-dimensional histories")
        if (not isinstance(self.termination, str)
                or self.termination not in {"window_end", "inventory_floor"}
                or not np.isfinite(self.minimum_inventory_kg)
                or self.minimum_inventory_kg <= 0):
            raise ValueError("Relief trace termination and inventory floor are invalid")
        if len(self.intervals) != len(self.time_s) - 1:
            raise ValueError("Every relief output interval must retain one native accepted interval")
        if np.any(np.diff(self.time_s) <= 0):
            raise ValueError("Relief trace output clock must be strictly increasing")
        if len(self.time_s) > 1 and any(
            not np.isclose(interval.start_time_s, self.time_s[index], rtol=0., atol=1e-10)
            or not np.isclose(interval.end_time_s, self.time_s[index + 1], rtol=0., atol=1e-10)
            for index, interval in enumerate(self.intervals)
        ):
            raise ValueError("Relief native intervals do not match the retained output clock")
        mass0 = finite(self.initial_state.hydrogen_mass_kg, "initial relief inventory", positive=True)
        state = self.initial_state
        initial_energy = (finite(state.hydrogen_internal_energy_J, "initial hydrogen energy")
                          + finite(self.native_tank.geometry.wall_heat_capacity_J_K,
                                   "wall heat capacity", positive=True)
                          * finite(state.wall_temperature_K, "initial wall temperature", positive=True))
        mass_out = energy_out = heat_in = 0.0
        expected_mass_residual = [0.0]
        expected_energy_residual = [0.0]
        expected_mass_out = [0.0]
        expected_energy_out = [0.0]
        expected_heat_in = [0.0]
        for interval in self.intervals:
            state = interval.native_step.state
            mass_out += finite(interval.released_mass_kg, "interval released mass")
            energy_out += finite(interval.released_enthalpy_j, "interval discharged enthalpy")
            heat_in += finite(interval.external_heat_j, "interval external heat")
            state_energy = (finite(state.hydrogen_internal_energy_J, "hydrogen energy")
                            + self.native_tank.geometry.wall_heat_capacity_J_K
                            * finite(state.wall_temperature_K, "wall temperature", positive=True))
            expected_mass_residual.append(
                finite(state.hydrogen_mass_kg, "hydrogen inventory", positive=True) - mass0 + mass_out
            )
            expected_energy_residual.append(state_energy - initial_energy + energy_out - heat_in)
            expected_mass_out.append(mass_out)
            expected_energy_out.append(energy_out)
            expected_heat_in.append(heat_in)
        expected = (expected_mass_residual, expected_energy_residual,
                    expected_mass_out, expected_energy_out, expected_heat_in)
        scales = (1e-9, 1e-6, 1e-12, 1e-8, 1e-8)
        for name, reference, atol in zip(names[1:], expected, scales, strict=True):
            if not np.allclose(getattr(self, name), reference, rtol=1e-12, atol=atol):
                raise ValueError(f"Relief trace {name} does not close against accepted native intervals")
        if self.termination == "inventory_floor":
            event = self.inventory_event
            if (event is None or not np.isclose(event.time_s, self.time_s[-1], rtol=0., atol=1e-10)
                    or not np.isclose(event.mass_kg, state.hydrogen_mass_kg, rtol=1e-12, atol=1e-10)
                    or not np.isclose(event.minimum_inventory_kg, self.minimum_inventory_kg,
                                      rtol=0., atol=1e-12)):
                raise ValueError("Inventory-floor termination must retain the matching terminal event")
        elif self.inventory_event is not None:
            raise ValueError("A window-ended relief trace cannot carry an inventory-floor event")


_PENDING_RELIEF_TRACE_ISSUERS: set[object] = set()


def _issue_relief_tank_trace(*args):
    """Issue a trace only from the native driver's completed acceptance path."""
    token = object()
    _PENDING_RELIEF_TRACE_ISSUERS.add(token)
    return ReliefTankTrace(*args, _issuer_token=token)


class ReliefIntegrationError(RuntimeError):
    """Failure receipt retaining the accepted native prefix, not failed trials."""

    def __init__(self, message, *, native_tank, protection, accepted_state, accepted_time_s,
                 accepted_intervals=(), transitions=(), output_times=(), mass_residuals=(),
                 energy_residuals=(), released_mass_history=(), released_energy_history=(),
                 external_heat_history=(), trial_count=0, termination="window_end",
                 inventory_event=None, cause=None):
        super().__init__(message)
        self.native_tank, self.protection = native_tank, protection
        self.accepted_state, self.accepted_time_s = accepted_state, accepted_time_s
        self.accepted_intervals = tuple(accepted_intervals)
        self.transitions = tuple(transitions)
        self.output_times = tuple(output_times)
        self.mass_residuals = tuple(mass_residuals)
        self.energy_residuals = tuple(energy_residuals)
        self.released_mass_history = tuple(released_mass_history)
        self.released_energy_history = tuple(released_energy_history)
        self.external_heat_history = tuple(external_heat_history)
        self.trial_count = trial_count
        self.termination, self.inventory_event = termination, inventory_event
        self.cause = cause


class Lh2dtReliefTankDriver:
    """Partition actual native tank integration at bracketed physical pressure events.

    Every candidate/replay uses HomogeneousTank.simulate with a frozen accepted
    latch. Native RK4 owns fluid/wall states and its boundary ledger. Endpoint
    bracketing detects the first resolved crossing; arbitrary hidden within-step
    nonmonotonic excursions are outside this event-detection guarantee.
    """

    def __init__(self, tank, protection: Lh2dtReliefProtection, *, flow_factory: Callable,
                 state_factory: Callable, event_settings: ReliefEventSettings | None = None):
        if tank.properties is not protection.bridge.native:
            raise ValueError("Native relief valve and tank must share the same property instance")
        for name in ("simulate", "thermo", "geometry"):
            if not hasattr(tank, name):
                raise ReliefCapabilityError(f"Native tank lacks {name}")
        self.native, self.protection = tank, protection
        self.flow_factory, self.state_factory = flow_factory, state_factory
        self.settings = event_settings or ReliefEventSettings()

    def run(self, initial, *, duration_s: float, maximum_step_s: float,
            start_time_s: float, clock_id: str, boundary: ReliefTankBoundary,
            minimum_inventory_kg: float) -> ReliefTankTrace:
        duration = finite(duration_s, "relief duration", positive=True)
        maximum_step = finite(maximum_step_s, "native maximum step", positive=True)
        start = finite(start_time_s, "absolute operation start")
        floor = finite(minimum_inventory_kg, "minimum finite inventory", positive=True)
        settings, protection, tank = self.settings, self.protection, self.native
        if maximum_step < settings.minimum_native_interval_s or duration < settings.minimum_native_interval_s:
            raise ValueError("Requested native interval is below its reviewed clock floor")
        if (not isinstance(clock_id, str) or not clock_id.strip()
                or not isinstance(boundary.clock_id, str) or boundary.clock_id != clock_id):
            raise ValueError("Tank boundary and protection clocks differ")
        boundary.require_time(start)
        end = start+duration
        boundary.require_time(end)
        protection.bridge.basis.require_compatible(boundary.downstream.basis)
        if boundary.downstream.pressure_pa >= protection.reseat_pressure_pa:
            raise ReliefCapabilityError("This event level requires fixed downstream pressure below reseat")
        if initial.hydrogen_mass_kg <= floor:
            raise ValueError("Initial tank inventory must exceed its explicit positive floor")
        downstream = to_lh2dt_state(boundary.downstream, expected_basis=protection.bridge.basis,
                                    factory=self.state_factory)
        state, time = initial, start
        transitions, intervals = [], []
        trial_count = 0
        energy0 = (initial.hydrogen_internal_energy_J
                   +tank.geometry.wall_heat_capacity_J_K*initial.wall_temperature_K)
        mass0 = initial.hydrogen_mass_kg
        cumulative_mass = cumulative_out_energy = cumulative_heat = 0.
        output_times, mass_residuals, energy_residuals = [start], [0.], [0.]
        mass_history, out_history, heat_history = [0.], [0.], [0.]

        def native_interval(base, absolute_start, dt):
            nonlocal trial_count
            if dt < settings.minimum_native_interval_s:
                raise ReliefCapabilityError("Event interval is below the reviewed native clock floor")
            trial_count += 1
            mode = protection.is_open
            stage_flows, stages, ambient_values = [], [], []

            def flow(local_time, thermo):
                absolute = absolute_start+local_time
                boundary.require_time(absolute)
                source = protection.evaluate(thermo, downstream)
                stage_flows.append((absolute, thermo, source))
                if source.mass_flow_kg_s == 0.:
                    return ()
                return (self.flow_factory(mass_flow_kg_s=-source.mass_flow_kg_s,
                    specific_enthalpy_J_kg=thermo.specific_enthalpy_J_kg,
                    source=f"{protection.opening.opening_id}:homogeneous-bulk-relief"),)

            def ambient(local_time):
                absolute = absolute_start+local_time
                value = finite(boundary.ambient_temperature_k(absolute), "ambient temperature", positive=True)
                ambient_values.append((absolute, value))
                return value

            def direct_heat(local_time, thermo, wall_temperature):
                absolute = absolute_start+local_time
                direct = finite(boundary.direct_wall_heat_w(absolute, thermo, wall_temperature), "direct wall heat")
                if (not stage_flows or not ambient_values or stage_flows[-1][0] != absolute
                        or stage_flows[-1][1] is not thermo or ambient_values[-1][0] != absolute):
                    raise ReliefCapabilityError("Native RK stage callback identity/order changed")
                power = tank.geometry.ambient_UA_W_K*(ambient_values[-1][1]-wall_temperature)+direct
                stages.append(ReliefStage(absolute, thermo, wall_temperature, stage_flows[-1][2], power))
                return direct

            rows = tank.simulate(base, duration_s=dt, time_step_s=dt,
                ambient_temperature_K=ambient, flow_callback=flow, wall_heat_callback=direct_heat)
            if len(rows) != 1 or len(stages) != 4 or len(stage_flows) != 4 or len(ambient_values) != 4:
                raise ReliefCapabilityError("Reviewed one-step native RK4 callback/result capability changed")
            row = rows[0]
            if not math.isclose(row.time_s, dt, rel_tol=0., abs_tol=1e-12):
                raise ReliefCapabilityError("Native tank did not reach the requested local interval")
            if protection.is_open != mode:
                raise ReliefCapabilityError("A trial probe mutated accepted protection state")
            weights = np.array([1., 2., 2., 1.])*dt/6.
            released = float(weights@np.array([s.source.mass_flow_kg_s for s in stages]))
            out_energy = float(weights@np.array([s.source.nozzle.withdrawal_energy_w for s in stages]))
            external = float(weights@np.array([s.external_heat_w for s in stages]))
            if abs(row.cumulative_boundary_mass_kg+released) > max(1e-12, 1e-9*released):
                raise ReliefCapabilityError("Native tank mass ledger differs from actual relief stage flow")
            if abs(row.cumulative_boundary_energy_J-(external-out_energy)) > max(1e-6, 1e-9*(abs(external)+abs(out_energy))):
                raise ReliefCapabilityError("Native tank heat/enthalpy ledger differs from actual relief boundary")
            return ReliefNativeInterval(absolute_start, absolute_start+dt, row, tuple(stages), mode,
                released, out_energy, external, protection.evaluate(tank.thermo(base), downstream),
                protection.evaluate(row.thermo, downstream))

        def crossed(interval, kind):
            if kind == "inventory_floor":
                return interval.native_step.state.hydrogen_mass_kg <= floor
            pressure = interval.native_step.thermo.pressure_Pa
            return (pressure <= protection.reseat_pressure_pa if protection.is_open
                    else pressure >= protection.set_pressure_pa)

        def localize(base, absolute_start, upper, kind):
            low, high = 0., upper.end_time_s-absolute_start
            high_interval = upper
            threshold = (floor if kind == "inventory_floor" else
                         protection.reseat_pressure_pa if protection.is_open else protection.set_pressure_pa)
            tolerance = settings.mass_tolerance_kg if kind == "inventory_floor" else settings.pressure_tolerance_pa
            for _ in range(settings.maximum_iterations):
                value = (high_interval.native_step.state.hydrogen_mass_kg if kind == "inventory_floor"
                         else high_interval.native_step.thermo.pressure_Pa)
                if high-low <= settings.time_tolerance_s and abs(value-threshold) <= tolerance:
                    return high_interval, absolute_start+low, absolute_start+high
                middle = .5*(low+high)
                if middle < settings.minimum_native_interval_s:
                    raise ReliefCapabilityError("Threshold is too close to an accepted state for the native clock floor")
                trial = native_interval(base, absolute_start, middle)
                if crossed(trial, kind):
                    high, high_interval = middle, trial
                else:
                    low = middle
            raise ReliefCapabilityError("Relief event did not meet its fixed time/state bracket budgets")

        def initial_commit():
            thermo = tank.thermo(state)
            before_source = protection.evaluate(thermo, downstream)
            before, after, after_source = protection.commit(time, thermo, downstream, clock_id=clock_id)
            if (after.is_open and thermo.pressure_Pa <= protection.reseat_pressure_pa
                    and thermo.pressure_Pa < downstream.pressure_Pa):
                raise ReliefCapabilityError("Native reverse-pressure initial latch cannot be reconciled publicly")
            if before.is_open != after.is_open:
                threshold = protection.set_pressure_pa if after.is_open else protection.reseat_pressure_pa
                transitions.append(ReliefTransition(time, "initial_open" if after.is_open else "initial_reseat",
                    thermo.pressure_Pa, threshold, time, time, before, after, before_source, after_source, state))
            return after_source

        termination = "window_end"
        inventory_event = None
        try:
            initial_source = initial_commit()
            while time < end:
                remaining = end-time
                dt = min(maximum_step, remaining)
                if 0. < remaining-dt < settings.minimum_native_interval_s:
                    # Two valid final intervals avoid leaving a sub-floor clock
                    # remainder without enlarging the declared maximum step.
                    dt = .5*remaining
                if dt < settings.minimum_native_interval_s:
                    if end-time <= settings.time_tolerance_s:
                        raise ReliefCapabilityError("Final requested interval is below the reviewed native clock floor")
                candidate = native_interval(state, time, dt)
                events = []
                for kind in ("pressure", "inventory_floor"):
                    if crossed(candidate, kind):
                        localized, lower, upper = localize(state, time, candidate, kind)
                        events.append((localized.end_time_s, kind, localized, lower, upper))
                event = min(events, key=lambda item: item[0]) if events else None
                accepted = candidate if event is None else event[2]
                state, time = accepted.native_step.state, accepted.end_time_s
                intervals.append(accepted)
                cumulative_mass += accepted.released_mass_kg
                cumulative_out_energy += accepted.released_enthalpy_j
                cumulative_heat += accepted.external_heat_j
                energy = state.hydrogen_internal_energy_J+tank.geometry.wall_heat_capacity_J_K*state.wall_temperature_K
                output_times.append(time)
                mass_residuals.append(state.hydrogen_mass_kg-mass0+cumulative_mass)
                energy_residuals.append(energy-energy0+cumulative_out_energy-cumulative_heat)
                mass_history.append(cumulative_mass)
                out_history.append(cumulative_out_energy)
                heat_history.append(cumulative_heat)
                if event is not None:
                    if event[1] == "inventory_floor":
                        termination = "inventory_floor"
                        inventory_event = ReliefInventoryTermination(time, state.hydrogen_mass_kg,
                            floor, event[3], event[4], state, accepted.source_at_end)
                        break
                    before_source = accepted.source_at_end
                    before, after, after_source = protection.commit(time, accepted.native_step.thermo,
                                                                  downstream, clock_id=clock_id)
                    if before.is_open == after.is_open:
                        raise ReliefCapabilityError("Localized native pressure event did not change its latch")
                    threshold = protection.set_pressure_pa if after.is_open else protection.reseat_pressure_pa
                    transitions.append(ReliefTransition(time, "open" if after.is_open else "reseat",
                        accepted.native_step.thermo.pressure_Pa, threshold, event[3], event[4], before,
                        after, before_source, after_source, state))
                    if len(transitions) > settings.maximum_events:
                        raise ReliefCapabilityError("Declared relief transition count was exceeded")
        except Exception as exc:
            raise ReliefIntegrationError(f"Native relief integration failed: {exc}", native_tank=tank,
                protection=protection, accepted_state=state, accepted_time_s=time,
                accepted_intervals=intervals, transitions=transitions, output_times=output_times,
                mass_residuals=mass_residuals, energy_residuals=energy_residuals,
                released_mass_history=mass_history, released_energy_history=out_history,
                external_heat_history=heat_history, trial_count=trial_count,
                termination=termination, inventory_event=inventory_event, cause=exc) from exc
        return _issue_relief_tank_trace(clock_id, initial, initial_source, tuple(intervals), tuple(transitions),
            output_times, mass_residuals, energy_residuals, mass_history, out_history, heat_history,
            tank, protection.native_origin, protection.native, termination, floor, trial_count, settings,
            inventory_event)
