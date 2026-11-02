"""Conditional supplied-field exposure through actual optional HyRAM6.1 laws.

Native functions own dose, probits and response probability. Histories require
explicit interpolation/reduction assumptions; no source/fire chain is verified.
"""

import hashlib
import importlib
import importlib.metadata
import inspect
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, finite


def _ids(*values):
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Declare receptor, coordinate frame, clock, source and assumption evidence")


def _array(values):
    raw = np.asarray(values)
    if raw.dtype.kind in {"b", "c"} or any(isinstance(v, (bool, np.bool_))
            for v in np.asarray(values, dtype=object).flat):
        raise ValueError("Exposure arrays cannot contain booleans or complex values")
    out = np.array(values, dtype=float, copy=True)
    out = immutable_array(out, name="out")
    return out


def _origin(value):
    value = Origin(value)
    if value == Origin.UNRESOLVED:
        raise ValueError("Resolve the exposure data/model role")
    return value


@dataclass(frozen=True, slots=True)
class ExposureReceptor:
    receptor_id: str
    frame_id: str
    position_m: tuple[float, float, float]
    input_basis_id: str

    def __post_init__(self):
        _ids(self.receptor_id, self.frame_id, self.input_basis_id)
        position = tuple(self.position_m)
        if len(position) != 3:
            raise ValueError("Receptor position needs three coordinates in m")
        for value in position:
            finite(value, "receptor coordinate")
        object.__setattr__(self, "position_m", position)


@dataclass(frozen=True, slots=True)
class ExposureHistory:
    receptor: ExposureReceptor
    time_s: np.ndarray
    values: np.ndarray
    quantity: str
    unit: str
    interpolation: str
    clock_id: str
    source_id: str
    basis_id: str
    origin: Origin
    valid: np.ndarray | None = None
    input_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.receptor, ExposureReceptor):
            raise ValueError("Supply an explicit receptor/frame")
        _ids(self.clock_id, self.source_id, self.basis_id)
        units = {"incident_radiant_flux": "W/m2", "absorbed_radiant_flux": "W/m2", "gauge_overpressure": "Pa"}
        if self.quantity not in units or self.unit != units[self.quantity]:
            raise ValueError("Use explicit incident/absorbed W/m2 or gauge overpressure Pa")
        times, values = _array(self.time_s), _array(self.values)
        if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
                or np.any(np.diff(times) <= 0)):
            raise ValueError("History clock edges must be finite and strictly increasing")
        expected = len(times)-1 if self.interpolation == "left_hold" else len(times)
        if self.interpolation not in {"left_hold", "linear"} or values.shape != (expected,):
            raise ValueError("Left-held histories have one value per interval; linear histories one per edge")
        valid = np.ones(values.shape, dtype=bool) if self.valid is None else np.asarray(self.valid)
        if valid.dtype.kind != "b" or valid.shape != values.shape:
            raise ValueError("Explicit validity mask must be boolean on the same value axes")
        valid = valid.copy()
        valid = immutable_array(valid, name="valid")
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid", valid)
        object.__setattr__(self, "origin", _origin(self.origin))
        evidence = tuple(self.input_evidence_ids)
        _ids(*evidence) if evidence else None
        object.__setattr__(self, "input_evidence_ids", evidence)

    @property
    def support_s(self):
        return float(self.time_s[0]), float(self.time_s[-1])

    @property
    def content_sha256(self):
        h = hashlib.sha256(repr((self.receptor, self.quantity, self.unit, self.interpolation,
                                self.clock_id, self.source_id, self.basis_id, self.origin,
                                self.input_evidence_ids)).encode())
        for value in (self.time_s, self.values, self.valid):
            h.update(value.tobytes())
        return h.hexdigest()


def incident_history_from_hyram_radiation(radiation, *, observer_index: int,
        start_s: float, end_s: float, receptor_id: str, basis_id: str):
    """Bind one accepted native HyRAM irradiance to an evidenced steady interval.

    This maps an already computed positive scalar field; it does not create a
    transient fire or a receptor-plane projection. The caller declares the
    absolute interval within the flame's steady premise and an input basis.
    """
    from .hyram_flame import HyRAMRadiationRun, _native_flame_signature

    if type(radiation) is not HyRAMRadiationRun or not radiation.accepted:
        raise ValueError("Require an accepted native HyRAM radiation result")
    flame = radiation.flame
    if (not flame.accepted or _native_flame_signature(flame.native) != flame.native_signature
            or radiation.status != "accepted-steady-flame"):
        raise ValueError("Native flame/source acceptance or live field identity changed")
    if (not radiation.gates or not all(radiation.gates.values())
            or radiation.irradiance_w_m2.shape != (len(radiation.points_m),)
            or not np.all(np.isfinite(radiation.irradiance_w_m2))
            or np.any(radiation.irradiance_w_m2 < 0)
            or np.asarray(radiation.native_flux).reshape(-1).shape != radiation.irradiance_w_m2.shape
            or not np.array_equal(np.asarray(radiation.native_flux, dtype=float).reshape(-1),
                                  radiation.irradiance_w_m2)):
        raise ValueError("Native radiation result lacks accepted finite nonnegative observer values")
    if isinstance(observer_index, bool) or not isinstance(observer_index, int):
        raise ValueError("Select one observer by integer index")
    if not 0 <= observer_index < len(radiation.points_m):
        raise ValueError("Observer index is outside the native radiation result")
    window = flame.window
    start, end = finite(start_s, "exposure start"), finite(end_s, "exposure end")
    if start >= end or start < window.start_s or end > window.end_s:
        raise ValueError("Exposure interval must lie wholly inside the caller-evidenced steady flame window")
    if flame.location.clock_id != window.clock_id:
        raise ValueError("Source and steady exposure window clocks differ")
    receptor = ExposureReceptor(receptor_id, flame.location.coordinate_frame_id,
        tuple(float(x) for x in radiation.points_m[observer_index]), basis_id)
    return ExposureHistory(receptor, [start, end],
        [float(radiation.irradiance_w_m2[observer_index])],
        "incident_radiant_flux", "W/m2", "left_hold", window.clock_id,
        flame.location.source_id, basis_id, window.origin,
        input_evidence_ids=(window.source_evidence_id, window.steady_evidence_id))


@dataclass(frozen=True, slots=True)
class PressurePeak:
    receptor: ExposureReceptor
    overpressure_pa: float
    positive_impulse_pa_s: float | None
    clock_id: str
    support_s: tuple[float, float]
    source_id: str
    basis_id: str
    origin: Origin
    input_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        _ids(self.clock_id, self.source_id, self.basis_id)
        if not isinstance(self.receptor, ExposureReceptor) or finite(self.overpressure_pa, "peak gauge overpressure") < 0:
            raise ValueError("Peak-only input needs a receptor and nonnegative gauge overpressure")
        if self.positive_impulse_pa_s is not None and finite(self.positive_impulse_pa_s, "positive-phase impulse") < 0:
            raise ValueError("Positive-phase impulse cannot be negative")
        support = tuple(self.support_s)
        if len(support) != 2 or finite(support[0], "support start") >= finite(support[1], "support end"):
            raise ValueError("Peak evidence needs an explicit increasing clock window")
        object.__setattr__(self, "support_s", support)
        object.__setattr__(self, "origin", _origin(self.origin))
        evidence = tuple(self.input_evidence_ids)
        _ids(*evidence) if evidence else None
        object.__setattr__(self, "input_evidence_ids", evidence)

    @property
    def content_sha256(self):
        return hashlib.sha256(repr(self).encode()).hexdigest()


def pressure_peak_from_hyram_overpressure(result, *, receptor_index: int,
        support_s: tuple[float, float], receptor_id: str, basis_id: str):
    """Bind a current native HyRAM Bauwens peak to a caller-timed pressure input.

    HyRAM supplies a peak correlation only. The support interval and pressure
    basis are explicit caller context; this adapter invents no waveform, impulse,
    arrival time, reflection or duration law.
    """
    from .hyram_overpressure import BauwensPeakResult

    if type(result) is not BauwensPeakResult:
        raise ValueError("Require an owner-issued native HyRAM Bauwens peak result")
    result.require_current()
    if isinstance(receptor_index, bool) or not isinstance(receptor_index, int):
        raise ValueError("Select one receptor by integer index")
    if not 0 <= receptor_index < len(result.receptors_m):
        raise ValueError("Receptor index is outside the native overpressure result")
    support = tuple(support_s)
    if len(support) != 2:
        raise ValueError("Declare an increasing caller-owned pressure clock support")
    start, end = finite(support[0], "pressure support start"), finite(support[1], "pressure support end")
    if start >= end or not start <= result.event.snapshot_time_s <= end:
        raise ValueError("Declared support must include the native event snapshot time")
    receptor = ExposureReceptor(receptor_id, result.event.frame_id,
        tuple(float(x) for x in result.receptors_m[receptor_index]), basis_id)
    return PressurePeak(receptor, float(result.peak_overpressure_pa[receptor_index]), None,
        result.event.clock_id, (start, end), result.energy.source_id, basis_id,
        result.energy.origin, (result.event.centre_evidence_id, result.energy.mass_evidence_id,
        result.energy.heat_evidence_id, result.energy.combustion_basis_id,
        result.environment.pressure_evidence_id, result.domain.evidence_id,
        result.native_source_id))


def exposure_history_from_pool_fire(trace, receptor_id: str, *, basis_id: str,
                                    evidence_id: str):
    """Convert one owner's finite pool-fire receptor field to typed exposure.

    Stage activity is represented by its exact held incident flux and any
    remaining inactive part of a stage by zero. No transient pool/fire model is
    added; this is only a typed history handoff to the existing exposure API.
    """
    from .pool_fire import PoolFireTrace

    if type(trace) is not PoolFireTrace:
        raise TypeError("Supply an original owner-issued finite PoolFireTrace")
    trace.require_current()
    _ids(receptor_id, basis_id, evidence_id)
    if not trace.steps:
        raise ValueError("Pool-fire trace contains no finite stages")
    location = trace.seed.location
    origins = {trace.seed.origin, trace.ignition.origin}
    times = [float(trace.steps[0].stage.start_s)]
    values, evidence = [], [evidence_id, trace.seed.evidence_id, trace.ignition.evidence_id]
    for step in trace.steps:
        stage = step.stage
        if stage.clock_id != location.clock_id or times[-1] != stage.start_s:
            raise ValueError("Pool-fire stages must be contiguous on the source clock")
        matches = [row for row in step.receptors if row.receptor.identifier == receptor_id]
        if len(matches) != 1:
            raise ValueError("Each stage must retain exactly one selected receptor")
        row = matches[0]
        receptor = row.receptor
        if (receptor.clock_id != location.clock_id or receptor.frame_id != location.coordinate_frame_id
                or receptor.position_m is None or row.active_start_s != stage.start_s
                or not stage.start_s < row.active_end_s <= stage.end_s):
            raise ValueError("Pool-fire receptor identity/activity is not aligned to source stage")
        origins.update((stage.origin, receptor.origin))
        flux = finite(row.incident_flux_w_m2, "native receptor incident flux")
        if flux < 0:
            raise ValueError("Incident receptor flux cannot be negative")
        values.append(flux)
        times.append(float(row.active_end_s))
        if row.active_end_s < stage.end_s:
            values.append(0.)
            times.append(float(stage.end_s))
        evidence.extend((stage.burning_flux_evidence_id, stage.sphere_geometry_evidence_id,
                         stage.energy_partition_evidence_id, receptor.geometry_evidence_id,
                         receptor.transmissivity_evidence_id))
    if len(origins) != 1:
        raise ValueError("A single exposure history requires one consistent declared origin")
    first_receptor = next(row.receptor for row in trace.steps[0].receptors
                          if row.receptor.identifier == receptor_id)
    result = ExposureHistory(ExposureReceptor(receptor_id, first_receptor.frame_id,
        tuple(first_receptor.position_m), basis_id), times, values,
        "incident_radiant_flux", "W/m2", "left_hold", location.clock_id,
        location.source_id, basis_id, next(iter(origins)),
        input_evidence_ids=tuple(evidence))
    trace.require_current()
    return result


@dataclass(frozen=True, slots=True)
class NativeHarmSelection:
    model_id: str
    normal_distribution_mean: float
    evidence_id: str
    applicability_id: str
    origin: Origin

    def __post_init__(self):
        _ids(self.model_id, self.evidence_id, self.applicability_id)
        finite(self.normal_distribution_mean, "native probit normal-distribution mean")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class NativeExposureCall:
    function: Any
    args: tuple
    kwargs: Any
    raw: Any


@dataclass(frozen=True, slots=True)
class ExposureResult:
    input: Any
    selection: NativeHarmSelection | None
    assumption_evidence_id: str
    thermal_dose: float | None
    fluence_j_m2: float | None
    peak_overpressure_pa: float | None
    positive_impulse_pa_s: float | None
    probability: float | None
    native_probit: Any
    native_result: Any
    native_module: Any
    native_calls: tuple[NativeExposureCall, ...]
    quadrature_records: tuple
    native_source_sha256: str
    input_sha256: str
    quadrature_relative_tolerance: float
    evaluation_kind: str
    evaluation_sha256: str
    status: str = "conditional-on-supplied-exposure"

    @property
    def receptor_id(self):
        return self.input.receptor.receptor_id

    @property
    def frame_id(self):
        return self.input.receptor.frame_id

    @property
    def clock_id(self):
        return self.input.clock_id

    @property
    def support_s(self):
        return self.input.support_s

    @property
    def source_id(self):
        return self.input.source_id

    @property
    def model_id(self):
        return None if self.selection is None else self.selection.model_id

    @property
    def evidence_id(self):
        return None if self.selection is None else self.selection.evidence_id


class ExposureEvaluationError(RuntimeError):
    def __init__(self, message, *, input, selection, native_module, native_calls, quadratures, failed_call):
        super().__init__(message)
        self.input, self.selection, self.native_module = input, selection, native_module
        self.native_calls, self.quadrature_records = tuple(native_calls), tuple(quadratures)
        self.failed_call = failed_call


class ExposureVerificationError(RuntimeError):
    """Keep the supplied record and actual replay when provenance audit fails."""

    def __init__(self, message, *, supplied, replayed, native_module):
        super().__init__(message)
        self.supplied, self.replayed, self.native_module = supplied, replayed, native_module


def _evaluation_id(input_sha, selection, assumption, tolerance, kind, source_sha):
    return hashlib.sha256(repr((input_sha, selection, assumption, tolerance, kind, source_sha)).encode()).hexdigest()


def _same_value(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, np.ndarray):
        return a.dtype == b.dtype and np.array_equal(a, b, equal_nan=True)
    return a == b


def _same_quadrature(a, b):
    if not isinstance(a, tuple) or len(a) != 3 or len(b) != 3:
        return False
    if not _same_value(a[0], b[0]) or not _same_value(a[1], b[1]):
        return False
    info, reference = a[2], b[2]
    if set(info) != set(reference) or info["neval"] != reference["neval"] or info["last"] != reference["last"]:
        return False
    active = reference["last"]
    for name in ("alist", "blist", "rlist", "elist"):
        if not _same_value(np.asarray(info[name])[:active], np.asarray(reference[name])[:active]):
            return False
    # QUADPACK work arrays have uninitialized unused tails. Only its documented
    # active error-order pointers and active subinterval records have meaning.
    capacity = len(reference["iord"])
    pointers = active if active <= capacity/2+2 else capacity+1-active
    return _same_value(np.asarray(info["iord"])[:pointers], np.asarray(reference["iord"])[:pointers])


class HyRAMExposure:
    """Actual separately installed HyRAM6.1; no model or probability defaults."""

    def __init__(self, native_probits=None, *, quadrature_relative_tolerance=1e-9):
        module = importlib.import_module("hyram.qra.probits")
        if native_probits is not None and native_probits is not module:
            raise ValueError("Supply the actual imported native HyRAM probits module")
        if importlib.metadata.version("hyram") != "6.1":
            raise ValueError("This native exposure level is checked with HyRAM6.1")
        self.native_module = module
        self.source_path = Path(module.__file__).resolve()
        self.native_source_sha256 = hashlib.sha256(self.source_path.read_bytes()).hexdigest()
        self.thermal_models = MappingProxyType(dict(module.PROBIT_THERMAL_CHOICES))
        self.pressure_models = MappingProxyType(dict(module.PROBIT_OVERP_CHOICES))
        functions = (module.calculate_thermal_dose, module.calculate_fatality_probability,
            module.compute_thermal_fatality_prob, module.compute_overpressure_fatality_prob,
            *self.thermal_models.values(), *self.pressure_models.values())
        self._functions = tuple((fn.__name__, fn, fn.__code__, fn.__defaults__) for fn in functions)
        self.native_normal_mean = inspect.signature(module.calculate_fatality_probability).parameters[
            "normal_distribution_mean"].default
        self.quadrature_relative_tolerance = finite(quadrature_relative_tolerance, "quadrature tolerance", positive=True)
        if not 50*np.finfo(float).eps < self.quadrature_relative_tolerance < 1:
            raise ValueError("Use an admitted native quadrature relative tolerance")

    def _require_native(self):
        m = self.native_module
        if (importlib.import_module("hyram.qra.probits") is not m
                or hashlib.sha256(self.source_path.read_bytes()).hexdigest() != self.native_source_sha256
                or set(m.PROBIT_THERMAL_CHOICES) != set(self.thermal_models)
                or set(m.PROBIT_OVERP_CHOICES) != set(self.pressure_models)):
            raise ValueError("Native exposure definition changed")
        if self.native_normal_mean != inspect.signature(m.calculate_fatality_probability).parameters[
                "normal_distribution_mean"].default:
            raise ValueError("Native normal-mean convention binding changed")
        for name, fn, code, defaults in self._functions:
            if getattr(m, name) is not fn or fn.__code__ is not code or fn.__defaults__ != defaults:
                raise ValueError("Native exposure function binding changed")
        if any(m.PROBIT_THERMAL_CHOICES[k] is not v for k, v in self.thermal_models.items()) or any(
                m.PROBIT_OVERP_CHOICES[k] is not v for k, v in self.pressure_models.items()):
            raise ValueError("Native harm model choice binding changed")

    def thermal_dose(self, history: ExposureHistory, *, additivity_evidence_id: str):
        return self._evaluate(history, None, additivity_evidence_id, "thermal")

    def thermal_response(self, history: ExposureHistory, selection: NativeHarmSelection, *, additivity_evidence_id: str):
        return self._evaluate(history, selection, additivity_evidence_id, "thermal")

    def pressure_response(self, input: ExposureHistory | PressurePeak, selection: NativeHarmSelection, *, positive_phase_evidence_id: str):
        return self._evaluate(input, selection, positive_phase_evidence_id, "pressure")

    def verify_result(self, result: ExposureResult) -> ExposureResult:
        """Replay the existing native path and return the original verified object.

        Concrete owner records are required. Matching structural fields alone
        cannot establish a native result or a conditional-risk probability.
        """
        replayed = None
        try:
            self._require_native()
            if type(result) is not ExposureResult:
                raise ValueError("Native exposure verification requires an actual ExposureResult")
            if (result.native_module is not self.native_module or result.native_source_sha256 != self.native_source_sha256
                    or result.status != "conditional-on-supplied-exposure"):
                raise ValueError("Exposure native source/module/status identity differs")
            if (result.input.content_sha256 != result.input_sha256 or result.evaluation_kind not in {"thermal", "pressure"}
                    or result.evaluation_sha256 != _evaluation_id(result.input_sha256, result.selection,
                        result.assumption_evidence_id, result.quadrature_relative_tolerance,
                        result.evaluation_kind, result.native_source_sha256)):
                raise ValueError("Exposure input/model/mean/evidence/settings identity changed")
            replay_engine = HyRAMExposure(self.native_module,
                quadrature_relative_tolerance=result.quadrature_relative_tolerance)
            replayed = replay_engine._evaluate(result.input, result.selection, result.assumption_evidence_id,
                                               result.evaluation_kind)
            for name in ("thermal_dose", "fluence_j_m2", "peak_overpressure_pa", "positive_impulse_pa_s",
                         "probability", "native_probit", "native_result", "input_sha256", "evaluation_sha256"):
                if not _same_value(getattr(result, name), getattr(replayed, name)):
                    raise ValueError("Exposure native replay differs in "+name)
            if not isinstance(result.native_calls, tuple) or len(result.native_calls) != len(replayed.native_calls):
                raise ValueError("Exposure native-call prefix differs from actual replay")
            for actual, reference in zip(result.native_calls, replayed.native_calls, strict=True):
                if (type(actual) is not NativeExposureCall or actual.function is not reference.function
                        or type(actual.args) is not tuple or len(actual.args) != len(reference.args)
                        or set(actual.kwargs) != set(reference.kwargs)
                        or not all(_same_value(a, b) for a, b in zip(actual.args, reference.args, strict=True))
                        or not all(_same_value(actual.kwargs[k], reference.kwargs[k]) for k in reference.kwargs)
                        or not _same_value(actual.raw, reference.raw)):
                    raise ValueError("Exposure retained native function/arguments/raw result differ")
            if result.probability is not None:
                if result.native_result is not result.native_calls[-1].raw:
                    raise ValueError("Exposure native probability is detached from its actual native call")
                if result.native_probit is not None and result.native_probit is not result.native_calls[-2].raw:
                    raise ValueError("Exposure native probit is detached from its actual native call")
            if (not isinstance(result.quadrature_records, tuple)
                    or len(result.quadrature_records) != len(replayed.quadrature_records)
                    or not all(_same_quadrature(a, b) for a, b in zip(
                        result.quadrature_records, replayed.quadrature_records, strict=True))):
                raise ValueError("Exposure meaningful native quadrature records differ")
            self._require_native()
            return result
        except Exception as error:
            raise ExposureVerificationError(str(error), supplied=result, replayed=replayed,
                native_module=self.native_module) from error

    def _evaluate(self, input, selection, assumption, kind):
        calls, quadratures, failed_call = [], [], None
        try:
            self._require_native()
            _ids(assumption)
            if not isinstance(input, (ExposureHistory, PressurePeak)):
                raise ValueError("Supply an explicit history or pressure summary")
            input_sha = input.content_sha256
            if selection is not None and not isinstance(selection, NativeHarmSelection):
                raise ValueError("Supply an explicit native harm selection")
            choices = self.thermal_models if kind == "thermal" else self.pressure_models
            if selection is not None and (selection.model_id not in choices
                    or selection.normal_distribution_mean != self.native_normal_mean):
                raise ValueError("Choose a canonical native model and its declared normal-mean convention")
            if kind == "pressure" and selection is None:
                raise ValueError("Pressure response requires an explicit harm model")
            if isinstance(input, ExposureHistory):
                if not np.all(input.valid) or not np.all(np.isfinite(input.values)):
                    raise ValueError("Missing/masked/nonfinite history is retained without filling")
                if kind == "thermal" and (input.quantity not in {"incident_radiant_flux", "absorbed_radiant_flux"}
                        or np.any(input.values < 0)):
                    raise ValueError("Thermal dose needs a nonnegative declared radiant-flux history")
                if kind == "pressure" and input.quantity != "gauge_overpressure":
                    raise ValueError("Pressure response needs a gauge-overpressure waveform")
            if kind == "thermal" and (not isinstance(input, ExposureHistory)
                    or (selection is not None and input.quantity != "incident_radiant_flux")):
                raise ValueError("Native thermal harm requires incident flux; absorbed dose is a separate diagnostic")

            def invoke(fn, *args, **kwargs):
                nonlocal failed_call
                failed_call = (fn, args, MappingProxyType(dict(kwargs)))
                raw = fn(*args, **kwargs)
                calls.append(NativeExposureCall(fn, args, MappingProxyType(dict(kwargs)), raw))
                failed_call = None
                return raw

            def integrate(fn, width):
                from scipy.integrate import quad
                record = quad(fn, 0., width, epsabs=0., epsrel=self.quadrature_relative_tolerance, full_output=1)
                quadratures.append(record)
                if len(record) != 3 or not math.isfinite(record[0]) or not math.isfinite(record[1]):
                    raise ValueError("Native quadrature failed; its raw result is retained")
                return record[0]

            dose = fluence = peak = impulse = probability = native_probability = native_probit = None
            if isinstance(input, ExposureHistory):
                terms, fluences = [], []
                for k, width in enumerate(np.diff(input.time_s)):
                    a = float(input.values[k])
                    b = a if input.interpolation == "left_hold" else float(input.values[k+1])
                    if kind == "thermal":
                        def unit_dose(value):
                            result = finite(invoke(self.native_module.calculate_thermal_dose, value, 1.), "native unit-time dose")
                            if value > 0 and result == 0:
                                raise ValueError("Positive native thermal dose underflow is unresolved")
                            return result
                        if a == b:
                            result = finite(invoke(self.native_module.calculate_thermal_dose, a, float(width)), "native dose")
                            if a > 0 and result == 0:
                                raise ValueError("Positive native thermal dose underflow is unresolved")
                            terms.append(result)
                        else:
                            terms.append(integrate(lambda offset: unit_dose(a+(b-a)*offset/width), float(width)))
                        fluences.append(finite((a+b)*.5*float(width), "radiant fluence"))
                    else:
                        terms.append(finite(max(a, 0.)*float(width), "positive impulse") if a == b else
                            integrate(lambda offset: max(a+(b-a)*offset/width, 0.), float(width)))
                if kind == "thermal":
                    dose, fluence = finite(math.fsum(terms), "accumulated native dose"), finite(math.fsum(fluences), "total fluence")
                else:
                    peak, impulse = max(0., float(np.max(input.values))), finite(math.fsum(terms), "positive-phase impulse")
                    if peak > 0 and impulse == 0:
                        raise ValueError("Positive waveform impulse underflow is unresolved")
            elif kind == "pressure":
                peak, impulse = input.overpressure_pa, input.positive_impulse_pa_s
            if selection is not None:
                fn = choices[selection.model_id]
                mean = selection.normal_distribution_mean
                if kind == "thermal":
                    if dose == 0:
                        native_probability = invoke(self.native_module.compute_thermal_fatality_prob,
                            selection.model_id, 0., input.support_s[1]-input.support_s[0], mean=mean)
                    else:
                        native_probit = invoke(fn, dose)
                else:
                    needs_impulse = "impulse" in inspect.signature(fn).parameters
                    if needs_impulse and impulse is None:
                        raise ValueError("Chosen native pressure model requires supplied positive-phase impulse")
                    native_impulse = impulse if needs_impulse else None
                    if peak == 0 or (needs_impulse and impulse == 0):
                        native_probability = invoke(self.native_module.compute_overpressure_fatality_prob,
                            selection.model_id, peak, native_impulse, mean=mean)
                    else:
                        native_probit = invoke(fn, overp=peak, **({"impulse": impulse} if needs_impulse else {}))
                if native_probit is not None:
                    finite(native_probit, "native probit")
                    native_probability = invoke(self.native_module.calculate_fatality_probability, native_probit, mean)
                probability = finite(native_probability, "native conditional harm probability")
                if not 0 <= probability <= 1:
                    raise ValueError("Native probability lies outside [0,1]")
            self._require_native()
            if input.content_sha256 != input_sha:
                raise ValueError("Exposure history/source coordinates changed during evaluation")
            return ExposureResult(input, selection, assumption, dose, fluence, peak, impulse, probability,
                native_probit, native_probability, self.native_module, tuple(calls), tuple(quadratures),
                self.native_source_sha256, input_sha, self.quadrature_relative_tolerance, kind,
                _evaluation_id(input_sha, selection, assumption, self.quadrature_relative_tolerance,
                               kind, self.native_source_sha256))
        except Exception as error:
            raise ExposureEvaluationError(str(error), input=input, selection=selection, native_module=self.native_module,
                native_calls=calls, quadratures=quadratures, failed_call=failed_call) from error
