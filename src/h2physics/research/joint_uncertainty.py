"""Explicit dependent-input transforms over the existing native QMC machinery.

The caller owns the joint law/transform. This module does not infer a copula,
correlation matrix, dependence-aware Sobol indices or annual event frequency.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from numbers import Real
from types import MappingProxyType

import numpy as np

from ..core import finite
from ..observations import Variable
from ..uncertainty import (
    IndependentParameterSpace,
    ModelOutput,
    ParameterDesign,
    UncertainModel,
    UncertaintyEvaluationError,
    independent_qmc_design,
    propagate,
)


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {label}")


_PENDING_RESULT_ISSUERS = set()


def _issue_result_token():
    token = object()
    _PENDING_RESULT_ISSUERS.add(token)
    return token


def _content_token(value, seen=None):
    """Fingerprint retained propagation data without rerunning model callbacks."""
    seen = set() if seen is None else seen
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (float, np.floating)):
        return ("float", float(value).hex())
    if isinstance(value, np.integer):
        return int(value)
    if id(value) in seen:
        return ("reference", id(value))
    seen.add(id(value))
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError("Object arrays cannot seal a joint propagation result")
        return ("array", id(value), value.dtype.str, value.shape,
                hashlib.sha256(value.tobytes(order="C")).hexdigest())
    if isinstance(value, Mapping):
        return ("mapping", id(value), tuple(
            (str(key), _content_token(item, seen)) for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_content_token(item, seen) for item in value))
    if is_dataclass(value):
        return (type(value).__module__, type(value).__qualname__, id(value), tuple(
            (item.name, _content_token(getattr(value, item.name), seen))
            for item in fields(value)))
    if callable(value):
        function = getattr(value, "__func__", value)
        code = getattr(function, "__code__", None)
        closure = getattr(function, "__closure__", None)
        closure_values = ()
        if closure:
            retained = []
            for cell in closure:
                try:
                    retained.append(_content_token(cell.cell_contents, seen))
                except ValueError:  # an intentionally empty closure cell
                    retained.append(("empty-cell",))
            closure_values = tuple(retained)
        bound_instance = getattr(value, "__self__", None)
        if bound_instance is not None and not isinstance(bound_instance, type):
            bound_state = _callable_state(bound_instance, seen)
        elif code is None:
            # Callable instances can carry mutable configuration in attributes.
            bound_state = _callable_state(value, seen)
        else:
            bound_state = None
        return ("callable", id(function), id(code),
                _content_token(getattr(function, "__defaults__", None), seen),
                _content_token(getattr(function, "__kwdefaults__", None), seen),
                closure_values, bound_state)
    return (type(value).__module__, type(value).__qualname__, id(value))


def _callable_state(value, seen):
    """Capture ordinary callable configuration while leaving opaque state by identity."""
    state = getattr(value, "__dict__", None)
    slots = []
    for cls in type(value).__mro__:
        declared = getattr(cls, "__slots__", ())
        if isinstance(declared, str):
            declared = (declared,)
        for name in declared:
            if name not in ("__dict__", "__weakref__") and hasattr(value, name):
                slots.append((name, _content_token(getattr(value, name), seen)))
    return (type(value).__module__, type(value).__qualname__, id(value),
            _content_token(state, seen) if state is not None else None, tuple(slots))


def _content_digest(value):
    return hashlib.sha256(repr(_content_token(value)).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class JointParameter:
    variable: Variable
    minimum: float
    maximum: float
    law_evidence_id: str

    def __post_init__(self):
        if not isinstance(self.variable, Variable):
            raise TypeError("A joint parameter needs explicit quantity, unit and basis")
        lower = finite(self.minimum, "minimum")
        upper = finite(self.maximum, "maximum")
        if lower >= upper:
            raise ValueError("Joint parameter admission bounds must increase")
        _text(self.law_evidence_id, "parameter law evidence")
        object.__setattr__(self, "minimum", lower)
        object.__setattr__(self, "maximum", upper)


@dataclass(frozen=True, slots=True)
class JointParameterSpace:
    latent_space: IndependentParameterSpace
    parameters: tuple[JointParameter, ...]
    transform: object = field(repr=False, compare=False)
    joint_law_id: str
    dependence_evidence_id: str
    transform_revision_id: str

    def __post_init__(self):
        if type(self.latent_space) is not IndependentParameterSpace:
            raise TypeError("Supply the existing independent latent parameter space")
        parameters = tuple(self.parameters)
        if (not parameters or any(type(p) is not JointParameter for p in parameters)
                or len({p.variable.name for p in parameters}) != len(parameters)):
            raise ValueError("Joint parameters need unique named admission boundaries")
        if not callable(self.transform):
            raise TypeError("Supply the actual latent-to-joint transform callable")
        for name in ("joint_law_id", "dependence_evidence_id", "transform_revision_id"):
            _text(getattr(self, name), name)
        object.__setattr__(self, "parameters", parameters)

    def transform_parameters(self, latent):
        """Call the declared transform; retain exact names and finite bounds."""
        self.latent_space.require_current()
        if not isinstance(latent, Mapping) or set(latent) != {
                p.variable.name for p in self.latent_space.parameters}:
            raise ValueError("Latent inputs must match the complete declared parameter names")
        for parameter in self.latent_space.parameters:
            parameter.admit(latent[parameter.variable.name])
        values = self.transform(MappingProxyType(dict(latent)))
        if not isinstance(values, Mapping) or set(values) != {p.variable.name for p in self.parameters}:
            raise ValueError("Joint transform must return exactly the declared parameter names")
        result = {}
        for parameter in self.parameters:
            name = parameter.variable.name
            if isinstance(values[name], bool) or not isinstance(values[name], Real):
                raise ValueError(f"Joint parameter {name!r} must be one real numeric scalar")
            value = finite(values[name], name)
            if not parameter.minimum <= value <= parameter.maximum:
                raise ValueError(f"Joint parameter {name!r} is outside admitted bounds")
            result[name] = value
        self.latent_space.require_current()
        return MappingProxyType(result)


@dataclass(frozen=True, slots=True)
class JointCaseResponse:
    latent_parameters: Mapping
    joint_parameters: Mapping
    original_response: object = field(repr=False)

    def __post_init__(self):
        for name in ("latent_parameters", "joint_parameters"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


class JointEvaluationError(RuntimeError):
    """Original failed physical input, response and latent propagation prefix."""

    def __init__(self, space, model, cause, latent, joint, response=None):
        self.space = space
        self.model = model
        self.cause = cause
        self.latent_parameters = MappingProxyType(dict(latent))
        self.joint_parameters = None if joint is None else MappingProxyType(dict(joint))
        self.original_response = response
        self.propagation_error = None
        super().__init__(f"Joint input evaluation failed for {space.joint_law_id!r}")


@dataclass(frozen=True, slots=True)
class JointPropagationResult:
    space: JointParameterSpace
    model: UncertainModel
    scenario_id: str
    latent_propagation: object
    _issuer_token: object = field(repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_RESULT_ISSUERS:
            raise TypeError("Create joint propagation results through a completed native QMC propagation")
        _PENDING_RESULT_ISSUERS.remove(self._issuer_token)
        self._validate_retained_result()
        object.__setattr__(self, "_seal", self._fingerprint())

    def _validate_retained_result(self):
        from ..uncertainty import PropagationResult

        _text(self.scenario_id, "physical scenario identity")
        if (type(self.space) is not JointParameterSpace or type(self.model) is not UncertainModel
                or type(self.latent_propagation) is not PropagationResult):
            raise TypeError("Retain the original joint space, model and completed latent propagation")
        propagation = self.latent_propagation
        propagation.require_current()
        propagation.design.require_current()
        if (propagation.design.space is not self.space.latent_space
                or propagation.model.evidence is not self.model.evidence
                or tuple(propagation.model.outputs) != tuple(self.model.outputs)):
            raise ValueError("Native propagation is detached from the declared latent space or model contract")
        if len(propagation.evaluations) != len(propagation.design.values):
            raise ValueError("Joint propagation must retain one response for every native design row")
        latent_names = tuple(parameter.variable.name for parameter in self.space.latent_space.parameters)
        joint_by_name = {parameter.variable.name: parameter for parameter in self.space.parameters}
        output_names = tuple(output.name for output in self.model.outputs)
        for index, case in enumerate(propagation.evaluations):
            if type(case.raw) is not JointCaseResponse:
                raise TypeError("Every native response must retain its original joint-input receipt")
            expected_latent = {
                name: float(value)
                for name, value in zip(latent_names, propagation.design.values[index], strict=True)
            }
            receipt = case.raw
            if (case.index != index or case.batch_index != 0
                    or dict(case.parameters) != expected_latent
                    or dict(receipt.latent_parameters) != expected_latent
                    or set(receipt.joint_parameters) != set(joint_by_name)):
                raise ValueError("Joint response no longer matches its exact native latent design row")
            for name, parameter in joint_by_name.items():
                value = receipt.joint_parameters[name]
                if (isinstance(value, bool) or not isinstance(value, Real)
                        or not parameter.minimum <= finite(value, name) <= parameter.maximum):
                    raise ValueError("Retained joint response lies outside its declared parameter bounds")
            original = receipt.original_response
            raw_values = original.values if isinstance(original, ModelOutput) else original
            if isinstance(original, ModelOutput):
                freshness_check = getattr(original.raw, "require_current", None)
                if callable(freshness_check):
                    freshness_check()
            if (not isinstance(raw_values, Mapping) or set(raw_values) != set(output_names)
                    or dict(case.outputs) != {
                        name: finite(raw_values[name], name) for name in output_names
                    }):
                raise ValueError("Joint response outputs differ from their retained original model response")
        return self

    def _fingerprint(self):
        return _content_digest((
            id(self.space), self.space.joint_law_id, self.space.dependence_evidence_id,
            self.space.transform_revision_id, _content_digest(self.space.transform),
            self.space.latent_space.content_sha256,
            tuple((parameter.variable, parameter.minimum, parameter.maximum,
                   parameter.law_evidence_id) for parameter in self.space.parameters),
            id(self.model), _content_digest(self.model.callback),
            self.model.outputs, self.model.evidence,
            self.scenario_id, id(self.latent_propagation),
            id(self.latent_propagation.design), self.latent_propagation.design.content_sha256,
            id(self.latent_propagation.model), self.latent_propagation.evaluations,
            self.latent_propagation.values,
        ))

    def require_current(self):
        if not self._seal or self._fingerprint() != self._seal:
            raise ValueError("Joint propagation result or retained response lineage changed")
        self.space.latent_space.require_current()
        self.latent_propagation.design.require_current()
        self._validate_retained_result()
        return self

    def summarize(self, quantile_probabilities=(0.05, 0.5, 0.95)):
        self.require_current()
        return self.latent_propagation.summarize(quantile_probabilities)

    @property
    def evaluations(self):
        self.require_current()
        return self.latent_propagation.evaluations


def joint_qmc_design(space: JointParameterSpace, *, power, seed, maximum_points=1_000_000):
    """Reuse the existing SciPy QMC design for independent latent coordinates."""
    if type(space) is not JointParameterSpace:
        raise TypeError("Supply an explicit JointParameterSpace")
    return independent_qmc_design(space.latent_space, power=power, seed=seed,
                                  maximum_points=maximum_points)


def propagate_joint(space: JointParameterSpace, design: ParameterDesign,
                    model: UncertainModel, *, scenario_id: str):
    """Propagate a complete latent design without replacing failed evaluations."""
    _text(scenario_id, "physical scenario identity")
    if type(space) is not JointParameterSpace or type(model) is not UncertainModel:
        raise TypeError("Supply the joint space and existing deterministic UncertainModel")
    if type(design) is not ParameterDesign or design.space is not space.latent_space:
        raise ValueError("Joint propagation requires a design from the exact latent space")

    def evaluate(latent):
        joint = response = None
        try:
            joint = space.transform_parameters(latent)
            response = model.callback(joint)
            values = response.values if isinstance(response, ModelOutput) else response
            return ModelOutput(values, JointCaseResponse(latent, joint, response))
        except Exception as cause:
            raise JointEvaluationError(space, model, cause, latent, joint, response) from cause

    wrapped = UncertainModel(evaluate, model.outputs, model.evidence)
    try:
        result = propagate(design, wrapped)
    except UncertaintyEvaluationError as error:
        cause = error.__cause__
        if isinstance(cause, JointEvaluationError):
            cause.propagation_error = error
            raise cause from cause.cause
        # Output-name/finite-value validation happens in the shared evaluator
        # after our callback returned. Retain the transformed physical mapping
        # and original response for that failure as well as the latent prefix.
        raw = getattr(error, "failed_raw", None)
        if isinstance(raw, JointCaseResponse):
            contextual = JointEvaluationError(space, model, cause or error,
                raw.latent_parameters, raw.joint_parameters, raw.original_response)
            contextual.propagation_error = error
            raise contextual from (cause or error)
        raise
    return JointPropagationResult(space, model, scenario_id, result, _issue_result_token())


@dataclass(frozen=True, slots=True)
class ScenarioUncertaintyResponse:
    """Retain the actual scenario and original execution alongside reader output."""

    scenario: object = field(repr=False)
    execution: object = field(repr=False)
    reader_response: object = field(repr=False)


class ScenarioUncertaintyError(RuntimeError):
    """Scenario construction/execution/reading failure with original evidence."""

    def __init__(self, stage, cause, parameters, scenario=None, execution=None):
        self.stage = stage
        self.cause = cause
        self.parameters = MappingProxyType(dict(parameters))
        self.scenario = scenario
        self.execution = execution
        self.scenario_error = cause if stage == "scenario execution" else None
        super().__init__(f"Scenario uncertainty evaluation failed during {stage}")


def scenario_uncertain_model(*, scenario_factory, output_reader, outputs, evidence,
                             targets=None):
    """Adapt existing operational scenarios to the deterministic model contract.

    The factory receives the explicit physical parameter mapping. The reader receives
    the original ``ScenarioResult`` and must return declared output values or a
    ``ModelOutput``. Optional target IDs are copied at binding. No scenario is built
    until the returned model is evaluated.
    """
    if not callable(scenario_factory) or not callable(output_reader):
        raise TypeError("Supply explicit scenario factory and output-reader callables")
    if isinstance(targets, (str, bytes)):
        raise TypeError("Scenario targets must be a sequence of node IDs")
    selected = None if targets is None else tuple(targets)
    if selected is not None:
        if not selected:
            raise ValueError("Scenario target selection cannot be empty")
        for node_id in selected:
            _text(node_id, "scenario target node ID")

    def evaluate(parameters):
        from ..scenarios import OperationalScenario

        scenario = execution = None
        stage = "scenario construction"
        try:
            scenario = scenario_factory(MappingProxyType(dict(parameters)))
            if type(scenario) is not OperationalScenario:
                raise TypeError("Scenario factory must return an OperationalScenario")
            stage = "scenario execution"
            execution = scenario.run(targets=selected)
            stage = "output reading"
            response = output_reader(execution)
            values = response.values if isinstance(response, ModelOutput) else response
            return ModelOutput(values, ScenarioUncertaintyResponse(scenario, execution, response))
        except Exception as cause:
            raise ScenarioUncertaintyError(stage, cause, parameters, scenario, execution) from cause

    return UncertainModel(evaluate, tuple(outputs), evidence)


__all__ = ["JointParameter", "JointParameterSpace", "JointCaseResponse",
           "JointEvaluationError", "JointPropagationResult", "joint_qmc_design", "propagate_joint",
           "ScenarioUncertaintyResponse", "ScenarioUncertaintyError", "scenario_uncertain_model"]
