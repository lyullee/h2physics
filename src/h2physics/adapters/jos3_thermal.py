"""Native multisegment thermal state in explicitly supplied ordinary air.

JOS3 owns physiology, conductances, capacities and its implicit time step. This
adapter copies actual prepared native objects, applies an explicit environment
and audits storage against the boundary used by that native time step. It does
not supply a freezing, injury, hydrogen-rich convection or hypoxia model.

Primary API: https://pythermalcomfort.readthedocs.io/en/latest/documentation/models.html
"""

import copy
import dataclasses
import datetime as dt
import hashlib
import importlib
import importlib.metadata
import inspect
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..core import immutable_array, Origin, finite

SOURCE_SHA256 = "84eb0b8ccd6d7aba575a3949ff27bc6bfe4485e33ee3e467cc5b57b0237c8d18"


def _array(value, size=None):
    if np.asarray(value).dtype.kind in "bc":
        raise ValueError("Thermal arrays require real numeric values, not booleans/complex values")
    values = np.array(value, dtype=float, copy=True)
    if size is not None and values.ndim == 0:
        values = np.full(size, float(values))
    if values.ndim != 1 or (size is not None and values.shape != (size,)):
        raise ValueError("One finite value per native body segment is required")
    if not np.all(np.isfinite(values)):
        raise ValueError("Thermal arrays must be finite")
    values = immutable_array(values, name="values")
    return values


def _normal(value):
    if dataclasses.is_dataclass(value):
        return {f.name: _normal(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, np.ndarray):
        return {"dtype": str(value.dtype), "shape": value.shape, "values": _normal(value.tolist())}
    if isinstance(value, np.generic):
        return _normal(value.item())
    if isinstance(value, dict):
        return {str(k): _normal(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normal(v) for v in value]
    if isinstance(value, dt.timedelta):
        return {"native_elapsed_seconds": value.total_seconds()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported native state definition: {type(value).__name__}")


def _digest(value):
    payload = json.dumps(_normal(value), sort_keys=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _native_source(package):
    root = Path(package.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ThermalSubject:
    """Explicit native constructor inputs; body fat is percent, not fraction."""

    height_m: float
    mass_kg: float
    body_fat_percent: float
    age_years: int
    sex: str
    cardiac_index_l_min_m2: float
    basal_metabolism_equation: str
    surface_area_equation: str

    def __post_init__(self):
        for name in ("height_m", "mass_kg", "body_fat_percent", "cardiac_index_l_min_m2"):
            finite(getattr(self, name), name, positive=True)
        if not 0 < self.body_fat_percent < 100:
            raise ValueError("Body fat must be an explicit percentage in (0,100)")
        if isinstance(self.age_years, bool) or not isinstance(self.age_years, int):
            raise ValueError("Age requires integer years")
        if self.sex not in {"male", "female"}:
            raise ValueError("Choose an actual native subject sex convention")
        for name in ("basal_metabolism_equation", "surface_area_equation"):
            if not getattr(self, name).strip():
                raise ValueError("Native body equations must be explicit")

    def native_kwargs(self):
        return dict(height=self.height_m, weight=self.mass_kg, fat=self.body_fat_percent,
                    age=self.age_years, sex=self.sex, ci=self.cardiac_index_l_min_m2,
                    bmr_equation=self.basal_metabolism_equation,
                    bsa_equation=self.surface_area_equation)


@dataclass(frozen=True, slots=True)
class OrdinaryAirEnvironment:
    """Uniform scalars or 17 local values; all temperatures enter in kelvin."""

    air_temperature_k: np.ndarray
    radiant_temperature_k: np.ndarray
    air_speed_m_s: np.ndarray
    relative_humidity_percent: np.ndarray
    clothing_clo: np.ndarray
    clothing_vapor_efficiency: np.ndarray
    activity_ratio: float
    posture: str
    evidence_id: str

    def __post_init__(self):
        names = ("air_temperature_k", "radiant_temperature_k", "air_speed_m_s",
                 "relative_humidity_percent", "clothing_clo", "clothing_vapor_efficiency")
        for name in names:
            object.__setattr__(self, name, _array(getattr(self, name), 17))
        if any(np.any(getattr(self, n) <= 0) for n in names[:2]):
            raise ValueError("Thermal environment temperatures are positive kelvin")
        if np.any(self.air_speed_m_s < 0) or np.any(self.clothing_clo < 0):
            raise ValueError("Air speed and clothing cannot be negative")
        if np.any((self.relative_humidity_percent < 0) | (self.relative_humidity_percent > 100)):
            raise ValueError("Humidity is percent in [0,100]")
        if np.any((self.clothing_vapor_efficiency <= 0) | (self.clothing_vapor_efficiency > 1)):
            raise ValueError("Clothing vapor efficiency lies in (0,1]")
        finite(self.activity_ratio, "physical activity/basal metabolic ratio", positive=True)
        if self.posture not in {"standing", "sitting", "lying"} or not self.evidence_id.strip():
            raise ValueError("Native posture and environmental evidence must be explicit")


@dataclass(frozen=True, slots=True)
class ThermalInterval:
    start_s: float
    end_s: float
    environment: OrdinaryAirEnvironment

    def __post_init__(self):
        finite(self.start_s, "absolute start")
        finite(self.end_s, "absolute end")
        if self.end_s <= self.start_s or not isinstance(self.environment, OrdinaryAirEnvironment):
            raise ValueError("Thermal intervals need positive duration and an actual environment")
        if (round((self.end_s-self.start_s)*1e6) < 1
                or abs(round(self.end_s-self.start_s, 6)-(self.end_s-self.start_s)) > 1e-9):
            raise ValueError("Native elapsed clock supports microsecond duration resolution")


@dataclass(frozen=True, slots=True)
class ThermalRunEvidence:
    clock_id: str
    frame_id: str
    receptor_id: str
    position_m: tuple[float, float, float]
    source_id: str
    subject_evidence_id: str
    initialization_evidence_id: str
    applicability_evidence_id: str
    medium: str
    reference_pressure_pa: float
    origin: Origin

    def __post_init__(self):
        for name in ("clock_id", "frame_id", "receptor_id", "source_id", "subject_evidence_id",
                     "initialization_evidence_id", "applicability_evidence_id"):
            if not getattr(self, name).strip():
                raise ValueError("Clock, location, initialization and applicability evidence are required")
        position = tuple(finite(v, "receptor coordinate") for v in self.position_m)
        if len(position) != 3:
            raise ValueError("A receptor position requires three coordinates")
        object.__setattr__(self, "position_m", position)
        if self.medium != "ordinary-air" or self.reference_pressure_pa != 101325.:
            raise ValueError("This native level admits ordinary air at its explicit 101325Pa reference only")
        if not isinstance(self.origin, Origin) or self.origin == Origin.UNRESOLVED:
            raise ValueError("Thermal evidence origin is unresolved")


@dataclass(frozen=True, slots=True)
class ThermalDomain:
    minimum_environment_k: float
    maximum_environment_k: float
    minimum_body_k: float
    maximum_body_k: float
    maximum_step_s: float
    numerical_energy_budget_j: float

    def __post_init__(self):
        for field in dataclasses.fields(self):
            finite(getattr(self, field.name), field.name, positive=True)
        if (self.minimum_environment_k < 273.15
                or self.minimum_environment_k >= self.maximum_environment_k
                or self.minimum_body_k <= 273.15
                or self.minimum_body_k >= self.maximum_body_k):
            raise ValueError("Declare ordered nonfreezing air/body domains; this is not a freezing solver")
        if (round(self.maximum_step_s*1e6) < 1
                or abs(round(self.maximum_step_s, 6)-self.maximum_step_s) > 1e-10):
            raise ValueError("Native time steps need microsecond resolution")


@dataclass(frozen=True, slots=True)
class ThermalStep:
    start_s: float
    end_s: float
    body_temperature_k: np.ndarray
    skin_temperature_k: np.ndarray
    core_temperature_k: np.ndarray
    stored_energy_change_j: float
    net_boundary_energy_j: float
    energy_defect_j: float
    output_rounding_budget_j: float
    implicit_sensible_out_w: float
    reported_previous_state_sensible_out_w: float
    native_output: object


@dataclass(frozen=True, slots=True)
class ThermalResponse:
    source_model: object
    native_model: object
    native_initial_history: tuple
    native_outputs: tuple
    steps: tuple[ThermalStep, ...]
    evidence: ThermalRunEvidence
    intervals: tuple[ThermalInterval, ...]
    initial_body_temperature_k: np.ndarray
    capacity_j_k: np.ndarray
    source_model_sha256: str
    input_sha256: str
    native_source_sha256: str
    body_part_names: tuple[str, ...]
    node_index_map: tuple[tuple[str, str, int], ...]
    native_global_shivering_before_w: float
    native_global_shivering_after_w: float
    native_global_memory_isolated: bool = False
    status: str = "conditional-ordinary-air-thermal-state"
    injury_probability: None = None
    full_cryogenic_chain_validated: bool = False


class ThermalResponseError(RuntimeError):
    def __init__(self, message, *, source_model, native_model, evidence, intervals, steps):
        super().__init__(message)
        self.source_model, self.native_model = source_model, native_model
        self.evidence, self.intervals, self.completed_steps = evidence, intervals, tuple(steps)


class NativeJOS3:
    """Optional reviewed native provider; JIT remains enabled and unmodified."""

    def __init__(self, package, model_class):
        module = importlib.import_module("pythermalcomfort.models.jos3")
        if (package is not importlib.import_module("pythermalcomfort")
                or model_class is not module.JOS3
                or model_class.__module__ != "pythermalcomfort.models.jos3"):
            raise TypeError("The actual installed native JOS3 class and package are required")
        self.package, self.model_class, self.module = package, model_class, module
        self.thermoregulation = module.threg
        self.index_sha256 = self._index_digest()
        self.functions = (model_class.__init__, model_class.simulate, model_class._run,
                          model_class.r_t.fget, model_class.to.fget)
        expected = Path(package.__file__).parent/"models/jos3.py"
        if any(Path(f.__code__.co_filename).resolve() != expected.resolve() for f in self.functions):
            raise TypeError("Native thermal methods do not originate in the reviewed module")
        modules = (module, module.threg, module.cons, module.matrix)
        self.owned_functions = tuple((owner, name, function)
            for owner in modules for name, function in vars(owner).items()
            if inspect.isfunction(function) and function.__module__.startswith("pythermalcomfort"))
        self.source_sha256 = _native_source(package)
        self.require_current()

    @classmethod
    def from_installed(cls):
        for name, version in (("pythermalcomfort", "4.7.0"), ("numba", "0.68.1"),
                              ("llvmlite", "0.50.0")):
            if importlib.metadata.version(name) != version:
                raise ValueError(f"Native thermal replay requires reviewed {name}{version}")
        import numba

        if numba.config.DISABLE_JIT:
            raise ValueError("Reviewed native thermal imports require enabled native JIT")
        import pythermalcomfort
        from pythermalcomfort.models import JOS3

        return cls(pythermalcomfort, JOS3)

    def require_current(self, *, source=True):
        cls = self.model_class
        functions = (cls.__init__, cls.simulate, cls._run, cls.r_t.fget, cls.to.fget)
        if functions != self.functions:
            raise ValueError("Native thermal method bindings changed")
        if any(getattr(module, name) is not function for module, name, function in self.owned_functions):
            raise ValueError("Native thermal function bindings changed")
        if self._index_digest() != self.index_sha256:
            raise ValueError("Native thermal node/channel index definitions changed")
        if self.source_sha256 != SOURCE_SHA256 or (source and _native_source(self.package) != SOURCE_SHA256):
            raise ValueError("Native thermal source differs from the reviewed artifact")

    def _index_digest(self):
        m = self.module
        return _digest((m.INDEX, m.VINDEX, m.NUM_NODES, m.matrix.IDICT,
                        m.matrix.INDEX, m.matrix.VINDEX))

    def prepare_neutral(self, subject: ThermalSubject):
        """Native neutral-setpoint warmup, not observed initial body temperatures.

        The engine retains only its final neutral output, not the internal warmup
        trajectory. Caller evidence must distinguish this from actual pre-exposure.
        """
        if not isinstance(subject, ThermalSubject):
            raise TypeError("An actual explicit ThermalSubject is required")
        subject = ThermalSubject(**{f.name: getattr(subject, f.name) for f in dataclasses.fields(subject)})
        self.require_current()
        model = self.model_class(**subject.native_kwargs())
        self.require_current()
        return model


class JOS3ThermalResponse:
    def __init__(self, native: NativeJOS3, domain: ThermalDomain):
        if not isinstance(native, NativeJOS3) or not isinstance(domain, ThermalDomain):
            raise TypeError("Actual reviewed native provider and thermal domain required")
        self.native, self.domain = native, domain

    def run(self, source_model, intervals, *, evidence: ThermalRunEvidence):
        model, steps = None, []
        original_intervals = tuple(intervals)
        try:
            self.native.require_current()
            global_before = float(self.native.thermoregulation.PRE_SHIV)
            if type(source_model) is not self.native.model_class:
                raise TypeError("An actual prepared native JOS3 object is required")
            if not isinstance(evidence, ThermalRunEvidence):
                raise TypeError("Actual thermal evidence is required")
            ThermalRunEvidence(**{f.name: getattr(evidence, f.name) for f in dataclasses.fields(evidence)})
            ThermalDomain(**{f.name: getattr(self.domain, f.name) for f in dataclasses.fields(self.domain)})
            admitted = []
            for item in original_intervals:
                if not isinstance(item, ThermalInterval):
                    raise TypeError("Actual thermal intervals are required")
                env = item.environment
                if not isinstance(env, OrdinaryAirEnvironment):
                    raise TypeError("Actual ordinary-air environment is required")
                env = OrdinaryAirEnvironment(**{f.name: getattr(env, f.name) for f in dataclasses.fields(env)})
                interval = ThermalInterval(item.start_s, item.end_s, env)
                if admitted and admitted[-1].end_s != interval.start_s:
                    raise ValueError("Thermal intervals must be contiguous with one explicit clock")
                first_duration = min(self.domain.maximum_step_s, interval.end_s-interval.start_s)
                if interval.start_s+first_duration <= interval.start_s:
                    raise ValueError("Absolute thermal clock cannot represent a forward native step")
                for array in (env.air_temperature_k, env.radiant_temperature_k):
                    if np.any((array < self.domain.minimum_environment_k)
                              | (array > self.domain.maximum_environment_k)):
                        raise ValueError("Environmental temperature lies outside declared thermal domain")
                admitted.append(interval)
            if not admitted:
                raise ValueError("A nonempty finite thermal campaign is required")
            total_us = sum(round((item.end_s-item.start_s)*1e6) for item in admitted)
            if abs(total_us/1e6-(admitted[-1].end_s-admitted[0].start_s)) > 1e-6:
                raise ValueError("Native microsecond intervals do not preserve total absolute clock support")
            original_signature = _digest((original_intervals, evidence, self.domain))
            source_signature = _digest(vars(source_model))
            model = copy.deepcopy(source_model)
            if _digest(vars(model)) != source_signature:
                raise ValueError("Native thermal private copy changed the prepared definition/state")
            if model._hc is not None or model._hr is not None or np.any(model.ex_q != 0):
                raise ValueError("Custom native heat coefficients/ex_q need a separately audited energy boundary")
            if model.options.get("limit_dshiv/dt") is not False:
                raise ValueError("Native global previous-shivering rate limiter is outside the isolated campaign level")
            if model.options.get("shivering") is not False:
                raise ValueError("The native shivering option is unused; it cannot declare disabled physiology")
            options_signature = _digest(model.options)
            capacity = _array(model._cap, 85)
            if np.any(capacity <= 0):
                raise ValueError("Actual native capacities must be positive")
            initial = _array(model.t_body + 273.15, 85)
            initial_history = tuple(model._history)
            self._body_domain(initial)
            for interval in admitted:
                env = interval.environment
                for field, value in (("tdb", env.air_temperature_k-273.15),
                                     ("tr", env.radiant_temperature_k-273.15),
                                     ("v", env.air_speed_m_s), ("rh", env.relative_humidity_percent),
                                     ("clo", env.clothing_clo), ("iclo", env.clothing_vapor_efficiency),
                                     ("par", env.activity_ratio), ("posture", env.posture)):
                    if field == "iclo":
                        # Native JOS3 exposes this state only as _iclo in 4.7.0.
                        model._iclo = np.array(value, copy=True)
                    else:
                        setattr(model, field, np.array(value, copy=True) if isinstance(value, np.ndarray) else value)
                elapsed_us = 0
                interval_us = round((interval.end_s-interval.start_s)*1e6)
                maximum_us = round(self.domain.maximum_step_s*1e6)
                while elapsed_us < interval_us:
                    duration_us = min(maximum_us, interval_us-elapsed_us)
                    duration = duration_us/1e6
                    start = interval.start_s+elapsed_us/1e6
                    end = (interval.end_s if elapsed_us+duration_us == interval_us
                           else interval.start_s+(elapsed_us+duration_us)/1e6)
                    if not start < end <= interval.end_s or abs((end-start)-duration) > 1e-6:
                        raise ValueError("Absolute thermal clock cannot represent the requested native step")
                    self.native.require_current(source=False)
                    before = model.t_body.copy()
                    resistance, operative = model.r_t.copy(), np.array(model.to, copy=True)
                    elapsed = model._time
                    model.simulate(1, dtime=duration)
                    raw = model._history[-1]
                    after = _array(model.t_body+273.15, 85)
                    self._body_domain(after)
                    if (not np.array_equal(capacity, model._cap) or _digest(model.options) != options_signature
                            or model._time-elapsed != dt.timedelta(microseconds=duration_us)):
                        raise ValueError("Native capacity/options/elapsed clock changed during the campaign")
                    latent = self._segments(raw.q_skin2env_latent)
                    sensible = float(np.sum((model.t_skin-operative)/resistance*model.bsa))
                    stored = float(np.dot(capacity, model.t_body-before))
                    external = float((raw.q_thermogenesis_total-raw.q_res-latent.sum()-sensible)*duration)
                    # Actual native output scalars/17 latent powers have 0.01 W precision.
                    budget = (2+len(latent))*.005*duration
                    defect = stored-external
                    if abs(defect) > budget+self.domain.numerical_energy_budget_j:
                        raise ValueError("Native thermal storage/implicit-boundary energy audit failed")
                    steps.append(ThermalStep(start, end, after,
                        _array(model.t_skin+273.15, 17), _array(model.t_core+273.15, 17),
                        stored, external, defect, budget, sensible,
                        float(self._segments(raw.q_skin2env_sensible).sum()), raw))
                    elapsed_us += duration_us
            if (_digest(vars(source_model)) != source_signature
                    or _digest((original_intervals, evidence, self.domain)) != original_signature):
                raise ValueError("Original prepared native model or campaign inputs changed")
            self.native.require_current()
            node_indices = tuple((part, layer, int(index))
                for part, layers in self.native.module.matrix.IDICT.items()
                for layer, index in (layers.items() if isinstance(layers, dict) else (("blood", layers),))
                if index is not None)
            return ThermalResponse(source_model, model, initial_history,
                tuple(s.native_output for s in steps), tuple(steps), evidence, original_intervals,
                initial, capacity, source_signature, original_signature, self.native.source_sha256,
                tuple(model.body_names), node_indices,
                global_before, float(self.native.thermoregulation.PRE_SHIV))
        except Exception as error:
            raise ThermalResponseError(str(error), source_model=source_model, native_model=model,
                evidence=evidence, intervals=original_intervals, steps=steps) from error

    @staticmethod
    def _segments(value):
        return _array(tuple(vars(value).values()), 17)

    def _body_domain(self, value):
        if np.any((value < self.domain.minimum_body_k) | (value > self.domain.maximum_body_k)):
            raise ValueError("Native body temperatures exceed the declared nonfreezing thermal domain")
