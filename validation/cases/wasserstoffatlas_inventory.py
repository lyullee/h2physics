"""Hangang source-ingestion contract for the Hydrogen Map inventory."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.hydrogen_map import SOURCE_DOI, SOURCE_FILE, read_hydrogen_map_inventory


def cases():
    return (ValidationCase(
        identifier="wasserstoffatlas-facility-inventory-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_inventory",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/wasserstoffatlas/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "wasserstoffatlas-hydrogen-map.toml"),
        },
        invariants=(
            "the official DOI, license attribution and exact CSV byte hashes are retained",
            "all 1049 facility rows and their source text fields are preserved without inferred units",
            "geometry remains source WKT; no coordinate-system or distance calculation is asserted",
            "the inventory is facility context and performs no process model or consequence validation",
        ),
    ),)


def validate_inventory(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != SOURCE_DOI or record.get("filename") != SOURCE_FILE
            or record.get("license_id") != "CC-BY-4.0"
            or record.get("acquisition_status") != "acquired_local"
            or record.get("sha256") != "050e7b8a5a45d554640c2668ab87b6e9c3d0d4658e7ee4a572d7a0864092e8fe"):
        raise ValueError("Hydrogen Map inventory manifest identity or rights receipt changed")
    inventory = read_hydrogen_map_inventory(Path(raw_data_root) / SOURCE_FILE)
    inventory.require_current()
    if inventory.path.stat().st_size != 181145:
        raise ValueError("Hydrogen Map source file size differs from reviewed bytes")
    first = inventory.rows[0]
    return ValidationOutcome(True, {
        "doi": SOURCE_DOI,
        "license": inventory.license,
        "attribution": inventory.attribution,
        "sha256": inventory.sha256,
        "rows": len(inventory.rows),
        "first_source_id": first.source_id,
        "first_facility_type": first.facility_type,
        "first_geometry_wkt": first.geometry_wkt,
        "model_validation_executed": False,
    }, (
        "The inventory is a Germany-focused infrastructure compilation with heterogeneous upstream lineage.",
        "Capacity, demand and emissions tokens are preserved but units and per-facility measurement bases are not normalized here.",
        "Locations and categories support caller-side screening only; no dynamic process or safety result is inferred.",
    ))
