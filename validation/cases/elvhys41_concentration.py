"""Hangang contract for the source-bound ELVHYS 4.1 vent concentration file."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.elvhys41 import (
    CONCENTRATION_SHA256,
    DOI,
    load_elvhys41_concentration_csv,
)


def cases():
    return (ValidationCase(
        identifier="elvhys41-vent-composition-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_sample",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/elvhys-condensed-explosion/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "elvhys41-condensed-explosion.toml"),
        },
        invariants=(
            "only the three official CC0 source files are read and their exact hashes are checked",
            "Test-1 output remains raw oxygen/hydrogen vent concentration in vol percent on strictly increasing source seconds from experiment start",
            "negative sensor readings are retained and never clipped into valid fractions",
            "only an explicitly admissible composition row can enter a later exact-time model comparison",
            "this ingestion contract makes no room mixing or condensed-phase explosion validation claim",
        ),
    ),)


def validate_sample(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != DOI or record.get("version") != "1.1"
            or record.get("license_id") != "CC0-1.0"
            or record.get("acquired_bytes") != 1_035_075):
        raise ValueError("ELVHYS 4.1 source manifest rights or acquisition scope changed")
    sample = load_elvhys41_concentration_csv(raw_data_root)
    if sample.source_sha256 != CONCENTRATION_SHA256 or len(sample.rows) < 2:
        raise ValueError("ELVHYS 4.1 concentration data did not match its pinned byte receipt")
    if sample.rows[0].hydrogen_vol_percent >= 0.0:
        raise ValueError("The source's initial negative H2 sensor reading was not retained raw")
    admissible = next((row for row in sample.rows
                       if 0 <= row.oxygen_vol_percent <= 100
                       and 0 <= row.hydrogen_vol_percent <= 100
                       and row.oxygen_vol_percent + row.hydrogen_vol_percent <= 100.000001), None)
    if admissible is None:
        raise ValueError("No physically admissible raw concentration row is available for later comparison")
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_id": "CC0-1.0",
        "sample_sha256": sample.source_sha256,
        "row_count": len(sample.rows),
        "initial_raw_h2_vol_percent": sample.rows[0].hydrogen_vol_percent,
        "admissible_example_row": admissible.row_index,
        "admissible_example_time_s": admissible.time_s,
        "admissible_example_o2_vol_percent": admissible.oxygen_vol_percent,
        "admissible_example_h2_vol_percent": admissible.hydrogen_vol_percent,
        "model_comparison_executed": False,
    }, (
        "The reader preserves the raw 1 Hz sensor concentrations and source-relative time after validating publisher hashes.",
        "Converting vent vol% to the model's mole-fraction basis and equating the vent sample to homogeneous region state require caller evidence.",
        "No room calculation, fitting, or condensed-phase explosion claim is made by this source-ingestion case.",
    ))
