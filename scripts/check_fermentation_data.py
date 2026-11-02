"""Complete offline fermentation audit and same-export algebra checks, without fitting."""

import hashlib
import json
import math
import time
import tomllib
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from h2physics.data.fermentation import (
    HEADERS,
    LITRE_PER_DAY_TO_M3_PER_S,
    PROFILE_ID,
    FermentationWorkbook,
    component_production_check,
)
from h2physics.data.pressure_peaking import file_sha256

SOURCES = ("src/h2physics/data/fermentation.py", "tests/test_fermentation_data.py",
           "scripts/check_fermentation_data.py", "src/h2physics/data/pressure_peaking.py",
           "src/h2physics/observations.py", "src/h2physics/units.py")


def fingerprints(root):
    result = {}
    for name in SOURCES:
        payload = (root / name).read_bytes()
        if b"\r" in payload:
            raise ValueError("Executed sources must retain LF endings")
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def main():
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    receipt_path = root / "research/data/dark-fermentation.toml"
    receipt_sha = file_sha256(receipt_path)
    receipt = tomllib.loads(receipt_path.read_text("utf-8"))
    record = receipt["files"][0]
    path = root / "data/raw" / record["relative_path"]
    metadata_path = path.parent / "repository-metadata.json"
    if file_sha256(metadata_path) != receipt["metadata_sha256"]:
        raise ValueError("Pinned metadata checksum mismatch")
    metadata = json.loads(metadata_path.read_text("utf-8"))
    if (metadata["doi"] != receipt["doi"] or str(metadata["version"]) != receipt["version"]
            or receipt["license_id"] != "CC-BY-4.0"
            or metadata["licence"]["short_name"] != "CC BY 4.0"
            or metadata["licence"]["url"] != receipt["license_url"]):
        raise ValueError("Pinned source identity/version/license mismatch")
    for supporting in receipt.get("supporting_metadata", []):
        if not any(file_sha256(p) == supporting["sha256"] for p in path.parent.glob("*.json")):
            raise ValueError("Supporting source file-list metadata unavailable")
    if path.stat().st_size != record["size_bytes"] or file_sha256(path) != record["sha256"]:
        raise ValueError("Workbook acquisition receipt mismatch")
    with path.open("rb") as stream:
        publisher = hashlib.file_digest(stream, record["publisher_checksum_algorithm"]).hexdigest()
    if publisher != record["publisher_checksum"]:
        raise ValueError("Publisher source checksum mismatch")
    report = dict(profile=PROFILE_ID, doi=receipt["doi"], license=receipt["license_id"],
        receipt_sha256=receipt_sha, metadata_sha256=receipt["metadata_sha256"],
        workbook_sha256=record["sha256"], workbook_bytes=path.stat().st_size,
        source_begin=fingerprints(root), source_rows=0, reactors={},
        column_headers=HEADERS, invalid_reasons=Counter(), blank_cells=0,
        placeholder_cells=0, cached_numeric_cells=0, numeric_string_cells=0,
        formula_cells=0, missing_formula_caches=0, error_cells=0, valid_numeric_cells=0,
        source_nr_gaps=[], duplicate_duration_edges=[], component_inconsistencies=[],
        component_tolerance_reported_L_per_day=1e-9, gas_fraction_closure_tolerance=1e-9,
        max_component_residual_reported_L_per_day=0., max_fraction_closure=0.)
    tolerance = report["component_tolerance_reported_L_per_day"] * LITRE_PER_DAY_TO_M3_PER_S
    digest, previous_nr = hashlib.sha256(), None
    with FermentationWorkbook(path, source_id=receipt["doi"], study_id=receipt["doi"] + "/one-study",
                              expected_sha256=record["sha256"]) as source:
        report["declared_dimensions"] = [source.source_last_row, len(HEADERS)]
        for block in source.iter_blocks():
            table = block.observations
            if not all(group == receipt["doi"] + "/one-study" for group in table.experiment_ids):
                raise ValueError("Unqualified replicate partition")
            stats = report["reactors"].setdefault(block.reactor_id, dict(rows=0,
                first_source_row=block.source_rows[0], last_source_row=None,
                source_nr_min=None, source_nr_max=None, duration_day_first=None, duration_day_last=None,
                valid_chemistry=[0] * 8, HRT_day_counts=Counter(),
                normalization_diagnostics=dict(HPR_over_HP=[], MPR_over_MP=[], HY_times_OLR_over_HPR=[])))
            stats["rows"] += len(block.source_rows)
            stats["last_source_row"] = block.source_rows[-1]
            stats["valid_chemistry"] = [a + int(b) for a, b in zip(stats["valid_chemistry"],
                table.valid[:, 16:24].sum(axis=0), strict=True)]
            report["source_rows"] += len(block.source_rows)
            report["valid_numeric_cells"] += int(table.valid.sum())
            report["formula_cells"] += len(block.formula_cells)
            report["missing_formula_caches"] += sum(reason == "source_formula_cache_missing"
                for row in block.invalid_reasons for reason in row)
            report["invalid_reasons"].update(reason for row in block.invalid_reasons for reason in row if reason)
            report["duplicate_duration_edges"].extend(asdict(issue) | {"reactor": block.reactor_id}
                for issue in block.issues)
            report.setdefault("reactor_variable_contracts", {})[block.reactor_id] = [asdict(v) for v in table.variables]
            report.setdefault("column_origins", [str(value) for value in table.origins])
            for row_number, raw, values, valid, row_id in zip(block.source_rows, block.raw_cells,
                    table.values, table.valid, table.row_ids, strict=True):
                digest.update(row_number.to_bytes(8, "big"))
                digest.update(row_id.encode())
                digest.update(np.asarray(values, dtype="<f8").tobytes())
                digest.update(valid.tobytes())
                for column, value in enumerate(raw):
                    report["blank_cells"] += int(value is None)
                    report["placeholder_cells"] += int(value == "--")
                    report["cached_numeric_cells"] += int(isinstance(value, (int, float)) and not isinstance(value, bool))
                    report["numeric_string_cells"] += int(isinstance(value, str) and valid[column])
                    report["error_cells"] += int(isinstance(value, str) and value.startswith(("#REF!", "#N/A", "#VALUE!", "#DIV/0!")))
                nr = values[0]
                if math.isfinite(nr):
                    stats["source_nr_min"] = nr if stats["source_nr_min"] is None else min(nr, stats["source_nr_min"])
                    stats["source_nr_max"] = nr if stats["source_nr_max"] is None else max(nr, stats["source_nr_max"])
                    if previous_nr is not None and nr != previous_nr + 1:
                        report["source_nr_gaps"].append(dict(source_row=row_number,
                            previous_nr=previous_nr, nr=nr, gap=nr - previous_nr - 1))
                    previous_nr = nr
                if stats["duration_day_first"] is None:
                    stats["duration_day_first"] = raw[2]
                stats["duration_day_last"] = raw[2]
                stats["HRT_day_counts"][str(raw[5])] += 1
                # Pure numeric column relations. These are NOT inferred reactor volumes.
                for key, numerator, denominator in (("HPR_over_HP", values[12], raw[10]),
                        ("MPR_over_MP", values[14], raw[13]),
                        ("HY_times_OLR_over_HPR", raw[11] * raw[15], values[12])):
                    if isinstance(denominator, (int, float)) and denominator != 0:
                        stats["normalization_diagnostics"][key].append(numerator / denominator)
            check = component_production_check(block)
            for column, name in ((1, "HP"), (3, "MP")):
                valid = check.valid[:, column]
                residual = check.values[:, column]
                if np.any(valid):
                    report["max_component_residual_reported_L_per_day"] = max(
                        report["max_component_residual_reported_L_per_day"],
                        float(np.abs(residual[valid]).max()) / LITRE_PER_DAY_TO_M3_PER_S)
                for i in np.flatnonzero(valid & (np.abs(residual) > tolerance)):
                    report["component_inconsistencies"].append(dict(source_row=block.source_rows[i],
                        source_nr=block.raw_cells[i][0], reactor=block.reactor_id, field=name,
                        residual_reported_L_per_day=float(residual[i] / LITRE_PER_DAY_TO_M3_PER_S)))
            if np.any(check.valid[:, 4]):
                report["max_fraction_closure"] = max(report["max_fraction_closure"],
                    float(np.abs(check.values[check.valid[:, 4], 4]).max()))
        if report["source_rows"] != source.source_last_row - 1:
            raise ValueError("Source worksheet rows omitted")
    for stats in report["reactors"].values():
        stats["HRT_day_counts"] = dict(stats["HRT_day_counts"])
        for key, values in stats["normalization_diagnostics"].items():
            stats["normalization_diagnostics"][key] = dict(count=len(values),
                minimum=min(values) if values else None, maximum=max(values) if values else None,
                interpretation="numeric relation only; printed HPR/MPR units and physical denominator unresolved")
    report["canonical_normalized_rows_sha256"] = digest.hexdigest()
    report["invalid_reasons"] = dict(report["invalid_reasons"])
    report["source_end"] = fingerprints(root)
    if report["source_begin"] != report["source_end"] or file_sha256(receipt_path) != receipt_sha:
        raise ValueError("Executed source or receipt changed; replay required")
    report["elapsed_seconds"] = time.perf_counter() - started
    output = root / "data/processed/dark-fermentation/2/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    write_summary(root, report)
    print(f"Complete {report['source_rows']} rows / 24 columns in {report['elapsed_seconds']:.2f}s; "
          f"{len(report['component_inconsistencies'])} retained component-field inconsistencies; no kinetic fitting")


def write_summary(root, report):
    rows = report["source_rows"]
    unique_bad_rows = sorted({item["source_row"] for item in report["component_inconsistencies"]})
    lines = ["# Dark-fermentation v2 complete-source qualification", "",
        "Roberto Hernández, [Raw data, version 2](https://doi.org/10.17632/2nwcdx9hst.2), CC BY 4.0. "
        "The pinned metadata and actual acquired workbook were inspected read-only. This original "
        "audit reproduces no source prose, measured-data table, publication figure or source program.", "",
        f"Complete offline scan: {report['elapsed_seconds']:.2f}s. Workbook/publisher checksum, "
        "pinned and supporting metadata and source begin/end hashes matched. No formulas or "
        "links were executed, source rows changed, interpolated or repaired.", "",
        f"- Actual dimensions: {report['declared_dimensions'][0]} x {report['declared_dimensions'][1]}; "
        f"{rows} data rows / {rows * 24} source data cells.",
        f"- Cached numeric cells: {report['cached_numeric_cells']}; strict decimal numeric strings: {report['numeric_string_cells']}.",
        f"- Blank cells: {report['blank_cells']}; source `--` placeholders: {report['placeholder_cells']}.",
        f"- Valid numeric observations: {report['valid_numeric_cells']}; invalid reasons: {report['invalid_reasons']}.",
        f"- Source formula cells: {report['formula_cells']}; missing formula caches: {report['missing_formula_caches']}; error cells: {report['error_cells']}.",
        f"- Nonincreasing per-reactor Duration edges retained: {len(report['duplicate_duration_edges'])}.",
        f"- Source Nr discontinuities: {len(report['source_nr_gaps'])}; identifier skips total "
        f"{sum(item['gap'] for item in report['source_nr_gaps'])}. Missing identifiers do not create invented rows.", "",
        "| Source reactor label | Source rows | First/last worksheet row | Valid COD in/out cells | Valid other chemistry cells |",
        "|---|---:|---|---|---:|"]
    for name, reactor in report["reactors"].items():
        chemistry = reactor["valid_chemistry"]
        lines.append(f"| {name} | {reactor['rows']} | {reactor['first_source_row']}/{reactor['last_source_row']} | "
            f"{chemistry[0]}/{chemistry[1]} | {sum(chemistry[2:])} |")
    lines += ["", "R is retained as a reactor identifier; independent replicates or common forcing are "
        "not established. All reactors therefore share one study experiment group. Blocks do not "
        "mix reactor clock bases. Duration's declared days convert to seconds without assigning "
        "a common day-zero, event clock or correcting repeated days. Automatic TimeSeries conversion "
        "and independent reactor holdout claims are not supplied.", "",
        "## Same-export algebra, not biological validation", "",
        "The executable comparison operator checks HP against BP times reported H2 volume fraction "
        "and MP against BP times reported CH4 volume fraction on the same reported-volume convention. "
        "It retains source rows, masks and reconstructed origin. It supplies no mass/molar yield, "
        "gas reference state, physical reactor volume, kinetics or independent measured target.", "",
        f"At an explicitly declared algebraic tolerance of {report['component_tolerance_reported_L_per_day']} "
        f"reported L/d (not noise sigma), {len(report['component_inconsistencies'])} component fields "
        f"differ across source worksheet row(s) {unique_bad_rows}. Their values remain unaltered. "
        f"Maximum absolute residual: {report['max_component_residual_reported_L_per_day']:.12g} reported L/d.",
        f"The listed gas fractions close numerically with maximum absolute residual {report['max_fraction_closure']:.12g}. "
        "This does not establish wet/dry conditions, absence of other gases, ideal mixing or sensor accuracy.", "",
        "HP/HY/HPR/MP/MPR are publisher-derived/reconstructed fields even though stored as numbers "
        "rather than Excel formulas. HRT/OLR operating/derived provenance remains unresolved. HPR/MPR "
        "retain the literal printed L/(L/d) units; no denominator repair or physical volume is inferred. "
        "Per-reactor proportionality diagnostics and the numerical HY/OLR/HPR relation remain local "
        "source-consistency evidence, not an independent reactor volume or yield calibration.", "",
        "## Biological model applicability", "",
        "Metadata identifies pig manure and glucose qualitatively, without a resolved feed "
        "composition/species/COD mapping, added/consumed substrate yield denominator, biomass inventory, "
        "growth/decay observations or uncertainty. COD is not glucose or biomass mass; abbreviated "
        "acid labels do not supply species/speciation. BP/HP/MP are reported gas volume per day, "
        "not liquid flow or hydrogen mass flow. Gas reference P/T and wet/dry/collection conventions "
        "are unresolved. Temperature alone does not supply energy input, heat loss or reaction heat.", "",
        "A next native biological level needs finite liquid/substrate/biomass and gas states, explicit "
        "feed/withdrawal and pH-control histories, working/headspace volume, phase transfer, source "
        "species/stoichiometric/COD/element/charge bases, gas observation/reference operators and "
        "qualified initial conditions. Reuse the existing reaction-core balance contracts after "
        "species/empirical biomass composition is supplied; its prescribed stoichiometric conversion "
        "does not provide microbial kinetics. Fit no Monod growth or inhibition parameters from "
        "these gas/yield columns alone. No biological model family or independent validation is claimed.", "",
        "## Source and executed identities", "",
        f"- Workbook SHA-256: `{report['workbook_sha256']}` ({report['workbook_bytes']} bytes).",
        f"- Metadata SHA-256: `{report['metadata_sha256']}`.",
        f"- Receipt SHA-256: `{report['receipt_sha256']}`.",
        f"- Canonical normalized rows/masks/identities SHA-256: `{report['canonical_normalized_rows_sha256']}`.", "",
        "Executed source begin/end fingerprints matched; sources used LF.", ""]
    lines.extend(f"- `{name}`: `{digest}`" for name, digest in report["source_begin"].items())
    lines += ["", "Detailed source units/bases/origins, formula/cache metadata, reactor clocks, source "
        "row identities, missingness, consistency residuals and normalization diagnostics remain in "
        "ignored `data/processed/dark-fermentation/2/audit.json`. External raw and normalized records "
        "remain outside Git and distributions. The receipt retains `validation_qualified = false`.", ""]
    (root / "research/fermentation_data.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
