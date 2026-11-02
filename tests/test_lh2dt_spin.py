"""Actual native rotor/kinetics and independent enthalpy-coupling limits."""

import importlib
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq

from h2physics.adapters.lh2dt_spin import (
    Lh2dtOrthoPara,
    Lh2dtSpinCalorimeter,
    SpinCutoffError,
    SpinDomain,
    SpinEnthalpyReference,
    SpinEvidence,
)
from h2physics.core import Origin


def native_api():
    pytest.importorskip("CoolProp")
    target = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
    if not (target / "lh2dt/ortho_para.py").is_file():
        pytest.skip("Install the separately reviewed optional native LH2DT target")
    if str(target) not in sys.path:
        sys.path.insert(0, str(target))
    module = importlib.import_module("lh2dt.ortho_para")
    assert Path(module.__file__).resolve() == (target / "lh2dt/ortho_para.py").resolve()
    return module


def kinetics(*, rate=1e-5, gap=600000., cutoff=24, minimum=1., maximum=1000.):
    native = native_api()
    parameters = native.OrthoParaKineticsParameters(rate, gap, 85.4, cutoff)
    return Lh2dtOrthoPara(native, parameters,
        evidence=SpinEvidence("authored-constant-rate-not-a-catalyst-fit",
            "authored-constant-enthalpy-gap", "dilute-molecular-H2-rotor/reference-calorimeter",
            ("authored-synthetic-parameters", "https://doi.org/10.1051/0004-6361/201527209"),
            Origin.SYNTHETIC),
        domain=SpinDomain(minimum, maximum, 96, 1e-10, "authored-T/cutoff-domain"))


def reference(**changes):
    return replace(SpinEnthalpyReference(1., 0., "explicit-para-endmember-relative-spin-enthalpy"), **changes)


def calorimeter(model=None, **changes):
    kwargs = dict(mass_kg=.01, pressure_pa=1000., pressure_evidence_id="held-low-pressure-reference",
        sensible_heat_capacity_j_k=1000., sensible_evidence_id="authored-frozen-sensible-Cp",
        enthalpy_reference=reference(), reference_temperature_k=20.)
    kwargs.update(changes)
    return Lh2dtSpinCalorimeter(model or kinetics(), **kwargs)


def test_native_even_odd_weights_low_and_high_temperature_limits():
    model = kinetics()
    low = model.equilibrium(10)
    two_level = 1/(1+9*math.exp(-2*85.4/10))
    assert low.para_fraction == pytest.approx(two_level, abs=2e-15)
    assert low.para_fraction > .999999
    # At finite 1000 K the rotor has a real, tiny departure from its limit.
    assert model.equilibrium(1000).para_fraction == pytest.approx(.25, abs=3e-12)
    mathematical_high_t = model.native.equilibrium_para_fraction(
        10000, rotational_temperature_K=85.4, maximum_rotational_level=96)
    assert mathematical_high_t == pytest.approx(.25, abs=2e-15)
    assert model.equilibrium(20).para_fraction > .998
    assert low.native_rotational_level == 24 and low.reference_rotational_level == 96


def test_finite_cutoff_is_checked_against_larger_native_sum_and_failures_retained():
    model = kinetics(cutoff=1)
    with pytest.raises(SpinCutoffError) as failure:
        model.equilibrium(300)
    assert failure.value.result.cutoff_difference > .01
    assert failure.value.result.native_rotational_level == 1
    adequate = kinetics(cutoff=16)
    assert adequate.equilibrium(1000).cutoff_difference < 1e-10


def test_frozen_rate_and_exact_native_constant_temperature_advance():
    frozen = kinetics(rate=0)
    initial = frozen.state(.25)
    point = frozen.rate(initial, 20, .01)
    assert point.para_fraction_rate_s == point.conversion_heat_w == 0
    assert frozen.advance(initial, 20, 1e7).para_fraction == .25
    model = kinetics()
    initial = model.state(.25)
    target = model.equilibrium(20).para_fraction
    for duration in (0., 1e3, 1e5, 1e6):
        actual = model.advance(initial, 20, duration)
        expected = target+(.25-target)*math.exp(-1e-5*duration)
        assert actual.para_fraction == pytest.approx(expected, abs=2e-15)
        assert isinstance(actual, model.native.OrthoParaState)


def test_native_heat_rate_and_reverse_conversion_sign_use_actual_fraction_change():
    model = kinetics()
    forward = model.rate(model.state(.25), 20, .01)
    reverse = model.rate(model.state(1.), 300, .01)
    assert forward.para_fraction_rate_s > 0 and forward.conversion_heat_w > 0
    assert reverse.para_fraction_rate_s < 0 and reverse.conversion_heat_w < 0
    assert forward.conversion_heat_w == pytest.approx(.01*600000*forward.para_fraction_rate_s)
    assert forward.native_parameters is model.parameters


@pytest.mark.parametrize("temperature,fraction", [(20., .25), (300., 1.)])
def test_exact_thermostat_enthalpy_ledger_and_long_absolute_clock(temperature, fraction):
    model = kinetics()
    initial = model.state(fraction)
    times = np.array([10., 110., 10010., 100010., 1000010.])
    trace = model.thermostat(initial, temperature_k=temperature, mass_kg=.01,
        pressure_pa=1000, time_s=times, clock_id="absolute-case",
        pressure_evidence_id="held-pressure", enthalpy_reference=reference())
    target = model.equilibrium(temperature).para_fraction
    for sample in trace.samples:
        expected = target+(fraction-target)*math.exp(-1e-5*(sample.time_s-10))
        assert sample.native_state.para_fraction == pytest.approx(expected, abs=2e-15)
        heat = -.01*600000*(expected-fraction)
        assert sample.cumulative_external_heat_j == pytest.approx(heat, abs=2e-10)
        assert abs(sample.enthalpy_balance_residual_j) < 2e-10
    final = trace.samples[-1]
    assert final.cumulative_external_heat_j < 0 if fraction == .25 else final.cumulative_external_heat_j > 0
    assert trace.kinetics is model and trace.pressure_pa == 1000
    assert trace.storage_constraint.startswith("constant-pressure enthalpy")


def test_exact_thermostat_refinement_and_restart_preserve_native_state():
    model = kinetics()
    kwargs = dict(temperature_k=20., mass_kg=.01, pressure_pa=1000, clock_id="absolute-case",
                  pressure_evidence_id="held-pressure", enthalpy_reference=reference())
    initial = model.state(.25)
    coarse = model.thermostat(initial, time_s=[10, 1000010], **kwargs)
    fine = model.thermostat(initial, time_s=np.linspace(10, 1000010, 101), **kwargs)
    assert fine.samples[-1].native_state.para_fraction == pytest.approx(
        coarse.samples[-1].native_state.para_fraction, abs=3e-15)
    prefix = model.thermostat(initial, time_s=[10, 500010], **kwargs)
    suffix = model.thermostat(prefix.samples[-1].native_state, time_s=[500010, 1000010], **kwargs)
    assert suffix.samples[-1].native_state == coarse.samples[-1].native_state


def test_coupled_constant_pressure_adiabatic_enthalpy_reference_and_equilibrium_limit():
    model = kinetics()
    finite = calorimeter(model)
    trace = finite.adiabatic(model.state(.25), temperature_k=20,
        time_s=np.linspace(10, 2000010, 101), clock_id="absolute-calorimeter",
        maximum_time_step_s=10000)
    final = trace.samples[-1]
    fraction = final.native_state.para_fraction
    assert final.temperature_k == pytest.approx(20+.01*600000/1000*(fraction-.25), abs=1e-12)
    root = brentq(lambda x: model.equilibrium(20+6*(x-.25)).para_fraction-x, .25, 1.)
    assert fraction == pytest.approx(root, abs=3e-9)
    assert final.temperature_k > 20
    assert max(abs(s.enthalpy_balance_residual_j) for s in trace.samples) < 5e-11
    assert all(s.external_power.total_w == 0 for s in trace.samples)
    assert trace.native_solver_result.success
    assert trace.sensible_heat_capacity_j_k == 1000


def test_zero_gap_coupled_native_kinetics_matches_independent_exact_isothermal_limit():
    model = kinetics(gap=0)
    trace = calorimeter(model).adiabatic(model.state(.25), temperature_k=20,
        time_s=np.linspace(0, 5e5, 31), clock_id="zero-gap", maximum_time_step_s=10000)
    target = model.equilibrium(20).para_fraction
    for sample in trace.samples:
        expected = target+(.25-target)*math.exp(-1e-5*sample.time_s)
        assert sample.native_state.para_fraction == pytest.approx(expected, abs=2e-10)
        assert sample.temperature_k == 20
        assert sample.conversion_heat_w == 0


def test_coupled_adiabatic_refinement_reverse_heat_and_reference_zero_invariance():
    model = kinetics()
    initial = model.state(1.)
    times = np.linspace(100, 500100, 51)
    fine = calorimeter(model).adiabatic(initial, temperature_k=300, time_s=times,
        clock_id="reverse", maximum_time_step_s=5000, relative_tolerance=1e-11)
    coarse = calorimeter(model).adiabatic(initial, temperature_k=300, time_s=times,
        clock_id="reverse", maximum_time_step_s=20000, relative_tolerance=1e-9)
    shifted = calorimeter(model, enthalpy_reference=reference(
        reference_specific_enthalpy_j_kg=2.3e7, reference_id="explicit-shifted-spin-zero"),
        sensible_reference_enthalpy_j=-8e5).adiabatic(initial, temperature_k=300, time_s=times,
        clock_id="reverse", maximum_time_step_s=5000, relative_tolerance=1e-11)
    assert fine.samples[-1].temperature_k < 300
    assert fine.samples[0].conversion_heat_w < 0
    assert abs(fine.samples[-1].temperature_k-coarse.samples[-1].temperature_k) < 1e-7
    for first, other in zip(fine.samples, shifted.samples, strict=True):
        assert first.temperature_k == other.temperature_k
        assert first.native_state == other.native_state


@pytest.mark.parametrize("fraction", [-.1, 1.1, True, float("nan")])
def test_unphysical_native_fractions_are_not_repaired(fraction):
    with pytest.raises(ValueError):
        kinetics().state(fraction)


def test_domain_clock_cutoff_boolean_and_native_parameter_changes_fail():
    model = kinetics()
    for value in (0, -1, True, float("nan"), 1001):
        with pytest.raises(ValueError):
            model.equilibrium(value)
    with pytest.raises(ValueError):
        model.advance(model.state(.25), 20, -1)
    with pytest.raises(ValueError, match="boolean"):
        kinetics(cutoff=True)
    object.__setattr__(model.parameters, "conversion_rate_constant_s", .5)
    with pytest.raises(ValueError, match="rebinding"):
        model.equilibrium(20)
    model = kinetics()
    with pytest.raises(ValueError, match="increasing"):
        model.thermostat(model.state(.25), temperature_k=20, mass_kg=.01, pressure_pa=1000,
            time_s=[10, 10], clock_id="bad-clock", pressure_evidence_id="held-pressure",
            enthalpy_reference=reference())
    with pytest.raises(ValueError, match="spin domain"):
        calorimeter(model, sensible_heat_capacity_j_k=.01).adiabatic(model.state(.25),
            temperature_k=20, time_s=[0, 1000], clock_id="out-of-domain",
            maximum_time_step_s=1)
