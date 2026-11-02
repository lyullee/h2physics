import numpy as np
import pytest

from h2physics.storage import (
    ArrheniusRate,
    HydrideBed,
    HydrideBoundary,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)
from h2physics.storage.hydride import R_J_MOL_K


def model(heat=0):
    # Authored dimensionless verification case, not a particular alloy.
    equilibrium = VanthoffPlateau(24000, 24000 / 300, 100000)
    kinetics = HydrideKinetics(equilibrium, ArrheniusRate(.01, 0, 300),
                              ArrheniusRate(.02, 0, 300))
    return HydrideBed(HydrideParameters(.002, 1000, heat, .002, 0), kinetics)


def test_isothermal_absorption_matches_closed_form_without_parameter_fit():
    bed = model()
    times = np.linspace(0, 100, 101)
    result = bed.simulate(times, HydrideState(.1, 300),
                          lambda t, s: HydrideBoundary(200000, 300))
    expected = 1 - .9 * np.exp(-.01 * times)
    np.testing.assert_allclose(result.fraction, expected, atol=2e-9)
    np.testing.assert_allclose(result.temperature_k, 300, atol=1e-10)
    assert not result.fraction.flags.writeable


def test_desorption_uses_stored_fraction_and_has_negative_uptake():
    bed = model()
    times = np.linspace(0, 100, 30)
    boundary = HydrideBoundary(0, 300)
    assert bed.rates(HydrideState(.8, 300), boundary).hydrogen_uptake_kg_s < 0
    result = bed.simulate(times, HydrideState(.8, 300), lambda t, s: boundary)
    np.testing.assert_allclose(result.fraction, .8 * np.exp(-.02 * times), atol=2e-9)


def test_adiabatic_thermal_reaction_identity_and_capacity_endpoints():
    bed = model(heat=12000)
    result = bed.simulate(np.linspace(0, 50, 51), HydrideState(.1, 300),
                          lambda t, s: HydrideBoundary(200000, 300))
    expected = 300 + bed.parameters.full_reaction_heat_j / 1000 * (result.fraction - .1)
    np.testing.assert_allclose(result.temperature_k, expected, atol=1e-9)
    assert np.max(abs(result.reduced_energy_residual_j)) < 1e-6
    assert bed.rates(HydrideState(1, 300), HydrideBoundary(200000, 300)).fraction_s_inv == 0
    assert bed.rates(HydrideState(0, 300), HydrideBoundary(0, 300)).fraction_s_inv == 0


def test_plateau_units_hysteresis_slope_and_arrhenius_temperature():
    eq = VanthoffPlateau(20000, 20000/300, 1e5, log_fugacity_slope=2,
                         log_hysteresis_gap=np.log(2))
    assert eq.fugacity_pa(300, .5, "absorption") / eq.fugacity_pa(300, .5, "desorption") == pytest.approx(2)
    assert eq.fugacity_pa(330, .5, "absorption") > eq.fugacity_pa(300, .5, "absorption")
    rate = ArrheniusRate(.5, 2000, 300)
    assert rate(300) == .5
    assert np.log(rate(330) / rate(300)) == pytest.approx(2000/R_J_MOL_K * (1/300-1/330))
    with pytest.raises(ValueError, match="fraction"):
        eq.fugacity_pa(300, 1.1, "absorption")
    with pytest.raises(ValueError, match="fugacity"):
        model().rates(HydrideState(.5, 300), HydrideBoundary(-1, 300))
