"""Deferred ingestion contract for the pinned WSKBIJ Test001 pressure trace."""

from __future__ import annotations

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.wskbij_test001 import (
    DOI,
    FILE_MD5,
    FILE_NAME,
    FILE_SHA256,
    FILE_SIZE_BYTES,
    LICENSE_ID,
    VERSION,
    read_wskbij_test001_trace,
)


def cases():
    return (
        ValidationCase(
            identifier="large-scale-h2-explosion-test001-source-ingestion",
            profile="source-data-ingestion",
            entrypoint=__name__ + ":validate_test001",
            parameters={
                "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/wskbij-explosion/1",
            },
            invariants=(
                "the selected Test001 source retains exact publisher MD5, byte-size, and SHA-256 receipts",
                "absolute first-sample timestamp token remains separate from elapsed sample seconds",
                "the reviewed nine-column schema and source unit tokens are preserved while rows stream without resampling",
                "PT1/PT2/MFR/camera-trigger channels remain voltage observations without an inferred calibration",
                "source row and nonmissing channel counts are reported as ingestion evidence only",
                "no pressure-to-FDS, flame-acceleration, or explosion-consequence comparison is performed",
            ),
        ),
    )


def validate_test001(*, work_directory, raw_data_root):
    del work_directory
    trace = read_wskbij_test001_trace(Path(raw_data_root))
    if (
        trace.doi != DOI
        or trace.license_id != LICENSE_ID
        or trace.size_bytes != FILE_SIZE_BYTES
        or trace.publisher_md5 != FILE_MD5
        or trace.sha256 != FILE_SHA256
        or trace.source_time_format != "Absolute"
        or trace.columns
        != ("Time", "P01", "P02", "P03", "P04", "PT1", "PT2", "MFR", "Trigger cam")
        or trace.unit_tokens != ("s", "kPa", "kPa", "kPa", "kPa", "V", "v", "V", "V")
    ):
        raise ValueError("WSKBIJ Test001 identity, timestamp, or reviewed channel schema changed")

    row_count = 0
    pressure_observation_count = 0
    voltage_observation_count = 0
    first_elapsed_s = None
    last_elapsed_s = None
    first_sample_timestamp_token = trace.first_sample_timestamp_token
    for sample in trace.iter_samples():
        row_count += 1
        if first_elapsed_s is None:
            first_elapsed_s = sample.source_time_s
        last_elapsed_s = sample.source_time_s
        pressure_observation_count += sum(value is not None for value in sample.pressure_channels_kpa)
        voltage_observation_count += sum(
            value is not None
            for value in (
                sample.upstream_pressure_1_v,
                sample.upstream_pressure_2_v,
                sample.mass_flow_meter_v,
                sample.camera_trigger_v,
            )
        )

    # iter_samples rechecks after full exhaustion; assert the final receipt
    # explicitly at the case boundary as part of the ingestion result.
    trace.require_current()

    if row_count == 0 or first_elapsed_s is None or last_elapsed_s is None:
        raise ValueError("Pinned WSKBIJ Test001 contains no streamed sample rows")
    if not first_sample_timestamp_token.strip():
        raise ValueError("WSKBIJ absolute first-sample timestamp token is empty")

    return ValidationOutcome(
        True,
        {
            "doi": DOI,
            "version": VERSION,
            "license_id": LICENSE_ID,
            "file_name": FILE_NAME,
            "file_size_bytes": trace.size_bytes,
            "publisher_md5": trace.publisher_md5,
            "sha256": trace.sha256,
            "source_time_format": trace.source_time_format,
            "first_sample_timestamp_token": first_sample_timestamp_token,
            "source_elapsed_first_s": first_elapsed_s,
            "source_elapsed_last_s": last_elapsed_s,
            "columns": trace.columns,
            "unit_tokens": trace.unit_tokens,
            "source_header_line_number": trace.header_line_number,
            "streamed_row_count": row_count,
            "pressure_observation_count": pressure_observation_count,
            "voltage_observation_count_uncalibrated": voltage_observation_count,
            "voltage_channel_calibration_applied": False,
            "quantitative_model_comparison_performed": False,
        },
        (
            "The absolute start-time token and per-row elapsed seconds are retained as distinct source fields.",
            "The four pressure channels are source observations; the four voltage channels remain uncalibrated.",
            "This case checks byte identity and streaming schema only; it does not validate an explosion or FDS model.",
        ),
    )
