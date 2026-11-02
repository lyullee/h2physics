"""Offline all-acquired USN thermal vectors; bounded workers and durable checkpoints."""

import argparse
import hashlib
import json
import time
import tomllib
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import h5py
import numpy as np

from h2physics.data.pressure_peaking import file_sha256
from h2physics.data.thermal_effects import (
    CLOCK_UNIT,
    PROFILE_ID,
    ThermalEffectsFile,
    thermal_location_rows,
)

SOURCES = ("src/h2physics/data/thermal_effects.py", "tests/test_thermal_effects_data.py",
           "scripts/check_thermal_effects_data.py", "src/h2physics/data/pressure_peaking.py",
           "src/h2physics/observations.py", "src/h2physics/units.py")


def fingerprints(root):
    result = {}
    for relative in SOURCES:
        payload = (root / relative).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed sources require LF endings")
        result[relative] = hashlib.sha256(payload).hexdigest()
    return result


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def audit_file(root, record, source_id):
    path = Path(root) / "data/raw" / record["relative_path"]
    with ThermalEffectsFile(path, source_id=source_id, experiment_id=path.stem,
                            expected_sha256=record["sha256"]) as source:
        inventory = {item[0]: item for item in source.inventory}
        fields = {key: dict(source_elements=0, nonfinite=0, negative=0, zero=0,
                           invalid_physical_temperature=0, raw_min=None, raw_max=None,
                           shape=list(item[1]), dtype=item[2], compression=item[3])
                  for key, item in inventory.items()}
        digests = {key: hashlib.sha256() for key in fields}
        profiles = []
        for recorder in source.recorders:
            paths = ([recorder.clock_path] if recorder.clock_path else [None]) + [c.path for c in recorder.channels]
            issues, rows, first_id, last_id = Counter(), 0, None, None
            first_contract_hash = None
            for block in source.iter_blocks(recorder):
                if first_id is None:
                    table = block.observations
                    first_id, first_contract_hash = table.row_ids[0], table.content_sha256
                rows += len(block.source_indices)
                last_id = f"{source.source_id}|{source.experiment_id}|{source.sha256}|{recorder.identity}|vector-index-{block.source_indices[-1]}"
                issues.update({f"{issue.code}:{issue.channel}": issue.count for issue in block.issues})
                for column, vector_path in enumerate(paths):
                    if vector_path is None:
                        continue  # A missing association is not a nonfinite source cell.
                    values = block.raw_values[:, column]
                    finite = np.isfinite(values)
                    stats = fields[vector_path]
                    stats["source_elements"] += len(values)
                    stats["nonfinite"] += int(np.count_nonzero(~finite))
                    stats["negative"] += int(np.count_nonzero(finite & (values < 0)))
                    stats["zero"] += int(np.count_nonzero(finite & (values == 0)))
                    if np.any(finite):
                        low, high = float(values[finite].min()), float(values[finite].max())
                        stats["raw_min"] = low if stats["raw_min"] is None else min(low, stats["raw_min"])
                        stats["raw_max"] = high if stats["raw_max"] is None else max(high, stats["raw_max"])
                    if column and recorder.channels[column - 1].variable.quantity == "temperature":
                        stats["invalid_physical_temperature"] += int(np.count_nonzero(
                            np.isfinite(block.values[:, column + 1]) & ~block.valid[:, column + 1]))
                    digests[vector_path].update(np.asarray(values, dtype="<f8").tobytes())
            if rows != recorder.samples:
                raise ValueError("Incomplete recorder consumption")
            profiles.append(dict(schema=asdict(recorder), observation_rows=rows, issues=dict(issues),
                first_row_id=first_id, last_row_id=last_id, first_block_contract_sha256=first_contract_hash))
        for key, stats in fields.items():
            if stats["source_elements"] != int(np.prod(inventory[key][1])):
                raise ValueError("Source vector omitted or counted more than once")
            stats["canonical_vector_values_sha256"] = digests[key].hexdigest()
        return dict(file=record["name"], sha256=source.sha256, bytes=path.stat().st_size,
            expanded_numeric_bytes=source.total_array_bytes, profiles=profiles, fields=fields,
            TS_present=any(key.startswith("/TS/") for key in fields))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--resume", action="store_true")
    options = parser.parse_args()
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    receipt_path = root / "research/data/carpark-thermal.toml"
    receipt_sha = file_sha256(receipt_path)
    receipt = tomllib.loads(receipt_path.read_text("utf-8"))
    source_dir = root / "data/raw/carpark-thermal/1"
    output = root / "data/processed/carpark-thermal/1"
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "audit.partial.json"
    begin = fingerprints(root)
    metadata_paths = [p for p in source_dir.glob("*.json") if file_sha256(p) == receipt["metadata_sha256"]]
    if not metadata_paths:
        raise ValueError("Pinned repository metadata receipt mismatch")
    metadata = json.loads(metadata_paths[0].read_text("utf-8"))
    if metadata["doi"] != receipt["doi"] or metadata["license"]["url"] != receipt["license_url"]:
        raise ValueError("Pinned source DOI/license differs")
    if len(metadata["files"]) != receipt["listed_file_count"]:
        raise ValueError("Pinned source attachment inventory differs")
    report = dict(profile=PROFILE_ID, source=receipt["doi"], license=receipt["license_id"],
        metadata_sha256=receipt["metadata_sha256"], metadata_file=metadata_paths[0].name,
        receipt_sha256=receipt_sha, source_begin=begin, workers=options.workers, resumed_segments=0,
        h5py_version=h5py.__version__, HDF5_version=h5py.version.hdf5_version,
        numpy_version=np.__version__, files=[], documentation=[], experiments=[])
    for supporting in receipt.get("supporting_metadata", []):
        if not any(file_sha256(p) == supporting["sha256"] for p in source_dir.glob("*.json")):
            raise ValueError("Supporting original metadata bytes unavailable")
    report["supporting_metadata"] = receipt.get("supporting_metadata", [])
    for record in receipt["files"]:
        path = root / "data/raw" / record["relative_path"]
        if path.stat().st_size != record["size_bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError("Acquired source attachment differs from receipt")
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, record["publisher_checksum_algorithm"]).hexdigest()
        if checksum != record["publisher_checksum"]:
            raise ValueError("Publisher source checksum differs")
        report["files"].append(dict(name=record["name"], bytes=path.stat().st_size,
            sha256=record["sha256"], publisher_checksum=checksum))
        if path.suffix == ".docx":
            with ZipFile(path) as archive:
                if sum(info.file_size for info in archive.infolist()) > 5_000_000:
                    raise ValueError("Documentation ZIP budget exceeded")
                document = ET.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                report["documentation"].append(dict(file=path.name, sha256=record["sha256"],
                    paragraphs=len(document.findall(".//w:p", ns)), tables=len(document.findall(".//w:tbl", ns)),
                    media_count=sum("/media/" in item.filename for item in archive.infolist())))
    report["location_rows"] = thermal_location_rows(source_dir / "data description.docx")
    records = sorted((r for r in receipt["files"] if r["name"].endswith(".mat")), key=lambda r: r["name"])
    report["omitted_files"] = receipt["omitted_files"]
    preceding_elapsed = 0.
    if options.resume and checkpoint.exists():
        prior = json.loads(checkpoint.read_text("utf-8"))
        if prior["source_begin"] != begin or prior["receipt_sha256"] != receipt_sha:
            raise ValueError("Checkpoint source/receipt changed; fresh audit required")
        report["experiments"] = prior["experiments"]
        expected = {r["name"]: r["sha256"] for r in records}
        if (len({r["file"] for r in report["experiments"]}) != len(report["experiments"])
                or any(expected.get(r["file"]) != r["sha256"] for r in report["experiments"])):
            raise ValueError("Checkpoint member identities differ")
        report["resumed_segments"] = prior["resumed_segments"] + 1
        preceding_elapsed = prior["elapsed_seconds"]
    done_files = {r["file"] for r in report["experiments"]}
    remaining = iter(r for r in records if r["name"] not in done_files)
    with ProcessPoolExecutor(max_workers=options.workers) as pool:
        pending = {}

        def submit_next():
            record = next(remaining, None)
            if record is not None:
                pending[pool.submit(audit_file, str(root), record, receipt["doi"])] = record["name"]

        for _ in range(options.workers):
            submit_next()
        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                name = pending.pop(future)
                report["experiments"].append(future.result())
                report["experiments"].sort(key=lambda item: item["file"])
                report["elapsed_seconds"] = preceding_elapsed + time.perf_counter() - started
                save(checkpoint, report)
                print(f"{name}: complete; {len(report['experiments'])}/{len(records)} durable checkpoints", flush=True)
                submit_next()
    report["source_end"] = fingerprints(root)
    if report["source_end"] != begin or file_sha256(receipt_path) != receipt_sha:
        raise ValueError("Executed sources or receipt changed during audit")
    report["elapsed_seconds"] = preceding_elapsed + time.perf_counter() - started
    save(output / "audit.json", report)
    write_summary(root, report)
    print(f"Complete: {len(records)} MAT files in {report['elapsed_seconds']:.2f}s; no clock seconds or model validation inferred", flush=True)


def write_summary(root, report):
    experiments = report["experiments"]
    fields = [field for e in experiments for field in e["fields"].values()]
    profiles = [p for e in experiments for p in e["profiles"]]
    clocked = [p for p in profiles if p["schema"]["clock_path"]]
    unclocked = [p for p in profiles if not p["schema"]["clock_path"]]
    negative_flux = sum(f["negative"] for e in experiments for path, f in e["fields"].items() if path.startswith("/HF/RHF"))
    negative_total_flux = sum(f["negative"] for e in experiments for path, f in e["fields"].items() if path.startswith("/HF/THF"))
    negative_mass_flow = sum(e["fields"]["/MFM/mfr"]["negative"] for e in experiments)
    negative_pressure = sum(f["negative"] for e in experiments for path, f in e["fields"].items() if path.endswith("/P"))
    clock_edges = sum(count for p in clocked for key, count in p["issues"].items() if key.startswith("nonincreasing_clock_retained:"))
    lines = ["# USN carpark thermal source qualification", "",
        "Agnieszka Lach and Andre Vagner Gaathaug, "
        "[Experimental data—hydrogen safety, thermal effects, version 1](https://doi.org/10.23642/usn.17695082.v1), "
        "CC BY 4.0. This record contains original aggregate audit results and source hashes, "
        "without reproducing source prose, figures, coordinates, tables, programs or measured traces.", "",
        f"The complete local native-HDF5 scan finished in {report['elapsed_seconds']:.2f}s with "
        f"{report['workers']} bounded workers and {report['resumed_segments']} resumed segments. "
        f"All {len(report['files'])} acquired attachment SHA-256/publisher checksums and the pinned "
        "metadata matched. The original supporting metadata was retained and verified. "
        "DOCX metadata was inspected as ZIP/XML without executing source content.", "",
        f"- Acquired attachment bytes: {sum(f['bytes'] for f in report['files'])}.",
        f"- Actual MAT files: {len(experiments)}; numeric source vectors: {len(fields)}.",
        f"- Source scalar elements (including each clock exactly once): {sum(f['source_elements'] for f in fields)}.",
        f"- Nonfinite source cells: {sum(f['nonfinite'] for f in fields)}.",
        f"- Nonphysical absolute-temperature cells retained/masked: {sum(f['invalid_physical_temperature'] for f in fields)}.",
        f"- Default export/vector profiles: {len(profiles)}; clock-bearing: {len(clocked)}; unclocked: {len(unclocked)}.",
        f"- Profile observation rows (includes independent clock-only vectors): {sum(p['observation_rows'] for p in profiles)}.",
        f"- Unclocked signal rows retained: {sum(p['observation_rows'] for p in unclocked)}.",
        f"- Negative radiative/combined-flux/mass-flow/reported-pressure source samples retained: "
        f"{negative_flux}/{negative_total_flux}/{negative_mass_flow}/{negative_pressure}.",
        f"- Nonincreasing source clock edges retained: {clock_edges}.",
        f"- Source-reported clock unit: `{CLOCK_UNIT}`. No sample rate in Hz, physical duration in seconds "
        "or inter-recorder synchronization is inferred.", "",
        "These are storage/vector coverage counts, not independent measurement, fitting or validation counts. "
        "All default source vectors passed exact once-only scalar coverage. No source normalization, "
        "baseline subtraction, negative clipping, sensor inversion, calibration fit, noise sigma or "
        "per-case combustion/source condition was invented.", "",
        "| MAT file | Source vectors | Source scalar elements | Profile rows | Unclocked rows | Nonphysical T cells | TS exported |",
        "|---|---:|---:|---:|---:|---:|---|"]
    for e in experiments:
        ff, pp = list(e["fields"].values()), e["profiles"]
        lines.append(f"| {e['file']} | {len(ff)} | {sum(f['source_elements'] for f in ff)} | "
            f"{sum(p['observation_rows'] for p in pp)} | "
            f"{sum(p['observation_rows'] for p in pp if not p['schema']['clock_path'])} | "
            f"{sum(f['invalid_physical_temperature'] for f in ff)} | {e['TS_present']} |")
    lines += ["", "## Scientific boundaries", "",
        "RHF radiation, THF combined-flux export, plate temperature, Coriolis mass flow, reported "
        "pressure, instrument/bolt temperatures, point thermocouples and ventilation outputs retain "
        "different variables, units, origins and observation roles. THF processing/plate inversion "
        "is unresolved; it is not an independently qualified total-flux measurement. Source bar "
        "is not promoted to absolute pressure. Meter and bolt readings are not bulk gas temperatures. "
        "The location table is local runtime metadata in source y,x,z order and millimetres, with "
        "drawing frame and the incomplete ventilation location preserved.", "",
        "RHF3 has no default paired clock. Its source vector and timech7 remain separate; matching "
        "lengths create candidate metadata only. A caller may explicitly declare an evidence-bearing "
        "association with reconstructed origin and unresolved physical time unit. Experiment 2's "
        "Vent/T and Vent/time lengths differ; every temperature survives unclocked without borrowing "
        "another group's clock or truncation. Experiment 3 does not export TS. All original vector "
        "orientations, source indices, signed fields, zeros, invalid masks and independent source "
        "clocks survive. No automatic TimeSeries conversion is available.", "",
        "The acquired metadata describes ignited releases, but does not assign all required source "
        "conditions to each exported experiment. This ingestion does not qualify a flame/radiation "
        "model, sensor response, steel/gas thermal inversion, exposure dose or CFD validation. "
        "Rights permission does not change `validation_qualified = false`.", "",
        "## Attachment identities", "",
        f"Pinned metadata SHA-256: `{report['metadata_sha256']}`; receipt SHA-256: `{report['receipt_sha256']}`.", "",
        "| Attachment | Bytes | SHA-256 |", "|---|---:|---|"]
    lines.extend(f"| {f['name']} | {f['bytes']} | `{f['sha256']}` |" for f in report["files"])
    lines += ["", "## Executed source fingerprints", "", "Begin and end fingerprints matched; sources used LF.", ""]
    lines.extend(f"- `{name}`: `{digest}`" for name, digest in report["source_begin"].items())
    lines += ["", f"Runtime: h5py {report['h5py_version']}, HDF5 {report['HDF5_version']}, NumPy {report['numpy_version']}.", "",
        "Complete private schemas, units/roles, per-vector canonical value hashes, counts/extrema, "
        "masks/issues, source row identities, runtime location rows and durable checkpoints remain "
        "in ignored `data/processed/carpark-thermal/1/audit.json`. Raw and normalized external "
        "observations remain excluded from Git and distributions.", ""]
    (root / "research/thermal_effects_data.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
