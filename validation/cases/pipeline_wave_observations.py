"""Synthetic Hangang contract for measured pipe-wave observation mapping."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-pipeline-wave-observation-operator",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_observation_operator",
        invariants=(
            "absolute-pressure and signed mass-flow channels retain source, sensor, unit and clock identities",
            "pressure and flow map linearly in space only inside the represented pipe support",
            "observation times must be exact retained solver samples and no temporal interpolation is implicit",
            "pressure taps use absolute Pa and mass-flow sign is positive toward increasing pipe x",
            "source observations and comparison diagnostics do not assert independent physical validation",
        ),
    ),)


def validate_observation_operator(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.adapters.isothermal_pipe_observations import (
        PipelineMassFlowHistory,
        PipelinePressureHistory,
        compare_isothermal_pipe_observations,
    )
    from h2physics.isothermal_pipe_waves import (
        IdealHydrogenIsothermalEOS,
        IsothermalPipeWaveModel,
    )

    model = IsothermalPipeWaveModel(
        length_m=12., internal_diameter_m=.08, cell_count=12,
        temperature_k=295., darcy_friction_factor=.015,
        eos=IdealHydrogenIsothermalEOS(),
    )
    trace = model.simulate(
        initial_pressure_pa=np.linspace(2.0e5, 2.1e5, 12),
        initial_velocity_m_s=np.zeros(12),
        time_samples_s=(0., .002, .006, .01),
    )
    pressure_times = np.asarray((0., .006, .01))
    pressure_indices = np.searchsorted(trace.time_s, pressure_times)
    tap = float(.5 * (trace.cell_center_m[5] + trace.cell_center_m[6]))
    pressure_values = np.asarray([
        np.interp(tap, trace.cell_center_m, trace.pressure_pa[index])
        for index in pressure_indices
    ])
    dx = float(np.diff(trace.cell_center_m)[0])
    face_positions = np.concatenate((
        [trace.cell_center_m[0] - .5 * dx],
        trace.cell_center_m + .5 * dx,
    ))
    meter_x = float(.5 * (face_positions[4] + face_positions[5]))
    flow_values = np.asarray([
        np.interp(meter_x, face_positions, trace.face_mass_flow_kg_s[index])
        for index in pressure_indices
    ])
    pressure = PipelinePressureHistory(
        time_s=pressure_times,
        pressure_pa=pressure_values,
        standard_uncertainty_pa=np.full(3, 250.),
        tap_position_m=tap,
        channel_id="synthetic-pressure-tap-07",
        clock_id="synthetic-pipe-clock-v1",
        source_evidence_id="synthetic-source-observation-v1",
        sensor_mapping_evidence_id="synthetic-tap-survey-v1",
    )
    flow = PipelineMassFlowHistory(
        time_s=pressure_times,
        mass_flow_kg_s=flow_values,
        standard_uncertainty_kg_s=np.full(3, .01),
        meter_position_m=meter_x,
        channel_id="synthetic-mass-flow-meter-03",
        clock_id="synthetic-pipe-clock-v1",
        source_evidence_id="synthetic-source-observation-v1",
        sensor_mapping_evidence_id="synthetic-meter-survey-v1",
    )
    result = compare_isothermal_pipe_observations(
        trace, pressure, flow,
        model_clock_id="synthetic-pipe-clock-v1",
        clock_alignment_evidence_id="synthetic-clock-alignment-v1",
    )
    if (not np.allclose(result.pressure_residual_pa, 0., rtol=0., atol=1e-9)
            or not np.allclose(result.flow_residual_kg_s, 0., rtol=0., atol=1e-14)):
        raise AssertionError("Exact synthetic observation projection produced nonzero residuals")
    shifted_pressure = PipelinePressureHistory(
        time_s=pressure_times + 1e-6,
        pressure_pa=pressure_values,
        standard_uncertainty_pa=np.full(3, 250.),
        tap_position_m=tap,
        channel_id="synthetic-pressure-shifted-clock",
        clock_id="synthetic-pipe-clock-v1",
        source_evidence_id="synthetic-source-observation-v1",
        sensor_mapping_evidence_id="synthetic-tap-survey-v1",
    )
    try:
        compare_isothermal_pipe_observations(
            trace, shifted_pressure, flow,
            model_clock_id="synthetic-pipe-clock-v1",
            clock_alignment_evidence_id="synthetic-clock-alignment-v1",
        )
    except ValueError:
        shifted_clock_rejected = True
    else:
        raise AssertionError("Off-grid measurement times must not be implicitly interpolated")
    return ValidationOutcome(True, {
        "pressure_channel": pressure.channel_id,
        "flow_channel": flow.channel_id,
        "clock_id": result.model_clock_id,
        "pressure_weighted_rms": result.pressure_weighted_rms,
        "flow_weighted_rms": result.flow_weighted_rms,
        "off_grid_times_rejected": shifted_clock_rejected,
        "pressure_tap_position_m": tap,
        "mass_flow_meter_position_m": meter_x,
    }, limitations=(
        "Synthetic observation-mapping software contract only; no measured H2 pipeline dataset was used.",
        "Spatial interpolation is linear between solver nodes; time interpolation, calibration, sensor dynamics, and uncertainty covariance are not represented.",
        "This comparison does not validate EOS, pipeline physics, parameter values, or field applicability.",
    ))
