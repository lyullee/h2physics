"""Deferred contract for one exact synchronized fuel-cell RHS exchange."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="fuel-cell-synchronized-trial-exchange-ledger",
        profile="fuel-cell-native",
        entrypoint=__name__ + ":validate_trial_exchange",
        invariants=(
            "H2, O2 and water-vapor channel states share exact time and clock",
            "ideal trial activities use absolute partial pressure and explicit reference pressure",
            "existing activity correction and HydrogenStack own voltage and Faraday extent",
            "separate channel species mass rates close for H2 plus half O2 to H2O",
            "caller mapping edits after admission do not alter the copied proxy, while replacing the retained proxy invalidates it",
            "unallocated stack power remains unresolved and no channel heat is fabricated",
            "forged, cloned, stale or callback-mutated receipts are rejected",
            "exchange does not claim simultaneous integration or depletion-event ownership",
        ),
    ),)


def validate_trial_exchange(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    from math import isclose

    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry
    from h2physics.adapters.fuel_cell_trial import (
        FuelCellSynchronizedTrial,
        FuelCellTrialExchange,
        FuelCellTrialGasState,
        evaluate_fuel_cell_trial_exchange,
    )

    clock = "authored-common-trial-clock"
    time = 12.5
    channels = {
        "hydrogen": FuelCellTrialGasState(
            "hydrogen", "H2", time, clock, 210000.0, 330.0, 0.02,
            1.0, 1.0, 0.002016, 100000.0, "H2-reference",
            "authored-native-H2-state"),
        "oxygen": FuelCellTrialGasState(
            "oxygen", "O2", time, clock, 190000.0, 325.0, 0.02,
            1.0, 0.5, 0.031998, 100000.0, "O2-reference",
            "authored-native-O2-state"),
        "water_vapor": FuelCellTrialGasState(
            "water_vapor", "H2O", time, clock, 120000.0, 320.0, 0.02,
            1.0, 0.25, 0.018015, 100000.0, "H2O-reference",
            "authored-native-water-state"),
    }
    trial = FuelCellSynchronizedTrial(
        time, clock, 333.15, 250.0, channels, "authored-synchronized-source-state")
    original_hydrogen = channels["hydrogen"]
    channels["hydrogen"] = replace(original_hydrogen, pressure_pa=220000.0)
    assert trial.require_current() is trial
    channels["hydrogen"] = original_hydrogen
    from types import MappingProxyType

    retained_proxy = trial.channels
    object.__setattr__(trial, "channels", MappingProxyType(dict(retained_proxy)))
    try:
        trial.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Replacing the retained channel proxy identity remained current")
    finally:
        object.__setattr__(trial, "channels", retained_proxy)
    assert trial.require_current() is trial
    standard = ReactionEnergy(228000.0, 286000.0, "authored-common-energy-reference", "vapor")
    stack = HydrogenStack(StackGeometry(12, 0.02, 0.002016), lambda _temperature: standard, {})

    exchange = evaluate_fuel_cell_trial_exchange(
        stack, standard, trial, evidence_id="authored-callback-integration-boundary")
    assert exchange.require_current() is exchange
    assert exchange.operating_state.hydrogen_activity == 2.1
    assert exchange.operating_state.oxygen_activity == 1.9
    assert exchange.operating_state.water_activity == 1.2
    assert exchange.species_molar_rate_into_cv_mol_s["hydrogen"] < 0.0
    assert exchange.species_molar_rate_into_cv_mol_s["oxygen"] < 0.0
    assert exchange.species_molar_rate_into_cv_mol_s["water_vapor"] > 0.0
    assert abs(exchange.net_mass_rate_residual_kg_s) < 1e-12
    assert exchange.unresolved_energy_rate_w == exchange.stack_result.unallocated_energy_rate_w
    assert exchange.stack_result.electric_input_w < 0.0

    try:
        replace(exchange)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned trial exchange reused its consumed issuer")
    try:
        FuelCellTrialExchange(
            stack, trial, standard, exchange.operating_state,
            exchange.corrected_reaction_energy, exchange.stack_result,
            exchange.species_molar_rate_into_cv_mol_s,
            exchange.species_mass_rate_into_cv_kg_s,
            exchange.net_mass_rate_residual_kg_s, exchange.unresolved_energy_rate_w,
            evidence_id="forged")
    except ValueError:
        pass
    else:
        raise AssertionError("Direct trial-exchange fabrication was accepted")

    try:
        FuelCellSynchronizedTrial(
            time, clock, 333.15, 250.0,
            channels | {"oxygen": replace(channels["oxygen"], time_s=time + 0.01)},
            "misaligned-trial")
    except ValueError:
        pass
    else:
        raise AssertionError("A mismatched native trial clock was accepted")

    assert isclose(
        exchange.species_mass_rate_into_cv_kg_s["hydrogen"]
        + exchange.species_mass_rate_into_cv_kg_s["oxygen"],
        -exchange.species_mass_rate_into_cv_kg_s["water_vapor"],
        rel_tol=1e-9, abs_tol=1e-12,
    )
    return ValidationOutcome(True, {
        "time_s": exchange.trial.time_s,
        "current_density_a_m2": trial.current_density_a_m2,
        "mass_rate_residual_kg_s": exchange.net_mass_rate_residual_kg_s,
        "unresolved_energy_rate_w": exchange.unresolved_energy_rate_w,
        "clock_id": trial.clock_id,
    }, ("Synthetic callback-exchange contract only; no native simultaneous solver or cell qualification.",))
