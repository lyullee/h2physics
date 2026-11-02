"""Hangang metadata-only contract for the Clashach PNM model-link gap."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


_MANIFEST = (Path(__file__).resolve().parents[2] / "research" / "data"
             / "clashach-h2-pnm-gap.toml")


def cases():
    return (ValidationCase(
        identifier="clashach-h2-pnm-porous-reservoir-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(_MANIFEST)},
        invariants=(
            "the explicit CC-BY record and README receipt identify the reviewed candidate",
            "the listed pore/throat PNM schemas remain 16-bit label volumes with stated voxel scale",
            "archives remain unacquired because the current continuum model inputs are absent",
            "no storage model parameterization or model comparison is asserted",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != "10.5281/zenodo.10500728"
            or record.get("license_id") != "CC-BY-4.0"
            or record.get("acquisition_status") != "readme_only_schema_audited"
            or record.get("selected_data_files") != []
            or record.get("pnm_volume_dimensions_xyz") != [800, 800, 1207]
            or record.get("voxel_size_um") != 7
            or record.get("pnm_voxel_storage") != "16-bit unsigned labels"):
        raise ValueError("Clashach PNM candidate rights, schema or acquisition boundary changed")
    return ValidationOutcome(True, {
        "doi": record["doi"],
        "license": record["license_id"],
        "readme_sha256": record["readme_sha256"],
        "pnm_dimensions_xyz": tuple(record["pnm_volume_dimensions_xyz"]),
        "voxel_size_um": record["voxel_size_um"],
        "selected_archives_acquired": 0,
        "model_comparison_executed": False,
    }, (
        "The PNM files are label volumes, not pore/throat geometric or hydraulic property tables.",
        "No capillary-pressure/saturation response, per-image operating clock or flow history is mapped.",
        "The current radial model needs continuum porosity/permeability and a well schedule; this candidate does not supply them.",
    ))
