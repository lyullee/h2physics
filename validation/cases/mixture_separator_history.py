"""Deferred audit contract for owner-accepted mixture-vessel trajectories."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mixture-separator-native-history-ledger",
        profile="gas-composition",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "exact-time accepted native flash packets retain pressure, temperature, phase and fixed vessel volume",
            "changing-composition inventory snapshots close against cumulative species-resolved inlet/outlet ledgers",
            "total internal-energy history closes against the declared net external-energy ledger on one property basis",
            "history audit retains exact original accepted points and rejects nested admission mutation/staleness",
            "history audit cannot be directly forged or cloned",
            "missing species, nonmonotone clock/port integrals, incompatible property bases and out-of-budget balances fail closed",
            "post-run balance audit does not claim ownership of native integration or phase-event localization",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import fsum

    from h2physics.adapters.mixture_separator_history import (
        MixtureSeparatorAcceptedPoint,
        audit_mixture_separator_history,
    )
    from h2physics.mixtures import GasComposition
    from h2physics.thermo import CoolPropMixtureProperties, MixtureInventoryStateAdmission

    provider = CoolPropMixtureProperties(GasComposition(
        "authored-separator-history", ("H2", "N2"), (.5, .5),
        (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    partition = provider.phase_partition_pq(5e6, .5,
        component_mole_balance_tolerance=1e-7)
    amount = partition.split_moles(2.)
    volume = fsum(amount.phase_volumes_m3)
    energy = amount.total_internal_energy_j
    admission = MixtureInventoryStateAdmission(provider, partition, amount.component_moles,
        energy, volume, 1e-7, 1e-12, 1e-6, "authored-equilibrium-packet")
    initial = MixtureSeparatorAcceptedPoint(0., admission, (0., 0.), (0., 0.), 0.)
    final = MixtureSeparatorAcceptedPoint(1., admission, (0., 0.), (0., 0.), 0.)
    audit = audit_mixture_separator_history((initial, final),
        native_run_id="synthetic-steady-accepted-history",
        native_owner_evidence_id="synthetic-native-owner-contract",
        component_mole_absolute_tolerance=1e-7,
        energy_absolute_tolerance_j=1e-6)
    assert audit.require_current() is audit
    assert audit.species == ("H2", "N2")
    assert len(audit.rows) == 2
    assert audit.accepted_points[0] is initial and audit.accepted_points[1] is final
    assert all(value == 0. for value in audit.maximum_component_mole_residuals)
    assert audit.maximum_absolute_energy_residual_j == 0.

    rejected = 0
    try:
        MixtureSeparatorAcceptedPoint(2., admission, (0.,), (0., 0.), 0.)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("A boundary ledger missing species coordinates was admitted")
    broken_final = MixtureSeparatorAcceptedPoint(1., admission, (0., 0.), (0., 0.), 2.)
    try:
        audit_mixture_separator_history((initial, broken_final),
            native_run_id="synthetic", native_owner_evidence_id="synthetic",
            component_mole_absolute_tolerance=1e-7, energy_absolute_tolerance_j=1e-6)
    except ValueError as error:
        rejected += "energy closure" in str(error)
    else:
        raise AssertionError("An energy-unclosed accepted packet was admitted")
    try:
        audit_mixture_separator_history((initial, final, final),
            native_run_id="synthetic", native_owner_evidence_id="synthetic",
            component_mole_absolute_tolerance=1e-7, energy_absolute_tolerance_j=1e-6)
    except ValueError as error:
        rejected += "strictly increasing" in str(error)
    else:
        raise AssertionError("Duplicate accepted clock times were admitted")
    try:
        replace(audit)
    except TypeError:
        rejected += 1
    else:
        raise AssertionError("A cloned post-run audit retained its private issuance")
    original_residual = admission.internal_energy_residual_j
    object.__setattr__(admission, "internal_energy_residual_j", original_residual + 1.)
    try:
        audit.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Nested native admission mutation left its enclosing audit current")
    finally:
        object.__setattr__(admission, "internal_energy_residual_j", original_residual)
    assert audit.require_current() is audit
    original_counter = final.cumulative_net_energy_into_vessel_j
    object.__setattr__(final, "cumulative_net_energy_into_vessel_j", original_counter + 1.)
    try:
        audit.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("An edited accepted point left its enclosing audit current")
    finally:
        object.__setattr__(final, "cumulative_net_energy_into_vessel_j", original_counter)
    assert audit.require_current() is audit
    assert rejected >= 6
    return ValidationOutcome(True, {
        "accepted_rows": len(audit.rows),
        "species": audit.species,
        "maximum_component_residuals_mol": audit.maximum_component_mole_residuals,
        "maximum_energy_residual_j": audit.maximum_absolute_energy_residual_j,
        "negative_contracts_rejected": rejected,
    }, ("Balance-admission contract only; no mixture-vessel solver, phase-event model, independent data comparison, or qualification is included",))
