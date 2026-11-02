"""A reusable native liquid-port tank/pump/stored-line/vaporizer assembly.

Callers construct native models with their own geometry, maps, coefficients
and initial states. This function wires them without duplicating their physics.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..core import ThermoState
from ..equipment import BoundaryPower
from .lh2dt import Lh2dtProperties, from_lh2dt_state
from .lh2dt_dynamics import (
    Lh2dtDynamicEquipment,
    Lh2dtInventoryNode,
    lumped_inventory_reader,
    stratified_inventory_reader,
)
from .lh2dt_equipment import Lh2dtEquipmentNetwork, stratified_node_with_heat_ledger
from .lh2dt_modes import Lh2dtEquipmentMode, Lh2dtModeSwitch


@dataclass(frozen=True, slots=True)
class Lh2dtSupplyAssembly:
    network: Lh2dtEquipmentNetwork
    driver: Lh2dtDynamicEquipment
    pump: Lh2dtModeSwitch
    outlet: Any
    node_ids: Mapping[str, str]
    native_models: Mapping[str, Any]

    def __post_init__(self):
        for field in ("node_ids", "native_models"):
            object.__setattr__(self, field, MappingProxyType(dict(getattr(self, field))))


def assemble_lh2dt_supply(bridge: Lh2dtProperties, *, native_api: Any,
        state_factory: Callable[..., Any], tank: Any, initial_tank: Any,
        line: Any, initial_line: Any, vaporizer: Any, initial_vaporizer: Any,
        pump: Any, isolated_pump_component: Any, restriction: Any, outlet: Any,
        delivery_state: ThermoState,
        power_readers: Mapping[str, Callable[[Any], BoundaryPower]],
        tank_ambient_temperature_k: float | Callable[[float], float],
        node_ids: Mapping[str, str] | None = None) -> Lh2dtSupplyAssembly:
    """Build one explicit liquid-port topology from injected native instances.

    Required power-reader keys are running_pump, isolated_pump, restriction,
    outlet. The isolated branch is caller-selected and is not a rotor model.
    For arbitrary topologies use Lh2dtEquipmentNetwork directly.
    """
    ids = dict(node_ids if node_ids is not None else
               {"tank": "supply", "line": "line", "vaporizer": "vaporizer", "delivery": "delivery"})
    if (set(ids) != {"tank", "line", "vaporizer", "delivery"}
            or len(set(ids.values())) != 4 or any(not name.strip() for name in ids.values())):
        raise ValueError("Supply node identities require four distinct tank/line/vaporizer/delivery names")
    if set(power_readers) != {"running_pump", "isolated_pump", "restriction", "outlet"}:
        raise ValueError("Every supply branch requires its explicit power reader")
    if any(not callable(reader) for reader in power_readers.values()):
        raise TypeError("Supply power readers must be Python callables")
    bridge.basis.require_compatible(delivery_state.basis)
    for model in (tank, line, vaporizer, pump, isolated_pump_component, restriction, outlet):
        if getattr(model, "properties", None) is not bridge.native:
            raise ValueError("All supplied native devices must share the declared property instance")
    network = Lh2dtEquipmentNetwork(native_api.SteadyNetwork(bridge.native), bridge,
                                     state_factory=state_factory)
    parameters = tank.parameters
    tank_node = stratified_node_with_heat_ledger(native_api.stratified_tank_node(
        ids["tank"], tank, initial_tank, ambient_temperature_K=tank_ambient_temperature_k,
        boundary_phase="liquid"))
    nodes = {
        ids["tank"]: Lh2dtInventoryNode(tank_node, stratified_inventory_reader(
            parameters.lower_wall_heat_capacity_J_K, parameters.upper_wall_heat_capacity_J_K, bridge.basis)),
        ids["line"]: Lh2dtInventoryNode(native_api.dynamic_hem_pipe_node(ids["line"], line, initial_line),
            lumped_inventory_reader(line.wall_heat_capacity, bridge.basis)),
        ids["vaporizer"]: Lh2dtInventoryNode(native_api.dynamic_vaporizer_node(
            ids["vaporizer"], vaporizer, initial_vaporizer),
            lumped_inventory_reader(vaporizer.wall_heat_capacity, bridge.basis)),
    }
    for name, node in nodes.items():
        network.add_boundary(name, from_lh2dt_state(node.native_node.thermo(node.native_node.initial_state),
                                                  basis=bridge.basis))
    network.add_boundary(ids["delivery"], delivery_state)
    selected_pump = Lh2dtModeSwitch(bridge, {
        "running": Lh2dtEquipmentMode(pump, power_readers["running_pump"]),
        "isolated": Lh2dtEquipmentMode(isolated_pump_component, power_readers["isolated_pump"]),
    }, mode_id="running")
    network.add_link("pump-assembly", ids["tank"], ids["line"], selected_pump,
        power_reader=lambda result: result.boundary_power,
        source_port_id=ids["tank"]+"/liquid", target_port_id=ids["line"]+"/in")
    network.add_link("restriction", ids["line"], ids["vaporizer"], restriction,
        power_reader=power_readers["restriction"], source_port_id=ids["line"]+"/out",
        target_port_id=ids["vaporizer"]+"/in")
    network.add_link("outlet-valve", ids["vaporizer"], ids["delivery"], outlet,
        power_reader=power_readers["outlet"], source_port_id=ids["vaporizer"]+"/out",
        target_port_id=ids["delivery"]+"/in")
    driver = Lh2dtDynamicEquipment(network, nodes, simulator_factory=native_api.DynamicNetworkSimulator)
    return Lh2dtSupplyAssembly(network, driver, selected_pump, outlet, ids,
        {"tank": tank, "line": line, "vaporizer": vaporizer, "running_pump": pump,
         "isolated_pump": isolated_pump_component, "restriction": restriction, "outlet": outlet})
