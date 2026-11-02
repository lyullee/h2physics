"""One polarization and Faraday-balance core for electrolysis and fuel cells.

Scientific context: https://www.nrel.gov/docs/fy23osti/83155.pdf and
https://www.nrel.gov/docs/fy10osti/47302.pdf. Coefficients and reaction-energy
functions are user inputs, not universal constants fitted to an unspecified cell.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .constants import FARADAY_C_MOL, R_J_MOL_K
from .core import finite


@dataclass(frozen=True, slots=True)
class ReactionEnergy:
    """Positive water-splitting reaction energies per mole H2 at the actual state."""

    gibbs_j_mol_h2: float
    enthalpy_j_mol_h2: float
    reference_id: str
    water_phase: str

    def __post_init__(self):
        finite(self.gibbs_j_mol_h2, "reaction Gibbs energy", positive=True)
        finite(self.enthalpy_j_mol_h2, "reaction enthalpy", positive=True)
        if (not isinstance(self.reference_id, str) or not self.reference_id.strip()
                or self.water_phase not in {"liquid", "vapor"}):
            raise ValueError("Declare a common reaction-energy reference and water phase")

    @property
    def reversible_voltage_v(self):
        return self.gibbs_j_mol_h2 / (2*FARADAY_C_MOL)

    @property
    def thermoneutral_voltage_v(self):
        return self.enthalpy_j_mol_h2 / (2*FARADAY_C_MOL)


@dataclass(frozen=True, slots=True)
class FuelCellOperatingState:
    """Explicit reversible-voltage state for separated fuel-cell channels.

    Activities are dimensionless relative to the declared channel references.
    This value object does not claim a simultaneous native device solve; it lets
    callers bind pressure/activity-corrected thermochemistry to the existing
    polarization stack without changing its temperature-only compatibility API.
    """

    temperature_k: float
    anode_pressure_pa: float
    cathode_pressure_pa: float
    hydrogen_activity: float
    oxygen_activity: float
    water_activity: float
    water_phase: str
    hydrogen_reference_id: str
    oxygen_reference_id: str
    water_reference_id: str
    state_evidence_id: str

    def __post_init__(self):
        for name in ("temperature_k", "anode_pressure_pa", "cathode_pressure_pa",
                     "hydrogen_activity", "oxygen_activity", "water_activity"):
            finite(getattr(self, name), name, positive=True)
        for name in ("hydrogen_reference_id", "oxygen_reference_id",
                     "water_reference_id", "state_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Operating state requires explicit activity references and evidence")
        if self.water_phase not in {"liquid", "vapor"}:
            raise ValueError("Operating state water activity requires an explicit liquid or vapor phase")

def ideal_activity_correction(standard: ReactionEnergy, *, temperature_k: float,
                             hydrogen_activity: float, oxygen_activity: float,
                             water_activity: float) -> ReactionEnergy:
    """Nernst correction with dimensionless, explicitly supplied activities.

    Reaction enthalpy is retained from the supplied standard state. This
    approximation excludes nonideal enthalpy departures; supply complete
    state-dependent reaction energies directly when those matter.
    """
    finite(temperature_k, "temperature", positive=True)
    for name, value in (("hydrogen", hydrogen_activity), ("oxygen", oxygen_activity),
                        ("water", water_activity)):
        finite(value, name + " activity", positive=True)
    log_quotient = math.log(hydrogen_activity) + .5*math.log(oxygen_activity) - math.log(water_activity)
    return ReactionEnergy(standard.gibbs_j_mol_h2 + R_J_MOL_K*temperature_k*log_quotient,
                           standard.enthalpy_j_mol_h2, standard.reference_id, standard.water_phase)


def fuel_cell_activity_correction(standard: ReactionEnergy,
                                  operating_state: FuelCellOperatingState) -> ReactionEnergy:
    """Apply caller-supplied channel activities to the shared reaction energy."""
    if type(standard) is not ReactionEnergy or type(operating_state) is not FuelCellOperatingState:
        raise TypeError("Supply the shared reaction-energy law and explicit fuel-cell state")
    if standard.water_phase != operating_state.water_phase:
        raise ValueError("Product-water activity phase differs from the reaction-energy reference phase")
    corrected = ideal_activity_correction(standard,
        temperature_k=operating_state.temperature_k,
        hydrogen_activity=operating_state.hydrogen_activity,
        oxygen_activity=operating_state.oxygen_activity,
        water_activity=operating_state.water_activity)
    return ReactionEnergy(corrected.gibbs_j_mol_h2, corrected.enthalpy_j_mol_h2,
        standard.reference_id + ":activity:" + ":".join((
            operating_state.hydrogen_reference_id, operating_state.oxygen_reference_id,
            operating_state.water_reference_id, operating_state.state_evidence_id)),
        standard.water_phase)


@dataclass(frozen=True, slots=True)
class SymmetricButlerVolmerLoss:
    exchange_current_density_a_m2: Callable[[float], float]
    effective_charge_transfer_electrons: float

    def __post_init__(self):
        finite(self.effective_charge_transfer_electrons, "effective charge-transfer electrons", positive=True)

    def __call__(self, current_density_a_m2, temperature_k):
        exchange = finite(self.exchange_current_density_a_m2(temperature_k), "exchange current density", positive=True)
        finite(temperature_k, "temperature", positive=True)
        return (2*R_J_MOL_K*temperature_k / (self.effective_charge_transfer_electrons*FARADAY_C_MOL)
                * math.asinh(current_density_a_m2 / (2*exchange)))


@dataclass(frozen=True, slots=True)
class OhmicLoss:
    area_resistance_ohm_m2: Callable[[float], float]

    def __call__(self, current_density_a_m2, temperature_k):
        resistance = finite(self.area_resistance_ohm_m2(temperature_k), "area-specific resistance")
        if resistance < 0:
            raise ValueError("Area-specific resistance cannot be negative")
        return current_density_a_m2 * resistance


@dataclass(frozen=True, slots=True)
class LimitingCurrentLoss:
    limiting_current_density_a_m2: Callable[[float], float]
    voltage_scale_v: Callable[[float], float]

    def __call__(self, current_density_a_m2, temperature_k):
        limit = finite(self.limiting_current_density_a_m2(temperature_k), "limiting current density", positive=True)
        scale = finite(self.voltage_scale_v(temperature_k), "concentration-loss voltage scale", positive=True)
        if not 0 <= current_density_a_m2 < limit:
            raise ValueError("Current density must remain below the supplied limiting current")
        return -scale * math.log1p(-current_density_a_m2/limit)


@dataclass(frozen=True, slots=True)
class StackGeometry:
    series_cells: int
    active_area_m2: float
    hydrogen_molar_mass_kg_mol: float

    def __post_init__(self):
        if isinstance(self.series_cells, bool) or not isinstance(self.series_cells, int) or self.series_cells < 1:
            raise ValueError("The stack needs a positive integer count of series cells")
        finite(self.active_area_m2, "active cell area", positive=True)
        finite(self.hydrogen_molar_mass_kg_mol, "hydrogen molar mass", positive=True)


@dataclass(frozen=True, slots=True)
class StackResult:
    mode: str
    reaction_energy: ReactionEnergy
    current_a: float
    cell_voltage_v: float
    stack_voltage_v: float
    loss_voltages: tuple[tuple[str, float], ...]
    electric_input_w: float
    hydrogen_production_mol_s: float
    hydrogen_production_kg_s: float
    reaction_enthalpy_rate_w: float
    unallocated_energy_rate_w: float
    isothermal_heat_rejection_w: float | None


class HydrogenStack:
    """Native callbacks select thermochemistry and separate polarization losses.

    Current density is a nonnegative magnitude. Electrolysis consumes positive
    electrical power and produces positive hydrogen; fuel-cell outputs have
    negative signs for those same boundary quantities. Faradaic inefficiency
    changes the gas balance, but its chemical/thermal fate is not silently
    assigned to heat. No cell aging, crossover or thermal inventory is implied.
    """

    def __init__(self, geometry: StackGeometry,
                 thermochemistry: Callable[[float], ReactionEnergy],
                 losses: Mapping[str, Callable[[float, float], float]]):
        if any(not name for name in losses):
            raise ValueError("Polarization losses need identifiable names")
        self.geometry, self.thermochemistry = geometry, thermochemistry
        self.losses = MappingProxyType(dict(losses))

    def evaluate(self, current_density_a_m2: float, temperature_k: float, *,
                 mode: Literal["electrolysis", "fuel_cell"],
                 faradaic_efficiency: float = 1.0) -> StackResult:
        finite(temperature_k, "temperature", positive=True)
        if finite(current_density_a_m2, "current density") < 0:
            raise ValueError("Supply a nonnegative current-density magnitude")
        if not 0 < finite(faradaic_efficiency, "Faradaic efficiency") <= 1:
            raise ValueError("Faradaic efficiency must lie in (0, 1]")
        if mode not in {"electrolysis", "fuel_cell"}:
            raise ValueError("Select electrolysis or fuel-cell operation")
        energy = self.thermochemistry(temperature_k)
        losses = tuple((name, finite(model(current_density_a_m2, temperature_k), name + " voltage loss"))
                       for name, model in self.losses.items())
        if any(value < 0 for _, value in losses):
            raise ValueError("Polarization losses must be nonnegative")
        sign = 1 if mode == "electrolysis" else -1
        voltage = energy.reversible_voltage_v + sign*sum(value for _, value in losses)
        if voltage <= 0:
            raise ValueError("The requested state has a nonpositive operating voltage")
        geometry = self.geometry
        current = current_density_a_m2 * geometry.active_area_m2
        electrical = sign * current * voltage * geometry.series_cells
        ideal_h2 = current * geometry.series_cells / (2*FARADAY_C_MOL)
        h2 = (ideal_h2*faradaic_efficiency if sign == 1 else -ideal_h2/faradaic_efficiency)
        reaction_heat = h2 * energy.enthalpy_j_mol_h2
        unallocated = electrical - reaction_heat
        stack_voltage = finite(voltage*geometry.series_cells, "computed stack voltage")
        hydrogen_mass = finite(h2*geometry.hydrogen_molar_mass_kg_mol,
                               "computed hydrogen mass rate")
        for name, value in (("current", current), ("cell voltage", voltage),
                            ("electrical power", electrical), ("hydrogen molar rate", h2),
                            ("reaction heat", reaction_heat), ("unallocated heat", unallocated)):
            finite(value, "computed stack " + name)
        return StackResult(mode, energy, current, voltage, stack_voltage, losses,
                            electrical, h2, hydrogen_mass, reaction_heat,
                            unallocated, unallocated if faradaic_efficiency == 1 else None)
