"""Actual native cooling, recovered phase, cold-side clocks and inventories."""

import importlib
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_dynamics import Lh2dtDynamicEquipment
from h2physics.adapters.lh2dt_equipment import Lh2dtEquipmentNetwork
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_reliquefier import (
    ColdSideBoundary,
    Lh2dtDynamicReliquefier,
    Lh2dtSteadyReliquefier,
    ReliquefactionDomain,
    ReliquefierClosureError,
    liquid_mass_fraction,
)
from h2physics.core import Origin


def api():
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
    if not (target / "lh2dt/dynamic_reliquefier.py").is_file():
        pytest.skip("Separately installed optional LH2DT snapshot is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return importlib.import_module("lh2dt")


def domain(**changes):
    return replace(ReliquefactionDomain(1e4, 10e6, 14.1, 1000,
        "authored-synthetic-domain-not-qualified-equipment"), **changes)


def properties(fluid="ParaHydrogen"):
    native = api()
    from h2physics.thermo import CoolPropProperties

    direct = CoolPropProperties(fluid, quality_roundoff_tolerance=1e-8)
    facade = Lh2dtLowLevelProperties(direct, state_factory=native.ThermoState)
    return direct, facade, Lh2dtProperties(facade, reference_id=direct.basis.reference_id)


def steady(capacity=100., fluid="ParaHydrogen"):
    direct, facade, bridge = properties(fluid)
    return direct, Lh2dtSteadyReliquefier(api().Reliquefier(capacity, facade), bridge,
        state_factory=api().ThermoState, domain=domain(), component_id="cold-recovery")


def dynamic(*, fluid_wall_ua=2., cold_ua=1., maximum=100., cold=18., wall_capacity=2.):
    direct, facade, bridge = properties()
    boundary = ColdSideBoundary("absolute-cold-clock", 10., 30., cold,
                                "authored-cold-reservoir", Origin.SYNTHETIC)
    native = api().DynamicReliquefier(.001, wall_capacity, fluid_wall_ua,
        18., cold_ua, maximum, facade)
    return direct, Lh2dtDynamicReliquefier(native, bridge, state_factory=api().ThermoState,
                                          domain=domain(), cold_boundary=boundary)


def sealed_run(model, initial, duration, step, *, start=10.):
    native = api()
    binding = model.inventory_binding("cold-volume", initial, node_factory=native.dynamic_vaporizer_node)
    graph = Lh2dtEquipmentNetwork(native.SteadyNetwork(model.bridge.native), model.bridge,
                                  state_factory=native.ThermoState)
    graph.add_boundary("cold-volume", model.fluid(initial))
    run = Lh2dtDynamicEquipment(graph, {"cold-volume": binding.inventory_node},
        simulator_factory=native.DynamicNetworkSimulator).run(
            duration, step, start_time_s=start, clock_id=model.cold_boundary.clock_id)
    return binding, run


@pytest.mark.parametrize("fraction", [.1, .5, 1.])
def test_actual_native_saturated_latent_heat_recovers_the_analytic_liquid_fraction(fraction):
    direct, _ = steady()
    liquid, vapor = direct.saturated(2e5, 0), direct.saturated(2e5, 1)
    flow = .001
    capacity = flow*(vapor.enthalpy_j_kg-liquid.enthalpy_j_kg)*fraction
    _, model = steady(capacity)
    result = model.evaluate(vapor, outlet_pressure_pa=2e5, mass_flow_kg_s=flow)
    assert result.outlet_liquid_mass_fraction == pytest.approx(fraction, abs=2e-9)
    assert result.liquid_outflow_kg_s == pytest.approx(flow*fraction, abs=2e-12)
    assert result.net_liquid_production_kg_s == pytest.approx(flow*fraction, abs=2e-12)
    assert result.power.heat_w == pytest.approx(-capacity, abs=1e-8)
    assert abs(result.energy_residual_w) < 1e-7
    assert result.capacity_limited is (fraction < 1)
    assert type(result.native_result).__module__ == "lh2dt.reliquefier"


def test_existing_inlet_liquid_is_not_claimed_as_new_condensation():
    direct, model = steady(1e5)
    inlet = direct.saturated(2e5, .3)
    result = model.evaluate(inlet, outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    assert result.inlet_liquid_mass_fraction == .7
    assert result.outlet_liquid_mass_fraction == pytest.approx(1, abs=1e-10)
    assert result.net_liquid_production_kg_s == pytest.approx(.0003, abs=1e-12)
    assert result.liquid_outflow_kg_s == pytest.approx(.001, abs=1e-12)


def test_capacity_limited_superheated_cooling_does_not_force_saturation():
    direct, model = steady(1.)
    inlet = direct.state_pt(2e5, 80)
    result = model.evaluate(inlet, outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    assert result.outlet.vapor_mass_fraction is None
    assert result.outlet_liquid_mass_fraction == 0
    assert result.net_liquid_production_kg_s == 0
    assert result.capacity_limited


@pytest.mark.parametrize("fluid,spin", [("Hydrogen", "normal"), ("ParaHydrogen", "para"),
                                      ("OrthoHydrogen", "ortho")])
def test_actual_spin_specific_recovery_references_are_preserved(fluid, spin):
    direct, model = steady(100., fluid)
    result = model.evaluate(direct.saturated(2e5, 1), outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    assert result.outlet.basis == direct.basis
    assert result.outlet.basis.spin_composition == spin
    assert result.power.shaft_work_w == 0


def test_target_quality_zero_duty_and_already_liquid_native_behavior():
    direct, model = steady(1e4)
    vapor = direct.saturated(2e5, 1)
    zero = model.evaluate(vapor, outlet_pressure_pa=2e5, mass_flow_kg_s=.001, target_quality=1)
    assert abs(zero.power.heat_w) < 1e-8
    assert zero.outlet_liquid_mass_fraction == pytest.approx(0, abs=1e-10)
    liquid = direct.state_pt(2e5, 19)
    result = model.evaluate(liquid, outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    assert result.net_liquid_production_kg_s == 0
    assert result.power.heat_w == 0


@pytest.mark.parametrize("pressure,flow,quality", [(2e5, 0, 0), (2e5, -.001, 0),
    (2e5, True, 0), (2e5, .001, 1.1), (1., .001, 0), (2e6, .001, 0), (3e5, .001, 0)])
def test_steady_native_unavailable_direction_zero_flow_pressure_and_quality_are_rejected(pressure, flow, quality):
    direct, model = steady()
    with pytest.raises(ValueError):
        model.evaluate(direct.state_pt(2e5, 35), outlet_pressure_pa=pressure,
                       mass_flow_kg_s=flow, target_quality=quality)


def test_wrong_reference_spin_and_forged_state_are_rejected():
    direct, model = steady()
    inlet = direct.state_pt(2e5, 35)
    for basis in (replace(inlet.basis, reference_id="arbitrary-zero"),
                  replace(inlet.basis, spin_composition="normal")):
        with pytest.raises(ValueError, match="bases differ"):
            model.evaluate(replace(inlet, basis=basis), outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    with pytest.raises(ValueError, match="inconsistent"):
        model.evaluate(replace(inlet, density_kg_m3=inlet.density_kg_m3*2),
                       outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    with pytest.raises(ValueError, match="vapor quality"):
        model.evaluate(replace(direct.saturated(2e5, .3), vapor_mass_fraction=.8),
                       outlet_pressure_pa=2e5, mass_flow_kg_s=.001)


def test_failed_native_heat_and_phase_summary_are_retained():
    direct, model = steady()
    original = model.native.evaluate
    model.native.evaluate = lambda *a, **k: replace(original(*a, **k), liquefied_mass_fraction=.9)
    with pytest.raises(ReliquefierClosureError, match="actual outlet phase") as error:
        model.evaluate(direct.saturated(2e5, 1), outlet_pressure_pa=2e5, mass_flow_kg_s=.001)
    assert error.value.native.liquefied_mass_fraction == .9


def test_dynamic_native_step_keeps_fluid_wall_and_cold_reservoir_heat_distinct():
    direct, model = dynamic(fluid_wall_ua=20, cold_ua=20, maximum=5.)
    inlet = direct.state_pt(2e5, 35)
    initial = model.initialize(inlet, wall_temperature_k=25)
    rates = model.derivative(initial, inlet, 0, 0, time_s=10)
    assert rates.fluid_wall_heat_w == -5.
    assert rates.external_power.heat_w == -140.
    assert abs(rates.energy_residual_w) < 1e-10
    step = model.step(initial, inlet, 0, 0, time_s=10, time_step_s=.01)
    assert step.inventory.mass_kg == initial.mass_kg
    assert step.inventory.fluid_internal_energy_j < initial.internal_energy_J
    assert type(step.native).__module__ == "lh2dt.dynamic_vaporizer"
    assert step.native.derivative is step.final_rates.native


def test_zero_gradient_native_finite_state_remains_unchanged():
    direct, model = dynamic()
    inlet = direct.state_pt(2e5, 18)
    initial = model.initialize(inlet, wall_temperature_k=18)
    step = model.step(initial, inlet, 0, 0, time_s=10, time_step_s=.1)
    assert step.native.state.mass_kg == initial.mass_kg
    assert step.native.state.internal_energy_J == initial.internal_energy_J
    assert step.native.state.wall_temperature_K == pytest.approx(18, abs=1e-12)
    assert abs(step.final_rates.external_power.heat_w) < 1e-12


def test_native_warmer_reservoir_reverses_heat_without_clipping():
    direct, model = dynamic(fluid_wall_ua=20, cold_ua=20, maximum=5., cold=50.)
    inlet = direct.state_pt(2e5, 20)
    state = model.initialize(inlet, wall_temperature_k=25)
    rates = model.derivative(state, inlet, 0, 0, time_s=10)
    assert rates.fluid_wall_heat_w == 5
    assert rates.external_power.heat_w == rates.total_storage_rate_w == 500


def test_completed_native_step_outside_declared_domain_is_retained():
    direct, model = dynamic()
    inlet = direct.state_pt(2e5, 35)
    state = model.initialize(inlet, wall_temperature_k=25)
    model.domain = replace(model.domain, minimum_temperature_k=34.99)
    with pytest.raises(ReliquefierClosureError, match="declared reliquefaction domain") as failure:
        model.step(state, inlet, 0, 0, time_s=10, time_step_s=.01)
    assert failure.value.native.fluid.temperature_K < 34.99
    assert failure.value.native.state.mass_kg == state.mass_kg


def test_native_absolute_clock_wall_cooling_matches_independent_analytic_limit():
    direct, model = dynamic(fluid_wall_ua=0, cold=lambda t: 18+.1*(t-10))
    initial = model.initialize(direct.state_pt(2e5, 35), wall_temperature_k=30)
    binding, run = sealed_run(model, initial, 1., .05)
    final = run.steps[-1].native.states["cold-volume"]
    expected = 18+.1*(1-2)+(30-18+.1*2)*math.exp(-1/2)
    assert final.wall_temperature_K == pytest.approx(expected, abs=1e-7)
    assert final.mass_kg == initial.mass_kg
    assert final.internal_energy_J == initial.internal_energy_J
    assert run.start_time_s == 10 and run.steps[-1].time_s == 11
    assert binding.original_native_node.advance is binding.inventory_node.native_node.advance
    assert max(abs(s.balances["cold-volume"].energy_residual_j) for s in run.steps) < 1e-8
    with pytest.raises(ValueError, match="inventory-node"):
        model.step(initial, model.fluid(initial), 0, 0, time_s=10, time_step_s=.1)


def test_native_sealed_cooling_condenses_finite_inventory_without_forced_pressure():
    direct, model = dynamic(fluid_wall_ua=20, cold_ua=20, maximum=5., wall_capacity=2.)
    inlet = direct.saturated(2e5, 1)
    initial = model.initialize(inlet, wall_temperature_k=18)
    _, coarse = sealed_run(model, initial, 2., .04)
    _, fine = sealed_run(model, initial, 2., .02)
    last = fine.steps[-1]
    fluid = last.equipment.node_states["cold-volume"]
    assert 0 < liquid_mass_fraction(fluid) < 1
    assert fluid.pressure_pa < inlet.pressure_pa
    assert last.inventories["cold-volume"].mass_kg == initial.mass_kg
    assert last.inventories["cold-volume"].total_energy_j < fine.initial_inventories["cold-volume"].total_energy_j
    assert abs(last.balances["cold-volume"].energy_residual_j) < 1e-8
    final_native = last.native.states["cold-volume"]
    assert abs(final_native.internal_energy_J-initial.internal_energy_J+10) < 1e-8
    expected_wall = 18+5/20*(1-math.exp(-20/2*2))
    assert abs(final_native.wall_temperature_K-expected_wall) < 1e-7
    coarse_pressure = coarse.steps[-1].equipment.node_states["cold-volume"].pressure_pa
    assert abs(coarse_pressure/fluid.pressure_pa-1) < 1e-6


def test_cooling_off_preserves_internal_wall_exchange_and_zero_flow_is_not_empty():
    direct, model = dynamic(cold_ua=0.)
    inlet = direct.state_pt(2e5, 35)
    initial = model.initialize(inlet, wall_temperature_k=25)
    _, run = sealed_run(model, initial, .2, .02)
    final = run.steps[-1]
    assert final.balances["cold-volume"].external_heat_j == 0
    assert abs(final.inventories["cold-volume"].total_energy_j
               - run.initial_inventories["cold-volume"].total_energy_j) < 1e-8
    assert final.inventories["cold-volume"].fluid_internal_energy_j < initial.internal_energy_J
    assert final.inventories["cold-volume"].mass_kg > 0


def test_actual_finite_recovery_with_native_boundary_flow_closes_open_inventory():
    from h2physics.adapters.lh2dt_equipment import Lh2dtSharedValve
    from h2physics.equipment import BoundaryPower
    from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

    direct, model = dynamic(fluid_wall_ua=20, cold_ua=20, maximum=5.)
    initial = model.initialize(direct.saturated(2e5, 1), wall_temperature_k=18)
    native = api()
    binding = model.inventory_binding("cold-volume", initial, node_factory=native.dynamic_vaporizer_node)
    graph = Lh2dtEquipmentNetwork(native.SteadyNetwork(model.bridge.native), model.bridge,
                                  state_factory=native.ThermoState)
    for name, state in (("feed", direct.state_pt(2.2e5, 35)), ("cold-volume", model.fluid(initial)),
                        ("delivery", direct.state_pt(1.8e5, 25))):
        graph.add_boundary(name, state)
    for identifier, left, right in (("feed-valve", "feed", "cold-volume"),
                                     ("outlet-valve", "cold-volume", "delivery")):
        valve = Lh2dtSharedValve(HomogeneousIsentropicNozzle(direct), model.bridge,
            NozzleOpening.circular(identifier, .0001, effective_area_factor=1,
                                    area_basis_id="authored-effective-area"),
            result_factory=native.ValveResult, opening_fraction=1., allow_reverse=False)
        graph.add_link(identifier, left, right, valve, power_reader=lambda _: BoundaryPower(),
                       source_port_id=f"{identifier}/in", target_port_id=f"{identifier}/out")
    run = Lh2dtDynamicEquipment(graph, {"cold-volume": binding.inventory_node},
        simulator_factory=native.DynamicNetworkSimulator).run(
            .1, .02, start_time_s=10, clock_id=model.cold_boundary.clock_id)
    final = run.steps[-1]
    balance = final.balances["cold-volume"]
    assert max(abs(t.mass_flow_kg_s) for t in final.equipment.transfers) > 0
    assert abs(balance.mass_residual_kg) < 1e-12
    assert abs(balance.energy_residual_j) < 1e-8
    assert liquid_mass_fraction(final.equipment.node_states["cold-volume"]) > 0
    assert all(t.upstream_node in {"feed", "cold-volume"} for t in final.equipment.transfers)


def test_dynamic_boundary_support_negative_flow_and_undersized_inventory_fail():
    direct, model = dynamic()
    inlet = direct.state_pt(2e5, 35)
    initial = model.initialize(inlet, wall_temperature_k=25)
    for at in (9., 31.):
        with pytest.raises(ValueError, match="clock support"):
            model.derivative(initial, inlet, 0, 0, time_s=at)
    with pytest.raises(ValueError, match="negative"):
        model.derivative(initial, inlet, -.1, 0, time_s=10)
    with pytest.raises(ValueError):
        model.step(initial, inlet, 0, 1, time_s=10, time_step_s=1.)
    with pytest.raises(ValueError, match="clock support"):
        sealed_run(model, initial, 1., .1, start=29.5)
