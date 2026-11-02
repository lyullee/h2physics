"""Original closed inventory, native caloric and analytic finite-gas checks."""

from dataclasses import replace

import numpy as np
import pytest

from h2physics.constants import R_J_MOL_K
from h2physics.core import PropertyBasis, ThermoState
from h2physics.storage.finite_hydride import (
    BoundHydrogenEnergyReference,
    FiniteHydrideBed,
    FiniteHydrideDomain,
    FiniteHydrideHeatBoundary,
    FiniteHydrideHeatInput,
    FiniteHydrideIntegrationError,
    HydrideGasThermodynamics,
)
from h2physics.storage.hydride import (
    ArrheniusRate,
    HydrideKinetics,
    HydrideParameters,
    HydrideState,
    VanthoffPlateau,
)

pytest.importorskip("CoolProp")


def model(*, gas=None, absorption=.01, desorption=.02, conductance=10., minimum_mass=1e-7,
          ambient_conductance=0., heat_capacity=1000.):
    gas = gas or HydrideGasThermodynamics.coolprop("Hydrogen")
    parameters = HydrideParameters(.002, heat_capacity, 24000., gas.molar_mass_kg_mol,
                                   ambient_conductance)
    kinetics = HydrideKinetics(VanthoffPlateau(24000., 80., 1e5),
        ArrheniusRate(absorption, 0., 300.), ArrheniusRate(desorption, 0., 300.))
    reference = BoundHydrogenEnergyReference.from_gas(gas, temperature_k=300., pressure_pa=1e5,
        desorption_enthalpy_j_mol_h2=24000., evidence_id="authored-synthetic-verification-heat")
    domain = FiniteHydrideDomain(200., 600., 1e3, 1e7, minimum_mass)
    return FiniteHydrideBed(parameters, kinetics, gas, reference, domain,
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=conductance)


def boundary(callback=None, *, start=10., end=110., clock="authored-clock"):
    return FiniteHydrideHeatBoundary(clock, start, end,
        callback or (lambda t, s: FiniteHydrideHeatInput(300.)), "authored-heat-boundary")


def simulate(bed, *, pressure=3e5, solid=HydrideState(.1, 300.), gas_temperature=300.,
             times=None, heat=None, step=.5, **kwargs):
    return bed.simulate(np.linspace(10., 30., 41) if times is None else times, solid,
        bed.gas.state_pt(pressure, gas_temperature), boundary=heat or boundary(),
        clock_id="authored-clock", maximum_step_s=step, **kwargs)


def assert_balances(result, *, energy=1e-5):
    assert max(abs(result.total_hydrogen_residual_kg)) < 1e-14
    assert max(abs(result.gas_transfer_residual_kg)) < 1e-13
    assert max(abs(result.solid_transfer_residual_kg)) < 1e-13
    assert max(abs(result.gas_energy_residual_j)) < energy
    assert max(abs(result.solid_energy_residual_j)) < energy
    assert max(abs(result.total_energy_residual_j)) < energy
    assert max(abs(result.gas_integrated_state_residual_j)) < energy


@pytest.mark.parametrize("fluid,spin", [("Hydrogen", "normal"), ("ParaHydrogen", "para")])
def test_actual_native_du_fugacity_derivative_and_explicit_spin(fluid, spin):
    gas = HydrideGasThermodynamics.coolprop(fluid)
    state = gas.state_pt(3e5, 300.)
    recovered = gas.state_rho_u(state.density_kg_m3, state.internal_energy_j_kg)
    assert recovered.temperature_k == pytest.approx(300., abs=1e-8)
    assert recovered.pressure_pa == pytest.approx(3e5, abs=.001)
    assert gas.basis.spin_composition == spin
    assert gas.fugacity_pa(state) > state.pressure_pa
    perturbation = state.density_kg_m3*1e-4
    plus = gas.state_rho_t(state.density_kg_m3+perturbation, 300.)
    minus = gas.state_rho_t(state.density_kg_m3-perturbation, 300.)
    independent = ((plus.density_kg_m3*plus.internal_energy_j_kg
                    -minus.density_kg_m3*minus.internal_energy_j_kg)/(2*perturbation))
    assert gas.isothermal_mass_energy_derivative(state) == pytest.approx(independent, rel=1e-8)
    assert len(gas.native_objects) == 2
    assert hasattr(gas.native_objects[1], "update")


def test_zero_kinetics_keeps_both_finite_inventories_and_energy():
    bed = model(absorption=0., desorption=0.)
    result = simulate(bed)
    before, after = result.snapshots[0], result.snapshots[-1]
    assert after.fraction == before.fraction
    assert after.solid_temperature_k == before.solid_temperature_k
    assert after.gas.pressure_pa == pytest.approx(before.gas.pressure_pa, rel=1e-12)
    assert np.all(result.integrated_hydrogen_uptake_kg == 0)
    assert result.termination == "window_end"
    assert result.native_solution.success
    assert result.gas_thermodynamics is bed.gas
    assert not result.total_energy_residual_j.flags.writeable
    assert_balances(result)


def test_closed_dynamic_absorption_conserves_total_u_without_double_heat():
    bed = model()
    result = simulate(bed, times=np.linspace(10., 110., 101))
    first, last = result.snapshots[0], result.snapshots[-1]
    assert last.fraction > first.fraction
    assert last.gas_mass_kg < first.gas_mass_kg
    assert last.gas.pressure_pa < first.gas.pressure_pa
    assert last.solid_temperature_k > first.solid_temperature_k
    assert last.fraction < first.fraction+first.gas_mass_kg/bed.parameters.hydrogen_capacity_kg
    assert np.all(result.integrated_external_gas_heat_j == 0)
    assert np.all(result.integrated_external_solid_heat_j == 0)
    assert result.integrated_nominal_reaction_heat_j[-1] > 1000.
    # Adding this nominal heat to conserved total U would count binding twice.
    wrong_balance = result.total_energy_residual_j[-1]-result.integrated_nominal_reaction_heat_j[-1]
    assert abs(wrong_balance) > 1000.
    assert_balances(result)


def test_desorption_returns_hydrogen_and_cools_solid_on_same_energy_reference():
    bed = model()
    result = simulate(bed, pressure=5e4, solid=HydrideState(.8, 320.), gas_temperature=320.)
    first, last = result.snapshots[0], result.snapshots[-1]
    assert last.fraction < first.fraction
    assert last.gas_mass_kg > first.gas_mass_kg
    assert last.solid_temperature_k < first.solid_temperature_k
    assert result.integrated_hydrogen_uptake_kg[-1] < 0
    assert result.integrated_material_enthalpy_to_solid_j[-1] < 0
    assert_balances(result)


def test_prescribed_heating_can_reverse_uptake_without_an_external_h2_port():
    bed = model()
    heat = boundary(lambda t, s: FiniteHydrideHeatInput(300., solid_heat_w=400.))
    result = simulate(bed, pressure=2e5, times=np.linspace(10., 90., 161), heat=heat)
    changes = np.diff([s.fraction for s in result.snapshots])
    assert max(changes) > 1e-5
    assert min(changes) < -1e-5
    assert result.integrated_external_solid_heat_j[-1] == pytest.approx(32000., abs=1e-7)
    assert_balances(result)


def test_no_reaction_solid_heat_and_absolute_clock_have_analytic_limits():
    bed = model(absorption=0., desorption=0., conductance=0.)
    observed = []

    def prescribed(t, s):
        observed.append(t)
        return FiniteHydrideHeatInput(300., solid_heat_w=2*(t-10.))

    result = simulate(bed, times=np.linspace(10., 12., 21), heat=boundary(prescribed))
    elapsed = result.time_s-10.
    expected_heat = elapsed**2
    np.testing.assert_allclose(result.integrated_external_solid_heat_j, expected_heat, atol=1e-10)
    np.testing.assert_allclose([s.solid_temperature_k for s in result.snapshots],
        300.+expected_heat/bed.parameters.heat_capacity_j_k, atol=1e-9)
    assert min(observed) == 10. and max(observed) == 12.
    assert_balances(result)


def constant_cp_native_gas():
    ct = pytest.importorskip("cantera")
    species = ct.Species("H2", {"H": 2})
    cp = 3.5*ct.gas_constant
    species.thermo = ct.ConstantCp(200., 1000., 1e5, [300., cp*300., 0., cp])
    phase = ct.Solution(thermo="ideal-gas", kinetics=None, species=[species])
    basis = PropertyBasis("H2", "authored-native-constant-cp-H2", "mechanism-H2-spin-unresolved")

    def snapshot():
        return ThermoState(basis, phase.P, phase.T, phase.density_mass, phase.enthalpy_mass,
            phase.int_energy_mass, phase.entropy_mass, "gas", phase.cp_mass, phase.cv_mass,
            speed_of_sound_m_s=phase.sound_speed, vapor_mass_fraction=1.)

    def state_pt(pressure, temperature):
        phase.TP = temperature, pressure
        return snapshot()

    def state_rho_u(density, internal_energy):
        phase.UV = internal_energy, 1./density
        return snapshot()

    def state_rho_t(density, temperature):
        phase.TD = temperature, density
        return snapshot()

    def fugacity(state):
        phase.TP = state.temperature_k, state.pressure_pa
        return phase.P  # Native pure ideal gas: f equals its native pressure.

    def fixed_t_derivative(state):
        phase.TD = state.temperature_k, state.density_kg_m3
        return phase.int_energy_mass  # Native ideal gas u has no density dependence.

    return HydrideGasThermodynamics(basis, phase.mean_molecular_weight/1000., state_rho_u,
        state_pt, fugacity, "authored-constant-cp-native-verification", (phase,),
        state_rho_t, fixed_t_derivative)


def test_isothermal_finite_gas_analytic_loading_and_delta_h_vs_delta_u():
    gas = constant_cp_native_gas()
    bed = model(gas=gas)
    times = np.linspace(10., 70., 121)
    result = simulate(bed, pressure=2e5, times=times, isothermal_temperature_k=300.)
    first, last = result.snapshots[0], result.snapshots[-1]
    alpha = first.gas.pressure_pa/first.gas_mass_kg
    cap = bed.parameters.hydrogen_capacity_kg
    b = alpha*cap/1e5
    a = alpha*first.total_hydrogen_mass_kg/1e5-1
    equilibrium_x = a/b
    assert first.fraction < equilibrium_x < 1.
    ratio = ((equilibrium_x-first.fraction)/(1-first.fraction)
             *np.exp(-.01*b*(1-equilibrium_x)*(times-times[0])))
    analytic_fraction = (equilibrium_x-ratio)/(1-ratio)
    np.testing.assert_allclose([s.fraction for s in result.snapshots], analytic_fraction, atol=2e-10)
    np.testing.assert_allclose([s.gas.temperature_k for s in result.snapshots], 300., atol=1e-10)
    np.testing.assert_allclose([s.solid_temperature_k for s in result.snapshots], 300., atol=1e-10)
    ref = bed.energy_reference
    assert ref.reference_absorption_internal_energy_j_mol_h2 == pytest.approx(
        R_J_MOL_K*300.-24000., abs=1e-8)
    uptake_mol = (last.solid_hydrogen_mass_kg-first.solid_hydrogen_mass_kg)/gas.molar_mass_kg_mol
    total_thermostat = (result.integrated_gas_thermostat_heat_j[-1]
                        +result.integrated_solid_thermostat_heat_j[-1])
    assert total_thermostat == pytest.approx(
        uptake_mol*ref.reference_absorption_internal_energy_j_mol_h2, abs=1e-5)
    assert abs(total_thermostat+uptake_mol*24000.) > 100.
    assert_balances(result)


def test_real_gas_isothermal_mode_preserves_native_inventory_and_thermostat_heat():
    bed = model()
    result = simulate(bed, isothermal_temperature_k=300.)
    assert result.snapshots[-1].fraction > result.snapshots[0].fraction
    np.testing.assert_allclose([s.gas.temperature_k for s in result.snapshots], 300., atol=1e-8)
    assert result.integrated_gas_thermostat_heat_j[-1] > 0
    assert result.integrated_solid_thermostat_heat_j[-1] < 0
    assert_balances(result)


def test_gas_floor_is_localized_and_returned_without_clipping_fraction_or_time():
    ordinary = model()
    initial_mass = ordinary.gas.state_pt(3e5, 300.).density_kg_m3*.005
    bed = model(minimum_mass=.95*initial_mass)
    result = simulate(bed, times=np.linspace(10., 110., 101), step=.1)
    assert result.termination == "gas_inventory_floor"
    assert 10. < result.event_time_s < 110.
    assert result.time_s[-1] == result.event_time_s
    assert result.snapshots[-1].gas_mass_kg == pytest.approx(bed.domain.minimum_gas_mass_kg, abs=1e-14)
    assert 0.1 < result.snapshots[-1].fraction < 1.
    assert result.native_solution.t_events[0][0] == result.event_time_s
    assert_balances(result)


def test_time_refinement_and_thermal_feedback_are_separate_from_balance():
    bed = model()
    coarse = simulate(bed, step=1., relative_tolerance=1e-8)
    fine = simulate(bed, step=.25, relative_tolerance=1e-8)
    assert_balances(coarse)
    assert_balances(fine)
    a, b = coarse.snapshots[-1], fine.snapshots[-1]
    assert abs(a.fraction-b.fraction) < 1e-8
    assert abs(a.solid_temperature_k-b.solid_temperature_k) < 1e-5
    assert abs(a.gas.pressure_pa-b.gas.pressure_pa) < .01
    isothermal = simulate(bed, isothermal_temperature_k=300.)
    assert abs(isothermal.snapshots[-1].fraction-b.fraction) > .001


def test_reference_molar_mass_phase_domain_and_clock_fail_without_repairs():
    bed = model()
    with pytest.raises(ValueError, match="molar masses"):
        FiniteHydrideBed(replace(bed.parameters, hydrogen_molar_mass_kg_mol=.002), bed.kinetics,
            bed.gas, bed.energy_reference, bed.domain, free_gas_volume_m3=.005,
            gas_solid_conductance_w_k=10.)
    altered_reference = replace(bed.energy_reference,
        gas_reference_state=replace(bed.energy_reference.gas_reference_state,
                                    enthalpy_j_kg=bed.energy_reference.gas_reference_state.enthalpy_j_kg+10.))
    with pytest.raises(ValueError, match="reference enthalpy"):
        FiniteHydrideBed(bed.parameters, bed.kinetics, bed.gas, altered_reference, bed.domain,
                        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.)
    para = HydrideGasThermodynamics.coolprop("ParaHydrogen")
    with pytest.raises(ValueError, match="thermostat temperature"):
        simulate(bed, heat=boundary(), solid=HydrideState(.1, 300.),
                 times=[10., 11.], pressure=3e5,
                 isothermal_temperature_k=301.)
    # Explicitly incompatible gas basis is rejected before native integration.
    with pytest.raises(ValueError, match="bases differ"):
        bed.simulate([10., 11.], HydrideState(.1, 300.), para.state_pt(3e5, 300.),
            boundary=boundary(), clock_id="authored-clock", maximum_step_s=.1)
    with pytest.raises(ValueError, match="single gas"):
        bad = replace(bed.gas.state_pt(3e5, 300.), phase="two_phase", vapor_mass_fraction=.5)
        bed.simulate([10., 11.], HydrideState(.1, 300.), bad,
            boundary=boundary(), clock_id="authored-clock", maximum_step_s=.1)
    with pytest.raises(ValueError, match="clock identities"):
        simulate(bed, heat=boundary(clock="unmapped-recorder"))
    with pytest.raises(ValueError, match="support"):
        simulate(bed, heat=boundary(end=11.))
    with pytest.raises(ValueError, match="fraction"):
        HydrideState(1.001, 300.)


@pytest.mark.parametrize("pressure,solid,gas_temperature", [
    (3e5, HydrideState(.1, 300.), 350.), (5e4, HydrideState(.8, 300.), 350.)])
def test_interface_enthalpy_comes_from_donor_gas_or_desorbing_solid_temperature(
        pressure, solid, gas_temperature):
    bed = model()
    result = simulate(bed, pressure=pressure, solid=solid, gas_temperature=gas_temperature,
                      times=[10., 10.00001], step=1e-6)
    transfer_h = (result.integrated_material_enthalpy_to_solid_j[-1]
                  /result.integrated_hydrogen_uptake_kg[-1])
    donor_temperature = (gas_temperature if result.integrated_hydrogen_uptake_kg[-1] > 0
                         else solid.temperature_k)
    native = bed.gas.state_pt(pressure, donor_temperature)
    assert transfer_h == pytest.approx(native.enthalpy_j_kg, rel=1e-6)
    assert_balances(result)


def test_runtime_domain_failure_retains_actual_unclipped_trial_and_native_objects():
    normal = model()
    narrow = FiniteHydrideBed(normal.parameters, normal.kinetics, normal.gas,
        normal.energy_reference, replace(normal.domain, maximum_temperature_k=300.1),
        free_gas_volume_m3=.005, gas_solid_conductance_w_k=10.)
    with pytest.raises(FiniteHydrideIntegrationError, match="Solid temperature") as failed:
        simulate(narrow, heat=boundary(lambda t, s: FiniteHydrideHeatInput(300., solid_heat_w=400.)))
    assert failed.value.trial_time_s > 10.
    assert failed.value.trial_values[2] > 300.1
    assert failed.value.gas_thermodynamics is normal.gas


def test_consistent_gas_and_bound_h_energy_zero_shift_preserves_physical_trajectory():
    base = HydrideGasThermodynamics.coolprop("Hydrogen")
    offset = 1e6  # Explicit verification transformation in J/kg; no native global edit.
    shifted_basis = replace(base.basis, reference_id=base.basis.reference_id+":plus-1e6-J-per-kg")

    def shifted(state):
        return replace(state, basis=shifted_basis, enthalpy_j_kg=state.enthalpy_j_kg+offset,
                       internal_energy_j_kg=state.internal_energy_j_kg+offset)

    def unshifted(state):
        return replace(state, basis=base.basis, enthalpy_j_kg=state.enthalpy_j_kg-offset,
                       internal_energy_j_kg=state.internal_energy_j_kg-offset)

    transformed = HydrideGasThermodynamics(shifted_basis, base.molar_mass_kg_mol,
        lambda rho, u: shifted(base.state_rho_u(rho, u-offset)),
        lambda p, t: shifted(base.state_pt(p, t)),
        lambda s: base.fugacity_pa(unshifted(s)), "authored-consistent-native-reference-shift",
        base.native_objects, lambda rho, t: shifted(base.state_rho_t(rho, t)),
        lambda s: base.isothermal_mass_energy_derivative(unshifted(s))+offset)
    original, changed = simulate(model(gas=base)), simulate(model(gas=transformed))
    for a, b in zip(original.snapshots, changed.snapshots, strict=True):
        assert abs(a.fraction-b.fraction) < 1e-9
        assert abs(a.solid_temperature_k-b.solid_temperature_k) < 1e-6
        assert abs(a.gas.pressure_pa-b.gas.pressure_pa) < .001
        assert b.total_internal_energy_j-a.total_internal_energy_j == pytest.approx(
            offset*a.total_hydrogen_mass_kg, abs=1e-5)
    assert_balances(original)
    assert_balances(changed)
