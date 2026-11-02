"""Caloric 1-D Euler waves on a caller-defined branched pipe graph.

Each edge advances the conservative Euler state with the shared caloric pipe
flux kernels. A zero-volume adiabatic perfect-mixing junction has one common
pressure and temperature and a resting state; those two values are found from
the exact Rusanov mass and total-energy fluxes applied to its connected pipe
ends. This is a declared junction approximation, not a detailed tee model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
from scipy.optimize import least_squares

from .caloric_pipe_nozzle_coupling import CaloricFiniteReservoirNozzleCoupling
from .caloric_pipe_waves import (
    CaloricDarcyFrictionLaw,
    CaloricGasEOS,
    CaloricPipeReservoirBoundary,
    CaloricPipeWallHeatBoundary,
    CaloricPipeWaveModel,
    _eos_identity,
    _positive_cv,
    _require_gas_state,
)
from .core import Origin, PropertyBasis, ThermoState, finite, immutable_array
from .finite_caloric_pipe_reservoir import FiniteCaloricPipeReservoir
from .release import NozzleSourceProjection, SourceHistory

_PENDING_ISSUERS: set[object] = set()


def _issue_trace(**values):
    token = object()
    _PENDING_ISSUERS.add(token)
    try:
        return CaloricPipeNetworkWaveTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class CaloricPipeNetworkNode:
    identifier: str
    coordinates_m: tuple[float, float, float]
    kind: str
    state_owner_id: str
    evidence_id: str
    origin: Origin
    pressure_bounds_pa: tuple[float, float] | None = None
    temperature_bounds_k: tuple[float, float] | None = None

    def __post_init__(self):
        for name in ("identifier", "state_owner_id", "evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare node {name}")
        if self.kind not in {"junction", "closed", "reservoir", "finite_reservoir"}:
            raise ValueError("Node kind must be junction, closed, reservoir, or finite_reservoir")
        coordinates = tuple(finite(x, "node coordinate") for x in self.coordinates_m)
        if len(coordinates) != 3:
            raise ValueError("Node coordinates require x, y, z")
        object.__setattr__(self, "coordinates_m", coordinates)
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Node origin must be explicit")
        object.__setattr__(self, "origin", origin)
        if self.kind == "junction":
            if self.pressure_bounds_pa is None or self.temperature_bounds_k is None:
                raise ValueError("Junction pressure and temperature brackets must be caller-declared")
            for values, label in ((self.pressure_bounds_pa, "pressure"),
                                  (self.temperature_bounds_k, "temperature")):
                if len(values) != 2:
                    raise ValueError(f"Junction {label} bounds require two entries")
                lower = finite(values[0], f"junction lower {label}", positive=True)
                upper = finite(values[1], f"junction upper {label}", positive=True)
                if lower >= upper:
                    raise ValueError(f"Junction {label} bounds must increase strictly")
            object.__setattr__(self, "pressure_bounds_pa", tuple(self.pressure_bounds_pa))
            object.__setattr__(self, "temperature_bounds_k", tuple(self.temperature_bounds_k))
        elif self.pressure_bounds_pa is not None or self.temperature_bounds_k is not None:
            raise ValueError("Terminal nodes cannot declare junction solve brackets")


@dataclass(frozen=True, slots=True)
class CaloricPipeNetworkEdge:
    identifier: str
    start_node_id: str
    end_node_id: str
    length_m: float
    internal_diameter_m: float
    cell_count: int
    geometry_owner_id: str
    geometry_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in ("identifier", "start_node_id", "end_node_id",
                     "geometry_owner_id", "geometry_evidence_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Declare edge {name}")
        if self.start_node_id == self.end_node_id:
            raise ValueError("A pipe edge must connect distinct nodes")
        finite(self.length_m, "edge length", positive=True)
        finite(self.internal_diameter_m, "edge diameter", positive=True)
        if isinstance(self.cell_count, bool) or not isinstance(self.cell_count, int) or self.cell_count < 2:
            raise ValueError("Each edge requires at least two cells")
        origin = Origin(self.origin)
        if origin is Origin.UNRESOLVED:
            raise ValueError("Pipe geometry origin must be explicit")
        object.__setattr__(self, "origin", origin)


def _freeze_arrays(source, *, label, time_count, edge_cells=None, face=False):
    result = {}
    for key, value in source.items():
        array = immutable_array(value, dtype=float, name=f"{label}[{key}]")
        if array.ndim != 2 or array.shape[0] != time_count or not np.all(np.isfinite(array)):
            raise ValueError(f"{label} must contain finite time-by-space arrays")
        if edge_cells is not None:
            expected = edge_cells[key] + (1 if face else 0)
            if array.shape[1] != expected:
                raise ValueError(f"{label}[{key}] has an invalid spatial length")
        result[key] = array
    return MappingProxyType(result)


@dataclass(frozen=True, slots=True)
class CaloricPipeNetworkWaveTrace:
    time_s: np.ndarray = field(repr=False, compare=False)
    pressure_pa: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    temperature_k: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    density_kg_m3: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    velocity_m_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    face_mass_flow_kg_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    face_energy_flow_w: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_pressure_pa: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_temperature_k: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_mass_residual_kg_s: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_energy_residual_w: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    junction_entropy_generation_w_k: Mapping[str, np.ndarray] = field(repr=False, compare=False)
    total_mass_kg: np.ndarray = field(repr=False, compare=False)
    total_energy_j: np.ndarray = field(repr=False, compare=False)
    cumulative_terminal_mass_in_kg: np.ndarray = field(repr=False, compare=False)
    cumulative_terminal_energy_in_j: np.ndarray = field(repr=False, compare=False)
    cumulative_junction_mass_kg: np.ndarray = field(repr=False, compare=False)
    cumulative_junction_energy_j: np.ndarray = field(repr=False, compare=False)
    cumulative_wall_heat_in_j: np.ndarray = field(repr=False, compare=False)
    mass_balance_residual_kg: np.ndarray = field(repr=False, compare=False)
    energy_balance_residual_j: np.ndarray = field(repr=False, compare=False)
    edge_cell_centers_m: Mapping[str, np.ndarray]
    edge_lengths_m: Mapping[str, float]
    edge_diameters_m: Mapping[str, float]
    edge_cell_counts: Mapping[str, int]
    edge_start_node_ids: Mapping[str, str]
    edge_end_node_ids: Mapping[str, str]
    edge_origins: Mapping[str, Origin]
    edge_geometry_owner_ids: Mapping[str, str]
    edge_geometry_evidence_ids: Mapping[str, str]
    node_coordinates_m: Mapping[str, tuple[float, float, float]]
    node_kinds: Mapping[str, str]
    node_origins: Mapping[str, Origin]
    node_state_owner_ids: Mapping[str, str]
    node_evidence_ids: Mapping[str, str]
    reservoir_boundary_ids: Mapping[str, str]
    reservoir_boundary_states: Mapping[str, ThermoState]
    reservoir_boundary_velocities_m_s: Mapping[str, float]
    friction_law_ids: Mapping[str, str]
    friction_state_owner_ids: Mapping[str, str]
    friction_evidence_ids: Mapping[str, str]
    wall_heat_boundary_ids: Mapping[str, str]
    wall_heat_state_owner_ids: Mapping[str, str]
    wall_heat_evidence_ids: Mapping[str, str]
    finite_reservoir_records: Mapping[str, FiniteCaloricPipeReservoir]
    finite_reservoir_nozzle_couplings: Mapping[str, CaloricFiniteReservoirNozzleCoupling]
    finite_reservoir_mass_kg: Mapping[str, np.ndarray]
    finite_reservoir_internal_energy_j: Mapping[str, np.ndarray]
    finite_reservoir_pressure_pa: Mapping[str, np.ndarray]
    finite_reservoir_temperature_k: Mapping[str, np.ndarray]
    finite_reservoir_nozzle_history: Mapping[str, SourceHistory]
    finite_reservoir_nozzle_coupling_ids: Mapping[str, str]
    finite_reservoir_nozzle_state_owner_ids: Mapping[str, str]
    finite_reservoir_nozzle_evidence_ids: Mapping[str, str]
    cumulative_nozzle_mass_out_kg: Mapping[str, np.ndarray]
    cumulative_nozzle_withdrawal_energy_j: Mapping[str, np.ndarray]
    clock_id: str
    eos_identity: str
    property_basis: PropertyBasis
    maximum_cfl: float
    cfl_limit: float
    _eos_provider: CaloricGasEOS = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ISSUERS:
            raise ValueError("Network traces can only be issued by a completed model run")
        _PENDING_ISSUERS.remove(self._issuer_token)
        time = immutable_array(self.time_s, dtype=float, name="network time_s")
        if time.ndim != 1 or len(time) < 2 or time[0] != 0. or not np.all(np.isfinite(time)) or np.any(np.diff(time) <= 0.):
            raise ValueError("Network times must start at zero and increase strictly")
        edge_ids = set(self.edge_cell_counts)
        junction_ids = set(self.junction_pressure_pa)
        if (not edge_ids or set(self.pressure_pa) != edge_ids or set(self.temperature_k) != edge_ids
                or set(self.density_kg_m3) != edge_ids or set(self.velocity_m_s) != edge_ids
                or set(self.face_mass_flow_kg_s) != edge_ids or set(self.face_energy_flow_w) != edge_ids):
            raise ValueError("Network trace edge maps must cover identical edge IDs")
        if (set(self.junction_temperature_k) != junction_ids
                or set(self.junction_mass_residual_kg_s) != junction_ids
                or set(self.junction_energy_residual_w) != junction_ids
                or set(self.junction_entropy_generation_w_k) != junction_ids):
            raise ValueError("Network trace junction maps must cover identical junction IDs")
        cell_counts = dict(self.edge_cell_counts)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "velocity_m_s"):
            object.__setattr__(self, name, _freeze_arrays(getattr(self, name), label=name,
                                                          time_count=len(time), edge_cells=cell_counts))
        for name in ("pressure_pa", "temperature_k", "density_kg_m3"):
            if any(np.any(values <= 0.) for values in getattr(self, name).values()):
                raise ValueError(f"Network trace {name} must remain positive")
        for name in ("face_mass_flow_kg_s", "face_energy_flow_w"):
            object.__setattr__(self, name, _freeze_arrays(getattr(self, name), label=name,
                                                          time_count=len(time), edge_cells=cell_counts,
                                                          face=True))
        for name in ("junction_pressure_pa", "junction_temperature_k",
                     "junction_mass_residual_kg_s", "junction_energy_residual_w",
                     "junction_entropy_generation_w_k"):
            mapping = {}
            for key, values in getattr(self, name).items():
                array = immutable_array(values, dtype=float, name=f"{name}[{key}]")
                if array.shape != (len(time),) or not np.all(np.isfinite(array)):
                    raise ValueError(f"{name}[{key}] has invalid values")
                mapping[key] = array
            object.__setattr__(self, name, MappingProxyType(mapping))
        for name in ("total_mass_kg", "total_energy_j", "cumulative_terminal_mass_in_kg",
                     "cumulative_terminal_energy_in_j", "cumulative_junction_mass_kg",
                     "cumulative_junction_energy_j", "cumulative_wall_heat_in_j",
                     "mass_balance_residual_kg",
                     "energy_balance_residual_j"):
            array = immutable_array(getattr(self, name), dtype=float, name=name)
            if array.shape != (len(time),) or not np.all(np.isfinite(array)):
                raise ValueError(f"{name} has invalid trace values")
            object.__setattr__(self, name, array)
        for name in ("edge_cell_centers_m",):
            mapping = {key: immutable_array(value, dtype=float, name=f"{name}[{key}]")
                       for key, value in getattr(self, name).items()}
            if set(mapping) != edge_ids or any(value.ndim != 1 or len(value) != cell_counts[key]
                                                for key, value in mapping.items()):
                raise ValueError("Edge center arrays do not match edge topology")
            object.__setattr__(self, name, MappingProxyType(mapping))
        for name in ("edge_lengths_m", "edge_diameters_m", "edge_cell_counts",
                     "edge_start_node_ids", "edge_end_node_ids", "edge_origins",
                     "edge_geometry_owner_ids", "edge_geometry_evidence_ids",
                     "node_coordinates_m", "node_kinds", "node_origins",
                     "node_state_owner_ids", "node_evidence_ids", "reservoir_boundary_ids",
                     "reservoir_boundary_states", "reservoir_boundary_velocities_m_s",
                     "friction_law_ids", "friction_state_owner_ids", "friction_evidence_ids",
                     "wall_heat_boundary_ids", "wall_heat_state_owner_ids", "wall_heat_evidence_ids",
                     "finite_reservoir_records", "finite_reservoir_nozzle_couplings"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        expected_finite_nodes = {key for key, kind in self.node_kinds.items() if kind == "finite_reservoir"}
        nozzle_ids = set(self.finite_reservoir_nozzle_history)
        object.__setattr__(self, "finite_reservoir_nozzle_history",
                           MappingProxyType(dict(self.finite_reservoir_nozzle_history)))
        for name in ("finite_reservoir_nozzle_coupling_ids",
                     "finite_reservoir_nozzle_state_owner_ids",
                     "finite_reservoir_nozzle_evidence_ids",
                     "cumulative_nozzle_mass_out_kg",
                     "cumulative_nozzle_withdrawal_energy_j"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))
        if any(set(getattr(self, name)) != nozzle_ids for name in (
            "finite_reservoir_nozzle_coupling_ids", "finite_reservoir_nozzle_state_owner_ids",
            "finite_reservoir_nozzle_evidence_ids", "cumulative_nozzle_mass_out_kg",
            "cumulative_nozzle_withdrawal_energy_j", "finite_reservoir_nozzle_couplings",
        )):
            raise ValueError("Nozzle histories, provenance and cumulative debits must cover identical nodes")
        if not nozzle_ids <= expected_finite_nodes:
            raise ValueError("Nozzle histories may only be attached to finite-reservoir nodes")
        cumulative_maps = {}
        for name in ("cumulative_nozzle_mass_out_kg", "cumulative_nozzle_withdrawal_energy_j"):
            values = {}
            for node_id, raw in getattr(self, name).items():
                array = immutable_array(raw, dtype=float, name=f"{name}[{node_id}]")
                if array.shape != (len(time),) or not np.all(np.isfinite(array)) or np.any(array < 0.):
                    raise ValueError(f"{name}[{node_id}] has invalid cumulative debits")
                if np.any(np.diff(array) < -1.e-12):
                    raise ValueError(f"{name}[{node_id}] must be cumulative and nondecreasing")
                values[node_id] = array
            cumulative_maps[name] = MappingProxyType(values)
            object.__setattr__(self, name, cumulative_maps[name])
        for node_id, history in self.finite_reservoir_nozzle_history.items():
            if type(history) is not SourceHistory or history.location.clock_id != self.clock_id:
                raise ValueError("Nozzle source history must retain its native network clock")
            coupling = self.finite_reservoir_nozzle_couplings[node_id]
            if (history.location.source_id != coupling.identifier
                    or history.location is not coupling.location
                    or coupling.node_id != node_id
                    or self.finite_reservoir_nozzle_coupling_ids[node_id] != coupling.identifier
                    or self.finite_reservoir_nozzle_state_owner_ids[node_id] != coupling.state_owner_id
                    or self.finite_reservoir_nozzle_evidence_ids[node_id] != coupling.evidence_id):
                raise ValueError("Nozzle history and coupling provenance do not match exactly")
        for node_id, history in self.finite_reservoir_nozzle_history.items():
            mass_history = self.cumulative_nozzle_mass_out_kg[node_id]
            history_mass = sum(sample.mass_flow_kg_s * (right-left)
                               for left, right, sample in zip(
                                   history.time_s[:-1], history.time_s[1:],
                                   history.samples[:-1], strict=True))
            if not np.isclose(history_mass, float(mass_history[-1]), rtol=1.e-12, atol=1.e-12):
                raise ValueError("Left-hold nozzle history does not equal the accepted solver mass debit")
            energy_history = self.cumulative_nozzle_withdrawal_energy_j[node_id]
            history_energy = sum(sample.withdrawal_energy_w * (right-left)
                                 for left, right, sample in zip(
                                     history.time_s[:-1], history.time_s[1:],
                                     history.samples[:-1], strict=True))
            if not np.isclose(history_energy, float(energy_history[-1]),
                              rtol=1.e-12, atol=1.e-8):
                raise ValueError("Left-hold nozzle history does not equal accepted withdrawal-energy debits")
            coupling = self.finite_reservoir_nozzle_couplings[node_id]
            if any(sample.opening != coupling.opening
                   or sample.back_pressure_pa != coupling.back_pressure_pa
                   for sample in history.samples):
                raise ValueError("Nozzle source history opening/back-pressure differs from its typed coupling")
        if set(self.edge_lengths_m) != edge_ids or set(self.edge_diameters_m) != edge_ids:
            raise ValueError("Trace geometry maps must cover every edge")
        if set(self.edge_geometry_owner_ids) != edge_ids or set(self.edge_geometry_evidence_ids) != edge_ids:
            raise ValueError("Trace geometry provenance is incomplete")
        if (set(self.edge_start_node_ids) != edge_ids or set(self.edge_end_node_ids) != edge_ids
                or set(self.edge_origins) != edge_ids):
            raise ValueError("Trace edge topology and origins must cover every edge")
        node_ids = set(self.node_coordinates_m)
        if (set(self.node_kinds) != node_ids or set(self.node_origins) != node_ids
                or set(self.node_state_owner_ids) != node_ids or set(self.node_evidence_ids) != node_ids):
            raise ValueError("Trace node topology and provenance must cover every node")
        if any(node_id not in node_ids for node_id in
               (*self.edge_start_node_ids.values(), *self.edge_end_node_ids.values())):
            raise ValueError("Trace edge endpoints do not resolve to retained nodes")
        if (set(self.reservoir_boundary_ids) != set(self.reservoir_boundary_states)
                or set(self.reservoir_boundary_ids) != set(self.reservoir_boundary_velocities_m_s)):
            raise ValueError("Trace reservoir identities and states must be retained together")
        for ids, owners, evidence, label in (
            (self.friction_law_ids, self.friction_state_owner_ids, self.friction_evidence_ids, "friction"),
            (self.wall_heat_boundary_ids, self.wall_heat_state_owner_ids, self.wall_heat_evidence_ids, "wall heat"),
        ):
            if set(ids) != set(owners) or set(ids) != set(evidence) or not set(ids) <= edge_ids:
                raise ValueError(f"Trace {label} provenance must cover only declared edges")
        expected_finite_nodes = {key for key, kind in self.node_kinds.items() if kind == "finite_reservoir"}
        if set(self.finite_reservoir_records) != expected_finite_nodes:
            raise ValueError("Trace finite reservoir records must exactly match finite-reservoir nodes")
        for node_id, record in self.finite_reservoir_records.items():
            if type(record) is not FiniteCaloricPipeReservoir or record.node_id != node_id:
                raise ValueError("Trace finite-reservoir records must retain their exact node identity")
            if (self.node_state_owner_ids[node_id] != record.state_owner_id
                    or self.node_evidence_ids[node_id] != record.state_evidence_id
                    or record.clock_id != self.clock_id or record.eos_identity != self.eos_identity
                    or record.property_basis != self.property_basis):
                raise ValueError("Trace finite-reservoir provenance does not match the network run")
        finite_history_names = ("finite_reservoir_mass_kg", "finite_reservoir_internal_energy_j",
                               "finite_reservoir_pressure_pa", "finite_reservoir_temperature_k")
        finite_histories = {}
        for name in finite_history_names:
            values = {}
            for node_id, raw in getattr(self, name).items():
                array = immutable_array(raw, dtype=float, name=f"{name}[{node_id}]")
                if array.shape != (len(time),) or not np.all(np.isfinite(array)):
                    raise ValueError(f"{name}[{node_id}] has invalid history values")
                if name != "finite_reservoir_internal_energy_j" and np.any(array <= 0.):
                    raise ValueError(f"{name}[{node_id}] must remain positive")
                values[node_id] = array
            if set(values) != expected_finite_nodes:
                raise ValueError(f"{name} histories must cover each finite-reservoir node")
            finite_histories[name] = MappingProxyType(values)
        for name, values in finite_histories.items():
            object.__setattr__(self, name, values)
        for node_id, record in self.finite_reservoir_records.items():
            mass = finite_histories["finite_reservoir_mass_kg"][node_id]
            energy = finite_histories["finite_reservoir_internal_energy_j"][node_id]
            pressure = finite_histories["finite_reservoir_pressure_pa"][node_id]
            temperature = finite_histories["finite_reservoir_temperature_k"][node_id]
            p_lo, p_hi = record.pressure_bounds_pa
            t_lo, t_hi = record.temperature_bounds_k
            if (np.any(mass <= record.minimum_mass_kg) or np.any(mass > record.maximum_mass_kg)
                    or np.any(pressure < p_lo) or np.any(pressure > p_hi)
                    or np.any(temperature < t_lo) or np.any(temperature > t_hi)):
                raise ValueError("Trace finite-reservoir history leaves its declared inventory/EOS domain")
            if (not np.isclose(mass[0], record.mass_kg, rtol=0., atol=1.e-12)
                    or not np.isclose(energy[0], record.internal_energy_j, rtol=0., atol=1.e-8)):
                raise ValueError("Trace finite-reservoir history does not start at its declared initial stock")
        if any(type(value) is not ThermoState for value in self.reservoir_boundary_states.values()):
            raise TypeError("Trace reservoir states must be ThermoState values")
        if set(self.node_state_owner_ids) != set(self.node_evidence_ids):
            raise ValueError("Trace node provenance is incomplete")
        if not isinstance(self.property_basis, PropertyBasis):
            raise TypeError("Network trace must retain a PropertyBasis")
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Trace must retain a clock identity")
        if not isinstance(self.eos_identity, str) or not self.eos_identity.strip():
            raise ValueError("Trace must retain the caloric EOS identity")
        cfl = finite(self.maximum_cfl, "maximum_cfl")
        limit = finite(self.cfl_limit, "cfl_limit", positive=True)
        if cfl < 0. or cfl > limit + 1.e-12 or limit > .5:
            raise ValueError("Network trace exceeds the explicit Rusanov CFL bound")
        object.__setattr__(self, "time_s", time)
        self.require_current()

    def require_current(self) -> None:
        """Replay every retained finite-reservoir state through its EOS owner."""
        if _eos_identity(self._eos_provider) != self.eos_identity:
            raise ValueError("Network trace EOS identity changed after the run")
        if self._eos_provider.basis != self.property_basis:
            raise ValueError("Network trace EOS property basis changed after the run")
        for node_id, kind in self.node_kinds.items():
            if kind != "finite_reservoir":
                continue
            incident = sum(start == node_id for start in self.edge_start_node_ids.values())
            incident += sum(end == node_id for end in self.edge_end_node_ids.values())
            if incident != 1:
                raise ValueError("A finite-reservoir node must resolve to exactly one pipe endpoint")
            record = self.finite_reservoir_records[node_id]
            record.require_eos(self._eos_provider)
            for mass, energy, pressure, temperature in zip(
                self.finite_reservoir_mass_kg[node_id],
                self.finite_reservoir_internal_energy_j[node_id],
                self.finite_reservoir_pressure_pa[node_id],
                self.finite_reservoir_temperature_k[node_id], strict=True,
            ):
                state = record.recover_state(mass_kg=float(mass),
                                             internal_energy_j=float(energy),
                                             eos=self._eos_provider)
                if (not np.isclose(state.pressure_pa, float(pressure), rtol=2.e-6, atol=1.e-2)
                        or not np.isclose(state.temperature_k, float(temperature),
                                          rtol=2.e-6, atol=1.e-8)):
                    raise ValueError("Retained reservoir P/T history does not replay from its m/U history")
        for node_id, coupling in self.finite_reservoir_nozzle_couplings.items():
            coupling.require_compatible(
                reservoir=self.finite_reservoir_records[node_id], eos=self._eos_provider,
                clock_id=self.clock_id, node_coordinates_m=self.node_coordinates_m[node_id],
                edge_id=next(edge_id for edge_id in self.edge_start_node_ids
                             if self.edge_start_node_ids[edge_id] == node_id
                             or self.edge_end_node_ids[edge_id] == node_id),
            )
            for sample in self.finite_reservoir_nozzle_history[node_id].samples:
                upstream = sample.upstream_stagnation
                if upstream.basis != coupling.nozzle.properties.basis:
                    raise ValueError("Nozzle sample basis differs from its retained exact property provider")
                recovered = self._eos_provider.state_rho_u(
                    upstream.density_kg_m3, upstream.internal_energy_j_kg,
                )
                if (not np.isclose(recovered.pressure_pa, upstream.pressure_pa,
                                   rtol=2.e-6, atol=1.e-2)
                        or not np.isclose(recovered.temperature_k, upstream.temperature_k,
                                          rtol=2.e-6, atol=1.e-8)
                        or not np.isclose(recovered.density_kg_m3, upstream.density_kg_m3,
                                          rtol=2.e-6, atol=1.e-10)):
                    raise ValueError("Nozzle sample upstream state does not replay through the retained rho-u EOS")
                provider_state = coupling.nozzle.properties.state_pt(
                    upstream.pressure_pa, upstream.temperature_k,
                )
                if (not np.isclose(provider_state.density_kg_m3, upstream.density_kg_m3,
                                   rtol=coupling.density_relative_tolerance,
                                   atol=coupling.density_absolute_tolerance_kg_m3)
                        or not np.isclose(provider_state.pressure_pa, upstream.pressure_pa,
                                          rtol=2.e-6, atol=1.e-2)
                        or not np.isclose(provider_state.temperature_k, upstream.temperature_k,
                                          rtol=2.e-6, atol=1.e-8)):
                    raise ValueError("Retained nozzle provider no longer reproduces its tank source state")

    def project_nozzle_source(self, node_id: str, *, representative_state: ThermoState,
                              quadrature_evidence_id: str,
                              state_projection_evidence_id: str) -> NozzleSourceProjection:
        """Project one accepted source history and bind it to the exact solver debit."""
        self.require_current()
        if node_id not in self.finite_reservoir_nozzle_history:
            raise KeyError(f"No finite-reservoir nozzle history for node {node_id}")
        projection = self.finite_reservoir_nozzle_history[node_id].interval_mass_projection(
            representative_state=representative_state, flow_rule="left_hold",
            quadrature_evidence_id=quadrature_evidence_id,
            state_projection_evidence_id=state_projection_evidence_id,
        )
        accepted = float(self.cumulative_nozzle_mass_out_kg[node_id][-1])
        if not np.isclose(sum(projection.interval_mass_kg), accepted, rtol=1.e-12, atol=1.e-12):
            raise ValueError("Projected nozzle bins differ from the mass debited by the network solver")
        return projection


@dataclass(frozen=True, slots=True)
class CaloricPipeNetworkWaveModel:
    nodes: tuple[CaloricPipeNetworkNode, ...]
    edges: tuple[CaloricPipeNetworkEdge, ...]
    eos: CaloricGasEOS = field(repr=False, compare=False)
    clock_id: str
    maximum_cfl: float = .3
    maximum_internal_steps: int = 2_000_000
    junction_mass_tolerance_kg_s: float = 1.e-8
    junction_energy_tolerance_w: float = 1.e-3
    junction_solver_tolerance: float = 1.e-11
    junction_entropy_tolerance_w_k: float = 1.e-7

    def __post_init__(self):
        nodes, edges = tuple(self.nodes), tuple(self.edges)
        if len(nodes) < 2 or not edges:
            raise ValueError("A pipe network needs at least two nodes and one edge")
        node_by_id = {node.identifier: node for node in nodes}
        if len(node_by_id) != len(nodes) or len({edge.identifier for edge in edges}) != len(edges):
            raise ValueError("Network node and edge IDs must be unique")
        elevations = {node.coordinates_m[2] for node in nodes}
        if len(elevations) != 1:
            raise ValueError("This network level is horizontal; elevation and gravity are excluded")
        adjacency = {key: [] for key in node_by_id}
        for edge in edges:
            if edge.start_node_id not in node_by_id or edge.end_node_id not in node_by_id:
                raise ValueError("Every edge endpoint must identify a declared node")
            start = np.asarray(node_by_id[edge.start_node_id].coordinates_m)
            end = np.asarray(node_by_id[edge.end_node_id].coordinates_m)
            if edge.length_m + 1.e-12 < float(np.linalg.norm(end - start)):
                raise ValueError("Pipe length cannot be shorter than endpoint separation")
            adjacency[edge.start_node_id].append(edge)
            adjacency[edge.end_node_id].append(edge)
        for node_id, incident in adjacency.items():
            kind = node_by_id[node_id].kind
            if kind == "junction" and len(incident) < 3:
                raise ValueError("A junction must connect at least three pipe edges")
            if kind != "junction" and len(incident) != 1:
                raise ValueError("Each wall or reservoir node must terminate one pipe edge")
        seen, stack = set(), [next(iter(node_by_id))]
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            for edge in adjacency[node_id]:
                stack.append(edge.end_node_id if edge.start_node_id == node_id else edge.start_node_id)
        if seen != set(node_by_id):
            raise ValueError("All edges must belong to one connected network")
        for method in ("state_pt", "state_rho_u"):
            if not callable(getattr(self.eos, method, None)):
                raise TypeError(f"Caloric EOS must implement {method}")
        _eos_identity(self.eos)
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Declare the network clock")
        if finite(self.maximum_cfl, "maximum_cfl", positive=True) > .5:
            raise ValueError("maximum_cfl cannot exceed 0.5")
        for value, name in ((self.junction_mass_tolerance_kg_s, "junction_mass_tolerance_kg_s"),
                            (self.junction_energy_tolerance_w, "junction_energy_tolerance_w"),
                            (self.junction_solver_tolerance, "junction_solver_tolerance"),
                            (self.junction_entropy_tolerance_w_k, "junction_entropy_tolerance_w_k")):
            finite(value, name, positive=True)
        if (isinstance(self.maximum_internal_steps, bool) or not isinstance(self.maximum_internal_steps, int)
                or self.maximum_internal_steps < 1):
            raise ValueError("maximum_internal_steps must be a positive integer")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)

    def simulate(self, *, initial_pressure_pa: Mapping[str, Sequence[float]],
                 initial_temperature_k: Mapping[str, Sequence[float]],
                 initial_velocity_m_s: Mapping[str, Sequence[float]],
                 time_samples_s: Sequence[float],
                 reservoir_boundaries: Mapping[str, CaloricPipeReservoirBoundary] | None = None,
                 finite_reservoirs: Mapping[str, FiniteCaloricPipeReservoir] | None = None,
                 finite_reservoir_nozzles: Mapping[str, CaloricFiniteReservoirNozzleCoupling] | None = None,
                 darcy_friction_laws: Mapping[str, CaloricDarcyFrictionLaw] | None = None,
                 wall_heat_boundaries: Mapping[str, CaloricPipeWallHeatBoundary] | None = None,
                 ) -> CaloricPipeNetworkWaveTrace:
        """Advance each caloric pipe edge on a shared explicit network clock."""
        times = np.asarray(tuple(time_samples_s), dtype=float)
        if (times.ndim != 1 or len(times) < 2 or times[0] != 0. or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0.)):
            raise ValueError("time_samples_s must start at zero and increase strictly")
        edge_ids = {edge.identifier for edge in self.edges}
        if any(set(mapping) != edge_ids for mapping in
               (initial_pressure_pa, initial_temperature_k, initial_velocity_m_s)):
            raise ValueError("Initial state maps must cover every edge exactly")
        node_by_id = {node.identifier: node for node in self.nodes}
        junctions = {node.identifier: node for node in self.nodes if node.kind == "junction"}
        reservoirs = {node.identifier: node for node in self.nodes if node.kind == "reservoir"}
        finite_nodes = {node.identifier: node for node in self.nodes if node.kind == "finite_reservoir"}
        boundary_map = {} if reservoir_boundaries is None else dict(reservoir_boundaries)
        if set(boundary_map) != set(reservoirs):
            raise ValueError("Reservoir boundaries must cover every reservoir node exactly")
        for node_id, node in reservoirs.items():
            boundary = boundary_map[node_id]
            if type(boundary) is not CaloricPipeReservoirBoundary:
                raise TypeError("Reservoir nodes require CaloricPipeReservoirBoundary values")
            if node.state_owner_id != boundary.state_owner_id or node.evidence_id != boundary.state_evidence_id:
                raise ValueError("Reservoir node owner/evidence must match its boundary state")
            boundary.require_compatible(eos=self.eos, clock_id=self.clock_id,
                                        start_time_s=float(times[0]), end_time_s=float(times[-1]))
        finite_map = {} if finite_reservoirs is None else dict(finite_reservoirs)
        if set(finite_map) != set(finite_nodes):
            raise ValueError("Finite caloric reservoir states must cover every finite_reservoir node exactly")
        finite_mass = {}
        finite_energy = {}
        for node_id, node in finite_nodes.items():
            inventory = finite_map[node_id]
            if type(inventory) is not FiniteCaloricPipeReservoir:
                raise TypeError("Finite-reservoir nodes require FiniteCaloricPipeReservoir values")
            if (inventory.node_id != node_id or inventory.state_owner_id != node.state_owner_id
                    or inventory.state_evidence_id != node.evidence_id
                    or inventory.origin is not node.origin):
                raise ValueError("Finite reservoir node, owner, evidence, and origin must match exactly")
            if inventory.clock_id != self.clock_id:
                raise ValueError("Finite reservoir and network use different clock identities")
            inventory.require_eos(self.eos)
            inventory.initial_state(self.eos)
            finite_mass[node_id] = inventory.mass_kg
            finite_energy[node_id] = inventory.internal_energy_j
        nozzle_map = {} if finite_reservoir_nozzles is None else dict(finite_reservoir_nozzles)
        if not set(nozzle_map) <= set(finite_nodes):
            raise ValueError("Nozzle couplings may only target finite caloric reservoir nodes")
        if any(type(value) is not CaloricFiniteReservoirNozzleCoupling
               for value in nozzle_map.values()):
            raise TypeError("Finite caloric reservoir nozzles require typed coupling contracts")
        for node_id, coupling in nozzle_map.items():
            incident = [edge for edge in self.edges
                                              if edge.start_node_id == node_id or edge.end_node_id == node_id]
            if len(incident) != 1:
                raise ValueError("Each finite reservoir nozzle requires one incident pipe edge")
            coupling.require_compatible(
                reservoir=finite_map[node_id], eos=self.eos, clock_id=self.clock_id,
                node_coordinates_m=node_by_id[node_id].coordinates_m,
                edge_id=incident[0].identifier,
            )
        nozzle_fingerprints = {
            key: (value.identifier, value.node_id, value.reservoir_id, value.edge_id,
                  value.opening, value.opening_fraction, value.back_pressure_pa,
                  value.location, value.nozzle, value.state_owner_id, value.evidence_id,
                  value.origin, value.density_relative_tolerance,
                  value.density_absolute_tolerance_kg_m3)
            for key, value in nozzle_map.items()
        }
        friction_map = {} if darcy_friction_laws is None else dict(darcy_friction_laws)
        wall_map = {} if wall_heat_boundaries is None else dict(wall_heat_boundaries)
        if not set(friction_map) <= edge_ids or not set(wall_map) <= edge_ids:
            raise ValueError("Per-edge source maps may contain only declared edge IDs")
        for edge_id, law in friction_map.items():
            for name in ("identity", "state_owner_id", "evidence_id", "clock_id"):
                if not isinstance(getattr(law, name, None), str) or not getattr(law, name).strip():
                    raise ValueError(f"Friction law on {edge_id} must declare {name}")
            if not callable(getattr(law, "darcy_factor", None)):
                raise TypeError(f"Friction law on {edge_id} must implement darcy_factor")
            if law.clock_id != self.clock_id:
                raise ValueError(f"Friction law on {edge_id} uses a different clock")
        friction_fingerprints = {
            key: tuple(getattr(value, name) for name in
                       ("identity", "state_owner_id", "evidence_id", "clock_id"))
            for key, value in friction_map.items()
        }
        for edge_id, boundary in wall_map.items():
            if type(boundary) is not CaloricPipeWallHeatBoundary:
                raise TypeError(f"Wall heat boundary on {edge_id} must be CaloricPipeWallHeatBoundary")
            if boundary.clock_id != self.clock_id:
                raise ValueError(f"Wall heat boundary on {edge_id} uses a different clock")
        wall_fingerprints = {
            key: (value.identifier, value.state_owner_id, value.state_evidence_id,
                  value.clock_id, value.wall_temperature_k,
                  value.heat_transfer_coefficient_w_m2_k)
            for key, value in wall_map.items()
        }
        area = {edge.identifier: np.pi * edge.internal_diameter_m**2 / 4. for edge in self.edges}
        dx = {edge.identifier: edge.length_m / edge.cell_count for edge in self.edges}
        adjacency = {node.identifier: [] for node in self.nodes}
        state = {}
        for edge in self.edges:
            adjacency[edge.start_node_id].append((edge, 1))
            adjacency[edge.end_node_id].append((edge, -1))
            n = edge.cell_count
            p = np.asarray(tuple(initial_pressure_pa[edge.identifier]), dtype=float)
            t = np.asarray(tuple(initial_temperature_k[edge.identifier]), dtype=float)
            u = np.asarray(tuple(initial_velocity_m_s[edge.identifier]), dtype=float)
            if any(x.shape != (n,) for x in (p, t, u)) or any(not np.all(np.isfinite(x)) for x in (p, t, u)) or np.any(p <= 0.) or np.any(t <= 0.):
                raise ValueError(f"Initial cell fields for edge {edge.identifier} have invalid dimensions or values")
            states = [_require_gas_state(self.eos.state_pt(float(pi), float(ti)), self.eos,
                                         f"Initial edge {edge.identifier}")
                      for pi, ti in zip(p, t, strict=True)]
            rho = np.asarray([x.density_kg_m3 for x in states])
            e = np.asarray([x.internal_energy_j_kg for x in states])
            state[edge.identifier] = np.vstack((rho, rho*u, rho*(e + .5*u*u)))
        junction_guesses: dict[str, tuple[float, float]] = {}

        def port_flux(edge, orientation, node_state, q, boundary_velocity_m_s=0.):
            cell = 0 if orientation == 1 else -1
            rho, mom, energy = q[:, cell]
            u = mom/rho
            outward_u = orientation*u
            inside = np.asarray((rho, rho*outward_u, energy))
            ghost = CaloricPipeWaveModel._boundary_conserved(
                node_state, orientation*boundary_velocity_m_s)
            left, right = (ghost, inside) if orientation == 1 else (ghost, inside)
            # Both states are expressed in the local outward coordinate.
            prim_left, _ = CaloricPipeWaveModel._primitive(left[:, None], self.eos)
            prim_right, _ = CaloricPipeWaveModel._primitive(right[:, None], self.eos)
            outward = CaloricPipeWaveModel._rusanov(left[:, None], right[:, None],
                                                    prim_left, prim_right)[:, 0]
            edge_flux = np.asarray((orientation*outward[0], outward[1], orientation*outward[2]))
            return edge_flux, outward

        def junction_state(node, current):
            bounds_p, bounds_t = node.pressure_bounds_pa, node.temperature_bounds_k
            endpoints = []
            for edge, orientation in adjacency[node.identifier]:
                q = current[edge.identifier]
                cell = 0 if orientation == 1 else -1
                prim, thermo_states = CaloricPipeWaveModel._primitive(
                    q[:, cell:cell+1] if cell == 0 else q[:, -1:], self.eos)
                endpoints.append((edge, orientation, q, float(prim[3, 0]),
                                  float(self._temperature(prim, self.eos)), thermo_states[0]))
            guessed = junction_guesses.get(node.identifier)
            p_seed = (np.mean([item[3] for item in endpoints]) if guessed is None else guessed[0])
            t_seed = (np.mean([item[4] for item in endpoints]) if guessed is None else guessed[1])
            p0 = float(np.clip(p_seed, *bounds_p))
            t0 = float(np.clip(t_seed, *bounds_t))
            cell_mass_scale = 0.
            for edge, orientation, q, _p, _t, _state in endpoints:
                i = 0 if orientation == 1 else -1
                primitive, _ = CaloricPipeWaveModel._primitive(q[:, i:i+1] if i == 0 else q[:, -1:], self.eos)
                cell_mass_scale += area[edge.identifier]*float(primitive[0, 0])*(abs(float(primitive[1, 0])) + float(primitive[4, 0]))
            mscale = max(cell_mass_scale, 1.e-10)
            escale = mscale*1.e6
            def residual(log_state):
                pressure, temperature = np.exp(log_state)
                ghost_state = _require_gas_state(self.eos.state_pt(float(pressure), float(temperature)),
                                                 self.eos, f"Junction {node.identifier}")
                mass, energy = 0., 0.
                for edge, orientation, q, _p, _t, _state in endpoints:
                    _edge_flux, outward_flux = port_flux(edge, orientation, ghost_state, q)
                    mass += area[edge.identifier]*outward_flux[0]
                    energy += area[edge.identifier]*outward_flux[2]
                return np.asarray((mass/mscale, energy/escale))
            solution = least_squares(
                residual, np.log((p0, t0)), bounds=(np.log((bounds_p[0], bounds_t[0])),
                                                      np.log((bounds_p[1], bounds_t[1]))),
                xtol=self.junction_solver_tolerance, ftol=self.junction_solver_tolerance,
                gtol=self.junction_solver_tolerance, max_nfev=200,
            )
            p, t = np.exp(solution.x)
            values = residual(solution.x)
            mass_residual, energy_residual = values[0]*mscale, values[1]*escale
            if (not solution.success or abs(mass_residual) > self.junction_mass_tolerance_kg_s
                    or abs(energy_residual) > self.junction_energy_tolerance_w):
                raise FloatingPointError(
                    f"Junction {node.identifier} has no admitted conservative pressure/temperature state "
                    f"(mass residual {mass_residual:g} kg/s, energy residual {energy_residual:g} W)"
                )
            node_state = _require_gas_state(self.eos.state_pt(float(p), float(t)), self.eos,
                                            f"Junction {node.identifier}")
            entropy_out = entropy_in = 0.
            for edge, orientation, q, _p, _t, cell_state in endpoints:
                _flux, outward_flux = port_flux(edge, orientation, node_state, q)
                mass_rate = area[edge.identifier]*outward_flux[0]
                if mass_rate >= 0.:
                    entropy_out += mass_rate*node_state.entropy_j_kg_k
                else:
                    entropy_in += -mass_rate*cell_state.entropy_j_kg_k
            entropy_generation = entropy_out-entropy_in
            if entropy_generation < -self.junction_entropy_tolerance_w_k:
                raise FloatingPointError(
                    f"Junction {node.identifier} violates its adiabatic perfect-mixing entropy inequality"
                )
            junction_guesses[node.identifier] = (float(p), float(t))
            return node_state, mass_residual, energy_residual, max(0., entropy_generation)

        initial_mass, initial_energy = self._totals(state, area, dx)
        initial_mass += sum(finite_mass.values())
        initial_energy += sum(finite_energy.values())
        mass_external = energy_external = mass_junction = energy_junction = 0.
        cumulative_wall_heat = 0.
        output = {name: {edge.identifier: [] for edge in self.edges} for name in
                  ("pressure", "temperature", "density", "velocity", "face_mass", "face_energy")}
        node_output = {name: {node_id: [] for node_id in junctions} for name in
                       ("pressure", "temperature", "mass_residual", "energy_residual", "entropy_generation")}
        total_mass, total_energy, mass_ext, energy_ext, wall_heat_samples = [], [], [], [], []
        finite_output = {name: {node_id: [] for node_id in finite_nodes} for name in
                         ("mass", "internal_energy", "pressure", "temperature")}
        nozzle_mass_out = {node_id: 0. for node_id in nozzle_map}
        nozzle_energy_out = {node_id: 0. for node_id in nozzle_map}
        nozzle_mass_output = {node_id: [] for node_id in nozzle_map}
        nozzle_energy_output = {node_id: [] for node_id in nozzle_map}
        nozzle_time_samples = {node_id: [] for node_id in nozzle_map}
        nozzle_result_samples = {node_id: [] for node_id in nozzle_map}
        mass_junc, energy_junc, mass_resid, energy_resid = [], [], [], []
        max_cfl, steps, time = 0., 0, 0.

        # Junction fluxes share one node pressure and temperature; terminal
        # fluxes use their fixed reservoir state or a reflective wall.
        def refresh_fluxes():
            primitive = {edge.identifier: CaloricPipeWaveModel._primitive(state[edge.identifier], self.eos)[0]
                         for edge in self.edges}
            fluxes = {}
            for edge in self.edges:
                q, p = state[edge.identifier], primitive[edge.identifier]
                face = np.empty((3, edge.cell_count+1), dtype=float)
                for j in range(1, edge.cell_count):
                    face[:, j] = CaloricPipeWaveModel._rusanov(q[:, j-1:j], q[:, j:j+1],
                                                               p[:, j-1:j], p[:, j:j+1])[:, 0]
                fluxes[edge.identifier] = face
            junction_states = {node_id: junction_state(node, state)
                               for node_id, node in junctions.items()}
            terminal_rates = {}
            finite_rates = {}
            finite_states = {}
            nozzle_results = {}
            for edge in self.edges:
                q = state[edge.identifier]
                for node_id, orientation in ((edge.start_node_id, 1), (edge.end_node_id, -1)):
                    node = node_by_id[node_id]
                    face_idx = 0 if orientation == 1 else -1
                    if node.kind == "closed":
                        cell = 0 if orientation == 1 else -1
                        inside = q[:, cell]
                        reflected = inside*np.asarray((1., -1., 1.))
                        pl, _ = CaloricPipeWaveModel._primitive(reflected[:, None], self.eos)
                        pi, _ = CaloricPipeWaveModel._primitive(inside[:, None], self.eos)
                        # Rusanov arguments follow the edge's increasing axial
                        # coordinate. The ghost is left of a start wall and
                        # right of an end wall; reversing the latter changes
                        # momentum damping into unphysical amplification.
                        if orientation == 1:
                            wall_flux = CaloricPipeWaveModel._rusanov(
                                reflected[:, None], inside[:, None], pl, pi)
                        else:
                            wall_flux = CaloricPipeWaveModel._rusanov(
                                inside[:, None], reflected[:, None], pi, pl)
                        fluxes[edge.identifier][:, face_idx] = wall_flux[:, 0]
                    elif node.kind == "reservoir":
                        boundary = boundary_map[node_id]
                        edge_flux, outward = port_flux(edge, orientation, boundary.state, q,
                                                       boundary.velocity_m_s)
                        fluxes[edge.identifier][:, face_idx] = edge_flux
                        terminal_rates[node_id] = (area[edge.identifier]*outward[0],
                                                   area[edge.identifier]*outward[2])
                    elif node.kind == "finite_reservoir":
                        inventory = finite_map[node_id]
                        reservoir_state = inventory.recover_state(
                            mass_kg=finite_mass[node_id],
                            internal_energy_j=finite_energy[node_id], eos=self.eos,
                        )
                        coupling = nozzle_map.get(node_id)
                        if coupling is not None:
                            nozzle_results[node_id] = coupling.evaluate(
                                mass_kg=finite_mass[node_id],
                                internal_energy_j=finite_energy[node_id],
                                reservoir=inventory, eos=self.eos,
                            )
                        edge_flux, outward = port_flux(edge, orientation, reservoir_state, q)
                        fluxes[edge.identifier][:, face_idx] = edge_flux
                        finite_states[node_id] = reservoir_state
                        finite_rates[node_id] = (area[edge.identifier]*outward[0],
                                                 area[edge.identifier]*outward[2])
                    else:
                        ghost = junction_states[node_id][0]
                        edge_flux, _ = port_flux(edge, orientation, ghost, q)
                        fluxes[edge.identifier][:, face_idx] = edge_flux
            return (primitive, fluxes, junction_states, terminal_rates, finite_rates,
                    finite_states, nozzle_results)

        for sample_index, sample_time in enumerate(times):
            if sample_index:
                while time < float(sample_time):
                    (primitive, fluxes, node_states, terminal_rates, finite_rates,
                     finite_states, nozzle_results) = refresh_fluxes()
                    speeds = []
                    for edge in self.edges:
                        p = primitive[edge.identifier]
                        speeds.extend((np.abs(p[1]) + p[4]).tolist())
                        for node_id, orientation in ((edge.start_node_id, 1), (edge.end_node_id, -1)):
                            if node_by_id[node_id].kind == "junction":
                                speeds.append(node_states[node_id][0].speed_of_sound_m_s)
                            elif node_by_id[node_id].kind == "reservoir":
                                b = boundary_map[node_id]
                                speeds.append(abs(b.velocity_m_s)+b.state.speed_of_sound_m_s)
                            elif node_by_id[node_id].kind == "finite_reservoir":
                                speeds.append(finite_states[node_id].speed_of_sound_m_s)
                    max_speed = max(speeds)
                    dt = min(float(sample_time)-time,
                             self.maximum_cfl*min(dx.values())/max_speed)
                    for edge in self.edges:
                        boundary = wall_map.get(edge.identifier)
                        if boundary is None or boundary.heat_transfer_coefficient_w_m2_k == 0.:
                            continue
                        edge_states = CaloricPipeWaveModel._primitive(state[edge.identifier], self.eos)[1]
                        cv = _positive_cv(edge_states, "Network wall heat transfer")
                        thermal_rate = (4. * boundary.heat_transfer_coefficient_w_m2_k
                                        / edge.internal_diameter_m
                                        / (state[edge.identifier][0] * cv))
                        dt = min(dt, 0.5 / float(np.max(thermal_rate)))
                    if not np.isfinite(dt) or dt <= 0.:
                        raise FloatingPointError("Network CFL controller produced an invalid time step")
                    step_cfl = dt*max_speed/min(dx.values())
                    if step_cfl > self.maximum_cfl*(1.+1.e-12):
                        raise FloatingPointError("Network CFL limit was exceeded")
                    max_cfl = max(max_cfl, step_cfl)
                    for node_id, (mres, eres) in ((key, (value[1], value[2]))
                                                  for key, value in node_states.items()):
                        mass_junction += dt*mres
                        energy_junction += dt*eres
                    for node_id, rates in terminal_rates.items():
                        mass_external += dt*rates[0]
                        energy_external += dt*rates[1]
                    next_finite_mass = {}
                    next_finite_energy = {}
                    for node_id, (mass_rate, energy_rate) in finite_rates.items():
                        inventory = finite_map[node_id]
                        endpoint_edge, _orientation = adjacency[node_id][0]
                        endpoint_state = finite_states[node_id]
                        reservoir_velocity = mass_rate / (area[endpoint_edge.identifier]
                                                          * endpoint_state.density_kg_m3)
                        if abs(reservoir_velocity) >= endpoint_state.speed_of_sound_m_s:
                            raise FloatingPointError(
                                f"Finite reservoir endpoint {node_id} is sonic or supersonic"
                            )
                        next_mass, next_energy, _next_state = inventory.advance(
                            current_mass_kg=finite_mass[node_id],
                            current_internal_energy_j=finite_energy[node_id],
                            outward_mass_flow_kg_s=mass_rate,
                            outward_energy_flow_w=energy_rate,
                            nozzle_outflow_mass_flow_kg_s=(
                                0. if node_id not in nozzle_results
                                else nozzle_results[node_id].mass_flow_kg_s
                            ),
                            nozzle_withdrawal_energy_w=(
                                0. if node_id not in nozzle_results
                                else nozzle_results[node_id].withdrawal_energy_w
                            ),
                            duration_s=dt, eos=self.eos,
                        )
                        next_finite_mass[node_id] = next_mass
                        next_finite_energy[node_id] = next_energy
                    updated = {}
                    wall_heat_step = 0.
                    for edge in self.edges:
                        q = state[edge.identifier]
                        new = q-(dt/dx[edge.identifier])*(fluxes[edge.identifier][:, 1:]-fluxes[edge.identifier][:, :-1])
                        if not np.all(np.isfinite(new)) or np.any(new[0] <= 0.):
                            raise FloatingPointError("Caloric network update produced invalid conserved states")
                        law = friction_map.get(edge.identifier)
                        if law is not None:
                            next_primitive, next_states = CaloricPipeWaveModel._primitive(new, self.eos)
                            factors = np.asarray([
                                finite(law.darcy_factor(cell_state, float(velocity), edge.internal_diameter_m),
                                       "Darcy friction factor")
                                for cell_state, velocity in zip(next_states, next_primitive[1], strict=True)
                            ])
                            if np.any(factors < 0.):
                                raise ValueError("Darcy friction factors must be nonnegative")
                            relaxed_velocity = (next_primitive[1]
                                                / (1. + factors * np.abs(next_primitive[1]) * dt
                                                   / (2. * edge.internal_diameter_m)))
                            new[1] = new[0] * relaxed_velocity
                        boundary = wall_map.get(edge.identifier)
                        if boundary is not None:
                            _next_primitive, next_states = CaloricPipeWaveModel._primitive(new, self.eos)
                            if boundary.heat_transfer_coefficient_w_m2_k > 0.:
                                cv_next = _positive_cv(next_states, "Network wall heat transfer")
                                proposed_rate = (4. * boundary.heat_transfer_coefficient_w_m2_k
                                                 / edge.internal_diameter_m / (new[0] * cv_next))
                                if dt * float(np.max(proposed_rate)) > 0.5 + 1.e-12:
                                    raise RuntimeError(
                                        "Proposed network source step violates the wall heat stability bound"
                                    )
                            heat_rate_density = (
                                4. * boundary.heat_transfer_coefficient_w_m2_k / edge.internal_diameter_m
                                * (boundary.wall_temperature_k
                                   - np.asarray([cell_state.temperature_k for cell_state in next_states]))
                            )
                            new[2] += dt * heat_rate_density
                            wall_heat_step += (dt * area[edge.identifier] * dx[edge.identifier]
                                               * float(np.sum(heat_rate_density)))
                        updated[edge.identifier] = new
                    cumulative_wall_heat += wall_heat_step
                    for node_id, nozzle_result in nozzle_results.items():
                        nozzle_mass_out[node_id] += dt*nozzle_result.mass_flow_kg_s
                        nozzle_energy_out[node_id] += dt*nozzle_result.withdrawal_energy_w
                        nozzle_time_samples[node_id].append(float(time))
                        nozzle_result_samples[node_id].append(nozzle_result)
                    state = updated
                    finite_mass.update(next_finite_mass)
                    finite_energy.update(next_finite_energy)
                    time = min(float(sample_time), time+dt)
                    steps += 1
                    if steps > self.maximum_internal_steps:
                        raise RuntimeError("maximum_internal_steps reached before requested output times")
            (primitive, fluxes, node_states, _terminal_rates, _finite_rates,
             finite_states, _nozzle_results) = refresh_fluxes()
            for edge in self.edges:
                p, states = CaloricPipeWaveModel._primitive(state[edge.identifier], self.eos)
                output["pressure"][edge.identifier].append(p[3].copy())
                output["temperature"][edge.identifier].append(np.asarray([x.temperature_k for x in states]))
                output["density"][edge.identifier].append(state[edge.identifier][0].copy())
                output["velocity"][edge.identifier].append(p[1].copy())
                output["face_mass"][edge.identifier].append(fluxes[edge.identifier][0]*area[edge.identifier])
                output["face_energy"][edge.identifier].append(fluxes[edge.identifier][2]*area[edge.identifier])
            for node_id, (node_state, mres, eres, sgen) in node_states.items():
                node_output["pressure"][node_id].append(node_state.pressure_pa)
                node_output["temperature"][node_id].append(node_state.temperature_k)
                node_output["mass_residual"][node_id].append(mres)
                node_output["energy_residual"][node_id].append(eres)
                node_output["entropy_generation"][node_id].append(sgen)
            m, e = self._totals(state, area, dx)
            m += sum(finite_mass.values())
            e += sum(finite_energy.values())
            for node_id, reservoir_state in finite_states.items():
                finite_output["mass"][node_id].append(finite_mass[node_id])
                finite_output["internal_energy"][node_id].append(finite_energy[node_id])
                finite_output["pressure"][node_id].append(reservoir_state.pressure_pa)
                finite_output["temperature"][node_id].append(reservoir_state.temperature_k)
            total_mass.append(m)
            total_energy.append(e)
            for node_id in nozzle_map:
                nozzle_mass_output[node_id].append(nozzle_mass_out[node_id])
                nozzle_energy_output[node_id].append(nozzle_energy_out[node_id])
            mass_ext.append(mass_external)
            energy_ext.append(energy_external)
            mass_junc.append(mass_junction)
            energy_junc.append(energy_junction)
            mass_resid.append(m-initial_mass-mass_external-mass_junction
                              +sum(nozzle_mass_out.values()))
            energy_resid.append(e-initial_energy-energy_external-energy_junction-cumulative_wall_heat
                                +sum(nozzle_energy_out.values()))
            wall_heat_samples.append(cumulative_wall_heat)
        current_friction_fingerprints = {
            key: tuple(getattr(value, name) for name in
                       ("identity", "state_owner_id", "evidence_id", "clock_id"))
            for key, value in friction_map.items()
        }
        current_wall_fingerprints = {
            key: (value.identifier, value.state_owner_id, value.state_evidence_id,
                  value.clock_id, value.wall_temperature_k,
                  value.heat_transfer_coefficient_w_m2_k)
            for key, value in wall_map.items()
        }
        if friction_fingerprints != current_friction_fingerprints:
            raise ValueError("Friction law provenance changed during the network run")
        if wall_fingerprints != current_wall_fingerprints:
            raise ValueError("Wall heat boundary changed during the network run")
        current_nozzle_fingerprints = {
            key: (value.identifier, value.node_id, value.reservoir_id, value.edge_id,
                  value.opening, value.opening_fraction, value.back_pressure_pa,
                  value.location, value.nozzle, value.state_owner_id, value.evidence_id,
                  value.origin, value.density_relative_tolerance,
                  value.density_absolute_tolerance_kg_m3)
            for key, value in nozzle_map.items()
        }
        if nozzle_fingerprints != current_nozzle_fingerprints:
            raise ValueError("Finite-reservoir nozzle coupling changed during the network run")
        nozzle_histories = {}
        for node_id, coupling in nozzle_map.items():
            final_result = coupling.evaluate(
                mass_kg=finite_mass[node_id], internal_energy_j=finite_energy[node_id],
                reservoir=finite_map[node_id], eos=self.eos,
            )
            nozzle_time_samples[node_id].append(float(times[-1]))
            nozzle_result_samples[node_id].append(final_result)
            nozzle_histories[node_id] = SourceHistory(
                coupling.location, tuple(nozzle_time_samples[node_id]),
                tuple(nozzle_result_samples[node_id]), "window_end",
            )
        cell_centers = {edge.identifier: (np.arange(edge.cell_count)+.5)*dx[edge.identifier]
                        for edge in self.edges}
        return _issue_trace(
            time_s=times,
            pressure_pa={key: np.asarray(value) for key, value in output["pressure"].items()},
            temperature_k={key: np.asarray(value) for key, value in output["temperature"].items()},
            density_kg_m3={key: np.asarray(value) for key, value in output["density"].items()},
            velocity_m_s={key: np.asarray(value) for key, value in output["velocity"].items()},
            face_mass_flow_kg_s={key: np.asarray(value) for key, value in output["face_mass"].items()},
            face_energy_flow_w={key: np.asarray(value) for key, value in output["face_energy"].items()},
            junction_pressure_pa={key: np.asarray(value) for key, value in node_output["pressure"].items()},
            junction_temperature_k={key: np.asarray(value) for key, value in node_output["temperature"].items()},
            junction_mass_residual_kg_s={key: np.asarray(value) for key, value in node_output["mass_residual"].items()},
            junction_energy_residual_w={key: np.asarray(value) for key, value in node_output["energy_residual"].items()},
            junction_entropy_generation_w_k={key: np.asarray(value) for key, value in node_output["entropy_generation"].items()},
            total_mass_kg=np.asarray(total_mass), total_energy_j=np.asarray(total_energy),
            cumulative_terminal_mass_in_kg=np.asarray(mass_ext),
            cumulative_terminal_energy_in_j=np.asarray(energy_ext),
            cumulative_junction_mass_kg=np.asarray(mass_junc),
            cumulative_junction_energy_j=np.asarray(energy_junc),
            cumulative_wall_heat_in_j=np.asarray(wall_heat_samples),
            mass_balance_residual_kg=np.asarray(mass_resid),
            energy_balance_residual_j=np.asarray(energy_resid),
            edge_cell_centers_m=cell_centers,
            edge_lengths_m={edge.identifier: edge.length_m for edge in self.edges},
            edge_diameters_m={edge.identifier: edge.internal_diameter_m for edge in self.edges},
            edge_cell_counts={edge.identifier: edge.cell_count for edge in self.edges},
            edge_start_node_ids={edge.identifier: edge.start_node_id for edge in self.edges},
            edge_end_node_ids={edge.identifier: edge.end_node_id for edge in self.edges},
            edge_origins={edge.identifier: edge.origin for edge in self.edges},
            edge_geometry_owner_ids={edge.identifier: edge.geometry_owner_id for edge in self.edges},
            edge_geometry_evidence_ids={edge.identifier: edge.geometry_evidence_id for edge in self.edges},
            node_coordinates_m={node.identifier: node.coordinates_m for node in self.nodes},
            node_kinds={node.identifier: node.kind for node in self.nodes},
            node_origins={node.identifier: node.origin for node in self.nodes},
            node_state_owner_ids={node.identifier: node.state_owner_id for node in self.nodes},
            node_evidence_ids={node.identifier: node.evidence_id for node in self.nodes},
            reservoir_boundary_ids={key: value.identifier for key, value in boundary_map.items()},
            reservoir_boundary_states={key: value.state for key, value in boundary_map.items()},
            reservoir_boundary_velocities_m_s={key: value.velocity_m_s for key, value in boundary_map.items()},
            friction_law_ids={key: value.identity for key, value in friction_map.items()},
            friction_state_owner_ids={key: value.state_owner_id for key, value in friction_map.items()},
            friction_evidence_ids={key: value.evidence_id for key, value in friction_map.items()},
            wall_heat_boundary_ids={key: value.identifier for key, value in wall_map.items()},
            wall_heat_state_owner_ids={key: value.state_owner_id for key, value in wall_map.items()},
            wall_heat_evidence_ids={key: value.state_evidence_id for key, value in wall_map.items()},
            finite_reservoir_records=finite_map,
            finite_reservoir_nozzle_couplings=nozzle_map,
            finite_reservoir_mass_kg={key: np.asarray(value) for key, value in finite_output["mass"].items()},
            finite_reservoir_internal_energy_j={
                key: np.asarray(value) for key, value in finite_output["internal_energy"].items()
            },
            finite_reservoir_pressure_pa={
                key: np.asarray(value) for key, value in finite_output["pressure"].items()
            },
            finite_reservoir_temperature_k={
                key: np.asarray(value) for key, value in finite_output["temperature"].items()
            },
            finite_reservoir_nozzle_history=nozzle_histories,
            finite_reservoir_nozzle_coupling_ids={key: value.identifier for key, value in nozzle_map.items()},
            finite_reservoir_nozzle_state_owner_ids={key: value.state_owner_id for key, value in nozzle_map.items()},
            finite_reservoir_nozzle_evidence_ids={key: value.evidence_id for key, value in nozzle_map.items()},
            cumulative_nozzle_mass_out_kg={key: np.asarray(value) for key, value in nozzle_mass_output.items()},
            cumulative_nozzle_withdrawal_energy_j={
                key: np.asarray(value) for key, value in nozzle_energy_output.items()
            },
            clock_id=self.clock_id, eos_identity=_eos_identity(self.eos),
            property_basis=self.eos.basis, maximum_cfl=max_cfl, cfl_limit=self.maximum_cfl,
            _eos_provider=self.eos,
        )

    @staticmethod
    def _temperature(primitive, eos):
        rho, _u, e, _p, _a = primitive[:, 0]
        return eos.state_rho_u(float(rho), float(e)).temperature_k

    @staticmethod
    def _totals(state, areas, widths):
        mass = energy = 0.
        for edge_id, q in state.items():
            volume = areas[edge_id]*widths[edge_id]
            mass += float(np.sum(q[0])*volume)
            energy += float(np.sum(q[2])*volume)
        return mass, energy


__all__ = ["CaloricPipeNetworkNode", "CaloricPipeNetworkEdge",
           "CaloricPipeNetworkWaveTrace", "CaloricPipeNetworkWaveModel",
           "FiniteCaloricPipeReservoir"]
