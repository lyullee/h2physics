"""Deferred, rights-aware local-file ingestion cases for AM316L workbooks."""

import os
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.am316l_workbooks import (
    ATTRIBUTION,
    DOI,
    LICENSE_ID,
    read_am316l_workbook,
)


def cases():
    profile = "source-data-ingestion"
    staged_root = os.environ.get("H2_AM316L_RAW_DATA_ROOT")
    parameters = {} if not staged_root else {"raw_data_root": staged_root}
    common = (
        "publisher-MD5-and-pinned-SHA-256-are-verified-before-and-after-reading",
        "original-worksheet-names-cell-values-and-cell-positions-are-preserved",
        "formula-text-is-retained-without-evaluation-and-headers-are-never-guessed",
        "no-units-specimen-pairings-calibrations-or-derived-material-summaries-are-inferred",
        "source-DOI-CC-BY-4.0-and-attribution-remain-attached-to-the-snapshot",
    )
    return (
        ValidationCase(
            identifier="am316l-tensile-workbook-source-ingestion",
            profile=profile,
            entrypoint=__name__ + ":validate_tensile_workbook",
            parameters=parameters,
            invariants=common,
        ),
        ValidationCase(
            identifier="am316l-hardness-workbook-source-ingestion",
            profile=profile,
            entrypoint=__name__ + ":validate_hardness_workbook",
            parameters=parameters,
            invariants=common,
        ),
    )


def _data_root(raw_data_root):
    if raw_data_root is None:
        # Local checkout fallback. Remote runners should pass the staged raw-data root.
        root = (Path(__file__).resolve().parents[2] / "research" / "data" / "payload"
                / "am-316l-hydrogen-embrittlement")
    else:
        root = Path(raw_data_root)
    if not root.is_dir():
        raise ValueError(
            "AM316L raw_data_root is absent: stage payload paths from "
            "research/data/am-316l-hydrogen-embrittlement.toml and pass their directory"
        )
    return root


def _validate(*, work_directory, raw_data_root, file_name):
    del work_directory
    snapshot = read_am316l_workbook(_data_root(raw_data_root), file_name)
    snapshot.require_current()
    if (snapshot.doi != DOI or snapshot.license_id != LICENSE_ID
            or snapshot.attribution != ATTRIBUTION or snapshot.file_name != file_name
            or not snapshot.worksheets):
        raise ValueError("AM316L workbook identity, rights, or worksheet snapshot changed")
    for sheet in snapshot.worksheets.values():
        if len(sheet.rows) != sheet.max_row or any(
                len(row) != sheet.max_column for row in sheet.rows):
            raise ValueError("AM316L worksheet cell grid does not match stored dimensions")
        if sheet.header_row_number is not None and sheet.header_values != sheet.rows[
                sheet.header_row_number - 1]:
            raise ValueError("AM316L declared header differs from its original cell row")
    return ValidationOutcome(True, {
        "doi": snapshot.doi,
        "version": snapshot.version,
        "license_id": snapshot.license_id,
        "license_url": snapshot.license_url,
        "attribution": snapshot.attribution,
        "file_name": snapshot.file_name,
        "byte_size": snapshot.byte_size,
        "publisher_md5": snapshot.publisher_md5,
        "sha256": snapshot.sha256,
        "source_url": snapshot.source_url,
        "worksheet_names": tuple(snapshot.worksheets),
        "worksheet_dimensions": {
            name: (sheet.max_row, sheet.max_column)
            for name, sheet in snapshot.worksheets.items()
        },
        "unit_conversions_or_material_summaries_applied": False,
    }, (
        "This case verifies local source bytes, workbook cell preservation, and dataset attribution only.",
        "The source does not establish specimen pairing, units, hydrogen content, or constitutive-model validity.",
    ))


def validate_tensile_workbook(*, work_directory, raw_data_root=None):
    return _validate(work_directory=work_directory, raw_data_root=raw_data_root,
                     file_name="Tensile tests.xlsx")


def validate_hardness_workbook(*, work_directory, raw_data_root=None):
    return _validate(work_directory=work_directory, raw_data_root=raw_data_root,
                     file_name="Hardness.xlsx")
