"""Three ordinary input-to-output examples, without physics qualification."""

import json
import math

import numpy as np

from h2physics.core import Origin


def record_case(record_property, name, inputs, outputs):
    record_property("representative_case", name)
    record_property("input_parameters", json.dumps(inputs, sort_keys=True))
    record_property("output_metrics", json.dumps(outputs, sort_keys=True))


def test_pv_electrolysis_finite_batch(record_property):
    from examples.pv_electrolysis import build_model, run_example

    model = build_model(native_packages="artifacts/native_pvlib_packages")
    trace = run_example(model)
    hydrogen = trace.final.amounts_mol["hydrogen"] - trace.initial.amounts_mol["hydrogen"]
    electricity = math.fsum(step.electricity_j for step in trace.steps)
    assert len(trace.steps) == 2 and trace.final.time_s == 160.
    assert hydrogen > 0. and electricity > 0.
    assert all(math.isfinite(v) for v in (hydrogen, electricity, trace.final.receiver.pressure_pa))
    record_case(record_property, "pv_to_finite_hydrogen",
        {"clock_id": "authored-energy-clock", "start_s": 100., "end_s": 160.,
         "irradiance_w_m2": [650., 950.], "water_initial_mol": 2., "receiver_volume_m3": .01},
        {"hydrogen_produced_mol": hydrogen, "electrical_input_j": electricity,
         "final_receiver_pressure_pa": trace.final.receiver.pressure_pa, "end_s": trace.final.time_s})


def test_photon_to_finite_chemical_output(record_property):
    from h2physics.photochemistry import (
        BeerLambertPath,
        PhotoConditions,
        PhotonSupply,
        PhotonYield,
        SteadyPhotoWindow,
        photon_hydrogen_rate,
        run_photochemical_operation,
    )
    from h2physics.reactions import ChemicalSpecies, StoichiometricReaction

    conditions = PhotoConditions("declared-catalyst", "declared-medium", .001, 300., 1e5,
                                 "beam", "synthetic-example")
    reaction = StoichiometricReaction("water-splitting", (
        ChemicalSpecies("water", {"H": 2, "O": 1}, .018, "liquid"),
        ChemicalSpecies("hydrogen", {"H": 2}, .002, "gas"),
        ChemicalSpecies("oxygen", {"O": 2}, .032, "gas")), (-2., 2., 1.))
    windows = []
    for index, power in enumerate((.25, .5)):
        supply = PhotonSupply.from_lines([500e-9], [power], geometry_id="beam", source_id="light")
        path = BeerLambertPath.uniform(supply, depth_m=.01, absorption_coefficient_m_inv=100.,
                                      evidence_id="declared-optical-input")
        yield_curve = PhotonYield.bind(supply, [.2], basis="absorbed_electron_equivalents",
            conditions=conditions, evidence_id="synthetic-yield", origin=Origin.SYNTHETIC)
        rate = photon_hydrogen_rate(supply, path, yield_curve)
        windows.append((rate, SteadyPhotoWindow(float(index), float(index+1), "clock", "exposure")))
    trace = run_photochemical_operation(windows, reaction=reaction,
        initial_mol={"water": 1e-5}, hydrogen_species_id="hydrogen")
    amounts = dict(zip((s.identifier for s in reaction.species), trace.final_mol))
    assert len(trace.segments) == 2 and trace.clock_id == "clock"
    assert amounts["hydrogen"] > 0. and amounts["water"] >= 0.
    assert np.all(np.isfinite(trace.final_mol))
    record_case(record_property, "photon_to_finite_conversion",
        {"wavelength_m": 500e-9, "optical_power_w": [.25, .5], "window_s": [0., 1., 2.],
         "initial_water_mol": 1e-5, "authored_photon_yield": .2},
        {"final_hydrogen_mol": float(amounts["hydrogen"]),
         "final_water_mol": float(amounts["water"]),
         "incident_optical_energy_j": trace.incident_optical_energy_j})


def test_release_room_sensor_alarm(record_property):
    from h2physics.adapters.gas_detection import (
        ConcentrationAlarmConfig,
        FirstOrderConcentrationSensorConfig,
        evaluate_concentration_alarm_from_sensor,
        evaluate_first_order_concentration_sensor,
    )
    from h2physics.compartment_network import (
        CompartmentMolarTransfer,
        CompartmentNetworkModel,
        WellMixedCompartment,
        simulate_hydrogen_compartment_network,
    )
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
    from h2physics.thermo import CoolPropProperties

    gas = CoolPropProperties("Hydrogen")
    source = HomogeneousIsentropicNozzle(gas).solve(gas.state_pt(5e5, 300.),
        back_pressure_pa=1e5, opening=NozzleOpening.circular("opening", .001,
            effective_area_factor=.8, area_basis_id="declared-opening"))
    molar_rate = source.mass_flow_kg_s / gas.molar_mass_kg_mol
    time = np.linspace(0., 10., 21)
    room = WellMixedCompartment("room", .1, 101325., 300., 0., "fixed-room", "declared-P-T")
    rates = tuple(molar_rate for _ in range(len(time)-1))
    streams = (CompartmentMolarTransfer("feed", None, "room", rates, "nozzle", "pure-H2", "clock", 1.),
               CompartmentMolarTransfer("out", "room", None, rates, "exhaust", "well-mixed", "clock"))
    trace = simulate_hydrogen_compartment_network(CompartmentNetworkModel((room,), streams, "clock"),
                                                time_samples_s=time)
    sensor = FirstOrderConcentrationSensorConfig("sensor", "room", "clock", "H2-mole-fraction", "1",
        1., .6, "declared-sensor", "declared-time-constant", "first-order")
    response = evaluate_first_order_concentration_sensor(sensor, time_s=trace.time_s,
        true_concentration=trace.hydrogen_mole_fraction[:, 0], initial_indication=0.,
        source_evidence_id="computed-room-output", operating_mode_id="run", episode_id="episode",
        origin=Origin.SYNTHETIC)
    alarm = evaluate_concentration_alarm_from_sensor(ConcentrationAlarmConfig(
        "sensor", "room", "clock", "run", "episode", "H2-mole-fraction", "1", .02, .01,
        1, 1, .6, "declared-sensor", "declared-threshold", "sampled-logic", Origin.SYNTHETIC), response)
    final_fraction = float(trace.hydrogen_mole_fraction[-1, 0])
    assert 0. < final_fraction <= 1. and np.all(np.isfinite(response.indicated_concentration))
    assert any(t.alarm_active for t in alarm.transitions)
    record_case(record_property, "nozzle_to_room_sensor_alarm",
        {"upstream_pressure_pa": 5e5, "temperature_k": 300., "back_pressure_pa": 1e5,
         "opening_diameter_m": .001, "room_volume_m3": .1, "duration_s": 10.,
         "sensor_time_constant_s": 1., "trip_mole_fraction": .02},
        {"release_mass_flow_kg_s": source.mass_flow_kg_s,
         "final_room_hydrogen_mole_fraction": final_fraction,
         "final_sensor_mole_fraction": float(response.indicated_concentration[-1]),
         "alarm_active": any(t.alarm_active for t in alarm.transitions)})
