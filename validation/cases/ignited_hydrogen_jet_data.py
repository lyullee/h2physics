"""Deferred source-ingestion contract for the DataverseNO X044QK matrix."""

import math

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="dataverse-x044qk-open-atmosphere-ignited-hydrogen-jet-matrix",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_matrix",
        parameters={
            "matrix_path": "/scratch/r1021a02/h2physics-source-attachments/"
                           "ignited-hydrogen-jet-x044qk/1/Matrix and H2 flow results.xlsx",
        },
        invariants=(
            "DataverseNO DOI, CC0 1.0 license, matrix PID, MD5, SHA-256 and byte size are pinned",
            "all 40 source matrix rows retain exact experiment numbers, headers and workbook row IDs",
            "the first row's reported pressure, pressure-derived flow and test conditions match retained source cells",
            "blank comments and text-valued obstacle conditions are preserved rather than coerced",
            "source workbook formulas are not executed or admitted as observations",
            "pressure basis and pressure-derived MFR remain source-stated and are not converted or qualified",
        ),
    ),)


def validate_matrix(*, work_directory, **parameters):
    from h2physics.data.ignited_hydrogen_jet import load_ignited_hydrogen_jet_matrix

    path = parameters.get("matrix_path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Stage the exact DataverseNO matrix attachment and configure matrix_path")
    matrix = load_ignited_hydrogen_jet_matrix(path)
    assert matrix.source_doi == "10.18710/X044QK"
    assert matrix.license_id == "CC0-1.0"
    assert matrix.source_file_pid == "doi:10.18710/X044QK/JH7P7P"
    assert matrix.source_size_bytes == 14199
    assert matrix.source_md5 == "6c929ee530ac393ee8e76f6db2eff05c"
    assert matrix.source_sha256 == "c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557"
    assert len(matrix.experiments) == 40
    assert tuple(item.experiment_number for item in matrix.experiments) == tuple(range(1, 41))
    first = matrix.experiment(1)
    assert first.source_row_id.endswith("Sheet1:row-3")
    assert math.isclose(first.reported_max_pressure_bar, 51.57337188720703,
                        rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(first.pressure_derived_max_mass_flow_kg_s,
                        0.007206352893263102, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(first.reported_average_pressure_bar, 33.466773986816406,
                        rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(first.pressure_derived_average_mass_flow_kg_s,
                        0.004676316399127245, rel_tol=0.0, abs_tol=1e-15)
    assert first.ignition_location_code == 3
    assert first.obstacle_distance_raw == 29
    assert first.hydrogen_release_time_s == 3.0 and first.ignition_delay_time_s == 2.5
    assert first.raw_cells == matrix.rows[0]
    assert matrix.experiment(40).experiment_number == 40
    assert matrix.require_current() is matrix
    summary = matrix.summary()
    return ValidationOutcome(True, {
        "doi": matrix.source_doi,
        "license_id": matrix.license_id,
        "matrix_sha256": matrix.source_sha256,
        "experiment_rows": summary["experiment_rows"],
        "first_experiment_reported_max_pressure_bar": first.reported_max_pressure_bar,
        "first_experiment_pressure_derived_max_mfr_kg_s": first.pressure_derived_max_mass_flow_kg_s,
        "max_reported_pressure_bar": summary["max_reported_pressure_bar"],
        "max_pressure_derived_mfr_kg_s": summary["max_pressure_derived_mfr_kg_s"],
        "pressure_basis": "unresolved/source-stated",
    }, (
        "The matrix contains source-reported condition summaries; the publisher notes mass flow is calculated from pressure.",
        "This ingestion/summary contract is not a pressure calibration, release-model comparison, or dispersion validation.",
        "The 39 raw time-history files and high-speed video bundles are not included in this matrix-only case.",
    ))
