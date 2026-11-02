from dataclasses import replace
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.thermo import CoolPropProperties


@pytest.mark.parametrize("pressure,temperature", [(300000., 20.), (300000., 28.), (5000000., 300.)])
def test_optional_inverse_flashes_return_the_same_state(pressure, temperature):
    pytest.importorskip("CoolProp")
    p = CoolPropProperties("ParaHydrogen")
    state = p.state_pt(pressure, temperature)
    for result in (p.state_pu(pressure, state.internal_energy_j_kg),
                   p.state_prho(pressure, state.density_kg_m3),
                   p.state_rho_u(state.density_kg_m3, state.internal_energy_j_kg)):
        assert result.temperature_k == pytest.approx(temperature, rel=1e-8)
        assert result.pressure_pa == pytest.approx(pressure, rel=1e-8)
        assert result.basis == state.basis


def test_native_facade_has_no_automatic_fallback_and_retains_explicit_quality_adjustment():
    pytest.importorskip("CoolProp")
    p = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    bridge = Lh2dtLowLevelProperties(p, state_factory=SimpleNamespace)
    entropy = p.state_pt(1e6, 22.).entropy_j_kg_k
    state = bridge.from_ps(144871.62322005248, entropy)
    assert state.quality == 0.
    assert bridge.maximum_quality_adjustment > 0 and bridge.quality_adjustment_count == 1
    assert bridge.last_adjusted_state.raw_vapor_mass_fraction < 0.
    with pytest.raises(AttributeError):
        bridge.unsupported_native_method()
    mixed = p.saturated(300000., .2)
    with pytest.raises(ValueError, match="mixture viscosity"):
        p.phase_viscosity(mixed)
    with pytest.raises(ValueError, match="mixture viscosity"):
        p.phase_viscosity(replace(mixed, vapor_mass_fraction=None))
