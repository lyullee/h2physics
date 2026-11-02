"""Deferred source-bound ingestion contract for the buried-pipeline V2 data."""

import importlib
from dataclasses import replace

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="buried-pipeline-v2-lossless-ingest",
            profile="buried-pipeline-data",
            entrypoint=__name__ + ":validate_numeric_table_ingest",
            parameters={
                "fixture_module": "REPLACE_WITH_BURIED_PIPELINE_DATA_FIXTURE_MODULE",
                "fixture_builder": "build_buried_pipeline_table_fixture",
            },
            invariants=(
                "publisher-file-sha256-required",
                "publisher-file-size-required",
                "publisher-filename-unambiguous",
                "version-two-and-license-bound",
                "pinned-repository-metadata-receipt-required",
                "resolved-files-must-match-pinned-publisher-listing",
                "headerless-columns-remain-anonymous",
                "blank-cells-retain-invalid-mask-and-exact-token",
                "source-row-identities-are-one-based",
                "direct-table-summary-must-reconstruct-from-retained-tokens",
                "source-bound-tables-are-issued-only-by-the-checksum-validating-loader",
                "a copied table cannot reseal a substituted publisher digest",
                "loaded-arrays-use-immutable-backing",
            ),
        ),
        ValidationCase(
            identifier="buried-pipeline-v2-column-lineage-projection",
            profile="buried-pipeline-data",
            entrypoint=__name__ + ":validate_column_projection",
            parameters={
                "fixture_module": "REPLACE_WITH_BURIED_PIPELINE_DATA_FIXTURE_MODULE",
                "fixture_builder": "build_buried_pipeline_table_fixture",
                "column_name": "source_column_1",
            },
            invariants=(
                "projection-retains-publisher-file-hash-and-anonymous-source-label",
                "projected-values-mask-and-exact-decoded-tokens-reconstruct",
                "source-row-identities-remain-exact-and-ordered",
                "projected-arrays-remain-immutable",
                "a copied projection cannot reseal a substituted publisher digest",
                "projection-adds-no-physical-meaning-unit-or-clock",
            ),
        ),
    )


def validate_numeric_table_ingest(*, work_directory, **parameters):
    """Use a configured offline receipt fixture; never fetch dataset files here."""
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name
            or not isinstance(builder_name, str) or not builder_name.isidentifier()):
        raise ValueError("Configure an offline V2 dataset fixture and builder")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Dataset fixture must expose the configured builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {"dataset", "path", "file_name"}:
        raise TypeError("Fixture must return the original Dataset, local file path and listed filename")

    from h2physics.data import load_buried_pipeline_numeric_table

    table = load_buried_pipeline_numeric_table(
        fixture["path"], dataset=fixture["dataset"], file_name=fixture["file_name"])
    import hashlib

    forged_metadata = replace(
        fixture["dataset"], metadata_bytes=b"{}",
        metadata_sha256=hashlib.sha256(b"{}").hexdigest(),
    )
    try:
        load_buried_pipeline_numeric_table(
            fixture["path"], dataset=forged_metadata, file_name=fixture["file_name"])
    except ValueError:
        pass
    else:
        raise AssertionError("Loader accepted a nonpinned repository metadata receipt")
    altered_files = list(fixture["dataset"].files)
    altered_files[0] = replace(altered_files[0], checksum="0" * 64)
    forged_listing = replace(fixture["dataset"], files=tuple(altered_files))
    try:
        load_buried_pipeline_numeric_table(
            fixture["path"], dataset=forged_listing, file_name=fixture["file_name"])
    except ValueError:
        pass
    else:
        raise AssertionError("Loader accepted resolved files that differ from publisher listing")
    assert table.source_id == fixture["dataset"].doi
    assert table.source_sha256 == next(
        item.checksum for item in fixture["dataset"].files
        if item.name == fixture["file_name"])
    assert table.column_names == tuple(
        f"source_column_{index}" for index in range(1, table.values.shape[1] + 1))
    assert table.row_ids[0].endswith(":row-1")
    assert np.array_equal(table.valid, np.isfinite(table.values))
    forged = table.values.copy()
    forged[0, 0] += 1.0
    rejected_forgery = False
    try:
        replace(table, values=forged)
    except ValueError:
        rejected_forgery = True
    assert rejected_forgery
    try:
        replace(table, source_sha256="0" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("A copied table resealed a forged publisher digest")
    rejected_write_enable = False
    try:
        table.values.setflags(write=True)
    except ValueError:
        rejected_write_enable = True
    assert rejected_write_enable
    assert table.require_current() is table
    return ValidationOutcome(True, {
        "rows": len(table.row_ids), "anonymous_columns": len(table.column_names),
        "valid_cells": int(np.count_nonzero(table.valid)),
        "source_sha256": table.source_sha256,
        "write_enable_rejected": rejected_write_enable,
        "post_load_mutation_prevented": rejected_write_enable,
    }, (
        "Headerless source columns remain anonymous and carry no inferred units or physical meaning.",
        "Offline source-file fixture only; no model fit, prediction or scientific validation is performed.",
    ))


def validate_column_projection(*, work_directory, **parameters):
    """Check a lineage-preserving view using only a locally staged receipt fixture."""
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    column_name = parameters.get("column_name", "source_column_1")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name
            or not isinstance(builder_name, str) or not builder_name.isidentifier()
            or not isinstance(column_name, str) or not column_name.strip()):
        raise ValueError("Configure the offline source fixture and anonymous column name")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Dataset fixture must expose the configured builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {"dataset", "path", "file_name"}:
        raise TypeError("Fixture must return the original Dataset, local file path and listed filename")
    from h2physics.data import load_buried_pipeline_numeric_table

    table = load_buried_pipeline_numeric_table(
        fixture["path"], dataset=fixture["dataset"], file_name=fixture["file_name"])
    series = table.column_series(column_name)
    index = table.column_names.index(column_name)
    expected_tokens = tuple(row[index] if index < len(row) else "" for row in table.raw_fields)
    assert series.source_id == table.source_id
    assert series.source_file == table.source_file
    assert series.source_sha256 == table.source_sha256
    assert series.row_ids == table.row_ids
    assert series.raw_tokens == expected_tokens
    assert np.array_equal(series.values, table.values[:, index], equal_nan=True)
    assert np.array_equal(series.valid, table.valid[:, index])
    rejected_write_enable = False
    try:
        series.values.setflags(write=True)
    except ValueError:
        rejected_write_enable = True
    assert rejected_write_enable
    assert series.require_current() is series
    try:
        replace(series, source_sha256="0" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("A copied column projection resealed a forged publisher digest")
    return ValidationOutcome(True, {
        "rows": len(series.row_ids), "column_name": series.column_name,
        "valid_cells": int(np.count_nonzero(series.valid)),
        "source_sha256": series.source_sha256,
        "immutable_projection": rejected_write_enable,
    }, (
        "Projection preserves positional source identity only; it does not imply column units, clocks or physical meaning.",
        "Offline file-level contract only; no model fit, prediction or validation is performed.",
    ))
