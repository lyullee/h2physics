"""Deferred bounded fixed-volume/internal-energy VLE inventory-flash contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mixture-two-phase-inventory-vu-flash",
        profile="gas-composition",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "native CoolProp PQ packets solve a bounded two-phase fixed-volume/internal-energy state",
            "retained phase amounts independently close each species, total volume and total internal energy",
            "all caller branch seeds converge within domain and cluster to one pressure/quality root",
            "distinct seed roots and seed failures reject instead of selecting one silently",
            "fixed-composition provider mismatch and single-phase/non-VLE packets are rejected",
            "single-state flash does not claim an accepted vessel history, port integration or phase event localization",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace
    from math import fsum, isclose

    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
    from h2physics.thermo.mixture_inventory_flash import (
        MixtureInventoryFlashError,
        flash_two_phase_inventory_vu,
    )

    del work_directory, parameters
    provider = CoolPropMixtureProperties(
        GasComposition(
            "authored-fixed-vu-inventory",
            ("H2", "N2"),
            (.5, .5),
            (2.01588e-3, 28.0134e-3),
        ),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
    )
    total_moles = 2.0
    reference_partition = provider.phase_partition_pq(
        5.0e6, .5, component_mole_balance_tolerance=1.0e-7,
    )
    reference_amounts = reference_partition.split_moles(total_moles)
    target_moles = reference_amounts.component_moles
    target_volume = fsum(reference_amounts.phase_volumes_m3)
    target_energy = reference_amounts.total_internal_energy_j
    result = flash_two_phase_inventory_vu(
        provider,
        target_moles,
        vessel_volume_m3=target_volume,
        internal_energy_j=target_energy,
        pressure_bounds_pa=(4.0e6, 6.0e6),
        quality_bounds=(.2, .8),
        initial_guesses=((4.9e6, .45), (5.1e6, .55)),
        volume_absolute_tolerance_m3=1.0e-9,
        energy_absolute_tolerance_j=1.0e-2,
        component_mole_absolute_tolerance=1.0e-7,
        phase_mole_balance_tolerance=1.0e-7,
        branch_evidence_id="authored-bounded-native-two-phase-region",
    )
    assert result.admission.provider is provider
    assert result.seed_unique_within_search is True
    assert len(result.seed_results) == 2
    assert all(item.converged for item in result.seed_results)
    assert isclose(result.pressure_pa, 5.0e6, rel_tol=1.0e-5)
    assert abs(result.partition.vapor_mole_fraction - .5) <= 1.0e-5
    assert abs(result.volume_residual_m3) <= 1.0e-9
    assert abs(result.internal_energy_residual_j) <= 1.0e-2
    assert all(abs(value) <= 1.0e-7
               for value in result.admission.component_mole_residuals)
    assert result.require_current() is result

    rejected = 0
    try:
        replace(result)
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A copied flash result retained its one-use solver issuance")
    wrong_composition = (target_moles[0] + 1.0e-3, target_moles[1] - 1.0e-3)
    try:
        flash_two_phase_inventory_vu(
            provider,
            wrong_composition,
            vessel_volume_m3=target_volume,
            internal_energy_j=target_energy,
            pressure_bounds_pa=(4.0e6, 6.0e6),
            quality_bounds=(.2, .8),
            initial_guesses=((4.9e6, .45), (5.1e6, .55)),
            volume_absolute_tolerance_m3=1.0e-9,
            energy_absolute_tolerance_j=1.0e-2,
            component_mole_absolute_tolerance=1.0e-7,
            phase_mole_balance_tolerance=1.0e-7,
            branch_evidence_id="authored-bounded-native-two-phase-region",
        )
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A fixed-composition provider entered a different component inventory")
    try:
        flash_two_phase_inventory_vu(
            provider,
            target_moles,
            vessel_volume_m3=target_volume,
            internal_energy_j=target_energy,
            pressure_bounds_pa=(4.0e6, 6.0e6),
            quality_bounds=(.2, .8),
            initial_guesses=((4.9e6, .45),),
            volume_absolute_tolerance_m3=1.0e-9,
            energy_absolute_tolerance_j=1.0e-2,
            component_mole_absolute_tolerance=1.0e-7,
            phase_mole_balance_tolerance=1.0e-7,
            branch_evidence_id="authored-bounded-native-two-phase-region",
        )
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("One seed was incorrectly reported as a branch search")
    assert rejected == 3
    return ValidationOutcome(True, {
        "pressure_pa": result.pressure_pa,
        "temperature_k": result.temperature_k,
        "vapor_mole_fraction": result.partition.vapor_mole_fraction,
        "volume_residual_m3": result.volume_residual_m3,
        "internal_energy_residual_j": result.internal_energy_residual_j,
        "native_evaluations": result.total_native_evaluations,
        "successful_branch_seeds": len(result.seed_results),
        "rejected_contracts": rejected,
    }, (
        "Authored VLE packet round trip only; this single-state resolver does not integrate a finite separator or validate mixture parameters.",
    ))
