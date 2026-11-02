"""Deferred finite-hydride desorption to real-fluid compressor contract."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-hydride-desorption-mechanical-compressor-handoff",
        profile="finite-hydride",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "only-positive-accepted-outward-H2-bed-intervals-feed-compression",
            "negative-into-bed-mass-and-enthalpy-increments-close-to-positive-compressor-inlet-ledgers",
            "each-native-compressor-run-is-bound-to-one-exact-bed-time-window",
            "process-window-id-plus-caller-clock-evidence-is-the-only-time-correspondence",
            "compressor-inlet-state-matches-selected-native-bed-edge-state-and-H2-basis",
            "compressor-throughput-closes-to-accepted-integrated-bed-withdrawal",
            "compressor-inlet-enthalpy-closes-to-accepted-integrated-port-energy",
            "state-clock-and-transfer-evidence-are-retained-for-each-interval",
            "direct-construction-or-reissuance-is-rejected-and-source-mutation-invalidates-link",
            "no-unmodeled-transfer-pressure-drop-or-conditioning-is-inferred",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.finite_hydride_compressor_inlet import (
        bind_finite_hydride_to_compressor,
    )
    from h2physics.combustion.fuel_compression import run_real_fluid_hydrogen_compression
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideGasPortBoundary, FiniteHydrideGasPortInput,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState,
        VanthoffPlateau,
    )
    from h2physics.thermo import CoolPropProperties
    from validation.cases.hydrogen_fuel_compression import _real_fluid_inputs

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-hydride-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 2e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    clock_id = "authored-hydride-compressor-clock"
    start, end = 0., .02
    source_id = "authored-bed-to-compressor-feed"
    rate = 2e-5
    gas_port = FiniteHydrideGasPortBoundary(
        clock_id, start, end,
        lambda _time, snapshot: FiniteHydrideGasPortInput(-rate, snapshot.gas, source_id),
        source_id,
    )
    heat = FiniteHydrideHeatBoundary(
        clock_id, start, end,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-isothermal-hydride-bath",
    )
    trace = bed.simulate(
        np.asarray([start, .01, end]), HydrideState(.5, 300.),
        gas.state_pt(300_000., 300.), boundary=heat, clock_id=clock_id,
        maximum_step_s=.002, gas_port=gas_port,
    )
    trace.require_current()

    times = tuple(float(value) for value in trace.time_s)
    withdrawn = -np.diff(trace.integrated_external_gas_mass_kg)
    provider = CoolPropProperties("Hydrogen", backend="HEOS")
    runs = []
    windows = []
    for index, mass in enumerate(withdrawn):
        source = trace.snapshots[index].gas
        duration = times[index+1]-times[index]
        window = f"{clock_id}:{index}:{times[index]:.17g}:{times[index+1]:.17g}"
        windows.append(window)
        inputs = _real_fluid_inputs(
            process_window_id=window,
            inlet_temperature_k=source.temperature_k,
            inlet_pressure_pa=source.pressure_pa,
            discharge_pressure_pa=2.*source.pressure_pa,
            hydrogen_mass_flow_kg_s=float(mass)/duration,
            state_evidence_id=f"authored-edge-state-map-{index}",
            efficiency_evidence_id=f"authored-compressor-efficiency-{index}",
            domain_evidence_id=f"authored-compressor-domain-{index}",
        )
        runs.append(run_real_fluid_hydrogen_compression(provider, inputs))

    link = bind_finite_hydride_to_compressor(
        trace, tuple(runs), source_edge_indices=tuple(range(len(runs))),
        process_window_ids=tuple(windows),
        clock_alignment_evidence_ids=tuple(f"authored-clock-alignment-{i}" for i in range(len(runs))),
        hydraulic_transfer_evidence_ids=tuple(f"authored-direct-transfer-{i}" for i in range(len(runs))),
        state_projection_evidence_ids=tuple(f"authored-edge-state-map-{i}" for i in range(len(runs))),
        absolute_mass_tolerance_kg=1e-10, relative_mass_tolerance=1e-6,
        absolute_energy_tolerance_j=1e-5, relative_energy_tolerance=1e-2,
    )
    assert link.require_current() is link
    assert all(abs(value) <= 1e-10+1e-6*mass for value, mass in zip(
        link.mass_residual_kg, link.interval_withdrawal_mass_kg, strict=True,
    ))
    assert all(abs(value) <= 1e-5+1e-2*max(abs(energy), 1.)
               for value, energy in zip(link.enthalpy_residual_j,
                                        link.interval_exported_enthalpy_j, strict=True))

    from dataclasses import replace
    direct_reissue_rejected = False
    try:
        replace(link)
    except TypeError:
        direct_reissue_rejected = True
    assert direct_reissue_rejected
    return ValidationOutcome(True, {
        "mapped_intervals": len(link.interval_withdrawal_mass_kg),
        "withdrawn_hydrogen_mass_kg": sum(link.interval_withdrawal_mass_kg),
        "withdrawn_hydrogen_enthalpy_j": sum(link.interval_exported_enthalpy_j),
        "maximum_mass_residual_kg": max(abs(value) for value in link.mass_residual_kg),
        "maximum_enthalpy_residual_j": max(abs(value) for value in link.enthalpy_residual_j),
        "direct_reissue_rejected": direct_reissue_rejected,
    }, (
        "Synthetic interface contract only; no compressor-map, line-flow or transfer-loss behavior is implied.",
        "The existing thermal hydride-compressor model is distinct and is not replaced by this coupling.",
    ))
