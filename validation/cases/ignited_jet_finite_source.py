"""Deferred source-row projection from DataverseNO X044QK to finite H2 input."""

import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="x044qk-average-flow-finite-hydrogen-source-bridge",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_finite_source",
        parameters={
            "matrix_path": "/scratch/r1021a02/h2physics-source-attachments/"
                           "ignited-hydrogen-jet-x044qk/1/Matrix and H2 flow results.xlsx",
        },
        invariants=(
            "exact CC0 source matrix and selected experiment row remain hash/row bound",
            "only publisher-reported average pressure-derived MFR and H2 release duration feed the finite source bin",
            "representative pure-H2 state, location, clock and both mapping evidence IDs are caller supplied",
            "source matrix pressure is not converted and peak MFR is not used",
            "one-bin mean source is not a recovered transient history or dispersion validation",
        ),
    ),)


def validate_finite_source(*, work_directory, **parameters):
    from h2physics.adapters.ignited_jet_finite_source import project_ignited_jet_average_source
    from h2physics.core import Origin, PropertyBasis, ThermoState
    from h2physics.data.ignited_hydrogen_jet import load_ignited_hydrogen_jet_matrix
    from h2physics.release import SourceLocation

    path = parameters.get("matrix_path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Stage the exact CC0 matrix file and configure matrix_path")
    matrix = load_ignited_hydrogen_jet_matrix(path)
    experiment_number = 1
    row = matrix.experiment(experiment_number)
    location = SourceLocation("synthetic-case-location", "x044qk/release-clock",
        "synthetic-coordinate-frame", (0., 0., 0.), (1., 0., 0.))
    state = ThermoState(PropertyBasis("Hydrogen", "synthetic-case-state", "normal"),
        101325., 300., 0.081, 0., 0., 0., "gas")
    projection = project_ignited_jet_average_source(matrix, experiment_number,
        location=location, state=state, start_s=0., clock_id=location.clock_id,
        flow_acceptance_evidence_id="deferred-case-explicitly-accepts-source-pressure-derived-average-MFR",
        clock_mapping_evidence_id="deferred-case-places-release-window-on-declared-clock-from-zero")
    projection.require_current()
    source = projection.source
    expected_mass = row.pressure_derived_average_mass_flow_kg_s * row.hydrogen_release_time_s
    if (source.origin is not Origin.RECONSTRUCTED
            or source.total_mass_kg != expected_mass
            or source.edges_s[-1] != row.hydrogen_release_time_s
            or not math.isclose(source.mean_rates_kg_s[0],
                row.pressure_derived_average_mass_flow_kg_s, rel_tol=1e-14, abs_tol=0.)):
        raise AssertionError("X044QK finite mean-source projection failed")
    return ValidationOutcome(True, {
        "dataset_doi": matrix.source_doi,
        "license_id": matrix.license_id,
        "matrix_sha256": matrix.source_sha256,
        "source_row_id": row.source_row_id,
        "average_pressure_derived_mfr_kg_s": row.pressure_derived_average_mass_flow_kg_s,
        "release_duration_s": row.hydrogen_release_time_s,
        "projected_mass_kg": source.total_mass_kg,
        "finite_bins": len(source.mass_kg),
        "origin": source.origin.value,
        "pressure_conversion_performed": False,
        "peak_flow_used": False,
        "physical_validation_claimed": False,
    }, (
        "Publisher states mass flow was calculated from experimental pressure; pressure basis remains unresolved.",
        "One constant mean-rate bin is a finite-source projection, not the absent measured time history.",
        "Location and thermodynamic state are synthetic case inputs, not experiment reconstruction.",
        "The matrix does not validate dispersion, ignition, flame or overpressure physics.",
    ))
