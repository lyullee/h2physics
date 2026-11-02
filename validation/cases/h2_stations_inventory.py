"""Deferred H2-Stations source workbook identity and schema contract."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.h2_stations import (
    DATASET_KEY,
    LICENSE_ID,
    load_h2_stations_workbook,
)


def cases():
    return (ValidationCase(
        identifier="h2-stations-source-inventory-schema",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_station_inventory",
        parameters={
            "workbook_path": "/scratch/r1021a02/h2physics-source-attachments/"
                            "h2-stations/2026-10-31/hrs-list-2026-10-31.xlsx",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "h2-stations-hrs-inventory.toml"),
        },
        invariants=(
            "local-workbook-bytes-match-the-rolling-export-size-and-sha256-receipt",
            "one-worksheet-and-the-seven-reviewed-header-tokens-are-preserved",
            "every-workbook-row-retains-its-source-row-number-and-uninterpreted-cell-values",
            "source-view-currentness-detects-file-or-parsed-projection-mutation",
            "station-inventory-does-not-claim-fuelling-state-physical-performance-or-safety-validation",
        ),
    ),)


def validate_station_inventory(*, work_directory, workbook_path, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    if (manifest.get("key") != DATASET_KEY
            or manifest.get("license_id") != LICENSE_ID
            or manifest.get("schema_audit_status") != "workbook_structure_only"
            or manifest.get("qualification_status")
            != "source-bound operational inventory candidate; not process/safety validation data"):
        raise ValueError("H2-Stations source manifest identity, rights or scope changed")
    files = manifest.get("files", ())
    if len(files) != 1 or files[0].get("status") != "acquired":
        raise ValueError("H2-Stations manifest must retain its single acquired workbook")
    snapshot = load_h2_stations_workbook(
        workbook_path,
        expected_sha256=files[0]["sha256"],
        expected_size_bytes=files[0]["size_bytes"],
    )
    snapshot.require_current()
    if (snapshot.worksheet_row_count != 166
            or snapshot.worksheet_column_count != 7
            or len(snapshot.headers) != 7):
        raise AssertionError("H2-Stations rolling workbook schema differs from its receipt")
    return ValidationOutcome(True, {
        "dataset_key": snapshot.dataset_key,
        "license": snapshot.license_id,
        "sha256": snapshot.sha256,
        "bytes": snapshot.byte_count,
        "worksheet": snapshot.worksheet_name,
        "worksheet_rows_including_header": snapshot.worksheet_row_count,
        "station_rows_retained": len(snapshot.records),
        "columns": snapshot.headers,
        "model_validation_executed": False,
    }, (
        "The source is a rolling public station-list export without a publisher checksum or immutable release identifier.",
        "The workbook contains registry metadata only and does not provide fueling pressure, temperature, or mass-flow traces.",
        "Station status, capacity and physical performance are not inferred from registry text.",
    ))
