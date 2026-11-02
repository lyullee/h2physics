"""Metadata-only PCT source/model boundary for simulated hydride curves."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="hydride-pct-simulated-equilibrium-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_metadata_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "hydride-pct-simulation.toml"
        )},
        invariants=(
            "the five CC BY 4.0 source workbooks are explicitly classified as simulated",
            "native concentration headers remain NL/kg or wt% without inferred basis conversion",
            "source pressure bar is not silently treated as absolute fugacity",
            "temperature, material, branch and uptake basis remain linked to source workbook identity",
            "the contract makes no independent equilibrium validation claim",
        ),
    ),)


def validate_metadata_gap(*, work_directory, manifest_path):
    """Validate source qualification metadata only; no workbook values are evaluated."""
    del work_directory
    path = Path(manifest_path)
    with path.open("rb") as stream:
        manifest = tomllib.load(stream)
    if (
        manifest.get("doi") != "10.17632/trpnk55pmz.1"
        or manifest.get("origin") != "simulated"
        or manifest.get("license_id") != "CC-BY-4.0"
        or manifest.get("listed_file_count") != 5
        or manifest.get("acquired_bytes") != 13_138_739
        or len(manifest.get("required_model_link_evidence", ())) < 3
    ):
        raise ValueError("Hydride PCT model-link gap manifest no longer matches its source qualification")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "origin": manifest["origin"],
        "license_id": manifest["license_id"],
        "workbook_count": manifest["listed_file_count"],
        "acquired_bytes": manifest["acquired_bytes"],
        "pressure_fugacity_conversion_admitted": False,
        "concentration_loading_conversion_admitted": False,
        "independent_validation_claim": False,
    }, (
        "Metadata-only gap contract; no source rows were read, converted, fitted or compared.",
        "Synthetic/processed source outputs can support only a source-specific regression after basis and generating-model lineage are established.",
    ))
