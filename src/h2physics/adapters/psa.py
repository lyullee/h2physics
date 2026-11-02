"""SI boundary for the separately installed PSA-Dyna native equilibrium provider.

Reference API: https://github.com/lyullee/psa-dyna/tree/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6
The native solver and isotherms are not reproduced here. Engine inputs are
partial pressures in bar; the adapter exposes Pa and converts derivatives too.
"""

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass

import numpy as np


from ..adsorption import AdsorptionBasis, AdsorptionDomain, AdsorptionState
from ..core import immutable_array, finite


@dataclass(frozen=True, slots=True)
class BedFaceTransfers:
    species: tuple[str, ...]
    component_mol_s: np.ndarray
    enthalpy_w: np.ndarray
    energy_reference_id: str

    def __post_init__(self):
        species = tuple(self.species)
        components = np.array(self.component_mol_s, dtype=float, copy=True)
        energy = np.array(self.enthalpy_w, dtype=float, copy=True)
        if (components.ndim != 2 or components.shape[1] != len(species)
                or energy.shape != (len(components),) or not self.energy_reference_id
                or not np.all(np.isfinite(components)) or not np.all(np.isfinite(energy))):
            raise ValueError("Bed face transfers need finite, matching species/energy axes and an energy reference")
        for name, value in (("species", species), ("component_mol_s", components), ("enthalpy_w", energy)):
            if isinstance(value, np.ndarray):
                value = immutable_array(value, name="value")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class BedSnapshot:
    basis: AdsorptionBasis
    energy_reference_id: str
    gas_inventory_mol: np.ndarray
    loading_mol_kg: np.ndarray
    temperature_k: np.ndarray
    wall_temperature_k: np.ndarray
    pressure_pa: np.ndarray
    mole_fractions: np.ndarray
    total_inventory_mol: np.ndarray
    stored_energy_j: float

    def __post_init__(self):
        for name in ("gas_inventory_mol", "loading_mol_kg", "temperature_k", "wall_temperature_k",
                     "pressure_pa", "mole_fractions", "total_inventory_mol"):
            value = np.array(getattr(self, name), dtype=float, copy=True)
            value = immutable_array(value, name="value")
            object.__setattr__(self, name, value)
        finite(self.stored_energy_j, "native bed energy")


class PsaDynaBed:
    """Expose an existing loading-LDF native Bed to a Python composition solver.

    This adapter does not implement a PSA schedule or duplicate bed equations.
    The caller supplies all internal/boundary face transfers in the explicit
    native energy reference. Native ideal/PR energy is not a CoolProp reference.
    The caller owns the native bed configuration; changing it invalidates the
    declared basis/parameter evidence until that identity is updated.
    """

    def __init__(self, native_bed, basis: AdsorptionBasis, domain: AdsorptionDomain,
                 *, energy_reference_id: str):
        if len(basis.species) != native_bed.ns or not energy_reference_id:
            raise ValueError("Declare native bed species order and energy reference")
        if native_bed.mode != "loading_ldf" or basis.loading_definition != "absolute":
            raise ValueError("This adapter level requires loading LDF with an explicit absolute-uptake basis")
        self.native_bed, self.basis, self.domain = native_bed, basis, domain
        self.energy_reference_id = energy_reference_id

    def _checked_fields(self, state):
        native = self.native_bed
        state = np.asarray(state, dtype=float)
        if state.shape != (native.size,) or not np.all(np.isfinite(state)):
            raise ValueError("Native bed state must be a finite flat vector with the declared size")
        rows = state.reshape(native.n, native.nv)
        if np.any(rows[:, :2*native.ns] < 0):
            raise ValueError("Negative gas inventories/loadings cannot be hidden by the native field floor")
        fields = native.fields(state)
        for pressure, fractions, temperature in zip(fields[4], fields[5], fields[2], strict=True):
            self.domain.require_state(pressure*100_000.*fractions, temperature)
        return state, fields

    def snapshot(self, state) -> BedSnapshot:
        state, fields = self._checked_fields(state)
        inventory, energy = self.native_bed.inventory_energy(state)
        gas, loading, temperature, wall, pressure, fractions = fields
        return BedSnapshot(self.basis, self.energy_reference_id, gas, loading, temperature,
                            wall, pressure*100_000., fractions, inventory, energy)

    def rates(self, state, transfers: BedFaceTransfers):
        state, _ = self._checked_fields(state)
        if transfers.species != self.basis.species or transfers.energy_reference_id != self.energy_reference_id:
            raise ValueError("Bed transfer species order or energy reference differs")
        if transfers.component_mol_s.shape != (self.native_bed.n+1, self.native_bed.ns):
            raise ValueError("Supply one component transfer per native cell face")
        return self.native_bed.rates(state, transfers.component_mol_s, transfers.enthalpy_w)


class PsaDynaEquilibrium:
    def __init__(self, native_equilibrium: Callable, native_material: Mapping,
                 basis: AdsorptionBasis, domain: AdsorptionDomain):
        self._native_equilibrium = native_equilibrium
        self._native_material = deepcopy(dict(native_material))
        self._basis, self.domain = basis, domain
        native_order = self._native_material.get("species_order")
        if native_order is not None and tuple(native_order) != basis.species:
            raise ValueError("Native material species order differs from the declared adsorption basis")

    @property
    def basis(self):
        return self._basis

    def material_parameters(self):
        """A separate native dictionary for inspection/customization, not live mutable state."""
        return deepcopy(self._native_material)

    def equilibrium(self, partial_pressures_pa, temperature_k: float) -> AdsorptionState:
        self.domain.require_state(partial_pressures_pa, temperature_k)
        pressures = np.asarray(partial_pressures_pa, dtype=float)
        if pressures.shape != (len(self.basis.species),):
            raise ValueError("Partial-pressure order/length must match the declared species")
        loading, derivative_pressure, derivative_temperature = self._native_equilibrium(
            pressures / 100_000., temperature_k, self._native_material)
        if derivative_pressure is not None:
            derivative_pressure = np.asarray(derivative_pressure) / 100_000.
        return AdsorptionState(self.basis, pressures, temperature_k, loading,
                                derivative_pressure, derivative_temperature)
