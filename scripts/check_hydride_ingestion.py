"""Ingest only the declared shell-temperature channels of acquired AB2 experiments."""

from pathlib import Path

import numpy as np
from openpyxl import load_workbook

from h2physics.core import Origin
from h2physics.data.excel import ExcelClock, load_excel_sheet
from h2physics.data.loaders import Column


def main():
    root = Path(__file__).resolve().parents[1]
    lines = ["# AB2 shell-temperature ingestion", "",
             "Source: Ramadhan, Suwarno and Hijriawan (2026), "
             "[dataset v1](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0.", "",
             "Each worksheet has its own elapsed clock, reconstructed from recorded datetimes. "
             "The first datetime is the explicit local origin; no shared timezone or cross-run "
             "alignment is inferred. Five shell thermocouples are declared in degrees Celsius "
             "by the repository description and converted to kelvin. Cached derived mass, "
             "moles and volume summaries are not independent measurements. Pressure unit/basis "
             "and MFC reference conditions remain unresolved; those channels are excluded.", "",
             "These are shell observations, not spatially uniform bed temperatures. "
             "Ingestion does not validate the reduced hydride model or identify its parameters.", "",
             "| Workbook / worksheet | Temperature records | Duration s | Missing temperature cells | Min K | Max K | Clock status |",
             "|---|---:|---:|---:|---:|---:|---|"]
    counts = dict(sheets=0, loaded=0, records=0, failed=0)
    for path in sorted((root / "data/raw/ab2-hydride-tank").rglob("*.xlsx")):
        workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        origins = {}
        try:
            for sheet in workbook:
                row = next(sheet.iter_rows(min_row=2, max_row=2, values_only=True))
                origins[sheet.title] = row[1]
        finally:
            workbook.close()
        for sheet, start in origins.items():
            counts["sheets"] += 1
            try:
                loaded = load_excel_sheet(path, sheet,
                    columns=tuple(Column(f"TC{i}", f"shell_{i}", "temperature", "degC") for i in range(1, 6)),
                    clock=ExcelClock("Date", "datetime", datetime_origin=start),
                    clock_id=f"ab2/{path.stem}/{sheet}/local-relative",
                    origin=Origin.RECONSTRUCTED, source_id="10.17632/8km9z62tct.1",
                    omit_missing_time=True)
                series = loaded.series
                values = series.values[series.valid]
                counts["loaded"] += 1
                counts["records"] += len(series.time_s)
                lines.append(f"| {path.name} / {sheet} | {len(series.time_s)} | "
                             f"{series.time_s[-1]-series.time_s[0]:g} | "
                             f"{loaded.report.invalid_measurement_values} | {np.min(values):g} | "
                             f"{np.max(values):g} | strictly increasing; "
                             f"{loaded.report.omitted_missing_time_rows} missing-time rows omitted |")
            except (ValueError, TypeError) as error:
                counts["failed"] += 1
                lines.append(f"| {path.name} / {sheet} | — | — | — | — | — | REJECTED: {error} |")
    lines += ["", "No sorting, interpolation, repeated-time averaging or pressure inference was performed.",
              "", f"Summary: {counts}."]
    (root / "research/hydride_ingestion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(counts)


if __name__ == "__main__":
    main()
