"""Rebuild the AHSS 1300 dataset receipt from an explicitly staged raw cache.

No network access is used. Set ``H2_AHSS1300_SOURCE_DIR`` to the versioned
directory containing the acquisition receipt and original Mendeley metadata files.
"""

from __future__ import annotations

import hashlib
import os
import tomllib
from pathlib import Path

from h2physics.data.models import Dataset, RemoteFile

_KEY = "hydrogen-permeation-ms-ahss-1300"
_METADATA_SHA256 = "4546c7c4ec577d12f0f688ce920a13d514bb2c05e391fd574ad268ac6fa5f1a7"
_LIST_SHA256 = "d23a9b0fc10fac770f1289d98612883ae1fb90e11b1539f5d5a5a699a186bb37"
_METADATA_URL = "https://data.mendeley.com/public-api/datasets/tnsgf7v76z/snapshot/1"
_LIST_URL = (
    "https://data.mendeley.com/public-api/datasets/tnsgf7v76z/files?"
    "folder_id=root&version=1&$start=0&$limit=1000"
)
_CURRENT_HEADER = "Current, \u03bcA"


def _read_pinned(path: Path, digest: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Pinned source cache entry is missing or not a regular file: {path.name}")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Pinned source cache entry has an unexpected SHA-256: {path.name}")
    return payload


def build_ahss1300_permeation_fixture(*, work_directory, parameters):
    """Return verified publisher bytes as Dataset plus the original workbook path."""
    source_value = os.environ.get("H2_AHSS1300_SOURCE_DIR")
    if not source_value or not Path(source_value).is_absolute():
        raise ValueError("Set H2_AHSS1300_SOURCE_DIR to the staged version-1 raw-data directory")
    source_dir = Path(source_value)
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("AHSS 1300 source directory must be a real staged directory")
    project_root = Path(__file__).resolve().parents[2]
    with (project_root / "research/data/hydrogen-permeation-ms-ahss-1300.toml").open("rb") as stream:
        receipt = tomllib.load(stream)
    if receipt.get("key") != _KEY or receipt.get("validation_qualified") is not False:
        raise ValueError("Project source receipt is not the expected unqualified AHSS 1300 record")
    metadata = _read_pinned(
        source_dir / f"repository-metadata-{_METADATA_SHA256}.json", _METADATA_SHA256,
    )
    listing = _read_pinned(
        source_dir / f"repository-file-list-0-{_LIST_SHA256}.json", _LIST_SHA256,
    )
    workbook = source_dir / Path(receipt["files"][0]["relative_path"]).name
    file_bytes = _read_pinned(workbook, receipt["files"][0]["sha256"])
    del file_bytes
    if len(listing) > 2_000_000 or len(metadata) > 2_000_000:
        raise ValueError("Pinned publisher metadata exceeds the small receipt budget")
    remote = RemoteFile(
        receipt["files"][0]["name"], receipt["files"][0]["url"],
        receipt["files"][0]["size_bytes"], receipt["files"][0]["publisher_checksum_algorithm"],
        receipt["files"][0]["publisher_checksum"],
    )
    dataset = Dataset(
        key=receipt["key"], title=receipt["title"], doi=receipt["doi"],
        version=receipt["version"], authors=tuple(receipt["authors"]),
        license_id=receipt["license_id"], license_url=receipt["license_url"],
        metadata_url=_METADATA_URL, metadata_sha256=_METADATA_SHA256,
        origin=receipt["origin"], families=tuple(receipt["families"]),
        files=(remote,), metadata_bytes=metadata,
        supporting_metadata=((_LIST_URL, listing),),
    )
    return {
        "dataset": dataset,
        "workbook_path": workbook,
        "expected_current_header": _CURRENT_HEADER,
    }


__all__ = ["build_ahss1300_permeation_fixture"]
