"""Deferred typed linepack outlet to compressor-inlet boundary."""

from dataclasses import replace

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-linepack-compressor-inlet-handoff",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_inlet",
        invariants=(
            "accepted-linepack-withdrawal-interval-and-integrated-mass-fix-compressor-inlet-flow",
            "linepack-source-pressure-and-temperature-are-preserved-at-compressor-suction",
            "mapped-inlet-state-is-replayed-by-the-existing-pure-H2-HEOS-property-owner",
            "signed-linepack-to-HEOS-enthalpy-conditioning-ledger-closes",
            "time-clock-transfer-state-efficiency-and-domain-evidence-are-explicit",
            "stale-or-reissued-linepack-compressor-receipts-are-rejected",
            "adapter-returns-existing-compressor-inputs-without-running-the-compressor",
            "no-pressure-loss-or-thermal-conditioning-solver-is-added",
        ),
    ),)


def validate_inlet(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.linepack_compressor_inlet import bind_linepack_compressor_inlet
    from h2physics.adapters.linepack_source import advance_linepack_to_source
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.pipeline_linepack import IsothermalLinepackState
    from h2physics.release import SourceLocation
    from h2physics.thermo import CoolPropProperties

    initial = IsothermalLinepackState.from_pressure(
        volume_m3=2., temperature_k=293.15,
        molecular_mass_kg_mol=.00201588, pressure_pa=5.e6, time_s=20.,
    )
    duration, withdrawal_rate = 10., .02
    final_pressure = (initial.mass_kg-withdrawal_rate*duration) * (
        8.31446261815324/initial.molecular_mass_kg_mol
    ) * initial.temperature_k/initial.volume_m3
    representative_pressure = .5*(initial.pressure_pa+final_pressure)
    representative_density = representative_pressure*initial.molecular_mass_kg_mol / (
        8.31446261815324*initial.temperature_k
    )
    source_state = ThermoState(
        PropertyBasis("H2", "authored-linepack-midpoint-state"),
        representative_pressure, initial.temperature_k, representative_density,
        5.e5, 5.e5-representative_pressure/representative_density, 0., "gas",
    )
    location = SourceLocation(
        "pipeline-withdrawal", "authored-linepack-clock", "pipe-axis-frame",
        (0., 0., 0.), (1., 0., 0.),
    )
    source = advance_linepack_to_source(
        initial, duration_s=duration, inlet_mass_flow_kg_s=0.,
        outlet_mass_flow_kg_s=withdrawal_rate, minimum_mass_kg=.01,
        location=location, gas_state=source_state, origin=Origin.SYNTHETIC,
        evidence_id="authored-linepack-outlet-withdrawal",
        state_projection_evidence_id="authored-linepack-representative-state",
    )
    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    mapped = provider.state_pt(source_state.pressure_pa, source_state.temperature_k)
    transferred_mass = source.source.total_mass_kg
    conditioning = transferred_mass*(mapped.enthalpy_j_kg-source_state.enthalpy_j_kg)
    receipt = bind_linepack_compressor_inlet(
        source, provider, discharge_pressure_pa=10.e6,
        isentropic_efficiency=.75, temperature_bounds_k=(250., 400.),
        pressure_bounds_pa=(1.e5, 20.e6),
        process_window_id="linepack-withdrawal-to-compressor-window",
        provider_id="coolprop-hydrogen-heos",
        state_evidence_id="authored-linepack-to-HEOS-inlet-state",
        efficiency_evidence_id="authored-compressor-efficiency",
        domain_evidence_id="authored-compressor-domain",
        transfer_evidence_id="authored-linepack-suction-boundary",
        time_mapping_evidence_id="authored-linepack-clock-to-process-window",
        conditioning_evidence_id="authored-signed-state-conditioning-ledger",
        conditioning_energy_j=conditioning,
        absolute_energy_tolerance_j=1.e-6,
        relative_energy_tolerance=1.e-10,
    )
    assert receipt.require_current() is receipt
    assert receipt.inputs.inlet_pressure_pa == source_state.pressure_pa
    assert receipt.inputs.inlet_temperature_k == source_state.temperature_k
    assert receipt.inputs.hydrogen_mass_flow_kg_s == withdrawal_rate
    assert receipt.transferred_mass_kg == source.ledger.outlet_mass_kg
    assert receipt.start_time_s == source.source.edges_s[0]
    assert receipt.end_time_s == source.source.edges_s[-1]
    assert abs(receipt.conditioning_energy_residual_j) <= 1.e-6

    reissue_rejected = False
    try:
        replace(receipt)
    except TypeError:
        reissue_rejected = True
    assert reissue_rejected
    return ValidationOutcome(True, {
        "source_clock_id": source.source.location.clock_id,
        "source_window_s": (receipt.start_time_s, receipt.end_time_s),
        "withdrawal_mass_kg": receipt.transferred_mass_kg,
        "compressor_inlet_mass_flow_kg_s": receipt.inputs.hydrogen_mass_flow_kg_s,
        "compressor_inlet_pressure_pa": receipt.inputs.inlet_pressure_pa,
        "compressor_inlet_temperature_k": receipt.inputs.inlet_temperature_k,
        "conditioning_energy_j": receipt.supplied_conditioning_energy_j,
        "conditioning_energy_residual_j": receipt.conditioning_energy_residual_j,
        "direct_reissue_rejected": reissue_rejected,
    }, (
        "The source state is a caller-projected ideal-H2 representative state; the HEOS enthalpy difference is caller-accounted.",
        "This case creates compressor inputs only; it does not run or qualify compression, pressure-loss, or conditioning models.",
    ))
