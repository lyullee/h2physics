"""Inspect pinned raw CSV structure without running deposited code or a model."""

import argparse
import csv
import hashlib
import io
from pathlib import Path
from zipfile import ZipFile

ARCHIVE_SHA256 = "40c16cca5099e2c69dc44aceb43300854307b3a6c8351c43013afc9967e60dc6"
PREFIX = "submission_package ZENODO_MINIMAL_FINAL/01_raw_data/"


def inspect(path):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Use the exact acquired latest-version archive")
    rows = []
    with ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member names are not admitted")
        for member in archive.infolist():
            if not member.filename.startswith(PREFIX) or not member.filename.endswith(".csv"):
                continue
            if member.file_size > 16_000_000:
                raise ValueError("Raw CSV exceeds this bounded structural inspection")
            raw = archive.read(member)
            reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            header = next(reader)
            if not header or len(header) != len(set(header)):
                raise ValueError("CSV needs unique nonempty column names")
            count, widths, blanks = 0, set(), [0]*len(header)
            for record in reader:
                count += 1
                widths.add(len(record))
                if len(record) == len(header):
                    for index, cell in enumerate(record):
                        blanks[index] += int(not cell.strip())
            relative = member.filename.removeprefix(PREFIX)
            scope = ("literature-derived; third-party reuse not admitted" if relative.startswith("literature/")
                     else "source measurements/configuration candidate; file-level rights review open")
            rows.append((relative, len(raw), hashlib.sha256(raw).hexdigest(), count,
                         tuple(sorted(widths)), tuple(header), tuple(blanks), scope))
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=root/"data/raw/geological-adsorption/zenodo-22305898/submission_package.zip")
    parser.add_argument("--report", type=Path, default=root/"research/geological_raw_schema.md")
    args = parser.parse_args()
    rows = inspect(args.archive)
    lines = ["# Geological adsorption raw CSV structure", "",
             "Source DOI:10.5281/zenodo.22305898; attribution and CC BY4.0 record are retained in "
             "research/data/geological-adsorption-2026-09.toml.", "",
             f"Pinned archive SHA-256:`{ARCHIVE_SHA256}`.", "",
             "Read-only structural inspection of the acquired archive: names, hashes, columns, "
             "record widths and blank-cell counts. No raw numerical observations or deposited prose/code "
             "are reproduced here. No fitting, EOS, logger averaging, mechanism or model ran.", "",
             "Literature-derived records remain outside admitted host reuse. Other records are candidates, "
             "not an assertion of third-party rights clearance or independent validation.", "",
             "| Raw CSV member | Bytes | Rows | Row widths | SHA-256 |",
             "|---|---:|---:|---|---|"]
    for name, size, digest, count, widths, _header, _blanks, _scope in rows:
        lines.append(f"| `{name}` | {size} | {count} | {widths} | `{digest}` |")
    for name, _size, _digest, _count, _widths, header, blanks, scope in rows:
        lines += ["", f"## `{name}`", "", scope+".", "",
                  "| Column | Empty source fields |", "|---|---:|"]
        lines += [f"| `{column}` | {blank} |" for column, blank in zip(header, blanks, strict=True)]
    lines += ["", "Absolute/excess uptake conversion, calibration fitting, raw logger clocks, linked "
              "COx workbook inputs and uncertainty reproduction remain separate source/model qualification. "
              "An empty calibration observation is not zero or an inferred logger mean.", ""]
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Pinned raw CSV schema: {len(rows)} members; no scientific execution")


if __name__ == "__main__":
    main()
