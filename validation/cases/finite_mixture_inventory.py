"""Deferred synthetic contract for accepted finite mixture V/U intervals."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "The authored initial VLE packet and tiny synthetic feed are software contracts, not measured data.",
    "The interval update is explicit first-order finite-volume marching on caller-selected endpoints.",
    "Only bounded two-phase states are admitted; phase-event localization and wall storage are outside scope.",
    "A successful case does not qualify the mixture EOS, binary interactions, or separator hardware.",
)


def cases():
    return (ValidationCase(
        identifier="finite-mixture-vu-accepted-steps",
        profile="mixture-vle",
        entrypoint=__name__ + ":validate_interval_march",
        invariants=(
            "a new immutable CoolProp provider follows every changing overall composition",
            "each interval updates component moles and total internal energy from explicit integrated ports",
            "phase-selective outlet species and energy use the left-end native phase packet",
            "every endpoint is re-flashed at fixed vessel volume before the next interval",
            "accepted run retains exact states and rechecks per-interval/cumulative ledgers",
            "nonpositive stocks, phase overdraw, changed provider basis, and stale receipts fail closed",
            "explicit endpoint method reports no continuous ODE, phase event, or wall model",
        ),
    ),)


def validate_interval_march(*, work_directory, **parameters):
    del work_directory, parameters
    from math import fsum

    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureProperties
    from h2physics.thermo.finite_mixture_inventory import (
        MixtureProviderTemplate,
        MixtureVesselInterval,
        run_finite_mixture_vu_intervals,
    )

    species = ("H2", "N2")
    molar_masses = (2.01588e-3, 28.0134e-3)
    composition = GasComposition("synthetic-initial-mixture", species, (.5, .5), molar_masses)
    provider = CoolPropMixtureProperties(composition,
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    initial_partition = provider.phase_partition_pq(5.0e6, .5,
        component_mole_balance_tolerance=1e-7)
    initial_amounts = initial_partition.split_moles(2.0)
    volume = fsum(initial_amounts.phase_volumes_m3)
    initial_u = initial_amounts.total_internal_energy_j
    added_h2_mol = 1e-5
    added_h2_energy = (added_h2_mol * molar_masses[0]
                       * initial_partition.vapor_enthalpy_j_kg)
    template = MixtureProviderTemplate(
        species, molar_masses, ("Hydrogen", "Nitrogen"),
        energy_reference_id="synthetic-coolprop-heos-common-reference",
    )
    interval = MixtureVesselInterval(
        end_time_s=1.0,
        liquid_inlet_component_moles=(0., 0.),
        vapor_inlet_component_moles=(added_h2_mol, 0.),
        liquid_inlet_enthalpy_j=0., vapor_inlet_enthalpy_j=added_h2_energy,
        evidence_id="synthetic-small-h2-feed-v1",
    )
    run = run_finite_mixture_vu_intervals(
        template, initial_amounts.component_moles,
        initial_internal_energy_j=initial_u,
        vessel_volume_m3=volume, intervals=(interval,),
        pressure_bounds_pa=(4.0e6, 6.0e6), quality_bounds=(.2, .8),
        initial_guesses=((4.9e6, .45), (5.1e6, .55)),
        volume_absolute_tolerance_m3=1e-9,
        energy_absolute_tolerance_j=1e-2,
        component_mole_absolute_tolerance=1e-7,
        phase_mole_balance_tolerance=1e-7,
        branch_evidence_id="synthetic-bounded-two-phase-neighborhood-v1",
        run_id="synthetic-small-feed-accepted-interval",
    )
    assert run.require_current() is run
    assert len(run.accepted) == 2
    assert run.accepted[0].provider is not run.accepted[1].provider
    assert run.accepted[0].provider.composition_sha256 != run.accepted[1].provider.composition_sha256
    assert run.accepted[1].admission.total_component_moles[0] > run.accepted[0].admission.total_component_moles[0]
    assert run.accepted[1].admission.total_component_moles[1] == run.accepted[0].admission.total_component_moles[1]
    assert abs(run.accepted[1].admission.vessel_volume_m3 - volume) <= 1e-12
    assert run.accepted[1].flash.partition.state.phase == "two_phase"
    return ValidationOutcome(True, {
        "accepted_intervals": len(run.intervals),
        "initial_pressure_pa": run.accepted[0].flash.pressure_pa,
        "final_pressure_pa": run.accepted[-1].flash.pressure_pa,
        "component_moles_added": added_h2_mol,
        "final_volume_m3": run.accepted[-1].admission.vessel_volume_m3,
        "final_internal_energy_j": run.accepted[-1].admission.target_internal_energy_j,
    }, LIMITS)
