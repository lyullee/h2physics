"""Deferred finite coolant enthalpy feedback contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-finite-coolant-enthalpy-feedback", profile="fuel-cell",
        entrypoint=__name__+":validate_coolant", parameters={}, invariants=(
            "original stack RHS advances finite coolant enthalpy with equal opposite heat",
            "CoolProp liquid state remains within explicit pressure and temperature domain",
            "stack plus coolant energy closes against actual generated and auxiliary heat",
            "same-owner thermal callback configuration changes are rejected on both RHS routes",
            "invalid boolean temperature bounds and noncallable conductance are refused",
        ),
    ),)


def validate_coolant(*, work_directory, **parameters):
    from examples.fuel_cell import synthetic_problem
    from h2physics.electrochemical_thermal import (
        FiniteCoolantReservoir,
        FiniteThermalStack,
        ThermalStackBoundary,
        ThermalStackStage,
    )
    from h2physics.thermo import CoolPropProperties

    model, initial, commands = synthetic_problem()
    for bounds, conductance in (((True, 350.), lambda ts, tc: 1.),
                                ((280., 350.), 1.)):
        try:
            ThermalStackBoundary(1000., conductance, bounds, initial.energy_basis_id,
                                 model.boundary.thermal_boundary_id)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("Invalid thermal boundary scalar/callback was admitted")
    properties = CoolPropProperties("Water")
    coolant = properties.state_pt(101325., 300.)
    reservoir = FiniteCoolantReservoir(
        1., 101325., properties, (280., 350.),
        lambda **kwargs: 0., model.boundary.thermal_boundary_id,
        model.evidence.clock_id, "authored-single-liquid-water-reservoir",
    )
    owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., lambda ts, tc: 5., (280., 430.), initial.energy_basis_id,
        model.boundary.thermal_boundary_id,
    ))
    stage = ThermalStackStage("finite-coolant", 0., 1., 200., 300., "fuel_cell")
    def changed_conductance(ts, tc):
        object.__setattr__(changed_owner.boundary, "heat_capacity_j_k", 2000.)
        return 5.
    changed_owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., changed_conductance, (280., 430.), initial.energy_basis_id,
        model.boundary.thermal_boundary_id))
    try:
        changed_owner.run(320., (stage,))
    except ValueError:
        pass
    else:
        raise AssertionError("Prescribed-coolant thermal RHS admitted changed owner configuration")
    result = owner.run_with_coolant(320., coolant, (stage,), reservoir=reservoir)
    assert result.final_coolant_state.temperature_k > coolant.temperature_k
    assert abs(result.combined_energy_residual_j) <= 2*owner.energy_tolerance_j
    retained = result.stages[0]
    assert retained.native_result.y.shape[0] == 5
    assert retained.coolant_heat_out_j > 0.
    result.require_current()
    combined_residual = result.combined_energy_residual_j
    retained.native_result.y[3, -1] += 1.
    try:
        result.require_current()
    except ValueError:
        pass
    else:
        raise AssertionError("Changed finite coolant enthalpy trajectory retained admission")
    return ValidationOutcome(True, {"combined_energy_residual_j": combined_residual},
                             ("Authored liquid reservoir and stack properties; no hardware validation",
                              "Constant pressure/fixed mass; no flow, boiling or coolant depletion"))
