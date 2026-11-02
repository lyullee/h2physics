"""Deferred source-bound intake contract for hydrogen-channel release cases."""

import importlib
import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (
        ValidationCase(
            identifier="hydrogen-channel-v2-source-bound-table",
            profile="hydrogen-channel-data",
            entrypoint=__name__ + ":validate_source_table",
            parameters={
                "fixture_module": "validation.fixtures.hydrogen_channel",
                "fixture_builder": "build_hydrogen_channel_case_fixture",
            },
            invariants=(
                "publisher-size-and-checksum-required",
                "local-sha256-matches-pinned-receipt",
                "exactly-one-safe-csv-member-required",
                "two-original-header-rows-retained",
                "numeric-source-records-and-blank-mask-reconstruct",
                "source-record-identities-include-header-offset",
                "publisher-experiment-label-is-source-readme-lookup-only",
                "resolved-attachments-match-the-pinned-source-metadata-bytes",
                "forged-dataset-attachment-record-rejected",
                "source-bound-case-can-only-be-issued-by-the-checksum-validating-loader",
                "a copied case-cannot reseal a substituted source digest",
                "arrays-have-immutable-backing",
                "forged-direct-summary-rejected",
                "boolean-cells-cannot-enter-the-numeric-observation-view",
                "no-clock-alignment-or-physical-meaning-inferred",
            ),
        ),
        ValidationCase(
            identifier="hydrogen-channel-measured-finite-source-bridge",
            profile="source-data-ingestion",
            entrypoint=__name__ + ":validate_measured_finite_source_bridge",
            parameters={
                "fixture_module": "validation.fixtures.hydrogen_channel",
                "fixture_builder": "build_hydrogen_channel_case_fixture",
            },
            invariants=(
                "the publisher's exact flow time [s] and mass flow meter 1 [g/s] channels bind to measured finite H2 source bins",
                "the caller selects the interval quadrature and representative H2 thermodynamic state explicitly",
                "only the recorded flow-clock support is used, with no extrapolation and no sensor-clock alignment",
                "the source receipt retains archive/member hashes and is consumable by existing finite-source safety APIs",
            ),
        ),
    )


def validate_source_table(*, work_directory, **parameters):
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name or not isinstance(builder_name, str)
            or not builder_name.isidentifier()):
        raise ValueError("Configure an offline source-backed hydrogen-channel fixture")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Fixture must expose the configured builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {
        "dataset", "archive_path", "file_name", "expected_sha256",
    }:
        raise TypeError("Fixture must return Dataset, local ZIP, publisher filename and pinned local SHA-256")

    from h2physics.data import load_hydrogen_channel_case

    table = load_hydrogen_channel_case(
        fixture["archive_path"], dataset=fixture["dataset"], file_name=fixture["file_name"],
        expected_sha256=fixture["expected_sha256"],
    )
    assert table.source_doi == fixture["dataset"].doi
    if fixture["file_name"] == "23_FFI_P101_T00005.zip":
        assert table.publisher_experiment_label == "test-05-0C"
    remote = next(entry for entry in fixture["dataset"].files
                  if entry.name == fixture["file_name"])
    archive_bytes = Path(fixture["archive_path"]).read_bytes()
    assert table.publisher_checksum_algorithm == remote.checksum_algorithm
    assert table.publisher_checksum == remote.checksum
    assert hashlib.new(remote.checksum_algorithm, archive_bytes).hexdigest() == remote.checksum
    assert hashlib.sha256(archive_bytes).hexdigest() == table.source_sha256
    assert table.source_sha256 == fixture["expected_sha256"]
    assert len(table.column_names) == len(table.channel_descriptions)
    assert table.row_ids[0].endswith("record-3")
    assert np.array_equal(table.valid, np.isfinite(table.values))
    forged = table.values.copy()
    forged[0, 0] += 1.0
    rejected_forgery = False
    try:
        replace(table, values=forged)
    except ValueError:
        rejected_forgery = True
    assert rejected_forgery
    forged_receipt_rejected = False
    try:
        replace(table, source_sha256="0" * 64)
    except ValueError:
        forged_receipt_rejected = True
    assert forged_receipt_rejected
    rejected_boolean_values = False
    try:
        replace(table, values=np.zeros(table.values.shape, dtype=bool))
    except (TypeError, ValueError):
        rejected_boolean_values = True
    assert rejected_boolean_values
    forged_files = list(fixture["dataset"].files)
    index = next(i for i, item in enumerate(forged_files) if item.name == fixture["file_name"])
    item = forged_files[index]
    replacement_digest = ("0" if item.checksum[0] != "0" else "1") + item.checksum[1:]
    forged_files[index] = replace(item, checksum=replacement_digest)
    forged_dataset = replace(fixture["dataset"], files=tuple(forged_files))
    rejected_attachment_forgery = False
    try:
        load_hydrogen_channel_case(
            fixture["archive_path"], dataset=forged_dataset,
            file_name=fixture["file_name"], expected_sha256=fixture["expected_sha256"],
        )
    except ValueError:
        rejected_attachment_forgery = True
    assert rejected_attachment_forgery
    rejected_write_enable = False
    try:
        table.values.setflags(write=True)
    except ValueError:
        rejected_write_enable = True
    assert rejected_write_enable and table.require_current() is table
    return ValidationOutcome(True, {
        "rows": len(table.row_ids), "columns": len(table.column_names),
        "valid_cells": int(np.count_nonzero(table.valid)),
        "archive_sha256": table.source_sha256,
        "member_sha256": table.member_sha256,
        "forged_source_digest_rejected": forged_receipt_rejected,
        "boolean_numeric_view_rejected": rejected_boolean_values,
    }, (
        "Source quantities remain raw columns; flow/sensor clocks are not aligned.",
        "This checks source-preserving ingestion only, not a dispersion comparison or model validation.",
    ))


def validate_measured_finite_source_bridge(*, work_directory, **parameters):
    fixture = _fixture(work_directory, parameters)
    from h2physics.adapters.hydrogen_channel_source import project_hydrogen_channel_finite_source
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.data import load_hydrogen_channel_case
    from h2physics.release import SourceLocation

    case = load_hydrogen_channel_case(
        fixture["archive_path"], dataset=fixture["dataset"], file_name=fixture["file_name"],
        expected_sha256=fixture["expected_sha256"],
    )
    state = ThermoState(
        PropertyBasis("Hydrogen", "caller-synthetic-reference", "normal"),
        101325., 298.15, 0.08, 0., 0., 0., "gas",
    )
    location = SourceLocation("fixture-release", "flow-clock-s", "fixture-frame",
                              (0., 0., 0.), (0., 0., 1.))
    projection = project_hydrogen_channel_finite_source(
        case, location=location, representative_state=state, flow_rule="trapezoid",
        state_projection_evidence_id="fixture-only-representative-state",
    )
    projection.require_current()
    assert projection.time_column == "flow time [s]"
    assert projection.flow_column == "mass flow meter 1 [g/s]"
    assert projection.source.origin.value == "measured"
    assert projection.source.edges_s[0] == projection.time_s[0]
    assert projection.source.edges_s[-1] == projection.time_s[-1]
    assert len(projection.source.mass_kg) == len(projection.time_s)-1
    assert projection.source.total_mass_kg >= 0.
    return ValidationOutcome(True, {
        "intervals": len(projection.source.mass_kg),
        "time_window_s": float(projection.time_s[-1]-projection.time_s[0]),
        "measured_total_h2_kg": projection.source.total_mass_kg,
        "archive_sha256": projection.source_sha256,
        "member_sha256": projection.member_sha256,
        "source_origin": projection.source.origin.value,
    }, (
        "Deferred fixture-backed bridge contract; not run locally in this task.",
        "The representative state and trapezoid quadrature are explicit fixture choices, not measured state/calibration claims.",
        "Only flow-clock support is used; pressure basis and sensor-clock alignment are not inferred.",
    ))


def _fixture(work_directory, parameters):
    import importlib
    module_name = parameters.get("fixture_module")
    builder_name = parameters.get("fixture_builder")
    if (not isinstance(module_name, str) or not module_name.strip()
            or "REPLACE_WITH" in module_name or not isinstance(builder_name, str)
            or not builder_name.isidentifier()):
        raise ValueError("Configure an offline source-backed hydrogen-channel fixture")
    module = importlib.import_module(module_name)
    builder = getattr(module, builder_name, None)
    if not callable(builder):
        raise ValueError("Fixture must expose the configured hydrogen-channel case builder")
    fixture = builder(work_directory=work_directory, parameters=parameters)
    if not isinstance(fixture, dict) or set(fixture) != {
        "dataset", "archive_path", "file_name", "expected_sha256",
    }:
        raise TypeError("Fixture must return dataset, archive, file name and pinned archive SHA-256")
    return fixture
