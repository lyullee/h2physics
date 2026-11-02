import numpy as np
import pytest

from h2physics.core import MassPartition, Origin, TimeSeries
from h2physics.thermo import CoolPropProperties


def test_nonclosing_source_partition_and_invalid_observation_are_rejected():
    with pytest.raises(ValueError, match="conserve"):
        MassPartition(1.0, 0.5, 0.1, 0.1)
    with pytest.raises(ValueError, match="Nonfinite"):
        TimeSeries(np.array([0., 1.]), np.array([[1.], [np.nan]]), ("PT",), ("Pa",),
                   np.ones((2, 1), bool), "experiment-1", Origin.MEASURED, "source-1", ("pressure",))


def test_observation_clock_and_owned_arrays():
    values = np.array([[1.], [np.nan]])
    series = TimeSeries(np.array([0., 1.]), values, ("PT",), ("Pa",),
                        np.array([[True], [False]]), "experiment-1", Origin.MEASURED, "source-1", ("pressure",))
    values[0, 0] = 100
    assert series.values[0, 0] == 1
    with pytest.raises(ValueError):
        series.values[0, 0] = 2


@pytest.mark.parametrize("fluid,pressure,temperature", [
    ("Hydrogen", 70e6, 300), ("Hydrogen", 1e5, 300), ("ParaHydrogen", 150e3, 22),
])
def test_eos_flash_roundtrip_and_enthalpy_identity(fluid, pressure, temperature):
    provider = CoolPropProperties(fluid)
    state = provider.state_pt(pressure, temperature)
    # Dense-gas EOS inversion has finite numerical precision; scale the ledger
    # check to specific energy while retaining a small absolute floor.
    assert abs(state.enthalpy_identity_residual_j_kg) < max(1e-6, 1e-9 * abs(state.enthalpy_j_kg))
    assert provider.state_ph(pressure, state.enthalpy_j_kg).temperature_k == pytest.approx(temperature, rel=1e-8)
    assert provider.state_ps(pressure, state.entropy_j_kg_k).temperature_k == pytest.approx(temperature, rel=1e-8)


def test_two_phase_state_and_hydrogen_spin_identity_are_explicit():
    normal = CoolPropProperties("Hydrogen")
    para = CoolPropProperties("ParaHydrogen")
    saturated = para.saturated(150e3, 0.25)
    assert saturated.phase == "two_phase"
    assert saturated.vapor_mass_fraction == pytest.approx(.25)
    assert saturated.cp_j_kg_k is None
    with pytest.raises(ValueError, match="bases differ"):
        normal.basis.require_compatible(para.basis)


def test_quality_roundoff_budget_is_explicit_and_preserves_raw_eos_value():
    strict = CoolPropProperties("ParaHydrogen")
    entropy = strict.state_pt(1e6, 22.).entropy_j_kg_k
    pressure = 144871.62322005248
    with pytest.raises(ValueError, match="roundoff budget exceeded"):
        strict.state_ps(pressure, entropy)
    selected = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    state = selected.state_ps(pressure, entropy)
    assert state.vapor_mass_fraction == 0.
    assert state.raw_vapor_mass_fraction < 0.
    assert abs(state.raw_vapor_mass_fraction) <= selected.quality_roundoff_tolerance
    with pytest.raises(ValueError, match="Quality roundoff tolerance"):
        CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=.1)
