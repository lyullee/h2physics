"""Branched 1-D isothermal-Euler pipe network with conservative junctions.

Each pipe is a finite-volume segment. Internal nodes enforce a shared pressure
and zero summed outward Rusanov mass flux; terminal wall nodes are impermeable.
The junction pressure is a bounded scalar solve on caller-declared limits.
Prescribed-pressure terminal histories impose a pipe boundary state but do not
evolve source-reservoir inventory; exchange ledgers describe the pipe side only.
Distinct finite-inventory terminals evolve from the same endpoint Rusanov flux
and contribute their mass to the combined network balance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

import numpy as np

from .core import Origin, finite, immutable_array
from .finite_pipe_reservoir import FiniteIsothermalPipeReservoir
from .pipe_reservoir_boundary import FiniteReservoirPressureBoundary
from .pipe_nozzle_coupling import FiniteReservoirNozzleCoupling
from .release import NozzleSourceProjection, SourceHistory
from .thermo.isothermal_eos import IsothermalSinglePhaseEOS


@dataclass(frozen=True, slots=True)
class IsothermalPipeNetworkNode:
    identifier: str
    coordinates_m: tuple[float, float, float]
    kind: str
    state_owner_id: str
    evidence_id: str
    origin: Origin = Origin.UNRESOLVED
    pressure_bounds_pa: tuple[float, float] | None = None

    def __post_init__(self):
        for name in ("identifier", "state_owner_id", "evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare node {name}")
        if self.kind not in ("junction", "closed", "reservoir", "finite_reservoir"):
            raise ValueError("Node kind must be junction, closed, reservoir, or finite_reservoir")
        xyz = tuple(finite(value, f"node {self.identifier} coordinate")
                    for value in self.coordinates_m)
        if len(xyz) != 3:
            raise ValueError("Node coordinates must contain x, y, z")
        object.__setattr__(self, "coordinates_m", xyz)
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Node geometry/state origin must be explicit")
        object.__setattr__(self, "origin", origin)
        if self.kind == "junction":
            if self.pressure_bounds_pa is None or len(self.pressure_bounds_pa) != 2:
                raise ValueError("Every junction requires caller-declared pressure bounds")
            lower = finite(self.pressure_bounds_pa[0], "junction lower pressure", positive=True)
            upper = finite(self.pressure_bounds_pa[1], "junction upper pressure", positive=True)
            if lower >= upper:
                raise ValueError("Junction pressure bounds must increase strictly")
            object.__setattr__(self, "pressure_bounds_pa", (lower, upper))
        elif self.pressure_bounds_pa is not None:
            raise ValueError("Terminal wall/reservoir nodes cannot declare a junction pressure bracket")


@dataclass(frozen=True, slots=True)
class IsothermalPipeNetworkEdge:
    identifier: str
    start_node_id: str
    end_node_id: str
    length_m: float
    internal_diameter_m: float
    cell_count: int
    geometry_owner_id: str
    geometry_evidence_id: str
    darcy_friction_factor: float = 0.0
    origin: Origin = Origin.UNRESOLVED

    def __post_init__(self):
        for name in ("identifier", "start_node_id", "end_node_id",
                     "geometry_owner_id", "geometry_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare edge {name}")
        if self.start_node_id == self.end_node_id:
            raise ValueError("A pipe segment must connect distinct nodes")
        finite(self.length_m, "edge length", positive=True)
        finite(self.internal_diameter_m, "edge internal diameter", positive=True)
        friction = finite(self.darcy_friction_factor, "Darcy friction factor")
        if friction < 0.:
            raise ValueError("Darcy friction factor cannot be negative")
        if isinstance(self.cell_count, bool) or not isinstance(self.cell_count, int) or self.cell_count < 2:
            raise ValueError("Each pipe edge requires at least two finite-volume cells")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Pipe geometry origin must be explicit")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class IsothermalPipeNetworkTrace:
    """Sampled network state and pipe-side boundary mass-exchange ledgers."""

    time_s: np.ndarray = field(repr=False, compare=False)
    edge_pressure_pa: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    edge_velocity_m_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    edge_face_mass_flow_kg_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_pressure_pa: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_mass_residual_kg_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    total_mass_kg: np.ndarray = field(repr=False, compare=False)
    global_mass_balance_residual_kg: np.ndarray = field(repr=False, compare=False)
    clock_id: str
    eos_identity: str
    temperature_k: float
    node_state_owner_ids: Mapping[str, str]
    node_evidence_ids: Mapping[str, str]
    edge_geometry_owner_ids: Mapping[str, str]
    edge_geometry_evidence_ids: Mapping[str, str]
    reservoir_pressure_pa: Mapping[str, np.ndarray] = field(default_factory=dict, repr=False, compare=False)
    boundary_mass_in_kg: np.ndarray | None = field(default=None, repr=False, compare=False)
    boundary_mass_out_kg: np.ndarray | None = field(default=None, repr=False, compare=False)
    reservoir_ids: Mapping[str, str] = field(default_factory=dict)
    reservoir_state_owner_ids: Mapping[str, str] = field(default_factory=dict)
    reservoir_evidence_ids: Mapping[str, str] = field(default_factory=dict)
    reservoir_clock_ids: Mapping[str, str] = field(default_factory=dict)
    reservoir_origins: Mapping[str, Origin] = field(default_factory=dict)
    finite_inventory_mass_kg: Mapping[str, np.ndarray] = field(default_factory=dict, repr=False, compare=False)
    finite_inventory_pressure_pa: Mapping[str, np.ndarray] = field(default_factory=dict, repr=False, compare=False)
    finite_inventory_ids: Mapping[str, str] = field(default_factory=dict)
    finite_inventory_state_owner_ids: Mapping[str, str] = field(default_factory=dict)
    finite_inventory_evidence_ids: Mapping[str, str] = field(default_factory=dict)
    finite_inventory_clock_ids: Mapping[str, str] = field(default_factory=dict)
    finite_inventory_origins: Mapping[str, Origin] = field(default_factory=dict)
    finite_reservoir_nozzle_history: Mapping[str, SourceHistory] = field(default_factory=dict, repr=False, compare=False)
    finite_reservoir_nozzle_coupling_ids: Mapping[str, str] = field(default_factory=dict)
    finite_reservoir_nozzle_evidence_ids: Mapping[str, str] = field(default_factory=dict)
    finite_reservoir_nozzle_mass_out_kg: Mapping[str, np.ndarray] = field(default_factory=dict, repr=False, compare=False)

    def project_nozzle_source(self, node_id: str, *, representative_state,
                              quadrature_evidence_id: str,
                              state_projection_evidence_id: str) -> NozzleSourceProjection:
        """Project one debited leak history with exact left-hold mass closure."""
        if node_id not in self.finite_reservoir_nozzle_history:
            raise KeyError(f"No debited nozzle history is retained for node {node_id!r}")
        history = self.finite_reservoir_nozzle_history[node_id]
        projection = history.interval_mass_projection(
            representative_state=representative_state, flow_rule="left_hold",
            quadrature_evidence_id=quadrature_evidence_id,
            state_projection_evidence_id=state_projection_evidence_id,
        )
        debited = float(self.finite_reservoir_nozzle_mass_out_kg[node_id][-1])
        projected = float(np.sum(projection.interval_mass_kg))
        if not np.isclose(projected, debited, rtol=2e-11, atol=2e-12):
            raise ValueError("Left-hold nozzle source mass does not close against debited reservoir inventory")
        return projection

    def __post_init__(self):
        time = immutable_array(self.time_s, dtype=float, name="network time_s")
        if time.ndim != 1 or len(time) < 2 or not np.all(np.isfinite(time)) or np.any(np.diff(time) <= 0.):
            raise ValueError("Network trace times must increase strictly")
        def arrays(source, label):
            result = {}
            for key, value in source.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(f"{label} keys must be nonempty IDs")
                array = immutable_array(value, dtype=float, name=f"{label}[{key}]")
                if array.ndim < 1 or not np.all(np.isfinite(array)):
                    raise ValueError(f"{label} values must be finite")
                result[key] = array
            return MappingProxyType(result)
        pressure = arrays(self.edge_pressure_pa, "edge_pressure_pa")
        velocity = arrays(self.edge_velocity_m_s, "edge_velocity_m_s")
        flow = arrays(self.edge_face_mass_flow_kg_s, "edge_face_mass_flow_kg_s")
        junction_pressure = arrays(self.junction_pressure_pa, "junction_pressure_pa")
        junction_residual = arrays(self.junction_mass_residual_kg_s, "junction_mass_residual_kg_s")
        reservoir_pressure = arrays(self.reservoir_pressure_pa, "reservoir_pressure_pa")
        finite_mass = arrays(self.finite_inventory_mass_kg, "finite_inventory_mass_kg")
        finite_pressure = arrays(self.finite_inventory_pressure_pa, "finite_inventory_pressure_pa")
        nozzle_mass_out = arrays(self.finite_reservoir_nozzle_mass_out_kg,
                                 "finite_reservoir_nozzle_mass_out_kg")
        if (set(pressure) != set(velocity) or set(pressure) != set(flow)
                or set(junction_pressure) != set(junction_residual)):
            raise ValueError("Network trace edge and junction maps must have matching IDs")
        if any(value.shape[0] != len(time) for mapping in
               (pressure, velocity, flow, junction_pressure, junction_residual, reservoir_pressure,
                finite_mass, finite_pressure, nozzle_mass_out)
               for value in mapping.values()):
            raise ValueError("Network trace arrays must begin with the requested time axis")
        if (any(pressure[key].ndim != 2 or velocity[key].shape != pressure[key].shape
                or flow[key].ndim != 2 or flow[key].shape[1] != pressure[key].shape[1]+1
                for key in pressure)
                or any(value.ndim != 1 for mapping in (junction_pressure, junction_residual)
                       for value in mapping.values())
                or any(value.ndim != 1 for value in reservoir_pressure.values())
                or any(value.ndim != 1 for mapping in (finite_mass, finite_pressure)
                       for value in mapping.values())
                or any(value.ndim != 1 or np.any(value < 0.)
                       or np.any(np.diff(value) < -1e-12)
                       for value in nozzle_mass_out.values())
                or any(np.any(value <= 0.) for mapping in (pressure, junction_pressure)
                       for value in mapping.values())
                or any(np.any(value <= 0.) for value in reservoir_pressure.values())
                or any(np.any(value <= 0.) for mapping in (finite_mass, finite_pressure)
                       for value in mapping.values())):
            raise ValueError("Network edge and node trace arrays have invalid ranks or cell/face counts")
        total = immutable_array(self.total_mass_kg, dtype=float, name="total_mass_kg")
        residual = immutable_array(self.global_mass_balance_residual_kg, dtype=float,
                                   name="global_mass_balance_residual_kg")
        if (total.shape != time.shape or residual.shape != time.shape
                or not np.all(np.isfinite(total)) or not np.all(np.isfinite(residual))
                or np.any(total <= 0.)):
            raise ValueError("Network mass traces must be positive and match the time axis")
        mass_in = immutable_array(
            np.zeros(len(time)) if self.boundary_mass_in_kg is None else self.boundary_mass_in_kg,
            dtype=float, name="boundary_mass_in_kg",
        )
        mass_out = immutable_array(
            np.zeros(len(time)) if self.boundary_mass_out_kg is None else self.boundary_mass_out_kg,
            dtype=float, name="boundary_mass_out_kg",
        )
        if (mass_in.shape != time.shape or mass_out.shape != time.shape
                or not np.all(np.isfinite(mass_in)) or not np.all(np.isfinite(mass_out))
                or np.any(mass_in < 0.) or np.any(mass_out < 0.)
                or np.any(np.diff(mass_in) < -1e-12) or np.any(np.diff(mass_out) < -1e-12)):
            raise ValueError("Boundary exchange ledgers must be finite, nonnegative, and cumulative")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Network trace must retain its caller clock identity")
        if not isinstance(self.eos_identity, str) or not self.eos_identity.strip():
            raise ValueError("Network trace must retain its EOS identity")
        for name in ("node_state_owner_ids", "node_evidence_ids",
                     "edge_geometry_owner_ids", "edge_geometry_evidence_ids",
                     "reservoir_ids", "reservoir_state_owner_ids",
                     "reservoir_evidence_ids", "reservoir_clock_ids", "reservoir_origins"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        for name in ("finite_inventory_ids", "finite_inventory_state_owner_ids",
                     "finite_inventory_evidence_ids", "finite_inventory_clock_ids",
                     "finite_inventory_origins"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        object.__setattr__(self, "finite_reservoir_nozzle_history", MappingProxyType(histories))
        for name in ("finite_reservoir_nozzle_coupling_ids", "finite_reservoir_nozzle_evidence_ids"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        if (set(self.node_state_owner_ids) != set(self.node_evidence_ids)
                or set(self.edge_geometry_owner_ids) != set(self.edge_geometry_evidence_ids)
                or set(self.edge_geometry_owner_ids) != set(pressure)):
            raise ValueError("Network provenance maps must retain matching node and edge identities")
        reservoir_keys = set(reservoir_pressure)
        if (set(self.reservoir_ids) != reservoir_keys
                or set(self.reservoir_state_owner_ids) != reservoir_keys
                or set(self.reservoir_evidence_ids) != reservoir_keys
                or set(self.reservoir_clock_ids) != reservoir_keys
                or set(self.reservoir_origins) != reservoir_keys):
            raise ValueError("Reservoir pressure histories must retain ID, owner, evidence, clock and origin")
        finite_keys = set(finite_mass)
        if (set(finite_pressure) != finite_keys
                or set(self.finite_inventory_ids) != finite_keys
                or set(self.finite_inventory_state_owner_ids) != finite_keys
                or set(self.finite_inventory_evidence_ids) != finite_keys
                or set(self.finite_inventory_clock_ids) != finite_keys
                or set(self.finite_inventory_origins) != finite_keys):
            raise ValueError("Finite inventory histories must retain matching mass/pressure and provenance maps")
        nozzle_keys = set(nozzle_mass_out)
        histories = dict(self.finite_reservoir_nozzle_history)
        if (set(histories) != nozzle_keys
                or set(self.finite_reservoir_nozzle_coupling_ids) != nozzle_keys
                or set(self.finite_reservoir_nozzle_evidence_ids) != nozzle_keys
                or not nozzle_keys <= finite_keys
                or any(type(value) is not SourceHistory for value in histories.values())):
            raise ValueError("Nozzle histories, sink ledgers and coupling provenance must align")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "edge_pressure_pa", pressure)
        object.__setattr__(self, "edge_velocity_m_s", velocity)
        object.__setattr__(self, "edge_face_mass_flow_kg_s", flow)
        object.__setattr__(self, "junction_pressure_pa", junction_pressure)
        object.__setattr__(self, "junction_mass_residual_kg_s", junction_residual)
        object.__setattr__(self, "reservoir_pressure_pa", reservoir_pressure)
        object.__setattr__(self, "finite_inventory_mass_kg", finite_mass)
        object.__setattr__(self, "finite_inventory_pressure_pa", finite_pressure)
        object.__setattr__(self, "finite_reservoir_nozzle_mass_out_kg", nozzle_mass_out)
        object.__setattr__(self, "boundary_mass_in_kg", mass_in)
        object.__setattr__(self, "boundary_mass_out_kg", mass_out)
        object.__setattr__(self, "total_mass_kg", total)
        object.__setattr__(self, "global_mass_balance_residual_kg", residual)
        object.__setattr__(self, "temperature_k", finite(self.temperature_k, "temperature K", positive=True))


@dataclass(frozen=True, slots=True)
class IsothermalPipeNetworkWaveModel:
    nodes: tuple[IsothermalPipeNetworkNode, ...]
    edges: tuple[IsothermalPipeNetworkEdge, ...]
    temperature_k: float
    clock_id: str
    eos: IsothermalSinglePhaseEOS = field(repr=False, compare=False)
    maximum_cfl: float = 0.35
    maximum_internal_steps: int = 2_000_000

    def __post_init__(self):
        nodes, edges = tuple(self.nodes), tuple(self.edges)
        if len(nodes) < 2 or not edges:
            raise ValueError("A pipeline network requires at least two nodes and one edge")
        node_by_id = {node.identifier: node for node in nodes}
        if len(node_by_id) != len(nodes):
            raise ValueError("Network node IDs must be unique")
        if len({edge.identifier for edge in edges}) != len(edges):
            raise ValueError("Network edge IDs must be unique")
        adjacency = {identifier: [] for identifier in node_by_id}
        elevations = {node.coordinates_m[2] for node in nodes}
        if len(elevations) != 1:
            raise ValueError("This network model is horizontal; gravity/elevation changes are unsupported")
        for edge in edges:
            if edge.start_node_id not in node_by_id or edge.end_node_id not in node_by_id:
                raise ValueError("Every edge endpoint must name a declared node")
            start = np.asarray(node_by_id[edge.start_node_id].coordinates_m)
            end = np.asarray(node_by_id[edge.end_node_id].coordinates_m)
            if edge.length_m + 1e-12 < float(np.linalg.norm(end - start)):
                raise ValueError("Pipe length cannot be shorter than endpoint separation")
            adjacency[edge.start_node_id].append((edge, 1))
            adjacency[edge.end_node_id].append((edge, -1))
        for identifier, ports in adjacency.items():
            kind = node_by_id[identifier].kind
            if kind == "junction" and len(ports) < 3:
                raise ValueError("A branched pressure junction must connect at least three pipe edges")
            if kind == "closed" and len(ports) != 1:
                raise ValueError("A closed wall node must terminate exactly one pipe edge")
            if kind == "reservoir" and len(ports) != 1:
                raise ValueError("A prescribed-pressure reservoir node must terminate exactly one pipe edge")
            if kind == "finite_reservoir" and len(ports) != 1:
                raise ValueError("A finite-inventory reservoir node must terminate exactly one pipe edge")
        reached = set()
        stack = [next(iter(node_by_id))]
        while stack:
            identifier = stack.pop()
            if identifier in reached:
                continue
            reached.add(identifier)
            for edge, _ in adjacency[identifier]:
                other = edge.end_node_id if edge.start_node_id == identifier else edge.start_node_id
                stack.append(other)
        if reached != set(node_by_id):
            raise ValueError("All pipe edges must belong to one connected network")
        for method in ("density_pt", "pressure_rho_t", "isothermal_sound_speed_rho_t"):
            if not callable(getattr(self.eos, method, None)):
                raise TypeError(f"EOS must implement {method}")
        identity = getattr(self.eos, "identity", None)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("EOS must expose a stable nonempty identity")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Declare the network clock identity")
        finite(self.temperature_k, "network temperature K", positive=True)
        if finite(self.maximum_cfl, "maximum_cfl", positive=True) > 0.5:
            raise ValueError("maximum_cfl cannot exceed 0.5")
        if (isinstance(self.maximum_internal_steps, bool)
                or not isinstance(self.maximum_internal_steps, int)
                or self.maximum_internal_steps < 1):
            raise ValueError("maximum_internal_steps must be a positive integer")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)

    def simulate(self, *, initial_pressure_pa: Mapping[str, Sequence[float]],
                 initial_velocity_m_s: Mapping[str, Sequence[float]],
                 time_samples_s: Sequence[float],
                 reservoir_boundaries: Mapping[str, FiniteReservoirPressureBoundary] | None = None,
                 finite_reservoirs: Mapping[str, FiniteIsothermalPipeReservoir] | None = None,
                 finite_reservoir_nozzles: Mapping[str, FiniteReservoirNozzleCoupling] | None = None
                 ) -> IsothermalPipeNetworkTrace:
        """Advance pipe waves with prescribed-pressure and finite-inventory terminals.

        Prescribed-pressure exchange is accounted on the pipe side only. A
        finite inventory endpoint evolves from the exact same Rusanov flux as
        its adjacent pipe update and joins the combined network mass trace.
        """
        times = np.asarray(tuple(time_samples_s), dtype=float)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or times[0] != 0. or np.any(np.diff(times) <= 0.)):
            raise ValueError("time_samples_s must start at zero and increase strictly")
        edge_ids = {edge.identifier for edge in self.edges}
        if set(initial_pressure_pa) != edge_ids or set(initial_velocity_m_s) != edge_ids:
            raise ValueError("Initial pressure and velocity maps must cover every edge exactly")
        temperature = finite(self.temperature_k, "network temperature K", positive=True)
        reservoir_nodes = {node.identifier: node for node in self.nodes if node.kind == "reservoir"}
        finite_nodes = {node.identifier: node for node in self.nodes
                        if node.kind == "finite_reservoir"}
        boundary_map = {} if reservoir_boundaries is None else dict(reservoir_boundaries)
        if set(boundary_map) != set(reservoir_nodes):
            raise ValueError("Prescribed-pressure boundaries must cover every reservoir node exactly")
        for node_id, node in reservoir_nodes.items():
            boundary = boundary_map[node_id]
            if type(boundary) is not FiniteReservoirPressureBoundary:
                raise TypeError("Reservoir nodes require FiniteReservoirPressureBoundary values")
            boundary.require_compatible(
                start_time_s=float(times[0]), end_time_s=float(times[-1]),
                clock_id=self.clock_id, eos_identity=self.eos.identity,
                temperature_k=temperature,
            )
            if (node.state_owner_id != boundary.state_owner_id
                    or node.evidence_id != boundary.state_evidence_id):
                raise ValueError("Reservoir node owner/evidence must match its supplied pressure-history boundary")
            for history_pressure in boundary.pressure_pa:
                density = finite(self.eos.density_pt(float(history_pressure), temperature),
                                  "network reservoir EOS density", positive=True)
                replay = finite(self.eos.pressure_rho_t(density, temperature),
                                "network reservoir EOS pressure", positive=True)
                finite(self.eos.isothermal_sound_speed_rho_t(
                    density, temperature), "network reservoir characteristic speed", positive=True)
                if not np.isclose(replay, history_pressure, rtol=1e-6, atol=1e-3):
                    raise ValueError("Reservoir pressure history does not replay through the network EOS")
        finite_map = {} if finite_reservoirs is None else dict(finite_reservoirs)
        if set(finite_map) != set(finite_nodes):
            raise ValueError("Finite-inventory records must cover every finite_reservoir node exactly")
        finite_mass_state = {}
        for node_id, node in finite_nodes.items():
            reservoir = finite_map[node_id]
            if type(reservoir) is not FiniteIsothermalPipeReservoir:
                raise TypeError("finite_reservoir nodes require FiniteIsothermalPipeReservoir values")
            if (reservoir.node_id != node_id or node.state_owner_id != reservoir.state_owner_id
                    or node.evidence_id != reservoir.state_evidence_id):
                raise ValueError("Finite reservoir node ID, owner and evidence must match its inventory record")
            if (reservoir.clock_id != self.clock_id or reservoir.eos_identity != self.eos.identity
                    or reservoir.temperature_k != temperature):
                raise ValueError("Finite reservoir clock, EOS identity and fixed temperature must match the network")
            reservoir.pressure_at_mass(reservoir.mass_kg, self.eos)
            finite_mass_state[node_id] = reservoir.mass_kg
        nozzle_map = {} if finite_reservoir_nozzles is None else dict(finite_reservoir_nozzles)
        if not set(nozzle_map) <= set(finite_nodes):
            raise ValueError("Nozzle sinks may only attach to finite-reservoir nodes")
        for node_id, coupling in nozzle_map.items():
            if type(coupling) is not FiniteReservoirNozzleCoupling:
                raise TypeError("Finite-reservoir nozzle entries require FiniteReservoirNozzleCoupling")
            endpoint_edges = [edge for edge in self.edges
                              if node_id in (edge.start_node_id, edge.end_node_id)]
            if len(endpoint_edges) != 1:
                raise ValueError("A finite-reservoir nozzle needs one unique pipe endpoint")
            coupling.require_compatible(
                reservoir=finite_map[node_id], eos=self.eos, clock_id=self.clock_id,
                node_id=node_id, edge_id=endpoint_edges[0].identifier,
            )
        area = {edge.identifier: float(np.pi * edge.internal_diameter_m**2 / 4.)
                for edge in self.edges}
        dx = {edge.identifier: edge.length_m / edge.cell_count for edge in self.edges}
        state = {}
        for edge in self.edges:
            pressure = np.asarray(tuple(initial_pressure_pa[edge.identifier]), dtype=float)
            velocity = np.asarray(tuple(initial_velocity_m_s[edge.identifier]), dtype=float)
            if (pressure.shape != (edge.cell_count,) or velocity.shape != pressure.shape
                    or not np.all(np.isfinite(pressure)) or not np.all(np.isfinite(velocity))
                    or np.any(pressure <= 0.)):
                raise ValueError(f"Initial state for edge {edge.identifier} has invalid dimensions or values")
            density = np.asarray([self.eos.density_pt(float(p), temperature) for p in pressure])
            replay = np.asarray([self.eos.pressure_rho_t(float(r), temperature) for r in density])
            if not np.allclose(replay, pressure, rtol=1e-6, atol=1e-3):
                raise ValueError(f"Initial pressure/density EOS closure failed on edge {edge.identifier}")
            state[edge.identifier] = np.vstack((density, density * velocity))

        node_ports = {node.identifier: [] for node in self.nodes}
        for edge in self.edges:
            node_ports[edge.start_node_id].append((edge, 1))
            node_ports[edge.end_node_id].append((edge, -1))
        junction_nodes = {node.identifier: node for node in self.nodes if node.kind == "junction"}
        node_by_id = {node.identifier: node for node in self.nodes}

        def pressure_node_states(current_state, time_s):
            states = {}
            flux_residuals = {}
            for node_id, node in junction_nodes.items():
                ports = node_ports[node_id]
                def port_states(pressure_node):
                    result = []
                    mass_fluxes = []
                    for edge, orientation in ports:
                        q = current_state[edge.identifier]
                        cell = 0 if orientation == 1 else -1
                        rho_inside = float(q[0, cell])
                        velocity_inside_x = float(q[1, cell] / rho_inside)
                        velocity_inside = orientation * velocity_inside_x
                        sound_inside = finite(self.eos.isothermal_sound_speed_rho_t(
                            rho_inside, temperature), "pipe characteristic speed", positive=True)
                        if abs(velocity_inside) >= sound_inside:
                            raise ValueError("Junction coupling supports only subsonic adjacent pipe states")
                        rho_node = finite(self.eos.density_pt(pressure_node, temperature),
                                          "junction EOS density", positive=True)
                        replay = finite(self.eos.pressure_rho_t(rho_node, temperature),
                                        "junction EOS pressure", positive=True)
                        if not np.isclose(replay, pressure_node, rtol=1e-6, atol=1e-3):
                            raise ValueError("Junction pressure does not replay through the shared EOS")
                        sound_node = finite(self.eos.isothermal_sound_speed_rho_t(
                            rho_node, temperature), "junction characteristic speed", positive=True)
                        logs = np.linspace(np.log(rho_inside), np.log(rho_node), 5)
                        speeds = np.asarray([self.eos.isothermal_sound_speed_rho_t(
                            float(np.exp(x)), temperature) for x in logs], dtype=float)
                        delta_phi = (logs[-1] - logs[0]) / 12. * (
                            speeds[0] + 4.*speeds[1] + 2.*speeds[2]
                            + 4.*speeds[3] + speeds[4]
                        )
                        # The outgoing Riemann invariant at the node is
                        # v - integral(c_T/rho d rho), fixed by the pipe side.
                        velocity_node_out = velocity_inside + float(delta_phi)
                        if abs(velocity_node_out) >= sound_node:
                            raise ValueError("Junction characteristic state is supersonic")
                        velocity_node_x = orientation * velocity_node_out
                        # Rusanov flux is evaluated in node-outward coordinates so
                        # the same mass flux enters both the root and FV update.
                        pressure_inside = finite(self.eos.pressure_rho_t(
                            rho_inside, temperature), "pipe endpoint pressure", positive=True)
                        speed = max(abs(velocity_inside)+sound_inside,
                                    abs(velocity_node_out)+sound_node)
                        mass_flux = (0.5*(rho_inside*velocity_inside
                                           + rho_node*velocity_node_out)
                                     - 0.5*speed*(rho_inside-rho_node))
                        result.append((edge, orientation, rho_node,
                                       velocity_node_x, pressure_node, velocity_inside_x,
                                       rho_inside, pressure_inside, sound_node, sound_inside))
                        mass_fluxes.append(area[edge.identifier] * mass_flux)
                    return result, mass_fluxes

                lower, upper = node.pressure_bounds_pa
                grid = np.geomspace(lower, upper, 65)
                residuals = []
                for candidate in grid:
                    _, fluxes = port_states(float(candidate))
                    residuals.append(float(sum(fluxes)))
                differences = np.diff(residuals)
                monotone_tolerance = 1e-12 * max(1., max(abs(value) for value in residuals))
                if not (np.all(differences >= -monotone_tolerance)
                        or np.all(differences <= monotone_tolerance)):
                    raise ValueError("Junction continuity residual is non-monotone inside declared bounds")
                exact = [index for index, value in enumerate(residuals) if value == 0.]
                crossings = [index for index in range(len(grid)-1)
                             if residuals[index] * residuals[index+1] < 0.]
                if len(exact) == 1:
                    root = float(grid[exact[0]])
                elif not exact and len(crossings) == 1:
                    lo, hi = float(grid[crossings[0]]), float(grid[crossings[0]+1])
                    f_lo = residuals[crossings[0]]
                    for _ in range(80):
                        mid = 0.5*(lo+hi)
                        _, trial_flux = port_states(mid)
                        f_mid = float(sum(trial_flux))
                        if abs(f_mid) <= 1e-12 * max(1., sum(abs(x) for x in trial_flux)):
                            lo = hi = mid
                            break
                        if f_lo * f_mid <= 0.:
                            hi = mid
                        else:
                            lo, f_lo = mid, f_mid
                    root = 0.5*(lo+hi)
                else:
                    raise ValueError("Junction pressure root is absent or non-unique inside declared bounds")
                states[node_id], fluxes = port_states(root)
                flux_residuals[node_id] = float(sum(fluxes))
                tolerance = 1e-10 * max(1., sum(abs(value) for value in fluxes))
                if abs(flux_residuals[node_id]) > tolerance:
                    raise FloatingPointError("Junction mass continuity did not close")
            for node_id in (*reservoir_nodes, *finite_nodes):
                edge, orientation = node_ports[node_id][0]
                q = current_state[edge.identifier]
                cell = 0 if orientation == 1 else -1
                rho_inside = float(q[0, cell])
                velocity_inside_x = float(q[1, cell] / rho_inside)
                velocity_inside = orientation * velocity_inside_x
                sound_inside = finite(self.eos.isothermal_sound_speed_rho_t(
                    rho_inside, temperature), "reservoir-adjacent pipe sound speed", positive=True)
                if abs(velocity_inside) >= sound_inside:
                    raise ValueError("Reservoir coupling supports only subsonic adjacent pipe states")
                if node_id in reservoir_nodes:
                    pressure_node = boundary_map[node_id].pressure_at(time_s)
                else:
                    pressure_node = finite_map[node_id].pressure_at_mass(
                        finite_mass_state[node_id], self.eos)
                rho_node = finite(self.eos.density_pt(pressure_node, temperature),
                                  "network reservoir density", positive=True)
                replay = finite(self.eos.pressure_rho_t(rho_node, temperature),
                                "network reservoir replay pressure", positive=True)
                if not np.isclose(replay, pressure_node, rtol=1e-6, atol=1e-3):
                    raise ValueError("Interpolated reservoir pressure does not replay through the network EOS")
                sound_node = finite(self.eos.isothermal_sound_speed_rho_t(
                    rho_node, temperature), "network reservoir sound speed", positive=True)
                logs = np.linspace(np.log(rho_inside), np.log(rho_node), 5)
                speeds = np.asarray([self.eos.isothermal_sound_speed_rho_t(
                    float(np.exp(value)), temperature) for value in logs], dtype=float)
                delta_phi = (logs[-1]-logs[0])/12. * (
                    speeds[0]+4.*speeds[1]+2.*speeds[2]+4.*speeds[3]+speeds[4]
                )
                velocity_node_out = velocity_inside + float(delta_phi)
                if abs(velocity_node_out) >= sound_node:
                    raise ValueError("Reservoir characteristic state is supersonic")
                velocity_node_x = orientation * velocity_node_out
                pressure_inside = finite(self.eos.pressure_rho_t(
                    rho_inside, temperature), "reservoir-adjacent pipe pressure", positive=True)
                states[node_id] = [(
                    edge, orientation, rho_node, velocity_node_x, pressure_node,
                    velocity_inside_x, rho_inside, pressure_inside, sound_node, sound_inside,
                )]
                flux_residuals[node_id] = 0.
            return states, flux_residuals

        def fluxes_for(current_state, junction_states):
            result = {}
            node_fluxes = {node.identifier: [] for node in self.nodes}
            for edge in self.edges:
                q = current_state[edge.identifier]
                rho = q[0]
                velocity = q[1] / rho
                pressure = np.asarray([self.eos.pressure_rho_t(float(value), temperature)
                                       for value in rho])
                sound = np.asarray([self.eos.isothermal_sound_speed_rho_t(float(value), temperature)
                                    for value in rho])
                face = np.empty((2, edge.cell_count+1), dtype=float)
                def rusanov(rl, ul, pl, cl, rr, ur, pr, cr):
                    sl = max(abs(ul)+cl, abs(ur)+cr)
                    return np.asarray((
                        0.5*(rl*ul+rr*ur)-0.5*sl*(rr-rl),
                        0.5*(rl*ul*ul+pl+rr*ur*ur+pr)-0.5*sl*(rr*ur-rl*ul),
                    ))
                for face_index in range(1, edge.cell_count):
                    i, j = face_index-1, face_index
                    face[:, face_index] = rusanov(rho[i], velocity[i], pressure[i], sound[i],
                                                  rho[j], velocity[j], pressure[j], sound[j])
                for node_id, orientation, index in ((edge.start_node_id, 1, 0),
                                                      (edge.end_node_id, -1, -1)):
                    node = node_by_id[node_id]
                    cell = 0 if index == 0 else -1
                    if node.kind == "closed":
                        face[:, index] = (0., pressure[cell])
                        node_fluxes[node_id].append(0.)
                    else:
                        match = next(item for item in junction_states[node_id]
                                     if item[0].identifier == edge.identifier)
                        (_, _, rho_node, velocity_node_x, p_node, _, _, _, c_node, _) = match
                        # Evaluate the Rusanov interface in outward coordinates.
                        v_inside = orientation * velocity[cell]
                        outward_flux = rusanov(
                            rho_node, orientation*velocity_node_x, p_node, c_node,
                            rho[cell], v_inside, pressure[cell], sound[cell],
                        )
                        face[:, index] = (orientation*outward_flux[0], outward_flux[1])
                        node_fluxes[node_id].append(area[edge.identifier]*outward_flux[0])
                result[edge.identifier] = face
            return result, {key: float(sum(value)) for key, value in node_fluxes.items()}

        def total_mass(current_state):
            return float(sum(np.sum(q[0]) * area[edge.identifier] * dx[edge.identifier]
                             for edge in self.edges for q in (current_state[edge.identifier],)))

        initial_mass = total_mass(state) + sum(finite_mass_state.values())
        pressure_samples = {edge.identifier: [] for edge in self.edges}
        velocity_samples = {edge.identifier: [] for edge in self.edges}
        flow_samples = {edge.identifier: [] for edge in self.edges}
        junction_pressure_samples = {node_id: [] for node_id in junction_nodes}
        junction_residual_samples = {node_id: [] for node_id in junction_nodes}
        reservoir_pressure_samples = {node_id: [] for node_id in reservoir_nodes}
        finite_mass_samples = {node_id: [] for node_id in finite_nodes}
        finite_pressure_samples = {node_id: [] for node_id in finite_nodes}
        nozzle_history_times = {node_id: [0.] for node_id in nozzle_map}
        nozzle_history_samples = {node_id: [] for node_id in nozzle_map}
        nozzle_current_results = {}
        nozzle_mass_out = {node_id: 0. for node_id in nozzle_map}
        nozzle_mass_out_samples = {node_id: [0.] for node_id in nozzle_map}
        for node_id, coupling in nozzle_map.items():
            _, initial_nozzle = coupling.nozzle_result(
                mass_kg=finite_mass_state[node_id], reservoir=finite_map[node_id], eos=self.eos,
            )
            nozzle_current_results[node_id] = initial_nozzle
            nozzle_history_samples[node_id].append(initial_nozzle)
        mass_samples, global_residual_samples = [], []
        cumulative_boundary_mass_in = 0.
        cumulative_boundary_mass_out = 0.
        boundary_mass_in_samples = [0.]
        boundary_mass_out_samples = [0.]
        elapsed_steps = 0

        def maximum_wave_speed(current_state, node_states):
            maximum = 0.
            for edge in self.edges:
                q = current_state[edge.identifier]
                rho, u = q[0], q[1]/q[0]
                speeds = [abs(float(v))+finite(self.eos.isothermal_sound_speed_rho_t(
                    float(r), temperature), "network wave speed", positive=True)
                          for r, v in zip(rho, u, strict=True)]
                for node_id in (edge.start_node_id, edge.end_node_id):
                    if node_id in node_states:
                        for item in node_states[node_id]:
                            if item[0].identifier == edge.identifier:
                                speeds.append(abs(item[3])+item[8])
                maximum = max(maximum, max(speeds))
            return maximum

        for sample_index, sample_time in enumerate(times):
            if sample_index > 0:
                current_time = float(times[sample_index-1])
                while current_time < sample_time:
                    remaining = float(sample_time-current_time)
                    interior_speed = max(
                        abs(float(q[1, i]/q[0, i])) + finite(
                            self.eos.isothermal_sound_speed_rho_t(float(q[0, i]), temperature),
                            "network wave speed", positive=True,
                        )
                        for q in state.values() for i in range(q.shape[1])
                    )
                    dt = min(remaining, self.maximum_cfl * min(dx.values()) / interior_speed)
                    for _ in range(12):
                        node_states, _ = pressure_node_states(state, current_time + .5*dt)
                        max_speed = maximum_wave_speed(state, node_states)
                        permitted = self.maximum_cfl * min(dx.values()) / max_speed
                        if dt <= min(remaining, permitted) * (1.+1e-12):
                            break
                        dt = min(remaining, permitted)
                    if not np.isfinite(dt) or dt <= 0.:
                        raise FloatingPointError("Network CFL controller could not form a positive step")
                    node_states, _ = pressure_node_states(state, current_time + .5*dt)
                    max_speed = maximum_wave_speed(state, node_states)
                    if dt * max_speed / min(dx.values()) > self.maximum_cfl * (1.+1e-12):
                        raise FloatingPointError("Boundary characteristic speeds could not satisfy the network CFL bound")
                    faces, node_flux_rates = fluxes_for(state, node_states)
                    for node_id in reservoir_nodes:
                        outward_rate = node_flux_rates[node_id]
                        cumulative_boundary_mass_in += dt * max(outward_rate, 0.)
                        cumulative_boundary_mass_out += dt * max(-outward_rate, 0.)
                    for node_id in finite_nodes:
                        edge = node_ports[node_id][0][0]
                        outward_rate = node_flux_rates[node_id]
                        reservoir = finite_map[node_id]
                        reservoir.require_subsonic(
                            mass_kg=finite_mass_state[node_id],
                            outward_mass_flow_kg_s=outward_rate,
                            endpoint_area_m2=area[edge.identifier], eos=self.eos,
                        )
                        nozzle_rate = 0.
                        if node_id in nozzle_map:
                            nozzle_rate = nozzle_current_results[node_id].mass_flow_kg_s
                        next_mass, _mass_residual = reservoir.advance_with_leak(
                            current_mass_kg=finite_mass_state[node_id],
                            pipe_outward_mass_flow_kg_s=outward_rate,
                            nozzle_outflow_mass_flow_kg_s=nozzle_rate,
                            duration_s=dt,
                        )
                        finite_mass_state[node_id] = next_mass
                        if node_id in nozzle_map:
                            nozzle_mass_out[node_id] += dt * nozzle_rate
                    updated = {}
                    for edge in self.edges:
                        q = state[edge.identifier]
                        next_q = q - (dt/dx[edge.identifier]) * (
                            faces[edge.identifier][:, 1:] - faces[edge.identifier][:, :-1]
                        )
                        if not np.all(np.isfinite(next_q)) or np.any(next_q[0] <= 0.):
                            raise FloatingPointError("Network finite-volume update produced invalid density")
                        if edge.darcy_friction_factor:
                            speed_before = next_q[1]/next_q[0]
                            rate = edge.darcy_friction_factor/(2.*edge.internal_diameter_m)
                            next_q[1] /= 1.+rate*np.abs(speed_before)*dt
                        updated[edge.identifier] = next_q
                    state = updated
                    current_time = min(float(sample_time), current_time+dt)
                    for node_id, coupling in nozzle_map.items():
                        # This endpoint solve is diagnostic; the preceding accepted
                        # interval used the left-end rate already debited above.
                        _, endpoint_nozzle = coupling.nozzle_result(
                            mass_kg=finite_mass_state[node_id], reservoir=finite_map[node_id],
                            eos=self.eos,
                        )
                        nozzle_current_results[node_id] = endpoint_nozzle
                        nozzle_history_times[node_id].append(current_time)
                        nozzle_history_samples[node_id].append(endpoint_nozzle)
                    elapsed_steps += 1
                    if elapsed_steps > self.maximum_internal_steps:
                        raise RuntimeError("maximum_internal_steps reached before requested samples")
            node_states, _ = pressure_node_states(state, float(sample_time))
            faces, node_flux_residual = fluxes_for(state, node_states)
            for edge in self.edges:
                q = state[edge.identifier]
                density = q[0]
                velocity = q[1]/density
                pressure = np.asarray([self.eos.pressure_rho_t(float(r), temperature)
                                       for r in density])
                pressure_samples[edge.identifier].append(pressure)
                velocity_samples[edge.identifier].append(velocity)
                flow_samples[edge.identifier].append(faces[edge.identifier][0] * area[edge.identifier])
            for node_id in junction_nodes:
                junction_pressure_samples[node_id].append(
                    float(node_states[node_id][0][4])
                )
                junction_residual_samples[node_id].append(node_flux_residual[node_id])
            for node_id, boundary in boundary_map.items():
                reservoir_pressure_samples[node_id].append(
                    boundary.pressure_at(float(sample_time))
                )
            for node_id, reservoir in finite_map.items():
                finite_mass_samples[node_id].append(finite_mass_state[node_id])
                finite_pressure_samples[node_id].append(
                    reservoir.pressure_at_mass(finite_mass_state[node_id], self.eos)
                )
            for node_id in nozzle_map:
                nozzle_mass_out_samples[node_id].append(nozzle_mass_out[node_id])
            mass = total_mass(state) + sum(finite_mass_state.values())
            mass_samples.append(mass)
            global_residual_samples.append(
                mass-initial_mass-cumulative_boundary_mass_in+cumulative_boundary_mass_out
                +sum(nozzle_mass_out.values())
            )
            if sample_index > 0:
                boundary_mass_in_samples.append(cumulative_boundary_mass_in)
                boundary_mass_out_samples.append(cumulative_boundary_mass_out)
        return IsothermalPipeNetworkTrace(
            time_s=times,
            edge_pressure_pa={key: np.asarray(value) for key, value in pressure_samples.items()},
            edge_velocity_m_s={key: np.asarray(value) for key, value in velocity_samples.items()},
            edge_face_mass_flow_kg_s={key: np.asarray(value) for key, value in flow_samples.items()},
            junction_pressure_pa={key: np.asarray(value) for key, value in junction_pressure_samples.items()},
            junction_mass_residual_kg_s={key: np.asarray(value) for key, value in junction_residual_samples.items()},
            total_mass_kg=np.asarray(mass_samples),
            global_mass_balance_residual_kg=np.asarray(global_residual_samples),
            clock_id=self.clock_id, eos_identity=self.eos.identity,
            temperature_k=temperature,
            node_state_owner_ids={node.identifier: node.state_owner_id for node in self.nodes},
            node_evidence_ids={node.identifier: node.evidence_id for node in self.nodes},
            edge_geometry_owner_ids={edge.identifier: edge.geometry_owner_id for edge in self.edges},
            edge_geometry_evidence_ids={edge.identifier: edge.geometry_evidence_id for edge in self.edges},
            reservoir_pressure_pa={key: np.asarray(value)
                                   for key, value in reservoir_pressure_samples.items()},
            boundary_mass_in_kg=np.asarray(boundary_mass_in_samples),
            boundary_mass_out_kg=np.asarray(boundary_mass_out_samples),
            reservoir_ids={key: value.identifier for key, value in boundary_map.items()},
            reservoir_state_owner_ids={key: value.state_owner_id
                                       for key, value in boundary_map.items()},
            reservoir_evidence_ids={key: value.state_evidence_id
                                    for key, value in boundary_map.items()},
            reservoir_clock_ids={key: value.clock_id for key, value in boundary_map.items()},
            reservoir_origins={key: value.origin for key, value in boundary_map.items()},
            finite_inventory_mass_kg={key: np.asarray(value)
                                      for key, value in finite_mass_samples.items()},
            finite_inventory_pressure_pa={key: np.asarray(value)
                                          for key, value in finite_pressure_samples.items()},
            finite_inventory_ids={key: value.identifier for key, value in finite_map.items()},
            finite_inventory_state_owner_ids={key: value.state_owner_id
                                              for key, value in finite_map.items()},
            finite_inventory_evidence_ids={key: value.state_evidence_id
                                           for key, value in finite_map.items()},
            finite_inventory_clock_ids={key: value.clock_id
                                        for key, value in finite_map.items()},
            finite_inventory_origins={key: value.origin for key, value in finite_map.items()},
            finite_reservoir_nozzle_history={
                node_id: SourceHistory(
                    nozzle_map[node_id].location,
                    tuple(nozzle_history_times[node_id]),
                    tuple(nozzle_history_samples[node_id]),
                    "window_end",
                ) for node_id in nozzle_map
            },
            finite_reservoir_nozzle_coupling_ids={
                key: value.identifier for key, value in nozzle_map.items()
            },
            finite_reservoir_nozzle_evidence_ids={
                key: value.evidence_id for key, value in nozzle_map.items()
            },
            finite_reservoir_nozzle_mass_out_kg={
                key: np.asarray(value) for key, value in nozzle_mass_out_samples.items()
            },
        )


__all__ = ["IsothermalPipeNetworkNode", "IsothermalPipeNetworkEdge",
           "IsothermalPipeNetworkTrace", "IsothermalPipeNetworkWaveModel"]
