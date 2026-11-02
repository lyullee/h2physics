"""Deferred Hangang source-ingestion contract for the attributed GrInHy2 CSV."""

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from pathlib import Path

SOURCE_SHA256 = "04cf4c65676bac11024cc35aaa83ce55c94165044108a17a89abc065a4f28612"


def cases():
    return (ValidationCase(
        identifier="grinhy2-flow-source-ingestion",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source",
        parameters={"source_path": str(
            Path(__file__).resolve().parents[2]
            / "data" / "processed" / "grinhy2" / "transient_hydrogen_flow.csv"
        )},
        invariants=(
            "the exact reviewed CSV schema and declared SHA-256 are accepted",
            "all 447 source observations and the long logger gap are preserved",
            "negative reported boundary readings remain unclipped",
            "source mutation invalidates the loaded receipt",
            "data remain an observed boundary-flow schedule, not electrochemical validation",
        ),
    ), ValidationCase(
        identifier="grinhy2-electrolyzer-coupling-evidence-gap",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_coupling_evidence_gap",
        parameters={"source_path": str(
            Path(__file__).resolve().parents[2]
            / "data" / "processed" / "grinhy2" / "transient_hydrogen_flow.csv"
        )},
        invariants=(
            "source rows expose boundary volume-flow channels but no stack current, electrical input, or temperature channel",
            "the unresolved Nm3 reference state blocks conversion to molar or mass production rate",
            "no parameter fit or forcing profile is admitted into the PV/electrolysis producer model",
            "the source remains usable for hash-bound boundary-flow schedule analysis without extrapolation",
        ),
    ))


def validate_source(*, work_directory, source_path):
    from pathlib import Path
    from h2physics.data.grinhy2 import load_grinhy2_flow

    del work_directory
    series = load_grinhy2_flow(Path(source_path), expected_sha256=SOURCE_SHA256)
    intervals = series.intervals_s
    long_gaps = intervals[intervals != 15.0]
    if len(series.elapsed_s) != 447 or len(long_gaps) != 1 or long_gaps[0] != 8205.0:
        raise ValueError("Source row count or recorded irregular interval changed")
    if not (series.vent_nm3_h.min() < 0 and series.grid_nm3_h.min() < 0):
        raise ValueError("Negative raw readings were not retained")
    series.require_current()
    return ValidationOutcome(True, {
        "observations": len(series.elapsed_s),
        "long_gap_s": float(long_gaps[0]),
        "negative_vent_rows": int((series.vent_nm3_h < 0).sum()),
        "negative_grid_rows": int((series.grid_nm3_h < 0).sum()),
        "source_sha256": series.source_sha256,
    }, ("Source ingestion only; flow reference state is unresolved and values were not converted to mass flow",))


def validate_coupling_evidence_gap(*, work_directory, source_path):
    """Record why this source cannot identify or force the producer model."""
    from dataclasses import fields
    from pathlib import Path
    from h2physics.data.grinhy2 import DOI, HEADERS, load_grinhy2_flow

    del work_directory
    series = load_grinhy2_flow(Path(source_path), expected_sha256=SOURCE_SHA256)
    names = {item.name for item in fields(series)}
    forbidden_evidence = {"current_a", "current_density_a_m2", "power_w",
                          "cell_temperature_k", "stack_temperature_k"}
    if names & forbidden_evidence:
        raise ValueError("The GrInHy2 reader unexpectedly claims electrochemical/electrical observations")
    flow_columns = tuple(name for name in HEADERS if name.endswith("_Nm3_h"))
    if len(flow_columns) != 4 or series.source_id != DOI:
        raise ValueError("The source-bound flow schema or source identity changed")
    series.require_current()
    return ValidationOutcome(True, {
        "source_id": DOI,
        "source_sha256": series.source_sha256,
        "flow_columns": flow_columns,
        "electrochemical_inputs_present": False,
        "normal_volume_reference_state_declared": False,
        "producer_model_fit_admitted": False,
    }, (
        "No current, electrical power, cell temperature, or stack temperature observations exist in the admitted schema.",
        "Nm3/h is retained as reported; the normal-volume reference state is not declared, so no conversion to molar/mass rate is defensible.",
        "No producer-model parameter fit, electrolysis forcing profile, or extrapolation is performed.",
    ))
