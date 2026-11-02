"""Deferred synthetic contracts for explicit common-cause detector voting."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="kofn-detector-common-cause-reliability",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_kofn_reliability",
        invariants=(
            "heterogeneous conditional-independent failure probabilities yield the exact Poisson-binomial fail-to-alarm probability",
            "a separately evidenced common-cause event disables all voters and combines without double-counting",
            "detector identities, vote threshold, probability basis and mission duration are retained",
            "invalid probabilities, duplicate channels and out-of-range voting thresholds are rejected",
            "the calculation does not infer detector reliability, failure rates, repair, setpoints or event independence evidence",
        ),
    ), ValidationCase(
        identifier="kofn-detector-versioned-trial-evidence",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_versioned_trials",
        invariants=(
            "ordered simultaneous detector outcomes bind a declared source, version, checksum and equal-duration mission window",
            "source row IDs are unique and the returned evidence arrays are immutable and currentness-sealed",
            "empirical system and common-cause frequencies reconstruct from exact observed counts",
            "simultaneous empirical voting results retain channel dependence without an independence assumption",
            "the frequency summary does not claim confidence bounds, future reliability, repair behavior or safety integrity",
        ),
    ), ValidationCase(
        identifier="kofn-detector-exact-binomial-interval",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_trial_interval",
        invariants=(
            "two-sided exact binomial bounds reproduce from source-bound simultaneous trial counts",
            "the selected outcome and caller-declared trial-independence evidence remain explicit",
            "conditional failure intervals exclude declared common-cause trials and fail when no eligible trials remain",
            "invalid confidence levels and unrecognized outcome families are rejected",
            "intervals do not imply annual failure rates, future reliability or safety-integrity qualification",
        ),
    ),)


def validate_kofn_reliability(*, work_directory, **parameters):
    from math import isclose

    from h2physics.detector_reliability import evaluate_kofn_detector_reliability

    del work_directory, parameters
    result = evaluate_kofn_detector_reliability(
        ("d-1", "d-2", "d-3"), (.1, .2, .3), votes_required=2,
        common_cause_failure_probability=.02, mission_duration_s=3600.,
        system_id="synthetic-gas-detection-system", mission_id="synthetic-one-hour-mission",
        voting_logic_id="synthetic-2oo3",
        independent_probability_evidence_ids=("synthetic-d-1", "synthetic-d-2", "synthetic-d-3"),
        common_cause_evidence_id="synthetic-common-cause-input",
    )
    # Independent fail-to-alarm: P(0 alarm) + P(exactly 1 alarm) = 0.098.
    if not isclose(result.conditional_independent_vote_failure_probability, .098,
                   rel_tol=0., abs_tol=2e-15):
        raise AssertionError("Heterogeneous Poisson-binomial failure probability did not close")
    if not isclose(result.total_vote_failure_probability, .11604,
                   rel_tol=0., abs_tol=2e-15):
        raise AssertionError("Common-cause event did not combine with independent vote failure")
    if (result.detector_ids != ("d-1", "d-2", "d-3")
            or any(not isclose(a, b, rel_tol=0., abs_tol=2e-15)
                   for a, b in zip(result.marginal_failure_probabilities, (.118, .216, .314)))):
        raise AssertionError("Detector ordering or modeled marginal probabilities changed")
    invalid = (
        lambda: evaluate_kofn_detector_reliability(
            ("d-1", "d-1"), (.1, .2), votes_required=1,
            common_cause_failure_probability=0., mission_duration_s=10., system_id="s",
            mission_id="m", voting_logic_id="v", independent_probability_evidence_ids=("i1", "i2"),
            common_cause_evidence_id="c"),
        lambda: evaluate_kofn_detector_reliability(
            ("d-1",), (1.1,), votes_required=1,
            common_cause_failure_probability=0., mission_duration_s=10., system_id="s",
            mission_id="m", voting_logic_id="v", independent_probability_evidence_ids=("i1",),
            common_cause_evidence_id="c"),
    )
    for call in invalid:
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Invalid detector reliability input was admitted")
    return ValidationOutcome(True, {
        "detector_count": len(result.detector_ids),
        "votes_required": result.votes_required,
        "conditional_independent_fail_to_alarm": result.conditional_independent_vote_failure_probability,
        "common_cause_failure_probability": result.common_cause_failure_probability,
        "total_fail_to_alarm_probability": result.total_vote_failure_probability,
    }, ("Synthetic reliability algebra only; no hydrogen detector data or safety-integrity level is qualified",))


def validate_versioned_trials(*, work_directory, **parameters):
    from dataclasses import replace
    from math import isclose

    from h2physics.detector_reliability import record_kofn_trial_evidence, summarize_kofn_trials

    del work_directory, parameters
    evidence = record_kofn_trial_evidence(
        ((False, False, False), (True, False, True),
         (True, True, True), (False, True, False)),
        (False, False, True, False),
        source_id="synthetic-detector-demand-record",
        source_version="v1",
        source_sha256="a" * 64,
        trial_design_id="synthetic-equal-one-hour-windows",
        mission_id="synthetic-one-hour-demand",
        mission_duration_s=3600.,
        voting_logic_id="synthetic-2oo3",
        detector_ids=("d-1", "d-2", "d-3"),
        votes_required=2,
        trial_ids=("demand-1", "demand-2", "demand-3", "demand-4"),
    )
    estimate = summarize_kofn_trials(evidence)
    if (estimate.mission_count != 4 or estimate.system_fail_to_alarm_count != 2
            or estimate.common_cause_count != 1 or estimate.conditional_fail_to_alarm_count != 1
            or not isclose(estimate.empirical_system_failure_frequency, .5, rel_tol=0., abs_tol=0.)
            or not isclose(estimate.empirical_common_cause_frequency, .25, rel_tol=0., abs_tol=0.)
            or not isclose(estimate.empirical_conditional_failure_frequency, 1./3., rel_tol=0., abs_tol=1e-16)):
        raise AssertionError("Empirical trial counts do not reproduce their exact frequencies")
    evidence.require_current()
    try:
        evidence.missed_alarm.setflags(write=True)
    except ValueError:
        immutable_outcomes = True
    else:
        raise AssertionError("Issued trial outcomes must be immutable bytes-backed arrays")
    try:
        replace(evidence)
    except ValueError:
        clone_rejected = True
    else:
        raise AssertionError("A dataclass clone must not retain source-reader issuance")
    original_version = evidence.source_version
    object.__setattr__(evidence, "source_version", "tampered")
    try:
        evidence.require_current()
    except ValueError:
        mutation_rejected = True
    else:
        raise AssertionError("Post-issuance source version mutation must be rejected")
    finally:
        object.__setattr__(evidence, "source_version", original_version)
    evidence.require_current()
    return ValidationOutcome(True, {
        "mission_count": estimate.mission_count,
        "system_fail_to_alarm_count": estimate.system_fail_to_alarm_count,
        "empirical_system_failure_frequency": estimate.empirical_system_failure_frequency,
        "common_cause_count": estimate.common_cause_count,
        "empirical_common_cause_frequency": estimate.empirical_common_cause_frequency,
        "source_id": evidence.source_id,
        "source_version": evidence.source_version,
        "source_sha256": evidence.source_sha256,
        "trial_content_sha256": evidence.content_sha256,
        "immutable_outcomes": immutable_outcomes,
        "clone_rejected": clone_rejected,
        "metadata_mutation_rejected": mutation_rejected,
    }, ("Synthetic equal-duration observations only; no confidence interval or future reliability inference",))


def validate_trial_interval(*, work_directory, **parameters):
    from math import isclose

    from h2physics.detector_reliability import interval_for_kofn_trials, record_kofn_trial_evidence

    del work_directory, parameters
    evidence = record_kofn_trial_evidence(
        ((False, False, False), (True, False, True),
         (True, True, True), (False, True, False)),
        (False, False, True, False),
        source_id="synthetic-detector-demand-record", source_version="v1",
        source_sha256="a" * 64, trial_design_id="synthetic-independent-windows",
        mission_id="synthetic-one-hour-demand", mission_duration_s=3600.,
        voting_logic_id="synthetic-2oo3", detector_ids=("d-1", "d-2", "d-3"),
        votes_required=2,
        trial_ids=("demand-1", "demand-2", "demand-3", "demand-4"),
    )
    result = interval_for_kofn_trials(
        evidence, confidence_level=.95,
        independence_evidence_id="synthetic-randomized-independent-demand-windows",
    )
    conditional = interval_for_kofn_trials(
        evidence, outcome="conditional_fail_to_alarm", confidence_level=.95,
        independence_evidence_id="synthetic-randomized-independent-demand-windows",
    )
    if (result.successes != 2 or result.trials != 4
            or not isclose(result.lower, .06758598648854296, rel_tol=0., abs_tol=2e-14)
            or not isclose(result.upper, .932414013511457, rel_tol=0., abs_tol=2e-14)
            or conditional.successes != 1 or conditional.trials != 3
            or not result.require_current()):
        raise AssertionError("Exact trial interval or source/evidence binding did not close")
    original_evidence_id = result.independence_evidence_id
    object.__setattr__(result, "independence_evidence_id", "tampered-evidence")
    try:
        result.require_current()
    except ValueError:
        mutation_rejected = True
    else:
        raise AssertionError("Mutated interval evidence identity must be rejected")
    finally:
        object.__setattr__(result, "independence_evidence_id", original_evidence_id)
    result.require_current()
    rejected = 0
    for kwargs in (
        {"confidence_level": 1.0},
        {"outcome": "annual_rate"},
    ):
        try:
            interval_for_kofn_trials(
                evidence, independence_evidence_id="synthetic-independence-evidence", **kwargs,
            )
        except ValueError:
            rejected += 1
    if rejected != 2:
        raise AssertionError("Invalid interval request was not rejected")
    return ValidationOutcome(True, {
        "successes": result.successes, "trials": result.trials,
        "confidence_level": result.confidence_level,
        "lower": result.lower, "upper": result.upper,
        "conditional_successes": conditional.successes,
        "conditional_trials": conditional.trials,
        "independence_evidence_id": result.independence_evidence_id,
        "evidence_id_mutation_rejected": mutation_rejected,
    }, ("Synthetic binomial interval only; independence is caller-evidenced, not inferred",))
