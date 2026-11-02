"""Metadata-only Hangang contract for the inaccessible Dryad PEM dataset."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="pem-grid-application-data-access-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_metadata_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "pem-grid-system.toml"
        )},
        invariants=(
            "the primary page identifies a shared timestamp file and command/stack/SMPS/chiller/subsystem power plus two hydrogen-flow trace files",
            "Dryad CC0 reuse policy and DOI are retained as metadata, not as evidence that attachments were acquired",
            "experimental trace units, sampling support, flow reference basis, uncertainty and sensor/system boundary mapping remain unverified while attachment bytes are unavailable",
            "reader/model linkage remains blocked while both listed publisher files have no locally acquired bytes",
            "simulation input power units do not establish experimental trace units or direct cell-polarization conditions",
            "the contract makes no process validation or measurement-derived model claim",
        ),
    ),)


def validate_metadata_gap(*, work_directory, manifest_path):
    """Verify the recorded source-evidence boundary without fetching payloads."""
    del work_directory
    path = Path(manifest_path)
    with path.open("rb") as stream:
        manifest = tomllib.load(stream)
    files = {entry["name"]: entry for entry in manifest.get("files", ())}
    expected_files = {"README.md", "Fixed_ERCOT_Electrolyzer_Sim_Engine.zip"}
    if (manifest.get("doi") != "10.5061/dryad.8931zcs64"
            or manifest.get("license_id") != "CC0-1.0"
            or manifest.get("acquired_bytes") != 0
            or set(files) != expected_files
            or any(file.get("status") != "failed_unacquired" for file in files.values())):
        raise ValueError("PEM grid dataset gap manifest no longer matches the reviewed source state")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "listed_files": len(files),
        "acquired_bytes": manifest["acquired_bytes"],
        "listed_archive_size_display": files["Fixed_ERCOT_Electrolyzer_Sim_Engine.zip"]["listed_size_display"],
        "payload_schema_available": False,
        "public_readme_channel_names": (
            "timestamp.txt", "power_command.txt", "stack_power.txt", "smps_power.txt",
            "chiller_power.txt", "subsystem_power.txt", "hydrogen_flow.txt", "hydrogen_flow_cs.txt",
        ),
        "model_linkage_admitted": False,
    }, (
        "Metadata-only gap contract; no Dryad attachment bytes are available in this run.",
        "The public page names candidate synchronized traces, but their numeric bytes, experimental units, time support, H2 flow basis, uncertainty and measurement boundary remain unavailable.",
        "The publisher's MW convention applies to separate simulation grid-input files; it is not applied to experimental power traces.",
        "No data reader, fit, conversion or physical model validation is implied.",
    ))
