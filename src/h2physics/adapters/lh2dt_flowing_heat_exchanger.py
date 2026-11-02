"""Flowing process-port admission over an original finite exchanger trace.

The native finite exchanger remains the owner of both fluid/wall hold-up
snapshots.  Existing ``ConnectionTransfer`` objects own process inlet/outlet
enthalpy and heat duty.  This module only binds those independent results and
audits pressure loss, port identity and whole-exchanger energy closure; it does
not add a UA, effectiveness, pressure-drop or integration model.
"""

from dataclasses import dataclass, field, replace
from math import fsum
from types import MappingProxyType
from weakref import WeakValueDictionary

from ..core import finite
from ..equipment import ConnectionTransfer, EquipmentTolerances
from .lh2dt_heat_exchanger import HeatExchangerPoint, HeatExchangerTrace, Lh2dtFiniteHeatExchanger

STATUS = "implemented_unverified"


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    return value


def _transfer_signature(value: ConnectionTransfer):
    return (
        value.component_id, value.left_node, value.right_node,
        value.left_port_id, value.right_port_id, value.mass_flow_kg_s,
        value.upstream, value.transmitted, value.power,
        value.momentum_residual_pa, value.operating_point_admissible,
    )


@dataclass(frozen=True, slots=True)
class FlowingHeatExchangerSide:
    side_id: str
    transfer: ConnectionTransfer
    pressure_loss_pa: float
    pressure_loss_source_id: str
    flow_source_id: str

    def __post_init__(self):
        for name in ("side_id", "pressure_loss_source_id", "flow_source_id"):
            _identity(getattr(self, name), name)
        if not isinstance(self.transfer, ConnectionTransfer):
            raise TypeError("A flowing side requires an original ConnectionTransfer")
        finite(self.pressure_loss_pa, "pressure_loss_pa")
        if self.pressure_loss_pa < 0.0:
            raise ValueError("Declared pressure loss cannot be negative")
        if self.transfer.mass_flow_kg_s == 0.0:
            raise ValueError("A flowing exchanger side requires nonzero material flow")
        if self.transfer.operating_point_admissible is not True:
            raise ValueError("The original process transfer must admit its operating point")
        if self.transfer.upstream is None or self.transfer.transmitted is None:
            raise ValueError("A flowing side requires original inlet and outlet states")
        observed = self.transfer.upstream.pressure_pa - self.transfer.transmitted.pressure_pa
        tolerance = max(1e-9, 1e-10 * max(abs(observed), abs(self.pressure_loss_pa)))
        if observed < -tolerance or abs(observed-self.pressure_loss_pa) > tolerance:
            raise ValueError("Caller pressure loss differs from the original process states")
        if self.transfer.power.shaft_work_w != 0.0:
            raise ValueError("This heat-exchanger level admits no shaft-work boundary")

    @property
    def inlet_enthalpy_flow_w(self) -> float:
        return self.transfer.inlet_enthalpy_flow_w

    @property
    def outlet_enthalpy_flow_w(self) -> float:
        return self.transfer.outlet_enthalpy_flow_w

    @property
    def heat_into_stream_w(self) -> float:
        return self.transfer.power.heat_w


@dataclass(frozen=True, slots=True)
class FiniteHeatExchangerWitness:
    side_id: str
    point_time_s: float
    native_state: object
    fluid_mass_kg: float
    fluid_internal_energy_j: float
    wall_internal_energy_j: float
    source_id: str

    def __post_init__(self):
        _identity(self.side_id, "side_id")
        _identity(self.source_id, "source_id")
        finite(self.point_time_s, "point_time_s")
        finite(self.fluid_mass_kg, "fluid_mass_kg", positive=True)
        finite(self.fluid_internal_energy_j, "fluid_internal_energy_j")
        finite(self.wall_internal_energy_j, "wall_internal_energy_j")

    @property
    def total_stored_energy_j(self) -> float:
        return self.fluid_internal_energy_j + self.wall_internal_energy_j


@dataclass(frozen=True, slots=True, weakref_slot=True)
class FlowingHeatExchangerResult:
    equipment_id: str
    trace: HeatExchangerTrace
    trace_point_index: int
    trace_point: HeatExchangerPoint
    sides: MappingProxyType
    witnesses: MappingProxyType
    external_heat_into_streams_w: float
    total_heat_into_streams_w: float
    total_enthalpy_change_w: float
    global_energy_residual_w: float
    pressure_basis: str = "Pa_absolute"
    storage_claim: str = "finite-snapshot-witness-only-no-flowing-hold-up-derivative"
    _owner: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _identity(self.equipment_id, "equipment_id")
        if not isinstance(self.trace, HeatExchangerTrace) or not isinstance(self.trace_point, HeatExchangerPoint):
            raise TypeError("Retain the original finite exchanger trace and point")
        if not isinstance(self.trace_point_index, int) or isinstance(self.trace_point_index, bool):
            raise TypeError("trace_point_index must be an integer")
        if self.trace_point_index < 0:
            raise ValueError("Trace point index must be nonnegative")
        object.__setattr__(self, "sides", MappingProxyType(dict(self.sides)))
        object.__setattr__(self, "witnesses", MappingProxyType(dict(self.witnesses)))
        for name in ("external_heat_into_streams_w", "total_heat_into_streams_w",
                     "total_enthalpy_change_w", "global_energy_residual_w"):
            finite(getattr(self, name), name)

    def require_current(self):
        if self._owner is None:
            raise ValueError("Retain the original owner-issued flowing exchanger result")
        self._owner.require_result(self)
        return self


class FlowingHeatExchangerAdmission:
    """Bind two original process transfers to one finite hold-up snapshot."""

    def __init__(self, finite_exchanger: Lh2dtFiniteHeatExchanger, *, equipment_id: str,
                 tolerances: EquipmentTolerances | None = None):
        if not isinstance(finite_exchanger, Lh2dtFiniteHeatExchanger):
            raise TypeError("Supply the original Lh2dtFiniteHeatExchanger owner")
        self.finite_exchanger = finite_exchanger
        self.equipment_id = _identity(equipment_id, "equipment_id")
        self.tolerances = tolerances or EquipmentTolerances()
        self._configuration = (id(finite_exchanger), finite_exchanger.equipment_id,
                               self.equipment_id, self.tolerances)
        self._results = WeakValueDictionary()

    def _require_configuration(self):
        current = (id(self.finite_exchanger), self.finite_exchanger.equipment_id,
                   self.equipment_id, self.tolerances)
        if current != self._configuration:
            raise ValueError("Original finite exchanger/admission configuration changed")

    def _seal(self, result: FlowingHeatExchangerResult):
        return (
            id(result.trace), result.trace_point_index, id(result.trace_point),
            tuple((name, _transfer_signature(side.transfer), side.pressure_loss_pa,
                   side.pressure_loss_source_id, side.flow_source_id)
                  for name, side in result.sides.items()),
            tuple((name, witness.side_id, witness.point_time_s, id(witness.native_state),
                   witness.fluid_mass_kg, witness.fluid_internal_energy_j,
                   witness.wall_internal_energy_j, witness.source_id)
                  for name, witness in result.witnesses.items()),
            result.external_heat_into_streams_w, result.total_heat_into_streams_w,
            result.total_enthalpy_change_w, result.global_energy_residual_w,
            self._configuration,
        )

    def require_result(self, result: FlowingHeatExchangerResult):
        if not isinstance(result, FlowingHeatExchangerResult):
            raise TypeError("Supply an original FlowingHeatExchangerResult")
        self._require_configuration()
        self.finite_exchanger.require_trace(result.trace)
        if (self._results.get(id(result)) is not result or result._owner is not self
                or result.trace.points[result.trace_point_index] is not result.trace_point
                or result._seal != self._seal(result)):
            raise ValueError("Original flowing exchanger result/trace/ports became stale")

    def bind(self, trace: HeatExchangerTrace, *, trace_point_index: int,
             left: FlowingHeatExchangerSide, right: FlowingHeatExchangerSide,
             external_heat_into_streams_w: float = 0.0) -> FlowingHeatExchangerResult:
        self._require_configuration()
        self.finite_exchanger.require_trace(trace)
        if not isinstance(trace_point_index, int) or isinstance(trace_point_index, bool):
            raise TypeError("trace_point_index must be an integer")
        if trace_point_index < 0:
            trace_point_index += len(trace.points)
        if trace_point_index < 0 or trace_point_index >= len(trace.points):
            raise ValueError("Trace point index is outside the original trace")
        if not isinstance(left, FlowingHeatExchangerSide) or not isinstance(
            right, FlowingHeatExchangerSide
        ):
            raise TypeError("Both flowing ports require typed exchanger-side declarations")
        try:
            point = trace.points[trace_point_index]
        except IndexError as error:
            raise ValueError("Trace point index is outside the original trace") from error
        expected = {self.finite_exchanger.left.side_id, self.finite_exchanger.right.side_id}
        sides = {left.side_id: left, right.side_id: right}
        if set(sides) != expected or len(sides) != 2:
            raise ValueError("Bind exactly the two original finite exchanger side identities")
        if left.transfer is right.transfer:
            raise ValueError("Each exchanger side requires a distinct original process transfer")
        for side_id, side in sides.items():
            snapshot = point.sides.get(side_id)
            if snapshot is None:
                raise ValueError("Original trace point lacks a declared finite side")
            snapshot.fluid.basis.require_compatible(side.transfer.upstream.basis)
            snapshot.fluid.basis.require_compatible(side.transfer.transmitted.basis)
            energy_limit = self.tolerances.energy_limit_w(
                side.inlet_enthalpy_flow_w, side.outlet_enthalpy_flow_w,
                side.heat_into_stream_w)
            if abs(side.transfer.energy_residual_w) > energy_limit:
                raise ValueError("Original process transfer enthalpy/heat does not close")
        finite(external_heat_into_streams_w, "external_heat_into_streams_w")
        total_heat = fsum(side.heat_into_stream_w for side in sides.values())
        total_enthalpy = fsum(side.outlet_enthalpy_flow_w-side.inlet_enthalpy_flow_w
                              for side in sides.values())
        residual = total_heat-external_heat_into_streams_w
        limit = self.tolerances.energy_limit_w(total_heat, external_heat_into_streams_w,
                                               total_enthalpy)
        if abs(residual) > limit:
            raise ValueError("Two process-side heat duties and external heat do not close")
        witnesses = {}
        for side_id, side in sides.items():
            snapshot = point.sides[side_id]
            witnesses[side_id] = FiniteHeatExchangerWitness(
                side_id, point.time_s, snapshot.native_state,
                snapshot.inventory.mass_kg, snapshot.inventory.fluid_internal_energy_j,
                snapshot.inventory.solid_internal_energy_j,
                f"{trace.clock_id}:{trace.requested_start_s}:{trace.requested_end_s}:{side.flow_source_id}",
            )
        result = FlowingHeatExchangerResult(
            self.equipment_id, trace, trace_point_index, point,
            sides, witnesses, external_heat_into_streams_w, total_heat,
            total_enthalpy, residual, _owner=self,
        )
        result = replace(result, _seal=self._seal(result))
        self._results[id(result)] = result
        return result
