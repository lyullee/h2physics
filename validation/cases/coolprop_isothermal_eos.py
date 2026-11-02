"""Deferred provider-specific checks for the isothermal HEOS closure."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="coolprop-isothermal-single-phase-eos",
        profile="isothermal-eos",
        entrypoint=__name__ + ":validate_provider",
        invariants=(
            "CoolProp-HEOS-pressure-temperature-density-roundtrip-closes",
            "characteristic-speed-squared-matches-isothermal-pressure-density-derivative",
            "the-provider-uses-isothermal-compressibility-not-adiabatic-speed-of-sound",
            "liquid-and-unresolved-mixture-identifiers-are-rejected",
            "nonpositive-state-inputs-and-non-HEOS-backends-are-rejected",
        ),
    ),)


def validate_provider(*, work_directory, **parameters):
    del work_directory, parameters
    from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

    eos = CoolPropIsothermalEOS("Hydrogen")
    points = ((1.0e5, 300.0), (1.0e6, 300.0), (1.0e7, 300.0),
              (2.0e7, 350.0), (8.0e7, 400.0))
    roundtrip_errors = []
    derivative_errors = []
    for pressure, temperature in points:
        density = eos.density_pt(pressure, temperature)
        recovered = eos.pressure_rho_t(density, temperature)
        roundtrip_errors.append(abs(recovered-pressure)/pressure)
        speed = eos.isothermal_sound_speed_rho_t(density, temperature)
        delta = density*1.0e-5
        dp_drho = (eos.pressure_rho_t(density+delta, temperature)
                   - eos.pressure_rho_t(density-delta, temperature))/(2.0*delta)
        derivative_errors.append(abs(speed*speed-dp_drho)/dp_drho)

    liquid_rejected = False
    try:
        eos.density_pt(5.0e6, 20.0)
    except ValueError:
        liquid_rejected = True
    mixture_rejected = False
    try:
        CoolPropIsothermalEOS("Hydrogen&Methane")
    except ValueError:
        mixture_rejected = True
    backend_rejected = False
    try:
        CoolPropIsothermalEOS("Hydrogen", backend="BICUBIC&HEOS")
    except ValueError:
        backend_rejected = True
    invalid_states_rejected = True
    for operation in (
        lambda: eos.density_pt(0.0, 300.0),
        lambda: eos.pressure_rho_t(-1.0, 300.0),
        lambda: eos.isothermal_sound_speed_rho_t(1.0, 0.0),
    ):
        try:
            operation()
        except ValueError:
            continue
        invalid_states_rejected = False
    assert max(roundtrip_errors) <= 1.0e-8
    assert max(derivative_errors) <= 2.0e-5
    assert liquid_rejected and mixture_rejected and backend_rejected and invalid_states_rejected
    return ValidationOutcome(True, {
        "coolprop_identity": eos.identity,
        "states": len(points),
        "maximum_pressure_density_roundtrip_relative_error": max(roundtrip_errors),
        "maximum_isothermal_derivative_relative_error": max(derivative_errors),
        "liquid_rejected": liquid_rejected,
        "unresolved_mixture_rejected": mixture_rejected,
        "non_heos_backend_rejected": backend_rejected,
        "nonpositive_state_inputs_rejected": invalid_states_rejected,
    }, (
        "Provider contract only; the centered finite difference is a numerical check, not a new acoustic model.",
        "These states check the closure implementation and phase guards, not a pipeline or facility.",
    ))
