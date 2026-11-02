"""Metadata-only boundary audit for the USN carpark unignited MAT collection."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


DOI = "10.23642/usn.14405903"
SAMPLE_FILE = "Exp03.mat"
SAMPLE_SHA256 = "2c74d3575c00fe84757ffcd9580f36f29bd3be43af58f1c9814a1544ac799cb4"
GUIDE = "File handling guide.pdf"


def cases():
    return (ValidationCase(
        identifier="usn-carpark-unignited-fds-boundary-evidence-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2] / "research" / "data" / "carpark-unignited.toml"
        )},
        invariants=(
            "only the versioned CC BY 4.0 source receipt and selected metadata-only schema audit are admitted",
            "22 cached attachments and the not-acquired guide retain their distinct receipt states",
            "the source flow clock, release direction/plane, sensor coordinate frame, and expansion state remain unresolved",
            "no experiment values are ingested and no FDS or physical model is executed",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    files = record.get("files", ())
    selected = next((item for item in files if item.get("name") == SAMPLE_FILE), None)
    guide = next((item for item in files if item.get("name") == GUIDE), None)
    if (record.get("doi") != DOI or record.get("version") != "2"
            or record.get("license_id") != "CC-BY-4.0" or record.get("rights_permitted") is not True
            or record.get("model_linkage_status") != "blocked_independent_recorder_clock_coordinates_and_release_expansion_mapping"
            or record.get("model_link_case") != "usn-carpark-unignited-fds-boundary-evidence-gap"
            or record.get("listed_file_count") != 23 or len(files) != 23
            or selected is None or selected.get("status") != "cached"
            or selected.get("size_bytes") != 3_174_901 or selected.get("sha256") != SAMPLE_SHA256
            or guide is None or guide.get("status") != "not_acquired"
            or guide.get("size_bytes") != 0 or guide.get("sha256") != ""):
        raise ValueError("USN carpark version, rights, selected file, or gap receipt changed")
    schema = record.get("schema_audit", {})
    inspection = schema.get("inspection", "")
    required_tokens = ("49,999-row", "g/s", "m^3/h", "38 sensor", "sec", "%vol")
    if (schema.get("state") != "metadata_only_hdf5_audit_of_Exp03"
            or record.get("schema_audit_file") != SAMPLE_FILE
            or record.get("schema_audit_file_sha256") != SAMPLE_SHA256
            or any(token not in inspection for token in required_tokens)):
        raise ValueError("USN carpark metadata-only schema audit changed")
    missing = tuple(record.get("missing_model_link_evidence", ()))
    if len(missing) != 6:
        raise ValueError("USN carpark source-to-FDS evidence-gap list changed")
    return ValidationOutcome(True, {
        "doi": DOI,
        "version": record["version"],
        "license_id": record["license_id"],
        "selected_metadata_audit_file": SAMPLE_FILE,
        "selected_file_sha256": SAMPLE_SHA256,
        "acquired_attachment_count": sum(entry.get("status") == "cached" for entry in files),
        "unacquired_guide": GUIDE,
        "model_linkage_admitted": False,
        "model_link_target": record["model_link_target"],
        "missing_evidence": missing,
    }, (
        "Only HDF5 metadata and the acquired USN readme were reviewed; no MAT measurement arrays enter this case.",
        "The data record suggests an H2 source/receptor comparison, but the metadata does not establish the source and sensor mappings required by the existing FDS boundary.",
    ))
