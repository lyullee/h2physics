"""Metadata contract for the evidence-gated MHC temperature observation adapter."""

import tomllib
import os
from datetime import datetime
from pathlib import Path

from h2physics.cluster_validation import ValidationCase, ValidationOutcome


def cases():
    return (ValidationCase(
        identifier="mhc-compressor-temperature-observation-contract",
        profile="source-data-ingestion",
        entrypoint=__name__ + ":validate_manifest_contract",
        parameters={"manifest_path": str(
            Path(__file__).resolve().parents[2]
            / "research" / "data" / "hydride-compressor.toml"
        )},
        invariants=(
            "the MHC adapter is bound to the acquired v1.2 CC BY 4.0 archive digest",
            "only measured raw logger temperatures are admissible; selected/calibration exports are excluded",
            "sensor-to-bed, clock alignment, and model interpolation each require caller evidence",
            "temperature residuals are diagnostic only and do not calibrate or validate the compressor",
            "logger field names do not independently establish bed sensor locations",
        ),
    ),)


def validate_manifest_contract(*, work_directory, manifest_path):
    del work_directory
    from dataclasses import replace

    with Path(manifest_path).open("rb") as stream:
        manifest = tomllib.load(stream)
    from h2physics.adapters.mhc_compressor_temperature import compare_mhc_temperature_to_compressor_bed
    from h2physics.data.hydride_compressor import HydrideCompressorArchive

    if (manifest.get("doi") != "10.5281/zenodo.19036733"
            or manifest.get("version") != "v1.2"
            or manifest.get("license_id") != "CC-BY-4.0"
            or manifest.get("acquired_bytes") != 377874239
            or len(manifest.get("files", ())) != 1
            or manifest["files"][0].get("sha256")
            != "91755fb1e555e0eb32d160ac140a4261b6bb47d24944c7e717b723fe2a641e32"):
        raise ValueError("MHC archive receipt no longer matches the reviewed v1.2 source")
    raw_root = os.environ.get("H2_CLUSTER_DATA_RAW_ROOT")
    if not raw_root or not Path(raw_root).is_absolute():
        raise ValueError("Supply an absolute raw-data snapshot root")
    archive_path = Path(raw_root) / manifest["files"][0]["relative_path"]
    with HydrideCompressorArchive(archive_path) as archive:
        with archive.experiment(8) as experiment:
            schema = experiment.schemas(experiment.raw_sheet)[0]
            blocks = next(experiment.iter_blocks(
                experiment.raw_sheet, datetime_origin=datetime(1970, 1, 1),
                start_row=schema.first_data_row, stop_row=schema.first_data_row + 2,
            ))
            block = blocks[0]
            if (block.archive_receipt_verified is not True
                    or dict(block.observations.context).get("archive_sha256")
                    != manifest["files"][0]["sha256"]):
                raise ValueError("Reader-issued block did not retain verified MHC archive provenance")
            for clone in (lambda: replace(block), lambda: type(block)(
                    block.observations, block.schema, block.source_rows, block.raw_cells,
                    block.invalid_reasons, block.formula_cells)):
                try:
                    clone()
                except TypeError:
                    continue
                raise ValueError("Caller clone/direct construction forged a verified source block")
    return ValidationOutcome(True, {
        "doi": manifest["doi"],
        "license_id": manifest["license_id"],
        "archive_sha256": manifest["files"][0]["sha256"],
        "adapter_callable": callable(compare_mhc_temperature_to_compressor_bed),
        "experimental_comparison_performed": False,
        "reader_issued_archive_verified_block": True,
        "caller_forgery_paths_rejected": True,
    }, (
        "The archive is read through the hash-pinned reader for a three-row provenance contract; no archive member is extracted.",
        "An actual comparison additionally needs independent sensor, clock, and bed-state mapping evidence.",
        "No fit or physical validation is implied.",
    ))
