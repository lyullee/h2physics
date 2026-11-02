import math

import pytest

from h2physics.electrochemistry import (
    FARADAY_C_MOL,
    HydrogenStack,
    LimitingCurrentLoss,
    OhmicLoss,
    ReactionEnergy,
    StackGeometry,
    SymmetricButlerVolmerLoss,
    ideal_activity_correction,
)


def model():
    return HydrogenStack(StackGeometry(10, .01, .002),
                          lambda t: ReactionEnergy(2*FARADAY_C_MOL, 3*FARADAY_C_MOL, "synthetic", "liquid"),
                          {"ohmic": OhmicLoss(lambda t: .001)})


def test_single_stack_core_changes_direction_and_conserves_ideal_reaction_power():
    electrolyzer = model().evaluate(100, 300, mode="electrolysis")
    fuel_cell = model().evaluate(100, 300, mode="fuel_cell")
    assert electrolyzer.cell_voltage_v == pytest.approx(1.1)
    assert fuel_cell.cell_voltage_v == pytest.approx(.9)
    assert electrolyzer.current_a == 1
    assert electrolyzer.hydrogen_production_mol_s == -fuel_cell.hydrogen_production_mol_s
    assert electrolyzer.electric_input_w == pytest.approx(11)
    assert fuel_cell.electric_input_w == pytest.approx(-9)
    assert electrolyzer.isothermal_heat_rejection_w == pytest.approx(-4)
    assert fuel_cell.isothermal_heat_rejection_w == pytest.approx(6)


def test_faradaic_loss_is_explicit_and_does_not_invent_its_thermal_fate():
    result = model().evaluate(100, 300, mode="electrolysis", faradaic_efficiency=.9)
    assert result.hydrogen_production_mol_s == pytest.approx(9/(2*FARADAY_C_MOL))
    assert result.isothermal_heat_rejection_w is None


def test_activity_and_activation_limits_are_checked_without_tafel_singularity():
    standard = ReactionEnergy(200000, 250000, "authored", "vapor")
    corrected = ideal_activity_correction(standard, temperature_k=300, hydrogen_activity=2,
                                          oxygen_activity=1, water_activity=1)
    assert corrected.gibbs_j_mol_h2 > standard.gibbs_j_mol_h2
    loss = SymmetricButlerVolmerLoss(lambda t: 10, 1)
    assert loss(0, 300) == 0
    assert loss(20, 300) > 0
    limit = LimitingCurrentLoss(lambda t: 100, lambda t: .1)
    assert limit(50, 300) == pytest.approx(.1*math.log(2))
    with pytest.raises(ValueError, match="limiting"):
        limit(100, 300)
