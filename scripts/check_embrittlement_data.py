"""All acquired HE-Austenite files, bounded workbook and semantic CSV replay."""

import hashlib
import json
import math
import stat
import time
import tomllib
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np

from h2physics.data.embrittlement import (
    COMPOSITION_HEADERS,
    ELEMENTS,
    FILES,
    HEADERS,
    NUMERIC_FIELDS,
    PROFILE_ID,
    PROPERTIES,
    EmbrittlementCollection,
    paired_property_check,
)
from h2physics.data.pressure_peaking import file_sha256

SOURCES = ("src/h2physics/data/embrittlement.py", "tests/test_embrittlement_data.py",
           "scripts/check_embrittlement_data.py", "src/h2physics/data/pressure_peaking.py",
           "src/h2physics/observations.py")


def fingerprints(root):
    result = {}
    for name in SOURCES:
        payload = (root/name).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed Python sources must use LF endings")
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def workbook_audit(path, primary_rows):
    """Native OOXML/openpyxl inspection; no formula, macro or link execution."""
    import openpyxl

    members = []
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if (len(infos) > 100 or len({i.filename for i in infos}) != len(infos)
                or sum(i.file_size for i in infos) > 5_000_000):
            raise ValueError("Workbook ZIP count/expanded budget differs")
        for info in infos:
            if (info.filename.startswith(("/", "\\")) or ".." in PurePosixPath(info.filename).parts
                    or "\\" in info.filename or ":" in info.filename or info.flag_bits & 1
                    or stat.S_ISLNK(info.external_attr >> 16) or info.file_size > 1_000_000
                    or "vbaProject" in info.filename or "externalLinks/" in info.filename):
                raise ValueError("Unsafe or unreviewed workbook member")
            payload = archive.read(info.filename)  # Native CRC verification.
            members.append(dict(name=info.filename, bytes=len(payload),
                                sha256=hashlib.sha256(payload).hexdigest()))
    formulas = openpyxl.load_workbook(path, read_only=True, data_only=False, keep_links=False)
    cached = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_links=False)
    result = dict(members=members, expanded_bytes=sum(m["bytes"] for m in members), sheets=[],
        formula_cells=0, missing_formula_caches=0, formula_error_caches=0,
        main_csv_xlsx_differences=[], source_metadata_rows={})
    try:
        for sheet in formulas:
            if sheet.max_row > 5000 or sheet.max_column > 64:
                raise ValueError("Workbook worksheet dimensions exceed bounds")
            stats = dict(sheet=sheet.title, source_rows=sheet.max_row, columns=sheet.max_column,
                nonempty_cells=0, numeric_cells=0, text_cells=0, blank_cells=0, formulas=[],
                missing_formula_caches=0, error_caches=0, header=())
            for row_number, (row, cache) in enumerate(zip(sheet.iter_rows(), cached[sheet.title].iter_rows(), strict=True), 1):
                if row_number == 1:
                    stats["header"] = tuple(c.value for c in row)
                for column, (cell, value) in enumerate(zip(row, cache, strict=True), 1):
                    raw = cell.value
                    stats["blank_cells"] += int(raw is None)
                    stats["nonempty_cells"] += int(raw is not None)
                    stats["numeric_cells"] += int(isinstance(raw, (int, float)) and not isinstance(raw, bool))
                    stats["text_cells"] += int(isinstance(raw, str) and cell.data_type != "f")
                    if cell.data_type == "f":
                        stats["formulas"].append(dict(source_row=row_number, source_column=column,
                            source_coordinate=cell.coordinate, formula=raw, cached_value=value.value))
                        stats["missing_formula_caches"] += int(value.value is None)
                        stats["error_caches"] += int(value.data_type == "e")
                    if sheet.title == "Data" and row_number > 1 and column <= len(HEADERS):
                        original = primary_rows[row_number-2][column-1]
                        equal = (original == "" and raw is None) or original == raw
                        if not equal and isinstance(raw, (int, float)) and not isinstance(raw, bool):
                            try:
                                equal = math.isfinite(float(original)) and float(original) == raw
                            except ValueError:
                                pass
                        if not equal:
                            result["main_csv_xlsx_differences"].append(dict(source_row=row_number,
                                source_column=column, csv_value=original, workbook_value=raw))
                if sheet.title in {"Sources", "Extraction log", "Data dictionary", "Read me"}:
                    result["source_metadata_rows"].setdefault(sheet.title, []).append(tuple(c.value for c in row))
            result["formula_cells"] += len(stats["formulas"])
            result["missing_formula_caches"] += stats["missing_formula_caches"]
            result["formula_error_caches"] += stats["error_caches"]
            result["sheets"].append(stats)
    finally:
        formulas.close()
        cached.close()
    return result


def main():
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    receipt_path = root/"research/data/austenite-embrittlement.toml"
    receipt_sha = file_sha256(receipt_path)
    receipt = tomllib.loads(receipt_path.read_text("utf-8"))
    directory = root/"data/raw/austenite-embrittlement"/receipt["version"]
    metadata_path = directory/"repository-metadata.json"
    if file_sha256(metadata_path) != receipt["metadata_sha256"]:
        raise ValueError("Pinned repository metadata SHA differs")
    metadata = json.loads(metadata_path.read_text("utf-8"))
    if (metadata["doi"] != receipt["doi"] or str(metadata["id"]) != receipt["version"]
            or metadata["metadata"]["license"]["id"] != "cc-by-4.0"
            or receipt["license_id"] != "CC-BY-4.0" or not receipt["rights_permitted"]
            or "CC BY 4.0" not in (directory/"LICENSE-DATA.txt").read_text("utf-8")):
        raise ValueError("Source identity/version/data rights differ from receipt")
    manifest = {r["name"]:r for r in receipt["files"]}
    if set(manifest) != set(FILES):
        raise ValueError("Acquired file scope differs from reviewed nine-file profile")
    for name, item in manifest.items():
        path = directory/name
        if path.stat().st_size != item["size_bytes"] or file_sha256(path) != item["sha256"]:
            raise ValueError("Acquired source file size/SHA differs")
        with path.open("rb") as stream:
            publisher = hashlib.file_digest(stream, item["publisher_checksum_algorithm"]).hexdigest()
        if publisher != item["publisher_checksum"]:
            raise ValueError("Publisher source checksum differs")
    report = dict(profile=PROFILE_ID, doi=receipt["doi"], version=receipt["version"],
        authors=receipt["authors"], license=receipt["license_id"], license_url=receipt["license_url"],
        receipt_sha256=receipt_sha, metadata_sha256=receipt["metadata_sha256"],
        acquired_files=len(manifest), publisher_listed_files=receipt["listed_file_count"],
        acquired_bytes=sum(r["size_bytes"] for r in manifest.values()), omitted=receipt["omitted_files"],
        files=[dict(name=n, sha256=f["sha256"], bytes=f["size_bytes"]) for n, f in manifest.items()],
        validation_qualified=False, source_begin=fingerprints(root), property_profiles={},
        raw_categories={}, primary_missing=Counter(), numeric_invalid_reasons=Counter(),
        composition_discrepancies=[], ratio_comparisons=0, ratio_mismatches=[],
        max_absolute_ratio_residual=0., actual_primary_temperature_offsets_k=Counter(),
        role_counts={}, source_numeric_cells=0, linked_numeric_cells=0, primary_rows=0)
    expected = {name: item["sha256"] for name, item in manifest.items()}
    with EmbrittlementCollection(directory, source_id=receipt["doi"], expected_sha256=expected) as collection:
        report["primary_rows"] = len(collection.records)
        report["primary_columns"] = len(HEADERS)
        report["linked_composition_rows"] = len(collection.compositions)
        report["linked_composition_columns"] = len(COMPOSITION_HEADERS)
        report["composition_mapping_rows"] = len(collection.composition_mapping)
        report["unmapped_records"] = sum(r.linked_composition is None for r in collection.records)
        report["used_composition_keys"] = len({r.material_group_id for r in collection.records if r.material_group_id})
        primary = [record.source.cells for record in collection.records]
        report["workbook"] = workbook_audit(directory/"HE-Austenite_v1.0.xlsx", primary)
        for field in ("source_id", "property_name", "zone", "is_weld", "reference_environment", "hydrogen_exposure",
                      "test_type", "composition_basis", "verified", "embrittlement_flag"):
            report["raw_categories"][field] = Counter(r.fields[field] for r in collection.records)
        for record in collection.records:
            report["primary_missing"].update(field for field in HEADERS if not record.fields[field].strip())
            report["composition_discrepancies"].extend(dict(record_id=record.record_id,
                primary_row_id=record.row_id, linked_row_id=record.linked_composition.row_id,
                field=d.field, primary_csv_raw=d.primary_csv_raw, linked_composition_raw=d.linked_composition_raw)
                for d in record.composition_discrepancies)
            k, c = float(record.fields["test_temperature_K"]), float(record.fields["test_temperature_C"])
            report["actual_primary_temperature_offsets_k"][str(round(k-(c+273.15), 8))] += 1
            for field in NUMERIC_FIELDS:
                report["role_counts"].setdefault(field, Counter())[record.numeric_role(field)] += 1
        for row in collection.compositions:
            observed = collection.composition_observations(row)
            report["linked_numeric_cells"] += int(observed.valid.sum())
        for property_name in PROPERTIES:
            digest = hashlib.sha256()
            values, masks, identities = [], [], []
            blocks = tuple(collection.iter_blocks(property_name, block_rows=17))
            profile = dict(rows=0, valid_numeric_cells=0, variables=[], origins=[], issues=Counter())
            for block in blocks:
                table = block.observations
                profile["rows"] += len(block.records)
                profile["valid_numeric_cells"] += int(table.valid.sum())
                profile["variables"] = [dict(name=v.name, quantity=v.quantity, unit=v.unit, basis=v.basis_id)
                                        for v in table.variables]
                profile["origins"] = [origin.value for origin in table.origins]
                report["numeric_invalid_reasons"].update(r for row in block.invalid_reasons for r in row if r)
                profile["issues"].update(issue for r in block.records for issue in r.issues)
                check = paired_property_check(block)
                report["ratio_comparisons"] += int(check.available.sum())
                if check.available.any():
                    report["max_absolute_ratio_residual"] = max(report["max_absolute_ratio_residual"],
                        float(np.max(abs(check.residual[check.available]))))
                report["ratio_mismatches"].extend(dict(row_id=check.row_ids[i], residual=float(check.residual[i]))
                    for i in np.flatnonzero(check.available & ~check.within_tolerance))
                values.extend(table.values)
                masks.extend(table.valid)
                identities.extend(table.row_ids)
                for row_id, row, mask in zip(table.row_ids, table.values, table.valid, strict=True):
                    digest.update(row_id.encode())
                    digest.update(np.asarray(row, dtype="<f8").tobytes())
                    digest.update(mask.tobytes())
            whole = tuple(collection.iter_blocks(property_name, block_rows=512))
            if (tuple(i for b in whole for i in b.observations.row_ids) != tuple(identities)
                    or not np.array_equal(np.concatenate([b.observations.values for b in whole]),
                                          np.array(values), equal_nan=True)
                    or not np.array_equal(np.concatenate([b.observations.valid for b in whole]), np.array(masks))):
                raise ValueError("Block partition changed source identity/numeric/mask observations")
            profile["partition_replay_equal"] = True
            profile["source_rows_numeric_mask_digest"] = digest.hexdigest()
            report["property_profiles"][property_name] = profile
            report["source_numeric_cells"] += profile["valid_numeric_cells"]
            print(f"{property_name}: {profile['rows']} original records", flush=True)
    report["element_discrepancies"] = sum(d["field"] in ELEMENTS for d in report["composition_discrepancies"])
    report["element_discrepancy_records"] = len({d["record_id"] for d in report["composition_discrepancies"]
                                                if d["field"] in ELEMENTS})
    report["source_end"] = fingerprints(root)
    if (report["source_begin"] != report["source_end"] or file_sha256(receipt_path) != receipt_sha
            or file_sha256(metadata_path) != receipt["metadata_sha256"]):
        raise ValueError("Executed/source receipt metadata changed during qualification")
    report["elapsed_seconds"] = time.perf_counter()-started
    output = root/"data/processed/austenite-embrittlement/23107780/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({k:report[k] for k in ("acquired_files", "acquired_bytes", "primary_rows",
        "source_numeric_cells", "linked_composition_rows", "linked_numeric_cells", "composition_mapping_rows",
        "ratio_comparisons", "max_absolute_ratio_residual", "element_discrepancies",
        "element_discrepancy_records", "elapsed_seconds")}, indent=2))
    print(f"All acquired hashes unchanged; ignored audit SHA {file_sha256(output)}")


if __name__ == "__main__":
    main()
