"""Quasi-steady grid-power dispatch into the shared hydrogen stack kernel.

The adapter converts caller-owned AC power intervals into held current commands
for the existing ``HydrogenStack`` and ``ThermalStackStage`` APIs. It owns no
rectifier dynamics, material inventory, stack polarization law, or thermal solve.
"""

from dataclasses import dataclass
import math

from ..core import finite
from ..electrochemistry import HydrogenStack
from ..electrochemical_thermal import ThermalStackStage


@dataclass(frozen=True, slots=True)
class GridPowerInterval:
    """Held AC bus power and explicit interval identity (SI units)."""

    identifier: str
    start_s: float
    end_s: float
    clock_id: str
    source_id: str
    available_ac_power_w: float
    fixed_auxiliary_ac_power_w: float = 0.0

    def __post_init__(self):
        for name in ("identifier", "clock_id", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Declare {name}")
        if finite(self.start_s, "grid interval start") >= finite(self.end_s, "grid interval end"):
            raise ValueError("Grid power intervals must have positive duration")
        for name in ("available_ac_power_w", "fixed_auxiliary_ac_power_w"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True, slots=True)
class GridElectrolysisStep:
    source: GridPowerInterval
    thermal_command: ThermalStackStage
    stack_result: object
    rectifier_efficiency: float
    stack_dc_power_w: float
    rectifier_loss_w: float
    auxiliary_ac_power_w: float
    grid_ac_power_w: float
    curtailed_ac_power_w: float
    current_density_resolution_a_m2: float


@dataclass(frozen=True, slots=True)
class GridElectrolysisSchedule:
    """Immutable dispatch result; run its commands through the existing thermal owner."""

    stack: HydrogenStack
    steps: tuple[GridElectrolysisStep, ...]
    current_density_limit_a_m2: float
    current_density_resolution_a_m2: float
    evidence_id: str

    @property
    def thermal_commands(self):
        return tuple(step.thermal_command for step in self.steps)

    @property
    def hydrogen_production_mol(self):
        return math.fsum(step.stack_result.hydrogen_production_mol_s
                         * (step.source.end_s-step.source.start_s) for step in self.steps)

    @property
    def grid_energy_j(self):
        return math.fsum(step.grid_ac_power_w*(step.source.end_s-step.source.start_s)
                         for step in self.steps)


def dispatch_grid_power_to_electrolysis(stack, intervals, *,
                                        coolant_temperature_k,
                                        maximum_current_density_a_m2,
                                        current_density_resolution_a_m2,
                                        rectifier_efficiency,
                                        evidence_id):
    """Choose the highest grid-feasible sampled current in each held interval.

    The search is explicit and quantized: it evaluates ``HydrogenStack`` at
    ``0, resolution, ...`` through the declared maximum. No monotonicity of an
    arbitrary user loss callback is assumed. Callers select the current grid
    resolution and must refine it for convergence studies. Intervals are not
    interpolated; each becomes one held thermal command on its supplied clock.
    """
    if not isinstance(stack, HydrogenStack):
        raise TypeError("Reuse the existing shared HydrogenStack")
    for name, value in (("evidence_id", evidence_id),):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name}")
    coolant = finite(coolant_temperature_k, "prescribed coolant temperature K", positive=True)
    maximum = finite(maximum_current_density_a_m2, "maximum current density", positive=True)
    resolution = finite(current_density_resolution_a_m2, "current-density grid resolution", positive=True)
    efficiency = finite(rectifier_efficiency, "AC/DC conversion efficiency", positive=True)
    if efficiency > 1:
        raise ValueError("Rectifier efficiency must be in (0, 1]")
    if resolution > maximum:
        raise ValueError("Current-density resolution cannot exceed its declared maximum")
    commands = tuple(intervals)
    if not commands or any(type(v) is not GridPowerInterval for v in commands):
        raise TypeError("Supply one or more typed grid-power intervals")
    if len({v.identifier for v in commands}) != len(commands):
        raise ValueError("Grid interval identifiers must be unique")
    clock = commands[0].clock_id
    if any(v.clock_id != clock for v in commands):
        raise ValueError("All dispatch intervals must use the same declared clock")
    for left, right in zip(commands[:-1], commands[1:], strict=True):
        if left.end_s != right.start_s:
            raise ValueError("Grid dispatch intervals must be contiguous and ordered")
    count = math.floor(maximum/resolution)
    current_grid = tuple(index*resolution for index in range(count+1))
    if current_grid[-1] < maximum:
        current_grid += (maximum,)
    results = []
    for interval in commands:
        feasible = []
        for density in current_grid:
            result = stack.evaluate(density, coolant, mode="electrolysis")
            if interval.fixed_auxiliary_ac_power_w + result.electric_input_w/efficiency \
                    <= interval.available_ac_power_w:
                feasible.append((density, result))
        if not feasible:
            raise ValueError("Even zero-current standby auxiliaries exceed the available grid power")
        density, result = feasible[-1]
        grid_power = interval.fixed_auxiliary_ac_power_w + result.electric_input_w/efficiency
        curtailed = interval.available_ac_power_w-grid_power
        command = ThermalStackStage(
            interval.identifier, interval.start_s, interval.end_s, density,
            coolant, "electrolysis", 1.0, 0.0,
        )
        results.append(GridElectrolysisStep(
            interval, command, result, efficiency, result.electric_input_w,
            result.electric_input_w*(1./efficiency-1.),
            interval.fixed_auxiliary_ac_power_w, grid_power, curtailed, resolution,
        ))
    return GridElectrolysisSchedule(stack, tuple(results), maximum, resolution, evidence_id)
