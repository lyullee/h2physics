"""Independent finite inventory audit of existing native adsorption bed snapshots.

No bed dynamics, solid caloric law, free-volume EOS or excess-uptake correction is
introduced. Native stored energy is retained in its declared native reference.
"""

from dataclasses import dataclass, field

import numpy as np

from ..core import immutable_array, _real_numeric_array, finite
from .psa import BedFaceTransfers, BedSnapshot, PsaDynaBed


def _positive_cells(values, cells, label):
    array = np.array(_real_numeric_array(values, label), dtype=float, copy=True)
    if array.shape != (cells,) or not np.all(np.isfinite(array)) or np.any(array <= 0):
        raise ValueError(f"{label} requires one positive SI value per native cell")
    array = immutable_array(array, name="array")
    return array


@dataclass(frozen=True, slots=True)
class BedInventoryAudit:
    snapshot: BedSnapshot = field(repr=False)
    adsorbent_mass_kg_by_cell: np.ndarray
    free_volume_m3_by_cell: np.ndarray
    geometry_evidence_id: str
    gas_component_mol: np.ndarray
    adsorbed_component_mol: np.ndarray
    total_component_mol: np.ndarray
    native_inventory_residual_mol: np.ndarray
    native_stored_energy_j: float
    native_energy_reference_id: str
    molar_tolerance: float
    _captured: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.snapshot) is not BedSnapshot:
            raise TypeError("Inventory receipt must retain a native-adapter BedSnapshot")
        _validate_snapshot(self.snapshot)
        if self.snapshot.basis.loading_definition != "absolute":
            raise ValueError("Finite bed inventories require absolute uptake")
        if (not isinstance(self.geometry_evidence_id, str)
                or not self.geometry_evidence_id.strip()
                or self.native_energy_reference_id != self.snapshot.energy_reference_id):
            raise ValueError("Inventory receipt must retain geometry and source energy identities")
        masses = _positive_cells(
            self.adsorbent_mass_kg_by_cell,
            self.snapshot.gas_inventory_mol.shape[0], "adsorbent mass kg",
        )
        volumes = _positive_cells(
            self.free_volume_m3_by_cell,
            self.snapshot.gas_inventory_mol.shape[0], "free volume m3",
        )
        species_count = len(self.snapshot.basis.species)
        receipt_arrays = {}
        for name in (
            "gas_component_mol", "adsorbed_component_mol", "total_component_mol",
            "native_inventory_residual_mol",
        ):
            values = np.array(_real_numeric_array(getattr(self, name), name), dtype=float, copy=True)
            if (values.shape != (species_count,) or not np.all(np.isfinite(values))):
                raise ValueError("Inventory receipt vectors must match the finite species axis")
            values = immutable_array(values, name="values")
            receipt_arrays[name] = values
        tolerance = finite(self.molar_tolerance, "molar_tolerance")
        if tolerance < 0.:
            raise ValueError("Molar tolerance cannot be negative")
        energy = finite(self.native_stored_energy_j, "native stored energy J")
        if energy != self.snapshot.stored_energy_j:
            raise ValueError("Inventory receipt changed the native stored-energy value")
        gas = np.sum(self.snapshot.gas_inventory_mol, axis=0)
        adsorbed = np.sum(self.snapshot.loading_mol_kg*masses[:, None], axis=0)
        total = gas+adsorbed
        expected = {
            "gas_component_mol": gas,
            "adsorbed_component_mol": adsorbed,
            "total_component_mol": total,
            "native_inventory_residual_mol": self.snapshot.total_inventory_mol-total,
        }
        if any(not np.array_equal(receipt_arrays[name], value)
               for name, value in expected.items()):
            raise ValueError("Direct inventory receipt does not reconstruct from its native snapshot")
        object.__setattr__(self, "adsorbent_mass_kg_by_cell", masses)
        object.__setattr__(self, "free_volume_m3_by_cell", volumes)
        object.__setattr__(self, "molar_tolerance", tolerance)
        object.__setattr__(self, "native_stored_energy_j", energy)
        for name, value in receipt_arrays.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_captured", self._content())

    def _content(self):
        snapshot = self.snapshot
        arrays = (snapshot.gas_inventory_mol, snapshot.loading_mol_kg,
                  snapshot.temperature_k, snapshot.wall_temperature_k,
                  snapshot.pressure_pa, snapshot.mole_fractions,
                  snapshot.total_inventory_mol, self.adsorbent_mass_kg_by_cell,
                  self.free_volume_m3_by_cell, self.gas_component_mol,
                  self.adsorbed_component_mol, self.total_component_mol,
                  self.native_inventory_residual_mol)
        return (snapshot.basis, snapshot.energy_reference_id, snapshot.stored_energy_j,
                self.geometry_evidence_id, self.native_energy_reference_id,
                self.native_stored_energy_j, self.molar_tolerance,
                tuple((id(array), array.shape, array.dtype.str, array.tobytes()) for array in arrays))

    def require_current(self):
        if self._content() != self._captured:
            raise ValueError("Bed inventory source, geometry or receipt changed after capture")
        _validate_snapshot(self.snapshot)
        gas = np.sum(self.snapshot.gas_inventory_mol, axis=0)
        adsorbed = np.sum(self.snapshot.loading_mol_kg*self.adsorbent_mass_kg_by_cell[:, None], axis=0)
        if (not np.array_equal(gas, self.gas_component_mol)
                or not np.array_equal(adsorbed, self.adsorbed_component_mol)
                or not np.array_equal(gas+adsorbed, self.total_component_mol)
                or not np.array_equal(self.snapshot.total_inventory_mol-(gas+adsorbed),
                                     self.native_inventory_residual_mol)):
            raise ValueError("Bed inventory receipt no longer reconstructs its native source")
        return self

    @property
    def inventory_within_tolerance(self):
        self.require_current()
        return bool(np.all(np.abs(self.native_inventory_residual_mol) <= self.molar_tolerance))


def _validate_snapshot(snapshot):
    if type(snapshot) is not BedSnapshot:
        raise TypeError("Supply an actual native-adapter BedSnapshot")
    if (not isinstance(snapshot.energy_reference_id, str)
            or not snapshot.energy_reference_id.strip()):
        raise ValueError("Native bed snapshot needs an explicit energy reference")
    ns = len(snapshot.basis.species)
    gas = np.asarray(snapshot.gas_inventory_mol)
    if gas.ndim != 2 or gas.shape[1] != ns or not len(gas):
        raise ValueError("Bed gas inventory must retain nonempty cell/species axes")
    cells = len(gas)
    loading = np.asarray(snapshot.loading_mol_kg)
    native_total = np.asarray(snapshot.total_inventory_mol)
    if (loading.shape != gas.shape or not np.all(np.isfinite(gas))
            or not np.all(np.isfinite(loading)) or np.any(gas < 0.)
            or np.any(loading < 0.)):
        raise ValueError("Bed gas inventory and absolute loading must be finite, nonnegative and aligned")
    if (native_total.shape != (ns,) or not np.all(np.isfinite(native_total))
            or np.any(native_total < 0.)):
        raise ValueError("Native total inventory must be finite on the species axis")
    for name in ("temperature_k", "wall_temperature_k", "pressure_pa"):
        values = np.asarray(getattr(snapshot, name))
        if values.shape != (cells,) or not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError(f"Native bed {name} must be positive per cell")
    fractions = np.asarray(snapshot.mole_fractions)
    if (fractions.shape != gas.shape or not np.all(np.isfinite(fractions))
            or np.any(fractions < 0) or np.any(fractions > 1)
            or not np.allclose(fractions.sum(axis=1), 1., rtol=0., atol=1e-12)):
        raise ValueError("Native bed composition must be normalized on cell/species axes")


def audit_bed_inventory(snapshot: BedSnapshot, *, adsorbent_mass_kg_by_cell,
                        free_volume_m3_by_cell, geometry_evidence_id, molar_tolerance):
    """Reconstruct gas-plus-absolute-loading inventory from declared cell geometry.

    Snapshot gas entries are already mol per cell, not concentration. Free volume
    is retained as explicit geometric evidence; it never rescales those gas entries.
    ``loading_mol_kg`` has cell/species axes and is weighted by each cell's declared
    adsorbent mass. The residual compares against the native total inventory without
    changing that output or inventing a missing native solid-energy law.
    """
    if type(snapshot) is not BedSnapshot:
        raise TypeError("Retain an actual native-adapter BedSnapshot")
    _validate_snapshot(snapshot)
    if snapshot.basis.loading_definition != "absolute":
        raise ValueError("Finite bed inventories require absolute uptake")
    if (not isinstance(geometry_evidence_id, str) or not geometry_evidence_id.strip()
            or not isinstance(snapshot.energy_reference_id, str)
            or not snapshot.energy_reference_id.strip()):
        raise ValueError("Declare geometry and native energy-reference evidence")
    gas = np.asarray(snapshot.gas_inventory_mol)
    loading = np.asarray(snapshot.loading_mol_kg)
    ns = len(snapshot.basis.species)
    if gas.ndim != 2 or gas.shape[1] != ns or loading.shape != gas.shape:
        raise ValueError("Bed inventory/loading must have native cell/species axes")
    cells = gas.shape[0]
    masses = _positive_cells(adsorbent_mass_kg_by_cell, cells, "adsorbent mass kg")
    volumes = _positive_cells(free_volume_m3_by_cell, cells, "free volume m3")
    tolerance = finite(molar_tolerance, "molar_tolerance")
    if tolerance < 0:
        raise ValueError("Molar tolerance cannot be negative")
    if (not np.all(np.isfinite(gas)) or not np.all(np.isfinite(loading))
            or np.any(gas < 0) or np.any(loading < 0)):
        raise ValueError("Absolute gas and adsorbed inventories must be finite and nonnegative")
    native = np.asarray(snapshot.total_inventory_mol)
    if native.shape != (ns,) or not np.all(np.isfinite(native)) or np.any(native < 0):
        raise ValueError("Native total inventory must retain the declared species axis")
    gas_total = np.sum(gas, axis=0)
    adsorbed = np.sum(loading*masses[:, None], axis=0)
    total = gas_total+adsorbed
    arrays = []
    for value in (gas_total, adsorbed, total, native-total):
        array = np.array(value, copy=True)
        if not np.all(np.isfinite(array)):
            raise ValueError("Bed inventory reconstruction overflowed")
        array = immutable_array(array, name="array")
        arrays.append(array)
    energy = finite(snapshot.stored_energy_j, "native stored energy J")
    return BedInventoryAudit(snapshot, masses, volumes, geometry_evidence_id,
                             *arrays, energy, snapshot.energy_reference_id, tolerance)


@dataclass(frozen=True, slots=True)
class BedRateLedger:
    """One native RHS observation; a rate is not an accepted trajectory step."""

    owner: PsaDynaBed = field(repr=False)
    time_s: float
    clock_id: str
    native_state: np.ndarray = field(repr=False)
    transfers: BedFaceTransfers
    inventory: BedInventoryAudit
    native_rates: object = field(repr=False)
    state_derivative_per_s: np.ndarray
    component_inventory_rate_mol_s: np.ndarray
    boundary_component_rate_mol_s: np.ndarray
    component_rate_residual_mol_s: np.ndarray
    boundary_enthalpy_rate_w: float
    native_ambient_heat_rate_w: float
    native_geometry_evidence_id: str


class BedRateLedgerError(RuntimeError):
    def __init__(self, cause, owner, state, transfers, snapshot=None, native_rates=None):
        self.cause = cause
        self.owner = owner
        self.native_state = state
        self.transfers = transfers
        self.snapshot = snapshot
        self.native_rates = native_rates
        super().__init__("Native adsorption rate-ledger observation failed")


def observe_bed_rates(owner, native_state, transfers, *, time_s, clock_id,
                      native_geometry_evidence_id, inventory_tolerance_mol):
    """Observe existing native rates and independently sum species inventories.

    This uses the reviewed loading-LDF layout: gas mol, adsorbent mol/kg, bed K,
    wall K per cell. Positive face transfers point along increasing cell index;
    first-face minus last-face is the net boundary input. Native rate outputs are
    retained unchanged, including any additional native outputs. Boundary enthalpy
    alone is not total stored-energy rate: native ambient/wall heat remains owned
    by the bed and is not silently set to zero. Use ``PsaDynaCycle.run`` for actual
    native cycle integration rather than treating this observation as a driver.
    """
    if type(owner) is not PsaDynaBed or type(transfers) is not BedFaceTransfers:
        raise TypeError("Use the existing native bed owner and explicit face transfers")
    for value in (clock_id, native_geometry_evidence_id):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Declare physical clock and native geometry evidence")
    time = finite(time_s, "time_s")
    state = np.array(_real_numeric_array(native_state, "native state"), dtype=float, copy=True)
    state = immutable_array(state, name="state")
    snapshot = raw_rates = None
    try:
        native = owner.native_bed
        snapshot = owner.snapshot(state)
        inventory = audit_bed_inventory(
            snapshot, adsorbent_mass_kg_by_cell=native.mass,
            free_volume_m3_by_cell=native.vgas,
            geometry_evidence_id=native_geometry_evidence_id,
            molar_tolerance=inventory_tolerance_mol,
        )
        raw_rates = owner.rates(state, transfers)
        # Reviewed native Bed.rates returns the flat derivative and ambient heat.
        if not isinstance(raw_rates, tuple) or len(raw_rates) != 2:
            raise TypeError("Native bed rates must retain derivative and ambient-heat outputs")
        derivative = np.array(raw_rates[0], dtype=float, copy=True)
        if derivative.shape != state.shape or not np.all(np.isfinite(derivative)):
            raise ValueError("Native derivative must match the finite state vector")
        if native.nv != 2*native.ns+2:
            raise ValueError("Native bed state layout differs from reviewed loading-LDF contract")
        rows = derivative.reshape(native.n, native.nv)
        inventory_rate = np.sum(rows[:, :native.ns]
                                + rows[:, native.ns:2*native.ns]*inventory.adsorbent_mass_kg_by_cell[:, None], axis=0)
        boundary_rate = transfers.component_mol_s[0]-transfers.component_mol_s[-1]
        residual = inventory_rate-boundary_rate
        arrays = []
        for value in (derivative, inventory_rate, boundary_rate, residual):
            array = np.array(value, copy=True)
            if not np.all(np.isfinite(array)):
                raise ValueError("Native rate-ledger sum overflowed")
            array = immutable_array(array, name="array")
            arrays.append(array)
        return BedRateLedger(owner, time, clock_id, state, transfers, inventory, raw_rates,
                             *arrays, float(transfers.enthalpy_w[0]-transfers.enthalpy_w[-1]),
                             finite(raw_rates[1], "native ambient heat W"),
                             native_geometry_evidence_id)
    except Exception as cause:
        raise BedRateLedgerError(cause, owner, state, transfers, snapshot, raw_rates) from cause


__all__ = ["BedInventoryAudit", "audit_bed_inventory", "BedRateLedger",
           "BedRateLedgerError", "observe_bed_rates"]
