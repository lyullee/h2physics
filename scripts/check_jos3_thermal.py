"""Actual native thermal campaign and energy/refinement/ownership acceptance."""

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

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

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("src/h2physics/adapters/jos3_thermal.py", "tests/test_jos3_thermal.py",
           "scripts/check_jos3_thermal.py", "docs/JOS3_THERMAL.md", "research/thermal_dependency.toml")


def fingerprints():
    result = {}
    for name in SOURCES:
        data = (ROOT/name).read_bytes()
        if b"\r" in data:
            raise ValueError("Executed inputs must use LF")
        result[name] = hashlib.sha256(data).hexdigest()
    return result


def environment(temperature):
    return OrdinaryAirEnvironment(temperature, temperature, .3, 40., .7, .45,
                                  1.3, "standing", "authored-uniform-ordinary-air")


def context():
    return ThermalRunEvidence("authored-absolute-clock", "authored-ENU", "thermal-reference",
        (1., 0., 1.5), "authored-air-environment", "authored-subject",
        "native-neutral-warmup-final-state", "authored-nonfreezing-domain",
        "ordinary-air", 101325., Origin.SYNTHETIC)


def campaign(native, source, step, intervals):
    domain = ThermalDomain(273.15, 313.15, 283.15, 315.15, step, 1e-6)
    return JOS3ThermalResponse(native, domain).run(source, intervals, evidence=context())


def replay(native):
    start = time.perf_counter()
    before = fingerprints()
    subject = ThermalSubject(1.74, 72., 18., 35, "male", 2.59, "harris-benedict", "dubois")
    source = native.prepare_neutral(subject)
    source_hash = _digest(vars(source))
    intervals = (ThermalInterval(100., 400., environment(283.15)),
                 ThermalInterval(400., 700., environment(298.15)))
    runs = [campaign(native, source, step, intervals) for step in (10., 5., 2.5)]
    baseline = runs[0]
    direct = copy.deepcopy(source)
    for item in intervals:
        e = item.environment
        direct.tdb, direct.tr = e.air_temperature_k-273.15, e.radiant_temperature_k-273.15
        direct.v, direct.rh, direct.clo = e.air_speed_m_s, e.relative_humidity_percent, e.clothing_clo
        direct._iclo, direct.par, direct.posture = e.clothing_vapor_efficiency.copy(), e.activity_ratio, e.posture
        direct.simulate(30, dtime=10.)
    temperatures = [r.steps[-1].body_temperature_k for r in runs]
    refinement = [float(np.max(abs(a-b))) for a, b in zip(temperatures[:-1], temperatures[1:], strict=True)]
    defects = [max(abs(s.energy_defect_j) for s in r.steps) for r in runs]
    energy_margin = [min(s.output_rounding_budget_j+1e-6-abs(s.energy_defect_j) for s in r.steps) for r in runs]
    storage = float(np.dot(baseline.capacity_j_k,
                          baseline.steps[-1].body_temperature_k-baseline.initial_body_temperature_k))
    sum_storage = sum(s.stored_energy_change_j for s in baseline.steps)
    rejected = []
    for kind in ("hidden-shivering-rate-memory", "custom-heat-source", "body-domain"):
        value = copy.deepcopy(source)
        domain = ThermalDomain(273.15, 313.15, 283.15, 315.15, 10., 1e-6)
        if kind == "hidden-shivering-rate-memory":
            value.options["limit_dshiv/dt"] = True
        elif kind == "custom-heat-source":
            value.ex_q[:] = 1.
        else:
            domain = ThermalDomain(273.15, 313.15,
                float(np.min(source.t_body+273.15))-.02, 315.15, 10., 1e-6)
        try:
            JOS3ThermalResponse(native, domain).run(value, intervals, evidence=context())
        except ThermalResponseError as error:
            rejected.append((kind, error))
    after = fingerprints()
    gates = {
        "actual native copied model and original owner retained":
            baseline.source_model is source and type(baseline.native_model) is native.model_class,
        "original prepared state and neutral output unchanged": _digest(vars(source)) == source_hash,
        "all original returned native step outputs retained":
            all(s.native_output is raw for s, raw in zip(baseline.steps, baseline.native_outputs, strict=True)),
        "explicit 85 capacities and17 local skin/core states":
            baseline.capacity_j_k.shape == (85,) and baseline.steps[-1].skin_temperature_k.shape == (17,),
        "exact direct unmodified native campaign": np.array_equal(baseline.native_model.t_body, direct.t_body),
        "exact independently declared command edge":
            any(s.end_s == 400. for s in baseline.steps) and any(s.start_s == 400. for s in baseline.steps),
        "native clock is elapsed and absolute offset retained":
            baseline.native_model._time.total_seconds() == 600. and baseline.steps[-1].end_s == 700.,
        "all storage and implicit heat audits within output precision": min(energy_margin) > 0,
        "total native stored energy equals sum of step changes": abs(storage-sum_storage) < 1e-7,
        "reported old-state sensible heat differs from implicit boundary":
            abs(baseline.steps[0].implicit_sensible_out_w-baseline.steps[0].reported_previous_state_sensible_out_w) > .5,
        "native time refinement contracts": refinement[1] < refinement[0] and refinement[1] < .03,
        "all three rejected native boundaries retain cause and actual model":
            len(rejected) == 3 and all(e.__cause__ is not None and e.native_model is not None for _, e in rejected),
        "body-domain rejection retains native completed output":
            rejected[-1][1].native_model._time.total_seconds() > 0,
        "no injury probability or validated cryogenic chain inferred":
            baseline.injury_probability is None and not baseline.full_cryogenic_chain_validated,
        "executed inputs unchanged": before == after,
    }
    if not all(gates.values()):
        raise RuntimeError(f"Native thermal replay failed: {[k for k,v in gates.items() if not v]}")
    return {"elapsed_s": time.perf_counter()-start, "gates": gates, "refinement_max_node_k": refinement,
        "maximum_step_energy_defects_j": defects, "minimum_energy_margin_j": energy_margin,
        "initial_min_body_k": float(np.min(baseline.initial_body_temperature_k)),
        "final_mean_skin_k": float(baseline.native_model.t_skin_mean+273.15),
        "native_source_sha256": native.source_sha256, "source_begin": before, "source_end": after,
        "negative_cases": [{"kind": k, "cause": type(e.__cause__).__name__, "message": str(e),
                            "completed_steps": len(e.completed_steps),
                            "native_elapsed_s": e.native_model._time.total_seconds()} for k, e in rejected]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-packages", type=Path, default=Path("artifacts/native_thermal_packages"))
    parser.add_argument("--report", type=Path, default=Path("research/jos3_thermal.md"))
    parser.add_argument("--details", type=Path,
                        default=Path("artifacts/thermal_comfort_feasibility/final_replay.json"))
    args = parser.parse_args()
    sys.path.append(str(args.native_packages.resolve()))
    native = NativeJOS3.from_installed()
    result = replay(native)
    rows = ["# Native ordinary-air multisegment thermal response", "",
        f"Actual pythermalcomfort4.7.0/NumPy{np.__version__}; enabled native JIT, {result['elapsed_s']:.8f}s.", "",
        "The authored subject and environment are numerical verification inputs, not a clinical cohort. "
        "An actual prepared native JOS3 object is copied without changing its definition/state. "
        "Native neutral-setpoint initialization retains only its final native output; its hidden warmup trajectory is unavailable. "
        "Ordinary-air10C for300s followed by25C for300s uses supplied clothing/activity and an explicit101325Pa model reference. "
        "No H2-rich convection, cryogenic contact/boiling, freezing, respiratory injury, hypoxia or physiological damage law is introduced.", "",
        "Native JOS3 owns85 capacities/nodes,17 local body segments, physiology and implicit stepping. "
        "Original native models, rounded native outputs, unrounded native body temperatures, absolute/elapsed clocks and failure-prefix objects survive. "
        "The source prepared model is unchanged. Historical snapshots are separate from mutable returned native objects.", "",
        "The original native displayed sensible heat uses the previous skin temperature. Its integrator uses the implicit updated skin temperature "
        "with the beginning-state native dry resistance/operative temperature. The audit queries those native properties before each step, "
        "then independently compares native capacity times temperature change with the actual implicit boundary. "
        "The native output is never rewritten to hide that difference. Native total thermogenesis/respiration and17latent powers are rounded0.01W; "
        "their worst-case summed precision is0.095W times step duration, plus the declared1e-6J numerical budget. "
        "This is a rounding bound, not an adjustable physical heat correction.", "",
        f"10/5/2.5s final-node refinement differencesK: {result['refinement_max_node_k']}; "
        f"maximum step storage/boundary defectsJ: {result['maximum_step_energy_defects_j']}.", "",
        "The native previous-shivering global limiter is not isolated across models. It is explicitly rejected when enabled; "
        "no global state or native equations are patched. The native unused shivering option cannot mean disabled physiology. "
        "Custom native hc/hr or ex_q require another audited boundary and are rejected at this level. "
        "Original NUMBA_DISABLE_JIT=1 import failed with a native compilation/dispatcher AttributeError; enabled native JIT succeeds. "
        "The factory rejects the disabled profile without a substitute engine. This record establishes numerical/API limits only; "
        "independent human validation and source/environment applicability remain open.", "",
        "| Gate | Pass |", "|---|---|"]
    rows += [f"| {name} | {value} |" for name, value in result["gates"].items()]
    rows += ["", "| Rejected original case | Cause | Completed host-admitted steps | Native elapsed s |",
             "|---|---|---:|---:|"]
    rows += [f"| {e['kind']} | {e['cause']}: {e['message']} | {e['completed_steps']} | {e['native_elapsed_s']} |"
             for e in result["negative_cases"]]
    rows += ["", f"Native94 Python-file aggregate SHA256: `{native.source_sha256}`.", "",
        "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|"]
    rows += [f"| {name} | {result['source_begin'][name]} | {result['source_end'][name]} |" for name in SOURCES]
    rows += ["", "Primary sources: [native4.7.0 metadata](https://pypi.org/project/pythermalcomfort/4.7.0/), "
        "[actual native documentation](https://pythermalcomfort.readthedocs.io/en/latest/documentation/models.html), "
        "[native source/license](https://github.com/pythermalcomfort/pythermalcomfort), "
        "[original model bibliographic record](https://doi.org/10.1016/j.enbuild.2020.110575). "
        "The publisher full-text endpoint returned403; no full original validation dataset was inspected or redistributed. "
        "MIT/native dependency notices and exact artifact hashes are in thermal_dependency.toml. No native source/coefficient table is bundled."]
    args.report.write_text("\n".join(rows)+"\n", encoding="utf-8", newline="\n")
    args.details.write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(f"Actual native thermal campaign: {len(result['gates'])}/{len(result['gates'])} gates in {result['elapsed_s']:.6g}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
