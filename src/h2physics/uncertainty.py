"""Explicit independent-input propagation using native SciPy QMC/Sobol analysis.

The statistical engine owns sampling and variance-based indices. Callbacks own
the physical model. Failed cases retain their actual parameters and prefix;
there is no rejection sampling, replacement response or conditional renormalization.
"""

from __future__ import annotations

import hashlib
import json
import math
import marshal
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import FunctionType, MappingProxyType, ModuleType
from typing import Any

import numpy as np

from .core import Origin, finite, immutable_array
from .observations import Variable


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must identify its source, assumption or revision")


def _integer(value: int, name: str, lower: int, upper: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    if not lower <= int(value) <= upper:
        raise ValueError(f"{name} must be in [{lower}, {upper}]")
    return int(value)


def _array(value: Any) -> np.ndarray:
    return immutable_array(value, dtype=float, name="uncertainty array")


_PENDING_PROPAGATION_ISSUERS: set[object] = set()
_PENDING_SOBOL_ISSUERS: set[object] = set()
_PENDING_JOINT_PROPAGATION_ISSUERS: set[object] = set()


def _issue_propagation_result(design, model, evaluations, values):
    token = object()
    _PENDING_PROPAGATION_ISSUERS.add(token)
    try:
        return PropagationResult(design, model, evaluations, values, token)
    except Exception:
        _PENDING_PROPAGATION_ISSUERS.discard(token)
        raise


def _issue_sobol_sensitivity(**values):
    token = object()
    _PENDING_SOBOL_ISSUERS.add(token)
    try:
        return SobolSensitivity(**values, _issuer_token=token)
    except Exception:
        _PENDING_SOBOL_ISSUERS.discard(token)
        raise


def _issue_joint_propagation_result(**values):
    token = object()
    _PENDING_JOINT_PROPAGATION_ISSUERS.add(token)
    try:
        return JointPropagationResult(**values, _issuer_token=token)
    except Exception:
        _PENDING_JOINT_PROPAGATION_ISSUERS.discard(token)
        raise


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return _canonical(value.item())
    if isinstance(value, (tuple, list, np.ndarray)):
        return [_canonical(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value).hex()
    if isinstance(value, (int, np.integer)):
        return int(value)
    if value is None or isinstance(value, (str, bool)):
        return value
    raise ValueError("Native distribution parameters must have reproducible scalar/array meanings")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True).encode()).hexdigest()


def _native():
    import scipy
    from scipy import stats

    # Core users may retain SciPy1.14; this reproducible Generator interface is
    # separately admitted rather than silently changing its RNG implementation.
    version = tuple(int(part) for part in scipy.__version__.split(".")[:2])
    if version < (1, 15):
        raise ValueError("This native uncertainty level requires SciPy>=1.15")
    return scipy, stats


def _immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _immutable(v) for k, v in value.items()})
    if isinstance(value, np.ndarray) and value.ndim == 0:
        return _immutable(value.item())
    if isinstance(value, (list, tuple, np.ndarray)):
        return tuple(_immutable(v) for v in value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _callable_definition_sha256(function: Any) -> str:
    """Bind a Python sampler to bytecode and simple captured/global definitions."""
    if not isinstance(function, FunctionType):
        raise TypeError("A joint sampler must be a Python function with inspectable code")

    def dependency(value):
        if isinstance(value, ModuleType):
            return ("module", value.__name__, getattr(value, "__version__", None))
        if isinstance(value, FunctionType):
            return (
                "function",
                value.__module__,
                value.__qualname__,
                hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
                _canonical(value.__defaults__),
            )
        if isinstance(value, type):
            return ("type", value.__module__, value.__qualname__)
        return ("value", _canonical(value))

    closure = () if function.__closure__ is None else tuple(
        dependency(cell.cell_contents) for cell in function.__closure__
    )
    globals_used = tuple(
        (name, dependency(function.__globals__[name]))
        for name in sorted(set(function.__code__.co_names))
        if name in function.__globals__ and name != function.__name__
    )
    payload = (
        hashlib.sha256(marshal.dumps(function.__code__)).hexdigest(),
        _canonical(function.__defaults__),
        _canonical(function.__kwdefaults__),
        closure,
        globals_used,
    )
    return hashlib.sha256(json.dumps(_canonical(payload), sort_keys=True).encode()).hexdigest()


def _distribution_definition(distribution: Any):
    scipy, stats = _native()
    if not isinstance(getattr(distribution, "dist", None), stats.rv_continuous):
        raise ValueError("Supply a separately frozen native SciPy continuous distribution")
    if not callable(getattr(distribution, "ppf", None)):
        raise ValueError("A native inverse distribution is required")
    support = np.asarray(distribution.support(), dtype=float)
    if support.shape != (2,) or np.any(np.isnan(support)) or support[0] >= support[1]:
        raise ValueError("Native distribution needs one valid scalar continuous support")
    return _immutable(
        {
            "scipy_version": scipy.__version__,
            "native_class": type(distribution.dist).__module__
            + "."
            + type(distribution.dist).__qualname__,
            "name": distribution.dist.name,
            "args": distribution.args,
            "keywords": distribution.kwds,
            "support": support,
        }
    )


def _distribution_id(distribution: Any) -> str:
    return _digest(_distribution_definition(distribution))


@dataclass(frozen=True, slots=True)
class ParameterDistribution:
    variable: Variable
    distribution: Any
    distribution_id: str
    source_id: str
    origin: Origin
    admitted_minimum: float
    admitted_maximum: float
    native_definition_sha256: str = field(init=False)
    native_definition_snapshot: Mapping[str, Any] = field(init=False)

    def __post_init__(self):
        if not isinstance(self.variable, Variable):
            raise ValueError("A parameter requires explicit variable quantity/unit/basis")
        for name in ("distribution_id", "source_id"):
            _text(getattr(self, name), name)
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("A distribution's origin must be resolved")
        lower = finite(self.admitted_minimum, "admitted minimum")
        upper = finite(self.admitted_maximum, "admitted maximum")
        if lower >= upper:
            raise ValueError("Declare increasing, finite physical admission bounds")
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "admitted_minimum", lower)
        object.__setattr__(self, "admitted_maximum", upper)
        definition = _distribution_definition(self.distribution)
        object.__setattr__(self, "native_definition_snapshot", definition)
        object.__setattr__(self, "native_definition_sha256", _digest(definition))

    def require_current(self):
        if _distribution_id(self.distribution) != self.native_definition_sha256:
            raise ValueError(f"Native distribution definition changed: {self.variable.name}")

    def admit(self, values):
        values = np.asarray(values, dtype=float)
        if (
            not np.all(np.isfinite(values))
            or np.any(values < self.admitted_minimum)
            or np.any(values > self.admitted_maximum)
        ):
            raise ValueError(f"Parameter {self.variable.name} outside declared physical admission")


@dataclass(frozen=True, slots=True)
class IndependentParameterSpace:
    parameters: tuple[ParameterDistribution, ...]
    independence_evidence_id: str
    space_id: str

    def __post_init__(self):
        parameters = tuple(self.parameters)
        if not parameters or not all(isinstance(p, ParameterDistribution) for p in parameters):
            raise ValueError("A space needs explicit parameter distributions")
        if len({p.variable.name for p in parameters}) != len(parameters):
            raise ValueError("Parameter names must be unique")
        _text(self.independence_evidence_id, "independence evidence")
        _text(self.space_id, "space identity")
        object.__setattr__(self, "parameters", parameters)

    def require_current(self):
        for parameter in self.parameters:
            parameter.require_current()

    @property
    def content_sha256(self):
        self.require_current()
        return _digest(
            (
                self.space_id,
                self.independence_evidence_id,
                tuple(
                    (
                        (
                            p.variable.name,
                            p.variable.quantity,
                            p.variable.unit,
                            p.variable.basis_id,
                        ),
                        p.distribution_id,
                        p.source_id,
                        p.origin,
                        p.admitted_minimum,
                        p.admitted_maximum,
                        p.native_definition_sha256,
                    )
                    for p in self.parameters
                ),
            )
        )


@dataclass(frozen=True, slots=True)
class UncertaintyEvidence:
    model_id: str
    model_revision_id: str
    deterministic_reset_evidence_id: str
    statistical_scope_id: str
    origin: Origin

    def __post_init__(self):
        for name in (
            "model_id",
            "model_revision_id",
            "deterministic_reset_evidence_id",
            "statistical_scope_id",
        ):
            _text(getattr(self, name), name)
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("Uncertainty evidence needs a resolved origin")
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class ModelOutput:
    values: Mapping[str, float]
    raw: Any = None


@dataclass(frozen=True, slots=True)
class UncertainModel:
    callback: Callable[[Mapping[str, float]], Mapping[str, float] | ModelOutput]
    outputs: tuple[Variable, ...]
    evidence: UncertaintyEvidence

    def __post_init__(self):
        outputs = tuple(self.outputs)
        if not callable(self.callback) or not isinstance(self.evidence, UncertaintyEvidence):
            raise ValueError("Supply a callable model and its explicit evidence")
        if (
            not outputs
            or not all(isinstance(v, Variable) for v in outputs)
            or len({v.name for v in outputs}) != len(outputs)
        ):
            raise ValueError("Outputs need unique, explicit variable meanings")
        object.__setattr__(self, "outputs", outputs)


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    index: int
    batch_index: int
    parameters: Mapping[str, float]
    outputs: Mapping[str, float]
    raw: Any


@dataclass(frozen=True, slots=True)
class JointParameterDomain:
    """A named physical output and admissible range of a caller-owned joint sampler."""

    variable: Variable
    source_id: str
    origin: Origin
    admitted_minimum: float
    admitted_maximum: float

    def __post_init__(self):
        if not isinstance(self.variable, Variable):
            raise TypeError("A joint parameter needs an explicit quantity, unit and basis")
        _text(self.source_id, "joint parameter source")
        origin = Origin(self.origin)
        if origin == Origin.UNRESOLVED:
            raise ValueError("A joint parameter's origin must be resolved")
        lower = finite(self.admitted_minimum, "joint parameter minimum")
        upper = finite(self.admitted_maximum, "joint parameter maximum")
        if lower >= upper:
            raise ValueError("Declare increasing, finite joint-parameter bounds")
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "admitted_minimum", lower)
        object.__setattr__(self, "admitted_maximum", upper)

    def admit(self, value: float) -> None:
        sample = finite(value, self.variable.name)
        if not self.admitted_minimum <= sample <= self.admitted_maximum:
            raise ValueError(f"Joint parameter {self.variable.name} outside declared physical bounds")


@dataclass(frozen=True, slots=True)
class JointScenarioSpace:
    """Caller-owned joint law; dependence is never inferred from marginal inputs."""

    parameters: tuple[JointParameterDomain, ...]
    sampler: Callable[[np.random.Generator, int], Any]
    sampler_id: str
    sampler_revision_id: str
    dependence_evidence_id: str
    source_id: str
    space_id: str
    sampler_definition_sha256: str = field(init=False)

    def __post_init__(self):
        parameters = tuple(self.parameters)
        if not parameters or not all(type(p) is JointParameterDomain for p in parameters):
            raise ValueError("A joint scenario space needs explicit parameter domains")
        if len({p.variable.name for p in parameters}) != len(parameters):
            raise ValueError("Joint parameter names must be unique")
        for name in ("sampler_id", "sampler_revision_id", "dependence_evidence_id",
                     "source_id", "space_id"):
            _text(getattr(self, name), name)
        digest = _callable_definition_sha256(self.sampler)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "sampler_definition_sha256", digest)

    def require_current(self):
        if _callable_definition_sha256(self.sampler) != self.sampler_definition_sha256:
            raise ValueError("Joint sampler code or captured dependencies changed")

    @property
    def content_sha256(self):
        self.require_current()
        return _digest((
            self.space_id,
            self.sampler_id,
            self.sampler_revision_id,
            self.sampler_definition_sha256,
            self.dependence_evidence_id,
            self.source_id,
            tuple((p.variable.name, p.variable.quantity, p.variable.unit,
                   p.variable.basis_id, p.source_id, p.origin,
                   p.admitted_minimum, p.admitted_maximum) for p in self.parameters),
        ))


@dataclass(frozen=True, slots=True)
class JointScenarioDesign:
    """Seeded caller-sampled scenarios with complete, retained joint inputs."""

    space: JointScenarioSpace
    space_sha256: str
    values: np.ndarray
    seed: int
    numpy_version: str
    content_sha256: str = field(init=False)
    scenario_ids: tuple[str, ...] = field(init=False)

    def __post_init__(self):
        values = _array(self.values)
        seed = _integer(self.seed, "joint sampler seed", 0, 2**63 - 1)
        if (values.ndim != 2 or not len(values)
                or values.shape[1] != len(self.space.parameters)
                or not np.all(np.isfinite(values))):
            raise ValueError("Joint sampler must return a finite (scenario, parameter) matrix")
        if self.space.content_sha256 != self.space_sha256:
            raise ValueError("Joint scenario space identity changed before design admission")
        for column, parameter in enumerate(self.space.parameters):
            for value in values[:, column]:
                parameter.admit(float(value))
        _text(self.numpy_version, "NumPy version")
        values.setflags(write=False)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "seed", seed)
        identity = _digest((self.space_sha256, seed, self.numpy_version, values))
        object.__setattr__(self, "content_sha256", identity)
        object.__setattr__(self, "scenario_ids", tuple(
            hashlib.sha256(f"{identity}:{index}".encode()).hexdigest()
            for index in range(len(values))
        ))

    def require_current(self):
        self.space.require_current()
        if self.space.content_sha256 != self.space_sha256:
            raise ValueError("Joint scenario mapping identity changed before propagation")
        current = _digest((self.space_sha256, self.seed, self.numpy_version, self.values))
        if current != self.content_sha256:
            raise ValueError("Joint scenario inputs changed after seeded sampling")


class JointScenarioDesignError(RuntimeError):
    """Preserve the caller sampler, seed and any returned rows when design fails."""

    def __init__(self, message, *, space, seed, sampled_values=None):
        super().__init__(message)
        self.space = space
        self.seed = seed
        self.sampled_values = sampled_values


def joint_scenario_design(
    space: JointScenarioSpace, *, count: int, seed: int, maximum_points: int = 1_000_000
) -> JointScenarioDesign:
    """Sample a caller-declared joint law with PCG64 and retain every actual draw."""
    count = _integer(count, "joint scenario count", 1, 2**63 - 1)
    seed = _integer(seed, "joint sampler seed", 0, 2**63 - 1)
    maximum_points = _integer(maximum_points, "maximum joint scenarios", 1, 2**63 - 1)
    if count > maximum_points:
        raise ValueError("Requested joint design exceeds the explicit scenario budget")
    space.require_current()
    rng = np.random.Generator(np.random.PCG64(seed))
    sampled = None
    try:
        sampled = space.sampler(rng, count)
        design = JointScenarioDesign(
            space=space,
            space_sha256=space.content_sha256,
            values=sampled,
            seed=seed,
            numpy_version=np.__version__,
        )
        space.require_current()
        return design
    except Exception as exc:
        raise JointScenarioDesignError(
            str(exc), space=space, seed=seed, sampled_values=sampled
        ) from exc


@dataclass(frozen=True, slots=True)
class JointCaseEvaluation:
    index: int
    scenario_id: str
    parameters: Mapping[str, float]
    outputs: Mapping[str, float]
    raw: Any


class UncertaintyEvaluationError(RuntimeError):
    """Retain failed input, actual callable/raw results and accepted evaluation prefix."""

    def __init__(
        self,
        message,
        *,
        space,
        model,
        parameters,
        completed,
        batch_inputs=None,
        native_result=None,
        design=None,
        failed_raw=None,
        failed_response=None,
        failed_output_values=None,
        scenario_id=None,
    ):
        super().__init__(message)
        self.space = space
        self.model = model
        self.parameters = MappingProxyType(dict(parameters))
        self.completed_evaluations = tuple(completed)
        self.case_index = len(completed)
        self.scenario_id = scenario_id
        self.batch_inputs = None if batch_inputs is None else _array(batch_inputs)
        self.native_result = native_result
        self.design = design
        self.failed_raw = failed_raw
        self.failed_response = failed_response
        self.failed_output_values = (
            MappingProxyType(dict(failed_output_values))
            if isinstance(failed_output_values, Mapping)
            else failed_output_values
        )


class UncertaintyDesignError(RuntimeError):
    """Retain a rejected native design without replacing invalid quantiles."""

    def __init__(self, message, *, space, engine, unit_cube, values):
        super().__init__(message)
        self.space = space
        self.native_engine = engine
        self.unit_cube = None if unit_cube is None else _array(unit_cube)
        self.transformed_values = None if values is None else _array(values)


def _design_id(values, cube, space_id, seed):
    digest = hashlib.sha256()
    digest.update(_digest((space_id, seed, values.shape)).encode())
    for array in (values, cube):
        digest.update(np.asarray(array, dtype="<f8").tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ParameterDesign:
    space: IndependentParameterSpace
    space_sha256: str
    values: np.ndarray
    unit_cube: np.ndarray
    seed: int
    native_engine: Any
    content_sha256: str = field(init=False)

    def __post_init__(self):
        values, cube = _array(self.values), _array(self.unit_cube)
        if (
            values.ndim != 2
            or values.shape != cube.shape
            or values.shape[1] != len(self.space.parameters)
        ):
            raise ValueError("Design rows must match complete parameter meanings")
        if not len(values) or not np.all(np.isfinite(cube)) or np.any((cube < 0) | (cube >= 1)):
            raise ValueError("A complete finite native unit-cube design is required")
        if self.space.content_sha256 != self.space_sha256:
            raise ValueError("Design space identity differs from current distributions")
        for column, parameter in enumerate(self.space.parameters):
            parameter.admit(values[:, column])
            expected = parameter.distribution.ppf(cube[:, column])
            if not np.array_equal(values[:, column], expected):
                raise ValueError("Transformed design differs from its actual quantile coordinates")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "unit_cube", cube)
        object.__setattr__(
            self, "content_sha256", _design_id(values, cube, self.space_sha256, self.seed)
        )

    def require_current(self):
        if self.space.content_sha256 != self.space_sha256:
            raise ValueError("Design law definition changed before propagation")
        if (
            _design_id(self.values, self.unit_cube, self.space_sha256, self.seed)
            != self.content_sha256
        ):
            raise ValueError(
                "Design coordinates changed after their native sampling identity was bound"
            )


def independent_qmc_design(
    space: IndependentParameterSpace, *, power: int, seed: int, maximum_points: int = 1_000_000
) -> ParameterDesign:
    """Draw a complete scrambled native base2 design; never thin or drop a point."""
    power = _integer(power, "base2 power", 1, 30)
    seed = _integer(seed, "seed", 0, 2**63 - 1)
    maximum_points = _integer(maximum_points, "maximum points", 1, 2**63 - 1)
    if 2**power > maximum_points:
        raise ValueError("Requested native design exceeds the explicit point budget")
    _, stats = _native()
    space.require_current()
    engine = cube = values = None
    try:
        engine = stats.qmc.Sobol(
            len(space.parameters), scramble=True, rng=np.random.default_rng(seed)
        )
        cube = engine.random_base2(power)
        values = np.column_stack(
            [p.distribution.ppf(cube[:, i]) for i, p in enumerate(space.parameters)]
        )
        space.require_current()
        return ParameterDesign(space, space.content_sha256, values, cube, seed, engine)
    except Exception as exc:
        raise UncertaintyDesignError(
            str(exc), space=space, engine=engine, unit_cube=cube, values=values
        ) from exc


class _Evaluator:
    def __init__(self, space, model):
        self.space, self.model = space, model
        self.completed = []
        self.batches = []

    def __call__(self, x):
        x = _array(x)
        parameters = {}
        batch = len(self.batches)
        outputs = []
        raw = output = values = None
        try:
            self.space.require_current()
            if x.ndim != 2 or x.shape[0] != len(self.space.parameters):
                raise ValueError(
                    "Native statistical batch differs from the complete parameter order"
                )
            for column in x.T:
                raw = output = values = None
                parameters = {
                    p.variable.name: float(v)
                    for p, v in zip(self.space.parameters, column, strict=True)
                }
                for parameter, value in zip(self.space.parameters, column, strict=True):
                    parameter.admit(value)
                readonly = MappingProxyType(parameters)
                output = self.model.callback(readonly)
                if isinstance(output, ModelOutput):
                    raw, values = output.raw, output.values
                else:
                    raw, values = None, output
                if not isinstance(values, Mapping) or set(values) != {
                    v.name for v in self.model.outputs
                }:
                    raise ValueError(
                        "Model response must contain exactly the declared output names"
                    )
                ordered = {v.name: finite(values[v.name], v.name) for v in self.model.outputs}
                self.space.require_current()
                self.completed.append(
                    CaseEvaluation(
                        len(self.completed), batch, readonly, MappingProxyType(ordered), raw
                    )
                )
                outputs.append(tuple(ordered.values()))
            result = _array(np.array(outputs).T)
            self.batches.append((x, result))
            # Native centering changes its returned arrays in place. Keep the
            # original response snapshots separate from that working storage.
            return result.copy()
        except Exception as exc:
            raise UncertaintyEvaluationError(
                str(exc),
                space=self.space,
                model=self.model,
                parameters=parameters,
                completed=self.completed,
                batch_inputs=x,
                failed_raw=raw,
                failed_response=output,
                failed_output_values=values,
            ) from exc


@dataclass(frozen=True, slots=True)
class PropagationSummary:
    mean: np.ndarray
    population_variance: np.ndarray
    quantile_probabilities: np.ndarray
    quantiles: np.ndarray

    def __post_init__(self):
        for name in ("mean", "population_variance", "quantile_probabilities", "quantiles"):
            object.__setattr__(self, name, _array(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class PropagationResult:
    design: ParameterDesign
    model: UncertainModel
    evaluations: tuple[CaseEvaluation, ...]
    values: np.ndarray
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PROPAGATION_ISSUERS:
            raise TypeError("Create propagation results through the completed native QMC propagator")
        _PENDING_PROPAGATION_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if type(self.design) is not ParameterDesign or type(self.model) is not UncertainModel:
            raise TypeError("Retain the original parameter design and uncertainty model")
        self.design.require_current()
        evaluations = tuple(self.evaluations)
        if len(evaluations) != len(self.design.values) or any(
            type(case) is not CaseEvaluation for case in evaluations
        ):
            raise ValueError("A native propagation must retain one row receipt per sampled input")
        object.__setattr__(self, "evaluations", evaluations)
        values = _array(self.values)
        names = tuple(v.name for v in self.model.outputs)
        object.__setattr__(self, "values", values)
        self._validate_retained_result()
        object.__setattr__(self, "_seal", self._fingerprint())

    def _validate_retained_result(self):
        names = tuple(output.name for output in self.model.outputs)
        if self.values.shape != (len(self.design.values), len(names)):
            raise ValueError("Propagation values differ from the design and declared outputs")
        expected_rows = []
        parameter_names = tuple(parameter.variable.name for parameter in self.design.space.parameters)
        for index, case in enumerate(self.evaluations):
            expected_parameters = dict(zip(parameter_names, self.design.values[index], strict=True))
            if (case.index != index or case.batch_index != 0
                    or dict(case.parameters) != expected_parameters
                    or set(case.outputs) != set(names)):
                raise ValueError("Evaluation receipt differs from its exact sampled design row")
            row = [finite(case.outputs[name], name) for name in names]
            expected_rows.append(row)
        if not np.array_equal(self.values, np.asarray(expected_rows, dtype=float)):
            raise ValueError("Propagation values differ from complete retained case outputs")
        return self

    def _fingerprint(self):
        return _digest((
            id(self.design), self.design.content_sha256, id(self.model),
            id(self.model.callback), id(self.model.evidence),
            tuple((item.name, item.quantity, item.unit, item.basis_id)
                  for item in self.model.outputs),
            tuple((case.index, case.batch_index,
                   tuple(sorted(case.parameters.items())),
                   tuple(sorted(case.outputs.items())), id(case.raw))
                  for case in self.evaluations),
            self.values,
        ))

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Propagation result or retained evaluation lineage changed")
        self.design.require_current()
        self._validate_retained_result()
        return self

    def summarize(self, quantile_probabilities=(0.05, 0.5, 0.95)):
        self.require_current()
        q = np.asarray(quantile_probabilities, dtype=float)
        if q.ndim != 1 or not len(q) or not np.all(np.isfinite(q)) or np.any((q < 0) | (q > 1)):
            raise ValueError("Declare finite quantile probabilities in [0,1]")
        with np.errstate(over="ignore", invalid="ignore"):
            mean = np.mean(self.values, axis=0)
            variance = np.var(self.values, axis=0)
            quantiles = np.quantile(self.values, q, axis=0, method="linear")
        if not all(np.all(np.isfinite(v)) for v in (mean, variance, quantiles)):
            raise ValueError("Ensemble summary has unresolved nonfinite arithmetic")
        if np.any((variance == 0) & np.any(self.values != self.values[0], axis=0)):
            raise ValueError("Ensemble variance underflow is unresolved")
        return PropagationSummary(mean, variance, q, quantiles)


@dataclass(frozen=True, slots=True)
class JointPropagationResult:
    """Complete deterministic evaluations bound to one explicit joint design."""

    design: JointScenarioDesign
    model: UncertainModel
    evaluations: tuple[JointCaseEvaluation, ...]
    values: np.ndarray
    _issuer_token: object = field(repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_JOINT_PROPAGATION_ISSUERS:
            raise TypeError("Create joint propagation results through propagate_joint")
        _PENDING_JOINT_PROPAGATION_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if type(self.design) is not JointScenarioDesign or type(self.model) is not UncertainModel:
            raise TypeError("Retain the original joint design and deterministic model")
        self.design.require_current()
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "values", _array(self.values))
        self._validate_retained_result()
        object.__setattr__(self, "_seal", self._fingerprint())

    def _validate_retained_result(self):
        names = tuple(output.name for output in self.model.outputs)
        if self.values.shape != (len(self.design.values), len(names)):
            raise ValueError("Joint response values differ from scenarios and declared outputs")
        if len(self.evaluations) != len(self.design.values):
            raise ValueError("Joint propagation must retain every sampled scenario")
        parameter_names = tuple(p.variable.name for p in self.design.space.parameters)
        expected_rows = []
        for index, case in enumerate(self.evaluations):
            expected_parameters = dict(zip(parameter_names, self.design.values[index], strict=True))
            if (type(case) is not JointCaseEvaluation or case.index != index
                    or case.scenario_id != self.design.scenario_ids[index]
                    or dict(case.parameters) != expected_parameters
                    or set(case.outputs) != set(names)):
                raise ValueError("Joint case receipt differs from its scenario identity or input row")
            expected_rows.append([finite(case.outputs[name], name) for name in names])
        if not np.array_equal(self.values, np.asarray(expected_rows, dtype=float)):
            raise ValueError("Joint response values differ from retained deterministic outputs")
        return self

    def _fingerprint(self):
        return _digest((
            id(self.design), self.design.content_sha256, id(self.model),
            id(self.model.callback), id(self.model.evidence), self.values,
            tuple((case.index, case.scenario_id, tuple(sorted(case.parameters.items())),
                   tuple(sorted(case.outputs.items())), id(case.raw))
                  for case in self.evaluations),
        ))

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Joint propagation or retained scenario lineage changed")
        self.design.require_current()
        self._validate_retained_result()
        return self


def propagate_joint(
    design: JointScenarioDesign, model: UncertainModel
) -> JointPropagationResult:
    """Evaluate every caller-sampled joint input; preserve the first failed scenario."""
    design.require_current()
    completed = []
    rows = []
    parameter_names = tuple(p.variable.name for p in design.space.parameters)
    output_names = tuple(output.name for output in model.outputs)
    for index, row in enumerate(design.values):
        scenario_id = design.scenario_ids[index]
        parameters = MappingProxyType({
            name: float(value) for name, value in zip(parameter_names, row, strict=True)
        })
        response = values = raw = None
        try:
            design.require_current()
            for parameter, value in zip(design.space.parameters, row, strict=True):
                parameter.admit(float(value))
            response = model.callback(parameters)
            if isinstance(response, ModelOutput):
                raw, values = response.raw, response.values
            else:
                values = response
            if not isinstance(values, Mapping) or set(values) != set(output_names):
                raise ValueError("Model response must contain exactly the declared output names")
            outputs = MappingProxyType({name: finite(values[name], name) for name in output_names})
            design.require_current()
            completed.append(JointCaseEvaluation(
                index, scenario_id, parameters, outputs, raw
            ))
            rows.append(tuple(outputs[name] for name in output_names))
        except Exception as exc:
            raise UncertaintyEvaluationError(
                str(exc), space=design.space, model=model, parameters=parameters,
                completed=completed, batch_inputs=design.values.T, design=design,
                failed_raw=raw, failed_response=response, failed_output_values=values,
                scenario_id=scenario_id,
            ) from exc
    design.require_current()
    return _issue_joint_propagation_result(
        design=design, model=model, evaluations=tuple(completed),
        values=_array(np.asarray(rows, dtype=float)),
    )


def propagate(design: ParameterDesign, model: UncertainModel) -> PropagationResult:
    design.require_current()
    evaluator = _Evaluator(design.space, model)
    try:
        values = evaluator(design.values.T).T
        # Physical callbacks use a copied batch. Recheck the original design
        # before binding those responses to its recorded sampling identity.
        design.require_current()
        return _issue_propagation_result(
            design, model, tuple(evaluator.completed), values
        )
    except UncertaintyEvaluationError as error:
        error.design = design
        raise
    except Exception as exc:
        parameters = evaluator.completed[-1].parameters if evaluator.completed else {}
        batch = evaluator.batches[0][0] if evaluator.batches else design.values.T
        raise UncertaintyEvaluationError(
            str(exc),
            space=design.space,
            model=model,
            parameters=parameters,
            completed=evaluator.completed,
            batch_inputs=batch,
            design=design,
        ) from exc


@dataclass(frozen=True, slots=True)
class SobolSensitivity:
    space: IndependentParameterSpace
    space_sha256: str
    model: UncertainModel
    native_result: Any
    evaluations: tuple[CaseEvaluation, ...]
    batches: tuple[tuple[np.ndarray, np.ndarray], ...]
    first_order: np.ndarray
    total_order: np.ndarray
    variance_resolved: np.ndarray
    n_base: int
    seed: int
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SOBOL_ISSUERS:
            raise TypeError("Create Sobol results through the completed native sensitivity analysis")
        _PENDING_SOBOL_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        if type(self.space) is not IndependentParameterSpace or type(self.model) is not UncertainModel:
            raise TypeError("Retain the exact admitted parameter space and model")
        self.space.require_current()
        if self.space_sha256 != self.space.content_sha256:
            raise ValueError("Sensitivity result differs from its admitted parameter space")
        if type(self.n_base) is not int or self.n_base < 2 or type(self.seed) is not int or self.seed < 0:
            raise ValueError("Sensitivity result must retain a valid base size and seed")
        evaluations = tuple(self.evaluations)
        if any(type(item) is not CaseEvaluation for item in evaluations):
            raise ValueError("Sensitivity results must retain native case evaluations")
        object.__setattr__(self, "evaluations", evaluations)
        batches = tuple(tuple(_array(part) for part in batch) for batch in self.batches)
        if len(batches) != 3 or any(len(batch) != 2 for batch in batches):
            raise ValueError("Sensitivity result must retain all three native input/output batches")
        object.__setattr__(self, "batches", batches)
        for name in ("first_order", "total_order"):
            object.__setattr__(self, name, _array(getattr(self, name)))
        mask = immutable_array(self.variance_resolved, dtype=bool, name="variance mask")
        object.__setattr__(self, "variance_resolved", mask)
        self._validate_retained_result()
        object.__setattr__(self, "_seal", self._fingerprint())

    def _validate_retained_result(self):
        shape = (len(self.model.outputs), len(self.space.parameters))
        if self.first_order.shape != shape or self.total_order.shape != shape or self.variance_resolved.shape != (len(self.model.outputs),):
            raise ValueError("Sensitivity indices and variance mask differ from declared outputs/inputs")
        native_first = np.asarray(self.native_result.first_order, dtype=float).reshape(shape)
        native_total = np.asarray(self.native_result.total_order, dtype=float).reshape(shape)
        expected_first, expected_total = native_first.copy(), native_total.copy()
        expected_first[~self.variance_resolved] = np.nan
        expected_total[~self.variance_resolved] = np.nan
        if not np.array_equal(self.first_order, expected_first, equal_nan=True) or not np.array_equal(
            self.total_order, expected_total, equal_nan=True
        ):
            raise ValueError("Sensitivity indices differ from the retained native result")
        if not np.all(np.isfinite(self.first_order[self.variance_resolved])) or not np.all(
            np.isfinite(self.total_order[self.variance_resolved])
        ):
            raise ValueError("Variable-response sensitivity indices must remain finite")
        if np.any(~np.isnan(self.first_order[~self.variance_resolved])) or np.any(
            ~np.isnan(self.total_order[~self.variance_resolved])
        ):
            raise ValueError("Unresolved variance indices must retain their NaN mask")
        if len(self.batches) != 3 or not self.evaluations:
            raise ValueError("Sensitivity result lost its native batches or accepted evaluations")
        for inputs, outputs in self.batches:
            if inputs.ndim != 2 or inputs.shape[0] != len(self.space.parameters):
                raise ValueError("Sensitivity input batch differs from declared parameter order")
            if outputs.ndim != 2 or outputs.shape != (len(self.model.outputs), inputs.shape[1]):
                raise ValueError("Sensitivity output batch differs from declared output order")
        return self

    def _fingerprint(self):
        return _digest((
            id(self.space), self.space_sha256, id(self.model), id(self.model.callback),
            id(self.native_result), _array(self.native_result.first_order),
            _array(self.native_result.total_order),
            tuple((item.index, item.batch_index, tuple(sorted(item.parameters.items())),
                   tuple(sorted(item.outputs.items())), id(item.raw)) for item in self.evaluations),
            tuple((inputs, outputs) for inputs, outputs in self.batches),
            self.first_order, self.total_order, self.variance_resolved, self.n_base, self.seed,
        ))

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Sensitivity result or retained native lineage changed")
        self.space.require_current()
        self._validate_retained_result()
        return self


def sobol_sensitivity(
    space: IndependentParameterSpace,
    model: UncertainModel,
    *,
    power: int,
    seed: int,
    maximum_evaluations: int = 1_000_000,
) -> SobolSensitivity:
    """Native Saltelli indices for the declared independent, deterministic model.

    Finite-sample negative estimates remain unchanged. Constant-output indices
    have no variance denominator and are exposed as NaN with a false mask,
    separately from the actual native result's zero convention.
    """
    power = _integer(power, "base2 power", 1, 30)
    seed = _integer(seed, "seed", 0, 2**63 - 1)
    maximum_evaluations = _integer(maximum_evaluations, "maximum evaluations", 1, 2**63 - 1)
    if 2**power * (len(space.parameters) + 2) > maximum_evaluations:
        raise ValueError("Requested native sensitivity design exceeds the evaluation budget")
    _, stats = _native()
    space_id = space.content_sha256
    evaluator = _Evaluator(space, model)
    native = None
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            native = stats.sobol_indices(
                func=evaluator,
                n=2**power,
                dists=[p.distribution for p in space.parameters],
                rng=np.random.default_rng(seed),
            )
        space.require_current()
        if len(evaluator.batches) != 3:
            raise ValueError("Native statistical batch layout changed; contract needs review")
        a, b = (v[1] for v in evaluator.batches[:2])
        with np.errstate(over="ignore", invalid="ignore"):
            center = np.mean(np.stack((a, b)), axis=(0, -1))
            centered = [values - center[:, None] for _, values in evaluator.batches]
            variance = np.var(np.concatenate((a, b), axis=1), axis=1)
            squares = [np.sum(values**2, axis=1) for values in centered]
        if not all(np.all(np.isfinite(v)) for v in (center, variance, *centered, *squares)):
            raise ValueError(
                "Native sensitivity arithmetic is unresolved; zero substitution is not accepted"
            )
        if not math.isfinite(math.fsum(float(value) for values in squares for value in values)):
            raise ValueError("Native cross-product scale overflows")
        shape = (len(model.outputs), len(space.parameters))
        first = np.array(native.first_order, copy=True).reshape(shape)
        total = np.array(native.total_order, copy=True).reshape(shape)
        mask = variance > 0
        varying = np.logical_or.reduce(
            [np.any(values != a[:, :1], axis=1) for _, values in evaluator.batches]
        )
        if np.any(~mask & varying):
            raise ValueError("Zero native variance with varying responses is unresolved")
        if not np.all(np.isfinite(first[mask])) or not np.all(np.isfinite(total[mask])):
            raise ValueError("Native statistical indices are nonfinite for a variable response")
        first[~mask], total[~mask] = np.nan, np.nan
        return _issue_sobol_sensitivity(
            space=space,
            space_sha256=space_id,
            model=model,
            native_result=native,
            evaluations=tuple(evaluator.completed),
            batches=tuple(evaluator.batches),
            first_order=first,
            total_order=total,
            variance_resolved=mask,
            n_base=2**power,
            seed=seed,
        )
    except UncertaintyEvaluationError:
        raise
    except Exception as exc:
        last = evaluator.completed[-1].parameters if evaluator.completed else {}
        raise UncertaintyEvaluationError(
            str(exc),
            space=space,
            model=model,
            parameters=last,
            completed=evaluator.completed,
            native_result=native,
        ) from exc
