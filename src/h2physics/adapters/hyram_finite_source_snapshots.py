"""Fixed-flow, independent quasi-steady snapshots for a finite H2 source.

This module defines a host-side contract for a separately installed receiver
that can accept a caller-owned source mass rate. The bundled stationary HyRAM
adapter does not implement that capability: it calculates its own orifice
flow. No HyRAM solver, flow equation, or transient plume model is included.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from ..core import ThermoState, finite
from ..release import NozzleOpening, NozzleSourceProjection, SourceLocation


def _freeze_options(value: Any, path: str = "solver_options"):
    """Freeze a deliberately small option tree, rejecting mutable payloads."""
    if isinstance(value, Mapping):
        return MappingProxyType({
            str(key): _freeze_options(item, f"{path}.{key}")
            for key, item in value.items()
        })
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_options(item, f"{path}[]") for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError(f"{path} must contain only immutable scalar/sequence/mapping values")


def _native_signature(value: Any, active: set[int] | None = None, depth: int = 0):
    """Capture visible native-result fields so edits cannot retain admission."""
    if active is None:
        active = set()
    kind = (type(value).__module__, type(value).__qualname__)
    if value is None or isinstance(value, (str, bool, int, float, bytes)):
        return kind, repr(value)
    if depth > 12:
        return kind, "maximum snapshot depth"
    identity = id(value)
    if identity in active:
        return kind, "recursive reference"
    active.add(identity)
    try:
        if (hasattr(value, "shape") and hasattr(value, "dtype")
                and callable(getattr(value, "tobytes", None))):
            return kind, repr(value.shape), str(value.dtype), sha256(value.tobytes()).hexdigest()
        if isinstance(value, Mapping):
            return kind, tuple(sorted((repr(key), _native_signature(item, active, depth+1))
                                      for key, item in value.items()))
        if isinstance(value, (tuple, list)):
            return kind, tuple(_native_signature(item, active, depth+1) for item in value)
        attributes = getattr(value, "__dict__", None)
        if isinstance(attributes, dict):
            return kind, tuple(sorted((str(key), _native_signature(item, active, depth+1))
                                      for key, item in attributes.items()))
        slots = getattr(type(value), "__slots__", ())
        if isinstance(slots, str):
            slots = (slots,)
        if slots:
            visible = tuple((name, _native_signature(getattr(value, name), active, depth+1))
                            for name in slots if isinstance(name, str) and hasattr(value, name))
            return kind, visible
        return kind, repr(value)
    finally:
        active.remove(identity)


@dataclass(frozen=True, slots=True)
class HyRAMFixedFlowCondition:
    """Caller-owned atmospheric and native-solver boundary for one interval."""

    ambient: ThermoState
    native_atmosphere: Any
    atmosphere_evidence_id: str
    state_mapping_evidence_id: str
    solver_options: Mapping[str, Any] = field(default_factory=dict)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.ambient, ThermoState):
            raise TypeError("Provide an explicit ambient ThermoState")
        if (self.ambient.basis.fluid != "Air"
                or self.ambient.phase not in {"gas", "supercritical_gas", "supercritical"}):
            raise ValueError("The fixed-flow snapshot contract requires a gas-phase air ambient")
        if self.native_atmosphere is None:
            raise ValueError("Retain the caller-owned native atmosphere object")
        for name in ("atmosphere_evidence_id", "state_mapping_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")
        if not isinstance(self.solver_options, Mapping):
            raise TypeError("solver_options must be a Python mapping")
        object.__setattr__(self, "solver_options", _freeze_options(self.solver_options))
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (
            self.ambient, repr(self.ambient), self.native_atmosphere,
            _native_signature(self.native_atmosphere), self.atmosphere_evidence_id,
            self.state_mapping_evidence_id, _native_signature(self.solver_options),
        )

    def require_current(self):
        current = self._current_binding()
        if (not self._binding or current[0] is not self._binding[0]
                or current[2] is not self._binding[2]
                or current[1] != self._binding[1] or current[3:] != self._binding[3:]):
            raise ValueError("Atmosphere, property mapping or solver options changed after capture")
        return self


@dataclass(frozen=True, slots=True)
class HyRAMFixedFlowRun:
    """Receiver receipt for one supplied source rate.

    The receiver must return the rate it actually admitted at the source plane.
    ``accepted`` describes that receiver's own solver gate; the host computes
    the independent source-rate residual and combines the two gates.
    """

    native_result: Any
    method_id: str
    requested_mass_flow_kg_s: float
    accepted_mass_flow_kg_s: float | None
    accepted: bool
    failure: BaseException | None = None
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.method_id, str) or not self.method_id.strip():
            raise ValueError("Identify the exact receiver method")
        requested = finite(self.requested_mass_flow_kg_s, "requested H2 rate")
        if requested <= 0.:
            raise ValueError("A native snapshot is only issued for positive source rates")
        if self.accepted_mass_flow_kg_s is not None:
            admitted = finite(self.accepted_mass_flow_kg_s, "accepted source-plane H2 rate")
            if admitted < 0.:
                raise ValueError("The accepted outward source-plane rate cannot be negative")
        if type(self.accepted) is not bool:
            raise TypeError("Receiver solver acceptance must be an explicit bool")
        if self.accepted and (self.native_result is None or self.failure is not None
                              or self.accepted_mass_flow_kg_s is None):
            raise ValueError("An accepted receiver run needs native output and an admitted rate")
        if self.failure is not None and self.accepted:
            raise ValueError("A failed native result cannot be marked accepted")
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (
            self.native_result, self.method_id,
            float(self.requested_mass_flow_kg_s),
            None if self.accepted_mass_flow_kg_s is None else float(self.accepted_mass_flow_kg_s),
            self.accepted, self.failure,
            None if self.failure is None else repr(self.failure),
            _native_signature(self.native_result),
        )

    def require_current(self):
        current = self._current_binding()
        if (not self._binding or current[0] is not self._binding[0]
                or current[5] is not self._binding[5]
                or current[1:] != self._binding[1:]):
            raise ValueError("Native receiver result or fixed-flow admission changed after capture")
        return self


@runtime_checkable
class HyRAMFixedFlowReceiver(Protocol):
    """Future/third-party receiver interface with explicit fixed-flow ownership."""

    def run_fixed_flow_snapshot(
        self,
        *,
        upstream: ThermoState,
        ambient: ThermoState,
        native_atmosphere: Any,
        opening: NozzleOpening,
        location: SourceLocation,
        start_s: float,
        end_s: float,
        clock_id: str,
        mass_flow_kg_s: float,
        source_evidence_id: str,
        atmosphere_evidence_id: str,
        state_mapping_evidence_id: str,
        solver_options: Mapping[str, Any],
    ) -> HyRAMFixedFlowRun:
        """Run one steady snapshot while preserving the supplied nozzle-plane flow."""


@dataclass(frozen=True, slots=True)
class HyRAMFiniteSourceSnapshot:
    """One source interval and its independent stationary receiver result."""

    interval_index: int
    start_s: float
    end_s: float
    requested_mass_flow_kg_s: float
    requested_mass_kg: float
    run: HyRAMFixedFlowRun | None
    failure: BaseException | None
    source_rate_residual_kg_s: float | None
    source_rate_budget_kg_s: float
    accepted: bool | None
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.interval_index) is not int or self.interval_index < 0:
            raise ValueError("Snapshot index must be a nonnegative integer")
        start, end = finite(self.start_s, "snapshot start"), finite(self.end_s, "snapshot end")
        if start >= end:
            raise ValueError("Snapshot interval must have positive duration")
        requested = finite(self.requested_mass_flow_kg_s, "requested H2 rate")
        mass = finite(self.requested_mass_kg, "requested source mass")
        budget = finite(self.source_rate_budget_kg_s, "source-rate budget")
        if requested < 0. or mass < 0. or budget < 0.:
            raise ValueError("Snapshot rates, interval mass and budget cannot be negative")
        if not math.isclose(mass, requested*(end-start), rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError("Requested snapshot mass differs from the exact source interval")
        if requested == 0.:
            if (self.run is not None or self.failure is not None
                    or self.source_rate_residual_kg_s != 0. or self.accepted is not True):
                raise ValueError("A zero-flow interval has no native call and no invented release")
        elif self.failure is not None:
            if (self.accepted is not False
                    or (self.run is not None and self.run.failure is not self.failure)):
                raise ValueError("A solver failure must retain its interval and cannot be accepted")
            if self.source_rate_residual_kg_s is not None:
                raise ValueError("A failed solver has no accepted flow for rate comparison")
        else:
            if not isinstance(self.run, HyRAMFixedFlowRun):
                raise TypeError("A positive interval needs a typed fixed-flow receiver result")
            if self.run.accepted_mass_flow_kg_s is None:
                if self.run.accepted or self.accepted is not False or self.source_rate_residual_kg_s is not None:
                    raise ValueError("A receiver without an admitted rate cannot pass source admission")
            else:
                residual = finite(self.source_rate_residual_kg_s, "source-rate residual")
                if residual != self.run.accepted_mass_flow_kg_s-requested:
                    raise ValueError("Source-rate residual differs from the receiver's admitted rate")
                expected = bool(self.run.accepted and abs(residual) <= budget)
                if self.accepted is not expected:
                    raise ValueError("Combined snapshot admission differs from solver and source gates")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)
        object.__setattr__(self, "_binding", self._current_binding())

    def _current_binding(self):
        return (
            self.interval_index, float(self.start_s), float(self.end_s),
            float(self.requested_mass_flow_kg_s), float(self.requested_mass_kg),
            self.run, self.failure,
            self.source_rate_residual_kg_s, float(self.source_rate_budget_kg_s),
            self.accepted,
        )

    def require_current(self):
        current = self._current_binding()
        if (not self._binding or current[5] is not self._binding[5]
                or current[6] is not self._binding[6] or current != self._binding):
            raise ValueError("Source interval or snapshot admission changed after capture")
        if self.run is not None:
            self.run.require_current()
        return self

    @property
    def native_failure_result(self) -> Any | None:
        """Return a receiver-attached native failure object when one exists."""
        if self.run is not None and self.run.failure is not None:
            return self.run.native_result
        return getattr(self.failure, "native_result", None)


@dataclass(frozen=True, slots=True)
class HyRAMFiniteSourceSnapshotSeries:
    """Finite-source results as independent snapshots, never a transient plume."""

    projection: NozzleSourceProjection
    conditions: tuple[HyRAMFixedFlowCondition | None, ...]
    interval_results: tuple[HyRAMFiniteSourceSnapshot, ...]
    receiver_identity: str
    source_rate_budget_kg_s: float
    _bindings: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.projection) is not NozzleSourceProjection:
            raise TypeError("Retain the original nozzle-source projection")
        self.projection.require_current()
        if self.projection.flow_rule != "left_hold":
            raise ValueError("This snapshot bridge requires explicit left-hold interval semantics")
        count = len(self.projection.source.mass_kg)
        conditions, results = tuple(self.conditions), tuple(self.interval_results)
        if len(conditions) != count or len(results) != count:
            raise ValueError("Retain one condition and result slot per source interval")
        if not isinstance(self.receiver_identity, str) or not self.receiver_identity.strip():
            raise ValueError("Identify the receiver implementation and version")
        budget = finite(self.source_rate_budget_kg_s, "source-rate budget")
        if budget < 0.:
            raise ValueError("Source-rate budget cannot be negative")
        for index, (condition, result, mass) in enumerate(zip(
                conditions, results, self.projection.source.mass_kg, strict=True)):
            expected_start = float(self.projection.source.edges_s[index])
            expected_end = float(self.projection.source.edges_s[index+1])
            rate = float(self.projection.source.mean_rates_kg_s[index])
            if (result.interval_index != index or result.start_s != expected_start
                    or result.end_s != expected_end or result.requested_mass_flow_kg_s != rate
                    or result.requested_mass_kg != float(mass)
                    or result.source_rate_budget_kg_s != budget):
                raise ValueError("Snapshot slots must preserve original source order, clock and mass")
            if rate == 0.:
                if condition is not None:
                    raise ValueError("Zero-flow bins need no receiver state or atmospheric snapshot")
            elif not isinstance(condition, HyRAMFixedFlowCondition):
                raise TypeError("Every positive source interval needs explicit receiver conditions")
            else:
                sample = self.projection.history.samples[index]
                if (sample.opening != self.projection.history.samples[0].opening
                        or sample.upstream_stagnation.basis.fluid != "Hydrogen"
                        or sample.upstream_stagnation.basis.spin_composition != "normal"
                        or sample.upstream_stagnation.phase not in {
                            "gas", "supercritical_gas", "supercritical"}):
                    raise ValueError("Snapshot source must be a normal-H2 single gas with one opening")
        object.__setattr__(self, "conditions", conditions)
        object.__setattr__(self, "interval_results", results)
        object.__setattr__(self, "source_rate_budget_kg_s", budget)
        object.__setattr__(self, "_bindings", (
            self.projection, self.projection.source, self.projection.history,
            self.projection.source.location,
            tuple(conditions), tuple(results), self.receiver_identity, budget,
        ))

    def require_current(self):
        self.projection.require_current()
        current = (self.projection, self.projection.source, self.projection.history,
                   self.projection.source.location, tuple(self.conditions),
                   tuple(self.interval_results), self.receiver_identity,
                   float(self.source_rate_budget_kg_s))
        if not self._bindings or any(value is not original for value, original in zip(
                current, self._bindings, strict=True)):
            raise ValueError("Snapshot series lost its original source/receiver objects")
        for condition in self.conditions:
            if condition is not None:
                condition.require_current()
        for item in self.interval_results:
            item.require_current()
            if item.run is not None:
                item.run.require_current()
        return self

    @property
    def plume_memory_included(self) -> bool:
        return False

    @property
    def method_id(self) -> str:
        return "independent_quasi_steady_fixed_flow_snapshots"

    @property
    def source_end_reason(self) -> str:
        self.require_current()
        return self.projection.source.end_reason

    @property
    def requested_source_mass_kg(self) -> float:
        self.require_current()
        return self.projection.source.total_mass_kg

    @property
    def accepted_source_mass_kg(self) -> float:
        self.require_current()
        total = 0.
        for item in self.interval_results:
            if item.accepted is True and item.run is not None:
                total += float(item.run.accepted_mass_flow_kg_s)*(item.end_s-item.start_s)
        return total

    @property
    def source_plane_mass_residual_kg(self) -> float | None:
        """Integrated admitted-minus-requested flow where every run reports a rate."""
        self.require_current()
        if any(item.requested_mass_flow_kg_s > 0. and
               (item.run is None or item.run.accepted_mass_flow_kg_s is None)
               for item in self.interval_results):
            return None
        return math.fsum(
            (0. if item.run is None else float(item.run.accepted_mass_flow_kg_s)
             - item.requested_mass_flow_kg_s)*(item.end_s-item.start_s)
            for item in self.interval_results
        )

    @property
    def all_intervals_accepted(self) -> bool:
        self.require_current()
        return all(item.accepted is True for item in self.interval_results)


class HyRAMFiniteSourceSnapshotError(ValueError):
    """Carries the full interval-ordered diagnostic when any source bin fails."""

    def __init__(self, series: HyRAMFiniteSourceSnapshotSeries):
        self.series = series
        super().__init__("One or more fixed-flow HyRAM snapshots failed admission")


def run_hyram_finite_source_snapshots(
    projection: NozzleSourceProjection,
    *,
    receiver: HyRAMFixedFlowReceiver,
    conditions: Sequence[HyRAMFixedFlowCondition | None],
    receiver_identity: str,
    source_rate_budget_kg_s: float,
    require_accepted: bool = True,
) -> HyRAMFiniteSourceSnapshotSeries:
    """Call a compatible fixed-flow receiver once for each positive source bin.

    Calls use the left-hold H2 rate and upstream state over each original
    interval. Zero-flow intervals are retained without a native call. Raised
    solver exceptions stay attached to their exact interval. This entrypoint
    deliberately has no plume memory, time interpolation, dose, or native
    HyRAM compatibility claim.
    """
    if not isinstance(projection, NozzleSourceProjection):
        raise TypeError("Pass an owner-issued NozzleSourceProjection")
    projection.require_current()
    if not callable(getattr(receiver, "run_fixed_flow_snapshot", None)):
        raise TypeError("Receiver must implement run_fixed_flow_snapshot with fixed-flow ownership")
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    if not isinstance(receiver_identity, str) or not receiver_identity.strip():
        raise ValueError("Identify the receiving implementation and version")
    conditions = tuple(conditions)
    source = projection.source
    if len(conditions) != len(source.mass_kg):
        raise ValueError("Supply one atmosphere/solver condition per original source interval")
    budget = finite(source_rate_budget_kg_s, "source-rate budget")
    if budget < 0.:
        raise ValueError("Source-rate budget cannot be negative")
    if projection.flow_rule != "left_hold":
        raise ValueError("Only a left-hold source projection has defined interval source states here")
    results = []
    for index, mass in enumerate(source.mass_kg):
        start, end = float(source.edges_s[index]), float(source.edges_s[index+1])
        rate = float(source.mean_rates_kg_s[index])
        if rate == 0.:
            if conditions[index] is not None:
                raise ValueError("Zero-flow bins must use a None condition and no native run")
            results.append(HyRAMFiniteSourceSnapshot(
                index, start, end, rate, float(mass), None, None, 0., budget, True,
            ))
            continue
        condition = conditions[index]
        if not isinstance(condition, HyRAMFixedFlowCondition):
            raise TypeError("Positive source bins need explicit ambient and solver conditions")
        sample = projection.history.samples[index]
        upstream = sample.upstream_stagnation
        if (upstream.basis.fluid != "Hydrogen" or upstream.basis.spin_composition != "normal"
                or upstream.phase not in {"gas", "supercritical_gas", "supercritical"}):
            raise ValueError("The supplied source is outside this normal-H2 gas snapshot contract")
        if (condition.ambient.pressure_pa <= 0.
                or upstream.pressure_pa <= 2.*condition.ambient.pressure_pa):
            raise ValueError("Snapshot source pressure is outside the declared high-pressure boundary")
        try:
            run = receiver.run_fixed_flow_snapshot(
                upstream=upstream,
                ambient=condition.ambient,
                native_atmosphere=condition.native_atmosphere,
                opening=sample.opening,
                location=source.location,
                start_s=start,
                end_s=end,
                clock_id=source.location.clock_id,
                mass_flow_kg_s=rate,
                source_evidence_id=source.evidence_id,
                atmosphere_evidence_id=condition.atmosphere_evidence_id,
                state_mapping_evidence_id=condition.state_mapping_evidence_id,
                solver_options=condition.solver_options,
            )
        except Exception as exc:
            # Preserve the exact exception, source interval and any native object
            # the receiver attached to its failure for downstream investigation.
            results.append(HyRAMFiniteSourceSnapshot(
                index, start, end, rate, float(mass), None, exc, None, budget, False,
            ))
            continue
        if not isinstance(run, HyRAMFixedFlowRun):
            raise TypeError("Receiver must return a typed HyRAMFixedFlowRun receipt")
        if run.requested_mass_flow_kg_s != rate:
            raise ValueError("Receiver changed the caller-owned requested H2 rate")
        if run.accepted_mass_flow_kg_s is None:
            residual = None
            accepted = False
        else:
            residual = run.accepted_mass_flow_kg_s-rate
            accepted = bool(run.accepted and abs(residual) <= budget)
        failure = run.failure
        if failure is not None:
            accepted = False
        results.append(HyRAMFiniteSourceSnapshot(
            index, start, end, rate, float(mass), run, failure,
            residual, budget, accepted,
        ))
    series = HyRAMFiniteSourceSnapshotSeries(
        projection, conditions, tuple(results), receiver_identity, budget,
    )
    if require_accepted and not series.all_intervals_accepted:
        raise HyRAMFiniteSourceSnapshotError(series)
    return series


__all__ = [
    "HyRAMFixedFlowCondition", "HyRAMFixedFlowRun", "HyRAMFixedFlowReceiver",
    "HyRAMFiniteSourceSnapshot", "HyRAMFiniteSourceSnapshotSeries",
    "HyRAMFiniteSourceSnapshotError", "run_hyram_finite_source_snapshots",
]
