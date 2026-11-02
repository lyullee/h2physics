"""Actual native physiology, independent heat ledger and explicit application limits."""

import copy
import importlib
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.jos3_thermal import (
    JOS3ThermalResponse,
    NativeJOS3,
    OrdinaryAirEnvironment,
    ThermalDomain,
    ThermalInterval,
    ThermalResponseError,
    ThermalRunEvidence,
    ThermalSubject,
    _digest,
)
from h2physics.core import Origin


@pytest.fixture(scope="module")
def native():
    path = Path(__file__).resolve().parents[1]/"artifacts/native_thermal_packages"
    if not (path/"pythermalcomfort/models/jos3.py").is_file():
        pytest.skip("Reviewed isolated native thermal provider is optional")
    sys.path.append(str(path))
    return NativeJOS3.from_installed()


@pytest.fixture(scope="module")
def prepared(native):
    subject = ThermalSubject(1.74, 72., 18., 35, "male", 2.59, "harris-benedict", "dubois")
    return native.prepare_neutral(subject)


def environment(temperature_k=283.15):
    return OrdinaryAirEnvironment(temperature_k, temperature_k, .3, 40., .7, .45,
                                  1.3, "standing", "authored-uniform-air")


def evidence():
    return ThermalRunEvidence("absolute-test-clock", "test-ENU", "declared-receptor",
        (1., 0., 1.5), "authored-air-history", "authored-subject",
        "explicit-native-neutral-initialization", "authored-air-domain",
        "ordinary-air", 101325., Origin.SYNTHETIC)


def domain(step=10.):
    return ThermalDomain(273.15, 313.15, 283.15, 315.15, step, 1e-6)


def run(native, prepared, *, step=10., intervals=None, context=None):
    return JOS3ThermalResponse(native, domain(step)).run(prepared,
        intervals or (ThermalInterval(100., 160., environment()),),
        evidence=context or evidence())


def test_core_import_is_optional():
    result = subprocess.run([sys.executable, "-X", "utf8", "-c",
        "import sys; import h2physics.adapters.jos3_thermal; "
        "assert 'pythermalcomfort' not in sys.modules and 'numba' not in sys.modules"],
        capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stderr


def test_actual_native_private_copy_and_complete_outputs(native, prepared):
    before = _digest(vars(prepared))
    result = run(native, prepared)
    assert result.source_model is prepared and result.native_model is not prepared
    assert type(result.native_model) is native.model_class
    assert len(result.steps) == len(result.native_outputs) == 6
    assert len(result.native_initial_history) == len(prepared._history)
    assert result.steps[0].native_output is result.native_model._history[-6]
    assert result.native_outputs[-1] is result.native_model._history[-1]
    assert _digest(vars(prepared)) == before == result.source_model_sha256
    assert prepared._time.total_seconds() == 0
    assert result.native_model._time.total_seconds() == 60
    assert result.capacity_j_k.shape == result.initial_body_temperature_k.shape == (85,)
    assert len(result.body_part_names) == 17
    assert sorted(i for _, _, i in result.node_index_map) == list(range(85))
    assert result.injury_probability is None and not result.full_cryogenic_chain_validated


def test_native_storage_and_implicit_boundary_energy(native, prepared):
    result = run(native, prepared)
    previous = result.initial_body_temperature_k
    for step in result.steps:
        independent = np.dot(result.capacity_j_k, step.body_temperature_k-previous)
        assert independent == pytest.approx(step.stored_energy_change_j, abs=1e-7)
        assert abs(step.energy_defect_j) < step.output_rounding_budget_j+1e-6
        assert step.output_rounding_budget_j == pytest.approx(.095*(step.end_s-step.start_s))
        previous = step.body_temperature_k
    assert sum(s.stored_energy_change_j for s in result.steps) < 0
    assert abs(result.steps[0].implicit_sensible_out_w
               -result.steps[0].reported_previous_state_sensible_out_w) > .5


def test_matches_an_unmodified_direct_native_campaign(native, prepared):
    direct = copy.deepcopy(prepared)
    direct.tdb = direct.tr = 10.
    direct.v, direct.rh, direct.clo = .3, 40., .7
    direct._iclo = np.full(17, .45)
    direct.par, direct.posture = 1.3, "standing"
    direct.simulate(6, dtime=10.)
    result = run(native, prepared)
    np.testing.assert_array_equal(result.native_model.t_body, direct.t_body)
    for original, wrapped in zip(direct._history[-6:], result.native_outputs, strict=True):
        assert _digest(original) == _digest(wrapped)


def test_unrounded_snapshots_and_arrays_are_separate_from_mutable_native(native, prepared):
    result = run(native, prepared)
    before = result.steps[-1].body_temperature_k.copy()
    result.native_model.t_body[:] += .01
    np.testing.assert_array_equal(result.steps[-1].body_temperature_k, before)
    with pytest.raises(ValueError):
        result.steps[0].skin_temperature_k[0] = 1


def test_environment_switches_use_exact_declared_command_edges(native, prepared):
    intervals = (ThermalInterval(100., 103.3, environment()),
                 ThermalInterval(103.3, 109.6, environment(298.15)))
    result = run(native, prepared, step=2., intervals=intervals)
    assert result.steps[0].start_s == 100.
    assert result.steps[-1].end_s == pytest.approx(109.6)
    assert any(s.end_s == 103.3 for s in result.steps)
    assert any(s.start_s == 103.3 for s in result.steps)
    assert all(not (s.start_s < 103.3 < s.end_s) for s in result.steps)


def test_native_time_refinement_and_same_prepared_initial_state(native, prepared):
    intervals = (ThermalInterval(100., 400., environment()),)
    results = [run(native, prepared, step=h, intervals=intervals) for h in (10., 5., 2.5)]
    a, b, c = (r.steps[-1].body_temperature_k for r in results)
    assert np.max(abs(b-c)) < np.max(abs(a-b))
    assert np.max(abs(b-c)) < .03
    np.testing.assert_array_equal(results[0].initial_body_temperature_k,
                                  results[2].initial_body_temperature_k)


def test_repeated_campaigns_do_not_depend_on_unused_previous_shivering(native, prepared):
    a, b = run(native, prepared), run(native, prepared)
    np.testing.assert_array_equal(a.steps[-1].body_temperature_k, b.steps[-1].body_temperature_k)
    assert a.input_sha256 == b.input_sha256


def test_prepared_history_and_native_elapsed_offset_are_preserved(native, prepared):
    source = copy.deepcopy(prepared)
    source.simulate(3, dtime=10.)
    before = _digest(vars(source))
    result = run(native, source)
    assert len(result.native_initial_history) == 4
    assert result.native_model._time.total_seconds() == 90.
    assert _digest(vars(source)) == before
    assert result.steps[0].start_s == 100.


@pytest.mark.parametrize("field,value", [("medium", "hydrogen-rich-gas"),
    ("reference_pressure_pa", 80000.), ("origin", Origin.UNRESOLVED),
    ("clock_id", ""), ("initialization_evidence_id", "")])
def test_unqualified_medium_pressure_and_missing_evidence(field, value):
    with pytest.raises(ValueError):
        replace(evidence(), **{field: value})


@pytest.mark.parametrize("field,value", [("relative_humidity_percent", 1.01e2),
    ("clothing_vapor_efficiency", 0.), ("air_speed_m_s", -.1),
    ("clothing_clo", -1.), ("air_temperature_k", np.ones(16))])
def test_units_bounds_and_native_segment_layout(field, value):
    with pytest.raises(ValueError):
        replace(environment(), **{field: value})


def test_gaps_and_sub_microsecond_durations_rejected(native, prepared):
    with pytest.raises(ValueError, match="microsecond"):
        ThermalInterval(0., .0000001, environment())
    with pytest.raises(ValueError, match="microsecond"):
        ThermalInterval(0., 1e-10, environment())
    with pytest.raises(ValueError, match="microsecond"):
        replace(domain(), maximum_step_s=1e-10)
    with pytest.raises(ThermalResponseError, match="contiguous") as caught:
        run(native, prepared, intervals=(ThermalInterval(0., 1., environment()),
                                        ThermalInterval(2., 3., environment())))
    assert caught.value.native_model is None and caught.value.__cause__ is not None


def test_large_absolute_clock_cannot_repeat_an_unadvanced_step(native, prepared):
    interval = ThermalInterval(1e18, 1e18+512., environment())
    with pytest.raises(ThermalResponseError, match="forward native step") as caught:
        run(native, prepared, intervals=(interval,))
    assert caught.value.native_model is None and caught.value.completed_steps == ()
    assert prepared._time.total_seconds() == 0


def test_epoch_clock_does_not_accumulate_float_substep_drift(native, prepared):
    result = run(native, prepared, step=.1,
        intervals=(ThermalInterval(1.8e9, 1.8e9+1., environment()),))
    assert len(result.steps) == 10
    assert result.steps[-1].end_s == 1.8e9+1.
    assert result.native_model._time.total_seconds() == 1.
    assert all(step.end_s > step.start_s for step in result.steps)


def test_original_native_failure_and_completed_command_prefix_retained(native, prepared):
    intervals = (ThermalInterval(0., 10., environment()),
                 ThermalInterval(10., 20., replace(environment(), posture="lying")))
    # A supported native posture must execute; a later body-domain rejection must
    # retain the actual completed native step, clock and unmodified source.
    assert len(run(native, prepared, intervals=intervals).steps) == 2
    threshold = float(np.min(prepared.t_body+273.15))-.02
    model = JOS3ThermalResponse(native, replace(domain(), minimum_body_k=threshold))
    with pytest.raises(ThermalResponseError, match="body temperatures") as caught:
        model.run(prepared, [ThermalInterval(0., 200., environment())], evidence=evidence())
    error = caught.value
    assert isinstance(error.__cause__, ValueError) and error.native_model is not None
    assert error.native_model._history[-1] is not prepared._history[-1]
    assert error.native_model._time.total_seconds() > 0
    assert prepared._time.total_seconds() == 0


@pytest.mark.parametrize("attribute,value,match", [("_hc", np.ones(17), "Custom native"),
    ("ex_q", np.ones(85), "Custom native"),
    ("options", {"limit_dshiv/dt": True}, "previous-shivering")])
def test_native_boundaries_and_global_rate_memory_not_silently_admitted(native, prepared,
                                                                      attribute, value, match):
    source = copy.deepcopy(prepared)
    setattr(source, attribute, value)
    with pytest.raises(ThermalResponseError, match=match) as caught:
        run(native, source)
    assert caught.value.native_model is not None and caught.value.completed_steps == ()


def test_bound_native_method_replacement_rejected(native, prepared, monkeypatch):
    monkeypatch.setattr(native.model_class, "simulate", lambda *args, **kwargs: None)
    with pytest.raises(ThermalResponseError, match="bindings") as caught:
        run(native, prepared)
    assert caught.value.native_model is None


def test_actual_native_heat_function_rebinding_rejected(native, prepared, monkeypatch):
    module = importlib.import_module("pythermalcomfort.models.jos3")
    monkeypatch.setattr(module.threg, "conv_coef", lambda **kwargs: np.ones(17))
    with pytest.raises(ThermalResponseError, match="function bindings"):
        run(native, prepared)


def test_structural_provider_class_is_not_native_provenance(native):
    with pytest.raises(TypeError, match="actual installed"):
        NativeJOS3(native.package, type("FakeJOS3", (), {}))


def test_actual_native_body_index_definition_is_not_a_changeable_label(native, prepared, monkeypatch):
    module = importlib.import_module("pythermalcomfort.models.jos3")
    monkeypatch.setitem(module.matrix.IDICT, "CB", 1)
    with pytest.raises(ThermalResponseError, match="index definitions"):
        run(native, prepared)


def test_unsupported_disabled_jit_profile_is_explicitly_rejected(native):
    target = Path(__file__).resolve().parents[1]/"artifacts/native_thermal_packages"
    code = (f"import sys;sys.path.insert(0,{str(target)!r});"
        "from h2physics.adapters.jos3_thermal import NativeJOS3;NativeJOS3.from_installed()")
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "NUMBA_DISABLE_JIT": "1"}, check=False)
    assert result.returncode != 0 and "enabled native JIT" in result.stderr
