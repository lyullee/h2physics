"""Metadata-only contract for the residential H2 pilot data rights/boundary gap."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


DOI = "10.5281/zenodo.15166733"


def cases():
    return (ValidationCase(
        identifier="residential-h2-pilot-license-and-physical-boundary-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "residential-h2-pilot.toml"
        )},
        invariants=(
            "the primary record's explicit channel units and 5-second cadence are preserved as metadata only",
            "no data payload is ingested while the official license field is empty",
            "normal-liter reference state, pressure basis, clock/break semantics and physical equipment boundary remain unresolved",
            "no measured row, model calculation or validation claim is made",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    file_record = record["files"][0]
    if (record.get("doi") != DOI or record.get("version") != "1"
            or record.get("license_id") != "unknown"
            or record.get("rights_permitted") is not False
            or record.get("acquired_bytes") != 0
            or file_record.get("name") != "HY2RES_202404.csv"
            or file_record.get("publisher_md5") != "9a3c3e3b1668596854b43bfd790d3e0e"
            or file_record.get("status") != "not_acquired_license_unresolved"):
        raise ValueError("Residential H2 pilot rights/file metadata changed")
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_verified": False,
        "acquired_bytes": record["acquired_bytes"],
        "listed_file": file_record["name"],
        "publisher_md5": file_record["publisher_md5"],
        "listed_channel_groups": ("electrical power W", "pressure bar", "hydrogen flow NL/h", "hydrogen total NL", "SOC", "ambient temperature degC"),
        "physical_data_link_admitted": False,
    }, (
        "Zenodo's official page describes the system and channel units, but its License field is blank and the CSV bytes were not acquired.",
        "NL reference state, pressure basis and PLC break semantics require source documentation before using the signals in a physical model.",
    ))
