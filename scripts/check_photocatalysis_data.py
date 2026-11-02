"""Offline all-member/all-cell replay; detailed external observations remain ignored."""

import hashlib
import json
import time
import tomllib
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from h2physics.data.photocatalysis import (
    LAYOUTS,
    MOLAR_RATE_SOURCE_UNIT,
    PRIMARY_DOI,
    PROFILE_ID,
    PhotocatalysisArchive,
    PhotocatalysisMappingEvidence,
    reported_aqy,
    reported_h2_specific_rate,
)
from h2physics.data.pressure_peaking import file_sha256

SOURCES = ("src/h2physics/data/photocatalysis.py", "tests/test_photocatalysis_data.py",
           "scripts/check_photocatalysis_data.py", "src/h2physics/data/pressure_peaking.py",
           "src/h2physics/observations.py")


def fingerprints(root):
    result = {}
    for name in SOURCES:
        payload = (root / name).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed Python inputs must retain LF endings")
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def digest_row(digest, line, raw, values, valid, row_id):
    # Length-prefixing avoids ambiguity and does not depend on block boundaries.
    for value in (str(line), row_id, *raw):
        payload = value.encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    digest.update(np.asarray(values, dtype="<f8").tobytes())
    digest.update(valid.tobytes())


def main():
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    receipt_path = root / "research/data/tio2-photo-evolution.toml"
    receipt_sha = file_sha256(receipt_path)
    receipt = tomllib.loads(receipt_path.read_text("utf-8"))
    record = receipt["files"][0]
    path = root / "data/raw" / record["relative_path"]
    metadata_path = path.parent / "repository-metadata.json"
    if file_sha256(metadata_path) != receipt["metadata_sha256"]:
        raise ValueError("Pinned source metadata checksum mismatch")
    metadata = json.loads(metadata_path.read_text("utf-8"))
    if (metadata["doi"] != receipt["doi"] or str(metadata["id"]) != receipt["version"]
            or metadata["metadata"]["license"]["id"] != "cc-by-4.0"
            or receipt["license_id"] != "CC-BY-4.0" or not receipt["rights_permitted"]):
        raise ValueError("Pinned source/version/rights mismatch")
    if path.stat().st_size != record["size_bytes"] or file_sha256(path) != record["sha256"]:
        raise ValueError("Acquired archive receipt mismatch")
    with path.open("rb") as stream:
        publisher = hashlib.file_digest(stream, record["publisher_checksum_algorithm"]).hexdigest()
    if publisher != record["publisher_checksum"]:
        raise ValueError("Publisher archive checksum mismatch")
    report = dict(profile=PROFILE_ID, doi=receipt["doi"], version=receipt["version"],
        authors=receipt["authors"], license=receipt["license_id"], license_url=receipt["license_url"],
        validation_qualified=False, receipt_sha256=receipt_sha, metadata_sha256=receipt["metadata_sha256"],
        archive_sha256=record["sha256"], archive_bytes=record["size_bytes"],
        publisher_checksum_verified=True, source_begin=fingerprints(root), files=[],
        data_rows=0, numeric_rows=0, numeric_cells=0, blank_cells=0, placeholder_cells=0,
        categorical_cells=0, nonfinite_cells=0, negative_numeric_cells=0,
        candidate_primary=dict(doi=PRIMARY_DOI,
            status="dataset-to-publication relationship; full paper/SI mapping not qualified by this replay"),
        primary_rate_mapping="not automatically activated; caller-reviewed member/column/primary evidence required",
        aqy_physical_basis="reported AQY only; incident/absorbed photon, electron factor and optical boundary unresolved",
        gas_reference="reported molar rate mapping needs no ideal-gas conversion; collection/calibration/P/T unresolved",
        study_group="one source study; no member/sample/row-based independent replicate claim")
    categorical_rows = {}
    with PhotocatalysisArchive(path, source_id=receipt["doi"], study_id=receipt["doi"] + "/one-study",
                              expected_sha256=record["sha256"]) as source:
        report["members"] = [asdict(m) for m in source.members]
        report["archive_member_count"] = len(source.members)
        report["archive_expanded_bytes"] = sum(m.bytes for m in source.members)
        report["text_member_count"] = len(source.text_members)
        report["exact_duplicate_members"] = source.duplicate_groups
        for member in source.text_members:
            schema = source.schema(member.name)
            stats = dict(name=member.name, member_sha256=member.sha256, bytes=member.bytes,
                headers=schema.header_rows, encoding=schema.encoding,
                source_first_data_line=schema.first_data_line, source_last_line=schema.last_data_line,
                data_rows=0, source_columns=len(schema.columns), numeric_rows=0,
                numeric_cells=0, invalid_reasons=Counter(),
                columns=[dict(source_column=c.source_column, header_cells=c.header_cells,
                    origin=c.origin.value, numeric=0, negative=0, zero=0, first_numeric_line=None,
                    last_numeric_line=None) for c in schema.columns],
                role=schema.source_role, physical_axes_status=schema.axis_status)
            canonical = hashlib.sha256()
            previous_line = schema.first_data_line - 1
            for block in source.iter_blocks(member.name, block_rows=512):
                table = block.observations
                if any(v != receipt["doi"] + "/one-study" for v in table.experiment_ids):
                    raise ValueError("Unqualified replicate grouping")
                stats["data_rows"] += len(block.source_lines)
                stats["numeric_rows"] += int(table.valid.any(axis=1).sum())
                stats["numeric_cells"] += int(table.valid.sum())
                stats["invalid_reasons"].update(v for row in block.invalid_reasons for v in row if v)
                if block.source_lines[0] != previous_line + 1:
                    raise ValueError("Native source line coverage has a gap/overlap")
                previous_line = block.source_lines[-1]
                for line, raw, values, valid, row_id in zip(block.source_lines, block.raw_cells,
                        table.values, table.valid, table.row_ids, strict=True):
                    digest_row(canonical, line, raw, values, valid, row_id)
                    for column, usable in enumerate(valid):
                        info = stats["columns"][column]
                        info["numeric"] += int(usable)
                        if usable:
                            info["negative"] += int(values[column] < 0)
                            info["zero"] += int(values[column] == 0)
                            if info["first_numeric_line"] is None:
                                info["first_numeric_line"] = line
                            info["last_numeric_line"] = line
                    if member.name in ("Figure4a.txt", "FigureS5.txt"):
                        categorical_rows.setdefault(member.name, []).append((line, raw))
            if (stats["data_rows"] != schema.last_data_line - schema.first_data_line + 1
                    or previous_line != schema.last_data_line):
                raise ValueError("Not every original data row survived")
            stats["canonical_rows_sha256"] = canonical.hexdigest()
            # A separate complete replay tests stable windows/masks/source identities.
            replay = hashlib.sha256()
            for block in source.iter_blocks(member.name, block_rows=127):
                for row in zip(block.source_lines, block.raw_cells, block.observations.values,
                               block.observations.valid, block.observations.row_ids, strict=True):
                    digest_row(replay, *row)
            if replay.hexdigest() != canonical.hexdigest():
                raise ValueError("Block partition changed actual source observations")
            stats["block_partition_replay_equal"] = True
            if member.name == "Figure4a.txt":
                block = next(source.iter_blocks(member.name))
                candidate = PhotocatalysisMappingEvidence(member.sha256, 2, MOLAR_RATE_SOURCE_UNIT,
                    PRIMARY_DOI, "Figure4A unit and Methods candidate; full source mapping review required",
                    "unqualified-primary-candidate", catalyst_mass_basis_id="unresolved")
                try:
                    reported_h2_specific_rate(block, evidence=candidate)
                except ValueError:
                    report["unreviewed_rate_mapping_rejected"] = True
                else:
                    raise ValueError("An unreviewed primary candidate became SI observations")
                # Limited unit/column review, separate from apparatus/uncertainty validation.
                # Author-institution primary PDF indexed text, p9428 Fig4A discussion,
                # explicitly relates named catalysts to umol g^-1 h^-1 reported rates.
                reviewed = PhotocatalysisMappingEvidence(member.sha256, 2, MOLAR_RATE_SOURCE_UNIT,
                    PRIMARY_DOI, "p9428 Figure4A discussion; author-institution indexed primary text",
                    "Hejazi-2024-Fig4A-specific-rate-unit-only", review_status="caller_reviewed",
                    catalyst_mass_basis_id="source catalyst mass denominator; dry/wet basis unresolved",
                    condition_source_id="p9426 Figure4A caption; full apparatus/SI not qualified")
                rate = reported_h2_specific_rate(block, evidence=reviewed)
                report["limited_rate_unit_mapping"] = dict(rows=len(rate.observations.values),
                    valid_cells=int(rate.observations.valid.sum()),
                    mapping_evidence=asdict(reviewed), variable_contracts=[asdict(v) for v in rate.observations.variables],
                    origins=[origin.value for origin in rate.observations.origins],
                    content_sha256=rate.observations.content_sha256,
                    scope="unit/column mapping only; not raw independent gas or catalyst measurement")
            if member.name == "Figure4b.txt":
                block = next(source.iter_blocks(member.name))
                view = reported_aqy(block)
                report["aqy_native_header_view"] = dict(rows=len(view.observations.values),
                    valid_cells=int(view.observations.valid.sum()),
                    source_column=2, sample_identity=view.sample_labels[0],
                    variable_contracts=[asdict(v) for v in view.observations.variables],
                    content_sha256=view.observations.content_sha256)
                try:
                    reported_aqy(block, source_column=3)
                except ValueError:
                    report["unqualified_candidate_aqy_column_rejected"] = True
                else:
                    raise ValueError("Candidate AQY column inherited its neighbor unit")
            report["files"].append(stats)
            for name in ("data_rows", "numeric_rows", "numeric_cells"):
                report[name] += stats[name]
            for key, reason in (("blank_cells", "source_blank"), ("placeholder_cells", "source_placeholder"),
                                ("categorical_cells", "categorical_or_unresolved_text"),
                                ("nonfinite_cells", "source_nonfinite")):
                report[key] += stats["invalid_reasons"][reason]
            report["negative_numeric_cells"] += sum(c["negative"] for c in stats["columns"])
            print(f"{member.name}: {stats['data_rows']} rows / {stats['numeric_cells']} numeric cells", flush=True)
    report["matching_categorical_control_rows"] = [dict(left_member="Figure4a.txt", left_line=left_line,
        right_member="FigureS5.txt", right_line=right_line,
        interpretation="exact raw row overlap; physical replicate provenance not independently established")
        for left_line, left in categorical_rows["Figure4a.txt"]
        for right_line, right in categorical_rows["FigureS5.txt"] if left == right]
    report["data_cells"] = sum(f["data_rows"] * f["source_columns"] for f in report["files"])
    if report["data_cells"] != sum(report[k] for k in (
            "numeric_cells", "blank_cells", "placeholder_cells", "categorical_cells", "nonfinite_cells")):
        raise ValueError("Original data cell accounting does not close")
    if len(report["files"]) != len(LAYOUTS):
        raise ValueError("Not all reviewed text schemas were audited")
    if (file_sha256(receipt_path) != receipt_sha or file_sha256(metadata_path) != receipt["metadata_sha256"]
            or file_sha256(path) != record["sha256"]):
        raise ValueError("Receipt/metadata/archive source changed during audit")
    report["source_end"] = fingerprints(root)
    if report["source_begin"] != report["source_end"]:
        raise ValueError("Executed source changed during replay")
    report["elapsed_seconds"] = time.perf_counter() - started
    output = root / "data/processed/tio2-photo-evolution/15277951/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("text_member_count", "data_rows", "numeric_rows",
        "data_cells", "numeric_cells", "blank_cells", "placeholder_cells", "categorical_cells",
        "nonfinite_cells", "negative_numeric_cells", "elapsed_seconds")}, indent=2))
    print(f"Ignored audit: {output}; SHA-256 {file_sha256(output)}")


if __name__ == "__main__":
    main()
