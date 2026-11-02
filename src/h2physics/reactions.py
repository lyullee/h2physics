"""Finite stoichiometric conversion and prescribed-conversion enthalpy balances.

Extent is a supplied operating constraint. It is not an equilibrium or kinetic
prediction. All amounts use mol, including when a native provider uses kmol.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

import numpy as np
from scipy.optimize import brentq

from .core import finite, immutable_array


@dataclass(frozen=True, slots=True)
class ChemicalSpecies:
    identifier: str
    elements: Mapping[str, int]
    molar_mass_kg_mol: float
    phase: str
    charge: int = 0

    def __post_init__(self):
        atoms = dict(self.elements)
        if not self.identifier or not self.phase or not atoms:
            raise ValueError("Species identity, composition and phase are required")
        if any(not isinstance(e, str) or not e or isinstance(n, bool)
               or not isinstance(n, int) or n <= 0 for e, n in atoms.items()):
            raise ValueError("Element counts must be positive integers")
        if isinstance(self.charge, bool) or not isinstance(self.charge, int):
            raise ValueError("Species charge must be an integer")
        finite(self.molar_mass_kg_mol, "molar mass", positive=True)
        object.__setattr__(self, "elements", MappingProxyType(atoms))


@dataclass(frozen=True, slots=True)
class StoichiometricReaction:
    identifier: str
    species: tuple[ChemicalSpecies, ...]
    coefficients: tuple[float, ...]

    def __post_init__(self):
        species, coefficients = tuple(self.species), tuple(self.coefficients)
        if not self.identifier or not species or len(species) != len(coefficients):
            raise ValueError("Reaction identity, species and coefficients are required")
        if not all(isinstance(s, ChemicalSpecies) for s in species):
            raise ValueError("Supply ChemicalSpecies objects")
        if len({s.identifier for s in species}) != len(species):
            raise ValueError("Species identities must be unique within a reaction")
        coefficients = tuple(finite(n, "stoichiometric coefficient") for n in coefficients)
        if not min(coefficients) < 0 < max(coefficients):
            raise ValueError("Declare both reactants and products; zero denotes an inert")
        elements = {e for s in species for e in s.elements}
        for element in elements:
            residual = math.fsum(n*s.elements.get(element, 0)
                                 for s, n in zip(species, coefficients, strict=True))
            scale = math.fsum(abs(n)*s.elements.get(element, 0)
                              for s, n in zip(species, coefficients, strict=True))
            if abs(residual) > 1e-12*scale:
                raise ValueError(f"Reaction does not conserve element {element}")
        charge = math.fsum(n*s.charge for s, n in zip(species, coefficients, strict=True))
        if abs(charge) > 1e-12*math.fsum(abs(n*s.charge)
                                      for s, n in zip(species, coefficients, strict=True)):
            raise ValueError("Reaction does not conserve charge")
        mass = math.fsum(n*s.molar_mass_kg_mol
                         for s, n in zip(species, coefficients, strict=True))
        scale = math.fsum(abs(n)*s.molar_mass_kg_mol
                          for s, n in zip(species, coefficients, strict=True))
        if abs(mass) > 1e-10*scale:
            raise ValueError("Species molar masses use inconsistent atomic-weight bases")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "coefficients", coefficients)

    def amounts(self, supplied: Mapping[str, float]) -> np.ndarray:
        """Missing declared species have zero initial amount; foreign names fail."""
        if set(supplied) - {s.identifier for s in self.species}:
            raise ValueError("Inventory contains undeclared species")
        amounts = np.array([finite(supplied.get(s.identifier, 0.), "amount")
                            for s in self.species])
        if np.any(amounts < 0):
            raise ValueError("Inventory cannot be negative")
        return amounts

    def extent_limits_mol(self, supplied: Mapping[str, float]) -> tuple[float, float]:
        amounts = self.amounts(supplied)
        lower = max(-n/v for n, v in zip(amounts, self.coefficients, strict=True) if v > 0)
        upper = min(n/-v for n, v in zip(amounts, self.coefficients, strict=True) if v < 0)
        return lower, upper

    def convert(self, supplied: Mapping[str, float], extent_mol: float) -> "ReactionConversion":
        extent_mol = finite(extent_mol, "reaction extent")
        lower, upper = self.extent_limits_mol(supplied)
        if not lower <= extent_mol <= upper:
            raise ValueError("Extent exceeds a finite reactant/product inventory")
        initial = self.amounts(supplied)
        final = initial + extent_mol*np.asarray(self.coefficients)
        # A bound multiplication can differ by one floating-point rounding unit.
        correction = float(max(0., -min(final)))
        return ReactionConversion(self, extent_mol, initial, np.maximum(final, 0.), correction)


@dataclass(frozen=True, slots=True)
class ReactionConversion:
    reaction: StoichiometricReaction
    extent_mol: float
    initial_mol: np.ndarray
    final_mol: np.ndarray
    maximum_roundoff_correction_mol: float

    def __post_init__(self):
        for name in ("initial_mol", "final_mol"):
            array = np.array(getattr(self, name), dtype=float, copy=True)
            if array.shape != (len(self.reaction.species),) or not np.all(np.isfinite(array)):
                raise ValueError("Conversion arrays must match the species")
            if np.any(array < 0):
                raise ValueError("Conversion inventory cannot be negative")
            array = immutable_array(array, name=name)
            object.__setattr__(self, name, array)
        finite(self.extent_mol, "extent")
        finite(self.maximum_roundoff_correction_mol, "roundoff correction")
        expected = self.initial_mol + self.extent_mol*np.array(self.reaction.coefficients)
        if (self.maximum_roundoff_correction_mol < 0
                or not np.array_equal(self.final_mol, np.maximum(expected, 0.))
                or self.maximum_roundoff_correction_mol != max(0., -min(expected))):
            raise ValueError("Conversion does not match its declared stoichiometry/correction")
        lower, upper = self.reaction.extent_limits_mol(dict(zip(
            (s.identifier for s in self.reaction.species), self.initial_mol, strict=True)))
        if not lower <= self.extent_mol <= upper:
            raise ValueError("Conversion lies outside its finite inventory")

    @property
    def mass_residual_kg(self) -> float:
        return math.fsum((b-a)*s.molar_mass_kg_mol for a, b, s in zip(
            self.initial_mol, self.final_mol, self.reaction.species, strict=True))

    @property
    def final_amounts(self) -> Mapping[str, float]:
        return MappingProxyType(dict(zip((s.identifier for s in self.reaction.species),
                                         self.final_mol, strict=True)))


class MolarEnthalpyProvider(Protocol):
    species: tuple[ChemicalSpecies, ...]
    basis_id: str

    def enthalpies_j_mol(self, temperature_k: float, pressure_pa: float) -> np.ndarray: ...


@dataclass(frozen=True, slots=True)
class FunctionalMolarEnthalpy:
    """Caller-owned phase/property functions, with an explicit common energy basis.

    Each function must include its species formation/reference offset. Supplying
    unrelated sensible-enthalpy zeros cannot establish a reaction heat.
    """

    species: tuple[ChemicalSpecies, ...]
    functions: tuple[Callable[[float, float], float], ...]
    basis_id: str
    temperature_bounds_k: tuple[float, float]
    pressure_bounds_pa: tuple[float, float]

    def __post_init__(self):
        for name in ("species", "functions", "temperature_bounds_k", "pressure_bounds_pa"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if (not self.basis_id or not self.species or len(self.species) != len(self.functions)
                or not all(callable(f) for f in self.functions)):
            raise ValueError("Declare species, enthalpy functions and their common reference")
        if len({s.identifier for s in self.species}) != len(self.species):
            raise ValueError("Thermochemical species must be unique")
        for bounds in (self.temperature_bounds_k, self.pressure_bounds_pa):
            if len(bounds) != 2 or not 0 < bounds[0] < bounds[1] < math.inf:
                raise ValueError("Declare finite positive increasing property bounds")

    def enthalpies_j_mol(self, temperature_k, pressure_pa):
        finite(temperature_k, "temperature", positive=True)
        finite(pressure_pa, "pressure", positive=True)
        if (not self.temperature_bounds_k[0] <= temperature_k <= self.temperature_bounds_k[1]
                or not self.pressure_bounds_pa[0] <= pressure_pa <= self.pressure_bounds_pa[1]):
            raise ValueError("State lies outside the declared caloric domain")
        return np.array([finite(f(temperature_k, pressure_pa), "molar enthalpy")
                         for f in self.functions])


def _enthalpy(conversion, provider, temperature_k, pressure_pa, amounts):
    finite(temperature_k, "temperature", positive=True)
    finite(pressure_pa, "pressure", positive=True)
    if provider.species != conversion.reaction.species or not provider.basis_id:
        raise ValueError("Thermochemical species/order/phase/reference differs from the reaction")
    values = np.asarray(provider.enthalpies_j_mol(temperature_k, pressure_pa), dtype=float)
    if values.shape != amounts.shape or not np.all(np.isfinite(values)):
        raise ValueError("Provider returned invalid molar enthalpies")
    return math.fsum(amounts*values)


def conversion_heat_j(conversion: ReactionConversion, provider: MolarEnthalpyProvider, *,
                      inlet_temperature_k: float, outlet_temperature_k: float,
                      pressure_pa: float) -> float:
    """H_out-H_in; positive heat enters at fixed P, without shaft/kinetic terms."""
    return (_enthalpy(conversion, provider, outlet_temperature_k, pressure_pa, conversion.final_mol)
            - _enthalpy(conversion, provider, inlet_temperature_k, pressure_pa, conversion.initial_mol))


@dataclass(frozen=True, slots=True)
class ProductTemperature:
    temperature_k: float
    supplied_heat_j: float
    energy_residual_j: float
    basis_id: str


def solve_product_temperature(conversion: ReactionConversion, provider: MolarEnthalpyProvider, *,
                              inlet_temperature_k: float, pressure_pa: float, supplied_heat_j: float,
                              bracket_k: tuple[float, float]) -> ProductTemperature:
    """Solve calorimetry at the supplied extent; no equilibrium or rate is inferred."""
    finite(supplied_heat_j, "supplied heat")
    if not np.any(conversion.final_mol > 0):
        raise ValueError("An empty final inventory has no product temperature")
    if len(bracket_k) != 2 or not 0 < bracket_k[0] < bracket_k[1] < math.inf:
        raise ValueError("Supply a positive increasing temperature bracket")
    def residual(temperature):
        return conversion_heat_j(conversion, provider, inlet_temperature_k=inlet_temperature_k,
                                  outlet_temperature_k=temperature, pressure_pa=pressure_pa) - supplied_heat_j
    temperature = brentq(residual, *bracket_k, xtol=1e-9, rtol=1e-13)
    return ProductTemperature(temperature, supplied_heat_j, residual(temperature), provider.basis_id)


@dataclass(frozen=True, slots=True)
class ReferenceReactionHeat:
    """A reaction heat qualified at one T/P and the reaction's declared phases."""

    reaction: StoichiometricReaction
    enthalpy_j_mol_extent: float
    temperature_k: float
    pressure_pa: float
    source_id: str
    method: str
    origin: str

    def __post_init__(self):
        finite(self.enthalpy_j_mol_extent, "reaction enthalpy")
        finite(self.temperature_k, "reference temperature", positive=True)
        finite(self.pressure_pa, "reference pressure", positive=True)
        if not self.source_id or not self.method or self.origin not in {"computed", "measured", "synthetic"}:
            raise ValueError("Reaction heat needs its source, method and explicit origin")

    def heat_j(self, conversion: ReactionConversion, *, temperature_k: float, pressure_pa: float):
        if conversion.reaction != self.reaction:
            raise ValueError("Reference heat belongs to another reaction/phase/normalization")
        if (not math.isclose(temperature_k, self.temperature_k, rel_tol=0, abs_tol=1e-9)
                or not math.isclose(pressure_pa, self.pressure_pa, rel_tol=0, abs_tol=1e-6)):
            raise ValueError("A single reference heat cannot be extrapolated in T/P")
        return conversion.extent_mol*self.enthalpy_j_mol_extent
