from dataclasses import replace

import numpy as np
import pytest
from scipy.integrate import quad

from h2physics.core import Origin
from h2physics.photochemistry import (
    BeerLambertPath,
    PhotoAdmissibilityError,
    PhotoConditions,
    PhotoInventoryError,
    PhotonSupply,
    PhotonYield,
    SteadyPhotoWindow,
    convert_photon_exposure,
    photon_hydrogen_rate,
)
from h2physics.reactions import ChemicalSpecies, FunctionalMolarEnthalpy, StoichiometricReaction

HCNA = 6.62607015e-34*299792458*6.02214076e23
CONDITIONS = PhotoConditions("authored-catalyst", "authored-medium", .002, 300., 1e5,
                              "authored-beam-plane", "authored-uniform-batch")


def supply():
    return PhotonSupply.from_lines([400e-9, 600e-9], [1., 2.],
        geometry_id=CONDITIONS.geometry_id, source_id="authored-source")


def response(light, values=.3, basis="absorbed_electron_equivalents"):
    return PhotonYield.bind(light, values, basis=basis, conditions=CONDITIONS,
                            evidence_id="authored-prescribed-efficiency", origin=Origin.SYNTHETIC)


def path(light, alpha=100., depth=.01, reflection=0.):
    return BeerLambertPath.uniform(light, depth_m=depth, absorption_coefficient_m_inv=alpha,
                                   reflectance=reflection, evidence_id="authored-nonscattering-path")


def water_reaction():
    return StoichiometricReaction("authored-water-balance", (
        ChemicalSpecies("water", {"H": 2, "O": 1}, .018, "declared-liquid"),
        ChemicalSpecies("hydrogen", {"H": 2}, .002, "declared-gas"),
        ChemicalSpecies("oxygen", {"O": 2}, .032, "declared-gas")), (-2, 2, 1))


def test_discrete_lines_use_exact_photon_energy_and_explicit_si_amount():
    light = supply()
    np.testing.assert_allclose(light.incident_photons_mol_s,
        np.array([400e-9, 2*600e-9])/HCNA, rtol=2e-15)
    assert light.incident_photons_mol_s[1]/light.incident_photons_mol_s[0] == pytest.approx(3.)
    assert not light.incident_power_w.flags.writeable
    assert light.wavelength_edges_m is None


def test_finite_bands_exact_flat_density_integral_and_explicit_nanometre_adapter():
    light = PhotonSupply.from_nanometer_bands([300., 450., 700.], [1., .5],
        illuminated_area_m2=.02, geometry_id=CONDITIONS.geometry_id, source_id="authored-bands")
    for i, density in enumerate((1., .5)):
        lo, hi = light.wavelength_edges_m[i:i+2]
        oracle = quad(lambda wavelength: .02*density*1e9*wavelength/HCNA, lo, hi,
                      epsabs=1e-20, epsrel=1e-12)[0]
        assert light.incident_photons_mol_s[i] == pytest.approx(oracle, rel=1e-14)
    assert light.incident_power_w == pytest.approx([3., 2.5])
    si = PhotonSupply.from_bands([300e-9, 450e-9, 700e-9], [1e9, .5e9],
        illuminated_area_m2=.02, geometry_id=CONDITIONS.geometry_id, source_id="authored-bands")
    np.testing.assert_allclose(si.incident_photons_mol_s, light.incident_photons_mol_s, rtol=1e-15)


@pytest.mark.parametrize("alpha,reflection", [(0., 0.), (1e-10, .2), (100., .3), (1e6, 0.), (100., 1.)])
def test_optical_energy_and_photon_partition_including_transparent_thin_opaque_limits(alpha, reflection):
    light = supply()
    optics = path(light, alpha=alpha, reflection=reflection)
    rate = photon_hydrogen_rate(light, optics, response(light))
    assert np.max(abs(rate.energy_residual_w)) < 1e-15
    assert np.max(abs(rate.photon_residual_mol_s)) < 1e-20
    expected_a = (1-reflection)*(-np.expm1(-alpha*.01))
    np.testing.assert_allclose(rate.absorbed_power_w, light.incident_power_w*expected_a, rtol=1e-15)
    if alpha == 1e-10:
        assert optics.absorbed_fraction[0] == pytest.approx((1-reflection)*1e-12, rel=1e-12)
    if alpha == 0 or reflection == 1:
        assert rate.hydrogen_mol_s == 0.


def test_incident_aqy_is_not_attenuated_twice_and_electron_to_h2_factor_is_two():
    light = supply()
    optics = path(light, reflection=.1)
    intrinsic = photon_hydrogen_rate(light, optics, response(light, .4))
    apparent = photon_hydrogen_rate(light, optics, response(light,
        optics.absorbed_fraction*.4, "incident_electron_equivalents"))
    assert apparent.hydrogen_mol_s == pytest.approx(intrinsic.hydrogen_mol_s, rel=1e-15)
    assert intrinsic.hydrogen_mol_s == pytest.approx(
        np.sum(light.incident_photons_mol_s*optics.absorbed_fraction*.4)/2)
    assert intrinsic.specific_hydrogen_mol_kg_s == pytest.approx(intrinsic.hydrogen_mol_s/.002)


def test_per_band_photon_budget_cannot_be_hidden_by_a_second_band_or_diagnostic_result():
    light = supply()
    optics = path(light, alpha=np.array([-np.log(.9), -np.log(.1)])/.01)
    invalid = response(light, [.2, 0.], "incident_electron_equivalents")
    with pytest.raises(PhotoAdmissibilityError) as caught:
        photon_hydrogen_rate(light, optics, invalid)
    diagnostic = caught.value.result
    assert not diagnostic.photon_budget_admitted
    assert diagnostic.supply is light
    assert np.sum(diagnostic.productive_electrons_mol_s) < np.sum(diagnostic.absorbed_photons_mol_s)
    with pytest.raises(PhotoAdmissibilityError):
        convert_photon_exposure(diagnostic, SteadyPhotoWindow(100., 101., "clock", "authored"),
            reaction=water_reaction(), initial_mol={"water": 1.}, hydrogen_species_id="hydrogen")


def test_finite_batch_reuses_stoichiometry_and_explicit_isothermal_energy_requirement():
    light = supply()
    rate = photon_hydrogen_rate(light, path(light), response(light))
    reaction = water_reaction()
    enthalpy = FunctionalMolarEnthalpy(reaction.species,
        (lambda t,p: -10000., lambda t,p: 0., lambda t,p: 0.),
        "authored-formation-energy-zero", (200., 500.), (1e4, 1e6))
    window = SteadyPhotoWindow(100., 110., "absolute-clock", "authored-steady-illumination")
    result = convert_photon_exposure(rate, window, reaction=reaction,
        initial_mol={"water": .1}, hydrogen_species_id="hydrogen", enthalpy=enthalpy)
    expected_h2 = rate.hydrogen_mol_s*10
    assert result.conversion.final_amounts["hydrogen"] == pytest.approx(expected_h2)
    assert result.conversion.final_amounts["oxygen"] == pytest.approx(expected_h2/2)
    assert result.conversion.final_amounts["water"] == pytest.approx(.1-expected_h2)
    assert abs(result.conversion.mass_residual_kg) < 1e-18
    assert result.reaction_enthalpy_change_j == pytest.approx(expected_h2*10000.)
    assert result.required_isothermal_heat_j == pytest.approx(
        expected_h2*10000.-np.sum(rate.absorbed_power_w)*10)
    assert result.energy_basis_id == enthalpy.basis_id


def test_reactant_exhaustion_retains_requested_photon_budget_without_capping_or_stopping_light():
    light = supply()
    rate = photon_hydrogen_rate(light, path(light), response(light))
    window = SteadyPhotoWindow(100., 1000., "clock", "authored")
    with pytest.raises(PhotoInventoryError) as caught:
        convert_photon_exposure(rate, window, reaction=water_reaction(),
            initial_mol={"water": 1e-12}, hydrogen_species_id="hydrogen")
    assert caught.value.rate is rate and caught.value.window is window
    assert caught.value.demanded_extent_mol > 1e-12
    assert isinstance(caught.value.__cause__, ValueError)


def test_missing_thermochemistry_does_not_invent_heat_or_solar_to_hydrogen_efficiency():
    light = supply()
    rate = photon_hydrogen_rate(light, path(light), response(light))
    result = convert_photon_exposure(rate, SteadyPhotoWindow(0., 1., "clock", "authored"),
        reaction=water_reaction(), initial_mol={"water": .1}, hydrogen_species_id="hydrogen")
    assert result.reaction_enthalpy_change_j is None
    assert result.required_isothermal_heat_j is None
    assert not hasattr(result, "solar_to_hydrogen_efficiency")


def test_exact_input_reference_geometry_and_result_integrity_guards():
    light = supply()
    optics, efficiency = path(light), response(light)
    with pytest.raises(ValueError, match="different optical input"):
        photon_hydrogen_rate(replace(light, source_id="other"), optics, efficiency)
    with pytest.raises(ValueError, match="geometry"):
        photon_hydrogen_rate(light, replace(optics, geometry_id="other"), efficiency)
    good = photon_hydrogen_rate(light, optics, efficiency)
    with pytest.raises(ValueError, match="does not match"):
        replace(good, productive_electrons_mol_s=np.zeros(2))
    with pytest.raises(ValueError, match="axes"):
        replace(good, reflected_power_w=np.zeros(3))


def test_optical_coefficients_cannot_move_to_another_wavelength_grid_or_representation():
    old = supply()
    optics = path(old)
    shifted = PhotonSupply.from_lines([800e-9, 1000e-9], [1., 2.],
        geometry_id=CONDITIONS.geometry_id, source_id="authored-shifted-spectrum")
    with pytest.raises(ValueError, match="spectral grid/representation"):
        photon_hydrogen_rate(shifted, optics, response(shifted))
    bands = PhotonSupply.from_bands([300e-9, 500e-9, 700e-9], [1e9, 2e9],
        illuminated_area_m2=.005, geometry_id=CONDITIONS.geometry_id, source_id="authored-bands")
    np.testing.assert_allclose(bands.representative_wavelength_m, old.representative_wavelength_m)
    with pytest.raises(ValueError, match="spectral grid/representation"):
        photon_hydrogen_rate(bands, optics, response(bands))
    with pytest.raises(ValueError, match="wavelength grid"):
        replace(optics, spectral_grid_sha256="")


def test_power_change_can_reuse_linear_optics_but_requires_rebound_yield_evidence():
    old = supply()
    optics = path(old)
    new = PhotonSupply.from_lines(old.representative_wavelength_m, old.incident_power_w*2,
        geometry_id=CONDITIONS.geometry_id, source_id="authored-doubled-light")
    assert old.spectral_grid_sha256 == new.spectral_grid_sha256
    before = photon_hydrogen_rate(old, optics, response(old))
    after = photon_hydrogen_rate(new, optics, response(new))
    assert after.hydrogen_mol_s == pytest.approx(2*before.hydrogen_mol_s)


@pytest.mark.parametrize("kind", ["negative_power", "decreasing_edges", "boolean_edges", "complex_edges",
    "negative_absorption", "bad_reflectance", "negative_depth", "bad_yield", "unknown_yield_basis",
    "unresolved_yield", "empty_evidence", "reversed_window"])
def test_invalid_physical_inputs_are_not_repaired(kind):
    light = supply()
    with pytest.raises(ValueError):
        if kind == "negative_power":
            PhotonSupply.from_lines([400e-9], [-1.], geometry_id="g", source_id="s")
        elif kind in {"decreasing_edges", "boolean_edges", "complex_edges"}:
            edges = {"decreasing_edges": [500e-9, 400e-9], "boolean_edges": [True, False],
                     "complex_edges": [300e-9+1j, 500e-9+1j]}[kind]
            PhotonSupply.from_bands(edges, [1.], illuminated_area_m2=1., geometry_id="g", source_id="s")
        elif kind == "negative_absorption":
            path(light, alpha=-1.)
        elif kind == "bad_reflectance":
            path(light, reflection=1.01)
        elif kind == "negative_depth":
            path(light, depth=-1.)
        elif kind == "bad_yield":
            response(light, 30.)
        elif kind == "unknown_yield_basis":
            response(light, .3, "unknown")
        elif kind == "unresolved_yield":
            replace(response(light), origin=Origin.UNRESOLVED)
        elif kind == "empty_evidence":
            replace(response(light), evidence_id="")
        elif kind == "reversed_window":
            SteadyPhotoWindow(1., 0., "clock", "authored")


def test_actual_native_gas_thermochemistry_energy_uses_shared_caloric_adapter():
    import hashlib
    from pathlib import Path

    ct = pytest.importorskip("cantera")
    from h2physics.adapters.cantera import MechanismBasis
    from h2physics.adapters.cantera_thermo import CanteraMolarEnthalpy

    source = (Path(ct.__file__).parent/"data/gri30.yaml").read_bytes()
    basis = MechanismBasis("authored-native-photo-energy", hashlib.sha256(source).hexdigest(),
        "Cantera-BSD-3-Clause; upstream GRI-Mech provenance", ("https://cantera.org",),
        200., 1500., 1e4, 1e6)
    caloric = CanteraMolarEnthalpy(lambda: ct.Solution(yaml=source.decode()), basis,
                                 ("H2O", "H2", "O2"))
    reaction = StoichiometricReaction("authored-gas-water-photoconversion", caloric.species, (-2, 2, 1))
    light = supply()
    rate = photon_hydrogen_rate(light, path(light), response(light))
    converted = convert_photon_exposure(rate, SteadyPhotoWindow(0., 10., "clock", "authored"),
        reaction=reaction, initial_mol={"H2O": .1}, hydrogen_species_id="H2", enthalpy=caloric)
    native = ct.Solution(yaml=source.decode())
    native.TPX = 300., 1e5, {"H2O": .1}
    before = .1*native.enthalpy_mole/1000
    native.TPX = 300., 1e5, dict(converted.conversion.final_amounts)
    after = sum(converted.conversion.final_mol)*native.enthalpy_mole/1000
    assert converted.reaction_enthalpy_change_j == pytest.approx(after-before, abs=1e-11)
