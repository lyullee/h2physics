"""Event-partitioned native LH2DT runs with independent inventory accounting.

The injected native simulator owns every integration step and physical RHS.
Accepted solutions are matched by object identity, without counting RK stages.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from math import fsum, isclose
from types import MappingProxyType
from typing import Any

from ..core import PropertyBasis, finite
from ..dynamics import (
    ConservedInventory,
    InventoryBalance,
    InventoryTolerances,
    SampledEquipmentIntegral,
    ScheduledEquipmentCommand,
)
from .lh2dt_equipment import EquipmentNetworkSnapshot, Lh2dtEquipmentNetwork


def _receipt_fingerprint(payload: object) -> str:
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


_PENDING_DYNAMIC_RUN_ISSUERS: set[object] = set()


def _issue_dynamic_run(**values):
    """Create an accepted run only from the native driver (or deferred fixtures)."""
    token = object()
    _PENDING_DYNAMIC_RUN_ISSUERS.add(token)
    try:
        return DynamicEquipmentRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_DYNAMIC_RUN_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class Lh2dtInventoryNode:
    native_node: Any
    inventory_reader: Callable[[Any], ConservedInventory]


def lumped_inventory_reader(wall_heat_capacity_j_k: float, basis: PropertyBasis):
    """Read the native pipe/vaporizer state with an explicit constant wall C."""
    capacity = finite(wall_heat_capacity_j_k, "wall_heat_capacity_j_k", positive=True)

    def read(state):
        temperature = finite(state.wall_temperature_K, "wall_temperature_K", positive=True)
        return ConservedInventory(basis, state.mass_kg, state.internal_energy_J,
                                  capacity*temperature)

    return read


def stratified_inventory_reader(lower_wall_heat_capacity_j_k: float,
                                upper_wall_heat_capacity_j_k: float, basis: PropertyBasis):
    """Read both native fluid regions and both constant-capacity tank walls."""
    lower = finite(lower_wall_heat_capacity_j_k, "lower_wall_heat_capacity_j_k", positive=True)
    upper = finite(upper_wall_heat_capacity_j_k, "upper_wall_heat_capacity_j_k", positive=True)

    def read(state):
        liquid = finite(state.liquid_mass_kg, "liquid_mass_kg", positive=True)
        vapor = finite(state.vapor_mass_kg, "vapor_mass_kg", positive=True)
        lower_t = finite(state.lower_wall_temperature_K, "lower_wall_temperature_K", positive=True)
        upper_t = finite(state.upper_wall_temperature_K, "upper_wall_temperature_K", positive=True)
        return ConservedInventory(basis, liquid+vapor,
            state.liquid_internal_energy_J+state.vapor_internal_energy_J, lower*lower_t+upper*upper_t)

    return read


@dataclass(frozen=True, slots=True)
class DynamicEquipmentStep:
    time_s: float
    inventories: Mapping[str, ConservedInventory]
    balances: Mapping[str, InventoryBalance]
    equipment: EquipmentNetworkSnapshot
    native: Any

    def __post_init__(self):
        object.__setattr__(self, "inventories", MappingProxyType(dict(self.inventories)))
        object.__setattr__(self, "balances", MappingProxyType(dict(self.balances)))


@dataclass(frozen=True, slots=True)
class EquipmentCommandTransition:
    time_s: float
    identifiers: tuple[str, ...]
    before: EquipmentNetworkSnapshot
    after: EquipmentNetworkSnapshot


@dataclass(frozen=True, slots=True)
class DynamicEquipmentRun:
    clock_id: str
    start_time_s: float
    initial_inventories: Mapping[str, ConservedInventory]
    initial_equipment: EquipmentNetworkSnapshot
    steps: tuple[DynamicEquipmentStep, ...]
    transitions: tuple[EquipmentCommandTransition, ...]
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DYNAMIC_RUN_ISSUERS:
            raise ValueError("Accepted dynamic runs are issued by the native driver")
        _PENDING_DYNAMIC_RUN_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "initial_inventories", MappingProxyType(dict(self.initial_inventories)))
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "transitions", tuple(self.transitions))
        if (not isinstance(self.clock_id, str) or not self.clock_id.strip()
                or not self.steps or any(type(step) is not DynamicEquipmentStep for step in self.steps)
                or any(right.time_s <= left.time_s for left, right in zip(self.steps, self.steps[1:]))
                or self.steps[0].time_s <= self.start_time_s):
            raise ValueError("Accepted dynamic run must retain a nonempty increasing native step sequence")
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self):
        return _receipt_fingerprint((self.clock_id, self.start_time_s, self.initial_inventories,
                                     self.initial_equipment, self.steps, self.transitions))

    def require_current(self):
        if self._content_fingerprint() != self._seal:
            raise ValueError("Accepted native dynamic run contents changed after issuance")
        return self


@dataclass(frozen=True, slots=True)
class UnidirectionalEquipmentIntegral:
    """Accepted-sample rate integral with its signed samples retained."""

    integral: SampledEquipmentIntegral
    trajectory_id: str
    sample_times_s: tuple[float, ...]
    sample_rates: tuple[float, ...]
    _source_run: DynamicEquipmentRun | None = dataclass_field(
        default=None, repr=False, compare=False,
    )
    _source_snapshots: tuple[EquipmentNetworkSnapshot, ...] = dataclass_field(
        default=(), repr=False, compare=False,
    )
    _rate_reader: Callable[[EquipmentNetworkSnapshot], float] | None = dataclass_field(
        default=None, repr=False, compare=False,
    )
    _fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.integral) is not SampledEquipmentIntegral:
            raise TypeError("Retain a shared sampled equipment integral")
        if not isinstance(self.trajectory_id, str) or not self.trajectory_id.strip():
            raise ValueError("Identify the physical trajectory shared across grid refinements")
        times, rates = tuple(self.sample_times_s), tuple(self.sample_rates)
        if len(times) != len(rates) or len(times) < 2:
            raise ValueError("Retain each sampled rate beside its time")
        times = tuple(finite(value, "sample time") for value in times)
        rates = tuple(finite(value, "sample rate") for value in rates)
        snapshots = tuple(self._source_snapshots)
        if self._source_run is None:
            if snapshots or self._rate_reader is not None:
                raise ValueError("Source snapshots and rate reader require their originating run")
        elif len(snapshots) != len(times) or self._rate_reader is None:
            raise ValueError("A run-bound integral must retain each sampled snapshot and its reader")
        if (times[0] != self.integral.start_time_s or times[-1] != self.integral.end_time_s
                or any(right < left for left, right in zip(times, times[1:]))):
            raise ValueError("Sampled rates must span the integral window in time order")
        if any(value < 0.0 for value in rates) or not any(value > 0.0 for value in rates):
            raise ValueError("The coolant rate samples must be forward or zero, with positive flow")
        areas = [((right_t-left_t)*(left_rate+right_rate)/2.0)
                 for (left_t, left_rate), (right_t, right_rate)
                 in zip(zip(times, rates), zip(times[1:], rates[1:]))
                 if right_t > left_t]
        if (len(areas) != self.integral.interval_count
                or not isclose(fsum(areas), self.integral.value,
                               rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Retained signed rate samples do not reproduce their integral")
        object.__setattr__(self, "sample_times_s", times)
        object.__setattr__(self, "sample_rates", rates)
        object.__setattr__(self, "_source_snapshots", snapshots)
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self) -> str:
        return _receipt_fingerprint((
            self.integral, self.trajectory_id, self.sample_times_s, self.sample_rates,
            id(self._source_run), tuple(id(item) for item in self._source_snapshots),
            id(self._rate_reader),
        ))

    def require_current(self) -> UnidirectionalEquipmentIntegral:
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Accepted rate samples or integral metadata changed after capture")
        if self._source_run is not None:
            run = self._source_run
            _basis, _end, times, rates, _areas, snapshots = _sample_equipment_rate(
                run, self._rate_reader, include_snapshots=True,
            )
            if (times != self.sample_times_s or rates != self.sample_rates
                    or len(snapshots) != len(self._source_snapshots)
                    or any(current is not retained for current, retained
                           in zip(snapshots, self._source_snapshots))):
                raise ValueError("The originating run no longer matches its retained coolant samples")
        UnidirectionalEquipmentIntegral(
            self.integral, self.trajectory_id, self.sample_times_s, self.sample_rates,
            self._source_run, self._source_snapshots, self._rate_reader,
        )
        return self

    @property
    def value(self) -> float:
        self.require_current()
        return self.integral.value


@dataclass(frozen=True, slots=True)
class EquipmentIntegralRefinement:
    """Observed coarse/fine accepted-sample integral change, not an error bound."""

    coarse: UnidirectionalEquipmentIntegral
    fine: UnidirectionalEquipmentIntegral
    signed_change: float
    absolute_change: float
    normalized_change: float
    interval_refinement_ratio: float
    normalized_tolerance: float
    within_tolerance: bool
    _fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self.coarse.require_current()
        self.fine.require_current()
        coarse, fine = self.coarse.integral, self.fine.integral
        if self.coarse.trajectory_id != self.fine.trajectory_id:
            raise ValueError("Coarse/fine integrals must refer to the same physical trajectory")
        coarse.basis.require_compatible(fine.basis)
        if (coarse.clock_id != fine.clock_id or coarse.rate_unit != fine.rate_unit
                or coarse.integral_unit != fine.integral_unit
                or not isclose(coarse.start_time_s, fine.start_time_s,
                               rel_tol=0.0, abs_tol=1e-12)
                or not isclose(coarse.end_time_s, fine.end_time_s,
                               rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Coarse/fine integrals need a common basis, clock, units and window")
        if fine.interval_count <= coarse.interval_count:
            raise ValueError("The fine integral must contain more accepted intervals")
        fine_cursor = 0
        for coarse_time in self.coarse.sample_times_s:
            while (fine_cursor < len(self.fine.sample_times_s)
                   and not isclose(coarse_time, self.fine.sample_times_s[fine_cursor],
                                   rel_tol=1e-12, abs_tol=1e-12)):
                fine_cursor += 1
            if fine_cursor >= len(self.fine.sample_times_s):
                raise ValueError("The fine clock must contain every coarse accepted time")
            fine_cursor += 1
        difference = fine.value-coarse.value
        scale = max(abs(fine.value), abs(coarse.value))
        normalized = 0.0 if scale == 0.0 else abs(difference)/scale
        ratio = fine.interval_count/coarse.interval_count
        tolerance = finite(self.normalized_tolerance, "normalized_tolerance")
        if tolerance < 0.0:
            raise ValueError("normalized_tolerance cannot be negative")
        for name, expected in (
            ("signed_change", difference),
            ("absolute_change", abs(difference)),
            ("normalized_change", normalized),
            ("interval_refinement_ratio", ratio),
        ):
            actual = finite(getattr(self, name), name)
            if not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError("Refinement metrics do not reproduce the retained integrals")
        if type(self.within_tolerance) is not bool or self.within_tolerance != (normalized <= tolerance):
            raise ValueError("Refinement tolerance decision differs from the declared threshold")
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self) -> str:
        return _receipt_fingerprint((
            self.coarse._fingerprint, self.fine._fingerprint, self.signed_change,
            self.absolute_change, self.normalized_change, self.interval_refinement_ratio,
            self.normalized_tolerance, self.within_tolerance,
        ))

    def require_current(self) -> EquipmentIntegralRefinement:
        self.coarse.require_current()
        self.fine.require_current()
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Coarse/fine refinement receipt changed after comparison")
        return self


def compare_unidirectional_equipment_integrals(
    coarse: UnidirectionalEquipmentIntegral,
    fine: UnidirectionalEquipmentIntegral,
    *,
    normalized_tolerance: float,
) -> EquipmentIntegralRefinement:
    """Compare observed accepted-sample change under interval refinement."""
    if (type(coarse) is not UnidirectionalEquipmentIntegral
            or type(fine) is not UnidirectionalEquipmentIntegral):
        raise TypeError("Pass direction-checked coarse and fine rate integrals")
    coarse_value, fine_value = coarse.integral.value, fine.integral.value
    difference = fine_value-coarse_value
    scale = max(abs(fine_value), abs(coarse_value))
    return EquipmentIntegralRefinement(
        coarse, fine, difference, abs(difference),
        0.0 if scale == 0.0 else abs(difference)/scale,
        fine.integral.interval_count/coarse.integral.interval_count,
        finite(normalized_tolerance, "normalized_tolerance"),
        (0.0 if scale == 0.0 else abs(difference)/scale) <= normalized_tolerance,
    )


@dataclass(frozen=True, slots=True)
class DynamicLineCooldownAudit:
    """Native line energy removal reconciled with coolant mass and enthalpy rise."""

    node_id: str
    clock_id: str
    start_time_s: float
    end_time_s: float
    initial: ConservedInventory
    final: ConservedInventory
    coolant_mass: UnidirectionalEquipmentIntegral
    coolant_enthalpy_rise_j_kg: float
    coolant_only_energy_transport: bool
    transported_enthalpy_j: float
    ambient_heat_j: float
    boundary_mass_kg: float
    boundary_energy_j: float
    required_coolant_mass_kg: float
    coolant_mass_residual_kg: float
    coolant_energy_residual_j: float
    stored_energy_drop_j: float
    inventory_mass_residual_kg: float
    inventory_energy_residual_j: float
    evidence_ids: tuple[str, ...]
    coolant_mass_refinement: EquipmentIntegralRefinement | None = None
    _source_run: DynamicEquipmentRun | None = dataclass_field(
        default=None, repr=False, compare=False,
    )
    _fingerprint: str = dataclass_field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.node_id, str) or not self.node_id.strip():
            raise ValueError("A dynamic line cooldown audit needs a node identity")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("A dynamic line cooldown audit needs an operation clock")
        finite(self.start_time_s, "start_time_s")
        finite(self.end_time_s, "end_time_s")
        if self.end_time_s <= self.start_time_s:
            raise ValueError("A dynamic line cooldown audit needs a positive time window")
        self.initial.basis.require_compatible(self.final.basis)
        integral = self.coolant_mass.integral
        self.coolant_mass.require_current()
        if self._source_run is None or self.coolant_mass._source_run is not self._source_run:
            raise ValueError("Cooldown audit has lost its originating accepted run")
        self.initial.basis.require_compatible(integral.basis)
        if integral.rate_unit != "kg/s" or integral.integral_unit != "kg":
            raise ValueError("Coolant mass integral units must be kg/s and kg")
        if (integral.clock_id != self.clock_id or integral.value <= 0.0
                or not isclose(integral.start_time_s, self.start_time_s,
                               rel_tol=0.0, abs_tol=1e-12)
                or not isclose(integral.end_time_s, self.end_time_s,
                               rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Coolant mass must retain the audit clock and full time window")
        for name in (
            "coolant_enthalpy_rise_j_kg", "transported_enthalpy_j", "ambient_heat_j",
            "boundary_mass_kg", "boundary_energy_j", "required_coolant_mass_kg",
            "coolant_mass_residual_kg",
            "coolant_energy_residual_j", "stored_energy_drop_j",
            "inventory_mass_residual_kg", "inventory_energy_residual_j",
        ):
            finite(getattr(self, name), name)
        if self.coolant_enthalpy_rise_j_kg <= 0.0 or self.required_coolant_mass_kg <= 0.0:
            raise ValueError("Cooldown audit must retain positive enthalpy rise and mass")
        if self.coolant_only_energy_transport is not True:
            raise ValueError("Cooldown audit requires coolant-only boundary energy transport")
        if (self.coolant_mass_refinement is not None
                and (type(self.coolant_mass_refinement) is not EquipmentIntegralRefinement
                     or self.coolant_mass_refinement.fine != self.coolant_mass)):
            raise ValueError("Coolant mass refinement must terminate at the audited integral")
        if self.coolant_mass_refinement is not None:
            self.coolant_mass_refinement.require_current()
        expected_required = -self.transported_enthalpy_j/self.coolant_enthalpy_rise_j_kg
        expected_coolant_mass_residual = integral.value-expected_required
        expected_energy_residual = (self.transported_enthalpy_j
                                    + integral.value*self.coolant_enthalpy_rise_j_kg)
        expected_boundary_energy = self.transported_enthalpy_j+self.ambient_heat_j
        expected_inventory_mass_residual = (
            self.final.mass_kg-self.initial.mass_kg-self.boundary_mass_kg
        )
        expected_drop = self.initial.total_energy_j-self.final.total_energy_j
        expected_inventory_residual = (
            self.final.total_energy_j-self.initial.total_energy_j
            - self.boundary_energy_j
        )
        identities = (
            (self.boundary_energy_j, expected_boundary_energy),
            (self.required_coolant_mass_kg, expected_required),
            (self.coolant_mass_residual_kg, expected_coolant_mass_residual),
            (self.coolant_energy_residual_j, expected_energy_residual),
            (self.stored_energy_drop_j, expected_drop),
            (self.inventory_mass_residual_kg, expected_inventory_mass_residual),
            (self.inventory_energy_residual_j, expected_inventory_residual),
        )
        if any(not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-9)
               for actual, expected in identities):
            raise ValueError("Dynamic line cooldown audit fields do not reproduce their ledgers")
        if isinstance(self.evidence_ids, str):
            raise TypeError("evidence_ids must be a sequence of evidence identities")
        evidence = tuple(self.evidence_ids)
        if not evidence or any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise ValueError("Dynamic line cooldown audit needs evidence identities")
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self) -> str:
        return _receipt_fingerprint((
            self.node_id, self.clock_id, self.start_time_s, self.end_time_s,
            self.initial, self.final, self.coolant_mass._fingerprint,
            self.coolant_enthalpy_rise_j_kg, self.coolant_only_energy_transport,
            self.transported_enthalpy_j, self.ambient_heat_j, self.boundary_mass_kg,
            self.boundary_energy_j, self.required_coolant_mass_kg,
            self.coolant_mass_residual_kg, self.coolant_energy_residual_j,
            self.stored_energy_drop_j, self.inventory_mass_residual_kg,
            self.inventory_energy_residual_j, self.evidence_ids,
            None if self.coolant_mass_refinement is None
            else self.coolant_mass_refinement._fingerprint,
            id(self._source_run),
        ))

    def require_current(self) -> DynamicLineCooldownAudit:
        self.coolant_mass.require_current()
        if self.coolant_mass_refinement is not None:
            self.coolant_mass_refinement.require_current()
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Dynamic line cooldown audit changed after construction")
        return self


def audit_dynamic_line_cooldown(
    run: DynamicEquipmentRun,
    node_id: str,
    coolant_mass: UnidirectionalEquipmentIntegral,
    *,
    coolant_enthalpy_rise_j_kg: float,
    coolant_only_energy_transport: bool,
    evidence_ids: Sequence[str],
    coolant_mass_refinement: EquipmentIntegralRefinement | None = None,
    tolerances: InventoryTolerances | None = None,
) -> DynamicLineCooldownAudit:
    """Reconcile an admitted native line run with sampled coolant throughput.

    The LH2DT trajectory and exact per-node enthalpy/ambient ledgers remain the
    physical result. Only gross coolant mass is integrated from accepted output
    samples, so its quadrature/refinement is retained independently in the receipt.
    A direction-aware integral verifies every retained signed sample is forward or
    zero. The caller must attest that no other stream contributes to this line
    node's transport energy; that premise is not inferred from the energy ledger.
    """
    if type(run) is not DynamicEquipmentRun:
        raise TypeError("Pass an accepted DynamicEquipmentRun")
    run.require_current()
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("Identify the dynamic line node")
    if (not run.clock_id.strip() or not run.steps
            or node_id not in run.initial_inventories):
        raise ValueError("The run must retain the selected line inventory and accepted steps")
    accepted_times = tuple(step.time_s for step in run.steps)
    if (accepted_times[0] <= run.start_time_s
            or any(right <= left for left, right in zip(accepted_times, accepted_times[1:]))):
        raise ValueError("Accepted line samples must increase after the run start")
    if any(node_id not in step.inventories or node_id not in step.balances
           for step in run.steps):
        raise ValueError("An accepted step omitted the selected line inventory ledger")
    if type(coolant_mass) is not UnidirectionalEquipmentIntegral:
        raise TypeError("Pass a direction-checked accepted-sample coolant mass integral")
    if coolant_mass._source_run is not run:
        raise ValueError("Integrate coolant mass from the same accepted run being audited")
    coolant_integral = coolant_mass.integral
    final_step = run.steps[-1]
    if node_id not in final_step.inventories or node_id not in final_step.balances:
        raise ValueError("The final accepted step omitted the selected line inventory ledger")
    expected_window = (run.start_time_s, final_step.time_s)
    if (coolant_integral.clock_id != run.clock_id
            or not isclose(coolant_integral.start_time_s, expected_window[0],
                           rel_tol=0.0, abs_tol=1e-12)
            or not isclose(coolant_integral.end_time_s, expected_window[1],
                           rel_tol=1e-12, abs_tol=1e-12)
            or coolant_integral.rate_unit != "kg/s"
            or coolant_integral.integral_unit != "kg"):
        raise ValueError("Coolant mass integral must match the native line clock and run window")
    if coolant_integral.value <= 0.0:
        raise ValueError("The accepted-sample coolant mass must be positive")
    if type(coolant_only_energy_transport) is not bool or not coolant_only_energy_transport:
        raise ValueError("Declare and satisfy that line transport energy belongs only to coolant")
    rise = finite(coolant_enthalpy_rise_j_kg, "coolant enthalpy rise", positive=True)
    if isinstance(evidence_ids, str):
        raise TypeError("evidence_ids must be a sequence of evidence identities")
    ids = tuple(evidence_ids)
    if not ids or any(not isinstance(item, str) or not item.strip() for item in ids):
        raise ValueError("Identify the coolant enthalpy rise and accepted mass quadrature")
    initial = run.initial_inventories[node_id]
    final = final_step.inventories[node_id]
    initial.basis.require_compatible(final.basis)
    initial.basis.require_compatible(coolant_integral.basis)
    balance = final_step.balances[node_id]
    if (type(balance) is not InventoryBalance or balance.initial != initial
            or balance.current != final):
        raise ValueError("Final line balance is detached from the retained run inventories")
    issues = balance.violations(tolerances or InventoryTolerances())
    if issues:
        raise ValueError("Native line inventory balance is not admitted: " + "; ".join(issues))
    removed_by_stream = -balance.transported_enthalpy_j
    if removed_by_stream <= 0.0:
        raise ValueError("The native transport ledger does not show net line cooling")
    required_mass = removed_by_stream / rise
    return DynamicLineCooldownAudit(
        node_id=node_id,
        clock_id=run.clock_id,
        start_time_s=run.start_time_s,
        end_time_s=final_step.time_s,
        initial=initial,
        final=final,
        coolant_mass=coolant_mass,
        coolant_enthalpy_rise_j_kg=rise,
        coolant_only_energy_transport=coolant_only_energy_transport,
        transported_enthalpy_j=balance.transported_enthalpy_j,
        ambient_heat_j=balance.external_heat_j,
        boundary_mass_kg=balance.boundary_mass_kg,
        boundary_energy_j=balance.boundary_energy_j,
        required_coolant_mass_kg=required_mass,
        coolant_mass_residual_kg=coolant_integral.value-required_mass,
        coolant_energy_residual_j=(balance.transported_enthalpy_j
                                   + coolant_integral.value*rise),
        stored_energy_drop_j=initial.total_energy_j-final.total_energy_j,
        inventory_mass_residual_kg=balance.mass_residual_kg,
        inventory_energy_residual_j=balance.energy_residual_j,
        evidence_ids=ids,
        coolant_mass_refinement=coolant_mass_refinement,
        _source_run=run,
    )


def _sample_equipment_rate(run, reader, *, include_snapshots=False):
    if type(run) is not DynamicEquipmentRun:
        raise TypeError("Supply an accepted DynamicEquipmentRun")
    run.require_current()
    if not run.steps or not run.initial_inventories:
        raise ValueError("A sampled integral requires accepted steps and an inventory basis")
    basis = next(iter(run.initial_inventories.values())).basis
    for inventory in run.initial_inventories.values():
        basis.require_compatible(inventory.basis)
    end = run.steps[-1].time_s
    points = [(run.start_time_s, 0, run.initial_equipment)]
    points.extend((step.time_s, 0, step.equipment) for step in run.steps)
    for event in run.transitions:
        points.extend(((event.time_s, 0, event.before), (event.time_s, 1, event.after)))
    points.sort(key=lambda item: (item[0], item[1]))
    if any(not run.start_time_s <= at <= end for at, _side, _snapshot in points):
        raise ValueError("A sampled point is outside the operation window")
    values = [(at, finite(reader(snapshot), "sampled rate"), snapshot)
              for at, _side, snapshot in points]
    areas = [(right_t-left_t)*(left_value+right_value)/2.
             for (left_t, left_value, _left_snapshot), (right_t, right_value, _right_snapshot)
             in zip(values, values[1:])
             if right_t > left_t]
    result = (basis, end, tuple(at for at, _value, _snapshot in values),
              tuple(value for _at, value, _snapshot in values), areas)
    if include_snapshots:
        return (*result, tuple(snapshot for _at, _value, snapshot in values))
    return result


def integrate_equipment_rate(run: DynamicEquipmentRun,
                             reader: Callable[[EquipmentNetworkSnapshot], float], *,
                             rate_unit: str, integral_unit: str) -> SampledEquipmentIntegral:
    """Explicit linear-sample quadrature retaining both sides of each command.

    This integrates accepted samples, not native RK-stage fluxes. Refinement
    must qualify its error for a selected rate, especially near sharp changes.
    """
    basis, end, _times, _rates, areas = _sample_equipment_rate(run, reader)
    return SampledEquipmentIntegral(fsum(areas), basis, rate_unit, integral_unit, run.clock_id,
                                    run.start_time_s, end, len(areas))


def integrate_unidirectional_equipment_rate(
    run: DynamicEquipmentRun,
    reader: Callable[[EquipmentNetworkSnapshot], float],
    *,
    rate_unit: str,
    integral_unit: str,
    trajectory_id: str,
) -> UnidirectionalEquipmentIntegral:
    """Integrate accepted rates and reject any sampled flow reversal."""
    basis, end, times, rates, areas, snapshots = _sample_equipment_rate(
        run, reader, include_snapshots=True,
    )
    integral = SampledEquipmentIntegral(fsum(areas), basis, rate_unit, integral_unit,
                                        run.clock_id, run.start_time_s, end, len(areas))
    return UnidirectionalEquipmentIntegral(
        integral, trajectory_id, times, rates, run, snapshots, reader,
    )


class InventoryClosureError(RuntimeError):
    def __init__(self, step, errors):
        self.step, self.errors = step, tuple(errors)
        super().__init__("; ".join(errors))


class Lh2dtDynamicEquipment:
    """Partition prescribed command times while retaining the native solver.

    Commands modify equipment modes, not dynamic inventories. A continuous
    command callback must be smooth within each prescribed interval. Pressure
    trigger localization and depletion events are outside this contract.
    """

    _ledger_fields = ("cumulative_boundary_mass_kg", "cumulative_boundary_energy_J",
                      "cumulative_boundary_transport_energy_J", "cumulative_boundary_ambient_heat_J")

    def __init__(self, network: Lh2dtEquipmentNetwork, nodes: Mapping[str, Lh2dtInventoryNode], *,
                 simulator_factory: Callable[..., Any], tolerances: InventoryTolerances | None = None):
        if not nodes or any(name != binding.native_node.name for name, binding in nodes.items()):
            raise ValueError("Inventory bindings need matching, nonempty native node identities")
        if set(nodes)-set(network.native.boundaries):
            raise ValueError("Every dynamic inventory must be a native boundary node")
        self.network, self.nodes = network, dict(nodes)
        self.simulator_factory = simulator_factory
        self.tolerances = tolerances or InventoryTolerances()

    def _inventory(self, name, state):
        value = self.nodes[name].inventory_reader(state)
        if not isinstance(value, ConservedInventory):
            raise TypeError("An inventory reader must return ConservedInventory")
        self.network.bridge.basis.require_compatible(value.basis)
        return value

    @staticmethod
    def _check_boundary(name, expected, actual):
        if (not isclose(expected.pressure_Pa, actual.pressure_pa, rel_tol=1e-8, abs_tol=.01)
                or not isclose(expected.specific_enthalpy_J_kg, actual.enthalpy_j_kg,
                               rel_tol=1e-8, abs_tol=1e-4)):
            raise ValueError(f"Command replaced dynamic inventory boundary {name!r}")

    def run(self, duration_s: float, time_step_s: float, *, clock_id: str,
            start_time_s: float = 0., commands: Sequence[ScheduledEquipmentCommand] = (),
            continuous_command: Callable[[float, Any], None] | None = None,
            pressure_solver_max_nfev: int = 300):
        duration = finite(duration_s, "duration_s", positive=True)
        width = finite(time_step_s, "time_step_s", positive=True)
        start = finite(start_time_s, "start_time_s")
        end = finite(start+duration, "end_time_s")
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("The operation clock identity must be explicit")
        if width < 1e-9 or end <= start:
            raise ValueError("Time resolution is below the reviewed native clock precision")
        if (not isinstance(pressure_solver_max_nfev, int) or isinstance(pressure_solver_max_nfev, bool)
                or pressure_solver_max_nfev < 1):
            raise ValueError("pressure_solver_max_nfev must be a positive integer")
        if len({c.identifier for c in commands}) != len(commands):
            raise ValueError("Scheduled command identities must be unique")
        grouped = {}
        for command in commands:
            if not start <= command.time_s <= end:
                raise ValueError("Scheduled command is outside the requested run window")
            grouped.setdefault(command.time_s, []).append(command)
        boundaries = sorted({start, end, *grouped})
        if any(b-a < 1e-9 for a, b in zip(boundaries, boundaries[1:])):
            raise ValueError("Scheduled boundaries are closer than the native clock precision")

        states = {name: binding.native_node.initial_state for name, binding in self.nodes.items()}
        initial = {name: self._inventory(name, state) for name, state in states.items()}
        expected = {}

        def publish():
            expected.update({name: self.nodes[name].native_node.thermo(state)
                             for name, state in states.items()})
            self.network.native.set_boundary_states(dict(expected))

        def check(snapshot):
            for name, state in expected.items():
                self._check_boundary(name, state, snapshot.node_states[name])

        publish()
        if continuous_command is not None:
            continuous_command(start, self.network.native)
        current = self.network.solve(max_pressure_nfev=pressure_solver_max_nfev)
        check(current)
        first = current
        steps, transitions = [], []
        offsets = {field: dict.fromkeys(self.nodes, 0.) for field in self._ledger_fields}
        for index, at in enumerate(boundaries):
            if at in grouped:
                before = current
                for command in grouped[at]:
                    command.apply(at, self.network.native)
                current = self.network.solve(max_pressure_nfev=pressure_solver_max_nfev)
                check(current)
                transitions.append(EquipmentCommandTransition(at,
                    tuple(c.identifier for c in grouped[at]), before, current))
            if index == len(boundaries)-1:
                break
            until = boundaries[index+1]
            accepted_by_identity = {}

            def remember(snapshot):
                check(snapshot)
                accepted_by_identity[id(snapshot.native)] = snapshot

            wrapped_nodes = {}
            for name, binding in self.nodes.items():
                original = binding.native_node

                def thermo(state, *, name=name, original=original):
                    result = original.thermo(state)
                    expected[name] = result
                    return result

                def derivative(state, flows, local_time, *, original=original, offset=at):
                    value = original.derivative(state, flows, offset+local_time)
                    if not hasattr(value, "ambient_heat_W"):
                        raise ValueError("Dynamic derivative must declare external ambient_heat_W")
                    finite(value.ambient_heat_W, "ambient_heat_W")
                    return value

                wrapped_nodes[name] = replace(original, initial_state=states[name],
                                               thermo=thermo, derivative=derivative)

            callback = None
            if continuous_command is not None:
                def callback(local_time, graph, *, offset=at):
                    continuous_command(offset+local_time, graph)

            simulator = self.simulator_factory(self.network.checked_native(on_solve=remember),
                wrapped_nodes, command_callback=callback,
                pressure_solver_max_nfev=pressure_solver_max_nfev)
            rows = simulator.simulate(until-at, min(width, until-at))
            previous = 0.
            for row in rows:
                local_time = finite(row.time_s, "native time_s", positive=True)
                if local_time <= previous or local_time > until-at+1e-12:
                    raise ValueError("Native accepted times are not ordered within the command interval")
                if local_time-previous > min(width, until-at)+1e-12:
                    raise ValueError("Native accepted step exceeds the requested maximum time step")
                previous = local_time
                snapshot = accepted_by_identity.get(id(row.network_solution))
                if snapshot is None or snapshot.native is not row.network_solution:
                    raise ValueError("Accepted native solution has no checked identity match")
                if set(row.states) != set(self.nodes):
                    raise ValueError("Native accepted state identities differ from the bound inventories")
                inventories = {name: self._inventory(name, state) for name, state in row.states.items()}
                balances = {}
                for name in self.nodes:
                    values = [offsets[field][name]+getattr(row, field)[name]
                              for field in self._ledger_fields]
                    balances[name] = InventoryBalance(initial[name], inventories[name], *values)
                absolute_time = (until if row is rows[-1] and isclose(local_time, until-at,
                                 rel_tol=1e-12, abs_tol=1e-12) else at+local_time)
                if absolute_time <= (steps[-1].time_s if steps else start):
                    raise ValueError("Accepted absolute times cannot be represented as increasing values")
                step = DynamicEquipmentStep(absolute_time, inventories, balances, snapshot, row)
                errors = [f"{name}: {error}" for name, balance in balances.items()
                          for error in balance.violations(self.tolerances)]
                if errors:
                    raise InventoryClosureError(step, errors)
                steps.append(step)
            if not rows or not isclose(previous, until-at, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError("Native simulator did not reach the prescribed command boundary")
            states = dict(rows[-1].states)
            for field in self._ledger_fields:
                offsets[field] = {name: offsets[field][name]+getattr(rows[-1], field)[name]
                                  for name in self.nodes}
            current = steps[-1].equipment
        return _issue_dynamic_run(clock_id=clock_id, start_time_s=start,
                                  initial_inventories=initial, initial_equipment=first,
                                  steps=tuple(steps), transitions=tuple(transitions))
