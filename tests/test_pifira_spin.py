"""Actual pifira rotor/Milenko calculations and independent thermodynamic limits."""

import importlib
import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from h2physics.adapters.lh2dt_spin import SpinDomain
from h2physics.adapters.pifira_spin import (
    MilenkoAdmission,
    PifiraSpinBridge,
    RotorCutoffError,
    RotorEnergyReference,
    RotorEvidence,
    SpinMedium,
    SpinPVAssumption,
)
from h2physics.core import Origin
from h2physics.thermo.coolprop import CoolPropProperties


def native_api():
    root = Path(__file__).resolve().parents[1]
    for directory in ("artifacts/native_fire_packages", "artifacts/native_packages"):
        target = root/directory
        if target.is_dir() and str(target) not in sys.path:
            sys.path.insert(0, str(target))
    pytest.importorskip("pifira")
    return importlib.import_module("pifira.lh2.spin"), pytest.importorskip("lh2dt.ortho_para")


def model(*, rotor=None, correlation=None, reference=None, domain=None):
    native, states = native_api()
    return PifiraSpinBridge(native, rotor or native.RigidRotorSpinThermo(),
        correlation or native.MilenkoCorrelation(), states.OrthoParaState,
        evidence=RotorEvidence("native-Petitpas-rotor-common-ground",
            "native-Milenko-Petitpas-natural-conversion", "prescribed-H2-medium", Origin.PREDICTED),
        domain=domain or SpinDomain(1., 1000., 96, 1e-10, "authored-rotor-cutoff-domain"),
        energy_reference=reference or RotorEnergyReference("native-para-J0-common-rotor-U"))


def medium(temperature=20., density=70., phase="liquid"):
    return SpinMedium(temperature, density, phase, "authored-density-not-mixture-EOS",
                      "authored-phase-branch", Origin.SYNTHETIC)


def test_optional_host_import_does_not_import_pifira_or_lh2dt():
    result = subprocess.run([sys.executable, "-c",
        "import sys; import h2physics.adapters.pifira_spin; "
        "assert 'pifira' not in sys.modules and 'lh2dt' not in sys.modules"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_native_low_temperature_common_ground_and_equilibrium_two_level_limit():
    bridge = model()
    point = bridge.point(bridge.state(.25), 10., .02)
    theta = bridge.thermo.rotational_temperature_K
    expected_para = 1/(1+9*math.exp(-2*theta/10))
    assert point.equilibrium.para_fraction == pytest.approx(expected_para, abs=2e-15)
    assert point.para_energy_j_kg == pytest.approx(0., abs=1e-12)
    assert point.ortho_energy_j_kg == pytest.approx(bridge.thermo.gap_J_per_kg, abs=1e-8)
    assert point.conversion_energy_j_kg == pytest.approx(bridge.thermo.gap_J_per_kg, abs=1e-8)
    assert isinstance(point.native_state, native_api()[1].OrthoParaState)
    assert point.native_thermo is bridge.thermo


def test_mathematical_high_temperature_rotor_limit_with_larger_native_cutoff():
    native, _ = native_api()
    rotor = native.RigidRotorSpinThermo(maximum_J=128)
    bridge = model(rotor=rotor, domain=SpinDomain(1., 20000., 192, 1e-10, "mathematical-rotor-only"))
    point = bridge.point(bridge.state(.25), 20000., 1.)
    assert point.equilibrium.para_fraction == pytest.approx(.25, abs=1e-13)
    assert point.para_cv_j_kg_k == pytest.approx(rotor.gas_constant_J_kgK, rel=1e-6)
    assert point.ortho_cv_j_kg_k == pytest.approx(rotor.gas_constant_J_kgK, rel=1e-6)
    assert abs(point.conversion_energy_j_kg) < 1e-5


@pytest.mark.parametrize("temperature", [10., 20., 40., 80., 100., 300., 1000.])
def test_native_cv_and_gap_derivative_match_independent_energy_finite_differences(temperature):
    bridge = model()
    rotor = bridge.thermo
    width = temperature*1e-4
    for species in ("para", "ortho"):
        difference = (rotor.rotational_energy_J_per_kg(temperature+width, species)
            -rotor.rotational_energy_J_per_kg(temperature-width, species))/(2*width)
        assert difference == pytest.approx(rotor.rotational_cv_J_per_kgK(temperature, species),
                                            rel=2e-6, abs=2e-5)
    gap_difference = (rotor.conversion_energy_J_per_kg(temperature+width)
                      -rotor.conversion_energy_J_per_kg(temperature-width))/(2*width)
    assert gap_difference == pytest.approx(rotor.d_conversion_energy_dT_J_per_kgK(temperature),
                                           rel=2e-6, abs=2e-5)


def test_cutoff_energy_failure_is_retained_and_not_hidden_by_equilibrium_only_check():
    native, _ = native_api()
    bridge = model(rotor=native.RigidRotorSpinThermo(maximum_J=8))
    with pytest.raises(RotorCutoffError) as failure:
        bridge.point(bridge.state(.25), 1000., 1.)
    assert failure.value.point.native_thermo.maximum_J == 8
    assert max(failure.value.point.cutoff_errors.values()) > 1.


def test_existing_para_state_and_native_lh2dt_equilibrium_agree_on_matched_rotor_parameters():
    bridge = model()
    _, native_states = native_api()
    state = bridge.state(.3)
    assert state.ortho_fraction == pytest.approx(.7)
    for temperature in (10., 20., 100., 300., 1000.):
        expected = native_states.equilibrium_para_fraction(temperature,
            rotational_temperature_K=bridge.thermo.rotational_temperature_K, maximum_rotational_level=40)
        assert bridge.point(state, temperature, 1.).equilibrium.para_fraction == pytest.approx(expected, abs=2e-15)


def test_actual_strict_rate_state_mapping_heat_and_gas_reverse_sign():
    bridge = model()
    state = bridge.state(.3)
    point = bridge.rate(state, medium(), .02)
    direct = bridge.correlation.ortho_fraction_rate_per_s(.7, 20., 70., "liquid",
                                                       thermo=bridge.thermo, strict=True)
    assert point.para_fraction_rate_s == pytest.approx(-direct)
    assert point.conversion_heat_w == pytest.approx(.02*point.point.conversion_energy_j_kg*(-direct))
    assert point.native_correlation is bridge.correlation
    assert point.shared_rate.native_state is state
    reverse = bridge.rate(bridge.state(.38), medium(120., 10., "gas"), .02)
    assert reverse.para_fraction_rate_s < 0
    assert reverse.conversion_heat_w < 0


def test_existing_frozen_density_keeps_phase_basis_and_requires_its_approximation_evidence():
    bridge = model()
    state = CoolPropProperties("Hydrogen").state_pt(2e5, 20.)
    args = dict(density_evidence_id="authored-normal-H2-density-reference",
        phase_evidence_id="existing-single-phase-reference", origin=Origin.SYNTHETIC)
    with pytest.raises(ValueError):
        SpinMedium.from_frozen_state(state, composition_density_assumption_id="", **args)
    m = SpinMedium.from_frozen_state(state,
        composition_density_assumption_id="authored-fixed-spin-density-approximation", **args)
    assert m.phase == "liquid"
    assert m.frozen_density_reference is state
    assert bridge.rate(bridge.state(.3), m, .02).para_fraction_rate_s > 0
    two_phase = CoolPropProperties("Hydrogen").saturated(101325., .5)
    with pytest.raises(ValueError, match="Two-phase"):
        SpinMedium.from_frozen_state(two_phase, composition_density_assumption_id="not-a-mixture-EOS", **args)


def test_explicit_native_balance_probe_is_not_a_low_ortho_admission():
    bridge = model()
    m = medium()
    equilibrium = float(bridge.thermo.equilibrium_ortho(m.temperature_k))
    fractions = [0., equilibrium/2, equilibrium, equilibrium*1.5, 1.]
    result = bridge.detailed_balance_probe(fractions, m)
    rates = result.native_rates_per_s
    assert rates[0] == 0
    assert rates[1] > 0
    assert abs(rates[2]) < 1e-20
    assert rates[3] < 0
    assert rates[-1] == pytest.approx(-bridge.correlation.forward_rate_per_s(20., 70., "liquid"))
    assert "not-admitted" in result.status
    with pytest.raises(bridge.native.CorrelationDomainError):
        bridge.rate(bridge.state(1-equilibrium), m, .02)


def test_rotational_storage_chain_rule_and_temperature_dependent_gap():
    bridge = model()
    state, temperature, mass = bridge.state(.3), 100., .02
    terms = bridge.storage_terms(state, temperature, mass)
    temperature_rate, para_rate, width = .02, 1e-7, .01
    before = bridge.point(bridge.state(state.para_fraction-width*para_rate),
                          temperature-width*temperature_rate, mass).mixture_rotational_energy_j
    after = bridge.point(bridge.state(state.para_fraction+width*para_rate),
                         temperature+width*temperature_rate, mass).mixture_rotational_energy_j
    assert (after-before)/(2*width) == pytest.approx(terms.energy_rate_w(
        temperature_rate_k_s=temperature_rate, para_fraction_rate_s=para_rate), rel=1e-7, abs=1e-7)
    assert bridge.point(state, 300., mass).conversion_energy_j_kg < .1*bridge.point(state, 20., mass).conversion_energy_j_kg
    assert not hasattr(bridge, "advance")
    assert not hasattr(bridge, "adiabatic")


def test_common_energy_shift_and_baseline_correction_do_not_double_rotational_storage():
    bridge = model()
    shifted = model(reference=RotorEnergyReference("authored-common-shift", 2.3e7))
    state = bridge.state(.3)
    a, b = bridge.point(state, 100., .02), shifted.point(state, 100., .02)
    assert b.mixture_rotational_energy_j-a.mixture_rotational_energy_j == pytest.approx(.02*2.3e7)
    assert b.para_energy_j_kg-a.para_energy_j_kg == pytest.approx(2.3e7)
    assert b.ortho_energy_j_kg-a.ortho_energy_j_kg == pytest.approx(2.3e7)
    assert a.frozen_rotational_capacity_j_k == b.frozen_rotational_capacity_j_k
    correction = bridge.storage_terms(state, 100., .02, baseline_para_fraction=.25,
                                       baseline_evidence_id="authored-frozen-normal-reference")
    baseline = bridge.point(bridge.state(.25), 100., .02)
    assert correction.energy_j == pytest.approx(a.mixture_rotational_energy_j-baseline.mixture_rotational_energy_j)
    assert correction.frozen_capacity_j_k == pytest.approx(a.frozen_rotational_capacity_j_k-baseline.frozen_rotational_capacity_j_k)
    zero = bridge.storage_terms(state, 100., .02, baseline_para_fraction=.3,
                                baseline_evidence_id="authored-identical-baseline")
    assert zero.energy_j == 0
    assert zero.frozen_capacity_j_k == 0
    with pytest.raises(ValueError, match="baseline evidence"):
        bridge.storage_terms(state, 100., .02, baseline_para_fraction=.25)


def test_enthalpy_requires_explicit_pv_assumption_and_never_creates_a_fluid_eos():
    bridge = model()
    with pytest.raises(ValueError, match="PV"):
        bridge.storage_terms(bridge.state(.3), 100., .02, energy_kind="rotational_H")
    pv = SpinPVAssumption("ideal-gas-no-mole-change", "gas", "authored-ideal-limit-no-spin-PV")
    terms = bridge.storage_terms(bridge.state(.3), 100., .02, energy_kind="rotational_H", pv_assumption=pv)
    assert terms.energy_kind == "rotational_H"
    assert terms.pv_assumption is pv
    with pytest.raises(ValueError):
        SpinPVAssumption("ideal-gas-no-mole-change", "liquid", "unsupported-liquid-claim")
    assert not hasattr(bridge, "state_pt")


def test_thermostat_instantaneous_power_and_external_generic_driver_constant_t_oracle():
    bridge = model()
    m = medium()
    mass, c0, duration = .02, .7, 10000.
    times = np.linspace(100., 100.+duration, 101)
    def callback(time, values):
        point = bridge.thermostat_power(bridge.state(values[0]), m, mass, time_s=time,
            clock_id="thermostat-test", support_start_s=100., support_end_s=10100.,
            boundary_evidence_id="authored-held-T-rotor-bath")
        return point.rate.para_fraction_rate_s, point.external_power.heat_w
    solution = solve_ivp(callback, (times[0], times[-1]), (1-c0, 0.), t_eval=times,
                         rtol=1e-10, atol=1e-12, max_step=200., method="DOP853")
    assert solution.success
    equilibrium = float(bridge.thermo.equilibrium_ortho(20.))
    forward = float(bridge.correlation.forward_rate_per_s(20., 70., "liquid"))
    # Independently integrated constant-T quadratic ODE; no correlation coefficients are copied.
    exact_c = equilibrium/(1-(1-equilibrium/c0)*np.exp(-forward*equilibrium/(1-equilibrium)*(times-times[0])))
    assert 1-solution.y[0] == pytest.approx(exact_c, abs=1e-11)
    initial = bridge.point(bridge.state(1-c0), 20., mass).mixture_rotational_energy_j
    residuals = [bridge.point(bridge.state(x), 20., mass).mixture_rotational_energy_j-initial-q
                 for x, q in zip(solution.y[0], solution.y[1], strict=True)]
    assert max(abs(np.asarray(residuals))) < 1e-9
    assert 1-solution.y[0, -1] > bridge.correlation.primary_ortho_fraction_range[0]


@pytest.mark.parametrize("settings", [
    (16.9, 70., "liquid", .7), (32.1, 70., "liquid", .7),
    (39.9, 10., "gas", .7), (120.1, 10., "gas", .7),
    (20., 91., "liquid", .7), (20., 70., "liquid", .61), (20., 70., "liquid", .76),
])
def test_phase_temperature_density_and_primary_composition_are_not_extended(settings):
    bridge = model()
    temperature, density, phase, ortho = settings
    with pytest.raises(ValueError):
        bridge.rate(bridge.state(1-ortho), medium(temperature, density, phase), .02)


def test_petitpas_reverse_threshold_records_do_not_override_native_primary_domain():
    bridge = model()
    assert bridge.native.PETITPAS_REVERSE_VALIDITY_THRESHOLDS
    for density, temperature, minimum_ortho in bridge.native.PETITPAS_REVERSE_VALIDITY_THRESHOLDS:
        with pytest.raises(ValueError):
            bridge.rate(bridge.state(1-minimum_ortho), medium(temperature, density, "gas"), .02)


def test_native_domain_parameter_and_clock_identity_guards():
    bridge = model()
    with pytest.raises(ValueError):
        bridge.state(True)
    with pytest.raises(ValueError):
        MilenkoAdmission(92.)
    with pytest.raises(ValueError):
        model(correlation=replace(bridge.correlation, liquid_temperature_K=(1., 32.)))
    with pytest.raises(ValueError):
        model(rotor=replace(bridge.thermo, maximum_J=40.5))
    with pytest.raises(ValueError):
        bridge.thermostat_power(bridge.state(.3), medium(), .02, time_s=2., clock_id="clock",
            support_start_s=0., support_end_s=1., boundary_evidence_id="authored-held-T")
