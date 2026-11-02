"""Deferred PV-electrolysis product-to-linepack boundary contract."""

from dataclasses import replace
from math import isclose

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="pv-electrolysis-isothermal-linepack-charge-handoff",
        profile="pv-electrolysis",
        entrypoint=__name__ + ":validate_charge",
        parameters={"native_packages": "artifacts/native_pvlib_packages"},
        invariants=(
            "producer H2 species, neutral gas phase and molar mass match the linepack basis",
            "explicit transfer window starts after production and advances the linepack clock",
            "caller-evidenced source pressure lower bound exceeds final linepack pressure",
            "caller-evidenced source temperature bounds fit the fixed-isothermal linepack boundary",
            "explicit transfer loss and integrated linepack inlet mass close the H2 inventory ledger",
            "source initial/available/withdrawn/lost/retained/post-transfer H2 stock ledger closes",
            "source energy reference matches the accepted ThermoState basis and signed energy ledger closes",
            "missing/mismatched reference and nonclosing signed energy ledgers are rejected",
            "loss equal to the available batch, wrong clock/reference and forged/reissued receipts are rejected",
            "adapter adds no compressor, valve, thermal, pressure-drop or pipeline-flow solver",
        ),
    ), ValidationCase(
        identifier="pv-electrolysis-coolprop-linepack-charge-handoff",
        profile="pv-electrolysis",
        entrypoint=__name__ + ":validate_charge",
        parameters={"native_packages": "artifacts/native_pvlib_packages", "native_linepack": True},
        invariants=(
            "existing real-gas linepack uses matched native HEOS hydrogen",
            "declared storage energy equals CoolProp endpoint mass times internal energy difference",
            "all production clock, source withdrawal, pressure and energy gates remain enforced",
            "native EOS definition mutation is rejected after receipt issuance",
        ),
    ))


def validate_charge(*, work_directory, native_packages, native_linepack=False, **parameters):
    del work_directory, parameters
    from examples.pv_electrolysis import build_model, source_stages
    from h2physics.adapters.electrolysis_linepack import charge_linepack_from_electrolysis
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.thermo import CoolPropIsothermalEOS

    producer = build_model(native_packages=native_packages)
    trace = producer.run(
        source_stages(),
        initial_amounts_mol={"water": 2., "hydrogen": .2, "oxygen": .1},
        receiver_volume_m3=.01,
        receiver_temperature_k=298.15,
    )
    initial = IsothermalLinepackState.from_pressure(
        volume_m3=.05,
        temperature_k=trace.final.receiver.temperature_k,
        molecular_mass_kg_mol=trace.gas.molar_mass_kg_mol,
        pressure_pa=1.e4,
        time_s=trace.final.time_s,
    )
    if native_linepack:
        initial = RealGasLinepackState.from_pressure(
            volume_m3=.05, temperature_k=trace.final.receiver.temperature_k,
            pressure_pa=1.e4, time_s=trace.final.time_s,
            eos=CoolPropIsothermalEOS("Hydrogen"),
        )
    available = (trace.final.amounts_mol[producer.hydrogen_id]
                 - trace.initial.amounts_mol[producer.hydrogen_id])
    loss = .02 * available
    transferred_mass = ((available-loss) * trace.gas.molar_mass_kg_mol)
    transfer_start = trace.final.time_s
    transfer_end = transfer_start + 10.
    source_pressure_min = .5 * trace.final.receiver.pressure_pa
    source_reference = trace.final.receiver.basis.reference_id
    source_transfer_enthalpy = transferred_mass * trace.final.receiver.enthalpy_j_kg
    linepack_energy_change = 0.
    if native_linepack:
        expected_final, _ = initial.advance(
            duration_s=transfer_end-transfer_start,
            inlet_mass_flow_kg_s=transferred_mass/(transfer_end-transfer_start),
            outlet_mass_flow_kg_s=0.,
        )
        before = trace.gas.state_pt(initial.pressure_pa, initial.temperature_k)
        after = trace.gas.state_pt(expected_final.pressure_pa, expected_final.temperature_k)
        linepack_energy_change = (expected_final.mass_kg*after.internal_energy_j_kg
                                 - initial.mass_kg*before.internal_energy_j_kg)
    conditioning_energy = linepack_energy_change-source_transfer_enthalpy
    receipt = charge_linepack_from_electrolysis(
        initial, trace,
        source_withdrawal_mol=available,
        source_removal_evidence_id="authored-source-batch-stock-removal",
        transfer_loss_mol=loss,
        clock_id=trace.evidence.clock_id,
        transfer_start_s=transfer_start,
        transfer_end_s=transfer_end,
        minimum_source_pressure_margin_pa=1.e3,
        minimum_source_pressure_during_transfer_pa=source_pressure_min,
        source_temperature_bounds_k=(trace.final.receiver.temperature_k,
                                     trace.final.receiver.temperature_k),
        temperature_tolerance_k=1.e-6,
        time_mapping_evidence_id="authored-electrolysis-production-to-linepack-clock",
        hydrogen_basis_evidence_id="authored-neutral-H2-species-and-molar-mass-match",
        pressure_boundary_evidence_id="authored-source-pressure-above-linepack-final-pressure",
        isothermal_boundary_evidence_id="authored-equal-product-and-linepack-temperature",
        transfer_boundary_evidence_id="authored-finite-production-batch-transfer",
        source_transfer_state_evidence_id="authored-constant-product-state-for-separate-transfer-window",
        source_energy_reference_id=source_reference,
        linepack_energy_reference_id=source_reference,
        reference_mapping_evidence_id="same-admitted-H2-enthalpy-reference",
        boundary_energy_evidence_id="authored-isothermal-product-energy-boundary",
        reference_offset_j=0.,
        conditioning_energy_j=conditioning_energy,
        source_transfer_enthalpy_j=source_transfer_enthalpy,
        linepack_energy_change_j=linepack_energy_change,
        absolute_energy_tolerance_j=1.e-8,
        relative_energy_tolerance=1.e-12,
    )
    receipt.require_current()
    assert receipt.transferred_hydrogen_mol == available-loss
    assert receipt.ledger.inlet_mass_kg == receipt.transferred_hydrogen_mass_kg
    assert receipt.ledger.outlet_mass_kg == 0.
    assert isclose(receipt.final.mass_kg-receipt.initial.mass_kg,
                   receipt.transferred_hydrogen_mass_kg, rel_tol=1e-12, abs_tol=1e-15)
    assert receipt.ledger.start_time_s == transfer_start
    assert receipt.final.time_s == transfer_end
    assert abs(receipt.ledger.mass_residual_kg) <= 1.e-12
    assert abs(receipt.energy_ledger.residual_j) <= 1.e-8

    excessive_rejected = False
    try:
        charge_linepack_from_electrolysis(
            initial, trace,
            source_withdrawal_mol=available,
            source_removal_evidence_id="authored-source-batch-stock-removal",
            transfer_loss_mol=available,
            clock_id=trace.evidence.clock_id,
            transfer_start_s=transfer_start,
            transfer_end_s=transfer_end,
            minimum_source_pressure_during_transfer_pa=source_pressure_min,
            source_temperature_bounds_k=(trace.final.receiver.temperature_k,
                                         trace.final.receiver.temperature_k),
            time_mapping_evidence_id="authored-time-map",
            hydrogen_basis_evidence_id="authored-H2-basis",
            pressure_boundary_evidence_id="authored-pressure-boundary",
            isothermal_boundary_evidence_id="authored-isothermal-boundary",
            transfer_boundary_evidence_id="authored-transfer-boundary",
            source_transfer_state_evidence_id="authored-constant-state",
            source_energy_reference_id=source_reference,
            linepack_energy_reference_id=source_reference,
            reference_mapping_evidence_id="same-admitted-H2-enthalpy-reference",
            boundary_energy_evidence_id="authored-energy-boundary",
            reference_offset_j=0.,
            conditioning_energy_j=conditioning_energy,
            source_transfer_enthalpy_j=source_transfer_enthalpy,
            linepack_energy_change_j=linepack_energy_change,
        )
    except ValueError:
        excessive_rejected = True
    else:
        raise AssertionError("Loss equal to the entire produced batch was accepted")

    wrong_clock_rejected = False
    try:
        charge_linepack_from_electrolysis(
            initial, trace,
            source_withdrawal_mol=available,
            source_removal_evidence_id="authored-source-batch-stock-removal",
            clock_id="different-physical-clock",
            transfer_start_s=transfer_start,
            transfer_end_s=transfer_end,
            minimum_source_pressure_during_transfer_pa=source_pressure_min,
            source_temperature_bounds_k=(trace.final.receiver.temperature_k,
                                         trace.final.receiver.temperature_k),
            time_mapping_evidence_id="authored-time-map",
            hydrogen_basis_evidence_id="authored-H2-basis",
            pressure_boundary_evidence_id="authored-pressure-boundary",
            isothermal_boundary_evidence_id="authored-isothermal-boundary",
            transfer_boundary_evidence_id="authored-transfer-boundary",
            source_transfer_state_evidence_id="authored-constant-state",
            source_energy_reference_id=source_reference,
            linepack_energy_reference_id=source_reference,
            reference_mapping_evidence_id="same-admitted-H2-enthalpy-reference",
            boundary_energy_evidence_id="authored-energy-boundary",
            reference_offset_j=0.,
            conditioning_energy_j=conditioning_energy,
            source_transfer_enthalpy_j=source_transfer_enthalpy,
            linepack_energy_change_j=linepack_energy_change,
        )
    except ValueError:
        wrong_clock_rejected = True
    else:
        raise AssertionError("A different physical clock was accepted")

    wrong_energy_reference_rejected = False
    try:
        charge_linepack_from_electrolysis(
            initial, trace,
            source_withdrawal_mol=available,
            source_removal_evidence_id="authored-source-batch-stock-removal",
            clock_id=trace.evidence.clock_id,
            transfer_start_s=transfer_start,
            transfer_end_s=transfer_end,
            minimum_source_pressure_during_transfer_pa=source_pressure_min,
            source_temperature_bounds_k=(trace.final.receiver.temperature_k,
                                         trace.final.receiver.temperature_k),
            time_mapping_evidence_id="authored-time-map",
            hydrogen_basis_evidence_id="authored-H2-basis",
            pressure_boundary_evidence_id="authored-pressure-boundary",
            isothermal_boundary_evidence_id="authored-isothermal-boundary",
            transfer_boundary_evidence_id="authored-transfer-boundary",
            source_transfer_state_evidence_id="authored-constant-state",
            source_energy_reference_id="different-source-reference",
            linepack_energy_reference_id=source_reference,
            reference_mapping_evidence_id="mapping-cannot-relabel-source-basis",
            boundary_energy_evidence_id="authored-energy-boundary",
            reference_offset_j=0.,
            conditioning_energy_j=conditioning_energy,
            source_transfer_enthalpy_j=source_transfer_enthalpy,
            linepack_energy_change_j=linepack_energy_change,
        )
    except ValueError:
        wrong_energy_reference_rejected = True
    else:
        raise AssertionError("A source energy reference inconsistent with the accepted state was accepted")

    nonclosing_energy_rejected = False
    try:
        charge_linepack_from_electrolysis(
            initial, trace,
            source_withdrawal_mol=available,
            source_removal_evidence_id="authored-source-batch-stock-removal",
            clock_id=trace.evidence.clock_id,
            transfer_start_s=transfer_start,
            transfer_end_s=transfer_end,
            minimum_source_pressure_during_transfer_pa=source_pressure_min,
            source_temperature_bounds_k=(trace.final.receiver.temperature_k,
                                         trace.final.receiver.temperature_k),
            time_mapping_evidence_id="authored-time-map",
            hydrogen_basis_evidence_id="authored-H2-basis",
            pressure_boundary_evidence_id="authored-pressure-boundary",
            isothermal_boundary_evidence_id="authored-isothermal-boundary",
            transfer_boundary_evidence_id="authored-transfer-boundary",
            source_transfer_state_evidence_id="authored-constant-state",
            source_energy_reference_id=source_reference,
            linepack_energy_reference_id=source_reference,
            reference_mapping_evidence_id="same-admitted-H2-enthalpy-reference",
            boundary_energy_evidence_id="authored-energy-boundary",
            reference_offset_j=0.,
            conditioning_energy_j=conditioning_energy,
            source_transfer_enthalpy_j=source_transfer_enthalpy,
            linepack_energy_change_j=linepack_energy_change + 1.e6,
        )
    except ValueError:
        nonclosing_energy_rejected = True
    else:
        raise AssertionError("A nonclosing energy boundary ledger was accepted")

    reissue_rejected = False
    try:
        replace(receipt)
    except TypeError:
        reissue_rejected = True
    assert reissue_rejected
    balanced_ledger_mutation_rejected = False
    old_enthalpy = receipt.energy_ledger.source_transfer_enthalpy_j
    old_conditioning = receipt.energy_ledger.conditioning_energy_j
    try:
        object.__setattr__(receipt.energy_ledger, "source_transfer_enthalpy_j", old_enthalpy+100.)
        object.__setattr__(receipt.energy_ledger, "conditioning_energy_j", old_conditioning-100.)
        try:
            receipt.require_current()
        except ValueError:
            balanced_ledger_mutation_rejected = True
    finally:
        object.__setattr__(receipt.energy_ledger, "source_transfer_enthalpy_j", old_enthalpy)
        object.__setattr__(receipt.energy_ledger, "conditioning_energy_j", old_conditioning)
    assert balanced_ledger_mutation_rejected
    receipt.require_current()
    native_mutation_rejected = False
    if native_linepack:
        old_fluid = initial.eos.fluid
        try:
            initial.eos.fluid = "ParaHydrogen"
            try:
                receipt.require_current()
            except ValueError:
                native_mutation_rejected = True
        finally:
            initial.eos.fluid = old_fluid
        assert native_mutation_rejected
        receipt.require_current()
    return ValidationOutcome(True, {
        "available_hydrogen_mol": receipt.available_hydrogen_mol,
        "transferred_hydrogen_mol": receipt.transferred_hydrogen_mol,
        "transferred_hydrogen_mass_kg": receipt.transferred_hydrogen_mass_kg,
        "source_initial_h2_mol": receipt.source_ledger.initial_hydrogen_inventory_mol,
        "source_post_production_h2_mol": receipt.source_ledger.post_production_hydrogen_inventory_mol,
        "source_withdrawn_h2_mol": receipt.source_ledger.withdrawn_from_source_mol,
        "source_transfer_loss_h2_mol": receipt.source_ledger.transfer_loss_mol,
        "source_retained_batch_h2_mol": receipt.source_ledger.retained_production_batch_mol,
        "source_post_transfer_h2_mol": receipt.source_ledger.post_transfer_hydrogen_inventory_mol,
        "source_transfer_window_s": (receipt.transfer_start_s, receipt.transfer_end_s),
        "linepack_initial_pressure_pa": receipt.initial.pressure_pa,
        "linepack_final_pressure_pa": receipt.final.pressure_pa,
        "source_pressure_at_transfer_start_pa": receipt.source_pressure_at_start_pa,
        "minimum_source_pressure_during_transfer_pa": receipt.minimum_source_pressure_pa,
        "pressure_margin_pa": receipt.pressure_margin_pa,
        "source_temperature_bounds_k": receipt.source_temperature_bounds_k,
        "maximum_temperature_difference_k": receipt.maximum_temperature_difference_k,
        "source_transfer_enthalpy_j": receipt.energy_ledger.source_transfer_enthalpy_j,
        "mass_residual_kg": receipt.ledger.mass_residual_kg,
        "energy_residual_j": receipt.energy_ledger.residual_j,
        "native_linepack": native_linepack,
        "linepack_energy_change_j": receipt.energy_ledger.linepack_energy_change_j,
        "native_definition_mutation_rejected": native_mutation_rejected,
        "balanced_ledger_mutation_rejected": balanced_ledger_mutation_rejected,
        "excessive_loss_rejected": excessive_rejected,
        "wrong_clock_rejected": wrong_clock_rejected,
        "wrong_energy_reference_rejected": wrong_energy_reference_rejected,
        "nonclosing_energy_rejected": nonclosing_energy_rejected,
        "receipt_reissue_rejected": reissue_rejected,
    }, (
        "The PV/electrolysis inputs and output trace are synthetic and authored; no plant calibration is implied.",
        "The producer trace remains unchanged; the source receipt tracks H2 moles only and does not reflash post-transfer pressure/temperature.",
        "The boundary charges fixed-temperature lumped linepack inventory and does not solve transfer equipment or thermal conditioning.",
    ))
