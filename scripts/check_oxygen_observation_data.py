"""All acquired ELVHYS4.2 CSVs, source roles, separate clocks and durable audits."""

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from h2physics.data.oxygen_observations import (
    PROFILE_ID,
    CryogenicRoomCollection,
    CryogenicRoomRecorder,
)
from h2physics.data.pressure_peaking import file_sha256

if __package__:
    from .check_shock_tube_data import _hex, _signature, _update
else:
    from check_shock_tube_data import _hex, _signature, _update

SOURCES = (
    "src/h2physics/data/oxygen_observations.py",
    "tests/test_oxygen_observations.py",
    "scripts/check_oxygen_observation_data.py",
    "src/h2physics/data/shock_tube.py",
    "src/h2physics/data/pressure_peaking.py",
    "src/h2physics/core.py",
    "src/h2physics/units.py",
    "src/h2physics/observations.py",
    "scripts/check_shock_tube_data.py",
)


def fingerprints(root):
    result = {}
    for name in SOURCES:
        payload = (root / name).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed Python sources must have LF endings")
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def _range(stat, prefix, array):
    values = array[np.isfinite(array)]
    if len(values):
        lo, hi = float(values.min()), float(values.max())
        stat[prefix + "_min"] = (
            lo if stat[prefix + "_min"] is None else min(stat[prefix + "_min"], lo)
        )
        stat[prefix + "_max"] = (
            hi if stat[prefix + "_max"] is None else max(stat[prefix + "_max"], hi)
        )


def audit_recorder(spec):
    entry, path, case, positions, directory = spec
    r = CryogenicRoomRecorder(
        path,
        case=case,
        positions=positions,
        expected_sha256=entry["sha256"],
        directory_label=directory,
    )
    stats = [
        dict(
            header=c.source_header,
            source_unit=c.source_unit,
            unit=c.variable.unit,
            quantity=c.variable.quantity,
            basis=c.variable.basis_id,
            origin=c.origin,
            reported_clock_column=c.reported_clock_column,
            position_m=None if c.position is None else c.position.position_m,
            position_source_line=None if c.position is None else c.position.source_line,
            candidate_position_m=None
            if c.candidate_position is None
            else c.candidate_position.position_m,
            candidate_position_source_line=None
            if c.candidate_position is None
            else c.candidate_position.source_line,
            semantic_issues=c.issues,
            numeric_finite=0,
            valid=0,
            masked=0,
            zeros=0,
            negatives=0,
            raw_min=None,
            raw_max=None,
            si_min=None,
            si_max=None,
            reasons={},
            first_masked_source_line=None,
        )
        for c in r.channels
    ]
    result = dict(
        name=path.name,
        sha256=r.source_sha256,
        case=case.number,
        case_source_line=case.source_line,
        source_declared_invalid_case=case.source_declared_invalid,
        directory=directory,
        kind=r.recorder_kind,
        source_date_token=r.date_token,
        columns=len(r.header),
        rows=0,
        first_source_line=None,
        last_source_line=None,
        numeric_finite_cells=0,
        source_cells=0,
        valid_cells=0,
        masked_cells=0,
        channels=stats,
        clocks={},
        unknown_fields=[
            c.source_header for c in r.channels if c.variable.quantity == "reported_unknown"
        ],
        missing_hydrogen_mass_flow=True,
        oxygen_is_not_measured=True,
        automatic_time_series_rejected=False,
    )
    clocks = {
        j: dict(
            valid=0,
            missing=0,
            duplicate_steps=0,
            decreasing_steps=0,
            minimum_step=None,
            maximum_step=None,
            previous=None,
        )
        for j, c in enumerate(r.channels)
        if c.variable.quantity == "reported_time_coordinate"
    }
    digests, prefix, prefix_rows = _signature(), _signature(), 0
    for block in r.iter_blocks(block_rows=4096, maximum_rows=2_000_000):
        _update(digests, block)
        if prefix_rows < 8192:
            count = min(8192 - prefix_rows, len(block.values))
            _update(prefix, block, count)
            prefix_rows += count
        if result["first_source_line"] is None:
            result["first_source_line"] = int(block.source_lines[0])
        result["last_source_line"] = int(block.source_lines[-1])
        result["rows"] += len(block.values)
        result["source_cells"] += block.raw_values.size
        result["numeric_finite_cells"] += int(block.numeric_valid.sum())
        result["valid_cells"] += int(block.valid[:, 1:].sum())
        result["masked_cells"] += int((~block.valid[:, 1:]).sum())
        table = block.observations
        if not all(
            n.endswith("|line-" + str(line))
            for n, line in zip(table.row_ids, block.source_lines, strict=True)
        ):
            raise ValueError("Original physical source-row identities changed")
        if table.experiment_ids != (case.experiment_id,) * len(table.values):
            raise ValueError("Original experiment/case grouping changed")
        try:
            block.as_time_series()
        except ValueError:
            result["automatic_time_series_rejected"] = True
        else:
            raise ValueError("Unknown clock unit became a physical seconds history")
        for j, stat in enumerate(stats):
            raw, si, valid = block.raw_values[:, j], block.values[:, j + 1], block.valid[:, j + 1]
            stat["numeric_finite"] += int(block.numeric_valid[:, j].sum())
            stat["valid"] += int(valid.sum())
            stat["masked"] += int((~valid).sum())
            stat["zeros"] += int((raw == 0.0).sum())
            stat["negatives"] += int((raw < 0.0).sum())
            _range(stat, "raw", raw)
            _range(stat, "si", si)
            stat["reasons"] = dict(
                Counter(stat["reasons"])
                + Counter(reason for row in block.reasons for reason in row[j].split(";") if reason)
            )
            if not valid.all() and stat["first_masked_source_line"] is None:
                stat["first_masked_source_line"] = int(
                    block.source_lines[np.flatnonzero(~valid)[0]]
                )
            if j in clocks:
                clock = clocks[j]
                clock["valid"] += int(block.numeric_valid[:, j].sum())
                clock["missing"] += int((~block.numeric_valid[:, j]).sum())
                values = raw if clock["previous"] is None else np.r_[clock["previous"], raw]
                steps = np.diff(values)[np.isfinite(values[:-1]) & np.isfinite(values[1:])]
                if len(steps):
                    lo, hi = float(steps.min()), float(steps.max())
                    clock["duplicate_steps"] += int((steps == 0.0).sum())
                    clock["decreasing_steps"] += int((steps < 0.0).sum())
                    clock["minimum_step"] = (
                        lo if clock["minimum_step"] is None else min(lo, clock["minimum_step"])
                    )
                    clock["maximum_step"] = (
                        hi if clock["maximum_step"] is None else max(hi, clock["maximum_step"])
                    )
                clock["previous"] = raw[-1]
    for j, clock in clocks.items():
        clock.pop("previous")
        result["clocks"][r.header[j]] = clock
    alternate, count = _signature(), 0
    if prefix_rows:
        for block in r.iter_blocks(
            block_rows=137, source_line_stop=prefix_rows + 2, maximum_rows=2_000_000
        ):
            _update(alternate, block)
            count += len(block.values)
    if count != prefix_rows or _hex(alternate) != _hex(prefix):
        raise ValueError("Original source arrays/masks/indices depend on block size")
    result["block_stability_rows"] = prefix_rows
    result["content_signatures"] = _hex(digests)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=Path("research/data/elvhys-cold-room.toml"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/elvhys-cold-room/1.1/audit.json")
    )
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not (
        output.is_relative_to(root / "data/processed") or output.is_relative_to(root / "artifacts")
    ):
        raise ValueError("External audit outputs must remain in ignored local directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = output.parent / "file-checkpoints"
    checkpoint.mkdir(exist_ok=True)
    start, before = time.perf_counter(), fingerprints(root)
    collection = CryogenicRoomCollection(args.receipt, args.raw_root)
    checked = collection.verify_sources()
    sources = []
    for e, p in collection.files:
        md5 = hashlib.md5(usedforsecurity=False)
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                md5.update(chunk)
        if e["publisher_checksum_algorithm"] != "md5" or md5.hexdigest() != e["publisher_checksum"]:
            raise ValueError("Actual source fails its native publisher checksum")
        sources.append(
            dict(
                name=e["name"],
                bytes=e["size_bytes"],
                sha256=checked[e["name"]],
                md5=md5.hexdigest(),
            )
        )
    identity = dict(
        code=before,
        receipt_sha256=collection.receipt_sha256,
        metadata_sha256=collection.metadata_sha256,
        profile=PROFILE_ID,
    )
    results, todo = [], []
    for r in collection.recorders:
        e = next(e for e, p in collection.files if p == r.path)
        target = checkpoint / (r.path.stem + ".json")
        if args.resume and target.exists():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing["identity"] != identity or existing["result"]["sha256"] != r.source_sha256:
                raise ValueError("Checkpoint inputs differ; refuse a stale resume")
            results.append(existing["result"])
        else:
            todo.append(((e, r.path, r.case, collection.positions, r.directory_label), target))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(audit_recorder, spec): target for spec, target in todo}
        for future in as_completed(pending):
            result = future.result()
            target = pending[future]
            temporary = target.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(dict(identity=identity, result=result), allow_nan=False),
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, target)
            results.append(result)
            print(
                json.dumps(
                    dict(
                        completed=len(results),
                        total=len(collection.recorders),
                        file=result["name"],
                        rows=result["rows"],
                        elapsed_s=time.perf_counter() - start,
                    )
                ),
                flush=True,
            )
    results.sort(key=lambda r: r["name"])
    after = fingerprints(root)
    if before != after or collection.verify_sources() != checked:
        raise ValueError("Executed code or original source changed during the complete audit")
    result = dict(
        profile=PROFILE_ID,
        receipt_sha256=collection.receipt_sha256,
        repository_metadata_sha256=collection.metadata_sha256,
        acquired_files=len(sources),
        acquired_bytes=sum(s["bytes"] for s in sources),
        source_files=sources,
        observed_cases=collection.observed_case_numbers,
        absent_nominal_cases=collection.absent_case_numbers,
        source_declared_invalid_observed_cases=[
            n
            for n in collection.observed_case_numbers
            if collection.cases[n].source_declared_invalid
        ],
        sources_unchanged=True,
        code_unchanged=True,
        begin_fingerprints=before,
        end_fingerprints=after,
        counts_by_kind=dict(Counter(r["kind"] for r in results)),
        recorders=results,
        totals={
            k: sum(r[k] for r in results)
            for k in ("rows", "source_cells", "numeric_finite_cells", "valid_cells", "masked_cells")
        },
        elapsed_s=time.perf_counter() - start,
    )
    output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            dict(
                output=str(output),
                sha256=file_sha256(output),
                totals=result["totals"],
                elapsed_s=result["elapsed_s"],
            )
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
