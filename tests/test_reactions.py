import math

import numpy as np
import pytest

from h2physics.reactions import (
    ChemicalSpecies,
    FunctionalMolarEnthalpy,
    ReferenceReactionHeat,
    StoichiometricReaction,
    conversion_heat_j,
    solve_product_temperature,
)


def carrier():
    return StoichiometricReaction("authored-cycle", (
        ChemicalSpecies("rich", {"C": 6, "H": 12}, .084156, "liquid"),
        ChemicalSpecies("lean", {"C": 6, "H": 6}, .078108, "liquid"),
        ChemicalSpecies("H2", {"H": 2}, .002016, "gas"),
        ChemicalSpecies("inert", {"N": 2}, .028014, "gas")), (-1, 1, 3, 0))


def test_finite_conversion_reverse_capacity_and_mass():
    reaction = carrier()
    initial = {"rich": 2, "lean": 1, "H2": .3, "inert": 4}
    assert reaction.extent_limits_mol(initial) == pytest.approx((-.1, 2))
    converted = reaction.convert(initial, 2)
    assert converted.final_amounts == {"rich": 0, "lean": 3, "H2": 6.3, "inert": 4}
    assert abs(converted.mass_residual_kg) < 1e-16
    reverse = reaction.convert(converted.final_amounts, -2)
    np.testing.assert_allclose(reverse.final_mol, reaction.amounts(initial), atol=1e-15)
    assert not converted.final_mol.flags.writeable
    with pytest.raises(TypeError):
        converted.final_amounts["rich"] = 100
    with pytest.raises(ValueError, match="finite"):
        reaction.convert(initial, np.nextafter(2., math.inf))
    with pytest.raises(ValueError, match="finite"):
        reaction.convert(initial, -.1000001)


@pytest.mark.parametrize("bad", [{"alien": 1}, {"rich": -1}, {"rich": math.nan}, {"rich": True}])
def test_invalid_inventory(bad):
    with pytest.raises(ValueError):
        carrier().convert(bad, 0)


def test_element_charge_and_mass_are_independent_gates():
    h2 = ChemicalSpecies("H2", {"H": 2}, .002016, "gas")
    h = ChemicalSpecies("H", {"H": 1}, .001008, "gas")
    with pytest.raises(ValueError, match="element"):
        StoichiometricReaction("bad-elements", (h2, h), (-1, 1))
    ion = ChemicalSpecies("H+", {"H": 1}, .001008, "gas", 1)
    with pytest.raises(ValueError, match="charge"):
        StoichiometricReaction("bad-charge", (h, ion), (-1, 1))
    wrong = ChemicalSpecies("wrong-H", {"H": 1}, .001, "gas")
    with pytest.raises(ValueError, match="atomic-weight"):
        StoichiometricReaction("bad-mass", (h2, wrong), (-1, 2))


def caloric(reaction, gauge=0.):
    cp = (100., 60., 30., 20.)
    hf = (0., 180000., 0., 0.)
    functions = tuple((lambda t, p, c=c, h=h, s=s:
        h + c*(t-300) + gauge*(2*s.elements.get("C", 0) + s.elements.get("H", 0)))
        for c, h, s in zip(cp, hf, reaction.species, strict=True))
    return FunctionalMolarEnthalpy(reaction.species, functions, f"authored:gauge={gauge}",
                                  (200, 2000), (1e4, 1e6))


def test_calorimetry_matches_analytic_and_conserved_element_gauge():
    reaction = carrier()
    conversion = reaction.convert({"rich": 2, "inert": 1}, .2)
    # Initial Cp=220 J/K; final Cp=230 J/K; formation increment=36 kJ.
    expected_t = 300 + (220*(800-300)-36000)/230
    result = solve_product_temperature(conversion, caloric(reaction), inlet_temperature_k=800,
        pressure_pa=1e5, supplied_heat_j=0, bracket_k=(200, 1800))
    assert result.temperature_k == pytest.approx(expected_t, abs=1e-9)
    assert abs(result.energy_residual_j) < 1e-8
    shifted = solve_product_temperature(conversion, caloric(reaction, 3e7), inlet_temperature_k=800,
        pressure_pa=1e5, supplied_heat_j=0, bracket_k=(200, 1800))
    assert shifted.temperature_k == pytest.approx(result.temperature_k, abs=1e-8)
    q = conversion_heat_j(conversion, caloric(reaction), inlet_temperature_k=300,
                          outlet_temperature_k=300, pressure_pa=1e5)
    assert q == pytest.approx(36000)


def test_caloric_domain_reference_phase_and_unbracketed_results_reject():
    reaction = carrier()
    converted = reaction.convert({"rich": 1}, .1)
    with pytest.raises(ValueError, match="domain"):
        conversion_heat_j(converted, caloric(reaction), inlet_temperature_k=199,
                          outlet_temperature_k=300, pressure_pa=1e5)
    with pytest.raises(ValueError):
        solve_product_temperature(converted, caloric(reaction), inlet_temperature_k=300,
            pressure_pa=1e5, supplied_heat_j=1e9, bracket_k=(200, 1800))
    reordered = FunctionalMolarEnthalpy(reaction.species[::-1], caloric(reaction).functions,
                                       "wrong-order", (200, 2000), (1e4, 1e6))
    with pytest.raises(ValueError, match="species/order/phase"):
        conversion_heat_j(converted, reordered, inlet_temperature_k=300,
                          outlet_temperature_k=300, pressure_pa=1e5)


def test_reference_heat_normalization_sign_and_no_extrapolation():
    reaction = carrier()
    heat = ReferenceReactionHeat(reaction, 180000, 298.15, 101325, "authored", "test", "synthetic")
    forward = reaction.convert({"rich": 2}, .5)
    reverse = reaction.convert(forward.final_amounts, -.5)
    assert heat.heat_j(forward, temperature_k=298.15, pressure_pa=101325) == 90000
    assert heat.heat_j(reverse, temperature_k=298.15, pressure_pa=101325) == -90000
    with pytest.raises(ValueError, match="extrapolated"):
        heat.heat_j(forward, temperature_k=350, pressure_pa=101325)


def test_empty_inventory_does_not_return_an_arbitrary_temperature():
    reaction = carrier()
    with pytest.raises(ValueError, match="empty"):
        solve_product_temperature(reaction.convert({}, 0), caloric(reaction),
            inlet_temperature_k=300, pressure_pa=1e5, supplied_heat_j=0, bracket_k=(200, 1800))
