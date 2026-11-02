"""Metadata-only linkage contract for the Dryad hypoxia-chamber workbook."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


DOI = "10.5061/dryad.t1g1jwtg9"
EXPECTED = {
    "Compiled_Data_PAPER_unformatted.xlsx": "f301464111d1feb33c1b28a192b8b9d868a352a6041d8f4b0da03eeccc152383",
    "README.md": "93517b02fa207c24ca7510802eff56da82f0e49aafa598229481d8d451ce6bc5",
}


def cases():
    return (ValidationCase(
        identifier="oxygen-hypoxia-chamber-gas-transfer-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2] / "research" / "data" / "oxygen-hypoxia-chamber.toml"
        )},
        invariants=(
            "the Dryad CC0 record and publisher file listing are pinned without claiming acquired file bytes",
            "README-described measured channels are not promoted to a source boundary without workbook row schema and units",
            "the oxygen-deficiency model remains a gas-volume API and does not claim liquid oxygen transfer or evaporation",
            "no observations are fabricated and no model calculation or validation is performed",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    files = record.get("files", ())
    if (record.get("doi") != DOI or record.get("version") != "6"
            or record.get("license_id") != "CC0-1.0" or record.get("rights_permitted") is not True
            or record.get("model_linkage_status") != "blocked_downloaded_workbook_schema_and_source_boundary"
            or record.get("model_link_case") != "oxygen-hypoxia-chamber-gas-transfer-model-link-gap"
            or len(files) != 2):
        raise ValueError("Dryad source identity, license, or model-link status changed")
    by_name = {entry.get("name"): entry for entry in files}
    if set(by_name) != set(EXPECTED):
        raise ValueError("Dryad primary listing differs from the two reviewed file entries")
    for name, checksum in EXPECTED.items():
        entry = by_name[name]
        if (entry.get("publisher_checksum_algorithm") != "sha256"
                or entry.get("publisher_checksum") != checksum
                or entry.get("status") != "failed"
                or entry.get("size_bytes") != 0 or entry.get("sha256") != ""):
            raise ValueError("Unacquired Dryad file receipt changed; refresh the review before ingestion")
    missing = tuple(record.get("missing_model_link_evidence", ()))
    if len(missing) != 7:
        raise ValueError("Dryad oxygen-model linkage evidence list changed")
    return ValidationOutcome(True, {
        "doi": DOI,
        "version": record["version"],
        "license_id": record["license_id"],
        "publisher_files": tuple(sorted(EXPECTED)),
        "acquired_file_count": 0,
        "model_linkage_admitted": False,
        "model_link_target": record["model_link_target"],
        "missing_evidence": missing,
    }, (
        "The primary Dryad README describes measured hypoxia-chamber observations, but no source file bytes or exact workbook schema were admitted.",
        "This contract records a data-access/model-boundary gap only; it does not evaluate oxygen or liquid-transfer physics.",
    ))
