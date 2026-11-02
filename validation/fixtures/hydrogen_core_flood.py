"""Staged-input fixture for the public hydrogen core-flood workbooks.

The publisher files and metadata responses are staged outside the repository.
This fixture reconstructs the curated publisher receipt from exact metadata
bytes via the repository resolver, then hands the loader the local source
directory. It never downloads or embeds workbook bytes.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from h2physics.data import DATASETS, dataset_from_mendeley_bytes


_DATASET_KEY = "hydrogen-core-flood"
_SOURCE_DIRECTORY_ENV = "H2_HYDROGEN_CORE_FLOOD_SOURCE_DIR"
_METADATA_SHA256 = "dbbcb9e3e4b5e4e4a85d513b1111ea9fe7657005acb911d3c36885c01b775b8a"
_LIST_SHA256 = "e91a03765634534500ab119b75544bda441c747198ec03a1afe914db1e919c72"


def _read_pinned(path: Path, expected_sha256: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required staged publisher metadata is absent: {path.name}")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"Staged publisher metadata has an unexpected digest: {path.name}")
    return payload


def build_hydrogen_core_flood_fixture(*, work_directory, parameters):
    """Return a repository-issued Dataset and the staged source directory.

    Configure ``source_directory`` in a campaign profile, or set
    ``H2_HYDROGEN_CORE_FLOOD_SOURCE_DIR`` in the worker environment. Publisher
    metadata hashes are checked here. Workbook names, sizes and digests are
    checked by the source loader before spreadsheet parsing.
    """
    del work_directory  # The source is externally staged and remains read-only.
    params = parameters if isinstance(parameters, dict) else {}
    source_value = params.get("source_directory") or os.environ.get(_SOURCE_DIRECTORY_ENV)
    if not isinstance(source_value, str) or not source_value.strip():
        raise ValueError(
            "Set source_directory or H2_HYDROGEN_CORE_FLOOD_SOURCE_DIR to the staged source"
        )
    source_directory = Path(source_value)
    if (not source_directory.is_absolute() or source_directory.is_symlink()
            or not source_directory.is_dir()):
        raise ValueError("Core-flood source directory must be an absolute, real staged directory")

    seeds = tuple(seed for seed in DATASETS if seed.key == _DATASET_KEY)
    if len(seeds) != 1:
        raise RuntimeError("Curated hydrogen core-flood dataset seed is missing or ambiguous")
    snapshot = _read_pinned(source_directory / "metadata.json", _METADATA_SHA256)
    listing = _read_pinned(source_directory / "file-listing.json", _LIST_SHA256)
    # The parser preserves staged bytes but does not issue repository replay
    # authority. The consuming adapter checks identity against pinned v1 fields.
    dataset = dataset_from_mendeley_bytes(
        seeds[0], snapshot_bytes=snapshot, file_listing_bytes=listing,
        expected_snapshot_sha256=_METADATA_SHA256,
        expected_listing_sha256=_LIST_SHA256,
    )
    return {"dataset": dataset, "directory": source_directory}


__all__ = ["build_hydrogen_core_flood_fixture"]
