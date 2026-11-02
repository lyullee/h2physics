"""Actual finite cryogenic high-pressure storage, without replacement physics."""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq

from h2physics.adapters.cryo_compressed import (
    CryoCompressedAuditError,
    CryoCompressedDomain,
    CryoCompressedEvidence,
    CryoCompressedGeometry,
    CryoCompressedNative,
    CryoCompressedStorage,
)
from h2physics.adapters.lh2dt_relief import ReliefIntegrationError, ReliefTankBoundary
from h2physics.core import Origin
from h2physics.release import NozzleOpening
from h2physics.thermo import CoolPropProperties


def bindings():
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1]/"artifacts/native_packages"
    if not (target/"lh2dt/tank.py").is_file():
        pytest.skip("Separately installed pinned LH2DT snapshot is unavailable")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return CryoCompressedNative.from_installed(source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec")


def case(fluid="ParaHydrogen", **changes):
    native = bindings()
    parameters = dict(properties=CoolPropProperties(fluid),
        geometry=CryoCompressedGeometry(.01, 100., 1., 100.),
        domain=CryoCompressedDomain(20., 350., 2e6, 120e6, .01, 80., 2.,
            ("supercritical_liquid", "supercritical", "supercritical_gas"), "authored-envelope-not-qualified"),
        evidence=CryoCompressedEvidence("authored-20MPa-25K", "authored-geometry",
            "authored-constant-UA", "authored-binary-PRV", "authored-single-fluid-no-solid-scope", Origin.SYNTHETIC),
        initial_pressure_pa_absolute=20e6, initial_temperature_k=25., initial_wall_temperature_k=25.,
        opening=NozzleOpening("authored-finite-PRV", 1e-8, 1., "authored-effective-orifice-area"),
        set_pressure_pa_absolute=100e6, reseat_pressure_pa_absolute=99e6)
    parameters.update(changes)
    return CryoCompressedStorage(native, **parameters)


def boundary(storage, *, duration=100., power=1000., start=100., ambient=300., receiver=19e6):
    return ReliefTankBoundary("authored-clock", start, start+duration,
        storage.properties.state_pt(receiver, 25.), lambda time: ambient,
        lambda time, fluid, wall: power-storage.geometry.ambient_ua_w_k*(ambient-wall),
        "authored-constant-net-wall-power")


def run(storage, *, duration=100., step=.5, power=1000., **kwargs):
    b = boundary(storage, duration=duration, power=power, **kwargs)
    return storage.run(duration_s=duration, maximum_step_s=step, start_time_s=b.support_start_s,
                       clock_id=b.clock_id, boundary=b)


@pytest.mark.parametrize("fluid", ["Hydrogen", "ParaHydrogen", "OrthoHydrogen"])
def test_actual_native_high_pressure_warming_crosses_Tcritical_with_one_eos_and_no_mass_loss(fluid):
    storage = case(fluid)
    trace = run(storage)
    assert trace.points[0].fluid.phase == "supercritical_liquid"
    assert trace.points[-1].fluid.phase == "supercritical"
    assert trace.points[0].fluid.temperature_k < trace.critical_temperature_k < trace.points[-1].fluid.temperature_k
    assert min(p.fluid.pressure_pa for p in trace.points) > trace.critical_pressure_pa
    assert not trace.native_trace.transitions and trace.native_trace.released_mass_kg[-1] == 0
    assert trace.points[-1].native_state.hydrogen_mass_kg == storage.initial_native_state.hydrogen_mass_kg
    assert isinstance(trace.native_trace.native_tank, storage.native.tank_module.HomogeneousTank)
    assert trace.native_trace.native_tank is storage.native_tank
    assert isinstance(trace.native_trace.intervals[-1].native_step, storage.native.tank_module.TankStepResult)
    assert trace.protection.native_origin is trace.native_trace.native_relief_origin
    assert trace.independent_properties is not storage.properties
    assert storage.native_properties.quality_adjustment_count == 0
    assert max(abs(p.balance.energy_residual_j) for p in trace.points) < 1e-5


def test_fresh_native_pt_and_prho_independently_reconstruct_mass_energy_and_temperature():
    trace = run(case(), duration=10.)
    for point in trace.points:
        assert abs(point.pt_mass_residual_kg) < 1e-10
        assert abs(point.pt_energy_residual_j) < 1e-4
        assert abs(point.prho_energy_residual_j) < 1e-4
        assert abs(point.prho_temperature_residual_k) < 1e-7
        assert point.independent_pt.basis == point.fluid.basis
        assert point.balance.violations(trace.inventory_tolerances) == ()


def test_constant_external_power_has_independent_exact_total_energy_limit():
    trace = run(case(), duration=20., power=1000.)
    energy0 = trace.points[0].inventory.total_energy_j
    for point in trace.points:
        expected = 1000.*(point.time_s-100.)
        assert point.inventory.total_energy_j-energy0 == pytest.approx(expected, abs=1e-5)
    assert trace.native_trace.external_heat_j[-1] == pytest.approx(20000., abs=1e-7)


def test_zero_power_uniform_state_and_signed_cooling_are_physical_native_limits():
    storage = case()
    stationary = run(storage, duration=10., power=0., ambient=25.)
    assert stationary.points[-1].fluid.temperature_k == pytest.approx(25., abs=1e-10)
    assert stationary.points[-1].fluid.pressure_pa == pytest.approx(20e6, abs=.001)
    cooled = run(storage, duration=5., power=-100.)
    assert cooled.points[-1].fluid.temperature_k < 25.
    assert cooled.points[-1].fluid.pressure_pa < 20e6
    assert cooled.native_trace.external_heat_j[-1] == pytest.approx(-500.)


def test_independent_closed_equilibrium_root_includes_finite_wall_storage():
    storage = case(initial_wall_temperature_k=200.)
    trace = run(storage, duration=30., step=.1, power=0.)
    m = storage.initial_native_state.hydrogen_mass_kg
    rho = m/storage.geometry.volume_m3
    total = trace.points[0].inventory.total_energy_j
    fresh = CoolPropProperties("ParaHydrogen")
    # Fresh native fixed-density flash, not an ideal gas/caloric surrogate.
    target_pressure = brentq(lambda p: m*fresh.state_prho(p, rho).internal_energy_j_kg
        +100*fresh.state_prho(p, rho).temperature_k-total, 20e6, 40e6, xtol=1e-6)
    equilibrium = fresh.state_prho(target_pressure, rho)
    assert trace.points[-1].fluid.temperature_k == pytest.approx(equilibrium.temperature_k, abs=1e-6)
    assert trace.points[-1].native_state.wall_temperature_K == pytest.approx(equilibrium.temperature_k, abs=1e-6)


def test_warm_gas_and_low_pressure_lh2_are_explicitly_distinct_initial_domains():
    fresh = CoolPropProperties("ParaHydrogen")
    warm = fresh.state_pt(20e6, 300.)
    cold = fresh.state_pt(20e6, 25.)
    low = fresh.saturated(1.5e5, 0.)
    assert cold.density_kg_m3 > 5*warm.density_kg_m3
    assert low.pressure_pa < fresh.critical_pressure_pa < cold.pressure_pa
    with pytest.raises(ValueError, match="cryogenic/high-pressure"):
        case(initial_temperature_k=300., initial_wall_temperature_k=300.)
    # Low-pressure liquid is a valid EOS state but outside this composition.
    with pytest.raises(ValueError, match="domain|cryogenic/high-pressure"):
        case(initial_pressure_pa_absolute=1.5e5, initial_temperature_k=20.)


def test_time_refinement_preserves_four_native_thermodynamic_outputs():
    storage = case()
    traces = [run(storage, step=step) for step in (1., .5, .25)]
    values = np.array([[t.points[-1].fluid.temperature_k, t.points[-1].fluid.pressure_pa,
                       t.points[-1].native_state.wall_temperature_K] for t in traces])
    assert max(abs(values[0]-values[2])) < 1.
    assert max(abs(values[1]-values[2])) < .1
    assert abs(traces[0].points[-1].inventory.total_energy_j-traces[2].points[-1].inventory.total_energy_j) < 1e-5


def test_existing_relief_driver_localizes_actual_pressure_and_removes_finite_inventory():
    storage = case(set_pressure_pa_absolute=21e6, reseat_pressure_pa_absolute=20.5e6)
    trace = run(storage, duration=6., step=.5)
    assert len(trace.native_trace.transitions) == 1
    event = trace.native_trace.transitions[0]
    assert event.kind == "open" and 100. < event.time_s < 106.
    assert abs(event.pressure_pa-21e6) < .001
    assert event.upper_bracket_time_s-event.lower_bracket_time_s <= 1e-8
    assert isinstance(event.native_after, storage.native.valve_module.PressureReliefValve)
    assert event.source_before.mass_flow_kg_s == 0 and event.source_after.mass_flow_kg_s > 0
    assert trace.native_trace.released_mass_kg[-1] > 0
    assert trace.points[-1].inventory.mass_kg < trace.points[0].inventory.mass_kg
    assert max(abs(p.balance.energy_residual_j) for p in trace.points) < 1e-5


def test_each_run_gets_fresh_native_latch_state_without_resetting_trial_clocks():
    storage = case()
    first, second = run(storage, duration=1.), run(storage, duration=1.)
    assert first.protection.native_origin is not second.protection.native_origin
    assert first.points[-1].native_state == second.points[-1].native_state
    assert not first.time_s.flags.writeable
    assert first.time_s[0] == 100. and first.time_s[-1] == 101.


def test_existing_positive_inventory_floor_is_localized_without_clipping_or_fake_closure():
    storage = case(set_pressure_pa_absolute=21e6, reseat_pressure_pa_absolute=20.5e6)
    floor = storage.initial_native_state.hydrogen_mass_kg-1e-5
    storage.domain = replace(storage.domain, minimum_inventory_kg=floor)
    trace = run(storage, duration=6.)
    assert trace.native_trace.termination == "inventory_floor"
    event = trace.native_trace.inventory_event
    assert event is not None and abs(event.mass_kg-floor) < 1e-12
    assert event.source_at_limit.mass_flow_kg_s > 0  # Termination is not a valve closure.
    assert trace.points[-1].native_state is event.native_tank_state


def test_domain_failures_retain_actual_native_driver_and_last_accepted_state():
    storage = case()
    storage.domain = replace(storage.domain, maximum_temperature_k=25.1,
                             maximum_initial_temperature_k=25.)
    with pytest.raises(ReliefIntegrationError, match="domain") as error:
        run(storage, duration=10.)
    assert error.value.native_tank is storage.native_tank
    assert isinstance(error.value.accepted_state, storage.native.tank_module.TankState)


def test_clock_support_receiver_reference_and_ownership_are_not_inferred():
    storage = case()
    b = boundary(storage, duration=1.)
    with pytest.raises(ValueError, match="support"):
        storage.run(duration_s=2., maximum_step_s=.5, start_time_s=100., clock_id=b.clock_id, boundary=b)
    with pytest.raises(ValueError, match="clocks"):
        storage.run(duration_s=1., maximum_step_s=.5, start_time_s=100., clock_id="other", boundary=b)
    wrong = replace(b, downstream=CoolPropProperties("Hydrogen").state_pt(19e6, 25.))
    with pytest.raises(ValueError, match="bases"):
        storage.run(duration_s=1., maximum_step_s=.5, start_time_s=100., clock_id=b.clock_id, boundary=wrong)
    storage.native_tank.properties = object()
    with pytest.raises(ValueError, match="ownership"):
        run(storage, duration=1.)


def test_reference_reconstruction_cannot_share_primary_provider_or_change_spin():
    storage = case()
    storage.independent_properties_factory = lambda fluid: storage.properties
    with pytest.raises(ValueError, match="separate"):
        run(storage, duration=1.)
    storage.independent_properties_factory = lambda fluid: CoolPropProperties("OrthoHydrogen")
    with pytest.raises(ValueError, match="bases"):
        run(storage, duration=1.)


def test_changed_independent_eos_energy_fails_with_actual_raw_trace(monkeypatch):
    storage = case()
    reference = CoolPropProperties("ParaHydrogen")
    original = reference.state_pt
    monkeypatch.setattr(reference, "state_pt", lambda p, t: replace(original(p, t),
                                                                 internal_energy_j_kg=1e7))
    storage.independent_properties_factory = lambda fluid: reference
    with pytest.raises(CryoCompressedAuditError) as error:
        run(storage, duration=1.)
    assert error.value.native_trace.native_tank is storage.native_tank
    assert error.value.point is not None
    assert error.value.native_state is error.value.point.native_state
    assert error.value.accepted_time_s == error.value.point.time_s
    assert error.value.audited_points == ()
    assert isinstance(error.value.__cause__, ValueError)


def test_smooth_heat_ramp_accepted_endpoint_domain_failure_retains_completed_native_run():
    storage = case()
    storage.domain = replace(storage.domain, maximum_temperature_k=26., maximum_initial_temperature_k=25.)
    b = ReliefTankBoundary("ramp-clock", 100., 101., storage.properties.state_pt(19e6, 25.),
        lambda time: 25., lambda time, fluid, wall: 1200.*(time-100.)**10,
        "authored-smooth-ramp-endpoint-regression")
    with pytest.raises(CryoCompressedAuditError, match="wall temperature") as error:
        storage.run(duration_s=1., maximum_step_s=1., start_time_s=100., clock_id=b.clock_id, boundary=b)
    failure = error.value
    assert failure.native_trace.time_s[-1] == 101.
    assert failure.native_state is failure.native_trace.intervals[-1].native_step.state
    assert failure.native_state.wall_temperature_K > 26.
    assert all(stage.wall_temperature_k <= 26. for stage in failure.native_trace.intervals[-1].stages)
    assert failure.accepted_time_s == 101.
    assert failure.point is None and len(failure.audited_points) == 1
    assert failure.audited_points[0].native_state is storage.initial_native_state
    assert failure.audited_points[0].time_s == 100.
    assert isinstance(failure.__cause__, ValueError)


@pytest.mark.parametrize("method_name", ["state_pt", "state_prho"])
def test_independent_eos_query_exception_retains_native_endpoint_and_prior_audits(method_name, monkeypatch):
    storage = case()
    reference = CoolPropProperties("ParaHydrogen")
    original = getattr(reference, method_name)
    cause = RuntimeError("authored independent EOS query failure")
    def failing_query(pressure, other):
        if pressure > 20e6+1.:
            raise cause
        return original(pressure, other)
    monkeypatch.setattr(reference, method_name, failing_query)
    storage.independent_properties_factory = lambda fluid: reference
    with pytest.raises(CryoCompressedAuditError, match="independent EOS query failure") as error:
        run(storage, duration=1., step=.5)
    failure = error.value
    assert failure.native_trace.time_s[-1] == 101.
    assert failure.native_state is failure.native_trace.intervals[0].native_step.state
    assert failure.accepted_time_s == 100.5
    assert failure.point is None and len(failure.audited_points) == 1
    assert isinstance(failure.audited_points, tuple)
    assert failure.audited_points[0].native_state is storage.initial_native_state
    assert failure.__cause__ is cause


def test_invalid_parameter_and_phase_scope_are_rejected():
    with pytest.raises(ValueError, match="Unresolved"):
        CryoCompressedEvidence("initial", "geometry", "thermal", "protection", "phase", Origin.UNRESOLVED)
    d = case().domain
    with pytest.raises(ValueError, match="critical pressure"):
        replace(d, minimum_initial_pressure_to_critical_ratio=1.)
    with pytest.raises(ValueError, match="phases"):
        replace(d, allowed_phases=("two_phase",))
    with pytest.raises(ValueError, match="thresholds"):
        case(set_pressure_pa_absolute=130e6)
    with pytest.raises(ValueError, match="closed initial"):
        case(set_pressure_pa_absolute=19e6, reseat_pressure_pa_absolute=18e6)
