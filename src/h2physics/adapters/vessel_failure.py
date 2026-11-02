"""Unverified fixed-flaw thermal/pressure initiation using actual optional HELPR.

HELPR owns cylindrical geometry, Anderson SIF, hoop reference stress, FAD ratios
and its selected FAD curve. The caller supplies material strength/toughness versus
wall temperature and service conditions. Existing vessel engines own fluid/wall
history; SciPy owns bracketed roots. There is no fatigue growth or post-failure
opening, fragmentation, blast, probability or new vessel ODE here.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field as dataclass_field, fields, replace
from importlib import metadata
from pathlib import Path
from types import MappingProxyType

from ..core import Origin, PropertyBasis, finite
from .fracture_fatigue import HELPR_REVISION, HELPR_VERSION

_SOURCES = {
    "helpr.physics.pipe": "2f1c7ec883c82cb31084341d922fa08f75509b857aa317e73699a673828e8363",
    "helpr.physics.material": "2a0bbde888b086ccb2efbe4cedf1795e56733a376521650f4f35b5bc4c0a5324",
    "helpr.physics.crack_initiation": "f29cead7164337ef833fd9f31894be701f1fb95e891609edb91d98a6798c3b80",
    "helpr.physics.stress_state": "f4e892b61c56bf5567a7e2efae8a7fc51212a45c26e81687272cfc7a2e1d6bd1",
    "helpr.physics.fracture": "a369318836a635057632c449a57229821d82f03faba8aee92dc5b6515172c58b",
    "helpr.utilities.plots": "cc6aed23ae096e268dd9854d1a39d48cba69e500bf280d41da947a692bb92433",
    "helpr.utilities.parameter": "b3aff09d5f1a8cb0180c4b2c21f1a2e8dbb9ddc7848edcc677fdfc8fb6be9b27",
}

_PENDING_FAILURE_REPORT_ISSUERS: set[object] = set()


def _issue_failure_report(report_type, *args, **kwargs):
    """Issue a result only from an actual HelprVesselFailure owner method."""
    token = object()
    _PENDING_FAILURE_REPORT_ISSUERS.add(token)
    try:
        return report_type(*args, **kwargs, _issuer_token=token)
    except Exception:
        _PENDING_FAILURE_REPORT_ISSUERS.discard(token)
        raise


def _failure_report_digest(report) -> str:
    payload = tuple(
        (item.name, _plain(getattr(report, item.name)))
        for item in fields(report)
        if item.name not in {"_issuer_token", "_seal"}
    )
    return _digest(payload)


def _ids(*items):
    if any(not isinstance(v, str) or not v.strip() for v in items):
        raise ValueError(
            "Explicit vessel/region/clock/material/geometry/source evidence is required"
        )


def _origin(value):
    origin = Origin(value)
    if origin is Origin.UNRESOLVED:
        raise ValueError("Unresolved input origin cannot admit a mechanical prediction")
    return origin


def _bounds(value, name, *, positive=False):
    values = tuple(finite(v, name, positive=positive) for v in value)
    if len(values) != 2 or values[0] < 0 or values[0] >= values[1]:
        raise ValueError(f"{name} must have ordered explicit finite bounds")
    return values


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if callable(value):
        function = getattr(value, "__func__", value)
        return (id(function), id(getattr(function, "__code__", None)))
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dataclass_fields__"):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if hasattr(value, "tolist"):
        return _plain(value.tolist())
    if hasattr(value, "item"):
        return value.item()
    return (type(value).__module__, type(value).__name__, id(value))


def _digest(value):
    return hashlib.sha256(
        json.dumps(_plain(value), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _methods(cls):
    return {
        name: _plain(getattr(cls, name))
        for name in dir(cls)
        if not name.startswith("__") and callable(getattr(cls, name))
    }


@dataclass(frozen=True, slots=True)
class VesselFailureContext:
    vessel_id: str
    wall_region_id: str
    frame_id: str
    clock_id: str
    source_id: str
    fluid_basis: PropertyBasis
    hydrogen_mole_fraction: float
    hydrogen_service_evidence_id: str
    wall_temperature_evidence_id: str
    geometry_binding_evidence_id: str
    origin: Origin

    def __post_init__(self):
        _ids(
            self.vessel_id,
            self.wall_region_id,
            self.frame_id,
            self.clock_id,
            self.source_id,
            self.hydrogen_service_evidence_id,
            self.wall_temperature_evidence_id,
            self.geometry_binding_evidence_id,
        )
        if type(self.fluid_basis) is not PropertyBasis:
            raise TypeError("Keep the actual fluid/reference/spin PropertyBasis")
        if not 0 <= finite(self.hydrogen_mole_fraction, "H2 mole fraction") <= 1:
            raise ValueError("Service H2 fraction must be a fraction, not percent")
        object.__setattr__(self, "origin", _origin(self.origin))


@dataclass(frozen=True, slots=True)
class VesselLoading:
    time_s: float
    internal_pressure_pa_absolute: float
    external_pressure_pa_absolute: float
    wall_temperature_k: float
    phase_id: str
    native_snapshot: object | None = None
    native_state: object | None = None
    native_fluid: object | None = None
    reconstruction_parents: tuple = ()

    def __post_init__(self):
        finite(self.time_s, "loading clock time")
        internal = finite(
            self.internal_pressure_pa_absolute, "internal absolute pressure", positive=True
        )
        external = finite(self.external_pressure_pa_absolute, "external absolute pressure")
        finite(self.wall_temperature_k, "mechanically represented wall temperature", positive=True)
        _ids(self.phase_id)
        if not 0 <= external < internal:
            raise ValueError(
                "Native tensile-pressure level requires Pinside > Poutside >= 0; no buckling model"
            )
        object.__setattr__(self, "reconstruction_parents", tuple(self.reconstruction_parents))

    @property
    def pressure_difference_pa(self):
        return self.internal_pressure_pa_absolute - self.external_pressure_pa_absolute


@dataclass(frozen=True, slots=True)
class VesselFailureHistory:
    context: VesselFailureContext
    samples: tuple[VesselLoading, ...]
    reconstruction_evidence_id: str
    native_trace: object | None = None

    def __post_init__(self):
        _ids(self.reconstruction_evidence_id)
        samples = tuple(self.samples)
        if type(self.context) is not VesselFailureContext or len(samples) < 2:
            raise ValueError(
                "A finite history needs explicit context and at least two loading samples"
            )
        if any(type(s) is not VesselLoading for s in samples):
            raise TypeError("Use actual typed loading samples")
        if any(b.time_s <= a.time_s for a, b in zip(samples[:-1], samples[1:], strict=True)):
            raise ValueError("Sample times must increase on the explicit operation clock")
        if len({s.phase_id for s in samples}) != 1:
            raise ValueError(
                "Split phase-label transitions into separately evidenced mechanical histories"
            )
        object.__setattr__(self, "samples", samples)

    def at(self, time_s):
        time = finite(time_s, "mechanical reconstruction time")
        if not self.samples[0].time_s <= time <= self.samples[-1].time_s:
            raise ValueError("No history extrapolation outside finite support")
        for sample in self.samples:
            if time == sample.time_s:
                return sample
        for left, right in zip(self.samples[:-1], self.samples[1:], strict=True):
            if left.time_s < time < right.time_s:
                weight = (time - left.time_s) / (right.time_s - left.time_s)
                values = [
                    a + weight * (b - a)
                    for a, b in (
                        (left.internal_pressure_pa_absolute, right.internal_pressure_pa_absolute),
                        (left.external_pressure_pa_absolute, right.external_pressure_pa_absolute),
                        (left.wall_temperature_k, right.wall_temperature_k),
                    )
                ]
                return VesselLoading(
                    time, *values, left.phase_id, reconstruction_parents=(left, right)
                )
        raise ValueError("Finite mechanical reconstruction interval was not found")


@dataclass(frozen=True, slots=True)
class HelprAxialFlaw:
    outer_diameter_m: float
    wall_thickness_m: float
    flaw_depth_m: float
    flaw_length_m: float
    location_factor: float
    geometry_id: str
    defect_id: str
    evidence_id: str

    def __post_init__(self):
        for name in (
            "outer_diameter_m",
            "wall_thickness_m",
            "flaw_depth_m",
            "flaw_length_m",
            "location_factor",
        ):
            finite(getattr(self, name), name, positive=True)
        _ids(self.geometry_id, self.defect_id, self.evidence_id)
        if not self.wall_thickness_m < self.outer_diameter_m / 2:
            raise ValueError("A cylindrical shell must have positive inner radius")
        ratio = (self.outer_diameter_m / 2 - self.wall_thickness_m) / self.wall_thickness_m
        if not 5 <= ratio <= 20 or self.flaw_depth_m / self.wall_thickness_m > 0.8:
            raise ValueError("Respect native Anderson bounds: 5<=Ri/t<=20 and 0<a/t<=0.8")
        if self.flaw_depth_m > self.flaw_length_m / 2:
            raise ValueError("This declared elliptical-flaw level requires a/c<=1")


@dataclass(frozen=True, slots=True)
class VesselMaterialPoint:
    yield_strength_pa: float
    fracture_resistance_pa_sqrt_m: float
    maximum_load_ratio: float
    evidence_id: str

    def __post_init__(self):
        for name in ("yield_strength_pa", "fracture_resistance_pa_sqrt_m", "maximum_load_ratio"):
            finite(getattr(self, name), name, positive=True)
        _ids(self.evidence_id)


@dataclass(frozen=True, slots=True)
class VesselMaterialLaw:
    material_id: str
    law_id: str
    evidence_id: str
    wall_temperature_k: tuple[float, float]
    internal_pressure_pa_absolute: tuple[float, float]
    hydrogen_mole_fraction: tuple[float, float]
    response: Callable[[VesselLoading, VesselFailureContext], VesselMaterialPoint]
    origin: Origin

    def __post_init__(self):
        _ids(self.material_id, self.law_id, self.evidence_id)
        for name in (
            "wall_temperature_k",
            "internal_pressure_pa_absolute",
            "hydrogen_mole_fraction",
        ):
            object.__setattr__(
                self,
                name,
                _bounds(getattr(self, name), name, positive=name != "hydrogen_mole_fraction"),
            )
        if self.hydrogen_mole_fraction[1] > 1 or not callable(self.response):
            raise ValueError(
                "Supply a material law and an explicit service-fraction domain within [0,1]"
            )
        object.__setattr__(self, "origin", _origin(self.origin))

    def evaluate(self, loading, context):
        for value, bounds in (
            (loading.wall_temperature_k, self.wall_temperature_k),
            (loading.internal_pressure_pa_absolute, self.internal_pressure_pa_absolute),
            (context.hydrogen_mole_fraction, self.hydrogen_mole_fraction),
        ):
            if not bounds[0] <= value <= bounds[1]:
                raise ValueError(
                    "Loading is outside explicitly supplied material thermal/H2/pressure qualification"
                )
        raw = self.response(loading, context)
        if type(raw) is not VesselMaterialPoint:
            raise TypeError("Material law must return an actual finite SI VesselMaterialPoint")
        VesselMaterialPoint(**{f.name: getattr(raw, f.name) for f in fields(raw)})
        return raw


@dataclass(frozen=True, slots=True)
class _MechanicalPressureLoad:
    """Native stress-interface adapter only: static differential pressure in MPa.

    It deliberately is not HELPR's fugacity EnvironmentSpecification. Both native
    accessors give the same instantaneous static load; no fatigue cycle is implied.
    """

    pressure_mpa: float

    def _get_max_pressure(self, _index):
        return self.pressure_mpa

    def _get_min_pressure(self, _index):
        return self.pressure_mpa


@dataclass(frozen=True, slots=True)
class NativeVesselObjects:
    pipe: object
    material: object
    defect: object
    pressure_load: object
    stress: object
    failure_assessment: object
    construction_warnings: tuple
    definition_sha256: str


@dataclass(frozen=True, slots=True)
class VesselFailureEvaluation:
    loading: VesselLoading
    material_point: VesselMaterialPoint
    native: NativeVesselObjects
    raw_stress_intensity: object
    raw_reference_stress: object
    raw_ratios: object
    raw_fad_limit: object | None
    k_max_pa_sqrt_m: float
    reference_stress_pa: float
    toughness_ratio: float
    load_ratio: float
    fad_limit: float | None
    margin: float
    failed: bool
    governing_criterion: str
    purpose: str


@dataclass(frozen=True, slots=True)
class VesselFailurePrediction:
    history: VesselFailureHistory
    geometry: HelprAxialFlaw
    material_law: VesselMaterialLaw
    criterion: str
    criterion_evidence_id: str
    evaluations: tuple[VesselFailureEvaluation, ...]
    initiation: VesselFailureEvaluation | None
    resolved_bracket_s: tuple[float, float] | None
    native_root_result: object | None
    maximum_reconstruction_step_s: float
    root_time_tolerance_s: float
    maximum_evaluations: int
    source_sha256: Mapping
    input_sha256: str
    termination: str
    software_status: str = "implemented_unverified"
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_FAILURE_REPORT_ISSUERS:
            raise ValueError("Vessel predictions are issued only by the native HELPR owner")
        _PENDING_FAILURE_REPORT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "source_sha256", MappingProxyType(dict(self.source_sha256)))
        object.__setattr__(self, "_seal", _failure_report_digest(self))

    def require_current(self):
        if _failure_report_digest(self) != self._seal:
            raise ValueError("Vessel prediction changed after native issuance")
        return self


@dataclass(frozen=True, slots=True)
class VesselPressureCapacity:
    context: VesselFailureContext
    original_loading: VesselLoading
    geometry: HelprAxialFlaw
    material_law: VesselMaterialLaw
    criterion: str
    criterion_evidence_id: str
    continuation_evidence_id: str
    evaluations: tuple[VesselFailureEvaluation, ...]
    capacity: VesselFailureEvaluation
    native_root_result: object
    bracket_pressure_pa_absolute: tuple[float, float]
    root_pressure_tolerance_pa: float
    source_sha256: Mapping
    software_status: str = "implemented_unverified"
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_FAILURE_REPORT_ISSUERS:
            raise ValueError("Vessel capacity reports are issued only by the native HELPR owner")
        _PENDING_FAILURE_REPORT_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "source_sha256", MappingProxyType(dict(self.source_sha256)))
        object.__setattr__(self, "_seal", _failure_report_digest(self))

    def require_current(self):
        if _failure_report_digest(self) != self._seal:
            raise ValueError("Vessel capacity report changed after native issuance")
        return self


class VesselFailureError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        source,
        evaluations=(),
        native_objects=(),
        last_loading=None,
        pending=None,
        native_root_result=None,
    ):
        super().__init__(message)
        self.source = source
        self.evaluations = tuple(evaluations)
        self.native_objects = tuple(native_objects)
        self.last_loading = last_loading
        self.pending = MappingProxyType(dict(pending or {}))
        self.native_root_result = native_root_result


class HelprVesselFailure:
    """Actual native static mechanics plus caller-evidenced thermal material law.

    ``native_2016_fad`` calls HELPR's existing curve without copying its equation.
    ``separate_yield_and_toughness`` uses the actual native dimensionless ratios.
    Both retain caller-supplied load-ratio cutoff; neither claims full API579 FFS.
    """

    def __init__(
        self,
        geometry: HelprAxialFlaw,
        material_law: VesselMaterialLaw,
        *,
        criterion: str,
        criterion_evidence_id: str,
        native_stress_factory=None,
    ):
        if type(geometry) is not HelprAxialFlaw or type(material_law) is not VesselMaterialLaw:
            raise TypeError(
                "Explicit actual geometry and qualified material-law objects are required"
            )
        HelprAxialFlaw(**{f.name: getattr(geometry, f.name) for f in fields(geometry)})
        VesselMaterialLaw(**{f.name: getattr(material_law, f.name) for f in fields(material_law)})
        if criterion not in {"native_2016_fad", "separate_yield_and_toughness"}:
            raise ValueError("Select the explicit static mechanical initiation criterion")
        _ids(criterion_evidence_id)
        modules = {name: importlib.import_module(name) for name in _SOURCES}
        if metadata.version("helpr") != HELPR_VERSION:
            raise ValueError("Select the exact inspected optional HELPR2.1.0 provider")
        self.geometry, self.material_law = geometry, material_law
        self.native_revision = HELPR_REVISION
        self.criterion, self.criterion_evidence_id = criterion, criterion_evidence_id
        self.modules = modules
        self.source_paths = {
            name: Path(inspect.getfile(module)) for name, module in modules.items()
        }
        self.pipe_class = modules["helpr.physics.pipe"].Pipe
        self.material_class = modules["helpr.physics.material"].MaterialSpecification
        self.defect_class = modules["helpr.physics.crack_initiation"].DefectSpecification
        self.stress_class = modules["helpr.physics.stress_state"].InternalAxialHoopStress
        self.failure_class = modules["helpr.physics.fracture"].FailureAssessment
        self.fad_function = modules["helpr.utilities.plots"].failure_assessment_diagram_equation
        self.stress_factory = native_stress_factory or self.stress_class
        self.source_sha256 = MappingProxyType(dict(_SOURCES))
        self._native_classes = (
            self.pipe_class,
            self.material_class,
            self.defect_class,
            self.stress_class,
            self.failure_class,
        )
        self._method_identity = _digest(tuple(_methods(cls) for cls in self._native_classes))
        self._input_identity = self._configuration()
        self.require_sources()

    def _configuration(self):
        return _digest(
            (
                self.geometry,
                self.material_law,
                self.criterion,
                self.criterion_evidence_id,
                self.stress_factory,
            )
        )

    def _guard(self):
        if self._configuration() != self._input_identity:
            raise ValueError("Geometry, material law, criterion or native factory binding changed")
        if _digest(tuple(_methods(cls) for cls in self._native_classes)) != self._method_identity:
            raise ValueError("Actual native mechanical method bindings changed")
        if (
            self.modules["helpr.utilities.plots"].failure_assessment_diagram_equation
            is not self.fad_function
        ):
            raise ValueError("Actual native FAD function identity changed")

    def require_sources(self):
        self._guard()
        if {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in self.source_paths.items()
        } != _SOURCES:
            raise ValueError("The inspected native mechanical source bytes changed")

    @staticmethod
    def _definition(objects):
        pipe, material, defect, load, stress, failure = objects
        return _digest(
            (
                vars(pipe),
                vars(material),
                vars(defect),
                load,
                {key: value for key, value in vars(stress).items() if key != "cycle_index"},
                vars(failure),
                tuple(id(value) for value in (pipe, material, defect, load)),
            )
        )

    def _check_native(self, owner):
        objects = (
            owner.pipe,
            owner.material,
            owner.defect,
            owner.pressure_load,
            owner.stress,
            owner.failure_assessment,
        )
        if self._definition(objects) != owner.definition_sha256:
            raise ValueError("Retained native geometry/material/load/reference definitions changed")

    def _evaluate(self, loading, context, purpose, owners, pending):
        self._guard()
        if type(loading) is not VesselLoading or type(context) is not VesselFailureContext:
            raise TypeError("Actual SI loading and context records are required")
        VesselLoading(**{f.name: getattr(loading, f.name) for f in fields(loading)})
        VesselFailureContext(**{f.name: getattr(context, f.name) for f in fields(context)})
        before = _digest((loading, context))
        point = self.material_law.evaluate(loading, context)
        pending["material_point"] = point
        self._guard()
        if _digest((loading, context)) != before:
            raise ValueError("Material callback changed the original loading/context")
        g = self.geometry
        pipe = self.pipe_class(g.outer_diameter_m, g.wall_thickness_m)
        pending["pipe"] = pipe
        material = self.material_class(
            point.yield_strength_pa / 1e6, point.fracture_resistance_pa_sqrt_m / 1e6
        )
        pending["material"] = material
        defect = self.defect_class(
            g.flaw_depth_m / g.wall_thickness_m * 100,
            g.flaw_length_m,
            surface="inside",
            location_factor=g.location_factor,
        )
        pending["defect"] = defect
        load = _MechanicalPressureLoad(loading.pressure_difference_pa / 1e6)
        pending["pressure_load"] = load
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            stress = self.stress_factory(
                pipe, load, material, defect, stress_intensity_method="anderson"
            )
        pending["stress"] = stress
        if type(stress) is not self.stress_class or any(
            callable(getattr(type(stress), name, None)) for name in vars(stress)
        ):
            raise TypeError("Factory must return an actual unmodified native stress object")
        if (
            stress.pipe_specification is not pipe
            or stress.environment_specification is not load
            or stress.material_specification is not material
            or stress.defect_specification is not defect
            or stress.stress_intensity_method != "anderson"
        ):
            raise ValueError("Native stress factory changed physical object/reference bindings")
        failure = self.failure_class(
            point.fracture_resistance_pa_sqrt_m / 1e6, point.yield_strength_pa / 1e6, "simple"
        )
        pending["failure_assessment"] = failure
        objects = (pipe, material, defect, load, stress, failure)
        owner = NativeVesselObjects(*objects, tuple(captured), self._definition(objects))
        owners.append(owner)
        raw_k = stress.calc_stress_intensity_factor(g.flaw_depth_m, g.flaw_length_m, cycle_index=0)
        pending["raw_stress_intensity"] = raw_k
        if len(raw_k) != 4:
            raise ValueError("Actual native SIF output shape changed")
        for item in raw_k:
            finite(item, "actual native SIF/shape-factor output")
        # Matches the actual native 'simple' FAD path: uncracked hoop reference.
        raw_ref = stress.calc_stress_solution(crack_depth=0.0)
        pending["raw_reference_stress"] = raw_ref
        k_max = finite(raw_k[0], "actual native Kmax")
        reference = finite(raw_ref, "actual native uncracked hoop stress")
        if k_max < 0 or reference < 0:
            raise ValueError("Negative native tensile mechanical result is not repaired")
        raw_ratios = failure.assess_failure_state(k_max, reference)
        pending["raw_ratios"] = raw_ratios
        kr, lr = (finite(v, "actual native failure ratio") for v in raw_ratios)
        if kr < 0 or lr < 0:
            raise ValueError("Native mechanical ratios must be nonnegative")
        load_margin = 1 - lr / point.maximum_load_ratio
        raw_fad, fad_limit = None, None
        if self.criterion == "native_2016_fad" and lr <= point.maximum_load_ratio:
            raw_fad = self.fad_function(lr)
            pending["raw_fad_limit"] = raw_fad
            fad_limit = finite(raw_fad, "native FAD ordinate", positive=True)
            margin = min(load_margin, fad_limit - kr)
            governing = (
                "native_fad_curve"
                if fad_limit - kr <= load_margin
                else "supplied_load_ratio_cutoff"
            )
        elif self.criterion == "separate_yield_and_toughness":
            margin = min(load_margin, 1 - kr)
            governing = (
                "native_toughness_ratio" if 1 - kr <= load_margin else "supplied_load_ratio_cutoff"
            )
        else:
            margin, governing = (
                load_margin,
                "supplied_load_ratio_cutoff;native_curve_not_extrapolated",
            )
        finite(margin, "mechanical initiation margin")
        self._guard()
        self._check_native(owner)
        result = VesselFailureEvaluation(
            loading,
            point,
            owner,
            raw_k,
            raw_ref,
            raw_ratios,
            raw_fad,
            k_max * 1e6,
            reference * 1e6,
            kr,
            lr,
            fad_limit,
            margin,
            margin <= 0,
            governing,
            purpose,
        )
        pending.clear()
        return result

    def evaluate(self, loading, context):
        owners, pending = [], {}
        try:
            self.require_sources()
            result = self._evaluate(loading, context, "point_evaluation", owners, pending)
            self.require_sources()
            return result
        except Exception as cause:
            raise VesselFailureError(
                f"Native vessel mechanics failed: {cause}",
                source=context,
                native_objects=owners,
                last_loading=loading,
                pending=pending,
            ) from cause

    def predict(
        self,
        history: VesselFailureHistory,
        *,
        maximum_reconstruction_step_s: float,
        root_time_tolerance_s: float = 1e-7,
        maximum_evaluations: int = 10000,
    ):
        evaluations, owners, pending = [], [], {}
        last, raw_root = None, None
        try:
            if type(history) is not VesselFailureHistory:
                raise TypeError("Use an actual finite explicitly reconstructed vessel history")
            VesselFailureHistory(**{f.name: getattr(history, f.name) for f in fields(history)})
            width = finite(
                maximum_reconstruction_step_s, "mechanical reconstruction step", positive=True
            )
            tolerance = finite(root_time_tolerance_s, "root time tolerance", positive=True)
            if type(maximum_evaluations) is not int or maximum_evaluations < 2:
                raise ValueError("Declare a finite actual mechanical evaluation budget")
            fingerprint = _digest(history)
            _require_native_history(history)
            # Snapshot physical coordinates before callbacks. Whole original
            # native evidence is checked again at return, rather than hashed
            # at every mechanical query with quadratic whole-trace work.
            physical_history = replace(
                history,
                context=replace(history.context, fluid_basis=replace(history.context.fluid_basis)),
                samples=tuple(replace(sample) for sample in history.samples),
            )
            self.require_sources()

            def evaluate(time, purpose):
                nonlocal last
                if len(evaluations) >= maximum_evaluations:
                    raise ValueError("Declared actual mechanical call budget reached")
                last = physical_history.at(time)
                value = self._evaluate(last, physical_history.context, purpose, owners, pending)
                evaluations.append(value)
                return value

            previous = evaluate(physical_history.samples[0].time_s, "first_resolved_history_state")
            initiation = previous if previous.failed else None
            bracket = (
                (previous.loading.time_s, previous.loading.time_s) if previous.failed else None
            )
            if initiation is None:
                for left, right in zip(
                    physical_history.samples[:-1], physical_history.samples[1:], strict=True
                ):
                    count = math.ceil((right.time_s - left.time_s) / width)
                    if count > maximum_evaluations - len(evaluations):
                        raise ValueError(
                            "Reconstruction request exceeds declared evaluation budget"
                        )
                    for index in range(1, count + 1):
                        time = (
                            right.time_s
                            if index == count
                            else left.time_s + (right.time_s - left.time_s) * index / count
                        )
                        current = evaluate(time, "resolved_reconstructed_history_state")
                        if current.failed:
                            bracket = (previous.loading.time_s, current.loading.time_s)
                            from scipy.optimize import root_scalar

                            raw_root = root_scalar(
                                lambda t: evaluate(t, "native_margin_time_root").margin,
                                bracket=bracket,
                                method="brentq",
                                xtol=tolerance,
                            )
                            if not raw_root.converged:
                                raise ValueError("Actual native-margin time root did not converge")
                            initiation = evaluate(
                                float(raw_root.root), "localized_reconstructed_initiation"
                            )
                            break
                        previous = current
                    if initiation is not None:
                        break
            if _digest(history) != fingerprint:
                raise ValueError("Source/history identities changed by the last callback")
            _require_native_history(history)
            for owner in owners:
                self._check_native(owner)
            self.require_sources()
            termination = (
                "first_resolved_initiation"
                if initiation is not None
                else "no_resolved_initiation_within_support"
            )
            return _issue_failure_report(VesselFailurePrediction,
                history,
                self.geometry,
                self.material_law,
                self.criterion,
                self.criterion_evidence_id,
                tuple(evaluations),
                initiation,
                bracket,
                raw_root,
                width,
                tolerance,
                maximum_evaluations,
                self.source_sha256,
                fingerprint,
                termination,
            )
        except Exception as cause:
            raise VesselFailureError(
                f"Unverified vessel history prediction failed: {cause}",
                source=history,
                evaluations=evaluations,
                native_objects=owners,
                last_loading=last,
                pending=pending,
                native_root_result=raw_root,
            ) from cause

    def pressure_capacity(
        self,
        loading: VesselLoading,
        context: VesselFailureContext,
        *,
        bracket_pressure_pa_absolute: tuple[float, float],
        continuation_evidence_id: str,
        root_pressure_tolerance_pa: float = 0.01,
    ):
        """Fixed wall-T counterfactual pressure root, not a fluid/EOS continuation."""
        evaluations, owners, pending = [], [], {}
        last, raw_root = None, None
        try:
            _ids(continuation_evidence_id)
            low, high = _bounds(
                bracket_pressure_pa_absolute, "capacity absolute-pressure bracket", positive=True
            )
            tolerance = finite(root_pressure_tolerance_pa, "capacity root tolerance", positive=True)
            fingerprint = _digest((loading, context))
            self.require_sources()

            def evaluate(pressure):
                nonlocal last
                if _digest((loading, context)) != fingerprint:
                    raise ValueError("Original counterfactual loading/context binding changed")
                last = replace(
                    loading,
                    internal_pressure_pa_absolute=float(pressure),
                    native_snapshot=None,
                    native_state=None,
                    native_fluid=None,
                    reconstruction_parents=(loading,),
                )
                value = self._evaluate(
                    last, context, "fixed_wall_temperature_pressure_continuation", owners, pending
                )
                evaluations.append(value)
                return value

            left, right = evaluate(low), evaluate(high)
            if left.margin <= 0 or right.margin >= 0:
                raise ValueError(
                    "Caller bracket must resolve an admitted safe-to-failed mechanical boundary"
                )
            from scipy.optimize import root_scalar

            raw_root = root_scalar(
                lambda p: evaluate(p).margin, bracket=(low, high), method="brentq", xtol=tolerance
            )
            if not raw_root.converged:
                raise ValueError("Actual native-margin pressure root did not converge")
            capacity = evaluate(float(raw_root.root))
            if _digest((loading, context)) != fingerprint:
                raise ValueError(
                    "Original counterfactual loading/context changed in final callback"
                )
            for owner in owners:
                self._check_native(owner)
            self.require_sources()
            return _issue_failure_report(VesselPressureCapacity,
                context,
                loading,
                self.geometry,
                self.material_law,
                self.criterion,
                self.criterion_evidence_id,
                continuation_evidence_id,
                tuple(evaluations),
                capacity,
                raw_root,
                (low, high),
                tolerance,
                self.source_sha256,
            )
        except Exception as cause:
            raise VesselFailureError(
                f"Unverified vessel capacity root failed: {cause}",
                source=loading,
                evaluations=evaluations,
                native_objects=owners,
                last_loading=last,
                pending=pending,
                native_root_result=raw_root,
            ) from cause


def history_from_cryo_compressed(
    trace,
    *,
    context: VesselFailureContext,
    external_pressure_pa_absolute: Callable[[float], float],
    reconstruction_evidence_id: str,
):
    """Use actual audited LH2DT fluid/wall outputs; never rerun a vessel ODE.

    The lumped wall is the declared mechanical region. It is not a hot-spot field.
    Native states are matched by identity to the original finite trace. Pressure
    is reread through the retained native tank and its existing property bridge.
    """
    from .cryo_compressed import CryoCompressedTrace
    from .lh2dt import from_lh2dt_state

    samples, last = [], None
    try:
        if type(trace) is not CryoCompressedTrace or type(context) is not VesselFailureContext:
            raise TypeError("Use the actual audited native finite-storage trace and typed context")
        if (
            trace.native_trace.clock_id != context.clock_id
            or trace.storage.native_tank is not trace.native_trace.native_tank
        ):
            raise ValueError("Native vessel/operation clock bindings differ")
        if context.source_id != trace.boundary.source_id or context.origin is Origin.MEASURED:
            raise ValueError(
                "Keep the actual thermal-boundary source identity and computed history role"
            )
        context.fluid_basis.require_compatible(trace.storage.properties.basis)
        if context.hydrogen_mole_fraction != 1.0:
            raise ValueError("This native pure-H2 storage trace cannot be relabeled a gas mixture")
        states = (
            trace.native_trace.initial_state,
            *(row.native_step.state for row in trace.native_trace.intervals),
        )
        times = tuple(float(t) for t in trace.native_trace.time_s)
        if len(states) != len(trace.points) or len(times) != len(states):
            raise ValueError("Actual native trace/output prefix lengths differ")
        trace.storage._require_configuration()
        for time, state, point in zip(times, states, trace.points, strict=True):
            last = point
            if point.native_state is not state or point.time_s != time:
                raise ValueError("Audited point is not the actual retained native state/time")
            raw = trace.storage.native_tank.thermo(state)
            fluid = from_lh2dt_state(raw, basis=context.fluid_basis)
            if fluid != point.fluid:
                raise ValueError(
                    "Cached fluid summary differs from the actual retained native state"
                )
            samples.append(
                VesselLoading(
                    time,
                    fluid.pressure_pa,
                    external_pressure_pa_absolute(time),
                    state.wall_temperature_K,
                    fluid.phase,
                    point,
                    state,
                    raw,
                )
            )
        trace.storage._require_configuration()
        return VesselFailureHistory(context, tuple(samples), reconstruction_evidence_id, trace)
    except Exception as cause:
        raise VesselFailureError(
            f"Native vessel-history binding failed: {cause}",
            source=trace,
            last_loading=last,
            pending={"bound_sample_prefix": tuple(samples)},
        ) from cause


def _require_native_history(history):
    """Rebind computed native-backed summaries, without rerunning a fluid ODE."""
    if history.native_trace is None:
        return
    # Finite hydride stores no wall temperature in its native state. Rebuild
    # the projection from the same accepted snapshots and the caller-mapped
    # wall samples retained on the HELPR history before using it.
    from ..storage.finite_hydride import FiniteHydrideTrace
    if type(history.native_trace) is FiniteHydrideTrace:
        from .finite_hydride_vessel_failure import history_from_finite_hydride

        trace = history.native_trace
        if len(history.samples) != len(trace.snapshots):
            raise ValueError("Finite-hydride-backed failure history lost accepted samples")
        mapped = history_from_finite_hydride(
            trace,
            context=history.context,
            wall_temperature_k=tuple(sample.wall_temperature_k for sample in history.samples),
            external_pressure_pa_absolute={
                sample.time_s: sample.external_pressure_pa_absolute
                for sample in history.samples
            }.__getitem__,
            shell_id=history.context.wall_region_id,
            wall_mapping_evidence_id=history.context.wall_temperature_evidence_id,
            geometry_mapping_evidence_id=history.context.geometry_binding_evidence_id,
            reconstruction_evidence_id=history.reconstruction_evidence_id,
        )
        for actual, accepted in zip(mapped.samples, history.samples, strict=True):
            if (actual.time_s != accepted.time_s
                    or actual.internal_pressure_pa_absolute != accepted.internal_pressure_pa_absolute
                    or actual.external_pressure_pa_absolute != accepted.external_pressure_pa_absolute
                    or actual.wall_temperature_k != accepted.wall_temperature_k
                    or actual.phase_id != accepted.phase_id
                    or actual.native_snapshot is not accepted.native_snapshot
                    or actual.native_state is not accepted.native_state
                    or actual.native_fluid is not accepted.native_fluid):
                raise ValueError("Finite-hydride history no longer matches its accepted source samples")
        return
    from .finite_separator import FiniteSeparatorTrace
    if type(history.native_trace) is FiniteSeparatorTrace:
        from .finite_separator_vessel_failure import history_from_finite_separator

        trace = history.native_trace
        if len(history.samples) != len(trace.points) or not history.samples:
            raise ValueError("Finite-separator-backed failure history lost accepted source samples")
        parents = history.samples[0].reconstruction_parents
        if (len(parents) != 7 or parents[0] is not trace
                or any(sample.reconstruction_parents != parents for sample in history.samples)):
            raise ValueError("Finite-separator failure history lost its pressure/geometry evidence mapping")
        mapped = history_from_finite_separator(
            trace, context=history.context,
            wall_temperature_k=tuple(sample.wall_temperature_k for sample in history.samples),
            external_pressure_pa_absolute={
                sample.time_s: sample.external_pressure_pa_absolute
                for sample in history.samples
            }.__getitem__,
            shell_id=parents[1], wall_mapping_evidence_id=parents[2],
            geometry_mapping_evidence_id=parents[3], pressure_basis_id=parents[4],
            pressure_basis_evidence_id=parents[5], external_pressure_evidence_id=parents[6],
            reconstruction_evidence_id=history.reconstruction_evidence_id,
        )
        for actual, accepted in zip(mapped.samples, history.samples, strict=True):
            if (actual.time_s != accepted.time_s
                    or actual.internal_pressure_pa_absolute != accepted.internal_pressure_pa_absolute
                    or actual.external_pressure_pa_absolute != accepted.external_pressure_pa_absolute
                    or actual.wall_temperature_k != accepted.wall_temperature_k
                    or actual.phase_id != accepted.phase_id
                    or actual.native_snapshot is not accepted.native_snapshot
                    or actual.native_state is not accepted.native_state
                    or actual.native_fluid is not accepted.native_fluid
                    or actual.reconstruction_parents != accepted.reconstruction_parents):
                raise ValueError("Finite-separator history no longer matches its accepted source samples")
        return
    external = {sample.time_s: sample.external_pressure_pa_absolute for sample in history.samples}
    actual = history_from_cryo_compressed(
        history.native_trace,
        context=history.context,
        external_pressure_pa_absolute=external.__getitem__,
        reconstruction_evidence_id=history.reconstruction_evidence_id,
    )
    if len(actual.samples) != len(history.samples):
        raise ValueError("A native-backed history must retain the complete original sampled prefix")
    for supplied, checked in zip(history.samples, actual.samples, strict=True):
        if (
            supplied.native_snapshot is not checked.native_snapshot
            or supplied.native_state is not checked.native_state
            or supplied.time_s != checked.time_s
            or supplied.internal_pressure_pa_absolute != checked.internal_pressure_pa_absolute
            or supplied.wall_temperature_k != checked.wall_temperature_k
            or supplied.phase_id != checked.phase_id
            or supplied.native_fluid != checked.native_fluid
            or supplied.reconstruction_parents
        ):
            raise ValueError(
                "Computed mechanical history differs from its actual native sampled evidence"
            )
