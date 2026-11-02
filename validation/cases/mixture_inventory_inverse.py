"""Deferred bounded fixed-density native gas inverse contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(identifier="mixture-bounded-density-energy-inverse", profile="gas-composition",
        entrypoint=__name__+":validate_contract", parameters={}, invariants=(
            "nested native PT/P-density inverse retains declared gas branch",
            "sampled strict energy monotonicity and explicit pressure bracket",
            "density and internal energy residuals satisfy caller budgets",
            "direct construction and dataclass replacement cannot forge or clone the native inverse receipt",
            "default unsupported rho-U entrypoint remains unchanged")),)


def validate_contract(*, work_directory, **parameters):
    from dataclasses import replace

    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
    from h2physics.thermo.mixture_inventory_inverse import MixtureInventoryInverse

    provider = CoolPropMixtureProperties(GasComposition("authored-H2-N2-inventory",
        ("H2", "N2"), (.5, .5), (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"},
        inverse_temperature_bounds_k=(280., 320.))
    reference = provider.state_pt(5e6, 300.)
    result = provider.state_rho_u_bounded(reference.density_kg_m3, reference.internal_energy_j_kg,
        pressure_bounds_pa=(4.9e6, 5.1e6), branch_evidence_id="authored-single-gas-branch",
        density_absolute_tolerance_kg_m3=1e-7, internal_energy_absolute_tolerance_j_kg=1e-3,
        pressure_absolute_tolerance_pa=.001)
    assert result.state is result.evaluations[-1] and result.native_root.converged
    assert abs(result.density_residual_kg_m3) <= 1e-7
    assert abs(result.internal_energy_residual_j_kg) <= 1e-3
    assert abs(result.state.temperature_k-reference.temperature_k) < 1e-5
    assert abs(result.state.pressure_pa-reference.pressure_pa) < 1.
    values = {
        name: getattr(result, name)
        for name in MixtureInventoryInverse.__dataclass_fields__
        if not name.startswith("_")
    }
    for construct in (
        lambda: MixtureInventoryInverse(**values),
        lambda: replace(result, branch_evidence_id="forged-branch"),
    ):
        try:
            construct()
        except TypeError:
            pass
        else:
            raise AssertionError("A caller-forged or cloned native inverse receipt was accepted")
    try:
        provider.state_rho_u(reference.density_kg_m3, reference.internal_energy_j_kg)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Default mixture rho-U operation silently selected a branch")
    return ValidationOutcome(True, {"density_residual_kg_m3": result.density_residual_kg_m3,
        "internal_energy_residual_j_kg": result.internal_energy_residual_j_kg},
        ("Sampled branch admission only; not a global inverse uniqueness or experimental EOS validation",))
