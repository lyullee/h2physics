"""Deferred contracts for caller-owned dependence and retained joint cases."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="uncertainty-joint-scenario-lineage",
        profile="joint-uncertainty",
        entrypoint=__name__ + ":validate_joint_scenario_lineage",
        invariants=(
            "caller-supplied anticorrelation is retained without marginal independence assumptions",
            "PCG64 seed and mapping definition reproduce the exact ordered scenarios and identities",
            "deterministic outputs bind one-to-one to scenario and source row identities",
            "a failed physical case retains its actual scenario id, inputs and completed prefix",
            "no failure is replaced, dropped or converted to an event frequency",
        ),
    ),)


def _anticorrelated_sampler(rng, count):
    first = rng.random(count)
    return np.column_stack((first, 1.0 - first))


def _first_case_failure_sampler(rng, count):
    values = _anticorrelated_sampler(rng, count)
    values[0, 0] = 0.9
    values[0, 1] = 0.1
    return values


def _closure_model(parameters):
    from h2physics.uncertainty import ModelOutput

    return ModelOutput(
        {"paired_sum": parameters["fraction_a"] + parameters["fraction_b"]},
        raw=(parameters["fraction_a"], parameters["fraction_b"]),
    )


def _failing_model(parameters):
    from h2physics.uncertainty import ModelOutput

    if parameters["fraction_a"] > 0.8:
        raise RuntimeError("authored physical-case failure sentinel")
    return ModelOutput({"paired_sum": 1.0}, raw=parameters)


def _space(sampler, sampler_id):
    from h2physics.core import Origin
    from h2physics.observations import Variable
    from h2physics.uncertainty import JointParameterDomain, JointScenarioSpace

    return JointScenarioSpace(
        parameters=(
            JointParameterDomain(
                Variable("fraction_a", "mole_fraction", "1", "mixture-A"),
                "synthetic-joint-source", Origin.SYNTHETIC, 0.0, 1.0,
            ),
            JointParameterDomain(
                Variable("fraction_b", "mole_fraction", "1", "mixture-B"),
                "synthetic-joint-source", Origin.SYNTHETIC, 0.0, 1.0,
            ),
        ),
        sampler=sampler,
        sampler_id=sampler_id,
        sampler_revision_id="authored-mapping-revision-1",
        dependence_evidence_id="authored-perfect-anticorrelation",
        source_id="synthetic-verification-only",
        space_id=sampler_id,
    )


def validate_joint_scenario_lineage(*, work_directory, **parameters):
    from h2physics.core import Origin
    from h2physics.observations import Variable
    from h2physics.uncertainty import (
        UncertainModel,
        UncertaintyEvidence,
        UncertaintyEvaluationError,
        joint_scenario_design,
        propagate_joint,
    )

    del work_directory, parameters
    model = UncertainModel(
        _closure_model,
        (Variable("paired_sum", "mole_fraction", "1", "synthetic-pair"),),
        UncertaintyEvidence(
            "synthetic-joint-contract", "revision-1", "pure-deterministic-map",
            "synthetic-method-contract-only", Origin.SYNTHETIC,
        ),
    )
    space = _space(_anticorrelated_sampler, "synthetic-anticorrelated-map")
    design = joint_scenario_design(space, count=32, seed=42)
    replay = joint_scenario_design(space, count=32, seed=42)
    assert np.array_equal(design.values, replay.values)
    assert design.scenario_ids == replay.scenario_ids
    assert np.all(design.values[:, 0] + design.values[:, 1] == 1.0)
    result = propagate_joint(design, model)
    result.require_current()
    assert np.array_equal(result.values[:, 0], np.ones(32))
    assert len({case.scenario_id for case in result.evaluations}) == 32

    failure_space = _space(_first_case_failure_sampler, "synthetic-failure-map")
    failure_design = joint_scenario_design(failure_space, count=4, seed=7)
    failure_model = UncertainModel(
        _failing_model,
        model.outputs,
        model.evidence,
    )
    try:
        propagate_joint(failure_design, failure_model)
    except UncertaintyEvaluationError as error:
        assert error.scenario_id == failure_design.scenario_ids[0]
        assert error.case_index == 0 and error.completed_evaluations == ()
        assert error.parameters["fraction_a"] == 0.9
        assert error.__cause__ is not None
    else:
        raise AssertionError("Joint propagation hid the authored physical failure")
    return ValidationOutcome(True, {
        "scenario_count": len(result.evaluations),
        "reproducible_seed": design.seed,
        "perfect_pair_sum_error": float(np.max(np.abs(result.values[:, 0] - 1.0))),
        "failed_scenario_identity_retained": True,
    }, (
        "Synthetic dependence wiring only; not empirical covariance, probability, or facility qualification.",
    ))
