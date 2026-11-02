"""Deferred native two-phase mixture component and mass-quality audit."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mixture-native-phase-mass-quality", profile="gas-composition",
        entrypoint=__name__+":validate_contract", parameters={},
        invariants=("native phase mole compositions reproduce overall species inventory",
                    "native component masses produce phase molar masses and true mass quality",
                    "native mole quality is preserved separately from derived mass quality",
                    "temperature-quality partition retains the same native phase identity as pressure-quality",
                    "phase-selective withdrawals use current native phase composition and conserve component stocks",
                    "withdrawal component masses and phase enthalpy exports use retained native phase properties",
                    "finite equilibrium packets derive occupied-phase volume and U from native h, rho and pressure",
                    "pure-liquid and pure-vapor native quality endpoints admit zero absent-phase inventory only",
                    "native phase packets and successful branch inverses reject direct construction/cloning",
                    "post-issuance phase property and inverse residual mutation invalidate receipts")),
        ValidationCase(
            identifier="mixture-native-inventory-state-admission", profile="gas-composition",
            entrypoint=__name__+":validate_inventory_admission", parameters={},
            invariants=("fixed-composition native packet must match volume, internal-energy and component-mole targets",
                        "exact provider identity, phase packet and accepted residual summaries remain sealed",
                        "inventory admission rejects missing source evidence or out-of-budget residuals")),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace
    from math import fsum, isclose, isfinite

    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties

    composition = GasComposition("authored-H2-N2-partition", ("H2", "N2"),
        (.5, .5), (2.01588e-3, 28.0134e-3))
    provider = CoolPropMixtureProperties(composition,
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    partition = provider.phase_partition_pq(5e6, .5, component_mole_balance_tolerance=1e-7)
    try:
        replace(partition)
    except ValueError:
        forged_partition_rejected = True
    else:
        raise AssertionError("A copied phase partition retained the native flash receipt")
    original_liquid_h = partition.liquid_enthalpy_j_kg
    object.__setattr__(partition, "liquid_enthalpy_j_kg", original_liquid_h + 1.)
    try:
        partition.require_current()
    except ValueError:
        mutated_partition_rejected = True
    else:
        raise AssertionError("Changed phase properties remained attached to the native partition")
    finally:
        object.__setattr__(partition, "liquid_enthalpy_j_kg", original_liquid_h)
    assert partition.require_current() is partition
    tq_partition = provider.phase_partition_tq(
        partition.state.temperature_k, partition.vapor_mole_fraction,
        component_mole_balance_tolerance=1e-7,
    )
    assert tq_partition.state.vapor_mole_fraction == partition.state.vapor_mole_fraction
    assert tq_partition.species == partition.species
    assert isclose(tq_partition.vapor_mass_fraction,
                   partition.vapor_mass_fraction, rel_tol=1e-8, abs_tol=1e-10)
    assert partition.state.vapor_mass_fraction is None
    assert partition.vapor_mole_fraction == .5
    total_mass_per_mol = fsum(z*m for z, m in zip(partition.overall_mole_fractions,
        partition.component_molar_masses_kg_mol, strict=True))
    vapor_mass_per_mol = .5*partition.vapor_molar_mass_kg_mol
    liquid_mass_per_mol = .5*partition.liquid_molar_mass_kg_mol
    assert isclose(vapor_mass_per_mol+liquid_mass_per_mol, total_mass_per_mol,
        rel_tol=1e-6, abs_tol=1e-10)
    assert isclose(partition.vapor_mass_fraction,
        vapor_mass_per_mol/(vapor_mass_per_mol+liquid_mass_per_mol), rel_tol=1e-12)
    assert 0. < partition.vapor_mass_fraction < 1.
    amount = partition.split_mass(.025)
    assert isclose(amount.total_mass_kg, .025, rel_tol=1e-12)
    assert all(volume > 0. for volume in amount.phase_volumes_m3)
    assert isfinite(amount.volume_residual_m3)
    assert isclose(sum(amount.phase_internal_energies_j),
                   amount.total_internal_energy_j, rel_tol=0., abs_tol=1e-10)
    assert isfinite(amount.internal_energy_residual_j)
    for observed, overall in zip(amount.component_moles, partition.overall_mole_fractions, strict=True):
        assert abs(observed-amount.total_moles*overall) <= amount.total_moles*1e-7
    moles = partition.split_moles(2.)
    assert isclose(fsum(moles.component_moles), 2., rel_tol=1e-12)
    inverse = provider.phase_partition_ph(5e6, partition.state.enthalpy_j_kg,
        quality_bounds=(.2, .8), component_mole_balance_tolerance=1e-7,
        enthalpy_absolute_tolerance_j_kg=1e-4, quality_absolute_tolerance=1e-10,
        branch_evidence_id="authored-single-native-PQ-branch", branch_samples=9)
    try:
        replace(inverse)
    except ValueError:
        forged_inverse_rejected = True
    else:
        raise AssertionError("A copied phase inverse retained its native solver receipt")
    original_inverse_residual = inverse.enthalpy_residual_j_kg
    object.__setattr__(inverse, "enthalpy_residual_j_kg", original_inverse_residual + 1.)
    try:
        inverse.require_current()
    except ValueError:
        mutated_inverse_rejected = True
    else:
        raise AssertionError("Changed enthalpy residual remained a current native inverse")
    finally:
        object.__setattr__(inverse, "enthalpy_residual_j_kg", original_inverse_residual)
    assert inverse.require_current() is inverse
    assert abs(inverse.partition.vapor_mole_fraction-.5) < 1e-7
    assert abs(inverse.enthalpy_residual_j_kg) <= 1e-4
    assert inverse.native_root.converged and inverse.monotonicity_is_sampled_only
    assert inverse.evaluations[-1] is inverse.partition
    withdrawn_liquid_mol = fsum(moles.liquid_component_moles)*.05
    withdrawn_vapor_mol = fsum(moles.vapor_component_moles)*.05
    withdrawal = partition.withdraw_component_moles(
        moles.liquid_component_moles, moles.vapor_component_moles,
        fsum(moles.liquid_component_moles), fsum(moles.vapor_component_moles),
        liquid_withdrawal_moles=withdrawn_liquid_mol,
        vapor_withdrawal_moles=withdrawn_vapor_mol)
    assert isclose(fsum(withdrawal.liquid_component_moles_out), withdrawn_liquid_mol,
        rel_tol=1e-12, abs_tol=1e-12)
    assert isclose(fsum(withdrawal.vapor_component_moles_out), withdrawn_vapor_mol,
        rel_tol=1e-12, abs_tol=1e-12)
    for before, out, left in zip(withdrawal.liquid_component_moles_before,
            withdrawal.liquid_component_moles_out, withdrawal.liquid_component_moles_after, strict=True):
        assert isclose(before, out+left, rel_tol=0., abs_tol=1e-12)
    for before, out, left in zip(withdrawal.vapor_component_moles_before,
            withdrawal.vapor_component_moles_out, withdrawal.vapor_component_moles_after, strict=True):
        assert isclose(before, out+left, rel_tol=0., abs_tol=1e-12)
    expected_phase_mass = (
        fsum(n*m for n, m in zip(withdrawal.liquid_component_moles_out,
            partition.component_molar_masses_kg_mol, strict=True)),
        fsum(n*m for n, m in zip(withdrawal.vapor_component_moles_out,
            partition.component_molar_masses_kg_mol, strict=True)),
    )
    assert all(isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)
               for a, b in zip(withdrawal.phase_mass_out_kg, expected_phase_mass, strict=True))
    expected_phase_energy = tuple(m*h for m, h in zip(
        expected_phase_mass, withdrawal.phase_enthalpies_j_kg, strict=True))
    assert all(isclose(a, b, rel_tol=1e-12, abs_tol=1e-10)
               for a, b in zip(withdrawal.phase_enthalpy_out_j,
                               expected_phase_energy, strict=True))
    assert isclose(withdrawal.total_enthalpy_out_j, fsum(expected_phase_energy),
                   rel_tol=1e-12, abs_tol=1e-10)
    mismatched_phase_stock_rejected = False
    wrong_liquid = list(moles.liquid_component_moles)
    wrong_liquid[0] *= .9
    wrong_liquid[1] += fsum(moles.liquid_component_moles)-fsum(wrong_liquid)
    try:
        partition.withdraw_component_moles(wrong_liquid, moles.vapor_component_moles,
            fsum(moles.liquid_component_moles), fsum(moles.vapor_component_moles),
            liquid_withdrawal_moles=withdrawn_liquid_mol)
    except ValueError as error:
        mismatched_phase_stock_rejected = "equilibrium compositions" in str(error)
    assert mismatched_phase_stock_rejected
    from h2physics.thermo.mixture_phase_partition import MixturePhaseWithdrawal

    forged_receipt_rejected = False
    forged_liquid = list(withdrawal.liquid_component_moles_before)
    forged_liquid[0] *= .9
    forged_liquid[1] += fsum(withdrawal.liquid_component_moles_before)-fsum(forged_liquid)
    forged_after = tuple(before-out for before, out in zip(
        forged_liquid, withdrawal.liquid_component_moles_out, strict=True))
    try:
        MixturePhaseWithdrawal(
            partition, tuple(forged_liquid), withdrawal.vapor_component_moles_before,
            withdrawal.liquid_component_moles_out, withdrawal.vapor_component_moles_out,
            forged_after, withdrawal.vapor_component_moles_after,
            withdrawal.phase_enthalpies_j_kg,
        )
    except ValueError as error:
        forged_receipt_rejected = "native phase composition" in str(error)
    assert forged_receipt_rejected

    endpoint_results = {}
    for quality, name in ((0., "liquid"), (1., "vapor")):
        endpoint = provider.phase_partition_pq(
            5e6, quality, component_mole_balance_tolerance=1e-7,
        )
        endpoint_amounts = endpoint.split_moles(2.)
        endpoint_volumes = endpoint_amounts.phase_volumes_m3
        endpoint_internal_energies = endpoint_amounts.phase_internal_energies_j
        assert endpoint_volumes[1 if quality == 0. else 0] == 0.
        assert endpoint_internal_energies[1 if quality == 0. else 0] == 0.
        endpoint_liquid = fsum(endpoint_amounts.liquid_component_moles)
        endpoint_vapor = fsum(endpoint_amounts.vapor_component_moles)
        withdrawal = endpoint.withdraw_component_moles(
            endpoint_amounts.liquid_component_moles,
            endpoint_amounts.vapor_component_moles,
            endpoint_liquid, endpoint_vapor,
            liquid_withdrawal_moles=endpoint_liquid*.05,
            vapor_withdrawal_moles=endpoint_vapor*.05,
        )
        absent = (withdrawal.vapor_component_moles_before if quality == 0.
                  else withdrawal.liquid_component_moles_before)
        assert all(value == 0. for value in absent)
        endpoint_results[name] = True
    return ValidationOutcome(True, {"vapor_mole_fraction": partition.vapor_mole_fraction,
        "vapor_mass_fraction": partition.vapor_mass_fraction,
        "forged_partition_rejected": forged_partition_rejected,
        "mutated_partition_rejected": mutated_partition_rejected,
        "forged_inverse_rejected": forged_inverse_rejected,
        "mutated_inverse_rejected": mutated_inverse_rejected,
        "mismatched_phase_stock_rejected": mismatched_phase_stock_rejected,
        "forged_phase_withdrawal_receipt_rejected": forged_receipt_rejected,
        "quality_endpoint_withdrawals": endpoint_results},
        ("Native binary VLE reference only; no independent phase-equilibrium experiment",))


def validate_inventory_admission(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import fsum

    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureProperties, MixtureInventoryStateAdmission

    provider = CoolPropMixtureProperties(GasComposition(
        "authored-inventory-admission", ("H2", "N2"), (.5, .5),
        (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    packet = provider.phase_partition_pq(
        5e6, .5, component_mole_balance_tolerance=1e-7)
    amounts = packet.split_moles(2.)
    target_moles = amounts.component_moles
    target_volume = fsum(amounts.phase_volumes_m3)
    target_energy = amounts.total_internal_energy_j
    admission = MixtureInventoryStateAdmission(
        provider, packet, target_moles, target_energy, target_volume,
        1e-7, 1e-12, 1e-6, "authored-inventory-target-provenance")
    assert admission.require_current() is admission
    assert all(abs(value) <= 1e-7 for value in admission.component_mole_residuals)
    assert abs(admission.volume_residual_m3) <= 1e-12
    assert abs(admission.internal_energy_residual_j) <= 1e-6
    rejected = 0
    try:
        replace(admission, vessel_volume_m3=target_volume+1e-6)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Native packet outside the fixed-volume tolerance was admitted")
    try:
        replace(admission, evidence_id=" ")
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Inventory admission without evidence was accepted")
    other_provider = CoolPropMixtureProperties(GasComposition(
        "authored-inventory-admission", ("H2", "N2"), (.5, .5),
        (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    try:
        replace(admission, provider=other_provider)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A phase packet from a different provider object was admitted")
    original_energy = admission.internal_energy_residual_j
    object.__setattr__(admission, "internal_energy_residual_j", original_energy+1.)
    try:
        admission.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Forged inventory residual remained current")
    object.__setattr__(admission, "internal_energy_residual_j", original_energy)
    assert admission.require_current() is admission
    return ValidationOutcome(True, {
        "component_residuals_mol": admission.component_mole_residuals,
        "volume_residual_m3": admission.volume_residual_m3,
        "internal_energy_residual_j": admission.internal_energy_residual_j,
        "rejected_invalid_admissions": rejected,
    }, ("Admission contract only; the local code did not solve an inventory flash or integrate a separator.",))
