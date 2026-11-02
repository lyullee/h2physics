"""Replay actual standalone HyRAM blast correlation in two explicit SciPy runtimes."""

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST_PATHS = ("src/h2physics/adapters/hyram_overpressure.py", "tests/test_hyram_overpressure.py",
              "scripts/check_hyram_overpressure.py", "src/h2physics/core.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_hashes(packages):
    root = packages/"hyram"
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"ordered-native-Python": digest.hexdigest(),
            "_unconfined_overpressure.py": sha(root/"phys/_unconfined_overpressure.py"),
            "_overpressure_data.py": sha(root/"phys/_overpressure_data.py"),
            "GPL-COPYING.txt": sha(packages/"hyram-6.1.dist-info/licenses/COPYING.txt"),
            "native-METADATA": sha(packages/"hyram-6.1.dist-info/METADATA")}


def worker(packages, runtime):
    if runtime == "default":
        import scipy  # Intentionally retain the host version before locating HyRAM.
        sys.path.append(str(packages))
    else:
        sys.path.insert(0, str(packages))
        import scipy
    import numpy as np
    from hyram.phys import Bauwens_method, BST_method, TNT_method

    from h2physics.adapters.hyram_overpressure import (
        BauwensCorrelationDomain,
        DetonableHydrogenEnergy,
        HyRAMBauwensOverpressure,
        OverpressureEnvironment,
        OverpressureEvent,
    )
    from h2physics.core import Origin

    before = native_hashes(packages)
    started = time.perf_counter()
    if importlib.metadata.version("hyram") != "6.1":
        raise RuntimeError("Replay expects the separately reviewed HyRAM6.1 native target")
    expected_scipy = "1.18.1" if runtime == "default" else "1.16.3"
    if scipy.__version__ != expected_scipy:
        raise RuntimeError(f"Requested {runtime} SciPy {expected_scipy}, got {scipy.__version__}")
    domain = BauwensCorrelationDomain(1., 100., 8e4, 1.2e5, .1,
                                      "authored-numerical-envelope-not-field-qualification")
    model = HyRAMBauwensOverpressure(Bauwens_method, domain=domain,
                                    native_source_id="HyRAM6.1/GPL-3.0-only")
    event = OverpressureEvent("authored-conditional-detonation", (0., 0., 0.), "global-xyz",
                             "authored-independent-centre", 100., "authored-operation-clock")

    def energy(mass):
        return DetonableHydrogenEnergy(mass, 120e6, "authored-participating-mass-not-jet-mass",
            "authored-constant-q-not-calibrated", "specified-H2-combustion-energy-reference",
            "independent-synthetic-input", Origin.SYNTHETIC)

    rows, anchors, similarity, monotonic, native_errors = [], [], [], [], []
    for mass in (.001, .01, .08):
        for pressure in (8e4, 1e5, 1.2e5):
            ambient = OverpressureEnvironment(pressure, "authored-absolute-pressure")
            source = energy(mass)
            scaled = np.geomspace(1., 100., 81)
            length = (source.energy_j/pressure)**(1/3)
            receptors = np.c_[scaled*length, np.zeros((len(scaled), 2))]
            result = model.evaluate(source, event, ambient, receptors, frame_id=event.frame_id)
            direct = Bauwens_method.calc_scaled_overpressure_from_dist(result.scaled_distance)
            native_errors.append(float(np.max(abs(result.scaled_overpressure-direct))))
            anchors.append(abs(float(result.scaled_overpressure[0])-.4053))
            monotonic.append(bool(np.all(np.diff(result.peak_overpressure_pa) < 0)))
            rows.append({"mass_kg": mass, "Pambient_Pa": pressure, "energy_J": source.energy_j,
                "first_R_m": float(result.distance_m[0]), "first_deltaP_Pa": float(result.peak_overpressure_pa[0]),
                "last_deltaP_Pa": float(result.peak_overpressure_pa[-1])})
            similarity.append(result.scaled_overpressure)
    maximum_similarity = float(np.max(np.ptp(np.stack(similarity), axis=0)))
    ambient = OverpressureEnvironment(1e5, "authored-absolute-pressure")
    thresholds = [model.threshold_radius(1e4, energy(mass), event, ambient) for mass in (.01, .08)]
    inverse_error = max(abs(float(value.forward.peak_overpressure_pa[0])-1e4) for value in thresholds)
    coarse = model.threshold_radius(5000., energy(.01), event, ambient,
                                    scaled_radius_tolerance=1e-8, relative_radius_tolerance=1e-8)
    fine = model.threshold_radius(5000., energy(.01), event, ambient,
                                  scaled_radius_tolerance=1e-13, relative_radius_tolerance=1e-13)
    zero = model.evaluate(energy(0.), event, ambient, [(10., 0., 0.)], frame_id=event.frame_id)
    zero_native = bool(np.all(zero.native_scaled_result == 0) and zero.zero_energy_limit)
    far_exponent = float(np.log(Bauwens_method.calc_scaled_overpressure_from_dist(2e9)
        /Bauwens_method.calc_scaled_overpressure_from_dist(1e9))/np.log(2))
    negative_cases = []
    for name, attempt in (
        ("near-origin Rstar0.001", lambda: model.evaluate(energy(.01), event, ambient,
                   [(.001*(energy(.01).energy_j/1e5)**(1/3), 0., 0.)], frame_id=event.frame_id)),
        ("outside ambient P", lambda: model.evaluate(energy(.01), event,
                   OverpressureEnvironment(3e5, "outside"), [(10., 0., 0.)], frame_id=event.frame_id)),
        ("unbracketed target", lambda: model.threshold_radius(1e8, energy(.01), event, ambient)),
        ("wrong frame", lambda: model.evaluate(energy(.01), event, ambient,
                                             [(10., 0., 0.)], frame_id="unknown")),
    ):
        try:
            attempt()
        except ValueError as error:
            negative_cases.append((name, str(error)))
        else:
            raise AssertionError(f"Expected failure: {name}")
    after = native_hashes(packages)
    gates = {
        "actual standalone native class/function retained; no Jet instantiated":
            zero.native_class is Bauwens_method and zero.native_function is
            Bauwens_method.calc_scaled_overpressure_from_dist,
        "729 participating-mass/ambient/distance points equal native raw correlation": max(native_errors) == 0,
        "independent published unit-scaled-distance anchor error <2e-15": max(anchors) < 2e-15,
        "all nine positive-energy pressure profiles strictly decrease": all(monotonic),
        "mass/ambient dimensional similarity defect <2e-15": maximum_similarity < 2e-15,
        "eightfold participating energy doubles threshold radius <1e-12 m":
            abs(thresholds[1].radius_m-2*thresholds[0].radius_m) < 1e-12,
        "native inverse forward-pressure error <1e-7 Pa": inverse_error < 1e-7,
        "root-tolerance refinement radius difference <1e-7 m": abs(coarse.radius_m-fine.radius_m) < 1e-7,
        "native infinite-scaled-distance zero-energy limit returns zero pressure": zero_native,
        "independent mathematical far-field exponent tends to -4/3 <1e-6": abs(far_exponent+4/3) < 1e-6,
        "domain/frame/unbracketed cases reject without clamping": len(negative_cases) == 4,
        "all native source/license/metadata begin/end fingerprints unchanged": before == after,
    }
    return {"runtime": runtime, "scipy": scipy.__version__, "numpy": np.__version__,
        "hyram": importlib.metadata.version("hyram"), "elapsed_s": time.perf_counter()-started,
        "rows": rows, "gates": gates, "native_before": before, "native_after": after,
        "maximum_anchor_error": max(anchors), "maximum_similarity_error": maximum_similarity,
        "inverse_pressure_error_pa": inverse_error,
        "threshold_10kPa_radius_m": [value.radius_m for value in thresholds],
        "root_refinement_m": abs(coarse.radius_m-fine.radius_m), "far_exponent": far_exponent,
        "negative_cases": negative_cases,
        "constructors": {cls.__name__: str(inspect.signature(cls))
                         for cls in (Bauwens_method, TNT_method, BST_method)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-packages", type=Path, default=ROOT/"artifacts/native_hyram_packages")
    parser.add_argument("--worker", choices=("default", "compatible"))
    args = parser.parse_args()
    packages = args.native_packages.resolve()
    if args.worker:
        print(json.dumps(worker(packages, args.worker), allow_nan=False))
        return
    host_before = {name: sha(ROOT/name) for name in HOST_PATHS}
    records = []
    for runtime in ("compatible", "default"):
        result = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
            "--native-packages", str(packages), "--worker", runtime], capture_output=True,
            text=True, encoding="utf-8", check=True)
        if result.stderr:
            sys.stderr.write(result.stderr)
        records.append(json.loads(result.stdout))
        print(f"actual HyRAM6.1 standalone correlation / SciPy{records[-1]['scipy']} passed", flush=True)
    host_after = {name: sha(ROOT/name) for name in HOST_PATHS}
    guards = host_before == host_after
    cross_error = max(abs(left["first_deltaP_Pa"]-right["first_deltaP_Pa"])
                      for left, right in zip(records[0]["rows"], records[1]["rows"], strict=True))
    lines = ["# Native conditional unconfined peak overpressure", "",
        "Authored mathematical/native interface verification only. Participating hydrogen mass, "
        "combustion heat, ambient absolute pressure and blast centre are explicit supplied evidence. "
        "No release/flammable/detonable cloud field, ignition or detonation probability is inferred. "
        "The existing rejected HyRAM Gaussian-entry source remains rejected; this API never accepts a Jet.", "",
        "The actual public Bauwens_method.calc_scaled_overpressure_from_dist static function owns all "
        "correlation coefficients/values. No fabricated Jet, cloud, native instance or copied table is used. "
        "Host dimensional definitions are E=m_H2*q, Rstar=R*(Pambient/E)^(1/3), deltaP=Pambient*Pstar. "
        "There is no inferred efficiency, TNT substitution or ground/reflection multiplier.", "",
        "Original synthetic envelope: participating H2 mass0.001/0.01/0.08kg, q120MJ/kg; "
        "ambient80/100/120kPa absolute; 81 scaled distances1–100 per pair; physical standoff>=0.1m. "
        "The coefficient, participation and envelope inputs are not experimental/calibrated values. "
        "Event snapshot100s uses its declared operation clock; no arrival-time or waveform is solved.", "",
        "## Actual native runtime checks", "",
        "| SciPy | NumPy | HyRAM | Local calculation s | Gates passed |", "|---|---|---|---:|---:|"]
    for record in records:
        lines.append(f"| {record['scipy']} | {record['numpy']} | {record['hyram']} | "
                     f"{record['elapsed_s']:.6f} | {sum(record['gates'].values())}/{len(record['gates'])} |")
    record = records[0]
    lines += ["", "No native ODE is executed in this standalone route. Passing both runtimes does not "
        "resolve the separate full-Jet SciPy callback/source failures.", "",
        "| Participating H2 kg | Ambient absolute Pa | Energy J | R at Rstar1 m | deltaP at Rstar1 Pa | deltaP at Rstar100 Pa |",
        "|---:|---:|---:|---:|---:|---:|"]
    for row in record["rows"]:
        lines.append("| "+" | ".join(f"{value:.12g}" for value in row.values())+" |")
    lines += ["", f"Maximum published anchor error: {record['maximum_anchor_error']:.12g}; "
        f"mass/ambient similarity defect: {record['maximum_similarity_error']:.12g}.", "",
        f"10kPa threshold radii for0.01/0.08kg: {record['threshold_10kPa_radius_m']}m. "
        f"Maximum native forward pressure defect: {record['inverse_pressure_error_pa']:.12g}Pa; "
        f"root-refinement radius difference: {record['root_refinement_m']:.12g}m.", "",
        f"Native mathematical far-field exponent at Rstar1e9/2e9: {record['far_exponent']:.12g}; "
        "this is outside the application envelope and is a mathematical limit only. "
        "Zero participating mass calls the actual native static function at Rstar=infinity and returns zero. "
        "That explicit zero-energy limit does not create a finite cloud or an impulse estimate.", "",
        f"Cross-runtime anchor pressure difference: {cross_error:.12g}Pa.", "",
        "| Gate | Compatible runtime | Host runtime |", "|---|---|---|"]
    for name in record["gates"]:
        lines.append(f"| {name} | {record['gates'][name]} | {records[1]['gates'][name]} |")
    lines += ["", "## Retained domain failures", "", "| Attempt | Actual error |", "|---|---|"]
    lines.extend(f"| {name} | {error} |" for name, error in record["negative_cases"])
    lines += ["", "## Full native constructors and receiving boundary", ""]
    lines.extend(f"- `{name}{signature}`" for name, signature in record["constructors"].items())
    lines += ["", "All three full constructors consume a real Jet: TNT/BST call its flammable-mass "
        "integration and determine an origin from its concentration field unless explicitly overridden; "
        "Bauwens also discretizes the real jet, evaluates cell-size/gradient criteria and integrates "
        "participating fuel. The inspected high-level compute_overpressure likewise constructs a Jet. "
        "They cannot accept the currently rejected source as a qualified cloud. Only the actual "
        "standalone Bauwens pressure correlation is executed here. TNT's separate static equivalent-mass "
        "function exists, but no TNT/BST pressure-table route is advertised by this adapter.", "",
        "Receiving work: native explicit participating-energy/mass constructors with provenance; "
        "separate immutable field-inventory/source audits; explicit pressure/geometry/domain and "
        "point-source/reflection conventions. Full source-to-cloud coupling remains blocked by the "
        "recorded Gaussian mass gap. No receiving project was edited or contacted.", "",
        "No impulse, positive-phase duration, waveform, reflection, enclosure/obstacle amplification, "
        "DDT/initiation or annual frequency is returned. The pressure rise is relative to ambient; "
        "ambient-plus-rise is labeled separately. Threshold radius is a conditional inversion, not "
        "a qualified safe/separation distance. No apparatus or field validation is inferred.", "",
        "Primary sources: [Sandia HyRAM technical reference](https://www.osti.gov/servlets/purl/2563814), "
        "[Bauwens and Dorofeev ICHS2019, pressure/energy/distance definitions onp10]"
        "(https://hysafe.info/uploads/papers/2019/279.pdf), "
        "[native public source](https://github.com/sandialabs/hyram). "
        "HyRAM6.1 is separately installed GPL-3.0-only; no native code, coefficient tables or external "
        "measurements are bundled. Mathematical anchors and original scaling tests are not measured validation.", "",
        "## Begin/end fingerprints", "", "| Native bytes | Begin SHA256 | End SHA256 |", "|---|---|---|"]
    for name, value in record["native_before"].items():
        if any(item["native_before"][name] != value or item["native_after"][name] != value for item in records):
            guards = False
        lines.append(f"| {name} | {value} | {record['native_after'][name]} |")
    lines += ["", "| Host source/test/replay | Begin SHA256 | End SHA256 |", "|---|---|---|"]
    lines.extend(f"| {name} | {value} | {host_after[name]} |" for name, value in host_before.items())
    lines += ["", f"Host/native source-byte guards passed: {guards}. Cross-runtime gate: {cross_error < 1e-9}."]
    (ROOT/"research/native_overpressure.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    if not guards or cross_error >= 1e-9 or not all(all(item["gates"].values()) for item in records):
        raise SystemExit("A native overpressure gate failed; report retained")
    print("wrote research/native_overpressure.md", flush=True)


if __name__ == "__main__":
    main()
