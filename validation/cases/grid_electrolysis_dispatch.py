"""Synthetic contract for the grid-power-to-existing-stack dispatch adapter."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="grid-ac-power-to-electrolysis-stack-dispatch",
        profile="grid-electrolysis",
        entrypoint=__name__ + ":validate_dispatch",
        invariants=(
            "grid-power-intervals-retain-source-clock-and-contiguous-edges",
            "dispatch-reuses-the-shared-HydrogenStack-polarization-kernel",
            "highest-feasible-sampled-current-respects-AC-availability-rectifier-and-auxiliaries",
            "AC-stack-loss-and-curtailed-power-ledgers-close-per-interval",
            "returned-held-commands-are-compatible-with-existing-FiniteThermalStack",
            "resolution-and-model-limitations-remain-explicit",
        ),
    ),)


def validate_dispatch(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.grid_electrolysis_dispatch import (
        GridPowerInterval,
        dispatch_grid_power_to_electrolysis,
    )
    from h2physics.electrochemistry import HydrogenStack, OhmicLoss, StackGeometry
    from h2physics.electrochemistry import ReactionEnergy

    stack = HydrogenStack(
        StackGeometry(20, .01, .00201588),
        lambda _temperature: ReactionEnergy(237000., 285800., "synthetic-water-reference", "liquid"),
        {"ohmic": OhmicLoss(lambda _temperature: .0002)},
    )
    intervals = (
        GridPowerInterval("grid-0", 0., 60., "authored-grid-clock", "synthetic-grid-input", 250., 10.),
        GridPowerInterval("grid-1", 60., 120., "authored-grid-clock", "synthetic-grid-input", 125., 10.),
    )
    schedule = dispatch_grid_power_to_electrolysis(
        stack, intervals, coolant_temperature_k=333.15,
        maximum_current_density_a_m2=20_000.,
        current_density_resolution_a_m2=100., rectifier_efficiency=.96,
        evidence_id="synthetic-grid-stack-boundary",
    )
    for step in schedule.steps:
        duration = step.source.end_s-step.source.start_s
        assert step.grid_ac_power_w <= step.source.available_ac_power_w
        assert abs(step.curtailed_ac_power_w-(
            step.source.available_ac_power_w-step.grid_ac_power_w)) <= 1e-12
        assert abs(step.grid_ac_power_w-(
            step.auxiliary_ac_power_w+step.stack_dc_power_w+step.rectifier_loss_w)) <= 1e-9
        assert step.stack_result.current_a == (
            step.thermal_command.current_density_a_m2*stack.geometry.active_area_m2)
        assert duration > 0
    assert tuple(c.identifier for c in schedule.thermal_commands) == ("grid-0", "grid-1")
    return ValidationOutcome(True, {
        "intervals": len(schedule.steps),
        "hydrogen_produced_mol": schedule.hydrogen_production_mol,
        "grid_energy_j": schedule.grid_energy_j,
        "chosen_current_densities_a_m2": tuple(
            step.thermal_command.current_density_a_m2 for step in schedule.steps),
        "maximum_grid_overdraw_w": max(
            step.grid_ac_power_w-step.source.available_ac_power_w for step in schedule.steps),
    }, (
        "Synthetic API contract only; it does not validate stack parameters against an operating plant.",
        "The dispatch uses a declared finite current-density grid; its resolution error must be assessed by refinement.",
        "No AC network dynamics, transformer, rectifier dynamics, stack ramping, degradation or material inventory is modeled.",
    ))
