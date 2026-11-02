"""Optional native SLABx-LH2 vapor-source boundary and applicability gate."""

import math
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Executor
from dataclasses import dataclass, field, replace
from hashlib import sha256
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import ThermoState, finite
from ..sources import IntervalMassSource


@dataclass(frozen=True, slots=True)
class NativeVaporPoolBoundary:
    native_source: Any
    mass_source: IntervalMassSource
    area_m2: float
    footprint_evidence_id: str
    ambient_pressure_pa: float
    native_rate_kg_s: float
    native_area_m2: float
    native_duration_s: float
    native_temperature_k: float
    _identity_bindings: tuple = field(default=(), init=False, repr=False, compare=False)
    _numeric_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _metadata_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.mass_source) is not IntervalMassSource:
            raise TypeError("Retain the finite source used to construct the native pool")
        for name in ("area_m2", "ambient_pressure_pa", "native_rate_kg_s", "native_area_m2",
                     "native_duration_s", "native_temperature_k"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        if not isinstance(self.footprint_evidence_id, str) or not self.footprint_evidence_id.strip():
            raise ValueError("Native pool footprint evidence is required")
        self._verify_native_values()
        object.__setattr__(self, "_identity_bindings", (
            self.native_source, self.mass_source, self.mass_source.location,
            self.mass_source.state, self.mass_source.edges_s, self.mass_source.mass_kg,
        ))
        object.__setattr__(self, "_numeric_binding", self._numeric_payload())
        object.__setattr__(self, "_metadata_binding", self._metadata_payload())

    def _verify_native_values(self):
        observed = (
            finite(self.native_source.rate, "native pool rate", positive=True),
            finite(self.native_source.area, "native pool area", positive=True),
            finite(self.native_source.duration, "native pool duration", positive=True),
            _native_source_temperature(self.native_source),
        )
        expected = (self.native_rate_kg_s, self.native_area_m2,
                    self.native_duration_s, self.native_temperature_k)
        if any(not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14)
               for a, b in zip(observed, expected, strict=True)):
            raise ValueError("Native pool source no longer matches its captured initial boundary")
        return observed

    def _numeric_payload(self):
        return (
            tuple(float(x) for x in self.mass_source.edges_s),
            tuple(float(x) for x in self.mass_source.mass_kg),
            float(self.area_m2), float(self.ambient_pressure_pa),
            float(self.native_rate_kg_s), float(self.native_area_m2),
            float(self.native_duration_s), float(self.native_temperature_k),
            _snapshot_signature(self.native_source),
        )

    def _metadata_payload(self):
        return (repr(self.mass_source.state), repr(self.mass_source.location),
                self.mass_source.evidence_id, self.mass_source.end_reason,
                self.footprint_evidence_id)

    def require_current(self):
        self.mass_source.require_current()
        current = (self.native_source, self.mass_source, self.mass_source.location,
                   self.mass_source.state, self.mass_source.edges_s, self.mass_source.mass_kg)
        if any(value is not original for value, original in zip(
            current, self._identity_bindings, strict=True,
        )):
            raise ValueError("Native pool boundary lost its original source objects")
        self._verify_native_values()
        if (self._numeric_payload() != self._numeric_binding
                or self._metadata_payload() != self._metadata_binding):
            raise ValueError("Native pool or finite source changed after boundary construction")
        return self


def _snapshot_signature(value, active=None, depth=0):
    """Fingerprint adapter receipts and mutable native outputs without copying them."""
    if isinstance(value, np.ndarray):
        contiguous = np.ascontiguousarray(value)
        if contiguous.dtype.hasobject:
            content = tuple(_snapshot_signature(item, active, depth + 1)
                            for item in contiguous.flat)
        else:
            content = sha256(contiguous.tobytes()).hexdigest()
        return ("ndarray", contiguous.shape, contiguous.dtype.str, content)
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return (type(value).__name__, value)
    if depth >= 16:
        return (type(value).__qualname__, id(value), repr(value))
    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        return ("cycle", type(value).__qualname__, identity)
    if isinstance(value, Mapping):
        active.add(identity)
        result = ("mapping", tuple(sorted(
            ((_snapshot_signature(key, active, depth + 1),
              _snapshot_signature(item, active, depth + 1)) for key, item in value.items()),
            key=repr,
        )))
        active.remove(identity)
        return result
    if isinstance(value, (tuple, list)):
        active.add(identity)
        result = (type(value).__name__, tuple(
            _snapshot_signature(item, active, depth + 1) for item in value
        ))
        active.remove(identity)
        return result
    if isinstance(value, (set, frozenset)):
        active.add(identity)
        result = (type(value).__name__, tuple(sorted(
            (_snapshot_signature(item, active, depth + 1) for item in value), key=repr,
        )))
        active.remove(identity)
        return result
    attributes = dict(getattr(value, "__dict__", {}) or {})
    for kind in type(value).__mro__:
        names = getattr(kind, "__slots__", ())
        if isinstance(names, str):
            names = (names,)
        for name in names:
            if name not in {"__dict__", "__weakref__"} and hasattr(value, name):
                attributes.setdefault(name, getattr(value, name))
    if not attributes:
        return (type(value).__qualname__, identity, repr(value))
    active.add(identity)
    result = (type(value).__qualname__, identity, tuple(sorted(
        ((name, _snapshot_signature(item, active, depth + 1))
         for name, item in attributes.items()),
        key=lambda pair: pair[0],
    )))
    active.remove(identity)
    return result


def steady_vapor_pool_boundary(source: IntervalMassSource, *, native_pool_factory: Callable,
                                substance: Any, area_m2: float, footprint_evidence_id: str,
                                ambient_pressure_pa: float) -> NativeVaporPoolBoundary:
    """Declare a uniform pure-vapor flux through a fixed horizontal footprint.

    Current native pool sources have one rate/area/duration. Variable source bins
    are rejected, rather than averaged into an unrequested steady scenario.
    """
    if type(source) is not IntervalMassSource:
        raise TypeError("Supply an actual shared IntervalMassSource")
    source.require_current()
    finite(area_m2, "pool vapor footprint", positive=True)
    finite(ambient_pressure_pa, "ambient pressure", positive=True)
    state = source.state
    if (not np.allclose(source.location.direction_unit, (0, 0, 1), rtol=0, atol=1e-10)
            or not math.isclose(source.location.position_m[2], 0., abs_tol=1e-10)):
        raise ValueError("This native pool source needs a ground-relative upward vapor boundary")
    if (state.basis.fluid != "Hydrogen" or state.basis.spin_composition != "normal"
            or state.vapor_mass_fraction != 1):
        raise ValueError("This native pool boundary requires pure normal-H2 vapor")
    if not footprint_evidence_id.strip() or not math.isclose(state.pressure_pa,
            ambient_pressure_pa, rel_tol=1e-8):
        raise ValueError("Declare the footprint evidence and atmospheric vapor pressure")
    if not math.isclose(substance.mw, .00201588, rel_tol=.001):
        raise ValueError("Native released substance does not identify hydrogen molar mass")
    rates = source.mean_rates_kg_s
    rate = finite(float(rates[0]), "vapor rate", positive=True)
    if not np.allclose(rates, rate, rtol=1e-10, atol=1e-14):
        raise ValueError("Variable vapor intervals require a native transient source extension")
    native = native_pool_factory(substance=substance, rate=rate, area=area_m2,
        duration=float(source.edges_s[-1]-source.edges_s[0]), T_source=state.temperature_k)
    return NativeVaporPoolBoundary(
        native, source, area_m2, footprint_evidence_id, ambient_pressure_pa,
        finite(native.rate, "native pool rate", positive=True),
        finite(native.area, "native pool area", positive=True),
        finite(native.duration, "native pool duration", positive=True),
        _native_source_temperature(native),
    )


def _native_source_temperature(source):
    if not hasattr(source, "T"):
        raise ValueError("Native pool source must expose its resolved source temperature as T")
    return finite(source.T, "native pool source temperature", positive=True)


@dataclass(frozen=True, slots=True)
class SLABLH2SnapshotCondition:
    """Explicit one-bin state and ground-footprint projection for screening."""

    state: ThermoState
    area_m2: float
    footprint_evidence_id: str
    state_projection_evidence_id: str | None = None

    def __post_init__(self):
        if type(self.state) is not ThermoState:
            raise TypeError("Each active vapor bin needs one explicit ThermoState")
        object.__setattr__(self, "area_m2", finite(self.area_m2, "pool vapor footprint", positive=True))
        if not isinstance(self.footprint_evidence_id, str) or not self.footprint_evidence_id.strip():
            raise ValueError("Each bin needs footprint evidence")
        if self.state_projection_evidence_id is not None and (
            not isinstance(self.state_projection_evidence_id, str)
            or not self.state_projection_evidence_id.strip()
        ):
            raise ValueError("State-projection evidence must be nonempty when supplied")


@dataclass(frozen=True, slots=True)
class SLABLH2SourceBinLedger:
    """Lineage-preserving view of one parent source bin and optional steady run.

    This ledger records bin inputs and run status only. It does not represent
    concentration history, plume carryover, or a transient SLAB solution.
    """

    series: "SLABLH2SnapshotSeries"
    interval_index: int

    def __post_init__(self):
        if type(self.series) is not SLABLH2SnapshotSeries:
            raise TypeError("Retain the parent SLAB snapshot series")
        if (isinstance(self.interval_index, bool)
                or not isinstance(self.interval_index, (int, np.integer))):
            raise TypeError("Source-bin ledger index must be an integer, not a boolean")
        index = int(self.interval_index)
        if not 0 <= index < len(self.series.source.mass_kg):
            raise IndexError("Source-bin ledger index lies outside the parent source")
        object.__setattr__(self, "interval_index", index)

    def require_current(self) -> "SLABLH2SourceBinLedger":
        self.series.require_current()
        if not 0 <= self.interval_index < len(self.series.source.mass_kg):
            raise ValueError("Source-bin ledger index no longer matches its parent source")
        return self

    @property
    def clock_id(self) -> str:
        self.require_current()
        return self.series.source.location.clock_id

    @property
    def source_evidence_id(self) -> str:
        self.require_current()
        return self.series.source.evidence_id

    @property
    def window_s(self) -> tuple[float, float]:
        self.require_current()
        edges = self.series.source.edges_s
        return float(edges[self.interval_index]), float(edges[self.interval_index + 1])

    @property
    def mass_kg(self) -> float:
        self.require_current()
        return float(self.series.source.mass_kg[self.interval_index])

    @property
    def mean_rate_kg_s(self) -> float:
        self.require_current()
        start, end = self.window_s
        return self.mass_kg / (end - start)

    @property
    def condition(self) -> SLABLH2SnapshotCondition | None:
        self.require_current()
        return self.series.bin_conditions[self.interval_index]

    @property
    def native_run(self) -> "SLABLH2Run | None":
        self.require_current()
        return self.series.interval_runs[self.interval_index]

    @property
    def accepted(self) -> bool | None:
        run = self.native_run
        return None if run is None else run.accepted

    @property
    def zero_mass(self) -> bool:
        return self.mass_kg == 0.0

    @property
    def plume_memory_included(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class SLABLH2SnapshotSeries:
    """Independent steady SLABx-LH2 runs mapped back to finite source bins.

    This is a quasi-steady diagnostic series, not a time-dependent plume:
    each positive-mass bin starts a separate native calculation and carries no
    concentration or momentum field from the preceding bin.
    """

    source: IntervalMassSource
    interval_runs: tuple["SLABLH2Run | None", ...]
    bin_conditions: tuple[SLABLH2SnapshotCondition | None, ...] = ()
    parallel_execution_evidence_id: str | None = None
    _identity_bindings: tuple = field(default=(), init=False, repr=False, compare=False)
    _numeric_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _metadata_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.source) is not IntervalMassSource:
            raise TypeError("Retain the original finite vapor mass source")
        self.source.require_current()
        runs = tuple(self.interval_runs)
        if len(runs) != len(self.source.mass_kg):
            raise ValueError("Retain one snapshot slot for every original source interval")
        conditions = tuple(self.bin_conditions)
        if (self.parallel_execution_evidence_id is not None
                and (not isinstance(self.parallel_execution_evidence_id, str)
                     or not self.parallel_execution_evidence_id.strip())):
            raise ValueError("Parallel execution evidence must be nonempty when supplied")
        if not conditions:
            conditions = tuple(
                None if run is None else SLABLH2SnapshotCondition(
                    run.boundary.mass_source.state,
                    run.boundary.area_m2,
                    run.boundary.footprint_evidence_id,
                )
                for run in runs
            )
        if len(conditions) != len(runs):
            raise ValueError("Retain one explicit state/footprint condition per source bin")
        for index, (mass, run) in enumerate(zip(self.source.mass_kg, runs, strict=True)):
            condition = conditions[index]
            if mass == 0.0:
                if run is not None or condition is not None:
                    raise ValueError("A zero-mass source interval cannot own a dispersion run")
                continue
            if not isinstance(run, SLABLH2Run) or not isinstance(condition, SLABLH2SnapshotCondition):
                raise ValueError("Each positive-mass source interval needs its own native run")
            run.require_current()
            sliced_source = run.boundary.mass_source
            expected_edges = (
                float(self.source.edges_s[index]),
                float(self.source.edges_s[index + 1]),
            )
            state_suffix = condition.state_projection_evidence_id or "parent-state"
            expected_id = (f"{self.source.evidence_id}:quasi-steady-bin-{index}"
                           f":state:{state_suffix}:footprint:{condition.footprint_evidence_id}")
            if (sliced_source.location is not self.source.location
                    or sliced_source.state is not condition.state
                    or not math.isclose(run.boundary.area_m2, condition.area_m2,
                                        rel_tol=1e-12, abs_tol=1e-14)
                    or run.boundary.footprint_evidence_id != condition.footprint_evidence_id
                    or sliced_source.end_reason != (
                        self.source.end_reason if index == len(runs) - 1 else "window_end"
                    )
                    or sliced_source.evidence_id != expected_id
                    or len(sliced_source.mass_kg) != 1
                    or tuple(float(edge) for edge in sliced_source.edges_s) != expected_edges
                    or not math.isclose(float(sliced_source.mass_kg[0]), float(mass),
                                        rel_tol=1e-12, abs_tol=1e-14)):
                raise ValueError(
                    "Native snapshot source clock, state, footprint or mass differs "
                    "from its retained parent bin"
                )
        object.__setattr__(self, "interval_runs", runs)
        object.__setattr__(self, "bin_conditions", conditions)
        object.__setattr__(self, "_identity_bindings", self._object_bindings())
        object.__setattr__(self, "_numeric_binding", self._numeric_payload())
        object.__setattr__(self, "_metadata_binding", self._metadata_payload())

    def _object_bindings(self):
        bindings = [self.source, self.source.location, self.source.state,
                    self.source.edges_s, self.source.mass_kg]
        for run, condition in zip(self.interval_runs, self.bin_conditions, strict=True):
            bindings.append(condition)
            if condition is not None:
                bindings.append(condition.state)
            if run is None:
                bindings.append(None)
            else:
                bindings.extend((run, run.boundary, run.boundary.mass_source,
                                 run.boundary.native_source, run.native, run.used_source,
                                 run.atmosphere))
        return tuple(bindings)

    def _numeric_payload(self):
        runs = []
        for run in self.interval_runs:
            if run is None:
                runs.append(None)
                continue
            boundary_source = run.boundary.mass_source
            runs.append((
                tuple(float(x) for x in boundary_source.edges_s),
                tuple(float(x) for x in boundary_source.mass_kg),
                float(run.source_mass_residual_kg),
                float(run.source_area_change_m2),
                bool(run.accepted),
                _snapshot_signature(run.boundary_audit),
                _snapshot_signature(run.source_tolerances),
                _snapshot_signature(run.boundary.native_source),
                _snapshot_signature(run.native),
                _snapshot_signature(run.used_source),
            ))
        return (
            tuple(float(x) for x in self.source.edges_s),
            tuple(float(x) for x in self.source.mass_kg),
            tuple(None if condition is None else (
                condition.state.pressure_pa,
                condition.state.temperature_k,
                condition.state.density_kg_m3,
                condition.state.enthalpy_j_kg,
                condition.state.internal_energy_j_kg,
            ) for condition in self.bin_conditions),
            tuple(None if condition is None else condition.area_m2
                  for condition in self.bin_conditions),
            tuple(runs),
        )

    def _metadata_payload(self):
        return (
            repr(self.source.location), repr(self.source.state), self.source.origin,
            self.source.evidence_id, self.source.end_reason,
            tuple(None if condition is None else (
                repr(condition.state),
                condition.footprint_evidence_id,
                condition.state_projection_evidence_id,
            ) for condition in self.bin_conditions),
            tuple(None if run is None else (
                run.boundary.footprint_evidence_id,
                float(run.boundary.area_m2),
                float(run.boundary.ambient_pressure_pa),
                float(run.boundary.native_rate_kg_s),
                float(run.boundary.native_area_m2),
                float(run.boundary.native_duration_s),
                float(run.boundary.native_temperature_k),
                _snapshot_signature(run.premise),
                _snapshot_signature(run.atmosphere),
            ) for run in self.interval_runs),
            self.parallel_execution_evidence_id,
        )

    def require_current(self):
        self.source.require_current()
        if any(current is not bound for current, bound in zip(
            self._object_bindings(), self._identity_bindings, strict=True,
        )):
            raise ValueError("Snapshot series lost its original source or native run objects")
        for run in self.interval_runs:
            if run is not None:
                run.require_current()
        if (self._numeric_payload() != self._numeric_binding
                or self._metadata_payload() != self._metadata_binding):
            raise ValueError("Snapshot source arrays or native run outputs changed after capture")
        return self

    @property
    def edges_s(self) -> tuple[float, ...]:
        self.require_current()
        return tuple(float(value) for value in self.source.edges_s)

    @property
    def interval_windows_s(self) -> tuple[tuple[float, float], ...]:
        edges = self.edges_s
        return tuple(zip(edges[:-1], edges[1:], strict=True))

    @property
    def termination_time_s(self) -> float:
        return self.edges_s[-1]

    @property
    def termination_reason(self) -> str:
        self.require_current()
        return self.source.end_reason

    @property
    def plume_memory_included(self) -> bool:
        return False

    @property
    def total_source_mass_kg(self) -> float:
        self.require_current()
        return self.source.total_mass_kg

    @property
    def accepted_by_interval(self) -> tuple[bool | None, ...]:
        self.require_current()
        return tuple(None if run is None else run.accepted for run in self.interval_runs)

    @property
    def all_snapshots_accepted(self) -> bool | None:
        self.require_current()
        outcomes = tuple(run.accepted for run in self.interval_runs if run is not None)
        return None if not outcomes else all(outcomes)

    @property
    def source_bin_ledger(self) -> tuple[SLABLH2SourceBinLedger, ...]:
        """Return exact-clock source bins with their independent snapshot slots."""
        self.require_current()
        return tuple(
            SLABLH2SourceBinLedger(self, index)
            for index in range(len(self.interval_runs))
        )


def run_slabx_lh2_quasi_steady_slices(
    *,
    source: IntervalMassSource,
    native_pool_factory: Callable,
    substance: Any,
    area_m2: float | Sequence[float],
    footprint_evidence_id: str | Sequence[str],
    state_by_interval: Sequence[ThermoState | None] | None = None,
    state_projection_evidence_ids: Sequence[str | None] | None = None,
    ambient_pressure_pa: float,
    atmosphere: Any,
    emission_thermo: Any,
    water_thermo: Any,
    runner: Callable,
    premise_check: Callable,
    width_context: Callable,
    width_coupling: bool,
    x_max_m: float,
    solver_options: Mapping[str, Any] | None = None,
    source_tolerances: "SLABLH2SourceTolerances | None" = None,
    require_accepted: bool = True,
    executor: Executor | None = None,
    parallel_execution_evidence_id: str | None = None,
) -> SLABLH2SnapshotSeries:
    """Run one independent quasi-steady SLAB case per positive source bin.

    Parent-bin mass is conserved exactly into each one-bin boundary. The native
    SLAB calculation itself remains steady and plume carryover between bins is
    deliberately absent; use only for explicitly requested snapshot screening.
    An optional caller-owned executor can run independent bins concurrently.
    Because native width coupling can use process-global state, the caller must
    supply worker-isolation evidence and an executor/provider combination that
    actually isolates that state. No executor is created implicitly.
    """
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    if executor is None:
        if parallel_execution_evidence_id is not None:
            raise ValueError("Parallel execution evidence requires a caller-owned executor")
    elif (not callable(getattr(executor, "submit", None))
          or not isinstance(parallel_execution_evidence_id, str)
          or not parallel_execution_evidence_id.strip()):
        raise ValueError("Parallel execution needs an Executor and worker-isolation evidence")
    if type(source) is not IntervalMassSource:
        raise TypeError("Supply an IntervalMassSource of resolved pure vapor")
    source.require_current()
    interval_count = len(source.mass_kg)
    areas = _interval_values(area_m2, interval_count, "pool vapor footprint", positive=True)
    footprint_ids = _interval_evidence_ids(footprint_evidence_id, interval_count,
                                            "footprint evidence")
    if state_by_interval is None:
        if state_projection_evidence_ids is not None:
            raise ValueError("State-projection IDs require explicit per-interval states")
        states = (source.state,) * interval_count
        state_ids = (None,) * interval_count
    else:
        states = tuple(state_by_interval)
        if len(states) != interval_count:
            raise ValueError("Supply one explicit state slot per source interval")
        if state_projection_evidence_ids is None:
            raise ValueError("Custom per-interval states need state-projection evidence IDs")
        if isinstance(state_projection_evidence_ids, (str, bytes, Mapping)):
            raise TypeError("State-projection evidence IDs must be an interval-aligned sequence")
        state_ids = tuple(state_projection_evidence_ids)
        if len(state_ids) != interval_count:
            raise ValueError("Supply one state-projection evidence slot per source interval")
        for index, (mass, state, evidence_id) in enumerate(
            zip(source.mass_kg, states, state_ids, strict=True),
        ):
            if mass > 0.0:
                if type(state) is not ThermoState:
                    raise TypeError(f"Active source bin {index} needs a ThermoState")
                source.state.basis.require_compatible(state.basis)
                if not isinstance(evidence_id, str) or not evidence_id.strip():
                    raise ValueError(f"Active source bin {index} needs state-projection evidence")
            elif state is not None and type(state) is not ThermoState:
                raise TypeError(f"State slot {index} must be ThermoState or None")
            elif state is not None or evidence_id is not None:
                raise ValueError(f"Zero-mass source bin {index} must not carry a state projection")

    runs = [None] * interval_count
    conditions = [None] * interval_count
    pending = []
    for index, (left, right, mass) in enumerate(zip(
        source.edges_s[:-1], source.edges_s[1:], source.mass_kg, strict=True,
    )):
        if mass == 0.0:
            continue
        state = states[index]
        if type(state) is not ThermoState:
            raise TypeError(f"Active source bin {index} needs a ThermoState")
        condition = SLABLH2SnapshotCondition(
            state, areas[index], footprint_ids[index], state_ids[index],
        )
        conditions[index] = condition
        reason = source.end_reason if right == source.edges_s[-1] else "window_end"
        window = source.window(
            float(left), float(right), clock_id=source.location.clock_id, end_reason=reason,
        )
        state_suffix = condition.state_projection_evidence_id or "parent-state"
        evidence_id = (f"{source.evidence_id}:quasi-steady-bin-{index}"
                       f":state:{state_suffix}:footprint:{condition.footprint_evidence_id}")
        window = replace(
            window, state=condition.state, evidence_id=evidence_id,
        )
        try:
            boundary = steady_vapor_pool_boundary(
                window,
                native_pool_factory=native_pool_factory,
                substance=substance,
                area_m2=condition.area_m2,
                footprint_evidence_id=condition.footprint_evidence_id,
                ambient_pressure_pa=ambient_pressure_pa,
            )
        except Exception as error:
            raise SLABLH2SnapshotSeriesError(
                source, index, tuple(runs[:index]), error,
                getattr(error, "result", None), condition,
            ) from error
        if executor is None:
            try:
                run = run_slabx_lh2(
                    boundary=boundary,
                    atmosphere=atmosphere,
                    emission_thermo=emission_thermo,
                    water_thermo=water_thermo,
                    runner=runner,
                    premise_check=premise_check,
                    width_context=width_context,
                    width_coupling=width_coupling,
                    x_max_m=x_max_m,
                    solver_options=solver_options,
                    source_tolerances=source_tolerances,
                    require_accepted=require_accepted,
                )
            except Exception as error:
                raise SLABLH2SnapshotSeriesError(
                    source, index, tuple(runs[:index]), error,
                    getattr(error, "result", None), condition,
                ) from error
            runs[index] = run
        else:
            pending.append((index, condition, boundary))
    if executor is not None:
        submitted = []
        failures = []
        for index, condition, boundary in pending:
            try:
                future = executor.submit(
                    _run_slabx_lh2_task,
                    boundary=boundary,
                    atmosphere=atmosphere,
                    emission_thermo=emission_thermo,
                    water_thermo=water_thermo,
                    runner=runner,
                    premise_check=premise_check,
                    width_context=width_context,
                    width_coupling=width_coupling,
                    x_max_m=x_max_m,
                    solver_options=solver_options,
                    source_tolerances=source_tolerances,
                    require_accepted=require_accepted,
                )
            except Exception as error:
                failures.append((index, condition, error))
            else:
                submitted.append((index, condition, future))
        for index, condition, future in submitted:
            try:
                runs[index] = future.result()
            except Exception as error:
                failures.append((index, condition, error))
        if failures:
            failed_index, condition, error = min(failures, key=lambda item: item[0])
            error_receipt = SLABLH2SnapshotSeriesError(
                source, failed_index, tuple(runs[:failed_index]), error,
                getattr(error, "result", None), condition,
                completed_by_interval=tuple(runs),
                failures_by_interval=tuple(
                    (index, failure) for index, _, failure in failures
                ),
            )
            raise error_receipt from error
    return SLABLH2SnapshotSeries(
        source, tuple(runs), tuple(conditions), parallel_execution_evidence_id,
    )


def _run_slabx_lh2_task(**kwargs):
    """Top-level task keeps the caller-owned executor free to use processes."""
    return run_slabx_lh2(**kwargs)


def _interval_values(value, count, name, *, positive=False):
    if np.isscalar(value):
        item = finite(value, name, positive=positive)
        return (item,) * count
    if isinstance(value, (str, bytes, Mapping)):
        raise TypeError(f"{name} must be a scalar or interval-aligned sequence")
    values = tuple(finite(item, name, positive=positive) for item in value)
    if len(values) != count:
        raise ValueError(f"{name} sequence must match the source interval count")
    return values


def _interval_evidence_ids(value, count, name):
    if isinstance(value, str):
        values = (value,) * count
    else:
        if isinstance(value, (bytes, Mapping)):
            raise TypeError(f"{name} must be a string or interval-aligned string sequence")
        values = tuple(value)
        if len(values) != count:
            raise ValueError(f"{name} sequence must match the source interval count")
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"Every {name} must be a nonempty string")
    return values


@dataclass(frozen=True, slots=True)
class SLABLH2SourceTolerances:
    """Dimensioned acceptance tolerances for native source-boundary drift."""

    rate_absolute_kg_s: float = 1e-10
    duration_absolute_s: float = 1e-10
    area_absolute_m2: float = 1e-12
    mass_absolute_kg: float = 1e-10
    temperature_absolute_k: float = 1e-8
    relative: float = 1e-8

    def __post_init__(self):
        for name in (
            "rate_absolute_kg_s", "duration_absolute_s", "area_absolute_m2",
            "mass_absolute_kg", "temperature_absolute_k", "relative",
        ):
            value = finite(getattr(self, name), name)
            if value < 0.0:
                raise ValueError("Source tolerances must be nonnegative")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class SLABLH2Run:
    native: Any
    used_source: Any
    boundary: NativeVaporPoolBoundary
    atmosphere: Any
    premise: Mapping[str, Any]
    source_mass_residual_kg: float
    source_area_change_m2: float
    boundary_audit: "SLABLH2SourceAudit"
    source_tolerances: SLABLH2SourceTolerances
    accepted: bool
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _identity_bindings: tuple = field(default=(), init=False, repr=False, compare=False)
    _numeric_binding: tuple = field(default=(), init=False, repr=False, compare=False)
    _metadata_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SLAB_RUN_ISSUERS:
            raise ValueError("SLAB-LH2 runs are issued only by the native run adapter")
        _PENDING_SLAB_RUN_ISSUERS.remove(self._issuer_token)
        if type(self.boundary) is not NativeVaporPoolBoundary:
            raise TypeError("Retain the exact native vapor-pool boundary")
        # Native runner and premise callbacks execute between the caller's
        # initial boundary check and this receipt construction. Recheck here
        # so callback-side mutation cannot become the new accepted baseline.
        self.boundary.require_current()
        if type(self.boundary_audit) is not SLABLH2SourceAudit:
            raise TypeError("Retain the native/requested source boundary audit")
        if type(self.source_tolerances) is not SLABLH2SourceTolerances:
            raise TypeError("Retain the dimensioned source-boundary tolerances")
        if type(self.accepted) is not bool:
            raise TypeError("SLAB run acceptance must be an explicit bool")
        if not isinstance(self.premise, Mapping):
            raise TypeError("Retain native applicability diagnostics as a mapping")
        object.__setattr__(self, "premise", MappingProxyType(dict(self.premise)))
        expected_audit = _build_source_audit(self.boundary, self.used_source)
        if self.boundary_audit != expected_audit:
            raise ValueError("Native/requested boundary audit differs from retained source objects")
        if not math.isclose(self.source_mass_residual_kg,
                            self.boundary_audit.used_mass_residual_kg,
                            rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError("Run mass residual differs from the native source audit")
        if not math.isclose(self.source_area_change_m2,
                            self.boundary_audit.used_area_change_m2,
                            rel_tol=1e-12, abs_tol=1e-14):
            raise ValueError("Run area change differs from the native source audit")
        expected_acceptance = _slab_source_acceptance(
            self.premise, self.native, self.boundary_audit, self.source_tolerances,
        )
        if self.accepted is not expected_acceptance:
            raise ValueError("Run acceptance flag differs from its retained premise and source audit")
        object.__setattr__(self, "_identity_bindings", self._object_bindings())
        object.__setattr__(self, "_numeric_binding", self._numeric_payload())
        object.__setattr__(self, "_metadata_binding", self._metadata_payload())

    def _object_bindings(self):
        return (
            self.native, self.used_source, self.boundary, self.boundary.native_source,
            self.boundary.mass_source, self.boundary.mass_source.location,
            self.boundary.mass_source.state, self.boundary.mass_source.edges_s,
            self.boundary.mass_source.mass_kg, self.atmosphere, self.premise,
            self.boundary_audit, self.source_tolerances,
        )

    def _numeric_payload(self):
        return (
            float(self.source_mass_residual_kg), float(self.source_area_change_m2),
            self.accepted, _snapshot_signature(self.boundary_audit),
            _snapshot_signature(self.source_tolerances), _snapshot_signature(self.native),
            _snapshot_signature(self.used_source), _snapshot_signature(self.premise),
        )

    def _metadata_payload(self):
        return (
            repr(self.boundary.mass_source.location), repr(self.boundary.mass_source.state),
            self.boundary.mass_source.evidence_id, self.boundary.mass_source.end_reason,
            self.boundary.footprint_evidence_id, self.boundary.area_m2,
            self.boundary.ambient_pressure_pa, _snapshot_signature(self.atmosphere),
        )

    def require_current(self):
        self.boundary.mass_source.require_current()
        if any(current is not bound for current, bound in zip(
            self._object_bindings(), self._identity_bindings, strict=True,
        )):
            raise ValueError("SLAB result lost its original native or source objects")
        self.boundary.require_current()
        if self.boundary_audit != _build_source_audit(self.boundary, self.used_source):
            raise ValueError("SLAB result audit no longer matches requested and used source values")
        if self.accepted is not _slab_source_acceptance(
            self.premise, self.native, self.boundary_audit, self.source_tolerances,
        ):
            raise ValueError("SLAB result acceptance no longer matches its native diagnostics")
        if (self._numeric_payload() != self._numeric_binding
                or self._metadata_payload() != self._metadata_binding):
            raise ValueError("SLAB native result or source audit changed after capture")
        return self


_PENDING_SLAB_RUN_ISSUERS: set[object] = set()


def _issue_slab_lh2_run(*args, **kwargs) -> SLABLH2Run:
    token = object()
    _PENDING_SLAB_RUN_ISSUERS.add(token)
    try:
        return SLABLH2Run(*args, _issuer_token=token, **kwargs)
    except Exception:
        _PENDING_SLAB_RUN_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class SLABLH2SourceAudit:
    """Requested, constructed and finally used source settings for one run."""

    requested_rate_kg_s: float
    initial_native_rate_kg_s: float
    used_rate_kg_s: float
    requested_duration_s: float
    initial_native_duration_s: float
    used_duration_s: float
    requested_area_m2: float
    initial_native_area_m2: float
    used_area_m2: float
    requested_temperature_k: float
    initial_native_temperature_k: float
    used_temperature_k: float
    requested_mass_kg: float

    def __post_init__(self):
        for name in (
            "requested_rate_kg_s", "initial_native_rate_kg_s", "used_rate_kg_s",
            "requested_duration_s", "initial_native_duration_s", "used_duration_s",
            "requested_area_m2", "initial_native_area_m2", "used_area_m2",
            "requested_temperature_k", "initial_native_temperature_k", "used_temperature_k",
        ):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        object.__setattr__(self, "requested_mass_kg",
                           finite(self.requested_mass_kg, "requested_mass_kg", positive=True))

    @property
    def initial_mass_kg(self) -> float:
        return self.initial_native_rate_kg_s * self.initial_native_duration_s

    @property
    def used_mass_kg(self) -> float:
        return self.used_rate_kg_s * self.used_duration_s

    @property
    def initial_mass_residual_kg(self) -> float:
        return self.initial_mass_kg - self.requested_mass_kg

    @property
    def used_mass_residual_kg(self) -> float:
        return self.used_mass_kg - self.requested_mass_kg

    @property
    def initial_rate_change_kg_s(self) -> float:
        return self.initial_native_rate_kg_s - self.requested_rate_kg_s

    @property
    def used_rate_change_kg_s(self) -> float:
        return self.used_rate_kg_s - self.requested_rate_kg_s

    @property
    def initial_duration_change_s(self) -> float:
        return self.initial_native_duration_s - self.requested_duration_s

    @property
    def used_duration_change_s(self) -> float:
        return self.used_duration_s - self.requested_duration_s

    @property
    def initial_area_change_m2(self) -> float:
        return self.initial_native_area_m2 - self.requested_area_m2

    @property
    def used_area_change_m2(self) -> float:
        return self.used_area_m2 - self.requested_area_m2

    @property
    def initial_temperature_change_k(self) -> float:
        return self.initial_native_temperature_k - self.requested_temperature_k

    @property
    def used_temperature_change_k(self) -> float:
        return self.used_temperature_k - self.requested_temperature_k


def _build_source_audit(boundary: NativeVaporPoolBoundary, used) -> SLABLH2SourceAudit:
    source = boundary.mass_source
    return SLABLH2SourceAudit(
        finite(float(source.mean_rates_kg_s[0]), "requested vapor rate", positive=True),
        boundary.native_rate_kg_s,
        finite(used.rate, "native used vapor rate", positive=True),
        finite(float(source.edges_s[-1] - source.edges_s[0]),
               "requested source duration", positive=True),
        boundary.native_duration_s,
        finite(used.duration, "native used source duration", positive=True),
        boundary.area_m2,
        boundary.native_area_m2,
        finite(used.area, "native used source area", positive=True),
        source.state.temperature_k,
        boundary.native_temperature_k,
        _native_source_temperature(used),
        source.total_mass_kg,
    )


def _slab_source_acceptance(premise, trajectory, audit, tolerances) -> bool:
    ratio = float(premise.get("max", math.nan))
    requested_rate = audit.requested_rate_kg_s
    requested_duration = audit.requested_duration_s
    requested_area = audit.requested_area_m2
    requested_temperature = audit.requested_temperature_k
    return bool(
        math.isfinite(ratio)
        and ratio <= 1.0
        and not premise.get("violated", True)
        and abs(audit.initial_rate_change_kg_s)
            <= tolerances.rate_absolute_kg_s + tolerances.relative * requested_rate
        and abs(audit.used_rate_change_kg_s)
            <= tolerances.rate_absolute_kg_s + tolerances.relative * requested_rate
        and abs(audit.initial_duration_change_s)
            <= tolerances.duration_absolute_s + tolerances.relative * requested_duration
        and abs(audit.used_duration_change_s)
            <= tolerances.duration_absolute_s + tolerances.relative * requested_duration
        and abs(audit.initial_area_change_m2)
            <= tolerances.area_absolute_m2 + tolerances.relative * requested_area
        and abs(audit.used_area_change_m2)
            <= tolerances.area_absolute_m2 + tolerances.relative * requested_area
        and abs(audit.initial_mass_residual_kg)
            <= tolerances.mass_absolute_kg + tolerances.relative * audit.requested_mass_kg
        and abs(audit.used_mass_residual_kg)
            <= tolerances.mass_absolute_kg + tolerances.relative * audit.requested_mass_kg
        and abs(audit.initial_temperature_change_k)
            <= tolerances.temperature_absolute_k + tolerances.relative * requested_temperature
        and abs(audit.used_temperature_change_k)
            <= tolerances.temperature_absolute_k + tolerances.relative * requested_temperature
        and len(trajectory.x) >= 2
        and np.all(np.isfinite(trajectory.x))
    )


class SLABLH2Error(ValueError):
    def __init__(self, result: SLABLH2Run):
        self.result, self.native = result, result.native
        super().__init__("Native SLABx-LH2 source or downwind applicability gate failed")


class SLABLH2SnapshotSeriesError(RuntimeError):
    """Keep completed snapshots, the failed bin and any original native result."""

    def __init__(self, source: IntervalMassSource, failed_index: int,
                 completed_runs: tuple[SLABLH2Run | None, ...], cause: Exception,
                 result: SLABLH2Run | None,
                 condition: SLABLH2SnapshotCondition | None, *,
                 completed_by_interval: tuple[SLABLH2Run | None, ...] | None = None,
                 failures_by_interval: tuple[tuple[int, Exception], ...] = ()):
        self.source = source
        self.failed_index = failed_index
        self.completed_runs = completed_runs
        self.cause = cause
        self.failed_condition = condition
        self.result = result if isinstance(result, SLABLH2Run) else None
        self.native = None if self.result is None else self.result.native
        self.completed_by_interval = completed_by_interval
        self.failures_by_interval = failures_by_interval
        super().__init__(f"SLABx-LH2 quasi-steady snapshot failed at source bin {failed_index}")


def run_slabx_lh2(*, boundary: NativeVaporPoolBoundary, atmosphere: Any,
                   emission_thermo: Any, water_thermo: Any, runner: Callable,
                   premise_check: Callable, width_context: Callable, width_coupling: bool,
                   x_max_m: float, solver_options: Mapping[str, Any] | None = None,
                   source_tolerances: SLABLH2SourceTolerances | None = None,
                   require_accepted: bool = True) -> SLABLH2Run:
    """Retain actual native objects and gate the completed trajectory.

    Water/ice corrections belong to the caller's reviewed native water backend.
    The native width context is process-global; concurrent work needs native-
    supported worker isolation. No automatic alternate dispersion engine is used.
    """
    if type(require_accepted) is not bool:
        raise TypeError("require_accepted must be an explicit bool")
    finite(x_max_m, "maximum downwind distance", positive=True)
    boundary.require_current()
    if not isinstance(width_coupling, bool):
        raise ValueError("Select the native width-coupling mode explicitly")
    tolerances = source_tolerances or SLABLH2SourceTolerances()
    if type(tolerances) is not SLABLH2SourceTolerances:
        raise TypeError("Use explicit SLABLH2SourceTolerances for source-boundary acceptance")
    if not math.isclose(atmosphere.p, boundary.ambient_pressure_pa, rel_tol=1e-8):
        raise ValueError("Native atmosphere and declared source pressure differ")
    if not math.isclose(emission_thermo.substance.mw,
                        boundary.native_source.substance.mw, rel_tol=1e-10):
        raise ValueError("Source and thermodynamic substance identities differ")
    options = dict(solver_options or {})
    if {"src", "atm", "emission", "water", "x_max"} & options.keys():
        raise ValueError("Native physical inputs cannot be overridden in solver options")
    with width_context(width_coupling):
        trajectory, used = runner(boundary.native_source, atmosphere, emission_thermo,
                                  water_thermo, x_max=x_max_m, **options)
    premise = dict(premise_check(trajectory))
    audit = _build_source_audit(boundary, used)
    mass_residual = audit.used_mass_residual_kg
    area_change = audit.used_area_change_m2
    accepted = _slab_source_acceptance(premise, trajectory, audit, tolerances)
    result = _issue_slab_lh2_run(
        trajectory, used, boundary, atmosphere, premise, mass_residual,
        area_change, audit, tolerances, accepted,
    )
    if require_accepted and not accepted:
        raise SLABLH2Error(result)
    return result
