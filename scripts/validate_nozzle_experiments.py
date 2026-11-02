"""Conditional flow comparison, with a whole operating condition held out.

Source: Grune and Sempert, doi:10.5281/zenodo.4668554, CC BY 4.0.
Only aggregate metrics are suitable for the public report. Gas temperature is
not measured here: ambient temperature is an explicit, unqualified proxy.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import openpyxl

from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties


def observations(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = []
    for sheet in workbook:
        # Use only calm, four-millimetre conditions. Crossflow and other nozzle
        # geometries are not interchangeable replicas of this calibration.
        if "W=0" not in sheet.title.replace(" ", ""):
            continue
        for index, values in enumerate(sheet.iter_rows(values_only=True), 1):
            if len(values) < 10:
                continue
            ambient, temperature, flow, overpressure, diameter, _, position = values[3:10]
            if not all(isinstance(v, (int, float)) and math.isfinite(v)
                       for v in (ambient, temperature, flow, overpressure, diameter, position)):
                continue
            if diameter != 4 or not (800 < ambient < 1200 and -30 < temperature < 60):
                raise ValueError(f"Unresolved source units/header mapping: {sheet.title}:{index}")
            if flow <= 0 or overpressure <= 0:
                raise ValueError("Measured positive release conditions are required")
            rows.append({"sheet": sheet.title, "source_row": index,
                         "ambient_pressure_pa": float(ambient)*100.,
                         "ambient_temperature_k": float(temperature)+273.15,
                         "upstream_pressure_pa": float(overpressure)*1e5+float(ambient)*100.,
                         "diameter_m": float(diameter)*1e-3,
                         "measured_mass_flow_kg_s": float(flow)*1e-3})
    workbook.close()
    if not rows:
        raise ValueError("No admissible calm source rows found")
    return rows


def metrics(observed, predicted):
    error = predicted-observed
    relative = error/observed
    return {"scan_rows": len(observed), "rmse_kg_s": float(np.sqrt(np.mean(error**2))),
            "mae_kg_s": float(np.mean(abs(error))), "bias_kg_s": float(np.mean(error)),
            "mean_absolute_relative_error": float(np.mean(abs(relative))),
            "maximum_absolute_relative_error": float(np.max(abs(relative)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path,
                        default=Path("data/raw/mechanical-ventilation/4668554"))
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/physical-validation-20261102/nozzle-validation.json"))
    args = parser.parse_args()
    paths = [args.raw / ("HTE2440PS00" + str(number) + "MIXED_300321.xlsx")
             for number in (3, 4)]
    properties = CoolPropProperties("Hydrogen")
    nozzle = HomogeneousIsentropicNozzle(properties)
    groups = []
    for path in paths:
        rows = observations(path)
        observed, ideal = [], []
        for row in rows:
            state = properties.state_pt(row["upstream_pressure_pa"], row["ambient_temperature_k"])
            opening = NozzleOpening("measured-four-mm", math.pi*row["diameter_m"]**2/4.,
                                   1., "reported-nozzle-diameter")
            result = nozzle.solve(state, back_pressure_pa=row["ambient_pressure_pa"], opening=opening)
            observed.append(row["measured_mass_flow_kg_s"])
            ideal.append(result.mass_flow_kg_s)
        groups.append((rows, np.array(observed), np.array(ideal)))
    train_rows, train, train_ideal = groups[0]
    test_rows, test, test_ideal = groups[1]
    coefficient = float(train_ideal @ train / (train_ideal @ train_ideal))
    if not 0 < coefficient <= 1:
        raise ValueError("Calibration has no admissible discharge coefficient in (0,1]")
    # Discharge coefficient is multiplicative in the existing nozzle. No new
    # flow solver or replacement property law is introduced for this exercise.
    predictions = coefficient*test_ideal
    report = {
        "source": "doi:10.5281/zenodo.4668554", "authors": ["Joachim Grune", "Karsten Sempert"],
        "license": "CC-BY-4.0", "model": "HomogeneousIsentropicNozzle",
        "status": "conditional_operating_condition_holdout", "validation_qualified": False,
        "protocol": {"calibration": "all calm four-mm nominal one-g/s scan rows",
                     "held_out": "all calm four-mm nominal five-g/s scan rows",
                     "parameter": "single fixed multiplicative discharge coefficient",
                     "pressure_mapping": "reported release overpressure plus measured ambient pressure",
                     "temperature_mapping": "measured ambient used as unqualified gas-temperature proxy",
                     "independent_experiment_count_established": False},
        "calibrated_discharge_coefficient": coefficient,
        "calibration_metrics": metrics(train, coefficient*train_ideal),
        "held_out_metrics": metrics(test, predictions),
        "held_out_by_sheet": {
            sheet: metrics(test[[r["sheet"] == sheet for r in test_rows]],
                           predictions[[r["sheet"] == sheet for r in test_rows]])
            for sheet in sorted({r["sheet"] for r in test_rows})},
        "calibration_sheets": sorted({r["sheet"] for r in train_rows}),
        "limitations": ["Gas temperature at nozzle is not provided; ambient is only a proxy.",
                        "Scan rows share operating conditions and are not independent experimental replicates.",
                        "Pressure/temperature sensor uncertainty and pressure-tap-to-nozzle losses are unresolved.",
                        "No accepted accuracy threshold or full release-model qualification is inferred."],
        "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "property_reference": properties.basis.reference_id,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"coefficient": coefficient, "held_out": report["held_out_metrics"]}))


if __name__ == "__main__":
    main()
