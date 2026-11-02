"""Checked native DynamicLH2PoolX boundaries; spreading and heat remain native.

The current native engine hard-codes normal hydrogen. A supplied ground history
must already describe saturated liquid on the surface; no jet partition is made.
"""

import math
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..core import Origin, ThermoState, finite
from ..release import SourceLocation
from ..sources import IntervalMassSource


@dataclass(frozen=True, slots=True)
class DeclaredGroundInflow:
    native: Any
    location: SourceLocation
    liquid_state: ThermoState
    start_time_s: float
    end_time_s: float
    origin: Origin
    evidence_id: str
    end_reason: str
    schedule_times_s: tuple[float, ...] = field(init=False)
    schedule_rates_kg_s: tuple[float, ...] = field(init=False)

    def __post_init__(self):
        start, end = finite(self.start_time_s, "start_time_s"), finite(self.end_time_s, "end_time_s")
        times = tuple(finite(value, "native inflow time") for value in self.native.times_s)
        rates = tuple(finite(value, "native inflow rate") for value in self.native.rates_kg_s)
        if (end <= start or not times or times[0] != 0. or len(times) != len(rates)
                or any(b <= a for a, b in zip(times, times[1:]))
                or times[-1] > end-start or any(rate < 0. for rate in rates)):
            raise ValueError("Declare a finite ground window and an ordered nonnegative native step history")
        if not callable(getattr(self.native, "rate_at", None)) or not self.evidence_id.strip():
            raise ValueError("The native history needs its rate function and ground-inflow evidence")
        if self.end_reason not in {"window_end", "isolation"}:
            raise ValueError("Declare the ground-history termination meaning")
        if self.end_reason == "isolation" and rates[-1] != 0.:
            raise ValueError("An isolated ground history must end with zero input")
        if self.liquid_state.vapor_mass_fraction != 0.:
            raise ValueError("The native pool requires explicitly saturated liquid already on the surface")
        object.__setattr__(self, "schedule_times_s", times)
        object.__setattr__(self, "schedule_rates_kg_s", rates)
        object.__setattr__(self, "origin", Origin(self.origin))

    def cumulative_mass_kg(self, time_s: float, *, clock_id: str) -> float:
        target = finite(time_s, "time_s")
        if clock_id != self.location.clock_id or not self.start_time_s <= target <= self.end_time_s:
            raise ValueError("Ground integration requires its declared clock and finite window")
        elapsed = target-self.start_time_s
        times = self.schedule_times_s
        ends = (*times[1:], self.end_time_s-self.start_time_s)
        return math.fsum(rate*max(0., min(elapsed, right)-left)
                         for left, right, rate in zip(times, ends, self.schedule_rates_kg_s, strict=True))


@dataclass(frozen=True, slots=True)
class PoolTolerances:
    absolute_mass_kg: float = 1e-10
    relative_mass: float = 1e-8
    maximum_numerical_adjustment_kg: float = 0.
    maximum_escaped_mass_kg: float = 0.
    property_relative: float = 1e-8
    event_clock_roundoff_s: float = 0.

    def __post_init__(self):
        for name in ("absolute_mass_kg", "relative_mass", "property_relative"):
            finite(getattr(self, name), name, positive=True)
        for name in ("maximum_numerical_adjustment_kg", "maximum_escaped_mass_kg", "event_clock_roundoff_s"):
            if finite(getattr(self, name), name) < 0.:
                raise ValueError("Pool adjustment, escape and clock budgets cannot be negative")


@dataclass(slots=True)
class EventClockInflow:
    """An explicit bounded time correction before calling the actual native input.

    The reviewed runner accepts this dataclass structurally. Its native input
    remains available, and every nonzero time correction is retained.
    """

    times_s: tuple[float, ...]
    rates_kg_s: tuple[float, ...]
    native: Any
    roundoff_s: float
    corrections_s: list[tuple[float, float]] = field(default_factory=list)

    def rate_at(self, time_s):
        index = bisect_left(self.times_s, time_s)
        adjacent = self.times_s[max(0, index-1):index+1]
        nearest = min(adjacent, key=lambda knot: abs(knot-time_s))
        selected = nearest if abs(nearest-time_s) <= self.roundoff_s else time_s
        if selected != time_s:
            self.corrections_s.append((time_s, selected))
        return self.native.rate_at(selected)


@dataclass(frozen=True, slots=True)
class PoolSampleAudit:
    time_s: float
    native: Any
    declared_cumulative_inflow_kg: float
    independently_recomputed_mass_residual_kg: float
    mass_limit_kg: float


class PoolCouplingError(ValueError):
    def __init__(self, native, issues):
        self.native, self.issues = native, tuple(issues)
        super().__init__("; ".join(self.issues))


@dataclass(frozen=True, slots=True)
class NativePoolRun:
    native: Any
    config: Any
    inflow: DeclaredGroundInflow
    vapor_location: SourceLocation
    liquid_state: ThermoState
    vapor_state: ThermoState
    samples: tuple[PoolSampleAudit, ...]
    engine_id: str
    issues: tuple[str, ...]
    input_clock: EventClockInflow | None

    @property
    def admissible(self) -> bool:
        return not self.issues

    @property
    def validation_qualified(self) -> bool:
        return False

    @property
    def maximum_input_clock_correction_s(self) -> float:
        return max((abs(b-a) for a, b in self.input_clock.corrections_s), default=0.) if self.input_clock else 0.

    def evaporation_source(self, *, end_reason: str = "window_end") -> IntervalMassSource:
        if self.issues:
            raise PoolCouplingError(self.native, self.issues)
        if end_reason == "depleted" and (self.samples[-1].native.liquid_mass_kg != 0.
                                        or self.inflow.schedule_rates_kg_s[-1] != 0.):
            raise ValueError("Depletion requires zero remaining liquid and no continuing declared supply")
        if end_reason == "isolation":
            raise ValueError("Stopping liquid input does not isolate the pool evaporation source")
        cumulative = np.array([row.native.cumulative_evaporation_kg for row in self.samples])
        return IntervalMassSource(self.vapor_location, np.array([row.time_s for row in self.samples]),
            np.diff(cumulative), self.vapor_state, Origin.PREDICTED,
            self.engine_id+":"+self.inflow.evidence_id, end_reason)


class NativeDynamicPool:
    def __init__(self, runner: Callable[..., Any], reference_properties, *, engine_id: str,
                 tolerances: PoolTolerances | None = None):
        basis = reference_properties.basis
        if basis.fluid != "Hydrogen" or basis.spin_composition != "normal":
            raise ValueError("The checked native pool currently supports normal Hydrogen only")
        if not engine_id.strip():
            raise ValueError("Declare the exact native pool engine identity")
        self.runner, self.properties, self.engine_id = runner, reference_properties, engine_id
        self.tolerances = tolerances or PoolTolerances()

    def run(self, config, inflow: DeclaredGroundInflow, *, output_times_s,
            vapor_location: SourceLocation, require_closed: bool = True) -> NativePoolRun:
        times = tuple(finite(value, "output_times_s") for value in output_times_s)
        if (len(times) < 2 or times[0] != inflow.start_time_s or times[-1] != inflow.end_time_s
                or any(b <= a for a, b in zip(times, times[1:]))):
            raise ValueError("Pool output times must cover the entire ordered ground-history window")
        if (vapor_location.clock_id != inflow.location.clock_id
                or vapor_location.coordinate_frame_id != inflow.location.coordinate_frame_id
                or vapor_location.position_m != inflow.location.position_m):
            raise ValueError("Pool vapor and ground boundaries need a common clock, frame and center")
        if (tuple(inflow.native.times_s) != inflow.schedule_times_s
                or tuple(inflow.native.rates_kg_s) != inflow.schedule_rates_kg_s):
            raise ValueError("The native ground schedule changed after its boundary was declared")
        self.properties.basis.require_compatible(inflow.liquid_state.basis)
        pressure = finite(config.ambient_pressure_Pa, "ambient_pressure_Pa", positive=True)
        if config.initial_liquid_mass_kg != 0.:
            raise ValueError("Initial pool inventory is not supported by the checked spreading route")
        liquid, vapor = self.properties.saturated(pressure, 0.), self.properties.saturated(pressure, 1.)
        for name in ("pressure_pa", "temperature_k", "density_kg_m3", "enthalpy_j_kg"):
            expected, actual = getattr(liquid, name), getattr(inflow.liquid_state, name)
            if abs(actual-expected) > self.tolerances.property_relative*max(abs(expected), 1.):
                raise ValueError("Ground liquid is not the native pool's saturated ambient-pressure state")
        self.properties.basis.require_compatible(liquid.basis)
        self.properties.basis.require_compatible(vapor.basis)
        if (liquid.vapor_mass_fraction != 0. or vapor.vapor_mass_fraction != 1.
                or not math.isclose(liquid.pressure_pa, pressure, rel_tol=self.tolerances.property_relative)
                or not math.isclose(vapor.pressure_pa, pressure, rel_tol=self.tolerances.property_relative)
                or not math.isclose(liquid.temperature_k, vapor.temperature_k,
                                    rel_tol=self.tolerances.property_relative)):
            raise ValueError("The pool reference must return consistent saturation endpoints")
        if vapor.enthalpy_j_kg <= liquid.enthalpy_j_kg:
            raise ValueError("The declared pool property reference has no positive vaporization enthalpy")
        relative_times = tuple(time-inflow.start_time_s for time in times)
        clock = None
        if self.tolerances.event_clock_roundoff_s:
            if any(b-a <= 2*self.tolerances.event_clock_roundoff_s
                   for a, b in zip(inflow.schedule_times_s, inflow.schedule_times_s[1:])):
                raise ValueError("Input knots are unresolved within the explicit event-clock budget")
            clock = EventClockInflow(inflow.schedule_times_s, inflow.schedule_rates_kg_s,
                                     inflow.native, self.tolerances.event_clock_roundoff_s)
        native = self.runner(config, clock if clock is not None else inflow.native,
                             output_times_s=relative_times)
        rows = tuple(native.ledger)
        if not math.isfinite(native.mass_balance_residual_kg):
            raise PoolCouplingError(native, ("Native final mass residual is nonfinite",))
        if len(rows) != len(times):
            raise PoolCouplingError(native, ("Native pool did not return every requested output edge",))
        issues, audits = [], []
        last_evaporation = 0.
        for time, elapsed, row in zip(times, relative_times, rows, strict=True):
            declared = inflow.cumulative_mass_kg(time, clock_id=inflow.location.clock_id)
            names = ("time_s", "cumulative_inflow_kg", "liquid_mass_kg", "cumulative_evaporation_kg",
                "escaped_domain_mass_kg", "cumulative_numerical_mass_adjustment_kg",
                "unledgered_mass_residual_kg", "pool_temperature_K", "liquid_density_kg_m3",
                "interval_mean_evaporation_rate_kg_s", "last_substep_evaporation_rate_kg_s")
            if any(not math.isfinite(getattr(row, name)) for name in names):
                raise PoolCouplingError(native, (f"Nonfinite native pool field at {time:g} s",))
            if any(getattr(row, name) < 0. for name in ("cumulative_inflow_kg", "liquid_mass_kg",
                    "cumulative_evaporation_kg", "escaped_domain_mass_kg",
                    "interval_mean_evaporation_rate_kg_s", "last_substep_evaporation_rate_kg_s")):
                issues.append(f"Negative native pool mass/rate at {time:g} s")
            residual = (declared+row.cumulative_numerical_mass_adjustment_kg
                        -row.liquid_mass_kg-row.cumulative_evaporation_kg-row.escaped_domain_mass_kg)
            limit = self.tolerances.absolute_mass_kg+self.tolerances.relative_mass*max(declared, 1e-30)
            if not math.isclose(row.time_s, elapsed, rel_tol=0., abs_tol=1e-10):
                issues.append(f"Native pool output clock differs at {time:g} s")
            if abs(row.cumulative_inflow_kg-declared) > limit:
                issues.append(f"Native pool input differs from independent step integral at {time:g} s")
            if abs(residual) > limit or abs(row.unledgered_mass_residual_kg-residual) > limit:
                issues.append(f"Native pool inventory does not close independently at {time:g} s")
            if abs(row.cumulative_numerical_mass_adjustment_kg) > self.tolerances.maximum_numerical_adjustment_kg:
                issues.append(f"Native numerical mass adjustment exceeds its explicit budget at {time:g} s")
            if row.escaped_domain_mass_kg > self.tolerances.maximum_escaped_mass_kg or row.source_status == "out_of_scope":
                issues.append(f"Liquid escaped the admissible pool domain at {time:g} s")
            if row.source_status not in {"within_declared_scope", "input_limited", "numerically_adjusted", "out_of_scope"}:
                issues.append(f"Unknown native pool status at {time:g} s")
            if row.cumulative_evaporation_kg < last_evaporation:
                issues.append(f"Cumulative evaporation decreased at {time:g} s")
            interval = 0. if not audits else (row.cumulative_evaporation_kg-last_evaporation)/(time-audits[-1].time_s)
            if abs(row.interval_mean_evaporation_rate_kg_s-interval) > limit/max(time-audits[-1].time_s if audits else 1., 1e-30):
                issues.append(f"Native interval-mean evaporation is inconsistent at {time:g} s")
            last_evaporation = row.cumulative_evaporation_kg
            for native_name, expected in (("pool_temperature_K", liquid.temperature_k),
                                          ("liquid_density_kg_m3", liquid.density_kg_m3)):
                if abs(getattr(row, native_name)-expected) > self.tolerances.property_relative*abs(expected):
                    issues.append(f"Native normal-hydrogen property mismatch at {time:g} s")
            audits.append(PoolSampleAudit(time, row, declared, residual, limit))
        if abs(native.mass_balance_residual_kg-audits[-1].independently_recomputed_mass_residual_kg) > audits[-1].mass_limit_kg:
            issues.append("Native final mass residual differs from the independent ledger")
        result = NativePoolRun(native, config, inflow, vapor_location, liquid, vapor,
                               tuple(audits), self.engine_id, tuple(issues), clock)
        if issues and require_closed:
            raise PoolCouplingError(native, issues)
        return result
