"""Offline all-member/29-experiment MHC audit; cached values only, no fitting."""

import argparse
import hashlib
import json
import math
import time
import tomllib
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import numpy as np

from h2physics.data.hydride_compressor import (
    PROFILE_ID,
    HydrideCompressorArchive,
    HydrideCompressorWorkbook,
)
from h2physics.data.pressure_peaking import file_sha256

SOURCE_FILES = ("src/h2physics/data/hydride_compressor.py",
                "tests/test_hydride_compressor_data.py",
                "scripts/check_hydride_compressor_data.py")


def _fingerprints(root):
    result = {}
    for relative in SOURCE_FILES:
        payload = (root / relative).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed source must use LF line endings")
        result[relative] = hashlib.sha256(payload).hexdigest()
    return result


def _recorder_stats():
    return dict(grid_rows=0, populated_rows=0, empty_rows=0, clocked_rows=0,
                active_missing_clock=0, nonincreasing_clock_edges=0, numeric_cells=0,
                valid_cells=0, invalid_reasons=Counter(), negative_pressure=0,
                negative_flow=0, raw_string_channels=0, previous_clock=None,
                clock_field_types=Counter(),
                first_clock=None, last_clock=None, first_source_row=None, last_source_row=None)


def _update(stats, block):
    table = block.observations
    stats["grid_rows"] += len(table.values)
    active = np.array([any(value is not None for value in row) for row in block.raw_cells])
    stats["populated_rows"] += int(np.count_nonzero(active))
    stats["empty_rows"] += int(np.count_nonzero(~active))
    stats["clocked_rows"] += int(np.count_nonzero(table.valid[:, 0]))
    stats["active_missing_clock"] += int(np.count_nonzero(active & ~table.valid[:, 0]))
    stats["numeric_cells"] += int(np.count_nonzero(np.isfinite(table.values[:, 1:])))
    stats["valid_cells"] += int(np.count_nonzero(table.valid[:, 1:]))
    stats["first_source_row"] = stats["first_source_row"] or block.source_rows[0]
    stats["last_source_row"] = block.source_rows[-1]
    for value in table.values[table.valid[:, 0], 0]:
        if stats["previous_clock"] is not None and value <= stats["previous_clock"]:
            stats["nonincreasing_clock_edges"] += 1
        if stats["first_clock"] is None:
            stats["first_clock"] = float(value)
        stats["previous_clock"] = stats["last_clock"] = float(value)
    for index, variable in enumerate(table.variables[1:], 1):
        valid_negative = table.valid[:, index] & (table.values[:, index] < 0)
        if variable.quantity == "reported_pressure":
            stats["negative_pressure"] += int(np.count_nonzero(valid_negative))
        elif variable.quantity in ("volume_flow", "reference_volume_flow"):
            stats["negative_flow"] += int(np.count_nonzero(valid_negative))
    clock_width = len(block.schema.clock_columns)
    stats["clock_field_types"].update("+".join(type(value).__name__ for value in row[:clock_width])
        for row, populated in zip(block.raw_cells, active, strict=True) if populated)
    stats["raw_string_channels"] += sum(isinstance(value, str)
        for row in block.raw_cells for value in row[clock_width:])
    stats["invalid_reasons"].update(reason for row in block.invalid_reasons for reason in row if reason)


def audit_experiment(payload, number, archive_sha, member, digest, limits, case):
    """One immutable member snapshot per worker; recorder clocks stay separate."""
    with HydrideCompressorWorkbook(payload, experiment=number, archive_sha256=archive_sha,
            member_name=member, member_sha256=digest, limits=limits) as workbook:
        result = dict(experiment=number, member=workbook.member_name,
            member_sha256=workbook.member_sha256, gas_context=workbook.gas_context,
            overview=[asdict(cell) for cell in case],
            notes=[asdict(cell) for cell in workbook.notes()],
            workbook_expanded_bytes=sum(info.file_size for info in workbook.inventory),
            sheets=[asdict(audit) for audit in workbook.audit()], profiles=[])
        for sheet in (workbook.raw_sheet, *workbook.selected_sheets):
            schemas = workbook.schemas(sheet)
            stats = {schema.identity: _recorder_stats() for schema in schemas}
            digests = {schema.identity: hashlib.sha256() for schema in schemas}
            offsets = {}
            for blocks in workbook.iter_blocks(sheet, datetime_origin=datetime(1970, 1, 1)):
                labview = blocks[0].observations
                for block in blocks:
                    _update(stats[block.schema.identity], block)
                    profile_digest = digests[block.schema.identity]
                    for source_row, values, valid in zip(block.source_rows,
                            block.observations.values, block.observations.valid, strict=True):
                        profile_digest.update(source_row.to_bytes(8, "big"))
                        profile_digest.update(np.asarray(values, dtype="<f8").tobytes())
                        profile_digest.update(valid.tobytes())
                    if block is blocks[0] or block.schema.clock_kind != "source-local-calendar":
                        continue
                    both = labview.valid[:, 0] & block.observations.valid[:, 0]
                    delta = block.observations.values[both, 0] - labview.values[both, 0]
                    if len(delta):
                        low, high = offsets.get(block.schema.identity, (math.inf, -math.inf))
                        offsets[block.schema.identity] = (min(low, float(delta.min())), max(high, float(delta.max())))
            for schema in schemas:
                stats[schema.identity].pop("previous_clock")
                stats[schema.identity]["invalid_reasons"] = dict(stats[schema.identity]["invalid_reasons"])
                result["profiles"].append(dict(sheet=sheet, schema=asdict(schema),
                    statistics=stats[schema.identity],
                    values_masks_rows_sha256=digests[schema.identity].hexdigest(),
                    same_grid_row_calendar_delta_to_labview_s=offsets.get(schema.identity)))
        return result


def _write_json(path, report):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
                         encoding="utf-8", newline="\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2,
                        help="At most two bounded experiment snapshots concurrently")
    parser.add_argument("--resume", action="store_true",
                        help="Reuse matching source/member/hash checkpoints after interruption")
    options = parser.parse_args()
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    destination = root / "data/processed/hydride-compressor/v1.2/profile-audit.json"
    checkpoint = destination.with_name("profile-audit.partial.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = _fingerprints(root)
    receipt = tomllib.loads((root / "research/data/hydride-compressor.toml").read_text("utf-8"))
    record = receipt["files"][0]
    path = root / "data/raw" / record["relative_path"]
    metadata = path.parent / "repository-metadata.json"
    if file_sha256(metadata) != receipt["metadata_sha256"]:
        raise ValueError("Repository metadata receipt mismatch")
    report = dict(profile=PROFILE_ID, source=receipt["doi"], license=receipt["license_id"],
                  metadata_sha256=receipt["metadata_sha256"], source_begin=fingerprints,
                  limits=None, members=[], experiments=[], audit_workers=options.workers,
                  resumed_segments=0)
    preceding_elapsed = 0.
    with path.open("rb") as stream:
        publisher_checksum = hashlib.file_digest(stream, record["publisher_checksum_algorithm"]).hexdigest()
    if publisher_checksum != record["publisher_checksum"]:
        raise ValueError("Publisher checksum mismatch")
    report["publisher_checksum"] = f"{record['publisher_checksum_algorithm']}:{publisher_checksum}"
    with HydrideCompressorArchive(path, expected_sha256=record["sha256"],
                                  expected_bytes=record["size_bytes"]) as archive:
        if tuple(sorted(archive.experiments)) != tuple(range(1, 30)):
            raise ValueError("The acquisition does not contain the reviewed 29 experiments")
        report["limits"] = asdict(archive.limits)
        report["archive_sha256"] = archive.sha256
        report["archive_expanded_bytes"] = sum(info.file_size for info in archive.inventory)
        report["archive_compressed_bytes"] = path.stat().st_size
        for info in archive.inventory:
            if info.is_dir():
                continue
            payload, digest = archive.read_member(info.filename)
            report["members"].append(dict(member=info.filename, bytes=len(payload),
                compressed_bytes=info.compress_size, sha256=digest, crc32=f"{info.CRC:08x}"))
        overview_name, overview_sha, overview_fields, cases = archive.overview()
        if set(cases) != set(archive.experiments):
            raise ValueError("Source overview and experiment members disagree")
        report["overview"] = dict(member=overview_name, sha256=overview_sha,
                                  fields=[asdict(cell) for cell in overview_fields])
        if options.resume and checkpoint.exists():
            previous = json.loads(checkpoint.read_text("utf-8"))
            identities = {item["member"]: item["sha256"] for item in report["members"]}
            results = previous.get("experiments", [])
            if (previous.get("source_begin") != fingerprints
                    or previous.get("archive_sha256") != archive.sha256
                    or previous.get("metadata_sha256") != receipt["metadata_sha256"]
                    or len({item["experiment"] for item in results}) != len(results)
                    or any(item["experiment"] not in archive.experiments
                        or archive.experiments[item["experiment"]] != item["member"]
                        or identities.get(item["member"]) != item["member_sha256"] for item in results)):
                raise ValueError("Checkpoint source/member identities differ; fresh audit required")
            report["experiments"] = results
            preceding_elapsed = previous.get("elapsed_seconds", 0.)
            report["resumed_segments"] = previous.get("resumed_segments", 0) + 1
            print(f"Resuming {len(results)} verified experiment checkpoints", flush=True)
        completed = {item["experiment"] for item in report["experiments"]}
        numbers = iter(number for number in sorted(archive.experiments) if number not in completed)
        with ProcessPoolExecutor(max_workers=options.workers) as pool:
            pending = {}

            def submit_next():
                number = next(numbers, None)
                if number is not None:
                    member = archive.experiments[number]
                    payload, digest = archive.read_member(member)
                    pending[pool.submit(audit_experiment, payload, number, archive.sha256,
                        member, digest, archive.limits, cases[number])] = number

            for _ in range(options.workers):
                submit_next()
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    number = pending.pop(future)
                    result = future.result()
                    report["experiments"].append(result)
                    report["experiments"].sort(key=lambda item: item["experiment"])
                    report["elapsed_seconds"] = preceding_elapsed + time.perf_counter() - started
                    _write_json(checkpoint, report)
                    print(f"Experiment {number}/29: {len(result['sheets'])} sheets, "
                        f"{sum(s['numeric_cells'] for s in result['sheets'])} stored numeric cells; "
                        f"{len(report['experiments'])}/29 durable checkpoints", flush=True)
                    submit_next()
    report["source_end"] = _fingerprints(root)
    if report["source_end"] != fingerprints:
        raise ValueError("Executed host/test/script changed; replay required")
    report["elapsed_seconds"] = preceding_elapsed + time.perf_counter() - started
    _write_json(destination, report)
    write_summary(root, report)
    print(f"Completed all 29 experiments in {report['elapsed_seconds']:.2f}s; "
          "source/schema audit only, no model validation", flush=True)


def write_summary(root, report):
    experiments = report["experiments"]
    sheets = [sheet for experiment in experiments for sheet in experiment["sheets"]]
    profiles = [profile for experiment in experiments for profile in experiment["profiles"]]
    totals = {key: sum(sheet[key] for sheet in sheets) for key in (
        "stored_rows", "populated_rows", "numeric_rows", "numeric_cells", "formula_cells",
        "missing_formula_caches", "error_cells", "nonfinite_numeric_cells")}
    profile_totals = {key: sum(profile["statistics"][key] for profile in profiles) for key in (
        "grid_rows", "populated_rows", "empty_rows", "clocked_rows", "active_missing_clock",
        "nonincreasing_clock_edges", "numeric_cells", "valid_cells", "negative_pressure",
        "negative_flow", "raw_string_channels")}
    lines = ["# MHC v1.2 complete archive qualification", "",
        "Lukas Fleming, [Experimental Dataset for a Two-Stage Metal Hydride Hydrogen Compressor, "
        "v1.2](https://doi.org/10.5281/zenodo.19036733), CC BY 4.0. The acquired "
        "repository metadata, README, license, overview, actual workbook schemas and source "
        "notes establish this profile. No publication prose, experiment values, source formulas, "
        "figures, code or source tables are reproduced here.", "",
        f"The offline local scan completed in {report['elapsed_seconds']:.2f} s. "
        f"All {len(report['members'])} file members passed CRC and SHA-256 snapshotting; "
        f"outer size {report['archive_compressed_bytes']} bytes, expanded directory "
        f"{report['archive_expanded_bytes']} bytes. All 29 experiment workbooks and "
        f"their {len(sheets)} worksheets were inspected. The source overview independently "
        "contains the same 29 experiment numbers. The publisher MD5 and receipt metadata "
        "hash also matched. No member was extracted or executed.", "",
        f"Audit concurrency was bounded to {report['audit_workers']} workbooks. Durable per-case "
        f"checkpoints were used; resumed segments: {report['resumed_segments']}. Elapsed time "
        "sums the recorded execution segments if a matching checkpoint is resumed.", "",
        "## What the counts mean", "",
        "XML numeric counts include stored dates, metadata, copied values and derived formula "
        "caches. Worksheet and export-grid row counts include padding. Repeated raw/selected "
        "exports are one physical experiment, so none of these counts proves independent "
        "measurement count, independent validation or experimental model acceptance.", "",
        *(f"- All-worksheet `{key}`: {value}." for key, value in totals.items()), "",
        *(f"- Profile `{key}`: {value}." for key, value in profile_totals.items()), "",
        "## Complete experiment storage audit", "",
        "| Experiment | Sheets | Stored rows | Numeric rows | Numeric cells | Formula cells | Missing formula cache | Error cells | Profile groups |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for experiment in experiments:
        ss = experiment["sheets"]
        counts = [sum(s[key] for s in ss) for key in ("stored_rows", "numeric_rows", "numeric_cells",
                  "formula_cells", "missing_formula_caches", "error_cells")]
        lines.append(f"| {experiment['experiment']} | {len(ss)} | " + " | ".join(map(str, counts))
                     + f" | {len(experiment['profiles'])} |")
    lines += ["", "## Recorder and schema issues", "",
        "Independent calendar and elapsed/time-of-day clocks remain separate. Clock missingness, "
        "duplicate/backward edges, first/last source rows, headers, unit evidence cells, sensor "
        "hardware/alias identities, profile array/mask/row fingerprints and same-grid-row clock "
        "differences are recorded in the ignored local audit. Those differences are diagnostics, "
        "not synchronization estimates or accepted clock mappings.", "",
        "- Experiment 1 is an argon thermal case; its declared defective Picolog T-2_1 is masked "
        "with the source note identity while retaining its cache. Experiment 2 is a non-hydrogen "
        "thermal case with unresolved fill gas; its separate AV thermometer calibration export "
        "has a different date and retains its own clock/group.",
        "- Experiments 6 and 7 use a loading-station export with a time-of-day field and Flow-3 "
        "strings containing commas. Its date and relationship to Labview are unresolved. "
        "Those strings remain raw and invalid as numeric observations; no decimal/thousands "
        "interpretation is guessed. Selected-cycle copies omit that export clock. Missing "
        "channel units remain unresolved instead of being filled from a generic template.",
        "- Typed calendar fields, ISO strings (experiment 3), day.month.year recorder strings "
        "(experiment 22), unformatted Excel serial dates/datetimes (including experiment 8 "
        "Labview and selected exports in experiments 4/19/22), and fractional-day Time fields "
        "decode against the workbook's declared Excel epoch and Date/Time headers. Raw "
        "representations and epoch evidence remain available; no recorder shift is applied. "
        "Raw headers begin at different source rows in experiments "
        "3 and 18. Experiment 4 has two selected cycles with the source nl/min spelling. "
        "Experiments 6 and 7 have distinct alias/unit layouts. Literal aliases, including "
        "unassigned raw Graphtec channels, are retained.",
        "- Pressure bar is scaled to Pa without assigning absolute/gauge basis. Barg remains "
        "reported gauge pressure without an atmospheric offset. HTF l/min is volume flow; "
        "ln/min and nl/min are reported reference volume flow with unresolved reference P/T, "
        "never mass flow. Temperatures use K but keep their source sensor identities; no "
        "shell-to-bed or spatial averaging operator is supplied.",
        "- PCI workbook records, material parameters and experiment mass/heat/efficiency summaries "
        "are outside the independent logger-measurement profile. Their presence is not independent "
        "validation evidence. Protocol/source notes include incomplete histories and possible "
        "unmeasured release paths; a compressor inventory/energy fit is not qualified here.", "",
        "## Source member fingerprints", "",
        f"- Outer archive SHA-256: `{report['archive_sha256']}`.",
        f"- Recomputed publisher checksum: `{report['publisher_checksum']}`.",
        f"- Repository metadata SHA-256: `{report['metadata_sha256']}`.", "",
        "| Member (root prefix omitted) | Bytes | SHA-256 |", "|---|---:|---|"]
    for member in report["members"]:
        short = member["member"].split("/", 1)[-1]
        lines.append(f"| {short} | {member['bytes']} | `{member['sha256']}` |")
    lines += ["", "## Executed source fingerprints", "",
        "Begin and end hashes matched; every listed source used LF endings.", ""]
    for relative, digest in report["source_begin"].items():
        lines.append(f"- `{relative}`: `{digest}`")
    lines += ["", "The complete machine-readable audit, source notes/headers and all-sheet counts "
              "remain at ignored `data/processed/hydride-compressor/v1.2/profile-audit.json`. "
              "External raw/normalized observations are not release inputs. Receipt rights "
              "permission does not change the unchanged `validation_qualified = false` status.", ""]
    (root / "research/hydride_compressor_data.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
