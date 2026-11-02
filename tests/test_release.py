"""Independent ideal-gas formulas plus real-fluid phase and source-boundary checks."""

import math
from dataclasses import replace

import numpy as np
import pytest

from h2physics.adapters.lh2dt import Lh2dtBulkNozzleOutflow, to_lh2dt_state
from h2physics.core import PropertyBasis, ThermoState
from h2physics.release import (
    HomogeneousIsentropicNozzle,
    NozzleOpening,
    NozzleSearch,
    SourceHistory,
    SourceLocation,
)


class IdealGas:
    """Test oracle only: constant-cp gas, with a deliberately shifted energy zero."""

    basis = PropertyBasis("test-gas", "ideal-gas-test-reference")
    gas_constant = 4124.
    gamma = 1.4
    cp = gamma * gas_constant / (gamma - 1)

    def state_pt(self, pressure, temperature):
        density = pressure / (self.gas_constant * temperature)
        enthalpy = self.cp * temperature - 2e6
        return ThermoState(self.basis, pressure, temperature, density, enthalpy,
                           enthalpy - pressure/density,
                           self.cp * math.log(temperature / 300.)
                           - self.gas_constant * math.log(pressure / 1e5), "gas")

    def state_ps(self, pressure, entropy):
        temperature = 300 * math.exp((entropy + self.gas_constant * math.log(pressure / 1e5))/self.cp)
        return self.state_pt(pressure, temperature)


def opening():
    return NozzleOpening.circular("hole-1", .005, effective_area_factor=.8,
                                  area_basis_id="test-effective-area")


@pytest.mark.parametrize("back_ratio", [.01, .4,
                                         (2/2.4)**3.5 * (1-2e-5), (2/2.4)**3.5,
                                         (2/2.4)**3.5 * (1+2e-5), .6, .9, .99999])
def test_ideal_gas_analytical_choked_and_backpressure_endpoints(back_ratio):
    provider = IdealGas()
    state = provider.state_pt(5e6, 300.)
    gamma, gas_constant = provider.gamma, provider.gas_constant
    critical_ratio = (2/(gamma + 1))**(gamma/(gamma - 1))
    ratio = max(back_ratio, critical_ratio)
    expected_flux = state.pressure_pa * math.sqrt(
        2 * gamma / ((gamma - 1) * gas_constant * state.temperature_k)
        * (ratio**(2/gamma) - ratio**((gamma + 1)/gamma)))
    result = HomogeneousIsentropicNozzle(provider).solve(
        state, back_pressure_pa=state.pressure_pa * back_ratio, opening=opening())
    assert result.mass_flux_kg_m2_s == pytest.approx(expected_flux, rel=1e-8)
    assert result.exit_state.pressure_pa == pytest.approx(state.pressure_pa * ratio, rel=1e-6)
    assert result.regime == ("choked" if back_ratio < critical_ratio else "back_pressure_limited")
    assert result.energy_residual_w == pytest.approx(0., abs=1e-8)
    assert result.mass_flow_kg_s == pytest.approx(expected_flux * opening().effective_area_m2(1.))
    assert result.diagnostics.grid_refinements >= 1
    assert result.exit_state.entropy_j_kg_k == pytest.approx(state.entropy_j_kg_k, abs=1e-10)


def test_closed_reverse_pressure_and_area_scaling():
    provider = IdealGas()
    model = HomogeneousIsentropicNozzle(provider)
    state = provider.state_pt(5e6, 300.)
    full = model.solve(state, back_pressure_pa=1e5, opening=opening())
    half = model.solve(state, back_pressure_pa=1e5, opening=opening(), opening_fraction=.5)
    assert half.mass_flow_kg_s == pytest.approx(full.mass_flow_kg_s/2)
    assert half.effective_area_thrust_n == pytest.approx(full.effective_area_thrust_n/2)
    for back, fraction, regime in ((1e5, 0., "closed"), (5e6, 1., "no_forward_pressure"),
                                   (6e6, 1., "no_forward_pressure")):
        result = model.solve(state, back_pressure_pa=back, opening=opening(), opening_fraction=fraction)
        assert result.regime == regime
        assert result.exit_state is None and result.mass_flow_kg_s == 0
        assert result.energy_residual_w == result.effective_area_thrust_n == 0


def test_basis_path_and_geometry_failures_are_not_silently_skipped():
    provider = IdealGas()
    state = provider.state_pt(5e6, 300.)
    model = HomogeneousIsentropicNozzle(provider)
    with pytest.raises(ValueError, match="bases differ"):
        model.solve(replace(state, basis=PropertyBasis("other", "other")),
                    back_pressure_pa=1e5, opening=opening())
    with pytest.raises(ValueError, match="inconsistent"):
        model.solve(replace(state, enthalpy_j_kg=state.enthalpy_j_kg + 500),
                    back_pressure_pa=1e5, opening=opening())
    with pytest.raises(ValueError, match="Opening fraction"):
        model.solve(state, back_pressure_pa=1e5, opening=opening(), opening_fraction=1.1)
    with pytest.raises(ValueError, match="factor"):
        NozzleOpening("hole", .01, 1.1, "test")
    with pytest.raises(ValueError, match="refinement"):
        NozzleSearch(maximum_refinements=0)

    class HoleProvider(IdealGas):
        def state_ps(self, pressure, entropy):
            if 2e5 < pressure < 4e5:
                raise ValueError("deliberate EOS-domain hole")
            return super().state_ps(pressure, entropy)

    with pytest.raises(ValueError, match="EOS-domain hole"):
        HomogeneousIsentropicNozzle(HoleProvider()).solve(state, back_pressure_pa=1e5, opening=opening())


def test_real_hydrogen_gas_liquid_saturated_and_two_phase():
    pytest.importorskip("CoolProp")
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("ParaHydrogen", quality_roundoff_tolerance=1e-8)
    model = HomogeneousIsentropicNozzle(provider)
    states = [provider.state_pt(5e6, 300.), provider.state_pt(1e6, 22.),
              *(provider.saturated(5e5, quality) for quality in (0., .2, 1.))]
    with pytest.raises(ValueError, match="vapor fraction is inconsistent"):
        model.solve(replace(states[3], vapor_mass_fraction=.8),
                    back_pressure_pa=101325., opening=opening())
    roundoff_diagnostics = []
    for state in states:
        result = model.solve(state, back_pressure_pa=101325., opening=opening())
        assert result.mass_flow_kg_s > 0
        assert result.exit_state.pressure_pa >= 101325.
        assert abs(result.energy_residual_w) < 1e-7
        assert result.exit_state.entropy_j_kg_k == pytest.approx(state.entropy_j_kg_k, abs=1e-4)
        assert result.diagnostics.relative_flux_change <= model.search.relative_flux_tolerance
        assert result.diagnostics.relative_pressure_change <= model.search.relative_pressure_tolerance
        roundoff_diagnostics.append(result.diagnostics.maximum_quality_roundoff)
        if state.vapor_mass_fraction is not None:
            assert result.exit_state.vapor_mass_fraction is not None
    assert max(roundoff_diagnostics) > 0.


def test_source_history_retains_clock_spatial_reference_and_termination():
    provider = IdealGas()
    model = HomogeneousIsentropicNozzle(provider)
    state = provider.state_pt(5e6, 300.)
    flowing = model.solve(state, back_pressure_pa=1e5, opening=opening())
    closed = model.solve(state, back_pressure_pa=1e5, opening=opening(), opening_fraction=0.)
    location = SourceLocation("tank-A/nozzle-B", "experiment-clock", "site-ENU", (1., 2., 3.), (1., 0., 0.))
    history = SourceHistory(location, (0., 1.), (flowing, closed), "isolation")
    series = history.mass_flow_series()
    assert series.clock_id == "experiment-clock"
    assert series.source_id == "tank-A/nozzle-B"
    assert not series.values.flags.writeable
    np.testing.assert_allclose(series.values[:, 0], [flowing.mass_flow_kg_s, 0.])
    assert not hasattr(history, "ground_liquid_kg_s")
    with pytest.raises(ValueError, match="closed final"):
        SourceHistory(location, (0., 1.), (flowing, flowing), "isolation")
    with pytest.raises(ValueError, match="unit vector"):
        replace(location, direction_unit=(2., 0., 0.))


def test_native_bulk_callback_uses_upstream_total_energy_and_no_stage_history():
    from types import SimpleNamespace

    provider = IdealGas()
    state = provider.state_pt(5e6, 300.)
    native = to_lh2dt_state(state, expected_basis=provider.basis, factory=SimpleNamespace)
    callback = Lh2dtBulkNozzleOutflow(HomogeneousIsentropicNozzle(provider), opening(),
                                    back_pressure_pa=lambda _time: 1e5,
                                    opening_fraction=lambda time: 1. if time < 2 else 0.,
                                    flow_factory=SimpleNamespace)
    result = callback.sample(0., native)
    flow, = callback(0., native)
    assert flow.mass_flow_kg_s == -result.mass_flow_kg_s
    assert flow.specific_enthalpy_J_kg == state.enthalpy_j_kg
    assert callback(2., native) == ()
    assert not hasattr(callback, "history")


def test_real_gas_flat_peak_is_stable_across_independent_initial_grids():
    pytest.importorskip("CoolProp")
    from h2physics.thermo import CoolPropProperties

    provider = CoolPropProperties("Hydrogen")
    # Numerical regression state reconstructed in the open DisCha comparison:
    # https://doi.org/10.35097/1187 . These are not a raw-source data fixture.
    for pressure, temperature in ((5957812.127680701, 238.31506629999998),
                                   (4517335.000498776, 236.41622040000001)):
        state = provider.state_pt(pressure, temperature)
        results = [HomogeneousIsentropicNozzle(provider, search=NozzleSearch(initial_grid_points=n)).solve(
            state, back_pressure_pa=101325., opening=opening()) for n in (17, 33, 65)]
        pressures = [result.exit_state.pressure_pa for result in results]
        fluxes = [result.mass_flux_kg_m2_s for result in results]
        assert all(result.diagnostics.sonic_refinements > 0 for result in results)
        assert (max(pressures)-min(pressures))/np.mean(pressures) < 1e-6
        assert (max(fluxes)-min(fluxes))/np.mean(fluxes) < 1e-9
