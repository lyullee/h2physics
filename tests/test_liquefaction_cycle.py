"""Native process balance, phase split and bounded integration checks."""

from dataclasses import replace

import pytest

from h2physics.adapters.liquefaction_cycle import (
    HydrogenLiquefactionSpec,
    NoTwoPhaseLiquefactionError,
    analyze_liquefaction_exergy,
    solve_hydrogen_liquefaction,
)


@pytest.fixture(scope="module")
def cycle():
    pytest.importorskip("tespy")
    pytest.importorskip("CoolProp")
    return solve_hydrogen_liquefaction(HydrogenLiquefactionSpec(
        compressor_isentropic_efficiency=.8, source_id="authored-not-measured-process"))


def test_actual_network_has_compression_precooling_jt_and_native_products(cycle):
    from CoolProp.CoolProp import PropsSI

    nw, spec, audit = cycle.network, cycle.spec, cycle.audit
    nw.assert_convergence()
    assert nw.get_comp("hydrogen_phase_separator").__class__.__name__ == "DropletSeparator"
    assert nw.get_comp("jt_valve").__class__.__name__ == "Valve"
    assert audit.compressor_shaft_input_w > 0
    assert audit.external_cold_utility_heat_absorbed_w > 0
    assert audit.precooler_sampled_minimum_approach_k > 0
    assert audit.precooler_sections == 128
    assert 0 < audit.liquid_mass_fraction < 1
    h_cold = PropsSI("Hmass", "P", spec.compression_pressure_pa_absolute,
                     "T", spec.precooler_outlet_temperature_k, spec.hydrogen_fluid)
    p = spec.separator_pressure_pa_absolute
    h_liq, h_vap = (PropsSI("Hmass", "P", p, "Q", q, spec.hydrogen_fluid) for q in (0, 1))
    # Independent phase lever rule, not the separator's mass-flow result.
    assert audit.liquid_mass_fraction == pytest.approx((h_vap-h_cold)/(h_vap-h_liq), rel=1e-7)
    assert nw.get_conn("h2_liquid").T.val_SI == pytest.approx(
        PropsSI("T", "P", p, "Q", 0, spec.hydrogen_fluid), abs=1e-7)
    assert nw.get_conn("h2_liquid").h.val_SI == pytest.approx(h_liq, abs=1e-5)
    assert nw.get_conn("h2_vapor").h.val_SI == pytest.approx(h_vap, abs=1e-5)


def test_actual_component_and_external_energy_balances(cycle):
    a = cycle.audit
    assert a.liquid_mass_flow_kg_s+a.vapor_mass_flow_kg_s == pytest.approx(
        cycle.spec.feed_mass_flow_kg_s, abs=1e-11)
    assert abs(a.hydrogen_first_law_residual_w) < 1e-4
    assert abs(a.utility_heat_balance_residual_w) < 1e-4
    assert abs(a.separator_energy_residual_w) < 1e-5
    assert abs(a.separator_mass_residual_kg_s) < 1e-11
    assert abs(a.jt_enthalpy_residual_j_kg) < 1e-5


def test_flow_scaling_is_extensive_without_changing_liquid_fraction(cycle):
    doubled = solve_hydrogen_liquefaction(replace(cycle.spec,
        feed_mass_flow_kg_s=2*cycle.spec.feed_mass_flow_kg_s, precooler_sections=256))
    assert doubled.audit.liquid_mass_fraction == pytest.approx(cycle.audit.liquid_mass_fraction, rel=1e-7)
    assert doubled.audit.precooler_sampled_minimum_approach_k == pytest.approx(
        cycle.audit.precooler_sampled_minimum_approach_k, abs=.2)
    for name in ("compressor_shaft_input_w", "external_cold_utility_heat_absorbed_w",
                 "liquid_mass_flow_kg_s", "vapor_mass_flow_kg_s", "cold_utility_mass_flow_kg_s"):
        assert getattr(doubled.audit, name) == pytest.approx(2*getattr(cycle.audit, name), rel=1e-7)


def test_warm_jt_feed_rejects_instead_of_creating_negative_liquid(cycle):
    with pytest.raises(NoTwoPhaseLiquefactionError) as error:
        solve_hydrogen_liquefaction(replace(cycle.spec, precooler_outlet_temperature_k=300.))
    assert error.value.inlet_enthalpy_j_kg > error.value.saturated_vapor_enthalpy_j_kg
    with pytest.raises(ValueError, match="single-gas"):
        solve_hydrogen_liquefaction(replace(cycle.spec, feed_temperature_k=19.))


def test_actual_exergy_handoff_includes_cold_utility(cycle):
    pytest.importorskip("exerpy")
    audit = analyze_liquefaction_exergy(cycle)
    assert audit.fuel_exergy_w > cycle.audit.compressor_shaft_input_w
    assert audit.product_exergy_w > 0
    assert audit.destruction_exergy_w > 0
    assert abs(audit.balance_residual_w) < .1
    assert {"hydrogen_compressor", "external_cryogenic_precooler", "jt_valve",
            "hydrogen_phase_separator"} <= set(audit.component_destruction_w)


@pytest.mark.parametrize("changes", [
    {"compressor_isentropic_efficiency": 1.01}, {"feed_mass_flow_kg_s": 0.},
    {"compression_pressure_pa_absolute": 1e4}, {"source_id": ""},
    {"hydrogen_fluid": "unknown-H2"}, {"utility_inlet_temperature_k": 29.},
    {"hydrogen_cooler_pressure_ratio": 1.01},
])
def test_input_boundaries_do_not_hide_invalid_states(changes):
    with pytest.raises(ValueError):
        replace(HydrogenLiquefactionSpec(.8, "authored"), **changes)
