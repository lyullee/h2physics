"""Source-bound access to the measured MS AHSS grade 1300 permeation workbook.

The reader keeps the two publisher worksheets as observations. It does not
infer an exposed electrode area, boundary flux or material coefficient.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core import Origin, _real_numeric_array, immutable_array
from .models import Dataset, license_url_matches

_KEY = "hydrogen-permeation-ms-ahss-1300"
_DOI = "10.17632/tnsgf7v76z.1"
_TITLE = "Hydrogen permeation test on MS AHSS grade 1300"
_AUTHORS = ("Giuseppe Macoretta",)
_METADATA_URL = "https://data.mendeley.com/public-api/datasets/tnsgf7v76z/snapshot/1"
_METADATA_SHA256 = "4546c7c4ec577d12f0f688ce920a13d514bb2c05e391fd574ad268ac6fa5f1a7"
_LICENSE_ID = "CC-BY-4.0"
_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_FILE = "Permeation_MS AHSS 1300.xlsx"
_FILE_SIZE = 88885
_FILE_SHA256 = "117d75a3f8329456732beada95b8f2be8bda688da88e6b8c7c83a9ee49698b3b"
_FILE_URL = "https://data.mendeley.com/public-files/datasets/tnsgf7v76z/files/64121556-2ab2-4aec-8a20-4bc51d48ad44/file_downloaded"
_FILE_LIST_URL = (
    "https://data.mendeley.com/public-api/datasets/tnsgf7v76z/files?"
    "folder_id=root&version=1&$start=0&$limit=1000"
)
_FILE_LIST_SHA256 = "d23a9b0fc10fac770f1289d98612883ae1fb90e11b1539f5d5a5a699a186bb37"
_SOURCE_ID = "mendeley-hydrogen-permeation-ms-ahss-1300-v1"
_SHEETS = (("0.5 to 1 mA_cm2", 1261), ("5 to 10 mA_cm2", 600))
_PENDING = set()


def _issue(**values):
    token = object()
    _PENDING.add(token)
    try:
        return AHSS1300Permeation(**values, _issuer=token)
    except Exception:
        _PENDING.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class AHSS1300Permeation:
    """Raw observation sheets with time and current values and source row IDs."""

    source_id: str
    title: str
    doi: str
    version: str
    author: str
    origin: Origin
    license_id: str
    license_url: str
    source_file: str
    source_url: str
    source_sha256: str
    sheet_names: tuple[str, ...]
    current_header: str
    values: tuple[np.ndarray, ...]
    source_row_ids: tuple[tuple[str, ...], ...]
    temperature_header: str
    material_label: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise ValueError("Use the checksum-verified AHSS 1300 workbook reader")
        _PENDING.remove(self._issuer)
        if (self.source_id != _SOURCE_ID or self.title != _TITLE or self.doi != _DOI
                or self.version != "1" or self.author != _AUTHORS[0]
                or self.origin is not Origin.MEASURED or self.license_id != _LICENSE_ID
                or self.license_url != _LICENSE_URL or self.source_file != _FILE
                or self.source_url != _FILE_URL
                or self.source_sha256 != _FILE_SHA256 or self.sheet_names != tuple(x[0] for x in _SHEETS)
                or not isinstance(self.current_header, str) or "Current," not in self.current_header
                or self.current_header != "Current, \u03bcA"
                or self.temperature_header != "293 K" or self.material_label.strip() != "MS AHSS grade 1300"):
            raise ValueError("Workbook identity, attribution, license or schema differs from pinned v1 source")
        matrices, rows = tuple(self.values), tuple(tuple(x) for x in self.source_row_ids)
        if len(matrices) != 2 or len(rows) != 2:
            raise ValueError("Both source experiment sheets must be retained in publisher order")
        frozen = []
        for index, ((_, last_row), matrix, row_ids) in enumerate(zip(_SHEETS, matrices, rows, strict=True)):
            numeric = _real_numeric_array(matrix, f"AHSS 1300 sheet {index + 1}")
            first_row = 2
            expected_count = last_row - first_row + 1
            if numeric.shape != (expected_count, 2) or not np.all(np.isfinite(numeric)):
                raise ValueError("Workbook numeric rows differ from pinned sheet dimensions")
            expected = tuple(
                f"{_SOURCE_ID}:sheet-{index + 1}:row-{row}"
                for row in range(first_row, last_row + 1)
            )
            if row_ids != expected:
                raise ValueError("Workbook row identifiers must preserve worksheet source order")
            frozen.append(immutable_array(numeric, name="AHSS 1300 measured values"))
        object.__setattr__(self, "values", tuple(frozen))
        object.__setattr__(self, "source_row_ids", rows)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        digest = hashlib.sha256()
        digest.update(repr((self.source_id, self.title, self.doi, self.version, self.author,
                            self.origin, self.license_id, self.license_url, self.source_file,
                            self.source_url, self.source_sha256, self.sheet_names,
                            self.current_header, self.source_row_ids,
                            self.temperature_header, self.material_label)).encode())
        for value in self.values:
            digest.update(value.tobytes(order="C"))
        return digest.hexdigest()

    def require_current(self):
        if self._fingerprint() != self._seal:
            raise ValueError("AHSS 1300 observation content changed after loading")
        return self

    @property
    def current_unit(self):
        """Source current unit: microampere; this is not a current density."""
        self.require_current()
        return "uA"

    def current_ampere(self, sheet_name: str) -> np.ndarray:
        """Convert source microamperes to A, without assigning area or H flux."""
        values = self.observations(sheet_name)
        return immutable_array(values[:, 1] * 1e-6, name="AHSS 1300 current in A")

    @property
    def observation_counts(self) -> tuple[int, ...]:
        """Number of retained measurement rows in each source worksheet."""
        self.require_current()
        return tuple(values.shape[0] for values in self.values)

    def observations(self, sheet_name: str) -> np.ndarray:
        """Return one immutable [time_s, raw_current] source table by exact sheet name."""
        self.require_current()
        matches = tuple(i for i, name in enumerate(self.sheet_names) if name == sheet_name)
        if len(matches) != 1:
            raise ValueError("Select one exact source worksheet name")
        return self.values[matches[0]]


def _verify_receipt(dataset: Dataset):
    if type(dataset) is not Dataset:
        raise TypeError("Pass the resolved Mendeley Dataset receipt")
    if (dataset.key != _KEY or dataset.title != _TITLE or dataset.doi != _DOI
            or dataset.version != "1" or dataset.license_id != _LICENSE_ID
            or dataset.license_url != _LICENSE_URL or dataset.metadata_url != _METADATA_URL
            or dataset.metadata_sha256 != _METADATA_SHA256
            or hashlib.sha256(dataset.metadata_bytes).hexdigest() != _METADATA_SHA256):
        raise ValueError("Dataset metadata does not match the pinned AHSS 1300 v1 record")
    try:
        metadata = json.loads(dataset.metadata_bytes)
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Pinned publisher metadata bytes are not valid JSON") from error
    if not isinstance(metadata, dict):
        raise ValueError("Pinned publisher metadata root must be an object")
    license_data = metadata.get("licence", {})
    contributors = metadata.get("contributors", [])
    try:
        authors = tuple(
            " ".join(filter(None, (item.get("first_name"), item.get("last_name"))))
            for item in contributors
        )
    except (AttributeError, TypeError):
        authors = ()
    if not isinstance(license_data, dict) or not isinstance(contributors, list):
        raise ValueError("Publisher license/contributor fields have invalid types")
    listing_matches = tuple(payload for url, payload in dataset.supporting_metadata if url == _FILE_LIST_URL)
    if (len(listing_matches) != 1 or hashlib.sha256(listing_matches[0]).hexdigest() != _FILE_LIST_SHA256):
        raise ValueError("Pinned Mendeley attachment listing is absent or changed")
    try:
        listing = json.loads(listing_matches[0])
    except (UnicodeDecodeError, ValueError, TypeError) as error:
        raise ValueError("Pinned attachment listing bytes are not valid JSON") from error
    if (not isinstance(listing, list) or len(listing) != 1
            or not isinstance(listing[0], dict)
            or listing[0].get("filename") != _FILE
            or listing[0].get("size") != _FILE_SIZE
            or listing[0].get("content_details", {}).get("sha256_hash") != _FILE_SHA256
            or listing[0].get("content_details", {}).get("download_url") != _FILE_URL):
        raise ValueError("Pinned attachment listing does not match the admitted workbook")
    if (metadata.get("id") != "tnsgf7v76z"
            or metadata.get("version") != 1
            or metadata.get("doi") != _DOI or metadata.get("name") != _TITLE
            or authors != _AUTHORS or dataset.authors != _AUTHORS
            or dataset.origin != "measured" or not license_url_matches(_LICENSE_ID, license_data.get("url", ""), require_https=False)
            or license_data.get("short_name") != "CC BY 4.0"
            or dataset.families != ("materials", "hydrogen_transport", "permeation",
                                    "advanced_high_strength_steel")
            or dataset.source_updated_at != "" or len(dataset.files) != 1):
        raise ValueError("Publisher metadata disagrees with the admitted workbook receipt")
    remote = dataset.files[0]
    if (remote.name != _FILE or remote.url != _FILE_URL or remote.size_bytes != _FILE_SIZE or remote.checksum_algorithm != "sha256"
            or remote.checksum != _FILE_SHA256):
        raise ValueError("Publisher attachment listing differs from pinned workbook identity")
    file_rows = tuple(
        payload for url, payload in dataset.supporting_metadata
        if url == _FILE_LIST_URL
    )
    if len(file_rows) != 1 or len(dataset.supporting_metadata) != 1:
        raise ValueError("Mendeley fixture must retain exactly the pinned attachment-list response")


def _read_source_workbook(workbook):
    """Check the pinned source schema; production access first verifies raw bytes."""
    if tuple(workbook.sheetnames) != tuple(x[0] for x in _SHEETS):
        raise ValueError("Workbook sheets differ from the pinned source order")
    matrices, row_ids = [], []
    for sheet_index, (name, last_row) in enumerate(_SHEETS, start=1):
        sheet = workbook[name]
        if sheet.max_column != 6 or sheet.max_row != last_row:
            raise ValueError("Workbook dimensions differ from pinned source schema")
        expected_labels = {
            "A1": "Time, s", "B1": "Current, \u03bcA", "D1": "Temperature",
            "F1": "293 K", "D3": "Material", "E3": "MS AHSS grade 1300 ",
        }
        if any(sheet[cell].value != label for cell, label in expected_labels.items()):
            raise ValueError("Workbook source labels differ from pinned schema")
        observations = list(sheet.iter_rows(min_row=2, max_row=last_row,
                                            min_col=1, max_col=2, values_only=True))
        if any(type(value) not in (float, int) for row in observations for value in row):
            raise ValueError("Workbook observations must be numeric time/current pairs")
        matrix = np.asarray(observations, dtype=float)
        if not np.all(np.isfinite(matrix)) or np.any(np.diff(matrix[:, 0]) <= 0):
            raise ValueError("Workbook times must increase and observations must be finite")
        matrices.append(matrix)
        row_ids.append(tuple(f"{_SOURCE_ID}:sheet-{sheet_index}:row-{row}"
                             for row in range(2, last_row + 1)))
    return matrices, row_ids


def load_ahss1300_permeation(path: str | Path, *, dataset: Dataset) -> AHSS1300Permeation:
    """Load source rows from a locally staged, exact-hash publisher workbook."""
    _verify_receipt(dataset)
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size != _FILE_SIZE:
        raise ValueError("Workbook must be a regular file with the pinned publisher byte size")
    try:
        payload = source.read_bytes()
    except OSError as error:
        raise ValueError("Workbook could not be read as a local source file") from error
    if hashlib.sha256(payload).hexdigest() != _FILE_SHA256:
        raise ValueError("Workbook bytes differ from publisher SHA-256")
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError("The spreadsheet data extra is required to read this workbook") from error
    workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    try:
        matrices, row_ids = _read_source_workbook(workbook)
        first_sheet = workbook[_SHEETS[0][0]]
        return _issue(source_id=_SOURCE_ID, title=_TITLE, doi=_DOI, version="1", author=_AUTHORS[0],
                      origin=Origin.MEASURED, license_id=_LICENSE_ID, license_url=_LICENSE_URL,
                      source_file=_FILE, source_url=_FILE_URL, source_sha256=_FILE_SHA256,
                      sheet_names=tuple(x[0] for x in _SHEETS),
                      current_header=first_sheet["B1"].value, values=tuple(matrices),
                      source_row_ids=tuple(row_ids), temperature_header="293 K",
                      material_label="MS AHSS grade 1300")
    finally:
        workbook.close()


__all__ = ["AHSS1300Permeation", "load_ahss1300_permeation"]
