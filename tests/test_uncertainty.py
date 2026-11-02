"""Statistical limits and model-failure boundaries, not parameter validation."""

from dataclasses import replace

import numpy as np
import pytest
from scipy import stats

from h2physics.core import Origin
from h2physics.observations import Variable
from h2physics.uncertainty import (
    IndependentParameterSpace,
    ModelOutput,
    ParameterDistribution,
    UncertainModel,
    UncertaintyDesignError,
    UncertaintyEvaluationError,
    UncertaintyEvidence,
    independent_qmc_design,
    propagate,
    sobol_sensitivity,
)


def space(count=2):
    return IndependentParameterSpace(
        tuple(
            ParameterDistribution(
                Variable(f"x{i}", "authored_dimensionless_input", "1", "authored-uniform"),
                stats.uniform(loc=0.0, scale=1.0),
                "authored-uniform01",
                "authored-limit",
                Origin.SYNTHETIC,
                0.0,
                1.0,
            )
            for i in range(count)
        ),
        "authored-independent-inputs",
        "original-analytic-case",
    )


def model(callback, names=("value",)):
    return UncertainModel(
        callback,
        tuple(Variable(n, "authored_response", "1") for n in names),
        UncertaintyEvidence(
            "analytic", "original1", "stateless-callable", "authored-not-measured", Origin.SYNTHETIC
        ),
    )


def test_native_qmc_complete_design_reproducible_and_meaningful():
    parameters = space()
    a = independent_qmc_design(parameters, power=5, seed=274)
    b = independent_qmc_design(parameters, power=5, seed=274)
    c = independent_qmc_design(parameters, power=5, seed=275)
    np.testing.assert_array_equal(a.values, b.values)
    assert not np.array_equal(a.values, c.values)
    assert a.native_engine.num_generated == 32
    assert a.values.shape == (32, 2)
    assert not a.values.flags.writeable and not a.unit_cube.flags.writeable
    assert a.space_sha256 == parameters.content_sha256


def test_propagation_preserves_raw_objects_and_declared_response_order():
    design = independent_qmc_design(space(), power=5, seed=48)
    raw = object()
    response = model(lambda p: ModelOutput({"b": p["x1"], "a": p["x0"]}, raw), ("a", "b"))
    result = propagate(design, response)
    np.testing.assert_array_equal(result.values, design.values)
    assert result.model is response and result.design is design
    assert all(case.raw is raw for case in result.evaluations)
    assert not result.values.flags.writeable
    with pytest.raises(TypeError):
        result.evaluations[0].parameters["x0"] = 0.0


def test_qmc_summary_uniform_linear_moments_and_explicit_quantiles():
    result = propagate(
        independent_qmc_design(space(1), power=9, seed=36),
        model(lambda p: {"value": 2 + 3 * p["x0"]}),
    )
    summary = result.summarize((0.0, 0.5, 1.0))
    assert summary.mean[0] == pytest.approx(3.5, abs=1e-6)
    assert summary.population_variance[0] == pytest.approx(0.75, abs=1e-5)
    assert summary.quantiles[1, 0] == pytest.approx(3.5, abs=0.01)
    assert summary.quantiles[0, 0] >= 2 and summary.quantiles[-1, 0] <= 5
    assert not summary.quantiles.flags.writeable


def test_native_additive_sobol_indices_match_independent_variances():
    result = sobol_sensitivity(
        space(), model(lambda p: {"value": p["x0"] + 3 * p["x1"]}), power=10, seed=83
    )
    # Var(x0):Var(3*x1)=1:9 for independent uniform inputs.
    np.testing.assert_allclose(result.first_order, [[0.1, 0.9]], atol=0.002)
    np.testing.assert_allclose(result.total_order, [[0.1, 0.9]], atol=0.002)
    assert result.variance_resolved.tolist() == [True]
    assert result.native_result is not None and len(result.evaluations) == 4096
    assert len(result.batches) == 3
    # Native centering must not overwrite physical responses retained by the host.
    for _, values in result.batches:
        assert np.all(values >= 0)
    assert not result.first_order.flags.writeable


def test_native_product_sobol_retains_interaction_and_singleton_shapes():
    result = sobol_sensitivity(
        space(), model(lambda p: {"value": p["x0"] * p["x1"]}), power=10, seed=381
    )
    # E[x]=1/2 and E[x²]=1/3 give Var(x*y)=7/144.
    np.testing.assert_allclose(result.first_order, [[3 / 7, 3 / 7]], atol=0.003)
    np.testing.assert_allclose(result.total_order, [[4 / 7, 4 / 7]], atol=0.003)
    one = sobol_sensitivity(
        space(1),
        model(lambda p: {"x": p["x0"], "square": p["x0"] ** 2}, ("x", "square")),
        power=7,
        seed=8,
    )
    assert one.first_order.shape == one.total_order.shape == (2, 1)


def test_actual_native_single_input_single_output_failure_retains_all_cases():
    # The native tuple-wide squeeze returns scalars, then native item assignment
    # fails. Do not add dummy outputs or substitute another estimator.
    with pytest.raises(UncertaintyEvaluationError) as failure:
        sobol_sensitivity(space(1), model(lambda p: {"value": p["x0"]}), power=4, seed=8)
    assert isinstance(failure.value.__cause__, TypeError)
    assert "item assignment" in str(failure.value)
    assert len(failure.value.completed_evaluations) == 48


def test_constant_output_has_no_identifiable_variance_denominator():
    result = sobol_sensitivity(
        space(),
        model(lambda p: {"fixed": 17.0, "variable": p["x0"]}, ("fixed", "variable")),
        power=5,
        seed=3,
    )
    assert result.variance_resolved.tolist() == [False, True]
    assert np.isnan(result.first_order[0]).all() and np.isnan(result.total_order[0]).all()
    np.testing.assert_array_equal(np.asarray(result.native_result.first_order)[0], [0.0, 0.0])
    assert np.isfinite(result.first_order[1]).all()


def test_failed_case_retains_exact_input_prefix_raw_and_original_cause():
    calls = []
    raw = object()

    def callback(p):
        calls.append(dict(p))
        if len(calls) == 3:
            raise LookupError("actual native model domain failure")
        return ModelOutput({"value": p["x0"]}, raw)

    design = independent_qmc_design(space(), power=3, seed=17)
    response = model(callback)
    with pytest.raises(UncertaintyEvaluationError, match="domain failure") as failure:
        propagate(design, response)
    error = failure.value
    assert error.model is response and error.space is design.space
    assert error.case_index == 2 and len(error.completed_evaluations) == 2
    assert dict(error.parameters) == calls[-1]
    assert error.completed_evaluations[0].raw is raw
    assert isinstance(error.__cause__, LookupError)
    np.testing.assert_array_equal(error.batch_inputs.T, design.values)


@pytest.mark.parametrize(
    "response",
    (
        {"value": np.nan},
        {"value": np.inf},
        {"wrong": 1.0},
        {"value": True},
        {"value": 1.0, "extra": 2.0},
    ),
)
def test_invalid_physical_response_is_not_filled_or_discarded(response):
    with pytest.raises(UncertaintyEvaluationError) as failure:
        propagate(independent_qmc_design(space(), power=2, seed=1), model(lambda p: response))
    assert not failure.value.completed_evaluations
    assert failure.value.parameters


def test_model_cannot_mutate_parameter_mapping():
    def callback(p):
        p["x0"] = 0.0
        return {"value": 0.0}

    with pytest.raises(UncertaintyEvaluationError) as failure:
        propagate(independent_qmc_design(space(), power=2, seed=1), model(callback))
    assert isinstance(failure.value.__cause__, TypeError)


def test_native_distribution_mutation_invalidates_existing_design():
    parameters = space()
    design = independent_qmc_design(parameters, power=2, seed=3)
    parameters.parameters[0].distribution.kwds["scale"] = 2.0
    assert parameters.parameters[0].native_definition_snapshot["keywords"]["scale"] == 1.0
    with pytest.raises(ValueError, match="definition changed"):
        propagate(design, model(lambda p: {"value": p["x0"]}))


def test_native_distribution_mutation_inside_model_retains_failing_case():
    parameters = space()

    def callback(p):
        parameters.parameters[0].distribution.kwds["scale"] = 2.0
        return {"value": p["x0"]}

    with pytest.raises(UncertaintyEvaluationError, match="definition changed") as failure:
        propagate(independent_qmc_design(parameters, power=2, seed=3), model(callback))
    assert not failure.value.completed_evaluations and failure.value.parameters


def test_outside_physical_domain_retains_actual_quantiles_without_resampling():
    p = ParameterDistribution(
        Variable("T", "temperature", "K"),
        stats.norm(300, 50),
        "authored-normal",
        "authored",
        Origin.SYNTHETIC,
        290,
        310,
    )
    parameters = IndependentParameterSpace((p,), "authored-independent", "narrow-domain")
    with pytest.raises(UncertaintyDesignError) as failure:
        independent_qmc_design(parameters, power=4, seed=4)
    error = failure.value
    assert error.native_engine.num_generated == 16
    assert error.unit_cube.shape == error.transformed_values.shape == (16, 1)
    assert np.any((error.transformed_values < 290) | (error.transformed_values > 310))
    assert isinstance(error.__cause__, ValueError)


def test_design_coordinate_meanings_cannot_be_replaced_by_matching_shape():
    design = independent_qmc_design(space(), power=3, seed=3)
    with pytest.raises(ValueError, match="quantile coordinates"):
        replace(design, values=design.values[::-1])


def test_design_fingerprint_rejects_explicit_array_rewrite_before_physical_calls():
    design = independent_qmc_design(space(), power=3, seed=3)
    design.values.setflags(write=True)
    design.values[0, 0] = 0.5
    with pytest.raises(ValueError, match="coordinates changed"):
        propagate(design, model(lambda p: {"value": p["x0"]}))


def test_propagation_response_replacement_cannot_keep_other_case_evidence():
    result = propagate(
        independent_qmc_design(space(), power=3, seed=3), model(lambda p: {"value": p["x0"]})
    )
    with pytest.raises(ValueError, match="retained case outputs"):
        replace(result, values=result.values[::-1])


@pytest.mark.parametrize("value", (True, 0, -1, 31, 1.5))
def test_invalid_base2_power_is_not_rounded_or_silently_thinned(value):
    with pytest.raises(ValueError):
        independent_qmc_design(space(), power=value, seed=3)


def test_missing_independence_or_resolved_origin_is_not_inferred():
    with pytest.raises(ValueError):
        replace(space(), independence_evidence_id="")
    with pytest.raises(ValueError):
        replace(space().parameters[0], origin=Origin.UNRESOLVED)
    with pytest.raises(ValueError):
        replace(space(), parameters=(space().parameters[0],) * 2)
    with pytest.raises(ValueError):
        replace(space().parameters[0], distribution=stats.poisson(3))
    with pytest.raises(ValueError):
        replace(space().parameters[0], distribution=stats.uniform(scale=-1))


def test_native_scalar_array_distribution_parameters_and_snapshot_are_supported():
    p = replace(
        space(1).parameters[0], distribution=stats.uniform(loc=np.array(0.0), scale=np.array(1.0))
    )
    design = independent_qmc_design(
        IndependentParameterSpace((p,), "independent", "scalar-arrays"), power=3, seed=9
    )
    assert design.values.shape == (8, 1)
    with pytest.raises(TypeError):
        p.native_definition_snapshot["keywords"]["scale"] = 2.0


def test_coordinate_mutation_inside_callback_cannot_return_stale_design_identity():
    design = independent_qmc_design(space(), power=2, seed=3)
    original = design.values.copy()

    def callback(p):
        design.values.setflags(write=True)
        design.values[0, 0] = 0.99
        return {"value": p["x0"]}

    with pytest.raises(UncertaintyEvaluationError, match="coordinates changed") as failure:
        propagate(design, model(callback))
    error = failure.value
    assert error.design is design and len(error.completed_evaluations) == 4
    np.testing.assert_array_equal(error.batch_inputs.T, original)
    assert error.completed_evaluations[0].parameters["x0"] == original[0, 0]


def test_invalid_returned_response_keeps_actual_raw_object_and_values():
    design = independent_qmc_design(space(), power=2, seed=3)
    raw = object()
    output = ModelOutput({"value": np.nan}, raw)
    with pytest.raises(UncertaintyEvaluationError) as failure:
        propagate(design, model(lambda p: output))
    error = failure.value
    assert error.failed_raw is raw and error.failed_response is output
    assert np.isnan(error.failed_output_values["value"])
    assert error.design is design
    with pytest.raises(TypeError):
        error.failed_output_values["value"] = 0.0


def test_computation_budget_is_checked_before_native_allocations():
    with pytest.raises(ValueError, match="budget"):
        independent_qmc_design(space(), power=30, seed=3)
    with pytest.raises(ValueError, match="budget"):
        sobol_sensitivity(
            space(), model(lambda p: {"value": p["x0"]}), power=10, seed=3, maximum_evaluations=4095
        )


@pytest.mark.parametrize("scale", (1e200, 1e-200))
def test_native_zero_substitution_cannot_hide_overflow_or_underflow(scale):
    with pytest.raises(UncertaintyEvaluationError, match="unresolved|overflows") as failure:
        sobol_sensitivity(space(), model(lambda p: {"value": scale * p["x0"]}), power=3, seed=4)
    assert failure.value.native_result is not None
    assert len(failure.value.completed_evaluations) == 32


def test_summary_overflow_is_not_reported_as_finite_uncertainty():
    result = propagate(
        independent_qmc_design(space(), power=3, seed=4),
        model(lambda p: {"value": 1e308 * p["x0"]}),
    )
    with pytest.raises(ValueError, match="nonfinite"):
        result.summarize()


def test_sobol_failure_keeps_prefix_across_native_batches():
    calls = 0

    def callback(p):
        nonlocal calls
        calls += 1
        if calls == 10:
            raise RuntimeError("second native batch model failure")
        return {"value": p["x0"]}

    with pytest.raises(UncertaintyEvaluationError) as failure:
        sobol_sensitivity(space(), model(callback), power=3, seed=1)
    error = failure.value
    assert error.case_index == 9
    assert error.completed_evaluations[-1].batch_index == 1
    assert isinstance(error.__cause__, RuntimeError)
