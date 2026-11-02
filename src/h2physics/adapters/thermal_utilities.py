"""Source-bound finite heat-duty and utility allocation contracts.

Implemented_unverified. Original models own heat calculation, thermodynamics and
integration. This module audits explicit finite heat transfers, not pinch,
utility availability, refrigeration performance, price or annual production.
"""

import weakref
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from types import MappingProxyType
from typing import Protocol, runtime_checkable

import numpy as np

from ..core import immutable_array, Origin, finite
from ..dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from .physical_economics import (
    QuantityBoundary,
    callable_identity,
    finite_sum,
    quantity_definition,
    require_validated_projection,
    snapshot_sha256,
)
from .result_provenance import recorded_content_sha256

STATUS = "implemented_unverified"


_PENDING_NATIVE_EXCHANGE_TOKENS: set[object] = set()


def _text(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare thermal boundary, source, clock and reference evidence")


def _fields(value):
    return {f.name: getattr(value, f.name) for f in fields(value)}


def _array(value, name, *, nonnegative=False):
    result = np.array(value, dtype=float, copy=True)
    if result.ndim != 1 or not np.all(np.isfinite(result)) or (nonnegative and np.any(result < 0)):
        raise ValueError(name + " needs a finite explicitly oriented one-dimensional SI array")
    result = immutable_array(result, name="result")
    return result


def _same(a, b):
    return len(a) == len(b) and all(x is y for x, y in zip(a, b, strict=True))


@dataclass(frozen=True, slots=True)
class HeatWindow:
    start_s: float
    end_s: float
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        if finite(self.start_s, "heat window start") >= finite(self.end_s, "heat window end"):
            raise ValueError("Thermal reporting needs an increasing physical-seconds window")
        _text(self.clock_id, self.evidence_id)


@dataclass(frozen=True, slots=True)
class HeatComponent:
    owner: object
    identifier: str

    def __post_init__(self):
        if self.owner is None:
            raise ValueError("Retain the original physical boundary owner")
        _text(self.identifier)

    @property
    def key(self):
        return id(self.owner), self.identifier


@dataclass(frozen=True, slots=True)
class HeatSnapshot:
    source: object
    window: HeatWindow
    source_id: str
    boundary_id: str
    energy_basis_id: str
    edges_s: np.ndarray
    heat_into_process_j: np.ndarray
    components: tuple[HeatComponent, ...]
    reported_temperature_k: tuple
    scope: str
    evidence_ids: tuple[str, ...]
    original_objects: tuple
    verification_scope: str

    def __post_init__(self):
        if type(self.window) is not HeatWindow:
            raise TypeError("Use an actual explicit HeatWindow")
        HeatWindow(**_fields(self.window))
        _text(self.source_id, self.boundary_id, self.energy_basis_id, self.verification_scope)
        if self.scope not in {
            "required-process-duty",
            "external-device-heat",
            "internal-transfer",
            "steady-held-duty",
        }:
            raise ValueError(
                "Distinguish required, external, internal and explicit steady-held heat"
            )
        edges, heat = (
            _array(self.edges_s, "heat edges s"),
            _array(self.heat_into_process_j, "signed heat J"),
        )
        if (
            len(edges) < 2
            or heat.shape != (len(edges) - 1,)
            or np.any(np.diff(edges) <= 0)
            or edges[0] != self.window.start_s
            or edges[-1] != self.window.end_s
        ):
            raise ValueError("Heat bins must exactly preserve this source's entire original window")
        components = tuple(self.components)
        if (
            not components
            or any(type(c) is not HeatComponent for c in components)
            or len({c.key for c in components}) != len(components)
        ):
            raise ValueError("Use distinct original heat-component identities")
        evidence = tuple(self.evidence_ids)
        if not evidence:
            raise ValueError("Original heat/source evidence is mandatory")
        _text(*evidence)
        object.__setattr__(self, "edges_s", edges)
        object.__setattr__(self, "heat_into_process_j", heat)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "reported_temperature_k", tuple(self.reported_temperature_k))
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "original_objects", tuple(self.original_objects))


@runtime_checkable
class HeatDutyAdapter(Protocol):
    identifier: str

    def snapshot(self, source, window: HeatWindow) -> HeatSnapshot: ...


def _material(snapshot):
    return (
        snapshot.window,
        snapshot.source_id,
        snapshot.boundary_id,
        snapshot.energy_basis_id,
        snapshot.edges_s,
        snapshot.heat_into_process_j,
        tuple(c.key for c in snapshot.components),
        snapshot.reported_temperature_k,
        snapshot.scope,
        snapshot.evidence_ids,
        snapshot.verification_scope,
    )


def _source_signature(source, adapter):
    native = getattr(adapter, "native_component", None)
    bridge = getattr(adapter, "bridge", None)
    properties = getattr(native, "properties", None)
    definitions = tuple(
        vars(obj)
        for obj in (source, adapter, native, bridge, properties)
        if obj is not None and hasattr(obj, "__dict__")
    )
    return recorded_content_sha256((source, adapter, definitions))


class ThermalUtilityError(ValueError):
    def __init__(
        self,
        message,
        *,
        original,
        source=None,
        adapter=None,
        profiles=(),
        allocations=(),
        result=None,
    ):
        super().__init__(message)
        self.original_error, self.source, self.adapter = original, source, adapter
        self.profiles, self.allocations, self.result = tuple(profiles), tuple(allocations), result


@dataclass(frozen=True, slots=True, weakref_slot=True)
class HeatDuty:
    source: object
    adapter: HeatDutyAdapter
    snapshot: HeatSnapshot
    _content: str = field(repr=False)
    _source_content: str = field(repr=False)
    _identities: tuple = field(repr=False)
    _audit: tuple = field(repr=False)
    _cache_content: str = field(repr=False)
    _original_ref: object = field(default=None, init=False, repr=False)

    @classmethod
    def bind(cls, source, adapter, window):
        try:
            if not isinstance(adapter, HeatDutyAdapter):
                raise TypeError("Provide an explicit source-owner HeatDutyAdapter")
            _text(adapter.identifier)
            audit = callable_identity(adapter.snapshot)
            before = _source_signature(source, adapter)
            snapshot = adapter.snapshot(source, window)
            if (
                type(snapshot) is not HeatSnapshot
                or snapshot.source is not source
                or snapshot.window is not window
            ):
                raise ValueError("Thermal adapter changed the actual source/window")
            if (
                not _same(callable_identity(adapter.snapshot), audit)
                or _source_signature(source, adapter) != before
            ):
                raise ValueError(
                    "A source/adapter definition changed during its read-only heat audit"
                )
            identities = (
                source,
                adapter,
                window,
                *tuple(c.owner for c in snapshot.components),
                *snapshot.original_objects,
            )
            result = cls(
                source,
                adapter,
                snapshot,
                snapshot_sha256(_material(snapshot)),
                before,
                identities,
                audit,
                recorded_content_sha256(snapshot),
            )
            object.__setattr__(result, "_original_ref", weakref.ref(result))
            return result.require_current()
        except Exception as cause:
            raise ThermalUtilityError(
                str(cause), original=cause, source=source, adapter=adapter
            ) from cause

    @property
    def window(self):
        return self.snapshot.window

    @property
    def heating_j(self):
        return np.maximum(self.snapshot.heat_into_process_j, 0.0)

    @property
    def rejection_j(self):
        return np.maximum(-self.snapshot.heat_into_process_j, 0.0)

    def require_current(self):
        if (
            self._original_ref is None
            or self._original_ref() is not self
            or not _same(callable_identity(self.adapter.snapshot), self._audit)
            or recorded_content_sha256(self.snapshot) != self._cache_content
            or snapshot_sha256(_material(self.snapshot)) != self._content
            or _source_signature(self.source, self.adapter) != self._source_content
        ):
            raise ValueError("Original thermal source/duty/cache/adapter binding changed")
        current = self.adapter.snapshot(self.source, self.window)
        identities = (
            self.source,
            self.adapter,
            self.window,
            *tuple(c.owner for c in current.components),
            *current.original_objects,
        )
        if (
            type(current) is not HeatSnapshot
            or current.source is not self.source
            or current.window is not self.window
            or not _same(identities, self._identities)
            or snapshot_sha256(_material(current)) != self._content
            or _source_signature(self.source, self.adapter) != self._source_content
        ):
            raise ValueError("Original source/native heat evidence became stale")
        return self


@dataclass(frozen=True, slots=True)
class ProjectionHeatAdapter:
    boundary: str
    identifier: str = "original-PV-MEC-physical-heat-projection"

    def snapshot(self, source, window):
        from .microbial_cell import MicrobialCellTrace
        from .pv_electrolysis import PVElectrolysisTrace

        require_validated_projection(source)
        trace = source.source
        if (window.start_s, window.end_s, window.clock_id) != (
            source.window.start_s,
            source.window.end_s,
            source.window.clock_id,
        ):
            raise ValueError("Physical and thermal reporting windows/clocks differ")
        if type(trace) is PVElectrolysisTrace and self.boundary in {"pv-stack", "pv-receiver"}:
            stack = self.boundary == "pv-stack"
            rows = tuple(trace.steps)
            heat = tuple(
                -s.stack_heat_rejected_j if stack else s.receiver_heat_into_j for s in rows
            )
            edges = (rows[0].point.stage.start_s, *(s.point.stage.end_s for s in rows))
            temperatures = tuple(
                (s.point.stage.stack_temperature_k,)
                if stack
                else (s.before.receiver.temperature_k, s.after.receiver.temperature_k)
                for s in rows
            )
            name = "stack_heat_input_j" if stack else "receiver_heat_input_j"
        elif type(trace) is MicrobialCellTrace and self.boundary == "mec":
            rows = tuple(trace.steps)
            heat = tuple(s.isothermal_heat_required_into_j for s in rows)
            edges = (rows[0].stage.start_s, *(s.stage.end_s for s in rows))
            temperatures = tuple((s.before.temperature_k, s.after.temperature_k) for s in rows)
            name = "required_heat_input_j"
        else:
            raise TypeError("Select the actual PV stack/receiver or MEC boundary")
        boundary = source.source_binding.cached_snapshot.boundaries[name]
        components = tuple(HeatComponent(trace.owner, k) for k in boundary.billing_components)
        require_validated_projection(source)
        return HeatSnapshot(
            source,
            window,
            source.source_binding.cached_snapshot.source_id,
            self.boundary,
            boundary.basis_id,
            edges,
            heat,
            components,
            temperatures,
            "required-process-duty",
            (window.evidence_id, boundary.evidence_id),
            (trace, trace.owner, trace.caloric_provider, *rows),
            "original validated projection/producer heat ledger; required duty is not utility availability",
        )


@dataclass(frozen=True, slots=True)
class CarrierHeatAdapter:
    identifier: str = "original-carrier-thermochemical-stage-heat"

    def snapshot(self, source, window):
        from .carrier_conversion import CarrierConversionResult

        if type(source) is not CarrierConversionResult or source.require_current() is not source:
            raise TypeError("Use an original producer-issued finite carrier result")
        rows = tuple(source.process_trace.steps)
        if not rows or source.evidence.clock_id != window.clock_id:
            raise ValueError("Carrier heat needs original nonempty stage clock/support")
        result = HeatSnapshot(
            source,
            window,
            source.evidence.process_id,
            "carrier-process-heat",
            source.caloric_source.provider.basis_id,
            (rows[0].stage.start_s, *(s.stage.end_s for s in rows)),
            tuple(s.heat_required_j for s in rows),
            (HeatComponent(source.owner, "carrier-thermal-boundary"),),
            tuple((s.before.temperature_k, s.after.temperature_k) for s in rows),
            "required-process-duty",
            (source.evidence.thermal_boundary_id, window.evidence_id),
            (source.owner, source.kernel, source.caloric_source, *rows),
            "producer-issued carrier stage-net heat; conditioning/reaction signs within a stage unresolved",
        )
        source.require_current()
        return result


@dataclass(frozen=True, slots=True)
class FiniteExchangerHeatAdapter:
    side_id: str
    identifier: str = "original-native-finite-interwall-heat"

    def snapshot(self, source, window):
        from .lh2dt_heat_exchanger import HeatExchangerTrace

        if type(source) is not HeatExchangerTrace:
            raise TypeError("Use an actual original finite native exchanger trace")
        source.require_current()
        if source.clock_id != window.clock_id:
            raise ValueError("Exchanger and thermal reporting clocks differ")
        sides = tuple(s for s in source.finite_sides if s.side_id == self.side_id)
        if len(sides) != 1:
            raise ValueError("Select one actual retained finite exchanger side")
        rows, side = source.points, sides[0]
        cumulative = [p.sides[self.side_id].balance.external_heat_j for p in rows]
        result = HeatSnapshot(
            source,
            window,
            side.initial_source_id,
            self.side_id,
            side.bridge.basis.reference_id,
            [p.time_s for p in rows],
            np.diff(cumulative),
            (HeatComponent(side.native_component, "interwall-heat-port"),),
            tuple(
                (
                    a.sides[self.side_id].native_state.wall_temperature_K,
                    b.sides[self.side_id].native_state.wall_temperature_K,
                )
                for a, b in zip(rows[:-1], rows[1:], strict=True)
            ),
            "internal-transfer",
            (source.coupling.parameter_source_id, window.evidence_id),
            (source.native_simulator, source.native_network, side, side.native_component, *rows),
            "original native closed finite interwall transfer already settled; not a new external utility",
        )
        source.require_current()
        return result


@dataclass(frozen=True, slots=True)
class DynamicDeviceHeatAdapter:
    node_id: str
    native_component: object
    native_provenance: object
    inventory_binding: object
    binding_evidence_id: str
    tolerances: InventoryTolerances
    identifier: str = "original-native-vaporizer-reliquefier-external-heat"

    def snapshot(self, source, window):
        from .lh2dt_compressor import Lh2dtNativeProvenance
        from .lh2dt_dynamics import DynamicEquipmentRun, lumped_inventory_reader
        from .lh2dt_reliquefier import ReliquefierInventoryBinding

        if type(source) is not DynamicEquipmentRun or not source.steps:
            raise TypeError("Use an original accepted finite native device run")
        _text(self.node_id, self.binding_evidence_id)
        InventoryTolerances(**_fields(self.tolerances))
        if type(self.native_provenance) is not Lh2dtNativeProvenance or not any(
            b[4] is self.native_component for b in self.native_provenance.bindings
        ):
            raise TypeError("Retain actual native component/source provenance")
        self.native_provenance.require_current()
        if type(self.inventory_binding) is ReliquefierInventoryBinding:
            if (
                self.inventory_binding.native_component is not self.native_component
                or self.inventory_binding.inventory_node.native_node.name != self.node_id
                or self.inventory_binding.cold_boundary.clock_id != window.clock_id
            ):
                raise ValueError("Original cold-side inventory/component/clock binding changed")
        elif (
            getattr(getattr(self.inventory_binding, "native_node", None), "name", None)
            != self.node_id
        ):
            raise TypeError("Retain the actual original native inventory-node binding")
        if (
            source.clock_id != window.clock_id
            or self.node_id not in source.initial_inventories
            or type(self.native_component).__module__
            not in {"lh2dt.dynamic_vaporizer", "lh2dt.dynamic_reliquefier"}
        ):
            raise ValueError("Bind the actual native vaporizer/reliquefier node and clock")
        initial = source.initial_inventories[self.node_id]
        reader = lumped_inventory_reader(self.native_component.wall_heat_capacity, initial.basis)
        values, temperatures = [0.0], []
        previous = None
        for row in source.steps:
            balance = row.balances[self.node_id]
            ConservedInventory(**_fields(row.inventories[self.node_id]))
            InventoryBalance(**_fields(balance))
            if (
                balance.initial is not initial
                or balance.current is not row.inventories[self.node_id]
                or balance.violations(self.tolerances)
            ):
                raise ValueError("Original external fluid-plus-wall ledger does not close")
            values.append(balance.external_heat_j)
            state = row.native.states[self.node_id]
            if reader(state) != row.inventories[self.node_id]:
                raise ValueError(
                    "Original native finite state differs from its fluid-plus-wall inventory"
                )
            finite(
                row.native.cumulative_boundary_ambient_heat_J[self.node_id],
                "native external heat ledger J",
            )
            temperatures.append(
                (
                    None if previous is None else previous.wall_temperature_K,
                    state.wall_temperature_K,
                )
            )
            previous = state
        self.native_provenance.require_current()
        return HeatSnapshot(
            source,
            window,
            self.binding_evidence_id,
            self.node_id + ":external-heat",
            initial.basis.reference_id,
            [source.start_time_s, *(r.time_s for r in source.steps)],
            np.diff(values),
            (HeatComponent(self.native_component, "external-fluid-plus-wall-heat"),),
            tuple(temperatures),
            "external-device-heat",
            (self.binding_evidence_id, window.evidence_id),
            (self.native_component, self.native_provenance, self.inventory_binding, *source.steps),
            "original accepted external net heat; caller node/component linkage; no chiller work/COP or utility availability",
        )


@dataclass(frozen=True, slots=True)
class SteadyNativeHeatAdapter:
    kind: str
    native_component: object
    bridge: object
    native_provenance: object
    steady_hold_evidence_id: str
    identifier: str = "actual-native-steady-heat-explicit-hold"

    def snapshot(self, source, window):
        from .lh2dt import from_lh2dt_state
        from .lh2dt_compressor import Lh2dtNativeProvenance
        from .lh2dt_reliquefier import SteadyReliquefierResult

        if type(self.native_provenance) is not Lh2dtNativeProvenance or not any(
            b[4] is self.native_component for b in self.native_provenance.bindings
        ):
            raise TypeError("Retain actual native component/source provenance")
        self.native_provenance.require_current()
        _text(self.steady_hold_evidence_id)
        if self.native_component.properties is not self.bridge.native:
            raise ValueError("Keep the actual native component/property/reference binding")
        if self.kind == "reliquefier":
            if (
                type(source) is not SteadyReliquefierResult
                or source.native_component is not self.native_component
            ):
                raise TypeError("Use the actual original native steady reliquefier result")
            power, native = source.transfer.power.heat_w, source.native_result
            if not any(b[4] is native for b in self.native_provenance.bindings):
                raise ValueError("Capture this actual native reliquefier result in its provenance")
            if (
                source.transfer.upstream is not source.inlet
                or source.transfer.transmitted is not source.outlet
                or from_lh2dt_state(native.outlet, basis=self.bridge.basis) != source.outlet
            ):
                raise ValueError("Original native cold point/state/transport ownership differs")
            if power != -finite(native.heat_removed_W, "native cold duty W"):
                raise ValueError("Native removed heat and signed process duty disagree")
            self.bridge.basis.require_compatible(source.inlet.basis)
            temperatures = ((source.inlet.temperature_k, source.outlet.temperature_k),)
        elif self.kind == "vaporizer":
            cls = type(source)
            if cls.__module__ != "lh2dt.vaporizer" or cls.__name__ != "VaporizerResult":
                raise TypeError("Use an actual native VaporizerResult")
            if not any(binding[4] is source for binding in self.native_provenance.bindings):
                raise ValueError("Capture this original native result in its native provenance")
            power, native = finite(source.heat_into_hydrogen_W, "native vaporizer heat W"), source
            outlet = from_lh2dt_state(source.outlet, basis=self.bridge.basis)
            temperatures = ((outlet.temperature_k,),)
        else:
            raise ValueError("Select explicit native vaporizer/reliquefier meaning")
        amount = finite(power * (window.end_s - window.start_s), "explicit steady-held heat J")
        self.native_provenance.require_current()
        return HeatSnapshot(
            source,
            window,
            self.steady_hold_evidence_id,
            self.kind + ":process-heat",
            self.bridge.basis.reference_id,
            [window.start_s, window.end_s],
            [amount],
            (HeatComponent(self.native_component, "process-heat"),),
            temperatures,
            "steady-held-duty",
            (self.steady_hold_evidence_id, window.evidence_id),
            (self.native_component, self.bridge, self.native_provenance, native),
            "native steady W times explicit caller hold seconds; not observed finite utility or refrigeration work",
        )


@dataclass(frozen=True, slots=True)
class ExergyReference:
    identifier: str
    environment_temperature_k: float | None
    environment_pressure_pa: float | None
    environment_composition_id: str
    evidence_id: str
    status: str

    def __post_init__(self):
        _text(self.identifier, self.environment_composition_id, self.evidence_id)
        if self.status not in {"declared-context-only", "unresolved"}:
            raise ValueError(
                "Exergy context is declared or explicitly unresolved; no exergy is calculated"
            )
        for name in ("environment_temperature_k", "environment_pressure_pa"):
            value = getattr(self, name)
            if value is not None:
                finite(value, name, positive=True)
        if self.status == "declared-context-only" and (
            self.environment_temperature_k is None or self.environment_pressure_pa is None
        ):
            raise ValueError("Declared environment context needs explicit temperature and pressure")


@dataclass(frozen=True, slots=True)
class TemperatureLevel:
    minimum_k: float
    maximum_k: float
    interface_id: str
    evidence_id: str
    exergy_reference: ExergyReference
    scale_id: str = "absolute-K"

    def __post_init__(self):
        if finite(self.minimum_k, "interface minimum K", positive=True) > finite(
            self.maximum_k, "interface maximum K", positive=True
        ):
            raise ValueError("Declare ordered interval interface-temperature bounds")
        _text(self.interface_id, self.evidence_id)
        if self.scale_id != "absolute-K" or type(self.exergy_reference) is not ExergyReference:
            raise ValueError(
                "Keep absolute thermodynamic temperature and actual environment-reference identity"
            )
        ExergyReference(**_fields(self.exergy_reference))


@dataclass(frozen=True, slots=True)
class HeatAvailability:
    source: HeatDuty
    recoverable_j: np.ndarray
    evidence_id: str
    finite_boundary_id: str
    original_budget_owner: object
    origin: Origin

    def __post_init__(self):
        if type(self.source) is not HeatDuty:
            raise TypeError("Availability must bind an actual original heat duty")
        self.source.require_current()
        values = _array(self.recoverable_j, "explicit recoverable heat J", nonnegative=True)
        if values.shape != self.source.rejection_j.shape or np.any(
            values > self.source.rejection_j
        ):
            raise ValueError(
                "Explicit finite recoverable budget cannot exceed original interval heat rejection"
            )
        _text(self.evidence_id, self.finite_boundary_id)
        if self.original_budget_owner is None:
            raise ValueError(
                "Retain the actual finite budget or explicit scenario assumption owner"
            )
        object.__setattr__(self, "origin", Origin(self.origin))
        if self.origin == Origin.UNRESOLVED:
            raise ValueError("Unresolved availability is absent, never automatic free heat")
        object.__setattr__(self, "recoverable_j", values)


@dataclass(frozen=True, slots=True)
class NativeExchangeReceipt:
    donor: HeatDuty
    receiver: HeatDuty
    evidence_id: str
    heat_j: np.ndarray
    energy_tolerance_j: float
    _content: str = field(repr=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_NATIVE_EXCHANGE_TOKENS:
            raise ValueError("Native exchange receipts are issued only by the validated binder")
        _PENDING_NATIVE_EXCHANGE_TOKENS.remove(self._issuer_token)
        if type(self.donor) is not HeatDuty or type(self.receiver) is not HeatDuty:
            raise TypeError("Retain the exact validated native exchanger heat duties")
        _text(self.evidence_id)
        finite(self.energy_tolerance_j, "native exchange energy tolerance", positive=True)
        object.__setattr__(
            self,
            "heat_j",
            _array(self.heat_j, "native transferred heat J", nonnegative=True),
        )

    @classmethod
    def bind(cls, donor, receiver, *, evidence_id, energy_tolerance_j):
        donor.require_current()
        receiver.require_current()
        tolerance = finite(energy_tolerance_j, "native exchange energy tolerance", positive=True)
        _text(evidence_id)
        if (
            type(donor.adapter) is not FiniteExchangerHeatAdapter
            or type(receiver.adapter) is not FiniteExchangerHeatAdapter
            or donor.source is not receiver.source
            or donor.adapter.side_id == receiver.adapter.side_id
            or not np.array_equal(donor.snapshot.edges_s, receiver.snapshot.edges_s)
        ):
            raise ValueError(
                "Native receipt requires both actual sides of the same original finite exchanger"
            )
        out, into = -donor.snapshot.heat_into_process_j, receiver.snapshot.heat_into_process_j
        if np.any(out < 0) or np.any(into < 0) or np.any(abs(out - into) > tolerance):
            raise ValueError(
                "Native closed transfer must retain one direction and equal opposite interval energy"
            )
        values = _array(into, "native transferred heat J")
        token = object()
        _PENDING_NATIVE_EXCHANGE_TOKENS.add(token)
        try:
            return cls(
                donor,
                receiver,
                evidence_id,
                values,
                tolerance,
                snapshot_sha256((donor._content, receiver._content, evidence_id, tolerance, values)),
                token,
            )
        except Exception:
            _PENDING_NATIVE_EXCHANGE_TOKENS.discard(token)
            raise

    def require_current(self):
        self.donor.require_current()
        self.receiver.require_current()
        tolerance = finite(
            self.energy_tolerance_j, "native exchange energy tolerance", positive=True
        )
        _text(self.evidence_id)
        if (
            type(self.donor.adapter) is not FiniteExchangerHeatAdapter
            or type(self.receiver.adapter) is not FiniteExchangerHeatAdapter
            or self.donor.source is not self.receiver.source
            or self.donor.adapter.side_id == self.receiver.adapter.side_id
            or not np.array_equal(self.donor.snapshot.edges_s, self.receiver.snapshot.edges_s)
        ):
            raise ValueError("Native exchange receipt lost its original opposite-side binding")
        out = -self.donor.snapshot.heat_into_process_j
        into = self.receiver.snapshot.heat_into_process_j
        if (
            np.any(out < 0)
            or np.any(into < 0)
            or np.any(abs(out - into) > tolerance)
            or not np.array_equal(self.heat_j, into)
            or snapshot_sha256(
                (
                    self.donor._content,
                    self.receiver._content,
                    self.evidence_id,
                    self.energy_tolerance_j,
                    self.heat_j,
                )
            )
            != self._content
        ):
            raise ValueError("Original native heat-transfer receipt changed")
        return self


@dataclass(frozen=True, slots=True)
class HeatAllocation:
    identifier: str
    availability: HeatAvailability
    sink: HeatDuty
    taken_j: np.ndarray
    delivered_j: np.ndarray
    loss_j: np.ndarray
    source_levels: tuple[TemperatureLevel | None, ...]
    sink_levels: tuple[TemperatureLevel | None, ...]
    minimum_approach_k: float
    thermal_contact_id: str
    reference_compatibility_evidence_id: str
    loss_boundary_evidence_id: str
    coincidence_evidence_id: str
    native_receipt: NativeExchangeReceipt | None = None

    def __post_init__(self):
        _text(
            self.identifier,
            self.thermal_contact_id,
            self.reference_compatibility_evidence_id,
            self.loss_boundary_evidence_id,
            self.coincidence_evidence_id,
        )
        if finite(self.minimum_approach_k, "declared minimum temperature approach") < 0:
            raise ValueError("Passive heat contact needs a nonnegative explicit approach")
        for name in ("taken_j", "delivered_j", "loss_j"):
            object.__setattr__(self, name, _array(getattr(self, name), name, nonnegative=True))
        object.__setattr__(self, "source_levels", tuple(self.source_levels))
        object.__setattr__(self, "sink_levels", tuple(self.sink_levels))


@dataclass(frozen=True, slots=True)
class ThermalUtilityLedger:
    profiles: tuple[HeatDuty, ...]
    allocations: tuple[HeatAllocation, ...]
    heating_remaining_j: tuple[np.ndarray, ...]
    rejection_remaining_j: tuple[np.ndarray, ...]
    quantities: Mapping[str, float]
    quantity_boundaries: Mapping[str, QuantityBoundary]
    evidence_id: str
    energy_tolerance_j: float
    declared_loss_j: float
    native_internal_transfer_j: float
    energy_residual_j: float
    _content: str = field(repr=False)
    _cache: str = field(default="", init=False, repr=False)
    status: str = "conditional finite heat allocation; no utility-performance/plant closure or exergy calculation"

    def require_current(self):
        if (
            not self._cache
            or recorded_content_sha256(
                (
                    self.heating_remaining_j,
                    self.rejection_remaining_j,
                    self.quantities,
                    self.quantity_boundaries,
                    self.evidence_id,
                    self.energy_tolerance_j,
                    self.declared_loss_j,
                    self.native_internal_transfer_j,
                    self.energy_residual_j,
                    self.status,
                )
            )
            != self._cache
        ):
            raise ValueError("Original net-utility result/array/quantity/reference cache changed")
        for profile in self.profiles:
            profile.require_current()
        replay = account_heat(
            self.profiles,
            self.allocations,
            evidence_id=self.evidence_id,
            energy_tolerance_j=self.energy_tolerance_j,
        )
        if (
            recorded_content_sha256((self.profiles, self.allocations)) != self._content
            or dict(replay.quantities) != dict(self.quantities)
            or replay.declared_loss_j != self.declared_loss_j
            or replay.native_internal_transfer_j != self.native_internal_transfer_j
            or replay.energy_residual_j != self.energy_residual_j
            or any(
                not np.array_equal(a, b)
                for a, b in zip(replay.heating_remaining_j, self.heating_remaining_j, strict=True)
            )
            or any(
                not np.array_equal(a, b)
                for a, b in zip(
                    replay.rejection_remaining_j, self.rejection_remaining_j, strict=True
                )
            )
        ):
            raise ValueError("Original heat budget/allocation/source or net-utility cache changed")
        return self


def account_heat(profiles, allocations, *, evidence_id, energy_tolerance_j):
    """Audit declared finite allocations; do not find or optimize a heat network."""
    profiles, allocations = tuple(profiles), tuple(allocations)
    try:
        tolerance = finite(energy_tolerance_j, "heat accounting tolerance J", positive=True)
        _text(evidence_id)
        if not profiles or any(type(p) is not HeatDuty for p in profiles):
            raise TypeError("Provide original source-bound HeatDuty profiles")
        first = profiles[0].snapshot
        component_keys, by_identity = set(), {id(p): i for i, p in enumerate(profiles)}
        if len(by_identity) != len(profiles):
            raise ValueError("A physical heat profile cannot be registered twice")
        for p in profiles:
            p.require_current()
            s = p.snapshot
            if (s.window.start_s, s.window.end_s, s.window.clock_id) != (
                first.window.start_s,
                first.window.end_s,
                first.window.clock_id,
            ) or not np.array_equal(s.edges_s, first.edges_s):
                raise ValueError(
                    "Heat profiles require identical original clock/window/bins; no hidden storage/rebinning"
                )
            keys = {c.key for c in s.components}
            if component_keys & keys:
                raise ValueError(
                    "Aliased/aggregate profiles would register a physical heat boundary twice"
                )
            component_keys.update(keys)
        consumed = [np.zeros_like(p.rejection_j) for p in profiles]
        served = [np.zeros_like(p.heating_j) for p in profiles]
        available_used, source_budgets, receipt_used, ids = {}, {}, set(), set()
        losses, native_transfers = [], []
        for a in allocations:
            if type(a) is not HeatAllocation or a.identifier in ids:
                raise ValueError("Use distinct explicit HeatAllocation records")
            ids.add(a.identifier)
            HeatAllocation(**_fields(a))
            budget = a.availability
            if type(budget) is not HeatAvailability:
                raise TypeError("Positive recovery requires explicit finite HeatAvailability")
            HeatAvailability(**_fields(budget))
            donor, sink = budget.source, a.sink
            if id(donor) not in by_identity or id(sink) not in by_identity or donor is sink:
                raise ValueError(
                    "Allocation endpoints must be distinct original registered physical duties"
                )
            i, j = by_identity[id(donor)], by_identity[id(sink)]
            shape = donor.rejection_j.shape
            if (
                any(v.shape != shape for v in (a.taken_j, a.delivered_j, a.loss_j))
                or len(a.source_levels) != shape[0]
                or len(a.sink_levels) != shape[0]
                or np.any(abs(a.taken_j - a.delivered_j - a.loss_j) > tolerance)
            ):
                raise ValueError(
                    "Explicit same-bin heat taken must equal delivered plus declared loss"
                )
            budget_key = id(budget)
            if id(donor) in source_budgets and source_budgets[id(donor)] is not budget:
                raise ValueError(
                    "Reuse one original finite availability record per physical source; no alias budgets"
                )
            source_budgets[id(donor)] = budget
            used = available_used.setdefault(budget_key, np.zeros(shape))
            used += a.taken_j
            if np.any(used - budget.recoverable_j > tolerance):
                raise ValueError("Allocations exceed the explicit finite recoverable budget")
            for q, lost, hot, cold in zip(
                a.delivered_j, a.loss_j, a.source_levels, a.sink_levels, strict=True
            ):
                if q == 0 and lost == 0:
                    continue
                if type(hot) is not TemperatureLevel or type(cold) is not TemperatureLevel:
                    raise ValueError(
                        "Unresolved interface temperature cannot authorize passive heat recovery"
                    )
                TemperatureLevel(**_fields(hot))
                TemperatureLevel(**_fields(cold))
                if hot.exergy_reference != cold.exergy_reference:
                    raise ValueError(
                        "Environment/exergy reference identities differ; no silent reference conversion"
                    )
                if hot.minimum_k < cold.maximum_k + a.minimum_approach_k:
                    raise ValueError(
                        "Declared passive contact cannot lift heat to a higher temperature"
                    )
                if lost > 0 and (
                    hot.exergy_reference.environment_temperature_k is None
                    or hot.minimum_k < hot.exergy_reference.environment_temperature_k
                ):
                    raise ValueError(
                        "Positive declared ambient loss requires compatible explicit environment temperature"
                    )
            consumed[i] += a.taken_j
            served[j] += a.delivered_j
            if np.any(consumed[i] - donor.rejection_j > tolerance) or np.any(
                served[j] - sink.heating_j > tolerance
            ):
                raise ValueError("Recovery exceeds original finite source rejection or sink demand")
            internal = (
                donor.snapshot.scope == "internal-transfer"
                or sink.snapshot.scope == "internal-transfer"
            )
            if internal and a.native_receipt is None:
                raise ValueError(
                    "An already settled internal HX transfer is not a free independent utility"
                )
            if a.native_receipt is not None:
                receipt = a.native_receipt.require_current()
                token = id(receipt.donor.source)
                if (
                    receipt.donor is not donor
                    or receipt.receiver is not sink
                    or token in receipt_used
                    or np.any(a.loss_j != 0)
                    or not np.array_equal(a.taken_j, receipt.heat_j)
                    or not np.array_equal(a.delivered_j, receipt.heat_j)
                ):
                    raise ValueError(
                        "Keep one original complete native closed transfer, without duplicate/loss/partial credit"
                    )
                receipt_used.add(token)
                native_transfers.append(finite_sum(receipt.heat_j, "native internal transfer"))
            losses.append(finite_sum(a.loss_j, "declared heat loss"))
        heating, rejection = [], []
        for p, q, r in zip(profiles, served, consumed, strict=True):
            # Differences within the explicitly admitted arithmetic tolerance are
            # retained, not clipped into an artificial exactly zero balance.
            heating.append(_array(p.heating_j - q, "remaining heat demand J"))
            rejection.append(_array(p.rejection_j - r, "remaining rejection J"))
            p.require_current()
        external = tuple(
            i for i, p in enumerate(profiles) if p.snapshot.scope != "internal-transfer"
        )
        quantities = {
            "required_heat_input_j": finite_sum(
                (finite_sum(heating[i]) for i in external), "remaining external heating J"
            ),
            "required_heat_rejection_j": finite_sum(
                (
                    *tuple(finite_sum(rejection[i]) for i in external),
                    finite_sum(losses, "declared external loss J"),
                ),
                "remaining external rejection J",
            ),
        }
        # Preserve tolerance residuals separately; registry-oriented billed
        # quantities must still be nonnegative, never silently rounded/clipped.
        if min(quantities.values()) < 0:
            raise ValueError(
                "Negative residual utility cannot be promoted to an oriented cost quantity"
            )
        initial_net = finite_sum(
            (finite_sum(profiles[i].snapshot.heat_into_process_j) for i in external),
            "original net external duty J",
        )
        residual = finite(
            initial_net
            - (quantities["required_heat_input_j"] - quantities["required_heat_rejection_j"]),
            "finite heat allocation energy residual J",
        )
        if abs(residual) > tolerance:
            raise ValueError(
                "Declared heat allocations/losses do not close the complete finite external balance"
            )
        components = tuple(
            str(id(c.owner)) + ":" + c.identifier for p in profiles for c in p.snapshot.components
        )
        boundaries = {}
        for key in quantities:
            definition = quantity_definition(key)
            if definition.unit != "J" or not definition.billable:
                raise ValueError("Keep original public energy/unit registry semantics")
            boundaries[key] = QuantityBoundary(
                key,
                "accounted-thermal-residual:" + key,
                "heat-transfer-increments-J; original process caloric references retained",
                evidence_id,
                components,
            )
        result = ThermalUtilityLedger(
            profiles,
            allocations,
            tuple(heating),
            tuple(rejection),
            MappingProxyType(quantities),
            MappingProxyType(boundaries),
            evidence_id,
            tolerance,
            finite_sum(losses, "declared total loss J"),
            finite_sum(native_transfers, "already settled native internal transfer J"),
            residual,
            recorded_content_sha256((profiles, allocations)),
        )
        object.__setattr__(
            result,
            "_cache",
            recorded_content_sha256(
                (
                    result.heating_remaining_j,
                    result.rejection_remaining_j,
                    result.quantities,
                    result.quantity_boundaries,
                    result.evidence_id,
                    result.energy_tolerance_j,
                    result.declared_loss_j,
                    result.native_internal_transfer_j,
                    result.energy_residual_j,
                    result.status,
                )
            ),
        )
        return result
    except Exception as cause:
        raise ThermalUtilityError(
            str(cause), original=cause, profiles=profiles, allocations=allocations
        ) from cause
