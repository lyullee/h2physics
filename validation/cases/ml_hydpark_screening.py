"""Deferred source-ingestion contract for the curated ML-HydPARK table."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    default_dir = (Path(__file__).resolve().parents[2] / "data" / "raw"
                   / "ml-hydpark-screening" / "0.0.5")
    return (ValidationCase(
        identifier="ml-hydpark-curated-material-screening-ingestion",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_table",
        parameters={"data_directory": str(default_dir)},
        invariants=(
            "the Zenodo v0.0.5 file, CC BY 4.0 grant and source metadata hashes match their receipt",
            "all 772 CSV data records retain 13 original text tokens in source order",
            "empty fields and duplicate index tokens remain unchanged",
            "source composition, capacity and thermodynamic labels are not converted or fitted",
            "curated screening records are not reported as independent experimental validation",
        ),
    ),)


def validate_source_table(*, work_directory, data_directory):
    from h2physics.data.ml_hydpark import load_ml_hydpark_screening

    del work_directory
    table = load_ml_hydpark_screening(data_directory)
    if len(table.rows) != 772 or len(table.headers) != 13:
        raise AssertionError("ML-HydPARK source row/column count changed")
    if any(len(row.raw_tokens) != 13 for row in table.rows):
        raise AssertionError("Every ML-HydPARK source record must retain 13 CSV tokens")
    if table.headers[0] != "" or table.headers[-1] != "Reference":
        raise AssertionError("Preserve the empty first header and source Reference column")
    table.require_current()
    empty_cells = sum(token == "" for row in table.rows for token in row.raw_tokens)
    repeated_record_indices = len(table.rows) - len({row.token("index") for row in table.rows})
    return ValidationOutcome(True, {
        "source_doi": table.doi,
        "source_version": table.version,
        "license_id": table.license_id,
        "publisher_md5": table.publisher_md5,
        "csv_sha256": table.sha256,
        "metadata_sha256": table.metadata_sha256,
        "rows": len(table.rows),
        "columns": len(table.headers),
        "empty_source_cells_preserved": empty_cells,
        "duplicate_index_tokens_preserved": repeated_record_indices,
        "numeric_conversion": False,
        "parameter_fitting": False,
        "experimental_validation_claim": False,
    }, (
        "Source-ingestion integrity only. This is a curated material screening table, "
        "not a raw PCT dataset or independent validation of a hydrogen-storage model.",
    ))
