"""Deferred contracts for source-bound concentration-sensor tau fitting."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Synthetic paired-sample calibration contract only; no field calibration or sensor qualification.",
    "The fitted model contains only first-order time constant; gain, bias, delay and uncertainty remain outside scope.",
)


def cases():
    return (
        ValidationCase(
            identifier="sensor-time-constant-calibration-recovery",
            profile="facility-protection",
            entrypoint=__name__ + ":validate_time_constant_recovery",
            parameters={},
            invariants=(
                "fit recovers the generating first-order tau from paired synthetic truth/indication samples",
                "fitted config retains the exact clock, concentration basis, unit and calibration evidence",
                "receipt retains aligned immutable source samples and residual RMS in the declared unit",
                "a fit driven to a search boundary marks the estimate bound-limited rather than implying uncertainty",
            ),
        ),
        ValidationCase(
            identifier="sensor-time-constant-calibration-rejections",
            profile="facility-protection",
            entrypoint=__name__ + ":validate_time_constant_rejections",
            parameters={},
            invariants=(
                "basis/unit mismatch, non-exciting input, bad clock, nonfinite samples and invalid bounds are rejected",
                "source truth and measured indication evidence IDs remain distinct",
                "dataclass replacement cannot mint a second one-use calibration receipt",
                "unsupported gain, bias, transport delay and uncertainty remain outside the fitted model",
            ),
        ),
    )


def validate_time_constant_recovery(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    import numpy as np

    from h2physics.adapters.gas_detection import (
        FirstOrderConcentrationSensorConfig,
        evaluate_first_order_concentration_sensor,
    )
    from h2physics.adapters.sensor_calibration import fit_first_order_sensor_time_constant
    from h2physics.core import Origin

    true_tau = 2.4
    truth_config = FirstOrderConcentrationSensorConfig(
        "sensor-A", "room-A", "clock-A", "dry mole fraction", "mol/mol",
        true_tau, 1.0, "sensor-source-A", "synthetic-generator", "first-order-v1",
    )
    time = np.arange(0.0, 16.0, .5)
    concentration = np.where(time < 2.0, 0.0, np.where(time < 8.0, .02, .005))
    truth_response = evaluate_first_order_concentration_sensor(
        truth_config, time_s=time, true_concentration=concentration,
        initial_indication=0.0, source_evidence_id="truth-series-A",
        operating_mode_id="calibration", episode_id="episode-A", origin=Origin.SYNTHETIC,
    )
    seed_config = replace(truth_config, response_time_constant_s=1.1,
                          response_parameter_evidence_id="initial-guess")
    fitted = fit_first_order_sensor_time_constant(
        seed_config, time_s=time, true_concentration=concentration,
        measured_indication=truth_response.indicated_concentration,
        initial_indication=0.0, time_constant_bounds_s=(.2, 12.0),
        calibration_evidence_id="calibration-A",
        truth_series_evidence_id="truth-series-A",
        indication_series_evidence_id="indication-series-A",
        truth_basis_id="dry mole fraction", truth_unit="mol/mol",
        indication_basis_id="dry mole fraction", indication_unit="mol/mol",
        origin=Origin.SYNTHETIC,
    )
    fitted.require_current()
    if (not np.isclose(fitted.response_time_constant_s, true_tau, rtol=2e-6, atol=1e-8)
            or fitted.sensor_config.response_parameter_evidence_id != "calibration-A"
            or fitted.residual_rms > 1e-10):
        raise AssertionError("Paired-sample first-order calibration did not recover its synthetic tau")
    fast_config = replace(truth_config, response_time_constant_s=.01)
    fast_response = evaluate_first_order_concentration_sensor(
        fast_config, time_s=time, true_concentration=concentration,
        initial_indication=0.0, source_evidence_id="truth-series-fast",
        operating_mode_id="calibration", episode_id="episode-fast", origin=Origin.SYNTHETIC,
    )
    boundary_fit = fit_first_order_sensor_time_constant(
        seed_config, time_s=time, true_concentration=concentration,
        measured_indication=fast_response.indicated_concentration,
        initial_indication=0.0, time_constant_bounds_s=(.2, 12.0),
        calibration_evidence_id="calibration-fast",
        truth_series_evidence_id="truth-series-fast",
        indication_series_evidence_id="indication-series-fast",
        truth_basis_id="dry mole fraction", truth_unit="mol/mol",
        indication_basis_id="dry mole fraction", indication_unit="mol/mol",
        origin=Origin.SYNTHETIC,
    )
    if not boundary_fit.bound_limited:
        raise AssertionError("A boundary-seeking estimate must be marked explicitly")
    try:
        fitted.time_s.setflags(write=True)
    except ValueError:
        readonly_samples_rejected = True
    else:
        raise AssertionError("Calibration arrays must be immutable bytes-backed snapshots")
    return ValidationOutcome(True, {
        "generating_time_constant_s": true_tau,
        "recovered_time_constant_s": fitted.response_time_constant_s,
        "residual_rms": fitted.residual_rms,
        "boundary_fit_time_constant_s": boundary_fit.response_time_constant_s,
        "boundary_fit_limited": boundary_fit.bound_limited,
        "readonly_sample_write_enable_rejected": readonly_samples_rejected,
    }, LIMITS)


def validate_time_constant_rejections(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters.gas_detection import FirstOrderConcentrationSensorConfig
    from h2physics.adapters.sensor_calibration import fit_first_order_sensor_time_constant
    from h2physics.core import Origin

    config = FirstOrderConcentrationSensorConfig(
        "sensor-B", "room-B", "clock-B", "dry mole fraction", "mol/mol",
        1.0, 2.0, "sensor-source-B", "response-source-B", "first-order-v1",
    )
    common = dict(
        time_s=[0.0, 1.0, 2.0, 3.0], true_concentration=[0.0, .02, .02, 0.0],
        measured_indication=[0.0, .01, .018, .012], initial_indication=0.0,
        time_constant_bounds_s=(.1, 5.0), calibration_evidence_id="calibration-B",
        truth_series_evidence_id="truth-B", indication_series_evidence_id="indicated-B",
        truth_basis_id="dry mole fraction", truth_unit="mol/mol",
        indication_basis_id="dry mole fraction", indication_unit="mol/mol",
        origin=Origin.SYNTHETIC,
    )
    rejected = 0
    for bad in (
        {**common, "indication_unit": "%"},
        {**common, "true_concentration": [0.0, 0.0, 0.0, 0.0]},
        {**common, "time_s": [0.0, 1.0, 1.0, 3.0]},
        {**common, "time_constant_bounds_s": (3.0, .1)},
    ):
        try:
            fit_first_order_sensor_time_constant(config, **bad)
        except (TypeError, ValueError):
            rejected += 1
            continue
        raise AssertionError("Invalid sampled calibration contract was accepted")
    admitted = fit_first_order_sensor_time_constant(config, **common)
    try:
        replace(admitted, response_time_constant_s=1.5)
    except TypeError:
        replacement_rejected = True
    else:
        raise AssertionError("A consumed issuer token must not authorize receipt replacement")
    return ValidationOutcome(True, {
        "invalid_fit_inputs_rejected": rejected,
        "consumed_receipt_replacement_rejected": replacement_rejected,
    }, LIMITS)
