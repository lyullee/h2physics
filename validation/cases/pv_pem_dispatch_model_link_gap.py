"""Metadata-only contract for a PV/PEM figure-output source boundary."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


DOI = "10.5281/zenodo.22900353"
FILENAME = "Manuscript_Figure3-10_Data.zip"
SHA256 = "2fb59438156bd9ccfd8caad6e9540dd68648ffa08816a5c2eedde0043be96b39"


def cases():
    return (ValidationCase(
        identifier="pv-pem-dispatch-figure-output-model-linkage-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_gap",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2] / "research" / "data" / "pv-pem-dispatch.toml"
        )},
        invariants=(
            "the selected source archive is attributed and remains pinned to the Zenodo CC BY 4.0 record",
            "mixed-origin figure reconstructions and dispatch outputs are not relabeled as measured plant inputs",
            "the existing PVElectrolysis PVStage input requirements remain explicit and unmet by this archive",
            "no model result, parameter fit, or validation claim is generated",
        ),
    ),)


def validate_gap(*, work_directory, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    files = manifest.get("files", ())
    if (manifest.get("doi") != DOI or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("origin") != "mixed"
            or manifest.get("model_linkage_status") != "not_admitted_figure_reconstruction_and_dispatch_outputs"
            or manifest.get("model_link_case") != "pv-pem-dispatch-figure-output-model-linkage-gap"
            or len(files) != 1 or files[0].get("name") != FILENAME
            or files[0].get("size_bytes") != 47_443 or files[0].get("sha256") != SHA256
            or files[0].get("status") != "cached"):
        raise ValueError("PV/PEM source receipt or model-linkage boundary changed")
    missing = tuple(manifest.get("missing_model_link_evidence", ()))
    expected = {
        "measured effective irradiance and its optical/spectral/soiling basis",
        "PV module and array electrical parameters with layout",
        "PV cell temperature observations",
        "electrolyzer stack temperature/current/voltage measurements matched to the same clock",
        "boundary and provenance for reported cumulative H2 traces",
        "uncertainty and row-level measured-versus-simulated lineage",
    }
    if set(missing) != expected:
        raise ValueError("PV/PEM model-link evidence list changed")
    return ValidationOutcome(True, {
        "doi": DOI,
        "filename": FILENAME,
        "source_sha256": SHA256,
        "origin": manifest["origin"],
        "license_id": manifest["license_id"],
        "model_linkage_admitted": False,
        "missing_evidence": missing,
    }, (
        "The archive contains manuscript-figure and dispatch-response data, not validated PV/PEM input and response measurements.",
        "The case checks attribution and evidence classification only; it performs no model calculation.",
    ))
