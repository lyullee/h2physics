"""Deferred source-ingestion contract for the acquired H2SAFE archive."""

from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


ARCHIVE_SHA256 = "f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e"


def cases():
    default_archive = (Path(__file__).resolve().parents[2] / "data" / "raw"
                       / "h2safe-indoor" / "2026-10-05" / "1787856683-Dataset.zip")
    return (ValidationCase(
        identifier="h2safe-indoor-source-bound-experiment-ingestion",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_source_archive",
        parameters={"source_archive_path": str(default_archive),
                    "experiment": "Lab1_Small/test1.csv"},
        invariants=(
            "the acquired publisher ZIP is accepted only with its reviewed full archive hash and exact member allowlist",
            "experiment channel labels map to the same lab's declared sensor-position identifiers",
            "source rows and raw tokens align with the numeric view and retain missing-value markers",
            "the retained archive path, checksum, metadata identity and license are source-bound",
            "time basis, concentration units, sensor calibration and coordinate frame remain unresolved",
            "the source is a helium-surrogate release and is not direct hydrogen dispersion evidence",
            "ingestion does not qualify a dispersion model or infer building ventilation physics",
        ),
    ),)


def validate_source_archive(*, work_directory, source_archive_path, experiment):
    from h2physics.data.h2safe_indoor import (
        DATASET_ID,
        LICENSE_ID,
        METADATA_SHA256,
        load_h2safe_indoor_series,
    )

    del work_directory
    series = load_h2safe_indoor_series(
        source_archive_path, experiment=experiment, expected_sha256=ARCHIVE_SHA256,
    )
    if (series.dataset_id != DATASET_ID or series.license_id != LICENSE_ID
            or series.metadata_sha256 != METADATA_SHA256
            or series.archive_sha256 != ARCHIVE_SHA256):
        raise AssertionError("H2SAFE source identity, rights or content hash changed")
    sensor_ids = {sensor.sensor_id.casefold() for sensor in series.sensors}
    if any(channel.casefold() not in sensor_ids for channel in series.channel_ids):
        raise AssertionError("H2SAFE measurement columns lost their sensor mapping")
    if len(series.raw_tokens) != len(series.time_values) or any(
            len(raw) != len(values) + 1
            for raw, values in zip(series.raw_tokens, series.sensor_values)):
        raise AssertionError("H2SAFE source tokens and numeric observations are no longer aligned")
    series.require_current()
    missing = sum(value is None for row in series.sensor_values for value in row)
    return ValidationOutcome(True, {
        "dataset_id": series.dataset_id,
        "license_id": series.license_id,
        "archive_sha256": series.archive_sha256,
        "experiment": series.experiment,
        "observations": len(series.time_values),
        "measurement_channels": len(series.channel_ids),
        "mapped_sensors": len(series.sensors),
        "retained_missing_values": missing,
        "time_unit": series.time_unit,
        "concentration_unit": series.concentration_unit,
    }, (
        "Source ingestion only. The reviewed experiments use helium as a surrogate, not hydrogen release measurements. Sensor calibration, concentration basis, clock synchronization, room geometry, and ventilation boundary conditions remain unresolved.",
    ))
