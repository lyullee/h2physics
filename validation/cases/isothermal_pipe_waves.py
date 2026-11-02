"""Synthetic stability, pulse-propagation, and closed-segment mass contracts."""

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-pipeline-isothermal-pressure-wave-dynamics",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_pressure_wave_contract",
        invariants=(
            "uniform resting hydrogen remains at the same thermodynamic state under closed reflective boundaries",
            "a bounded initial velocity disturbance evolves into a finite pressure wave under the isothermal Euler equations",
            "Rusanov finite-volume substeps obey the configured CFL bound and preserve positive cell density",
            "impermeable end faces and telescoping internal face fluxes conserve total pipe mass",
            "Darcy wall drag acts in the momentum equation without changing total pipe mass",
            "the level is fixed-temperature single-segment dynamics with an explicit isothermal EOS, not quasi-steady linepack",
        ),
    ),)


def validate_pressure_wave_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.isothermal_pipe_waves import (
        IdealHydrogenIsothermalEOS, IsothermalPipeWaveModel,
    )

    class SyntheticEOSAdapter:
        """Exercise the public structural closure hooks without external dependencies."""

        identity = "synthetic-isothermal-eos-adapter-v1"

        def __init__(self):
            self._reference = IdealHydrogenIsothermalEOS()

        def density_pt(self, p_pa, t_k):
            return self._reference.density_pt(p_pa, t_k)

        def pressure_rho_t(self, rho_kg_m3, t_k):
            return self._reference.pressure_rho_t(rho_kg_m3, t_k)

        def isothermal_sound_speed_rho_t(self, rho_kg_m3, t_k):
            return self._reference.isothermal_sound_speed_rho_t(rho_kg_m3, t_k)

    eos = SyntheticEOSAdapter()

    count = 40
    initial_pressure = np.full(count, 5.0e6)
    rest_velocity = np.zeros(count)
    times = (0., 0.02, 0.05, 0.10)
    equilibrium = IsothermalPipeWaveModel(
        length_m=100., internal_diameter_m=0.1, cell_count=count,
        temperature_k=300., eos=eos,
        darcy_friction_factor=0.015, maximum_cfl=0.35,
    ).simulate(initial_pressure_pa=initial_pressure,
               initial_velocity_m_s=rest_velocity, time_samples_s=times)
    if (not np.allclose(equilibrium.pressure_pa, initial_pressure[None, :], rtol=0., atol=1e-7)
            or not np.allclose(equilibrium.velocity_m_s, 0., rtol=0., atol=1e-14)):
        raise AssertionError("Uniform resting state drifted under closed boundaries")

    centers = equilibrium.cell_center_m
    velocity_pulse = 8. * np.exp(-((centers - 25.) / 8.) ** 2)
    wave = IsothermalPipeWaveModel(
        length_m=100., internal_diameter_m=0.1, cell_count=count,
        temperature_k=300., eos=eos,
        darcy_friction_factor=0.015, maximum_cfl=0.35,
    ).simulate(initial_pressure_pa=initial_pressure,
               initial_velocity_m_s=velocity_pulse, time_samples_s=times)
    if np.max(np.abs(wave.pressure_pa[-1] - wave.pressure_pa[0])) <= 1.:
        raise AssertionError("Initial velocity pulse did not create a resolved pressure response")
    if np.max(np.abs(wave.mass_balance_residual_kg)) > 1e-10:
        raise AssertionError("Closed pipe segment failed the total-mass conservation contract")
    if np.any(wave.density_kg_m3 <= 0.) or np.any(wave.pressure_pa <= 0.):
        raise AssertionError("Finite-volume trace lost positive density or pressure")
    if not (0. < wave.maximum_cfl <= wave.cfl_limit <= 0.5):
        raise AssertionError("Observed substep CFL must remain within its declared explicit-scheme bound")
    if not np.all(wave.face_mass_flow_kg_s[:, (0, -1)] == 0.):
        raise AssertionError("Impermeable pipe ends must have zero face mass flow")
    try:
        wave.pressure_pa.setflags(write=True)
    except ValueError:
        immutable = True
    else:
        raise AssertionError("Pressure-wave trace arrays must be bytes-backed immutable")
    return ValidationOutcome(True, {
        "cell_count": count,
        "time_samples_s": wave.time_s.tolist(),
        "maximum_isothermal_sound_speed_m_s": float(np.max(wave.isothermal_sound_speed_m_s)),
        "eos_identity": wave.eos_closure_id,
        "observed_maximum_cfl": wave.maximum_cfl,
        "maximum_cfl_limit": wave.cfl_limit,
        "minimum_density_kg_m3": float(np.min(wave.density_kg_m3)),
        "maximum_absolute_mass_residual_kg": float(np.max(np.abs(wave.mass_balance_residual_kg))),
        "pressure_perturbation_max_pa": float(np.max(np.abs(wave.pressure_pa[-1] - wave.pressure_pa[0]))),
        "closed_end_flow_max_kg_s": float(np.max(np.abs(wave.face_mass_flow_kg_s[:, (0, -1)]))),
        "trace_arrays_immutable": immutable,
    }, (
        "Synthetic numerical contract only. Isothermal Euler with caller EOS closure and constant caller Darcy factor.",
        "No real-gas correction, energy/wall heat equation, leak, valve, reservoir boundary, pipe junction or measured-pipeline validation is included.",
        "The source is governing-equation provenance only; this synthetic case is not evidence of independent model qualification.",
    ))
