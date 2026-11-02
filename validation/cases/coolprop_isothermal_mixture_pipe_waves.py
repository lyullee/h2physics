"""Deferred Hangang composition-EOS and isothermal pipe-wave contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydrogen-pipeline-isothermal-mixture-pressure-wave",
        profile="gas-compressible-pipe",
        entrypoint=__name__ + ":validate_mixture_pressure_wave",
        invariants=(
            "fixed-H2-N2-CoolProp-mixture-implements-the-existing-isothermal-EOS-protocol",
            "homogeneous-gas-pressure-density-closure-is-reproduced-by-the-wave-solver",
            "isothermal-characteristic-speed-and-CFL-remain-positive-and-bounded",
            "closed-end-finite-volume-face-ledger-conserves-total-mixture-mass",
            "reservoir-boundary-with-a-different-frozen-mixture-provider-identity-is-rejected",
            "no-ideal-gas-fallback-or-composition-change-is-introduced",
        ),
    ),)


def validate_mixture_pressure_wave(*, work_directory, **parameters):
    """Exercise the existing pipe-wave solver with a frozen H2/N2 HEOS EOS."""
    del work_directory, parameters
    import numpy as np

    from h2physics.core import Origin
    from h2physics.mixtures import GasComposition
    from h2physics.isothermal_pipe_waves import IsothermalPipeWaveModel
    from h2physics.pipe_reservoir_boundary import FiniteReservoirPressureBoundary
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
    from h2physics.thermo.isothermal_eos import CoolPropMixtureIsothermalEOS

    composition = GasComposition(
        "wave-contract-H2-10mol-N2-90mol",
        ("Hydrogen", "Nitrogen"),
        (0.10, 0.90),
        (0.00201588, 0.0280134),
    )
    properties = CoolPropMixtureProperties(composition)
    eos = CoolPropMixtureIsothermalEOS(properties)
    temperature = 300.0
    initial_pressure = 5.0e6
    density = eos.density_pt(initial_pressure, temperature)
    pressure_recovered = eos.pressure_rho_t(density, temperature)
    pressure_roundtrip_relative_error = abs(pressure_recovered-initial_pressure) / initial_pressure
    assert pressure_roundtrip_relative_error <= 1.0e-6

    cell_count = 12
    model = IsothermalPipeWaveModel(
        length_m=120.0,
        internal_diameter_m=0.1,
        cell_count=cell_count,
        temperature_k=temperature,
        darcy_friction_factor=0.015,
        maximum_cfl=0.35,
        eos=eos,
    )
    initial_pressures = np.full(cell_count, initial_pressure)
    centers = np.linspace(5.0, 115.0, cell_count)
    initial_velocity = 1.5*np.exp(-((centers-45.0)/15.0)**2)
    times = (0.0, 0.01, 0.02)
    trace = model.simulate(
        initial_pressure_pa=initial_pressures,
        initial_velocity_m_s=initial_velocity,
        time_samples_s=times,
    )
    assert trace.eos_closure_id == eos.identity
    assert 0.0 < trace.maximum_cfl <= trace.cfl_limit <= 0.5
    assert np.all(trace.pressure_pa > 0.0)
    assert np.all(trace.density_kg_m3 > 0.0)
    assert np.all(trace.isothermal_sound_speed_m_s > 0.0)
    assert np.max(np.abs(trace.mass_balance_residual_kg)) <= 1.0e-9
    assert np.all(trace.face_mass_flow_kg_s[:, (0, -1)] == 0.0)
    selected_closure_errors = []
    for sample_index in (0, -1):
        for pressure, sample_density in zip(
                trace.pressure_pa[sample_index],
                trace.density_kg_m3[sample_index], strict=True):
            replay = eos.pressure_rho_t(float(sample_density), temperature)
            selected_closure_errors.append(
                abs(replay-float(pressure)) / max(abs(float(pressure)), 1.0))
    assert max(selected_closure_errors) <= 1.0e-6

    wrong_identity_boundary = FiniteReservoirPressureBoundary(
        identifier="wrong-mixture-source",
        state_owner_id="synthetic-boundary-owner",
        state_evidence_id="synthetic-boundary-state",
        clock_id="synthetic-wave-clock",
        eos_identity=eos.identity + ":different-mixture",
        temperature_k=temperature,
        time_s=np.asarray((0.0, times[-1])),
        pressure_pa=np.asarray((initial_pressure, initial_pressure)),
        origin=Origin.SYNTHETIC,
    )
    identity_rejected = False
    try:
        model.simulate(
            initial_pressure_pa=initial_pressures,
            initial_velocity_m_s=np.zeros(cell_count),
            time_samples_s=times,
            left_reservoir=wrong_identity_boundary,
            clock_id="synthetic-wave-clock",
        )
    except ValueError as error:
        identity_rejected = "different isothermal EOS" in str(error)
    assert identity_rejected
    return ValidationOutcome(True, {
        "mixture_identity": eos.identity,
        "composition_sha256": properties.composition_sha256,
        "h2_mole_fraction": float(properties.mole_fractions[0]),
        "initial_density_kg_m3": density,
        "initial_pressure_roundtrip_relative_error": pressure_roundtrip_relative_error,
        "maximum_sampled_pressure_density_closure_relative_error": max(selected_closure_errors),
        "cell_count": cell_count,
        "maximum_used_cfl": trace.maximum_cfl,
        "cfl_limit": trace.cfl_limit,
        "maximum_mass_balance_residual_kg": float(np.max(np.abs(trace.mass_balance_residual_kg))),
        "wrong_provider_identity_rejected": identity_rejected,
    }, (
        "Synthetic CoolProp HEOS frozen-composition pipe-wave software contract only",
        "EOS phase behavior and binary interactions belong to the installed CoolProp release",
        "No blend-pipeline measurements, composition evolution, energy equation, or facility qualification is established",
    ))
