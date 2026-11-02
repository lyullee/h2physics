"""Deferred native finite mixture separation ledger contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(identifier="mixture-equilibrium-finite-separation", profile="gas-composition",
        entrypoint=__name__+":validate_contract", parameters={}, invariants=(
            "native equilibrium phase keyed enthalpies used at common VLE composition",
            "finite component mass and total enthalpy ledgers satisfy explicit budgets",
            "pressure increase and missing equilibrium evidence rejected",
            "a cloned separation receipt cannot reseal altered residual summaries")),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.adapters.mixture_flash_separator import separate_equilibrium_mixture
    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties

    properties = CoolPropMixtureProperties(GasComposition("authored-separator-H2-N2",
        ("H2", "N2"), (.5, .5), (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"})
    upstream = properties.state_pq(6e6, .5)
    kwargs = dict(total_mass_kg=.01, downstream_pressure_pa=5e6, quality_bounds=(.001, .999),
        component_mole_balance_tolerance=1e-7, component_mass_absolute_tolerance_kg=1e-8,
        enthalpy_absolute_tolerance_j=.01, inverse_enthalpy_absolute_tolerance_j_kg=1e-4,
        quality_absolute_tolerance=1e-10, branch_evidence_id="authored-native-PQ-branch",
        equilibrium_throttle_evidence_id="authored-equilibrium-assumption",
        negligible_kinetic_potential_evidence_id="authored-negligible-mechanical-energy")
    result = separate_equilibrium_mixture(properties, upstream, **kwargs)
    assert max(abs(value) for value in result.component_mass_residuals_kg) <= 1e-8
    assert abs(result.total_enthalpy_residual_j) <= .01
    assert result.amounts.partition is result.inverse.partition
    try:
        replace(result, total_enthalpy_residual_j=result.total_enthalpy_residual_j + 1.)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Cloned separation receipt resealed a changed enthalpy residual")
    try:
        separate_equilibrium_mixture(properties,
            replace(upstream, enthalpy_j_kg=upstream.enthalpy_j_kg+1e4), **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError("Edited typed upstream enthalpy bypassed native state reconstruction")
    for changes in ({"downstream_pressure_pa": 7e6}, {"equilibrium_throttle_evidence_id": ""}):
        try:
            separate_equilibrium_mixture(properties, upstream, **dict(kwargs, **changes))
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported compression or implicit equilibrium was admitted")
    return ValidationOutcome(True, {"enthalpy_residual_j": result.total_enthalpy_residual_j},
        ("Native equilibrium reference only; no mechanical separator or measured VLE validation",))
