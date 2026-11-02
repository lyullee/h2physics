"""Explicit probability model for common-cause-aware k-of-n gas detection."""

import hashlib
import re
from dataclasses import dataclass, field
from math import fsum, isclose

import numpy as np

from .core import finite, immutable_array

_PENDING_TRIAL_ISSUERS: set[object] = set()


@dataclass(frozen=True, slots=True)
class KofNDetectorReliability:
    """Fail-to-alarm probability for an ordered detector vote in one mission."""

    system_id: str
    mission_id: str
    voting_logic_id: str
    independent_probability_evidence_ids: tuple[str, ...]
    common_cause_evidence_id: str
    detector_ids: tuple[str, ...]
    votes_required: int
    mission_duration_s: float
    independent_failure_probabilities: tuple[float, ...]
    common_cause_failure_probability: float
    conditional_independent_vote_failure_probability: float
    total_vote_failure_probability: float
    marginal_failure_probabilities: tuple[float, ...]

    def __post_init__(self):
        for name in ("system_id", "mission_id", "voting_logic_id", "common_cause_evidence_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must identify its declared evidence or scope")
        identifiers = tuple(self.detector_ids)
        probability_evidence = tuple(self.independent_probability_evidence_ids)
        probabilities = tuple(self.independent_failure_probabilities)
        marginals = tuple(self.marginal_failure_probabilities)
        if (not identifiers or len(set(identifiers)) != len(identifiers)
                or any(not isinstance(item, str) or not item.strip() for item in identifiers)):
            raise ValueError("Detector identities must be nonempty, ordered and unique")
        if len(probabilities) != len(identifiers) or len(marginals) != len(identifiers):
            raise ValueError("Detector probabilities must align with the declared detector order")
        if (len(probability_evidence) != len(identifiers)
                or any(not isinstance(item, str) or not item.strip()
                       for item in probability_evidence)):
            raise ValueError("Every detector probability needs its own evidence identity")
        if (isinstance(self.votes_required, bool)
                or not isinstance(self.votes_required, int)
                or not 1 <= self.votes_required <= len(identifiers)):
            raise ValueError("votes_required must lie from one through the detector count")
        finite(self.mission_duration_s, "mission_duration_s", positive=True)
        q = tuple(_probability(value, f"independent failure probability[{i}]")
                  for i, value in enumerate(probabilities))
        common = _probability(self.common_cause_failure_probability,
                              "common-cause failure probability")
        independent_system = _poisson_binomial_miss(q, self.votes_required)
        total_system = common + (1. - common) * independent_system
        expected_marginals = tuple(common + (1. - common) * value for value in q)
        conditional = _probability(
            self.conditional_independent_vote_failure_probability,
            "conditional_independent_vote_failure_probability",
        )
        total = _probability(self.total_vote_failure_probability,
                             "total_vote_failure_probability")
        frozen_marginals = tuple(_probability(value, f"marginal failure probability[{i}]")
                                 for i, value in enumerate(marginals))
        if (abs(conditional-independent_system) > 5e-13
                or abs(total-total_system) > 5e-13
                or any(abs(a-b) > 5e-13 for a, b in zip(frozen_marginals, expected_marginals))):
            raise ValueError("Reliability result does not reconstruct from its retained probabilities")
        object.__setattr__(self, "detector_ids", identifiers)
        object.__setattr__(self, "independent_probability_evidence_ids", probability_evidence)
        object.__setattr__(self, "independent_failure_probabilities", q)
        object.__setattr__(self, "common_cause_failure_probability", common)
        object.__setattr__(self, "conditional_independent_vote_failure_probability", conditional)
        object.__setattr__(self, "total_vote_failure_probability", total)
        object.__setattr__(self, "marginal_failure_probabilities", frozen_marginals)


def _probability(value, name):
    result = finite(value, name)
    if not 0. <= result <= 1.:
        raise ValueError(f"{name} must lie in [0, 1]")
    return result


def _poisson_binomial_miss(failure_probabilities, votes_required):
    """Probability of fewer than k successes under independent Bernoulli trials."""
    # Retain only states with fewer than k alarms; transitions to k are absorbing
    # success and need not be stored for a fail-to-alarm probability.
    states = [1.]
    for failure in failure_probabilities:
        updated = [0.] * min(votes_required, len(states) + 1)
        updated[0] = states[0] * failure
        for successes in range(1, len(updated)):
            prior_same = states[successes] if successes < len(states) else 0.
            updated[successes] = (
                prior_same * failure + states[successes - 1] * (1. - failure)
            )
        states = updated
    return min(1., max(0., fsum(states)))


def evaluate_kofn_detector_reliability(
    detector_ids,
    independent_failure_probabilities,
    *,
    votes_required,
    common_cause_failure_probability,
    mission_duration_s,
    system_id,
    mission_id,
    voting_logic_id,
    independent_probability_evidence_ids,
    common_cause_evidence_id,
) -> KofNDetectorReliability:
    """Evaluate fail-to-alarm for a k-of-n vote with an explicit common-cause event.

    Per-detector probabilities mean independent failure during the declared
    mission, conditional on no modeled common-cause event. The common-cause
    event disables all detectors with the separate supplied probability. No
    event rate, repair model, setpoint, dependence law or evidence is inferred.
    """
    identifiers = tuple(detector_ids)
    evidence_ids = tuple(independent_probability_evidence_ids)
    probabilities = tuple(independent_failure_probabilities)
    if (not identifiers or len(probabilities) != len(identifiers)
            or len(evidence_ids) != len(identifiers)
            or len(set(identifiers)) != len(identifiers)):
        raise ValueError("Supply one uniquely identified failure probability per detector")
    if any(not isinstance(item, str) or not item.strip() for item in evidence_ids):
        raise ValueError("Supply one evidence identity for each detector probability")
    q = tuple(_probability(value, f"independent failure probability[{i}]")
              for i, value in enumerate(probabilities))
    if (isinstance(votes_required, bool) or not isinstance(votes_required, int)
            or not 1 <= votes_required <= len(q)):
        raise ValueError("votes_required must lie from one through the detector count")
    common = _probability(common_cause_failure_probability,
                          "common-cause failure probability")
    mission = finite(mission_duration_s, "mission_duration_s", positive=True)
    conditional = _poisson_binomial_miss(q, votes_required)
    total = common + (1. - common) * conditional
    marginals = tuple(common + (1. - common) * value for value in q)
    return KofNDetectorReliability(
        system_id, mission_id, voting_logic_id, evidence_ids, common_cause_evidence_id,
        identifiers, votes_required, mission, q, common,
        conditional, total, marginals,
    )


@dataclass(frozen=True, slots=True)
class KofNTrialEvidence:
    """One immutable aligned sample set for identical-duration detector demands."""

    source_id: str
    source_version: str
    source_sha256: str
    trial_design_id: str
    mission_id: str
    mission_duration_s: float
    voting_logic_id: str
    detector_ids: tuple[str, ...]
    votes_required: int
    trial_ids: tuple[str, ...]
    missed_alarm: np.ndarray
    common_cause_outage: np.ndarray
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _content_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_TRIAL_ISSUERS:
            raise ValueError("Use record_kofn_trial_evidence to issue source-bound trials")
        _PENDING_TRIAL_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        for name in ("source_id", "source_version", "trial_design_id", "mission_id", "voting_logic_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        finite(self.mission_duration_s, "mission_duration_s", positive=True)
        detector_ids, trial_ids = tuple(self.detector_ids), tuple(self.trial_ids)
        if (not detector_ids or len(set(detector_ids)) != len(detector_ids)
                or any(not isinstance(item, str) or not item.strip() for item in detector_ids)):
            raise ValueError("Detector IDs must be ordered, nonempty and unique")
        if (not trial_ids or len(set(trial_ids)) != len(trial_ids)
                or any(not isinstance(item, str) or not item.strip() for item in trial_ids)):
            raise ValueError("Trial IDs must be ordered, nonempty and unique")
        if (isinstance(self.votes_required, bool) or not isinstance(self.votes_required, int)
                or not 1 <= self.votes_required <= len(detector_ids)):
            raise ValueError("votes_required must lie from one through the detector count")
        missed = immutable_array(self.missed_alarm, dtype=bool, name="missed_alarm")
        common = immutable_array(self.common_cause_outage, dtype=bool, name="common_cause_outage")
        if missed.shape != (len(trial_ids), len(detector_ids)) or common.shape != (len(trial_ids),):
            raise ValueError("Trial outcomes must align exactly to trial and detector identity order")
        if np.any(common & ~np.all(missed, axis=1)):
            raise ValueError("A declared common-cause outage must mark every detector as failed")
        object.__setattr__(self, "detector_ids", detector_ids)
        object.__setattr__(self, "trial_ids", trial_ids)
        object.__setattr__(self, "missed_alarm", missed)
        object.__setattr__(self, "common_cause_outage", common)
        object.__setattr__(self, "_content_sha256", self._content_digest())

    def _content_digest(self):
        digest = hashlib.sha256(repr((
            self.source_id, self.source_version, self.source_sha256, self.trial_design_id,
            self.mission_id, self.mission_duration_s, self.voting_logic_id,
            self.detector_ids, self.votes_required, self.trial_ids,
            self.missed_alarm.shape, self.missed_alarm.dtype.str,
            self.common_cause_outage.shape, self.common_cause_outage.dtype.str,
        )).encode("utf-8"))
        digest.update(self.missed_alarm.tobytes())
        digest.update(self.common_cause_outage.tobytes())
        return digest.hexdigest()

    def require_current(self):
        if self._content_digest() != self._content_sha256:
            raise ValueError("Trial evidence metadata or outcomes changed after issuance")
        return self

    @property
    def content_sha256(self):
        return self._content_sha256


def record_kofn_trial_evidence(
    missed_alarm,
    common_cause_outage,
    *,
    source_id,
    source_version,
    source_sha256,
    trial_design_id,
    mission_id,
    mission_duration_s,
    voting_logic_id,
    detector_ids,
    votes_required,
    trial_ids,
) -> KofNTrialEvidence:
    """Issue aligned, hash-bound observed outcomes without fitting a rate law.

    Every row is one caller-defined demand window with the same mission
    duration. `True` in missed_alarm means that channel did not alarm within
    that window. A common-cause row must show failure of all channels. The
    supplied source checksum is retained as provenance, not downloaded or
    independently revalidated by this function.
    """
    raw_missed, raw_common = np.asarray(missed_alarm), np.asarray(common_cause_outage)
    if raw_missed.dtype.kind != "b" or raw_common.dtype.kind != "b":
        raise ValueError("Observed alarm and common-cause states must be explicit booleans")
    token = object()
    _PENDING_TRIAL_ISSUERS.add(token)
    try:
        return KofNTrialEvidence(
            source_id, source_version, source_sha256, trial_design_id, mission_id,
            mission_duration_s, voting_logic_id, tuple(detector_ids), votes_required,
            tuple(trial_ids), raw_missed, raw_common, _issuer_token=token,
        )
    except Exception:
        _PENDING_TRIAL_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class KofNTrialReliabilityEstimate:
    """Descriptive frequencies from observed simultaneous mission trials."""

    evidence: KofNTrialEvidence

    def __post_init__(self):
        if type(self.evidence) is not KofNTrialEvidence:
            raise TypeError("Retain the original reader-issued trial evidence")
        self.evidence.require_current()

    def require_current(self):
        self.evidence.require_current()
        return self

    def _current_evidence(self):
        self.evidence.require_current()
        return self.evidence

    @property
    def mission_count(self):
        return len(self._current_evidence().trial_ids)

    @property
    def common_cause_count(self):
        return int(np.count_nonzero(self._current_evidence().common_cause_outage))

    @property
    def system_fail_to_alarm_count(self):
        evidence = self._current_evidence()
        alarm_count = len(evidence.detector_ids) - np.sum(evidence.missed_alarm, axis=1)
        return int(np.count_nonzero(alarm_count < evidence.votes_required))

    @property
    def conditional_fail_to_alarm_count(self):
        evidence = self._current_evidence()
        not_common = ~evidence.common_cause_outage
        alarm_count = len(evidence.detector_ids) - np.sum(evidence.missed_alarm, axis=1)
        return int(np.count_nonzero(not_common & (alarm_count < evidence.votes_required)))

    @property
    def empirical_system_failure_frequency(self):
        return self.system_fail_to_alarm_count / self.mission_count

    @property
    def empirical_common_cause_frequency(self):
        return self.common_cause_count / self.mission_count

    @property
    def empirical_conditional_failure_frequency(self):
        count = self.mission_count - self.common_cause_count
        if count == 0:
            raise ValueError("No non-common-cause trials support a conditional frequency")
        return self.conditional_fail_to_alarm_count / count


def summarize_kofn_trials(evidence: KofNTrialEvidence) -> KofNTrialReliabilityEstimate:
    """Summarize empirical counts; does not assume channel independence or extrapolate."""
    if type(evidence) is not KofNTrialEvidence:
        raise TypeError("Pass source-bound KofNTrialEvidence")
    evidence.require_current()
    return KofNTrialReliabilityEstimate(evidence)


@dataclass(frozen=True, slots=True)
class KofNTrialConfidenceInterval:
    """Exact binomial interval bound to observed trials and caller evidence."""

    evidence: KofNTrialEvidence
    outcome: str
    successes: int
    trials: int
    confidence_level: float
    lower: float
    upper: float
    independence_evidence_id: str
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.evidence) is not KofNTrialEvidence:
            raise TypeError("Retain the original source-bound trial evidence")
        self.evidence.require_current()
        if self.outcome not in {"system_fail_to_alarm", "common_cause", "conditional_fail_to_alarm"}:
            raise ValueError("Unsupported trial outcome")
        if not isinstance(self.independence_evidence_id, str) or not self.independence_evidence_id.strip():
            raise ValueError("Declare the evidence for independent, identically distributed trial windows")
        if (isinstance(self.successes, bool) or isinstance(self.trials, bool)
                or not isinstance(self.successes, int) or not isinstance(self.trials, int)
                or self.trials < 1 or not 0 <= self.successes <= self.trials):
            raise ValueError("Require integer successes within a positive trial count")
        level = finite(self.confidence_level, "confidence_level")
        if not 0. < level < 1.:
            raise ValueError("confidence_level must lie strictly between zero and one")
        lower, upper = _clopper_pearson(self.successes, self.trials, level)
        if (not isclose(self.lower, lower, rel_tol=2e-13, abs_tol=2e-15)
                or not isclose(self.upper, upper, rel_tol=2e-13, abs_tol=2e-15)):
            raise ValueError("Interval bounds do not match the retained binomial counts")
        successes, trials = _trial_outcome_counts(self.evidence, self.outcome)
        if (self.successes != successes or self.trials != trials
                or not isclose(self.confidence_level, level, rel_tol=0., abs_tol=0.)):
            raise ValueError("Interval counts do not match the retained trial evidence")
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (
            id(self.evidence), self.outcome, self.successes, self.trials,
            self.confidence_level, self.lower, self.upper, self.independence_evidence_id,
        )

    def require_current(self):
        self.evidence.require_current()
        successes, trials = _trial_outcome_counts(self.evidence, self.outcome)
        lower, upper = _clopper_pearson(self.successes, self.trials, self.confidence_level)
        if (self.successes != successes or self.trials != trials
                or not isclose(self.lower, lower, rel_tol=2e-13, abs_tol=2e-15)
                or not isclose(self.upper, upper, rel_tol=2e-13, abs_tol=2e-15)
                or self._content() != self._seal):
            raise ValueError("Confidence interval no longer matches the source-bound counts")
        return self


def _clopper_pearson(successes, trials, confidence_level):
    """Two-sided equal-tailed exact binomial interval using beta quantiles."""
    from scipy.special import betaincinv

    tail = (1. - confidence_level) / 2.
    lower = 0. if successes == 0 else float(betaincinv(successes, trials - successes + 1, tail))
    upper = 1. if successes == trials else float(
        betaincinv(successes + 1, trials - successes, 1. - tail)
    )
    return lower, upper


def _trial_outcome_counts(evidence, outcome):
    if outcome == "system_fail_to_alarm":
        alarms = len(evidence.detector_ids) - np.sum(evidence.missed_alarm, axis=1)
        return int(np.count_nonzero(alarms < evidence.votes_required)), len(evidence.trial_ids)
    if outcome == "common_cause":
        return int(np.count_nonzero(evidence.common_cause_outage)), len(evidence.trial_ids)
    if outcome == "conditional_fail_to_alarm":
        eligible = ~evidence.common_cause_outage
        alarms = len(evidence.detector_ids) - np.sum(evidence.missed_alarm, axis=1)
        return int(np.count_nonzero(eligible & (alarms < evidence.votes_required))), int(
            np.count_nonzero(eligible)
        )
    raise ValueError("Unsupported trial outcome")


def interval_for_kofn_trials(
    evidence: KofNTrialEvidence,
    *,
    outcome: str = "system_fail_to_alarm",
    confidence_level: float = 0.95,
    independence_evidence_id: str,
) -> KofNTrialConfidenceInterval:
    """Calculate an exact interval only after caller declares trial sampling evidence.

    The binomial interval concerns a probability per identically designed,
    independent demand window. This function cannot verify that assumption;
    it is unsuitable for repeated/serially dependent windows without a sampling
    model. The interval is not an annual failure rate or SIL qualification.
    """
    if type(evidence) is not KofNTrialEvidence:
        raise TypeError("Pass source-bound KofNTrialEvidence")
    evidence.require_current()
    if outcome not in {"system_fail_to_alarm", "common_cause", "conditional_fail_to_alarm"}:
        raise ValueError("outcome must be system_fail_to_alarm, common_cause, or conditional_fail_to_alarm")
    successes, trials = _trial_outcome_counts(evidence, outcome)
    if trials < 1:
        raise ValueError("Selected outcome has no eligible trials")
    level = finite(confidence_level, "confidence_level")
    if not 0. < level < 1.:
        raise ValueError("confidence_level must lie strictly between zero and one")
    lower, upper = _clopper_pearson(successes, trials, level)
    return KofNTrialConfidenceInterval(
        evidence, outcome, successes, trials, level, lower, upper,
        independence_evidence_id,
    )
