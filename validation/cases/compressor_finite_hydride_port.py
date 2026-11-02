"""Deferred real-fluid compressor-to-finite-hydride storage contract."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-compressor-finite-hydride-gas-port-handoff",
        profile="finite-hydride",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "owner-issued-CoolProp-HEOS-compressor-discharge-state-is-retained",
            "discharge-is-pure-H2-on-the-same-spin-and-energy-reference-basis",
            "compressor-and-hydride-port-share-the-exact-H2-property-basis",
            "caller-state-projection-closes-P-T-density-enthalpy-and-entropy",
            "caller-clock-and-transfer-evidence-define-the-constant-flow-window",
            "accepted-compressor-mass-flow-and-discharge-enthalpy-enter-bed-port-ledgers",
            "directly-constructed-or-reissued-boundary-receipts-are-rejected",
            "stale-compressor-or-mutated-source-invalidates-the-handoff",
            "no-valve-flow-pressure-loss-or-transient-compressor-is-inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.compressor_finite_hydride_port import (
        bind_compressor_to_finite_hydride,
    )
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.core import ThermoState
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState,
        VanthoffPlateau,
    )
    from h2physics.thermo import CoolPropProperties
    from validation.cases.hydrogen_fuel_compression import _real_fluid_inputs

    compressor_provider = CoolPropProperties("Hydrogen", backend="HEOS")
    compressor = run_real_fluid_hydrogen_compression(
        compressor_provider, _real_fluid_inputs(process_window_id="hydride-charge-window"),
    )
    bed_gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    outlet = compressor.actual_outlet
    state = bed_gas.state_pt(outlet.pressure_pa, outlet.temperature_k)
    assert type(state) is ThermoState
    handoff = bind_compressor_to_finite_hydride(
        compressor, bed_gas, stream_state=state,
        clock_id="authored-compressor-bed-clock",
        start_time_s=0., end_time_s=.01,
        clock_alignment_evidence_id="authored-compressor-window-clock-map",
        hydraulic_transfer_evidence_id="authored-direct-transfer-boundary",
        state_projection_evidence_id="authored-coolprop-outlet-state-map",
        absolute_enthalpy_tolerance_j_kg=1., relative_enthalpy_tolerance=1e-7,
    )
    assert handoff.require_current() is handoff
    assert handoff.boundary.source_id == handoff.source_id

    material = HydrideParameters(.002, 1000., 24000., bed_gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        bed_gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-hydride-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, bed_gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 2e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    clock = handoff.clock_id
    heat = FiniteHydrideHeatBoundary(
        clock, handoff.start_time_s, handoff.end_time_s,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-isothermal-hydride-bath",
    )
    initial_gas = bed_gas.state_pt(300_000., 300.)
    trace = bed.simulate(
        np.asarray([handoff.start_time_s, handoff.end_time_s]),
        HydrideState(.1, 300.), initial_gas, boundary=heat, clock_id=clock,
        maximum_step_s=.002, gas_port=handoff.boundary,
    )
    handoff.require_current()
    trace.require_current()
    assert trace.gas_port_boundary is handoff.boundary
    assert np.isclose(trace.integrated_external_gas_mass_kg[-1],
                      handoff.transferred_mass_kg, rtol=1e-9, atol=1e-12)
    assert np.isclose(trace.integrated_external_gas_enthalpy_j[-1],
                      handoff.transferred_enthalpy_j, rtol=1e-8, atol=1e-7)

    from dataclasses import replace
    direct_reissue_rejected = False
    try:
        replace(handoff)
    except TypeError:
        direct_reissue_rejected = True
    assert direct_reissue_rejected

    original = state.pressure_pa
    object.__setattr__(state, "pressure_pa", original + 1.)
    mutation_rejected = False
    try:
        handoff.require_current()
    except ValueError:
        mutation_rejected = True
    finally:
        object.__setattr__(state, "pressure_pa", original)
    assert mutation_rejected
    assert handoff.require_current() is handoff

    return ValidationOutcome(True, {
        "compressor_process_window": compressor.inputs.process_window_id,
        "clock_id": handoff.clock_id,
        "mass_flow_kg_s": handoff.mass_flow_kg_s,
        "transferred_mass_kg": handoff.transferred_mass_kg,
        "transferred_enthalpy_j": handoff.transferred_enthalpy_j,
        "bed_hydrogen_residual_kg": float(np.max(np.abs(trace.total_hydrogen_residual_kg))),
        "bed_energy_residual_j": float(np.max(np.abs(trace.total_energy_residual_j))),
        "direct_reissue_rejected": direct_reissue_rejected,
        "post_issue_state_mutation_rejected": mutation_rejected,
    }, (
        "Existing CoolProp compressor and finite-hydride owners only; no compressor transient or line-flow validation.",
        "Clock alignment, transfer hydraulics and compressor-state-to-bed mapping remain caller-owned evidence.",
    ))
