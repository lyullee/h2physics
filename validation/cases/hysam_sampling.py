"""Deferred source-bound schema contract for the HySaM sampling-system data."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


SOURCE_ROOT = "/scratch/r1021a02/h2physics-source-attachments/hysam-sampling-system/v1.0"
FILES = (
    ("20241023_Test_1_HySaM.xlsx", 6601, 23),
    ("20241023_Test_4_HySaM_CESAME.xlsx", 721, 14),
    ("20241024_Test_9_HySaM.xlsx", 2161, 21),
)


def cases():
    return (ValidationCase(
        identifier="hysam-source-bound-workbook-schema",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_workbooks",
        parameters={"source_root": SOURCE_ROOT},
        invariants=(
            "each workbook is admitted only with the Zenodo v1.0 publisher MD5, exact bytes and local SHA-256",
            "the three single-sheet workbooks retain their audited row and column dimensions and original header row",
            "workbook currentness rejects changed publisher files after admission",
            "sensor tags, units, pressure basis, clock origin and sampling-system boundary are not inferred",
            "the case checks data identity and schema only; it does not validate a transfer model or sampling instrument",
        ),
    ),)


def validate_source_workbooks(*, work_directory, source_root):
    """Verify staged source bytes and workbook schema; do not interpret values."""
    del work_directory
    from h2physics.data.hysam_sampling import (
        DATASET_DOI,
        LICENSE_ID,
        METADATA_SHA256,
        load_hysam_workbook,
    )

    root = Path(source_root)
    receipts = []
    for filename, rows, columns in FILES:
        workbook = load_hysam_workbook(root / filename)
        workbook.require_current()
        if (workbook.doi != DATASET_DOI or workbook.license_id != LICENSE_ID
                or workbook.metadata_sha256 != METADATA_SHA256
                or workbook.row_count != rows or workbook.column_count != columns
                or workbook.headers[0] != "Zeit"):
            raise AssertionError("HySaM source identity or audited workbook schema changed")
        receipts.append((workbook.filename, workbook.sha256, workbook.row_count,
                         workbook.column_count, len(workbook.rows)))
    if len(receipts) != 3 or sum(item[4] for item in receipts) != 9480:
        raise AssertionError("The expected three-workbook HySaM source subset was not retained")
    return ValidationOutcome(True, {
        "doi": DATASET_DOI,
        "license_id": LICENSE_ID,
        "metadata_sha256": METADATA_SHA256,
        "files": len(receipts),
        "data_rows_after_header": sum(item[4] for item in receipts),
        "schema": tuple(receipts),
    }, (
        "Publisher-byte ingestion and schema check only; no numerical model is called.",
        "The dataset record and workbooks provide no complete sensor dictionary or unit/calibration mapping; no physical qualification is claimed.",
    ))
