"""Deferred source-bound API contract for ignited USN measured SIGMA flow."""

import tomllib
from pathlib import Path

import numpy as np

from h2physics.cluster_validation import ValidationCase, ValidationOutcome

DOI = "10.23642/usn.17934047.v1"
FILE = "HTE341USN0015READ191111.mat"
SHA256 = "3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4"


def cases():
    return (ValidationCase(
        identifier="usn-ignited-measured-flow-finite-source-contract",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_contract",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2] / "research" / "data" / "pressure-ignited.toml"
        )},
        invariants=(
            "only the hash-pinned CC BY 4.0 ignited SIGMA measured mass-flow channel enters the finite source",
            "raw SIGMA and GEN3i dimension/unit label vectors match the reviewed source profile exactly",
            "the additional top-level Tavg variable is retained under its raw name and shape without inferred units or semantics",
            "g/s conversion is limited to the documented SIGMA mass-flow channel",
            "source-window edges coincide exactly with rows on the SIGMA recorder clock",
            "negative measured flow is rejected and never clipped or relabeled",
            "flow quadrature, release plane, source-clock placement, and H2 state are caller supplied",
            "GEN3i remains on its independent clock and its unknown second column is preserved but unused",
            "pressure and ignition-overpressure comparison remain outside this boundary",
        ),
    ),)


def validate_contract(*, work_directory, manifest_path, raw_data_root=None):
    del work_directory
    from h2physics.adapters.pressure_ignited_source import project_ignited_usn_flow
    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.data.pressure_ignited import load_pressure_ignited_mat
    from h2physics.release import SourceLocation

    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    entry = next((item for item in manifest.get("files", ()) if item.get("name") == FILE), None)
    if (manifest.get("doi") != DOI or manifest.get("license_id") != "CC-BY-4.0"
            or entry is None or entry.get("status") != "acquired"
            or entry.get("size_bytes") != 40_666_968 or entry.get("sha256") != SHA256):
        raise ValueError("Ignited USN attachment receipt or license changed")
    if not isinstance(raw_data_root, str) or not Path(raw_data_root).is_absolute():
        raise ValueError("An absolute Hangang staged-data root is required")
    run = load_pressure_ignited_mat(
        Path(raw_data_root) / entry["relative_path"],
        experiment_id="USN-ignited-source-experiment-0015", expected_sha256=SHA256,
    )
    if run.tavg_raw.shape != (999_999, 1) or run.tavg_raw.flags.writeable:
        raise ValueError("Unlabeled Tavg recorder array was not retained as immutable raw data")

    candidate = None
    triple = None
    negative_seen = False
    for block in run.iter_flow_blocks(block_rows=100_000):
        rates = np.asarray(block.series.values[:, 0], dtype=float)
        valid = np.asarray(block.series.valid[:, 0], dtype=bool)
        negative_seen = negative_seen or bool(np.any(valid & (rates < 0.)))
        if candidate is None:
            for index in range(max(0, len(rates) - 1)):
                if valid[index] and valid[index + 1] and rates[index] >= 0. and rates[index + 1] >= 0.:
                    candidate = block, index
                    break
        if triple is None:
            for index in range(max(0, len(rates) - 2)):
                if bool(np.all(valid[index:index + 3])):
                    triple = block, index
                    break
        if candidate is not None and triple is not None and negative_seen:
            break
    if candidate is None or triple is None:
        raise ValueError("Pinned SIGMA source has no valid nonnegative adjacent rows or three-row window")

    state = ThermoState(
        PropertyBasis("hydrogen", "Hangang API-contract synthetic state"),
        101325., 300., .08, 0., 0., 0., "gas",
    )
    block, index = candidate
    pair_times = np.asarray(block.series.time_s[index:index + 2], dtype=float)
    location = SourceLocation(
        source_id="Hangang API-contract synthetic release plane",
        clock_id=block.series.clock_id,
        coordinate_frame_id="Hangang API-contract synthetic coordinate frame",
        position_m=(0., 0., 0.), direction_unit=(1., 0., 0.),
    )
    projection = project_ignited_usn_flow(
        block, location=location, representative_state=state,
        source_window_s=(float(pair_times[0]), float(pair_times[1])),
        flow_rule="trapezoid",
        release_plane_evidence_id="Hangang API-contract placeholder; not an experiment mapping",
        state_projection_evidence_id="Hangang API-contract placeholder; not an experiment mapping",
    )
    projection.require_current()

    triple_block, triple_index = triple
    triple_times = np.asarray(triple_block.series.time_s[triple_index:triple_index + 3], dtype=float)
    nonaligned_start = float(.5 * (triple_times[0] + triple_times[1]))
    if triple_times[0] < nonaligned_start < triple_times[1]:
        try:
            project_ignited_usn_flow(
                triple_block, location=location, representative_state=state,
                source_window_s=(nonaligned_start, float(triple_times[2])), flow_rule="trapezoid",
                release_plane_evidence_id="contract-only",
                state_projection_evidence_id="contract-only",
            )
        except ValueError as error:
            if "coincide with measured rows" not in str(error):
                raise
            nonaligned_rejected = True
        else:
            raise ValueError("Non-row-aligned window was accepted")
    else:
        raise ValueError("Could not choose a non-row-aligned window edge")

    return ValidationOutcome(True, {
        "doi": DOI,
        "filename": FILE,
        "sha256": SHA256,
        "source_rows": projection.source_rows,
        "source_window_s": projection.source_window_s,
        "raw_sigma_dimensions_labels_pinned": run.sigma_dimensions,
        "raw_sigma_unit_labels_pinned": run.sigma_labels,
        "raw_gen3i_dimensions_labels_pinned": run.gen3i_dimensions,
        "raw_gen3i_unit_labels_pinned": run.gen3i_labels,
        "unresolved_auxiliary_mat_variable_names": ("Tavg",),
        "unresolved_auxiliary_mat_variable_shapes": {"Tavg": run.tavg_raw.shape},
        "unresolved_auxiliary_values_used_for_projection": False,
        "finite_source_mass_bins": int(len(projection.source.mass_kg)),
        "negative_flow_present_in_scanned_rows": negative_seen,
        "nonaligned_window_rejected": nonaligned_rejected,
        "pressure_channels_used": False,
        "gen3i_alignment_attempted": False,
    }, (
        "The selected adapter output uses only source-defined SIGMA measured mass flow and explicitly synthetic state/location placeholders.",
        "The case checks row/clock preservation and does not infer a physical nozzle plane or ignition state.",
        "Pressure or ignition-overpressure comparison still requires sensor, timing, filtering, and source-state evidence.",
    ))
