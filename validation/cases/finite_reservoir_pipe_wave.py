"""Deferred pressure-reservoir boundary and mass-closure case for pipe waves."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-pipeline-isothermal-wave-finite-reservoir-boundaries",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_reservoir_boundaries",
        invariants=(
            "time-varying-reservoir-pressure-is-interpolated-only-inside-owned-clock-support",
            "reservoir-and-pipe-temperature-and-EOS-identities-match-exactly",
            "subsonic-boundary-state-combines-reservoir-incoming-and-pipe-outgoing-characteristics",
            "signed-left-and-right-boundary-mass-flows-are-retained-at-output-times",
            "cumulative-boundary-inflow-outflow-close-total-pipe-mass",
            "finite-reservoir-pressure-is-caller-owned-and-no-reservoir-depletion-model-is-implied",
            "past-future-and-incomplete-reservoir-clock-support-are-rejected",
            "clock-EOS-temperature-characteristic-bracket-and-supersonic-mismatches-are-rejected",
        ),
    ),)


def validate_reservoir_boundaries(*, work_directory, **parameters):
    del work_directory, parameters
    from dataclasses import replace
    import numpy as np

    from h2physics.core import Origin
    from h2physics.isothermal_pipe_waves import IdealHydrogenIsothermalEOS, IsothermalPipeWaveModel
    from h2physics.pipe_reservoir_boundary import FiniteReservoirPressureBoundary

    eos = IdealHydrogenIsothermalEOS()
    clock = "authored-pipe-reservoir-clock"
    left = FiniteReservoirPressureBoundary(
        identifier="authored-left-finite-reservoir",
        state_owner_id="authored-left-reservoir-state-owner",
        state_evidence_id="authored-left-reservoir-pressure-history",
        clock_id=clock, eos_identity=eos.identity, temperature_k=300.,
        time_s=(0., .1, .2), pressure_pa=(5.10e6, 5.08e6, 5.05e6),
        origin=Origin.SYNTHETIC,
    )
    right = FiniteReservoirPressureBoundary(
        identifier="authored-right-finite-reservoir",
        state_owner_id="authored-right-reservoir-state-owner",
        state_evidence_id="authored-right-reservoir-pressure-history",
        clock_id=clock, eos_identity=eos.identity, temperature_k=300.,
        time_s=(0., .1, .2), pressure_pa=(4.90e6, 4.92e6, 4.95e6),
        origin=Origin.SYNTHETIC,
    )
    count = 32
    model = IsothermalPipeWaveModel(
        length_m=100., internal_diameter_m=.1, cell_count=count,
        temperature_k=300., eos=eos, darcy_friction_factor=.015,
        maximum_cfl=.35,
    )
    trace = model.simulate(
        initial_pressure_pa=np.full(count, 5.e6),
        initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .05, .1, .15, .2),
        left_reservoir=left, right_reservoir=right, clock_id=clock,
    )
    assert trace.left_reservoir_id == left.identifier
    assert trace.right_reservoir_id == right.identifier
    assert np.allclose(trace.left_reservoir_pressure_pa, (5.10e6, 5.09e6, 5.08e6, 5.065e6, 5.05e6))
    assert np.allclose(trace.right_reservoir_pressure_pa, (4.90e6, 4.91e6, 4.92e6, 4.935e6, 4.95e6))
    assert np.max(np.abs(trace.face_mass_flow_kg_s[:, (0, -1)])) > 0.
    assert trace.boundary_mass_in_kg[-1] > 0. and trace.boundary_mass_out_kg[-1] > 0.
    assert np.max(np.abs(trace.mass_balance_residual_kg)) < 1.e-8
    assert np.allclose(
        trace.mass_balance_residual_kg,
        trace.total_mass_kg - trace.total_mass_kg[0]
        - trace.boundary_mass_in_kg + trace.boundary_mass_out_kg,
        rtol=0., atol=1.e-12,
    )
    assert np.all(trace.boundary_mass_in_kg[1:] >= trace.boundary_mass_in_kg[:-1])
    assert np.all(trace.boundary_mass_out_kg[1:] >= trace.boundary_mass_out_kg[:-1])
    assert np.all(np.isfinite(trace.face_mass_flow_kg_s[:, (0, -1)]))
    assert 0. < trace.maximum_cfl <= trace.cfl_limit <= .5

    def require_rejection(call):
        try:
            call()
        except (TypeError, ValueError, FloatingPointError):
            return
        raise AssertionError("Unsupported pressure-boundary contract was accepted")

    require_rejection(lambda: left.pressure_at(-1.e-6))
    require_rejection(lambda: right.pressure_at(.200001))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .1, .21), left_reservoir=left, right_reservoir=right,
        clock_id=clock,
    ))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .1), left_reservoir=replace(left, clock_id="wrong-clock"),
        right_reservoir=right, clock_id=clock,
    ))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .1), left_reservoir=replace(left, eos_identity="wrong-eos"),
        right_reservoir=right, clock_id=clock,
    ))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .1), left_reservoir=replace(left, temperature_k=301.),
        right_reservoir=right, clock_id=clock,
    ))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.zeros(count),
        time_samples_s=(0., .1), left_reservoir=replace(left, pressure_pa=(2.e7, 2.e7, 2.e7)),
        right_reservoir=right, clock_id=clock,
    ))
    require_rejection(lambda: model.simulate(
        initial_pressure_pa=np.full(count, 5.e6), initial_velocity_m_s=np.full(count, 2.e3),
        time_samples_s=(0., .01), left_reservoir=left, right_reservoir=right,
        clock_id=clock,
    ))
    return ValidationOutcome(True, {
        "clock_id": trace.boundary_clock_id,
        "left_reservoir_id": trace.left_reservoir_id,
        "right_reservoir_id": trace.right_reservoir_id,
        "sampled_left_pressure_pa": trace.left_reservoir_pressure_pa.tolist(),
        "sampled_right_pressure_pa": trace.right_reservoir_pressure_pa.tolist(),
        "cumulative_boundary_inflow_kg": float(trace.boundary_mass_in_kg[-1]),
        "cumulative_boundary_outflow_kg": float(trace.boundary_mass_out_kg[-1]),
        "maximum_mass_balance_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "maximum_cfl": trace.maximum_cfl,
    }, (
        "Synthetic software contract only; the reservoir pressure histories are caller-owned inputs.",
        "No reservoir inventory/depletion, valve/orifice, regulator, thermal transient, or measured pipeline qualification is added.",
    ))
