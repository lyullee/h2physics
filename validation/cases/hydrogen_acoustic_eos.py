"""Deferred source-bound comparison of one acoustic table with the existing EOS."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

ARCHIVE_SHA256 = "38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553"
METADATA_SHA256 = "1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad"
MEMBER = "H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt"


def cases():
    root = Path(__file__).resolve().parents[2] / "data" / "raw" / "hydrogen-sound-speed" / "1.0.0"
    return (ValidationCase(
        identifier="hydrogen-acoustic-source-to-coolprop-pointwise-diagnostic",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_acoustic_eos_bridge",
        parameters={"archive_path": str(root / "H2_speedofsound_dataset.zip"),
                    "metadata_path": str(root / "repository-metadata.json"),
                    "member_path": MEMBER},
        invariants=(
            "the exact Zenodo DOI, CC BY 4.0 metadata, archive and member bytes are retained",
            "only the exact normal-H2 Carey 1974 member is compared, with spin basis matched",
            "source T, p and sound speed use declared K, MPa and m/s units and are projected to SI",
            "each complete source row is evaluated directly through the existing CoolPropProperties state_pt API",
            "no fit, interpolation, extrapolation, saturation reconstruction or source-row deletion is performed",
            "historical overlap with EOS development is unresolved; this is a diagnostic and not validation",
        ),
    ), ValidationCase(
        identifier="hydrogen-acoustic-source-phase-mismatch-diagnostic",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_phase_mismatch",
        parameters={"archive_path": str(root / "H2_speedofsound_dataset.zip"),
                    "metadata_path": str(root / "repository-metadata.json")},
        invariants=(
            "pinned source liquid phase is retained independently of the native PT phase",
            "VanDael loop-1 row-28 remains in residuals and is explicitly marked phase-incompatible",
            "no source pressure correction, forced phase or saturation reconstruction is applied",
        ),
    ),)


def validate_acoustic_eos_bridge(*, work_directory, archive_path, metadata_path, member_path):
    del work_directory
    import math

    from h2physics.adapters.hydrogen_acoustic_eos import compare_acoustic_file_with_eos
    from h2physics.data.hydrogen_sound_speed import load_hydrogen_acoustic_dataset
    from h2physics.thermo import CoolPropProperties

    source = load_hydrogen_acoustic_dataset(archive_path, metadata_path)
    if source.archive_sha256 != ARCHIVE_SHA256 or source.metadata_sha256 != METADATA_SHA256:
        raise ValueError("Hangang acoustic source hashes differ from the deferred case pins")
    trace = compare_acoustic_file_with_eos(source, member_path, CoolPropProperties("Hydrogen"))
    trace.require_current()
    if not trace.points:
        raise ValueError("No acoustic source rows were compared; an empty diagnostic cannot pass")
    residuals = tuple(point.residual_m_s for point in trace.points)
    relative_errors = tuple(point.relative_error_percent for point in trace.points)
    count = len(trace.points)
    return ValidationOutcome(True, {
        "source_doi": source.doi,
        "license": source.license_id,
        "archive_sha256": source.archive_sha256,
        "metadata_sha256": source.metadata_sha256,
        "member": member_path,
        "source_spin": "normal",
        "eos_basis": trace.provider.basis.reference_id,
        "compared_rows": len(trace.points),
        "excluded_rows": len(trace.exclusions),
        "phase_mismatch_rows": sum(point.phase_matches is False for point in trace.points),
        "unclassified_phase_rows": sum(point.phase_matches is None for point in trace.points),
        "mean_residual_m_s": math.fsum(residuals) / count,
        "rms_residual_m_s": math.sqrt(math.fsum(x*x for x in residuals) / count),
        "max_absolute_residual_m_s": max(abs(x) for x in residuals),
        "mean_relative_error_percent": math.fsum(relative_errors) / count,
        "max_absolute_relative_error_percent": max(abs(x) for x in relative_errors),
        "temperature_min_k": min(point.temperature_k for point in trace.points),
        "temperature_max_k": max(point.temperature_k for point in trace.points),
        "pressure_min_pa": min(point.pressure_pa for point in trace.points),
        "pressure_max_pa": max(point.pressure_pa for point in trace.points),
        "comparison_type": "pointwise EOS replay; no fit",
    }, (
        "This reproduces a bounded pointwise comparison only. The compiled literature rows may overlap historical EOS development; independence is unresolved and no universal accuracy or validation claim follows.",
    ))


def validate_phase_mismatch(*, work_directory, archive_path, metadata_path):
    del work_directory
    from h2physics.adapters.hydrogen_acoustic_eos import compare_acoustic_file_with_eos
    from h2physics.data.hydrogen_sound_speed import load_hydrogen_acoustic_dataset
    from h2physics.thermo import CoolPropProperties

    source = load_hydrogen_acoustic_dataset(archive_path, metadata_path)
    provider = CoolPropProperties("Hydrogen")
    member = "H2_speedofsound_dataset/H2_speedofsound_VanDael_1965_nH2_2.txt"
    trace = compare_acoustic_file_with_eos(source, member, provider).require_current()
    point, = (p for p in trace.points if p.row_id.endswith(":loop-1:row-28"))
    assert point.source_phase == "liquid"
    assert point.predicted_phase == "gas"
    assert point.phase_matches is False
    psat = provider.saturated_at_temperature(point.temperature_k, 0.0).pressure_pa
    assert point.pressure_pa < psat
    return ValidationOutcome(True, {
        "compared_rows": len(trace.points),
        "phase_mismatch_rows": sum(p.phase_matches is False for p in trace.points),
        "flagged_row_id": point.row_id,
        "flagged_relative_error_percent": point.relative_error_percent,
        "pressure_distance_below_saturation_percent": 100.0*(psat-point.pressure_pa)/psat,
    }, (
        "Phase conflict is diagnosed, not repaired. No experimental accuracy or metastability conclusion follows.",
    ))
