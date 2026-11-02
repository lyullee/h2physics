"""Deferred Hangang contracts for finite-capacity gas-pipe wall coupling."""


def cases():
    from h2physics.cluster_validation import ValidationCase

    return (ValidationCase(
        identifier="hydrogen-caloric-pipe-finite-wall-energy-closure",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_finite_wall_energy_closure",
        invariants=(
            "finite-wall-temperature-responds-to-integrated-gas-wall-heat",
            "combined-gas-wall-energy-ledger-closes-without-ambient-exchange",
            "ambient-heat-is-accounted-as-an-external-wall-energy-transfer",
            "outer-time-refinement-retains-one-issued-caloric-gas-trace-per-interval",
        ),
    ),)


def validate_finite_wall_energy_closure(*, work_directory, **parameters):
    from dataclasses import replace

    import numpy as np

    from h2physics.caloric_pipe_finite_wall import (
        LumpedPipeWall,
        simulate_caloric_pipe_with_finite_wall,
    )
    from h2physics.caloric_pipe_waves import CaloricPipeWaveModel
    from h2physics.cluster_validation import ValidationOutcome
    from validation.cases.caloric_pipe_waves import (
        _SyntheticCaloricHydrogen,
    )

    eos = _SyntheticCaloricHydrogen()
    model = CaloricPipeWaveModel(length_m=4.0, internal_diameter_m=0.02,
                                 cell_count=4, eos=eos)
    wall = LumpedPipeWall(
        identifier="synthetic-finite-wall", state_owner_id="authored-fixture",
        state_evidence_id="synthetic-contract-only", clock_id="hangang-case-clock",
        initial_temperature_k=310.0, heat_capacity_j_k=1200.0,
        gas_heat_transfer_coefficient_w_m2_k=8.0,
    )
    trace = simulate_caloric_pipe_with_finite_wall(
        model, wall=wall, initial_pressure_pa=np.full(4, 2.0e5),
        initial_temperature_k=np.full(4, 300.0), initial_velocity_m_s=np.zeros(4),
        time_samples_s=(0.0, 0.05, 0.1), clock_id=wall.clock_id,
    )
    if len(trace.gas_traces) != 2:
        raise AssertionError("one solver trace must be retained for each outer interval")
    if np.isclose(trace.wall_temperature_k[-1], wall.initial_temperature_k, rtol=0., atol=1.e-12):
        raise AssertionError("nonzero wall heat must change finite wall temperature")
    energy_scale = max(1.0, abs(trace.cumulative_gas_wall_heat_into_gas_j[-1]))
    if np.max(np.abs(trace.combined_energy_balance_residual_j)) > 1.e-8 * energy_scale:
        raise AssertionError("combined gas-wall energy ledger failed closure")
    try:
        replace(trace)
    except ValueError:
        pass
    else:
        raise AssertionError("finite-wall summary traces must be run-issued and not caller-constructed")
    ambient_wall = LumpedPipeWall(
        identifier="synthetic-finite-wall-ambient", state_owner_id="authored-fixture",
        state_evidence_id="synthetic-contract-only", clock_id="hangang-case-clock",
        initial_temperature_k=310.0, heat_capacity_j_k=1200.0,
        gas_heat_transfer_coefficient_w_m2_k=8.0,
        ambient_temperature_k=290.0, ambient_ua_w_k=2.0,
        ambient_evidence_id="synthetic-ambient-contract-only",
    )
    ambient_trace = simulate_caloric_pipe_with_finite_wall(
        model, wall=ambient_wall, initial_pressure_pa=np.full(4, 2.0e5),
        initial_temperature_k=np.full(4, 300.0), initial_velocity_m_s=np.zeros(4),
        time_samples_s=(0.0, 0.05, 0.1), clock_id=ambient_wall.clock_id,
    )
    if ambient_trace.cumulative_ambient_heat_into_wall_j[-1] >= 0.:
        raise AssertionError("cooler ambient must remove energy from the wall")
    ambient_scale = max(1.0, abs(ambient_trace.cumulative_ambient_heat_into_wall_j[-1]))
    if np.max(np.abs(ambient_trace.combined_energy_balance_residual_j)) > 1.e-8 * ambient_scale:
        raise AssertionError("ambient heat was not included in the combined energy ledger")
    return ValidationOutcome(True, {
        "outer_intervals": len(trace.gas_traces),
        "wall_temperature_change_k": float(
            trace.wall_temperature_k[-1] - wall.initial_temperature_k),
        "maximum_combined_energy_residual_j": float(
            np.max(np.abs(trace.combined_energy_balance_residual_j))),
        "ambient_heat_into_wall_j": float(
            ambient_trace.cumulative_ambient_heat_into_wall_j[-1]),
    }, (
        "synthetic finite-wall contract only; one mixed wall node and first-order splitting",
        "no measured pipe-wall thermal validation or spatial axial wall gradient",
    ))
