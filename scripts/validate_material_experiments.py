"""Conditional held-out permeance comparison with a measured CC BY 4.0 dataset.

Source: Ververs, Arratibel, Di Felice and Gallucci, Zenodo 10691625 (2024).
Only lumped permeance is identifiable here. No specimen thickness, diffusivity
or solubility is invented. Raw observations and per-row outputs stay ignored.
"""

import argparse
import csv
import hashlib
import json
import math
import platform
import urllib.request
from pathlib import Path

import CoolProp
import CoolProp.CoolProp as CP
import numpy as np
from openpyxl import load_workbook

from h2physics.materials import HydrogenCarrier, PowerLawSolubility, steady_permeation
from h2physics.thermo import CoolPropProperties

DOI = "10.5281/zenodo.10691625"
METADATA_URL = "https://zenodo.org/api/records/10691625"
FILE_URL = METADATA_URL + "/files/DataPalladiumBasedMembranes.xlsx/content"
FILE_SHA256 = "042e32db5d70257c5d322a472ac85991fa1668036ea58f606f915a2932ff1af8"
FILE_MD5 = "f4eec195c254ed7ded3c2598c0ff9775"
BLOCKS = (1, 6, 11, 16)
TRAIN_C = (350., 450.)
TEST_C = 400.


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "h2physics-research/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def load_verified(data_dir, acquire):
    data_dir.mkdir(parents=True, exist_ok=True)
    file = data_dir / "pd-data.xlsx"
    metadata = data_dir / "pd-metadata.json"
    if acquire and not metadata.exists():
        metadata.write_bytes(fetch(METADATA_URL))
    if not metadata.exists():
        raise FileNotFoundError("Acquire the primary metadata before using its observations")
    record = json.loads(metadata.read_text(encoding="utf-8"))
    if record["doi"] != DOI or record["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Source identity or explicit reuse grant differs")
    entry = next(item for item in record["files"]
                 if item["key"] == "DataPalladiumBasedMembranes.xlsx")
    if entry["checksum"] != "md5:" + FILE_MD5:
        raise ValueError("Publisher file checksum differs from admitted source")
    if acquire and not file.exists():
        file.write_bytes(fetch(FILE_URL))
    raw = file.read_bytes()
    if len(raw) != entry["size"] or hashlib.sha256(raw).hexdigest() != FILE_SHA256:
        raise ValueError("Workbook bytes differ from the pinned measured dataset")
    if hashlib.md5(raw).hexdigest() != FILE_MD5:
        raise ValueError("Publisher MD5 mismatch")
    return file, metadata, record


def observations(file):
    sheet = load_workbook(file, data_only=True, read_only=True)["Pure H2 tests"]
    rows = list(sheet.values)
    result = []
    for start in BLOCKS:
        name = rows[4][start]
        if tuple(rows[5][start:start + 4]) != ("T", "p(perm)", "p(ret)", "flux"):
            raise ValueError("Unexpected source column meanings")
        if tuple(rows[6][start:start + 4]) != ("\N{DEGREE SIGN}C", "bar(a)", "bar(a)", "mol s-1 m-2"):
            raise ValueError("Unexpected temperature/absolute-pressure/flux units")
        for row_number, row in enumerate(rows[7:], 8):
            temperature, downstream, upstream, flux = map(float, row[start:start + 4])
            if temperature not in (*TRAIN_C, TEST_C) or not (upstream > downstream > 0 and flux > 0):
                raise ValueError("Unexpected measured pure-H2 domain")
            result.append({"material": name, "source_row": row_number,
                           "temperature_c": temperature, "temperature_k": temperature + 273.15,
                           "downstream_pressure_pa_absolute": downstream * 1e5,
                           "upstream_pressure_pa_absolute": upstream * 1e5,
                           "measured_flux_mol_m2_s": flux})
    if len(result) != 96:
        raise ValueError("Expected all 96 pure-H2 observations")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path,
                        default=Path("data/raw/material-validation-candidates/20261102"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("artifacts/physical-validation-20261102"))
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    file, metadata, record = load_verified(args.data_dir, args.acquire)
    rows = observations(file)
    # Fix the split before estimation: all350/450C curves calibrate, all400C
    # curves are held out. No row-wise random split or test-derived scaling.
    gas = CoolPropProperties("Hydrogen")
    law = PowerLawSolubility(HydrogenCarrier("molecular_hydrogen", gas.molar_mass_kg_mol),
                            lambda temperature: 1., .5)
    native = CP.AbstractState("HEOS", "Hydrogen")

    def fugacity(pressure, temperature):
        native.update(CP.PT_INPUTS, pressure, temperature)
        return pressure * native.fugacity_coefficient(0)

    for row in rows:
        up = fugacity(row["upstream_pressure_pa_absolute"], row["temperature_k"])
        down = fugacity(row["downstream_pressure_pa_absolute"], row["temperature_k"])
        # The unit reference is an algebraic factorization of D*S/L, NOT
        # observed geometry or material coefficients. Only its fitted product
        # is used to predict flux. D and S cannot be inferred individually.
        response = steady_permeation(law, diffusivity_m2_s=1., thickness_m=1.,
            upstream_fugacity_pa=up, downstream_fugacity_pa=down,
            temperature_k=row["temperature_k"])
        row["sqrt_fugacity_response_pa_half"] = response.mobile_entity_flux_mol_m2_s
        row["split"] = "test" if row["temperature_c"] == TEST_C else "calibration"

    materials = []
    for name in dict.fromkeys(row["material"] for row in rows):
        selected = [row for row in rows if row["material"] == name]
        coefficients = {}
        for temperature in TRAIN_C:
            train = [row for row in selected if row["temperature_c"] == temperature]
            x = np.array([row["sqrt_fugacity_response_pa_half"] for row in train])
            y = np.array([row["measured_flux_mol_m2_s"] for row in train])
            coefficients[temperature] = float(np.dot(x, y) / np.dot(x, x))
        # Two calibrated endpoint permeances define one Arrhenius line in1/T.
        t0, t1 = (temperature + 273.15 for temperature in TRAIN_C)
        k0, k1 = (coefficients[temperature] for temperature in TRAIN_C)
        slope = (math.log(k1) - math.log(k0)) / (1. / t1 - 1. / t0)
        for row in selected:
            log_k = math.log(k0) + slope * (1. / row["temperature_k"] - 1. / t0)
            row["predicted_flux_mol_m2_s"] = math.exp(log_k) * row["sqrt_fugacity_response_pa_half"]
            row["residual_mol_m2_s"] = row["predicted_flux_mol_m2_s"] - row["measured_flux_mol_m2_s"]
        heldout = [row for row in selected if row["split"] == "test"]
        error = np.array([row["residual_mol_m2_s"] for row in heldout])
        measured = np.array([row["measured_flux_mol_m2_s"] for row in heldout])
        materials.append({"material": name, "calibration_count": 16, "heldout_count": 8,
            "calibration_permeance_mol_m2_s_pa_half": {str(t): coefficients[t] for t in TRAIN_C},
            "fitted_effective_activation_j_mol": -slope * 8.31446261815324,
            "heldout_bias_mol_m2_s": float(np.mean(error)),
            "heldout_rmse_mol_m2_s": float(np.sqrt(np.mean(error ** 2))),
            "heldout_mean_absolute_relative_error": float(np.mean(np.abs(error / measured))),
            "heldout_max_absolute_relative_error": float(np.max(np.abs(error / measured)))})

    report = {"source_doi": DOI, "source_url": "https://zenodo.org/records/10691625",
        "attribution": [creator["name"] for creator in record["metadata"]["creators"]],
        "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "file_sha256": FILE_SHA256, "publisher_md5_verified": True,
        "metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
        "raw_redistribution_admitted": False,
        "measurement_count": len(rows), "calibration_count": 64, "heldout_count": 32,
        "calibration_temperature_c": list(TRAIN_C), "heldout_temperature_c": TEST_C,
        "test_pressure_range_pa_absolute": [150000., 500000.],
        "permeate_pressure_pa_absolute": 100000.,
        "model": "steady_permeation / PowerLawSolubility exponent0.5 with fitted effective D*S/L(T)",
        "status": "conditional_within_dataset_heldout_prediction_not_material_qualification",
        "validation_qualified": False,
        "limitations": [
            "Effective permeance only: physical thickness, D and S are not identified or invented.",
            "The1m/1m2s unit response is algebraic factorization, not specimen geometry or diffusivity.",
            "Held-out complete temperature curves are from the same dataset/apparatus, not a new independent campaign.",
            "Only pure H2 observations used; no mixed-gas concentration polarization or coating-layer model validated.",
            "Source measurement uncertainty and replicate identities unavailable; no uncertainty-normalized pass/fail.",
            "No universal error threshold selected; every heldout point is retained.",
            "Independent third-party content review is not complete; source workbook stays outside public distribution."],
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "CoolProp": CoolProp.__version__},
        "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in
            (Path(__file__), Path("src/h2physics/materials/transport.py"))},
        "materials": materials}
    atomic_json(args.output_dir / "materials-validation.json", report)
    with (args.output_dir / "materials-heldout-and-calibration.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": report["status"], "heldout_count": 32, "materials": materials}))


if __name__ == "__main__":
    main()
