"""Actual native hysteresis, source ownership, event replay and finite inventory."""

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_relief import (
    Lh2dtReliefTankDriver,
    ReliefCapabilityError,
    ReliefEventSettings,
    ReliefTankBoundary,
    shared_native_relief,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties


def native_bindings():
    target = Path(__file__).resolve().parents[1]/"artifacts/native_packages"
    if not (target/"lh2dt/valve.py").exists():
        pytest.skip("Separately installed pinned native LH2DT snapshot is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    pytest.importorskip("CoolProp")
    native = importlib.import_module("lh2dt")
    return SimpleNamespace(native=native, valve=importlib.import_module("lh2dt.valve"),
        tank=importlib.import_module("lh2dt.tank"), properties=importlib.import_module("lh2dt.properties"),
        streams=importlib.import_module("lh2dt.streams"))


def case(*, pressure=1.9e5, set_pressure=2e5, reseat=1.8e5, power=100., duration=30.):
    modules = native_bindings()
    properties = CoolPropProperties("Hydrogen")
    native_properties = Lh2dtLowLevelProperties(properties, state_factory=modules.properties.ThermoState)
    bridge = Lh2dtProperties(native_properties, reference_id=properties.basis.reference_id)
    opening = NozzleOpening("authored-PRV-opening", 1e-6, 1., "declared-effective-orifice-area")
    protection = shared_native_relief(native_valve_type=modules.valve.Valve,
        native_relief_factory=modules.valve.PressureReliefValve, result_factory=modules.valve.ValveResult,
        nozzle=HomogeneousIsentropicNozzle(properties), bridge=bridge, opening=opening,
        set_pressure_pa_absolute=set_pressure, reseat_pressure_pa_absolute=reseat,
        native_source_id="lh2dt:b2f276333c1b1793c39f25763703d196d36742ec")
    tank = modules.tank.HomogeneousTank(modules.tank.TankGeometry(.01, 100., 1., 10.), native_properties)
    thermo = native_properties.from_pT(pressure, 300.)
    mass = thermo.density_kg_m3*.01
    initial = modules.tank.TankState(mass, mass*thermo.specific_internal_energy_J_kg, 300.)
    boundary = ReliefTankBoundary("authored-clock", 10., 10.+duration,
        properties.state_pt(1e5, 300.), lambda t: 300.,
        lambda t, s, wall: power-1.*(300.-wall), "authored-constant-net-wall-power")
    driver = Lh2dtReliefTankDriver(tank, protection, flow_factory=modules.streams.MassEnergyFlow,
                                  state_factory=modules.properties.ThermoState)
    return SimpleNamespace(modules=modules, properties=properties, bridge=bridge, protection=protection,
        tank=tank, initial=initial, boundary=boundary, driver=driver,
        downstream=native_properties.from_pT(1e5, 300.))


def run(value, *, step=.5, duration=30., minimum_mass=1e-6):
    return value.driver.run(value.initial, duration_s=duration, maximum_step_s=step,
        start_time_s=10., clock_id="authored-clock", boundary=value.boundary,
        minimum_inventory_kg=minimum_mass)


def assert_balances(result):
    assert max(abs(result.mass_residual_kg)) < 1e-12
    assert max(abs(result.energy_residual_j)) < 1e-5


def test_probe_order_never_commits_native_hysteresis_and_copies_remain_actual_native():
    c = case()
    p = c.protection
    high = c.bridge.native.from_pT(2.1e5, 300.)
    low = c.bridge.native.from_pT(1.7e5, 300.)
    band = c.bridge.native.from_pT(1.9e5, 300.)
    for state in (high, low, band, high):
        assert p.evaluate(state, c.downstream).mass_flow_kg_s == 0.
    assert not p.is_open and not p.native_origin.is_open
    before, opened, actual = p.commit(10., high, c.downstream, clock_id="authored-clock")
    assert isinstance(before, c.modules.valve.PressureReliefValve)
    assert isinstance(opened, c.modules.valve.PressureReliefValve)
    assert opened is p.native and opened is not before and not before.is_open
    assert opened.is_open and not p.native_origin.is_open
    assert isinstance(actual.native, c.modules.valve.ValveResult)
    assert isinstance(p.native.valve, c.modules.valve.Valve)
    reference = {s.pressure_Pa: p.evaluate(s, c.downstream).mass_flow_kg_s for s in (low, band, high)}
    for state in (high, low, band, low, high):
        assert p.evaluate(state, c.downstream).mass_flow_kg_s == pytest.approx(reference[state.pressure_Pa], rel=1e-14)
    assert p.is_open and opened.is_open
    p.commit(11., band, c.downstream, clock_id="authored-clock")
    assert p.is_open
    native_before, closed, _ = p.commit(12., low, c.downstream, clock_id="authored-clock")
    assert not closed.is_open and native_before.is_open
    assert opened.is_open  # Earlier accepted actual native copy did not change.


def test_raw_native_evaluation_retains_original_trial_order_failure():
    c = case()
    raw = c.protection.native_origin
    high = c.bridge.native.from_pT(2.1e5, 300.)
    band = c.bridge.native.from_pT(1.9e5, 300.)
    assert raw.evaluate(band, c.downstream).mass_flow_kg_s == 0.
    raw.evaluate(high, c.downstream)  # A solver trial changes the raw native latch.
    assert raw.is_open and raw.evaluate(band, c.downstream).mass_flow_kg_s > 0.
    assert not c.protection.is_open  # Protected accepted copy is isolated from it.


def test_reverse_equal_pressure_and_zero_opening_never_create_reverse_flow():
    c = case()
    high = c.bridge.native.from_pT(2.1e5, 300.)
    c.protection.commit(10., high, c.downstream, clock_id="authored-clock")
    reverse = c.bridge.native.from_pT(3e5, 300.)
    assert c.protection.evaluate(high, reverse).mass_flow_kg_s == 0.
    assert c.protection.evaluate(high, high).mass_flow_kg_s == 0.
    assert c.protection.native.valve.evaluate(high, c.downstream, opening=0.).mass_flow_kg_s == 0.
    assert c.protection.is_open
    with pytest.raises(ValueError, match="binary opening"):
        c.protection.native.valve.evaluate(high, c.downstream, opening=.5)


def test_source_plane_and_remote_enthalpy_keep_one_shared_nozzle():
    c = case()
    upstream = c.bridge.native.from_pT(2.1e5, 300.)
    c.protection.commit(10., upstream, c.downstream, clock_id="authored-clock")
    actual = c.protection.evaluate(upstream, c.downstream)
    assert actual.native.outlet_specific_enthalpy_J_kg == upstream.specific_enthalpy_J_kg
    assert actual.nozzle.withdrawal_energy_w == pytest.approx(
        actual.mass_flow_kg_s*upstream.specific_enthalpy_J_kg, rel=1e-12)
    assert abs(actual.nozzle.energy_residual_w) < 1e-6
    assert actual.nozzle.opening is c.protection.opening


def test_commit_failure_and_wrong_clock_do_not_advance_accepted_latch(monkeypatch):
    c = case()
    high = c.bridge.native.from_pT(2.1e5, 300.)
    old = c.protection.native

    def fail(*args, **kwargs):
        raise RuntimeError("authored native flow capability failure")

    with monkeypatch.context() as patch:
        patch.setattr(c.protection.native.valve, "evaluate", fail)
        with pytest.raises(RuntimeError, match="authored native flow"):
            c.protection.commit(10., high, c.downstream, clock_id="authored-clock")
    assert c.protection.native is old and not c.protection.is_open
    c.protection.commit(10., high, c.downstream, clock_id="authored-clock")
    live = c.protection.native
    with pytest.raises(ValueError, match="clock identities"):
        c.protection.commit(11., high, c.downstream, clock_id="other-recorder")
    with pytest.raises(ValueError, match="backwards"):
        c.protection.commit(9., high, c.downstream, clock_id="authored-clock")
    assert c.protection.native is live


def test_closed_zero_heat_has_constant_native_inventory_and_temperature():
    c = case(power=0., duration=1.)
    result = run(c, duration=1., step=.1)
    assert not result.transitions and not result.native_relief_final.is_open
    assert result.released_mass_kg[-1] == 0.
    assert result.intervals[-1].native_step.state.hydrogen_mass_kg == c.initial.hydrogen_mass_kg
    assert result.intervals[-1].native_step.thermo.temperature_K == pytest.approx(300., abs=1e-9)
    assert result.native_tank is c.tank
    assert result.native_relief_origin is c.protection.native_origin
    assert not result.time_s.flags.writeable
    assert_balances(result)


def test_sealed_constant_net_heat_has_independent_analytic_total_energy():
    c = case(set_pressure=1e7, reseat=9e6, duration=1.)
    result = run(c, duration=1., step=.1)
    assert not result.transitions
    np.testing.assert_allclose(result.external_heat_j, 100.*(result.time_s-10.), atol=1e-10)
    initial_energy = c.initial.hydrogen_internal_energy_J+100.*c.initial.wall_temperature_K
    final = result.intervals[-1].native_step.state
    assert final.hydrogen_internal_energy_J+100.*final.wall_temperature_K-initial_energy == pytest.approx(100., abs=1e-7)
    assert_balances(result)


def test_heat_driven_pressure_open_and_reseat_events_have_native_left_right_limits():
    c = case()
    result = run(c)
    assert [event.kind for event in result.transitions] == ["open", "reseat"]
    assert result.trial_interval_count > len(result.intervals)
    for event in result.transitions:
        assert abs(event.pressure_pa-event.threshold_pa) <= result.event_settings.pressure_tolerance_pa
        assert event.upper_bracket_time_s-event.lower_bracket_time_s <= result.event_settings.time_tolerance_s
        interval = next(i for i in result.intervals if i.end_time_s == event.time_s)
        assert interval.native_step.state is event.native_tank_state
        assert interval.interval_is_open == event.native_before.is_open
        assert isinstance(event.native_after, c.modules.valve.PressureReliefValve)
    opening, reseat = result.transitions
    assert opening.source_before.mass_flow_kg_s == 0. < opening.source_after.mass_flow_kg_s
    assert reseat.source_before.mass_flow_kg_s > 0. == reseat.source_after.mass_flow_kg_s
    assert result.external_heat_j[-1] == pytest.approx(3000., abs=1e-7)
    assert result.released_mass_kg[-1] > 0.
    assert not result.native_relief_final.is_open
    assert_balances(result)


def test_initial_pressure_trip_is_explicit_without_advancing_native_tank_inventory():
    c = case(pressure=2.1e5, duration=.1)
    result = run(c, duration=.1, step=.05)
    event = result.transitions[0]
    assert event.kind == "initial_open" and event.time_s == 10.
    assert event.native_tank_state is c.initial
    assert event.source_before.mass_flow_kg_s == 0.
    assert result.initial_source is event.source_after
    assert not result.native_relief_origin.is_open
    assert_balances(result)


def test_positive_inventory_floor_is_localized_before_reseat_without_fake_isolation():
    c = case(pressure=2.1e5, duration=5.)
    floor = .99*c.initial.hydrogen_mass_kg
    result = run(c, duration=5., step=.25, minimum_mass=floor)
    assert result.termination == "inventory_floor"
    event = result.inventory_event
    assert event is not None and 10. < event.time_s < 15.
    assert abs(event.mass_kg-floor) < result.event_settings.mass_tolerance_kg
    assert event.upper_bracket_time_s-event.lower_bracket_time_s <= result.event_settings.time_tolerance_s
    assert event.native_tank_state is result.intervals[-1].native_step.state
    assert result.native_relief_final.is_open and event.source_at_limit.mass_flow_kg_s > 0.
    assert_balances(result)


def test_step_refinement_keeps_thresholds_and_native_conservation():
    coarse, fine = run(case(), step=.5), run(case(), step=.25)
    assert [e.kind for e in coarse.transitions] == [e.kind for e in fine.transitions]
    assert max(abs(a.time_s-b.time_s) for a, b in zip(coarse.transitions, fine.transitions, strict=True)) < .01
    assert abs(coarse.released_mass_kg[-1]-fine.released_mass_kg[-1]) < 1e-7
    assert abs(coarse.intervals[-1].native_step.thermo.pressure_Pa-fine.intervals[-1].native_step.thermo.pressure_Pa) < 10.
    assert_balances(coarse)
    assert_balances(fine)


def test_native_clock_hysteresis_and_boundary_capability_guards():
    with pytest.raises(ValueError, match="clock floor"):
        ReliefEventSettings(minimum_native_interval_s=1e-12)
    c = case(duration=1.)
    with pytest.raises(ValueError, match="clocks differ"):
        c.driver.run(c.initial, duration_s=1., maximum_step_s=.1, start_time_s=10.,
            clock_id="unmapped-recorder", boundary=c.boundary, minimum_inventory_kg=1e-6)
    with pytest.raises(ReliefCapabilityError, match="below reseat"):
        bad = ReliefTankBoundary("authored-clock", 10., 11., c.properties.state_pt(1.9e5, 300.),
                                 lambda t: 300., lambda t, s, w: 0., "authored")
        c.driver.run(c.initial, duration_s=1., maximum_step_s=.1, start_time_s=10.,
            clock_id="authored-clock", boundary=bad, minimum_inventory_kg=1e-6)
    with pytest.raises(ValueError, match="strict set/reseat"):
        case(set_pressure=2e5, reseat=2e5)
