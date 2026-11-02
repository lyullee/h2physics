"""Unverified native HELPR constitutive law / SciPy finite crack composition.

HELPR owns Paris and published hydrogen-growth relations and its selected native
fugacity closure. Caller geometry owns mode-I stress intensity. SciPy owns the
numerical integration and event roots. No transport, new EOS or growth law is
implemented here. Execution/validation is deferred to the cluster case handlers.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from importlib import metadata
from pathlib import Path
from types import MappingProxyType

import numpy as np

from ..core import Origin, finite

HELPR_VERSION = "2.1.0"
HELPR_REVISION = "ae12d20b6608123af41dd9d5f70db6b6547fece5"
_REVIEWED = {
    "helpr.physics.crack_growth": "a54266a68668fd26153f890aceafbc0f83569efa5e556de2fb4162ad9d9c100f",
    "helpr.physics.environment": "6663ef55cba3319983bfbc3822b31f3c00057eae1dcb805b6601625d2f6a2895",
    "helpr.utilities.parameter": "b3aff09d5f1a8cb0180c4b2c21f1a2e8dbb9ddc7848edcc677fdfc8fb6be9b27",
}


def _text(*items):
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError("Explicit material, model, geometry, clock and evidence IDs are required")


def _origin(item):
    value = Origin(item)
    if value == Origin.UNRESOLVED:
        raise ValueError("Unresolved origin cannot admit fracture-growth inputs")
    return value


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _plain(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if callable(value):
        return (id(value), id(getattr(value, "__code__", None)))
    return value


def _digest(value):
    return hashlib.sha256(
        json.dumps(_plain(value), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _method_bindings(obj):
    bindings = []
    for name in type(obj).__dict__:
        if name.startswith("__"):
            continue
        value = getattr(obj, name)
        if callable(value):
            function = getattr(value, "__func__", value)
            bindings.append((name, id(function), id(getattr(function, "__code__", None))))
    return bindings


@dataclass(frozen=True, slots=True)
class HydrogenCrackEnvironment:
    maximum_pressure_pa: float
    minimum_pressure_pa: float
    temperature_k: float
    hydrogen_mole_fraction: float
    hydrogen_fugacity_pa: float
    fugacity_basis_id: str
    evidence_id: str
    origin: Origin

    def __post_init__(self):
        _text(self.fugacity_basis_id, self.evidence_id)
        finite(self.maximum_pressure_pa, "maximum gas pressure", positive=True)
        finite(self.temperature_k, "gas temperature", positive=True)
        if (
            not 0
            <= finite(self.minimum_pressure_pa, "minimum gas pressure")
            <= self.maximum_pressure_pa
        ):
            raise ValueError("Pressure extrema must be ordered absolute Pa")
        if not 0 <= finite(self.hydrogen_mole_fraction, "gas-phase H2 mole fraction") <= 1:
            raise ValueError("H2 fraction is a fraction, not percent or mass fraction")
        if finite(self.hydrogen_fugacity_pa, "H2 fugacity") < 0:
            raise ValueError("H2 fugacity must be nonnegative")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class FractureMaterialDomain:
    pressure_pa: tuple[float, float]
    temperature_k: tuple[float, float]
    fugacity_pa: tuple[float, float]
    stress_intensity_ratio: tuple[float, float]
    frequency_hz: tuple[float, float]
    growth_delta_k_pa_sqrt_m: tuple[float, float]
    maximum_trial_delta_k_pa_sqrt_m: float
    material_id: str
    curve_id: str
    environment_qualification_id: str
    small_scale_yielding_evidence_id: str
    numerical_extension_evidence_id: str
    origin: Origin

    def __post_init__(self):
        for name in (
            "pressure_pa",
            "temperature_k",
            "fugacity_pa",
            "stress_intensity_ratio",
            "frequency_hz",
            "growth_delta_k_pa_sqrt_m",
        ):
            bounds = tuple(finite(v, name) for v in getattr(self, name))
            if len(bounds) != 2 or bounds[0] < 0 or bounds[0] >= bounds[1]:
                raise ValueError(
                    "Material domain bounds must be explicit, nonnegative and increasing"
                )
            object.__setattr__(self, name, bounds)
        if self.temperature_k[0] <= 0 or self.frequency_hz[0] <= 0:
            raise ValueError("Material temperature and frequency domains must be positive")
        if self.stress_intensity_ratio[1] >= 1:
            raise ValueError("This tensile-cycle law admits only 0 <= Kmin/Kmax < 1")
        if (
            finite(self.maximum_trial_delta_k_pa_sqrt_m, "trial deltaK maximum", positive=True)
            < self.growth_delta_k_pa_sqrt_m[1]
        ):
            raise ValueError(
                "Numerical trial limit cannot be narrower than the physical growth domain"
            )
        _text(
            self.material_id,
            self.curve_id,
            self.environment_qualification_id,
            self.small_scale_yielding_evidence_id,
            self.numerical_extension_evidence_id,
        )
        object.__setattr__(self, "origin", _origin(self.origin))

    def require_block(self, block):
        env = block.environment
        for label, value, bounds in (
            ("maximum pressure", env.maximum_pressure_pa, self.pressure_pa),
            ("minimum pressure", env.minimum_pressure_pa, self.pressure_pa),
            ("temperature", env.temperature_k, self.temperature_k),
            ("fugacity", env.hydrogen_fugacity_pa, self.fugacity_pa),
            ("cycle frequency", block.frequency_hz, self.frequency_hz),
        ):
            if not bounds[0] <= value <= bounds[1]:
                raise ValueError(
                    f"{label} is outside the explicitly qualified material curve domain"
                )


@dataclass(frozen=True, slots=True)
class LoadCycleBlock:
    block_id: str
    start_cycle: float
    end_cycle: float
    start_time_s: float
    end_time_s: float
    minimum_stress_pa: float
    maximum_stress_pa: float
    environment: HydrogenCrackEnvironment

    def __post_init__(self):
        _text(self.block_id)
        for name in (
            "start_cycle",
            "end_cycle",
            "start_time_s",
            "end_time_s",
            "minimum_stress_pa",
            "maximum_stress_pa",
        ):
            finite(getattr(self, name), name)
        if (
            self.start_cycle < 0
            or self.end_cycle <= self.start_cycle
            or self.end_time_s <= self.start_time_s
            or not 0 <= self.minimum_stress_pa <= self.maximum_stress_pa
        ):
            raise ValueError("Declare an ordered finite tensile constant-amplitude cycle block")
        if type(self.environment) is not HydrogenCrackEnvironment:
            raise TypeError("A resolved actual hydrogen environment record is required")
        finite(self.frequency_hz, "explicit block frequency", positive=True)

    @property
    def frequency_hz(self):
        return (self.end_cycle - self.start_cycle) / (self.end_time_s - self.start_time_s)

    def time_at_cycle(self, cycle):
        return self.start_time_s + (cycle - self.start_cycle) / self.frequency_hz


@dataclass(frozen=True, slots=True)
class LoadCycleHistory:
    blocks: tuple[LoadCycleBlock, ...]
    cycle_clock_id: str
    physical_clock_id: str
    stress_basis_id: str
    ordering_evidence_id: str
    source_id: str
    origin: Origin

    def __post_init__(self):
        blocks = tuple(self.blocks)
        if not blocks or any(type(b) is not LoadCycleBlock for b in blocks):
            raise ValueError("Use a nonempty ordered sequence of actual cycle blocks")
        if len({b.block_id for b in blocks}) != len(blocks):
            raise ValueError("Cycle block IDs must be unique")
        for first, second in zip(blocks[:-1], blocks[1:], strict=True):
            if first.end_cycle != second.start_cycle or first.end_time_s != second.start_time_s:
                raise ValueError("Cycle blocks must meet on both explicitly declared clocks")
        object.__setattr__(self, "blocks", blocks)
        _text(
            self.cycle_clock_id,
            self.physical_clock_id,
            self.stress_basis_id,
            self.ordering_evidence_id,
            self.source_id,
        )
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class ModeIStressIntensity:
    minimum_pa_sqrt_m: float
    maximum_pa_sqrt_m: float

    def __post_init__(self):
        if (
            not 0
            <= finite(self.minimum_pa_sqrt_m, "Kmin")
            <= finite(self.maximum_pa_sqrt_m, "Kmax")
        ):
            raise ValueError("Only finite ordered tensile mode-I Kmin/Kmax are supported")

    @property
    def range_pa_sqrt_m(self):
        return self.maximum_pa_sqrt_m - self.minimum_pa_sqrt_m

    @property
    def ratio(self):
        return self.minimum_pa_sqrt_m / self.maximum_pa_sqrt_m if self.maximum_pa_sqrt_m else None


@dataclass(frozen=True, slots=True)
class CrackGeometryCallback:
    geometry_id: str
    stress_intensity: Callable[[float, LoadCycleBlock], ModeIStressIntensity]
    minimum_crack_m: float
    maximum_physical_crack_m: float
    maximum_trial_crack_m: float
    geometry_evidence_id: str
    trial_extension_evidence_id: str

    def __post_init__(self):
        _text(self.geometry_id, self.geometry_evidence_id, self.trial_extension_evidence_id)
        if not callable(self.stress_intensity):
            raise TypeError(
                "Supply a mode-I SIF callback, not an inferred pressure/stress geometry"
            )
        if not (
            0
            < finite(self.minimum_crack_m, "minimum crack")
            < finite(self.maximum_physical_crack_m, "physical geometry maximum")
            <= finite(self.maximum_trial_crack_m, "numerical geometry extension")
        ):
            raise ValueError(
                "Declare positive physical geometry and bounded native trial extension"
            )

    def evaluate(self, crack_m, block):
        if (
            not self.minimum_crack_m
            <= finite(crack_m, "trial crack size")
            <= self.maximum_trial_crack_m
        ):
            raise ValueError("Crack size is outside the caller's numerical SIF evaluation domain")
        value = self.stress_intensity(float(crack_m), block)
        if type(value) is not ModeIStressIntensity:
            raise TypeError("The geometry must return an actual SI ModeIStressIntensity")
        ModeIStressIntensity(value.minimum_pa_sqrt_m, value.maximum_pa_sqrt_m)
        return value


@dataclass(frozen=True, slots=True)
class CrackStopConditions:
    maximum_crack_m: float
    critical_k_max_pa_sqrt_m: float
    arrest_delta_k_pa_sqrt_m: float
    fracture_evidence_id: str
    arrest_evidence_id: str
    stop_at_arrest: bool

    def __post_init__(self):
        finite(self.maximum_crack_m, "stopping crack size", positive=True)
        finite(self.critical_k_max_pa_sqrt_m, "mode-I peak toughness", positive=True)
        if finite(self.arrest_delta_k_pa_sqrt_m, "arrest threshold") < 0:
            raise ValueError("A supplied arrest threshold must be nonnegative")
        if type(self.stop_at_arrest) is not bool:
            raise TypeError("Declare whether first arrest terminates the supplied cycle history")
        _text(self.fracture_evidence_id, self.arrest_evidence_id)


@dataclass(frozen=True, slots=True)
class HelprLawSelection:
    model_name: str
    model_evidence_id: str
    paris_coefficient_si: float | None = None
    paris_exponent: float | None = None
    reference_pressure_pa: float | None = None
    fugacity_compatibility_relative_budget: float = 1e-10

    def __post_init__(self):
        _text(self.model_evidence_id)
        if self.model_name not in {"paris_law", "code_case_2938", "g_202006"}:
            raise ValueError("Select an explicitly reviewed native HELPR model")
        if self.model_name == "paris_law":
            finite(self.paris_coefficient_si, "supplied SI Paris coefficient", positive=True)
            finite(self.paris_exponent, "supplied Paris exponent", positive=True)
            if self.reference_pressure_pa is not None:
                raise ValueError(
                    "A generic supplied Paris curve does not use native fugacity correction"
                )
        else:
            if self.paris_coefficient_si is not None or self.paris_exponent is not None:
                raise ValueError(
                    "Do not replace native published hydrogen branches by an air Paris fit"
                )
            finite(self.reference_pressure_pa, "explicit native reference pressure", positive=True)
        if (
            not 0
            < finite(self.fugacity_compatibility_relative_budget, "fugacity comparison budget")
            < 1
        ):
            raise ValueError("A strict finite fugacity comparison budget is required")


@dataclass(frozen=True, slots=True)
class NativeHelprObjects:
    growth: object
    environment: object | None
    arguments: Mapping
    definition_sha256: str

    def __post_init__(self):
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


class NativeConstitutiveAdmissionError(ValueError):
    def __init__(self, message, selection, created):
        super().__init__(message)
        self.selection = selection
        self.native_environment = created["environment"]
        self.native_growth = created["growth"]


class HelprFatigueLaw:
    """Actual pinned optional native constitutive objects; no trajectory solver.

    Generic Paris coefficients are supplied in m/cycle/(Pa*sqrt(m))**m. Only the
    unit conversion to native MPa*sqrt(m) is performed. Published H2 model branches
    and the selected native Abel-Noble fugacity remain wholly inside HELPR.
    """

    def __init__(self, selection: HelprLawSelection, *, native_growth_factory=None):
        if type(selection) is not HelprLawSelection:
            raise TypeError("Use an explicit native model selection")
        try:
            modules = {name: importlib.import_module(name) for name in _REVIEWED}
        except ImportError as cause:
            raise ImportError(
                "Separately install reviewed HELPR2.1.0 at the pinned revision; no engine fallback is provided"
            ) from cause
        if metadata.version("helpr") != HELPR_VERSION:
            raise ValueError("This unverified adapter targets the inspected HELPR2.1.0 source only")
        self.source_paths = {
            name: Path(inspect.getfile(module)) for name, module in modules.items()
        }
        self.selection = selection
        self.native_class = modules["helpr.physics.crack_growth"].CrackGrowth
        self.environment_class = modules["helpr.physics.environment"].EnvironmentSpecification
        self.native_growth_factory = native_growth_factory or self.native_class
        self.source_sha256 = MappingProxyType(dict(_REVIEWED))
        self._method = self.native_class.calc_change_in_crack_size
        self.require_sources()

    def require_sources(self):
        if {
            name: _sha(path) for name, path in self.source_paths.items()
        } != _REVIEWED or self.native_class.calc_change_in_crack_size is not self._method:
            raise ValueError("The inspected native HELPR source/method identity changed")

    @staticmethod
    def _definition(growth):
        environment = growth.environment_specification
        values = (
            None
            if environment is None
            else {
                key: float(getattr(environment, key))
                for key in (
                    "max_pressure",
                    "min_pressure",
                    "temperature",
                    "volume_fraction_h2",
                    "reference_pressure",
                    "fugacity",
                    "reference_fugacity",
                    "fugacity_ratio",
                    "partial_pressure",
                )
            }
        )
        return _digest(
            (
                growth.model_arguments,
                values,
                id(environment),
                _method_bindings(growth),
                None if environment is None else _method_bindings(environment),
            )
        )

    def make_native(self, environment: HydrogenCrackEnvironment):
        created = {"environment": None, "growth": None}
        try:
            return self._make_native(environment, created)
        except Exception as cause:
            raise NativeConstitutiveAdmissionError(
                f"Native HELPR constitutive admission failed: {cause}", self.selection, created
            ) from cause

    def _make_native(self, environment, created):
        selection = self.selection
        native_env = None
        arguments = {"model_name": selection.model_name}
        if selection.model_name == "paris_law":
            # Dimensional conversion only; the native library evaluates the law.
            arguments.update(
                c=selection.paris_coefficient_si * 1e6**selection.paris_exponent,
                m=selection.paris_exponent,
            )
            finite(arguments["c"], "native unit-converted Paris coefficient", positive=True)
        else:
            if environment.fugacity_basis_id != "HELPR-native-Abel-Noble":
                raise ValueError(
                    "Published native H2 models require explicit native fugacity basis admission"
                )
            native_env = self.environment_class(
                max_pressure=environment.maximum_pressure_pa / 1e6,
                min_pressure=environment.minimum_pressure_pa / 1e6,
                temperature=environment.temperature_k,
                volume_fraction_h2=environment.hydrogen_mole_fraction,
                reference_pressure=selection.reference_pressure_pa / 1e6,
            )
            created["environment"] = native_env
            if not math.isclose(
                float(native_env.fugacity) * 1e6,
                environment.hydrogen_fugacity_pa,
                rel_tol=selection.fugacity_compatibility_relative_budget,
                abs_tol=0.0,
            ):
                raise ValueError("Supplied H2 fugacity and actual native model reference disagree")
        native = self.native_growth_factory(native_env, dict(arguments))
        created["growth"] = native
        if (
            type(native) is not self.native_class
            or native.environment_specification is not native_env
        ):
            raise TypeError("The factory must return an actual unmodified native HELPR CrackGrowth")
        if any(callable(getattr(type(native), name, None)) for name in native.__dict__):
            raise ValueError(
                "Instance-level replacements of native constitutive methods are unsupported"
            )
        if native.model_arguments != arguments:
            raise ValueError("Native factory changed selected model parameters")
        return NativeHelprObjects(native, native_env, arguments, self._definition(native))

    def require_definition(self, owner):
        if (
            type(owner.growth) is not self.native_class
            or self._definition(owner.growth) != owner.definition_sha256
            or self.native_class.calc_change_in_crack_size is not self._method
        ):
            raise ValueError(
                "Native constitutive parameters, environment or method identity changed"
            )


@dataclass(frozen=True, slots=True)
class FractureIntegrationSettings:
    method: str = "DOP853"
    relative_tolerance: float = 1e-8
    absolute_tolerance_m: float = 1e-11
    maximum_cycle_step: float = 50.0
    maximum_native_calls: int = 100000
    event_size_admission_m: float = 1e-9
    event_k_admission_pa_sqrt_m: float = 1.0

    def __post_init__(self):
        if self.method not in {"RK45", "DOP853"}:
            raise ValueError("Select a reviewed existing SciPy explicit integrator")
        for name in (
            "relative_tolerance",
            "absolute_tolerance_m",
            "maximum_cycle_step",
            "event_size_admission_m",
            "event_k_admission_pa_sqrt_m",
        ):
            finite(getattr(self, name), name, positive=True)
        if (
            self.relative_tolerance >= 1
            or type(self.maximum_native_calls) is not int
            or self.maximum_native_calls < 1
        ):
            raise ValueError("Declare useful numerical accuracy and a finite actual-call budget")


@dataclass(frozen=True, slots=True)
class NativeGrowthCall:
    block_id: str
    cycle: float
    crack_size_m: float
    stress_intensity: ModeIStressIntensity
    native_owner: NativeHelprObjects
    native_delta_k_mpa_sqrt_m: float
    native_r_ratio: float
    native_delta_n: float
    raw_result: object
    rate_m_per_cycle: float | None
    purpose: str
    numerical_extension: bool


@dataclass(frozen=True, slots=True)
class FractureSnapshot:
    block_id: str
    cycle: float
    physical_time_s: float
    crack_size_m: float
    stress_intensity: ModeIStressIntensity
    growth_rate_m_per_cycle: float
    native_call: NativeGrowthCall | None
    reason: str


@dataclass(frozen=True, slots=True)
class FractureBlockSummary:
    """Exact sample-window reduction for one reached load block.

    The result is descriptive only: it does not interpolate event coordinates,
    reconstruct a crack-front shape, or imply a material acceptance criterion.
    """

    block_id: str
    start_cycle: float
    end_cycle: float
    start_time_s: float
    end_time_s: float
    start_crack_m: float
    end_crack_m: float
    sampled_growth_m: float
    sampled_mean_growth_m_per_cycle: float | None
    snapshot_count: int
    last_snapshot_reason: str

    def __post_init__(self):
        _text(self.block_id, self.last_snapshot_reason)
        for name in ("start_cycle", "end_cycle", "start_time_s", "end_time_s",
                     "start_crack_m", "end_crack_m", "sampled_growth_m"):
            finite(getattr(self, name), name)
        if (self.end_cycle < self.start_cycle or self.end_time_s < self.start_time_s
                or self.start_crack_m <= 0 or self.end_crack_m <= 0
                or type(self.snapshot_count) is not int or self.snapshot_count < 1):
            raise ValueError("Fracture block summaries require ordered, nonempty retained samples")
        expected = self.end_crack_m - self.start_crack_m
        if not math.isclose(self.sampled_growth_m, expected, rel_tol=2e-13, abs_tol=1e-18):
            raise ValueError("Sampled crack-size change must reconstruct from retained endpoints")
        span = self.end_cycle - self.start_cycle
        expected_mean = expected / span if span > 0 else None
        if self.sampled_mean_growth_m_per_cycle != expected_mean:
            if (self.sampled_mean_growth_m_per_cycle is None or expected_mean is None
                    or not math.isclose(self.sampled_mean_growth_m_per_cycle, expected_mean,
                                        rel_tol=2e-13, abs_tol=1e-18)):
                raise ValueError("Sampled mean growth must use the exact cycle-coordinate span")


@dataclass(frozen=True, slots=True)
class FractureGrowthResult:
    history: LoadCycleHistory
    geometry: CrackGeometryCallback
    material_domain: FractureMaterialDomain
    conditions: CrackStopConditions
    settings: FractureIntegrationSettings
    selection: HelprLawSelection
    snapshots: tuple[FractureSnapshot, ...]
    native_owners: tuple[NativeHelprObjects, ...]
    native_solutions: tuple
    native_calls: tuple[NativeGrowthCall, ...]
    termination: str
    source_sha256: Mapping
    input_sha256: str
    software_status: str = "implemented_unverified"
    trajectory_owner: str = "SciPy solve_ivp with native HELPR constitutive calls"

    def __post_init__(self):
        object.__setattr__(self, "source_sha256", MappingProxyType(dict(self.source_sha256)))

    def block_summaries(self):
        """Return exact sampled crack-size changes for the reached history blocks."""
        return fracture_block_summaries(self)


def fracture_block_summaries(result: FractureGrowthResult) -> tuple[FractureBlockSummary, ...]:
    """Summarize retained crack-size samples without event interpolation.

    Only reached blocks are returned. A terminal event leaves later declared
    blocks absent; a one-sample block has an undefined mean-per-cycle value.
    All time and cycle coordinates come from the original snapshot records.
    """
    if type(result) is not FractureGrowthResult:
        raise TypeError("Supply the exact FractureGrowthResult to summarize")
    declared = {block.block_id: block for block in result.history.blocks}
    order = {block.block_id: index for index, block in enumerate(result.history.blocks)}
    grouped: dict[str, list[FractureSnapshot]] = {}
    previous_order = -1
    for point in result.snapshots:
        if type(point) is not FractureSnapshot or point.block_id not in declared:
            raise ValueError("Every retained sample must identify a declared load block")
        current_order = order[point.block_id]
        if current_order < previous_order:
            raise ValueError("Retained fracture samples must preserve load-block order")
        previous_order = current_order
        block = declared[point.block_id]
        if not block.start_cycle <= point.cycle <= block.end_cycle:
            raise ValueError("Retained sample cycle lies outside its declared load block")
        if point.physical_time_s != block.time_at_cycle(point.cycle):
            raise ValueError("Retained sample time does not reconstruct from the original block clocks")
        grouped.setdefault(point.block_id, []).append(point)
    summaries = []
    prior_end = None
    prior_index = None
    for block_index, block in enumerate(result.history.blocks):
        samples = grouped.get(block.block_id)
        if not samples:
            continue
        if prior_index is None and block_index != 0:
            raise ValueError("A reached fatigue history must retain its first declared block")
        if prior_index is not None and block_index != prior_index + 1:
            raise ValueError("Reached fatigue blocks must preserve an unbroken ordered prefix")
        cycles = [point.cycle for point in samples]
        if any(right <= left for left, right in zip(cycles, cycles[1:])):
            raise ValueError("Fracture samples must advance strictly within each reached block")
        first, last = samples[0], samples[-1]
        if first.cycle != block.start_cycle:
            raise ValueError("Reached blocks must retain their exact initial boundary sample")
        if prior_end is not None and first.crack_size_m != prior_end:
            raise ValueError("Crack size must be continuous across retained adjacent blocks")
        growth = last.crack_size_m - first.crack_size_m
        span = last.cycle - first.cycle
        summaries.append(FractureBlockSummary(
            block.block_id, first.cycle, last.cycle,
            first.physical_time_s, last.physical_time_s,
            first.crack_size_m, last.crack_size_m, growth,
            growth / span if span > 0 else None,
            len(samples), last.reason,
        ))
        prior_end = last.crack_size_m
        prior_index = block_index
    return tuple(summaries)


class FractureGrowthError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        history,
        geometry,
        native_owners=(),
        native_solutions=(),
        native_calls=(),
        snapshots=(),
        last_evaluation=None,
        failed_solution=None,
        pending_native_call=None,
    ):
        super().__init__(message)
        self.history, self.geometry = history, geometry
        self.native_owners, self.native_solutions = tuple(native_owners), tuple(native_solutions)
        self.native_calls, self.snapshots = tuple(native_calls), tuple(snapshots)
        self.last_evaluation, self.failed_solution = last_evaluation, failed_solution
        self.pending_native_call = pending_native_call


def integrate_fatigue_crack(
    law: HelprFatigueLaw,
    history: LoadCycleHistory,
    geometry: CrackGeometryCallback,
    material: FractureMaterialDomain,
    conditions: CrackStopConditions,
    *,
    initial_crack_m: float,
    settings=FractureIntegrationSettings(),
) -> FractureGrowthResult:
    """Finite supplied cycle sequence; no rainflow, initiation or transport inference.

    Every block is constant amplitude and constant gas environment. Frequency is
    recorded/admitted from its explicit two clocks, not used to invent a rate or
    dwell correction. A later block can restart a threshold-arrested crack unless
    stop_at_arrest was explicitly selected. Strict out-of-domain native trials
    fail; user-declared bounded numerical extensions are retained as such.
    """
    owners, solutions, calls, snapshots = [], [], [], []
    last_evaluation, failed_solution, pending_native_call = None, None, None
    try:
        if type(law) is not HelprFatigueLaw:
            raise TypeError("Use the actual optional native HELPR law adapter")
        for item, expected in (
            (history, LoadCycleHistory),
            (geometry, CrackGeometryCallback),
            (material, FractureMaterialDomain),
            (conditions, CrackStopConditions),
            (settings, FractureIntegrationSettings),
        ):
            if type(item) is not expected:
                raise TypeError(
                    "Explicit typed cycle, material, geometry and stopping contracts are required"
                )
            expected(**{f.name: getattr(item, f.name) for f in fields(item)})
        for block in history.blocks:
            LoadCycleBlock(**{f.name: getattr(block, f.name) for f in fields(block)})
            HydrogenCrackEnvironment(
                **{f.name: getattr(block.environment, f.name) for f in fields(block.environment)}
            )
            material.require_block(block)
        a = finite(initial_crack_m, "initial finite crack", positive=True)
        if (
            not geometry.minimum_crack_m
            <= a
            <= conditions.maximum_crack_m
            <= geometry.maximum_physical_crack_m
        ):
            raise ValueError(
                "Initial and stopping sizes must lie inside the admitted physical geometry"
            )
        fingerprint = _digest((history, geometry, material, conditions, settings, law.selection))
        law.require_sources()
        from scipy.integrate import solve_ivp

        def guard():
            if (
                _digest((history, geometry, material, conditions, settings, law.selection))
                != fingerprint
            ):
                raise ValueError(
                    "Load/material/geometry/clock/selection inputs changed during integration"
                )
            for owner in owners:
                law.require_definition(owner)

        termination = "history_exhausted"
        for block in history.blocks:
            failed_solution = None
            last_evaluation = (
                block.block_id,
                block.start_cycle,
                float(a),
                "native_block_admission",
            )
            guard()
            owner = law.make_native(block.environment)
            if any(owner.growth is old.growth for old in owners):
                raise ValueError(
                    "Native factories must return independent constitutive objects per block"
                )
            owners.append(owner)

            def evaluate_sif(cycle, crack, purpose):
                nonlocal last_evaluation
                last_evaluation = (block.block_id, float(cycle), float(crack), purpose)
                guard()
                sif = geometry.evaluate(crack, block)
                guard()
                return sif

            def rate(cycle, crack, purpose):
                nonlocal pending_native_call
                sif = evaluate_sif(cycle, crack, purpose)
                delta = sif.range_pa_sqrt_m
                if delta <= conditions.arrest_delta_k_pa_sqrt_m:
                    return sif, 0.0, None, "supplied_arrest_or_zero_range"
                if (
                    not material.stress_intensity_ratio[0]
                    <= sif.ratio
                    <= material.stress_intensity_ratio[1]
                ):
                    raise ValueError(
                        "SIF ratio lies outside the material calibration domain; no closure correction is inferred"
                    )
                if (
                    not material.growth_delta_k_pa_sqrt_m[0]
                    <= delta
                    <= material.maximum_trial_delta_k_pa_sqrt_m
                ):
                    raise ValueError(
                        "DeltaK lies outside the physical/numerical constitutive evaluation domain"
                    )
                if len(calls) >= settings.maximum_native_calls:
                    raise ValueError("Declared actual native-call budget reached")
                native_k = delta / 1e6
                raw = owner.growth.calc_change_in_crack_size(
                    delta_n=1.0, delta_k=native_k, r_ratio=sif.ratio, cycle_index=0
                )
                pending_native_call = NativeGrowthCall(
                    block.block_id,
                    float(cycle),
                    float(crack),
                    sif,
                    owner,
                    native_k,
                    sif.ratio,
                    1.0,
                    raw,
                    None,
                    purpose,
                    crack > geometry.maximum_physical_crack_m
                    or delta > material.growth_delta_k_pa_sqrt_m[1],
                )
                guard()
                value = finite(raw, "actual native m/cycle growth result")
                if value < 0:
                    raise ValueError("Negative native crack growth is not repaired or clipped")
                call = NativeGrowthCall(
                    block.block_id,
                    float(cycle),
                    float(crack),
                    sif,
                    owner,
                    native_k,
                    sif.ratio,
                    1.0,
                    raw,
                    value,
                    purpose,
                    crack > geometry.maximum_physical_crack_m
                    or delta > material.growth_delta_k_pa_sqrt_m[1],
                )
                calls.append(call)
                pending_native_call = None
                return sif, value, call, "native_constitutive_result"

            def observe(cycle, crack):
                sif, value, call, reason = rate(cycle, crack, "reported_scipy_output")
                if (
                    crack > conditions.maximum_crack_m + settings.event_size_admission_m
                    or sif.maximum_pa_sqrt_m
                    > conditions.critical_k_max_pa_sqrt_m + settings.event_k_admission_pa_sqrt_m
                    or (value > 0 and sif.range_pa_sqrt_m > material.growth_delta_k_pa_sqrt_m[1])
                ):
                    raise ValueError(
                        "A reported state exceeded its physical size, toughness or calibrated-growth domain"
                    )
                snapshots.append(
                    FractureSnapshot(
                        block.block_id,
                        float(cycle),
                        block.time_at_cycle(cycle),
                        float(crack),
                        sif,
                        value,
                        call,
                        reason,
                    )
                )

            initial_sif = evaluate_sif(block.start_cycle, a, "block_initial_geometry")
            if a >= conditions.maximum_crack_m:
                termination = "crack_size_limit"
                snapshots.append(
                    FractureSnapshot(
                        block.block_id,
                        block.start_cycle,
                        block.start_time_s,
                        a,
                        initial_sif,
                        0.0,
                        None,
                        "initial_size_criterion;no_growth_claim",
                    )
                )
                break
            if initial_sif.maximum_pa_sqrt_m >= conditions.critical_k_max_pa_sqrt_m:
                termination = "peak_mode_I_fracture_criterion"
                snapshots.append(
                    FractureSnapshot(
                        block.block_id,
                        block.start_cycle,
                        block.start_time_s,
                        a,
                        initial_sif,
                        0.0,
                        None,
                        "initial_fracture_criterion;no_growth_claim",
                    )
                )
                break
            observe(block.start_cycle, a)
            if (
                initial_sif.range_pa_sqrt_m <= conditions.arrest_delta_k_pa_sqrt_m
                and conditions.stop_at_arrest
            ):
                termination = "supplied_arrest_criterion"
                break

            def rhs(cycle, values):
                return [rate(cycle, float(values[0]), "native_integrator_trial")[1]]

            def size_event(cycle, values):
                return conditions.maximum_crack_m - values[0]

            def fracture_event(cycle, values):
                return (
                    conditions.critical_k_max_pa_sqrt_m
                    - evaluate_sif(
                        cycle, float(values[0]), "fracture_event_geometry"
                    ).maximum_pa_sqrt_m
                )

            def arrest_event(cycle, values):
                return (
                    evaluate_sif(cycle, float(values[0]), "arrest_event_geometry").range_pa_sqrt_m
                    - conditions.arrest_delta_k_pa_sqrt_m
                )

            event_functions = [size_event, fracture_event]
            if conditions.stop_at_arrest:
                event_functions.append(arrest_event)
            for event in event_functions:
                event.terminal, event.direction = True, -1.0
            solution = solve_ivp(
                rhs,
                (block.start_cycle, block.end_cycle),
                [a],
                method=settings.method,
                rtol=settings.relative_tolerance,
                atol=settings.absolute_tolerance_m,
                max_step=settings.maximum_cycle_step,
                events=event_functions,
                dense_output=True,
            )
            failed_solution = solution
            solutions.append(solution)
            if not solution.success:
                raise ValueError(f"Actual SciPy integration failed: {solution.message}")
            if (
                np.any(~np.isfinite(solution.t))
                or np.any(np.diff(solution.t) <= 0)
                or np.any(~np.isfinite(solution.y))
                or np.any(np.diff(solution.y[0]) < -settings.event_size_admission_m)
            ):
                raise ValueError(
                    "Native numerical output is nonfinite, reversed in cycles or healing"
                )
            for cycle, crack in zip(solution.t[1:], solution.y[0, 1:], strict=True):
                observe(float(cycle), float(crack))
            a = float(solution.y[0, -1])
            guard()
            if solution.status == 1:
                terminated = next(
                    i for i, event_values in enumerate(solution.t_events) if len(event_values)
                )
                termination = (
                    "crack_size_limit",
                    "peak_mode_I_fracture_criterion",
                    "supplied_arrest_criterion",
                )[terminated]
                break
        guard()
        law.require_sources()
        return FractureGrowthResult(
            history,
            geometry,
            material,
            conditions,
            settings,
            law.selection,
            tuple(snapshots),
            tuple(owners),
            tuple(solutions),
            tuple(calls),
            termination,
            law.source_sha256,
            fingerprint,
        )
    except Exception as cause:
        raise FractureGrowthError(
            f"Unverified native fracture composition failed: {cause}",
            history=history,
            geometry=geometry,
            native_owners=owners,
            native_solutions=solutions,
            native_calls=calls,
            snapshots=snapshots,
            last_evaluation=last_evaluation,
            failed_solution=failed_solution,
            pending_native_call=pending_native_call,
        ) from cause
