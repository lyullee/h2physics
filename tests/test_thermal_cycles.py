"""Executed native network integration, balances and boundary classifications."""
from dataclasses import replace

import pytest

from h2physics.adapters.thermal_cycles import (
    RankineCycleSpec,
    analyze_physical_exergy,
    analyze_rankine_exergy,
    solve_rankine_cycle,
)


def test_rankine_input_pressure_and_efficiency_domains():
    with pytest.raises(ValueError, match="high pressure"):
        RankineCycleSpec(high_pressure_pa=100_000)
    with pytest.raises(ValueError, match="exceed one"):
        RankineCycleSpec(turbine_isentropic_efficiency=1.01)
    with pytest.raises(ValueError, match="ordered"):
        RankineCycleSpec(hot_outlet_temperature_k=390)


@pytest.fixture(scope="module")
def cycle():
    pytest.importorskip("tespy")
    pytest.importorskip("CoolProp")
    return solve_rankine_cycle()


def test_real_rankine_network_resolves_mass_heat_work_and_carnot_bound(cycle):
    from tespy.networks import Network
    assert isinstance(cycle.network, Network)
    assert cycle.network.converged
    audit = cycle.energy
    assert audit.net_output_w > 0
    assert audit.heat_input_w > audit.net_output_w
    assert abs(audit.first_law_residual_w) < 1e-5
    assert audit.maximum_mass_residual_kg_s < 1e-10
    assert 0 < audit.thermal_efficiency < 1-cycle.spec.cold_inlet_temperature_k/cycle.spec.hot_inlet_temperature_k
    inlet = cycle.network.get_conn("turbine_inlet")
    outlet = cycle.network.get_conn("turbine_outlet")
    assert outlet.s.val_SI > inlet.s.val_SI
    assert audit.turbine_output_w == pytest.approx(inlet.m.val_SI*(inlet.h.val_SI-outlet.h.val_SI))


def test_cycle_extensive_scaling_uses_new_actual_native_solve(cycle):
    scaled = solve_rankine_cycle(replace(cycle.spec, mass_flow_kg_s=2.5))
    assert scaled.energy.net_output_w == pytest.approx(2.5*cycle.energy.net_output_w, rel=1e-8)
    assert scaled.energy.heat_input_w == pytest.approx(2.5*cycle.energy.heat_input_w, rel=1e-8)
    assert scaled.network.get_conn("hot_in").m.val_SI == pytest.approx(
        2.5*cycle.network.get_conn("hot_in").m.val_SI, rel=1e-8)


@pytest.mark.parametrize("ambient_k,coolant_role", [(298.15,"fuel"),(288.15,"loss")])
def test_current_exerpy_native_component_and_overall_exergy_close(cycle, ambient_k, coolant_role):
    pytest.importorskip("exerpy")
    audit = analyze_rankine_exergy(cycle, environment_temperature_k=ambient_k)
    assert audit.product_exergy_w == pytest.approx(cycle.energy.net_output_w)
    assert abs(audit.balance_residual_w) < 1e-5
    assert min(audit.component_destruction_w.values()) > 0
    assert audit.fuel_exergy_w > audit.product_exergy_w > 0
    if coolant_role == "fuel":
        assert audit.loss_exergy_w == 0
        assert "cold_in" in audit.analysis.E_F_dict["inputs"]
    else:
        assert audit.loss_exergy_w > 0
        assert "cold_out" in audit.analysis.E_L_dict["inputs"]


def test_exergy_refuses_non_native_network_instead_of_faking_provider_result():
    pytest.importorskip("tespy")
    pytest.importorskip("exerpy")
    with pytest.raises(TypeError, match="actual native"):
        analyze_physical_exergy(object(), environment_temperature_k=300,
            environment_pressure_pa=101325, fuel={}, product={})


def test_actual_cycle_generator_stack_current_and_hydrogen_boundary(cycle):
    from examples.thermal_cycle_electrolysis import run_example
    from h2physics.constants import FARADAY_C_MOL
    result = run_example(cycle)
    stack = result["stack_result"]
    assert stack.electric_input_w == pytest.approx(.95*cycle.energy.net_output_w)
    assert stack.hydrogen_production_mol_s == pytest.approx(
        stack.current_a*100/(2*FARADAY_C_MOL))
    assert stack.hydrogen_production_kg_s > 0
    assert abs(result["electrical_power_residual_w"]) < 1e-6
    assert abs(result["shaft_to_reaction_energy_residual_w"]) < 1e-6
    with pytest.raises(ValueError,match="operating-current bound"):
        run_example(cycle,upper_current_density_a_m2=1.)
