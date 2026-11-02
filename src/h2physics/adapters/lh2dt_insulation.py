"""Native LH2DT vacuum heat boundaries with explicit provenance and wall allocation.

LH2DT owns every heat-transfer equation and tank integration. This adapter keeps
the signed boundary, area, gas-pressure basis, clock and inventory ledger visible.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import fsum, isclose
from types import MappingProxyType
from typing import Any

from ..core import Origin, PropertyBasis, finite
from ..dynamics import ConservedInventory
from ..equipment import BoundaryPower


@dataclass(frozen=True, slots=True)
class InsulationEvidence:
    geometry_id: str
    closure_id: str
    residual_gas_id: str
    pressure_evidence_id: str
    source_ids: tuple[str, ...]
    origin: Origin
    pressure_basis: str = "absolute"

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() for value in (
                self.geometry_id, self.closure_id, self.residual_gas_id, self.pressure_evidence_id)):
            raise ValueError("Geometry, closures, residual gas and pressure evidence must be explicit")
        sources = tuple(self.source_ids)
        if not sources or any(not isinstance(source, str) or not source.strip() for source in sources):
            raise ValueError("Declare the independently inspectable parameter/source identities")
        if self.pressure_basis != "absolute":
            raise ValueError("Vacuum gas conduction requires absolute annulus pressure in Pa")
        object.__setattr__(self, "source_ids", sources)
        object.__setattr__(self, "origin", Origin(self.origin))


@dataclass(frozen=True, slots=True)
class WallHeatAllocation:
    zone_ids: tuple[str, ...]
    area_fractions: tuple[float, ...]
    localized_path_fractions: Mapping[str, Sequence[float]]
    evidence_id: str

    def __post_init__(self):
        zones, fractions = tuple(self.zone_ids), tuple(self.area_fractions)
        if (not zones or len(set(zones)) != len(zones)
                or any(not isinstance(zone, str) or not zone.strip() for zone in zones)):
            raise ValueError("Declare unique physical wall-zone identities")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Wall and penetration allocation needs geometry evidence")

        def partition(values):
            values = tuple(finite(value, "allocation fraction") for value in values)
            if len(values) != len(zones) or any(value < 0. for value in values):
                raise ValueError("Allocation fractions must be nonnegative and match wall zones")
            if not isclose(fsum(values), 1., abs_tol=1e-12, rel_tol=0.):
                raise ValueError("Each explicit geometric allocation must sum to one")
            return values

        object.__setattr__(self, "zone_ids", zones)
        object.__setattr__(self, "area_fractions", partition(fractions))
        paths = {}
        for path, values in self.localized_path_fractions.items():
            if not isinstance(path, str) or not path.strip():
                raise ValueError("Every localized allocation needs its physical path identity")
            paths[path] = partition(values)
        object.__setattr__(self, "localized_path_fractions", MappingProxyType(paths))


@dataclass(frozen=True, slots=True)
class InsulationHeat:
    warm_temperature_k: float
    cold_temperature_k: float
    vacuum_pressure_pa_abs: float
    power: BoundaryPower
    path_heat_w: tuple[tuple[str, float], ...]
    heat_residual_w: float
    native: Any
    evidence: InsulationEvidence


@dataclass(frozen=True, slots=True)
class PartitionedInsulationHeat:
    warm_temperature_k: float
    wall_temperatures_k: tuple[float, ...]
    vacuum_pressure_pa_abs: float
    zone_heat_w: tuple[float, ...]
    power: BoundaryPower
    native: Any
    allocation: WallHeatAllocation
    evidence: InsulationEvidence


class InsulationClosureError(RuntimeError):
    """Retain a failed native result without assigning it an accepted heat boundary."""

    def __init__(self, native, message):
        self.native = native
        super().__init__(message)


class Lh2dtVacuumInsulation:
    """Keep an actual native VacuumInsulation object; do not collapse it into a UA."""

    _heat_fields = (("radiation", "radiation_heat_W"), ("mli_solid", "mli_solid_heat_W"),
        ("support", "support_heat_W"), ("residual_gas", "residual_gas_heat_W"),
        ("localized", "localized_heat_W"))

    def __init__(self, native, *, evidence: InsulationEvidence, heat_tolerance_w: float = 1e-10):
        if (not callable(getattr(native, "evaluate", None))
                or not callable(getattr(native, "layered_wall_heat_distribution", None))):
            raise TypeError("Supply the native vacuum-insulation evaluator and partition interface")
        if not isinstance(evidence, InsulationEvidence):
            raise TypeError("Supply explicit InsulationEvidence")
        self.native, self.evidence = native, evidence
        self.parameters = native.parameters
        self.area_m2 = finite(self.parameters.area_m2, "native area_m2", positive=True)
        self.maximum_pressure_pa_abs = finite(self.parameters.maximum_valid_vacuum_pressure_Pa,
                                              "native vacuum pressure limit", positive=True)
        self.heat_tolerance_w = finite(heat_tolerance_w, "heat_tolerance_w", positive=True)

    def _inputs(self, warm, cold, pressure):
        if self.native.parameters is not self.parameters:
            raise ValueError("Native insulation parameters changed; bind the new parameters/evidence explicitly")
        warm = finite(warm, "warm_temperature_k", positive=True)
        cold = finite(cold, "cold_temperature_k", positive=True)
        pressure = finite(pressure, "vacuum_pressure_pa_abs")
        if not 0. <= pressure <= self.maximum_pressure_pa_abs:
            raise ValueError("Vacuum pressure lies outside the declared native molecular-flow closure")
        return warm, cold, pressure

    def evaluate(self, warm_temperature_k: float, cold_temperature_k: float,
                 vacuum_pressure_pa_abs: float) -> InsulationHeat:
        warm, cold, pressure = self._inputs(warm_temperature_k, cold_temperature_k,
                                            vacuum_pressure_pa_abs)
        raw = self.native.evaluate(warm, cold, pressure)
        try:
            total = finite(raw.total_heat_into_cold_W, "native total heat")
            terms = tuple((name, finite(getattr(raw, field), f"native {name} heat"))
                          for name, field in self._heat_fields)
            residual = total - fsum(value for _name, value in terms)
            tolerance = max(self.heat_tolerance_w, abs(total) * 1e-12)
            if abs(residual) > tolerance:
                raise ValueError("Native parallel heat paths do not close their total")
            for _name, value in (("total", total), *terms):
                if ((warm == cold and abs(value) > tolerance)
                        or (warm > cold and value < -tolerance)
                        or (warm < cold and value > tolerance)):
                    raise ValueError("Native heat violates the declared warm-to-cold sign/zero-gradient limit")
            if not isclose(finite(raw.vacuum_pressure_Pa, "native pressure"), pressure,
                           rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("Native reported vacuum pressure differs from its supplied absolute pressure")
        except (ValueError, AttributeError, TypeError) as error:
            raise InsulationClosureError(raw, str(error)) from error
        return InsulationHeat(warm, cold, pressure, BoundaryPower(heat_w=total), terms, residual,
                              raw, self.evidence)

    def partition(self, warm_temperature_k: float, wall_temperatures_k: Sequence[float],
                  vacuum_pressure_pa_abs: float, *, allocation: WallHeatAllocation
                  ) -> PartitionedInsulationHeat:
        if not isinstance(allocation, WallHeatAllocation):
            raise TypeError("Supply the explicit wall-area and localized-path allocation")
        temperatures = tuple(wall_temperatures_k)
        if not temperatures or len(temperatures) != len(allocation.zone_ids):
            raise ValueError("Wall temperatures must match the declared geometric zones")
        for temperature in temperatures:
            warm, _cold, pressure = self._inputs(warm_temperature_k, temperature, vacuum_pressure_pa_abs)
        paths = {path.path_id for path in self.parameters.localized_heat_paths}
        if paths != set(allocation.localized_path_fractions):
            raise ValueError("Allocate every native localized path explicitly, without inferred area weighting")
        raw = self.native.layered_wall_heat_distribution(warm, temperatures, pressure,
            area_fractions=allocation.area_fractions,
            localized_path_fractions=allocation.localized_path_fractions)
        try:
            values = tuple(finite(value, "native zone heat") for value in raw)
            if len(values) != len(temperatures):
                raise ValueError("Native heat allocation does not match wall-zone count")
            for value, cold in zip(values, temperatures, strict=True):
                if ((warm == cold and abs(value) > self.heat_tolerance_w)
                        or (warm > cold and value < -self.heat_tolerance_w)
                        or (warm < cold and value > self.heat_tolerance_w)):
                    raise ValueError("Native zone heat violates the signed wall boundary")
        except (ValueError, TypeError) as error:
            raise InsulationClosureError(raw, str(error)) from error
        return PartitionedInsulationHeat(warm, tuple(float(t) for t in temperatures), pressure,
            values, BoundaryPower(heat_w=fsum(values)), raw, allocation, self.evidence)

    def layered_wall_callback(self, allocation: WallHeatAllocation, *,
                              warm_temperature_k: float | Callable[[float, Any], float],
                              vacuum_pressure_pa_abs: float | Callable[[float, Any], float],
                              clock_id: str, start_time_s: float = 0.,
                              observer: Callable[[float, PartitionedInsulationHeat], None] | None = None):
        """Native LayeredTank callback; functions receive absolute time and actual thermo."""
        return LayeredVacuumWallBoundary(self, allocation, warm_temperature_k,
            vacuum_pressure_pa_abs, clock_id, start_time_s, observer)


@dataclass(frozen=True, slots=True)
class LayeredVacuumWallBoundary:
    insulation: Lh2dtVacuumInsulation
    allocation: WallHeatAllocation
    warm_temperature_k: float | Callable[[float, Any], float]
    vacuum_pressure_pa_abs: float | Callable[[float, Any], float]
    clock_id: str
    start_time_s: float = 0.
    observer: Callable[[float, PartitionedInsulationHeat], None] | None = None

    def __post_init__(self):
        if not isinstance(self.clock_id, str) or not self.clock_id.strip():
            raise ValueError("Declare the operation clock for thermal-boundary functions")
        finite(self.start_time_s, "start_time_s")

    def __call__(self, local_time_s: float, thermo):
        time = self.start_time_s + finite(local_time_s, "native local time_s")
        warm = (self.warm_temperature_k(time, thermo) if callable(self.warm_temperature_k)
                else self.warm_temperature_k)
        pressure = (self.vacuum_pressure_pa_abs(time, thermo) if callable(self.vacuum_pressure_pa_abs)
                    else self.vacuum_pressure_pa_abs)
        result = self.insulation.partition(warm, thermo.wall_temperatures_K, pressure,
                                           allocation=self.allocation)
        if self.observer is not None:
            self.observer(time, result)
        return result.zone_heat_w


def layered_inventory_reader(*, rigid_volume_m3: float, wall_heat_capacities_j_k: Sequence[float],
                             basis: PropertyBasis):
    """Independent native layered-state inventory using U=sum(m*h)-p*V and explicit wall C.

    The caller supplies geometrically justified capacities in native wall order.
    Projected rigid-volume states are required; no EOS or native integrator is replaced.
    """
    volume = finite(rigid_volume_m3, "rigid_volume_m3", positive=True)
    capacities = tuple(finite(value, "wall_heat_capacity_j_k", positive=True)
                       for value in wall_heat_capacities_j_k)
    if not capacities or not isinstance(basis, PropertyBasis):
        raise ValueError("Declare wall capacities and the native thermodynamic reference")

    def read(state):
        if len(capacities) != len(state.wall_temperatures_K):
            raise ValueError("Declared wall capacities differ from the native state zones")
        masses = (*state.liquid_masses_kg, *state.vapor_masses_kg)
        enthalpies = (*state.liquid_specific_enthalpies_J_kg, *state.vapor_specific_enthalpies_J_kg)
        if not masses or len(masses) != len(enthalpies):
            raise ValueError("Native cell masses and enthalpies must match")
        masses = tuple(finite(mass, "native cell mass_kg", positive=True) for mass in masses)
        enthalpies = tuple(finite(value, "native cell enthalpy_j_kg") for value in enthalpies)
        pressure = finite(state.pressure_Pa, "native pressure_pa_abs", positive=True)
        wall = fsum(capacity * finite(temperature, "native wall temperature_k", positive=True)
                    for capacity, temperature in zip(capacities, state.wall_temperatures_K, strict=True))
        internal = fsum(mass * enthalpy for mass, enthalpy in zip(masses, enthalpies, strict=True)) - pressure * volume
        return ConservedInventory(basis, fsum(masses), internal, wall)

    return read
