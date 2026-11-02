"""Actual native transmitter and independently authored observation limits."""

import importlib
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2physics.adapters.lh2dt_instrumentation import (
    Lh2dtTransmitter,
    TransmitterClosureError,
    TransmitterEvidence,
)
from h2physics.core import Origin, TimeSeries
from h2physics.observations import Variable

TARGET = Path(__file__).resolve().parents[1] / "artifacts/native_packages"
if not (TARGET / "lh2dt/instrumentation.py").is_file():
    pytest.skip("Install the reviewed optional native LH2DT target", allow_module_level=True)
sys.path.insert(0, str(TARGET))
native = importlib.import_module("lh2dt.instrumentation")
assert Path(native.__file__).resolve() == (TARGET / "lh2dt/instrumentation.py").resolve()
VARIABLE = Variable("pressure", "pressure", "Pa", "absolute")


def instrument(**parameters):
    values = dict(lower_range=0., upper_range=1e6, time_constant_s=2.)
    values.update(parameters)
    sensor = native.FirstOrderTransmitter(native.TransmitterParameters(**values))
    evidence = TransmitterEvidence("P1", "vessel-gas-port", VARIABLE, "authored-calibration",
        "authored-step-response", ("synthetic-verification",), Origin.SYNTHETIC)
    return Lh2dtTransmitter(sensor, evidence=evidence)


def process(times=(10., 10.3, 11.4, 14.), values=None, **changes):
    if values is None:
        values = np.full((len(times), 1), 3e5)
    values = np.asarray(values, dtype=float).reshape(-1, 1)
    fields = dict(time_s=times, values=values, channels=("pressure",), units=("Pa",),
        valid=np.isfinite(values), clock_id="authored-absolute-clock", origin=Origin.PREDICTED,
        source_id="authored-process", quantities=("pressure",), basis_ids=("absolute",))
    fields.update(changes)
    return TimeSeries(**fields)


def run(sensor, series, *, initial=None, **changes):
    fields = dict(channel="pressure", initial_native_state=(sensor.initialize(1e5)
        if initial is None else initial), initial_time_s=series.time_s[0],
        location_id="vessel-gas-port")
    fields.update(changes)
    return sensor.run(series, **fields)


def test_irregular_native_step_matches_analytic_and_retains_actual_objects():
    sensor, series = instrument(), process()
    trace = run(sensor, series)
    expected = 3e5-2e5*np.exp(-(series.time_s-10)/2)
    assert trace.prediction.values[:, 0] == pytest.approx(expected, abs=1e-9)
    assert trace.native_transmitter is sensor.native and trace.input_series is series
    assert isinstance(trace.final_native_state, native.TransmitterState)
    assert isinstance(trace.native_readings[-1], native.TransmitterReading)
    assert trace.prediction.origin == Origin.PREDICTED
    assert trace.prediction.clock_id == series.clock_id
    assert not trace.prediction.values.flags.writeable


def test_left_hold_final_value_and_zero_lag_semantics_are_explicit():
    series = process((10., 11., 12.), [2e5, 4e5, 9e5])
    finite = run(instrument(time_constant_s=1.), series)
    first = 2e5-1e5*math.exp(-1)
    assert finite.prediction.values[:, 1] == pytest.approx(
        [1e5, first, 4e5+(first-4e5)*math.exp(-1)])
    instantaneous = run(instrument(time_constant_s=0.), series)
    assert instantaneous.prediction.values[:, 0] == pytest.approx([1e5, 2e5, 4e5])


def test_native_scale_bias_clipping_quantization_and_bounds_are_not_process_truth():
    sensor = instrument(time_constant_s=0., upper_range=5e5, scale_factor=1.1,
                        bias=-123., resolution=100., accuracy_fraction_of_span=.002)
    trace = run(sensor, process((0., 1., 2.), [123456., 9e5, 1e5]))
    values = trace.prediction.values
    assert values[1, 0] == pytest.approx(135700.)
    assert values[1, 1] == 123456.
    assert values[1, 2] == pytest.approx(1.1*123456-123)
    assert values[2, 0] == 5e5 and values[2, 5] == 1.
    assert values[:, 3] == pytest.approx([50.]*3)
    assert values[:, 4] == pytest.approx([1000.]*3)
    assert values[1, 5] == 0.


def test_exact_native_constant_hold_has_refinement_and_continuation_identity():
    sensor = instrument()
    coarse = run(sensor, process((10., 14.)))
    fine_series = process(np.linspace(10., 14., 81))
    fine = run(sensor, fine_series)
    assert fine.prediction.values[-1, 0] == pytest.approx(coarse.prediction.values[-1, 0], abs=1e-8)
    prefix = run(sensor, process(fine_series.time_s[:41]))
    suffix = run(sensor, process(fine_series.time_s[40:]), initial=prefix.final_native_state)
    assert suffix.prediction.values[-1, 0] == pytest.approx(fine.prediction.values[-1, 0], abs=1e-9)


@pytest.mark.parametrize("changes", [{"units": ("bar",)}, {"quantities": ("reported_pressure",)},
                                  {"basis_ids": ("gauge",)}])
def test_observation_unit_quantity_and_reference_mismatches_fail(changes):
    with pytest.raises(ValueError, match="quantity, unit or"):
        run(instrument(), process(**changes))


def test_missing_process_clock_start_and_location_fail_without_reconstruction():
    with pytest.raises(ValueError, match="Missing"):
        run(instrument(), process(values=[3e5, np.nan, 3e5, 3e5]))
    for changes in ({"initial_time_s": 9.}, {"location_id": "vessel-wall"}):
        with pytest.raises(ValueError):
            run(instrument(), process(), **changes)


def test_native_parameter_replacement_and_in_place_evidence_changes_fail():
    sensor = instrument()
    sensor.native.parameters = replace(sensor.parameters, time_constant_s=3.)
    with pytest.raises(ValueError, match="ownership"):
        run(sensor, process())
    sensor = instrument()
    object.__setattr__(sensor.parameters, "bias", 42.)
    with pytest.raises(ValueError, match="without rebinding"):
        run(sensor, process())


def test_invalid_native_result_keeps_original_state_and_reading():
    sensor = instrument()
    initial = sensor.initialize(1e5)
    broken = replace(sensor.native.read(initial), indicated_value=2e6)
    sensor.native.read = lambda state: broken
    with pytest.raises(TransmitterClosureError, match="range") as failed:
        run(sensor, process(), initial=initial)
    assert failed.value.native_state is initial and failed.value.native_reading is broken


def test_pressure_without_basis_is_not_an_implicit_absolute_instrument():
    with pytest.raises(ValueError, match="basis"):
        TransmitterEvidence("P", "port", Variable("P", "pressure", "Pa"), "cal", "response",
                            ("authored",), Origin.SYNTHETIC)


def test_numpy_scalar_native_parameters_keep_boolean_saturation_diagnostics():
    sensor = instrument(lower_range=np.float64(0.), upper_range=np.float64(2e5),
                        scale_factor=np.float64(1.), time_constant_s=0.)
    trace = run(sensor, process())
    assert trace.prediction.values[-1, 0] == 2e5
    assert trace.prediction.values[-1, 5] == 1.
