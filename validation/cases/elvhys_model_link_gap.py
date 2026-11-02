"""Metadata-only scope contract for ELVHYS LH2 rupture model evidence gaps."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="elvhys-lh2-rupture-model-link-evidence-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap_record",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "elvhys-shock-tube.toml"
        )},
        invariants=(
            "the record identifies the acquired CC0 dataset and selected source scope",
            "reported PRESF bar_a values are not elevated to thermodynamic absolute pressure",
            "tube composition and liquid inventory are not inferred from containment oxygen or temperature",
            "recorder clocks and pressure-wave channels are not synchronized/calibrated by this case",
            "no BLEVE, fire, release, detonation, or pressure-wave validation claim is made",
        ),
    ),)


def validate_gap_record(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    gaps = manifest.get("required_model_link_evidence", ())
    if (manifest.get("doi") != "10.18710/M5LOLM"
            or manifest.get("license_id") != "CC0-1.0"
            or manifest.get("listed_file_count") != 133
            or manifest.get("acquired_bytes") != 534609893
            or manifest.get("model_link_status") != "evidence_gap_no_source_model_comparison"
            or len(gaps) < 4):
        raise ValueError("ELVHYS source receipt or model-link gap changed")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "listed_files": manifest["listed_file_count"],
        "acquired_bytes": manifest["acquired_bytes"],
        "explicit_missing_evidence_items": len(gaps),
        "source_rows_read": False,
        "model_comparison_performed": False,
    }, (
        "This contract checks provenance and the stated evidence gap only.",
        "The acquired recorder observations do not yet establish calibrated model boundary/response quantities.",
    ))
