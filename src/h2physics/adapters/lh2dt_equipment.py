"""Native LH2DT network composition, shared valve and independently read power ledgers.

Primary interface: https://github.com/lyullee/lh2dt_models
The caller supplies installed native instances/factories; no native implementation
or external equipment parameter map is bundled in this adapter.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

from ..core import PropertyBasis, ThermoState, finite
from ..equipment import BoundaryPower, ConnectionTransfer, EquipmentTolerances
from ..release import HomogeneousIsentropicNozzle, NozzleOpening, NozzleResult
from .lh2dt import Lh2dtProperties, from_lh2dt_state, to_lh2dt_state


@dataclass(frozen=True)
class SharedValveEvaluation:
    native: Any
    nozzle: NozzleResult

    def __getattr__(self, name):
        return getattr(self.native, name)


class Lh2dtSharedValve:
    """Native two-port throttling interface using the one shared nozzle kernel.

    Both remote ports have negligible kinetic energy; the downstream mixed
    enthalpy equals upstream enthalpy. The nozzle-plane static/kinetic split
    remains a separate source result and is not a downstream pipe state.
    """

    def __init__(self, nozzle: HomogeneousIsentropicNozzle, bridge: Lh2dtProperties,
                 opening: NozzleOpening, *, result_factory: Callable[..., Any],
                 opening_fraction: float, allow_reverse: bool):
        nozzle.properties.basis.require_compatible(bridge.basis)
        if not isinstance(allow_reverse, bool):
            raise ValueError("allow_reverse must be bool")
        self.nozzle, self.bridge, self.opening = nozzle, bridge, opening
        self.result_factory = result_factory
        self.properties = bridge.native
        self.allow_reverse = allow_reverse
        self.set_opening(opening_fraction)

    def set_opening(self, value: float):
        self.opening.effective_area_m2(value)
        self.opening_fraction = float(value)

    def evaluate(self, left, right):
        forward = left.pressure_Pa >= right.pressure_Pa
        upstream, downstream = (left, right) if forward else (right, left)
        fraction = self.opening_fraction if forward or self.allow_reverse else 0.
        result = self.nozzle.solve(from_lh2dt_state(upstream, basis=self.bridge.basis),
            back_pressure_pa=downstream.pressure_Pa, opening=self.opening, opening_fraction=fraction)
        rate = result.mass_flow_kg_s * (1. if forward else -1.)
        native = self.result_factory(mass_flow_kg_s=rate,
            outlet_specific_enthalpy_J_kg=upstream.specific_enthalpy_J_kg,
            throat_pressure_Pa=(upstream.pressure_Pa if result.exit_state is None
                                else result.exit_state.pressure_pa),
            mass_flux_kg_m2_s=result.mass_flux_kg_m2_s, choked=result.regime == "choked",
            upstream_side=None if rate == 0 else ("left" if forward else "right"))
        return SharedValveEvaluation(native, result)

    def evaluate_mass_flow(self, left, right):
        return self.evaluate(left, right).mass_flow_kg_s


@dataclass(frozen=True, slots=True)
class EquipmentNetworkSnapshot:
    node_states: Mapping[str, ThermoState]
    transfers: tuple[ConnectionTransfer, ...]
    junction_mass_residuals_kg_s: Mapping[str, float]
    junction_energy_residuals_w: Mapping[str, float]
    boundary_inlet_kg_s: float
    boundary_outlet_kg_s: float
    boundary_inlet_enthalpy_w: float
    boundary_outlet_enthalpy_w: float
    native_success: bool
    native: Any = field(repr=False, compare=False)
    native_component_results: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self):
        for name in ("node_states", "junction_mass_residuals_kg_s", "junction_energy_residuals_w",
                     "native_component_results"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    @property
    def energy_residual_w(self):
        return (self.boundary_outlet_enthalpy_w - self.boundary_inlet_enthalpy_w
                - sum(item.power.total_w for item in self.transfers))

    @property
    def mass_residual_kg_s(self):
        return self.boundary_inlet_kg_s - self.boundary_outlet_kg_s

    @property
    def missing_momentum_components(self):
        return tuple(item.component_id for item in self.transfers if item.momentum_residual_pa is None)

    def violations(self, tolerances: EquipmentTolerances):
        errors = []
        if not self.native_success:
            errors.append("native network did not converge conservatively")
        mass_limit = max(tolerances.mass_absolute_kg_s,
                         tolerances.relative * max(self.boundary_inlet_kg_s, self.boundary_outlet_kg_s))
        if abs(self.mass_residual_kg_s) > mass_limit:
            errors.append("network boundary mass does not close")
        if abs(self.energy_residual_w) > tolerances.energy_limit_w(
                self.boundary_inlet_enthalpy_w, self.boundary_outlet_enthalpy_w,
                *(item.power.total_w for item in self.transfers)):
            errors.append("network boundary enthalpy/power does not close")
        for name, residual in self.junction_mass_residuals_kg_s.items():
            incident = [item for item in self.transfers if name in (item.left_node, item.right_node)]
            local_limit = max(tolerances.mass_absolute_kg_s,
                              tolerances.relative * sum(abs(item.mass_flow_kg_s) for item in incident))
            if abs(residual) > local_limit:
                errors.append(f"junction {name} mass does not close")
        for name, residual in self.junction_energy_residuals_w.items():
            incident = [item for item in self.transfers if name in (item.left_node, item.right_node)]
            if abs(residual) > tolerances.energy_limit_w(
                    *(value for item in incident for value in (
                        item.inlet_enthalpy_flow_w, item.outlet_enthalpy_flow_w))):
                errors.append(f"junction {name} energy does not close")
        for item in self.transfers:
            if abs(item.energy_residual_w) > tolerances.energy_limit_w(
                    item.inlet_enthalpy_flow_w, item.outlet_enthalpy_flow_w, item.power.total_w):
                errors.append(f"component {item.component_id} enthalpy/power does not close")
            if item.momentum_residual_pa is not None and abs(item.momentum_residual_pa) > tolerances.momentum_absolute_pa:
                errors.append(f"component {item.component_id} reported momentum does not close")
            if item.operating_point_admissible is False:
                errors.append(f"component {item.component_id} reports an inadmissible operating point")
        return tuple(errors)


class EquipmentClosureError(RuntimeError):
    def __init__(self, snapshot, errors):
        self.snapshot = snapshot
        super().__init__("; ".join(errors))


class Lh2dtEquipmentNetwork:
    """Build/solve the native graph and expose independently recomputed balances."""

    def __init__(self, network, bridge: Lh2dtProperties, *, state_factory: Callable[..., Any],
                 tolerances: EquipmentTolerances | None = None):
        if network.properties is not bridge.native:
            raise ValueError("Native graph and adapter must share the same property instance")
        self.native, self.bridge, self.state_factory = network, bridge, state_factory
        self.tolerances = tolerances or EquipmentTolerances()
        self._power_readers: dict[str, Callable[[Any], BoundaryPower]] = {}

    def _state(self, value):
        return to_lh2dt_state(value, expected_basis=self.bridge.basis, factory=self.state_factory)

    def add_boundary(self, name: str, state: ThermoState):
        self.native.add_boundary(name, self._state(state))

    def add_junction(self, name: str, initial: ThermoState):
        self.bridge.basis.require_compatible(initial.basis)
        self.native.add_junction(name, initial.pressure_pa, initial.enthalpy_j_kg)

    def add_link(self, name: str, left: str, right: str, component, *,
                 power_reader: Callable[[Any], BoundaryPower], source_port_id: str,
                 target_port_id: str, declared_basis: PropertyBasis | None = None):
        native_properties = getattr(component, "properties", None)
        fluid = getattr(native_properties, "fluid", None)
        if fluid is not None and fluid != self.bridge.basis.fluid:
            raise ValueError("A declared basis cannot override a contradictory native fluid identity")
        if native_properties is not self.bridge.native:
            if declared_basis is None:
                raise ValueError("A component without the shared provider needs an explicit compatible basis")
            self.bridge.basis.require_compatible(declared_basis)
        self.native.add_link(name, left, right, component,
                             source_port_id=source_port_id, target_port_id=target_port_id)
        self._power_readers[name] = power_reader

    def solve(self, *, require_closed: bool = True, **native_options):
        solution = self.native.solve(**native_options)
        return self.snapshot(solution, require_closed=require_closed)

    def checked_native(self, *, on_solve: Callable[[EquipmentNetworkSnapshot], None] | None = None):
        """Structural native graph view validating every solve, including RK stages."""
        return _CheckedNativeNetwork(self, on_solve)

    def snapshot(self, solution, *, require_closed: bool = True):
        states = {name: from_lh2dt_state(value, basis=self.bridge.basis)
                  for name, value in solution.node_states.items()}
        transfers, raw_results = [], {}
        incoming = outgoing = inlet_energy = outlet_energy = 0.
        junction_mass = dict.fromkeys(self.native.junctions, 0.)
        junction_energy = dict.fromkeys(self.native.junctions, 0.)
        for link in self.native.links:
            if link.name not in self._power_readers:
                raise ValueError("Every native link must have an explicit power reader")
            solved = solution.link_flows[link.name]
            raw = link.component.evaluate(solution.node_states[link.left], solution.node_states[link.right])
            raw_results[link.name] = raw
            rate = finite(raw.mass_flow_kg_s, "native mass flow")
            enthalpy = finite(raw.outlet_specific_enthalpy_J_kg, "native outlet enthalpy")
            if (abs(rate-solved.mass_flow_kg_s) > max(1e-12, 1e-8*abs(rate))
                    or abs(enthalpy-solved.transmitted_specific_enthalpy_J_kg) > max(1e-6, 1e-8*abs(enthalpy))):
                raise ValueError("Component changed between native solve and ledger evaluation")
            power = self._power_readers[link.name](raw)
            if not isinstance(power, BoundaryPower):
                raise ValueError("A power reader must return BoundaryPower")
            upstream_name, downstream_name = ((link.left, link.right) if rate > 0 else (link.right, link.left))
            upstream = None if rate == 0 else states[upstream_name]
            transmitted = (None if rate == 0 else self.bridge.state_ph(
                states[downstream_name].pressure_pa, enthalpy))
            item = ConnectionTransfer(link.name, link.left, link.right, link.source_port_id,
                link.target_port_id, rate, upstream, transmitted, power,
                getattr(raw, "momentum_residual_Pa", None),
                getattr(raw, "operating_point_physical_valid", None))
            transfers.append(item)
            if rate == 0:
                continue
            magnitude = abs(rate)
            if upstream_name in self.native.boundaries:
                incoming += magnitude
                inlet_energy += item.inlet_enthalpy_flow_w
            else:
                junction_mass[upstream_name] -= magnitude
                junction_energy[upstream_name] -= item.inlet_enthalpy_flow_w
            if downstream_name in self.native.boundaries:
                outgoing += magnitude
                outlet_energy += item.outlet_enthalpy_flow_w
            else:
                junction_mass[downstream_name] += magnitude
                junction_energy[downstream_name] += item.outlet_enthalpy_flow_w
        snapshot = EquipmentNetworkSnapshot(states, tuple(transfers), junction_mass, junction_energy,
            incoming, outgoing, inlet_energy, outlet_energy, bool(solution.pressure_solver_success), solution,
            native_component_results=raw_results)
        errors = snapshot.violations(self.tolerances)
        if require_closed and errors:
            raise EquipmentClosureError(snapshot, errors)
        return snapshot


class _CheckedNativeNetwork:
    def __init__(self, adapter, on_solve):
        self.adapter = adapter
        self.on_solve = on_solve

    def solve(self, **options):
        snapshot = self.adapter.solve(require_closed=True, **options)
        if self.on_solve is not None:
            self.on_solve(snapshot)
        return snapshot.native

    def __getattr__(self, name):
        return getattr(self.adapter.native, name)


@dataclass(frozen=True)
class _StratifiedHeatDerivative:
    native: Any

    @property
    def ambient_heat_W(self):
        return self.native.lower_ambient_heat_W + self.native.upper_ambient_heat_W

    def __getattr__(self, name):
        return getattr(self.native, name)


def stratified_node_with_heat_ledger(native_node):
    """Keep native phase equations while exposing both external wall heat terms.

    The reviewed generic simulator reads ambient_heat_W, while the stratified
    derivative exposes two separate terms. This explicit bridge only supplies
    their sum to the ledger; it changes no tank derivative or integrator.
    """
    derivative = native_node.derivative

    def evaluate(state, flows, time_s):
        return _StratifiedHeatDerivative(derivative(state, flows, time_s))

    return replace(native_node, derivative=evaluate)
