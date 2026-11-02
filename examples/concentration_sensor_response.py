"""Synthetic first-order gas-sensor and sampled-alarm composition example.

The response constant and alarm limits are illustrative values, not guidance.
"""


def prepare_example():
    from h2physics.adapters import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm_from_sensor,
        evaluate_first_order_concentration_sensor,
    )
    from h2physics.core import Origin

    sensor = FirstOrderConcentrationSensorConfig(
        sensor_id="synthetic-hydrogen-detector",
        location_id="synthetic-compressor-room",
        clock_id="synthetic-room-clock",
        concentration_basis="dry mole fraction",
        concentration_unit="mol/mol",
        response_time_constant_s=0.8,
        maximum_input_sample_gap_s=0.5,
        sensor_evidence_id="synthetic-sensor-record",
        response_parameter_evidence_id="synthetic-response-fit",
        model_evidence_id="first-order-lag-model-v1",
    )
    response = evaluate_first_order_concentration_sensor(
        sensor,
        time_s=[0.0, 0.2, 0.4, 0.6],
        true_concentration=[0.0, 0.012, 0.02, 0.02],
        initial_indication=0.0,
        source_evidence_id="synthetic-prescribed-room-history",
        operating_mode_id="synthetic-normal-mode",
        episode_id="synthetic-release-episode",
        origin=Origin.SYNTHETIC,
    )
    alarm = ConcentrationAlarmConfig(
        detector_id=sensor.sensor_id,
        location_id=sensor.location_id,
        clock_id=sensor.clock_id,
        operating_mode_id="synthetic-normal-mode",
        episode_id="synthetic-release-episode",
        concentration_basis=sensor.concentration_basis,
        concentration_unit=sensor.concentration_unit,
        trip_threshold=0.01,
        reset_threshold=0.005,
        trip_confirmation_samples=1,
        reset_confirmation_samples=2,
        maximum_sample_gap_s=0.5,
        sensor_evidence_id=sensor.sensor_evidence_id,
        threshold_evidence_id="synthetic-threshold-source",
        logic_evidence_id="synthetic-alarm-logic-revision",
        origin=Origin.SYNTHETIC,
    )
    trace = evaluate_concentration_alarm_from_sensor(alarm, response)
    trace.require_current()
    return response, trace
