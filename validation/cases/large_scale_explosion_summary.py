"""Hangang ingestion contract for the selected WSKBIJ source summary."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.wskbij_summary import (
    DOI,
    LICENSE_ID,
    README_MD5,
    README_NAME,
    README_SHA256,
    README_SIZE_BYTES,
    WORKBOOK_MD5,
    WORKBOOK_NAME,
    WORKBOOK_SHA256,
    WORKBOOK_SIZE_BYTES,
    read_wskbij_experiment_summary,
)
from h2physics.data.wskbij_test001 import (
    FILE_MD5,
    FILE_NAME,
    FILE_SHA256,
    FILE_SIZE_BYTES,
)


def cases():
    return (ValidationCase(
        identifier="large-scale-h2-explosion-summary-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_summary",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/wskbij-explosion/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "large-scale-open-hydrogen-explosion.toml"),
        },
        invariants=(
            "the case reads the official CC0 README and workbook while validating the complete three-file acquisition manifest",
            "test number, reported nozzle/pressure fields, ignition code and four pressure summary channels retain source units",
            "signed pressure summary values remain raw and are not clipped or reinterpreted as a pressure history",
            "no source-to-FDS or explosion-overpressure comparison is made from workbook summary rows",
            "missing ambient, sensor-coordinate, and transient source evidence remains explicit",
        ),
    ),)


def validate_summary(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != DOI or record.get("version") != "1.0"
            or record.get("license_id") != LICENSE_ID
            or record.get("rights_permitted") is not True
            or record.get("acquisition_status") != "readme_summary_and_test001_trace_acquired"
            or record.get("model_linkage_status")
            != "raw_single_trace_ingested_no_quantitative_model_comparison"):
        raise ValueError("WSKBIJ source identity, license or selected acquisition scope changed")
    candidates = {item.get("name"): item for item in record.get("selected_candidates", ())}
    expected_candidates = {
        README_NAME: (README_SIZE_BYTES, README_MD5, README_SHA256),
        WORKBOOK_NAME: (WORKBOOK_SIZE_BYTES, WORKBOOK_MD5, WORKBOOK_SHA256),
        FILE_NAME: (FILE_SIZE_BYTES, FILE_MD5, FILE_SHA256),
    }
    acquired = tuple(item for item in record.get("selected_candidates", ())
                     if item.get("status") == "acquired")
    acquired_bytes = sum(item.get("size_bytes", 0) for item in acquired)
    if (set(candidates) != set(expected_candidates)
            or record.get("acquired_bytes") != acquired_bytes
            or acquired_bytes != sum(size for size, _, _ in expected_candidates.values())):
        raise ValueError("WSKBIJ acquired-file inventory or byte total changed")
    for name, (expected_size, expected_md5, expected_sha) in expected_candidates.items():
        item = candidates.get(name)
        if (item is None or item.get("status") != "acquired"
                or item.get("size_bytes") != expected_size
                or item.get("publisher_md5") != expected_md5
                or item.get("sha256") != expected_sha):
            raise ValueError("WSKBIJ selected file receipt differs from the source manifest")
    sample = read_wskbij_experiment_summary(raw_data_root)
    sample.require_current()
    if sample.workbook_sha256 != WORKBOOK_SHA256:
        raise ValueError("WSKBIJ experiment summary is not the pinned workbook")
    row = sample.rows[0]
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_id": LICENSE_ID,
        "case_read_scope": (README_NAME, WORKBOOK_NAME),
        "manifest_acquired_files": tuple(sorted(candidates)),
        "manifest_acquired_bytes": acquired_bytes,
        "test001_raw_trace_ingestion_is_separate": True,
        "workbook_sha256": sample.workbook_sha256,
        "summary_rows": len(sample.rows),
        "first_test_number": row.test_number,
        "first_nozzle_diameter_mm": row.nozzle_diameter_mm,
        "first_reservoir_pressure_bar_reported": row.reservoir_pressure_bar_reported,
        "first_ignition_position_code": row.ignition_position_code,
        "first_pressure_sensor_summary_kpa": row.pressure_sensor_summary_kpa,
        "model_comparison_executed": False,
    }, (
        "The workbook contains per-test pressure summary values, not time-resolved pressure traces.",
        "The README provides synchronized acquisition context, but no ambient history or absolute pressure-sensor coordinates.",
        "This case qualifies byte/schema ingestion only and does not validate FDS, flame acceleration or explosion pressure.",
    ))
