"""Deferred identity and cell-lineage ingestion case for the AEM workbook."""

import os
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

_DEFAULT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data" / "raw" / "aem-water-electrolysis-crossover" / "20068087"
)


def cases():
    staged_root = os.environ.get("H2_AEM_ELECTROLYSIS_DATA_ROOT")
    directory = Path(staged_root) if staged_root else _DEFAULT_DIRECTORY
    return (ValidationCase(
        identifier="aem-water-electrolysis-crossover-ingestion",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_workbook",
        parameters={"data_directory": str(directory)},
        invariants=(
            "Zenodo-v1-open-CC-BY-4.0-workbook-and-record-metadata-match-the-pinned-receipt",
            "all-six-worksheet-names-dimensions-and-cell-positions-match-the-source-workbook",
            "cell-values-formula-text-data-types-and-number-formats-are-retained-without-conversion",
            "source-cell-references-remain-accessible-by-worksheet-and-original-A1-coordinate",
            "no-polarization-or-crossover-fitting-calibration-unit-conversion-or-validation-is-performed",
        ),
    ),)


def validate_source_workbook(*, work_directory, data_directory):
    del work_directory
    from h2physics.data.aem_water_electrolysis import (
        ATTRIBUTION,
        DOI,
        LICENSE_ID,
        METADATA_SHA256,
        VERSION,
        WORKBOOK_MD5,
        WORKBOOK_SHA256,
        load_aem_electrolysis_workbook,
    )

    workbook = load_aem_electrolysis_workbook(data_directory)
    workbook.require_current()
    if (workbook.doi != DOI or workbook.version != VERSION
            or workbook.license_id != LICENSE_ID or workbook.attribution != ATTRIBUTION
            or workbook.publisher_md5 != WORKBOOK_MD5 or workbook.sha256 != WORKBOOK_SHA256
            or workbook.metadata_sha256 != METADATA_SHA256):
        raise ValueError("AEM workbook provenance differs from its source receipt")

    cell_count = 0
    nonempty_cell_count = 0
    formula_count = 0
    dimensions = {}
    first_cells = {}
    for name, sheet in workbook.worksheets.items():
        if (len(sheet.rows) != sheet.max_row
                or any(len(row) != sheet.max_column for row in sheet.rows)
                or len(sheet.data_types) != sheet.max_row
                or len(sheet.number_formats) != sheet.max_row):
            raise ValueError("AEM worksheet cell grid no longer matches its source dimensions")
        first = sheet.cell(1, 1)
        if first.worksheet_name != name or first.coordinate != "A1":
            raise ValueError("AEM cell address lineage does not resolve to source cell A1")
        dimensions[name] = (sheet.max_row, sheet.max_column)
        first_cells[name] = first.data_type
        cell_count += sheet.max_row * sheet.max_column
        for values, data_types in zip(sheet.rows, sheet.data_types, strict=True):
            nonempty_cell_count += sum(value is not None for value in values)
            formula_count += sum(cell_type == "f" for cell_type in data_types)

    workbook.require_current()
    return ValidationOutcome(True, {
        "doi": workbook.doi,
        "version": workbook.version,
        "license_id": workbook.license_id,
        "file_name": workbook.source_path.name,
        "byte_size": workbook.byte_size,
        "publisher_md5": workbook.publisher_md5,
        "workbook_sha256": workbook.sha256,
        "metadata_sha256": workbook.metadata_sha256,
        "worksheet_dimensions": dimensions,
        "worksheet_A1_data_types": first_cells,
        "source_cell_positions_preserved": cell_count,
        "nonempty_cell_values_preserved": nonempty_cell_count,
        "formula_cells_retained_without_evaluation": formula_count,
        "unit_conversion": False,
        "parameter_fitting_or_calibration": False,
        "physical_validation_claim": False,
    }, (
        "This case checks acquisition identity, workbook schema, and cell lineage only.",
        "No AEM polarization or hydrogen-crossover model is fitted or validated.",
    ))
