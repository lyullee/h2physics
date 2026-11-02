"""Necessary-condition FA/DDT screens with explicit evidence and applicability.

These empirical screens do not calculate initiation, run-up distance, explosion
probability or a pressure history. Geometry and mixture conditions must be
qualified independently. Scientific sources are listed in INDOOR_AND_DDT.md.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from .core import finite


def _identity(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


@dataclass(frozen=True, slots=True)
class EvidenceInterval:
    """Closed physical uncertainty/support interval, not a confidence claim."""

    lower: float
    upper: float
    evidence_id: str

    def __post_init__(self):
        if finite(self.lower, "lower bound", positive=True) > finite(
                self.upper, "upper bound", positive=True):
            raise ValueError("Evidence interval must be positive and ordered")
        _identity(self.evidence_id, "interval evidence")


class ScreeningGeometry(StrEnum):
    CLOSED_OBSTRUCTED_TUBE = "closed_obstructed_tube"
    TRANSVERSE_VENTED_TUBE = "transverse_vented_tube"
    SEMICONFINED_FLAT_LAYER = "semiconfined_flat_layer"
    UNCONFINED = "unconfined"
    COMPLEX_COMPARTMENT = "complex_compartment"


@dataclass(frozen=True, slots=True)
class HydrogenMixtureCondition:
    temperature_k: float
    pressure_pa_absolute: float
    hydrogen_mole_fraction: float
    steam_mole_fraction: float
    condition_id: str

    def __post_init__(self):
        finite(self.temperature_k, "initial temperature", positive=True)
        finite(self.pressure_pa_absolute, "initial absolute pressure", positive=True)
        fractions = [finite(self.hydrogen_mole_fraction, "hydrogen mole fraction"),
                     finite(self.steam_mole_fraction, "steam mole fraction")]
        if any(value < 0 or value > 1 for value in fractions) or sum(fractions) > 1:
            raise ValueError("H2 and steam mole fractions must define a possible mixture")
        _identity(self.condition_id, "mixture condition identity")


@dataclass(frozen=True, slots=True)
class ScreeningDomain:
    """Source-qualified envelope supplied by the research application.

    Bounds are not inferred from an isolated coefficient or a single passing
    calculation. The evidence must also establish tube/layer geometry, obstacle
    and characteristic-length definitions and the oxidizer/diluent mixture.
    """

    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa_absolute: float
    maximum_pressure_pa_absolute: float
    minimum_hydrogen_mole_fraction: float
    maximum_hydrogen_mole_fraction: float
    maximum_steam_mole_fraction: float
    geometries: tuple[ScreeningGeometry, ...]
    evidence_id: str
    mixture_family: str = "hydrogen_air_steam"

    def __post_init__(self):
        for low, high in ((self.minimum_temperature_k, self.maximum_temperature_k),
                          (self.minimum_pressure_pa_absolute, self.maximum_pressure_pa_absolute)):
            if finite(low, "domain minimum", positive=True) > finite(
                    high, "domain maximum", positive=True):
                raise ValueError("Domain bounds must increase")
        if not 0 <= finite(self.minimum_hydrogen_mole_fraction, "minimum H2") <= finite(
                self.maximum_hydrogen_mole_fraction, "maximum H2") <= 1:
            raise ValueError("Hydrogen domain must lie in [0, 1]")
        if not 0 <= finite(self.maximum_steam_mole_fraction, "maximum steam") <= 1:
            raise ValueError("Steam domain must lie in [0, 1]")
        values = tuple(ScreeningGeometry(item) for item in self.geometries)
        if not values or len(set(values)) != len(values):
            raise ValueError("Supply distinct qualified geometries")
        object.__setattr__(self, "geometries", values)
        if self.mixture_family != "hydrogen_air_steam":
            raise ValueError("This screen supports only the declared H2/air/steam family")
        _identity(self.evidence_id, "domain evidence")

    def exclusions(self, condition, geometry):
        reasons = []
        if geometry not in self.geometries:
            reasons.append("geometry is outside criterion evidence")
        if not self.minimum_temperature_k <= condition.temperature_k <= self.maximum_temperature_k:
            reasons.append("initial temperature is outside criterion evidence")
        if not self.minimum_pressure_pa_absolute <= condition.pressure_pa_absolute <= (
                self.maximum_pressure_pa_absolute):
            reasons.append("initial pressure is outside criterion evidence")
        if not self.minimum_hydrogen_mole_fraction <= condition.hydrogen_mole_fraction <= (
                self.maximum_hydrogen_mole_fraction):
            reasons.append("hydrogen content is outside criterion evidence")
        if condition.steam_mole_fraction > self.maximum_steam_mole_fraction:
            reasons.append("steam content is outside criterion evidence")
        return tuple(reasons)


@dataclass(frozen=True, slots=True)
class MixtureExpansion:
    condition: HydrogenMixtureCondition
    density_unburned_kg_m3: float
    density_burned_kg_m3: float
    burned_temperature_k: float
    thermochemistry_evidence_id: str
    definition: str = "adiabatic_constant_pressure_equilibrium"

    def __post_init__(self):
        if not isinstance(self.condition, HydrogenMixtureCondition):
            raise TypeError("Supply a HydrogenMixtureCondition")
        for name in ("density_unburned_kg_m3", "density_burned_kg_m3", "burned_temperature_k"):
            finite(getattr(self, name), name, positive=True)
        _identity(self.thermochemistry_evidence_id, "thermochemistry evidence")
        if self.definition != "adiabatic_constant_pressure_equilibrium":
            raise ValueError("Sigma requires this explicitly selected thermodynamic definition")
        finite(self.expansion_ratio, "mixture expansion ratio", positive=True)

    @property
    def expansion_ratio(self):
        return self.density_unburned_kg_m3 / self.density_burned_kg_m3


def cantera_mixture_expansion(gas, *, temperature_k: float, pressure_pa_absolute: float,
                              mole_fractions: Mapping[str, float], condition_id: str,
                              mechanism_evidence_id: str) -> MixtureExpansion:
    """Evaluate sigma with the caller's actual Cantera gas and restore its state.

    Cantera owns reacting mixture thermochemistry. The gas must be a separately
    selected ideal-gas reaction phase, not a CoolProp fluid substitute. Only
    H2/O2/N2/H2O input is supported, with dry air O2:N2 = 1:3.76.
    """
    import cantera as ct

    if not isinstance(gas, ct.Solution) or gas.thermo_model != "ideal-gas":
        raise TypeError("Select a real Cantera ideal-gas Solution")
    finite(temperature_k, "initial temperature", positive=True)
    finite(pressure_pa_absolute, "initial pressure", positive=True)
    _identity(mechanism_evidence_id, "mechanism evidence")
    values = dict(mole_fractions)
    if not values or set(values) - {"H2", "O2", "N2", "H2O"}:
        raise ValueError("Only H2, O2, N2 and steam inputs are admitted")
    for value in values.values():
        if finite(value, "mixture amount") < 0:
            raise ValueError("Mixture amounts cannot be negative")
    if values.get("H2", 0) <= 0 or values.get("O2", 0) <= 0:
        raise ValueError("Supply hydrogen and oxygen")
    if abs(values.get("N2", 0) / values["O2"] - 3.76) > 1e-8:
        raise ValueError("This domain requires dry-air N2:O2 = 3.76")
    total = sum(values.values())
    finite(total, "total mixture amount", positive=True)
    condition = HydrogenMixtureCondition(temperature_k, pressure_pa_absolute,
        values["H2"] / total, values.get("H2O", 0) / total, condition_id)
    state = gas.state.copy()
    try:
        gas.TPX = temperature_k, pressure_pa_absolute, values
        initial_density = float(gas.density)
        gas.equilibrate("HP")
        return MixtureExpansion(condition, initial_density, float(gas.density),
                                 float(gas.T), mechanism_evidence_id)
    finally:
        gas.state = state


@dataclass(frozen=True, slots=True)
class FlameAccelerationCriterion:
    critical_expansion_ratio: EvidenceInterval
    domain: ScreeningDomain
    source_id: str

    def __post_init__(self):
        if not isinstance(self.critical_expansion_ratio, EvidenceInterval):
            raise TypeError("Supply a critical-expansion evidence interval")
        if not isinstance(self.domain, ScreeningDomain):
            raise TypeError("Supply a qualified screening domain")
        _identity(self.source_id, "flame-acceleration criterion source")


def dorofeev_critical_expansion(*, activation_temperature_k: float,
                               unburned_temperature_k: float,
                               qualified_x_interval: EvidenceInterval,
                               turbulent_peclet_number: float,
                               applicability_evidence_id: str) -> EvidenceInterval:
    """Evaluate the published polynomial with explicitly qualified x support.

    x = (Ea/R)/Tu. ``activation_temperature_k`` is Ea/R in kelvin, not Ea
    in J/mol. Source: https://doi.org/10.1016/j.ijhydene.2022.07.024 .
    The caller supplies the independently justified x range; this function
    does not admit cryogenic extrapolation merely because it is calculable.
    Pe >= 100 is a necessary correlation prerequisite, not a validation claim.
    """
    finite(activation_temperature_k, "activation temperature Ea/R", positive=True)
    finite(unburned_temperature_k, "unburned temperature", positive=True)
    if finite(turbulent_peclet_number, "turbulent Peclet number", positive=True) < 100:
        raise ValueError("This selected polynomial requires turbulent Pe >= 100")
    _identity(applicability_evidence_id, "polynomial applicability evidence")
    x = activation_temperature_k / unburned_temperature_k
    if not qualified_x_interval.lower <= x <= qualified_x_interval.upper:
        raise ValueError("Ea/(R Tu) lies outside the supplied qualified interval")
    value = ((9e-6 * x - .0019) * x + .1807) * x + .2314
    return EvidenceInterval(value, value, applicability_evidence_id)


def vent_corrected_critical_expansion(closed: EvidenceInterval, *,
                                     vent_to_total_surface_ratio: float,
                                     qualified_vent_ratio_bounds: tuple[float, float],
                                     coefficient: EvidenceInterval,
                                     applicability_evidence_id: str) -> EvidenceInterval:
    """Apply sigma_vent/sigma_closed = 1 + c*alpha with supplied evidence.

    Do not confuse vent/floor area with vent/total tube-surface area. The
    fitted c, alpha range, obstacle geometry and applicability must come from
    the selected experiment, e.g. https://doi.org/10.1016/S0950-4230(01)00051-1 .
    No universal coefficient or enclosure geometry is assumed.
    """
    ratio = finite(vent_to_total_surface_ratio, "vent/total surface area")
    if not 0 <= ratio <= 1:
        raise ValueError("Vent/surface area ratio must lie in [0, 1]")
    if len(qualified_vent_ratio_bounds) != 2:
        raise ValueError("Supply two qualified vent-ratio bounds")
    low, high = (finite(value, "qualified vent-ratio bound")
                 for value in qualified_vent_ratio_bounds)
    if not 0 <= low <= high <= 1 or not low <= ratio <= high:
        raise ValueError("Vent ratio is outside the qualified correction domain")
    _identity(applicability_evidence_id, "vent-correction applicability")
    return EvidenceInterval(closed.lower * (1 + coefficient.lower * ratio),
                            closed.upper * (1 + coefficient.upper * ratio),
                            applicability_evidence_id)


@dataclass(frozen=True, slots=True)
class DetonationCellCriterion:
    cell_width_m: EvidenceInterval
    characteristic_length_m: EvidenceInterval
    domain: ScreeningDomain
    cell_data_condition_id: str
    geometry_length_definition_id: str
    source_id: str
    required_cell_multiples: float = 7.0

    def __post_init__(self):
        if not isinstance(self.cell_width_m, EvidenceInterval) or not isinstance(
                self.characteristic_length_m, EvidenceInterval):
            raise TypeError("Supply positive cell-width and length evidence intervals")
        if not isinstance(self.domain, ScreeningDomain):
            raise TypeError("Supply a qualified cell-size domain")
        finite(self.required_cell_multiples, "required cell multiples", positive=True)
        for name in ("cell_data_condition_id", "geometry_length_definition_id", "source_id"):
            _identity(getattr(self, name), name)


class NecessaryConditionStatus(StrEnum):
    MET = "necessary_condition_met"
    NOT_MET = "necessary_condition_not_met"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class CombustionScreen:
    expansion: MixtureExpansion
    geometry: ScreeningGeometry
    flame_criterion: FlameAccelerationCriterion
    cell_criterion: DetonationCellCriterion
    flame_acceleration: NecessaryConditionStatus
    cell_size: NecessaryConditionStatus
    combined_ddt: NecessaryConditionStatus
    reasons: tuple[str, ...]
    predicts_initiation: bool = False


def _greater_interval(value_low, value_high, threshold_low, threshold_high):
    if value_low > threshold_high:
        return NecessaryConditionStatus.MET
    if value_high <= threshold_low:
        return NecessaryConditionStatus.NOT_MET
    return NecessaryConditionStatus.INDETERMINATE


def screen_combustion(expansion: MixtureExpansion, geometry: ScreeningGeometry,
                       flame: FlameAccelerationCriterion,
                       cell: DetonationCellCriterion) -> CombustionScreen:
    """Compare bounded necessary conditions, retaining out-of-domain ambiguity.

    Cell data must refer to the exact mixture-condition identity. A met result
    leaves ignition, flame run-up and sufficient geometry unresolved. A not-met
    result only fails this selected route; it does not exclude direct initiation
    or establish safety of a facility.
    """
    if not isinstance(expansion, MixtureExpansion):
        raise TypeError("Supply a MixtureExpansion")
    if not isinstance(flame, FlameAccelerationCriterion) or not isinstance(cell, DetonationCellCriterion):
        raise TypeError("Supply typed flame and detonation-cell criteria")
    geometry = ScreeningGeometry(geometry)
    fa_reasons = flame.domain.exclusions(expansion.condition, geometry)
    cell_reasons = cell.domain.exclusions(expansion.condition, geometry)
    if cell.cell_data_condition_id != expansion.condition.condition_id:
        cell_reasons += ("cell data are not matched to the selected mixture condition",)
    sigma = expansion.expansion_ratio
    critical = flame.critical_expansion_ratio
    fa = NecessaryConditionStatus.INDETERMINATE if fa_reasons else _greater_interval(
        sigma, sigma, critical.lower, critical.upper)
    length, width = cell.characteristic_length_m, cell.cell_width_m
    low, high = cell.required_cell_multiples * width.lower, cell.required_cell_multiples * width.upper
    finite(low, "minimum cell-size threshold", positive=True)
    finite(high, "maximum cell-size threshold", positive=True)
    size = NecessaryConditionStatus.INDETERMINATE if cell_reasons else _greater_interval(
        length.lower, length.upper, low, high)
    if NecessaryConditionStatus.NOT_MET in (fa, size):
        combined = NecessaryConditionStatus.NOT_MET
    elif fa == size == NecessaryConditionStatus.MET:
        combined = NecessaryConditionStatus.MET
    else:
        combined = NecessaryConditionStatus.INDETERMINATE
    reasons = tuple(dict.fromkeys(fa_reasons + cell_reasons))
    if fa == NecessaryConditionStatus.INDETERMINATE and not fa_reasons:
        reasons += ("expansion ratio overlaps the critical interval",)
    if size == NecessaryConditionStatus.INDETERMINATE and not cell_reasons:
        reasons += ("length and cell-size uncertainty overlap the threshold",)
    return CombustionScreen(expansion, geometry, flame, cell, fa, size, combined, reasons)
