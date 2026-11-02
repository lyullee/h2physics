"""Deferred typed coupling from a finite oxygen room to existing alarm logic."""

import hashlib

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="oxygen-room-deficit-detector-alarm-handoff",
        profile="oxygen-deficiency",
        entrypoint=__name__ + ":validate_handoff",
        parameters={},
        invariants=(
            "exact current dry oxygen output drives caller-declared deficit sensor input",
            "existing sensor lag and sampled alarm APIs remain the sole response logic",
            "source, clock, region, threshold-reference and trip evidence remain bound",
            "no human injury or population consequence is inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    import cantera as ct
    from pathlib import Path
    from h2physics.adapters.cantera import MechanismBasis, ReactiveState
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig, FirstOrderConcentrationSensorConfig,
    )
    from h2physics.adapters.oxygen_alarm_handoff import evaluate_oxygen_deficit_alarm
    from h2physics.adapters.oxygen_deficiency import (
        CanteraOxygenRoom, OxygenRoomRegion,
    )
    from h2physics.core import Origin

    source_path = Path(ct.__file__).parent / "data" / "nasa_gas.yaml"
    raw = source_path.read_bytes()
    species = {item.name: item for item in ct.Species.list_from_yaml(
        raw.decode("utf-8"), section="species")}
    phase_species = [species[name] for name in ("O2", "N2", "H2", "H2O", "CO2")]
    phase_factory = lambda: ct.Solution(thermo="ideal-gas", species=phase_species,
                                        name="oxygen-room-frozen-five-species")
    basis = MechanismBasis("Cantera-installed-nasa-gas-five-species",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause;NASA-TM-4513-public-US-government-work",
        ("https://cantera.org/3.2/python/thermo.html", "https://ntrs.nasa.gov/citations/19940013151"),
        200., 6000., 1e4, 5e6)
    region = OxygenRoomRegion("authored-small-room", "authored-room-receptor", "global-xyz",
        "authored-oxygen-clock", (0., 0., 1.5), 1.5, 40.,
        "authored-mixing-premise", "authored-single-gas-premise", "authored-no-flow-premise",
        Origin.SYNTHETIC)
    room = CanteraOxygenRoom(phase_factory, basis, region)
    result = room.run(ReactiveState(298.15, 101325., {"O2": .15, "N2": .85}),
                      (0., .2, .4, .6, 1.))
    reference_id = "authored-dry-ambient-oxygen-reference"
    concentration_basis = "dry-oxygen-deficit-mole-fraction:" + reference_id
    sensor = FirstOrderConcentrationSensorConfig("oxygen-deficit-sensor", region.region_id,
        region.clock_id, concentration_basis, "mole_fraction", .1, .5,
        "authored-sensor-basis", "authored-response-time-parameter", "first-order-sensor-law")
    alarm = ConcentrationAlarmConfig(sensor.sensor_id, region.region_id, region.clock_id,
        "normal-mode", "oxygen-deficit-episode", concentration_basis, "mole_fraction",
        .02, .01, 2, 2, .5, sensor.sensor_evidence_id,
        "authored-trip-reset-thresholds", "authored-two-sample-hysteresis", Origin.SYNTHETIC)
    coupling = evaluate_oxygen_deficit_alarm(result, sensor_config=sensor, alarm_config=alarm,
        reference_dry_oxygen_mole_fraction=.2095, reference_evidence_id=reference_id,
        initial_sensor_indication=0., operating_mode_id="normal-mode",
        episode_id="oxygen-deficit-episode")
    coupling.require_current()
    assert coupling.sensor_response.source_evidence_id == coupling.source_evidence_id
    assert coupling.alarm_trace.sensor_response is coupling.sensor_response
    assert coupling.trip_evidence
    assert all(item.require_current() is item for item in coupling.trip_evidence)
    return ValidationOutcome(True, {
        "dry_oxygen_mole_fraction": result.dry_oxygen_mole_fraction.tolist(),
        "deficit_mole_fraction": coupling.sensor_response.true_concentration.tolist(),
        "alarm_trip_times_s": [item.time_s for item in coupling.trip_evidence],
        "source_evidence_id": coupling.source_evidence_id,
    }, ("Synthetic static room input; detector response and sampled alarm use declared parameters.",
        "No human dose, injury probability or complete facility consequence is asserted."))
