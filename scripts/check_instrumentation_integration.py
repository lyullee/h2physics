"""Actual native instrument verification without assumed measured calibration."""

import hashlib
import importlib
import math
import sys
import time
import tomllib
from pathlib import Path

import numpy as np

from h2physics.adapters.lh2dt_instrumentation import Lh2dtTransmitter, TransmitterEvidence
from h2physics.core import Origin, TimeSeries
from h2physics.data.pressure_peaking import load_pressure_mat
from h2physics.observations import Variable

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "artifacts/native_packages"
NATIVE_SHA = "5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61"
HOST_FILES = ("src/h2physics/adapters/lh2dt_instrumentation.py",
              "tests/test_lh2dt_instrumentation.py", "scripts/check_instrumentation_integration.py")


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sha():
    digest = hashlib.sha256()
    for path in sorted((TARGET / "lh2dt").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    start = time.perf_counter()
    fingerprints = {name: file_sha(ROOT / name) for name in HOST_FILES}
    if native_sha() != NATIVE_SHA:
        raise ValueError("Install/review the exact native LH2DT snapshot")
    sys.path.insert(0, str(TARGET))
    native = importlib.import_module("lh2dt.instrumentation")
    if Path(native.__file__).resolve() != (TARGET / "lh2dt/instrumentation.py").resolve():
        raise ValueError("Native instrument import differs from selected source")
    variable = Variable("pressure", "pressure", "Pa", "absolute")
    evidence = TransmitterEvidence("authored-P1", "tank-headspace", variable,
        "authored-calibration", "authored-response", ("independent-synthetic-check",), Origin.SYNTHETIC)

    def sensor(**changes):
        parameters = dict(lower_range=0., upper_range=1e6, time_constant_s=2.)
        parameters.update(changes)
        return Lh2dtTransmitter(native.FirstOrderTransmitter(native.TransmitterParameters(**parameters)),
                               evidence=evidence)

    def trajectory(times, pressure):
        values = np.full((len(times), 1), pressure)
        return TimeSeries(np.asarray(times), values, ("pressure",), ("Pa",),
            np.ones_like(values, dtype=bool), "authored-clock", Origin.PREDICTED,
            "authored-held-process", ("pressure",), ("absolute",))

    def execute(adapter, series, initial=1e5):
        return adapter.run(series, channel="pressure", initial_native_state=adapter.initialize(initial),
            initial_time_s=series.time_s[0], location_id="tank-headspace")

    errors, refinement = [], []
    for step in (1., .1, .01):
        times = np.linspace(7., 12., round(5/step)+1)
        trace = execute(sensor(), trajectory(times, 5e5))
        analytic = 5e5-4e5*np.exp(-(times-7)/2)
        errors.append(float(np.max(np.abs(trace.prediction.values[:, 0]-analytic))))
        refinement.append(float(trace.prediction.values[-1, 0]))
    fine = trace
    continuous_crossing = 7+2*math.log(4)
    sampled_crossing = float(fine.prediction.time_s[
        np.flatnonzero(fine.prediction.values[:, 0] >= 4e5)[0]])
    times = np.linspace(7., 12., 501)
    bounded = execute(sensor(upper_range=4e5, scale_factor=1.01, bias=-700., resolution=125.,
        accuracy_fraction_of_span=.001), trajectory(times, 7e5))
    values = bounded.prediction.values
    quantized = np.abs(values[:, 0]-np.clip(values[:, 2], 0., 4e5))
    quantization_error = float(np.max(quantized))
    gates = {
        "exact native constant-hold step error <1e-7 Pa": max(errors) < 1e-7,
        "native endpoint refinement difference <1e-7 Pa": np.ptp(refinement) < 1e-7,
        "sampled threshold follows analytic lag within one declared sample":
            0 <= sampled_crossing-continuous_crossing <= .01000001,
        "native quantization error <=62.5 Pa after explicit range saturation": quantization_error <= 62.5,
        "native bounds remain span-based, not standard deviations":
            bool(np.all(values[:, 3] == 62.5) and np.all(values[:, 4] == 400.)),
        "native saturation diagnostic and actual object types retained":
            bool(np.any(values[:, 5] == 1) and isinstance(bounded.final_native_state, native.TransmitterState)),
    }
    receipt = tomllib.loads((ROOT / "research/data/pressure-unignited.toml").read_text("utf-8"))
    record = next(item for item in receipt["files"] if item["name"] == "HTE242USN_00003_READ190621.mat")
    path = ROOT / "data/raw" / record["relative_path"]
    run = load_pressure_mat(path, source_id=f"{receipt['doi']}:{record['name']}",
        experiment_id="USN-00003", expected_sha256=record["sha256"])
    observed = next(run.sigma.iter_blocks(block_rows=4, last_row=4)).series
    try:
        sensor().run(observed, channel="meter_reported_pressure",
            initial_native_state=sensor().initialize(1e5), initial_time_s=observed.time_s[0],
            location_id="tank-headspace")
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Unresolved measured meter pressure silently became headspace absolute pressure")
    gates["actual measured pressure is rejected without a qualified basis/location map"] = (
        "quantity, unit or measurement/reference basis" in rejection)
    gates["host/native source bytes unchanged during replay"] = (
        native_sha() == NATIVE_SHA and all(file_sha(ROOT / path) == sha for path, sha in fingerprints.items()))
    lines = ["# Native instrument and observation verification", "",
        "Native LH2DT0.1.2, pinned revision b2f276333c1b1793c39f25763703d196d36742ec, MIT. "
        f"Ordered native Python tree SHA-256: `{NATIVE_SHA}`.", "",
        "All instrument parameters are authored verification values, not device calibration. "
        "LH2DT owns the exact held-input lag and indication effects. The host preserves "
        "units, pressure/reference/location and clocks, native states/readings, and parameter evidence. "
        "There is no new response integrator, stochastic noise, safety credit or historian clock repair.", "",
        "Input is held on the left of each interval; output at each endpoint is a left limit. "
        "The first reading uses an explicit initial native state. The last process value does "
        "not drive an invented later interval. Native states can continue a subsequent window.", "",
        "| Check | Value |", "|---|---|",
        f"| Step analytic errors at1/.1/.01s sampling | {errors} Pa |",
        f"| Endpoint spread over three samplings | {np.ptp(refinement):.12g} Pa |",
        f"| Continuous / sampled indicated400kPa crossing | {continuous_crossing:.12g} / {sampled_crossing:.12g} s |",
        f"| Maximum quantization error after explicit saturation | {quantization_error:.12g} Pa |", "",
        "Synthetic step:100 to500kPa at absolute7s, tau2s, up to12s. Separate bounded run: "
        "100 to700kPa, range0–400kPa, scale1.01, bias−700Pa, resolution125Pa, accuracy fraction "
        "of span .001. The resulting bounds are62.5Pa quantization and400Pa stated accuracy. "
        "These are deterministic reported bounds, not Gaussian sigma, measured residuals or "
        "confidence intervals. No probability distribution or coverage factor is inferred.", "",
        "## Actual data boundary", "",
        "Lach and Gaathaug's [USN data v1](https://doi.org/10.23642/usn.17932439.v1), "
        "CC BY4.0, is loaded only from locally acquired hash-verified bytes. The selected "
        "meter pressure has unresolved absolute/gauge basis and a different physical location. "
        f"Automatic use as absolute headspace pressure is rejected: {rejection}. "
        "No measured sensor time constant, uncertainty, process truth or calibration fit is "
        "claimed. This gate does not infer anything about other experiments or channels.", "",
        "| Gate | Pass |", "|---|---|", *(f"| {name} | {passed} |" for name, passed in gates.items()), "",
        "Primary references: [pinned native instrument API]"
        "(https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/instrumentation.py), "
        "[NIST sensor time-response study](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=909856), "
        "[BIPM measurement uncertainty definition](https://jcgm.bipm.org/vim/en/2.26.html). "
        "The thermal study motivates careful time-constant meaning, not a universal pressure "
        "transmitter calibration. No source parameter table or implementation is bundled.", "",
        "## Executed host fingerprints", ""]
    lines += [f"- `{path}`: `{sha}`" for path, sha in fingerprints.items()]
    lines += ["", f"Local replay wall time: {time.perf_counter()-start:.6g}s."]
    (ROOT / "research/native_instrumentation.md").write_text("\n".join(lines)+"\n",
                                                           encoding="utf-8", newline="\n")
    print("native instrument gates", gates, flush=True)
    if not all(gates.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
