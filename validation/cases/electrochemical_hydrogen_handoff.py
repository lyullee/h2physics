"""Deferred PV-production to finite fuel-cell inventory bridge contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrolysis-fuel-cell-single-batch-handoff",
        profile="pv-electrolysis",
        entrypoint=__name__ + ":validate_handoff",
        parameters={"native_packages": "artifacts/native_pvlib_packages"},
        invariants=(
            "native producer retains a positive EOS seed and transfers only its net H2 inventory increase",
            "finite consumer begins on the producer clock at the completed production time",
            "transfer amount equals producer H2 minus explicit loss and consumer initial stock",
            "species and original source/sink ports match across both native traces",
            "wrong transferred amount is rejected within the declared molar budget",
            "post-binding transfer evidence relabeling invalidates the handoff receipt",
            "molar inventory closure does not claim thermal, pressure or storage-path closure",
        ),
    ), ValidationCase(
        identifier="pv-electrolysis-real-fluid-compressor-inlet-handoff",
        profile="pv-electrolysis",
        entrypoint=__name__ + ":validate_compressor_inlet",
        parameters={"native_packages": "artifacts/native_pvlib_packages"},
        invariants=(
            "producer output pressure/temperature, EOS basis, and clock bind to the compressor inlet",
            "only net H2 produced by the accepted trace is available for the declared finite withdrawal",
            "compressor withdrawal interval begins after production and preserves the producer clock",
            "withdrawal exceeding the accepted H2 batch is rejected",
            "no regulator, conditioning, receiver-pressure trajectory or compressor solution is inferred",
        ),
    ),)


def validate_handoff(*, work_directory, native_packages, **parameters):
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from examples.pv_electrolysis import build_model, source_stages
    from h2physics.adapters.electrochemical_hydrogen_handoff import (
        HydrogenHandoffError,
        bind_electrolysis_to_fuel_cell,
    )
    from h2physics.thermochemical import ThermochemicalInventory

    producer = build_model(native_packages=native_packages)
    produced_trace = producer.run(
        source_stages(),
        initial_amounts_mol={"water": 2.0, "hydrogen": 0.2, "oxygen": 0.1},
        receiver_volume_m3=0.01,
        receiver_temperature_k=298.15,
    )
    produced = (produced_trace.final.amounts_mol[producer.hydrogen_id]
                - produced_trace.initial.amounts_mol[producer.hydrogen_id])
    assert produced > 0.0

    consumer, _unused_initial, commands = synthetic_problem(
        hydrogen_id=producer.hydrogen_id,
        hydrogen_molar_mass_kg_mol=producer.gas.molar_mass_kg_mol,
        clock_id=produced_trace.evidence.clock_id,
    )
    transfer_loss = produced * 0.02
    delivered = produced - transfer_loss
    initial = ThermochemicalInventory(
        {consumer.hydrogen_id: delivered, "O2": 0.007, "H2O": 0.001},
        320.0,
        consumer.boundary.pressure_pa,
        consumer.caloric_source.provider.basis_id,
    )
    consumer_command = replace(
        commands[0], start_s=produced_trace.final.time_s,
        end_s=produced_trace.final.time_s + 10.0,
        clock_id=produced_trace.evidence.clock_id,
    )
    consumed_trace = consumer.run(initial, (consumer_command,))
    receipt = bind_electrolysis_to_fuel_cell(
        produced_trace,
        consumed_trace,
        transfer_loss_mol=transfer_loss,
        source_id=produced_trace.evidence.source_id,
        sink_id=consumed_trace.boundary.hydrogen_inlet_id,
        transfer_evidence_id="authored-single-batch-transfer",
        conditioning_evidence_id="authored-state-conditioning-boundary",
        closure_tolerance_mol=1e-10,
    )
    assert receipt.require_current() is receipt


    assert abs(receipt.produced_mol - receipt.delivered_mol - transfer_loss) <= receipt.closure_tolerance_mol
    assert receipt.consumed_mol > 0.0
    assert receipt.consumer_remaining_mol >= 0.0
    original_transfer_evidence = receipt.transfer_evidence_id
    object.__setattr__(receipt, "transfer_evidence_id", "relabeled-after-admission")
    try:
        receipt.require_current()
    except HydrogenHandoffError as error:
        assert "changed after construction" in str(error)
    else:
        raise AssertionError("A handoff accepted transfer-evidence relabeling after admission")
    object.__setattr__(receipt, "transfer_evidence_id", original_transfer_evidence)
    assert receipt.require_current() is receipt

    try:
        bind_electrolysis_to_fuel_cell(
            produced_trace,
            consumed_trace,
            transfer_loss_mol=produced * 0.1,
            source_id=produced_trace.evidence.source_id,
            sink_id=consumed_trace.boundary.hydrogen_inlet_id,
            transfer_evidence_id="authored-intentionally-inconsistent-transfer",
            conditioning_evidence_id="authored-state-conditioning-boundary",
            closure_tolerance_mol=1e-10,
        )
    except HydrogenHandoffError:
        rejected = True
    else:
        raise AssertionError("A delivered amount inconsistent with sink stock was admitted")
    assert rejected

    try:
        synthetic_problem(
            hydrogen_id=producer.hydrogen_id,
            hydrogen_molar_mass_kg_mol=producer.gas.molar_mass_kg_mol * 1.01,
            clock_id=produced_trace.evidence.clock_id,
        )
    except ValueError as error:
        assert "CoolProp Hydrogen" in str(error)
        alias_mismatch_rejected = True
    else:
        raise AssertionError("Same-name H2 species with a different molar mass was accepted")
    return ValidationOutcome(True, {
        "produced_h2_mol": receipt.produced_mol,
        "consumed_h2_mol": receipt.consumed_mol,
        "remaining_h2_mol": receipt.consumer_remaining_mol,
        "wrong_transfer_rejected": rejected,
        "evidence_relabeling_rejected": True,
        "coolprop_consumer_mass_override_rejected": alias_mismatch_rejected,
    }, (
        "Authored PV and electrical loss parameters; CoolProp calorimetry; no device calibration",
        "Inventory handoff only; pressure, phase, transport and thermal conditioning are caller evidence",
        "Deferred execution; no scientific result is implied by this case definition",
    ))


def validate_compressor_inlet(*, work_directory, native_packages, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from examples.pv_electrolysis import build_model, source_stages
    from h2physics.adapters.electrolysis_compressor_inlet import (
        bind_electrolysis_compressor_inlet,
    )
    from h2physics.combustion.fuel_compression import HydrogenRealFluidCompressionInputs
    from h2physics.thermo.coolprop import CoolPropProperties

    producer = build_model(native_packages=native_packages)
    trace = producer.run(
        source_stages(),
        initial_amounts_mol={"water": 2.0, "hydrogen": 0.2, "oxygen": 0.1},
        receiver_volume_m3=0.01, receiver_temperature_k=298.15,
    )
    provider = CoolPropProperties("Hydrogen")
    source = trace.final.receiver
    window = "authored-electrolyzer-product-withdrawal-window"
    end = trace.final.time_s + 10.0
    produced_mol = (trace.final.amounts_mol[producer.hydrogen_id]
                    - trace.initial.amounts_mol[producer.hydrogen_id])
    draw_mass = produced_mol * trace.gas.molar_mass_kg_mol * .1
    inputs = HydrogenRealFluidCompressionInputs(
        provider_id="authored-coolprop-heos-hydrogen",
        process_window_id=window,
        inlet_temperature_k=source.temperature_k,
        inlet_pressure_pa=source.pressure_pa,
        discharge_pressure_pa=2.0*source.pressure_pa,
        hydrogen_mass_flow_kg_s=draw_mass/10.0,
        isentropic_efficiency=.75,
        temperature_bounds_k=(100., 1000.),
        pressure_bounds_pa=(1e4, 1e8),
        state_evidence_id="authored-direct-electrolyzer-to-compressor-state-map",
        efficiency_evidence_id="authored-independent-compressor-efficiency",
        domain_evidence_id="authored-coolprop-compressor-domain",
    )
    receipt = bind_electrolysis_compressor_inlet(
        trace, provider, inputs,
        provider_id=inputs.provider_id, process_window_id=window,
        clock_id=trace.evidence.clock_id,
        withdrawal_start_s=trace.final.time_s, withdrawal_end_s=end,
        transfer_evidence_id=inputs.state_evidence_id,
    )
    receipt.require_current()
    assert receipt.withdrawn_hydrogen_kg <= (
        receipt.available_hydrogen_mol*trace.gas.molar_mass_kg_mol
    )
    excessive = replace(inputs, hydrogen_mass_flow_kg_s=inputs.hydrogen_mass_flow_kg_s*20.)
    try:
        bind_electrolysis_compressor_inlet(
            trace, provider, excessive, provider_id=excessive.provider_id,
            process_window_id=window, clock_id=trace.evidence.clock_id,
            withdrawal_start_s=trace.final.time_s, withdrawal_end_s=end,
            transfer_evidence_id=excessive.state_evidence_id,
        )
    except ValueError:
        rejected = True
    else:
        raise AssertionError("Compressor feed withdrawal exceeded the finite electrolyzer H2 batch")
    return ValidationOutcome(True, {
        "available_hydrogen_mol": receipt.available_hydrogen_mol,
        "withdrawn_hydrogen_kg": receipt.withdrawn_hydrogen_kg,
        "source_pressure_pa": source.pressure_pa,
        "source_temperature_k": source.temperature_k,
        "excess_withdrawal_rejected": rejected,
    }, ("The adapter creates compressor inputs only; it does not solve the compressor or model pressure conditioning.",))
