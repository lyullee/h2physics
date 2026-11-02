"""Deferred finite-hydride to vessel-history interface contract."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="finite-hydride-vessel-failure-history-handoff",
        profile="finite-hydride",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "accepted H2 absolute pressure, clock, and EOS basis are retained exactly",
            "one caller-mapped shell temperature and geometry evidence item is required per declared wall region",
            "solid-bed temperature is never relabeled as vessel wall temperature",
            "HELPR remains the sole failure criterion and pressure differential is formed downstream",
            "mutated provider/state ownership invalidates history reconstruction",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.finite_hydride_vessel_failure import history_from_finite_hydride
    from h2physics.adapters.vessel_failure import VesselFailureContext
    from h2physics.core import Origin
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState,
        VanthoffPlateau,
    )

    gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    material = HydrideParameters(.002, 1000., 24000., gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000.,
        evidence_id="authored-interface-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 1e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    clock = "authored-hydride-vessel-common-clock"
    boundary = FiniteHydrideHeatBoundary(
        clock, 100., 101., lambda _t, _s: FiniteHydrideHeatInput(300.),
        "authored-constant-bed-boundary",
    )
    trace = bed.simulate(
        np.array([100., 100.5, 101.]), HydrideState(.1, 300.),
        gas.state_pt(3e5, 300.), boundary=boundary, clock_id=clock,
        maximum_step_s=.25,
    )
    context = VesselFailureContext(
        "authored-hydride-vessel", "authored-shell-region", "authored-frame",
        clock, gas.source_id, gas.basis, 1., "authored-pure-H2-service",
        "authored-independent-shell-temperature-mapping",
        "authored-shell-geometry-mapping", Origin.SYNTHETIC,
    )
    history = history_from_finite_hydride(
        trace, context=context, wall_temperature_k=(300., 301., 302.),
        external_pressure_pa_absolute=lambda _t: 101325.,
        shell_id=context.wall_region_id,
        wall_mapping_evidence_id=context.wall_temperature_evidence_id,
        geometry_mapping_evidence_id=context.geometry_binding_evidence_id,
        reconstruction_evidence_id="authored-pressure-history-reconstruction",
    )
    assert len(history.samples) == len(trace.snapshots)
    assert all(sample.internal_pressure_pa_absolute == state.gas.pressure_pa
               for sample, state in zip(history.samples, trace.snapshots, strict=True))
    assert tuple(sample.wall_temperature_k for sample in history.samples) == (300., 301., 302.)
    return ValidationOutcome(True, {
        "accepted_samples": len(history.samples),
        "absolute_pressure_pa_first": history.samples[0].internal_pressure_pa_absolute,
        "clock_id": history.context.clock_id,
    }, ("Caller maps shell temperature and geometry; this contract does not execute HELPR or establish failure probability.",))
