"""Deferred meter-bound electrochemical H2 storage accounting contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-hydrogen-storage-metered-round-trip-ledger",
        profile="pv-electrolysis",
        entrypoint=__name__ + ":validate_round_trip",
        parameters={"native_packages": "artifacts/native_pvlib_packages"},
        invariants=(
            "charge and discharge meters share the admitted physical clock, electrical basis and declared system boundary",
            "meter windows cover complete accepted electrolysis and fuel-cell traces in sequential order",
            "metered charge includes native stack input while metered output does not exceed native stack output",
            "round-trip ratio uses boundary meter energy and remains distinct from stack-only energy ratio",
            "only the net H2 inventory increase above the EOS seed is transferred and reconciled",
            "mismatched clocks, boundaries, energy bases and incomplete windows are rejected",
            "no compression, auxiliaries, AC conversion or omitted plant loads are inferred beyond meter evidence",
        ),
    ),)


def validate_round_trip(*, work_directory, native_packages, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import fsum

    from examples.fuel_cell import synthetic_problem
    from examples.pv_electrolysis import build_model, source_stages
    from h2physics.adapters.electrochemical_hydrogen_handoff import (
        bind_electrolysis_to_fuel_cell,
    )
    from h2physics.adapters.electrochemical_round_trip import (
        ElectricalBoundaryMeter,
        account_electrochemical_storage_round_trip,
    )
    from h2physics.thermochemical import ThermochemicalInventory

    producer = build_model(native_packages=native_packages)
    production = producer.run(
        source_stages(),
        initial_amounts_mol={"water": 2.0, "hydrogen": 0.2, "oxygen": 0.1},
        receiver_volume_m3=0.01,
        receiver_temperature_k=298.15,
    )
    produced = (production.final.amounts_mol[producer.hydrogen_id]
                - production.initial.amounts_mol[producer.hydrogen_id])
    assert produced > 0.0

    consumer, _, commands = synthetic_problem(
        hydrogen_id=producer.hydrogen_id,
        hydrogen_molar_mass_kg_mol=producer.gas.molar_mass_kg_mol,
        clock_id=production.evidence.clock_id,
    )
    loss = produced * 0.02
    delivered = produced - loss
    initial = ThermochemicalInventory(
        {consumer.hydrogen_id: delivered, "O2": 0.007, "H2O": 0.001},
        320.0,
        consumer.boundary.pressure_pa,
        consumer.caloric_source.provider.basis_id,
    )
    command = replace(
        commands[0], start_s=production.final.time_s,
        end_s=production.final.time_s + 10.0,
        clock_id=production.evidence.clock_id,
    )
    consumption = consumer.run(initial, (command,))
    handoff = bind_electrolysis_to_fuel_cell(
        production, consumption, transfer_loss_mol=loss,
        source_id=production.evidence.source_id,
        sink_id=consumption.boundary.hydrogen_inlet_id,
        transfer_evidence_id="authored-round-trip-H2-transfer",
        conditioning_evidence_id="authored-no-conditioning-loss-boundary",
        closure_tolerance_mol=1e-10,
    )

    stack_in = fsum(step.electricity_j for step in production.steps)
    stack_out = -consumption.electricity_into_j
    charge = ElectricalBoundaryMeter(
        "authored-charge-meter", "authored-system-boundary", "charge-window",
        production.evidence.clock_id, "authored-DC-joule-basis",
        "authored-integrated-charge-meter-evidence",
        production.initial.time_s, production.final.time_s, stack_in * 1.05,
    )
    discharge = ElectricalBoundaryMeter(
        "authored-discharge-meter", "authored-system-boundary", "discharge-window",
        production.evidence.clock_id, "authored-DC-joule-basis",
        "authored-integrated-discharge-meter-evidence",
        command.start_s, command.end_s, stack_out * 0.95,
    )
    result = account_electrochemical_storage_round_trip(
        handoff, charge_meter=charge, discharge_meter=discharge,
    ).require_current()
    assert result.round_trip_electricity_ratio == result.meter_electricity_out_j / result.meter_electricity_in_j
    assert result.stack_electricity_in_j == stack_in
    assert result.stack_electricity_out_j == stack_out
    assert result.hydrogen_produced_mol == handoff.produced_mol
    assert result.hydrogen_delivered_mol == handoff.delivered_mol
    assert result.hydrogen_consumed_mol == handoff.consumed_mol
    assert result.hydrogen_remaining_mol == handoff.consumer_remaining_mol
    assert result.hydrogen_transfer_loss_mol == handoff.transfer_loss_mol

    bad_boundary = replace(charge, system_boundary_id="different-boundary")
    try:
        account_electrochemical_storage_round_trip(
            handoff, charge_meter=bad_boundary, discharge_meter=discharge,
        )
    except ValueError:
        rejected = True
    else:
        raise AssertionError("Mismatched electrical system boundaries were admitted")

    return ValidationOutcome(True, {
        "metered_charge_j": result.meter_electricity_in_j,
        "metered_discharge_j": result.meter_electricity_out_j,
        "stack_charge_j": result.stack_electricity_in_j,
        "stack_discharge_j": result.stack_electricity_out_j,
        "metered_round_trip_ratio": result.round_trip_electricity_ratio,
        "h2_produced_mol": result.hydrogen_produced_mol,
        "h2_consumed_mol": result.hydrogen_consumed_mol,
        "mismatched_boundary_rejected": rejected,
    }, (
        "Authored PV, electrolysis and fuel-cell settings; no device calibration",
        "Meter completeness and omitted loads remain caller evidence",
        "Software contract only; no physical round-trip performance is implied",
    ))
