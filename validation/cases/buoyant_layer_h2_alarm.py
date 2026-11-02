"""Deferred synthetic integration of buoyant H2 layer output and alarm logic."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="two-vent-hydrogen-layer-concentration-alarm-handoff",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_layer_alarm",
        invariants=(
            "existing-buoyant-layer-owner-drives-upper-zone-h2-signal",
            "sensor-first-order-response-and-hysteretic-alarm-are-original-engines",
            "clock-location-basis-release-and-zone-mapping-are-explicit",
            "trip-evidence-retains-the-original-alarm-transition",
            "no-room-average-detector-credit-or-closed-loop-protection-claim",
        ),
    ),)


def validate_layer_alarm(*, work_directory, **parameters):
    del work_directory, parameters
    import numpy as np

    from h2physics.adapters.buoyant_layer_h2_alarm import evaluate_buoyant_layer_h2_alarm
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
    )
    from h2physics.buoyant_layer import TwoVentHydrogenLayerConfig
    from h2physics.core import Origin

    clock = "synthetic-layer-clock"
    zone = "compressor-room-upper-layer"
    sensor = FirstOrderConcentrationSensorConfig(
        "synthetic-h2-sensor", zone, clock, "upper-layer-h2-mole-fraction",
        "mol/mol", .2, .5, "synthetic-sensor", "synthetic-tau", "first-order-test",
    )
    alarm = ConcentrationAlarmConfig(
        sensor.sensor_id, zone, clock, "normal-operation", "episode-1",
        "upper-layer-h2-mole-fraction", "mol/mol", .01, .005, 1, 1, .5,
        sensor.sensor_evidence_id, "synthetic-threshold", "sampled-hysteresis",
        Origin.SYNTHETIC,
    )
    result = evaluate_buoyant_layer_h2_alarm(
        TwoVentHydrogenLayerConfig(
            compartment_height_m=3., floor_area_m2=36., source_height_m=.2,
            lower_vent_area_m2=1., upper_vent_area_m2=1.,
            lower_discharge_coefficient=.65, upper_discharge_coefficient=.65,
            ambient_pressure_pa=101325., ambient_temperature_k=293.15,
            initial_upper_layer_volume_m3=1., initial_upper_h2_mole_fraction=.1,
        ),
        hydrogen_mass_flow_kg_s=1.e-5, duration_s=10., maximum_step_s=.25,
        clock_id=clock, layer_location_id=zone,
        source_evidence_id="synthetic-release-definition",
        zone_mapping_evidence_id="synthetic-upper-zone-detector-mapping",
        sensor_config=sensor, alarm_config=alarm, initial_sensor_indication=0.,
        operating_mode_id="normal-operation", episode_id="episode-1",
    )
    result.require_current()
    assert np.array_equal(result.time_s, result.sensor_response.time_s)
    assert result.true_h2_mole_fraction == tuple(result.sensor_response.true_concentration)
    assert result.alarm_trace.sensor_response is result.sensor_response
    assert result.trip_evidence
    assert all(item.trace is result.alarm_trace for item in result.trip_evidence)
    return ValidationOutcome(True, {
        "model_samples": len(result.time_s),
        "initial_upper_h2_mole_fraction": result.true_h2_mole_fraction[0],
        "final_upper_h2_mole_fraction": result.true_h2_mole_fraction[-1],
        "confirmed_trip_count": len(result.trip_evidence),
        "first_trip_time_s": result.trip_evidence[0].time_s,
    }, (
        "Synthetic reduced-order room case only; no detector placement or field qualification.",
        "No detector credit, closed-loop action, or facility protection performance is inferred.",
    ))
