"""Deferred accepted UH2SC dry-H2 withdrawal to compressor-input contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="underground-cavern-compressor-inlet-handoff",
        profile="underground-storage",
        entrypoint=__name__ + ":validate_inlet",
        invariants=(
            "accepted-native-cavern-withdrawal-bin-preserves-exact-clock-and-mass",
            "source-bin-flow-equals-integrated-dry-H2-withdrawal-over-the-selected-window",
            "CoolProp-HEOS-replays-the-explicit-representative-inlet-state",
            "native-and-representative-source-enthalpy-ledgers-remain-distinct-and-retained",
            "caller-signed-energy-mapping-closes-native-cavern-to-compressor-inlet-basis",
            "provider-window-state-efficiency-domain-transfer-and-clock-evidence-are-required",
            "adapter-returns-existing-compressor-inputs-without-executing-compression",
            "no-well-flow-law-pressure-loss-or-conditioning-solver-is-added",
        ),
    ),)


def validate_inlet(*, work_directory, **parameters):
    del work_directory, parameters
    import copy
    import numpy as np

    from examples.underground_storage import authored_inputs, authored_owner
    from h2physics.adapters.underground_compressor_inlet import (
        bind_underground_compressor_inlet,
    )
    from h2physics.release import SourceLocation
    from h2physics.thermo.coolprop import CoolPropProperties

    solver_options = {
        "TOL": 1.e-9, "LOG_PROGRESS": False, "MAXITER": 100,
        "USE_RELATIVE_CONVERGENCE": True,
    }
    trace = authored_owner().run(
        authored_inputs(mode="injection-withdrawal", step_s=2., rock_cells=8),
        solver_options=copy.deepcopy(solver_options),
    )
    projection = trace.withdrawal_projection(
        location=SourceLocation(
            "authored-cavern-compressor-outlet", trace.evidence.clock_id,
            trace.evidence.frame_id, (0., 0., 0.), (0., 0., 1.),
        ),
        representative_state=trace.snapshots[0].dry_hydrogen,
        flow_rule="trapezoid",
        quadrature_evidence_id="authored-cavern-bin-trapezoid",
        state_projection_evidence_id="authored-cavern-representative-dry-H2-state",
        end_reason="window_end",
    )
    projection.require_current()
    positive_bins = np.flatnonzero(projection.source.mass_kg > 0.)
    assert len(positive_bins) > 0
    index = int(positive_bins[0])
    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    state = projection.representative_state
    mass = float(projection.source.mass_kg[index])
    native_enthalpy = projection.native_dry_hydrogen_enthalpy_j[index]
    conditioning = mass*state.enthalpy_j_kg-native_enthalpy
    receipt = bind_underground_compressor_inlet(
        projection, provider, interval_index=index,
        discharge_pressure_pa=state.pressure_pa*1.5,
        isentropic_efficiency=.75,
        temperature_bounds_k=(state.temperature_k*.9, state.temperature_k*1.1),
        pressure_bounds_pa=(state.pressure_pa*.5, state.pressure_pa*1.7),
        provider_id="coolprop-hydrogen-heos",
        process_window_id=f"cavern-withdrawal-bin-{index}-compressor-window",
        state_evidence_id="authored-cavern-heos-inlet-state",
        efficiency_evidence_id="authored-compressor-efficiency",
        domain_evidence_id="authored-compressor-property-domain",
        transfer_evidence_id="authored-cavern-to-compressor-transfer-boundary",
        time_mapping_evidence_id="authored-uh2sc-clock-to-compressor-window",
        state_projection_evidence_id=projection.state_projection_evidence_id,
        energy_mapping_evidence_id="authored-native-to-compressor-enthalpy-mapping",
        conditioning_energy_j=conditioning,
        absolute_mass_tolerance_kg=1.e-12,
        relative_mass_tolerance=1.e-10,
        absolute_energy_tolerance_j=1.e-6,
        relative_energy_tolerance=1.e-10,
    )
    assert receipt.require_current() is receipt
    assert receipt.inputs.provider_id == "coolprop-hydrogen-heos"
    assert receipt.inputs.inlet_pressure_pa == state.pressure_pa
    assert receipt.inputs.inlet_temperature_k == state.temperature_k
    assert receipt.transferred_mass_kg == mass
    assert np.isclose(receipt.mass_flow_kg_s*(receipt.end_time_s-receipt.start_time_s),
                      mass, rtol=1.e-12, atol=1.e-15)
    assert receipt.native_source_enthalpy_j == native_enthalpy
    assert receipt.representative_source_enthalpy_j == projection.projected_enthalpy_j[index]
    assert abs(receipt.energy_mapping_residual_j) <= 1.e-6
    return ValidationOutcome(True, {
        "cavern_clock_id": trace.evidence.clock_id,
        "source_window_s": (receipt.start_time_s, receipt.end_time_s),
        "source_bin_index": index,
        "dry_hydrogen_withdrawal_kg": receipt.transferred_mass_kg,
        "compressor_inlet_mass_flow_kg_s": receipt.inputs.hydrogen_mass_flow_kg_s,
        "cavern_native_enthalpy_j": receipt.native_source_enthalpy_j,
        "representative_enthalpy_j": receipt.representative_source_enthalpy_j,
        "energy_mapping_j": receipt.supplied_energy_mapping_j,
        "energy_mapping_residual_j": receipt.energy_mapping_residual_j,
    }, (
        "Synthetic native cavern withdrawal and compressor-input contract only; compression is not run.",
        "Native implicit-step withdrawal enthalpy and caller representative-state enthalpy remain distinct; the supplied mapping ledger is not a heat exchanger model.",
        "No wellbore/tubing pressure loss or cavern-to-surface transient is added.",
    ))
