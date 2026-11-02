"""Deferred actual closed-reactant schedule preparation and execution contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-closed-schedule-stock-and-owner", profile="fuel-cell",
        entrypoint=__name__+":validate_schedule", parameters={}, invariants=(
            "finite H2 and O2 stock limits follow shared series-cell Faraday convention",
            "original material and thermal owners execute paired held commands",
            "foreign clock rejected before execution; original commands require unity Faradaic efficiency",
            "approximation budget mutation invalidates prepared schedule",
        ),
    ),)


def validate_schedule(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.electrochemical_schedule import (
        compare_electrochemical_schedules,
        prepare_closed_fuel_cell_schedule,
    )
    from h2physics.electrochemical_thermal import (
        FiniteThermalStack,
        ThermalStackBoundary,
        ThermalStackStage,
    )

    model, initial, steps = synthetic_problem()
    step = steps[0]
    generated = model.stack.evaluate(step.current_density_a_m2, step.temperature_k,
                                     mode="fuel_cell").unallocated_energy_rate_w
    thermal_owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., lambda t, tc: 0., (280., 430.), initial.energy_basis_id,
        model.boundary.thermal_boundary_id,
    ))
    thermal = (ThermalStackStage(
        step.identifier, step.start_s, step.end_s, step.current_density_a_m2,
        step.temperature_k, "fuel_cell", auxiliary_heat_into_w=-generated,
    ),)
    options = dict(material_steps=steps, thermal_stages=thermal,
                   refinement_identity="authored-grid-one-held-window",
                   approximation_evidence_id="authored-isothermal-compatibility",
                   temperature_tolerance_k=1e-6, energy_tolerance_j=1e-5)
    schedule = prepare_closed_fuel_cell_schedule(model, thermal_owner, initial, **options)
    assert schedule.require_current() is schedule
    receipt = schedule.run()
    assert receipt.require_current() is receipt
    fine_steps = (replace(step, identifier="first-half", end_s=5.),
                  replace(step, identifier="second-half", start_s=5.))
    fine_thermal = (replace(thermal[0], identifier="first-half", end_s=5.),
                    replace(thermal[0], identifier="second-half", start_s=5.))
    fine = prepare_closed_fuel_cell_schedule(
        model, thermal_owner, initial,
        **{**options, "material_steps": fine_steps, "thermal_stages": fine_thermal},
    ).run()
    comparison = compare_electrochemical_schedules(
        receipt, fine, refinement_identity=options["refinement_identity"],
        normalizations=dict(hydrogen_consumed_mol=.01, electricity_into_j=100.,
                            required_heat_into_j=100., coolant_heat_out_j=100.,
                            maximum_sampled_temperature_k=1.), threshold=1e-6,
    )
    assert comparison.require_current() is comparison
    assert comparison.within_threshold
    rejected = 0
    for changed_initial, changed_options in (
        (replace(initial, amounts_mol={"H2": 1e-12, "O2": .007, "H2O": .001}), options),
        (initial, {**options, "material_steps": (replace(step, clock_id="foreign-clock"),)}),
    ):
        try:
            prepare_closed_fuel_cell_schedule(model, thermal_owner, changed_initial, **changed_options)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Unusable finite closed-stock schedule admitted")
    object.__setattr__(schedule, "energy_tolerance_j", 1.)
    try:
        schedule.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed held-approximation budget retained admission")
    assert rejected == 3
    return ValidationOutcome(True, {"schedule_rejections": rejected}, (
        "Authored closed-stock schedule only; no dynamic thermal feedback",
        "No experimental stack or coolant qualification",
    ))
