"""Deferred finite-hydride desorption to fuel-cell feed contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-hydride-fuel-cell-hydrogen-feed-handoff",
        profile="finite-hydride",
        entrypoint=__name__ + ":validate_feed",
        invariants=(
            "one-fuel-cell-step-matches-the-exact-hydride-outlet-interval-and-clock",
            "positive-H2-feed-mass-and-enthalpy-equal-negative-bed-port-ledger-deltas",
            "H2-elemental-charge-and-molar-mass-bases-match-the-existing-fuel-cell-reaction",
            "caller-feed-state-and-energy-basis-mapping-close-with-signed-conditioning-ledger",
            "all-source-edge-states-remain-retained-and-variable-histories-are-not-collapsed-silently",
            "existing-fuel-cell-step-receives-one-separate-H2-port-packet",
            "replayed-receipt-rejects-direct-reissue-and-no-fuel-cell-solver-is-run",
        ),
    ),)


def validate_feed(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    import numpy as np

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.finite_hydride_fuel_cell_feed import (
        bind_finite_hydride_fuel_cell_feed,
    )
    from h2physics.core import Origin
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideGasPortBoundary, FiniteHydrideGasPortInput,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput,
        HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState,
        VanthoffPlateau,
    )

    fuel_cell, _initial, commands = synthetic_problem()
    step = commands[0]
    clock = fuel_cell.evidence.clock_id
    start, end = step.start_s, step.end_s
    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1.e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas, temperature_k=300., pressure_pa=1.e5,
        desorption_enthalpy_j_mol_h2=24000.,
        evidence_id="authored-hydride-fuel-cell-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1.e3, 1.e7, 1.e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    heat = FiniteHydrideHeatBoundary(
        clock, start, end,
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-fuel-cell-coupling-bath",
    )
    initial_gas = gas.state_pt(3.e5, 300.)
    port = FiniteHydrideGasPortBoundary(
        clock, start, end,
        lambda _time, snapshot: FiniteHydrideGasPortInput(
            -1.e-8, snapshot.gas, "authored-desorption-to-fuel-cell-boundary"),
        "authored-desorption-to-fuel-cell-boundary",
    )
    trace = bed.simulate(
        np.array([start, end]), HydrideState(.1, 300.), initial_gas,
        boundary=heat, clock_id=clock, maximum_step_s=(end-start)/2,
        gas_port=port,
    )
    feed_state = trace.snapshots[0].gas
    names = tuple(fuel_cell.kernel.names)
    h2_index = names.index(fuel_cell.hydrogen_id)
    molar_h = fuel_cell.caloric_source.provider.enthalpies_j_mol(
        feed_state.temperature_k, feed_state.pressure_pa,
    )[h2_index]
    mass = -(trace.integrated_external_gas_mass_kg[-1]
             - trace.integrated_external_gas_mass_kg[0])
    exported_h = -(trace.integrated_external_gas_enthalpy_j[-1]
                   - trace.integrated_external_gas_enthalpy_j[0])
    amount = mass/fuel_cell.stack.geometry.hydrogen_molar_mass_kg_mol
    conditioning = amount*molar_h-exported_h
    receipt = bind_finite_hydride_fuel_cell_feed(
        trace, fuel_cell, step,
        interval_index=0,
        feed_source_id="authored-hydride-step0-H2-feed",
        origin=Origin.SYNTHETIC,
        fuel_cell_feed_state=feed_state,
        clock_mapping_evidence_id="authored-shared-hydride-cell-clock",
        state_mapping_evidence_id="authored-H2-feed-state-projection",
        transfer_evidence_id="authored-bed-port-to-cell-inlet-transfer",
        energy_mapping_evidence_id="authored-bed-to-cell-energy-reference-map",
        conditioning_energy_j=conditioning,
        absolute_mass_tolerance_kg=1.e-12,
        relative_mass_tolerance=1.e-10,
        absolute_energy_tolerance_j=1.e-6,
        relative_energy_tolerance=1.e-10,
    )
    assert receipt.require_current() is receipt
    assert receipt.step.start_s == trace.time_s[0]
    assert receipt.step.end_s == trace.time_s[-1]
    assert receipt.step.clock_id == trace.clock_id
    assert receipt.feed.inventory.amounts_mol[fuel_cell.hydrogen_id] == receipt.feed_amount_mol
    assert receipt.feed.inventory.energy_basis_id == fuel_cell.kernel.energy_basis_id
    assert receipt.source_mass_kg == mass
    assert receipt.source_enthalpy_j == exported_h
    assert receipt.source_state is trace.snapshots[0].gas
    assert receipt.source_end_state is trace.snapshots[-1].gas
    assert abs(receipt.conditioning_energy_residual_j) <= 1.e-6
    assert receipt.step.feed_ports[receipt.feed_source_id] == fuel_cell.boundary.hydrogen_inlet_id
    reissue_rejected = False
    try:
        replace(receipt)
    except TypeError:
        reissue_rejected = True
    assert reissue_rejected
    return ValidationOutcome(True, {
        "source_clock_id": trace.clock_id,
        "interval_s": (receipt.start_time_s, receipt.end_time_s),
        "H2_outflow_mass_kg": receipt.source_mass_kg,
        "H2_feed_amount_mol": receipt.feed_amount_mol,
        "source_enthalpy_j": receipt.source_enthalpy_j,
        "fuel_cell_feed_enthalpy_j": receipt.feed_enthalpy_j,
        "conditioning_energy_j": receipt.supplied_conditioning_energy_j,
        "conditioning_energy_residual_j": receipt.conditioning_energy_residual_j,
        "fuel_cell_step_feed_count": len(receipt.step.feeds),
        "direct_reissue_rejected": reissue_rejected,
    }, (
        "Synthetic one-interval source and feed contract only; the fuel-cell solver is not run.",
        "Any state or energy-reference conditioning is caller-owned evidence, not a modeled regulator or heat exchanger.",
        "Hydride outlet state histories remain in the original trace; the representative feed state is caller supplied.",
    ))
