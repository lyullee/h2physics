"""Deferred source-pinned SOFC curve bridge to the existing stack model."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

SOURCE_SHA256 = "eac5c114ecec8747169dd2f260a599a8f8fdcaeddcea8856ab1fd44161cf4e33"


def cases():
    return (ValidationCase(
        identifier="sofc-polarization-existing-hydrogen-stack-bridge",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_model_bridge",
        parameters={
            "source_path": str(Path(__file__).resolve().parents[2]
                                / "data" / "raw" / "sofc-polarization" / "1"
                                / "Ui_50H2_10H2O_40N2.txt"),
            "expected_sha256": SOURCE_SHA256,
        },
        invariants=(
            "the exact CC BY 4.0 Mendeley v1 file hash and corrupted-header unit policy are enforced",
            "one measured-condition current-density/temperature curve enters the existing HydrogenStack fuel-cell evaluator",
            "reported voltage origin remains unresolved because the publisher says the archive mixes experimental and multiphysics-model curves",
            "the caller's thermochemistry and loss callbacks are retained and outputs reproduce without fitting or extrapolation",
            "the fixture model is synthetic and the contract does not qualify SOFC performance",
        ),
    ),)


def validate_source_model_bridge(*, work_directory, source_path, expected_sha256):
    del work_directory
    from h2physics.adapters.sofc_fuel_cell_curve import compare_sofc_curve_with_hydrogen_stack
    from h2physics.data.sofc_polarization import load_sofc_polarization_data
    from h2physics.electrochemistry import HydrogenStack, ReactionEnergy, StackGeometry

    source = load_sofc_polarization_data(source_path)
    if source.source_sha256 != expected_sha256:
        raise ValueError("Hangang-pinned SOFC source hash differs")
    # Deliberately synthetic callbacks test API ownership only; not a SOFC fit.
    stack = HydrogenStack(
        StackGeometry(series_cells=1, active_area_m2=1.0, hydrogen_molar_mass_kg_mol=0.00201588),
        lambda _temperature: ReactionEnergy(220000., 250000., "fixture-reference", "vapor"),
        {},
    )
    trace = compare_sofc_curve_with_hydrogen_stack(
        source, stack, temperature_k=1073.15,
        model_evidence_id="fixture-only-synthetic-SOFC-thermochemistry",
    )
    trace.require_current()
    if not trace.points or trace.source_sha256 != SOURCE_SHA256 or trace.source_doi != "10.17632/j8b9v4cb9d.1":
        raise ValueError("SOFC source/model bridge did not retain its pinned source and result")
    return ValidationOutcome(True, {
        "source_sha256": trace.source_sha256,
        "source_doi": trace.source_doi,
        "temperature_k": trace.temperature_k,
        "source_rows_evaluated": len(trace.points),
        "source_voltage_origin": "unresolved",
        "synthetic_model_callbacks": True,
    }, (
        "Synthetic HydrogenStack callbacks exercise source/model binding only; no experimental validation is claimed.",
        "Mendeley v1 includes both experimental and multiphysics-generated curves; reported voltage origin remains unresolved.",
        "Nominal feed fractions are not local gas activities; caller thermochemistry applicability remains unverified.",
    ))
