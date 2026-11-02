"""Conditional premixed material-frame network front; implemented_unverified.

Native Cantera owns premixed flame speeds and HP chemistry. Native SciPy owns
shortest paths. This is a discrete material-coordinate reference, not a solved
Eulerian accident flame, obstacle-flow solver or thermal-injury model.
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from ..core import finite, immutable_array
from .cantera import (
    CanteraGas,
    EquilibriumResult,
    FreeFlameResult,
    NativePhaseBinding,
    NativePhaseHandle,
    ReactiveState,
)

STATUS = "implemented_unverified"

_PENDING_FRONT_TRACE_ISSUERS: set[object] = set()


def _issue_front_trace(**values):
    token = object()
    _PENDING_FRONT_TRACE_ISSUERS.add(token)
    try:
        return FlashFrontTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_FRONT_TRACE_ISSUERS.discard(token)
        raise


def _front_trace_content(trace):
    references = {id(cell.reference): cell.reference for cell in trace.cells}
    references.update({id(contact.native_reference): contact.native_reference for contact in trace.contacts})
    for reference in references.values():
        reference.guard()
    digest = hashlib.sha256()
    digest.update(repr((tuple((id(cell), cell.identifier, cell.lattice_index,
                              id(cell.reference), _reference_binding(cell.reference))
                             for cell in trace.cells),
                       trace.spacing_m, trace.ignition_cell_ids, trace.ignition_s,
                       trace.horizon_s, trace.clock_projection_tolerance_s,
                       tuple(dict(trace.arrival_s).items()),
                       tuple((id(burn), id(burn.cell), burn.arrival_s, burn.initial_volume_m3,
                              burn.expanded_hp_volume_m3, burn.mixture_mass_kg,
                              burn.initial_hydrogen_kg, burn.final_hydrogen_kg,
                              burn.hydrogen_consumed_kg, burn.internal_energy_change_j,
                              burn.pressure_work_out_j, burn.total_energy_residual_j,
                              burn.maximum_element_mass_residual_kg, id(burn.hp_result))
                             for burn in trace.burned_cells),
                       tuple((id(contact), id(contact.contact), contact.front_arrival_s,
                              contact.band_end_s, contact.overlap_s,
                              id(contact.native_reference), _reference_binding(contact.native_reference))
                             for contact in trace.contacts),
                       trace.initial_cloud_mass_kg, trace.burned_mixture_mass_kg,
                       trace.unburned_mixture_mass_kg, trace.mass_residual_kg,
                       trace.total_energy_residual_j, trace.laboratory_flame_prediction,
                       trace.radiation_or_injury_prediction, id(trace.native_sparse_graph))).encode("utf-8"))
    graph = trace.native_sparse_graph
    for values in (graph.data, graph.indices, graph.indptr, trace.native_travel_times_s,
                   trace.native_predecessors, trace.native_sources):
        array = np.asarray(values)
        digest.update(repr((array.shape, array.dtype.str)).encode("utf-8"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _text(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Declare nonempty identity, clock, frame and applicability evidence")


def _readonly(values, *, dtype=float):
    result = np.array(values, dtype=dtype, copy=True)
    result = immutable_array(result, name="result")
    return result


def _flame_digest(result):
    flame = result.native_solution
    digest = hashlib.sha256()
    digest.update(repr((result.basis, result.settings, result.speed_m_s,
                        result.grid_points, result.relative_mass_flux_span,
                        flame.transport_model, flame.soret_enabled)).encode())
    for values in (flame.grid, flame.T, flame.velocity, flame.X, flame.density_mass,
                   (flame.P, flame.inlet.T), flame.inlet.X):
        array = np.asarray(values, dtype='<f8')
        digest.update(repr(array.shape).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _phase_digest(phase):
    values = np.asarray((phase.T, phase.P, phase.density_mass, phase.enthalpy_mass,
                         phase.int_energy_mass, *phase.Y, *phase.molecular_weights), dtype='<f8')
    digest = hashlib.sha256(repr((phase.name, phase.thermo_model, phase.species_names)).encode())
    digest.update(values.tobytes())
    return digest.hexdigest()


def _reference_binding(reference):
    return (reference.identifier, id(reference.gas_owner), id(reference.flame_result),
        id(reference.admission), id(reference.initial), id(reference.hp_result),
        id(reference.unburned_phase), id(reference.burned_phase), reference.speed_m_s,
        reference.thermal_band_residence_s, reference.flame_sha256,
        reference.unburned_sha256, reference.burned_sha256,
        id(reference.flame_source_binding), id(reference.unburned_binding), id(reference.burned_binding),
        reference.thermal_progress_time_s.tobytes(),
        reference.thermal_progress_temperature_k.tobytes())


@dataclass(frozen=True)
class FrontAdmission:
    evidence_id: str
    material_frame_id: str
    clock_id: str
    mixture_evidence_id: str
    native_flame_qualification_id: str
    low_temperature_progress: float
    high_temperature_progress: float
    minimum_temperature_rise_k: float
    maximum_relative_mass_flux_span: float
    maximum_hp_residual_j_kg: float
    maximum_element_residual: float

    def __post_init__(self):
        _text(self.evidence_id, self.material_frame_id, self.clock_id,
              self.mixture_evidence_id, self.native_flame_qualification_id)
        low = finite(self.low_temperature_progress, "low_temperature_progress")
        high = finite(self.high_temperature_progress, "high_temperature_progress")
        if not 0 < low < high < 1:
            raise ValueError("Declare strictly interior ordered thermal progress levels")
        for name in ("minimum_temperature_rise_k", "maximum_relative_mass_flux_span",
                     "maximum_hp_residual_j_kg", "maximum_element_residual"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True)
class NativePremixedReference:
    identifier: str
    gas_owner: CanteraGas
    flame_result: FreeFlameResult
    admission: FrontAdmission
    initial: ReactiveState
    hp_result: EquilibriumResult
    unburned_phase: object
    burned_phase: object
    speed_m_s: float
    thermal_band_residence_s: float
    thermal_progress_time_s: np.ndarray
    thermal_progress_temperature_k: np.ndarray
    flame_sha256: str
    unburned_sha256: str
    burned_sha256: str
    flame_source_binding: NativePhaseBinding
    unburned_binding: NativePhaseBinding
    burned_binding: NativePhaseBinding
    _binding: object = field(default=None, repr=False, compare=False)

    def guard(self):
        self.flame_result.require_current()
        self.hp_result.require_current()
        for binding in (self.flame_source_binding, self.unburned_binding, self.burned_binding):
            binding.require_current()
        if (self._binding is None or _reference_binding(self) != self._binding
                or _flame_digest(self.flame_result) != self.flame_sha256
                or _phase_digest(self.unburned_phase) != self.unburned_sha256
                or _phase_digest(self.burned_phase) != self.burned_sha256
                or self.gas_owner.basis != self.flame_result.basis):
            raise ValueError("Original native flame/thermodynamic reference was changed")


def _premixed_reference(identifier, gas_owner, flame_result, admission, attempt):
    """Bind an actual completed native flame and native HP material endpoint.

    Thermal-band residence integrates native axial gas travel through the
    selected temperature band. It is neither a radiant dose nor a flame length
    divided by an inferred accident propagation velocity.
    """
    _text(identifier)
    if not isinstance(gas_owner, CanteraGas) or not isinstance(flame_result, FreeFlameResult):
        raise TypeError("Actual CanteraGas and FreeFlameResult objects are required")
    if not isinstance(admission, FrontAdmission) or gas_owner.basis != flame_result.basis:
        raise ValueError("Bind an admission and matching native mechanism evidence")
    flame_result.require_current()
    flame = flame_result.native_solution
    if not isinstance(flame, gas_owner.ct.FreeFlame):
        raise TypeError("A completed native Cantera FreeFlame is required")
    source_handle = flame_result.native_phase_handle
    if (not isinstance(source_handle, NativePhaseHandle) or source_handle.owner is not gas_owner
            or source_handle.native_phase is not flame.gas):
        raise ValueError("Retain the native flame's original public source phase handle")
    source_binding = gas_owner.bind_phase(source_handle, freeze_state=False)
    attempt["flame_source_binding"] = source_binding
    before = _flame_digest(flame_result)
    speed = finite(float(flame.velocity[0]), "native premixed speed", positive=True)
    if speed != flame_result.speed_m_s or len(flame.grid) != flame_result.grid_points:
        raise ValueError("Native flame summary does not match the actual solution")
    flux = np.asarray(flame.density_mass)*np.asarray(flame.velocity)
    span = float(np.ptp(flux)/max(abs(flux)))
    if (not np.isfinite(span) or span > admission.maximum_relative_mass_flux_span
            or abs(span-flame_result.relative_mass_flux_span) > 1e-12):
        raise ValueError("Native premixed mass-flux gate failed")
    temperature = np.asarray(flame.T, dtype=float)
    velocity = np.asarray(flame.velocity, dtype=float)
    grid = np.asarray(flame.grid, dtype=float)
    if (not np.all(np.isfinite(grid)) or np.any(np.diff(grid) <= 0) or np.any(np.diff(temperature) < 0)
            or not np.all(np.isfinite(temperature)) or np.any(velocity <= 0)
            or not np.all(np.isfinite(velocity))):
        raise ValueError("This thermal-band reference needs a monotone positive-flow flame")
    rise = float(temperature[-1]-temperature[0])
    if rise < admission.minimum_temperature_rise_k:
        raise ValueError("Native flame has no admitted burning temperature rise")
    low = temperature[0]+admission.low_temperature_progress*rise
    high = temperature[0]+admission.high_temperature_progress*rise
    # Locate crossings without a correlation or an empirical flame-thickness fit.
    def crossing(value):
        upper = int(np.searchsorted(temperature, value, side="left"))
        lower = upper-1
        fraction = (value-temperature[lower])/(temperature[upper]-temperature[lower])
        return float(grid[lower]+fraction*(grid[upper]-grid[lower]))

    left, right = crossing(low), crossing(high)
    positions = np.concatenate(([left], grid[(grid > left) & (grid < right)], [right]))
    local_velocity = np.interp(positions, grid, velocity)
    increments = np.diff(positions)*(.5/local_velocity[:-1]+.5/local_velocity[1:])
    times = np.concatenate(([0.], np.cumsum(increments)))
    duration = finite(float(times[-1]), "native thermal-band residence", positive=True)
    names = flame.gas.species_names
    fractions = dict(zip(names, np.asarray(flame.inlet.X, dtype=float), strict=True))
    initial = ReactiveState(float(flame.inlet.T), float(flame.P), fractions)
    created = source_handle.creation_snapshot.state
    if (not np.isclose(initial.temperature_k, created.temperature_k, rtol=1e-12, atol=1e-12)
            or not np.isclose(initial.pressure_pa, created.pressure_pa, rtol=1e-12, atol=1e-12)
            or max(abs(fractions[name]-created.mole_fractions.get(name, 0.)) for name in fractions) > 1e-12):
        raise ValueError("Native flame inlet no longer matches its public factory creation state")
    if initial.mole_fractions.get("H2", 0.) <= 0 or initial.mole_fractions.get("O2", 0.) <= 0:
        raise ValueError("This reference requires explicitly premixed hydrogen and oxygen")
    admitted = {"H2", "O2", "N2", "AR", "HE", "H2O", "CO2"}
    if any(value > 0 and name not in admitted for name, value in fractions.items()):
        raise ValueError("Initial reactive radicals or additional fuels require another qualified model level")
    unburned_handle = gas_owner.create_phase(initial)
    unburned = unburned_handle.native_phase
    attempt["unburned_phase"] = unburned
    unburned_binding = gas_owner.bind_phase(unburned_handle, freeze_state=True)
    attempt["unburned_binding"] = unburned_binding
    try:
        hp = gas_owner.equilibrium(initial, constraint="HP")
    except Exception:
        attempt["failed_hp_phase_handle"] = gas_owner.last_legacy_phase_handle
        raise
    attempt["hp_result"] = hp
    burned_handle = gas_owner.create_phase(hp.final.state)
    burned = burned_handle.native_phase
    attempt["burned_phase"] = burned
    burned_binding = gas_owner.bind_phase(burned_handle, freeze_state=True)
    attempt["burned_binding"] = burned_binding
    if unburned is burned:
        raise ValueError("Native factory reused the unburned phase as a mutable burned phase")
    hp_energy = finite(hp.energy_residual_j_kg, "native HP residual")
    hp_element = finite(hp.maximum_element_mass_fraction_residual, "native element residual")
    if (abs(hp_energy) > admission.maximum_hp_residual_j_kg or hp_element < 0
            or hp_element > admission.maximum_element_residual):
        raise ValueError("Native HP energy/element gate failed")
    for phase in (unburned, burned):
        finite(float(phase.density_mass), "native phase density", positive=True)
        finite(float(phase.enthalpy_mass), "native phase enthalpy")
        finite(float(phase.int_energy_mass), "native phase internal energy")
    if _flame_digest(flame_result) != before:
        raise ValueError("Native flame changed while constructing its reference")
    reference = NativePremixedReference(identifier, gas_owner, flame_result, admission, initial,
        hp, unburned, burned, speed, duration, _readonly(times),
        _readonly(np.interp(positions, grid, temperature)), before,
        _phase_digest(unburned), _phase_digest(burned), source_binding,
        unburned_binding, burned_binding)
    object.__setattr__(reference, "_binding", _reference_binding(reference))
    return reference


class PremixedReferenceError(RuntimeError):
    def __init__(self, cause, flame_result, native_attempt):
        super().__init__(str(cause))
        self.cause = cause
        self.flame_result = flame_result
        self.native_attempt = MappingProxyType(dict(native_attempt))


def premixed_reference(identifier: str, gas_owner: CanteraGas,
                       flame_result: FreeFlameResult, admission: FrontAdmission) -> NativePremixedReference:
    """Bind native premixed flame/HP objects and preserve construction failures."""
    attempt = {}
    try:
        return _premixed_reference(identifier, gas_owner, flame_result, admission, attempt)
    except Exception as error:
        raise PremixedReferenceError(error, flame_result, attempt) from error


@dataclass(frozen=True)
class FrontCell:
    identifier: str
    lattice_index: tuple
    reference: NativePremixedReference

    def __post_init__(self):
        _text(self.identifier)
        index = tuple(self.lattice_index)
        if len(index) != 3 or any(isinstance(v, bool) or not isinstance(v, int) for v in index):
            raise ValueError("A front cell needs three integer material-lattice indices")
        if not isinstance(self.reference, NativePremixedReference):
            raise TypeError("Bind an actual native premixed reference")
        object.__setattr__(self, "lattice_index", index)


@dataclass(frozen=True)
class CellBurn:
    cell: FrontCell
    arrival_s: float
    initial_volume_m3: float
    expanded_hp_volume_m3: float
    mixture_mass_kg: float
    initial_hydrogen_kg: float
    final_hydrogen_kg: float
    hydrogen_consumed_kg: float
    internal_energy_change_j: float
    pressure_work_out_j: float
    total_energy_residual_j: float
    maximum_element_mass_residual_kg: float
    hp_result: EquilibriumResult


@dataclass(frozen=True)
class MaterialContact:
    receptor_id: str
    cell_id: str
    occupancy_start_s: float
    occupancy_end_s: float
    evidence_id: str

    def __post_init__(self):
        _text(self.receptor_id, self.cell_id, self.evidence_id)
        if finite(self.occupancy_end_s, "occupancy_end_s") <= finite(self.occupancy_start_s, "occupancy_start_s"):
            raise ValueError("Declare an increasing material-contact occupancy window")


@dataclass(frozen=True)
class ContactResult:
    contact: MaterialContact
    front_arrival_s: float | None
    band_end_s: float | None
    overlap_s: float
    native_reference: NativePremixedReference


@dataclass(frozen=True)
class FlashFrontTrace:
    cells: tuple
    spacing_m: tuple
    ignition_cell_ids: tuple
    ignition_s: float
    horizon_s: float
    clock_projection_tolerance_s: float
    arrival_s: object
    native_sparse_graph: object
    native_travel_times_s: np.ndarray
    native_predecessors: np.ndarray
    native_sources: np.ndarray
    burned_cells: tuple
    contacts: tuple
    initial_cloud_mass_kg: float
    burned_mixture_mass_kg: float
    unburned_mixture_mass_kg: float
    mass_residual_kg: float
    total_energy_residual_j: float
    laboratory_flame_prediction: bool = False
    radiation_or_injury_prediction: bool = False
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _issuer_seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_FRONT_TRACE_ISSUERS:
            raise ValueError("Flash-front traces are issued only by the native front driver")
        _PENDING_FRONT_TRACE_ISSUERS.remove(token)
        object.__setattr__(self, "cells", tuple(self.cells))
        object.__setattr__(self, "spacing_m", tuple(self.spacing_m))
        object.__setattr__(self, "ignition_cell_ids", tuple(self.ignition_cell_ids))
        object.__setattr__(self, "burned_cells", tuple(self.burned_cells))
        object.__setattr__(self, "contacts", tuple(self.contacts))
        object.__setattr__(self, "_issuer_seal", _front_trace_content(self))

    def require_current(self):
        if _front_trace_content(self) != self._issuer_seal:
            raise ValueError("Flash-front trace or native result lineage changed after issuance")
        return self


class FlashFrontError(RuntimeError):
    def __init__(self, cause, completed_burns, native_graph=None, native_paths=None):
        super().__init__(str(cause))
        self.cause = cause
        self.completed_burns = tuple(completed_burns)
        self.native_graph = native_graph
        self.native_paths = native_paths


def run_material_front(cells: Iterable[FrontCell], *, spacing_m: tuple[float, float, float],
                       ignition_cell_ids: Iterable[str], ignition_s: float,
                       horizon_s: float, clock_projection_tolerance_s: float,
                       contacts: Iterable[MaterialContact] = ()) -> FlashFrontTrace:
    """Lumped cell ignition along face-connected material-coordinate paths.

    Each edge traverses half a cell at each cell's native unburned flame speed.
    Six-neighbor paths retain lattice directional bias; no claim of continuum
    eikonal convergence, obstacle flow, expansion-induced advection or lab-frame
    receptor position is made. A missing cell is an absent path, not a CFD wall.
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra

    completed, graph, paths = [], None, None
    try:
        cells = tuple(cells)
        if not cells or not all(isinstance(cell, FrontCell) for cell in cells):
            raise ValueError("Provide a nonempty native premixed material lattice")
        spacing = tuple(finite(x, "lattice spacing", positive=True) for x in spacing_m)
        if len(spacing) != 3:
            raise ValueError("Declare three positive lattice spacings in metres")
        ignition = finite(ignition_s, "ignition_s")
        horizon = finite(horizon_s, "horizon_s")
        clock_budget = finite(clock_projection_tolerance_s, "clock_projection_tolerance_s", positive=True)
        if horizon < ignition:
            raise ValueError("Horizon must not precede the declared ignition")

        def project_clock(start, span):
            end = finite(start+span, "projected front clock")
            if (span > 0 and end <= start) or abs((end-start)-span) > clock_budget:
                raise ValueError("Absolute clock cannot represent native positive travel/residence within its budget")
            return end
        ids = {cell.identifier: i for i, cell in enumerate(cells)}
        locations = {cell.lattice_index: i for i, cell in enumerate(cells)}
        if len(ids) != len(cells) or len(locations) != len(cells):
            raise ValueError("Cell identities and occupied lattice positions must be unique")
        records = {id(cell.reference): cell.reference for cell in cells}
        contexts = {(r.admission.clock_id, r.admission.material_frame_id) for r in records.values()}
        if len(contexts) != 1:
            raise ValueError("All material cells must share clock and reference frame")
        if len({r.initial.pressure_pa for r in records.values()}) != 1:
            raise ValueError("This quiescent material reference requires one common pressure")
        for reference in records.values():
            reference.guard()
        ignition_ids = tuple(ignition_cell_ids)
        if not ignition_ids or len(set(ignition_ids)) != len(ignition_ids) or set(ignition_ids)-ids.keys():
            raise ValueError("Declare distinct existing cell-centre ignition sites")
        rows, columns, weights = [], [], []
        for i, cell in enumerate(cells):
            for axis in range(3):
                neighbor = list(cell.lattice_index)
                neighbor[axis] += 1
                j = locations.get(tuple(neighbor))
                if j is None:
                    continue
                travel = finite(spacing[axis]/2*(1/cell.reference.speed_m_s+1/cells[j].reference.speed_m_s),
                                "native-speed edge time", positive=True)
                rows.extend((i, j))
                columns.extend((j, i))
                weights.extend((travel, travel))
        graph = csr_matrix((weights, (rows, columns)), shape=(len(cells), len(cells)))
        paths = dijkstra(graph, directed=True, indices=[ids[x] for x in ignition_ids],
                         min_only=True, return_predecessors=True)
        distances, predecessors, sources = paths
        if np.any(np.isnan(distances)) or np.any(distances < 0):
            raise ValueError("Native shortest paths returned inadmissible times")
        # Unreachable nodes remain None rather than adopting the final time.
        arrival = {cell.identifier: (project_clock(ignition, float(distances[i])) if np.isfinite(distances[i]) else None)
                   for i, cell in enumerate(cells)}
        volume = finite(float(np.prod(spacing)), "finite initial cell volume", positive=True)
        masses = [finite(cell.reference.unburned_binding.snapshot.density_kg_m3*volume,
                         "finite native cell mass", positive=True) for cell in cells]
        for cell, mass in zip(cells, masses, strict=True):
            time = arrival[cell.identifier]
            if time is None or time > horizon:
                continue
            reference = cell.reference
            unburned, burned = reference.unburned_phase, reference.burned_phase
            before_state, after_state = reference.unburned_binding.snapshot, reference.burned_binding.snapshot
            final_volume = finite(mass/after_state.density_kg_m3, "native HP volume", positive=True)
            work = reference.initial.pressure_pa*(final_volume-volume)
            change = mass*(after_state.internal_energy_j_kg-before_state.internal_energy_j_kg)
            if abs(finite(change+work, "native parcel energy residual")) > mass*reference.admission.maximum_hp_residual_j_kg:
                raise ValueError("Actual native U/expansion-work ledger exceeds its HP energy budget")
            initial_h2 = mass*float(unburned.Y[unburned.species_index("H2")])
            final_h2 = mass*float(burned.Y[burned.species_index("H2")])
            consumed = initial_h2-final_h2
            if consumed < 0:
                raise ValueError("Native HP endpoint creates net hydrogen; not an admitted fuel burn")
            completed.append(CellBurn(cell, time, volume, final_volume, mass, initial_h2,
                final_h2, consumed, change, work, change+work,
                mass*reference.hp_result.maximum_element_mass_fraction_residual,
                reference.hp_result))
        contact_results = []
        for contact in contacts:
            if not isinstance(contact, MaterialContact) or contact.cell_id not in ids:
                raise ValueError("Contacts must identify actual material cells")
            cell = cells[ids[contact.cell_id]]
            time = arrival[cell.identifier]
            end = None if time is None else project_clock(time, cell.reference.thermal_band_residence_s)
            overlap = 0. if time is None else max(0., min(end, horizon, contact.occupancy_end_s)-
                                                   max(time, ignition, contact.occupancy_start_s))
            contact_results.append(ContactResult(contact, time, end, overlap, cell.reference))
        for reference in records.values():
            reference.guard()
        total = sum(masses)
        burned_mass = sum(b.mixture_mass_kg for b in completed)
        remaining = sum(m for cell, m in zip(cells, masses, strict=True)
                        if arrival[cell.identifier] is None or arrival[cell.identifier] > horizon)
        return _issue_front_trace(cells=cells, spacing_m=spacing, ignition_cell_ids=ignition_ids,
            ignition_s=ignition, horizon_s=horizon, clock_projection_tolerance_s=clock_budget,
            arrival_s=MappingProxyType(arrival), native_sparse_graph=graph,
            native_travel_times_s=_readonly(distances),
            native_predecessors=_readonly(predecessors, dtype=predecessors.dtype),
            native_sources=_readonly(sources, dtype=sources.dtype), burned_cells=tuple(completed),
            contacts=tuple(contact_results), initial_cloud_mass_kg=total,
            burned_mixture_mass_kg=burned_mass, unburned_mixture_mass_kg=remaining,
            mass_residual_kg=total-burned_mass-remaining,
            total_energy_residual_j=sum(b.total_energy_residual_j for b in completed))
    except Exception as error:
        raise FlashFrontError(error, completed, graph, paths) from error
