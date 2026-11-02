"""Deferred typed Cantera composition-to-hydrogen-detector contract."""

import hashlib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cantera-reactor-hydrogen-sensor-alarm-handoff",
        profile="counterflow-flame",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "the exact native gas-phase H2 mole-fraction samples drive existing sensor response",
            "reactor/site/clock/origin assumptions are explicit caller inputs",
            "alarm trip evidence remains linked to the original reactor and sensor outputs",
            "no spatial mixing or room concentration transfer is inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, MechanismBasis, ReactiveState
    from h2physics.adapters.cantera_gas_alarm import evaluate_cantera_species_alarm
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig, FirstOrderConcentrationSensorConfig,
    )
    from h2physics.core import Origin

    source_path = Path(ct.__file__).parent / "data" / "nasa_gas.yaml"
    raw = source_path.read_bytes()
    available = {item.name: item for item in ct.Species.list_from_yaml(
        raw.decode("utf-8"), section="species")}
    selected = [available[name] for name in ("H2", "N2")]
    basis = MechanismBasis("installed-Cantera-nasa-gas-H2-N2-alarm-contract",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause;NASA-TM-4513-public-US-government-work",
        ("https://cantera.org/3.2/python/thermo.html", "https://ntrs.nasa.gov/citations/19940013151"),
        200., 6000., 1e4, 5e6)
    owner = CanteraGas(lambda: ct.Solution(thermo="ideal-gas", species=selected,
        name="authored-H2-N2-closed-gas"), basis)
    trace = owner.closed_reactor(ReactiveState(298.15, 101325., {"H2": .1, "N2": .9}),
        (0., .02, .04, .06), constraint="UV", maximum_time_step_s=.01,
        relative_tolerance=1e-9, absolute_tolerance=1e-15)
    location, clock, origin = "authored-well-mixed-gas-zone", "authored-reactor-clock", Origin.SYNTHETIC
    source_evidence = "authored-closed-reactor-composition-as-local-gas-source"
    mode, episode = "authored-normal-operation", "authored-hydrogen-detector-episode"
    concentration_basis = "cantera-gas-phase-mole-fraction:H2"
    sensor = FirstOrderConcentrationSensorConfig("authored-hydrogen-sensor", location,
        clock, concentration_basis, "mole_fraction", .05, .05,
        "authored-H2-sensor-calibration", "authored-first-order-time-constant",
        "first-order-sensor-model")
    alarm = ConcentrationAlarmConfig(sensor.sensor_id, location, clock, mode, episode,
        concentration_basis, "mole_fraction", .04, .02, 2, 2, .05,
        sensor.sensor_evidence_id, "authored-H2-trip-reset-limits",
        "authored-two-sample-confirmation", origin)
    handoff = evaluate_cantera_species_alarm(trace, species_id="H2", location_id=location,
        clock_id=clock, source_evidence_id=source_evidence, origin=origin,
        sensor_config=sensor, alarm_config=alarm, initial_sensor_indication=0.,
        operating_mode_id=mode, episode_id=episode)
    handoff.require_current()
    assert all(abs(float(value)-.1) < 1e-12
               for value in handoff.sensor_response.true_concentration)
    assert handoff.sensor_response.source_evidence_id == handoff.source_evidence_id
    assert handoff.alarm_trace.sensor_response is handoff.sensor_response
    assert handoff.trip_evidence
    assert all(item.require_current() is item for item in handoff.trip_evidence)
    return ValidationOutcome(True, {
        "H2_mole_fraction": handoff.sensor_response.true_concentration.tolist(),
        "indicated_mole_fraction": handoff.sensor_response.indicated_concentration.tolist(),
        "alarm_trip_times_s": [item.time_s for item in handoff.trip_evidence],
        "source_evidence_id": handoff.source_evidence_id,
    }, ("Synthetic closed-cell H2/N2 mixture; no spatial dispersion or site transfer is inferred.",
        "Detector response, setpoints and confirmation rule are caller-authored software-contract inputs."))
