"""Source-bound access to reported gas/water core-flood relative-permeability tables.

Native worksheet labels and cell values are preserved. This adapter assigns no
normalization, fitting law, or SI interpretation beyond labels written by the authors.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .models import Dataset, license_url_matches

_KEY = "hydrogen-core-flood"
_DOI = "10.17632/rfhf7wjydn.1"
_TITLE = "Steady state core flood data for hydrogen- and nitrogen-water systems"
_AUTHORS = ("Maksim Lysyy", "Tore Føyen")
_META_URL = "https://data.mendeley.com/public-api/datasets/rfhf7wjydn/snapshot/1"
_META_SHA256 = "dbbcb9e3e4b5e4e4a85d513b1111ea9fe7657005acb911d3c36885c01b775b8a"
_LICENSE = "CC-BY-4.0"
_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_LIST_URL = ("https://data.mendeley.com/public-api/datasets/rfhf7wjydn/files?"
             "folder_id=root&version=1&$start=0&$limit=1000")
_LIST_SHA256 = "e91a03765634534500ab119b75544bda441c747198ec03a1afe914db1e919c72"
_FILES = (
    ("Imbibition_H2.xlsx", "17cb9ae3-70cc-4231-b979-643b5d199a90", 1554207,
     "1f07f4bd5f5472f57ff0dd718744b180f8d8ee5b7e4ca9a51d484a90e5e002db", "Kr"),
    ("Primary_drainage_H2.xlsx", "ce094687-9357-4234-8dc4-9fda3efa5199", 2251477,
     "60b94149b4f84b131fc1a70eac592dc741f22486cec1725ec7b904c4b56ec7ff", "Kr"),
    ("Primary_drainage_N2.xlsx", "83ab3ce9-5b2f-47af-a33b-fbc53a8929c4", 2966915,
     "ae2934256439f959f358c3dce468beaed9f6e98b8388934d26a36791fa047a3f", "Kr"),
    ("Secondary_drainage_H2.xlsx", "3616a016-909b-46e2-820b-abfdd4aeae02", 3052789,
     "a79b90ecc62ee1b23f821da31149d0673d741e6652979ce46ddcf77714ba14e4", "Kr"),
)


@dataclass(frozen=True, slots=True)
class CoreFloodTable:
    """One workbook's reported relative-permeability worksheet as native cell rows."""

    filename: str
    source_url: str
    sha256: str
    worksheet: str
    rows: tuple[tuple[object, ...], ...]
    source_row_ids: tuple[str, ...]

    @property
    def headers(self) -> tuple[object, ...]:
        return self.rows[0]


@dataclass(frozen=True, slots=True)
class HydrogenCoreFlood:
    """Four reported Kr worksheets, kept as source-labelled tables without fitting."""

    title: str
    doi: str
    authors: tuple[str, ...]
    license_id: str
    license_url: str
    tables: tuple[CoreFloodTable, ...]

    def table(self, filename: str) -> CoreFloodTable:
        """Select one experiment by its exact publisher attachment name."""
        matches = tuple(item for item in self.tables if item.filename == filename)
        if len(matches) != 1:
            raise ValueError("Select an exact filename from the four admitted source attachments")
        return matches[0]


def _verify_receipt(dataset: Dataset) -> None:
    if type(dataset) is not Dataset:
        raise TypeError("Pass the resolved Mendeley Dataset receipt")
    if (dataset.key != _KEY or dataset.title != _TITLE or dataset.doi != _DOI
            or dataset.version != "1" or dataset.authors != _AUTHORS
            or dataset.license_id != _LICENSE or dataset.license_url != _LICENSE_URL
            or dataset.metadata_url != _META_URL or dataset.metadata_sha256 != _META_SHA256
            or hashlib.sha256(dataset.metadata_bytes).hexdigest() != _META_SHA256
            or dataset.families != ("underground_storage", "two_phase_flow", "relative_permeability")
            or dataset.origin != "measured"):
        raise ValueError("Dataset metadata differs from the pinned CC BY 4.0 v1 record")
    try:
        metadata = json.loads(dataset.metadata_bytes)
        contributors = tuple(" ".join(filter(None, (x.get("first_name"), x.get("last_name"))))
                             for x in metadata["contributors"])
        license_data = metadata["licence"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as error:
        raise ValueError("Publisher metadata does not retain its license and contributor fields") from error
    if (metadata.get("id") != "rfhf7wjydn" or metadata.get("version") != 1
            or metadata.get("doi") != _DOI or metadata.get("name") != _TITLE
            or contributors != _AUTHORS or not isinstance(license_data, dict)
            or license_data.get("short_name") != "CC BY 4.0"
            or not license_url_matches(_LICENSE, license_data.get("url", ""), require_https=False)):
        raise ValueError("Publisher record identity, contributors, or license changed")
    listing_rows = tuple(payload for url, payload in dataset.supporting_metadata if url == _LIST_URL)
    if (len(listing_rows) != 1 or len(dataset.supporting_metadata) != 1
            or hashlib.sha256(listing_rows[0]).hexdigest() != _LIST_SHA256):
        raise ValueError("Pinned publisher attachment listing is absent or has changed")
    listing = json.loads(listing_rows[0])
    if not isinstance(listing, list) or len(listing) != len(_FILES) or len(dataset.files) != len(_FILES):
        raise ValueError("All four versioned workbook attachments must be represented")
    for index, (name, file_id, size, digest, _) in enumerate(_FILES):
        entry = listing[index]
        remote = dataset.files[index]
        url = f"https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/{file_id}/file_downloaded"
        if (entry.get("filename") != name or entry.get("size") != size
                or entry.get("id") != file_id
                or entry.get("content_details", {}).get("sha256_hash") != digest
                or entry.get("content_details", {}).get("download_url") != url
                or remote.name != name or remote.url != url or remote.size_bytes != size
                or remote.checksum_algorithm != "sha256" or remote.checksum != digest):
            raise ValueError("Publisher file identity or checksum differs from pinned v1 listing")


def load_hydrogen_core_flood(directory: str | Path, *, dataset: Dataset) -> HydrogenCoreFlood:
    """Read only the four `Kr` tabs after validating publisher receipt and file hashes.

    Requires the optional `data` dependencies. Workbook formulas are loaded as
    stored expressions (`data_only=False`); no recalculation is attempted.
    """
    _verify_receipt(dataset)
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise ImportError("Install h2physics[data] to read core-flood workbooks") from error
    root = Path(directory)
    tables = []
    for name, file_id, size, expected_hash, sheet_name in _FILES:
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
            raise ValueError(f"Source workbook {name!r} is missing or has an unexpected byte size")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_hash:
            raise ValueError(f"Source workbook {name!r} differs from publisher SHA-256")
        url = f"https://data.mendeley.com/public-files/datasets/rfhf7wjydn/files/{file_id}/file_downloaded"
        workbook = load_workbook(path, read_only=True, data_only=False)
        try:
            if sheet_name not in workbook.sheetnames:
                raise ValueError(f"Source workbook {name!r} lacks its reported {sheet_name!r} tab")
            sheet = workbook[sheet_name]
            rows = tuple(tuple(row) for row in sheet.iter_rows(values_only=True))
            while rows and all(value is None for value in rows[-1]):
                rows = rows[:-1]
            if len(rows) < 2 or not rows[0] or all(value is None for value in rows[0]):
                raise ValueError(f"Source workbook {name!r} has no tabular Kr observations")
            row_ids = tuple(f"hydrogen-core-flood:{name}:{sheet_name}:row-{index}"
                             for index in range(1, len(rows) + 1))
            tables.append(CoreFloodTable(name, url, digest, sheet_name, rows, row_ids))
        finally:
            workbook.close()
    return HydrogenCoreFlood(_TITLE, _DOI, _AUTHORS, _LICENSE, _LICENSE_URL, tuple(tables))
