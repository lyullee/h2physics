"""Deferred provenance/schema contract for one cryogenic LH2 phase-change run."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


SOURCE_ARCHIVE_SHA256 = "46301398eeed7c93d7c522581422f45ff5664a844abd412a2d40bcdd175cbbed"


def cases():
    default_dir = (Path(__file__).resolve().parents[2] / "data" / "raw"
                   / "cryo-neutron-phase-change" / "2" / "Jan(H2)" / "jan_tc1"
                   / "jan_tc1_run1")
    return (ValidationCase(
        identifier="cryo-neutron-lh2-phase-change-source-ingestion",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_run",
        parameters={"run_directory": str(default_dir)},
        invariants=(
            "only the selected three version-2 CC BY 4.0 member files and their reviewed SHA-256 values are accepted",
            "selected CSV member CRC32 receipts bind the range-extracted bytes to the publisher ZIP directory",
            "DAQ source seconds remain nondecreasing in original row order, including four adjacent duplicate timestamps; image seconds remain a separate clock",
            "pressure, temperatures, volumes, and thickness retain source-declared units and raw tokens",
            "rate_od_mug and od_error labels are preserved without invented units or mass conversions",
            "the selected table triple is source ingestion only and performs no fit or model comparison",
        ),
    ),)


def validate_source_run(*, work_directory, run_directory):
    from h2physics.data.cryo_neutron_phase_change import (
        SOURCE_ARCHIVE_SHA256 as PINNED_ARCHIVE_SHA256,
        SOURCE_DOI,
        SOURCE_LICENSE,
        load_cryo_neutron_phase_change_run,
    )

    del work_directory
    run = load_cryo_neutron_phase_change_run(run_directory)
    if (run.source_doi != SOURCE_DOI or run.license_id != SOURCE_LICENSE
            or run.publisher_archive_sha256 != SOURCE_ARCHIVE_SHA256
            or PINNED_ARCHIVE_SHA256 != SOURCE_ARCHIVE_SHA256):
        raise AssertionError("Cryo-neutron source identity or rights changed")
    if any(len(point.raw_tokens) != 9 for point in run.daq_points):
        raise AssertionError("DAQ raw records no longer match the reviewed nine-field schema")
    if any(len(point.raw_tokens) != 16 for point in run.image_points):
        raise AssertionError("Image records no longer match the reviewed sixteen-field schema")
    if any(len(point.raw_tokens) != 9 for point in run.rate_windows):
        raise AssertionError("Rate windows no longer match the reviewed nine-field schema")
    if any(point.time_s < 0 for point in run.daq_points) or any(
            later.time_s < earlier.time_s
            for earlier, later in zip(run.daq_points, run.daq_points[1:])):
        raise AssertionError("DAQ source seconds must be nondecreasing in original source-row order")
    duplicate_daq_times = sum(
        later.time_s == earlier.time_s
        for earlier, later in zip(run.daq_points, run.daq_points[1:]))
    if duplicate_daq_times != 4:
        raise AssertionError("Pinned DAQ duplicate-time count changed; inspect source ordering and schema")
    if any(later.image_elapsed_time_s <= earlier.image_elapsed_time_s
           for earlier, later in zip(run.image_points, run.image_points[1:])):
        raise AssertionError("Image elapsed-time channel must remain strictly increasing")
    run.require_current()
    return ValidationOutcome(True, {
        "source_doi": run.source_doi,
        "license_id": run.license_id,
        "publisher_archive_sha256_declared": run.publisher_archive_sha256,
        "selected_run": "tc1/run1; conical cell; 17.9 psia; Tsat 21 K",
        "daq_member_sha256": run.daq_sha256,
        "image_member_sha256": run.image_sha256,
        "rate_member_sha256": run.rate_sha256,
        "daq_observations_1s_nominal": len(run.daq_points),
        "daq_adjacent_duplicate_timestamp_pairs": duplicate_daq_times,
        "image_observation_rows": len(run.image_points),
        "article_image_capture_description_s": 10,
        "phase_rate_windows": len(run.rate_windows),
        "daq_clock_unit": run.daq_time_unit,
        "image_elapsed_clock_unit": run.image_time_unit,
        "image_timestamp_timezone": run.image_timestamp_timezone,
        "phase_rate_unit": run.rate_windows[0].rate_unit,
    }, (
        "Source ingestion only; no phase-change model fit or validation is performed. The test-cell geometry/material mapping, surface sensor positions, accommodation coefficient, full-cell thermal boundary, and phase-rate unit remain unqualified for the repository's finite-tank model.",
    ))
