"""Metadata-only model-linkage gap for the acquired dark-fermentation workbook."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    manifest = (Path(__file__).resolve().parents[2] / "research" / "data"
                / "dark-fermentation.toml")
    return (ValidationCase(
        identifier="dark-fermentation-h2-process-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_fermentation_link_gap",
        parameters={"manifest_path": str(manifest)},
        invariants=(
            "the acquired Mendeley v2 workbook DOI, CC BY 4.0 status and exact file hash remain recorded",
            "gas BP remains reported volume rather than standard molar or mass flow",
            "H2/CH4/CO2 labels are not assumed to be mole fractions aligned to gas-flow sampling",
            "reactor state, feed, initial biomass, gas reference condition, clock and replicate independence remain unresolved",
            "the contract performs no ADM1 source replay, parameter fitting, or process validation",
            "the prepared author request is tracked but not sent",
        ),
    ),)


def validate_fermentation_link_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    files = tuple(manifest.get("files", ()))
    gaps = tuple(manifest.get("missing_model_link_evidence", ()))
    if (manifest.get("doi") != "10.17632/2nwcdx9hst.2"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("metadata_sha256") != "887b80088dfb7b635690fa3150171c953621b9863b11a0f9e44ab45075af6811"
            or manifest.get("acquired_bytes") != 165_296
            or len(files) != 1
            or files[0].get("name") != "Raw data.xlsx"
            or files[0].get("sha256") != "f13352e6ae633878aa7cf47a9b7d79f859ad815cda24000c11f04abf32b60729"
            or manifest.get("model_linkage_admitted") is not False
            or len(gaps) < 8
            or manifest.get("metadata_contract_case") != "dark-fermentation-h2-process-model-link-gap"):
        raise ValueError("Fermentation model-link gap manifest differs from the pinned source receipt")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "source_sha256": files[0]["sha256"],
        "acquired_bytes": manifest["acquired_bytes"],
        "unresolved_link_items": len(gaps),
        "model_linkage_admitted": False,
        "request_file": manifest["author_request"],
    }, (
        "Metadata-only evidence-gap contract; it does not reopen the workbook or convert its source gas basis.",
        "No QSDsan/ADM1 state initialization, rate fit, standard-volume conversion, or hydrogen-production validation is claimed.",
    ))
