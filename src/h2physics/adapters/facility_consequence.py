"""Pass an admitted preferred-dispersion result to a caller-owned consequence model.

This module owns only the handoff contract. It does not interpret plume fields,
select receptors or thresholds, or assign harm/protection consequences.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from functools import partial
from types import CodeType, FunctionType

import numpy as np

from .facility_accident_chain import FacilityDispersionHandoff


def _configuration_token(value, seen=None):
    """Snapshot mutable callback configuration without calling user code."""
    seen = set() if seen is None else seen
    if value is None or isinstance(value, (str, bool, int)):
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
            return ("object-array", id(value), tuple(
                _configuration_token(item, seen) for item in value.flat))
        return ("array", id(value), value.dtype.str, value.shape,
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest())
    if isinstance(value, Mapping):
        return ("mapping", id(value), tuple(
            (str(key), _configuration_token(item, seen)) for key, item in value.items()))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, id(value), tuple(
            _configuration_token(item, seen) for item in value))
    if isinstance(value, (staticmethod, classmethod)):
        return (type(value).__name__, id(value), _configuration_token(value.__func__, seen))
    if isinstance(value, FunctionType):
        closure = []
        for cell in value.__closure__ or ():
            try:
                closure.append(_configuration_token(cell.cell_contents, seen))
            except ValueError:
                closure.append("<empty>")
        return ("function", id(value), _code_definition_token(value.__code__),
                _configuration_token(value.__defaults__, seen),
                _configuration_token(value.__kwdefaults__, seen),
                tuple(closure), _configuration_token(value.__dict__, seen))
    if isinstance(value, type):
        # Class.__dict__ creates a new mappingproxy on each lookup. Retain the
        # declared class/attribute identities and values, not that wrapper.
        return ("class", value.__module__, value.__qualname__, id(value), tuple(
            (name, _configuration_token(item, seen)) for name, item in vars(value).items()))
    if is_dataclass(value) and not isinstance(value, type):
        return (type(value).__module__, type(value).__qualname__, id(value), tuple(
            (item.name, _configuration_token(getattr(value, item.name), seen))
            for item in fields(value)))
    state = getattr(value, "__dict__", None)
    slots = []
    for cls in type(value).__mro__:
        declared = getattr(cls, "__slots__", ())
        if isinstance(declared, str):
            declared = (declared,)
        for name in declared:
            if name in ("__dict__", "__weakref__"):
                continue
            try:
                item = getattr(value, name)
            except (AttributeError, ValueError):
                continue
            slots.append((name, _configuration_token(item, seen)))
    return (type(value).__module__, type(value).__qualname__, id(value),
            _configuration_token(state, seen) if state is not None else None,
            tuple(slots))


def _code_definition_token(code):
    """Retain code semantics without marshal's mutable string-intern flags."""
    def constant(value):
        if isinstance(value, CodeType):
            return ("code", _code_definition_token(value))
        if isinstance(value, tuple):
            return ("tuple", tuple(constant(item) for item in value))
        if isinstance(value, frozenset):
            return ("frozenset", tuple(sorted((constant(item) for item in value), key=repr)))
        if value is None or value is Ellipsis or isinstance(value, (str, bytes, bool, int, float, complex)):
            return (type(value).__name__, repr(value))
        return _configuration_token(value)

    attributes = (
        "co_argcount", "co_posonlyargcount", "co_kwonlyargcount", "co_nlocals",
        "co_stacksize", "co_flags", "co_code", "co_names", "co_varnames",
        "co_freevars", "co_cellvars", "co_filename", "co_name", "co_qualname",
        "co_firstlineno", "co_linetable", "co_exceptiontable",
    )
    return (tuple((name, getattr(code, name)) for name in attributes),
            tuple(constant(item) for item in code.co_consts))


def _evaluator_binding(value, seen=None):
    """Bind evaluator code and ordinary captured configuration, not its behavior."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return ("reference", id(value))
    seen.add(id(value))
    if isinstance(value, partial):
        return ("partial", id(value), _evaluator_binding(value.func, seen),
                _configuration_token(value.args), _configuration_token(value.keywords))
    function = getattr(value, "__func__", value)
    bound = getattr(value, "__self__", None)
    if not hasattr(function, "__code__"):
        call = getattr(type(value), "__call__", None)
        function = getattr(call, "__func__", call)
        bound = value
    code = getattr(function, "__code__", None)
    closure = []
    for cell in getattr(function, "__closure__", None) or ():
        try:
            closure.append(_configuration_token(cell.cell_contents))
        except ValueError:
            closure.append("<empty>")
    bound_state = None
    if bound is not None and not isinstance(bound, type):
        bound_state = _configuration_token(bound)
    return (
        id(value), id(function),
        hashlib.sha256(repr(_code_definition_token(code)).encode("utf-8")).hexdigest()
        if code is not None else None,
        _configuration_token(getattr(function, "__defaults__", None)),
        _configuration_token(getattr(function, "__kwdefaults__", None)),
        tuple(closure), bound_state,
    )


@dataclass(frozen=True, slots=True)
class FacilityConsequenceEvaluation:
    """Retain the exact source/dispersion handoff and receiving model result.

    A receiving result implements ``require_current()`` and exposes its original
    ``facility_handoff`` object. The host does not copy or serialize the result.
    """

    facility_handoff: FacilityDispersionHandoff
    evaluator: object = field(repr=False, compare=False)
    consequence_result: object = field(repr=False, compare=False)
    method_evidence_id: str
    _identity: tuple = field(default=(), init=False, repr=False, compare=False)
    _evaluator_identity: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.facility_handoff) is not FacilityDispersionHandoff:
            raise TypeError("Retain the admitted finite-source/dispersion handoff")
        if not callable(self.evaluator):
            raise TypeError("Retain the caller-owned consequence evaluator")
        if not isinstance(self.method_evidence_id, str) or not self.method_evidence_id.strip():
            raise ValueError("Identify the receiving consequence method and applicability")
        self._validate_result()
        self.facility_handoff.require_current()
        object.__setattr__(self, "_identity", (
            self.facility_handoff, self.evaluator, self.consequence_result,
            self.method_evidence_id,
        ))
        object.__setattr__(self, "_evaluator_identity", _evaluator_binding(self.evaluator))

    def _validate_result(self):
        if self.consequence_result is None:
            raise TypeError("A consequence evaluator must return its typed result object")
        if getattr(self.consequence_result, "facility_handoff", None) is not self.facility_handoff:
            raise ValueError("Consequence result must retain this exact facility handoff")
        if not callable(getattr(self.consequence_result, "require_current", None)):
            raise TypeError("Consequence result must expose require_current()")

    def require_current(self) -> FacilityConsequenceEvaluation:
        if not self._identity or any(current is not original for current, original in zip(
            (self.facility_handoff, self.evaluator, self.consequence_result,
             self.method_evidence_id),
            self._identity,
            strict=True,
        )):
            raise ValueError("Consequence evaluation lost its original source or owner result")
        self.facility_handoff.require_current()
        self._validate_result()
        if _evaluator_binding(self.evaluator) != self._evaluator_identity:
            raise ValueError("Consequence evaluator code or captured configuration changed")
        self.consequence_result.require_current()
        return self


class FacilityConsequenceEvaluationError(RuntimeError):
    """Retain a consequence handoff failure and any returned native result."""

    def __init__(self, message, *, facility_handoff, cause, stage, consequence_result=None):
        if stage not in {"pre_evaluation_integrity", "evaluator", "post_evaluation_integrity",
                         "invalid_result"}:
            raise ValueError("Unknown facility consequence evaluation stage")
        super().__init__(message)
        self.facility_handoff = facility_handoff
        self.cause = cause
        self.stage = stage
        self.consequence_result = consequence_result


def evaluate_facility_consequence(
    facility_handoff: FacilityDispersionHandoff,
    evaluator,
    *,
    method_evidence_id: str,
) -> FacilityConsequenceEvaluation:
    """Call a receiving consequence model with the exact accepted handoff.

    The evaluator receives the full typed handoff, including the source binding,
    preferred-provider receipt and actual native result. Its result must retain
    this handoff and implement its own freshness check.
    """
    if type(facility_handoff) is not FacilityDispersionHandoff:
        raise TypeError("Supply an admitted FacilityDispersionHandoff")
    if not callable(evaluator):
        raise TypeError("Supply a caller-owned consequence evaluator")
    if not isinstance(method_evidence_id, str) or not method_evidence_id.strip():
        raise ValueError("Identify the receiving consequence method and applicability")
    try:
        facility_handoff.require_current()
    except Exception as cause:
        raise FacilityConsequenceEvaluationError(
            "Facility handoff failed before consequence evaluation",
            facility_handoff=facility_handoff, cause=cause,
            stage="pre_evaluation_integrity",
        ) from cause
    try:
        evaluator_before = _evaluator_binding(evaluator)
    except Exception as cause:
        raise FacilityConsequenceEvaluationError(
            "Consequence evaluator configuration could not be captured before evaluation",
            facility_handoff=facility_handoff, cause=cause,
            stage="pre_evaluation_integrity",
        ) from cause
    try:
        result = evaluator(facility_handoff)
    except Exception as cause:
        try:
            if _evaluator_binding(evaluator) != evaluator_before:
                raise ValueError("Consequence evaluator changed during evaluation")
            facility_handoff.require_current()
        except Exception as integrity_error:
            error = FacilityConsequenceEvaluationError(
                "Consequence evaluator failed after changing itself or the admitted handoff",
                facility_handoff=facility_handoff, cause=integrity_error,
                stage="post_evaluation_integrity",
            )
            error.evaluator_cause = cause
            raise error from cause
        raise FacilityConsequenceEvaluationError(
            "Caller consequence evaluator rejected the admitted facility handoff",
            facility_handoff=facility_handoff, cause=cause, stage="evaluator",
        ) from cause
    try:
        if _evaluator_binding(evaluator) != evaluator_before:
            raise ValueError("Consequence evaluator changed during evaluation")
        facility_handoff.require_current()
    except Exception as cause:
        raise FacilityConsequenceEvaluationError(
            "Facility source, dispersion receipt, or consequence evaluator changed during evaluation",
            facility_handoff=facility_handoff, cause=cause,
            stage="post_evaluation_integrity", consequence_result=result,
        ) from cause
    try:
        receipt = FacilityConsequenceEvaluation(
            facility_handoff, evaluator, result, method_evidence_id,
        )
        return receipt.require_current()
    except Exception as cause:
        raise FacilityConsequenceEvaluationError(
            "Caller consequence result does not retain the admitted facility lineage",
            facility_handoff=facility_handoff, cause=cause,
            stage="invalid_result", consequence_result=result,
        ) from cause
