"""Actual finite gas/transmitter/native learned-monitor replay on authored signals."""

import hashlib
import importlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.adapters.cantera import MechanismBasis, ReactiveState
from h2physics.adapters.cantera_volume import CanteraOpenGasVolume, GasHeatBoundary
from h2physics.adapters.lh2dt_instrumentation import Lh2dtTransmitter, TransmitterEvidence
from h2physics.adapters.process_monitoring import (
    MonitoringNativeError,
    NativeProcessMonitoring,
    NativeResidualMonitor,
    ResidualContext,
    ResidualFeature,
    residual_batch,
)
from h2physics.core import Origin, TimeSeries
from h2physics.observations import Variable

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ("src/h2physics/adapters/process_monitoring.py", "tests/test_process_monitoring.py",
          "scripts/check_process_monitoring.py")


def fingerprints():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in INPUTS}


def native_provider():
    target = ROOT/"artifacts/native_monitoring_packages"
    if not (target/"process_monitoring/pipeline.py").exists():
        raise RuntimeError("Install the reviewed immutable native monitoring source/dependencies separately")
    if str(target) not in sys.path:
        sys.path.append(str(target))
    return NativeProcessMonitoring.from_installed()


def physical_reference():
    """Existing native finite enclosure and existing native instrument owners."""
    import cantera as ct

    target = ROOT/"artifacts/native_packages"
    if str(target) not in sys.path:
        sys.path.append(str(target))
    instruments = importlib.import_module("lh2dt.instrumentation")
    raw = (Path(ct.__file__).parent/"data/h2o2.yaml").read_bytes()
    basis = MechanismBasis("installed-H2-thermochemistry-monitoring-verification",
        hashlib.sha256(raw).hexdigest(), "Cantera-BSD-3-Clause; upstream species provenance",
        ("https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html",),
        310., 1000., 5e4, 5e5)

    def phase():
        donor = ct.Solution(yaml=raw.decode("utf-8"), name="ohmech")
        return ct.Solution(thermo="ideal-gas", kinetics=None, species=[donor.species("H2")])

    times = np.arange(100., 221.)
    clock = "authored-finite-volume-reference-clock"
    heat = GasHeatBoundary("signed-test-heater", clock, 100., 222.,
        ReactiveState(350., 2e5, {"H2": 1.}), 1.,
        heat_flux_w_m2=lambda t: 20.*np.cos(2*np.pi*(t-100.)/120.))
    volume = CanteraOpenGasVolume(phase, basis)
    trace = volume.run(ReactiveState(350., 2e5, {"H2": 1.}), times,
        volume_m3=.05, clock_id=clock, heat_boundaries=(heat,), maximum_time_step_s=.5,
        relative_tolerance=1e-10, absolute_tolerance=1e-14)
    process = TimeSeries(times,
        np.array([[s.pressure_pa, s.temperature_k] for s in trace.snapshots]),
        ("pressure", "temperature"), ("Pa", "K"), np.ones((len(times), 2), bool),
        clock, Origin.PREDICTED, "authored-native-finite-H2-gas-volume",
        ("pressure", "temperature"), ("absolute", ""))
    observed_predictions, owners = [], []
    for i, (channel, unit, tau, upper) in enumerate(
            (("pressure", "Pa", 2., 1e6), ("temperature", "K", 3., 1000.))):
        variable = Variable(channel, channel, unit, process.basis_ids[i])
        evidence = TransmitterEvidence(f"authored-{channel}-sensor", "finite-vessel-bulk",
            variable, "authored-not-calibrated", "native-held-input-response",
            ("authored-finite-process-case",), Origin.SYNTHETIC)
        sensor = Lh2dtTransmitter(instruments.FirstOrderTransmitter(
            instruments.TransmitterParameters(lower_range=0., upper_range=upper,
                                               time_constant_s=tau)), evidence=evidence)
        sensor_trace = sensor.run(process, channel=channel,
            initial_native_state=sensor.initialize(process.values[0, i]),
            initial_time_s=times[0], location_id="finite-vessel-bulk")
        owners.append(sensor_trace)
        observed_predictions.append(sensor_trace.prediction.values[:, 0])
    prediction = TimeSeries(times, np.column_stack(observed_predictions),
        ("pressure", "temperature"), ("Pa", "K"), np.ones((len(times), 2), bool), clock,
        Origin.PREDICTED, "authored-native-transmitter-prediction",
        ("pressure", "temperature"), ("absolute", ""))
    modes = tuple("warming" if np.cos(2*np.pi*(t-100.)/120.) >= 0 else "cooling" for t in times)
    return {"volume": volume, "trace": trace, "process": process, "prediction": prediction,
            "instruments": tuple(owners), "modes": modes, "mechanism_basis": basis}


def features():
    return (ResidualFeature("pressure_residual", "pressure", "pressure",
        Variable("pressure", "pressure", "Pa", "absolute"), "finite-vessel-bulk",
        "finite-vessel-bulk", 80., "authored-80Pa-residual-scale"),
        ResidualFeature("temperature_residual", "temperature", "temperature",
        Variable("temperature", "temperature", "K"), "finite-vessel-bulk",
        "finite-vessel-bulk", .06, "authored-0.06K-residual-scale"))


def case_batch(native, reference, role, *, seed, shifted=False, selection=None,
               valid=None, modes=None, episode=None, feature_spec=None, normal_reference=True):
    """Authored repeated scenario; independent noise seeds, no measured validation."""
    prediction = reference["prediction"]
    rng = np.random.default_rng(seed)
    e = rng.normal(size=(len(prediction.time_s), 2))
    e[:, 1] = .6*e[:, 0]+.4*e[:, 1]
    if shifted:
        e[(prediction.time_s >= 160.) & (prediction.time_s <= 200.), 0] += 7.
    values = prediction.values+e*np.array([80., .06])
    valid = np.ones(values.shape, bool) if valid is None else np.asarray(valid, bool)
    observed = replace(prediction, values=values, valid=valid, origin=Origin.SYNTHETIC,
                       source_id=f"authored-independent-noise-realization:{seed}")
    modes = tuple(reference["modes"] if modes is None else modes)
    groups = (episode or f"authored-{role}-run-{seed}",)*len(values)
    if selection is not None:
        indices = np.arange(len(values))[selection]
        observed = replace(observed, time_s=observed.time_s[indices],
            values=observed.values[indices], valid=observed.valid[indices])
        prediction = replace(prediction, time_s=prediction.time_s[indices],
            values=prediction.values[indices], valid=prediction.valid[indices])
        modes = tuple(modes[i] for i in indices)
        groups = tuple(groups[i] for i in indices)
    context = ResidualContext(f"authored-{role}-partition-{seed}", role,
        "authored-repeated-finite-H2-process-and-residual-scope", "known-heater-sign-observed-mode",
        "native-constant-volume-H2-and-transmitter-reference",
        "native-held-input-transmitter-2sP-3sT", "authored-normal-reference" if normal_reference else "")
    return residual_batch(native, observed, prediction, features() if feature_spec is None else feature_spec,
        context=context, episodes=groups, modes=modes, prediction_owner=reference)


def campaign(native, reference):
    fit = case_batch(native, reference, "fitting", seed=101)
    calibration = case_batch(native, reference, "calibration", seed=202)
    owner = NativeResidualMonitor(native).fit(fit).calibrate(calibration)
    return owner, fit, calibration


def main():
    start, before = time.perf_counter(), fingerprints()
    native = native_provider()
    reference = physical_reference()
    owner, fit, calibration = campaign(native, reference)
    normal_data = case_batch(native, reference, "evaluation", seed=303)
    normal = owner.evaluate(normal_data)
    shifted_data = case_batch(native, reference, "evaluation", seed=404, shifted=True)
    shifted = owner.evaluate(shifted_data)
    prefix = owner.evaluate(case_batch(native, reference, "evaluation", seed=404,
                                      shifted=True, selection=slice(0, 85)))
    valid = np.ones((len(normal.time_s), 2), bool)
    valid[50, 0] = False
    missing = owner.evaluate(case_batch(native, reference, "evaluation", seed=505, valid=valid))
    unseen = owner.evaluate(case_batch(native, reference, "evaluation", seed=606,
                                      modes=("unqualified-mode",)*len(normal.time_s)))
    triggered = (shifted.time_s >= 164.) & (shifted.time_s <= 198.) & shifted.valid
    actual = reference["trace"]
    native_models = owner.native_model.monitors
    parameters_before = owner._parameter_hash()
    failure = None
    try:
        owner.evaluate(fit)
    except MonitoringNativeError as error:
        failure = error
    gates = {
        "actual finite native volume and wall retained": actual.native.network is not None
            and len(actual.native.walls) == 1,
        "independent finite mass and U closure": float(np.max(np.abs(actual.mass_residual_kg))) < 1e-11
            and float(np.max(np.abs(actual.energy_residual_j))) < 1e-5,
        "finite physical pressure and temperature change": np.ptp(reference["process"].values[:, 0]) > 1000.
            and np.ptp(reference["process"].values[:, 1]) > 1.,
        "actual native instruments and readings retained": all(s.native_readings and s.native_states
            for s in reference["instruments"]),
        "actual native mode PCA and scaler fitted": all(m.fitted and m.scaler is not None
            and type(m.detector.model).__module__ == "sklearn.decomposition._pca" for m in native_models.values()),
        "whole-group fit calibration heldout disjoint": not (fit.episodes & calibration.episodes
            or fit.episodes & shifted_data.episodes or calibration.episodes & shifted_data.episodes),
        "native residual physical scaling": np.allclose(normal_data.native_batch.values,
            (normal_data.observed.values-normal_data.predicted.values)/[80., .06]),
        "original physical observation table retained": normal_data.observations.source_id
            == normal_data.context.partition_id and normal_data.prediction_owner is reference,
        "authored normal heldout mostly quiet": float(normal.alarms[normal.valid].mean()) < .3,
        "authored pressure-offset deviation visible": bool(np.any(triggered))
            and float(shifted.alarms[triggered].mean()) > .8,
        "causal prefix scores and abstention unchanged": np.array_equal(prefix.valid, shifted.valid[:85])
            and np.allclose(prefix.scores, shifted.scores[:85], equal_nan=True),
        "missing sensor resets complete windows": not missing.valid[50:54].any(),
        "unseen modes abstain": not unseen.valid.any() and not unseen.alarms.any()
            and np.isnan(unseen.scores).all(),
        "evaluation retains frozen trained state": normal.trained_state_sha256 == shifted.trained_state_sha256
            and parameters_before == owner._parameter_hash(),
        "original failure and completed evidence retained": failure is not None
            and failure.__cause__ is not None and failure.native_model is owner.native_model
            and failure.fitting_data is fit and len(failure.completed_evaluations) == 5,
        "immutable result snapshot": not shifted.scores.flags.writeable and not shifted.valid.flags.writeable,
        "no physical fault or control claim": not shifted.fault_identification and not shifted.physical_control_actions,
        "source and native bytes unchanged": before == fingerprints()
            and NativeProcessMonitoring.from_installed().source_sha256 == native.source_sha256,
    }
    report = {"scope": "authored finite-process/native instrument/native PCA residual verification",
        "versions": dict(native.versions), "normal_valid": int(normal.valid.sum()),
        "normal_alarm_fraction": float(normal.alarms[normal.valid].mean()),
        "shifted_interval_alarm_fraction": float(shifted.alarms[triggered].mean()),
        "mode_thresholds": dict(shifted.mode_thresholds),
        "mass_residual_kg": float(np.max(np.abs(actual.mass_residual_kg))),
        "energy_residual_j": float(np.max(np.abs(actual.energy_residual_j))),
        "trained_state_sha256": shifted.trained_state_sha256,
        "fitting_residual_sha256": fit.content_sha256,
        "calibration_residual_sha256": calibration.content_sha256,
        "native_source_sha256_begin": native.source_sha256,
        "native_source_sha256_end": NativeProcessMonitoring.from_installed().source_sha256,
        "input_sha256_begin": before, "input_sha256_end": fingerprints(),
        "gates": {name: bool(value) for name, value in gates.items()},
        "elapsed_s": time.perf_counter()-start}
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    if not all(gates.values()):
        raise RuntimeError("Actual native monitoring replay gate failed")
    return report


if __name__ == "__main__":
    main()
