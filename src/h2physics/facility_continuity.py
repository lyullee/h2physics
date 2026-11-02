"""Steady facility-node continuity over original equipment transfers.

This module does not solve pressures, flows or equipment states.  It admits
already-produced :class:`ConnectionTransfer` objects and makes their material
and enthalpy ownership explicit at facility nodes.  Positive external rates are
into a node; positive storage rates increase the node inventory.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from math import fsum

from .core import PropertyBasis, ThermoState, finite
from .equipment import ConnectionTransfer, EquipmentTolerances


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    return value


@dataclass(frozen=True, slots=True)
class FacilityNode:
    node_id: str
    basis: PropertyBasis

    def __post_init__(self):
        _identity(self.node_id, "node_id")
        if not isinstance(self.basis, PropertyBasis):
            raise TypeError("A facility node requires a PropertyBasis")


@dataclass(frozen=True, slots=True)
class ExternalFacilityRate:
    """One declared material or non-material boundary at a facility node."""

    boundary_id: str
    node_id: str
    port_id: str
    mass_flow_into_node_kg_s: float
    transported_state: ThermoState | None = None
    heat_into_node_w: float = 0.0
    shaft_work_into_node_w: float = 0.0

    def __post_init__(self):
        for name in ("boundary_id", "node_id", "port_id"):
            _identity(getattr(self, name), name)
        finite(self.mass_flow_into_node_kg_s, "mass_flow_into_node_kg_s")
        finite(self.heat_into_node_w, "heat_into_node_w")
        finite(self.shaft_work_into_node_w, "shaft_work_into_node_w")
        if self.mass_flow_into_node_kg_s == 0.0:
            if self.transported_state is not None:
                raise ValueError("A zero material boundary cannot carry a state")
        elif not isinstance(self.transported_state, ThermoState):
            raise TypeError("A nonzero material boundary requires its transported state")

    @property
    def material_energy_into_node_w(self) -> float:
        if self.transported_state is None:
            return 0.0
        return self.mass_flow_into_node_kg_s * self.transported_state.enthalpy_j_kg

    @property
    def nonmaterial_energy_into_node_w(self) -> float:
        return self.heat_into_node_w + self.shaft_work_into_node_w


@dataclass(frozen=True, slots=True)
class FacilityStorageRate:
    node_id: str
    basis: PropertyBasis
    mass_accumulation_kg_s: float
    energy_accumulation_w: float

    def __post_init__(self):
        _identity(self.node_id, "node_id")
        if not isinstance(self.basis, PropertyBasis):
            raise TypeError("A storage rate requires a PropertyBasis")
        finite(self.mass_accumulation_kg_s, "mass_accumulation_kg_s")
        finite(self.energy_accumulation_w, "energy_accumulation_w")


@dataclass(frozen=True, slots=True)
class FacilityContinuityFrame:
    clock_id: str
    time_s: float
    transfers: tuple[ConnectionTransfer, ...]
    external_rates: tuple[ExternalFacilityRate, ...] = ()
    storage_rates: tuple[FacilityStorageRate, ...] = ()

    def __post_init__(self):
        _identity(self.clock_id, "clock_id")
        finite(self.time_s, "time_s")
        if any(not isinstance(row, ConnectionTransfer) for row in self.transfers):
            raise TypeError("transfers must contain original ConnectionTransfer objects")
        if any(not isinstance(row, ExternalFacilityRate) for row in self.external_rates):
            raise TypeError("external_rates contains an unsupported object")
        if any(not isinstance(row, FacilityStorageRate) for row in self.storage_rates):
            raise TypeError("storage_rates contains an unsupported object")


@dataclass(frozen=True, slots=True)
class NodeContinuity:
    node_id: str
    mass_accumulation_kg_s: float
    material_flow_into_node_kg_s: float
    energy_accumulation_w: float
    material_energy_into_node_w: float
    nonmaterial_energy_into_node_w: float

    @property
    def mass_residual_kg_s(self) -> float:
        return self.mass_accumulation_kg_s - self.material_flow_into_node_kg_s

    @property
    def energy_residual_w(self) -> float:
        return self.energy_accumulation_w - self.material_energy_into_node_w - self.nonmaterial_energy_into_node_w


@dataclass(frozen=True, slots=True)
class FacilityContinuityResult:
    clock_id: str
    time_s: float
    nodes: tuple[NodeContinuity, ...]
    component_energy_residual_w: tuple[tuple[str, float], ...]

    @property
    def mass_residual_kg_s(self) -> float:
        return fsum(row.mass_residual_kg_s for row in self.nodes)

    @property
    def node_energy_residual_w(self) -> float:
        return fsum(row.energy_residual_w for row in self.nodes)

    @property
    def equipment_energy_residual_w(self) -> float:
        return fsum(value for _, value in self.component_energy_residual_w)

    def violations(self, tolerances: EquipmentTolerances) -> tuple[str, ...]:
        if not isinstance(tolerances, EquipmentTolerances):
            raise TypeError("violations requires EquipmentTolerances")
        errors: list[str] = []
        for row in self.nodes:
            mass_limit = max(tolerances.mass_absolute_kg_s, tolerances.relative * max(
                abs(row.mass_accumulation_kg_s), abs(row.material_flow_into_node_kg_s)))
            energy_limit = tolerances.energy_limit_w(
                row.energy_accumulation_w, row.material_energy_into_node_w,
                row.nonmaterial_energy_into_node_w)
            if abs(row.mass_residual_kg_s) > mass_limit:
                errors.append(f"node {row.node_id} mass continuity does not close")
            if abs(row.energy_residual_w) > energy_limit:
                errors.append(f"node {row.node_id} energy continuity does not close")
        for component_id, residual in self.component_energy_residual_w:
            if abs(residual) > tolerances.energy_absolute_w:
                errors.append(f"component {component_id} enthalpy/power does not close")
        return tuple(errors)


class FacilityContinuityAudit:
    """Audit a fixed node/port topology without recalculating equipment physics."""

    def __init__(self, nodes: Iterable[FacilityNode], *, tolerances: EquipmentTolerances | None = None):
        admitted = tuple(nodes)
        if not admitted or any(not isinstance(row, FacilityNode) for row in admitted):
            raise ValueError("At least one explicit FacilityNode is required")
        ids = tuple(row.node_id for row in admitted)
        if len(set(ids)) != len(ids):
            raise ValueError("Facility node identities must be unique")
        self._nodes = admitted
        self._by_id = {row.node_id: row for row in admitted}
        self.tolerances = tolerances or EquipmentTolerances()

    @property
    def nodes(self) -> tuple[FacilityNode, ...]:
        return self._nodes

    def _require_state(self, node_id: str, state: ThermoState | None) -> None:
        if state is not None:
            self._by_id[node_id].basis.require_compatible(state.basis)

    def audit(self, frame: FacilityContinuityFrame, *, require_closed: bool = True) -> FacilityContinuityResult:
        if not isinstance(frame, FacilityContinuityFrame):
            raise TypeError("audit requires a FacilityContinuityFrame")
        mass = {node.node_id: [] for node in self._nodes}
        material_energy = {node.node_id: [] for node in self._nodes}
        nonmaterial_energy = {node.node_id: [] for node in self._nodes}
        storage: dict[str, FacilityStorageRate] = {}
        occupied_ports: set[tuple[str, str]] = set()
        component_residuals: list[tuple[str, float]] = []

        for transfer in frame.transfers:
            if transfer.left_node not in self._by_id or transfer.right_node not in self._by_id:
                raise ValueError("A transfer references a node outside this facility topology")
            ports = ((transfer.left_node, transfer.left_port_id),
                     (transfer.right_node, transfer.right_port_id))
            if any(port in occupied_ports for port in ports):
                raise ValueError("A facility port is occupied by more than one admitted boundary")
            occupied_ports.update(ports)
            self._require_state(transfer.upstream_node or transfer.left_node, transfer.upstream)
            self._require_state(transfer.downstream_node or transfer.right_node, transfer.transmitted)
            rate = transfer.mass_flow_kg_s
            mass[transfer.left_node].append(-rate)
            mass[transfer.right_node].append(rate)
            if rate > 0.0:
                material_energy[transfer.left_node].append(-transfer.inlet_enthalpy_flow_w)
                material_energy[transfer.right_node].append(transfer.outlet_enthalpy_flow_w)
            elif rate < 0.0:
                material_energy[transfer.right_node].append(-transfer.inlet_enthalpy_flow_w)
                material_energy[transfer.left_node].append(transfer.outlet_enthalpy_flow_w)
            component_residuals.append((transfer.component_id, transfer.energy_residual_w))

        for boundary in frame.external_rates:
            if boundary.node_id not in self._by_id:
                raise ValueError("An external boundary references an unknown facility node")
            port = (boundary.node_id, boundary.port_id)
            if port in occupied_ports:
                raise ValueError("A facility port is occupied by more than one admitted boundary")
            occupied_ports.add(port)
            self._require_state(boundary.node_id, boundary.transported_state)
            mass[boundary.node_id].append(boundary.mass_flow_into_node_kg_s)
            material_energy[boundary.node_id].append(boundary.material_energy_into_node_w)
            nonmaterial_energy[boundary.node_id].append(boundary.nonmaterial_energy_into_node_w)

        for rate in frame.storage_rates:
            if rate.node_id not in self._by_id or rate.node_id in storage:
                raise ValueError("Storage rates need one known, unique node identity")
            self._by_id[rate.node_id].basis.require_compatible(rate.basis)
            storage[rate.node_id] = rate

        rows = []
        for node in self._nodes:
            rate = storage.get(node.node_id)
            rows.append(NodeContinuity(
                node.node_id,
                0.0 if rate is None else rate.mass_accumulation_kg_s,
                fsum(mass[node.node_id]),
                0.0 if rate is None else rate.energy_accumulation_w,
                fsum(material_energy[node.node_id]),
                fsum(nonmaterial_energy[node.node_id]),
            ))
        result = FacilityContinuityResult(frame.clock_id, frame.time_s, tuple(rows),
                                          tuple(component_residuals))
        if require_closed:
            errors = result.violations(self.tolerances)
            if errors:
                raise ValueError("; ".join(errors))
        return result
