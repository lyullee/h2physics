"""Retain mixture property references and native definition ownership."""

from dataclasses import replace

import pytest

from h2physics.mixtures import GasComposition
from h2physics.thermo.coolprop_mixture import CoolPropMixtureProperties
from h2physics.thermo.isothermal_eos import CoolPropMixtureIsothermalEOS


def _provider():
    return CoolPropMixtureProperties(GasComposition(
        "isothermal-identity-H2-N2", ("Hydrogen", "Nitrogen"),
        (.1, .9), (.00201588, .0280134),
    ))


def test_mixture_identity_retains_existing_reference_and_unresolved_spin():
    properties = _provider()
    eos = CoolPropMixtureIsothermalEOS(properties)
    assert properties.basis.reference_id in eos.identity
    assert properties.basis.fluid in eos.identity
    assert properties.basis.spin_composition == "mixture-H2-spin-unresolved"
    assert properties.basis.spin_composition in eos.identity
    assert eos.density_pt(5.e6, 300.) > 0.
    with pytest.raises(AttributeError, match="immutable"):
        eos.properties = _provider()


@pytest.mark.parametrize("attribute", ["_basis", "_state", "state_pt", "mole_fractions"])
def test_native_mixture_definition_changes_reject_and_restore(attribute):
    properties = _provider()
    eos = CoolPropMixtureIsothermalEOS(properties)
    original = getattr(properties, attribute)
    replacements = {
        "_basis": replace(properties.basis, reference_id=properties.basis.reference_id+":changed"),
        "_state": _provider()._state,
        "state_pt": lambda p, t: None,
        "mole_fractions": (.2, .8),
    }
    try:
        object.__setattr__(properties, attribute, replacements[attribute])
        with pytest.raises(ValueError, match="definition changed"):
            eos.density_pt(5.e6, 300.)
    finally:
        object.__setattr__(properties, attribute, original)
    assert eos.density_pt(5.e6, 300.) > 0.


@pytest.mark.parametrize("attribute", ["reference_id", "spin_composition"])
def test_nested_property_basis_values_are_snapshotted(attribute):
    properties = _provider()
    eos = CoolPropMixtureIsothermalEOS(properties)
    basis = properties.basis
    original = getattr(basis, attribute)
    try:
        object.__setattr__(basis, attribute, original+":changed")
        with pytest.raises(ValueError, match="definition changed"):
            eos.density_pt(5.e6, 300.)
    finally:
        object.__setattr__(basis, attribute, original)
    assert eos.density_pt(5.e6, 300.) > 0.


def test_native_molar_mass_restores_captured_composition_after_state_drift():
    properties = _provider()
    expected = properties.molar_mass_kg_mol
    with properties._lock:
        properties._state.set_mole_fractions([.9, .1])
        assert properties._state.molar_mass() != expected
    assert properties.molar_mass_kg_mol == expected
    assert tuple(properties._state.get_mole_fractions()) == properties.mole_fractions


@pytest.mark.parametrize("pressure,temperature", [(1.e5, 300.), (5.e6, 300.), (7.e6, 330.)])
def test_native_eos_reads_match_full_provider_without_phase_imposition(pressure, temperature):
    properties = _provider()
    eos = CoolPropMixtureIsothermalEOS(properties)
    expected = properties.state_pt(pressure, temperature)
    density = eos.density_pt(pressure, temperature)
    assert density == pytest.approx(expected.density_kg_m3, rel=1.e-12)
    assert eos.pressure_rho_t(density, temperature) == pytest.approx(pressure, rel=1.e-10)
    speed = eos.isothermal_sound_speed_rho_t(density, temperature)
    reference = properties.isothermal_sound_speed_rho_t(density, temperature)
    assert speed == pytest.approx(reference, rel=1.e-12)


def test_native_eos_path_preserves_liquid_rejection():
    eos = CoolPropMixtureIsothermalEOS(_provider())
    with pytest.raises(ValueError):
        eos.density_pt(1.e5, 20.)
