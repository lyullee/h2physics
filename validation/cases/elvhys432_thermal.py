"""Hangang source ingestion contract for ELVHYS 4.3.2 Test-1 diodes."""

import tomllib
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.data.elvhys432 import (
    DOI, TEMPERATURE_SHA256, load_elvhys432_temperature_csv,
)


def cases():
    return (ValidationCase(
        identifier="elvhys432-pipe-surface-temperature-source-ingest",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_sample",
        parameters={
            "raw_data_root": "/scratch/r1021a02/h2physics-source-attachments/elvhys-fireline/1",
            "manifest_path": str(Path(__file__).resolve().parents[2]
                                  / "research" / "data" / "elvhys432-fireline.toml"),
        },
        invariants=(
            "only the published README and Test-1 diode CSV are hash checked and read",
            "source time remains minutes and both reported temperature channels remain kelvin",
            "source times are strictly increasing before they may be considered for an exact-time comparison",
            "SD2 outlet process temperature is preserved but not projected onto a radial wall face",
            "no property fitting, heat-flux inference, model execution, or physical qualification is claimed",
        ),
    ),)


def validate_sample(*, work_directory, raw_data_root, manifest_path):
    del work_directory
    with Path(manifest_path).open("rb") as stream:
        record = tomllib.load(stream)
    if (record.get("doi") != DOI or record.get("version") != "1.0"
            or record.get("license_id") != "CC0-1.0"
            or record.get("acquired_bytes") != 482_617):
        raise ValueError("ELVHYS 4.3.2 manifest rights or acquired scope changed")
    sample = load_elvhys432_temperature_csv(raw_data_root)
    if sample.source_sha256 != TEMPERATURE_SHA256 or len(sample.rows) < 2:
        raise ValueError("ELVHYS 4.3.2 Test-1 source receipt or rows are missing")
    if any(a.time_min >= b.time_min for a, b in zip(sample.rows, sample.rows[1:])):
        raise ValueError("ELVHYS 4.3.2 time series is not strictly increasing")
    return ValidationOutcome(True, {
        "doi": DOI,
        "license_id": "CC0-1.0",
        "temperature_sha256": sample.source_sha256,
        "row_count": len(sample.rows),
        "first_time_min": sample.rows[0].time_min,
        "first_pipe_surface_temperature_k": sample.rows[0].pipe_surface_temperature_k,
        "first_outlet_process_temperature_k": sample.rows[0].outlet_process_temperature_k,
        "radial_heat_model_compared": False,
    }, (
        "The acquired source contains a pipe-surface diode signal and an outlet process-temperature signal.",
        "A future exact-time radial wall comparison requires caller evidence for sensor location, physical pipe-to-domain mapping, and clock alignment.",
        "The source README says the silicon diodes were not calibrated; the data are not used to fit heat flux or material properties.",
    ))
