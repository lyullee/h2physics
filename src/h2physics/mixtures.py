"""Immutable gas-mixture composition and component-flow bookkeeping.

This module performs composition algebra only. It does not provide an equation
of state, phase-equilibrium model, fugacity, or transport-property mixing rule.
"""

from dataclasses import dataclass

import numpy as np

from .core import _real_numeric_array, immutable_array


def _readonly_vector(value, name, size=None):
    result = np.array(_real_numeric_array(value, name), dtype=float, copy=True)
    if (result.ndim != 1 or (size is not None and result.shape != (size,))
            or not np.all(np.isfinite(result))):
        raise ValueError(f"{name} must be a finite one-dimensional vector")
    return immutable_array(result, name=name)


def _readonly_result(value):
    result = np.array(value, dtype=float, copy=True)
    return immutable_array(result, name="mixture result")


@dataclass(frozen=True, slots=True)
class GasComposition:
    """A fixed gas composition with explicit species and molar-mass identities.

    Mole and mass fractions are converted using declared molar masses in kg/mol.
    Component flow arrays put species on the final axis and retain the sign of
    the supplied total flow. Composition is fixed; reactions require constructing
    a new object after updating the composition.
    """

    composition_id: str
    species: tuple[str, ...]
    mole_fractions: np.ndarray
    molar_masses_kg_mol: np.ndarray

    def __post_init__(self):
        if not isinstance(self.composition_id, str) or not self.composition_id.strip():
            raise ValueError("Gas composition needs a nonblank identity")
        names = tuple(self.species)
        if (not names or any(not isinstance(name, str) or not name.strip() for name in names)
                or len(set(names)) != len(names)):
            raise ValueError("Gas species must be nonblank, unique strings")
        fractions = _readonly_vector(self.mole_fractions, "mole fractions", len(names))
        masses = _readonly_vector(self.molar_masses_kg_mol, "molar masses", len(names))
        if (np.any(fractions < 0) or not np.isclose(fractions.sum(), 1., rtol=0., atol=1e-12)
                or np.any(masses <= 0)):
            raise ValueError("Mole fractions must be nonnegative and normalized; molar masses positive")
        object.__setattr__(self, "species", names)
        object.__setattr__(self, "mole_fractions", fractions)
        object.__setattr__(self, "molar_masses_kg_mol", masses)

    @classmethod
    def from_mass_fractions(cls, composition_id, species, mass_fractions,
                            molar_masses_kg_mol):
        names = tuple(species)
        fractions = _readonly_vector(mass_fractions, "mass fractions", len(names))
        masses = _readonly_vector(molar_masses_kg_mol, "molar masses", len(names))
        if (np.any(fractions < 0) or not np.isclose(fractions.sum(), 1., rtol=0., atol=1e-12)
                or np.any(masses <= 0)):
            raise ValueError("Mass fractions must be nonnegative and normalized; molar masses positive")
        amount_proportions = fractions / masses
        mole_fractions = amount_proportions / amount_proportions.sum()
        return cls(composition_id, names, mole_fractions, masses)

    @property
    def molar_mass_kg_mol(self):
        """Mixture molar mass from the declared mole-fraction basis."""
        return float(self.mole_fractions @ self.molar_masses_kg_mol)

    @property
    def mass_fractions(self):
        values = self.mole_fractions * self.molar_masses_kg_mol / self.molar_mass_kg_mol
        return _readonly_result(values)

    def total_molar_flow_from_mass_flow(self, mass_flow_kg_s):
        flow = _flow_array(mass_flow_kg_s, "mass flow")
        return float(flow / self.molar_mass_kg_mol) if flow.ndim == 0 else _readonly_result(
            flow / self.molar_mass_kg_mol
        )

    def total_mass_flow_from_molar_flow(self, molar_flow_mol_s):
        flow = _flow_array(molar_flow_mol_s, "molar flow")
        return float(flow * self.molar_mass_kg_mol) if flow.ndim == 0 else _readonly_result(
            flow * self.molar_mass_kg_mol
        )

    def component_molar_flows(self, total_molar_flow_mol_s):
        flow = _flow_array(total_molar_flow_mol_s, "total molar flow")
        return _readonly_result(np.expand_dims(flow, -1) * self.mole_fractions)

    def component_mass_flows(self, total_mass_flow_kg_s):
        flow = _flow_array(total_mass_flow_kg_s, "total mass flow")
        return _readonly_result(np.expand_dims(flow, -1) * self.mass_fractions)


def _flow_array(value, name):
    result = _real_numeric_array(value, name)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


__all__ = ["GasComposition"]
