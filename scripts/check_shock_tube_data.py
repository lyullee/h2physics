"""Offline all-acquired-file ELVHYS qualification; only ignored audit output."""

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from h2physics.data.pressure_peaking import file_sha256
from h2physics.data.shock_tube import PROFILE_ID, ShockTubeCollection

SOURCES = (
    "src/h2physics/data/shock_tube.py",
    "tests/test_shock_tube_data.py",
    "scripts/check_shock_tube_data.py",
    "src/h2physics/data/pressure_peaking.py",
    "src/h2physics/observations.py",
    "src/h2physics/core.py",
    "src/h2physics/units.py",
)


def fingerprints(root):
    result = {}
    for name in SOURCES:
        payload = (root / name).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed sources must use LF endings")
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def _signature():
    return [hashlib.sha256() for _ in range(4)]


def _update(digests, block, count=None):
    arrays = (block.values, block.valid, block.raw_values, block.source_lines)
    for digest, array in zip(digests, arrays, strict=True):
        digest.update(np.ascontiguousarray(array[:count]).tobytes())


def _hex(digests):
    return tuple(d.hexdigest() for d in digests)


def audit_recorder(recorder):
    columns = len(recorder.header)
    stats = [
        dict(
            name=v.name,
            unit=v.unit,
            quantity=v.quantity,
            basis=v.basis_id,
            valid=0,
            invalid=0,
            zero=0,
            negative=0,
            finite_min=None,
            finite_max=None,
            valid_min=None,
            valid_max=None,
            reasons={},
            first_invalid_source_line=None,
        )
        for v in recorder.variables
    ]
    result = dict(
        file=recorder.path.name,
        sha256=recorder.source_sha256,
        run_id=recorder.run_id,
        recorder=recorder.kind,
        header=recorder.header,
        columns=columns,
        rows=0,
        numeric_finite_cells=0,
        valid_cells=0,
        invalid_cells=0,
        channels=stats,
        clock_id=recorder.clock_id,
        clock_nonincreasing_steps=0,
        clock_invalid=0,
        minimum_clock_step_s=None,
        maximum_clock_step_s=None,
        clock_zero_count=0,
        series_block_failures=0,
        first_source_line=None,
        last_source_line=None,
        station_positions={
            c.variable.name: None
            if c.position is None
            else dict(
                r_m_reported=c.position.reported_r_m,
                z_m_reported=c.position.reported_z_m,
                phi_deg_reported=c.position.reported_phi_deg,
                source_line=c.position.source_line,
                source_sha256=c.position.source_sha256,
                reference=c.position.reference,
            )
            for c in recorder.channels
        },
        semantic_issues={c.variable.name: c.issues for c in recorder.channels if c.issues},
    )
    stream_digest, prefix_digest = _signature(), _signature()
    prefix_rows, prefix_limit, previous = 0, 8192, None
    for block in recorder.iter_blocks(block_rows=4096):
        _update(stream_digest, block)
        if prefix_rows < prefix_limit:
            count = min(prefix_limit - prefix_rows, len(block.values))
            _update(prefix_digest, block, count)
            prefix_rows += count
        if result["first_source_line"] is None:
            result["first_source_line"] = int(block.source_lines[0])
        result["last_source_line"] = int(block.source_lines[-1])
        result["rows"] += len(block.values)
        result["numeric_finite_cells"] += int(np.isfinite(block.raw_values).sum())
        result["valid_cells"] += int(block.valid.sum())
        result["invalid_cells"] += int((~block.valid).sum())
        table = block.observations
        if (
            table.values.shape != block.values.shape
            or table.row_ids[0].split("line-")[-1] != str(block.source_lines[0])
            or len(set(table.experiment_ids)) != 1
            or table.experiment_ids[0] != recorder.run_id
        ):
            raise ValueError("Actual source row/group identity failed")
        try:
            _ = block.series
        except ValueError:
            result["series_block_failures"] += 1
        for j, stat in enumerate(stats):
            value, valid = block.values[:, j], block.valid[:, j]
            finite = value[np.isfinite(value)]
            admitted = value[valid]
            stat["valid"] += int(valid.sum())
            stat["invalid"] += int((~valid).sum())
            stat["zero"] += int(np.sum(value == 0.0))
            stat["negative"] += int(np.sum(value < 0.0))
            for key, data in (("finite", finite), ("valid", admitted)):
                if data.size:
                    lo, hi = float(data.min()), float(data.max())
                    stat[key + "_min"] = (
                        lo if stat[key + "_min"] is None else min(stat[key + "_min"], lo)
                    )
                    stat[key + "_max"] = (
                        hi if stat[key + "_max"] is None else max(stat[key + "_max"], hi)
                    )
            reasons = Counter(row[j] for row in block.reasons if row[j])
            stat["reasons"] = dict(Counter(stat["reasons"]) + reasons)
            if stat["first_invalid_source_line"] is None and not valid.all():
                stat["first_invalid_source_line"] = int(
                    block.source_lines[np.flatnonzero(~valid)[0]]
                )
        clock = block.values[:, 0]
        result["clock_invalid"] += int((~block.valid[:, 0]).sum())
        result["clock_zero_count"] += int((clock == 0.0).sum())
        joined = clock if previous is None else np.r_[previous, clock]
        adjacent = np.isfinite(joined[:-1]) & np.isfinite(joined[1:])
        steps = np.diff(joined)[adjacent]
        if len(steps):
            lo, hi = float(steps.min()), float(steps.max())
            result["clock_nonincreasing_steps"] += int((steps <= 0.0).sum())
            result["minimum_clock_step_s"] = (
                lo
                if result["minimum_clock_step_s"] is None
                else min(result["minimum_clock_step_s"], lo)
            )
            result["maximum_clock_step_s"] = (
                hi
                if result["maximum_clock_step_s"] is None
                else max(result["maximum_clock_step_s"], hi)
            )
        previous = clock[-1]
    prefix_alternate = _signature()
    alternate_rows = 0
    for block in recorder.iter_blocks(block_rows=137, source_line_stop=prefix_rows + 2):
        _update(prefix_alternate, block)
        alternate_rows += len(block.values)
    if alternate_rows != prefix_rows or _hex(prefix_digest) != _hex(prefix_alternate):
        raise ValueError("Actual source prefix depends on block size")
    result["content_signatures"] = _hex(stream_digest)
    result["alternate_block_prefix_rows"] = prefix_rows
    result["block_stability"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt", type=Path, default=Path("research/data/elvhys-shock-tube.toml")
    )
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/shock_tube_audit.json"))
    parser.add_argument(
        "--progress", type=Path, default=Path("artifacts/shock_tube_audit.progress.jsonl")
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for path in (args.output, args.progress):
        destination = path.resolve()
        if not (
            destination.is_relative_to(root / "artifacts")
            or destination.is_relative_to(root / "data/processed")
        ):
            raise ValueError("Audit outputs must stay in the ignored local artifact directories")
        path.parent.mkdir(parents=True, exist_ok=True)
    before, start = fingerprints(root), time.perf_counter()
    collection = ShockTubeCollection(args.receipt, args.raw_root)
    checked = collection.verify_sources()
    metadata_path = args.raw_root / "elvhys-shock-tube/1.0/repository-metadata.json"
    native = json.loads(metadata_path.read_text(encoding="utf-8"))["data"]["latestVersion"]
    published = {f["dataFile"]["filename"]: f for f in native["files"]}
    source_files = []
    for entry, path in collection.files:
        digest = hashlib.new(entry["publisher_checksum_algorithm"])
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        p = published[entry["name"]]
        if (
            digest.hexdigest() != entry["publisher_checksum"]
            or p.get("restricted", False)
            or p["dataFile"]["filesize"] != entry["size_bytes"]
            or p["dataFile"]["checksum"]["value"] != entry["publisher_checksum"]
        ):
            raise ValueError("Publisher size/checksum/access differs from acquisition receipt")
        source_files.append(
            dict(
                name=entry["name"],
                size_bytes=entry["size_bytes"],
                sha256=checked[entry["name"]],
                publisher_checksum_algorithm=entry["publisher_checksum_algorithm"],
                publisher_checksum=digest.hexdigest(),
            )
        )
    result = dict(
        profile=PROFILE_ID,
        doi=collection.receipt["doi"],
        version=collection.receipt["version"],
        license_id=collection.receipt["license_id"],
        authors=collection.receipt["authors"],
        receipt_sha256=collection.receipt_sha256,
        repository_metadata_sha256=collection.metadata_sha256,
        source_files=source_files,
        acquired_files=len(source_files),
        acquired_bytes=sum(f["size_bytes"] for f in source_files),
        listed_files=collection.receipt["listed_file_count"],
        omitted_files=len(collection.receipt["omitted_files"]),
        begin_source_fingerprints=before,
        reported_tube_geometry_m=collection.reported_tube_geometry_m,
        runs=[
            dict(
                id=r.run_id,
                code=r.code,
                date=r.date,
                ignition_condition=r.ignition_condition,
                membrane=r.membrane_description,
                batch_marker=r.membrane_batch_marker,
                reported_burst_pressure_pa=r.burst_pressure_pa_reported,
                reported_initial_containment_O2_fraction=r.containment_oxygen_fraction_reported,
                reported_initial_containment_temperature_k=r.containment_temperature_k_reported,
                source_line=r.metadata_source_line,
                metadata_sha256=r.metadata_sha256,
            )
            for r in collection.runs.values()
        ],
        support=[
            dict(
                name=e["name"],
                encoding=collection.support_encodings.get(e["name"], "utf-8"),
                physical_lines=len(
                    p.read_text(
                        encoding=collection.support_encodings.get(e["name"], "utf-8")
                    ).splitlines()
                ),
            )
            for e, p in collection.files
            if not any(r.path == p for r in collection.recorders)
        ],
        recorders=[],
    )
    with args.progress.open("a", encoding="utf-8", newline="\n") as progress:
        for index, recorder in enumerate(collection.recorders, 1):
            audit = audit_recorder(recorder)
            result["recorders"].append(audit)
            update = dict(
                index=index,
                total=len(collection.recorders),
                file=recorder.path.name,
                rows=audit["rows"],
                invalid_cells=audit["invalid_cells"],
                elapsed_s=time.perf_counter() - start,
            )
            progress.write(json.dumps(update) + "\n")
            progress.flush()
            print(json.dumps(update), flush=True)
    result["totals"] = {
        key: sum(r[key] for r in result["recorders"])
        for key in (
            "rows",
            "numeric_finite_cells",
            "valid_cells",
            "invalid_cells",
            "clock_nonincreasing_steps",
            "clock_invalid",
            "series_block_failures",
        )
    }
    result["counts_by_recorder"] = dict(Counter(r["recorder"] for r in result["recorders"]))
    result["end_source_fingerprints"] = fingerprints(root)
    result["elapsed_s"] = time.perf_counter() - start
    result["source_checksums_unchanged"] = collection.verify_sources() == checked
    result["source_code_unchanged"] = result["end_source_fingerprints"] == before
    if not result["source_checksums_unchanged"] or not result["source_code_unchanged"]:
        raise ValueError("Source changed during audit")
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            dict(
                output=str(args.output),
                sha256=file_sha256(args.output),
                totals=result["totals"],
                elapsed_s=result["elapsed_s"],
            )
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
