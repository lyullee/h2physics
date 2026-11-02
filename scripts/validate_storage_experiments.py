"""Conditional held-batch prediction of measured normalized AB2 hydride kinetics.

Source: Neves, Warfsmann and Grossmann, Zenodo 10.5281/zenodo.16458050,
v1.0, CC BY 4.0; article DOI 10.1016/j.egyai.2025.100659. Only the
measurement CSVs and experiment-condition summary are read. Bundled code,
neural-network outputs and fitted kinetic constants are never used.
"""

import argparse
import hashlib
import io
import json
import math
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import CoolProp
import CoolProp.CoolProp as CP
import numpy as np
import openpyxl
from scipy.optimize import least_squares, minimize_scalar

from h2physics.constants import R_J_MOL_K
from h2physics.storage.hydride import ArrheniusRate, HydrideKinetics, VanthoffPlateau

EXPECTED_ARCHIVE_SHA256 = "8a9fa655f0244a34e77edf84b3b3a32147abd9102bcfafe686f12e4630e5eb5f"
REFERENCE_TEMPERATURE_K = 293.15


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_measurements(path):
    if sha256(path) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("Archive does not match the acquired version-1 receipt")
    state = CP.AbstractState("HEOS", "Hydrogen")
    curves = []
    with zipfile.ZipFile(path) as archive:
        summary_name = next(n for n in archive.namelist() if n.endswith("_Summary.xlsx"))
        workbook = openpyxl.load_workbook(io.BytesIO(archive.read(summary_name)),
                                         read_only=True, data_only=True)
        rows = workbook["Summary"].iter_rows(values_only=True)
        header = next(rows)
        required = ("Descriptor", "Batch", "Reaction", "Mean T [°C]", "Mean P [bar]")
        columns = {name: header.index(name) for name in required}
        conditions = {}
        for row in rows:
            descriptor = row[columns["Descriptor"]]
            if isinstance(descriptor, str) and descriptor.startswith("JW("):
                if descriptor in conditions:
                    raise ValueError("Duplicate experiment-condition descriptor")
                conditions[descriptor] = {key: row[index] for key, index in columns.items()}
        workbook.close()
        names = sorted(n for n in archive.namelist() if "/Raw Data/" in n and n.endswith(".csv"))
        if len(names) != 144:
            raise ValueError("Unexpected experimental curve inventory")
        for name in names:
            raw = archive.read(name)
            data = np.genfromtxt(io.BytesIO(raw), delimiter=",", names=True)
            if data.dtype.names != ("Time", "Alpha", "Smoothed_Alpha"):
                raise ValueError("Source measurement schema changed")
            identifier = Path(name).stem
            condition = conditions[identifier]
            t = np.asarray(data["Time"], dtype=float)
            alpha = np.asarray(data["Alpha"], dtype=float)
            if (not np.all(np.isfinite(t)) or not np.all(np.isfinite(alpha))
                    or np.any(np.diff(t) <= 0) or np.any((alpha < 0) | (alpha > 1))):
                raise ValueError("Invalid source observation; no silent cleaning is applied")
            temperature = float(condition["Mean T [°C]"]) + 273.15
            pressure = float(condition["Mean P [bar]"]) * 1e5
            state.update(CP.PT_INPUTS, pressure, temperature)
            fugacity = float(state.fugacity(0))
            curves.append({"identifier": identifier, "member": name,
                           "sha256": hashlib.sha256(raw).hexdigest(),
                           "batch": condition["Batch"], "branch": condition["Reaction"],
                           "temperature_k": temperature, "pressure_pa_assumed_absolute": pressure,
                           "fugacity_pa": fugacity, "elapsed_s": t - t[0], "alpha": alpha,
                           "initial_alpha": float(alpha[0]),
                           "rows": len(t), "split": "test" if condition["Batch"] == "JW(H)" else "train"})
    return curves


def kinetics(parameters, branch):
    log_rate, activation, enthalpy, log_reference_fugacity = parameters
    entropy = R_J_MOL_K * log_reference_fugacity + enthalpy / REFERENCE_TEMPERATURE_K
    equilibrium = VanthoffPlateau(enthalpy, entropy, 1.)
    rate = ArrheniusRate(math.exp(log_rate), activation, REFERENCE_TEMPERATURE_K)
    zero = ArrheniusRate(0., 0., REFERENCE_TEMPERATURE_K)
    return HydrideKinetics(equilibrium, rate if branch == "Abs" else zero,
                          zero if branch == "Abs" else rate)


def predicted_rate(model, curve):
    x = 0. if curve["branch"] == "Abs" else 1.
    value = model.fraction_rate_s_inv(x, curve["temperature_k"], curve["fugacity_pa"])
    return value if curve["branch"] == "Abs" else -value


def trajectory(q, elapsed_s, initial_alpha):
    """Exact solution of the selected constant-forcing first-order host law."""
    return initial_alpha + (1. - initial_alpha) * (-np.expm1(-q * elapsed_s))


def fit_branch(training, branch):
    # A per-curve training-only nuisance rate summarizes the observed first-order
    # response. The actual global physical law remains the existing host model.
    selected = [c for c in training if c["branch"] == branch]
    observed_rates = []
    for curve in selected:
        mask = (curve["alpha"] >= .1) & (curve["alpha"] <= .9)
        t, alpha = curve["elapsed_s"][mask], curve["alpha"][mask]
        if len(t) < 5:
            raise ValueError("Training curve has insufficient middle-range observations")
        estimate = minimize_scalar(lambda log_q: float(np.mean(
            (trajectory(math.exp(log_q), t, curve["initial_alpha"]) - alpha) ** 2)),
            bounds=(-20., 5.), method="bounded", options={"xatol": 1e-10})
        if not estimate.success:
            raise RuntimeError("Training nuisance-rate estimation failed")
        observed_rates.append(math.exp(estimate.x))
    target = np.log(observed_rates)

    def residual(parameters):
        model = kinetics(parameters, branch)
        rates = np.array([predicted_rate(model, c) for c in selected])
        return np.log(np.maximum(rates, 1e-30)) - target

    attempts = []
    for initial_enthalpy in (20000., 30000., 40000.):
        result = least_squares(residual, (-2., 20000., initial_enthalpy, math.log(1e6)),
            bounds=((-20., 0., 5000., math.log(1e3)),
                    (5., 150000., 80000., math.log(1e8))),
            x_scale=(1., 30000., 30000., 1.), max_nfev=1500,
            ftol=1e-10, xtol=1e-10, gtol=1e-10)
        attempts.append(result)
    fitted = min(attempts, key=lambda r: float(np.dot(r.fun, r.fun)))
    parameters = fitted.x
    return parameters, {
        "branch": branch, "training_curves": len(selected), "optimizer_success": bool(fitted.success),
        "optimizer_message": fitted.message, "objective_log_rate_sse": float(np.dot(fitted.fun, fitted.fun)),
        "active_bounds": dict(zip(("log_reference_rate", "activation_energy", "plateau_enthalpy",
                                   "log_reference_fugacity"), map(int, fitted.active_mask))),
        "parameter_bounds": {"log_reference_rate_s_inv": [-20., 5.],
                             "activation_energy_j_mol": [0., 150000.],
                             "plateau_enthalpy_j_mol": [5000., 80000.],
                             "reference_fugacity_pa": [1e3, 1e8]},
        "fitted": {"reference_rate_s_inv": math.exp(parameters[0]),
                   "activation_energy_j_mol": float(parameters[1]),
                   "plateau_enthalpy_j_mol": float(parameters[2]),
                   "reference_fugacity_pa": math.exp(parameters[3])},
        "multistart_count": len(attempts),
        "training_only_effective_rates": dict(zip((c["identifier"] for c in selected), observed_rates)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
        default=Path("artifacts/physical-validation-20261102/storage-source/hydride-kinetics-v1.zip"))
    parser.add_argument("--output", type=Path,
        default=Path("artifacts/physical-validation-20261102/storage-results.json"))
    args = parser.parse_args()
    started = time.monotonic()
    pinned = {str(p): sha256(p) for p in (Path(__file__), Path("src/h2physics/storage/hydride.py"))}
    curves = load_measurements(args.archive)
    training = [c for c in curves if c["split"] == "train"]
    testing = [c for c in curves if c["split"] == "test"]
    if len(training) != 100 or len(testing) != 44:
        raise ValueError("Predeclared whole-batch split changed")
    models, calibration = {}, {}
    for branch in ("Abs", "Des"):
        parameters, calibration[branch] = fit_branch(training, branch)
        models[branch] = kinetics(parameters, branch)
    results = []
    for curve in curves:
        q = predicted_rate(models[curve["branch"]], curve)
        prediction = trajectory(q, curve["elapsed_s"], curve["initial_alpha"])
        errors = prediction - curve["alpha"]
        total = np.sum((curve["alpha"] - np.mean(curve["alpha"])) ** 2)
        results.append({key: value for key, value in curve.items() if key not in ("alpha", "elapsed_s")}
                       | {"predicted_rate_s_inv": q, "rmse_alpha": float(np.sqrt(np.mean(errors**2))),
                          "mae_alpha": float(np.mean(np.abs(errors))), "bias_alpha": float(np.mean(errors)),
                          "max_abs_error_alpha": float(np.max(np.abs(errors))),
                          "r_squared": float(1. - np.sum(errors**2) / total)})
    aggregates = []
    for split in ("train", "test"):
        for branch in ("Abs", "Des"):
            selected = [r for r in results if r["split"] == split and r["branch"] == branch]
            aggregates.append({"split": split, "branch": branch, "curves": len(selected),
                "observations": sum(r["rows"] for r in selected),
                "mean_curve_rmse_alpha": float(np.mean([r["rmse_alpha"] for r in selected])),
                "median_curve_rmse_alpha": float(np.median([r["rmse_alpha"] for r in selected])),
                "mean_curve_mae_alpha": float(np.mean([r["mae_alpha"] for r in selected])),
                "mean_curve_bias_alpha": float(np.mean([r["bias_alpha"] for r in selected])),
                "minimum_curve_r_squared": min(r["r_squared"] for r in selected)})
    report = {"recorded_utc": datetime.now(UTC).isoformat(),
        "source_doi": "10.5281/zenodo.16458050", "source_version": "v1.0", "license_id": "CC-BY-4.0",
        "attribution": "Neves (maintainer/data analysis), Warfsmann (data collection), Grossmann (coding), 2025",
        "archive_sha256": EXPECTED_ARCHIVE_SHA256, "coolprop_version": CoolProp.__version__,
        "backend": "HEOS/Hydrogen, native fugacity", "model": "HydrideKinetics/ArrheniusRate/VanthoffPlateau",
        "status": "conditional_normalized_experimental_holdout_comparison_not_qualified",
        "validation_qualified": False, "independent_external_lab_validation": False,
        "split": {"training_batches": ["JW(D)", "JW(E)", "JW(F)", "JW(G)"],
                  "heldout_batch": "JW(H)", "training_curves": 100, "heldout_curves": 44,
                  "rule_declared_before_fit": True, "test_data_used_for_fit_or_model_selection": False},
        "observation_policy": "Unsmoothed Alpha only, source-normalized by each run's observed capacity. No own endpoint rescaling. Time starts at first recorded sample with that sample's measured Alpha as initial condition. Training nuisance rates use alpha0.1..0.9; all source rows are retained and evaluated for curve error, including every heldout row.",
        "limitations": [
            "Normalized fraction validation only; source normalization uses each run's maximum measured capacity, so no absolute uptake/capacity prediction is tested.",
            "Only source mean pressure and temperature are available; fixed forcing is conditional, not a reconstruction of measured forcing histories.",
            "Mean source pressure in bar is interpreted as absolute for native fugacity. Explicit absolute/gauge metadata remains unresolved.",
            "The CSV Time column has no unit in its header; seconds are assumed from the associated experiment convention. Explicit per-file time-unit metadata remains unresolved, so fitted reference rates are conditional on that assumption.",
            "Summary source kinetic constants, model labels, smoothed Alpha and neural-network outputs are unused.",
            "Training parameters are calibrated for this alloy; not universal material coefficients. No test-based parameter adjustment is performed.",
            "Absorption/desorption are fitted as separate one-direction isothermal rate models. No combined hysteresis or finite thermal/inventory behavior is validated.",
            "An active parameter bound is a calibration/identifiability limitation; fitted plateau enthalpy is not an independently measured thermodynamic property.",
            "Raw instrument pressure/temperature/uptake histories and pointwise uncertainty are not in these CSVs; no uncertainty-normalized acceptance test is possible.",
            "Whole-batch holdout is from the same experimental program, not an independent laboratory.",
            "No arbitrary percentage acceptance threshold is applied. Discrepancies are retained; no model change is made to force agreement."],
        "calibration": calibration, "aggregate": aggregates, "curves": results,
        "source_sha256": pinned, "source_unchanged": all(sha256(Path(p)) == digest for p, digest in pinned.items()),
        "elapsed_s": time.monotonic() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"aggregate": aggregates, "fitted": {b: c["fitted"] for b, c in calibration.items()},
                      "elapsed_s": report["elapsed_s"], "validation_qualified": False}))


if __name__ == "__main__":
    main()
