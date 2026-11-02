"""Actual learned native residuals, physical reference and partition/causality guards."""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.process_monitoring import (
    MonitoringNativeError,
    MonitoringSettings,
    NativeResidualMonitor,
    ResidualContext,
    residual_batch,
)
from scripts.check_process_monitoring import (
    campaign,
    case_batch,
    features,
    native_provider,
    physical_reference,
)


@pytest.fixture(scope="module")
def native():
    target = Path(__file__).resolve().parents[1]/"artifacts/native_monitoring_packages"
    if not (target/"process_monitoring/pipeline.py").exists():
        pytest.skip("Reviewed separately installed native monitoring is optional")
    return native_provider()


@pytest.fixture(scope="module")
def reference(native):
    pytest.importorskip("cantera")
    if not (Path(__file__).resolve().parents[1]/"artifacts/native_packages/lh2dt/instrumentation.py").exists():
        pytest.skip("Reviewed separately installed native LH2DT instrumentation is optional")
    return physical_reference()


def evaluation_data(native, reference, **changes):
    return case_batch(native, reference, "evaluation", seed=303, **changes)


def test_import_keeps_optional_domain_packages_lazy():
    r = subprocess.run([sys.executable, "-X", "utf8", "-c",
        "import sys; import h2physics.adapters.process_monitoring; "
        "assert not ({'process_monitoring','sklearn','cloudpickle','cantera','lh2dt'} & set(sys.modules))"],
        capture_output=True, text=True, encoding="utf-8", check=False)
    assert r.returncode == 0, r.stderr


def test_actual_finite_native_physics_and_instrument_owners(reference):
    trace = reference["trace"]
    assert trace.native.network is not None
    assert len(trace.native.walls) == 1
    expected = trace.snapshots[0].internal_energy_j+20*120/(2*np.pi)*np.sin(
        2*np.pi*(trace.time_s-100.)/120.)
    actual = np.array([s.internal_energy_j for s in trace.snapshots])
    assert np.max(np.abs(actual-expected)) < 1e-4
    assert np.max(np.abs(trace.mass_residual_kg)) < 1e-11
    assert np.max(np.abs(trace.energy_residual_j)) < 1e-5
    assert np.max(np.abs(reference["process"].values-reference["prediction"].values), axis=0)[0] > 100.
    assert all(s.native_readings and s.native_states for s in reference["instruments"])


def test_actual_native_signed_residual_and_observation_contract(native, reference):
    data = evaluation_data(native, reference)
    expected = (data.observed.values-data.predicted.values)/[80., .06]
    assert data.native_batch.values == pytest.approx(expected)
    assert np.any(expected < 0)
    assert data.prediction_owner is reference
    assert data.observations.values == pytest.approx(expected)
    assert data.observations.experiment_ids == tuple(data.native_batch.episodes)
    assert data.observations.origins[0].value == "synthetic"
    assert data.native_batch.metadata["clock_id"] == data.observed.clock_id
    assert not data.native_batch.values.flags.writeable


def test_actual_pca_independent_covariance_eigenspace(native, reference):
    owner, fitting, _ = campaign(native, reference)
    x, valid = owner.native_model.monitors["cooling"].features.transform(fitting.native_batch)
    selected = valid & (fitting.native_batch.modes == "cooling")
    model = owner.native_model.monitors["cooling"]
    scaled = model.scaler.transform(x[selected])
    covariance = np.cov(scaled, rowvar=False)
    _values, vectors = np.linalg.eigh(covariance)
    principal = vectors[:, -1]
    native_direction = model.detector.model.components_[0]
    assert np.outer(native_direction, native_direction) == pytest.approx(
        np.outer(principal, principal), abs=1e-10)
    assert np.dot(native_direction, native_direction) == pytest.approx(1., abs=1e-12)
    assert type(model.detector.model).__module__ == "sklearn.decomposition._pca"


def test_independent_calibration_quantile_without_reference_refit(native, reference):
    fit = case_batch(native, reference, "fitting", seed=101)
    cal = case_batch(native, reference, "calibration", seed=202)
    owner = NativeResidualMonitor(native).fit(fit)
    before = owner._parameter_hash()
    owner.calibrate(cal)
    assert owner._parameter_hash() == before
    for mode, model in owner.native_model.monitors.items():
        r = model.score(cal.native_batch)
        mask = r.valid & (cal.native_batch.modes == mode)
        assert model.threshold == np.quantile(r.scores[mask], .95, method="higher")


def test_shifted_heldout_is_deviation_and_retains_original_native_results(native, reference):
    owner, fit, cal = campaign(native, reference)
    result = owner.evaluate(case_batch(native, reference, "evaluation", seed=404, shifted=True))
    mask = result.valid & (result.time_s >= 164) & (result.time_s <= 198)
    assert result.alarms[mask].mean() > .8
    assert result.native_model is owner.native_model
    assert result.fitting_data is fit and result.calibration_data is cal
    assert result.native_result.detector == "ModeMonitor"
    assert not result.physical_control_actions and not result.fault_identification


def test_causal_prefix_and_frozen_evaluation_parameters(native, reference):
    owner, _, _ = campaign(native, reference)
    first = owner.evaluate(case_batch(native, reference, "evaluation", seed=404, shifted=True))
    prefix = owner.evaluate(case_batch(native, reference, "evaluation", seed=404, shifted=True,
                                      selection=slice(0, 85)))
    assert np.array_equal(first.valid[:85], prefix.valid)
    assert np.allclose(first.scores[:85], prefix.scores, equal_nan=True)
    assert first.trained_state_sha256 == prefix.trained_state_sha256 == owner._model_hash()


def test_missing_sensor_samples_abstain_without_fill(native, reference):
    owner, _, _ = campaign(native, reference)
    mask = np.ones((len(reference["prediction"].time_s), 2), bool)
    mask[50, 0] = False
    data = evaluation_data(native, reference, valid=mask)
    result = owner.evaluate(data)
    assert np.isnan(data.native_batch.values[50, 0])
    assert not result.valid[50:54].any()
    assert np.isnan(result.scores[50:54]).all()
    assert not result.alarms[50:54].any()
    assert result.valid[54]


def test_actual_clock_gap_interrupts_windows(native, reference):
    owner, _, _ = campaign(native, reference)
    selection = np.r_[np.arange(50), np.arange(51, 121)]
    result = owner.evaluate(evaluation_data(native, reference, selection=selection))
    assert not result.valid[50:53].any()
    assert result.valid[53]


def test_episode_boundaries_interrupt_windows(native, reference):
    owner, _, _ = campaign(native, reference)
    source = evaluation_data(native, reference)
    data = residual_batch(native, source.observed, source.predicted, source.features,
        context=source.context, episodes=("heldout-A",)*60+("heldout-B",)*61,
        modes=source.native_batch.modes, prediction_owner=reference)
    result = owner.evaluate(data)
    assert not result.valid[60:63].any()
    assert result.valid[63]


def test_unknown_observed_modes_abstain(native, reference):
    owner, _, _ = campaign(native, reference)
    data = evaluation_data(native, reference, modes=("maintenance",)*121)
    result = owner.evaluate(data)
    assert not result.valid.any() and not result.alarms.any()
    assert np.isnan(result.scores).all()


def test_whole_run_overlap_and_role_reuse_rejected(native, reference):
    owner, fitting, _ = campaign(native, reference)
    overlap = evaluation_data(native, reference, episode=next(iter(fitting.episodes)))
    with pytest.raises(MonitoringNativeError, match="disjoint") as caught:
        owner.evaluate(overlap)
    assert caught.value.native_model is owner.native_model
    assert caught.value.fitting_data is fitting
    assert caught.value.__cause__ is not None
    other, fit, _ = campaign(native, reference)
    with pytest.raises(MonitoringNativeError, match="role"):
        other.evaluate(fit)


def test_feature_order_scope_and_physical_basis_require_explicit_correspondence(native, reference):
    owner, _, _ = campaign(native, reference)
    reversed_data = evaluation_data(native, reference, feature_spec=features()[::-1])
    with pytest.raises(MonitoringNativeError, match="order"):
        owner.evaluate(reversed_data)
    owner, _, _ = campaign(native, reference)
    data = evaluation_data(native, reference)
    changed = residual_batch(native, data.observed, data.predicted, data.features,
        context=replace(data.context, mode_definition_id="other-mode-definition"),
        episodes=data.native_batch.episodes, modes=data.native_batch.modes, prediction_owner=reference)
    with pytest.raises(MonitoringNativeError, match="scope"):
        owner.evaluate(changed)
    with pytest.raises(ValueError, match="basis"):
        residual_batch(native, replace(data.observed, basis_ids=("gauge", "")), data.predicted,
            data.features, context=data.context, episodes=data.native_batch.episodes,
            modes=data.native_batch.modes, prediction_owner=reference)


def test_clock_offset_and_physical_location_not_inferred(native, reference):
    data = evaluation_data(native, reference)
    with pytest.raises(ValueError, match="exactly"):
        residual_batch(native, data.observed, replace(data.predicted, time_s=data.predicted.time_s+.01),
            data.features, context=data.context, episodes=data.native_batch.episodes,
            modes=data.native_batch.modes, prediction_owner=reference)
    with pytest.raises(ValueError, match="locations"):
        replace(features()[0], predicted_location_id="different-vessel")


def test_native_trained_state_tamper_retains_failure_and_prior_result(native, reference):
    owner, fitting, calibration = campaign(native, reference)
    first = owner.evaluate(evaluation_data(native, reference))
    model = owner.native_model.monitors["cooling"].detector.model
    model.components_[0, 0] += .1
    with pytest.raises(MonitoringNativeError, match="state changed") as caught:
        owner.evaluate(evaluation_data(native, reference))
    error = caught.value
    assert error.native_model.monitors["cooling"].detector.model is model
    assert error.fitting_data is fitting and error.calibration_data is calibration
    assert error.completed_evaluations == (first,)
    assert error.last_admitted_model_sha256 == first.trained_state_sha256


def test_mutable_native_metadata_tamper_rejected(native, reference):
    owner, fit, _ = campaign(native, reference)
    fit.native_batch.metadata["clock_id"] = "different-clock"
    with pytest.raises(MonitoringNativeError, match="changed") as caught:
        owner.evaluate(evaluation_data(native, reference))
    assert caught.value.fitting_data is fit


def test_real_native_no_usable_training_failure_retains_attempted_model(native, reference):
    owner = NativeResidualMonitor(native)
    data = case_batch(native, reference, "fitting", seed=909, valid=np.zeros((121, 2), bool))
    with pytest.raises(MonitoringNativeError, match="no usable training windows") as caught:
        owner.fit(data)
    assert caught.value.native_model is owner.native_model
    assert caught.value.native_attempted_models
    assert caught.value.attempted_data is data
    assert isinstance(caught.value.__cause__, ValueError)
    assert owner.status == "failed"


def test_real_native_insufficient_calibration_preserves_fitted_campaign(native, reference):
    owner = NativeResidualMonitor(native)
    fitting = case_batch(native, reference, "fitting", seed=101)
    owner.fit(fitting)
    data = case_batch(native, reference, "calibration", seed=202, valid=np.zeros((121, 2), bool))
    with pytest.raises(MonitoringNativeError, match="two usable") as caught:
        owner.calibrate(data)
    assert caught.value.fitting_data is fitting
    assert caught.value.calibration_data is None
    assert all(m.fitted for m in caught.value.native_model.monitors.values())
    assert caught.value.__cause__ is not None


def test_reference_confirmation_and_calibration_mode_coverage_required(native, reference):
    with pytest.raises(MonitoringNativeError, match="normal-reference"):
        NativeResidualMonitor(native).fit(case_batch(native, reference, "fitting",
            seed=101, normal_reference=False))
    owner = NativeResidualMonitor(native).fit(case_batch(native, reference, "fitting", seed=101))
    with pytest.raises(MonitoringNativeError, match="Every fitted mode"):
        owner.calibrate(case_batch(native, reference, "calibration", seed=202,
                                   modes=("warming",)*121))


def test_separate_calibration_and_new_campaign_owner_required(native, reference):
    owner = NativeResidualMonitor(native).fit(case_batch(native, reference, "fitting", seed=101))
    with pytest.raises(MonitoringNativeError, match="separate"):
        owner.evaluate(evaluation_data(native, reference))
    owner, fit, _ = campaign(native, reference)
    with pytest.raises(MonitoringNativeError, match="new owner"):
        owner.fit(fit)


def test_raw_native_result_retained_with_separate_immutable_score_snapshot(native, reference):
    owner, _, _ = campaign(native, reference)
    result = owner.evaluate(evaluation_data(native, reference))
    snapshot = result.scores.copy()
    result.native_result.scores[10] = 12345.
    assert np.array_equal(result.scores, snapshot, equal_nan=True)
    assert not result.scores.flags.writeable and not result.valid.flags.writeable
    assert result.native_result.scores[10] == 12345.


def test_current_evidence_settings_and_feature_types_validated(native, reference):
    data = evaluation_data(native, reference)
    with pytest.raises(TypeError, match="Every ordered"):
        residual_batch(native, data.observed, data.predicted, (features()[0], None),
            context=data.context, episodes=data.native_batch.episodes,
            modes=data.native_batch.modes, prediction_owner=reference)
    with pytest.raises(TypeError, match="ResidualContext"):
        residual_batch(native, data.observed, data.predicted, features(), context=None,
            episodes=data.native_batch.episodes, modes=data.native_batch.modes, prediction_owner=reference)
    changed = replace(data.context)
    object.__setattr__(changed, "scope_id", "")
    with pytest.raises(ValueError, match="scope_id"):
        residual_batch(native, data.observed, data.predicted, features(), context=changed,
            episodes=data.native_batch.episodes, modes=data.native_batch.modes, prediction_owner=reference)
    with pytest.raises(ValueError, match="role"):
        ResidualContext("x", "unknown", "x", "x", "x", "x")
    with pytest.raises(ValueError, match="two"):
        MonitoringSettings(window=1)
    with pytest.raises(ValueError, match="positive"):
        replace(features()[0], uncertainty_scale=0)


def test_native_class_method_rebinding_cannot_change_calculation_basis(native, reference):
    owner, _, _ = campaign(native, reference)
    data = evaluation_data(native, reference)
    original = native.module.ModeMonitor.score

    def delegate(model, batch):
        return original(model, batch)

    native.module.ModeMonitor.score = delegate
    try:
        with pytest.raises(MonitoringNativeError, match="origin/binding") as caught:
            owner.evaluate(data)
        assert caught.value.native_model is owner.native_model
        assert caught.value.__cause__ is not None
    finally:
        native.module.ModeMonitor.score = original
    native.require_source()


@pytest.mark.parametrize("field", ["clock_id", "source_id"])
def test_current_timeseries_identity_cannot_be_empty_at_residual_admission(native, reference, field):
    data = evaluation_data(native, reference)
    observed, predicted = replace(data.observed), replace(data.predicted)
    object.__setattr__(observed, field, "")
    object.__setattr__(predicted, field, "")
    with pytest.raises(ValueError, match="Clock, source"):
        residual_batch(native, observed, predicted, features(), context=data.context,
            episodes=data.native_batch.episodes, modes=data.native_batch.modes,
            prediction_owner=reference)
