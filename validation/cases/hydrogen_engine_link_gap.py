"""Metadata-only model-linkage gap case for acquired hydrogen-engine HDF5 figures."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

_SOURCE_FILES = {
    "Fig2.h5": "729b8a4f0dd67cfa84b9c925a34a033618bc6af5d0abe876ba8f03d8e57eac4e",
    "Fig3.h5": "ecb5072582cea99128be1937a54cc3d851c05f3a22429820e9c0960fba37dc5a",
    "Fig5.h5": "adeb246afb604a1f4d48432d19db6fa12f545dfb0404eae5863bd64b25d8b038",
    "Fig6.h5": "e3156d6d2d9a499788afee90090bfe5d33190a16cff7e390754d0cc3e746a532",
    "Fig7.h5": "9688ce757428b5b47483a0bc33cfdcedd8937fe083324a147364f24861479976",
    "Fig8.h5": "f8452f914c12be28ac97f1e741f7a861416d514d6075b91b3c2c1a1fcbdae3a2",
    "Fig9.h5": "668cc2ff3e54c61a19842a5d3dc2794e9bc15608645b47c374fd0614dca315f2",
    "README.txt": "997491971bc67bd62ed460d14657d8c4bb549b65a41256dce553a2730dc77c07",
}
_METADATA_SHA256 = "3438d88458f9ffb08eb5e4224fea51eba6f6fa29cb15923d9acd50315d1e30fa"


def cases():
    manifest = (Path(__file__).resolve().parents[2] / "research" / "data"
                / "hydrogen-engine-flame-wall.toml")
    return (ValidationCase(
        identifier="hydrogen-engine-figure-data-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_model_link_gap",
        parameters={"manifest_path": str(manifest)},
        invariants=(
            "the public TUdatalib DOI, CC BY 4.0 declaration, eight file hashes and total acquisition bytes remain pinned",
            "HDF5 schema inspection remains metadata-only and performs no dataset-value reads",
            "measurement quantity, location, crank-angle/time reference and sample-population semantics are not inferred",
            "existing engine-pressure/thermal APIs remain unlinked until the field-specific data dictionary arrives",
            "component-level third-party rights review and raw redistribution admission remain separate",
        ),
    ),)


def validate_model_link_gap(*, work_directory, manifest_path):
    """Verify exact reviewed gap metadata only; no HDF5 source values are loaded."""
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    files = tuple(manifest.get("files", ()))
    source_hashes = {item.get("name"): item.get("sha256") for item in files}
    gaps = tuple(manifest.get("missing_model_link_evidence", ()))
    if (manifest.get("doi") != "10.48328/tudatalib-2291"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("metadata_sha256") != _METADATA_SHA256
            or manifest.get("listed_file_count") != 8
            or manifest.get("acquired_bytes") != 8_828_090
            or len(files) != 8
            or source_hashes != _SOURCE_FILES
            or sum(item.get("size_bytes", 0) for item in files) != 8_828_090
            or any(item.get("status") != "acquired"
                   for item in files)
            or manifest.get("model_linkage_admitted") is not False
            or manifest.get("third_party_component_rights_reviewed") is not False
            or manifest.get("raw_redistribution_admitted") is not False
            or len(gaps) < 8
            or manifest.get("metadata_contract_case") != "hydrogen-engine-figure-data-model-link-gap"):
        raise ValueError("Hydrogen-engine model-link gap record changed or is incomplete")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "acquired_files": len(files),
        "acquired_bytes": manifest["acquired_bytes"],
        "schema_gap_items": len(gaps),
        "model_linkage_admitted": False,
        "component_rights_reviewed": False,
        "request_file": manifest["author_request"],
    }, (
        "Metadata-only contract; it does not reopen HDF5 arrays or reproduce publisher plots.",
        "No crank-angle pressure, flame, or wall-heat source is assigned to a physical model.",
    ))
