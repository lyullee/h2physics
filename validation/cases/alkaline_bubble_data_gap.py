"""Metadata-only source/model evidence gap for alkaline electrolysis bubbles."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="alkaline-bubble-electrolysis-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_metadata_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "alkaline-bubble-observations.toml"
        )},
        invariants=(
            "Mendeley version 2 DOI, declared CC BY 4.0 and publication date remain source-bound metadata",
            "publisher record description is retained without treating raw figure data or videos as inspected observations",
            "missing file schema, bubble calibration and electrochemical condition mapping block model input admission",
            "existing HydrogenStack is not assigned an unobserved bubble-coverage or ohmic-loss parameter",
            "no source ingestion, fitting or physical validation is claimed",
        ),
    ),)


def validate_metadata_gap(*, work_directory, manifest_path):
    """Check the recorded evidence boundary without opening or acquiring payloads."""
    del work_directory
    path = Path(manifest_path)
    with path.open("rb") as stream:
        manifest = tomllib.load(stream)
    if (
        manifest.get("doi") != "10.17632/r6np4f7gmf.2"
        or manifest.get("version") != "2"
        or manifest.get("license_id") != "CC-BY-4.0"
        or manifest.get("acquired_bytes") != 0
        or manifest.get("acquired_file_count") != 0
        or manifest.get("raw_payload_acquired") is not False
        or not manifest.get("required_evidence")
    ):
        raise ValueError("Alkaline bubble evidence-gap manifest no longer matches reviewed metadata")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "version": manifest["version"],
        "license_id": manifest["license_id"],
        "acquired_file_count": manifest["acquired_file_count"],
        "listed_file_count": "unknown",
        "payload_schema_available": False,
        "bubble_to_HydrogenStack_mapping_admitted": False,
    }, (
        "Metadata-only gap contract; no files or videos were acquired or inspected.",
        "A model adapter requires quantitative bubble observations and an evidenced relation to electrochemical inputs or losses.",
    ))
