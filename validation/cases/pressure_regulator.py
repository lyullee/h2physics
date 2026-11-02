"""Deferred sampled PI pressure-regulator controller contracts."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-pipeline-pressure-regulator-pi",
            profile="gas-compressible-pipe",
            entrypoint=__name__ + ":validate_pi_control",
            invariants=(
                "downstream-pressure-error-drives-open-and-close-stroke-commands",
                "command-intervals-follow-the-measurement-clock",
                "integral-memory-is-bounded-and-controller-state-is-explicit",
                "output-is-compatible-with-existing-valve-command-contract",
                "saturation-uses-conditional-integration-anti-windup",
                "sensor-owner-and-clock-substitution-is-rejected",
            ),
        ),
    )


def validate_pi_control(*, work_directory, **parameters):
    """Check controller direction, interval/lineage, bounds and anti-windup."""
    del work_directory, parameters
    from h2physics.adapters.pressure_regulator import (
        PressureRegulatorMeasurement,
        ProportionalIntegralPressureRegulator,
    )
    from h2physics.adapters.lh2dt_valve_actuator import ValveCommand

    regulator = ProportionalIntegralPressureRegulator(
        controller_id="synthetic-downstream-regulator",
        setpoint_pa_absolute=5.0e6,
        pressure_scale_pa=1.0e5,
        proportional_gain=0.2,
        integral_gain_s_inv=0.01,
        bias_stroke_fraction=0.5,
        minimum_target_stroke_fraction=0.05,
        maximum_target_stroke_fraction=0.95,
        maximum_integral_error_normalized_s=2.0,
        clock_id="synthetic-regulator-clock",
        evidence_id="synthetic-controller-tuning",
    )
    state = regulator.initial_state(
        time_s=0.0, sensor_id="outlet-pressure", sensor_owner_id="test-rig",
    )
    below = PressureRegulatorMeasurement(
        0.0, 4.8e6, "outlet-pressure", "test-rig",
        "synthetic-regulator-clock", "measurement-0",
    )
    first = regulator.step(state, below, end_time_s=1.0)
    assert type(first.command) is ValveCommand
    assert first.command.start_s == 0.0 and first.command.end_s == 1.0
    assert first.command.target_stroke_fraction > regulator.bias_stroke_fraction
    assert first.next_state.integral_error_normalized_s == 0.2

    above = PressureRegulatorMeasurement(
        1.0, 5.2e6, "outlet-pressure", "test-rig",
        "synthetic-regulator-clock", "measurement-1",
    )
    second = regulator.step(first.next_state, above, end_time_s=2.0)
    assert second.command.start_s == first.command.end_s
    assert second.command.target_stroke_fraction < regulator.bias_stroke_fraction

    saturating = PressureRegulatorMeasurement(
        0.0, 1.0e6, "outlet-pressure", "test-rig",
        "synthetic-regulator-clock", "measurement-low",
    )
    clipped = regulator.step(state, saturating, end_time_s=1.0)
    assert clipped.saturated
    assert clipped.command.target_stroke_fraction == regulator.maximum_target_stroke_fraction
    assert clipped.next_state.integral_error_normalized_s == 0.0

    rejected = []
    for sample in (
        PressureRegulatorMeasurement(
            0.0, 4.8e6, "other-sensor", "test-rig",
            "synthetic-regulator-clock", "wrong-sensor",
        ),
        PressureRegulatorMeasurement(
            0.0, 4.8e6, "outlet-pressure", "other-rig",
            "synthetic-regulator-clock", "wrong-owner",
        ),
        PressureRegulatorMeasurement(
            0.0, 4.8e6, "outlet-pressure", "test-rig",
            "other-clock", "wrong-clock",
        ),
    ):
        try:
            regulator.step(state, sample, end_time_s=1.0)
        except ValueError:
            rejected.append(True)
        else:
            rejected.append(False)
    assert all(rejected)
    return ValidationOutcome(True, {
        "below_setpoint_stroke_target": first.command.target_stroke_fraction,
        "above_setpoint_stroke_target": second.command.target_stroke_fraction,
        "upper_saturation_target": clipped.command.target_stroke_fraction,
        "lineage_substitutions_rejected": sum(rejected),
    }, (
        "Controller law uses authored synthetic gain/setpoint values only",
        "No sensor dynamics, valve-flow prediction or downstream pressure evolution is simulated",
    ))
