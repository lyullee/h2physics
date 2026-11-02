"""Deferred dependent-input contract using the existing native QMC engine."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="joint-input-transform-propagation", profile="model-selection",
        entrypoint=__name__ + ":validate_joint",
        invariants=("joint transform preserves explicit law/scenario identity",
                    "dependent physical inputs reuse native latent QMC samples",
                    "original model responses and failed input/prefix survive propagation",
                    "joint propagation receipt cannot be directly fabricated or cloned with altered scenario identity",
                    "nested native propagation receipt cannot be directly constructed or cloned",
                    "native Sobol result cannot be directly fabricated or cloned with altered indices",
                    "joint result evaluation rows remain bound to the exact latent design and original outputs",
                    "ordinary mutable transform/model callback configuration changes invalidate retained lineage",
                    "wrong latent-space identity and out-of-domain transform are rejected",
                    "scenario output reader retains original execution and target selection",
                    "scenario failures preserve the original dependency failure receipt"),
    ),)


def validate_joint(*, work_directory, **parameters):
    del work_directory, parameters
    from math import isclose

    from scipy.stats import uniform

    from h2physics.core import Origin
    from h2physics.observations import Variable
    from h2physics.research.joint_uncertainty import (
        JointEvaluationError,
        JointParameter,
        JointParameterSpace,
        ScenarioUncertaintyError,
        joint_qmc_design,
        propagate_joint,
        scenario_uncertain_model,
    )
    from h2physics.uncertainty import (
        IndependentParameterSpace,
        ModelOutput,
        ParameterDistribution,
        PropagationResult,
        SobolSensitivity,
        UncertainModel,
        UncertaintyEvidence,
        sobol_sensitivity,
    )

    latent = IndependentParameterSpace((ParameterDistribution(
        Variable("u", "latent_coordinate", "1"), uniform(), "uniform-v1",
        "authored-latent-law", Origin.SYNTHETIC, 0., 1.),),
        "one-latent-coordinate", "joint-reference-latent")
    space = JointParameterSpace(latent, (
        JointParameter(Variable("x", "reference_parameter", "1"), 0., 1., "x-law"),
        JointParameter(Variable("y", "reference_parameter", "1"), 0., 2., "y-law"),
    ), lambda values: {"x": values["u"], "y": 2*values["u"]},
        "authored-perfect-linear-dependence", "y-equals-two-x", "transform-v1")
    raw = object()
    evidence = UncertaintyEvidence("joint-reference", "v1", "stateless-callback",
                                   "finite-ensemble-only", Origin.SYNTHETIC)
    model = UncertainModel(lambda values: ModelOutput({"z": values["x"]+values["y"]}, raw),
                           (Variable("z", "reference_response", "1"),), evidence)
    design = joint_qmc_design(space, power=2, seed=9)
    result = propagate_joint(space, design, model, scenario_id="reference-scenario")
    assert result.space is space and result.model is model
    assert result.scenario_id == "reference-scenario"
    assert result.require_current() is result
    try:
        from dataclasses import replace
        replace(result, scenario_id="forged-scenario")
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A copied joint propagation receipt resealed a changed scenario identity")
    try:
        replace(result.latent_propagation)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A copied native propagation receipt was reissued without QMC execution")
    try:
        PropagationResult(
            result.latent_propagation.design,
            result.latent_propagation.model,
            result.latent_propagation.evaluations,
            result.latent_propagation.values,
        )
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("A caller-constructed propagation receipt was accepted")
    sensitivity_space = IndependentParameterSpace((
        ParameterDistribution(Variable("a", "reference_parameter", "1"), uniform(),
                              "uniform-a", "synthetic-a", Origin.SYNTHETIC, 0., 1.),
        ParameterDistribution(Variable("b", "reference_parameter", "1"), uniform(),
                              "uniform-b", "synthetic-b", Origin.SYNTHETIC, 0., 1.),
    ), "authored-independent-uniforms", "sobol-receipt-reference")
    sensitivity_model = UncertainModel(
        lambda values: {"z": values["a"] + 2*values["b"]}, model.outputs, evidence
    )
    sensitivity = sobol_sensitivity(sensitivity_space, sensitivity_model, power=2, seed=12)
    assert sensitivity.require_current() is sensitivity
    for forged in (
        lambda: SobolSensitivity(
            sensitivity.space, sensitivity.space_sha256, sensitivity.model,
            sensitivity.native_result, sensitivity.evaluations, sensitivity.batches,
            sensitivity.first_order, sensitivity.total_order, sensitivity.variance_resolved,
            sensitivity.n_base, sensitivity.seed,
        ),
        lambda: replace(sensitivity, first_order=sensitivity.total_order + 1.),
    ):
        try:
            forged()
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("A fabricated or cloned Sobol receipt was accepted")
    for case in result.evaluations:
        receipt = case.raw
        assert receipt.joint_parameters["y"] == 2*receipt.joint_parameters["x"]
        assert receipt.original_response.raw is raw
        assert isclose(case.outputs["z"], 3*receipt.joint_parameters["x"], rel_tol=1e-14)
    transform_config = [2.]
    callback_config = [1.]

    def configured_transform(values):
        return {"x": values["u"], "y": transform_config[0]*values["u"]}

    def configured_model(values):
        return {"z": callback_config[0]*values["x"]}

    configured_space = replace(space, transform=configured_transform,
                               transform_revision_id="mutable-config-transform")
    configured_receipt = propagate_joint(
        configured_space, joint_qmc_design(configured_space, power=2, seed=10),
        UncertainModel(configured_model, model.outputs, evidence),
        scenario_id="mutable-callback-config",
    )
    transform_config[0] = 1.5
    try:
        configured_receipt.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A changed transform closure left its old receipt current")
    callback_configured_receipt = propagate_joint(
        configured_space, joint_qmc_design(configured_space, power=2, seed=11),
        UncertainModel(configured_model, model.outputs, evidence),
        scenario_id="mutable-model-callback-config",
    )
    callback_config[0] = 2.
    try:
        callback_configured_receipt.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("A changed model callback closure left its old receipt current")
    original_error = RuntimeError("physical-model-failure")
    count = 0

    def failing(values):
        nonlocal count
        count += 1
        if count == 2:
            raise original_error
        return {"z": values["x"]}

    try:
        propagate_joint(space, design, UncertainModel(failing, model.outputs, evidence),
                        scenario_id="failure-scenario")
    except JointEvaluationError as error:
        assert error.cause is original_error
        assert error.joint_parameters["y"] == 2*error.joint_parameters["x"]
        assert len(error.propagation_error.completed_evaluations) == 1
    else:
        raise AssertionError("Joint physical failure was discarded")
    try:
        space.transform_parameters({"u": 2.})
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-domain joint input was admitted")
    from dataclasses import replace

    import numpy as np

    for invalid in (True, np.array([0.5]), np.array(0.5), float("nan")):
        invalid_space = replace(space, transform=lambda values: {"x": invalid, "y": 1.})
        try:
            invalid_space.transform_parameters({"u": .5})
        except ValueError:
            pass
        else:
            raise AssertionError("A nonfinite or nonscalar joint parameter was admitted")
    from h2physics.scenarios import (
        OperationalScenario,
        ScenarioExecutionError,
        ScenarioNode,
        ScenarioValue,
    )

    built = []

    def factory(values):
        graph = OperationalScenario("joint-operational-scenario", (
            ScenarioNode("response", lambda value: value, {"value": ScenarioValue(values["x"])},
                         "declared-response-evidence"),
            ScenarioNode("unrelated", lambda: (_ for _ in ()).throw(RuntimeError("must-not-run")),
                         {}, "unrelated-evidence"),
        ))
        built.append(graph)
        return graph

    scenario_model = scenario_uncertain_model(
        scenario_factory=factory, output_reader=lambda execution: {"z": execution.results["response"]},
        outputs=model.outputs, evidence=evidence, targets=("response",),
    )
    assert built == []
    scenario_response = scenario_model.callback({"x": 0.25})
    assert scenario_response.values["z"] == 0.25
    assert scenario_response.raw.scenario is built[0]
    assert tuple(scenario_response.raw.execution.results) == ("response",)
    failing_scenario_model = scenario_uncertain_model(
        scenario_factory=factory, output_reader=lambda execution: {"z": 0.},
        outputs=model.outputs, evidence=evidence,
    )
    try:
        failing_scenario_model.callback({"x": 0.25})
    except ScenarioUncertaintyError as error:
        assert error.stage == "scenario execution"
        assert isinstance(error.scenario_error, ScenarioExecutionError)
        assert len(error.scenario_error.completed) == 1
    else:
        raise AssertionError("Original scenario execution failure was discarded")
    return ValidationOutcome(True, {"joint_cases": len(result.evaluations)},
                             ("Authored dependent-input software contract; no annual frequency implied",))
