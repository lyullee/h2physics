"""Deferred staggered existing-owner temperature projection contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-staggered-temperature-feedback", profile="fuel-cell",
        entrypoint=__name__+":validate_staged", parameters={}, invariants=(
            "each explicit interval retains original thermal and finite material solver outputs",
            "material stock and thermal boundary temperature continue separately",
            "declared projected temperature and heat mismatch are retained without correction",
            "out-of-range projection rejects with original completed prefix and thermal output",
            "staged operation receipt cannot be directly fabricated or cloned",
            "the staged owner integration is re-exported by the public adapters facade",
        ),
    ),)


def validate_staged(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from h2physics import adapters
    from h2physics.adapters.electrochemical_staged_operation import (
        StagedElectrochemicalError,
        StagedElectrochemicalStep,
        StagedElectrochemicalTrace,
        run_staged_electrochemical_operation,
    )
    assert adapters.StagedElectrochemicalError is StagedElectrochemicalError
    assert adapters.StagedElectrochemicalStep is StagedElectrochemicalStep
    assert adapters.StagedElectrochemicalTrace is StagedElectrochemicalTrace
    assert adapters.run_staged_electrochemical_operation is run_staged_electrochemical_operation
    from h2physics.electrochemical_thermal import (
        FiniteThermalStack,
        ThermalStackBoundary,
        ThermalStackStage,
    )

    model, initial, commands = synthetic_problem()
    step = commands[0]
    generated = model.stack.evaluate(step.current_density_a_m2, step.temperature_k,
                                     mode="fuel_cell").unallocated_energy_rate_w
    owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., lambda t, tc: 0., (280., 430.), initial.energy_basis_id,
        model.boundary.thermal_boundary_id,
    ))
    first = ThermalStackStage("first", 0., 5., step.current_density_a_m2,
                              initial.temperature_k, "fuel_cell", auxiliary_heat_into_w=-generated)
    schedule = (first, replace(first, identifier="second", start_s=5., end_s=10.))
    options = dict(projection_evidence_id="authored-accepted-final-temperature",
                   refinement_identity="authored-two-stage-schedule", clock_id=model.evidence.clock_id,
                   heat_mismatch_budget_j=1e-5,
                   thermal_capacity_scope_evidence_id="authored-separate-stack-solid-capacity")
    result = run_staged_electrochemical_operation(
        model, owner, initial, schedule,
        temperature_projection=lambda thermal, command: thermal.final_temperature_k, **options,
    )
    assert result.require_current() is result
    try:
        StagedElectrochemicalTrace(
            owner, model, initial, result.steps, result.temperature_projection,
            result.projection_evidence_id, result.refinement_identity, result.clock_id,
            result.heat_mismatch_budget_j, result.thermal_capacity_scope_evidence_id,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("A caller-constructed staged receipt claimed native execution")
    try:
        replace(result)
    except ValueError:
        pass
    else:
        raise AssertionError("A cloned staged receipt retained native issuance")
    assert result.steps[1].material_result.initial is result.steps[0].material_result.final
    assert result.steps[1].thermal_result.initial_temperature_k == result.steps[0].thermal_result.final_temperature_k
    assert all(abs(stage.generated_vs_material_heat_residual_j
                   -stage.material_conditioning_heat_j
                   -stage.thermal_projection_heat_difference_j) < 1e-8
               for stage in result.steps)

    def invalid_second(thermal, command):
        return thermal.final_temperature_k+(1. if command.identifier == "second" else 0.)

    try:
        run_staged_electrochemical_operation(
            model, owner, initial, schedule, temperature_projection=invalid_second, **options,
        )
    except StagedElectrochemicalError as error:
        assert len(error.completed) == 1
        assert error.thermal_result is not None and error.material_result is None
        assert isinstance(error.cause, ValueError)
    else:
        raise AssertionError("Out-of-range staggered temperature projection was admitted")
    def mutating_projection(thermal, command):
        thermal.stages[0].native_result.y[0, -1] += .01
        return thermal.final_temperature_k

    try:
        run_staged_electrochemical_operation(
            model, owner, initial, schedule, temperature_projection=mutating_projection, **options,
        )
    except StagedElectrochemicalError as error:
        assert not error.completed and error.thermal_result is not None
        assert "mutated" in str(error.cause)
    else:
        raise AssertionError("Projection callback changed the original native thermal result")
    try:
        run_staged_electrochemical_operation(
            model, owner, replace(initial, pressure_pa=initial.pressure_pa+1.), schedule,
            temperature_projection=lambda thermal, command: thermal.final_temperature_k, **options,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Foreign initial stock pressure entered staggered operation")
    return ValidationOutcome(True, {"completed_intervals": len(result.steps)}, (
        "Authored isothermal limiting trajectory; no dynamic experiment qualification",
        "Staggered held-temperature projection is not simultaneous coupled energy closure",
    ))
