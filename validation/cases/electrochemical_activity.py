"""Deferred reaction-energy/activity-to-stack composition contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="fuel-cell-activity-corrected-stack-operating-point",
        profile="electrochemical-thermal",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "ReactionEnergy voltage properties use its Gibbs and enthalpy fields",
            "fuel-cell operating activities are applied by the shared reaction-energy correction",
            "water activity phase must match the reaction-energy product phase",
            "the corrected reaction energy is consumed by the existing HydrogenStack",
            "a finite fuel-cell schedule can bind one explicit operating state per step",
            "finite-step energy closure retains reaction enthalpy while applying corrected reversible voltage",
            "temperature-only compatibility API remains unchanged and evidence references are retained",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from math import isclose, log

    from h2physics.constants import FARADAY_C_MOL, R_J_MOL_K
    from h2physics.electrochemistry import (
        FuelCellOperatingState,
        HydrogenStack,
        ReactionEnergy,
        StackGeometry,
        fuel_cell_activity_correction,
    )

    standard = ReactionEnergy(228_000., 286_000., "authored-common-reference", "liquid")
    state = FuelCellOperatingState(
        333.15, 2.1e5, 1.9e5, .82, .74, .93, "liquid",
        "anode-H2-reference", "cathode-O2-reference", "product-water-reference",
        "authored-operating-point-evidence",
    )
    corrected = fuel_cell_activity_correction(standard, state)
    from dataclasses import replace
    try:
        fuel_cell_activity_correction(standard, replace(state, water_phase="vapor"))
    except ValueError as error:
        assert "phase" in str(error)
    else:
        raise AssertionError("Water activity from a different product phase was admitted")
    independent_delta_g = R_J_MOL_K*state.temperature_k*log(
        state.hydrogen_activity*state.oxygen_activity**.5/state.water_activity
    )
    expected_voltage = (standard.gibbs_j_mol_h2+independent_delta_g)/(2*FARADAY_C_MOL)
    if not isclose(corrected.reversible_voltage_v, expected_voltage, rel_tol=1e-13):
        raise AssertionError("Activity correction differs from the independently written Nernst factor")
    if corrected.thermoneutral_voltage_v != standard.thermoneutral_voltage_v:
        raise AssertionError("Ideal activity correction must retain the supplied enthalpy")
    stack = HydrogenStack(
        StackGeometry(8, .012, .002), lambda temperature: corrected, {},
    )
    result = stack.evaluate(250., state.temperature_k, mode="fuel_cell")
    if result.reaction_energy is not corrected:
        raise AssertionError("Shared stack did not retain the corrected reaction-energy object")
    if not isclose(result.cell_voltage_v, corrected.reversible_voltage_v, rel_tol=1e-13):
        raise AssertionError("Stack operating voltage does not use the corrected reversible potential")

    from examples.fuel_cell import synthetic_problem

    model, inventory, commands = synthetic_problem(operating_state=state)
    trace = model.run(inventory, commands)
    finite_result = trace.steps[0].stack_result
    if trace.steps[0].operating_state is not state:
        raise AssertionError("Finite result did not retain its original operating-state object")
    if finite_result.reaction_energy.reference_id != corrected.reference_id:
        raise AssertionError("Finite schedule did not apply the activity-corrected energy reference")
    if not isclose(finite_result.cell_voltage_v, corrected.reversible_voltage_v,
                   rel_tol=1e-13):
        raise AssertionError("Finite schedule did not apply the activity-corrected voltage")
    if finite_result.reaction_energy.enthalpy_j_mol_h2 != standard.enthalpy_j_mol_h2:
        raise AssertionError("Activity correction must retain the common enthalpy basis")
    trace.require_current()
    return ValidationOutcome(True, {
        "standard_reversible_voltage_v": standard.reversible_voltage_v,
        "corrected_reversible_voltage_v": corrected.reversible_voltage_v,
        "thermoneutral_voltage_v": corrected.thermoneutral_voltage_v,
        "activity_reference_count": len(corrected.reference_id.split(":")),
        "finite_step_energy_residual_j": trace.steps[0].energy_residual_j,
    }, ("Synthetic API contract only; no activity/pressure law or cell validation.",))
