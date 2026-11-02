"""Bounded steady operating-point solve around the existing Brayton cycle.

The host solves only three caller-declared quantities: compressor corrected
speed, compressor pressure ratio, and inlet-air mass flow. A caller speed-link
callback supplies turbine corrected speed. Compressor/turbine corrected-flow
conversions are also caller-owned and evidence-bound. Cantera thermodynamics and
equilibrium remain in ``run_open_cycle_brayton``; this module adds no cycle EOS.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from .compressor_map import (
    CompressorComponentMap,
    CompressorMapPoint,
    MapMatchedBraytonInputs,
    MapMatchedBraytonRun,
    interpolate_compressor_map,
    run_map_matched_brayton,
)
from .open_brayton import OpenBraytonInputs, OpenBraytonRun, run_open_cycle_brayton
from .turbine_map import TurbineComponentMap, TurbineMapPoint, interpolate_turbine_map

_PENDING_SOLUTIONS: set[object] = set()


def _identity(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label} evidence identity")
    return value.strip()


def _pair(values, label, *, positive=False):
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{label} must be a two-value numeric interval")
    result = tuple(finite(value, label, positive=positive) for value in values)
    if len(result) != 2 or result[0] >= result[1]:
        raise ValueError(f"{label} bounds must increase strictly")
    return result


def _interval_within(bounds, axis, label):
    if bounds[0] < axis[0] or bounds[1] > axis[-1]:
        raise ValueError(f"{label} solver bounds must remain within the supplied map domain")


@dataclass(frozen=True, slots=True)
class MapOperatingSeed:
    """One initial guess for the three supported caller-selected unknowns."""

    compressor_corrected_speed: float
    compressor_pressure_ratio: float
    air_mass_flow_kg_s: float

    def __post_init__(self):
        object.__setattr__(self, "compressor_corrected_speed", finite(
            self.compressor_corrected_speed, "compressor corrected speed", positive=True))
        ratio = finite(self.compressor_pressure_ratio, "compressor pressure ratio", positive=True)
        if ratio <= 1.:
            raise ValueError("Compressor pressure ratio must exceed one")
        object.__setattr__(self, "compressor_pressure_ratio", ratio)
        object.__setattr__(self, "air_mass_flow_kg_s", finite(
            self.air_mass_flow_kg_s, "inlet-air mass flow", positive=True))

    def vector(self):
        return np.asarray((self.compressor_corrected_speed,
                           self.compressor_pressure_ratio,
                           self.air_mass_flow_kg_s), dtype=float)


@dataclass(frozen=True, slots=True)
class SteadyMapSolveInputs:
    """Bounds, evidence and residual closures for one steady map-matched solve.

    The exact solve vector is ``(compressor corrected speed, compressor pressure
    ratio, inlet-air mass flow)``. Turbine corrected speed is not independently
    optimized: ``speed_link`` maps compressor corrected speed to it. Both flow
    converters return corrected mass flow in kg/s for comparison with their
    respective admitted maps. They receive the actual flow, the existing native
    cycle result, and the selected interpolated map point.
    """

    cycle_inputs: OpenBraytonInputs
    compressor_map: CompressorComponentMap
    turbine_map: TurbineComponentMap
    compressor_speed_bounds: tuple[float, float]
    compressor_pressure_ratio_bounds: tuple[float, float]
    air_mass_flow_bounds_kg_s: tuple[float, float]
    seeds: tuple[MapOperatingSeed, ...]
    speed_link: Callable[[float], float] = field(repr=False, compare=False)
    compressor_corrected_flow: Callable[[float, OpenBraytonRun, CompressorMapPoint], float] = field(
        repr=False, compare=False)
    turbine_corrected_flow: Callable[[float, OpenBraytonRun, TurbineMapPoint], float] = field(
        repr=False, compare=False)
    speed_link_evidence_id: str
    compressor_flow_evidence_id: str
    turbine_flow_evidence_id: str
    shaft_loss_evidence_id: str
    shaft_target_evidence_id: str
    shaft_mechanical_loss_w: float
    shaft_residual_target_w: float
    flow_relative_tolerance: float = 1e-3
    flow_absolute_tolerance_kg_s: float = 1e-6
    shaft_absolute_tolerance_w: float = 1e-2
    root_merge_tolerance: float = 1e-5
    max_nfev: int = 120
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.cycle_inputs) is not OpenBraytonInputs:
            raise TypeError("cycle_inputs must be OpenBraytonInputs")
        if type(self.compressor_map) is not CompressorComponentMap:
            raise TypeError("compressor_map must be CompressorComponentMap")
        if type(self.turbine_map) is not TurbineComponentMap:
            raise TypeError("turbine_map must be TurbineComponentMap")
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if self.turbine_map.pressure_ratio_convention != "inlet-over-exit-total-pressure":
            raise ValueError("Turbine map must declare inlet-over-exit total-pressure ratio")
        if not callable(self.speed_link) or not callable(self.compressor_corrected_flow) or not callable(self.turbine_corrected_flow):
            raise TypeError("Explicit speed-link and two corrected-flow callbacks are required")
        for name in ("speed_link_evidence_id", "compressor_flow_evidence_id",
                     "turbine_flow_evidence_id", "shaft_loss_evidence_id",
                     "shaft_target_evidence_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        speed_bounds = _pair(self.compressor_speed_bounds, "compressor corrected speed", positive=True)
        ratio_bounds = _pair(self.compressor_pressure_ratio_bounds,
                             "compressor pressure ratio", positive=True)
        flow_bounds = _pair(self.air_mass_flow_bounds_kg_s, "inlet-air mass flow", positive=True)
        _interval_within(speed_bounds, self.compressor_map.corrected_speed,
                         "Compressor corrected-speed")
        _interval_within(ratio_bounds, self.compressor_map.compression_pressure_ratio,
                         "Compressor pressure-ratio")
        if ratio_bounds[0] <= 1.:
            raise ValueError("Compressor pressure-ratio bounds must exceed one")
        object.__setattr__(self, "compressor_speed_bounds", speed_bounds)
        object.__setattr__(self, "compressor_pressure_ratio_bounds", ratio_bounds)
        object.__setattr__(self, "air_mass_flow_bounds_kg_s", flow_bounds)
        pressure_scale = (self.cycle_inputs.air_pressure_pa
                          * self.cycle_inputs.combustor_pressure_recovery
                          / self.cycle_inputs.turbine_exhaust_pressure_pa)
        turbine_ratios = tuple(value * pressure_scale for value in ratio_bounds)
        if (turbine_ratios[0] < self.turbine_map.expansion_pressure_ratio[0]
                or turbine_ratios[1] > self.turbine_map.expansion_pressure_ratio[-1]):
            raise ValueError("Declared pressure-ratio solve bounds exceed the turbine-map domain")
        seeds = tuple(self.seeds)
        if len(seeds) < 2 or any(type(seed) is not MapOperatingSeed for seed in seeds):
            raise ValueError("At least two typed seeds are required for multi-start ambiguity reporting")
        if len({tuple(seed.vector()) for seed in seeds}) != len(seeds):
            raise ValueError("Multi-start seeds must be distinct")
        lows = np.asarray((speed_bounds[0], ratio_bounds[0], flow_bounds[0]))
        highs = np.asarray((speed_bounds[1], ratio_bounds[1], flow_bounds[1]))
        for seed in seeds:
            vector = seed.vector()
            if np.any(vector < lows) or np.any(vector > highs):
                raise ValueError("Every seed must lie inside the caller-declared solver bounds")
        object.__setattr__(self, "seeds", seeds)
        for name, label in (("flow_relative_tolerance", "flow relative tolerance"),
                            ("flow_absolute_tolerance_kg_s", "flow absolute tolerance"),
                            ("shaft_absolute_tolerance_w", "shaft residual tolerance"),
                            ("root_merge_tolerance", "root merge tolerance")):
            value = finite(getattr(self, name), label, positive=True)
            if name == "flow_relative_tolerance" and value > .1:
                raise ValueError("Flow relative tolerance cannot exceed 0.1")
            if name == "root_merge_tolerance" and value > .1:
                raise ValueError("Root merge tolerance cannot exceed 0.1 of the declared range")
            object.__setattr__(self, name, value)
        loss = finite(self.shaft_mechanical_loss_w, "shaft mechanical loss")
        if loss < 0.:
            raise ValueError("Shaft mechanical loss cannot be negative")
        object.__setattr__(self, "shaft_mechanical_loss_w", loss)
        object.__setattr__(self, "shaft_residual_target_w", finite(
            self.shaft_residual_target_w, "shaft residual target"))
        if isinstance(self.max_nfev, bool) or not isinstance(self.max_nfev, int) or self.max_nfev < 10:
            raise ValueError("max_nfev must be an integer of at least ten")
        object.__setattr__(self, "_seal", self._payload())

    @property
    def unknowns(self):
        """The complete explicit unknown vector used by this 3-residual closure."""
        return ("compressor_corrected_speed", "compressor_pressure_ratio", "air_mass_flow_kg_s")

    def _payload(self):
        return (id(self.cycle_inputs), repr(self.cycle_inputs), id(self.compressor_map),
                id(self.turbine_map), self.compressor_speed_bounds,
                self.compressor_pressure_ratio_bounds, self.air_mass_flow_bounds_kg_s,
                tuple(tuple(seed.vector()) for seed in self.seeds), id(self.speed_link),
                id(self.compressor_corrected_flow), id(self.turbine_corrected_flow),
                self.speed_link_evidence_id, self.compressor_flow_evidence_id,
                self.turbine_flow_evidence_id, self.shaft_loss_evidence_id,
                self.shaft_target_evidence_id, self.shaft_mechanical_loss_w,
                self.shaft_residual_target_w, self.flow_relative_tolerance,
                self.flow_absolute_tolerance_kg_s, self.shaft_absolute_tolerance_w,
                self.root_merge_tolerance, self.max_nfev)

    def require_current(self):
        self.compressor_map.require_current()
        self.turbine_map.require_current()
        if not self._seal or self._seal != self._payload():
            raise ValueError("Steady-map solve inputs changed after admission")
        return self


@dataclass(frozen=True, slots=True)
class SteadyMapOperatingPoint:
    """One converged map/cycle/shaft root with retained original native run."""

    inputs: SteadyMapSolveInputs
    compressor_corrected_speed: float
    compressor_pressure_ratio: float
    air_mass_flow_kg_s: float
    turbine_corrected_speed: float
    cycle_run: MapMatchedBraytonRun
    compressor_flow_residual_kg_s: float
    turbine_flow_residual_kg_s: float
    shaft_residual_w: float
    optimizer_nfev: int

    def __post_init__(self):
        self.require_current()

    def require_current(self):
        self.inputs.require_current()
        self.cycle_run.require_current()
        inps = self.cycle_run.inputs
        if (inps.compressor_corrected_speed != self.compressor_corrected_speed
                or inps.compressor_pressure_ratio != self.compressor_pressure_ratio
                or inps.air_mass_flow_kg_s != self.air_mass_flow_kg_s
                or inps.turbine_corrected_speed != self.turbine_corrected_speed):
            raise ValueError("Solved operating point is detached from its retained map cycle")
        linked_speed = finite(self.inputs.speed_link(self.compressor_corrected_speed),
                              "speed-link turbine corrected speed", positive=True)
        if not math.isclose(linked_speed, self.turbine_corrected_speed,
                            rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Retained turbine corrected speed differs from the declared speed link")
        compressor = self.inputs.compressor_corrected_flow(
            self.air_mass_flow_kg_s, self.cycle_run.turbine_run.cycle_run,
            self.cycle_run.compressor_point)
        turbine_actual = self.air_mass_flow_kg_s * (
            1. + inps.cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
        turbine = self.inputs.turbine_corrected_flow(
            turbine_actual, self.cycle_run.turbine_run.cycle_run,
            self.cycle_run.turbine_run.map_point)
        expected = (float(compressor) - self.cycle_run.compressor_point.corrected_mass_flow_kg_s,
                    float(turbine) - self.cycle_run.turbine_run.map_point.corrected_mass_flow_kg_s,
                    self.cycle_run.shaft_ledger.shaft_residual_w
                    - self.inputs.shaft_mechanical_loss_w
                    - self.inputs.shaft_residual_target_w)
        actual = (self.compressor_flow_residual_kg_s,
                  self.turbine_flow_residual_kg_s, self.shaft_residual_w)
        for label, value, expected_value in zip(("compressor flow", "turbine flow", "shaft"),
                                                actual, expected, strict=True):
            if not math.isclose(finite(value, f"{label} residual"), expected_value,
                                rel_tol=1e-12, abs_tol=1e-8):
                raise ValueError(f"Solved {label} residual differs from its retained maps/cycle")
        if abs(expected[0]) > max(self.inputs.flow_absolute_tolerance_kg_s,
                                  self.inputs.flow_relative_tolerance
                                  * self.cycle_run.compressor_point.corrected_mass_flow_kg_s):
            raise ValueError("Compressor corrected-flow closure exceeds the declared tolerance")
        if abs(expected[1]) > max(self.inputs.flow_absolute_tolerance_kg_s,
                                  self.inputs.flow_relative_tolerance
                                  * self.cycle_run.turbine_run.map_point.corrected_mass_flow_kg_s):
            raise ValueError("Turbine corrected-flow closure exceeds the declared tolerance")
        if abs(expected[2]) > self.inputs.shaft_absolute_tolerance_w:
            raise ValueError("Shaft residual is outside the declared target tolerance")
        return self


@dataclass(frozen=True, slots=True)
class SteadyMapSeedAttempt:
    """Convergence record for one initial seed, including nonaccepted attempts."""

    seed: MapOperatingSeed
    converged: bool
    final_vector: tuple[float, float, float] | None
    scaled_residuals: tuple[float, float, float] | None
    nfev: int
    message: str
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class SteadyMapSolveResult:
    """All distinct roots and seed attempts; ambiguity is never silently hidden."""

    inputs: SteadyMapSolveInputs
    status: str
    candidates: tuple[SteadyMapOperatingPoint, ...]
    attempts: tuple[SteadyMapSeedAttempt, ...]
    _issuer: object = field(repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_SOLUTIONS:
            raise TypeError("Create solve results through solve_steady_map_operating_point")
        _PENDING_SOLUTIONS.remove(self._issuer)
        if self.status not in {"unique", "multiple", "incomplete_search", "no_converged_root"}:
            raise ValueError("Unknown multi-start solve status")
        failed_seed = any(not attempt.converged for attempt in self.attempts)
        expected = ("multiple" if len(self.candidates) > 1 else
                    "unique" if len(self.candidates) == 1 and not failed_seed else
                    "incomplete_search" if failed_seed else "no_converged_root")
        if self.status != expected:
            raise ValueError("Solve status differs from the retained distinct candidate count")
        if not self.attempts:
            raise ValueError("Every seed must retain one optimizer attempt")
        for candidate in self.candidates:
            candidate.require_current()

    def require_current(self):
        self.inputs.require_current()
        for candidate in self.candidates:
            candidate.require_current()
        return self

    @property
    def unique_candidate(self):
        """Return the sole root or reject ambiguous/empty results."""
        if self.status != "unique":
            raise ValueError(f"A unique accepted point is unavailable: solve status is {self.status}")
        return self.candidates[0].require_current()


def _trial(phase_factory, problem, vector):
    speed, pressure_ratio, air_flow = (float(value) for value in vector)
    compressor_point = interpolate_compressor_map(
        problem.compressor_map, corrected_speed=speed,
        compression_pressure_ratio=pressure_ratio)
    turbine_speed = finite(problem.speed_link(speed), "speed-link turbine corrected speed", positive=True)
    if not problem.turbine_map.corrected_speed[0] <= turbine_speed <= problem.turbine_map.corrected_speed[-1]:
        raise ValueError("Speed-link callback placed turbine speed outside its admitted map")
    turbine_ratio = (problem.cycle_inputs.air_pressure_pa * pressure_ratio
                     * problem.cycle_inputs.combustor_pressure_recovery
                     / problem.cycle_inputs.turbine_exhaust_pressure_pa)
    turbine_point = interpolate_turbine_map(
        problem.turbine_map, corrected_speed=turbine_speed,
        expansion_pressure_ratio=turbine_ratio)
    from dataclasses import replace

    import cantera as ct

    cycle_inputs = replace(
        problem.cycle_inputs,
        compressor_pressure_ratio=pressure_ratio,
        compressor_isentropic_efficiency=compressor_point.isentropic_efficiency,
        turbine_isentropic_efficiency=turbine_point.isentropic_efficiency,
    )
    phase = phase_factory()
    if not isinstance(phase, ct.Solution):
        raise TypeError("phase_factory must return a native Cantera Solution")
    cycle = run_open_cycle_brayton(phase, cycle_inputs)
    corrected_air_flow = finite(problem.compressor_corrected_flow(
        air_flow, cycle, compressor_point), "converted compressor corrected flow", positive=True)
    gas_flow = air_flow * (1. + cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
    corrected_gas_flow = finite(problem.turbine_corrected_flow(
        gas_flow, cycle, turbine_point), "converted turbine corrected flow", positive=True)
    compressor_power = cycle.compressor_work_j_kg_air * air_flow
    turbine_power = cycle.turbine_work_j_kg_air * air_flow
    shaft_residual = (turbine_power - compressor_power
                      - problem.shaft_mechanical_loss_w
                      - problem.shaft_residual_target_w)
    flow_scale_c = max(problem.flow_absolute_tolerance_kg_s,
                       problem.flow_relative_tolerance * compressor_point.corrected_mass_flow_kg_s)
    flow_scale_t = max(problem.flow_absolute_tolerance_kg_s,
                       problem.flow_relative_tolerance * turbine_point.corrected_mass_flow_kg_s)
    shaft_scale = max(problem.shaft_absolute_tolerance_w, abs(turbine_power),
                      abs(compressor_power), abs(problem.shaft_mechanical_loss_w),
                      abs(problem.shaft_residual_target_w), 1.)
    residuals = np.asarray(((corrected_air_flow - compressor_point.corrected_mass_flow_kg_s)
                            / flow_scale_c,
                            (corrected_gas_flow - turbine_point.corrected_mass_flow_kg_s)
                            / flow_scale_t,
                            shaft_residual / shaft_scale), dtype=float)
    return (residuals, cycle, compressor_point, turbine_point, turbine_speed,
            corrected_air_flow, corrected_gas_flow, shaft_residual)


def _root_close(first, second, lower, upper, tolerance):
    scale = np.maximum(upper - lower, 1e-15)
    return bool(np.all(np.abs((first - second) / scale) <= tolerance))


def solve_steady_map_operating_point(phase_factory, inputs: SteadyMapSolveInputs) -> SteadyMapSolveResult:
    """Solve map-flow and shaft residuals with bounded multi-start least squares.

    The unknown vector contains exactly compressor corrected speed, compressor
    pressure ratio and inlet-air mass flow. Three residuals are solved: compressor
    corrected flow, turbine corrected flow, and net shaft power minus explicit
    loss and target. Turbine corrected speed and both corrected-flow conversions
    are never inferred; caller callbacks and evidence IDs supply them.

    Each trial delegates all cycle thermodynamics and HP equilibrium to the
    existing Cantera Brayton runner. Map interpolation rejects extrapolation.
    Only roots meeting every physical tolerance are returned as candidates.
    Multiple distinct roots produce status ``multiple``; no nearest-root choice
    is made on behalf of the caller.
    """
    from scipy.optimize import least_squares

    if type(inputs) is not SteadyMapSolveInputs:
        raise TypeError("Supply SteadyMapSolveInputs")
    if not callable(phase_factory):
        raise TypeError("A native Cantera phase factory is required")
    inputs.require_current()
    low = np.asarray((inputs.compressor_speed_bounds[0],
                      inputs.compressor_pressure_ratio_bounds[0],
                      inputs.air_mass_flow_bounds_kg_s[0]), dtype=float)
    high = np.asarray((inputs.compressor_speed_bounds[1],
                       inputs.compressor_pressure_ratio_bounds[1],
                       inputs.air_mass_flow_bounds_kg_s[1]), dtype=float)
    roots: list[SteadyMapOperatingPoint] = []
    attempts: list[SteadyMapSeedAttempt] = []
    for seed in inputs.seeds:
        last_error = [None]

        def residual(vector):
            try:
                return _trial(phase_factory, inputs, vector)[0]
            except Exception as exc:
                last_error[0] = exc
                return np.full(3, 1e6, dtype=float)

        try:
            _trial(phase_factory, inputs, seed.vector())
            solution = least_squares(
                residual, seed.vector(), bounds=(low, high), method="trf",
                x_scale=np.maximum(high-low, 1e-12), max_nfev=inputs.max_nfev,
                ftol=1e-10, xtol=1e-10, gtol=1e-10,
            )
            final = _trial(phase_factory, inputs, solution.x)
            scaled = tuple(float(v) for v in final[0])
            physical_ok = (
                abs(final[5] - final[2].corrected_mass_flow_kg_s)
                <= max(inputs.flow_absolute_tolerance_kg_s,
                       inputs.flow_relative_tolerance * final[2].corrected_mass_flow_kg_s)
                and abs(final[6] - final[3].corrected_mass_flow_kg_s)
                <= max(inputs.flow_absolute_tolerance_kg_s,
                       inputs.flow_relative_tolerance * final[3].corrected_mass_flow_kg_s)
                and abs(final[7]) <= inputs.shaft_absolute_tolerance_w
            )
            candidate = None
            if solution.success and physical_ok:
                speed, ratio, air = (float(v) for v in solution.x)
                comp_factor = final[5] / air
                turbine_actual = air * (1. + inputs.cycle_inputs.hydrogen_fuel_to_air_mass_ratio)
                turb_factor = final[6] / turbine_actual
                matched_inputs = MapMatchedBraytonInputs(
                    cycle_inputs=inputs.cycle_inputs,
                    compressor_map=inputs.compressor_map,
                    compressor_corrected_speed=speed,
                    compressor_pressure_ratio=ratio,
                    compressor_actual_to_corrected_flow_factor=comp_factor,
                    turbine_map=inputs.turbine_map,
                    turbine_corrected_speed=final[4],
                    turbine_actual_to_corrected_flow_factor=turb_factor,
                    air_mass_flow_kg_s=air,
                    speed_link_evidence_id=inputs.speed_link_evidence_id,
                    compressor_flow_evidence_id=inputs.compressor_flow_evidence_id,
                    turbine_flow_evidence_id=inputs.turbine_flow_evidence_id,
                    relative_flow_tolerance=inputs.flow_relative_tolerance,
                    absolute_flow_tolerance_kg_s=inputs.flow_absolute_tolerance_kg_s,
                )
                # Final cycle is rerun by the existing map-composition API,
                # retaining its issuer-checked native run and map evidence.
                cycle_run = run_map_matched_brayton(phase_factory(), matched_inputs)
                candidate = SteadyMapOperatingPoint(
                    inputs, speed, ratio, air, final[4], cycle_run,
                    final[5] - final[2].corrected_mass_flow_kg_s,
                    final[6] - final[3].corrected_mass_flow_kg_s,
                    final[7], int(solution.nfev),
                )
                if not any(_root_close(
                        solution.x,
                        np.asarray((old.compressor_corrected_speed,
                                    old.compressor_pressure_ratio,
                                    old.air_mass_flow_kg_s)), low, high,
                        inputs.root_merge_tolerance) for old in roots):
                    roots.append(candidate)
            attempts.append(SteadyMapSeedAttempt(
                seed, candidate is not None, tuple(float(v) for v in solution.x), scaled,
                int(solution.nfev), str(solution.message),
                None if candidate is not None else (str(last_error[0]) if last_error[0]
                                                      else "optimizer failed or residual tolerances were not met"),
            ))
        except Exception as exc:
            attempts.append(SteadyMapSeedAttempt(
                seed, False, None, None, 0, "seed run failed", str(exc),
            ))
    failed_seed = any(not attempt.converged for attempt in attempts)
    status = ("multiple" if len(roots) > 1 else
              "unique" if len(roots) == 1 and not failed_seed else
              "incomplete_search" if failed_seed else "no_converged_root")
    token = object()
    _PENDING_SOLUTIONS.add(token)
    return SteadyMapSolveResult(inputs, status, tuple(roots), tuple(attempts), token)
