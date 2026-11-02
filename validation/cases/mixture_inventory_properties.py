"""Deferred explicit inventory-provider facade contract."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(identifier="mixture-bounded-inventory-provider", profile="gas-composition",
        entrypoint=__name__+":validate_contract", parameters={}, invariants=(
            "explicit wrapper preserves original composition and property basis",
            "finite inventory rho-U call uses existing bounded inverse",
            "only most recent successful inverse retained and stale success cleared on failure",
            "native PU remains explicitly unsupported")),)


def validate_contract(*, work_directory, **parameters):
    from h2physics.mixtures import GasComposition
    from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
    from h2physics.thermo.mixture_inventory_properties import BoundedMixtureInventoryProperties

    provider = CoolPropMixtureProperties(GasComposition("authored-inventory-facade",
        ("H2", "N2"), (.5, .5), (2.01588e-3, 28.0134e-3)),
        fluid_names={"H2": "Hydrogen", "N2": "Nitrogen"}, inverse_temperature_bounds_k=(280., 320.))
    wrapper = BoundedMixtureInventoryProperties(provider, (4.9e6, 5.1e6),
        "authored-single-gas-branch", 1e-7, 1e-3, .001)
    reference = provider.state_pt(5e6, 300.)
    assert wrapper.provider is provider and wrapper.basis is provider.basis
    assert wrapper.state_pt(5e6, 300.) == reference
    state = wrapper.state_rho_u(reference.density_kg_m3, reference.internal_energy_j_kg)
    assert wrapper.last_inverse.state is state
    assert abs(state.temperature_k-reference.temperature_k) < 1e-5
    assert wrapper.composition_id == provider.composition_id
    assert wrapper.species == provider.species
    assert wrapper.mole_fractions == provider.mole_fractions
    assert wrapper.molar_masses_kg_mol == provider.molar_masses_kg_mol
    from h2physics.adapters.finite_adsorption_vessel import FrozenGasBinding
    bound = FrozenGasBinding.bind(wrapper, species=provider.species,
        mole_fractions=provider.mole_fractions,
        molar_masses_kg_mol=provider.molar_masses_kg_mol,
        composition_id=provider.composition_id)
    assert bound.provider is wrapper
    # Actual native low-level state conversion, not a fabricated state factory.
    # This tests only the rho-U consuming seam, not a tank transient or saturation.
    from lh2dt.properties import ThermoState as NativeState

    from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
    native_provider = Lh2dtLowLevelProperties(wrapper, state_factory=NativeState)
    native_state = native_provider.from_rho_u(reference.density_kg_m3, reference.internal_energy_j_kg)
    assert native_state.quality is None
    assert abs(native_state.temperature_K-reference.temperature_k) < 1e-5
    try:
        wrapper.state_rho_u(-1., reference.internal_energy_j_kg)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid inventory density entered native inverse")
    assert wrapper.last_inverse is None
    try:
        wrapper.state_pu(5e6, reference.internal_energy_j_kg)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Inventory facade invented a PU flash")
    return ValidationOutcome(True, {"bounded_pressure_pa": state.pressure_pa},
        ("Provider-composition contract only; native finite inventory transient remains unverified",))
