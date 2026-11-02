"""Actual native gas/iron-oxide calorimetry; all densities here are synthetic."""

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.cantera import MechanismBasis
from h2physics.adapters.cantera_caloric import (
    CanteraMultiphaseMolarEnthalpy,
    SolidDensityEvidence,
)
from h2physics.adapters.cantera_multiphase import EquilibriumPhase
from h2physics.core import Origin
from h2physics.reactions import StoichiometricReaction, conversion_heat_j, solve_product_temperature

ct = pytest.importorskip("cantera")
DATA = Path(ct.__file__).parent/"data"
REFERENCE = "declared-native-NASA-standard-formation-reference"
SPIN = "native-mechanism-H2-spin-unresolved"
MAPPING = (("magnetite", "Fe3O4(s)", "oxidized"), ("wustite", "FeO(s)", "reduced"),
           ("gas", "O2", "oxygen"), ("gas", "H2O", "steam"), ("gas", "H2", "hydrogen"))


def phase_spec(phase_id, species=None, *, density=5000., maximum=1600.):
    file = "h2o2.yaml" if species is None else "nasa_condensed.yaml"
    raw = (DATA/file).read_bytes()
    def factory():
        if species is None:
            return ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
        selected = next(s for s in ct.Species.list_from_yaml(raw.decode("utf-8"), "species")
                        if s.name == species)
        data = dict(selected.input_data)
        data["equation-of-state"] = {"model": "constant-volume", "density": density}
        native = ct.Solution(thermo="fixed-stoichiometry", species=[ct.Species.from_dict(data)],
                             name="authored-density-"+phase_id, transport_model="none")
        native.TP = 300., 101325.
        return native
    basis = MechanismBasis("installed-"+file+":"+phase_id, hashlib.sha256(raw).hexdigest(),
        "Cantera BSD-3-Clause; NASA TM4513 upstream thermochemistry",
        ("https://ntrs.nasa.gov/citations/19940013151",), 300., maximum, 1e4, 2e6)
    return EquilibriumPhase(phase_id, "gas" if species is None else "solid", factory, basis, REFERENCE, SPIN)


def provider(*, maximum=1600.):
    phases = (phase_spec("magnetite", "Fe3O4(s)", density=4800., maximum=maximum),
              phase_spec("wustite", "FeO(s)", maximum=maximum), phase_spec("gas", maximum=maximum))
    evidence = {p.phase_id: SolidDensityEvidence(density, "authored-test-density:"+p.phase_id,
        Origin.SYNTHETIC, "Constant density verification fixture; no measured oxide EOS claim")
        for p, density in zip(phases[:2], (4800., 5000.), strict=True)}
    return CanteraMultiphaseMolarEnthalpy(phases, MAPPING, solid_density_evidence=evidence)


def reactions(caloric):
    return (StoichiometricReaction("authored-oxide-reduction", caloric.species, (-1, 3, .5, 0, 0)),
            StoichiometricReaction("authored-oxide-steam-oxidation", caloric.species, (1, -3, 0, -1, 1)))


def test_actual_native_provider_alias_order_units_and_common_reference():
    caloric = provider()
    values = caloric.enthalpies_j_mol(900., 101325.)
    assert tuple(s.identifier for s in caloric.species) == tuple(m[2] for m in MAPPING)
    assert tuple(s.phase for s in caloric.species[:2]) == ("solid:magnetite", "solid:wustite")
    for mapping, value in zip(MAPPING, values, strict=True):
        phase = caloric.owned_phases[caloric._phase_indices[mapping[0]]]
        assert value == pytest.approx(phase.partial_molar_enthalpies[phase.species_index(mapping[1])]/1000.)
        assert isinstance(phase, ct.Solution)
    assert caloric.native_gas_providers["gas"].native_phase is caloric.owned_phases[2]
    assert not values.flags.writeable
    assert caloric.energy_reference_id == REFERENCE and caloric.hydrogen_partition_id == SPIN


def test_extensive_native_mixture_h_and_independent_h_u_pv_close():
    caloric = provider()
    amounts = np.array([.37, .21, .08, .6, .13])
    values = caloric.enthalpies_j_mol(1050., 350000.)
    mixture = ct.Mixture([(phase, 0.) for phase in caloric.owned_phases])
    mixture.T, mixture.P = 1050., 350000.
    native_amounts = np.zeros(mixture.n_species)
    for mapping, amount in zip(MAPPING, amounts, strict=True):
        native_amounts[mixture.species_index(caloric._phase_indices[mapping[0]], mapping[1])] = amount/1000.
    mixture.species_moles = native_amounts
    mixture.chemical_potentials  # synchronize the native heavyweight phase states
    native_h = sum(mixture.phase_moles(k)*p.enthalpy_mole for k, p in enumerate(caloric.owned_phases))
    native_u = sum(mixture.phase_moles(k)*p.int_energy_mole for k, p in enumerate(caloric.owned_phases))
    volume = sum(mixture.phase_moles(k)*p.mean_molecular_weight/p.density_mass
                 for k, p in enumerate(caloric.owned_phases))
    assert amounts@values == pytest.approx(native_h, abs=1e-9)
    assert native_h-native_u == pytest.approx(mixture.P*volume, abs=1e-9)


def test_constant_volume_solid_native_pressure_correction_and_gas_pressure_independence():
    caloric = provider()
    a = caloric.enthalpies_j_mol(950., 101325.)
    b = caloric.enthalpies_j_mol(950., 1100000.)
    assert b[2:] == pytest.approx(a[2:], abs=1e-9)
    for k, phase in enumerate(caloric.owned_phases[:2]):
        molar_volume = phase.mean_molecular_weight/phase.density_mass/1000.
        assert b[k]-a[k] == pytest.approx((1100000.-101325.)*molar_volume, abs=1e-9)
        reference_h = phase.species(0).thermo.h(950.)/1000.
        assert b[k]-reference_h == pytest.approx((1100000.-phase.species(0).thermo.reference_pressure)
                                               *molar_volume, abs=1e-9)


def test_native_cp_matches_temperature_derivative_without_implementing_cp():
    caloric = provider()
    delta = .01
    derivative = (caloric.enthalpies_j_mol(900.+delta, 230000.)
                  -caloric.enthalpies_j_mol(900.-delta, 230000.))/(2*delta)
    caloric.enthalpies_j_mol(900., 230000.)
    exact = [caloric.owned_phases[caloric._phase_indices[p]].partial_molar_cp[
        caloric.owned_phases[caloric._phase_indices[p]].species_index(n)]/1000. for p, n, _ in MAPPING]
    assert derivative == pytest.approx(exact, rel=1e-8, abs=1e-7)
    assert min(exact) > 0


def test_two_finite_oxide_stages_use_shared_conversion_and_close_net_water_heat():
    caloric = provider()
    reduction, oxidation = reactions(caloric)
    first = reduction.convert({"oxidized": .4, "steam": 1.}, .15)
    second = oxidation.convert(first.final_amounts, .15)
    assert second.final_amounts["oxidized"] == pytest.approx(.4)
    assert second.final_amounts["hydrogen"] == pytest.approx(.15)
    assert second.final_amounts["oxygen"] == pytest.approx(.075)
    heat1 = conversion_heat_j(first, caloric, inlet_temperature_k=1000., outlet_temperature_k=1000., pressure_pa=101325.)
    heat2 = conversion_heat_j(second, caloric, inlet_temperature_k=1000., outlet_temperature_k=1000., pressure_pa=101325.)
    h = caloric.enthalpies_j_mol(1000., 101325.)
    assert heat1+heat2 == pytest.approx(.15*(h[4]+.5*h[2]-h[3]), abs=1e-9)
    assert abs(first.mass_residual_kg) < 1e-16 and abs(second.mass_residual_kg) < 1e-16
    reverse = reduction.convert(first.final_amounts, -.15)
    reverse_heat = conversion_heat_j(reverse, caloric, inlet_temperature_k=1000., outlet_temperature_k=1000., pressure_pa=101325.)
    assert reverse_heat == pytest.approx(-heat1, abs=1e-9)
    with pytest.raises(ValueError, match="finite"):
        reduction.convert({"oxidized": .4}, .4000001)


def test_shared_temperature_solver_recovers_prescribed_nonisothermal_native_heat():
    caloric = provider()
    conversion = reactions(caloric)[0].convert({"oxidized": .4, "steam": .6}, .05)
    supplied = conversion_heat_j(conversion, caloric, inlet_temperature_k=800., outlet_temperature_k=1120., pressure_pa=200000.)
    solved = solve_product_temperature(conversion, caloric, inlet_temperature_k=800., pressure_pa=200000.,
        supplied_heat_j=supplied, bracket_k=(700., 1500.))
    assert solved.temperature_k == pytest.approx(1120., abs=1e-8)
    assert abs(solved.energy_residual_j) < 1e-7


def test_native_state_reuse_is_reset_but_source_and_owned_thermo_mutation_rejected():
    caloric = provider()
    expected = caloric.enthalpies_j_mol(900., 101325.)
    gas = caloric.owned_phases[2]
    gas.TPX = 1500., 500000., {"H2O": .9, "H2": .1}
    caloric.owned_phases[0].TP = 1400., 600000.
    assert caloric.enthalpies_j_mol(900., 101325.) == pytest.approx(expected, abs=1e-10)
    assert gas.X[0] == 1.
    source = caloric.source_phases[0]
    before = caloric.owned_phases[0].species(0).thermo.coeffs.copy()
    species = source.species(0)
    thermo = species.thermo
    coeff = thermo.coeffs.copy()
    coeff[6] += .001
    coeff[13] += .001
    species.thermo = type(thermo)(thermo.min_temp, thermo.max_temp, thermo.reference_pressure, coeff)
    source.modify_species(0, species)
    assert np.array_equal(caloric.owned_phases[0].species(0).thermo.coeffs, before)
    with pytest.raises(ValueError, match="definition changed"):
        caloric.enthalpies_j_mol(900., 101325.)
    other = provider()
    other.owned_phases[2].set_multiplier(.5, 0)
    with pytest.raises(ValueError, match="definition changed"):
        other.enthalpies_j_mol(900., 101325.)


def test_reused_gas_provider_cannot_rebind_to_a_different_actual_native_phase():
    caloric = provider()
    expected = caloric.enthalpies_j_mol(900., 101325.)
    alternative = caloric.phases[2].factory()
    index = alternative.species_index("H2")
    species = alternative.species(index)
    thermo = species.thermo
    coefficients = thermo.coeffs.copy()
    coefficients[6] += 1000.
    coefficients[13] += 1000.
    species.thermo = type(thermo)(thermo.min_temp, thermo.max_temp, thermo.reference_pressure, coefficients)
    alternative.modify_species(index, species)
    alternative.TP = 900., 101325.
    assert alternative.partial_molar_enthalpies[index]/1000.-expected[-1] == pytest.approx(ct.gas_constant)
    native_gas = caloric.native_gas_providers["gas"]
    native_gas.native_phase = alternative
    assert caloric.owned_phases[2] is not alternative
    with pytest.raises(ValueError, match="caloric binding changed"):
        caloric.enthalpies_j_mol(900., 101325.)


@pytest.mark.parametrize("field", ["_indices", "species", "mechanism_basis", "basis_id"])
def test_reused_gas_provider_species_indices_and_reference_binding_are_guarded(field):
    caloric = provider()
    gas = caloric.native_gas_providers["gas"]
    value = getattr(gas, field)
    changed = (tuple(reversed(value)) if field in {"_indices", "species"}
               else replace(value, identifier="unreviewed-basis") if field == "mechanism_basis"
               else "unreviewed-reference")
    setattr(gas, field, changed)
    with pytest.raises(ValueError, match="caloric binding changed"):
        caloric.enthalpies_j_mol(900., 101325.)


@pytest.mark.parametrize("temperature,pressure", [(299., 101325.), (1700., 101325.),
    (900., 0.), (float("nan"), 101325.), (True, 101325.), (900., 3e6)])
def test_domain_and_selected_fit_failures(temperature, pressure):
    # Wider host envelope makes the native FeO(s) upper fit bound independently active.
    with pytest.raises(ValueError):
        provider(maximum=2000.).enthalpies_j_mol(temperature, pressure)


def test_reference_spin_mapping_and_density_evidence_are_not_inferred():
    original = provider()
    phases, evidence = original.phases, original.solid_density_evidence
    for altered, match in ((replace(phases[0], energy_reference_id="arbitrary-sensible-zero"), "reference"),
                           (replace(phases[0], hydrogen_partition_id="para-H2"), "partition")):
        with pytest.raises(ValueError, match=match):
            CanteraMultiphaseMolarEnthalpy((altered, *phases[1:]), MAPPING, solid_density_evidence=evidence)
    for mapping in ((MAPPING[0], MAPPING[0], *MAPPING[1:]), (("foreign", "FeO(s)", "alien"), *MAPPING[1:])):
        with pytest.raises(ValueError):
            CanteraMultiphaseMolarEnthalpy(phases, mapping, solid_density_evidence=evidence)
    with pytest.raises(ValueError, match="density evidence"):
        CanteraMultiphaseMolarEnthalpy(phases, MAPPING)
    bad = dict(evidence)
    bad["wustite"] = replace(bad["wustite"], density_kg_m3=4999.)
    with pytest.raises(ValueError, match="density differs"):
        CanteraMultiphaseMolarEnthalpy(phases, MAPPING, solid_density_evidence=bad)
    with pytest.raises(ValueError):
        SolidDensityEvidence(5000., "authored", Origin.UNRESOLVED, "unresolved")


def test_actual_native_custom_atomic_weight_and_phase_model_mismatches_reject():
    original = provider()
    def altered_weight_factory():
        native = original.phases[1].factory()
        return ct.Solution(yaml="elements:\n- symbol: O\n  atomic-weight: 17.0\n"
                           +native.write_yaml(precision=17), name=native.name)
    altered = replace(original.phases[1], factory=altered_weight_factory)
    assert altered.factory().atomic_weight("O") == 17.
    with pytest.raises(ValueError, match="atomic-weight"):
        CanteraMultiphaseMolarEnthalpy((original.phases[0], altered, original.phases[2]), MAPPING,
                                       solid_density_evidence=original.solid_density_evidence)
    bad_phase = replace(original.phases[0], factory=original.phases[2].factory)
    with pytest.raises(ValueError, match="pure stoichiometric-solid"):
        CanteraMultiphaseMolarEnthalpy((bad_phase, *original.phases[1:]), MAPPING,
                                       solid_density_evidence=original.solid_density_evidence)
