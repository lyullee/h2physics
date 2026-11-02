"""Source-bound reader for a dated Clean Hydrogen JU HRS registry workbook.

The reader preserves worksheet cells and does not infer a site's operating
state, geospatial reference system, capacity, pressure, or dispensing behavior.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATASET_KEY = "h2-stations-hrs-inventory"
DATASET_SOURCE = "https://map.h2-stations.eu/hrs-list"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
WORKSHEET_NAME = "Hrs"
HEADERS = (
    "name", "HRS operator", "HRS owner", "street address",
    "postal code", "city", "country",
)
_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H2StationRecord:
    """One unchanged row of the source station registry."""

    source_row_number: int
    name: Any
    operator: Any
    owner: Any
    street_address: Any
    postal_code: Any
    city: Any
    country: Any
    source_cells: tuple[Any, ...]

    def __post_init__(self) -> None:
        if type(self.source_row_number) is not int or self.source_row_number < 2:
            raise ValueError("A station source row number must include the worksheet header offset")
        cells = tuple(self.source_cells)
        if len(cells) != len(HEADERS):
            raise ValueError("A retained station row must match the reviewed seven-column schema")
        projected = (self.name, self.operator, self.owner, self.street_address,
                     self.postal_code, self.city, self.country)
        if projected != cells:
            raise ValueError("Named station cells must exactly retain the source row values")
        object.__setattr__(self, "source_cells", cells)


@dataclass(frozen=True, slots=True)
class H2StationWorkbook:
    """Read-only parsed view of a locally hash-pinned HRS registry snapshot."""

    path: Path
    source_bytes: bytes = field(repr=False, compare=False)
    sha256: str
    worksheet_name: str
    worksheet_row_count: int
    worksheet_column_count: int
    headers: tuple[str, ...]
    records: tuple[H2StationRecord, ...]
    _issued_by: object = field(default=None, repr=False, compare=False)
    _view_sha256: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issued_by is not _ISSUER:
            raise ValueError("HRS workbook views are issued only by load_h2_stations_workbook()")
        if self.worksheet_name != WORKSHEET_NAME or tuple(self.headers) != HEADERS:
            raise ValueError("HRS worksheet name or source column schema changed")
        if self.worksheet_column_count != len(HEADERS):
            raise ValueError("HRS worksheet column count differs from the retained schema")
        records = tuple(self.records)
        if self.worksheet_row_count != len(records) + 1:
            raise ValueError("Worksheet dimensions do not match the retained source rows")
        if any(type(row) is not H2StationRecord for row in records):
            raise TypeError("Retain source-bound H2StationRecord rows")
        if tuple(row.source_row_number for row in records) != tuple(
                range(2, self.worksheet_row_count + 1)):
            raise ValueError("Station records must retain contiguous source worksheet row numbers")
        if not isinstance(self.source_bytes, bytes):
            raise TypeError("Retain the exact source workbook bytes")
        if hashlib.sha256(self.source_bytes).hexdigest() != self.sha256:
            raise ValueError("HRS workbook bytes do not match the retained SHA-256")
        object.__setattr__(self, "path", Path(self.path))
        object.__setattr__(self, "headers", tuple(self.headers))
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_view_sha256", self._view_digest())

    @property
    def byte_count(self) -> int:
        return len(self.source_bytes)

    @property
    def dataset_key(self) -> str:
        return DATASET_KEY

    @property
    def license_id(self) -> str:
        return LICENSE_ID

    def _view_digest(self) -> str:
        payload = repr((self.worksheet_name, self.worksheet_row_count,
                        self.worksheet_column_count, self.headers, self.records)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def require_current(self) -> None:
        """Reject changed local source bytes or mutation of the parsed projection."""
        if (self._issued_by is not _ISSUER
                or hashlib.sha256(self.source_bytes).hexdigest() != self.sha256
                or self._view_digest() != self._view_sha256):
            raise ValueError("HRS workbook source or retained view changed after ingestion")
        current = self.path.read_bytes()
        if hashlib.sha256(current).hexdigest() != self.sha256:
            raise ValueError("HRS workbook path no longer contains the acquired source bytes")


def load_h2_stations_workbook(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
) -> H2StationWorkbook:
    """Load one exact export after caller-supplied size and SHA-256 checks.

    The optional workbook dependency is imported only when this reader is used.
    Header and worksheet checks are intentionally source-specific; later rolling
    exports require their own receipt and explicit schema review.
    """
    import openpyxl

    source_path = Path(path)
    raw = source_path.read_bytes()
    if type(expected_size_bytes) is not int or expected_size_bytes < 1:
        raise ValueError("expected_size_bytes must be a positive integer")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) != expected_size_bytes or actual_sha256 != expected_sha256:
        raise ValueError("HRS workbook size or SHA-256 differs from the acquisition receipt")

    workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        if workbook.sheetnames != [WORKSHEET_NAME]:
            raise ValueError("HRS workbook sheets differ from the reviewed one-sheet source schema")
        sheet = workbook[WORKSHEET_NAME]
        values = sheet.iter_rows(values_only=True)
        header = tuple(next(values, ()))
        if header != HEADERS:
            raise ValueError("HRS workbook header differs from the reviewed source schema")
        if sheet.max_column != len(HEADERS) or sheet.max_row < 2:
            raise ValueError("HRS worksheet has no station records or unexpected dimensions")
        records = []
        for row_number, row in enumerate(values, start=2):
            cells = tuple(row)
            if len(cells) != len(HEADERS):
                raise ValueError(f"HRS row {row_number} differs from the seven-column schema")
            records.append(H2StationRecord(
                row_number, *cells, source_cells=cells,
            ))
        if len(records) + 1 != sheet.max_row:
            raise ValueError("HRS iterator row count differs from worksheet dimensions")
        row_count, column_count = sheet.max_row, sheet.max_column
    finally:
        workbook.close()

    return H2StationWorkbook(
        source_path, raw, actual_sha256, WORKSHEET_NAME, row_count, column_count,
        HEADERS, tuple(records), _ISSUER,
    )


__all__ = ["H2StationRecord", "H2StationWorkbook", "load_h2_stations_workbook"]
