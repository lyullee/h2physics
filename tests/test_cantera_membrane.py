"""Original porous-gas probes against actual native Cantera and analytic limits."""

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_membrane import (
    FLUX_FRAME,
    CanteraDustyGasTransport,
    MembraneEndpoint,
    MembraneTransportError,
    MembraneTransportEvidence,
    PorousTransportGeometry,
)
from h2physics.core import Origin

ct = pytest.importorskip("cantera")
RAW = (Path(ct.__file__).parent/"data/h2o2.yaml").read_bytes()
SPECIES = ("H2", "N2", "AR")


def gas():
    # Retain native species/transport data without path lookup or bundled inputs.
    by_name = {s.name: s for s in ct.Species.list_from_yaml(RAW.decode(), section="species")}
    return ct.Solution(thermo="ideal-gas", species=[by_name[n] for n in SPECIES],
                       transport_model="multicomponent")


def geometry(**kwargs):
    return PorousTransportGeometry(**(dict(porosity=.35, tortuosity=2.5,
        mean_pore_radius_m=50e-9, permeability_m2=0., thickness_m=.001,
        geometry_id="authored-porous-plane", evidence_id="authored-no-material-validation",
        origin=Origin.SYNTHETIC) | kwargs))


def endpoint(boundary="left", fractions=(.7, .2, .1), **kwargs):
    return MembraneEndpoint(**(dict(temperature_k=330., pressure_pa_absolute=101325.,
        species=SPECIES, fractions=fractions, composition_basis="mole", boundary_id=boundary,
        phase_id="native-warm-ideal-gas", geometry_id="authored-porous-plane",
        source_id="authored-operating-state", origin=Origin.SYNTHETIC) | kwargs))


def model(factory=gas):
    basis = MechanismBasis("installed-h2o2-authored-H2-N2-Ar-selection", hashlib.sha256(RAW).hexdigest(),
        "Cantera-BSD-3-Clause; upstream GRI-Mech thermo/transport provenance",
        ("https://cantera.org/3.2/python/transport.html",), 300., 1000., .001, 2e5)
    evidence = MembraneTransportEvidence("installed-h2o2-gri30-transport-data",
        "native-warm-ideal-gas", "authored-neutral-ideal-gas-no-condensation",
        "native-NASA-formation-reference", "native-mechanism-H2-spin-unresolved")
    return CanteraDustyGasTransport(factory, basis, evidence=evidence)


def solve(engine=None, **changes):
    return (engine or model()).flux(endpoint(), endpoint("right", (.4, .5, .1)), geometry(**changes))


def test_actual_native_units_multicomponent_countertransport_and_complete_identity():
    result = solve()
    assert isinstance(result.native_dusty_gas, ct.DustyGas)
    assert result.native_dusty_gas.transport_model == "DustyGas"
    assert result.species == SPECIES and result.frame == FLUX_FRAME
    assert result.molar_flux_mol_m2_s[0] > 0 > result.molar_flux_mol_m2_s[1]
    assert result.molar_flux_mol_m2_s[2] != 0  # Constant Ar mole fraction is coupled.
    assert abs(result.molar_flux_mol_m2_s.sum()) > .01  # Not zero-sum relative flux.
    np.testing.assert_array_equal(result.molar_flux_mol_m2_s, result.native_flux_kmol_m2_s*1000.)
    np.testing.assert_array_equal(result.mass_flux_kg_m2_s,
                                 result.molar_flux_mol_m2_s*result.molecular_weights_kg_mol)
    assert not result.native_flux_kmol_m2_s.flags.writeable
    assert len(result.input_sha256) == 64 and len(result.phase_copy_audits) == 2
    assert max(a.maximum_relative_roundtrip for a in result.transport_copy_audits) < 2e-13
    assert result.evidence.energy_reference_id == "native-NASA-formation-reference"
    np.testing.assert_allclose(result.left_state.partial_molar_enthalpies_j_mol,
                              result.owned_endpoint_phases[0].partial_molar_enthalpies/1000.)
    assert "unresolved" in result.thermal_closure
    assert not hasattr(result, "recovery") and not hasattr(result, "product_purity")


def test_same_state_zero_reverse_and_inverse_thickness_without_clipping():
    engine = model()
    left, right, pore = endpoint(), endpoint("right", (.4, .5, .1)), geometry()
    zero = engine.flux(left, replace(left, boundary_id="right"), pore)
    assert np.all(zero.native_flux_kmol_m2_s == 0)
    forward = engine.flux(left, right, pore)
    reverse = engine.flux(right, left, pore)
    doubled = engine.flux(left, right, replace(pore, thickness_m=.002))
    np.testing.assert_allclose(reverse.molar_flux_mol_m2_s, -forward.molar_flux_mol_m2_s, rtol=1e-13)
    np.testing.assert_allclose(doubled.molar_flux_mol_m2_s, forward.molar_flux_mol_m2_s/2, rtol=1e-13)
    assert forward.input_sha256 != reverse.input_sha256 != doubled.input_sha256


def test_numpy_scalars_are_physical_numbers_in_endpoint_geometry_and_basis_fingerprints():
    engine = model()
    basis = replace(engine.mechanism_basis, minimum_temperature_k=np.int64(300),
                    maximum_pressure_pa=np.int64(200000))
    engine = CanteraDustyGasTransport(gas, basis, evidence=engine.evidence)
    left = endpoint(temperature_k=np.int64(330), pressure_pa_absolute=np.int64(101325))
    right = endpoint("right", (.4, .5, .1), temperature_k=np.float64(330))
    pore = geometry(porosity=np.float64(.35), tortuosity=np.float64(2.5), permeability_m2=np.int64(0))
    result = engine.flux(left, right, pore)
    assert left.content_sha256 == endpoint().content_sha256
    assert isinstance(pore.permeability_m2, float)
    np.testing.assert_array_equal(result.molar_flux_mol_m2_s, solve().molar_flux_mol_m2_s)


def test_physical_pore_low_pressure_knudsen_limit_and_porosity_tortuosity_convention():
    engine, pore = model(), geometry()
    errors = []
    for pressure in (1e5, 1e3, 1., .01):
        left = endpoint(pressure_pa_absolute=pressure)
        right = endpoint("right", (.4, .5, .1), pressure_pa_absolute=pressure)
        result = engine.flux(left, right, pore)
        mass = result.molecular_weights_kg_mol
        effective = (2/3)*pore.mean_pore_radius_m*pore.porosity/pore.tortuosity*np.sqrt(
            8*(ct.gas_constant/1000.)*left.temperature_k/(np.pi*mass))
        concentrations = [p.density_kg_m3*p.mass_fractions/mass
                          for p in (result.left_state, result.right_state)]
        oracle = -effective*(concentrations[1]-concentrations[0])/pore.thickness_m
        errors.append(np.max(abs(result.molar_flux_mol_m2_s-oracle))/np.max(abs(oracle)))
    assert all(b < a for a, b in zip(errors, errors[1:], strict=False))
    assert errors[-1] < 1e-6  # Fixed 50nm pore; mathematical dilute-gas limit.
    reference = solve(engine)
    half = solve(engine, porosity=.175)
    twice = solve(engine, tortuosity=5.)
    np.testing.assert_allclose(half.molar_flux_mol_m2_s, reference.molar_flux_mol_m2_s/2, rtol=1e-13)
    np.testing.assert_allclose(twice.molar_flux_mol_m2_s, reference.molar_flux_mol_m2_s/2, rtol=1e-13)


def test_native_pressure_driven_darcy_addition_uses_actual_gas_viscosity():
    engine = model()
    left = endpoint(fractions=(.6, .3, .1), pressure_pa_absolute=105000.)
    right = endpoint("right", (.6, .3, .1), pressure_pa_absolute=95000.)
    zero = engine.flux(left, right, geometry())
    permeable = engine.flux(left, right, geometry(permeability_m2=5e-17))
    mean = gas()
    mean.TPX = 330., 100000., [.6, .3, .1]
    oracle = -mean.concentrations*1000.*5e-17/mean.viscosity*(95000.-105000.)/.001
    np.testing.assert_allclose(permeable.molar_flux_mol_m2_s-zero.molar_flux_mol_m2_s,
                               oracle, rtol=1e-10, atol=1e-16)
    assert np.all(permeable.molar_flux_mol_m2_s > 0)


def test_mass_basis_and_native_molar_reporting_basis_do_not_change_si_density_or_flux():
    source = gas()
    source.basis = "molar"
    source.TPX = 330., 101325., [.7, .2, .1]
    left = endpoint(fractions=source.Y, composition_basis="mass")
    source.TPX = 330., 101325., [.4, .5, .1]
    right = endpoint("right", source.Y, composition_basis="mass")
    result = model(lambda: source).flux(left, right, geometry())
    np.testing.assert_allclose(result.molar_flux_mol_m2_s, solve().molar_flux_mol_m2_s, rtol=1e-12)
    assert result.left_state.density_kg_m3 == pytest.approx(result.owned_endpoint_phases[0].density_mass)
    assert source.basis == "molar" and result.left.composition_basis == "mass"


def test_shared_source_state_is_private_and_returned_native_mutation_is_not_reused():
    shared = gas()
    shared.TPX = 360., 1.1e5, [.1, .2, .7]
    before = shared.state.copy()
    engine = model(lambda: shared)
    first = solve(engine)
    np.testing.assert_array_equal(shared.state, before)
    assert first.source_phase is shared
    assert first.owned_endpoint_phases[0] is not shared
    assert first.owned_endpoint_phases[0] is not first.owned_endpoint_phases[1]
    first.native_dusty_gas.permeability = 1e-10
    first.native_dusty_gas.mean_pore_radius = 1e-4
    first.owned_endpoint_phases[0].TP = 700., 2e5
    second = solve(engine)
    assert first.native_dusty_gas is not second.native_dusty_gas
    np.testing.assert_array_equal(first.molar_flux_mol_m2_s, second.molar_flux_mol_m2_s)
    np.testing.assert_array_equal(shared.state, before)


def test_runtime_binary_and_viscosity_fit_changes_are_rejected_not_silently_regenerated():
    for parameter in ("binary", "viscosity"):
        shared = gas()
        if parameter == "binary":
            fit = shared.get_binary_diff_coeffs_polynomial(0, 1)
            shared.set_binary_diff_coeffs_polynomial(0, 1, fit*1.01)
        else:
            fit = shared.get_viscosity_polynomial(0)
            shared.set_viscosity_polynomial(0, fit*1.01)
        with pytest.raises(MembraneTransportError, match="runtime-modified") as caught:
            solve(model(lambda: shared))
        assert caught.value.source_phase is shared
        assert caught.value.owned_endpoint_phases and caught.value.__cause__ is not None


def test_changed_native_definition_needs_rebound_evidence_and_result_units_are_guarded():
    shared = gas()
    engine = model(lambda: shared)
    first = solve(engine)
    species = shared.species(0)
    species.transport.diameter *= 1.01
    shared.modify_species(0, species)
    with pytest.raises(MembraneTransportError, match="definition changed"):
        solve(engine)
    with pytest.raises(ValueError, match="Flux units"):
        replace(first, molar_flux_mol_m2_s=first.native_flux_kmol_m2_s)
    with pytest.raises(ValueError, match="input fingerprint"):
        replace(first, geometry=replace(first.geometry, permeability_m2=1e-12))


@pytest.mark.parametrize("change", [dict(porosity=0.), dict(porosity=1.), dict(tortuosity=.9),
    dict(mean_pore_radius_m=0.), dict(permeability_m2=-1.), dict(thickness_m=0.),
    dict(thickness_m=-1.), dict(porosity=True), dict(origin=Origin.UNRESOLVED)])
def test_bad_pore_geometry_never_reaches_unchecked_native_setters(change):
    with pytest.raises(ValueError):
        geometry(**change)


@pytest.mark.parametrize("change", [dict(fractions=[.2, .2, .2]), dict(fractions=[1.1, -.1, 0.]),
    dict(fractions=[True, False, False]), dict(fractions=[True, 0., 0.]), dict(fractions=[.7+.1j, .2, .1]),
    dict(fractions=[np.nan, .2, .1]), dict(composition_basis="volume-unknown"),
    dict(species=("H2", "H2", "AR")), dict(origin=Origin.UNRESOLVED)])
def test_endpoint_normalization_basis_and_raw_values_are_not_repaired(change):
    with pytest.raises(ValueError):
        endpoint(**change)


@pytest.mark.parametrize("change", [dict(temperature_k=331.), dict(geometry_id="other"),
    dict(phase_id="liquid"), dict(boundary_id="left"), dict(pressure_pa_absolute=3e5),
    dict(temperature_k=250.)])
def test_endpoint_phase_geometry_temperature_pressure_identity_gates(change):
    with pytest.raises(ValueError):
        model().flux(endpoint(), endpoint("right", (.4, .5, .1), **change), geometry())


def test_wrong_native_species_transport_charges_or_reactions_are_not_substituted():
    with pytest.raises(MembraneTransportError, match="species order"):
        model().flux(endpoint(species=("N2", "H2", "AR")), endpoint("right"), geometry())
    wrong = gas()
    wrong.transport_model = "mixture-averaged"
    with pytest.raises(MembraneTransportError, match="multicomponent"):
        solve(model(lambda: wrong))
    reactive = ct.Solution(yaml=RAW.decode(), name="ohmech", transport_model="multicomponent")
    with pytest.raises(MembraneTransportError, match="frozen"):
        solve(model(lambda: reactive))


def test_native_numerical_failure_retains_objects_raw_diagnostics_and_cause():
    with pytest.raises(MembraneTransportError) as caught:
        solve(mean_pore_radius_m=np.nextafter(0., 1.))
    failure = caught.value
    assert failure.source_phase is not None
    assert len(failure.owned_endpoint_phases) == 2
    assert isinstance(failure.native_dusty_gas, ct.DustyGas)
    assert failure.__cause__ is not None
    assert failure.native_state is not None and not failure.native_state.flags.writeable
    assert len(failure.owned_native_states) == 2
    if failure.raw_native_flux is not None:
        assert not failure.raw_native_flux.flags.writeable
