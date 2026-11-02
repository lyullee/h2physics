"""Deferred thermal/material operation admission contracts; no import-time runs."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="electrochemical-thermal-material-admission", profile="fuel-cell",
        entrypoint=__name__+":validate_operation", parameters={}, invariants=(
            "original finite fuel-cell result and shared thermal stack identity",
            "same stage clock, energy reference and thermal boundary",
            "complete native trajectory remains inside explicit isothermal budget",
            "generated heat equals negative finite material heat duty",
            "changed thermal native arrays invalidate retained receipt",
        ),
    ), ValidationCase(
        identifier="pv-electrolysis-finite-thermal-admission", profile="pv-electrolysis",
        entrypoint=__name__+":validate_pv_electrolysis_thermal_operation", parameters={}, invariants=(
            "original PV producer and finite thermal traces retain one exact HydrogenStack",
            "all thermal stages match the original electrolysis clock, intervals, current and caloric basis",
            "temperature and generated-heat differences stay inside explicit admission budgets",
            "changed thermal trajectory invalidates the handoff receipt",
            "receipt copying and post-binding identity, evidence, tolerance and ledger edits are rejected",
            "post-run compatibility does not claim live temperature feedback",
        ),
    ),)


def validate_operation(*, work_directory, **parameters):
    from dataclasses import replace

    from examples.fuel_cell import synthetic_problem
    from h2physics.adapters.electrochemical_operation import bind_electrochemical_operation
    from h2physics.electrochemical_thermal import (
        FiniteThermalStack,
        ThermalStackBoundary,
        ThermalStackStage,
    )

    model, initial, commands = synthetic_problem()
    material = model.run(initial, commands)
    command = commands[0]
    heat = model.stack.evaluate(command.current_density_a_m2, command.temperature_k,
                                mode="fuel_cell").unallocated_energy_rate_w
    owner = FiniteThermalStack(model.stack, ThermalStackBoundary(
        1000., lambda stack_t, coolant_t: 0., (280., 430.),
        initial.energy_basis_id, model.boundary.thermal_boundary_id,
    ))
    stage = ThermalStackStage(
        command.identifier, command.start_s, command.end_s,
        command.current_density_a_m2, command.temperature_k, "fuel_cell",
        auxiliary_heat_into_w=-heat,
    )
    thermal = owner.run(command.temperature_k, (stage,))
    arguments = dict(clock_id=model.evidence.clock_id,
                     evidence_id="authored-held-isothermal-compatibility",
                     temperature_tolerance_k=1e-6, energy_tolerance_j=1e-5)
    receipt = bind_electrochemical_operation(owner, thermal, material, **arguments)
    assert receipt.require_current() is receipt
    rejected = 0
    for changed_arguments, changed_thermal in (
        ({**arguments, "clock_id": "foreign-clock"}, thermal),
        (arguments, replace(thermal, stages=(replace(
            thermal.stages[0], command=replace(stage, current_density_a_m2=201.),
        ),))),
    ):
        try:
            bind_electrochemical_operation(owner, changed_thermal, material, **changed_arguments)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Incompatible held operation was admitted")
    native = thermal.stages[0].native_result
    native.y[0, -1] += .1
    try:
        receipt.require_current()
    except ValueError:
        rejected += 1
    else:
        raise AssertionError("Changed thermal trajectory retained admission")
    assert rejected == 3
    return ValidationOutcome(True, {
        "generated_heat_residual_j": receipt.generated_heat_residual_j,
        "admission_rejections": rejected,
    }, ("Authored isothermal post-run compatibility only; no thermal/material feedback",
        "No device, coolant or reactant-depletion experiment qualification"))


def validate_pv_electrolysis_thermal_operation(*, work_directory, native_packages, **parameters):
    del work_directory, parameters
    from dataclasses import replace

    from examples.pv_electrolysis import build_model, source_stages
    from h2physics.adapters.electrolysis_thermal_handoff import bind_electrolysis_thermal_operation
    from h2physics.electrochemical_thermal import (
        FiniteThermalStack, ThermalStackBoundary, ThermalStackStage,
    )

    producer = build_model(native_packages=native_packages)
    pv_trace = producer.run(
        source_stages(), initial_amounts_mol={"water": 2., "hydrogen": .2, "oxygen": .1},
        receiver_volume_m3=.01, receiver_temperature_k=298.15,
    )
    stages = tuple(ThermalStackStage(
        step.point.stage.identifier, step.point.stage.start_s, step.point.stage.end_s,
        step.point.stack.current_a/producer.stack.geometry.active_area_m2,
        step.point.stage.stack_temperature_k, "electrolysis", 1.,
        -step.point.stack.unallocated_energy_rate_w,
    ) for step in pv_trace.steps)
    owner = FiniteThermalStack(producer.stack, ThermalStackBoundary(
        1e6, lambda _stack_t, _coolant_t: 0., (250., 450.),
        producer.caloric.basis_id, "authored-electrolysis-coolant-boundary",
    ))
    thermal = owner.run(stages[0].coolant_temperature_k, stages)
    fabricated_thermal_rejections = 0
    thermal_values = (
        thermal.initial_temperature_k, thermal.final_temperature_k, thermal.stages,
        thermal.generated_heat_j, thermal.coolant_heat_out_j,
        thermal.auxiliary_heat_into_j, thermal.internal_energy_change_j,
        thermal.energy_residual_j, thermal.status,
    )
    for candidate in (lambda: type(thermal)(*thermal_values), lambda: replace(thermal)):
        try:
            candidate()
        except TypeError:
            fabricated_thermal_rejections += 1
        else:
            raise AssertionError("Thermal trace was directly forged or cloned")
    assert fabricated_thermal_rejections == 2
    arguments = dict(
        clock_id=pv_trace.evidence.clock_id,
        evidence_id="authored-electrolysis-thermal-compatibility",
        temperature_tolerance_k=1e-6, energy_tolerance_j=1e-4,
    )
    receipt = bind_electrolysis_thermal_operation(owner, thermal, pv_trace, **arguments)
    assert receipt.require_current() is receipt
    try:
        replace(receipt)
    except TypeError:
        pass
    else:
        raise AssertionError("Electrolysis thermal receipt was cloned with a new integrity baseline")
    receipt_fields = (
        ("evidence_id", "relabeled-evidence"),
        ("temperature_tolerance_k", 10.),
        ("energy_tolerance_j", 10.),
        ("generated_heat_residual_j", 10.),
        ("electrolysis_trace", None),
    )
    for field_name, changed_value in receipt_fields:
        original_value = getattr(receipt, field_name)
        object.__setattr__(receipt, field_name, changed_value)
        try:
            receipt.require_current()
        except ValueError:
            pass
        else:
            raise AssertionError(f"Receipt accepted post-binding edit to {field_name}")
        object.__setattr__(receipt, field_name, original_value)
        assert receipt.require_current() is receipt
    altered = replace(thermal, stages=(replace(thermal.stages[0], generated_heat_j=
                                               thermal.stages[0].generated_heat_j+1.),
                                       *thermal.stages[1:]))
    try:
        bind_electrolysis_thermal_operation(owner, altered, pv_trace, **arguments)
    except ValueError:
        pass
    else:
        raise AssertionError("PV electrolysis thermal receipt accepted a forged heat row")
    return ValidationOutcome(True, {
        "matched_native_intervals": len(thermal.stages),
        "generated_heat_residual_j": receipt.generated_heat_residual_j,
        "forged_thermal_trace_rejections": fabricated_thermal_rejections,
    }, ("Post-run synthetic compatibility only; no live feedback, utility or device validation",))
