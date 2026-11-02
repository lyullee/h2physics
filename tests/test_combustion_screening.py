"""Independent threshold arithmetic and native thermochemistry connection."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.combustion_screening import (
    DetonationCellCriterion,
    EvidenceInterval,
    FlameAccelerationCriterion,
    HydrogenMixtureCondition,
    MixtureExpansion,
    ScreeningDomain,
    cantera_mixture_expansion,
    dorofeev_critical_expansion,
    screen_combustion,
    vent_corrected_critical_expansion,
)
from h2physics.combustion_screening import (
    NecessaryConditionStatus as Status,
)
from h2physics.combustion_screening import (
    ScreeningGeometry as Geometry,
)


def fixture(sigma=5., *, length=(1., 1.), width=(.1, .1), critical=(3.5, 4.)):
    # All intervals are authored arithmetic inputs, not experimental envelopes.
    condition = HydrogenMixtureCondition(300., 101325., .2, 0., "authored-condition")
    expansion = MixtureExpansion(condition, 1., 1. / sigma, 1700., "authored-density-ratio")
    domain = ScreeningDomain(290., 310., 1e5, 1.1e5, .1, .3, .05,
                             (Geometry.CLOSED_OBSTRUCTED_TUBE,), "authored-domain-not-qualification")
    flame = FlameAccelerationCriterion(EvidenceInterval(*critical, "authored-sigma"),
                                        domain, "authored-threshold")
    cell = DetonationCellCriterion(EvidenceInterval(*width, "authored-cell"),
        EvidenceInterval(*length, "authored-length"), domain, condition.condition_id,
        "authored-tube-characteristic-length", "authored-cell-rule")
    return expansion, flame, cell


def test_joint_necessary_conditions_met_is_not_a_prediction():
    expansion, flame, cell = fixture()
    result = screen_combustion(expansion, Geometry.CLOSED_OBSTRUCTED_TUBE, flame, cell)
    assert result.flame_acceleration == result.cell_size == result.combined_ddt == Status.MET
    assert result.predicts_initiation is False
    assert result.reasons == ()


@pytest.mark.parametrize("sigma,length,expected_fa,expected_size,expected_combined", [
    (3., (1., 1.), Status.NOT_MET, Status.MET, Status.NOT_MET),
    (3.7, (1., 1.), Status.INDETERMINATE, Status.MET, Status.INDETERMINATE),
    (5., (.6, .6), Status.MET, Status.NOT_MET, Status.NOT_MET),
    (5., (.6, .8), Status.MET, Status.INDETERMINATE, Status.INDETERMINATE),
    (5., (.7, .7), Status.MET, Status.NOT_MET, Status.NOT_MET),
])
def test_bounded_thresholds_and_equality(sigma, length, expected_fa, expected_size, expected_combined):
    expansion, flame, cell = fixture(sigma, length=length)
    result = screen_combustion(expansion, Geometry.CLOSED_OBSTRUCTED_TUBE, flame, cell)
    assert (result.flame_acceleration, result.cell_size, result.combined_ddt) == (
        expected_fa, expected_size, expected_combined)


def test_cell_uncertainty_is_not_replaced_by_nominal_value():
    expansion, flame, cell = fixture(width=(.05, .2))
    result = screen_combustion(expansion, Geometry.CLOSED_OBSTRUCTED_TUBE, flame, cell)
    assert result.cell_size == Status.INDETERMINATE
    assert "uncertainty" in result.reasons[-1]


@pytest.mark.parametrize("geometry", [Geometry.UNCONFINED, Geometry.SEMICONFINED_FLAT_LAYER,
                                      Geometry.COMPLEX_COMPARTMENT, Geometry.TRANSVERSE_VENTED_TUBE])
def test_tube_criterion_does_not_admit_other_geometries(geometry):
    expansion, flame, cell = fixture()
    result = screen_combustion(expansion, geometry, flame, cell)
    assert result.combined_ddt == Status.INDETERMINATE
    assert "geometry" in result.reasons[0]


def test_mismatched_cell_conditions_are_indeterminate():
    expansion, flame, cell = fixture()
    result = screen_combustion(expansion, Geometry.CLOSED_OBSTRUCTED_TUBE, flame,
                               replace(cell, cell_data_condition_id="other-temperature"))
    assert result.flame_acceleration == Status.MET
    assert result.cell_size == result.combined_ddt == Status.INDETERMINATE


def test_temperature_pressure_and_composition_outside_envelope_are_retained():
    expansion, flame, cell = fixture()
    condition = HydrogenMixtureCondition(100., 2e5, .4, .2, expansion.condition.condition_id)
    result = screen_combustion(replace(expansion, condition=condition),
                               Geometry.CLOSED_OBSTRUCTED_TUBE, flame, cell)
    assert result.combined_ddt == Status.INDETERMINATE
    assert len(result.reasons) == 4


def test_polynomial_anchor_and_explicit_dimensionless_domain():
    value = dorofeev_critical_expansion(activation_temperature_k=7500.,
        unburned_temperature_k=300., qualified_x_interval=EvidenceInterval(24., 26., "authored-x"),
        turbulent_peclet_number=100., applicability_evidence_id="authored-range")
    assert value.lower == value.upper == pytest.approx(3.702025)
    with pytest.raises(ValueError, match="outside"):
        dorofeev_critical_expansion(activation_temperature_k=7500., unburned_temperature_k=100.,
            qualified_x_interval=EvidenceInterval(24., 26., "authored-x"),
            turbulent_peclet_number=100., applicability_evidence_id="authored-range")
    with pytest.raises(ValueError, match="Pe"):
        dorofeev_critical_expansion(activation_temperature_k=7500., unburned_temperature_k=300.,
            qualified_x_interval=EvidenceInterval(24., 26., "authored-x"),
            turbulent_peclet_number=99., applicability_evidence_id="authored-range")


def test_vent_correction_keeps_coefficient_uncertainty():
    value = vent_corrected_critical_expansion(EvidenceInterval(3.7, 3.7, "authored-closed"),
        vent_to_total_surface_ratio=.2, qualified_vent_ratio_bounds=(.2, .4),
        coefficient=EvidenceInterval(1.8, 2.2, "authored-c"),
        applicability_evidence_id="authored-vented-tube")
    assert value.lower == pytest.approx(5.032)
    assert value.upper == pytest.approx(5.328)
    with pytest.raises(ValueError, match="outside"):
        vent_corrected_critical_expansion(EvidenceInterval(3.7, 3.7, "authored-closed"),
            vent_to_total_surface_ratio=.5, qualified_vent_ratio_bounds=(.2, .4),
            coefficient=EvidenceInterval(1.8, 2.2, "authored-c"),
            applicability_evidence_id="authored-vented-tube")


@pytest.mark.parametrize("low,high", [(0., 1.), (2., 1.), (1., float("inf")), (True, 2.)])
def test_interval_rejects_invalid_support(low, high):
    with pytest.raises(ValueError):
        EvidenceInterval(low, high, "authored")


def test_actual_cantera_connection_restores_phase_and_uses_density_ratio():
    ct = pytest.importorskip("cantera")
    # Read unmodified installed text with Python, avoiding native Unicode-path I/O.
    raw = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_text(encoding="utf-8")
    gas = ct.Solution(yaml=raw, name="ohmech")
    gas.TPX = 450., 2e5, "H2:1,O2:1,N2:3.76"
    original = gas.state.copy()
    expansion = cantera_mixture_expansion(gas, temperature_k=300., pressure_pa_absolute=101325.,
        mole_fractions={"H2": 2., "O2": 1., "N2": 3.76}, condition_id="stoichiometric-dry-air",
        mechanism_evidence_id="Cantera-installed-h2o2.yaml")
    np.testing.assert_array_equal(gas.state, original)
    assert expansion.condition.hydrogen_mole_fraction == pytest.approx(2. / 6.76)
    assert expansion.burned_temperature_k > 2000.
    assert expansion.expansion_ratio > 5.
    # Independent mass-basis relation rho_u/rho_b = Tb/Tu * MWu/MWb.
    gas.TPX = 300., 101325., "H2:2,O2:1,N2:3.76"
    mw_unburned = gas.mean_molecular_weight
    gas.equilibrate("HP")
    assert expansion.expansion_ratio == pytest.approx(
        gas.T / 300. * mw_unburned / gas.mean_molecular_weight, rel=2e-12)


def test_cantera_rejects_nonair_or_unmatched_diluents():
    ct = pytest.importorskip("cantera")
    raw = (Path(ct.__file__).parent / "data" / "h2o2.yaml").read_text(encoding="utf-8")
    gas = ct.Solution(yaml=raw, name="ohmech")
    for composition in ({"H2": 1., "O2": 1.}, {"H2": 1., "O2": 1., "AR": 3.}):
        with pytest.raises(ValueError):
            cantera_mixture_expansion(gas, temperature_k=300., pressure_pa_absolute=1e5,
                mole_fractions=composition, condition_id="authored", mechanism_evidence_id="native")
