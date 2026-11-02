"""Actual native harm laws; histories and model choices are authored fixtures."""

import math
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from h2physics.adapters.hyram_exposure import (
    ExposureEvaluationError,
    ExposureHistory,
    ExposureReceptor,
    ExposureVerificationError,
    HyRAMExposure,
    NativeHarmSelection,
    PressurePeak,
)
from h2physics.core import Origin


@pytest.fixture(scope="module")
def engine():
    pytest.importorskip("hyram", reason="Separately installed optional HyRAM6.1")
    return HyRAMExposure()


def receptor():
    return ExposureReceptor("authored-receptor", "global-xyz", (4., -1., 1.5), "supplied-local-exposure-plane")


def history(values=(40000.,), times=(100., 110.), quantity="incident_radiant_flux", interpolation="left_hold", **kwargs):
    return ExposureHistory(receptor(), times, values, quantity,
        "Pa" if quantity == "gauge_overpressure" else "W/m2", interpolation,
        "authored-absolute-clock", "conditional-supplied-field", "authored-field-basis", Origin.SYNTHETIC, **kwargs)


def selection(model_id):
    return NativeHarmSelection(model_id, 5., "explicit-native-model-choice", "authored-not-qualified-applicability", Origin.SYNTHETIC)


def test_default_module_import_keeps_optional_hyram_unloaded():
    result = subprocess.run([sys.executable, "-c", "import sys; import h2physics.adapters.hyram_exposure; assert 'hyram' not in sys.modules"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("model_id", ["eise", "tsao", "tno", "lees"])
def test_constant_incident_heat_uses_actual_native_dose_model_and_cdf(engine, model_id):
    result = engine.thermal_response(history(), selection(model_id), additivity_evidence_id="explicit-additive-no-recovery")
    native = engine.native_module
    assert result.thermal_dose == pytest.approx(native.calculate_thermal_dose(40000., 10.))
    assert result.probability == pytest.approx(native.compute_thermal_fatality_prob(model_id, 40000., 10., mean=5.))
    oracle = .5*(1+math.erf((result.native_probit-5.)/math.sqrt(2.)))
    assert result.probability == pytest.approx(oracle, abs=1e-15)
    assert result.native_module is native and result.native_result is result.native_calls[-1].raw
    assert result.receptor_id == "authored-receptor" and result.clock_id == "authored-absolute-clock"
    assert result.support_s == (100., 110.) and result.status == "conditional-on-supplied-exposure"


def test_pulse_additivity_is_dose_not_mean_flux_or_fluence(engine):
    pulse = engine.thermal_response(history((40000., 0.), (100., 105., 110.)), selection("eise"), additivity_evidence_id="no-recovery")
    smooth = engine.thermal_response(history((20000.,)), selection("eise"), additivity_evidence_id="no-recovery")
    assert pulse.fluence_j_m2 == smooth.fluence_j_m2 == 200000.
    assert pulse.thermal_dose/smooth.thermal_dose == pytest.approx(2**(1/3))
    assert pulse.probability > smooth.probability
    refined = engine.thermal_dose(history(np.full(32, 40000.), np.linspace(100., 110., 33)), additivity_evidence_id="no-recovery")
    assert refined.thermal_dose == pytest.approx(engine.native_module.calculate_thermal_dose(40000., 10.))


def test_native_linear_history_quadrature_matches_independent_power_integral_and_refinement(engine):
    a, b, duration = 12000., 36000., 6.
    coarse = engine.thermal_dose(history((a, b), (100., 106.), interpolation="linear"), additivity_evidence_id="linear-dose-accumulation")
    refined = engine.thermal_dose(history(np.linspace(a, b, 17), np.linspace(100., 106., 17), interpolation="linear"),
                                  additivity_evidence_id="linear-dose-accumulation")
    analytic = duration*3/7*(b**(7/3)-a**(7/3))/(b-a)
    assert coarse.thermal_dose == pytest.approx(analytic, rel=2e-14)
    assert refined.thermal_dose == pytest.approx(coarse.thermal_dose, rel=2e-14)
    assert coarse.quadrature_records and coarse.native_calls


def test_absorbed_dose_is_separate_and_never_silently_used_as_incident_harm(engine):
    absorbed = history((20000.,), quantity="absorbed_radiant_flux")
    diagnostic = engine.thermal_dose(absorbed, additivity_evidence_id="absorbed-mathematical-dose-only")
    assert diagnostic.probability is None and diagnostic.selection is None
    assert diagnostic.fluence_j_m2 == 200000.
    with pytest.raises(ExposureEvaluationError, match="incident") as caught:
        engine.thermal_response(absorbed, selection("eise"), additivity_evidence_id="explicit")
    assert caught.value.input is absorbed and not caught.value.native_calls


def test_pressure_waveform_positive_phase_has_exact_peak_impulse_and_retained_negative_phase(engine):
    signal = history((0., 100000., 0., -20000.), (100., 100.05, 100.1, 100.15),
                     quantity="gauge_overpressure", interpolation="linear")
    result = engine.pressure_response(signal, selection("head"), positive_phase_evidence_id="explicit-positive-gauge-phase")
    assert result.peak_overpressure_pa == 100000.
    assert result.positive_impulse_pa_s == pytest.approx(5000., abs=1e-7)
    assert result.probability == pytest.approx(engine.native_module.compute_overpressure_fatality_prob("head", 100000., 5000., mean=5.), rel=1e-12)
    assert result.input.values[-1] == -20000.


@pytest.mark.parametrize("model_id", ["leis", "lhse", "head", "coll"])
def test_native_pressure_model_identity_units_and_peak_vs_waveform(engine, model_id):
    summary = PressurePeak(receptor(), 100000., 5000., "clock", (100., 101.), "supplied-summary", "local-gauge-pressure", Origin.SYNTHETIC)
    result = engine.pressure_response(summary, selection(model_id), positive_phase_evidence_id="supplied-summary-evidence")
    assert result.probability == pytest.approx(engine.native_module.compute_overpressure_fatality_prob(model_id, 100000., 5000., mean=5.))
    if model_id in {"leis", "lhse"}:
        ignored_zero = engine.pressure_response(replace(summary, positive_impulse_pa_s=0.), selection(model_id), positive_phase_evidence_id="unused-impulse")
        assert ignored_zero.probability == result.probability
    else:
        with pytest.raises(ExposureEvaluationError, match="requires supplied") as caught:
            engine.pressure_response(replace(summary, positive_impulse_pa_s=None), selection(model_id), positive_phase_evidence_id="missing-impulse")
        assert caught.value.input.positive_impulse_pa_s is None


def test_zero_exposure_uses_native_zero_wrapper_and_longer_wave_impulse_changes_impact(engine):
    zero = engine.thermal_response(history((0.,)), selection("eise"), additivity_evidence_id="zero-exposure")
    assert zero.probability == 0. and zero.native_probit is None
    assert zero.native_calls[-1].function is engine.native_module.compute_thermal_fatality_prob
    a = history((100000.,), (100., 100.025), quantity="gauge_overpressure")
    b = history((100000.,), (100., 100.05), quantity="gauge_overpressure")
    short = engine.pressure_response(a, selection("head"), positive_phase_evidence_id="positive-phase")
    long = engine.pressure_response(b, selection("head"), positive_phase_evidence_id="positive-phase")
    assert short.peak_overpressure_pa == long.peak_overpressure_pa
    assert long.positive_impulse_pa_s == pytest.approx(2*short.positive_impulse_pa_s)
    assert long.probability > short.probability


@pytest.mark.parametrize("values,valid", [((-1.,), None), ((np.nan,), None), ((10000.,), [False]), ((np.inf,), [True])])
def test_missing_invalid_or_signed_heat_is_retained_without_filling(engine, values, valid):
    signal = history(values, valid=valid)
    with pytest.raises(ExposureEvaluationError) as caught:
        engine.thermal_response(signal, selection("eise"), additivity_evidence_id="explicit")
    assert caught.value.input is signal and caught.value.native_module is engine.native_module
    assert caught.value.__cause__ is not None and not caught.value.native_calls


@pytest.mark.parametrize("value", [1e308, 1e-300])
def test_native_dose_overflow_underflow_retains_raw_calls_or_failed_native_call(engine, value):
    with pytest.raises(ExposureEvaluationError) as caught:
        engine.thermal_dose(history((value,)), additivity_evidence_id="numeric-limit-probe")
    assert caught.value.native_calls or caught.value.failed_call is not None
    assert caught.value.__cause__ is not None


def test_no_default_model_mean_clock_frame_or_unit_conversion_is_inferred(engine):
    for chosen in (selection("unknown"), replace(selection("eise"), normal_distribution_mean=0.)):
        with pytest.raises(ExposureEvaluationError):
            engine.thermal_response(history(), chosen, additivity_evidence_id="explicit")
    with pytest.raises(ExposureEvaluationError):
        engine.thermal_response(history(), selection("eise"), additivity_evidence_id="")
    for change in (dict(unit="kW/m2"), dict(interpolation="unknown"), dict(time_s=[100., 100.]), dict(values=[True])):
        with pytest.raises(ValueError):
            replace(history(), **change)


def test_exposed_native_mean_convention_cannot_be_rebound_under_the_old_model_evidence(engine):
    other = HyRAMExposure(engine.native_module)
    other.native_normal_mean = 0.
    with pytest.raises(ExposureEvaluationError, match="convention binding changed") as caught:
        other.thermal_response(history(), replace(selection("eise"), normal_distribution_mean=0.),
                               additivity_evidence_id="explicit")
    assert not caught.value.native_calls


def test_owner_verification_replays_thermal_pressure_and_absorbed_dose_returning_original_identity(engine):
    thermal = engine.thermal_response(history((12000., 36000.), (100., 106.), interpolation="linear"), selection("eise"),
                                      additivity_evidence_id="explicit-linear-dose")
    pressure = engine.pressure_response(PressurePeak(receptor(), 100000., 5000., "clock", (100., 101.),
        "supplied-summary", "local-gauge-pressure", Origin.SYNTHETIC), selection("head"), positive_phase_evidence_id="explicit-summary")
    absorbed = engine.thermal_dose(history((20000.,), quantity="absorbed_radiant_flux"), additivity_evidence_id="diagnostic-only")
    for result in (thermal, pressure, absorbed):
        assert engine.verify_result(result) is result


@pytest.mark.parametrize("field", ["probability", "thermal_dose", "native_probit", "native_result",
    "detached_native_result", "detached_native_probit", "model", "mean", "evidence", "input", "source", "status", "calls"])
def test_owner_verification_rejects_cached_summary_model_mean_or_source_replacement(engine, field):
    result = engine.thermal_response(history(), selection("eise"), additivity_evidence_id="explicit-no-recovery")
    replacement = {
        "probability": dict(probability=.9),
        "thermal_dose": dict(thermal_dose=result.thermal_dose*1.1),
        "native_probit": dict(native_probit=np.float64(result.native_probit+1.)),
        "native_result": dict(native_result=np.float64(.9)),
        "detached_native_result": dict(native_result=np.float64(float(result.native_result))),
        "detached_native_probit": dict(native_probit=np.float64(float(result.native_probit))),
        "model": dict(selection=replace(result.selection, model_id="tsao")),
        "mean": dict(selection=replace(result.selection, normal_distribution_mean=0.)),
        "evidence": dict(selection=replace(result.selection, evidence_id="unbound-evidence")),
        "input": dict(input=replace(result.input, source_id="unbound-source")),
        "source": dict(native_source_sha256="0"*64),
        "status": dict(status="accepted-source-fire-chain"),
        "calls": dict(native_calls=result.native_calls[:-1]),
    }[field]
    altered = replace(result, **replacement)
    with pytest.raises(ExposureVerificationError) as caught:
        engine.verify_result(altered)
    assert caught.value.supplied is altered and caught.value.__cause__ is not None
    if field == "probability":
        assert caught.value.replayed.probability == result.probability


def test_owner_verification_rejects_consistently_replaced_probability_and_native_raw_record(engine):
    original = engine.thermal_response(history(), selection("eise"), additivity_evidence_id="explicit")
    forged_call = replace(original.native_calls[-1], raw=np.float64(.9))
    altered = replace(original, probability=.9, native_result=forged_call.raw,
                      native_calls=(*original.native_calls[:-1], forged_call))
    with pytest.raises(ExposureVerificationError) as caught:
        engine.verify_result(altered)
    assert caught.value.replayed.native_result == original.native_result
    with pytest.raises(ExposureVerificationError, match="actual ExposureResult"):
        engine.verify_result(SimpleNamespace(probability=original.probability, status=original.status))


def test_owner_verification_checks_active_quadrature_but_ignores_uninitialized_workspace_tails(engine):
    result = engine.thermal_response(history((12000., 36000.), (100., 106.), interpolation="linear"), selection("eise"),
                                     additivity_evidence_id="explicit-linear-dose")
    value, error, original_info = result.quadrature_records[0]
    info = {key: val.copy() if isinstance(val, np.ndarray) else val for key, val in original_info.items()}
    active = info["last"]
    for name in ("alist", "blist", "rlist", "elist"):
        info[name][active:] = np.nan
    info["iord"][active:] = -999
    tails_changed = replace(result, quadrature_records=((value, error, info),))
    assert engine.verify_result(tails_changed) is tails_changed
    info["rlist"][0] += 1.
    with pytest.raises(ExposureVerificationError, match="quadrature"):
        engine.verify_result(tails_changed)
