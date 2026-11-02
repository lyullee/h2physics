"""Finite native transfer, independent caloric limits and error/event contracts."""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.constants import R_J_MOL_K
from h2physics.storage.finite_hydride import (
    BoundHydrogenEnergyReference,
    FiniteHydrideBed,
    FiniteHydrideHeatBoundary,
    FiniteHydrideHeatInput,
    HydrideGasThermodynamics,
)
from h2physics.storage.hydride import HydrideState
from h2physics.storage.hydride_compressor import (
    HydrideCompressorIntegrationError,
    HydrideCompressorStage,
    HydrideThermalCompressor,
)
from scripts.check_hydride_compressor import make_case, stages


def case(**kwargs):
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1]/"artifacts/native_packages"
    if not (target/"lh2dt/tank.py").exists():
        pytest.skip("Reviewed separately installed native LH2DT is optional")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    return make_case(**kwargs)


def run(model, schedule=None, *, loading=.01, step=1., rtol=1e-8):
    return model.run(stages(model, durations=(50., 40., 60., 50.)) if schedule is None else schedule,
        initial_solid=HydrideState(loading, 300.), initial_bed_gas=model.bed.gas.state_pt(2e5, 300.),
        sample_interval_s=2., maximum_step_s=step, relative_tolerance=rtol)


@pytest.fixture(scope="module")
def compressed():
    model = case(solid_capacity=50.)
    return model, run(model)


def assert_conservation(trace):
    for point in trace.points:
        assert abs(point.total_hydrogen_residual_kg) < 1e-12
        assert abs(point.total_energy_residual_j) < 1e-5
        assert abs(point.bed_gas_energy_residual_j) < 1e-5
        assert abs(point.bed_solid_energy_residual_j) < 1e-5
        for balance in point.body_balances.values():
            assert abs(balance.mass_residual_kg) < 1e-12
            assert abs(balance.energy_residual_j) < 1e-5


def test_stage_commands_have_explicit_clocks_support_and_no_bypass():
    heat = FiniteHydrideHeatBoundary("clock", 10., 20.,
        lambda t, s: FiniteHydrideHeatInput(300.), "authored-bath")
    with pytest.raises(ValueError, match="bypass"):
        HydrideCompressorStage("both", 10., 20., 1., 1., heat, 300., 300.)
    with pytest.raises(ValueError, match="support"):
        HydrideCompressorStage("late", 10., 21., 0., 0., heat, 300., 300.)
    with pytest.raises(ValueError, match="opening"):
        HydrideCompressorStage("signed", 10., 20., -.1, 0., heat, 300., 300.)


def test_shared_bed_core_separates_external_flow_from_total_mass_derivative():
    bed = case().bed
    gas = bed.gas.state_pt(3e5, 300.)
    mass = gas.density_kg_m3*bed.free_gas_volume_m3
    state = bed.snapshot_from_inventory(100., .2, mass, mass*gas.internal_energy_j_kg, 300.)
    heat = FiniteHydrideHeatInput(300.)
    closed = bed.rates(state, heat)
    flow, enthalpy = 1e-5, bed.gas.state_pt(5e5, 310.).enthalpy_j_kg
    opened = bed.rates(state, heat, gas_mass_flow_kg_s=flow, gas_enthalpy_flow_w=flow*enthalpy)
    assert opened.external_gas_mass_flow_kg_s == flow
    assert opened.gas_mass_kg_s == pytest.approx(flow-opened.hydrogen_uptake_kg_s, abs=1e-18)
    assert opened.gas_mass_kg_s-closed.gas_mass_kg_s == pytest.approx(flow, abs=1e-18)
    assert opened.gas_internal_energy_w-closed.gas_internal_energy_w == pytest.approx(flow*enthalpy, abs=1e-10)
    assert opened.fraction_s_inv == closed.fraction_s_inv
    assert opened.solid_temperature_k_s == closed.solid_temperature_k_s
    with pytest.raises(ValueError, match="snapshot inventory"):
        bed.rates(replace(state, gas_mass_kg=mass*1.1), heat)


def test_variable_mass_isothermal_duty_has_ideal_low_density_pressure_work_limit():
    bed = case(absorption=0., desorption=0.).bed
    gas = bed.gas.state_pt(100., 300.)
    mass = gas.density_kg_m3*bed.free_gas_volume_m3
    state = bed.snapshot_from_inventory(100., .2, mass, mass*gas.internal_energy_j_kg, 300.,
                                        isothermal_temperature_k=300.)
    flow = 1e-6
    rates = bed.rates(state, FiniteHydrideHeatInput(300.), gas_mass_flow_kg_s=flow,
        gas_enthalpy_flow_w=flow*gas.enthalpy_j_kg, isothermal_temperature_k=300.)
    expected = -flow*R_J_MOL_K/bed.gas.molar_mass_kg_mol*300.
    assert rates.gas_mass_kg_s == flow
    assert rates.gas_thermostat_heat_w == pytest.approx(expected, rel=1e-4)
    assert rates.solid_thermostat_heat_w == 0
    assert rates.gas_internal_energy_w == pytest.approx(
        flow*bed.gas.isothermal_mass_energy_derivative(state.gas), abs=1e-10)
    assert abs(rates.gas_thermostat_heat_w) > 1.


def test_consistent_energy_zero_shift_preserves_open_port_thermal_rate():
    original = case().bed
    base, offset = original.gas, 1e6
    basis = replace(base.basis, reference_id=base.basis.reference_id+":explicit-shift-1e6-J-kg")

    def shifted(s):
        return replace(s, basis=basis, enthalpy_j_kg=s.enthalpy_j_kg+offset,
                       internal_energy_j_kg=s.internal_energy_j_kg+offset)

    def unshifted(s):
        return replace(s, basis=base.basis, enthalpy_j_kg=s.enthalpy_j_kg-offset,
                       internal_energy_j_kg=s.internal_energy_j_kg-offset)

    changed_gas = HydrideGasThermodynamics(basis, base.molar_mass_kg_mol,
        lambda rho, u: shifted(base.state_rho_u(rho, u-offset)),
        lambda p, t: shifted(base.state_pt(p, t)), lambda s: base.fugacity_pa(unshifted(s)),
        "authored-consistent-native-port-reference-shift", base.native_objects,
        lambda rho, t: shifted(base.state_rho_t(rho, t)),
        lambda s: base.isothermal_mass_energy_derivative(unshifted(s))+offset)
    reference = BoundHydrogenEnergyReference.from_gas(changed_gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-corresponding-bound-H-shift")
    changed = FiniteHydrideBed(original.parameters, original.kinetics, changed_gas, reference,
        original.domain, free_gas_volume_m3=original.free_gas_volume_m3, gas_solid_conductance_w_k=1.)
    gas = base.state_pt(3e5, 300.)
    mass = gas.density_kg_m3*original.free_gas_volume_m3
    a = original.snapshot_from_inventory(100., .2, mass, mass*gas.internal_energy_j_kg, 300.)
    b = changed.snapshot_from_inventory(100., .2, mass, mass*(gas.internal_energy_j_kg+offset), 300.)
    flow, h = 1e-5, base.state_pt(5e5, 310.).enthalpy_j_kg
    r = original.rates(a, FiniteHydrideHeatInput(300.), gas_mass_flow_kg_s=flow, gas_enthalpy_flow_w=flow*h)
    s = changed.rates(b, FiniteHydrideHeatInput(300.), gas_mass_flow_kg_s=flow,
                       gas_enthalpy_flow_w=flow*(h+offset))
    assert s.fraction_s_inv == pytest.approx(r.fraction_s_inv, abs=1e-12)
    assert s.solid_temperature_k_s == pytest.approx(r.solid_temperature_k_s, abs=1e-9)
    assert s.gas_internal_energy_w-r.gas_internal_energy_w == pytest.approx(r.gas_mass_kg_s*offset, abs=1e-8)


def test_actual_delivered_hydrogen_exceeds_initial_bed_inventory_at_higher_receiver_pressure(compressed):
    model, trace = compressed
    assert trace.termination == "schedule_end" and len(trace.segments) == 4
    assert trace.admitted_hydrogen_kg > 5e-4
    assert trace.delivered_hydrogen_kg > trace.initial_snapshot.bed.total_hydrogen_mass_kg
    assert trace.delivered_above_source_mass_kg == pytest.approx(trace.delivered_hydrogen_kg, abs=1e-14)
    assert trace.points[-1].snapshot.source_inventory.mass_kg < trace.initial_snapshot.source_inventory.mass_kg
    assert trace.points[-1].snapshot.receiver_inventory.mass_kg > trace.initial_snapshot.receiver_inventory.mass_kg
    for point in trace.points:
        if point.outlet_nozzle.mass_flow_kg_s > 0:
            assert point.snapshot.receiver.pressure_pa > point.snapshot.source.pressure_pa
            assert point.snapshot.bed.gas.pressure_pa > point.snapshot.receiver.pressure_pa
    assert trace.points[-1].snapshot.receiver_inventory.mass_kg-trace.initial_snapshot.receiver_inventory.mass_kg == pytest.approx(
        trace.delivered_hydrogen_kg, abs=1e-13)
    assert model.source.native_tank.geometry.ambient_UA_W_K > 0
    assert model.receiver.native_tank.geometry.fluid_wall_UA_W_K > 0


def test_native_objects_shared_nozzle_and_distinct_boundary_limits_are_retained(compressed):
    model, trace = compressed
    native = model.native
    for segment in trace.segments:
        assert segment.native_solution.success
        for point in segment.points:
            assert isinstance(point.snapshot.source_native_state, native.tank.TankState)
            assert isinstance(point.source_native_derivative, native.tank.TankDerivative)
            assert isinstance(point.receiver_native_derivative, native.tank.TankDerivative)
            assert point.inlet_nozzle.opening is model.inlet_opening
            assert point.outlet_nozzle.opening is model.outlet_opening
            assert abs(point.inlet_nozzle.energy_residual_w) < 1e-7
            assert abs(point.outlet_nozzle.energy_residual_w) < 1e-7
    for a, b in zip(trace.segments, trace.segments[1:]):
        left, right = a.points[-1], b.points[0]
        assert left.snapshot.time_s == right.snapshot.time_s
        assert left.snapshot.stage_id != right.snapshot.stage_id
        assert left.snapshot.bed.fraction == right.snapshot.bed.fraction
        assert left.snapshot.bed.gas_mass_kg == right.snapshot.bed.gas_mass_kg
    assert trace.segments[0].points[-1].inlet_nozzle.effective_area_m2 > 0
    assert trace.segments[1].points[0].inlet_nozzle.effective_area_m2 == 0


def test_all_body_hydrogen_U_and_separate_gas_solid_heat_ledgers(compressed):
    _model, trace = compressed
    assert_conservation(trace)
    last = trace.points[-1]
    assert last.integrated["positive_bed_thermal_duty_j"] > 1000
    assert last.integrated["negative_bed_thermal_duty_j"] < -1000
    assert last.integrated["positive_bed_thermal_duty_j"]+last.integrated["negative_bed_thermal_duty_j"] == pytest.approx(
        last.integrated["bed_gas_heat_j"]+last.integrated["bed_solid_heat_j"], abs=1e-7)
    assert abs(last.total_energy_residual_j-last.integrated["nominal_reaction_heat_j"]) > 10
    cold, heat, hot, cool = trace.segments
    assert cold.points[-1].snapshot.bed.fraction > cold.points[0].snapshot.bed.fraction
    assert hot.points[-1].snapshot.bed.fraction < hot.points[0].snapshot.bed.fraction
    assert cool.points[-1].snapshot.bed.fraction > cool.points[0].snapshot.bed.fraction
    for segment in (heat, cool):
        assert all(p.inlet_nozzle.mass_flow_kg_s == p.outlet_nozzle.mass_flow_kg_s == 0 for p in segment.points)


def test_fresh_native_PT_reconstruction_checks_total_mass_U_independently(compressed):
    model, trace = compressed
    fresh = HydrideGasThermodynamics.coolprop("Hydrogen")
    reference = fresh.state_pt(1e5, 300.)
    bound = reference.enthalpy_j_kg*fresh.molar_mass_kg_mol-24000.
    for point in trace.points[::10]:
        s = point.snapshot
        mass = model.bed.parameters.hydrogen_capacity_kg*s.bed.fraction
        energy = (model.bed.parameters.heat_capacity_j_k*(s.bed.solid_temperature_k-300.)
                  +mass/fresh.molar_mass_kg_mol*bound)
        for thermo, volume in ((s.bed.gas, model.bed.free_gas_volume_m3),
                              (s.source, model.source.native_tank.geometry.volume_m3),
                              (s.receiver, model.receiver.native_tank.geometry.volume_m3)):
            state = fresh.state_pt(thermo.pressure_pa, thermo.temperature_k)
            m = state.density_kg_m3*volume
            mass += m
            energy += m*state.internal_energy_j_kg
        energy += model.source.native_tank.geometry.wall_heat_capacity_J_K*(s.source_native_state.wall_temperature_K-300.)
        energy += model.receiver.native_tank.geometry.wall_heat_capacity_J_K*(s.receiver_native_state.wall_temperature_K-300.)
        assert mass == pytest.approx(s.total_hydrogen_mass_kg, abs=1e-10)
        assert energy == pytest.approx(s.total_internal_energy_j, abs=1e-4)


def test_common_time_refinement_keeps_delivered_mass_and_hot_cold_feedback(compressed):
    _model, coarse = compressed
    fine = run(case(solid_capacity=50.), step=.5, rtol=2e-9)
    assert_conservation(fine)
    assert abs(coarse.delivered_hydrogen_kg-fine.delivered_hydrogen_kg) < 1e-8
    assert abs(coarse.points[-1].snapshot.bed.fraction-fine.points[-1].snapshot.bed.fraction) < 1e-6
    assert abs(coarse.points[-1].snapshot.bed.solid_temperature_k-fine.points[-1].snapshot.bed.solid_temperature_k) < .001


def test_isolated_pressure_rise_is_not_counted_as_delivered_compression():
    model = case(solid_capacity=50.)
    trace = run(model, stages(model, durations=(1., 40., 1., 40.), isolated=True), loading=.1)
    assert max(p.snapshot.bed.gas.pressure_pa for p in trace.points) > 1e6
    assert trace.admitted_hydrogen_kg == trace.delivered_hydrogen_kg == trace.delivered_above_source_mass_kg == 0
    assert_conservation(trace)


@pytest.mark.parametrize("fluid,spin", [("Hydrogen", "normal"), ("ParaHydrogen", "para")])
def test_zero_kinetics_thermal_isolation_native_identity_limits(fluid, spin):
    model = case(fluid=fluid, absorption=0., desorption=0., solid_ua=0., gas_solid_ua=0.)
    schedule = stages(model, durations=(.5, .5, .5, .5), isolated=True)
    trace = run(model, schedule, loading=.2)
    assert model.bed.gas.basis.spin_composition == spin
    assert len(model.bed.gas.native_objects) == 2
    for p in trace.points:
        assert p.snapshot.bed.fraction == .2
        assert p.snapshot.bed.solid_temperature_k == 300.
        assert p.snapshot.bed.gas.pressure_pa == pytest.approx(2e5, abs=.001)
    assert trace.delivered_hydrogen_kg == 0
    assert_conservation(trace)


def test_native_one_way_ports_block_pressure_reversal_without_signed_repair():
    model = case(absorption=0., desorption=0., solid_ua=0., gas_solid_ua=0.,
                 source_pressure=1e5, receiver_pressure=3e5)
    trace = run(model, stages(model, durations=(.5, .5, .5, .5)))
    assert trace.admitted_hydrogen_kg == trace.delivered_hydrogen_kg == 0
    assert trace.segments[0].points[0].inlet_nozzle.regime == "no_forward_pressure"
    assert trace.segments[2].points[0].outlet_nozzle.regime == "no_forward_pressure"
    assert_conservation(trace)


def test_positive_bed_gas_floor_is_localized_without_clipping_loading_or_time():
    model = case(floor_fraction=.99)
    trace = run(model, stages(model, durations=(1., 1., 1., 1.), isolated=True), loading=.1, step=.01)
    assert trace.termination == "bed_gas_inventory_floor"
    assert 100 < trace.event_time_s < 101
    assert trace.points[-1].snapshot.time_s == trace.event_time_s
    assert trace.points[-1].snapshot.bed.gas_mass_kg == pytest.approx(model.bed.domain.minimum_gas_mass_kg, abs=1e-14)
    assert .1 < trace.points[-1].snapshot.bed.fraction < 1
    assert_conservation(trace)


def test_finite_source_floor_stops_actual_inlet_transfer():
    ordinary = case()
    source = replace(ordinary.source, minimum_gas_mass_kg=.99999*ordinary.source.initial_native_state.hydrogen_mass_kg)
    model = HydrideThermalCompressor(ordinary.native, bed=ordinary.bed, source=source,
        receiver=ordinary.receiver, nozzle=ordinary.nozzle, inlet_opening=ordinary.inlet_opening,
        outlet_opening=ordinary.outlet_opening, evidence=ordinary.evidence)
    trace = run(model, stages(model, durations=(1., 1., 1., 1.)), loading=.1, step=.01)
    assert trace.termination == "source_inventory_floor"
    assert 100 < trace.event_time_s < 101
    assert trace.points[-1].snapshot.source_inventory.mass_kg == pytest.approx(source.minimum_gas_mass_kg, abs=1e-14)
    assert trace.admitted_hydrogen_kg > 0
    assert trace.delivered_hydrogen_kg == 0
    assert_conservation(trace)


def test_reference_phase_schedule_and_clock_fail_before_physical_execution():
    model = case()
    schedule = stages(model, durations=(1., 1., 1., 1.))
    para = HydrideGasThermodynamics.coolprop("ParaHydrogen").state_pt(2e5, 300.)
    with pytest.raises(ValueError, match="bases differ"):
        model.run(schedule, initial_solid=HydrideState(.1, 300.), initial_bed_gas=para,
                   sample_interval_s=1., maximum_step_s=.1)
    bad = replace(model.bed.gas.state_pt(2e5, 300.), phase="two_phase", vapor_mass_fraction=.5)
    with pytest.raises(ValueError, match="single gas"):
        model.run(schedule, initial_solid=HydrideState(.1, 300.), initial_bed_gas=bad,
                   sample_interval_s=1., maximum_step_s=.1)
    with pytest.raises(ValueError, match="clock"):
        run(model, (replace(schedule[0], bed_heat=replace(schedule[0].bed_heat, clock_id="unaligned-recorder")),))
    with pytest.raises(ValueError, match="contiguous"):
        run(model, (schedule[0], schedule[2]))


def test_runtime_failure_retains_completed_stage_prefix_actual_trial_and_cause():
    model = case()
    schedule = list(stages(model, durations=(1., 1., 1., 1.)))
    cause = RuntimeError("authored unavailable heating utility")

    def fail(t, s):
        raise cause

    schedule[1] = replace(schedule[1], bed_heat=replace(schedule[1].bed_heat, callback=fail))
    with pytest.raises(HydrideCompressorIntegrationError) as failure:
        run(model, schedule, loading=.1, step=.1)
    error = failure.value
    assert error.__cause__ is cause
    assert error.compressor is model
    assert len(error.completed_segments) == 1
    assert error.completed_segments[0].native_solution.success
    assert error.native_solution is None
    assert error.trial_time_s == 101.
    assert error.audit_time_s is None
    assert error.trial_values[1] > 0
    assert not error.trial_values.flags.writeable


def test_postrun_failure_retains_completed_raw_solution_and_failing_audit_state(monkeypatch):
    model = case()
    original = model._point
    calls = []
    cause = LookupError("authored independent audit unavailable")

    def fail(time, values, *args):
        calls.append(time)
        if len(calls) == 2:
            raise cause
        return original(time, values, *args)

    monkeypatch.setattr(model, "_point", fail)
    with pytest.raises(HydrideCompressorIntegrationError) as failure:
        run(model, stages(model, durations=(5., 1., 1., 1.)), loading=.1, step=.5)
    error = failure.value
    assert error.__cause__ is cause
    assert error.native_solution.success
    assert len(error.audited_points) == 1
    assert error.audit_time_s == calls[-1]
    np.testing.assert_array_equal(error.audit_values, error.native_solution.sol(error.audit_time_s))
