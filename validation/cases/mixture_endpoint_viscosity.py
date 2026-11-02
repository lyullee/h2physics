"""Deferred native endpoint-viscosity contract for fixed-composition mixtures."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mixture-saturation-endpoint-viscosity",
        profile="gas-composition",
        entrypoint=__name__ + ":validate_contract",
        parameters={},
        invariants=(
            "liquid and vapor endpoint viscosity use explicit native mole-quality identity",
            "endpoint values match direct CoolProp saturated-phase keyed outputs",
            "interior two-phase quality is rejected without a transport closure",
        ),
    ),)


def validate_contract(*, work_directory, **parameters):
    del work_directory, parameters
    from CoolProp import AbstractState
    from CoolProp import CoolProp as CP

    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties

    composition = GasComposition("endpoint-viscosity-H2-N2", ("H2", "N2"),
                                 (.5, .5), (2.01588e-3, 28.0134e-3))
    provider = CoolPropMixtureProperties(
        composition, fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    reference = AbstractState("HEOS", "Hydrogen&Nitrogen")
    reference.set_mole_fractions(list(composition.mole_fractions))
    errors = []
    for quality, phase_method in (
        (0., "saturated_liquid_keyed_output"),
        (1., "saturated_vapor_keyed_output"),
    ):
        pressure = 5e6
        observed = provider.saturated_phase_viscosity_pq(pressure, quality)
        reference.update(CP.PQ_INPUTS, pressure, quality)
        expected = getattr(reference, phase_method)(CP.iviscosity)
        errors.append(abs(observed-expected))
        assert observed > 0.
    try:
        provider.saturated_phase_viscosity_pq(5e6, .5)
    except ValueError:
        interior_rejected = True
    else:
        raise AssertionError("Interior two-phase viscosity was admitted without a closure")
    assert max(errors) <= 1e-12
    return ValidationOutcome(
        True,
        {"maximum_endpoint_error_pa_s": max(errors),
         "interior_quality_rejected": interior_rejected},
        ("Direct same-release CoolProp comparison only; no independent transport data",),
    )
