"""Synthetic evidence-bound MOF-to-Langmuir bridge contract for Hangang."""

from hashlib import md5, sha256

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="cryo-mof-source-to-langmuir-diagnostic-bridge",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_langmuir_bridge",
        invariants=(
            "source rows bind to the exact Langmuir material, H2 species and source digest",
            "absolute-pressure and absolute-uptake interpretations require separate caller evidence",
            "77/87 K complete rows evaluate without interpolation, fitting or extrapolation",
            "20 K normalized-pressure/reference-volume input is rejected by this absolute-pressure bridge",
            "results are diagnostic and do not qualify the adsorption model or tank",
        ),
    ),)


def validate_langmuir_bridge(*, work_directory):
    from pathlib import Path

    import numpy as np

    from h2physics.adsorption import AdsorptionBasis, AdsorptionDomain, ExtendedLangmuirIsotherm
    from h2physics.adapters.cryo_mof_langmuir import compare_cryo_mof_with_langmuir
    from h2physics.data.cryo_mof import load_cryo_mof_isotherm
    from h2physics.data.models import Dataset, RemoteFile

    root = Path(work_directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "H2.77K--MIL-100(Fe).csv"
    raw = ("Relative pressure adsorption (bar) ,Quantity Adsorbed (mmol/g) ,"
           "Relative pressure desorption (bar) ,Quantity Desorbed (mmol/g)\n"
           "0.2,0.3333333333333333,0.2,0.3333333333333333\n"
           "0.8,1.0,0.8,1.0\n").encode("utf-8")
    path.write_bytes(raw)
    metadata = b"synthetic source metadata receipt"
    dataset = Dataset(key="cryo-mof-dormancy", title="Synthetic cryogenic MOF fixture",
        doi="10.57745/FCV2R0", version="1.1", authors=("synthetic",),
        license_id="etalab-2.0", license_url="https://spdx.org/licenses/etalab-2.0.html",
        metadata_url="https://example.org/metadata", metadata_sha256=sha256(metadata).hexdigest(),
        origin="measured", families=("adsorption",), files=(RemoteFile(
            path.name, "https://example.org/" + path.name, len(raw), "md5",
            md5(raw, usedforsecurity=False).hexdigest()),), metadata_bytes=metadata)
    source = load_cryo_mof_isotherm(path, dataset=dataset,
                                   expected_sha256=sha256(raw).hexdigest())
    basis = AdsorptionBasis("MIL-100(Fe)", ("H2",), "synthetic-absolute-mol-per-kg",
        "host-extended-langmuir", "synthetic-model-parameters", ("synthetic-test-only",),
        loading_definition="absolute")
    model = ExtendedLangmuirIsotherm(basis, AdsorptionDomain(77., 77., 100_000.),
        np.asarray([2.]), lambda temperature: np.asarray([[1.e-5]]),
        evidence_id="synthetic-parameter-contract")
    trace = compare_cryo_mof_with_langmuir(source, model, direction="adsorption",
        pressure_basis_evidence_id="synthetic-source-pressure-is-absolute-Pa-after-parser-scale",
        uptake_basis_evidence_id="synthetic-source-uptake-is-absolute-mol-per-kg",
        material_identity_evidence_id="synthetic-MIL-100-Fe-identity")
    trace.require_current()
    twenty_k_path = root / "H2.20K--MIL-100(Fe).csv"
    twenty_raw = ("Relative pressure adsorption (p/p) ,Quantity Adsorbed (cm3 g-1 STP) ,"
                  "Relative pressure desorption (p/p) ,Quantity Desorbed (cm3 g-1 STP)\n"
                  "0.2,1.0,0.2,1.0\n").encode("utf-8")
    twenty_k_path.write_bytes(twenty_raw)
    twenty_dataset = Dataset(key=dataset.key, title=dataset.title, doi=dataset.doi,
        version=dataset.version, authors=dataset.authors, license_id=dataset.license_id,
        license_url=dataset.license_url, metadata_url=dataset.metadata_url,
        metadata_sha256=dataset.metadata_sha256, origin=dataset.origin,
        families=dataset.families, files=(RemoteFile(twenty_k_path.name,
        "https://example.org/" + twenty_k_path.name, len(twenty_raw), "md5",
        md5(twenty_raw, usedforsecurity=False).hexdigest()),), metadata_bytes=metadata)
    twenty_k = load_cryo_mof_isotherm(twenty_k_path, dataset=twenty_dataset,
        expected_sha256=sha256(twenty_raw).hexdigest())
    rejected = False
    try:
        compare_cryo_mof_with_langmuir(twenty_k, model, direction="adsorption",
            pressure_basis_evidence_id="must-not-override-unresolved-normalizer",
            uptake_basis_evidence_id="synthetic-uptake-interpretation",
            material_identity_evidence_id="synthetic-material-id")
    except ValueError:
        rejected = True
    if not rejected or len(trace.points) != 2:
        raise AssertionError("Cryogenic MOF Langmuir bridge contract failed")
    return ValidationOutcome(True, {
        "source_sha256": source.source_sha256,
        "source_rows_compared": len(trace.points),
        "first_uptake_residual_mol_kg": trace.points[0].uptake_residual_mol_kg,
        "20K_rejected": rejected,
        "fit_performed": False,
        "physical_validation_claimed": False,
    }, (
        "Synthetic source/model binding only; acquired measurements were not opened.",
        "Absolute pressure and uptake interpretations remain caller-provided evidence.",
        "No parameter fit, independent validation, or bed/tank qualification is performed.",
    ))
