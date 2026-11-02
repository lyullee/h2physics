"""Original analytic oracles and actual native mixture/nozzle integration."""

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.core import PropertyBasis, PropertyProvider
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening


def authored_phase():
    ct = pytest.importorskip("cantera")
    species = []
    # These arbitrary coefficients are authored numerical fixtures, not measured data.
    for name, atoms, limits, coefficients in (
        ("H2", {"H": 2}, (180, 3200), (300, 1.7e6, 8e4, 31000)),
        ("N2", {"N": 2}, (220, 2800), (300, -2.2e6, 1.25e5, 35000)),
        ("AR", {"Ar": 1}, (250, 600), (300, 0, 5e4, 24000)),
    ):
        item = ct.Species(name, atoms)
        item.thermo = ct.ConstantCp(*limits, 101325., coefficients)
        species.append(item)
    return ct.Solution(name="authored-constant-cp-gas", thermo="ideal-gas", kinetics=None,
                       species=species)


def authored_basis(**changes):
    basis = MechanismBasis("authored-frozen-constant-cp-v1",
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "Apache-2.0-authored-fixture",
        ("https://cantera.org/3.2/reference/thermo/species-thermo.html#constant-heat-capacity",),
        150, 3000, 1e4, 2e6)
    return replace(basis, **changes)


def authored_provider(**kwargs):
    return CanteraFrozenGasProperties(authored_phase(), authored_basis(),
                                     {"H2": .14, "N2": .86}, **kwargs)


def analytic(pressure, temperature, fractions=(.14, .86)):
    """Independent constant-cp ideal mixture algebra; molar units are J/kmol."""
    weights, cp, h0, s0 = (2.016, 28.014), (31000., 35000.), (1.7e6, -2.2e6), (8e4, 1.25e5)
    universal = 8314.46261815324
    amount = [y/w for y, w in zip(fractions, weights, strict=True)]
    total = math.fsum(amount)
    molar = [n/total for n in amount]
    specific_cp = math.fsum(n*c for n, c in zip(amount, cp, strict=True))
    gas_constant = universal*total
    enthalpy = math.fsum(n*(h+c*(temperature-300))
        for n, h, c in zip(amount, h0, cp, strict=True))
    entropy = math.fsum(n*(s+c*math.log(temperature/300)
                            - universal*math.log(x*pressure/101325))
        for n, s, c, x in zip(amount, s0, cp, molar, strict=True))
    return {"density_kg_m3": pressure/(gas_constant*temperature),
            "enthalpy_j_kg": enthalpy, "internal_energy_j_kg": enthalpy-gas_constant*temperature,
            "entropy_j_kg_k": entropy, "cp_j_kg_k": specific_cp,
            "cv_j_kg_k": specific_cp-gas_constant,
            "speed_of_sound_m_s": math.sqrt(specific_cp/(specific_cp-gas_constant)
                                             *gas_constant*temperature)}


@pytest.mark.parametrize("pressure,temperature", [(1e4, 220), (1e5, 700), (2e6, 2800)])
def test_actual_native_ideal_mixture_against_independent_caloric_and_entropy_algebra(pressure, temperature):
    provider = authored_provider()
    state = provider.state_pt(pressure, temperature)
    assert isinstance(provider, PropertyProvider)
    assert state.phase == "gas"
    assert state.vapor_mass_fraction == 1
    for name, expected in analytic(pressure, temperature).items():
        assert getattr(state, name) == pytest.approx(expected, rel=4e-14, abs=1e-8), name
    assert abs(state.enthalpy_identity_residual_j_kg) < 2e-9
    assert provider.minimum_temperature_k == 220
    assert provider.maximum_temperature_k == 2800  # Zero-fraction AR's 600 K bound is irrelevant.


def test_frozen_native_flashes_reset_composition_units_and_initial_state():
    provider = authored_provider()
    native = provider.native_phase
    reference = provider.state_pt(7e5, 1150)
    native.TPX = 400, 1.2e5, {"AR": 1}
    native.basis = "molar"
    by_h = provider.state_ph(reference.pressure_pa, reference.enthalpy_j_kg)
    native.TPY = 280, 1.5e5, {"N2": 1}
    native.basis = "molar"
    by_s = provider.state_ps(reference.pressure_pa, reference.entropy_j_kg_k)
    for recovered in (by_h, by_s):
        assert recovered.temperature_k == pytest.approx(1150, rel=1e-10)
        assert recovered.density_kg_m3 == pytest.approx(reference.density_kg_m3, rel=1e-10)
        assert recovered.enthalpy_j_kg == pytest.approx(reference.enthalpy_j_kg, rel=1e-10)
        assert recovered.entropy_j_kg_k == pytest.approx(reference.entropy_j_kg_k, rel=1e-10)
    assert provider.native_phase is native
    assert native.basis == "mass"
    assert np.array_equal(native.Y, [.14, .86, 0])
    with pytest.raises(TypeError):
        provider.mass_fractions["H2"] = .2


@pytest.mark.parametrize("temperature", [220, 2800])
def test_exact_native_fit_endpoint_flash_uses_the_already_evaluated_boundary_state(temperature):
    provider = authored_provider()
    state = provider.state_pt(1e5, temperature)
    assert provider.state_ph(1e5, state.enthalpy_j_kg).temperature_k == temperature
    assert provider.state_ps(1e5, state.entropy_j_kg_k).temperature_k == temperature


@pytest.mark.parametrize("back_pressure,regime", [(1e5, "choked"), (7e5, "back_pressure_limited")])
def test_one_common_nozzle_closes_analytic_frozen_pressure_mass_energy(back_pressure, regime):
    provider = authored_provider()
    pressure, temperature = 8e5, 700.
    upstream = provider.state_pt(pressure, temperature)
    opening = NozzleOpening("authored-mixture-vent", 2e-5, .73, "declared-effective-area")
    result = HomogeneousIsentropicNozzle(provider).solve(
        upstream, back_pressure_pa=back_pressure, opening=opening)
    cp, cv = upstream.cp_j_kg_k, upstream.cv_j_kg_k
    gamma, gas_constant = cp/cv, cp-cv
    critical = pressure*(2/(gamma+1))**(gamma/(gamma-1))
    exit_pressure = max(back_pressure, critical)
    exit_temperature = temperature*(exit_pressure/pressure)**((gamma-1)/gamma)
    velocity = math.sqrt(2*cp*(temperature-exit_temperature))
    flux = exit_pressure/(gas_constant*exit_temperature)*velocity
    assert result.regime == regime
    assert result.exit_state.pressure_pa == pytest.approx(exit_pressure, rel=2e-8)
    assert result.exit_state.temperature_k == pytest.approx(exit_temperature, rel=2e-9)
    # Native SP temperature tolerance is amplified in a small enthalpy drop.
    assert result.mass_flux_kg_m2_s == pytest.approx(flux, rel=1e-8)
    assert result.mass_flow_kg_s == pytest.approx(flux*2e-5*.73, rel=1e-8)
    assert result.velocity_m_s == pytest.approx(velocity, rel=1e-8)
    assert abs(result.energy_residual_w) < 1e-7
    assert result.exit_state.basis == provider.basis
    assert result.diagnostics.grid_refinements >= 1
    if regime == "choked":
        assert result.velocity_m_s == pytest.approx(result.exit_state.speed_of_sound_m_s, rel=1e-9)


def test_actual_installed_h2o2_mechanism_roundtrips_and_executes_common_nozzle():
    ct = pytest.importorskip("cantera")
    raw = (Path(ct.__file__).parent / "data/h2o2.yaml").read_bytes()
    basis = MechanismBasis(f"Cantera:{ct.__version__}:h2o2:ohmech",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause; upstream-GRI-Mech-provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",), 300, 3000, 1e4, 2e6)
    native = ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
    provider = CanteraFrozenGasProperties(native, basis, {"H2": .03, "O2": .225, "N2": .745})
    upstream = provider.state_pt(6e5, 850)
    assert provider.state_ph(6e5, upstream.enthalpy_j_kg).temperature_k == pytest.approx(850, rel=1e-9)
    assert provider.state_ps(6e5, upstream.entropy_j_kg_k).temperature_k == pytest.approx(850, rel=1e-9)
    result = HomogeneousIsentropicNozzle(provider).solve(upstream, back_pressure_pa=1e5,
        opening=NozzleOpening("installed-gas-vent", 1e-5, 1, "ideal-area"))
    assert result.regime == "choked"
    assert result.exit_state.temperature_k > 300
    assert result.exit_state.basis.spin_composition == "mechanism-H2-spin-unresolved"
    assert abs(result.energy_residual_w) < 1e-7
    assert np.array_equal(native.Y, [provider.mass_fractions.get(n, 0) for n in native.species_names])


@pytest.mark.parametrize("fractions", [
    {}, {"H2": 2, "N2": 1}, {"H2": -.1, "N2": 1.1}, {"missing": 1},
    {"H2": float("nan")}, {"H2": True}, {"H2": .9999999999999}, {"H2": 0},
])
def test_composition_is_explicit_and_never_silently_normalized(fractions):
    with pytest.raises(ValueError):
        CanteraFrozenGasProperties(authored_phase(), authored_basis(), fractions)


def test_native_boundary_sum_correction_has_an_explicit_budget_id_and_immutable_record():
    fractions = {"H2": .14, "N2": float(np.nextafter(np.nextafter(.86, 1), 1))}
    assert math.fsum(fractions.values()) > 1
    with pytest.raises(ValueError, match="no silent normalization"):
        CanteraFrozenGasProperties(authored_phase(), authored_basis(), fractions)
    provider = CanteraFrozenGasProperties(authored_phase(), authored_basis(), fractions,
        composition_sum_tolerance=1e-12, composition_correction_id="authored-accepted-ulp-case")
    correction = provider.composition_correction
    assert correction.raw_mass_fractions == fractions
    assert correction.raw_sum == math.fsum(fractions.values())
    assert correction.corrected_sum == 1
    assert correction.corrected_species == "N2"
    assert 0 < abs(correction.mass_fraction_change) < 1e-12
    assert correction.declared_tolerance == 1e-12
    assert correction.correction_id == "authored-accepted-ulp-case"
    assert provider.mass_fractions == {"H2": .14, "N2": .86}
    assert provider.basis == authored_provider().basis
    with pytest.raises(TypeError):
        correction.raw_mass_fractions["N2"] = .86
    for invalid in ({"H2": .14, "N2": .8600000001},
                    {"H2": .14, "N2": .86, "AR": -1e-16}):
        with pytest.raises(ValueError):
            CanteraFrozenGasProperties(authored_phase(), authored_basis(), invalid,
                composition_sum_tolerance=1e-12, composition_correction_id="authored-accepted-ulp-case")
    with pytest.raises(ValueError, match="sum tolerance"):
        authored_provider(composition_sum_tolerance=1e-3, composition_correction_id="invalid-budget")
    with pytest.raises(ValueError, match="composition_correction_id"):
        authored_provider(composition_sum_tolerance=1e-12)


def test_actual_native_evolving_enclosure_uses_frozen_shared_nozzle_on_a_separate_phase():
    ct = pytest.importorskip("cantera")
    from h2physics.adapters.cantera import ReactiveState
    from h2physics.adapters.cantera_volume import (
        CanteraOpenGasVolume,
        GasBoundaryRate,
        GasFeed,
        GasVent,
    )
    from h2physics.core import Origin

    def phase_factory():
        return ct.Solution(name="authored-enclosure-gas", thermo="ideal-gas", kinetics=None,
                           species=authored_phase().species()[:2])

    property_phase = phase_factory()
    basis = authored_basis()
    opening = NozzleOpening("mixed-enclosure-vent", 1e-5, .8, "declared-effective-area")
    compositions, corrections = [], []

    def vent_flow(time_s, current):
        properties = CanteraFrozenGasProperties(property_phase, basis,
            dict(zip(current.species_names, current.Y, strict=True)),
            composition_sum_tolerance=1e-7,
            composition_correction_id="native-CVODES-Jacobian-largest-species-trial-extension")
        state = properties.state_pt(current.P, current.T)
        result = HomogeneousIsentropicNozzle(properties).solve(state,
            back_pressure_pa=1e5, opening=opening)
        compositions.append(properties.mass_fractions["H2"])
        if properties.composition_correction is not None:
            corrections.append(properties.composition_correction)
        return result.mass_flow_kg_s

    feed = GasFeed(GasBoundaryRate("feed", "absolute-case-clock", 12.5, 13.,
        lambda t, phase: .001, Origin.SYNTHETIC, "authored-H2-feed"),
        ReactiveState(500, 4e5, {"H2": 1}))
    vent = GasVent(GasBoundaryRate("vent", "absolute-case-clock", 12.5, 13., vent_flow,
        Origin.SYNTHETIC, "shared-nozzle"), ReactiveState(500, 1e5, {"N2": 1}))
    trace = CanteraOpenGasVolume(phase_factory, basis).run(
        ReactiveState(500, 3e5, {"H2": .1, "N2": .9}), np.linspace(12.5, 12.55, 6),
        volume_m3=.5, clock_id="absolute-case-clock", feeds=(feed,), vents=(vent,),
        maximum_time_step_s=.01, relative_tolerance=1e-8, absolute_tolerance=1e-12)
    assert len(compositions) > 6
    assert max(compositions)-min(compositions) > 1e-5
    assert all(abs(c.mass_fraction_change) <= c.declared_tolerance for c in corrections)
    assert trace.native.reactor.phase is not property_phase
    assert trace.snapshots[-1].mass_fractions["H2"] > trace.snapshots[0].mass_fractions["H2"]
    assert trace.integral("outlet:vent:mass")[-1] > 0
    assert max(abs(trace.mass_residual_kg)) < 1e-8
    assert np.max(abs(trace.species_residual_kg)) < 1e-8
    assert max(abs(trace.energy_residual_j)) < 2e-3


def test_basis_retains_composition_mechanism_native_reference_and_hydrogen_partition():
    provider = authored_provider()
    reordered = CanteraFrozenGasProperties(authored_phase(), authored_basis(),
                                          {"N2": .86, "AR": 0, "H2": .14})
    assert provider.basis == reordered.basis
    assert provider.composition_sha256 in provider.basis.fluid
    assert provider.phase_sha256 in provider.basis.reference_id
    assert provider.mechanism_basis.source_sha256 in provider.basis.reference_id
    assert provider.basis.spin_composition == "mechanism-H2-spin-unresolved"
    other_composition = CanteraFrozenGasProperties(authored_phase(), authored_basis(),
                                                  {"H2": .15, "N2": .85})
    other_source = CanteraFrozenGasProperties(authored_phase(), authored_basis(source_sha256="f"*64),
                                             provider.mass_fractions)
    shifted_native = authored_phase()
    species = shifted_native.species(0)
    ct = pytest.importorskip("cantera")
    species.thermo = ct.ConstantCp(180, 3200, 101325, [300, 1.8e6, 8e4, 31000])
    shifted_native.modify_species(0, species)
    other_reference = CanteraFrozenGasProperties(shifted_native, authored_basis(), provider.mass_fractions)
    for other in (other_composition.basis, other_source.basis, other_reference.basis,
                  PropertyBasis("Hydrogen", "CoolProp:sensible-default", "normal")):
        with pytest.raises(ValueError, match="bases differ"):
            provider.basis.require_compatible(other)
    for partition in ("para", "normal", "ortho", "unspecified"):
        with pytest.raises(ValueError, match="spin-unresolved"):
            authored_provider(hydrogen_partition_id=partition)
    pure_nitrogen = CanteraFrozenGasProperties(authored_phase(), authored_basis(), {"N2": 1})
    assert pure_nitrogen.basis.spin_composition == "no-molecular-H2"


def test_pressure_temperature_and_flash_targets_stay_inside_selected_fit_and_declared_domain():
    provider = authored_provider()
    for pressure, temperature in ((9999, 700), (2000001, 700), (1e5, 219), (1e5, 2801),
                                  (float("nan"), 700), (True, 700), (1e5, float("inf"))):
        with pytest.raises(ValueError):
            provider.state_pt(pressure, temperature)
    low, high = provider.state_pt(1e5, 220), provider.state_pt(1e5, 2800)
    for method, values in ((provider.state_ph, (low.enthalpy_j_kg-1, high.enthalpy_j_kg+1)),
                           (provider.state_ps, (low.entropy_j_kg_k-1, high.entropy_j_kg_k+1))):
        for value in values:
            with pytest.raises(ValueError, match="bounds"):
                method(1e5, value)
        with pytest.raises(ValueError):
            method(1e5, float("nan"))
    # A rejected query does not poison the following native flash.
    assert provider.state_pt(1e5, 700).temperature_k == 700
    with pytest.raises(ValueError, match="do not overlap"):
        CanteraFrozenGasProperties(authored_phase(), authored_basis(
            minimum_temperature_k=2900, maximum_temperature_k=3000), {"N2": 1})


def test_wrong_phase_selected_view_and_definition_mutation_are_rejected():
    ct = pytest.importorskip("cantera")
    with pytest.raises(ValueError, match="native ideal-gas"):
        CanteraFrozenGasProperties(object(), authored_basis(), {"H2": 1})
    species = ct.Species("solid-H", {"H": 1})
    species.thermo = ct.ConstantCp(200, 3000, 101325, [300, 0, 0, 1e4])
    condensed = ct.Solution(thermo="fixed-stoichiometry", species=[species])
    with pytest.raises(ValueError, match="native ideal-gas"):
        CanteraFrozenGasProperties(condensed, authored_basis(), {"solid-H": 1})
    with pytest.raises(ValueError, match="selected-species"):
        CanteraFrozenGasProperties(authored_phase()["H2"], authored_basis(), {"H2": 1})
    provider = authored_provider()
    species = provider.native_phase.species(0)
    species.thermo = ct.ConstantCp(180, 3200, 101325, [300, 1.8e6, 8e4, 31000])
    provider.native_phase.modify_species(0, species)
    with pytest.raises(ValueError, match="definition changed"):
        provider.state_pt(1e5, 700)


def test_common_nozzle_cannot_mix_compositions_or_energy_references():
    provider = authored_provider()
    state = provider.state_pt(8e5, 700)
    wrong = replace(state, basis=replace(state.basis, spin_composition="para"))
    with pytest.raises(ValueError, match="bases differ"):
        HomogeneousIsentropicNozzle(provider).solve(wrong, back_pressure_pa=1e5,
            opening=NozzleOpening("vent", 1e-5, 1, "area"))
