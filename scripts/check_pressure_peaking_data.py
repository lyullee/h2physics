"""Offline, checksum-pinned all-file audit of acquired USN pressure-peaking data."""

import argparse
import hashlib
import re
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from h2physics.data.pressure_peaking import (
    PROFILE_ID,
    file_sha256,
    load_pressure_concentration,
    load_pressure_mat,
)

ROOT = Path(__file__).resolve().parents[1]
CODE = ("src/h2physics/data/pressure_peaking.py", "scripts/check_pressure_peaking_data.py")


def recorder_summary(recorder, block_rows):
    channels = len(recorder.raw[0]) - 1
    result = {"rows": 0, "invalid": np.zeros(channels, dtype=np.int64),
        "negative": np.zeros(channels, dtype=np.int64), "min": np.full(channels, np.inf),
        "max": np.full(channels, -np.inf), "dt_min": np.inf, "dt_max": -np.inf,
        "first_time": float(recorder.raw[0, 0]), "last_time": float(recorder.raw[-1, 0])}
    values_digest, masks_digest = hashlib.sha256(), hashlib.sha256()
    previous = None
    for block in recorder.iter_blocks(block_rows=block_rows):
        series = block.series
        assert block.source_rows[0] == result["rows"] + 1
        result["rows"] += len(series.time_s)
        result["invalid"] += np.count_nonzero(~series.valid, axis=0)
        result["negative"] += np.count_nonzero(series.values < 0., axis=0)
        for column in range(channels):
            finite = series.values[np.isfinite(series.values[:, column]), column]
            if finite.size:
                result["min"][column] = min(result["min"][column], float(np.min(finite)))
                result["max"][column] = max(result["max"][column], float(np.max(finite)))
        dt = np.diff(series.time_s)
        if previous is not None:
            dt = np.r_[series.time_s[0] - previous, dt]
        if len(dt):
            result["dt_min"] = min(result["dt_min"], float(np.min(dt)))
            result["dt_max"] = max(result["dt_max"], float(np.max(dt)))
        previous = series.time_s[-1]
        values_digest.update(np.asarray(np.column_stack((series.time_s, series.values)),
                                        dtype="<f8").tobytes(order="C"))
        masks_digest.update(series.valid.tobytes(order="C"))
    assert result["rows"] == len(recorder.raw)
    result["values_sha256"] = values_digest.hexdigest()
    result["masks_sha256"] = masks_digest.hexdigest()
    return result


def workbook_summary(source, block_rows):
    result = {"rows": 0, "missing_cells": 0, "invalid_cells": 0, "negative_concentration": 0,
        "invalid_concentration": 0, "clock_violations": 0, "invalid_clock": 0,
        "nonzero_alarm": 0, "repeated_iteration": 0, "concentration_min": np.inf,
        "concentration_max": -np.inf, "first_clock": None, "last_clock": None,
        "issues": Counter()}
    values_digest, masks_digest = hashlib.sha256(), hashlib.sha256()
    previous_iteration = None
    first_row_id = last_row_id = None
    for block in source.iter_blocks(block_rows=block_rows):
        table = block.observations
        if first_row_id is None:
            first_row_id = table.row_ids[0]
        last_row_id = table.row_ids[-1]
        result["rows"] += len(table.values)
        result["missing_cells"] += int(np.count_nonzero(~np.isfinite(table.values)))
        result["invalid_cells"] += int(np.count_nonzero(~table.valid))
        concentration, good = table.column("reported_h2_concentration")
        result["negative_concentration"] += int(np.count_nonzero(concentration < 0.))
        result["invalid_concentration"] += int(np.count_nonzero(~good))
        finite = concentration[np.isfinite(concentration)]
        if finite.size:
            result["concentration_min"] = min(result["concentration_min"], float(np.min(finite)))
            result["concentration_max"] = max(result["concentration_max"], float(np.max(finite)))
        result["invalid_clock"] += int(np.count_nonzero(~table.column("recorder_time_of_day")[1]))
        alarm, good_alarm = table.column("alarm")
        result["nonzero_alarm"] += int(np.count_nonzero(good_alarm & (alarm != 0.)))
        iteration = table.column("iteration")[0]
        repeated = np.isfinite(iteration[:-1]) & (iteration[1:] == iteration[:-1])
        result["repeated_iteration"] += int(np.count_nonzero(repeated))
        if previous_iteration is not None and iteration[0] == previous_iteration:
            result["repeated_iteration"] += 1
        previous_iteration = iteration[-1]
        if result["first_clock"] is None:
            result["first_clock"] = str(block.raw_clock_strings[0])
        result["last_clock"] = str(block.raw_clock_strings[-1])
        for issue in block.issues:
            result["issues"][(issue.code, issue.channel)] += issue.count
            if issue.code.startswith("clock_not_increasing"):
                result["clock_violations"] += issue.count
        values_digest.update(np.asarray(table.values, dtype="<f8").tobytes(order="C"))
        masks_digest.update(table.valid.tobytes(order="C"))
    result.update(first_row_id=first_row_id, last_row_id=last_row_id,
                  values_sha256=values_digest.hexdigest(), masks_sha256=masks_digest.hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mat-block-rows", type=int, default=100_000)
    parser.add_argument("--xlsx-block-rows", type=int, default=2048)
    parser.add_argument("--output", type=Path, default=ROOT / "research/pressure_peaking_data.md")
    args = parser.parse_args()
    code_sha = {name: file_sha256(ROOT / name) for name in CODE}
    receipt_path = ROOT / "research/data/pressure-unignited.toml"
    receipt = tomllib.loads(receipt_path.read_text(encoding="utf-8"))
    if not receipt["rights_permitted"] or receipt["license_id"] != "CC-BY-4.0":
        raise ValueError("This audit requires the reviewed CC-BY-4.0 acquisition receipt")
    files = [item for item in receipt["files"] if item["status"] == "acquired"]
    if (sum(item["name"].endswith(".mat") for item in files),
            sum(item["name"].endswith(".xlsx") for item in files)) != (8, 9):
        raise ValueError("Acquired version-1 coverage changed; review the profile/report scope")
    mat_results, xlsx_results, checksums = [], [], []
    for item in files:
        path = ROOT / "data/raw" / item["relative_path"]
        digest = file_sha256(path)
        if path.stat().st_size != item["size_bytes"] or digest != item["sha256"]:
            raise ValueError(f"Recorded SHA-256/size mismatch: {item['name']}")
        md5 = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as stream:
            for payload in iter(lambda: stream.read(1024 * 1024), b""):
                md5.update(payload)
        if item["publisher_checksum_algorithm"] != "md5" or md5.hexdigest() != item["publisher_checksum"]:
            raise ValueError(f"Publisher checksum mismatch: {item['name']}")
        checksums.append((item["name"], digest))
        suffix = path.suffix.lower()
        if suffix not in {".mat", ".xlsx"}:
            continue
        match = re.fullmatch(r"HTE242USN_?(\d{5})(?:_READ|CONC?|CONT)190621\.(?:mat|xlsx)", path.name)
        if match is None:
            raise ValueError("Unreviewed source experiment filename")
        experiment = f"USN-source-experiment-{match[1]}"
        identity = f"{receipt['doi']}:{path.name}"
        print("auditing", path.name, flush=True)
        if suffix == ".mat":
            run = load_pressure_mat(path, source_id=identity, experiment_id=experiment,
                                    expected_sha256=digest)
            sigma = recorder_summary(run.sigma, args.mat_block_rows)
            gen = recorder_summary(run.gen3i, args.mat_block_rows)
            mat_results.append((path.name, sigma, gen))
            print(" inspected", sigma["rows"], "SIGMA +", gen["rows"], "GEN3i rows", flush=True)
            del run
        else:
            source = load_pressure_concentration(path, source_id=identity, experiment_id=experiment,
                                                 expected_sha256=digest)
            stats = workbook_summary(source, args.xlsx_block_rows)
            stats["device"] = str(source.metadata_values[0])
            stats["factory_device"] = str(source.metadata_values[1])
            stats["identity_conflict"] = source.metadata_values[0] != source.metadata_values[1]
            xlsx_results.append((path.name, stats))
            print(" inspected", stats["rows"], "worksheet rows", flush=True)
    metadata = ROOT / "data/raw/pressure-unignited/1/repository-metadata.json"
    if file_sha256(metadata) != receipt["metadata_sha256"]:
        raise ValueError("Repository metadata differs from the recorded rights evidence")
    totals = {"files_hashed": len(files), "mat_files": len(mat_results), "xlsx_files": len(xlsx_results),
        "sigma_rows": sum(s["rows"] for _, s, _ in mat_results),
        "gen3i_rows": sum(g["rows"] for _, _, g in mat_results),
        "xlsx_rows": sum(s["rows"] for _, s in xlsx_results),
        "negative_flow_rows": sum(int(s["negative"][0]) for _, s, _ in mat_results),
        "negative_meter_pressure_rows": sum(int(s["negative"][1]) for _, s, _ in mat_results),
        "negative_concentration_rows": sum(s["negative_concentration"] for _, s in xlsx_results),
        "xlsx_missing_cells": sum(s["missing_cells"] for _, s in xlsx_results),
        "xlsx_invalid_cells": sum(s["invalid_cells"] for _, s in xlsx_results),
        "xlsx_clock_violations": sum(s["clock_violations"] for _, s in xlsx_results),
        "xlsx_invalid_clock_cells": sum(s["invalid_clock"] for _, s in xlsx_results)}
    lines = ["# USN unignited pressure-peaking data ingestion", "",
        f"Audit completed UTC: {datetime.now(UTC).isoformat()}. Profile: `{PROFILE_ID}`.", "",
        "Source: Agnieszka Lach and Andre Vagner Gaathaug, "
        "[Hydrogen safety: Pressure Peaking Phenomena-unignited releases, version 1]"
        "(https://doi.org/10.23642/usn.17932439.v1), "
        "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). "
        "The acquired receipt and metadata retain the rights evidence and attribution.", "",
        "This offline run recomputed SHA-256, publisher MD5 and size for every acquired attachment, "
        "then consumed every row of all eight acquired MAT exports and nine XLSX exports. "
        "Two listed MAT files (source experiments 00002/00009) remain omitted by the acquisition receipt. "
        "The two DOCX guides were checksum verified; their XML had been inspected for the profile. "
        "Raw and normalized external observations remain excluded from Git/distributions.", "",
        f"Actual totals: `{totals}`.", "",
        "The MAT variables named `dimensions` contain units, while `units` contain channel labels. "
        "SIGMA is seconds, signed g/s and bar at the Coriolis meter/outlet. Only unit scaling is "
        "applied; absolute/gauge pressure, a nozzle state and a physical release direction are unresolved. "
        "Negative flow and meter-pressure values remain present and are counted below. "
        "GEN3i exports time/P1 in seconds/kPa, although the guide identifies column 3 as overpressure. "
        "All four dimension labels and 35 channel labels survive; the unavailable channels are not "
        "reconstructed. Exported P1 is retained as reported pressure with the column conflict in its basis.", "",
        "Recorder clocks are independent per file/matrix/device. Neither matching experiment IDs nor "
        "similar elapsed-clock starts establish synchronization. No baseline subtraction, automatic "
        "time shift, averaging between sensors or negative clipping is performed. Finite MAT values "
        "have numerical validity masks; unresolved reported-pressure bases prevent their automatic use "
        "as absolute/differential model pressures.", "",
        "| MAT source file | SIGMA rows | GEN3i rows | Negative flow | Negative meter pressure | "
        "SIGMA invalid cells | GEN3i invalid cells | Exported P1 min/max (Pa) |",
        "|---|---:|---:|---:|---:|---:|---:|---|"]
    for name, sigma, gen in mat_results:
        lines.append(f"| {name} | {sigma['rows']} | {gen['rows']} | {sigma['negative'][0]} | "
            f"{sigma['negative'][1]} | {sum(sigma['invalid'])} | {sum(gen['invalid'])} | "
            f"{gen['min'][0]:.10g} / {gen['max'][0]:.10g} |")
    lines += ["", "| Source / matrix | First/last time (s) | Minimum/maximum adjacent step (s) | "
        "SI value-stream SHA-256 | Validity-stream SHA-256 |", "|---|---|---|---|---|"]
    for name, sigma, gen in mat_results:
        for matrix, stats in (("SIGMA", sigma), ("GEN3i", gen)):
            lines.append(f"| {name} / {matrix} | {stats['first_time']:.12g} / {stats['last_time']:.12g} | "
                f"{stats['dt_min']:.12g} / {stats['dt_max']:.12g} | `{stats['values_sha256']}` | "
                f"`{stats['masks_sha256']}` |")
    lines += ["", "XLSX row 1/2 device/calibration metadata and literal row-3 headers are retained. "
        "The two documented Celsius glyph variants are recognized without changing the stored header. "
        "All 17 columns and each original worksheet row survive. Column B contains local time-of-day "
        "strings, despite the guide describing seconds; conversion preserves seconds since local midnight, "
        "without an inferred date/timezone or midnight unwrapping. Iteration numbers are not row identities. "
        "Output percent is scaled by 0.01 and retained as reported point-sensor concentration; "
        "its volume/mole convention, sensor location and response still need qualification. "
        "Negative/over-100-percent values are present but masked for physical concentration use. "
        "Missing cells are NaN/masked, alarms remain source codes, and the AH pressure-like column "
        "retains unresolved semantics. Pt100/Tsens are separate instrument temperatures.", "",
        "| XLSX source file | Rows | Missing numeric cells | Invalid cells | Negative output | "
        "Invalid output | Clock violations | Invalid clock | Repeated iteration pairs | Nonzero alarm | Device / factory ID |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name, stats in xlsx_results:
        lines.append(f"| {name} | {stats['rows']} | {stats['missing_cells']} | {stats['invalid_cells']} | "
            f"{stats['negative_concentration']} | {stats['invalid_concentration']} | "
            f"{stats['clock_violations']} | {stats['invalid_clock']} | {stats['repeated_iteration']} | "
            f"{stats['nonzero_alarm']} | {stats['device']} / {stats['factory_device']} |")
    lines += ["", "| XLSX source file | First/last raw clock | Reported fraction min/max | "
        "SI value-stream SHA-256 | Validity-stream SHA-256 |", "|---|---|---|---|---|"]
    for name, stats in xlsx_results:
        lines.append(f"| {name} | {stats['first_clock']} / {stats['last_clock']} | "
            f"{stats['concentration_min']:.10g} / {stats['concentration_max']:.10g} | "
            f"`{stats['values_sha256']}` | `{stats['masks_sha256']}` |")
    lines += ["", "Observed XLSX issue counts (source file / channel / reason):", ""]
    for name, stats in xlsx_results:
        for (code, channel), count in sorted(stats["issues"].items()):
            lines.append(f"- {name} / {channel} / `{code}`: {count}.")
        if stats["identity_conflict"]:
            lines.append(f"- {name}: configured device ID differs from factory ID; no reassignment applied.")
        lines.append(f"- {name}: first/last row IDs `{stats['first_row_id']}` / `{stats['last_row_id']}`.")
    lines += ["", "Checksum-pinned original attachments (all SHA-256/MD5/size checks passed):", "",
        "| Source file | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | `{digest}` |" for name, digest in checksums]
    lines += ["", f"Acquisition receipt SHA-256: `{file_sha256(receipt_path)}`. "
        f"Repository metadata SHA-256: `{receipt['metadata_sha256']}`.", "",
        "SI value digests concatenate canonical little-endian float64 rows (MAT: time then channels; "
        "XLSX: all 17 normalized columns), while validity digests concatenate row-major boolean bytes. "
        "They are independent of block size for the same parsed values/masks; meanings are pinned by "
        "the source/profile/code hashes. No normalized observation file is released.", "",
        "Host code SHA-256:", ""]
    lines += [f"- `{name}`: `{digest}`." for name, digest in code_sha.items()]
    lines += ["", "This is an ingestion/schema/numerical-data audit, not measured model validation. "
        "Required qualification includes apparatus geometry, enclosure/vent boundaries, sensor locations "
        "and calibration/response, pressure reference, the GEN3i column discrepancy, and evidence-bearing "
        "recorder/event alignment. Source experiment labels do not establish independent trials or "
        "a well-mixed room concentration. No measured validation target is claimed."]
    if any(file_sha256(ROOT / name) != digest for name, digest in code_sha.items()):
        raise ValueError("Ingestion/audit code changed during this run; report not finalized")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(totals, flush=True)
    print("wrote", args.output.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
