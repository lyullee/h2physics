"""Deferred HEOS mixture-EOS contract on real-gas linepack."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="coolprop-isothermal-mixture-linepack",
        profile="isothermal-eos",
        entrypoint=__name__ + ":validate_mixture_linepack",
        invariants=(
            "frozen-composition-CoolProp-mixture-binds-to-the-isothermal-EOS-protocol",
            "mass-density-and-pressure-invert-through-the-native-HEOS-mixture",
            "the-specified-H2-mole-fraction-is-retained-without-an-ideal-gas-fallback",
            "linepack-port-mass-ledger-closes-and-pressure-responds-to-charge",
            "two-phase-mixture-states-are-rejected-by-the-gas-linepack-closure",
        ),
    ),)


def validate_mixture_linepack(*, work_directory, **parameters):
    del work_directory, parameters

    from h2physics.mixtures import GasComposition
    from h2physics.real_gas_linepack import RealGasLinepackState
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
    from h2physics.thermo.isothermal_eos import CoolPropMixtureIsothermalEOS

    composition = GasComposition(
        "h2-10mol-n2-90mol",
        ("Hydrogen", "Nitrogen"),
        (0.10, 0.90),
        (0.00201588, 0.0280134),
    )
    properties = CoolPropMixtureProperties(composition)
    eos = CoolPropMixtureIsothermalEOS(properties)
    state = RealGasLinepackState.from_pressure(
        volume_m3=2.0,
        temperature_k=293.15,
        pressure_pa=7.0e6,
        eos=eos,
        minimum_pressure_pa=1.0e6,
        maximum_pressure_pa=1.0e7,
    )
    speed = eos.isothermal_sound_speed_rho_t(
        state.density_kg_m3, state.temperature_k,
    )
    delta = state.density_kg_m3 * 1.0e-5
    pressure_derivative = (
        eos.pressure_rho_t(state.density_kg_m3 + delta, state.temperature_k)
        - eos.pressure_rho_t(state.density_kg_m3 - delta, state.temperature_k)
    ) / (2.0 * delta)
    derivative_relative_error = abs(speed * speed - pressure_derivative) / pressure_derivative
    assert derivative_relative_error <= 1.0e-4
    charged, ledger = state.advance(
        duration_s=20.0,
        inlet_mass_flow_kg_s=0.05,
        outlet_mass_flow_kg_s=0.01,
        minimum_mass_kg=0.01,
    )
    assert charged.pressure_pa > state.pressure_pa
    assert abs(ledger.mass_residual_kg) <= 1.0e-12
    assert eos.identity.endswith(f"{properties.composition_sha256}:isothermal-frozen-mixture")

    phase_rejected = False
    try:
        eos.density_pt(1.0e5, 20.0)
    except ValueError:
        phase_rejected = True
    assert phase_rejected
    return ValidationOutcome(True, {
        "composition_sha256": properties.composition_sha256,
        "h2_mole_fraction": properties.mole_fractions[0],
        "initial_pressure_pa": state.pressure_pa,
        "isothermal_speed_m_s": speed,
        "isothermal_derivative_relative_error": derivative_relative_error,
        "charged_pressure_pa": charged.pressure_pa,
        "mass_residual_kg": ledger.mass_residual_kg,
        "phase_rejected": phase_rejected,
    }, (
        "CoolProp HEOS frozen-composition isothermal mixture contract only",
        "Composition does not evolve during linepack charging or discharge",
        "No mixture-pipeline transient or independent data qualification is established",
    ))
