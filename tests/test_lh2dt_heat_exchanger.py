"""Actual native coupled cores, analytic wall limits and independent EOS energy."""

import importlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import brentq

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_heat_exchanger import (
    FiniteHeatExchangerSide,
    HeatExchangerCapabilityError,
    HeatExchangerCoupling,
    HeatExchangerDomain,
    HeatExchangerIntegrationError,
    Lh2dtFiniteHeatExchanger,
)
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.core import Origin
from h2physics.thermo import CoolPropProperties


def modules():
    target = Path(__file__).resolve().parents[1]/"artifacts/native_packages"
    if not (target/"lh2dt/dynamic_vaporizer.py").exists():
        pytest.skip("The separately installed native LH2DT snapshot is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    pytest.importorskip("CoolProp")
    return SimpleNamespace(vaporizer=importlib.import_module("lh2dt.dynamic_vaporizer"),
        dynamic=importlib.import_module("lh2dt.dynamic_network"),
        network=importlib.import_module("lh2dt.network"),
        properties=importlib.import_module("lh2dt.properties"))


def case(*, conductance=2., fluid_wall=(5., 6.), wall_capacity=(100., 150.),
         temperatures=(400., 250.), wall_temperatures=None, maximum_heat=1e6,
         network_factory=None):
    native = modules()
    sides = []
    for i, (name, fluid, pressure, volume) in enumerate((
            ("left", "Hydrogen", 3e5, .01), ("right", "ParaHydrogen", 2e5, .02))):
        direct = CoolPropProperties(fluid)
        properties = Lh2dtLowLevelProperties(direct, state_factory=native.properties.ThermoState)
        bridge = Lh2dtProperties(properties, reference_id=direct.basis.reference_id)
        core = native.vaporizer.DynamicVaporizer(volume, wall_capacity[i], fluid_wall[i],
            300., conductance, maximum_heat, properties)
        state = core.initialize(properties.from_pT(pressure, temperatures[i]),
            wall_temperature_K=None if wall_temperatures is None else wall_temperatures[i])
        domain = HeatExchangerDomain(200., 650., 1e3, 1e7, 1e-8,
                                    ("gas", "supercritical_gas", "supercritical"))
        sides.append(FiniteHeatExchangerSide(name, core, state, bridge, domain,
                                            "authored-finite-inventory-verification"))
    exchanger = Lh2dtFiniteHeatExchanger(*sides,
        HeatExchangerCoupling(conductance, "authored-wall-conductance", Origin.SYNTHETIC,
                              "LH2DT:b2f276333c1b1793c39f25763703d196d36742ec"),
        native_side_node_factory=native.dynamic.dynamic_vaporizer_node,
        native_network_factory=network_factory or native.network.SteadyNetwork,
        native_simulator_factory=native.dynamic.DynamicNetworkSimulator, equipment_id="authored-HX")
    return exchanger, native


def run(exchanger, *, duration=20., step=.5):
    return exchanger.run(duration_s=duration, maximum_step_s=step,
                         start_time_s=100., clock_id="authored-HX-clock")


def assert_balances(trace):
    for point in trace.points:
        assert abs(point.global_energy_residual_j) < 1e-5
        assert abs(point.integrated_coupling_residual_j) < 1e-8
        for side in point.sides.values():
            assert abs(side.balance.mass_residual_kg) < 1e-13
            assert abs(side.balance.energy_residual_j) < 1e-5


def test_two_finite_fluids_and_both_walls_respond_with_separate_bases():
    exchanger, native = case()
    result = run(exchanger)
    first, last = result.points[0], result.points[-1]
    assert last.sides["left"].fluid.temperature_k < first.sides["left"].fluid.temperature_k
    assert last.sides["right"].fluid.temperature_k > first.sides["right"].fluid.temperature_k
    assert last.sides["left"].native_state.wall_temperature_K < 400.
    assert last.sides["right"].native_state.wall_temperature_K > 250.
    assert last.sides["left"].fluid.basis.spin_composition == "normal"
    assert last.sides["right"].fluid.basis.spin_composition == "para"
    assert last.sides["left"].fluid.basis != last.sides["right"].fluid.basis
    assert isinstance(result.native_simulator, native.dynamic.DynamicNetworkSimulator)
    assert all(isinstance(c, native.vaporizer.DynamicVaporizer) for c in result.native_components)
    assert result.native_components == (exchanger.left.native_component, exchanger.right.native_component)
    assert isinstance(result.native_composite_node, native.dynamic.DynamicNodeModel)
    for point in result.points[1:]:
        assert point.native_step.states[exchanger.equipment_id] is point.native_composite_state
        assert point.sides["left"].native_state is point.native_composite_state.left
        assert isinstance(point.sides["right"].native_derivative,
                          native.vaporizer.DynamicVaporizerDerivative)
        assert point.native_step.network_solution.link_flows == {}
    assert_balances(result)


def test_zero_wall_conductance_preserves_each_uniform_side_independently():
    exchanger, _ = case(conductance=0.)
    result = run(exchanger, duration=5., step=.25)
    for name in ("left", "right"):
        a, b = result.points[0].sides[name], result.points[-1].sides[name]
        assert a.inventory == b.inventory
        assert b.fluid.temperature_k == pytest.approx(a.fluid.temperature_k, abs=1e-9)
        assert b.balance.boundary_energy_j == 0.
    assert_balances(result)


def test_equal_temperature_different_fluids_has_no_coupling_or_reference_conversion():
    exchanger, _ = case(temperatures=(300., 300.))
    result = run(exchanger, duration=3., step=.25)
    assert all(abs(s.coupling_heat_into_side_w) < 1e-9 for p in result.points for s in p.sides.values())
    assert all(abs(s.fluid.temperature_k-300.) < 1e-9 for p in result.points for s in p.sides.values())
    assert_balances(result)


def test_actual_native_two_wall_limit_matches_analytic_exponential():
    exchanger, _ = case(fluid_wall=(0., 0.))
    result = run(exchanger, duration=30., step=.25)
    elapsed = result.time_s-100.
    cl, cr, g = 100., 150., 2.
    mean = (cl*400.+cr*250.)/(cl+cr)
    difference = 150.*np.exp(-g*(1/cl+1/cr)*elapsed)
    expected_l = mean+cr/(cl+cr)*difference
    expected_r = mean-cl/(cl+cr)*difference
    np.testing.assert_allclose([p.sides["left"].native_state.wall_temperature_K for p in result.points],
                              expected_l, atol=1e-8)
    np.testing.assert_allclose([p.sides["right"].native_state.wall_temperature_K for p in result.points],
                              expected_r, atol=1e-8)
    np.testing.assert_allclose([p.sides["left"].fluid.temperature_k for p in result.points], 400., atol=1e-8)
    assert result.points[-1].sides["left"].balance.boundary_energy_j == pytest.approx(
        cl*(expected_l[-1]-400.), abs=1e-6)
    assert_balances(result)


def test_independent_native_fixed_density_equilibrium_uses_all_four_inventories():
    cp = pytest.importorskip("CoolProp.CoolProp")
    coolprop = pytest.importorskip("CoolProp")
    exchanger, _ = case()
    native_states = [coolprop.AbstractState("HEOS", fluid) for fluid in ("Hydrogen", "ParaHydrogen")]
    initial_total = sum(s.initial_native_state.internal_energy_J
        +s.native_component.wall_heat_capacity*s.initial_native_state.wall_temperature_K
        for s in (exchanger.left, exchanger.right))

    def energy_at(temperature):
        energy = 0.
        for side, native in zip((exchanger.left, exchanger.right), native_states, strict=True):
            mass = side.initial_native_state.mass_kg
            native.update(cp.DmassT_INPUTS, mass/side.native_component.fluid_volume, temperature)
            energy += mass*native.umass()+side.native_component.wall_heat_capacity*temperature
        return energy-initial_total

    equilibrium = brentq(energy_at, 250., 400., xtol=1e-10)
    result = run(exchanger, duration=1000., step=.5)
    for side in result.points[-1].sides.values():
        assert side.fluid.temperature_k == pytest.approx(equilibrium, abs=1e-5)
        assert side.native_state.wall_temperature_K == pytest.approx(equilibrium, abs=1e-5)
    assert_balances(result)


def test_finite_initial_wall_and_fluid_storage_can_reverse_heat_direction():
    exchanger, _ = case(fluid_wall=(5., 5.), wall_capacity=(10., 10.),
        temperatures=(250., 450.), wall_temperatures=(400., 300.))
    result = run(exchanger, duration=20., step=.1)
    heat = np.array([p.sides["left"].coupling_heat_into_side_w for p in result.points])
    assert heat[0] < 0. and max(heat) > 0.
    assert min(heat) < -100. and max(heat) > 20.
    assert_balances(result)


def test_native_fluid_wall_caps_remain_native_and_conservative():
    exchanger, _ = case(fluid_wall=(50., 50.), wall_capacity=(10., 10.),
        temperatures=(250., 450.), wall_temperatures=(400., 300.), maximum_heat=100.)
    result = run(exchanger, duration=.1, step=.01)
    initial = result.points[0]
    assert initial.sides["left"].fluid_wall_heat_into_fluid_w == 100.
    assert initial.sides["right"].fluid_wall_heat_into_fluid_w == -100.
    assert_balances(result)


def test_one_native_simultaneous_time_refinement_and_independent_sampled_heat():
    coarse = run(case()[0], step=.5)
    fine = run(case()[0], step=.125)
    for side in ("left", "right"):
        a, b = coarse.points[-1].sides[side], fine.points[-1].sides[side]
        assert abs(a.fluid.temperature_k-b.fluid.temperature_k) < 1e-3
        assert abs(a.native_state.wall_temperature_K-b.native_state.wall_temperature_K) < 1e-3
        sampled = np.trapezoid([p.sides[side].coupling_heat_into_side_w for p in fine.points], fine.time_s)
        assert abs(sampled-b.balance.boundary_energy_j) < .01
    assert_balances(coarse)
    assert_balances(fine)


def test_clock_and_native_identity_are_explicit_and_results_are_immutable():
    exchanger, _ = case()
    result = run(exchanger, duration=2., step=.25)
    assert result.clock_id == "authored-HX-clock"
    assert result.time_s[0] == 100. and result.time_s[-1] == 102.
    assert result.evaluated_clock_bounds_s == (100., 102.)
    assert not result.time_s.flags.writeable
    with pytest.raises(TypeError):
        result.points[0].sides["third-fluid"] = result.points[0].sides["left"]
    assert result.native_network.links == [] and result.native_network.junctions == {}


def test_declared_gas_wall_bases_inventory_domain_and_conductance_are_not_repaired():
    exchanger, _ = case()
    side = exchanger.left
    with pytest.raises(ValueError, match="bases differ"):
        replace(side, bridge=Lh2dtProperties(side.bridge.native, reference_id="foreign-energy-reference"))
    with pytest.raises(ValueError, match="Wall-to-wall"):
        HeatExchangerCoupling(-1., "authored", Origin.SYNTHETIC, "pinned-native")
    with pytest.raises(ValueError, match="resolved conductance"):
        HeatExchangerCoupling(1., "authored", Origin.UNRESOLVED, "pinned-native")
    with pytest.raises(ValueError, match="domain"):
        altered = replace(side, domain=replace(side.domain, allowed_phases=("liquid",)))
        Lh2dtFiniteHeatExchanger(altered, exchanger.right, exchanger.coupling,
            native_side_node_factory=exchanger.native_side_node_factory,
            native_network_factory=exchanger.native_network_factory,
            native_simulator_factory=exchanger.native_simulator_factory, equipment_id="invalid-HX")
    with pytest.raises(ValueError, match="minimum"):
        altered = replace(side, domain=replace(side.domain,
            minimum_inventory_kg=2*side.initial_native_state.mass_kg))
        Lh2dtFiniteHeatExchanger(altered, exchanger.right, exchanger.coupling,
            native_side_node_factory=exchanger.native_side_node_factory,
            native_network_factory=exchanger.native_network_factory,
            native_simulator_factory=exchanger.native_simulator_factory, equipment_id="invalid-HX")
    side.native_component.ambient_UA = 3.
    with pytest.raises(HeatExchangerCapabilityError, match="configuration changed"):
        run(exchanger)


def test_each_native_derivative_must_close_before_global_errors_can_cancel(monkeypatch):
    exchanger, _ = case()
    original = exchanger.left.native_component.derivative_from_flows

    def wrong(*args, **kwargs):
        native = original(*args, **kwargs)
        return replace(native, internal_energy_W=native.internal_energy_W+1.)

    monkeypatch.setattr(exchanger.left.native_component, "derivative_from_flows", wrong)
    with pytest.raises(HeatExchangerIntegrationError, match="derivative does not close") as failed:
        run(exchanger, duration=1.)
    assert failed.value.native_components[0] is exchanger.left.native_component
    assert failed.value.last_trial[1].left is exchanger.left.initial_native_state


def test_unqualified_external_network_boundaries_are_rejected():
    native = modules()

    def extra_boundary(*, properties):
        network = native.network.SteadyNetwork(properties=properties)
        network.add_boundary("unqualified-extra-bath", properties.from_pT(1e5, 300.))
        return network

    exchanger, _ = case(network_factory=extra_boundary)
    with pytest.raises(HeatExchangerIntegrationError, match="closed thermal pair"):
        run(exchanger, duration=1.)
