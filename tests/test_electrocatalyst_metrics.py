import numpy as np
import pytest

from h2physics.constants import FARADAY_C_MOL, R_J_MOL_K
from h2physics.electrocatalyst_metrics import (
    compare_product_to_charge,
    corrected_overpotential_v,
    fit_tafel,
    turnover_frequency_from_current,
    turnover_frequency_from_product,
)


def test_ir_correction_and_cathodic_tafel_parameters():
    j = -np.geomspace(1, 1000, 13)  # A/m2 on a geometric area basis.
    j0, slope, area, resistance = .02, .12, 1e-4, 3.
    eta = -slope*np.log10(abs(j)/j0)
    measured = eta+j*area*resistance
    corrected = corrected_overpotential_v(measured, 0., j*area,
                                          remaining_uncompensated_resistance_ohm=resistance)
    result = fit_tafel(corrected, j, branch="cathodic", area_basis="geometric",
                       protocol_id="synthetic charge-transfer-only fixture",
                       current_density_window_a_m2=(1., 1000.))
    assert result.slope_v_decade == pytest.approx(slope, rel=1e-12)
    assert result.exchange_current_density_a_m2 == pytest.approx(j0, rel=1e-12)
    assert result.transfer_coefficient_times_electrons(300.) == pytest.approx(
        np.log(10)*R_J_MOL_K*300/(slope*FARADAY_C_MOL))
    assert result.r_squared == pytest.approx(1.)
    with pytest.raises(ValueError):
        result.covariance.setflags(write=True)


def test_weighted_fit_window_excludes_transport_region_and_retains_residuals():
    j = np.geomspace(1, 1e4, 21)
    eta = .08*np.log10(j/.001)
    eta[j > 100] += .3
    result = fit_tafel(eta, j, branch="anodic", area_basis="ECSA", protocol_id="fixture",
                       current_density_window_a_m2=(1., 100.),
                       overpotential_standard_uncertainty_v=np.full_like(j, .002))
    assert result.slope_v_decade == pytest.approx(.08)
    assert result.covariance[1, 1] > 0
    assert len(result.selected_indices) == 11
    with pytest.raises(ValueError, match="branch"):
        fit_tafel(-eta, j, branch="anodic", area_basis="ECSA", protocol_id="fixture",
                   current_density_window_a_m2=(1., 100.))


def test_product_charge_uses_interpolated_interval_edges_and_keeps_excess_fe():
    # I(t)=2+t A; charge [0.5, 1.5] is 3 C, [1.5, 2] is 1.875 C.
    expected_charge = np.array([3., 1.875])
    efficiency = np.array([.8, 1.1])
    amount = expected_charge*efficiency/(2*FARADAY_C_MOL)
    result = compare_product_to_charge([0., 1., 2.], [-2., -3., -4.],
        interval_edges_s=[.5, 1.5, 2.], product_mol=amount, product="H2",
        current_clock_id="electrode", collection_clock_id="electrode", measurement_id="fixture")
    np.testing.assert_allclose(result.charge_magnitude_c, expected_charge)
    np.testing.assert_allclose(result.faradaic_efficiency, efficiency)
    oxygen = compare_product_to_charge([0., 1.], [4., 4.], interval_edges_s=[0., 1.],
        product_mol=[1/FARADAY_C_MOL], product="O2", current_clock_id="clock",
        collection_clock_id="clock", measurement_id="fixture")
    assert oxygen.faradaic_efficiency[0] == pytest.approx(1)


def test_product_charge_rejects_clock_extrapolation_and_polarity_reversal():
    args = dict(interval_edges_s=[0., 1.], product_mol=[1e-6], product="H2",
                current_clock_id="clock", collection_clock_id="clock", measurement_id="fixture")
    with pytest.raises(ValueError, match="polarity"):
        compare_product_to_charge([0., 1.], [-1., 1.], **args)
    with pytest.raises(ValueError, match="Align"):
        compare_product_to_charge([0., 1.], [1., 1.], **(args | {"collection_clock_id": "other"}))
    with pytest.raises(ValueError, match="support"):
        compare_product_to_charge([0., .5], [1., 1.], **args)


def test_her_and_oer_tof_use_product_electrons_and_moles_of_sites():
    current, sites, efficiency = 1., 1e-6, .8
    her = turnover_frequency_from_current(current, product="H2", faradaic_efficiency=efficiency,
                                          active_site_amount_mol=sites, site_basis_id="counted sites")
    oer = turnover_frequency_from_current(current, product="O2", faradaic_efficiency=efficiency,
                                          active_site_amount_mol=sites, site_basis_id="counted sites")
    assert her == pytest.approx(2*oer)
    assert her == pytest.approx(turnover_frequency_from_product(
        current*efficiency/(2*FARADAY_C_MOL), active_site_amount_mol=sites,
        site_basis_id="counted sites"))
    with pytest.raises(ValueError):
        turnover_frequency_from_current(current, product="H2", faradaic_efficiency=1.01,
                                         active_site_amount_mol=sites, site_basis_id="fixture")


def test_extreme_measurements_reject_numeric_overflow_instead_of_returning_infinity():
    with pytest.raises(ValueError, match="finite"):
        corrected_overpotential_v(1., 0., 1e308,
                                   remaining_uncompensated_resistance_ohm=1e308)
    with pytest.raises(ValueError, match="finite"):
        turnover_frequency_from_product(1e308, active_site_amount_mol=1e-308, site_basis_id="fixture")
    with pytest.raises(ValueError, match="finite"):
        compare_product_to_charge([0., 1.], [1., 1.], interval_edges_s=[0., 1.],
            product_mol=[1e308], product="H2", current_clock_id="clock",
            collection_clock_id="clock", measurement_id="fixture")
