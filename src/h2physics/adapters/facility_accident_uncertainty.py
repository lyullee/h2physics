"""Source-bound accident/consequence responses for the shared uncertainty engine.

This adapter orchestrates the already selected facility chain and consequence
owner for each declared input row. It adds no sampling law, consequence physics,
event frequency or replacement propagation algorithm.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Real
from types import MappingProxyType

from ..core import finite
from ..uncertainty import ModelOutput, UncertainModel, UncertaintyEvidence
from .facility_accident_chain import FacilityAccidentChain
from .facility_accident_consequence import (
    FacilityAccidentConsequenceRun,
    run_facility_accident_consequence,
)


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")


def _reader_values(response):
    values = response.values if isinstance(response, ModelOutput) else response
    if not isinstance(values, Mapping):
        raise TypeError("Consequence output reader must return a numeric mapping or ModelOutput")
    result = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Consequence output names must be nonblank strings")
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"Consequence output {name!r} must be one real scalar")
        result[name] = finite(value, name)
    if not result:
        raise ValueError("Consequence output reader returned no declared outputs")
    return MappingProxyType(result)


def _value_signature(values):
    return tuple(sorted((name, float(value).hex()) for name, value in values.items()))


@dataclass(frozen=True, slots=True)
class FacilityAccidentUncertaintyResponse:
    """Per-row source, consequence and scalar-reader lineage receipt."""

    run: FacilityAccidentConsequenceRun = field(repr=False, compare=False)
    reader_response: object = field(repr=False, compare=False)
    output_names: tuple[str, ...]
    values: Mapping[str, float] = field(init=False)
    _identity: tuple = field(default=(), init=False, repr=False, compare=False)
    _signature: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.run) is not FacilityAccidentConsequenceRun:
            raise TypeError("Retain the accepted facility accident/consequence run")
        names = tuple(self.output_names)
        if (not names or any(not isinstance(name, str) or not name.strip() for name in names)
                or len(set(names)) != len(names)):
            raise ValueError("Declare unique names for consequence outputs")
        self.run.require_current()
        values = _reader_values(self.reader_response)
        if set(values) != set(names):
            raise ValueError("Consequence reader values must match every declared uncertainty output")
        object.__setattr__(self, "output_names", names)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "_identity", (
            self.run, self.run.chain, self.run.chain_result,
            self.run.facility_handoff, self.run.consequence, self.reader_response,
        ))
        object.__setattr__(self, "_signature", _value_signature(values))

    def require_current(self):
        self.run.require_current()
        current = (self.run, self.run.chain, self.run.chain_result,
                   self.run.facility_handoff, self.run.consequence, self.reader_response)
        if (not self._identity or any(value is not original for value, original in zip(
                current, self._identity, strict=True))):
            raise ValueError("Uncertainty response lost its accepted source/consequence lineage")
        values = _reader_values(self.reader_response)
        if set(values) != set(self.output_names) or _value_signature(values) != self._signature:
            raise ValueError("Consequence reader values changed after source-bound capture")
        if dict(values) != dict(self.values):
            raise ValueError("Consequence scalar outputs differ from the retained uncertainty row")
        return self


def facility_accident_consequence_uncertain_model(
    *, chain_factory, evaluator_factory, output_reader, outputs, evidence,
    method_evidence_id,
):
    """Build one existing ``UncertainModel`` around typed accident/consequence runs.

    ``chain_factory(parameters)`` and ``evaluator_factory(parameters)`` are called
    once for each existing uncertainty-engine evaluation. ``output_reader(run)``
    must return exactly the declared scalar output names. Sample generation,
    dependence transforms, retries, and propagation remain owned by the existing
    uncertainty APIs; caller evidence supplies reset and statistical scope.
    """
    if not callable(chain_factory) or not callable(evaluator_factory) or not callable(output_reader):
        raise TypeError("Supply explicit per-row chain, consequence-evaluator and output-reader factories")
    if type(evidence) is not UncertaintyEvidence:
        raise TypeError("Supply the existing typed uncertainty evidence")
    output_variables = tuple(outputs)
    output_names = tuple(getattr(output, "name", None) for output in output_variables)
    if (not output_names or any(not isinstance(name, str) or not name.strip()
                                for name in output_names)
            or len(set(output_names)) != len(output_names)):
        raise ValueError("Declare unique output Variable names for the consequence reader")
    _text(method_evidence_id, "consequence method/applicability evidence")

    def evaluate(parameters):
        snapshot = MappingProxyType(dict(parameters))
        chain = chain_factory(snapshot)
        if type(chain) is not FacilityAccidentChain:
            raise TypeError("Accident chain factory must return a typed FacilityAccidentChain")
        evaluator = evaluator_factory(snapshot)
        if not callable(evaluator):
            raise TypeError("Consequence evaluator factory must return a callable owner")
        run = run_facility_accident_consequence(
            chain, evaluator, method_evidence_id=method_evidence_id,
        )
        response = output_reader(run)
        receipt = FacilityAccidentUncertaintyResponse(run, response, output_names)
        receipt.require_current()
        return ModelOutput(receipt.values, receipt)

    return UncertainModel(evaluate, output_variables, evidence)


__all__ = [
    "FacilityAccidentUncertaintyResponse",
    "facility_accident_consequence_uncertain_model",
]
