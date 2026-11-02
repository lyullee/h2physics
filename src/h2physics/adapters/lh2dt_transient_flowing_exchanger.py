"""Transient two-fluid flowing hold-up through native LH2DT derivatives/integration.

Caller boundary streams are evaluated at every native stage from both current
fluid states. Native DynamicVaporizer owns upwind enthalpy and fluid/wall energy;
native DynamicNetworkSimulator owns integration. No pressure-drop law is inferred.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from math import fsum, isclose
from types import MappingProxyType

from ..core import finite
from .lh2dt_heat_exchanger import HeatExchangerCompositeDerivative, Lh2dtFiniteHeatExchanger

_PENDING_TRANSIENT_EXCHANGER_TRACE_ISSUERS: set[object] = set()


@dataclass(frozen=True, slots=True)
class FlowingCompositeState:
    left: object
    right: object
    # Per side: net transported mass kg, net stream enthalpy J, interwall heat J.
    left_ledgers: tuple = (0., 0., 0.)
    right_ledgers: tuple = (0., 0., 0.)


@dataclass(frozen=True, slots=True)
class TransientExchangerPoint:
    time_s: float
    native_state: FlowingCompositeState
    mass_residuals_kg: tuple
    energy_residuals_j: tuple
    native_step: object


@dataclass(frozen=True, slots=True)
class NativeExchangerSegment:
    start_time_s: float
    end_time_s: float
    initial_state: FlowingCompositeState
    final_state: FlowingCompositeState
    native_simulator: object
    native_rows: tuple


@dataclass(frozen=True, slots=True)
class TransientFlowingExchangerTrace:
    owner: object
    clock_id: str
    boundary_evidence_id: str
    points: tuple
    native_rows: tuple
    native_simulator: object
    native_boundary_evaluations: tuple
    boundary_change_times_s: tuple = ()
    clock_tolerance_s: float = 1e-10
    native_segments: tuple = ()
    interval_boundary_streams: object = field(default=None, repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRANSIENT_EXCHANGER_TRACE_ISSUERS:
            raise TypeError("Create transient exchanger traces through the native run method")
        _PENDING_TRANSIENT_EXCHANGER_TRACE_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (id(self.owner), id(self.owner.finite_owner), id(self.owner.boundary_streams),
                self.clock_id, self.boundary_evidence_id, repr(self.points),
                tuple(id(row) for row in self.native_rows), id(self.native_simulator),
                self.boundary_change_times_s, self.clock_tolerance_s, id(self.interval_boundary_streams),
                tuple((segment.start_time_s, segment.end_time_s, id(segment.initial_state),
                       id(segment.final_state), id(segment.native_simulator),
                       tuple(id(row) for row in segment.native_rows)) for segment in self.native_segments))

    def require_current(self):
        self.owner.finite_owner._require_configuration()
        if self._content() != self._seal:
            raise ValueError("Transient exchanger trace or original owner changed")
        return self


def _issue_transient_flowing_exchanger_trace(**values):
    token = object()
    _PENDING_TRANSIENT_EXCHANGER_TRACE_ISSUERS.add(token)
    try:
        return TransientFlowingExchangerTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_TRANSIENT_EXCHANGER_TRACE_ISSUERS.discard(token)
        raise


class TransientExchangerError(RuntimeError):
    def __init__(self, cause, owner, evaluations, rows, simulator, segments=(), failed_interval=None):
        self.cause, self.owner = cause, owner
        self.native_boundary_evaluations, self.native_rows = tuple(evaluations), tuple(rows)
        self.native_simulator = simulator
        self.completed_native_segments = tuple(segments)
        self.failed_interval_s = failed_interval
        super().__init__("Native transient flowing exchanger failed")


class Lh2dtTransientFlowingExchanger:
    """Simultaneous finite fluid/wall operation with explicit native stream callbacks."""

    def __init__(self, finite_owner, boundary_streams, *, boundary_evidence_id):
        if type(finite_owner) is not Lh2dtFiniteHeatExchanger or not callable(boundary_streams):
            raise TypeError("Supply the admitted finite native exchanger and boundary callback")
        if not isinstance(boundary_evidence_id, str) or not boundary_evidence_id.strip():
            raise ValueError("Declare boundary stream/reference applicability evidence")
        self.finite_owner, self.boundary_streams = finite_owner, boundary_streams
        self.boundary_evidence_id = boundary_evidence_id

    def run(self, *, duration_s, maximum_step_s, start_time_s, clock_id,
            boundary_change_times_s=(), clock_tolerance_s=1e-10,
            interval_boundary_streams=None):
        """Run the native fixed-step grid with explicitly aligned boundary changes.

        Declared changes require ``interval_boundary_streams``; grid alignment
        alone cannot assign both limits of a discontinuous RK endpoint. Each interval gets
        its own native simulator, carrying the complete physical state and ledgers.
        That callback also receives ``interval_start_s`` and ``interval_end_s`` and
        owns both endpoint limits for that interval, so an endpoint jump cannot
        accidentally select the next interval's command. No physical time is shifted.
        Unknown event localization remains outside this scheduled restart API.
        """
        base = self.finite_owner
        duration = finite(duration_s, "duration_s", positive=True)
        step = finite(maximum_step_s, "maximum_step_s", positive=True)
        start = finite(start_time_s, "start_time_s")
        tolerance = finite(clock_tolerance_s, "clock_tolerance_s", positive=True)
        changes = tuple(finite(value, "boundary change time") for value in boundary_change_times_s)
        grid_step = min(duration, step)
        if tolerance >= grid_step/4:
            raise ValueError("Clock tolerance must resolve distinct native integration steps")
        if (any(not start < value < start+duration for value in changes)
                or any(b <= a for a, b in zip(changes, changes[1:]))):
            raise ValueError("Boundary changes must be strictly increasing interior absolute times")
        if interval_boundary_streams is not None and not callable(interval_boundary_streams):
            raise TypeError("Interval boundary streams must be an explicit callable")
        if changes and interval_boundary_streams is None:
            raise ValueError(
                "Scheduled boundary jumps require interval_boundary_streams with explicit endpoint limits; "
                "grid alignment alone cannot resolve both RK endpoint commands"
            )
        for value in changes if interval_boundary_streams is None else ():
            index = round((value-start)/grid_step)
            if index < 1 or not isclose(start+index*grid_step, value, rel_tol=0., abs_tol=tolerance):
                raise ValueError("Native fixed-step simulator cannot admit this irregular boundary-change grid")
        if (min(duration, step) < 1e-9 or start+min(duration, step) <= start
                or abs((start+duration)-start-duration) > 1e-10):
            raise ValueError("Physical clock cannot resolve the native simulation interval")
        if not isinstance(clock_id, str) or not clock_id.strip():
            raise ValueError("Declare the physical operation clock")
        base._require_configuration()
        sides = (base.left, base.right)
        nodes = tuple(base.native_side_node_factory(s.side_id, s.native_component,
                                                    s.initial_native_state) for s in sides)
        initial = FlowingCompositeState(*(s.initial_native_state for s in sides))
        initial_inventories = tuple(base._read(s, state)[1] for s, state in zip(sides, (initial.left, initial.right)))
        evaluations, rows, simulator = [], (), None
        segments = []
        interval_start, interval_end = start, start+duration
        original_configuration = (self.finite_owner, self.boundary_streams, self.boundary_evidence_id)

        def guard():
            if (self.finite_owner is not original_configuration[0]
                    or self.boundary_streams is not original_configuration[1]
                    or self.boundary_evidence_id != original_configuration[2]):
                raise ValueError("Transient exchanger owner/boundary configuration changed")
            base._require_configuration()

        def fluids(state):
            guard()
            return tuple(base._read(s, raw)[0] for s, raw in zip(sides, (state.left, state.right)))

        def derivative(state, network_flows, local_time):
            if tuple(network_flows):
                raise ValueError("Process flows must enter through explicit side boundary callbacks")
            pair = fluids(state)
            time = interval_start+local_time
            if abs((time-interval_start)-local_time) > tolerance:
                raise ValueError("Absolute physical clock loses native interval elapsed time")
            if not interval_start-tolerance <= time <= interval_end+tolerance:
                raise ValueError("Native stage left the declared physical clock window")
            callback_inputs = dict(time_s=time, clock_id=clock_id,
                fluids=MappingProxyType(dict(zip((s.side_id for s in sides), pair))))
            if interval_boundary_streams is None:
                boundary = self.boundary_streams(**callback_inputs)
            else:
                boundary = interval_boundary_streams(**callback_inputs,
                    interval_start_s=interval_start, interval_end_s=interval_end)
            guard()
            if not isinstance(boundary, Mapping) or set(boundary) != {s.side_id for s in sides}:
                raise ValueError("Boundary callback must supply each exact side's native streams")
            streams = tuple(tuple(boundary[s.side_id]) for s in sides)
            guard()
            from lh2dt.dynamic_network import MassEnergyFlow
            for stream_set in streams:
                for stream in stream_set:
                    if type(stream) is not MassEnergyFlow:
                        raise TypeError("Boundary callback must supply original native MassEnergyFlow objects")
                    finite(stream.mass_flow_kg_s, "native signed mass flow")
                    finite(stream.specific_enthalpy_J_kg, "native stream enthalpy")
            rates = tuple(s.native_component.derivative_from_flows(raw, incoming,
                ambient_temperature_K=other.wall_temperature_K)
                for s, raw, other, incoming in zip(sides, (state.left, state.right),
                                                  (state.right, state.left), streams))
            guard()
            for s, rate, fluid, stream_set in zip(sides, rates, pair, streams):
                for name in ("mass_kg_s", "internal_energy_W", "wall_temperature_K_s",
                             "mass_flow_in_kg_s", "mass_flow_out_kg_s", "inlet_enthalpy_flow_W",
                             "outlet_enthalpy_flow_W", "heat_from_ambient_W", "heat_from_wall_W"):
                    finite(getattr(rate, name), "native "+name)
                mass_in = fsum(flow.mass_flow_kg_s for flow in stream_set if flow.mass_flow_kg_s >= 0.)
                mass_out = -fsum(flow.mass_flow_kg_s for flow in stream_set if flow.mass_flow_kg_s < 0.)
                incoming_energy = fsum(flow.mass_flow_kg_s*flow.specific_enthalpy_J_kg
                                       for flow in stream_set if flow.mass_flow_kg_s >= 0.)
                if (not isclose(rate.mass_kg_s, mass_in-mass_out, rel_tol=1e-12, abs_tol=1e-14)
                        or not isclose(rate.mass_flow_in_kg_s, mass_in, rel_tol=1e-12, abs_tol=1e-14)
                        or not isclose(rate.mass_flow_out_kg_s, mass_out, rel_tol=1e-12, abs_tol=1e-14)
                        or not isclose(rate.inlet_enthalpy_flow_W, incoming_energy,
                                       rel_tol=1e-12, abs_tol=base.heat_rate_tolerance_w)
                        or not isclose(rate.outlet_enthalpy_flow_W, mass_out*fluid.enthalpy_j_kg,
                                       rel_tol=1e-12, abs_tol=base.heat_rate_tolerance_w)):
                    raise ValueError("Native side transport changed signed mass or upwind enthalpy semantics")
                residual = (rate.internal_energy_W+s.native_component.wall_heat_capacity*rate.wall_temperature_K_s
                            -rate.inlet_enthalpy_flow_W+rate.outlet_enthalpy_flow_W-rate.heat_from_ambient_W)
                if abs(finite(residual, "native energy-rate residual")) > base.heat_rate_tolerance_w:
                    raise ValueError("Native flowing fluid/wall energy-rate balance failed")
            if abs(rates[0].heat_from_ambient_W+rates[1].heat_from_ambient_W) > base.heat_rate_tolerance_w:
                raise ValueError("Native wall coupling is not equal and opposite")
            evaluations.append((time, state, streams, rates))
            return HeatExchangerCompositeDerivative(*rates)

        def advance(state, rates, dt):
            def ledger(previous, rate):
                return tuple(a+dt*b for a, b in zip(previous, (
                    rate.mass_kg_s, rate.inlet_enthalpy_flow_W-rate.outlet_enthalpy_flow_W,
                    rate.heat_from_ambient_W)))
            return FlowingCompositeState(nodes[0].advance(state.left, rates.left, dt),
                nodes[1].advance(state.right, rates.right, dt),
                ledger(state.left_ledgers, rates.left), ledger(state.right_ledgers, rates.right))

        def combine(a, b, c, d):
            return HeatExchangerCompositeDerivative(
                nodes[0].combine_derivatives(a.left, b.left, c.left, d.left),
                nodes[1].combine_derivatives(a.right, b.right, c.right, d.right))

        try:
            composite = replace(nodes[0], name=base.equipment_id, initial_state=initial,
                thermo=lambda state: (fluids(state), nodes[0].thermo(state.left))[1],
                derivative=derivative, advance=advance, combine_derivatives=combine)
            edges = (start, *changes, start+duration) if interval_boundary_streams is not None else (start, start+duration)
            timeline = []
            carried = initial
            for interval_start, interval_end in zip(edges, edges[1:]):
                length = interval_end-interval_start
                if (length < 1e-9 or interval_start+min(step, length) <= interval_start
                        or tolerance >= min(step, length)/4
                        or abs((interval_start+length)-interval_end) > tolerance):
                    raise ValueError("Native interval cannot resolve the scheduled boundary clock")
                native_node = replace(composite, initial_state=carried)
                network = base.native_network_factory(properties=base.left.bridge.native)
                network.add_boundary(base.equipment_id, nodes[0].thermo(carried.left))
                simulator = base.native_simulator_factory(network, {base.equipment_id: native_node})
                segment_rows = tuple(simulator.simulate(length, min(length, step)))
                guard()
                if not segment_rows or abs(segment_rows[-1].time_s-length) > tolerance:
                    raise ValueError("Native segment did not reach its declared endpoint")
                following = segment_rows[-1].states[base.equipment_id]
                segments.append(NativeExchangerSegment(interval_start, interval_end, carried,
                                                         following, simulator, segment_rows))
                rows = rows+segment_rows
                timeline.extend((interval_start+row.time_s, row.states[base.equipment_id], row)
                                for row in segment_rows)
                carried = following
            points = []
            for time, state, row in [(start, initial, None)]+timeline:
                fluids(state)
                if points and not 0 < time-points[-1].time_s <= step+tolerance:
                    raise ValueError("Native accepted time/step sequence is invalid")
                if points and any(points[-1].time_s+tolerance < change < time-tolerance for change in changes):
                    raise ValueError("Native step crossed a declared boundary discontinuity")
                inventories = tuple(base._read(s, raw)[1] for s, raw in zip(sides, (state.left, state.right)))
                mass, energy = [], []
                for inventory, original, ledger in zip(inventories, initial_inventories,
                                                       (state.left_ledgers, state.right_ledgers)):
                    mass.append(inventory.mass_kg-original.mass_kg-ledger[0])
                    energy.append(inventory.total_energy_j-original.total_energy_j-ledger[1]-ledger[2])
                for merror, eerror, inventory, original, ledger in zip(
                        mass, energy, inventories, initial_inventories,
                        (state.left_ledgers, state.right_ledgers)):
                    mass_budget = max(base.tolerances.mass_absolute_kg,
                                      base.tolerances.relative*max(original.mass_kg, inventory.mass_kg, abs(ledger[0])))
                    energy_budget = max(base.tolerances.energy_absolute_j,
                                        base.tolerances.relative*max(abs(original.total_energy_j),
                                            abs(inventory.total_energy_j), abs(ledger[1]), abs(ledger[2])))
                    if abs(merror) > mass_budget or abs(eerror) > energy_budget:
                        raise ValueError("Accepted native flowing hold-up mass/energy residual exceeded budget")
                if abs(state.left_ledgers[2]+state.right_ledgers[2]) > base.tolerances.energy_absolute_j:
                    raise ValueError("Accepted interwall heat integrals are not equal and opposite")
                points.append(TransientExchangerPoint(time, state, tuple(mass), tuple(energy), row))
            return _issue_transient_flowing_exchanger_trace(
                owner=self, clock_id=clock_id,
                boundary_evidence_id=self.boundary_evidence_id,
                points=tuple(points), native_rows=rows,
                native_simulator=simulator,
                native_boundary_evaluations=tuple(evaluations),
                boundary_change_times_s=changes,
                clock_tolerance_s=tolerance,
                native_segments=tuple(segments),
                interval_boundary_streams=interval_boundary_streams,
            )
        except Exception as cause:
            raise TransientExchangerError(cause, self, evaluations, rows, simulator,
                                           segments, (interval_start, interval_end)) from cause


__all__ = ["Lh2dtTransientFlowingExchanger", "TransientFlowingExchangerTrace",
           "TransientExchangerPoint", "TransientExchangerError", "NativeExchangerSegment"]
