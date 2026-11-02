"""Actual native learned residual monitoring; scores do not identify physical faults."""

import hashlib
import importlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ..core import immutable_array, Origin, TimeSeries, finite
from ..observations import ObservationTable, Variable

_NATIVE_SHA = "6c4b02f9d578b33c08194a5545e0f524a0b937373aad4f1981e814c3e12ac10b"
_CALLS = {
    "pipeline": ("Monitor.__init__", "Monitor.fit", "Monitor._scores", "Monitor.calibrate",
                 "Monitor.score", "ModeMonitor.__init__", "ModeMonitor.fit",
                 "ModeMonitor.calibrate", "ModeMonitor.score", "_mode_subset"),
    "contracts": ("SignalBatch.__post_init__", "SignalBatch.subset"),
    "features": ("WindowFeatures.__post_init__", "WindowFeatures.transform"),
    "detectors.classical": ("PCADetector.__init__", "PCADetector.fit",
                           "PCADetector._statistics", "PCADetector.score_samples"),
    "detectors.base": ("matrix",),
    "registry": ("create_detector", "_create_detector"),
    "thermo": ("predicted_measurement_residual",),
}


def _call_bindings(package):
    result = []
    modules = {}
    for suffix, names in _CALLS.items():
        module = importlib.import_module(f"{package.__name__}.{suffix}")
        modules[suffix] = module
        for name in names:
            function = module
            for part in name.split("."):
                function = getattr(function, part)
            if (getattr(function, "__module__", None) != module.__name__
                    or getattr(function, "__qualname__", None) != name
                    or not hasattr(function, "__code__")
                    or Path(function.__code__.co_filename).resolve() != Path(module.__file__).resolve()):
                raise ValueError(f"Native monitoring method origin/binding changed: {suffix}.{name}")
            result.append((function, function.__code__, repr(function.__defaults__),
                           repr(function.__kwdefaults__)))
    for name, source in (("Monitor", "pipeline"), ("ModeMonitor", "pipeline"),
                         ("WindowFeatures", "features"), ("SignalBatch", "contracts"),
                         ("create_detector", "registry")):
        if getattr(package, name) is not getattr(modules[source], name):
            raise ValueError(f"Native monitoring export binding changed: {name}")
    return tuple(result)


def _source_hash(module):
    base = Path(module.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(base.rglob("*.py")):
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


@dataclass(frozen=True, slots=True)
class NativeProcessMonitoring:
    module: Any
    thermo: Any
    classical: Any
    serialization: Any
    sklearn: Any
    source_sha256: str
    versions: Mapping[str, str]
    call_bindings: tuple

    @classmethod
    def from_installed(cls):
        """Explicit optional native import; no installation or path changes."""
        module = importlib.import_module("process_monitoring")
        sklearn = importlib.import_module("sklearn")
        serialization = importlib.import_module("cloudpickle")
        versions = {"process_monitoring": module.__version__, "scikit-learn": sklearn.__version__,
                    "cloudpickle": serialization.__version__,
                    "numpy": np.__version__, "scipy": importlib.import_module("scipy").__version__}
        if (module.__version__, sklearn.__version__, serialization.__version__) != (
                "0.1.0", "1.9.1", "3.1.2") or _source_hash(module) != _NATIVE_SHA:
            raise ValueError("Native monitoring code/dependency versions differ from the reviewed source")
        return cls(module, importlib.import_module("process_monitoring.thermo"),
            importlib.import_module("process_monitoring.detectors.classical"), serialization,
            sklearn, _NATIVE_SHA, MappingProxyType(versions), _call_bindings(module))

    def digest(self, value):
        # Only serialize current in-memory objects. No external pickle is loaded.
        return hashlib.sha256(self.serialization.dumps(value)).hexdigest()

    def require_source(self):
        if self.source_sha256 != _NATIVE_SHA or _source_hash(self.module) != self.source_sha256:
            raise ValueError("Actual native monitoring source changed after admission")
        if _call_bindings(self.module) != self.call_bindings:
            raise ValueError("Actual native monitoring method/code binding changed after admission")


@dataclass(frozen=True, slots=True)
class ResidualFeature:
    name: str
    observed_channel: str
    predicted_channel: str
    variable: Variable
    observed_location_id: str
    predicted_location_id: str
    uncertainty_scale: float
    uncertainty_id: str

    def __post_init__(self):
        for name in ("name", "observed_channel", "predicted_channel", "observed_location_id",
                     "predicted_location_id", "uncertainty_id"):
            _text(getattr(self, name), name)
        if not isinstance(self.variable, Variable):
            raise TypeError("Residual features require an explicit physical Variable")
        if self.observed_location_id != self.predicted_location_id:
            raise ValueError("Observed and predicted physical locations differ")
        if self.variable.quantity in {"pressure", "pressure_difference"}:
            if self.variable.unit != "Pa" or not self.variable.basis_id:
                raise ValueError("Pressure residuals require Pa and an explicit absolute/gauge/differential basis")
        if self.variable.quantity == "temperature" and self.variable.unit != "K":
            raise ValueError("Temperature residuals require K")
        finite(self.uncertainty_scale, "residual scale in the original physical unit", positive=True)


@dataclass(frozen=True, slots=True)
class ResidualContext:
    partition_id: str
    role: str
    scope_id: str
    mode_definition_id: str
    prediction_model_id: str
    observation_operator_id: str
    normal_reference_id: str = ""

    def __post_init__(self):
        for name in ("partition_id", "scope_id", "mode_definition_id", "prediction_model_id",
                     "observation_operator_id"):
            _text(getattr(self, name), name)
        if self.role not in {"fitting", "calibration", "evaluation"}:
            raise ValueError("Declare fitting/calibration/evaluation role before building residuals")
        if not isinstance(self.normal_reference_id, str):
            raise ValueError("Normal-reference evidence must be an explicit string")


def _series_value(series):
    return (series.time_s, series.values, series.valid, series.channels, series.units,
            series.quantities, series.basis_ids, series.clock_id, series.origin, series.source_id)


@dataclass(frozen=True, slots=True)
class ResidualBatch:
    native_batch: Any
    observations: ObservationTable
    observed: TimeSeries
    predicted: TimeSeries
    features: tuple[ResidualFeature, ...]
    context: ResidualContext
    prediction_owner: Any
    content_sha256: str

    def current_sha256(self, native):
        return native.digest((self.native_batch, self.observations.content_sha256, self.features,
            self.context, _series_value(self.observed), _series_value(self.predicted)))

    def require_unchanged(self, native):
        if not isinstance(self.native_batch, native.module.SignalBatch):
            raise TypeError("Residual input must retain its actual native SignalBatch")
        if self.current_sha256(native) != self.content_sha256:
            raise ValueError("Admitted residual arrays, evidence, order or original signals changed")

    @property
    def episodes(self):
        return frozenset(self.observations.experiment_ids)

    @property
    def contract(self):
        c = self.context
        return (self.features, c.scope_id, c.mode_definition_id, c.prediction_model_id,
                c.observation_operator_id)


def residual_batch(native: NativeProcessMonitoring, observed: TimeSeries, predicted: TimeSeries,
                   features: tuple[ResidualFeature, ...], *, context: ResidualContext,
                   episodes, modes, prediction_owner) -> ResidualBatch:
    """Same-clock native observed-minus-predicted residuals with explicit masks.

    Scale is in each original physical unit; it is not inferred to be a noise
    standard deviation or a probability model. No resampling or missing-data fill.
    """
    native.require_source()
    if not isinstance(context, ResidualContext) or not isinstance(observed, TimeSeries) or not isinstance(predicted, TimeSeries):
        raise TypeError("Explicit ResidualContext and original TimeSeries objects are required")
    for series in (observed, predicted):
        # Reuse the existing current-value contract while retaining original
        # source objects below; do not invent a second time-series validator.
        TimeSeries(**{n: getattr(series, n) for n in series.__dataclass_fields__})
    # Revalidate the current values of frozen evidence objects before using them.
    context = ResidualContext(**{n: getattr(context, n) for n in context.__dataclass_fields__})
    features = tuple(features)
    if any(not isinstance(f, ResidualFeature) for f in features):
        raise TypeError("Every ordered residual feature must be an actual ResidualFeature")
    features = tuple(ResidualFeature(**{n: getattr(f, n) for n in f.__dataclass_fields__})
                     for f in features)
    if not features or len({f.name for f in features}) != len(features):
        raise ValueError("Declare nonempty unique ordered residual features")
    if prediction_owner is None:
        raise ValueError("Retain the physical prediction/observation owner explicitly")
    if observed.origin in {Origin.UNRESOLVED, Origin.PREDICTED} or predicted.origin not in {
            Origin.PREDICTED, Origin.SYNTHETIC}:
        raise ValueError("Declare observed/synthetic and predicted/synthetic signal origins")
    if observed.clock_id != predicted.clock_id or not np.array_equal(observed.time_s, predicted.time_s):
        raise ValueError("Observed and predicted clocks/times must be exactly aligned; no hidden interpolation")
    episodes, modes = tuple(episodes), tuple(modes)
    if len(episodes) != len(observed.time_s) or len(modes) != len(episodes):
        raise ValueError("Whole-run episode IDs and observed modes must match every row")
    for value in episodes+modes:
        _text(value, "whole-run episode and observed mode IDs")
    values, masks = [], []
    for f in features:
        oi, pi = observed.channels.index(f.observed_channel), predicted.channels.index(f.predicted_channel)
        for series, i in ((observed, oi), (predicted, pi)):
            f.variable.require_compatible(Variable(series.channels[i], series.quantities[i],
                                                   series.units[i], series.basis_ids[i]))
        valid = observed.valid[:, oi] & predicted.valid[:, pi]
        a = np.where(valid, observed.values[:, oi], np.nan)
        b = np.where(valid, predicted.values[:, pi], np.nan)
        result = np.asarray(native.thermo.predicted_measurement_residual(
            a, b, uncertainty=f.uncertainty_scale), dtype=float)
        if result.shape != a.shape or np.any(valid & ~np.isfinite(result)):
            raise ValueError("Actual native residual function returned nonfinite/misaligned usable values")
        values.append(result)
        masks.append(valid)
    data, valid = np.column_stack(values), np.column_stack(masks)
    variables = tuple(Variable(f.name, "scaled_prediction_residual", "1",
        f"{f.variable.quantity}:{f.variable.unit}:{f.variable.basis_id}:{f.observed_location_id}:"
        f"scale={f.uncertainty_scale}:{f.uncertainty_id}") for f in features)
    table = ObservationTable(data, variables, valid,
        tuple(f"{context.partition_id}:{i}" for i in range(len(data))), episodes,
        (observed.origin,)*len(features), context.partition_id,
        (("observed_source", observed.source_id), ("predicted_source", predicted.source_id),
         ("clock_id", observed.clock_id), ("role", context.role), ("scope_id", context.scope_id)))
    batch = native.module.SignalBatch(observed.time_s, data, tuple(f.name for f in features),
        ("1",)*len(features), valid, episodes, modes, observed.origin.value,
        {"partition_id": context.partition_id, "clock_id": observed.clock_id,
         "observed_source": observed.source_id, "predicted_source": predicted.source_id,
         "scope_id": context.scope_id, "observation_table_sha256": table.content_sha256})
    value = ResidualBatch(batch, table, observed, predicted, features, context, prediction_owner, "")
    object.__setattr__(value, "content_sha256", value.current_sha256(native))
    return value


@dataclass(frozen=True, slots=True)
class MonitoringSettings:
    window: int = 4
    statistics: tuple[str, ...] = ("mean", "std")
    maximum_gap_s: float = 1.5
    principal_components: int = 1
    false_alarm_fraction: float = .05

    def __post_init__(self):
        if isinstance(self.window, bool) or not isinstance(self.window, int) or self.window < 2:
            raise ValueError("A causal residual window requires at least two rows")
        if (isinstance(self.principal_components, bool) or not isinstance(self.principal_components, int)
                or self.principal_components < 1):
            raise ValueError("Declare a positive integer native PCA dimension")
        if not self.statistics or set(self.statistics)-{"last", "mean", "std", "slope", "rms", "range"}:
            raise ValueError("Declare the supported causal feature statistics")
        object.__setattr__(self, "statistics", tuple(self.statistics))
        finite(self.maximum_gap_s, "maximum causal gap", positive=True)
        if not 0 < finite(self.false_alarm_fraction, "empirical calibration fraction") < 1:
            raise ValueError("Calibration fraction must lie in (0,1)")


class MonitoringNativeError(RuntimeError):
    """Original cause plus actual attempted model, data, result and completed stages."""

    def __init__(self, message, *, operation, owner, attempted_data, native_result=None):
        super().__init__(message)
        self.operation, self.owner = operation, owner
        self.native_model = owner.native_model
        self.attempted_data, self.native_result = attempted_data, native_result
        self.fitting_data, self.calibration_data = owner.fitting_data, owner.calibration_data
        self.completed_evaluations = tuple(owner.evaluations)
        self.native_attempted_models = tuple(owner.native_attempts)
        self.last_admitted_model_sha256 = owner._state_sha


@dataclass(frozen=True, slots=True)
class MonitoringEvaluation:
    data: ResidualBatch
    native_result: Any
    native_model: Any
    fitting_data: ResidualBatch
    calibration_data: ResidualBatch
    trained_state_sha256: str
    mode_thresholds: Mapping[str, float]
    score_meaning: str = "native combined-PCA score minus independently calibrated mode threshold"
    physical_control_actions: bool = False
    fault_identification: bool = False
    time_s: np.ndarray = field(init=False)
    scores: np.ndarray = field(init=False)
    valid: np.ndarray = field(init=False)
    alarms: np.ndarray = field(init=False)

    def __post_init__(self):
        for name in ("time_s", "scores", "valid", "alarms"):
            value = np.array(getattr(self.native_result, name), copy=True)
            value = immutable_array(value, name="value")
            object.__setattr__(self, name, value)


class NativeResidualMonitor:
    """Native mode-specific learned PCA; explicit independent lifecycle and evidence."""

    def __init__(self, native: NativeProcessMonitoring,
                 settings: MonitoringSettings = MonitoringSettings()):
        if not isinstance(native, NativeProcessMonitoring) or not isinstance(settings, MonitoringSettings):
            raise TypeError("Actual reviewed native provider and MonitoringSettings are required")
        native.require_source()
        self.native, self.settings = native, settings
        self.fitting_data = self.calibration_data = None
        self.evaluations, self._state_sha, self.status = [], None, "new"
        self.native_attempts = []
        self._functions = (native.module.Monitor, native.module.ModeMonitor, native.module.create_detector,
                           native.module.WindowFeatures, native.thermo.predicted_measurement_residual)

        def factory():
            detector = native.module.create_detector("pca", n_components=settings.principal_components,
                                                     statistic="combined")
            if type(detector) is not native.classical.PCADetector:
                raise TypeError("Native registry no longer returns the actual reviewed PCA detector")
            monitor = native.module.Monitor(detector, native.module.WindowFeatures(
                settings.window, settings.statistics, max_gap_s=settings.maximum_gap_s))
            self.native_attempts.append(monitor)
            return monitor

        self._factory = factory
        self.native_model = native.module.ModeMonitor(factory)
        self._model = self.native_model
        self._settings_sha = native.digest(settings)

    def _guard(self):
        self.native.require_source()
        if self.native.digest(self.settings) != self._settings_sha or self.native_model is not self._model:
            raise ValueError("Admitted monitoring settings or actual model ownership changed")
        if self._functions != (self.native.module.Monitor, self.native.module.ModeMonitor,
                self.native.module.create_detector, self.native.module.WindowFeatures,
                self.native.thermo.predicted_measurement_residual) or self.native_model.factory is not self._factory:
            raise ValueError("Admitted actual native monitoring functions changed")
        if self._state_sha is not None and self._model_hash() != self._state_sha:
            raise ValueError("Fitted native model/scaler/threshold state changed outside its lifecycle")
        for data in (self.fitting_data, self.calibration_data):
            if data is not None:
                data.require_unchanged(self.native)

    def _model_hash(self):
        return self.native.digest(tuple(sorted(self.native_model.monitors.items())))

    def _parameter_hash(self):
        return self.native.digest(tuple((k, m.detector, m.scaler, m.features, m.channels,
            m.units, m.normalize, m.fitted) for k, m in sorted(self.native_model.monitors.items())))

    def _data(self, data, role):
        if not isinstance(data, ResidualBatch):
            raise TypeError("Supply an admitted ResidualBatch")
        data.require_unchanged(self.native)
        if data.context.role != role:
            raise ValueError("Partition role does not match fitting/calibration/evaluation operation")
        if role != "evaluation" and not data.context.normal_reference_id.strip():
            raise ValueError("Fitting and calibration require explicit independent normal-reference evidence")
        for prior in (self.fitting_data, self.calibration_data):
            if prior is not None:
                if data.contract != prior.contract:
                    raise ValueError("Residual feature order, units, basis, location, model or mode scope changed")
                if data.episodes & prior.episodes or data.context.partition_id == prior.context.partition_id:
                    raise ValueError("Whole-run fitting/calibration/evaluation groups must be disjoint")

    def fit(self, data: ResidualBatch):
        try:
            self._guard()
            if self.status != "new":
                raise ValueError("Create a new owner for a new fitting campaign")
            self._data(data, "fitting")
            self.native_model.fit(data.native_batch)
            self.fitting_data, self.status = data, "fitted"
            self._state_sha = self._model_hash()
            return self
        except Exception as error:
            self.status = "failed"
            raise MonitoringNativeError(str(error), operation="fit", owner=self, attempted_data=data) from error

    def calibrate(self, data: ResidualBatch):
        try:
            self._guard()
            if self.status != "fitted":
                raise ValueError("Calibrate a successfully fitted owner exactly once")
            self._data(data, "calibration")
            if set(data.native_batch.modes) != set(self.native_model.monitors):
                raise ValueError("Every fitted mode requires independent calibration; no extra mode is calibrated")
            parameters = self._parameter_hash()
            self.native_model.calibrate(data.native_batch,
                                        false_alarm_fraction=self.settings.false_alarm_fraction)
            if self._parameter_hash() != parameters:
                raise ValueError("Native calibration refitted the frozen reference parameters")
            if any(m.threshold is None or not np.isfinite(m.threshold) for m in self.native_model.monitors.values()):
                raise ValueError("Every native mode needs a finite independently calibrated threshold")
            self.calibration_data, self.status = data, "calibrated"
            self._state_sha = self._model_hash()
            return self
        except Exception as error:
            self.status = "failed"
            raise MonitoringNativeError(str(error), operation="calibrate", owner=self, attempted_data=data) from error

    def evaluate(self, data: ResidualBatch) -> MonitoringEvaluation:
        result = None
        try:
            self._guard()
            if self.status != "calibrated":
                raise ValueError("Evaluation requires separate completed normal calibration")
            self._data(data, "evaluation")
            before = self._model_hash()
            result = self.native_model.score(data.native_batch)
            if self._model_hash() != before:
                raise ValueError("Evaluation mutated the frozen native trained state")
            n = len(data.observed.time_s)
            if (result.scores.shape != (n,) or result.valid.shape != (n,) or result.alarms.shape != (n,)
                    or not np.array_equal(result.time_s, data.observed.time_s)
                    or np.any(result.valid & ~np.isfinite(result.scores))
                    or np.any(~result.valid & (~np.isnan(result.scores) | result.alarms))
                    or not np.array_equal(result.alarms, result.valid & (result.scores > result.threshold))):
                raise ValueError("Actual native scores/abstention/alarms do not preserve aligned decision semantics")
            self._guard()
            data.require_unchanged(self.native)
            evaluation = MonitoringEvaluation(data, result, self.native_model,
                self.fitting_data, self.calibration_data, before,
                MappingProxyType({k: float(m.threshold) for k, m in self.native_model.monitors.items()}))
            self.evaluations.append(evaluation)
            return evaluation
        except Exception as error:
            self.status = "failed"
            raise MonitoringNativeError(str(error), operation="evaluate", owner=self,
                                        attempted_data=data, native_result=result) from error
