"""Source-bound container reader for the public HySaM Group B workbooks.

This module preserves workbook content and source identity. It does not assign
units or sensor meaning to the publisher's channel tags.
"""

from __future__ import annotations

import hashlib
import io
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATASET_KEY = "hysam-sampling-system"
DATASET_DOI = "10.5281/zenodo.20590842"
DATASET_VERSION = "v1.0"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
METADATA_SHA256 = "312afd497b04fb45bcad907802fae42039f1722961f361dce6a825c87b5e05e6"
ATTRIBUTION = (
    "The Hydrogen and Fuel Cell Center (2026), Group B -- HySam system measurement data, "
    "v1.0, Zenodo, https://doi.org/10.5281/zenodo.20590842, CC BY 4.0."
)

_ISSUER = object()
_PINS = {
    "20241023_Test_1_HySaM.xlsx": (
        663869,
        "8eb7c14218ae25d4ffe410cbf440484f",
        "fbdd81a7ec9c1191d69322f06087e8b30a33acc8b340b861a636173c08d9913a",
        6601,
        23,
    ),
    "20241023_Test_4_HySaM_CESAME.xlsx": (
        75292,
        "ce0f85c5b12f55300bf8a5792e9221c8",
        "bc9e5cbd23350b7320a96d627854cc5154f1b92ff987e087c957b1da691ea4aa",
        721,
        14,
    ),
    "20241024_Test_9_HySaM.xlsx": (
        283636,
        "9cb74d5b885ebfcf90589bfe41bbc806",
        "f33d3e451b42b1d3aff905cc5deb1e9a2ed11eeaf7d4f0d559446a609bdc7563",
        2161,
        21,
    ),
}


@dataclass(frozen=True, slots=True)
class HySamWorkbook:
    """Immutable parsed view of one checksum-pinned source workbook."""

    path: Path
    source_bytes: bytes = field(repr=False, compare=False)
    publisher_md5: str
    sha256: str
    worksheet_name: str
    row_count: int
    column_count: int
    headers: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    metadata_sha256: str = METADATA_SHA256
    dataset_key: str = DATASET_KEY
    doi: str = DATASET_DOI
    version: str = DATASET_VERSION
    license_id: str = LICENSE_ID
    _issued_by: object = field(default=None, init=False, repr=False, compare=False)
    _issued_view_sha256: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issued_by is not _ISSUER:
            raise ValueError("HySam workbooks are issued only by load_hysam_workbook()")
        if (self.dataset_key != DATASET_KEY or self.doi != DATASET_DOI
                or self.version != DATASET_VERSION or self.license_id != LICENSE_ID
                or self.metadata_sha256 != METADATA_SHA256):
            raise ValueError("HySam dataset identity or rights changed")
        if not isinstance(self.source_bytes, bytes):
            raise TypeError("Retain the exact acquired workbook bytes")
        if self.row_count != len(self.rows) + 1 or self.column_count != len(self.headers):
            raise ValueError("Parsed HySam dimensions do not agree with the retained workbook view")
        if any(len(row) != self.column_count for row in self.rows):
            raise ValueError("A retained HySam row differs from the pinned worksheet width")
        object.__setattr__(self, "path", Path(self.path))
        object.__setattr__(self, "headers", tuple(self.headers))
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))
        object.__setattr__(self, "_issued_view_sha256", self._view_sha256())

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def source_row_numbers(self) -> tuple[int, ...]:
        """Original Excel row numbers for observations after the header."""
        return tuple(range(2, self.row_count + 1))

    def _view_sha256(self) -> str:
        payload = repr((self.worksheet_name, self.row_count, self.column_count,
                        self.headers, self.rows)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def require_current(self) -> None:
        """Reject a forged/stale receipt or bytes changed at its source path."""
        pin = _PINS.get(self.filename)
        if (self._issued_by is not _ISSUER or pin is None
                or self.dataset_key != DATASET_KEY or self.doi != DATASET_DOI
                or self.version != DATASET_VERSION or self.license_id != LICENSE_ID
                or self.metadata_sha256 != METADATA_SHA256
                or len(self.source_bytes) != pin[0]
                or hashlib.md5(self.source_bytes, usedforsecurity=False).hexdigest() != pin[1]
                or hashlib.sha256(self.source_bytes).hexdigest() != pin[2]
                or self._view_sha256() != self._issued_view_sha256):
            raise ValueError("Retained HySam source receipt no longer matches its pinned identity")
        try:
            mode = self.path.lstat().st_mode
        except OSError as error:
            raise ValueError("HySam source file is no longer present") from error
        if not stat.S_ISREG(mode):
            raise ValueError("HySam source path must remain a regular file")
        current = self.path.read_bytes()
        if (len(current) != pin[0]
                or hashlib.md5(current, usedforsecurity=False).hexdigest() != pin[1]
                or hashlib.sha256(current).hexdigest() != pin[2]):
            raise ValueError("HySam source bytes changed after workbook admission")


def load_hysam_workbook(path: str | Path) -> HySamWorkbook:
    """Load one exact public workbook without unit or channel interpretation."""
    path = Path(path)
    pin = _PINS.get(path.name)
    if pin is None:
        raise ValueError("Only the three reviewed HySaM v1.0 workbook files are supported")
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        raise ValueError("HySam workbook path does not exist") from error
    if not stat.S_ISREG(mode):
        raise ValueError("HySam workbook path must be a regular file")
    source_bytes = path.read_bytes()
    size, md5, sha256, expected_rows, expected_columns = pin
    if (len(source_bytes) != size
            or hashlib.md5(source_bytes, usedforsecurity=False).hexdigest() != md5
            or hashlib.sha256(source_bytes).hexdigest() != sha256):
        raise ValueError("HySam workbook size or publisher/local checksum does not match v1.0 pins")

    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(source_bytes), read_only=True, data_only=False)
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("HySam v1.0 workbooks must retain their single worksheet")
        sheet = workbook.worksheets[0]
        if (sheet.max_row != expected_rows or sheet.max_column != expected_columns):
            raise ValueError("HySam worksheet dimensions differ from the audited v1.0 schema")
        iterator = sheet.iter_rows(values_only=True)
        raw_header = next(iterator, None)
        if raw_header is None or not raw_header or raw_header[0] != "Zeit":
            raise ValueError("HySam sheet header no longer starts with the publisher time column")
        headers = tuple("" if item is None else str(item) for item in raw_header)
        rows = tuple(tuple(row) for row in iterator)
    finally:
        workbook.close()

    result = object.__new__(HySamWorkbook)
    for name, value in {
        "path": path,
        "source_bytes": source_bytes,
        "publisher_md5": md5,
        "sha256": sha256,
        "worksheet_name": sheet.title,
        "row_count": expected_rows,
        "column_count": expected_columns,
        "headers": headers,
        "rows": rows,
        "metadata_sha256": METADATA_SHA256,
        "dataset_key": DATASET_KEY,
        "doi": DATASET_DOI,
        "version": DATASET_VERSION,
        "license_id": LICENSE_ID,
        "_issued_by": _ISSUER,
        "_issued_view_sha256": "",
    }.items():
        object.__setattr__(result, name, value)
    result.__post_init__()
    result.require_current()
    return result


__all__ = [
    "ATTRIBUTION",
    "DATASET_DOI",
    "DATASET_KEY",
    "DATASET_VERSION",
    "HySamWorkbook",
    "LICENSE_ID",
    "LICENSE_URL",
    "METADATA_SHA256",
    "load_hysam_workbook",
]
