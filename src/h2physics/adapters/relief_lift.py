"""Finite relief lift and phase-selective pickup over existing physical owners.

The existing native relief owns set/reseat pressure identity.  The shared nozzle
owns every flow solution.  A caller-owned pickup selects a real tank phase and
retains the native tank state.  This module only advances an accepted, bounded
lift state at caller-supplied clock samples; it does not localize hidden pressure
crossings, integrate a tank, size a device or infer valve coefficients.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..core import PropertyBasis, ThermoState, finite
from ..release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult
from .lh2dt_relief import Lh2dtReliefProtection, ReliefCapabilityError


@dataclass(frozen=True, slots=True)
class PhasePickup:
    """One owner-selected phase at an accepted native tank state."""

    vessel_pressure_pa: float
    upstream: ThermoState
    available_mass_kg: float
    phase_id: str
    selection_id: str
    state_id: str
    native_tank_state: Any

    def __post_init__(self):
        finite(self.vessel_pressure_pa, "vessel pressure", positive=True)
        finite(self.available_mass_kg, "pickup available mass")
        if self.available_mass_kg < 0:
            raise ValueError("Pickup available mass cannot be negative")
        if not all(value.strip() for value in (self.phase_id, self.selection_id, self.state_id)):
            raise ValueError("Phase, selection and native-state identities are required")
        if self.native_tank_state is None:
            raise ValueError("Retain the actual native tank state selected by the pickup owner")
        tolerance = max(1e-6, 1e-10 * self.vessel_pressure_pa)
        if abs(self.upstream.pressure_pa - self.vessel_pressure_pa) > tolerance:
            raise ValueError("Selected phase and vessel pressure must share the accepted pressure")


@dataclass(frozen=True, slots=True)
class PhasePickupOwner:
    """Explicit selection callback and its admitted phase/domain identity."""

    owner_id: str
    property_basis: PropertyBasis
    admitted_phase_ids: tuple[str, ...]
    select: Callable[[Any], PhasePickup]

    def __post_init__(self):
        phases = tuple(self.admitted_phase_ids)
        if (not self.owner_id.strip() or not phases or any(not item.strip() for item in phases)
                or len(set(phases)) != len(phases) or not callable(self.select)):
            raise ValueError("Pickup owner needs a callable and unique admitted phase identities")
        object.__setattr__(self, "admitted_phase_ids", phases)

    def at(self, native_tank_state: Any) -> PhasePickup:
        value = self.select(native_tank_state)
        if not isinstance(value, PhasePickup):
            raise TypeError("The phase owner must return PhasePickup")
        if value.native_tank_state is not native_tank_state:
            raise ValueError("Pickup must retain the exact accepted native tank state")
        if value.phase_id not in self.admitted_phase_ids:
            raise ValueError("Pickup phase is outside the declared owner domain")
        self.property_basis.require_compatible(value.upstream.basis)
        return value


@dataclass(frozen=True, slots=True)
class ReliefLiftLaw:
    """Caller-supplied first-order travel limits, not a vendor valve map."""

    opening_rate_fraction_s: float
    closing_rate_fraction_s: float
    closed_leakage_fraction: float
    maximum_clock_step_s: float
    law_id: str
    coefficient_evidence_id: str

    def __post_init__(self):
        finite(self.opening_rate_fraction_s, "opening rate", positive=True)
        finite(self.closing_rate_fraction_s, "closing rate", positive=True)
        finite(self.maximum_clock_step_s, "maximum clock step", positive=True)
        leakage = finite(self.closed_leakage_fraction, "closed leakage fraction")
        if not 0 <= leakage < 1:
            raise ValueError("Closed leakage fraction must lie in [0, 1)")
        if not self.law_id.strip() or not self.coefficient_evidence_id.strip():
            raise ValueError("Lift law and coefficient evidence identities are required")


@dataclass(frozen=True, slots=True)
class ReliefLiftState:
    time_s: float
    lift_fraction: float
    demanded_open: bool
    clock_id: str

    def __post_init__(self):
        finite(self.time_s, "lift state time")
        lift = finite(self.lift_fraction, "lift fraction")
        if not 0 <= lift <= 1 or not isinstance(self.demanded_open, bool):
            raise ValueError("Lift must be in [0, 1] and demand must be bool")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Lift state requires an explicit clock identity")


@dataclass(frozen=True, slots=True)
class ReliefLiftResult:
    state: ReliefLiftState
    pickup: PhasePickup
    downstream: ThermoState
    effective_opening_fraction: float
    nozzle: NozzleResult
    interval_start_s: float
    interval_end_s: float
    endpoint_rate_mass_if_held_kg: float
    endpoint_rate_enthalpy_if_held_j: float
    source_owner_id: str
    native_relief_origin: Any
    native_relief_current: Any
    evidence_id: str

    @property
    def mass_flow_kg_s(self):
        return self.nozzle.mass_flow_kg_s

    @property
    def enthalpy_flow_w(self):
        return self.nozzle.withdrawal_energy_w


def _law_binding(law: ReliefLiftLaw):
    return (law.opening_rate_fraction_s, law.closing_rate_fraction_s,
            law.closed_leakage_fraction, law.maximum_clock_step_s,
            law.law_id, law.coefficient_evidence_id)


def _result_binding(value: ReliefLiftResult):
    p = value.pickup
    return (value.state, id(p.native_tank_state), p.vessel_pressure_pa,
            p.upstream, p.available_mass_kg, p.phase_id, p.selection_id, p.state_id,
            value.downstream, value.effective_opening_fraction, id(value.nozzle),
            value.interval_start_s, value.interval_end_s,
            value.endpoint_rate_mass_if_held_kg, value.endpoint_rate_enthalpy_if_held_j,
            value.source_owner_id, id(value.native_relief_origin),
            id(value.native_relief_current), value.evidence_id)


class FiniteLiftRelief:
    """Accepted-sample finite lift with explicit phase pickup and seat leakage.

    Pressure hysteresis is evaluated only at the supplied accepted state.  Linear
    travel between samples is exact for the declared constant rate limit, while
    the returned nozzle is an endpoint rate.  The `*_if_held` quantities are not
    an integrated tank withdrawal and must not be used as one without a separate
    accepted quadrature/inventory owner.
    """

    def __init__(self, protection: Lh2dtReliefProtection, *,
                 nozzle: HomogeneousIsentropicNozzle, opening: NozzleOpening,
                 pickup: PhasePickupOwner, law: ReliefLiftLaw, evidence_id: str):
        if type(protection) is not Lh2dtReliefProtection:
            raise TypeError("Retain the exact existing native relief protection owner")
        if type(nozzle) is not HomogeneousIsentropicNozzle or opening is not protection.opening:
            raise TypeError("Retain the shared nozzle and exact native relief opening")
        if not evidence_id.strip():
            raise ValueError("Finite-lift composition requires an evidence identity")
        nozzle.properties.basis.require_compatible(protection.bridge.basis)
        nozzle.properties.basis.require_compatible(pickup.property_basis)
        protection.is_open  # checks that native thresholds/latch were not modified
        self.protection = protection
        self.nozzle = nozzle
        self.opening = opening
        self.pickup = pickup
        self.law = law
        self.evidence_id = evidence_id
        self._law_binding = _law_binding(law)
        self._issued: dict[int, tuple[ReliefLiftResult, tuple]] = {}

    def _require_owner_current(self):
        if (_law_binding(self.law) != self._law_binding
                or self.opening is not self.protection.opening):
            raise ReliefCapabilityError("Finite lift law or native opening owner changed")
        self.nozzle.properties.basis.require_compatible(self.protection.bridge.basis)
        self.pickup.property_basis.require_compatible(self.nozzle.properties.basis)
        self.protection.is_open

    def require_current(self, result: ReliefLiftResult):
        entry = self._issued.get(id(result))
        if entry is None or entry[0] is not result or entry[1] != _result_binding(result):
            raise ValueError("Require the original unchanged owner-issued relief-lift result")
        self._require_owner_current()

    def initialize(self, *, time_s: float, clock_id: str, native_tank_state: Any,
                   downstream: ThermoState, initial_lift_fraction: float = 0.,
                   initial_demand_open: bool = False) -> ReliefLiftResult:
        self._require_owner_current()
        if not isinstance(initial_demand_open, bool):
            raise ValueError("Initial demand must be explicitly boolean")
        state = ReliefLiftState(time_s, initial_lift_fraction, initial_demand_open, clock_id)
        selected = self.pickup.at(native_tank_state)
        demanded = self._demand(selected.vessel_pressure_pa, state.demanded_open)
        state = ReliefLiftState(state.time_s, state.lift_fraction, demanded, state.clock_id)
        return self._issue(state, selected, downstream, state.time_s, state.time_s)

    def advance(self, previous: ReliefLiftResult, *, time_s: float,
                native_tank_state: Any, downstream: ThermoState) -> ReliefLiftResult:
        self.require_current(previous)
        time = finite(time_s, "accepted lift time")
        dt = time - previous.state.time_s
        if dt <= 0 or dt > self.law.maximum_clock_step_s:
            raise ValueError("Lift clock step must be positive and within its declared support")
        selected = self.pickup.at(native_tank_state)
        demanded = self._demand(selected.vessel_pressure_pa, previous.state.demanded_open)
        rate = (self.law.opening_rate_fraction_s if demanded
                else self.law.closing_rate_fraction_s)
        direction = 1. if demanded else -1.
        lift = min(1., max(0., previous.state.lift_fraction + direction * rate * dt))
        state = ReliefLiftState(time, lift, demanded, previous.state.clock_id)
        result = self._issue(state, selected, downstream, previous.state.time_s, time)
        if result.endpoint_rate_mass_if_held_kg > selected.available_mass_kg + 1e-12:
            self._issued.pop(id(result), None)
            raise ValueError("Endpoint relief rate would exceed declared selectable phase inventory")
        return result

    def _demand(self, pressure_pa: float, previous: bool):
        if pressure_pa >= self.protection.set_pressure_pa:
            return True
        if pressure_pa <= self.protection.reseat_pressure_pa:
            return False
        return previous

    def _issue(self, state, selected, downstream, start, end):
        selected.upstream.basis.require_compatible(downstream.basis)
        fraction = self.law.closed_leakage_fraction + (
            1. - self.law.closed_leakage_fraction) * state.lift_fraction
        result = self.nozzle.solve(selected.upstream,
            back_pressure_pa=downstream.pressure_pa, opening=self.opening,
            opening_fraction=fraction)
        dt = end - start
        value = ReliefLiftResult(state, selected, downstream, fraction, result,
            start, end, result.mass_flow_kg_s * dt, result.withdrawal_energy_w * dt,
            self.pickup.owner_id, self.protection.native_origin, self.protection.native,
            self.evidence_id)
        binding = _result_binding(value)
        self._issued[id(value)] = (value, binding)
        return value
