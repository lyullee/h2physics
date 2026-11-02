"""Inventory and command contracts for composed native transient models.

Stored internal energy includes declared solid thermal storage. Transported
energy is enthalpy; a zero flow does not remove the remaining fluid inventory.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .core import PropertyBasis, finite


@dataclass(frozen=True, slots=True)
class ConservedInventory:
    basis: PropertyBasis
    mass_kg: float
    fluid_internal_energy_j: float
    solid_internal_energy_j: float

    def __post_init__(self):
        finite(self.mass_kg, "mass_kg", positive=True)
        finite(self.fluid_internal_energy_j, "fluid_internal_energy_j")
        finite(self.solid_internal_energy_j, "solid_internal_energy_j")
        finite(self.total_energy_j, "total_energy_j")

    @property
    def total_energy_j(self):
        return self.fluid_internal_energy_j + self.solid_internal_energy_j


@dataclass(frozen=True, slots=True)
class InventoryTolerances:
    mass_absolute_kg: float = 1e-8
    energy_absolute_j: float = 1e-4
    relative: float = 1e-8

    def __post_init__(self):
        for name in ("mass_absolute_kg", "energy_absolute_j", "relative"):
            finite(getattr(self, name), name, positive=True)


@dataclass(frozen=True, slots=True)
class InventoryBalance:
    initial: ConservedInventory
    current: ConservedInventory
    boundary_mass_kg: float
    boundary_energy_j: float
    transported_enthalpy_j: float
    external_heat_j: float

    def __post_init__(self):
        self.initial.basis.require_compatible(self.current.basis)
        for name in ("boundary_mass_kg", "boundary_energy_j", "transported_enthalpy_j",
                     "external_heat_j"):
            finite(getattr(self, name), name)
        finite(self.mass_residual_kg, "mass_residual_kg")
        finite(self.energy_residual_j, "energy_residual_j")

    @property
    def mass_residual_kg(self):
        return self.current.mass_kg - self.initial.mass_kg - self.boundary_mass_kg

    @property
    def energy_residual_j(self):
        return self.current.total_energy_j - self.initial.total_energy_j - self.boundary_energy_j

    def violations(self, tolerances: InventoryTolerances):
        mass_scale = max(abs(self.current.mass_kg-self.initial.mass_kg), abs(self.boundary_mass_kg))
        energy_scale = max(abs(self.current.total_energy_j-self.initial.total_energy_j),
                           abs(self.boundary_energy_j), abs(self.transported_enthalpy_j),
                           abs(self.external_heat_j))
        errors = []
        if abs(self.mass_residual_kg) > max(tolerances.mass_absolute_kg,
                                          tolerances.relative*mass_scale):
            errors.append("inventory mass does not close")
        limit = max(tolerances.energy_absolute_j, tolerances.relative*energy_scale)
        if abs(self.energy_residual_j) > limit:
            errors.append("inventory energy does not close")
        if abs(self.boundary_energy_j-self.transported_enthalpy_j-self.external_heat_j) > limit:
            errors.append("transport and external heat do not sum to the boundary energy")
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class ScheduledEquipmentCommand:
    identifier: str
    time_s: float
    apply: Callable[[float, Any], None]

    def __post_init__(self):
        if not isinstance(self.identifier, str) or not self.identifier.strip():
            raise ValueError("A scheduled command needs an explicit identity")
        finite(self.time_s, "time_s")
        if not callable(self.apply):
            raise TypeError("A scheduled command needs a Python callable")


@dataclass(frozen=True, slots=True)
class SampledEquipmentIntegral:
    value: float
    basis: PropertyBasis
    rate_unit: str
    integral_unit: str
    clock_id: str
    start_time_s: float
    end_time_s: float
    interval_count: int
    method: str = "piecewise_linear_trapezoid"

    def __post_init__(self):
        if not all(isinstance(value, str) and value.strip()
                   for value in (self.rate_unit, self.integral_unit, self.clock_id, self.method)):
            raise ValueError("Rate/integral units, clock and integration method need identities")
        finite(self.value, "value")
        finite(self.start_time_s, "start_time_s")
        finite(self.end_time_s, "end_time_s")
        if self.end_time_s <= self.start_time_s:
            raise ValueError("An integral needs a positive time window")
        if not isinstance(self.interval_count, int) or isinstance(self.interval_count, bool) or self.interval_count < 1:
            raise ValueError("A sampled integral requires at least one positive interval")
