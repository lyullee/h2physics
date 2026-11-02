"""Run a prepared source-to-dispersion chain into its receiving consequence owner.

This composes existing admitted owners. It does not calculate exposure, select
receptors, interpret consequence fields, or assign risk probabilities.
"""

from dataclasses import dataclass, field

from .facility_accident_chain import FacilityAccidentChain, FacilityDispersionHandoff
from .facility_consequence import (
    FacilityConsequenceEvaluation,
    evaluate_facility_consequence,
)


@dataclass(frozen=True, slots=True)
class FacilityAccidentConsequenceRun:
    """Retain the accepted chain execution and its exact receiving result."""

    chain: FacilityAccidentChain = field(repr=False, compare=False)
    chain_result: object = field(repr=False, compare=False)
    facility_handoff: FacilityDispersionHandoff = field(repr=False, compare=False)
    consequence: FacilityConsequenceEvaluation = field(repr=False, compare=False)
    _identity: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.chain) is not FacilityAccidentChain:
            raise TypeError("Retain the prepared facility accident chain")
        if type(self.facility_handoff) is not FacilityDispersionHandoff:
            raise TypeError("Retain the chain's admitted source/dispersion handoff")
        if type(self.consequence) is not FacilityConsequenceEvaluation:
            raise TypeError("Retain the existing typed consequence evaluation")
        self.chain_result.require_current()
        outputs = self.chain_result.results
        if (outputs.get("preferred-dispersion") is not self.facility_handoff
                or self.consequence.facility_handoff is not self.facility_handoff):
            raise ValueError("Chain and consequence must retain the same exact final handoff")
        self.facility_handoff.require_current()
        self.consequence.require_current()
        object.__setattr__(self, "_identity", (
            self.chain, self.chain_result, self.facility_handoff, self.consequence,
        ))

    def require_current(self):
        if not self._identity or any(current is not original for current, original in zip(
            (self.chain, self.chain_result, self.facility_handoff, self.consequence),
            self._identity, strict=True,
        )):
            raise ValueError("Facility accident/consequence run lost its original owners")
        self.chain_result.require_current()
        self.facility_handoff.require_current()
        self.consequence.require_current()
        if (self.chain_result.results.get("preferred-dispersion") is not self.facility_handoff
                or self.consequence.facility_handoff is not self.facility_handoff):
            raise ValueError("Facility accident/consequence lineage no longer matches")
        return self


class FacilityAccidentConsequenceError(RuntimeError):
    """Preserve the failure stage and any completed chain/consequence output."""

    def __init__(self, message, *, stage, cause, chain, chain_result=None,
                 facility_handoff=None, consequence_result=None):
        if stage not in {"chain", "handoff", "consequence"}:
            raise ValueError("Unknown facility accident/consequence stage")
        super().__init__(message)
        self.stage = stage
        self.cause = cause
        self.chain = chain
        self.chain_result = chain_result
        self.facility_handoff = facility_handoff
        self.consequence_result = consequence_result


def run_facility_accident_consequence(chain, evaluator, *, method_evidence_id):
    """Run the prepared chain, then pass its exact final handoff downstream.

    Existing chain acceptance is authoritative. The receiving callback runs only
    after ``chain.run()`` has accepted its exact finite source and dispersion
    receipt. Callback or result-admission failures remain failures and retain the
    completed chain result and any native consequence result.
    """
    if type(chain) is not FacilityAccidentChain:
        raise TypeError("Supply the prepared FacilityAccidentChain")
    try:
        chain_result = chain.run()
    except Exception as cause:
        raise FacilityAccidentConsequenceError(
            "Facility source/dispersion chain did not complete", stage="chain",
            cause=cause, chain=chain,
        ) from cause
    try:
        handoff = chain_result.results["preferred-dispersion"]
        if type(handoff) is not FacilityDispersionHandoff:
            raise TypeError("Accepted chain did not return a typed dispersion handoff")
        handoff.require_current()
    except Exception as cause:
        raise FacilityAccidentConsequenceError(
            "Completed chain did not retain a current final handoff", stage="handoff",
            cause=cause, chain=chain, chain_result=chain_result,
        ) from cause
    try:
        consequence = evaluate_facility_consequence(
            handoff, evaluator, method_evidence_id=method_evidence_id,
        )
        return FacilityAccidentConsequenceRun(
            chain, chain_result, handoff, consequence,
        ).require_current()
    except Exception as cause:
        raise FacilityAccidentConsequenceError(
            "Receiving consequence evaluation did not complete and admit", stage="consequence",
            cause=cause, chain=chain, chain_result=chain_result,
            facility_handoff=handoff,
            consequence_result=getattr(cause, "consequence_result", None),
        ) from cause


__all__ = [
    "FacilityAccidentConsequenceError",
    "FacilityAccidentConsequenceRun",
    "run_facility_accident_consequence",
]
