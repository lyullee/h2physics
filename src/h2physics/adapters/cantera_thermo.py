"""Native ideal-gas species enthalpies for prescribed-conversion calorimetry."""

from collections.abc import Callable

import numpy as np

from ..reactions import ChemicalSpecies
from .cantera import MechanismBasis


class CanteraMolarEnthalpy:
    """Retains an actual caller-created Cantera phase; amounts remain host mol.

    Cantera owns thermochemistry. Reaction extents are external constraints,
    unlike the existing native equilibrium and kinetic-reactor adapters.
    """

    def __init__(self, phase_factory: Callable, basis: MechanismBasis, species_names: tuple[str, ...]):
        self.native_phase = phase_factory()
        self.mechanism_basis = basis
        if self.native_phase.thermo_model != "ideal-gas":
            raise ValueError("This caloric adapter requires a native ideal-gas phase")
        if not species_names or len(set(species_names)) != len(species_names):
            raise ValueError("Declare unique native species names in the intended reaction order")
        self._indices = tuple(self.native_phase.species_index(name) for name in species_names)
        species = []
        for name, index in zip(species_names, self._indices, strict=True):
            native = self.native_phase.species(index)
            if any(not float(n).is_integer() or n <= 0 for n in native.composition.values()):
                raise ValueError("Native species has unsupported noninteger element counts")
            if not float(native.charge).is_integer():
                raise ValueError("Native species has a noninteger charge")
            species.append(ChemicalSpecies(name, {e: int(n) for e, n in native.composition.items()},
                self.native_phase.molecular_weights[index]/1000, "ideal-gas", int(native.charge)))
        self.species = tuple(species)
        self.basis_id = f"{basis.identifier}:{basis.source_sha256}:native-molar-enthalpy"

    def enthalpies_j_mol(self, temperature_k, pressure_pa):
        self.mechanism_basis.require_state(temperature_k, pressure_pa)
        lower = max(self.native_phase.species(i).thermo.min_temp for i in self._indices)
        upper = min(self.native_phase.species(i).thermo.max_temp for i in self._indices)
        if not lower <= temperature_k <= upper:
            raise ValueError("State is outside native species thermochemistry fit bounds")
        self.native_phase.TP = temperature_k, pressure_pa
        # Native partial molar enthalpy is J/kmol; ideal-gas h_i is composition independent.
        return np.asarray(self.native_phase.partial_molar_enthalpies)[list(self._indices)]/1000
