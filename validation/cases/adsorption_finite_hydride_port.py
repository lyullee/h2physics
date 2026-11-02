"""Deferred adsorption-vessel to finite-hydride inlet contract."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="adsorption-to-finite-hydride-gas-port-handoff",
        profile="finite-hydride",
        entrypoint=__name__ + ":validate_handoff",
        invariants=(
            "native adsorption outlet mole and enthalpy increments map to each finite-hydride inlet interval",
            "caller state projections preserve common H2 provider basis and interval enthalpy budgets",
            "each supplied inlet state exactly matches the accepted adsorption trace pressure and temperature",
            "accepted source times and explicit clock alignment define exact piecewise-constant bed-port support",
            "finite-hydride gas inventory and energy ledgers close against the accepted inlet boundary",
            "adapter does not infer line pressure loss, valve flow, or transfer hydraulics",
        ),
    ),)


def validate_handoff(*, work_directory, **parameters):
    del work_directory, parameters
    from validation.cases.adsorption_dynamics import _inputs
    from h2physics.adapters.adsorption_finite_hydride_port import bind_adsorption_to_finite_hydride
    from h2physics.storage.adsorption_dynamics import AdsorptionBoundaryRates, integrate_adsorption_dynamics
    from h2physics.storage.finite_hydride import (
        BoundHydrogenEnergyReference, FiniteHydrideBed, FiniteHydrideDomain,
        FiniteHydrideHeatBoundary, FiniteHydrideHeatInput, HydrideGasThermodynamics,
    )
    from h2physics.storage.hydride import (
        ArrheniusRate, HydrideKinetics, HydrideParameters, HydrideState,
        VanthoffPlateau,
    )

    def outlet(_state):
        return AdsorptionBoundaryRates(
            0., 0., 1.e-4, 0., "synthetic-adsorption-outlet", "synthetic-h2-energy-reference",
        )

    source = integrate_adsorption_dynamics(
        _inputs(outlet, end=2., boundaries=(0., 2.))
    )
    target_gas = HydrideGasThermodynamics.coolprop("Hydrogen")
    provider_states = tuple(
        source.inputs.vessel.gas.state_pt(float(p), float(t))
        for p, t in zip(source.pressure_pa[:-1], source.temperature_k[:-1], strict=True)
    )
    port = bind_adsorption_to_finite_hydride(
        source, target_gas, stream_states=provider_states,
        clock_id="authored-adsorption-to-hydride-clock",
        clock_alignment_evidence_id="authored-common-time-axis-mapping",
        hydraulic_transfer_evidence_id="authored-direct-port-hydraulic-boundary",
        state_projection_evidence_ids=tuple(
            f"authored-provider-state-projection-{i}" for i in range(len(provider_states))
        ),
        absolute_enthalpy_tolerance_j=100., relative_enthalpy_tolerance=1e-2,
    )
    port.require_current()

    material = HydrideParameters(.002, 1000., 24000., target_gas.molar_mass_kg_mol, 0.)
    kinetics = HydrideKinetics(
        VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(.01, 0., 300.), ArrheniusRate(.02, 0., 300.),
    )
    reference = BoundHydrogenEnergyReference.from_gas(
        target_gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-hydride-reference",
    )
    bed = FiniteHydrideBed(
        material, kinetics, target_gas, reference,
        FiniteHydrideDomain(200., 600., 1e3, 2e7, 1e-7),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.,
    )
    clock_id = port.clock_id
    heat = FiniteHydrideHeatBoundary(
        clock_id, float(source.time_s[0]), float(source.time_s[-1]),
        lambda _time, _snapshot: FiniteHydrideHeatInput(300.),
        "authored-isothermal-hydride-bath",
    )
    bed_trace = bed.simulate(
        source.time_s, HydrideState(.1, 300.),
        target_gas.state_pt(3e5, 300.), boundary=heat, clock_id=clock_id,
        maximum_step_s=.1, gas_port=port.boundary,
    )
    port.require_current()
    bed_trace.require_current()
    total_mapped = sum(rate*(right-left) for rate, left, right in zip(
        port.mass_flow_kg_s, source.time_s[:-1], source.time_s[1:], strict=True,
    ))
    assert bed_trace.gas_port_boundary is port.boundary
    assert np.isclose(bed_trace.integrated_external_gas_mass_kg[-1], total_mapped,
                      rtol=1e-9, atol=1e-12)
    return ValidationOutcome(True, {
        "source_intervals": len(port.mass_flow_kg_s),
        "accepted_h2_mass_kg": total_mapped,
        "bed_external_gas_enthalpy_j": float(bed_trace.integrated_external_gas_enthalpy_j[-1]),
        "maximum_bed_hydrogen_residual_kg": float(np.max(np.abs(bed_trace.total_hydrogen_residual_kg))),
        "maximum_bed_energy_residual_j": float(np.max(np.abs(bed_trace.total_energy_residual_j))),
    }, ("Synthetic provider/interface contract; no line hydraulic or pressure-flow validation is implied.",))
