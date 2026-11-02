"""Metadata-only evidence-gap contract for the large public SOE fault archive."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    manifest = (Path(__file__).resolve().parents[2] / "research" / "data"
                / "soe-fault-operation.toml")
    return (ValidationCase(
        identifier="soe-fault-operation-data-schema-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_metadata_gap",
        parameters={"manifest_path": str(manifest)},
        invariants=(
            "the public record declares CC BY 4.0 and lists eleven files totaling 1,092,175,741 bytes",
            "zero payload files have been acquired and the archive is not parsed or executed",
            "file-to-fault mapping, MAT schema, channel units, clocks and sensor semantics are explicitly unresolved",
            "existing HydrogenStack and process-monitoring models are candidate interfaces only, with no data linkage admitted",
            "the documented acquisition request asks for a small fault/baseline subset with checksums before bulk acquisition",
        ),
    ),)


def validate_metadata_gap(*, work_directory, manifest_path):
    """Check only the versioned metadata-gap record; perform no network or model work."""
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    missing = tuple(record.get("missing_evidence", ()))
    if (record.get("doi") != "10.5281/zenodo.10648884"
            or record.get("license_id") != "CC-BY-4.0"
            or record.get("listed_file_count") != 11
            or record.get("listed_total_bytes") != 1_092_175_741
            or record.get("acquired_bytes") != 0
            or record.get("acquisition_status") != "identified_not_acquired"
            or record.get("model_linkage_admitted") is not False
            or len(missing) < 7
            or record.get("metadata_contract_case") != "soe-fault-operation-data-schema-gap"):
        raise ValueError("SOE fault-operation evidence-gap manifest changed or is incomplete")
    return ValidationOutcome(True, {
        "doi": record["doi"],
        "license_id": record["license_id"],
        "listed_files": record["listed_file_count"],
        "listed_bytes": record["listed_total_bytes"],
        "acquired_bytes": record["acquired_bytes"],
        "unresolved_schema_items": len(missing),
        "model_linkage_admitted": False,
        "request_file": record["author_request"],
    }, (
        "Metadata-only gap contract: no MAT attachment bytes or row schema are present.",
        "No HydrogenStack comparison, fault classification, fitting, or physical validation is performed or implied.",
    ))
