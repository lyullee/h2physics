"""Actual native multiphase equilibrium against mass-action and conservation oracles."""

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_multiphase import (
    CanteraMultiphaseEquilibrium,
    EquilibriumPhase,
    MultiphaseEquilibriumError,
    MultiphaseFeed,
    MultiphaseSettings,
)
from h2physics.core import Origin

ct = pytest.importorskip("cantera")
DATA = Path(ct.__file__).parent/"data"


def phase_spec(file, name, role, *, subset=False, maximum=2800.):
    raw = (DATA/file).read_bytes()
    def factory():
        source = ct.Solution(yaml=raw.decode("utf-8"), name=name)
        if subset:
            selection = ct.Solution(thermo="ideal-gas", species=[source.species(s) for s in ("CO", "CO2")],
                                    name="authored-CO-CO2-selection")
            selection.TP = source.TP
            return selection
        return source
    basis = MechanismBasis("installed-"+name+("-authored-subset" if subset else ""),
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause; upstream thermochemistry provenance",
        ("https://cantera.org/3.2/python/thermo.html",), 300., maximum, 1e4, 1e6)
    return EquilibriumPhase("gas" if role == "gas" else "carbon", role, factory, basis,
        "declared-native-NASA-formation-and-third-law", "native-mechanism-H2-spin-unresolved")


def model(*, subset=False, maximum=2800., solids=True):
    phases = [phase_spec("gri30.yaml", "gri30", "gas", subset=subset, maximum=maximum)]
    if solids:
        phases.append(phase_spec("graphite.yaml", "graphite", "solid", maximum=maximum))
    return CanteraMultiphaseEquilibrium(phases)


def feed(*, gas=None, solid=0., temperature=750., scale=1.):
    gas = {"CH4": .6, "H2O": .12, "CO2": .08, "AR": .2} if gas is None else gas
    return MultiphaseFeed(temperature, 101325.,
        {"gas": {name: value*scale for name, value in gas.items()}, "carbon": {"C(gr)": solid*scale}},
        "original-finite-feed-case", Origin.SYNTHETIC)


def test_actual_carbon_appearance_and_tp_extensive_first_law():
    result = model().equilibrate(feed())
    assert result.accepted
    assert isinstance(result.native_mixture, ct.Mixture)
    assert result.initial.phase_mol[0] == pytest.approx(1.)
    assert result.native_mixture.phase_moles(0) == pytest.approx(result.final.phase_mol[0]/1000)
    assert result.amount_mol("carbon", "C(gr)") > .05
    assert result.final.temperature_k == pytest.approx(750.)
    assert abs(result.mass_residual_kg) < 1e-12
    assert np.max(abs(result.element_residual_mol)) < 1e-10
    assert abs(result.energy_balance_residual_j) < 1e-6
    assert result.heat_into_j == pytest.approx(result.final.enthalpy_j-result.initial.enthalpy_j)
    assert result.final.gibbs_energy_j < result.initial.gibbs_energy_j
    assert not result.final.species_mol.flags.writeable


def test_native_boudouard_extent_matches_independent_pure_potential_mass_action_oracle():
    engine = model(subset=True)
    result = engine.equilibrate(feed(gas={"CO": 1.}, temperature=800.))
    assert result.initial.mass_kg == pytest.approx(result.owned_phases[0].molecular_weights[0]/1000.)
    gas, carbon = (phase.factory() for phase in engine.phases)
    chemical = {}
    for species in ("CO", "CO2"):
        gas.TPX = 800., 101325., {species: 1.}
        chemical[species] = gas.chemical_potentials[gas.species_index(species)]
    carbon.TP = 800., 101325.
    dg = chemical["CO2"]+carbon.chemical_potentials[0]-2*chemical["CO"]
    constant = math.exp(-dg/(ct.gas_constant*800.))
    extent = .5*(1-1/math.sqrt(1+4*constant))
    assert result.amount_mol("carbon", "C(gr)") == pytest.approx(extent, rel=1e-8, abs=1e-10)
    assert result.amount_mol("gas", "CO2") == pytest.approx(extent, abs=1e-9)
    assert result.amount_mol("gas", "CO") == pytest.approx(1-2*extent, abs=1e-9)
    mu = dict(zip(result.species_keys, result.final.chemical_potentials_j_mol, strict=True))
    affinity = mu[("carbon", "C(gr)")]+mu[("gas", "CO2")]-2*mu[("gas", "CO")]
    assert abs(affinity)/(ct.gas_constant*800./1000.) < 1e-7


def test_solid_disappearance_obeys_absent_phase_stability_and_no_solid_gas_limit():
    gas_feed = {"H2O": .7, "CO2": .15, "H2": .05, "AR": .1}
    engine = model()
    result = engine.equilibrate(feed(gas=gas_feed, solid=.18, temperature=1100.))
    assert result.amount_mol("carbon", "C(gr)") == 0.
    assert result.chemical_audit.absent_solid_affinity_over_rt["carbon"] > 0
    # Equal elements at the same TP are supplied to a separate actual gas-only solver.
    # Atomic C and graphite feeds have different H; no equal-heat claim is made.
    gas = engine.phases[0].factory()
    gas.TPX = 1100., 101325., {"H2O": .7, "CO2": .15, "H2": .05, "AR": .1, "C": .18}
    gas.equilibrate("TP", solver="gibbs", rtol=1e-10)
    native_gas = result.native_mixture.phase(0)
    assert native_gas.X == pytest.approx(gas.X, abs=1e-7)


def test_native_hp_enthalpy_and_independent_pv_work_energy_close():
    engine = model()
    initial = feed(gas={"H2O": .7, "CO2": .15, "H2": .05, "AR": .1}, solid=.18, temperature=1100.)
    result = engine.equilibrate(initial, constraint="HP")
    assert result.accepted
    assert result.heat_into_j == 0
    assert result.final.temperature_k != pytest.approx(initial.temperature_k, abs=1.)
    assert abs(result.enthalpy_constraint_residual_j) < 1e-3
    assert abs(result.energy_balance_residual_j) < 1e-3
    assert result.final.entropy_j_k >= result.initial.entropy_j_k


def test_finite_mol_scaling_preserves_composition_and_scales_all_extensive_quantities():
    engine = model(subset=True)
    a = engine.equilibrate(feed(gas={"CO": 1.}, temperature=800.))
    b = engine.equilibrate(feed(gas={"CO": 1.}, temperature=800., scale=7.3))
    assert b.final.species_mol == pytest.approx(a.final.species_mol*7.3, rel=1e-8, abs=1e-10)
    assert b.heat_into_j == pytest.approx(a.heat_into_j*7.3, rel=1e-8)
    assert b.final.mass_kg == pytest.approx(a.final.mass_kg*7.3, rel=1e-12)


def test_source_phases_are_unchanged_and_owned_objects_have_no_definition_alias():
    engine = model(subset=True)
    result = engine.equilibrate(feed(gas={"CO": 1.}, temperature=800.))
    for source, owned in zip(result.source_phases, result.owned_phases, strict=True):
        assert source is not owned
        assert source.T == pytest.approx(300.)
    source = result.source_phases[0]
    owned = result.owned_phases[0]
    before = owned.species(0).thermo.coeffs.copy()
    species = source.species(0)
    thermo = species.thermo
    coefficients = thermo.coeffs.copy()
    coefficients[-1] += 1.
    coefficients[7] += 1.  # shift both NASA7 branch entropy constants, preserving their match
    species.thermo = type(thermo)(thermo.min_temp, thermo.max_temp, thermo.reference_pressure, coefficients)
    source.modify_species(0, species)
    assert np.array_equal(owned.species(0).thermo.coeffs, before)
    assert result.owned_phases[1].density_mass == 2160.


def test_native_convergence_failure_retains_actual_partial_mixture_and_cause():
    with pytest.raises(MultiphaseEquilibriumError) as error:
        model().equilibrate(feed(), settings=MultiphaseSettings(maximum_steps=1))
    failure = error.value
    assert isinstance(failure.native_mixture, ct.Mixture)
    assert len(failure.owned_phases) == 2
    assert failure.initial is not None
    assert not failure.native_solver_completed
    assert failure.__cause__ is not None


def test_post_native_hp_domain_failure_retains_completed_candidate():
    original = model()
    engine = CanteraMultiphaseEquilibrium(tuple(replace(p, mechanism_basis=replace(
        p.mechanism_basis, minimum_temperature_k=1099.)) for p in original.phases))
    # The already checked endothermic gasification case cools below this deliberately narrow envelope.
    with pytest.raises(MultiphaseEquilibriumError) as error:
        engine.equilibrate(feed(gas={"H2O": .7, "CO2": .15, "H2": .05, "AR": .1},
                                solid=.18, temperature=1100.), constraint="HP")
    assert error.value.native_solver_completed
    assert error.value.final is not None
    assert error.value.final.temperature_k < 1099.
    assert isinstance(error.value.native_mixture, ct.Mixture)


def test_actual_native_zero_carbon_candidate_hp_failure_is_retained_without_gas_fallback():
    with pytest.raises(MultiphaseEquilibriumError) as error:
        model().equilibrate(feed(gas={"H2": .05, "O2": .025, "AR": .925}), constraint="HP")
    assert not error.value.native_solver_completed
    assert error.value.native_mixture.n_phases == 2
    assert error.value.initial is not None and error.value.final is None
    assert error.value.__cause__ is not None


@pytest.mark.parametrize("amount", [-1., float("nan"), True])
def test_invalid_species_amounts_are_not_normalized_or_clipped(amount):
    with pytest.raises(ValueError):
        MultiphaseFeed(750., 101325., {"gas": {"CO": amount}, "carbon": {}},
                       "invalid-native-amount", Origin.SYNTHETIC)


def test_phase_reference_candidate_and_species_identity_guards():
    engine = model()
    with pytest.raises(ValueError, match="reference"):
        CanteraMultiphaseEquilibrium((engine.phases[0], replace(engine.phases[1], energy_reference_id="CoolProp-arbitrary-zero")))
    with pytest.raises(ValueError, match="every candidate"):
        engine.equilibrate(MultiphaseFeed(750., 101325., {"gas": {"CO": 1.}}, "authored", Origin.SYNTHETIC))
    with pytest.raises(MultiphaseEquilibriumError, match="absent"):
        engine.equilibrate(feed(gas={"missing-species": 1.}))
    with pytest.raises(ValueError):
        MultiphaseSettings(solver="auto")
    with pytest.raises(ValueError):
        MultiphaseFeed(750., 101325., {"gas": {}, "carbon": {}}, "zero-feed", Origin.SYNTHETIC)
