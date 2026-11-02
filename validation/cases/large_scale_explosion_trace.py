"""Full-stream schema and receipt ingestion for one WSKBIJ raw Test001 trace."""

import math
import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="large-scale-h2-test001-pressure-trace-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_test001",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/wskbij-explosion/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "large-scale-open-hydrogen-explosion.toml"),
        },
        invariants=(
            "the selected Test001 text member matches the official DataverseNO file ID, size, MD5 and local SHA-256",
            "source preamble retains the absolute time-format label and first-sample timestamp token separately from the trace Time column",
            "all nine reviewed channel names and units are retained and every row streams without normalization",
            "P01-P04 signed kPa values survive without clipping; PT1/PT2/MFR and camera-trigger volts remain raw",
            "source time remains monotone if the publisher records it monotonically; every source sample is consumed",
            "no pressure conversion, mass-flow calibration, sensor coordinate, model fit or consequence comparison is inferred",
        ),
    ),)


def validate_test001(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    from h2physics.data.wskbij_test001 import (
        DOI, FILE_ID, FILE_MD5, FILE_NAME, FILE_SHA256, FILE_SIZE_BYTES,
        LICENSE_ID, VERSION, read_wskbij_test001_trace,
    )

    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    candidate = next((item for item in record.get("selected_candidates", ())
                      if item.get("name") == FILE_NAME), None)
    if (record.get("doi") != DOI or record.get("version") != VERSION
            or record.get("license_id") != LICENSE_ID
            or record.get("rights_permitted") is not True
            or candidate is None or candidate.get("status") != "acquired"
            or candidate.get("persistent_id") != f"doi:{DOI}/PIQIIP"
            or candidate.get("file_id") != FILE_ID
            or candidate.get("size_bytes") != FILE_SIZE_BYTES
            or candidate.get("publisher_md5") != FILE_MD5
            or candidate.get("sha256") != FILE_SHA256):
        raise ValueError("WSKBIJ Test001 source manifest receipt changed")

    trace = read_wskbij_test001_trace(raw_data_root)
    last_time = None
    minimum_delta = math.inf
    maximum_delta = 0.
    two_microsecond_steps = 0
    interval_count = 0
    row_count = 0
    raw_width_counts = {9: 0, 10: 0}
    missing_counts = [0] * len(trace.columns)
    negative_pressure_counts = [0] * 4
    for sample in trace.iter_samples():
        row_count += 1
        raw_width_counts[len(sample.raw_tokens)] = raw_width_counts.get(len(sample.raw_tokens), 0) + 1
        values = (
            sample.source_time_s, *sample.pressure_channels_kpa,
            sample.upstream_pressure_1_v, sample.upstream_pressure_2_v,
            sample.mass_flow_meter_v, sample.camera_trigger_v,
        )
        for index, value in enumerate(values):
            if value is None:
                missing_counts[index] += 1
        for index, pressure in enumerate(sample.pressure_channels_kpa):
            if pressure is not None and pressure < 0.:
                negative_pressure_counts[index] += 1
        if last_time is not None:
            delta = sample.source_time_s - last_time
            if delta <= 0.:
                raise ValueError("WSKBIJ Test001 source time is not strictly increasing")
            minimum_delta = min(minimum_delta, delta)
            maximum_delta = max(maximum_delta, delta)
            interval_count += 1
            if math.isclose(delta, 2e-6, rel_tol=1e-9, abs_tol=1e-15):
                two_microsecond_steps += 1
        elif sample.source_time_s != 0.:
            raise ValueError("The first WSKBIJ trace time token changed from the reviewed zero origin")
        last_time = sample.source_time_s
    if row_count < 2 or interval_count != row_count-1:
        raise ValueError("WSKBIJ Test001 contains too few usable time-series rows")
    trace.require_current()
    return ValidationOutcome(True, {
        "doi": DOI,
        "version": VERSION,
        "license_id": LICENSE_ID,
        "file_id": FILE_ID,
        "file_name": FILE_NAME,
        "file_size_bytes": FILE_SIZE_BYTES,
        "publisher_md5": FILE_MD5,
        "file_sha256": FILE_SHA256,
        "source_time_format": trace.source_time_format,
        "first_sample_timestamp_token": trace.first_sample_timestamp_token,
        "columns": trace.columns,
        "unit_tokens": trace.unit_tokens,
        "header_line_number": trace.header_line_number,
        "source_row_count": row_count,
        "source_time_first_s": 0.,
        "source_time_last_s": last_time,
        "source_time_delta_min_s": minimum_delta,
        "source_time_delta_max_s": maximum_delta,
        "two_microsecond_interval_count": two_microsecond_steps,
        "raw_field_width_counts": raw_width_counts,
        "missing_signal_counts": tuple(missing_counts),
        "negative_pressure_value_counts_by_channel": tuple(negative_pressure_counts),
        "model_fit_or_comparison_executed": False,
    }, (
        "Dataset CC0 is declared at record scope; the file contains original measurement channels and the repository preserves attribution.",
        "The absolute timestamp is retained as source text and is not aligned to an external plant or model clock.",
        "PT1/PT2/MFR remain voltage channels. The README's formulas lack row-specific V0 records in this selected file; no conversion is applied.",
        "Pressure sensor coordinates, ignition geometry, calibration uncertainty, ambient history, source expansion mapping and a compatible explosion-pressure model remain unresolved.",
        "The source-side producer trace is not modified, and this schema ingestion is not physical validation.",
    ))
