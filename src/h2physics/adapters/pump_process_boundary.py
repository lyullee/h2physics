"""Typed native pump-operation handoff to the shared process connection API."""

from dataclasses import dataclass

from ..core import ThermoState, finite
from ..equipment import BoundaryPower, ConnectionTransfer
from .result_provenance import recorded_content_sha256


@dataclass(frozen=True, slots=True)
class PumpProcessConnectionBoundary:
    trace: object
    property_adapter: object
    time_s: tuple[float, ...]
    clock_id: str
    connections: tuple[ConnectionTransfer, ...]
    receiver_pressures_pa: tuple[float, ...]
    upstream_node: str
    downstream_node: str
    source_evidence_id: str
    property_basis_id: str
    _seal: str

    def require_current(self):
        from .lh2dt_pump_operation import PumpOperationTrace

        if type(self.trace) is not PumpOperationTrace:
            raise TypeError("Retain the original issued PumpOperationTrace")
        self.trace.require_current()
        if self.property_adapter.native is not self.trace.owner.native.properties:
            raise ValueError("Original pump/property-provider identity changed")
        if self.property_adapter.basis.reference_id != self.property_basis_id or any(
                c.upstream.basis != self.property_adapter.basis
                or c.transmitted.basis != self.property_adapter.basis for c in self.connections):
            raise ValueError("Process connection thermodynamic basis changed")
        expected = _boundary_content(
            self.trace, self.property_adapter, self.connections, self.time_s, self.clock_id,
            self.receiver_pressures_pa, self.upstream_node, self.downstream_node,
            self.source_evidence_id, self.property_basis_id)
        if expected != self._seal:
            raise ValueError("Pump-to-process connection outputs changed after issue")
        if (not self.connections or len(self.connections) != len(self.trace.points)
                or self.time_s != tuple(point.time_s for point in self.trace.points)
                or self.clock_id != self.trace.actuator.clock_id
                or tuple(c.transmitted.pressure_pa for c in self.connections) != self.receiver_pressures_pa
                or self.connections[0].left_node != self.upstream_node
                or self.connections[0].right_node != self.downstream_node):
            raise ValueError("Connection series no longer matches its declared nodes/source samples")
        return self


def _connection_content(connections):
    return recorded_content_sha256(tuple(
        (c.component_id, c.left_node, c.right_node, c.left_port_id, c.right_port_id,
         c.mass_flow_kg_s, c.upstream, c.transmitted, c.power,
         c.momentum_residual_pa, c.operating_point_admissible)
        for c in connections))


def pump_operation_to_process_connections(
    trace,
    properties,
    *,
    upstream_node: str,
    downstream_node: str,
    source_evidence_id: str,
    receiver_pressure_pa: float | None = None,
) -> PumpProcessConnectionBoundary:
    """Convert accepted native pump points to `ConnectionTransfer` records.

    `properties` must be the explicit LH2DT property adapter over the exact
    provider instance owned by the native pump. Each accepted pump point retains
    its receiver absolute pressure; an optional explicit pressure asserts a
    constant-pressure boundary. Native results supply flow, outlet enthalpy and
    shaft power in SI.
    """
    from .lh2dt import Lh2dtProperties, from_lh2dt_state
    from .lh2dt_pump_operation import PumpOperationTrace

    if type(trace) is not PumpOperationTrace:
        raise TypeError("Use an original owner-issued native PumpOperationTrace")
    trace.require_current()
    if not isinstance(properties, Lh2dtProperties):
        raise TypeError("Supply the explicit shared Lh2dtProperties adapter")
    if trace.owner.native.properties is not properties.native:
        raise ValueError("Pump and process property adapter must share the exact native property owner")
    upstream = (trace.left_state if isinstance(trace.left_state, ThermoState)
                else from_lh2dt_state(trace.left_state, basis=properties.basis))
    properties.basis.require_compatible(upstream.basis)
    fixed_pressure = (None if receiver_pressure_pa is None else
                      finite(receiver_pressure_pa, "receiver absolute pressure", positive=True))
    if not isinstance(upstream_node, str) or not upstream_node.strip() or not isinstance(
            downstream_node, str) or not downstream_node.strip() or upstream_node == downstream_node:
        raise ValueError("Declare distinct nonempty process node identities")
    if not isinstance(source_evidence_id, str) or not source_evidence_id.strip():
        raise ValueError("Declare source/equipment evidence for the pump boundary")
    if not trace.points or any(not point.accepted for point in trace.points):
        raise ValueError("Only accepted native capacity/NPSH points can enter a process network")

    output = []
    for point in trace.points:
        native = point.native_result
        pressure = finite(point.receiver_pressure_pa, "accepted receiver absolute pressure", positive=True)
        if fixed_pressure is not None and pressure != fixed_pressure:
            raise ValueError("An explicit fixed receiver pressure differs from an accepted pump sample")
        flow = finite(native.mass_flow_kg_s, "native pump mass flow")
        outlet_h = finite(native.outlet_specific_enthalpy_J_kg, "native pump outlet enthalpy")
        shaft = finite(native.shaft_power_W, "native pump shaft power")
        if flow <= 0 or shaft < 0:
            raise ValueError("This process boundary supports forward flow and nonnegative shaft input only")
        outlet = properties.state_ph(pressure, outlet_h)
        properties.basis.require_compatible(outlet.basis)
        result_pressure = getattr(native, "outlet_pressure_Pa", pressure)
        if finite(result_pressure, "native outlet absolute pressure", positive=True) != pressure:
            raise ValueError("Native pump outlet pressure differs from the declared receiver boundary")
        momentum = getattr(native, "momentum_residual_Pa", None)
        output.append(ConnectionTransfer(
            component_id=trace.pump_map.map_id,
            left_node=upstream_node,
            right_node=downstream_node,
            left_port_id=trace.actuator.actuator_id + "/in",
            right_port_id=trace.actuator.actuator_id + "/out",
            mass_flow_kg_s=flow,
            upstream=upstream,
            transmitted=outlet,
            power=BoundaryPower(shaft_work_w=shaft),
            momentum_residual_pa=None if momentum is None else finite(momentum, "native momentum residual"),
            operating_point_admissible=point.accepted,
        ))

    result = PumpProcessConnectionBoundary(
        trace, properties, tuple(point.time_s for point in trace.points), trace.actuator.clock_id,
        tuple(output), tuple(c.transmitted.pressure_pa for c in output), upstream_node, downstream_node,
        source_evidence_id, properties.basis.reference_id, "")
    from dataclasses import replace
    result = replace(result, _seal=_boundary_content(
        result.trace, result.property_adapter, result.connections, result.time_s, result.clock_id,
        result.receiver_pressures_pa, result.upstream_node, result.downstream_node,
        result.source_evidence_id, result.property_basis_id))
    trace.require_current()
    return result.require_current()


def _boundary_content(trace, properties, connections, times, clock_id, pressures,
                      upstream_node, downstream_node, source_evidence_id, basis_id):
    return recorded_content_sha256((
        id(trace), id(properties), _connection_content(connections), tuple(times), clock_id,
        tuple(pressures), upstream_node, downstream_node, source_evidence_id, basis_id))
