"""Deferred linepack withdrawal to finite fuel-cell feed contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="linepack-fuel-cell-hydrogen-feed-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_feed",
        invariants=(
            "fuel-cell-feed-interval-and-clock-match-the-exact-linepack-bin",
            "H2-feed-moles-reproduce-the-accepted-linepack-withdrawal-mass",
            "caller-integrated-source-enthalpy-and-reference-conditioning-close",
            "mapped-feed-state-and-thermochemical-reference-are-explicit",
            "receipt-replays-source-mass-and-energy-evidence-without-running-fuel-cell",
            "no-linepack-energy-or-conditioning-solver-is-added",
        ),
    ),)


def validate_feed(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.linepack_fuel_cell_feed import bind_linepack_fuel_cell_feed
    from h2physics.adapters.linepack_source import advance_linepack_to_source
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    fuel_cell, _initial, commands = synthetic_problem()
    step = commands[0]
    duration = step.end_s-step.start_s
    withdrawn_mass = .02*duration
    state = IsothermalLinepackState.from_pressure(
        volume_m3=2., temperature_k=step.temperature_k,
        molecular_mass_kg_mol=.00201588, pressure_pa=5.e6, time_s=step.start_s,
    )
    outlet_pressure = (state.mass_kg-withdrawn_mass)*(
        8.31446261815324/state.molecular_mass_kg_mol
    )*state.temperature_k/state.volume_m3
    p = .5*(state.pressure_pa+outlet_pressure)
    properties = CoolPropProperties("Hydrogen")
    # This case is the explicit ideal-linepack contract. Its source density
    # must retain that owner's ideal basis; the real-fluid route is separate.
    rho = p*state.molecular_mass_kg_mol/(8.31446261815324*state.temperature_k)
    source_state = ThermoState(
        PropertyBasis("H2", "authored-linepack-feed-stream"), p,
        state.temperature_k, rho, 4.e5, 4.e5-p/rho, 0., "gas",
    )
    feed_state = properties.state_pt(fuel_cell.boundary.pressure_pa, step.temperature_k)
    location = SourceLocation("linepack-feed", step.clock_id, "pipe-axis",
                              (0., 0., 0.), (1., 0., 0.))
    source = advance_linepack_to_source(
        state, duration_s=duration, inlet_mass_flow_kg_s=0.,
        outlet_mass_flow_kg_s=.02, minimum_mass_kg=.01,
        location=location, gas_state=source_state, origin=Origin.SYNTHETIC,
        evidence_id="authored-linepack-fuel-cell-withdrawal",
        state_projection_evidence_id="authored-linepack-bin-state",
    )
    names = tuple(fuel_cell.kernel.names)
    h2 = fuel_cell.hydrogen_id
    hs = fuel_cell.caloric_source.provider.enthalpies_j_mol(
        feed_state.temperature_k, feed_state.pressure_pa)
    amount = source.ledger.outlet_mass_kg / fuel_cell.stack.geometry.hydrogen_molar_mass_kg_mol
    source_enthalpy = source.ledger.outlet_mass_kg*source_state.enthalpy_j_kg
    feed_enthalpy = amount*float(hs[names.index(h2)])
    reference_offset = 17.
    receipt = bind_linepack_fuel_cell_feed(
        source, fuel_cell, step, feed_source_id="authored-linepack-step0-H2-feed",
        origin=Origin.SYNTHETIC, fuel_cell_feed_state=feed_state,
        source_enthalpy_j=source_enthalpy,
        source_enthalpy_reference_id="authored-linepack-H-reference",
        receiver_energy_basis_id=fuel_cell.kernel.energy_basis_id,
        reference_offset_j=reference_offset,
        clock_evidence_id="authored-shared-linepack-cell-clock",
        state_evidence_id="authored-linepack-to-cell-state-projection",
        transfer_evidence_id="authored-linepack-to-cell-inlet-transfer",
        energy_evidence_id="authored-constant-bin-source-enthalpy-ledger",
        conditioning_energy_j=feed_enthalpy-source_enthalpy-reference_offset,
        absolute_mass_tolerance_kg=1.e-12, relative_mass_tolerance=1.e-10,
        absolute_energy_tolerance_j=1.e-6, relative_energy_tolerance=1.e-10,
    )
    assert receipt.require_current() is receipt
    assert receipt.source_mass_kg == source.ledger.outlet_mass_kg
    assert receipt.step.start_s == source.ledger.start_time_s
    assert receipt.step.end_s == source.ledger.end_time_s
    assert receipt.step.clock_id == source.source.location.clock_id
    assert receipt.feed.inventory.amounts_mol[h2] == receipt.feed_amount_mol
    assert receipt.feed.inventory.energy_basis_id == fuel_cell.kernel.energy_basis_id
    assert abs(receipt.energy_residual_j) <= 1.e-6
    assert receipt.receiver_energy_basis_id == fuel_cell.kernel.energy_basis_id
    assert receipt.source_enthalpy_reference_id == "authored-linepack-H-reference"
    assert receipt.reference_offset_j == reference_offset
    bad_basis_rejected = False
    try:
        bind_linepack_fuel_cell_feed(
            source, fuel_cell, step, feed_source_id="authored-invalid-basis-feed",
            origin=Origin.SYNTHETIC, fuel_cell_feed_state=feed_state,
            source_enthalpy_j=source_enthalpy,
            source_enthalpy_reference_id="authored-linepack-H-reference",
            receiver_energy_basis_id="wrong-energy-basis", reference_offset_j=reference_offset,
            clock_evidence_id="authored-shared-linepack-cell-clock",
            state_evidence_id="authored-linepack-to-cell-state-projection",
            transfer_evidence_id="authored-linepack-to-cell-inlet-transfer",
            energy_evidence_id="authored-constant-bin-source-enthalpy-ledger",
            conditioning_energy_j=feed_enthalpy-source_enthalpy-reference_offset,
            absolute_mass_tolerance_kg=1.e-12, relative_mass_tolerance=1.e-10,
            absolute_energy_tolerance_j=1.e-6, relative_energy_tolerance=1.e-10,
        )
    except ValueError:
        bad_basis_rejected = True
    assert bad_basis_rejected
    missing_source_reference_rejected = False
    try:
        bind_linepack_fuel_cell_feed(
            source, fuel_cell, step, feed_source_id="authored-missing-reference-feed",
            origin=Origin.SYNTHETIC, fuel_cell_feed_state=feed_state,
            source_enthalpy_j=source_enthalpy, source_enthalpy_reference_id=" ",
            receiver_energy_basis_id=fuel_cell.kernel.energy_basis_id,
            reference_offset_j=reference_offset,
            clock_evidence_id="authored-shared-linepack-cell-clock",
            state_evidence_id="authored-linepack-to-cell-state-projection",
            transfer_evidence_id="authored-linepack-to-cell-inlet-transfer",
            energy_evidence_id="authored-constant-bin-source-enthalpy-ledger",
            conditioning_energy_j=feed_enthalpy-source_enthalpy-reference_offset,
            absolute_mass_tolerance_kg=1.e-12, relative_mass_tolerance=1.e-10,
            absolute_energy_tolerance_j=1.e-6, relative_energy_tolerance=1.e-10,
        )
    except ValueError:
        missing_source_reference_rejected = True
    assert missing_source_reference_rejected
    rejected = False
    try:
        replace(receipt)
    except TypeError:
        rejected = True
    assert rejected
    return ValidationOutcome(True, {
        "interval_s": (receipt.start_time_s, receipt.end_time_s),
        "withdrawal_mass_kg": receipt.source_mass_kg,
        "feed_amount_mol": receipt.feed_amount_mol,
        "source_enthalpy_j": receipt.source_enthalpy_j,
        "feed_enthalpy_j": receipt.feed_enthalpy_j,
        "conditioning_energy_j": receipt.supplied_conditioning_energy_j,
        "energy_residual_j": receipt.energy_residual_j,
        "source_enthalpy_reference_id": receipt.source_enthalpy_reference_id,
        "receiver_energy_basis_id": receipt.receiver_energy_basis_id,
        "reference_offset_j": receipt.reference_offset_j,
        "mismatched_energy_basis_rejected": bad_basis_rejected,
        "missing_source_reference_rejected": missing_source_reference_rejected,
        "direct_reissue_rejected": rejected,
    }, (
        "The linepack owner supplies mass only; the caller supplies an interval-integrated enthalpy ledger.",
        "This case issues a fuel-cell packet without running the fuel-cell solver or modeling conditioning equipment.",
    ))
