"""Conditional temporal holdout comparison of authored PEM polarization losses.

Brundiers et al., Zenodo v1, DOI10.5281/zenodo.19361280, CC BY4.0.
Raw observations remain in the ignored source archive and output directory.
This does not qualify reaction thermodynamics, efficiency or a plant model.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from h2physics.data.pem import load_pem_csv, pem_spectra
from h2physics.electrochemistry import OhmicLoss, SymmetricButlerVolmerLoss

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = "ef15233374ece3af33a3f876a80d8a7c38c965dff122b884c6ebd39f391952e4"
SOURCE = "https://doi.org/10.5281/zenodo.19361280"
MEMBERS = ("Reference_dataset.csv", "PtNano_dataset.csv", "PtBlack_dataset.csv", "PtC_dataset.csv")
AREA_M2 = 4e-4
MIN_TRAIN_J = 500.  #0.05 A/cm2; predefined above the documented low-current crossover region.


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prefix_before_counter_three(archive, member):
    """Keep exact original leading bytes, without parsing the later durability run."""
    parts, source_lines, boundary_found = [], 0, False
    with archive.open(member) as stream:
        header = stream.readline()
        parts.append(header)
        for line in stream:
            source_lines += 1
            trimmed = line.rstrip(b"\r\n")
            if trimmed:
                row = next(csv.reader([trimmed.decode("utf-8")]))
                if len(row) != 13:
                    raise ValueError("Source row differs from the reviewed13-column profile")
                if row[-2] == "POL_GEIS" and int(row[-1]) >= 3:
                    boundary_found = True
                    break
            parts.append(line)
    if not boundary_found:
        raise ValueError("Complete counter1/2 prefix boundary was not found")
    return b"".join(parts), source_lines


def voltage(parameters, current_density, temperatures):
    offset, log_exchange, log_resistance = parameters
    exchange, resistance = math.exp(log_exchange), math.exp(log_resistance)
    activation = SymmetricButlerVolmerLoss(lambda t: exchange, 1.)
    ohmic = OhmicLoss(lambda t: resistance)
    return np.array([offset + activation(float(j), float(t)) + ohmic(float(j), float(t))
                     for j, t in zip(current_density, temperatures, strict=True)])


def metrics(observed, predicted):
    error = predicted - observed
    return {"n": len(error), "rmse_v": float(np.sqrt(np.mean(error**2))),
            "mae_v": float(np.mean(abs(error))), "bias_v": float(np.mean(error)),
            "maximum_absolute_error_v": float(np.max(abs(error)))} if len(error) else {"n": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
        default=ROOT / "data/raw/pem-crossover/Version v1/pem_water_electrolysis_degradation_data.zip")
    parser.add_argument("--output", type=Path,
        default=ROOT / "artifacts/physical-validation-20261102/electrochemical-comparison.json")
    args = parser.parse_args()
    started = time.monotonic()
    sources = [ROOT / "src/h2physics/electrochemistry.py", ROOT / "src/h2physics/data/pem.py",
               ROOT / "scripts/validate_electrochemical_experiments.py"]
    before = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    if digest(args.archive) != ARCHIVE_SHA:
        raise ValueError("Source archive does not match the rights-reviewed v1 receipt")
    result = {
        "source_url": SOURCE, "authors": "Brundiers et al. (2026)", "license": "CC-BY-4.0",
        "archive_sha256": ARCHIVE_SHA, "source_sha256": before,
        "status": "conditional_temporal_holdout_diagnostic_not_qualified_validation",
        "model": "existing SymmetricButlerVolmerLoss(n_eff=1) + OhmicLoss + fitted voltage offset",
        "area_m2": AREA_M2, "area_source": "dataset documentation page2, Table1; visually checked",
        "selection_fixed_before_fit": {
            "training": "whole POL_GEIS counter1; current density >=500A/m2",
            "heldout": "all positive-current DC-context points in whole counter2; no heldout refit",
            "dc_context": "last10 preceding non-EIS rows in same protocol, gap<=120s; existing loader",
            "reason_for_training_lower_limit": "source documents crossover-dominated lowest0.01/0.02Acm-2",
            "no_voltage_based_outlier_removal": True,
        },
        "limits": [
            "Repeated curves belong to the same physical cell/bench, not independent cells or sources.",
            "Reported block temperature is an explicit proxy; actual reaction temperature is unknown.",
            "Cathode pressure is recorded; the offset absorbs pressure/reversible-reference effects rather than predicting them.",
            "Voltage offset and effective exchange/resistance are estimated from counter1, not independent material measurements.",
            "Effective charge-transfer electron factor1 is an explicit selected closure, not a measured material constant.",
            "No measurement voltage uncertainty is specified in the reviewed description; no invented pass threshold or confidence interval.",
            "Faradaic H2 rate, thermodynamic energies, degradation and system efficiency are not validated.",
            "Current loader consumes exact original prefixes; prefix SHA is not claimed to be a full CSV member hash.",
        ], "cells": [],
    }
    all_observed, all_predicted = [], []
    with zipfile.ZipFile(args.archive) as archive:
        result["description_sha256"] = hashlib.sha256(
            archive.read("readMe_dataset_documentation.pdf")).hexdigest()
        for member in MEMBERS:
            prefix, lines = prefix_before_counter_three(archive, member)
            experiment = load_pem_csv(io.BytesIO(prefix), experiment_id="pem/" + member,
                source_id=SOURCE, measurement_types=("POL_GEIS",), counters=(1, 2),
                active_area_m2=AREA_M2, phase_sign=1)
            points, missing = [], 0
            for sweep in pem_spectra(experiment, maximum_dc_gap_s=120.):
                counter = int(sweep.spectrum.experiment_id.split("/POL_GEIS/")[1].split("/")[0])
                context = (sweep.dc_current_a, sweep.dc_voltage_v, sweep.block_temperature_k,
                           sweep.cathode_pressure_pa)
                if any(v is None or not math.isfinite(v) for v in context):
                    missing += 1
                    continue
                current, potential, temperature, pressure = context
                if current <= 0:
                    missing += 1
                    continue
                points.append({"counter": counter, "current_density_a_m2": current / AREA_M2,
                    "voltage_v": potential, "block_temperature_k": temperature,
                    "cathode_pressure_pa_absolute": pressure,
                    "source_row_ids": sweep.dc_context_row_ids,
                    "sweep_id": sweep.spectrum.experiment_id})
            train = [p for p in points if p["counter"] == 1 and p["current_density_a_m2"] >= MIN_TRAIN_J]
            test = [p for p in points if p["counter"] == 2]
            if len(train) < 6 or not test:
                result["cells"].append({"member": member, "status": "insufficient_declared_groups",
                    "training_points": len(train), "heldout_points": len(test)})
                continue
            def arrays(rows):
                return tuple(np.array([p[k] for p in rows]) for k in
                    ("current_density_a_m2", "block_temperature_k", "voltage_v"))
            j, temp, observed = arrays(train)
            fit = least_squares(lambda x: voltage(x, j, temp) - observed,
                (1.4, math.log(10.), math.log(2e-5)),
                bounds=((.8, math.log(1e-6), math.log(1e-9)),
                        (1.8, math.log(1e5), math.log(1e-3))),
                max_nfev=2000, ftol=1e-11, xtol=1e-11, gtol=1e-11)
            if not fit.success:
                raise ValueError(f"Declared calibration did not converge: {member}: {fit.message}")
            test_j, test_t, test_v = arrays(test)
            predicted = voltage(fit.x, test_j, test_t)
            inside = test_j >= MIN_TRAIN_J
            singular = np.linalg.svd(fit.jac, compute_uv=False)
            for p, pred in zip(test, predicted, strict=True):
                p["predicted_voltage_v"] = float(pred)
                p["error_v"] = float(pred - p["voltage_v"])
                p["above_predeclared_low_current_cutoff"] = p["current_density_a_m2"] >= MIN_TRAIN_J
                p["within_actual_training_current_range"] = float(j.min()) <= p["current_density_a_m2"] <= float(j.max())
            result["cells"].append({"member": member, "status": "heldout_compared_no_acceptance_threshold",
                "prefix_sha256": hashlib.sha256(prefix).hexdigest(), "prefix_bytes": len(prefix),
                "source_lines_scanned": lines, "selected_loader_rows": experiment.report.rows_retained,
                "unavailable_dc_context_count": missing,
                "training_points": len(train), "heldout_points": len(test),
                "fit": {"offset_v": float(fit.x[0]), "exchange_current_density_a_m2": math.exp(fit.x[1]),
                        "area_resistance_ohm_m2": math.exp(fit.x[2]), "nfev": fit.nfev,
                        "jacobian_singular_values": singular.tolist(),
                        "condition_number": float(singular[0] / singular[-1]),
                        "active_bounds": fit.active_mask.tolist()},
                "training_error": metrics(observed, voltage(fit.x, j, temp)),
                "heldout_all": metrics(test_v, predicted),
                "heldout_above_current_cutoff": metrics(test_v[inside], predicted[inside]),
                "heldout_low_current": metrics(test_v[~inside], predicted[~inside]),
                "heldout_outside_actual_training_current_range": sum(
                    not p["within_actual_training_current_range"] for p in test),
                "training_current_range_a_m2": [float(j.min()), float(j.max())],
                "heldout_current_range_a_m2": [float(test_j.min()), float(test_j.max())],
                "heldout_block_temperature_range_k": [float(test_t.min()), float(test_t.max())],
                "heldout_cathode_pressure_range_pa": [float(min(p["cathode_pressure_pa_absolute"] for p in test)),
                                                      float(max(p["cathode_pressure_pa_absolute"] for p in test))],
                "heldout_rows": test})
            all_observed.extend(test_v)
            all_predicted.extend(predicted)
            print(member, "train", len(train), "test", len(test),
                  "heldout_RMSE_V", metrics(test_v, predicted)["rmse_v"], flush=True)
    if not all_observed:
        raise ValueError("No independent-of-fit heldout protocol curve was compared")
    result["pooled_heldout_error"] = metrics(np.asarray(all_observed), np.asarray(all_predicted))
    result["source_unchanged"] = before == {str(p.relative_to(ROOT)): digest(p) for p in sources}
    result["elapsed_s"] = time.monotonic() - started
    result["recorded_utc"] = datetime.now(UTC).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps(result["pooled_heldout_error"]))


if __name__ == "__main__":
    main()
