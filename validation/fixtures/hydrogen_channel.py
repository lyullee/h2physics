"""Offline fixture for one hash-pinned public Figshare channel experiment.

The original metadata response and archive are staged outside the repository.
This module reconstitutes the public record from the exact metadata bytes and
does not fetch or redistribute third-party files.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from h2physics.data import DATASETS, dataset_from_figshare_bytes

_KEY = "hydrogen-channel"
_METADATA_SHA256 = "ecfb5690fe87b9c8ad9293a0783e33a24818556d38446e97e1103c8c3d1eb2dc"
_ARCHIVE_NAME = "23_FFI_P101_T00005.zip"
_ARCHIVE_SHA256 = "b6243a250ca5dcef7a1577132d3740af34efc0fe9baebbc02087203b23cea0d9"
_SOURCE_DIRECTORY_ENV = "H2_HYDROGEN_CHANNEL_SOURCE_DIR"


def _read_pinned(path: Path, expected_sha256: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required staged hydrogen-channel source file is missing: {path.name}")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"Staged hydrogen-channel file has an unexpected SHA-256: {path.name}")
    return payload


def build_hydrogen_channel_case_fixture(*, work_directory, parameters):
    """Return the pinned Figshare record and one staged experiment archive.

    Set the campaign's ``source_directory`` parameter or the
    ``H2_HYDROGEN_CHANNEL_SOURCE_DIR`` environment variable to a read-only
    directory containing ``repository-metadata.json`` and the selected ZIP.
    """
    del work_directory
    params = parameters if isinstance(parameters, dict) else {}
    source_value = params.get("source_directory") or os.environ.get(_SOURCE_DIRECTORY_ENV)
    if not isinstance(source_value, str) or not source_value.strip():
        raise ValueError(
            "Set source_directory or H2_HYDROGEN_CHANNEL_SOURCE_DIR to staged public source files"
        )
    source_dir = Path(source_value)
    if not source_dir.is_absolute() or source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("Hydrogen-channel source directory must be an absolute real directory")

    seeds = tuple(seed for seed in DATASETS if seed.key == _KEY)
    if len(seeds) != 1:
        raise RuntimeError("Curated hydrogen-channel Figshare seed is missing or ambiguous")
    metadata = _read_pinned(source_dir / "repository-metadata.json", _METADATA_SHA256)
    archive_path = source_dir / _ARCHIVE_NAME
    _read_pinned(archive_path, _ARCHIVE_SHA256)
    dataset = dataset_from_figshare_bytes(
        seeds[0], snapshot_bytes=metadata, expected_snapshot_sha256=_METADATA_SHA256,
    )
    return {
        "dataset": dataset,
        "archive_path": archive_path,
        "file_name": _ARCHIVE_NAME,
        "expected_sha256": _ARCHIVE_SHA256,
    }


__all__ = ["build_hydrogen_channel_case_fixture"]
