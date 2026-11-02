"""Two finite fluid/wall cores coupled by native LH2DT wall conductance.

Both native DynamicVaporizer derivatives see the other *current finite wall*,
and one native DynamicNetworkSimulator integrates their composite state. Native
node advance/combine functions retain all physical equations and RK integration.
Only signed per-side heat integrals and Python coupling contracts are added.
Primary native API: https://github.com/lyullee/lh2dt_models
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from dataclasses import field as record_field
from types import MappingProxyType
from weakref import WeakValueDictionary

import numpy as np

from ..core import immutable_array, Origin, ThermoState, finite
from ..dynamics import ConservedInventory, InventoryBalance, InventoryTolerances
from .lh2dt import Lh2dtProperties, from_lh2dt_state
from .lh2dt_compressor import (
    Lh2dtNativeProvenance,
    _callable_binding,
    _property_binding,
    _record_signature,
)

STATUS = "implemented_unverified"


@dataclass(frozen=True, slots=True)
class HeatExchangerDomain:
    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_inventory_kg: float
    allowed_phases: tuple[str, ...]

    def __post_init__(self):
        for name in ("minimum_temperature_k", "maximum_temperature_k", "minimum_pressure_pa",
                     "maximum_pressure_pa", "minimum_inventory_kg"):
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_temperature_k >= self.maximum_temperature_k
                or self.minimum_pressure_pa >= self.maximum_pressure_pa):
            raise ValueError("Heat-exchanger domain bounds must increase")
        if not self.allowed_phases or any(not phase for phase in self.allowed_phases):
            raise ValueError("Declare the allowed native fluid phases")

    def require(self, state: ThermoState, *, wall_temperature_k, mass_kg):
        finite(mass_kg, "native finite-side mass", positive=True)
        finite(wall_temperature_k, "native finite-wall temperature", positive=True)
        if mass_kg <= self.minimum_inventory_kg:
            raise ValueError("Finite heat-exchanger inventory is below its declared minimum")
        if state.phase not in self.allowed_phases:
            raise ValueError("Fluid phase is outside the declared heat-exchanger domain")
        if not self.minimum_pressure_pa <= state.pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("Fluid pressure is outside the declared heat-exchanger domain")
        for temperature in (state.temperature_k, wall_temperature_k):
            if not self.minimum_temperature_k <= temperature <= self.maximum_temperature_k:
                raise ValueError("Fluid/wall temperature is outside the declared heat-exchanger domain")


@dataclass(frozen=True, slots=True)
class FiniteHeatExchangerSide:
    side_id: str
    native_component: object
    initial_native_state: object
    bridge: Lh2dtProperties
    domain: HeatExchangerDomain
    initial_source_id: str

    def __post_init__(self):
        if not self.side_id.strip() or not self.initial_source_id.strip():
            raise ValueError("Declare side and finite-inventory source identities")
        if self.native_component.properties is not self.bridge.native:
            raise ValueError("Each finite side and bridge must share its own native property instance")
        native_basis = getattr(self.native_component.properties, "basis", None)
        if native_basis is not None:
            native_basis.require_compatible(self.bridge.basis)


@dataclass(frozen=True, slots=True)
class HeatExchangerCoupling:
    conductance_w_k: float
    parameter_source_id: str
    origin: Origin
    native_source_id: str

    def __post_init__(self):
        if finite(self.conductance_w_k, "wall-to-wall conductance") < 0:
            raise ValueError("Wall-to-wall conductance must be nonnegative")
        object.__setattr__(self, "origin", Origin(self.origin))
        if (self.origin == Origin.UNRESOLVED or not self.parameter_source_id.strip()
                or not self.native_source_id.strip()):
            raise ValueError("Declare resolved conductance evidence and installed native source identity")


@dataclass(frozen=True, slots=True)
class HeatExchangerCompositeState:
    left: object
    right: object
    left_integrated_heat_j: float = 0.
    right_integrated_heat_j: float = 0.


@dataclass(frozen=True, slots=True)
class HeatExchangerCompositeDerivative:
    left: object
    right: object

    @property
    def ambient_heat_W(self):
        # Each native field is the heat received from the *other finite wall*.
        # Their sum is the boundary heat of the complete closed pair: zero.
        return self.left.ambient_heat_W+self.right.ambient_heat_W


@dataclass(frozen=True, slots=True)
class HeatExchangerSideSnapshot:
    side_id: str
    native_state: object
    fluid: ThermoState
    native_derivative: object
    inventory: ConservedInventory
    balance: InventoryBalance
    coupling_heat_into_side_w: float
    fluid_wall_heat_into_fluid_w: float


@dataclass(frozen=True, slots=True)
class HeatExchangerPoint:
    time_s: float
    sides: Mapping[str, HeatExchangerSideSnapshot]
    global_energy_residual_j: float
    integrated_coupling_residual_j: float
    native_composite_state: HeatExchangerCompositeState
    native_step: object | None

    def __post_init__(self):
        object.__setattr__(self, "sides", MappingProxyType(dict(self.sides)))


@dataclass(frozen=True, slots=True, weakref_slot=True)
class HeatExchangerTrace:
    clock_id: str
    requested_start_s: float
    requested_end_s: float
    coupling: HeatExchangerCoupling
    points: tuple[HeatExchangerPoint, ...]
    native_simulator: object
    native_network: object
    native_side_nodes: tuple
    native_composite_node: object
    native_components: tuple
    evaluated_clock_bounds_s: tuple[float, float]
    native_evaluation_count: int
    inventory_tolerances: InventoryTolerances
    source_boundary: str = "closed-two-finite-fluids-no-material-ports-no-external-heat"
    clock_tolerance_s: float = 1e-10
    pressure_basis: str = "Pa_absolute"
    native_provenance: Lh2dtNativeProvenance | None = None
    finite_sides: tuple[FiniteHeatExchangerSide, ...] = ()
    _owner: object = record_field(default=None, repr=False, compare=False)
    _seal: object = record_field(default=None, repr=False, compare=False)

    def require_current(self):
        """Reject a stale native trace/configuration before handing it downstream."""
        if self._owner is None:
            raise ValueError("Retain the original owner-issued finite exchanger trace")
        self._owner.require_trace(self)

    def wall_transfer_series(self, side_id: str) -> "HeatExchangerWallTransferSeries":
        """Project native accepted wall-transfer quantities for one finite side.

        Returned power values are native derivative samples and cumulative energy
        values are the integrator's retained ledgers. No quadrature, interpolation,
        or heat-direction convention is substituted by this accessor.
        """
        self.require_current()
        return HeatExchangerWallTransferSeries.from_trace(self, side_id)

    @property
    def time_s(self):
        result = np.array([p.time_s for p in self.points])
        result = immutable_array(result, name="result")
        return result


def _wall_transfer_projection(trace, side_id):
    if type(trace) is not HeatExchangerTrace:
        raise TypeError("Wall-transfer history requires an original finite exchanger trace")
    if not isinstance(side_id, str) or not side_id.strip():
        raise ValueError("Select a nonempty finite-side identity")
    trace.require_current()
    matches = [index for index, side in enumerate(trace.finite_sides)
               if side.side_id == side_id]
    if len(matches) != 1:
        raise KeyError(f"Unknown finite heat-exchanger side: {side_id}")
    field_name = ("left_integrated_heat_j" if matches[0] == 0
                  else "right_integrated_heat_j")
    if not trace.points:
        raise ValueError("Finite exchanger trace has no accepted points")
    try:
        times = np.asarray([point.time_s for point in trace.points], dtype=float)
        cumulative = np.asarray([
            getattr(point.native_composite_state, field_name) for point in trace.points
        ], dtype=float)
        rates = np.asarray([
            point.sides[side_id].coupling_heat_into_side_w for point in trace.points
        ], dtype=float)
    except (AttributeError, KeyError, TypeError) as error:
        raise ValueError("Native accepted exchanger points lack the selected side's transfer fields") from error
    if (times.ndim != 1 or times.size < 1 or np.any(~np.isfinite(times))
            or np.any(np.diff(times) <= 0.) or cumulative.shape != times.shape
            or rates.shape != times.shape or np.any(~np.isfinite(cumulative))
            or np.any(~np.isfinite(rates))):
        raise ValueError("Native wall-transfer outputs must align on a finite increasing accepted clock")
    return times, cumulative, rates


@dataclass(frozen=True, slots=True)
class HeatExchangerWallTransferSeries:
    """Evidence-bound view of one side's native accepted transfer history."""

    trace: HeatExchangerTrace
    side_id: str
    clock_id: str
    time_s: object
    cumulative_heat_into_side_j: object
    native_heat_rate_into_side_w: object

    def __post_init__(self):
        times, cumulative, rates = _wall_transfer_projection(self.trace, self.side_id)
        if self.clock_id != self.trace.clock_id:
            raise ValueError("Wall-transfer history must retain the original trace clock")
        supplied = (np.asarray(self.time_s, dtype=float),
                    np.asarray(self.cumulative_heat_into_side_j, dtype=float),
                    np.asarray(self.native_heat_rate_into_side_w, dtype=float))
        expected = (times, cumulative, rates)
        if any(value.shape != target.shape or not np.array_equal(value, target)
               for value, target in zip(supplied, expected, strict=True)):
            raise ValueError("Wall-transfer values must reproduce from the exact native accepted trace")
        object.__setattr__(self, "time_s", immutable_array(times, name="wall-transfer time"))
        object.__setattr__(self, "cumulative_heat_into_side_j",
                           immutable_array(cumulative, name="cumulative wall heat"))
        object.__setattr__(self, "native_heat_rate_into_side_w",
                           immutable_array(rates, name="native wall heat rate"))

    @classmethod
    def from_trace(cls, trace: HeatExchangerTrace, side_id: str):
        times, cumulative, rates = _wall_transfer_projection(trace, side_id)
        return cls(trace, side_id, trace.clock_id, times, cumulative, rates)

    def require_current(self):
        times, cumulative, rates = _wall_transfer_projection(self.trace, self.side_id)
        if self.clock_id != self.trace.clock_id or any(
            not np.array_equal(retained, current)
            for retained, current in zip(
                (self.time_s, self.cumulative_heat_into_side_j,
                 self.native_heat_rate_into_side_w),
                (times, cumulative, rates), strict=True,
            )
        ):
            raise ValueError("Wall-transfer projection no longer matches its original trace")
        return self


class HeatExchangerCapabilityError(RuntimeError):
    pass


class HeatExchangerIntegrationError(RuntimeError):
    def __init__(self, message, *, native_simulator, native_components, last_trial,
                 cause=None, completed_points=(), native_rows=(), native_network=None,
                 native_side_nodes=(), native_provenance=None):
        super().__init__(message)
        self.native_simulator = native_simulator
        self.native_components = native_components
        self.last_trial = last_trial
        self.cause, self.completed_points = cause, tuple(completed_points)
        self.native_rows, self.native_network = tuple(native_rows), native_network
        self.native_side_nodes, self.native_provenance = native_side_nodes, native_provenance


class Lh2dtFiniteHeatExchanger:
    """One native simultaneous integration of two sealed finite fluid/wall sides.

    The native ambient-temperature argument is connected to the other current
    wall, with equal native ambient_UA values. It is not an infinite heat bath.
    No physical fluid/wall equation, heat law or RK combiner is reproduced here.

    A port-free native network is integrator plumbing only; its representative
    thermodynamic boundary is the left side, never a combined hydraulic state.
    All physical side states/bases are returned separately. Material links and
    external heat leakage are deliberately unavailable in this closed level.
    """

    def __init__(self, left: FiniteHeatExchangerSide, right: FiniteHeatExchangerSide,
                 coupling: HeatExchangerCoupling, *, native_side_node_factory: Callable,
                 native_network_factory: Callable, native_simulator_factory: Callable,
                 equipment_id: str, inventory_tolerances: InventoryTolerances | None = None,
                 heat_rate_tolerance_w: float = 1e-9):
        if not equipment_id.strip() or left.side_id == right.side_id:
            raise ValueError("Declare an exchanger and two distinct side identities")
        if left.native_component is right.native_component:
            raise ValueError("The exchanger needs two distinct finite native components")
        self.left, self.right, self.coupling = left, right, coupling
        self.native_side_node_factory = native_side_node_factory
        self.native_network_factory, self.native_simulator_factory = native_network_factory, native_simulator_factory
        self.equipment_id = equipment_id
        self.tolerances = inventory_tolerances or InventoryTolerances(1e-12, 1e-5, 1e-10)
        self.heat_rate_tolerance_w = finite(heat_rate_tolerance_w, "heat-rate tolerance", positive=True)
        self._signatures = tuple(self._signature(s.native_component) for s in (left, right))
        self.native_provenance = Lh2dtNativeProvenance.capture(left.native_component,
            right.native_component, left.initial_native_state, right.initial_native_state,
            native_side_node_factory, native_simulator_factory)
        if coupling.native_source_id != f"LH2DT:{self.native_provenance.revision}":
            raise ValueError("Declared coupling native source does not match the verified installed revision")
        # A caller-authored network factory is permitted, never attested as native.
        self._configuration_stamp = self._configuration_signature()
        self._traces = WeakValueDictionary()
        self._running = False
        self._require_configuration()
        for side in (left, right):
            self._read(side, side.initial_native_state)

    @staticmethod
    def _signature(component):
        try:
            return (component.properties, component.fluid_volume, component.wall_heat_capacity,
                    component.fluid_wall_UA, component.ambient_UA, component.maximum_heat)
        except AttributeError as exc:
            raise HeatExchangerCapabilityError("Native DynamicVaporizer configuration is unavailable") from exc

    def _require_configuration(self):
        self.native_provenance.require_current(check_files=False)
        if self._configuration_signature() != self._configuration_stamp:
            raise HeatExchangerCapabilityError("Original finite-side/source/factory configuration changed")
        for side, signature in zip((self.left, self.right), self._signatures, strict=True):
            if self._signature(side.native_component) != signature:
                raise HeatExchangerCapabilityError("Native finite-side configuration changed during coupling")
            if side.native_component.ambient_UA != self.coupling.conductance_w_k:
                raise ValueError("Both native ambient_UA slots must equal the declared wall-to-wall conductance")

    def _configuration_signature(self):
        return (self.equipment_id, id(self.native_provenance), _record_signature(self.coupling),
            _record_signature(self.tolerances), self.heat_rate_tolerance_w,
            tuple((id(side), side.side_id, side.initial_source_id, id(side.native_component),
                id(side.initial_native_state), _record_signature(side.initial_native_state),
                _record_signature(side.domain), _property_binding(side.bridge),
                self._signature(side.native_component)) for side in (self.left, self.right)),
            tuple(_callable_binding(factory) for factory in (self.native_side_node_factory,
                self.native_network_factory, self.native_simulator_factory)))

    def _trace_signature(self, trace):
        return (_record_signature(trace), self._configuration_signature(),
            _record_signature(trace.native_network.boundaries),
            _record_signature(trace.native_network.links), _record_signature(trace.native_network.junctions),
            _record_signature(trace.native_simulator.dynamic_nodes),
            trace.native_simulator.network is trace.native_network,
            id(trace.native_network.properties),
            _callable_binding(trace.native_simulator.simulate),
            _callable_binding(trace.native_simulator.command_callback),
            trace.native_simulator.pressure_solver_max_nfev)

    def require_trace(self, trace: HeatExchangerTrace):
        if not isinstance(trace, HeatExchangerTrace):
            raise TypeError("Supply an original owner-issued HeatExchangerTrace")
        self._require_configuration()
        self.native_provenance.require_current()
        if trace.native_provenance is not None:
            trace.native_provenance.require_current()
        if (self._traces.get(id(trace)) is not trace or trace._owner is not self
                or trace._seal != self._trace_signature(trace)):
            raise HeatExchangerCapabilityError("Original finite exchanger trace/native rows became stale")

    def _read(self, side, state):
        fluid = from_lh2dt_state(side.native_component.thermo(state), basis=side.bridge.basis)
        side.domain.require(fluid, wall_temperature_k=state.wall_temperature_K, mass_kg=state.mass_kg)
        inventory = ConservedInventory(side.bridge.basis, state.mass_kg, state.internal_energy_J,
            side.native_component.wall_heat_capacity*state.wall_temperature_K)
        mass_error = fluid.density_kg_m3*side.native_component.fluid_volume-state.mass_kg
        energy_error = state.mass_kg*fluid.internal_energy_j_kg-state.internal_energy_J
        if (abs(mass_error) > max(self.tolerances.mass_absolute_kg, self.tolerances.relative*state.mass_kg)
                or abs(energy_error) > max(self.tolerances.energy_absolute_j,
                                          self.tolerances.relative*abs(state.internal_energy_J))):
            raise HeatExchangerCapabilityError("Native EOS recovery changed finite-side mass/internal energy")
        return fluid, inventory

    def run(self, *, duration_s: float, maximum_step_s: float, start_time_s: float,
            clock_id: str, clock_tolerance_s: float = 1e-10) -> HeatExchangerTrace:
        if self._running:
            raise HeatExchangerCapabilityError("One finite exchanger owner cannot run concurrently")
        context = {"simulator": None, "network": None, "nodes": (), "points": [], "rows": (),
                   "trial": None, "provenance": self.native_provenance}
        self._running = True
        try:
            self.native_provenance.require_current()
            trace = self._run(duration_s=duration_s, maximum_step_s=maximum_step_s,
                start_time_s=start_time_s, clock_id=clock_id, clock_tolerance_s=clock_tolerance_s,
                context=context)
            self.native_provenance.require_current()
            trace = replace(trace, native_provenance=context["provenance"],
                            finite_sides=(self.left, self.right), _owner=self)
            object.__setattr__(trace, "_seal", self._trace_signature(trace))
            self._traces[id(trace)] = trace
            return trace
        except Exception as cause:
            raise HeatExchangerIntegrationError(f"Native finite exchanger integration failed: {cause}",
                native_simulator=context["simulator"], native_components=(self.left.native_component,
                self.right.native_component), last_trial=context["trial"], cause=cause,
                completed_points=context["points"], native_rows=context["rows"],
                native_network=context["network"], native_side_nodes=context["nodes"],
                native_provenance=context["provenance"]) from cause
        finally:
            self._running = False

    def _run(self, *, duration_s, maximum_step_s, start_time_s, clock_id, clock_tolerance_s, context):
        duration = finite(duration_s, "duration", positive=True)
        step = finite(maximum_step_s, "maximum native step", positive=True)
        start = finite(start_time_s, "absolute start")
        clock_tolerance = finite(clock_tolerance_s, "native clock tolerance", positive=True)
        if not isinstance(clock_id, str) or not clock_id.strip() or min(step, duration) < 1e-9:
            raise ValueError("Declare an absolute clock and native intervals of at least 1e-9 s")
        end = start+duration
        if (end <= start or start+min(step, duration) <= start
                or abs(((start+min(step, duration))-start)-min(step, duration)) > clock_tolerance
                or abs((end-start)-duration) > clock_tolerance):
            raise ValueError("Operation clock cannot resolve the requested duration")
        self._require_configuration()
        sides = (self.left, self.right)
        native_nodes = tuple(self.native_side_node_factory(s.side_id, s.native_component,
                             s.initial_native_state) for s in sides)
        context["nodes"] = native_nodes
        initial = HeatExchangerCompositeState(self.left.initial_native_state, self.right.initial_native_state)
        initial_inventories = {s.side_id: self._read(s, s.initial_native_state)[1] for s in sides}
        evaluations = {}
        clock_bounds = [start, start]
        last_trial = None
        evaluation_count = 0
        derivative_provenance = None

        def thermo(state):
            self._require_configuration()
            # Only a representative state is required by the port-free native
            # scheduling graph. Never expose it as the pair's hydraulic state.
            self._read(self.left, state.left)
            self._read(self.right, state.right)
            return native_nodes[0].thermo(state.left)

        def derivative(state, flows, local_time):
            nonlocal last_trial, evaluation_count, derivative_provenance
            evaluation_count += 1
            self._require_configuration()
            if tuple(flows):
                raise HeatExchangerCapabilityError("This closed two-fluid level rejects all material process ports")
            absolute = start+local_time
            if abs((absolute-start)-local_time) > clock_tolerance:
                raise ValueError("Absolute clock loses native exchanger elapsed time")
            if not start-clock_tolerance <= absolute <= end+clock_tolerance:
                raise ValueError("Native stage clock is outside the declared exchanger window")
            clock_bounds[0], clock_bounds[1] = min(clock_bounds[0], absolute), max(clock_bounds[1], absolute)
            last_trial = (absolute, state, None)
            context["trial"] = last_trial
            left_fluid, _ = self._read(self.left, state.left)
            right_fluid, _ = self._read(self.right, state.right)
            native_left = self.left.native_component.derivative_from_flows(
                state.left, (), ambient_temperature_K=state.right.wall_temperature_K)
            context["trial"] = (absolute, state, (native_left, None))
            native_right = self.right.native_component.derivative_from_flows(
                state.right, (), ambient_temperature_K=state.left.wall_temperature_K)
            if derivative_provenance is None:
                derivative_provenance = Lh2dtNativeProvenance.capture(native_left, native_right)
            else:
                derivative_provenance.require_current(check_files=False)
            combined = HeatExchangerCompositeDerivative(native_left, native_right)
            last_trial = (absolute, state, combined)
            context["trial"] = last_trial
            for side, native_derivative in zip(sides, (native_left, native_right), strict=True):
                for field in ("mass_kg_s", "internal_energy_W", "wall_temperature_K_s",
                              "mass_flow_in_kg_s", "mass_flow_out_kg_s", "inlet_enthalpy_flow_W",
                              "outlet_enthalpy_flow_W", "heat_from_wall_W", "heat_from_ambient_W"):
                    finite(getattr(native_derivative, field), f"native {side.side_id} {field}")
                if any(getattr(native_derivative, field) != 0. for field in (
                        "mass_kg_s", "mass_flow_in_kg_s", "mass_flow_out_kg_s",
                        "inlet_enthalpy_flow_W", "outlet_enthalpy_flow_W")):
                    raise HeatExchangerCapabilityError("A native sealed side introduced material transfer")
                residual = (native_derivative.internal_energy_W
                    +side.native_component.wall_heat_capacity*native_derivative.wall_temperature_K_s
                    -native_derivative.heat_from_ambient_W)
                if abs(residual) > self.heat_rate_tolerance_w:
                    raise HeatExchangerCapabilityError("Native fluid-plus-wall derivative does not close its heat boundary")
            if abs(combined.ambient_heat_W) > self.heat_rate_tolerance_w:
                raise HeatExchangerCapabilityError("The native wall-to-wall heat is not equal and opposite")
            evaluations[id(state)] = (state, absolute, left_fluid, right_fluid, combined)
            return combined

        def advance(state, rates, dt):
            return HeatExchangerCompositeState(
                native_nodes[0].advance(state.left, rates.left, dt),
                native_nodes[1].advance(state.right, rates.right, dt),
                state.left_integrated_heat_j+dt*rates.left.heat_from_ambient_W,
                state.right_integrated_heat_j+dt*rates.right.heat_from_ambient_W)

        def combine(k1, k2, k3, k4):
            return HeatExchangerCompositeDerivative(
                native_nodes[0].combine_derivatives(k1.left, k2.left, k3.left, k4.left),
                native_nodes[1].combine_derivatives(k1.right, k2.right, k3.right, k4.right))

        composite_node = replace(native_nodes[0], name=self.equipment_id, initial_state=initial,
            thermo=thermo, derivative=derivative, advance=advance, combine_derivatives=combine)
        network = self.native_network_factory(properties=self.left.bridge.native)
        context["network"] = network
        if network.properties is not self.left.bridge.native:
            raise HeatExchangerCapabilityError("Native scheduling network changed representative property ownership")
        network.add_boundary(self.equipment_id, thermo(initial))
        simulator = self.native_simulator_factory(network, {self.equipment_id: composite_node})
        context["simulator"] = simulator
        context["provenance"] = Lh2dtNativeProvenance.capture(network, simulator,
            *native_nodes, composite_node, *(s.native_component for s in sides))

        def point(state, time, native_step):
            entry = evaluations.get(id(state))
            if entry is None or entry[0] is not state:
                raise HeatExchangerCapabilityError("Native accepted composite state has no identical derivative evaluation")
            if abs(entry[1]-time) > clock_tolerance:
                raise HeatExchangerCapabilityError("Accepted native derivative and returned clocks differ")
            side_points = {}
            for side, native_state, fluid, rates, heat in zip(sides, (state.left, state.right),
                    entry[2:4], (entry[4].left, entry[4].right),
                    (state.left_integrated_heat_j, state.right_integrated_heat_j), strict=True):
                _, inventory = self._read(side, native_state)
                balance = InventoryBalance(initial_inventories[side.side_id], inventory,
                                           0., heat, 0., heat)
                violations = balance.violations(self.tolerances)
                if violations:
                    raise HeatExchangerCapabilityError(f"Side {side.side_id}: {'; '.join(violations)}")
                side_points[side.side_id] = HeatExchangerSideSnapshot(side.side_id, native_state, fluid,
                    rates, inventory, balance, rates.heat_from_ambient_W, rates.heat_from_wall_W)
            changes = sum(s.inventory.total_energy_j-initial_inventories[name].total_energy_j
                          for name, s in side_points.items())
            heat_sum = state.left_integrated_heat_j+state.right_integrated_heat_j
            if max(abs(changes), abs(heat_sum)) > max(self.tolerances.energy_absolute_j,
                    self.tolerances.relative*max(abs(state.left_integrated_heat_j), abs(state.right_integrated_heat_j))):
                raise HeatExchangerCapabilityError("Closed pair global energy or interwall heat does not close")
            return HeatExchangerPoint(time, side_points, changes, heat_sum, state, native_step)

        derivative(initial, (), 0.)
        initial_point = point(initial, start, None)
        points = context["points"]
        points.append(initial_point)
        rows = simulator.simulate(duration, min(step, duration))
        context["rows"] = rows
        if rows:
            context["provenance"] = Lh2dtNativeProvenance.capture(network, simulator,
                *native_nodes, composite_node, *(s.native_component for s in sides),
                *(s.initial_native_state for s in sides), rows[0],
                *(p.native_derivative for p in initial_point.sides.values()))
        previous = start
        for row in rows:
            absolute = start+row.time_s
            if (absolute <= previous or absolute-previous > step+clock_tolerance
                    or absolute > end+clock_tolerance
                    or abs((absolute-start)-row.time_s) > clock_tolerance):
                raise HeatExchangerCapabilityError("Native accepted exchanger clock/step changed")
            if (set(row.states) != {self.equipment_id} or row.network_solution.link_flows
                    or row.node_flows[self.equipment_id] or network.links or network.junctions
                    or set(network.boundaries) != {self.equipment_id}):
                raise HeatExchangerCapabilityError("A port or hydraulic junction entered the closed thermal pair")
            if not row.network_solution.pressure_solver_success:
                raise HeatExchangerCapabilityError("Native empty scheduling network reported failure")
            if (abs(row.cumulative_network_boundary_mass_kg) > self.tolerances.mass_absolute_kg
                    or abs(row.cumulative_network_boundary_energy_J) > self.tolerances.energy_absolute_j):
                raise HeatExchangerCapabilityError("Native closed-pair network ledger introduced an external boundary")
            points.append(point(row.states[self.equipment_id], absolute, row))
            previous = absolute
        if not rows or abs(previous-end) > clock_tolerance:
            raise HeatExchangerCapabilityError("Native coupled integration did not reach its declared time window")
        return HeatExchangerTrace(clock_id, start, end, self.coupling, tuple(points), simulator, network,
            native_nodes, composite_node, tuple(s.native_component for s in sides), tuple(clock_bounds),
            evaluation_count, self.tolerances, clock_tolerance_s=clock_tolerance)
