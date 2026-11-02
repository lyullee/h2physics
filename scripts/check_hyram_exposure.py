"""Replay actual native HyRAM exposure laws with original conditional inputs."""

import argparse
import hashlib
import importlib.metadata
import math
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hyram-packages", type=Path, required=True)
    parser.add_argument("--use-main-scipy", action="store_true")
    parser.add_argument("--no-report", action="store_true", help="Keep the primary environment's saved report unchanged")
    args = parser.parse_args()
    if args.use_main_scipy:
        import scipy
    sys.path.insert(0, str(args.hyram_packages.resolve()))
    import hyram
    import numpy as np
    import scipy
    import scipy.integrate._quadpack
    import scipy.special._ufuncs
    import scipy.stats._continuous_distns
    import scipy.stats._distn_infrastructure

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

    root = Path(__file__).resolve().parents[1]
    host_names = ("src/h2physics/adapters/hyram_exposure.py", "tests/test_hyram_exposure.py",
        "scripts/check_hyram_exposure.py", "docs/NATIVE_EXPOSURE.md", "src/h2physics/core.py")
    before = {name: sha(root/name) for name in host_names}
    metadata = importlib.metadata.distribution("hyram")
    package = Path(hyram.__file__).resolve().parent
    native_paths = {"HyRAM probits": package/"qra/probits.py", "HyRAM utility": package/"utilities/misc_utils.py",
        "HyRAM GPL notice": Path(metadata.locate_file("hyram-6.1.dist-info/licenses/COPYING.txt")),
        "HyRAM metadata": Path(metadata.locate_file("hyram-6.1.dist-info/METADATA")),
        "SciPy distributions": Path(scipy.stats._continuous_distns.__file__),
        "SciPy distribution infrastructure": Path(scipy.stats._distn_infrastructure.__file__),
        "SciPy special compiled functions": Path(scipy.special._ufuncs.__file__),
        "SciPy quadrature compiled engine": Path(scipy.integrate._quadpack.__file__)}
    native_before = {name: sha(path) for name, path in native_paths.items()}
    engine = HyRAMExposure()
    receptor = ExposureReceptor("authored-receptor", "global-xyz", (4., -1., 1.5), "supplied-local-receptor-plane")
    def selection(name):
        return NativeHarmSelection(name, 5., "explicit-native-choice", "authored-not-calibrated-applicability", Origin.SYNTHETIC)
    def history(values=(40000.,), times=(100., 110.), *, quantity="incident_radiant_flux", interpolation="left_hold", valid=None):
        return ExposureHistory(receptor, times, values, quantity, "Pa" if quantity == "gauge_overpressure" else "W/m2",
            interpolation, "authored-absolute-clock", "conditional-supplied-field", "explicit-local-input-basis", Origin.SYNTHETIC, valid)
    started = perf_counter()
    thermal = {name: engine.thermal_response(history(), selection(name), additivity_evidence_id="additive-dose-no-recovery")
               for name in engine.thermal_models}
    native_constant_error = max(abs(result.probability-engine.native_module.compute_thermal_fatality_prob(name, 40000., 10., mean=5.))
                                for name, result in thermal.items())
    cdf_error = max(abs(result.probability-.5*(1+math.erf((result.native_probit-5.)/math.sqrt(2)))) for result in thermal.values())
    pulse = engine.thermal_response(history((40000., 0.), (100., 105., 110.)), selection("eise"), additivity_evidence_id="additive-no-recovery")
    smooth = engine.thermal_response(history((20000.,)), selection("eise"), additivity_evidence_id="additive-no-recovery")
    split = engine.thermal_dose(history(np.full(32, 40000.), np.linspace(100., 110., 33)), additivity_evidence_id="exact-hold-splitting")
    split_error = abs(split.thermal_dose/thermal["eise"].thermal_dose-1)
    linear = engine.thermal_dose(history((12000., 36000.), (100., 106.), interpolation="linear"), additivity_evidence_id="explicit-linear-dose-law")
    refined = engine.thermal_dose(history(np.linspace(12000., 36000., 17), np.linspace(100., 106., 17), interpolation="linear"),
                                  additivity_evidence_id="explicit-linear-dose-law")
    analytic = 6.*3/7*(36000.**(7/3)-12000.**(7/3))/(36000.-12000.)
    linear_error, refinement = abs(linear.thermal_dose/analytic-1), abs(refined.thermal_dose/linear.thermal_dose-1)
    absorbed = engine.thermal_dose(history((20000.,), quantity="absorbed_radiant_flux"), additivity_evidence_id="absorbed-diagnostic-only")
    waveform = history((0., 100000., 0., -20000.), (100., 100.05, 100.1, 100.15), quantity="gauge_overpressure", interpolation="linear")
    triangle = engine.pressure_response(waveform, selection("head"), positive_phase_evidence_id="explicit-positive-gauge-phase")
    summary = PressurePeak(receptor, 100000., 5000., "authored-absolute-clock", (100., 100.15),
                           "conditional-supplied-summary", "explicit-local-gauge-basis", Origin.SYNTHETIC)
    pressure = {name: engine.pressure_response(summary, selection(name), positive_phase_evidence_id="explicit-summary-assumption")
                for name in engine.pressure_models}
    pressure_error = max(abs(result.probability-engine.native_module.compute_overpressure_fatality_prob(name, 100000., 5000., mean=5.))
                         for name, result in pressure.items())
    peak_only_zero = engine.pressure_response(replace(summary, positive_impulse_pa_s=0.), selection("leis"),
                                              positive_phase_evidence_id="peak-only-model-does-not-use-impulse")
    native_unused_zero = engine.native_module.compute_overpressure_fatality_prob("leis", 100000., 0., mean=5.)
    zero = engine.thermal_response(history((0.,)), selection("eise"), additivity_evidence_id="zero-exposure")
    failures = {}
    probes = (
        ("masked supplied sample", lambda: engine.thermal_response(history((np.nan,), valid=[False]), selection("eise"), additivity_evidence_id="explicit")),
        ("unmasked nonfinite sample", lambda: engine.thermal_response(history((np.inf,)), selection("eise"), additivity_evidence_id="explicit")),
        ("negative heat", lambda: engine.thermal_response(history((-1.,)), selection("eise"), additivity_evidence_id="explicit")),
        ("absorbed is not incident", lambda: engine.thermal_response(history((20000.,), quantity="absorbed_radiant_flux"), selection("eise"), additivity_evidence_id="explicit")),
        ("unknown model", lambda: engine.thermal_response(history(), selection("unknown"), additivity_evidence_id="explicit")),
        ("wrong normal convention", lambda: engine.thermal_response(history(), replace(selection("eise"), normal_distribution_mean=0.), additivity_evidence_id="explicit")),
        ("missing impact impulse", lambda: engine.pressure_response(replace(summary, positive_impulse_pa_s=None), selection("head"), positive_phase_evidence_id="explicit")),
        ("native dose overflow", lambda: engine.thermal_dose(history((1e308,)), additivity_evidence_id="numeric-probe")),
        ("native dose underflow", lambda: engine.thermal_dose(history((1e-300,)), additivity_evidence_id="numeric-probe")),
        ("native collapse arithmetic limit", lambda: engine.pressure_response(replace(summary, overpressure_pa=1e-300, positive_impulse_pa_s=1e-300),
            selection("coll"), positive_phase_evidence_id="numeric-probe")),
    )
    for name, callback in probes:
        try:
            callback()
        except ExposureEvaluationError as error:
            failures[name] = error
    mean_probe = HyRAMExposure(engine.native_module)
    mean_probe.native_normal_mean = 0.
    mean_binding_rejected = False
    try:
        mean_probe.thermal_response(history(), replace(selection("eise"), normal_distribution_mean=0.), additivity_evidence_id="explicit")
    except ExposureEvaluationError:
        mean_binding_rejected = True
    after = {name: sha(root/name) for name in host_names}
    native_after = {name: sha(path) for name, path in native_paths.items()}
    results = (*thermal.values(), pulse, smooth, split, linear, refined, absorbed, triangle, *pressure.values(), peak_only_zero, zero)
    owner_verified = all(engine.verify_result(result) is result for result in results)
    original = thermal["eise"]
    altered_raw_call = replace(original.native_calls[-1], raw=np.float64(.9))
    verification_failures = {}
    replacements = {
        "probability .9": replace(original, probability=.9),
        "different native model": replace(original, selection=replace(original.selection, model_id="tsao")),
        "different mean": replace(original, selection=replace(original.selection, normal_distribution_mean=0.)),
        "different model evidence": replace(original, selection=replace(original.selection, evidence_id="unbound-evidence")),
        "detached raw native probability": replace(original, native_result=np.float64(float(original.native_result))),
        "mutually replaced native call and probability": replace(original, probability=.9, native_result=altered_raw_call.raw,
            native_calls=(*original.native_calls[:-1], altered_raw_call)),
        "different input source": replace(original, input=replace(original.input, source_id="unbound-source")),
        "different chain status": replace(original, status="accepted-source-fire-chain"),
        "different native source": replace(original, native_source_sha256="0"*64),
        "structural fake": SimpleNamespace(probability=original.probability, status=original.status),
    }
    for name, record in replacements.items():
        try:
            engine.verify_result(record)
        except ExposureVerificationError as error:
            verification_failures[name] = error
    integral, error_bound, original_info = linear.quadrature_records[0]
    info = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in original_info.items()}
    for name in ("alist", "blist", "rlist", "elist"):
        info[name][info["last"]:] = np.nan
    info["iord"][info["last"]:] = -999
    unused_tail_record = replace(linear, quadrature_records=((integral, error_bound, info),))
    unused_tails_ignored = engine.verify_result(unused_tail_record) is unused_tail_record
    gates = {
        "actual native HyRAM6.1 functions retained": metadata.version == "6.1" and all(r.native_module is engine.native_module for r in results),
        "all four thermal models match actual constant native wrapper": native_constant_error < 1e-14,
        "independent normal CDF error <1e-14": cdf_error < 1e-14,
        "piecewise held pulse dose law differs from equal fluence": pulse.fluence_j_m2 == smooth.fluence_j_m2
            and abs(pulse.thermal_dose/smooth.thermal_dose-2**(1/3)) < 1e-14 and pulse.probability > smooth.probability,
        "held interval splitting preserves native dose <1e-14": split_error < 1e-14,
        "independent linear power integral <3e-14 relative": linear_error < 3e-14,
        "linear-history subdivision refinement <3e-14 relative": refinement < 3e-14,
        "absorbed diagnostic has no implicit harm response": absorbed.probability is None and absorbed.selection is None,
        "signed pressure triangle has explicit positive impulse": abs(triangle.positive_impulse_pa_s-5000.) < 1e-7
            and triangle.peak_overpressure_pa == 100000. and triangle.input.values[-1] == -20000.,
        "all four pressure models match genuine native summary response": pressure_error < 1e-14,
        "peak-only unused-zero native anomaly is exposed": peak_only_zero.probability == pressure["leis"].probability
            and native_unused_zero == 0. and peak_only_zero.probability > 0.,
        "native zero exposure branch retained": zero.probability == 0. and zero.native_probit is None,
        "ten invalid/missing/native numeric cases retain original input/cause": len(failures) == 10
            and all(e.input is not None and e.native_module is engine.native_module and e.__cause__ is not None for e in failures.values()),
        "normal-mean owner binding cannot be silently redirected": mean_binding_rejected,
        "owner verifies actual native records returning original identity": owner_verified,
        "owner rejects ten altered summaries/model/raw/source/structural records": len(verification_failures) == 10,
        "probability .9 rejection retains actual native replay": verification_failures["probability .9"].replayed.probability == original.probability,
        "native quadrature inactive workspace tails are ignored": unused_tails_ignored,
        "conditional source/clock/receptor status remains explicit": all(r.status == "conditional-on-supplied-exposure"
            and r.receptor_id == receptor.receptor_id and r.support_s[0] == 100. for r in results),
        "host/test/script/docs unchanged": before == after,
        "native source/license/metadata/numerical engines unchanged": native_before == native_after,
        "new host inputs are LF text": all(b"\r" not in (root/name).read_bytes() for name in host_names[:4]),
    }
    elapsed = perf_counter()-started
    rows = ["# Conditional supplied-field native exposure verification", "",
        "Reproduce: `python scripts/check_hyram_exposure.py --hyram-packages artifacts/native_hyram_packages`.", "",
        f"Actual HyRAM{metadata.version},SciPy{scipy.__version__},NumPy{np.__version__}; native/analytic/invalid cases took {elapsed:.6g}s. "
        "Native GPL-3.0-only implementation, coefficients and datasets are separately installed and unchanged.", "",
        "All fields/model choices/receptor coordinates are original numerical fixtures, not measured receptor vulnerability. "
        "Every result is conditional-on-supplied-exposure. No source/Flame/blast or accepted accident chain, participant count, "
        "occurrence probability or annual frequency is inferred; existing source-to-Flame rejection remains rejected.", "",
        "Native dose/probit/CDF calls are actual functions, not copied formulas or a replacement solver. "
        "Input units are incident/absorbed radiant W/m2, pressure gaugePa and positive impulsePa*s. "
        "Absorbed mathematical dose has no native harm probability. Canonical model IDs and the native normal mean convention are explicitly selected, "
        "with caller-declared applicability/evidence that this replay does not independently qualify.", "",
        "| Actual thermal model at40000W/m2 for10s | Native probability |", "|---|---:|"]
    rows.extend(f"| {name} | {r.probability:.12g} |" for name, r in thermal.items())
    rows.extend(["", "| Check | Value |", "|---|---:|",
        f"| constant native dose (W/m2)^(4/3)s | {thermal['eise'].thermal_dose:.12g} |",
        f"| pulse dose / equal-fluence smooth dose | {pulse.thermal_dose/smooth.thermal_dose:.12g} |",
        f"| common pulse/smooth radiant fluence J/m2 | {pulse.fluence_j_m2:.12g} |",
        f"| constant wrapper probability error | {native_constant_error:.12g} |",
        f"| independent normal CDF error | {cdf_error:.12g} |",
        f"| native held splitting relative error | {split_error:.12g} |",
        f"| linear analytic power-integral relative error | {linear_error:.12g} |",
        f"| native linear subdivision relative error | {refinement:.12g} |",
        f"| signed triangle positive impulse Pa*s | {triangle.positive_impulse_pa_s:.12g} |",
        f"| peak-only native model probability | {peak_only_zero.probability:.12g} |",
        f"| native convenience wrapper with unused zero impulse | {native_unused_zero:.12g} |", "",
        "Held histories sum native interval doses under an explicit additive/no-recovery equivalent-dose assumption. "
        "The pulse uses40000W/m2 for5s thenzero5s; the equal-fluence smooth history uses20000W/m2 for10s. "
        "Linear12000→36000W/m2 over6s calls native unit-time dose inside SciPy quadrature; the independent mathematical power integral "
        "and16-segment native refinement agree. No effective averaged flux is invented. Biological recovery, movement/escape and calibration "
        "of time-varying harm remain outside this constitutive reduction.", "",
        "The linear pressure waveform at times100,100.05,100.1,100.15s has gaugePa0,100000,0,−20000. "
        "Its positive triangle impulse is5000Pa*s; the negative phase remains in the original input. "
        "The chosen native impact models require both summaries; missing impulse is retained as an error. "
        "For native peak-only models no unused impulse is supplied to the selected native function. The existing native convenience wrapper "
        "would force zero when given an irrelevant zero impulse; that actual discrepancy is recorded without altering native code/model.", "",
        "| Actual pressure model at100000Pa and5000Pa*s | Native probability |", "|---|---:|"])
    rows.extend(f"| {name} | {r.probability:.12g} |" for name, r in pressure.items())
    rows.extend(["", "| Retained failed input | Native calls returned | Native failed-call pending | Original cause |", "|---|---:|---|---|"])
    rows.extend(f"| {name} | {len(e.native_calls)} | {e.failed_call is not None} | {type(e.__cause__).__name__}: {' '.join(str(e.__cause__).split())[:200]} |"
                for name, e in failures.items())
    rows.extend(["", "The exact input/selection, actual native module/function references, returned raw-call prefix, pending failed-call args, "
        "quadrature records and original cause remain available. No missing sample, negative heat, numeric underflow or absent impulse is filled. "
        "Native zero exposure uses its actual wrapper; the unexposed intermediate probit is None. Native CDF saturation at0/1 is numerical response, "
        "not measured certainty. Normal-mean rebinding is rejected; no native monkeypatch or copied coefficient table is used.", "",
        "The public owner verify_result API reexecutes the existing native path and returns the original result object on success. "
        "Input/model/mean/evidence/tolerance/response-kind/native-source identity is bound separately from the computed summaries. "
        "It compares probability,dose,probit,fluence,pressure/impulse and actual native function/argument/raw-call records, including raw-result "
        "object binding to its retained native call. Concrete owner type is required; structural lookalikes are not computed-native provenance. "
        "QUADPACK comparisons use only integral/error, counts, active subintervals and active error-order pointers; unused uninitialized work-array "
        "tails are ignored and a deliberate tail rewrite still verifies.", "",
        "| Rejected cached record | Actual replay available | Original verification cause |", "|---|---|---|"])
    rows.extend(f"| {name} | {failure.replayed is not None} | {' '.join(str(failure.__cause__).split())[:200]} |"
                for name, failure in verification_failures.items())
    rows.extend(["", "| Verification gate | Pass |", "|---|---|"])
    rows.extend(f"| {name} | {passed} |" for name, passed in gates.items())
    rows.extend(["", "Primary sources: [official native probit API/source](https://github.com/sandialabs/hyram/blob/master/src/hyram/qra/probits.py), "
        "[Sandia HyRAM/versioned documentation](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/), "
        "[HyRAM6.1 metadata](https://pypi.org/project/hyram/6.1/), "
        "[technical manual bibliographic reference](https://doi.org/10.2172/2563814). Installed6.1source/API/GPL notice and public source were inspected; "
        "manual download endpoints timed out during this review. Original harm-calibration data/table rights and independent human-response validation "
        "were not reviewed or supplied. No table/coefficients are redistributed.", "",
        "## Source fingerprints", "", "| Host input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {before[name]} | {after[name]} |" for name in host_names)
    rows.extend(["", "| Installed input | Begin SHA256 | End SHA256 |", "|---|---|---|"])
    rows.extend(f"| {name} | {native_before[name]} | {native_after[name]} |" for name in native_paths)
    if not args.no_report:
        (root/"research/native_exposure.md").write_text("\n".join(rows)+"\n", encoding="utf-8", newline="\n")
    print(f"Native exposure HyRAM{metadata.version}/SciPy{scipy.__version__}: {sum(gates.values())}/{len(gates)} gates passed in {elapsed:.6g}s")
    print(f"linear relative error={linear_error:.12g}; pressure impulse={triangle.positive_impulse_pa_s:.12g}; CDF error={cdf_error:.12g}")
    for name, passed in gates.items():
        if not passed:
            print("FAILED:", name)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
