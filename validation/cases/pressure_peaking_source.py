"""Deferred receipt/API contract for measured USN flow-to-safety-source projection."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="usn-unignited-measured-flow-finite-source-contract",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_contract",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "pressure-unignited.toml"
        )},
        invariants=(
            "only the exact CC BY 4.0 measured SIGMA flow file and hash are admitted",
            "signed negative mass flow is never clipped or relabeled as positive release",
            "positive and negative flow branches are exercised from the exact measured source rows",
            "flow-to-interval mass requires caller-declared quadrature and exact recorder clock",
            "requested source-window edges must exactly equal measured recorder timestamps",
            "release-plane and representative hydrogen-state evidence remain explicit inputs",
            "meter pressure and GEN3i pressure are not converted or used by this source projection",
            "the finite source is a boundary input only and does not validate enclosure pressure peaking",
        ),
    ),)


def validate_source_contract(*, work_directory, manifest_path, raw_data_root=None):
    del work_directory
    import numpy as np

    from h2physics.core import PropertyBasis, ThermoState
    from h2physics.adapters.pressure_peaking_source import (
        SOURCE_DOI, SOURCE_FILE, SOURCE_SHA256,
        project_pressure_peaking_flow_to_finite_source,
    )
    from h2physics.data.pressure_peaking import load_pressure_mat
    from h2physics.release import SourceLocation

    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    file = next((item for item in manifest.get("files", ())
                 if item.get("name") == SOURCE_FILE), None)
    if (manifest.get("doi") != SOURCE_DOI or manifest.get("license_id") != "CC-BY-4.0"
            or file is None or file.get("sha256") != SOURCE_SHA256
            or file.get("status") != "acquired"):
        raise ValueError("USN SIGMA source receipt or rights status changed")
    if not isinstance(raw_data_root, str) or not Path(raw_data_root).is_absolute():
        raise ValueError("Supply the absolute staged source root injected by the Hangang plan")
    source_path = Path(raw_data_root) / file["relative_path"]
    run = load_pressure_mat(
        source_path, source_id=f"{SOURCE_DOI}:{SOURCE_FILE}",
        experiment_id="USN-source-experiment-00003", expected_sha256=SOURCE_SHA256,
    )
    positive_pair = None
    negative_pair = None
    valid_triple = None
    for block in run.sigma.iter_blocks(block_rows=10000):
        valid = np.asarray(block.series.valid[:, 0], dtype=bool)
        rates = np.asarray(block.series.values[:, 0], dtype=float)
        for index in range(max(0, len(valid) - 1)):
            if not bool(np.all(valid[index:index + 2])):
                continue
            pair_rates = rates[index:index + 2]
            if positive_pair is None and bool(np.all(pair_rates >= 0.)):
                positive_pair = block, index
            if negative_pair is None and bool(np.any(pair_rates < 0.)):
                negative_pair = block, index
        if valid_triple is None:
            matches = [index for index in range(max(0, len(valid) - 2))
                       if bool(np.all(valid[index:index + 3]))]
            if matches:
                valid_triple = block, matches[0]
        if positive_pair and negative_pair and valid_triple:
            break
    if positive_pair is None:
        raise ValueError("Pinned source has no pair of consecutive valid nonnegative flow rows")
    if negative_pair is None:
        raise ValueError("Pinned source has no pair containing a negative measured flow row")
    if valid_triple is None:
        raise ValueError("Pinned source contains no three consecutive valid mass-flow rows")

    test_state = ThermoState(
        PropertyBasis("hydrogen", "Hangang contract-only synthetic thermodynamic basis"),
        101325., 300., .08, 0., 0., 0., "gas",
    )
    test_location = SourceLocation(
        source_id="Hangang contract-only synthetic source",
        clock_id=run.sigma.clock_id,
        coordinate_frame_id="Hangang contract-only synthetic frame",
        position_m=(0., 0., 0.), direction_unit=(1., 0., 0.),
    )
    positive_block, positive_index = positive_pair
    positive_times = np.asarray(
        positive_block.series.time_s[positive_index:positive_index + 2], dtype=float,
    )
    positive_rates = np.asarray(
        positive_block.series.values[positive_index:positive_index + 2, 0], dtype=float,
    )
    positive = project_pressure_peaking_flow_to_finite_source(
        positive_block, location=test_location, representative_state=test_state,
        source_window_s=(float(positive_times[0]), float(positive_times[1])),
        flow_rule="trapezoid",
        release_plane_evidence_id="Hangang contract-only synthetic release-plane placeholder",
        state_projection_evidence_id="Hangang contract-only synthetic state placeholder",
    )
    expected_mass = .5 * (positive_rates[0] + positive_rates[1]) * (positive_times[1] - positive_times[0])
    if (positive.source_rows != tuple(int(x) for x in positive_block.source_rows[positive_index:positive_index + 2])
            or positive.time_s != tuple(float(x) for x in positive_times)
            or not np.isclose(positive.source.mass_kg[0], expected_mass, rtol=1e-12, atol=0.)):
        raise ValueError("Positive-flow finite bins do not preserve exact source rows/clock/quadrature")
    positive.require_current()

    negative_block, negative_index = negative_pair
    negative_times = np.asarray(
        negative_block.series.time_s[negative_index:negative_index + 2], dtype=float,
    )
    try:
        project_pressure_peaking_flow_to_finite_source(
            negative_block, location=test_location, representative_state=test_state,
            source_window_s=(float(negative_times[0]), float(negative_times[1])),
            flow_rule="trapezoid",
            release_plane_evidence_id="Hangang contract-only synthetic release-plane placeholder",
            state_projection_evidence_id="Hangang contract-only synthetic state placeholder",
        )
    except ValueError as error:
        if "negative meter flow is retained" not in str(error):
            raise
        negative_flow_rejected = True
    else:
        raise ValueError("Signed negative mass flow was silently accepted as a release source")

    block, index = valid_triple
    measured_times = np.asarray(block.series.time_s[index:index + 3], dtype=float)
    start = float(.5 * (measured_times[0] + measured_times[1]))
    end = float(measured_times[2])
    if start in measured_times or not measured_times[0] < start < measured_times[1]:
        raise ValueError("Could not construct a representable non-row-aligned interval edge")
    try:
        project_pressure_peaking_flow_to_finite_source(
            block, location=test_location, representative_state=test_state,
            source_window_s=(start, end), flow_rule="trapezoid",
            release_plane_evidence_id="contract-only-evidence",
            state_projection_evidence_id="contract-only-evidence",
        )
    except ValueError as error:
        if "edges must coincide with measured rows" not in str(error):
            raise
        nonaligned_window_rejected = True
    else:
        raise ValueError("Non-row-aligned source-window edge was silently accepted")
    return ValidationOutcome(True, {
        "doi": SOURCE_DOI,
        "filename": SOURCE_FILE,
        "source_sha256": SOURCE_SHA256,
        "license_id": manifest["license_id"],
        "projector_callable": callable(project_pressure_peaking_flow_to_finite_source),
        "source_rows_evaluated": True,
        "positive_measured_flow_projection_contract": True,
        "negative_measured_flow_rejected": negative_flow_rejected,
        "non_row_aligned_source_window_rejected": nonaligned_window_rejected,
        "contract_only_finite_source_created": True,
        "pressure_channels_used": False,
    }, (
        "The case reads pinned measured row pairs to check positive-bin issuance and negative/nonaligned rejection.",
        "A short finite source is created only for API regression using explicitly synthetic state/location/evidence placeholders; it is not an experiment mapping or physical calculation.",
        "Actual use must select a nonnegative source-clock window and provide independent release-plane/state evidence.",
        "No dispersion, overpressure, or accident validation is implied.",
    ))
