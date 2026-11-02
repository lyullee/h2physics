"""Deferred source-bound upper-layer O2 deficit sensor/alarm contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="two-vent-layer-oxygen-deficit-sensor-alarm-handoff",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "caller-reference-and-reference-to-projection-mappings-are-required",
            "exact-layer-projection-clock-drives-existing-first-order-sensor",
            "existing-sampled-alarm-engine-and-trip-evidence-remain-source-bound",
            "upper-layer-only-signal-does-not-claim-room-average-or-human-response",
            "detached-context-or-mutated-signal-is-rejected",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
    )
    from h2physics.adapters.layer_oxygen_alarm_handoff import (
        evaluate_layer_oxygen_deficit_alarm,
        layer_oxygen_deficit_basis,
    )
    from h2physics.adapters.layer_oxygen_projection import project_layer_oxygen
    from h2physics.buoyant_layer import (
        TwoVentHydrogenLayerConfig,
        run_two_vent_hydrogen_layer,
    )
    from h2physics.core import Origin

    layer_config = TwoVentHydrogenLayerConfig(
        compartment_height_m=3.0,
        floor_area_m2=36.0,
        source_height_m=0.2,
        lower_vent_area_m2=1.0,
        upper_vent_area_m2=1.0,
        lower_discharge_coefficient=0.65,
        upper_discharge_coefficient=0.65,
        ambient_pressure_pa=101325.0,
        ambient_temperature_k=293.15,
        initial_upper_layer_volume_m3=1.0,
        initial_upper_h2_mole_fraction=0.1,
    )
    layer = run_two_vent_hydrogen_layer(
        layer_config,
        hydrogen_mass_flow_kg_s=1.0e-5,
        duration_s=1.0,
        maximum_step_s=0.2,
    )
    projection = project_layer_oxygen(
        layer,
        carrier_basis="fixed_dry_air",
        carrier_oxygen_mole_fraction=layer.dry_air_mole_fractions[1],
    )

    reference_evidence = "authored-upper-layer-reference"
    basis = layer_oxygen_deficit_basis(reference_evidence)
    sensor = FirstOrderConcentrationSensorConfig(
        sensor_id="upper-layer-o2-deficit-sensor",
        location_id="upper-layer-sensor-location",
        clock_id="upper-layer-clock",
        concentration_basis=basis,
        concentration_unit="mole_fraction",
        response_time_constant_s=0.1,
        maximum_input_sample_gap_s=0.25,
        sensor_evidence_id="authored-sensor-identity",
        response_parameter_evidence_id="authored-sensor-lag",
        model_evidence_id="declared-first-order-lag-model",
    )
    alarm = ConcentrationAlarmConfig(
        detector_id=sensor.sensor_id,
        location_id=sensor.location_id,
        clock_id=sensor.clock_id,
        operating_mode_id="synthetic-normal-mode",
        episode_id="synthetic-upper-layer-episode",
        concentration_basis=basis,
        concentration_unit="mole_fraction",
        trip_threshold=0.005,
        reset_threshold=0.002,
        trip_confirmation_samples=2,
        reset_confirmation_samples=2,
        maximum_sample_gap_s=0.25,
        sensor_evidence_id=sensor.sensor_evidence_id,
        threshold_evidence_id="authored-upper-layer-thresholds",
        logic_evidence_id="authored-two-sample-alarm-logic",
        origin=Origin.SYNTHETIC,
    )
    common = dict(
        reference_oxygen_mole_fraction=0.2095,
        reference_evidence_id=reference_evidence,
        reference_clock_id="reference-clock",
        reference_location_id="reference-air-location",
        projection_clock_id=sensor.clock_id,
        projection_location_id=sensor.location_id,
        clock_mapping_evidence_id="authored-reference-clock-mapping",
        location_mapping_evidence_id="authored-reference-location-mapping",
        source_evidence_id="authored-layer-source",
        origin=Origin.SYNTHETIC,
        sensor_config=sensor,
        alarm_config=alarm,
        initial_sensor_indication=0.0,
        operating_mode_id="synthetic-normal-mode",
        episode_id="synthetic-upper-layer-episode",
    )
    result = evaluate_layer_oxygen_deficit_alarm(projection, **common)
    result.require_current()
    expected = tuple(
        max(0.2095 - value, 0.0)
        for value in projection.upper_oxygen_mole_fraction
    )
    assert result.projection is projection
    assert result.time_s is projection.time_s
    assert result.deficit_mole_fraction == expected
    assert result.sensor_response.source_evidence_id == common["source_evidence_id"]
    assert result.sensor_response.config is sensor
    assert result.alarm_trace.sensor_response is result.sensor_response
    assert result.alarm_trace.config is alarm
    assert result.trip_evidence
    assert all(item.require_current() is item for item in result.trip_evidence)

    bad_clock = dict(common, projection_clock_id="wrong-clock")
    try:
        evaluate_layer_oxygen_deficit_alarm(projection, **bad_clock)
    except ValueError:
        pass
    else:
        raise AssertionError("A mismatched projection/sensor clock must be rejected")

    try:
        replace(result, source_evidence_id="detached-source")
    except TypeError:
        pass
    else:
        raise AssertionError("A replaced handoff must not retain issued provenance")

    return ValidationOutcome(True, {
        "sample_count": len(result.time_s),
        "reference_evidence_id": result.reference_evidence_id,
        "clock_mapping_evidence_id": result.clock_mapping_evidence_id,
        "location_mapping_evidence_id": result.location_mapping_evidence_id,
        "deficit_mole_fraction": list(result.deficit_mole_fraction),
        "indicated_deficit_mole_fraction": result.sensor_response.indicated_concentration.tolist(),
        "alarm_trip_times_s": [item.time_s for item in result.trip_evidence],
        "source_evidence_id": result.source_evidence_id,
    }, (
        "Synthetic upper-layer composition and caller-authored reference, sensor and thresholds.",
        "No room-average, exposure-duration, safety certification or human-response result is produced.",
    ))
