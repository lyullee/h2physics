"""Offline whole-workbook qualification; derived summaries are not validation data."""

import hashlib
import re
import tomllib
from datetime import datetime
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

from h2physics.data.hydride_tank import hydride_summary_cells, iter_hydride_tank_blocks
from h2physics.data.pressure_peaking import file_sha256


def main():
    root = Path(__file__).resolve().parents[1]
    fingerprints = {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in ("src/h2physics/data/hydride_tank.py", "scripts/check_hydride_tank_data.py")}
    receipt = tomllib.loads((root / "research/data/ab2-hydride-tank.toml").read_text("utf-8"))
    lines = ["# AB2 complete-channel qualification", "",
        "Ramadhan, Suwarno and Hijriawan, "
        "[version 1](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0. "
        "Three acquired workbooks are checked against their acquisition receipts. "
        "No external observations or literal source formulas are reproduced here.", "",
        "All source rows survive, including rows with missing or reversed datetimes. "
        "A local elapsed clock is reconstructed only from each sheet's first datetime. "
        "Raw Date/Time/counter/flow/pressure/temperature/volume fields remain accessible. "
        "Formula caches are never executed. Flow is reference volume, not mass; the MFC "
        "reference P/T and pressure unit/basis remain unqualified. Shell temperatures "
        "are not bed temperatures. Derived totals do not independently validate sorption.", "",
        "| Workbook / sheet | All source rows | Missing datetime | Nonincreasing datetime edges | "
        "Missing/nonphysical shell cells | Negative flow cells | Negative pressure cells | "
        "Max cached-vs-reconstructed time difference s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    summaries, total_rows, sheets = [], 0, 0
    for record in receipt["files"]:
        path = root / "data/raw" / record["relative_path"]
        if path.stat().st_size != record["size_bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"Acquisition receipt mismatch: {path.name}")
        workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        try:
            origins = {sheet.title: next(sheet.iter_rows(min_row=2, max_row=2,
                max_col=2, values_only=True))[1] for sheet in workbook}
        finally:
            workbook.close()
        for sheet, start in origins.items():
            if not isinstance(start, datetime):
                raise ValueError("Source local datetime origin is unavailable")
            summary = hydride_summary_cells(path, sheet)
            target = None
            if summary and summary[0].formula:
                match = re.fullmatch(r"=L(\d+)", summary[0].formula)
                if match:
                    target = int(match[1])
            target_value, final_value, final_timed_row = None, None, None
            counts = dict(rows=0, missing_time=0, backwards=0, invalid_shell=0,
                          negative_flow=0, negative_pressure=0)
            previous_time, max_time_error = None, 0.
            for block in iter_hydride_tank_blocks(path, sheet, source_id=receipt["doi"],
                    experiment_id=f"{path.stem}/{sheet}", clock_id=f"ab2/{path.stem}/{sheet}/local",
                    datetime_origin=start, expected_sha256=record["sha256"]):
                table = block.observations
                times, valid_time = table.column("datetime_elapsed")
                cached, valid_cache = table.column("exported_elapsed")
                counts["rows"] += len(times)
                counts["missing_time"] += int(np.count_nonzero(~valid_time))
                for index, source_row in enumerate(block.source_rows):
                    if valid_time[index]:
                        if previous_time is not None and times[index] <= previous_time:
                            counts["backwards"] += 1
                        previous_time, final_timed_row = times[index], source_row
                    if source_row == target:
                        target_value = table.column("exported_total_volume")[0][index]
                both = valid_time & valid_cache
                if np.any(both):
                    max_time_error = max(max_time_error, float(np.max(np.abs(times[both]-cached[both]))))
                counts["invalid_shell"] += int(np.count_nonzero(~table.valid[:, 5:10]))
                for column, key in ((3, "negative_flow"), (4, "negative_pressure")):
                    counts[key] += int(np.count_nonzero(table.valid[:, column] & (table.values[:, column] < 0)))
                totals, valid_totals = table.column("exported_total_volume")
                if np.any(valid_totals):
                    final_value = float(totals[np.flatnonzero(valid_totals)[-1]])
            sheets += 1
            total_rows += counts["rows"]
            lines.append(f"| {path.name} / {sheet} | {counts['rows']} | {counts['missing_time']} | "
                f"{counts['backwards']} | {counts['invalid_shell']} | {counts['negative_flow']} | "
                f"{counts['negative_pressure']} | {max_time_error:.9g} |")
            if summary:
                values = [cell.cached_value for cell in summary]
                summaries.append(f"- {path.name} / {sheet}: summary selects source row {target}; "
                    f"last datetime row {final_timed_row}; selected/final cached reference volume "
                    f"{target_value!r}/{final_value!r} m3_ref. Four derived summary caches "
                    f"available: {sum(isinstance(x, (int, float)) for x in values)}/{len(values)}.")
    lines += ["", "## Summary selection audit", "", *summaries, "",
        "The summary formula's ideal-gas calculation uses 293.15 K and 101.31 kPa. "
        "This documents the author's calculation convention; it does not establish the "
        "MFC calibration reference state, the pressure-channel unit, free gas volume, "
        "bed temperature or independent absorbed mass. A desorption sheet also retains "
        "an absorption-labelled summary; run direction is therefore not inferred from "
        "that label. No fitted material parameters or experimental model acceptance is claimed.", "",
        f"Full scan: {sheets} sheets, {total_rows} source rows; all three file receipts matched.",
        "", "## Executed source fingerprints", ""]
    for relative, digest in fingerprints.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Executed source changed during the qualification scan; replay required")
        lines.append(f"- `{relative}`: `{digest}`")
    (root / "research/hydride_tank_data.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Qualified {sheets} sheets / {total_rows} source rows; no mass/pressure qualification inferred")


if __name__ == "__main__":
    main()
