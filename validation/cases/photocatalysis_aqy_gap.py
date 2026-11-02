"""Metadata-only provenance contract for the AQY-to-photon-model evidence gap."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    manifest = (Path(__file__).resolve().parents[2] / "research" / "data"
                / "tio2-photo-evolution.toml")
    return (ValidationCase(
        identifier="tio2-brookite-aqy-model-link-evidence-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_aqy_link_gap",
        parameters={"manifest_path": str(manifest)},
        invariants=(
            "the acquired CC BY 4.0 dataset and publisher archive digest remain identified",
            "Figure4b native wavelength and AQY-percent headers do not alone identify the PhotonYield basis or matching photon supply",
            "row-matched optical power, spectrum, catalyst/geometry, conditions and H2 collection evidence remain required",
            "the contract performs no payload reinterpretation, conversion, fit, or photon-hydrogen model calculation",
            "the prepared author request is tracked but not sent",
        ),
    ),)


def validate_aqy_link_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    files = manifest.get("files", ())
    archive = next((item for item in files if item.get("name") == "Dataset.zip"), None)
    gaps = tuple(manifest.get("missing_model_link_evidence", ()))
    if (manifest.get("doi") != "10.5281/zenodo.15277951"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("acquired_bytes") != 1_946_372
            or archive is None
            or archive.get("sha256") != "b22f168f0244fa9138c6e392150171d9c808bec605f619268f8e8d18de997353"
            or manifest.get("model_linkage_admitted") is not False
            or len(gaps) < 6
            or manifest.get("metadata_contract_case") != "tio2-brookite-aqy-model-link-evidence-gap"):
        raise ValueError("Photocatalysis AQY link-gap manifest no longer matches its pinned source")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "archive_sha256": archive["sha256"],
        "acquired_bytes": manifest["acquired_bytes"],
        "unresolved_link_items": len(gaps),
        "model_linkage_admitted": False,
        "request_file": manifest["author_request"],
    }, (
        "Metadata/provenance gap only. The underlying source archive is already parsed by the data API; this case does not reopen or recalculate its values.",
        "Reported AQY is not replayed through PhotonYield without the row-matched optical supply and electron/photon basis.",
    ))
