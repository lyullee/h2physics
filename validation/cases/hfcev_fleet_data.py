"""Hangang contract for the source-bound HFCEV fuel-consumption observation."""

import tomllib
from collections import Counter
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.hfcev_fleet import (
    DOI,
    SAMPLE_SHA256,
    read_hfcev_operation_sample,
)
from h2physics.adapters.hfcev_fleet import select_hfcev_hydrogen_window


def cases():
    return (ValidationCase(
        identifier="hfcev-fleet-hydrogen-consumption-model-comparator",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_window",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/hfcev-fleet/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "hfcev-fleet-telemetry.toml"),
        },
        invariants=(
            "only the official hash-pinned V001 operation sample is read from an explicit Hangang source root",
            "source H2 mass is the publisher-attributed restored counter increment in kg, never derived from voltage/current",
            "source windows require exact receipt-time row edges, one vehicle/unit/segment and every included H2 increment attributed",
            "receipt timestamps, device-time status, missing masks, current and voltage remain distinct source observations",
            "no active area, cell conditions, GPS, model fit or physical validation claim is inferred",
        ),
    ),)


def validate_source_window(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    if (manifest.get("doi") != DOI or manifest.get("version") != "1.0"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("acquired_bytes") != 2_383_383):
        raise ValueError("HFCEV dataset provenance/rights manifest changed")
    sample = read_hfcev_operation_sample(raw_data_root)
    if sample.source_sha256 != SAMPLE_SHA256 or len(sample.rows) < 2:
        raise ValueError("The selected publisher operation sample is not the accepted byte stream")
    time_counts = Counter(row.receipt_time for row in sample.rows)
    pair_index = next((i for i in range(1, len(sample.rows))
                       if sample.rows[i - 1].unit == sample.rows[i].unit
                       and sample.rows[i - 1].segment == sample.rows[i].segment
                       and sample.rows[i - 1].receipt_time < sample.rows[i].receipt_time
                       and time_counts[sample.rows[i - 1].receipt_time] == 1
                       and time_counts[sample.rows[i].receipt_time] == 1
                       and sample.rows[i - 1].h2_kg_restored is not None
                       and (sample.rows[i - 1].missing_mask & (1 << 26)) == 0
                       and (sample.rows[i - 1].counter_backward_mask & (1 << 1)) == 0
                       and sample.rows[i].h2_kg_restored is not None
                       and (sample.rows[i].missing_mask & (1 << 26)) == 0
                       and (sample.rows[i].counter_backward_mask & (1 << 1)) == 0
                       and sample.rows[i].h2_attributed
                       and sample.rows[i].h2_increment_kg is not None
                       and sample.rows[i].h2_increment_kg > 0), None)
    if pair_index is None:
        raise ValueError("The pinned sample has no positive attributed H2 interval for the reader contract")
    left, right = sample.rows[pair_index - 1], sample.rows[pair_index]
    observation = select_hfcev_hydrogen_window(
        sample,
        start_receipt_time=left.receipt_time.isoformat(sep=" "),
        end_receipt_time=right.receipt_time.isoformat(sep=" "),
        window_selection_evidence_id="publisher receipt-time row-edge selection; no model alignment asserted",
    )
    observation.require_current()
    try:
        select_hfcev_hydrogen_window(
            sample,
            start_receipt_time=left.receipt_time.replace(microsecond=1).isoformat(sep=" "),
            end_receipt_time=right.receipt_time.isoformat(sep=" "),
            window_selection_evidence_id="negative control",
        )
    except ValueError:
        non_row_aligned_rejected = True
    else:
        non_row_aligned_rejected = False
    if not non_row_aligned_rejected:
        raise ValueError("HFCEV source reader accepted a non-row-aligned window")
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_id": "CC-BY-4.0",
        "sample_sha256": sample.source_sha256,
        "row_count": len(sample.rows),
        "selected_source_rows": observation.source_rows,
        "increment_previous_counter_row_pairs": observation.source_interval_rows,
        "receipt_time_edges": (left.receipt_time.isoformat(sep=" "), right.receipt_time.isoformat(sep=" ")),
        "attributed_h2_mass_kg": observation.measured_h2_consumed_kg,
        "elapsed_receipt_seconds": observation.elapsed_receipt_s,
        "device_time_status": (left.device_time_status, right.device_time_status),
        "current_and_voltage_retained": (
            (left.stack_current_a, left.stack_voltage_v),
            (right.stack_current_a, right.stack_voltage_v),
        ),
        "non_row_aligned_rejected": non_row_aligned_rejected,
        "model_trace_compared": False,
    }, (
        "This case reads a CC BY source sample and verifies the source-bound observation window only.",
        "The data's receipt clock is not treated as device event time; callers need independent clock-alignment evidence before comparing a model trace.",
        "No physical model run, fitting, or validation claim is made by this ingestion contract.",
    ))
