"""Hangang source-ingestion contract for the Empa leaky-coating dataset."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.leaky_coating_sorption import (
    SOURCE_DOI, read_leaky_coating_sorption_data,
)


def cases():
    return (ValidationCase(
        identifier="pd-leaky-coating-sorption-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_sorption_source",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/leaky-coating-hydride-sorption/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "leaky-coating-hydride-sorption.toml"),
        },
        invariants=(
            "all four selected Zenodo CC BY 4.0 source files match exact publisher size, MD5 and local SHA-256 receipts",
            "feed-pressure-delta and UHV-MS traces preserve their source channel and clock structures",
            "raw time/value pairs preserve every source token, including -- missing-time and missing-value markers",
            "the numeric view contains only complete pairs and reports exact counts for missing token types",
            "signed mbar signal values remain source observations and are not converted to absolute feed pressure or solid concentration",
            "no diffusion/hydride model fitting or comparison is executed",
        ),
    ),)


def validate_sorption_source(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != SOURCE_DOI
            or record.get("license_id") != "CC-BY-4.0"
            or record.get("acquisition_status") != "selected_figure4_source_traces_acquired"
            or len(record.get("files", ())) != 4
            or record.get("model_linkage_status") != "source_observations_only_no_model_fit"):
        raise ValueError("Leaky-coating source manifest identity, rights or scope changed")
    data = read_leaky_coating_sorption_data(raw_data_root)
    data.require_current()
    if (data.source_pair_count != 59328
            or data.missing_time_token_count != 1785
            or data.missing_value_token_count != 137
            or data.incomplete_pair_count != 1922):
        raise AssertionError("Leaky-coating raw source pairs or missing-token counts changed")
    if any(len(trace.source_pairs) < len(trace.time_s) for trace in data.traces):
        raise AssertionError("Raw source pair records were dropped from a numeric trace")
    by_key = {}
    for trace in data.traces:
        key = (trace.figure, trace.signal)
        by_key[key] = by_key.get(key, 0) + 1
    return ValidationOutcome(True, {
        "doi": SOURCE_DOI,
        "license": data.license,
        "files": len(data.file_sha256),
        "trace_count": len(data.traces),
        "raw_source_pairs": data.source_pair_count,
        "source_missing_time_tokens": data.missing_time_token_count,
        "source_missing_value_tokens": data.missing_value_token_count,
        "incomplete_pairs_preserved_raw": data.incomplete_pair_count,
        "trace_groups": tuple(sorted((figure, signal, count)
                                      for (figure, signal), count in by_key.items())),
        "first_trace": {
            "figure": data.traces[0].figure,
            "signal": data.traces[0].signal,
            "channel": data.traces[0].channel,
            "sample_count": len(data.traces[0].time_s),
        },
        "model_comparison_executed": False,
    }, (
        "Figure 4a feed pressure is provided as pressure-change channels rather than a documented absolute inlet pressure.",
        "The source states that the UHV mass-spectrometer signal has an arbitrary scale relative to the feed ordinate.",
        "This case checks source receipts/schema only; it does not fit diffusion or metal-hydride kinetics.",
    ))
