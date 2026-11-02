from math import pi, sqrt
from types import SimpleNamespace

import pytest

from h2physics.adapters.lh2dt_hydraulics import Lh2dtDarcyPipe
from h2physics.hydraulics import DarcyGeometry, HydraulicConvergenceError, solve_darcy_flow


@pytest.mark.parametrize("pressure", [.1, 10., 1000.])
def test_one_root_kernel_matches_the_independent_poiseuille_limit(pressure):
    geometry = DarcyGeometry(1., .001, 0.)
    result = solve_darcy_flow(geometry, density_kg_m3=1., viscosity_pa_s=1e-5,
        driving_pressure_pa=pressure, friction_law=lambda reynolds, roughness: 64./reynolds)
    expected = pi*.001**4*pressure/(128.*1e-5)
    assert result.mass_flow_kg_s == pytest.approx(expected, rel=1e-10)
    assert abs(result.momentum_residual_pa) < 1e-7 and result.root_converged


def test_exact_upper_endpoint_has_defined_iteration_metadata():
    geometry = DarcyGeometry(1., .01, 0.)
    result = solve_darcy_flow(geometry, density_kg_m3=1000., viscosity_pa_s=.001,
        driving_pressure_pa=100., friction_law=lambda reynolds, roughness: .02)
    assert result.velocity_m_s == pytest.approx(sqrt(2.*100./(1000.*.02*100.)))
    assert result.iterations >= 0 and result.momentum_residual_pa == pytest.approx(0., abs=1e-10)


def test_a_root_flag_does_not_accept_a_gap_in_a_discontinuous_constitutive_law():
    # At Re=2000 the authored law jumps between pressure losses 40 and 160 Pa.
    def discontinuous(reynolds, roughness):
        return .02 if reynolds < 2000. else .08

    with pytest.raises(HydraulicConvergenceError) as caught:
        solve_darcy_flow(DarcyGeometry(1., .01, 0.), density_kg_m3=1000., viscosity_pa_s=.001,
                         driving_pressure_pa=100., friction_law=discontinuous)
    assert caught.value.result.root_converged
    assert abs(caught.value.result.momentum_residual_pa) > 50.


def test_native_result_bridge_preserves_reverse_upstream_energy_and_live_parameters():
    props = object()
    native = SimpleNamespace(properties=props, length=1., diameter=.001, roughness=0.,
                              local_k=0., dz=0., heat=.001)
    component = Lh2dtDarcyPipe(native, SimpleNamespace(native=props), viscosity_reader=lambda state: 1e-5,
        friction_law=lambda reynolds, roughness: 64./reynolds, friction_law_id="authored-laminar-limit",
        result_factory=lambda **fields: SimpleNamespace(**fields))
    left = SimpleNamespace(pressure_Pa=100000., density_kg_m3=1., specific_enthalpy_J_kg=1000.)
    right = SimpleNamespace(pressure_Pa=101000., density_kg_m3=1., specific_enthalpy_J_kg=2000.)
    result = component.evaluate(left, right)
    assert result.mass_flow_kg_s < 0. and result.upstream_side == "right"
    assert abs(result.mass_flow_kg_s)*(result.outlet_specific_enthalpy_J_kg-2000.) == pytest.approx(.001)
    assert abs(result.momentum_residual_Pa) < 1e-7
    native.heat = .002
    changed = component.evaluate(left, right)
    assert abs(changed.mass_flow_kg_s)*(changed.outlet_specific_enthalpy_J_kg-2000.) == pytest.approx(.002)
    with pytest.raises(ValueError, match="stored thermal"):
        component.evaluate(left, left)


def test_continuous_library_correlation_closes_the_transition_region():
    friction = pytest.importorskip("fluids.friction").Churchill_1977
    assert friction(100., .001) == pytest.approx(64./100., rel=1e-12)
    geometry = DarcyGeometry(1., .001, 1e-6)
    for pressure in (150., 200., 250., 300., 400.):
        result = solve_darcy_flow(geometry, density_kg_m3=72., viscosity_pa_s=1.45e-5,
                                 driving_pressure_pa=pressure, friction_law=friction)
        assert abs(result.momentum_residual_pa) < 1e-7
        assert result.darcy_friction_factor == pytest.approx(friction(result.reynolds_number, .001))
