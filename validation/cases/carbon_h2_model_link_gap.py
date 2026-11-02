"""Metadata-only link-gap contract for the acquired nanoporous-carbon H2 isotherm."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    manifest = (Path(__file__).resolve().parents[2] / "research" / "data"
                / "carbon-chemisorption.toml")
    return (ValidationCase(
        identifier="carbon-h2-chemisorption-model-link-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_carbon_link_gap",
        parameters={"manifest_path": str(manifest)},
        invariants=(
            "the Mendeley v1 CC BY 4.0 source record, table and file digest remain pinned",
            "the source H2 table labels pressure in torr and uptake in STP cm3/g but does not identify STP reference conditions in the admitted schema",
            "all material-column identities and absolute/total-versus-other uptake meaning remain evidence-gated",
            "the contract performs no gas-volume conversion, isotherm fit or ExtendedLangmuir evaluation",
            "the prepared author/repository request is tracked but not sent",
        ),
    ),)


def validate_carbon_link_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    files = tuple(manifest.get("files", ()))
    table = next((item for item in files if item.get("name") == "total_chemisorption_isotherms.csv"), None)
    gaps = tuple(manifest.get("missing_model_link_evidence", ()))
    if (manifest.get("doi") != "10.17632/vyp4wbhxzr.1"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("metadata_sha256") != "028397968b939e7e2adb5be3673aede15a6f29863c4e5fc068f55770f120676e"
            or manifest.get("acquired_bytes") != 26_374
            or manifest.get("listed_file_count") != 19
            or table is None
            or table.get("sha256") != "1224b5ba3198f24b30569e30678845fcebe345548c446f438806a5fcdada3312"
            or manifest.get("model_linkage_admitted") is not False
            or len(gaps) < 7
            or manifest.get("metadata_contract_case") != "carbon-h2-chemisorption-model-link-gap"):
        raise ValueError("Carbon H2 isotherm model-link gap differs from the pinned source record")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "source_table_sha256": table["sha256"],
        "acquired_bytes": manifest["acquired_bytes"],
        "unresolved_link_items": len(gaps),
        "model_linkage_admitted": False,
        "request_file": manifest["author_request"],
    }, (
        "Metadata-only gap contract; no CSV values are reopened or converted.",
        "The CO2/N2 physisorption files are not treated as H2 storage data, and no carbon H2 isotherm model is fit or validated.",
    ))
