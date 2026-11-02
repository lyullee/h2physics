"""Deferred synthetic contracts for transient gas-turbine shaft mechanics."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

LIMITS = (
    "Prescribed powers, torque and inertia are synthetic software fixtures.",
    "The case covers rotor dynamics only; cycle and component power accuracy are outside it.",
    "Speed-limit events are terminal and must not be clipped or silently extrapolated.",
)


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-brayton-transient-shaft-balance",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_shaft_transient",
            invariants=("kinetic-energy-ledger-closes", "equal-powers-preserve-speed",
                        "cumulative-work-signs", "input-and-result-mutation-rejected"),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-transient-shaft-speed-event",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_shaft_transient",
            parameters={"scenario": "maximum-speed"},
            invariants=("speed-limit-is-terminal", "event-state-is-retained",
                        "rotor-speed-is-never-clipped"),
        ),
        ValidationCase(
            identifier="hydrogen-brayton-transient-shaft-speed-event-retry-20261031",
            profile="hydrogen-engine",
            entrypoint=__name__ + ":validate_shaft_transient",
            parameters={"scenario": "maximum-speed"},
            invariants=("retry-after-outcome-contract-fix", "speed-limit-is-terminal",
                        "event-state-is-retained", "rotor-speed-is-never-clipped"),
        ),
    )


def validate_shaft_transient(*, work_directory, scenario="balanced", **parameters):
    del work_directory, parameters
    from h2physics.combustion.shaft_transient import (
        ShaftTransientInputs,
        integrate_shaft_transient,
    )

    if scenario == "balanced":
        times = np.asarray((0., 1., 2.))
        turbine = np.asarray((5000., 5000., 5000.))
        compressor = turbine.copy()
        load = np.zeros(3)
        upper = 120.
    elif scenario == "maximum-speed":
        times = np.asarray((0., 0.1, 0.2))
        turbine = np.full(3, 10000.)
        compressor = np.zeros(3)
        load = np.zeros(3)
        upper = 11.
    else:
        raise ValueError(f"Unknown shaft scenario: {scenario}")
    inputs = ShaftTransientInputs(
        time_s=times,
        turbine_power_w=turbine,
        compressor_power_w=compressor,
        load_torque_nm=load,
        output_time_s=np.linspace(times[0], times[-1], 21),
        rotor_inertia_kg_m2=1.,
        initial_speed_rad_s=10.,
        minimum_speed_rad_s=1.,
        maximum_speed_rad_s=upper,
        coulomb_loss_torque_nm=0.,
        viscous_loss_nm_per_rad_s=0.,
        relative_tolerance=1e-9,
        absolute_energy_tolerance_j=1e-9,
        maximum_step_s=0.005,
        shaft_id="synthetic:one-spool",
        power_basis_id="synthetic:power-schedule",
        load_basis_id="synthetic:load-torque",
        inertia_evidence_id="synthetic:inertia",
    )
    trace = integrate_shaft_transient(inputs)
    trace.require_current()
    energy_error = float(np.max(np.abs(trace.energy_residual_j)))
    if scenario == "balanced":
        if trace.termination != "completed" or not np.allclose(
                trace.speed_rad_s, 10., rtol=0., atol=1e-10):
            raise AssertionError("Balanced shaft powers must preserve rotor speed")
        if not np.allclose(trace.cumulative_turbine_work_j,
                           trace.cumulative_compressor_work_j, rtol=0., atol=1e-9):
            raise AssertionError("Equal component work must cancel in the inventory ledger")
    else:
        if trace.termination != "maximum_speed" or not np.isclose(
                trace.speed_rad_s[-1], upper, rtol=0., atol=1e-12):
            raise AssertionError("The rotor must terminate exactly at the maximum-speed event")
        if trace.time_s[-1] >= times[-1]:
            raise AssertionError("The maximum-speed event should occur inside the requested window")
    if energy_error > 1e-5:
        raise AssertionError("Transient rotor energy residual exceeds the fixture budget")
    return ValidationOutcome(accepted=True, metrics={
        "scenario_code": float(0 if scenario == "balanced" else 1),
        "termination_code": float({"completed": 0, "minimum_speed": 1,
                                    "maximum_speed": 2, "solver_failed": 3}[trace.termination]),
        "final_speed_rad_s": float(trace.speed_rad_s[-1]),
        "final_energy_residual_j": float(trace.energy_residual_j[-1]),
        "solver_evaluations": float(trace.function_evaluations),
    }, limitations=LIMITS)
