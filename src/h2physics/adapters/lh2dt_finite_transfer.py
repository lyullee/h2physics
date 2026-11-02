"""Finite source/receiver transfer through existing native inventory machinery.

Native tank/line RHS, pressure network, nozzle and RK stepping are reused.
This is caller-scheduled transfer, not an inferred charging protocol/control law.
Primary source: https://github.com/lyullee/lh2dt_models
"""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from math import fsum
from types import MappingProxyType
from weakref import WeakValueDictionary

import numpy as np

from ..core import Origin, TimeSeries, finite
from ..dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from ..equipment import BoundaryPower
from ..release import HomogeneousIsentropicNozzle
from .lh2dt import Lh2dtProperties, from_lh2dt_state
from .lh2dt_compressor import (
    Lh2dtNativeProvenance,
    _callable_binding,
    _property_binding,
    _record_signature,
)
from .lh2dt_dynamics import Lh2dtDynamicEquipment, Lh2dtInventoryNode
from .lh2dt_equipment import Lh2dtEquipmentNetwork, Lh2dtSharedValve
from .lh2dt_heat_exchanger import HeatExchangerDomain

STATUS = "implemented_unverified"


def _text(*values):
    if any(not isinstance(x, str) or not x.strip() for x in values):
        raise ValueError("Declare nonempty source, node, port, stage and clock identities")


def _series_signature(series):
    return (series.clock_id, series.source_id, series.origin, series.channels, series.units,
        series.quantities, series.basis_ids,
        tuple((a.shape, a.dtype.str, hashlib.sha256(a.tobytes()).hexdigest())
              for a in (series.time_s, series.values, series.valid)))


@dataclass(frozen=True, slots=True)
class TransferAmbient:
    """Explicit piecewise-linear ambient K history, with no extrapolation/gap fill."""

    series: TimeSeries
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        s = self.series
        if not isinstance(s, TimeSeries):
            raise TypeError("Supply the original typed ambient observation history")
        TimeSeries(**{f.name: getattr(s, f.name) for f in fields(s)})
        if (not isinstance(s, TimeSeries) or len(s.time_s) < 2 or s.values.shape != (len(s.time_s), 1)
                or s.units != ("K",) or s.quantities != ("ambient_temperature",)
                or s.origin == Origin.UNRESOLVED or not np.all(s.valid) or np.any(s.values <= 0)):
            raise ValueError("Ambient needs a resolved, all-valid positive single-channel K history")
        object.__setattr__(self, "_seal", _series_signature(s))

    def require_current(self):
        if _series_signature(self.series) != self._seal:
            raise ValueError("Original ambient clock/mask/source/value history changed")

    def sample(self, time_s):
        self.require_current()
        time = finite(time_s, "ambient absolute time")
        if not self.series.time_s[0] <= time <= self.series.time_s[-1]:
            raise ValueError("Native ambient request is outside the declared clock support")
        return float(np.interp(time, self.series.time_s, self.series.values[:, 0]))


@dataclass(frozen=True, slots=True)
class FiniteTransferBody:
    node_id: str
    role: str
    native_model: object
    initial_native_state: object
    domain: HeatExchangerDomain
    source_id: str
    thermal_source_id: str
    ambient: TransferAmbient | None

    def __post_init__(self):
        _text(self.node_id, self.source_id, self.thermal_source_id)
        expected = {"homogeneous-tank": "HomogeneousTank", "mixed-line": "DynamicHEMPipe"}
        if self.role not in expected or type(self.native_model).__name__ != expected[self.role]:
            raise TypeError("Use actual homogeneous native tanks or an explicit finite native mixed line")
        if not isinstance(self.domain, HeatExchangerDomain):
            raise TypeError("Declare a finite inventory/phase/pressure/temperature domain")
        if self.role == "homogeneous-tank" and not isinstance(self.ambient, TransferAmbient):
            raise TypeError("Each tank requires an explicit ambient history")
        if self.role == "mixed-line" and self.ambient is not None:
            raise ValueError("The native pipe-node API uses its fixed declared ambient, not a history")

    def inventory(self, state, basis):
        model = self.native_model
        if self.role == "homogeneous-tank":
            return ConservedInventory(basis, state.hydrogen_mass_kg, state.hydrogen_internal_energy_J,
                model.geometry.wall_heat_capacity_J_K*state.wall_temperature_K)
        return ConservedInventory(basis, state.mass_kg, state.internal_energy_J,
                                  model.wall_heat_capacity*state.wall_temperature_K)


@dataclass(frozen=True, slots=True)
class TransferStage:
    identifier: str
    start_s: float
    end_s: float
    mode: str
    opening_fractions: tuple[float, ...]
    source_id: str

    def __post_init__(self):
        _text(self.identifier, self.source_id)
        if finite(self.end_s, "stage end") <= finite(self.start_s, "stage start"):
            raise ValueError("Each scheduled transfer stage needs positive clock support")
        fractions = tuple(finite(v, "valve opening fraction") for v in self.opening_fractions)
        if not fractions or any(not 0 <= x <= 1 for x in fractions):
            raise ValueError("Supply every valve fraction explicitly within [0, 1]")
        if self.mode not in {"transfer", "isolated"} or (self.mode == "isolated" and any(fractions)):
            raise ValueError("Choose a declared transfer mode or an exactly closed isolated mode")
        object.__setattr__(self, "opening_fractions", fractions)


@dataclass(frozen=True, slots=True)
class TransferStop:
    """A caller condition checked at accepted samples, not an event-localized controller."""

    kind: str
    threshold: float
    evidence_id: str

    def __post_init__(self):
        _text(self.evidence_id)
        if self.kind not in {"receiver-pressure-at-least", "receiver-net-mass-at-least", "source-mass-at-most"}:
            raise ValueError("Declare a supported accepted-sample stopping condition")
        finite(self.threshold, "stopping threshold", positive=True)


@dataclass(frozen=True, slots=True)
class TransferNativeAttempt:
    start_s: float
    end_s: float
    native_simulator: object | None
    native_rows: tuple
    native_stage_clocks_s: tuple
    native_provenance: Lh2dtNativeProvenance | None = None


@dataclass(frozen=True, slots=True)
class TransferPoint:
    time_s: float
    stage: TransferStage
    local_run: object
    inventories: Mapping
    balances: Mapping
    source_withdrawn_kg: float
    receiver_net_received_kg: float
    global_mass_residual_kg: float
    global_energy_residual_j: float
    internal_transport_residual_j: float

    def __post_init__(self):
        for name in ("inventories", "balances"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True, slots=True)
class TransferModeTransition:
    time_s: float
    kind: str
    openings_before: tuple
    openings_after: tuple
    equipment_before: object
    equipment_after: object


@dataclass(frozen=True, slots=True, weakref_slot=True)
class FiniteTransferTrace:
    clock_id: str
    requested_start_s: float
    requested_end_s: float
    actual_end_s: float
    clock_tolerance_s: float
    maximum_step_s: float
    stages: tuple
    bodies: tuple
    initial_inventories: Mapping
    initial_equipment: object
    points: tuple[TransferPoint, ...]
    transitions: tuple[TransferModeTransition, ...]
    native_attempts: tuple[TransferNativeAttempt, ...]
    termination: str
    stop_condition: TransferStop | None
    stop_value: float | None
    stop_time_bracket_s: tuple | None
    final_equipment: object
    final_isolated: bool
    native_network: object
    native_provenance: Lh2dtNativeProvenance
    inventory_tolerances: InventoryTolerances
    pressure_basis: str = "Pa_absolute"
    source_boundary: str = "all-material-nodes-finite-no-external-mass-reservoir"
    _owner: object = field(default=None, repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "initial_inventories", MappingProxyType(dict(self.initial_inventories)))

    def require_current(self):
        if self._owner is None:
            raise ValueError("Retain the original owner-issued finite transfer trace")
        self._owner.require_trace(self)


class FiniteTransferError(RuntimeError):
    def __init__(self, cause, *, owner, points, transitions, attempts, states, last_native_thermo,
                 stop_candidate=None):
        super().__init__(str(cause))
        self.cause, self.owner = cause, owner
        self.completed_points, self.transitions = tuple(points), tuple(transitions)
        self.native_attempts, self.last_accepted_states = tuple(attempts), MappingProxyType(dict(states))
        self.last_native_thermo, self.stop_candidate = last_native_thermo, stop_candidate
        self.native_network, self.native_provenance = owner.network.native, owner.native_provenance
        self.opening_fractions_at_failure = tuple(v.opening_fraction for v in owner.valves)


class _RecordingSimulator:
    """Observe the original native simulator; no physical stepping is implemented."""

    def __init__(self, factory, start, end, budget):
        self.factory, self.start, self.end, self.budget = factory, start, end, budget
        self.native, self.rows, self.clocks = None, (), []
        self.provenance = None

    def __call__(self, network, nodes, **options):
        callback = options.pop("command_callback", None)

        def observe(local_time, graph):
            local = finite(local_time, "native local stage time")
            absolute = finite(self.start+local, "native absolute stage clock")
            if (not self.start <= absolute <= self.end
                    or abs((absolute-self.start)-local) > self.budget):
                raise ValueError("Native transfer stage loses clock support/projection precision")
            self.clocks.append((local, absolute))
            if callback is not None:
                callback(local, graph)

        self.native = self.factory(network, nodes, command_callback=observe, **options)
        self.provenance = Lh2dtNativeProvenance.capture(self.native, *nodes.values())
        return self

    def simulate(self, *args, **kwargs):
        rows = self.native.simulate(*args, **kwargs)
        self.rows = tuple(rows)
        self.provenance = Lh2dtNativeProvenance.capture(self.native, *self.native.dynamic_nodes.values(), *rows)
        return rows

    def snapshot(self):
        return TransferNativeAttempt(self.start, self.end, self.native, self.rows, tuple(self.clocks), self.provenance)


class Lh2dtFiniteTransfer:
    """Two finite tanks, optional native finite line, one native simultaneous solve.

    Schedule partitioning and accepted-sample stopping reuse Lh2dtDynamicEquipment.
    Pressure feedback and all inventory/flow equations remain in existing engines.
    """

    def __init__(self, source: FiniteTransferBody, receiver: FiniteTransferBody, *,
                 bridge: Lh2dtProperties, native_api, valves: Sequence[Lh2dtSharedValve],
                 equipment_id: str, line: FiniteTransferBody | None = None,
                 inventory_tolerances: InventoryTolerances | None = None):
        _text(equipment_id)
        if source.role != "homogeneous-tank" or receiver.role != "homogeneous-tank":
            raise ValueError("Source and receiver must both be finite homogeneous native tanks")
        if line is not None and line.role != "mixed-line":
            raise ValueError("The optional intermediate inventory must be an actual finite mixed native line")
        self.source, self.receiver, self.line = source, receiver, line
        self.bodies = (source, receiver) if line is None else (source, line, receiver)
        if len({b.node_id for b in self.bodies}) != len(self.bodies):
            raise ValueError("Finite material node identities must be distinct")
        if len({id(b.native_model) for b in self.bodies}) != len(self.bodies):
            raise ValueError("Distinct finite inventories need distinct native core objects")
        self.bridge, self.native_api, self.valves, self.equipment_id = bridge, native_api, tuple(valves), equipment_id
        if len(self.valves) != (1 if line is None else 2):
            raise ValueError("Direct path needs one valve; an explicit finite-line path needs both isolation valves")
        for body in self.bodies:
            if body.native_model.properties is not bridge.native:
                raise ValueError("All finite bodies must share the declared native property instance/reference")
        for valve in self.valves:
            if type(valve) is not Lh2dtSharedValve or type(valve.nozzle) is not HomogeneousIsentropicNozzle:
                raise TypeError("Use the existing shared valve/nozzle implementation explicitly")
            if valve.properties is not bridge.native:
                raise ValueError("Every shared valve must retain the same native property instance")
            bridge.basis.require_compatible(valve.nozzle.properties.basis)
            if (valve.nozzle.properties is not bridge
                    and valve.nozzle.properties is not getattr(bridge.native, "provider", None)):
                raise ValueError("Nozzle and native inventories must share the original property owner/view")
        self.tolerances = inventory_tolerances or InventoryTolerances()
        self.halves = () if line is None else (line.native_model.inlet_hydraulic_component,
                                               line.native_model.outlet_hydraulic_component)
        for half in self.halves:
            if half.properties is not bridge.native or half.heat != 0 or half.dz != 0:
                raise ValueError("This finite transfer path needs explicit adiabatic same-height native half-segments")
        factories = (native_api.SteadyNetwork, native_api.DynamicNetworkSimulator,
                     native_api.homogeneous_tank_node, native_api.ThermoState)
        if line is not None:
            factories += (native_api.dynamic_hem_pipe_node,)
        if type(bridge.native).__module__.startswith("lh2dt."):
            factories += (bridge.native,)
        self.native_provenance = Lh2dtNativeProvenance.capture(*factories,
            *(b.native_model for b in self.bodies), *(b.initial_native_state for b in self.bodies),
            *self.halves, *(v.result_factory for v in self.valves))
        self.network = Lh2dtEquipmentNetwork(native_api.SteadyNetwork(bridge.native), bridge,
                                             state_factory=native_api.ThermoState)
        for body in self.bodies:
            self.network.add_boundary(body.node_id, self._read(body, body.initial_native_state)[0])
        if line is None:
            self._link("transfer", source.node_id, receiver.node_id, self.valves[0])
        else:
            fluid = self._read(line, line.initial_native_state)[0]
            left, right = equipment_id+":line-inlet-junction", equipment_id+":line-outlet-junction"
            self.network.add_junction(left, fluid)
            self.network.add_junction(right, fluid)
            self._link("source-isolation", source.node_id, left, self.valves[0])
            self._link("line-inlet-half", left, line.node_id, self.halves[0])
            self._link("line-outlet-half", line.node_id, right, self.halves[1])
            self._link("receiver-isolation", right, receiver.node_id, self.valves[1])
        self._host_bindings = self._host_signature()
        self._configuration_stamp = self._configuration()
        self._traces, self._running, self._last_native_thermo = WeakValueDictionary(), False, None

    def _link(self, name, left, right, component):
        self.network.add_link(self.equipment_id+":"+name, left, right, component,
            power_reader=lambda _raw: BoundaryPower(), source_port_id=left+"/"+name+"/out",
            target_port_id=right+"/"+name+"/in")

    def _read(self, body, state):
        self._last_native_thermo = (body.node_id, state, None)
        native = body.native_model.thermo(state)
        self._last_native_thermo = (body.node_id, state, native)
        fluid = from_lh2dt_state(native, basis=self.bridge.basis)
        inventory = body.inventory(state, self.bridge.basis)
        body.domain.require(fluid, wall_temperature_k=state.wall_temperature_K, mass_kg=inventory.mass_kg)
        volume = (body.native_model.geometry.volume_m3 if body.role == "homogeneous-tank"
                  else body.native_model.fluid_volume)
        if (abs(fluid.density_kg_m3*volume-inventory.mass_kg) > max(self.tolerances.mass_absolute_kg,
                self.tolerances.relative*inventory.mass_kg)
                or abs(inventory.mass_kg*fluid.internal_energy_j_kg-inventory.fluid_internal_energy_j)
                > max(self.tolerances.energy_absolute_j,
                      self.tolerances.relative*abs(inventory.fluid_internal_energy_j))):
            raise ValueError("Native EOS recovery disagrees with the finite conserved inventory")
        return fluid, inventory

    def _configuration(self):
        valve_signatures = []
        for valve in self.valves:
            provider = valve.nozzle.properties
            valve_signatures.append((id(valve), valve.properties, valve.bridge,
                _record_signature(valve.opening), valve.allow_reverse, valve.result_factory,
                _record_signature(valve.nozzle.search), id(provider), _record_signature(provider.basis),
                getattr(provider, "backend", None), id(getattr(provider, "_state", None)),
                tuple(_callable_binding(getattr(obj, name)) for obj, names in (
                    (valve, ("evaluate", "set_opening")), (valve.nozzle, ("solve",)),
                    (provider, ("state_pt", "state_ph", "state_ps"))) for name in names)))
        factory_names = ("SteadyNetwork", "DynamicNetworkSimulator", "homogeneous_tank_node", "ThermoState")
        if self.line is not None:
            factory_names += ("dynamic_hem_pipe_node",)
        native_state_method = getattr(type(self.bridge.native), "_state", None)
        native_cp = getattr(native_state_method, "__globals__", {}).get("CP")
        return (self.equipment_id, id(self.native_provenance), id(self.source), id(self.receiver), id(self.line),
            id(self.network), id(self.network.native), id(self.network.native.properties),
            _property_binding(self.bridge), _record_signature(self.network._power_readers),
            native_cp, getattr(native_cp, "PropsSI", None), getattr(native_cp, "PhaseSI", None),
            tuple(_callable_binding(getattr(self.native_api, name)) for name in factory_names),
            _record_signature(self.tolerances), tuple((id(b), _record_signature(b),
            b.source_id, b.thermal_source_id, _record_signature(b.initial_native_state),
            _record_signature(vars(b.native_model)), None if b.ambient is None else _series_signature(b.ambient.series))
            for b in self.bodies), tuple(valve_signatures),
            tuple(_record_signature(vars(h)) for h in self.halves),
            tuple((link.name, link.left, link.right, id(link.component), link.source_port_id, link.target_port_id)
                  for link in self.network.native.links), tuple(self.network.native.boundaries),
            _record_signature(self.network.native.junctions))

    @staticmethod
    def _host_signature():
        return tuple((cls, name, _callable_binding(getattr(cls, name)))
            for cls in (Lh2dtDynamicEquipment, Lh2dtEquipmentNetwork, Lh2dtSharedValve,
                        HomogeneousIsentropicNozzle, HeatExchangerDomain, TransferAmbient, FiniteTransferBody)
            for name in vars(cls) if callable(getattr(cls, name)))

    def _guard(self):
        self.native_provenance.require_current(check_files=False)
        bindings = self._host_signature()
        if bindings != self._host_bindings or self._configuration() != self._configuration_stamp:
            raise ValueError("Original native/host inventory, path, reference or callable configuration changed")
        for body in self.bodies:
            if body.ambient is not None:
                body.ambient.require_current()

    def _trace_signature(self, trace):
        return (_record_signature(trace), self._configuration(),
            tuple(v.opening_fraction for v in self.valves),
            _record_signature(self.network.native.boundaries),
            tuple((a.native_simulator, _record_signature(a.native_simulator.dynamic_nodes),
                _callable_binding(a.native_simulator.simulate),
                _callable_binding(a.native_simulator.command_callback), id(a.native_simulator.network),
                a.native_simulator.pressure_solver_max_nfev) for a in trace.native_attempts
                  if a.native_simulator is not None))

    def require_trace(self, trace):
        if not isinstance(trace, FiniteTransferTrace):
            raise TypeError("Supply an original FiniteTransferTrace")
        self._guard()
        self.native_provenance.require_current()
        for attempt in trace.native_attempts:
            if attempt.native_provenance is not None:
                attempt.native_provenance.require_current(check_files=False)
        if (self._traces.get(id(trace)) is not trace or trace._owner is not self
                or trace._seal != self._trace_signature(trace)):
            raise ValueError("Original finite transfer trace, native rows or final mode became stale")

    def _publish(self, states):
        self.network.native.set_boundary_states({b.node_id: b.native_model.thermo(states[b.node_id])
                                                for b in self.bodies})

    def _nodes(self, states):
        nodes = {}
        for body in self.bodies:
            if body.role == "homogeneous-tank":
                node = self.native_api.homogeneous_tank_node(body.node_id, body.native_model,
                    states[body.node_id], body.ambient.sample)
            else:
                node = self.native_api.dynamic_hem_pipe_node(body.node_id, body.native_model, states[body.node_id])

            def thermo(state, *, body=body):
                self._guard()
                self._read(body, state)
                return body.native_model.thermo(state)

            nodes[body.node_id] = Lh2dtInventoryNode(replace(node, thermo=thermo),
                lambda state, body=body: body.inventory(state, self.bridge.basis))
        return nodes

    @staticmethod
    def _project(start, span, budget):
        end = finite(start+span, "projected transfer absolute clock")
        if (span > 0 and end <= start) or abs((end-start)-span) > budget:
            raise ValueError("Absolute transfer clock cannot represent the requested positive interval")
        return end

    def run(self, stages: Sequence[TransferStage], *, clock_id: str, maximum_step_s: float,
            clock_tolerance_s: float, isolate_on_completion: bool,
            stop: TransferStop | None = None) -> FiniteTransferTrace:
        if self._running:
            raise ValueError("One finite transfer owner cannot run concurrently")
        points, transitions, attempts, states = [], [], [], {b.node_id: b.initial_native_state for b in self.bodies}
        context = {"stop": None}
        self._running = True
        try:
            self._guard()
            self.native_provenance.require_current()
            result = self._run(tuple(stages), clock_id, maximum_step_s, clock_tolerance_s,
                isolate_on_completion, stop, points, transitions, attempts, states, context)
            self.native_provenance.require_current()
            result = replace(result, _owner=self)
            object.__setattr__(result, "_seal", self._trace_signature(result))
            self._traces[id(result)] = result
            return result
        except Exception as cause:
            raise FiniteTransferError(cause, owner=self, points=points, transitions=transitions,
                attempts=attempts, states=states, last_native_thermo=self._last_native_thermo,
                stop_candidate=context["stop"]) from cause
        finally:
            self._running = False

    def _run(self, stages, clock, width, budget, isolate, stop, points, transitions, attempts, states, context):
        _text(clock)
        if not stages or any(not isinstance(s, TransferStage) for s in stages):
            raise TypeError("Provide an explicit contiguous schedule of TransferStage objects")
        for stage in stages:
            TransferStage(**{f.name: getattr(stage, f.name) for f in fields(stage)})
        if stop is not None and isinstance(stop, TransferStop):
            TransferStop(stop.kind, stop.threshold, stop.evidence_id)
        width, budget = finite(width, "maximum native step", positive=True), finite(budget, "clock budget", positive=True)
        if width < 1e-9 or type(isolate) is not bool or (stop is not None and not isinstance(stop, TransferStop)):
            raise ValueError("Declare >=1e-9 s steps, an explicit completion action and optional typed stop")
        if len({s.identifier for s in stages}) != len(stages):
            raise ValueError("Scheduled stage identities must be unique")
        start, end = stages[0].start_s, stages[-1].end_s
        for i, stage in enumerate(stages):
            if (len(stage.opening_fractions) != len(self.valves)
                    or (i and stage.start_s != stages[i-1].end_s)):
                raise ValueError("Schedule gaps/overlaps or missing valve openings are unsupported")
            if stage.end_s-stage.start_s < 1e-9:
                raise ValueError("Stage duration is below native clock resolution")
        for body in self.bodies:
            if body.ambient is not None:
                s = body.ambient.series
                if s.clock_id != clock or s.time_s[0] > start or s.time_s[-1] < end:
                    raise ValueError("Tank ambient clock/support must cover the entire declared schedule")
        initial = {b.node_id: self._read(b, states[b.node_id])[1] for b in self.bodies}
        totals = {name: [[], [], [], []] for name in states}
        for valve, fraction in zip(self.valves, stages[0].opening_fractions, strict=True):
            valve.set_opening(fraction)
        self._publish(states)
        first = current = self.network.solve()
        at, termination, value, bracket = start, "requested-window-end", None, None

        def stop_value():
            if stop is None:
                return None
            if stop.kind == "receiver-pressure-at-least":
                return self._read(self.receiver, states[self.receiver.node_id])[0].pressure_pa
            if stop.kind == "source-mass-at-most":
                return self._read(self.source, states[self.source.node_id])[1].mass_kg
            return fsum(totals[self.receiver.node_id][0])

        def hit(v):
            return v is not None and (v <= stop.threshold if stop.kind == "source-mass-at-most" else v >= stop.threshold)

        value = stop_value()
        if hit(value):
            termination, bracket = "initial-condition-already-met", (start, start)
            context["stop"] = (stop, value, bracket)
        else:
            for stage in stages:
                before = tuple(v.opening_fraction for v in self.valves)
                for valve, fraction in zip(self.valves, stage.opening_fractions, strict=True):
                    valve.set_opening(fraction)
                after = tuple(v.opening_fraction for v in self.valves)
                if after != before:
                    previous = current
                    current = self.network.solve()
                    transitions.append(TransferModeTransition(at, stage.identifier, before, after, previous, current))
                interval_index = 0
                while at < stage.end_s:
                    self._guard()
                    interval_index += 1
                    relative_end = min(interval_index*width, stage.end_s-stage.start_s)
                    until = (stage.end_s if relative_end == stage.end_s-stage.start_s
                             else self._project(stage.start_s, relative_end, budget))
                    dt = until-at
                    if dt < 1e-9:
                        raise ValueError("Remaining scheduled interval is below native clock resolution")
                    if dt > width+2*budget or abs(self._project(at, dt, budget)-until) > budget:
                        raise ValueError("Absolute schedule grid exceeds the native step/projection budget")
                    self._project(at, dt/2., budget)
                    recorder = _RecordingSimulator(self.native_api.DynamicNetworkSimulator, at, until, budget)
                    driver = Lh2dtDynamicEquipment(self.network, self._nodes(states),
                        simulator_factory=recorder, tolerances=self.tolerances)
                    try:
                        local = driver.run(dt, dt, clock_id=clock, start_time_s=at)
                    finally:
                        attempts.append(recorder.snapshot())
                    if len(local.steps) != 1 or local.steps[0].native is not recorder.rows[-1]:
                        raise ValueError("Native accepted interval did not return one original identity-matched step")
                    step = local.steps[0]
                    if abs(step.time_s-until) > budget:
                        raise ValueError("Native accepted absolute clock differs from its explicit interval")
                    balances = {}
                    for body in self.bodies:
                        name = body.node_id
                        balance = step.balances[name]
                        for values, amount in zip(totals[name], (balance.boundary_mass_kg,
                            balance.boundary_energy_j, balance.transported_enthalpy_j, balance.external_heat_j), strict=True):
                            values.append(amount)
                        balances[name] = InventoryBalance(initial[name], step.inventories[name],
                                                         *(fsum(values) for values in totals[name]))
                        errors = balances[name].violations(self.tolerances)
                        if errors:
                            raise ValueError(name+": "+"; ".join(errors))
                    mass = fsum(b.current.mass_kg-b.initial.mass_kg for b in balances.values())
                    transport = fsum(b.transported_enthalpy_j for b in balances.values())
                    energy = fsum(b.current.total_energy_j-b.initial.total_energy_j-b.external_heat_j
                                  for b in balances.values())
                    if (abs(mass) > self.tolerances.mass_absolute_kg
                            or max(abs(transport), abs(energy)) > self.tolerances.energy_absolute_j):
                        raise ValueError("Closed finite transfer global mass/U/transport ledger does not close")
                    points.append(TransferPoint(until, stage, local, step.inventories, balances,
                        -balances[self.source.node_id].boundary_mass_kg,
                        balances[self.receiver.node_id].boundary_mass_kg, mass, energy, transport))
                    previous_time = at
                    states.update(step.native.states)
                    at, current = until, step.equipment
                    value = stop_value()
                    if hit(value):
                        termination, bracket = "accepted-sample-condition", (previous_time, at)
                        context["stop"] = (stop, value, bracket)
                        break
                if bracket is not None:
                    break
        if isolate:
            before, previous = tuple(v.opening_fraction for v in self.valves), current
            for valve in self.valves:
                valve.set_opening(0.)
            current = self.network.solve()
            if any(t.mass_flow_kg_s != 0 for link, t in zip(self.network.native.links,
                current.transfers, strict=True) if any(link.component is v for v in self.valves)):
                raise ValueError("Explicit final isolation left a transported material flow")
            transitions.append(TransferModeTransition(at, "caller-completion-isolation", before,
                tuple(v.opening_fraction for v in self.valves), previous, current))
        self._guard()
        return FiniteTransferTrace(clock, start, end, at, budget, width, stages, self.bodies, initial,
            first, tuple(points), tuple(transitions), tuple(attempts), termination, stop, value, bracket,
            current, all(v.opening_fraction == 0 for v in self.valves), self.network.native,
            self.native_provenance, self.tolerances)
