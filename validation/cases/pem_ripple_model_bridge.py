"""Deferred PEM measurement to existing electrolysis-core bridge case."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="pem-ripple-iv-to-hydrogen-stack-diagnostic",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_model_bridge",
        parameters={
            "source_path": str(
                Path(__file__).resolve().parents[2]
                / "data" / "processed" / "pem-ripple" / "2"
                / "PEM1_Initial.csv.gz"
            ),
        },
        invariants=(
            "one selected source member retains its exact parent-archive and member hashes",
            "measured single-cell amperes map to model current density only using caller active area",
            "source voltage is compared only with one-cell HydrogenStack electrolysis voltage",
            "temperature and active-area evidence remain caller inputs, never inferred from source",
            "synthetic thermochemistry is an API fixture and does not qualify a physical model",
        ),
    ),)


def validate_source_model_bridge(*, work_directory, source_path, **parameters):
    del work_directory, parameters
    from h2physics.adapters.pem_ripple_stack import compare_pem_ripple_curve_with_hydrogen_stack
    from h2physics.data.pem_ripple_member import (
        PARENT_ARCHIVE_SHA256,
        load_pem_ripple_iv_member,
    )
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    curve = load_pem_ripple_iv_member(source_path)
    # Explicit fixture inputs exercise only the bridge contract; they are not dataset facts.
    stack = HydrogenStack(
        StackGeometry(1, 0.01, 0.00201588),
        lambda _temperature: ReactionEnergy(
            237000.0, 285800.0, "synthetic-water-reference", "liquid",
        ),
        {},
    )
    trace = compare_pem_ripple_curve_with_hydrogen_stack(
        curve, stack, temperature_k=333.15,
        active_area_evidence_id="synthetic-fixture-area",
        temperature_evidence_id="synthetic-fixture-temperature",
        model_evidence_id="synthetic-fixture-electrochemical-model",
    )
    trace.require_current()
    if (trace.source_sha256 != PARENT_ARCHIVE_SHA256
            or trace.source_member_sha256 != curve.source_member_sha256
            or len(trace.points) != len(curve.current_a)):
        raise ValueError("PEM ripple model bridge lost its source-bound row lineage")
    return ValidationOutcome(True, {
        "parent_archive_sha256": trace.source_sha256,
        "member_sha256": trace.source_member_sha256,
        "source_doi": "10.17632/93jz2rgy4d.2",
        "cell_id": curve.cell_id,
        "cycle": curve.cycle,
        "rows_mapped": len(trace.points),
        "caller_area_and_temperature": True,
        "synthetic_model_callbacks": True,
    }, (
        "Synthetic caller callbacks exercise a source-bound input bridge only; this is not electrolysis validation.",
        "The dataset supplies no active area or cell temperature, and its independent model applicability is unresolved.",
    ))
