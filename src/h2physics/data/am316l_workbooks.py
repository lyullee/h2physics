"""Hash-bound, lossless cell snapshots for the licensed AM316L workbooks.

This reader preserves workbook cells and source headers as stored; it does not
assign physical units, select specimen subsets, or compute derived summaries.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


DOI = "10.5281/zenodo.19813205"
VERSION = "v1"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Michal Kresta, Kateřina Konečná, and Petra Váňová, "
    "Effect of Hydrogen Embrittlement on Mechanical Properties of "
    "Additively Manufactured 316L Stainless Steel, Zenodo v1, 2026"
)
METADATA_URL = "https://zenodo.org/records/19813205"

_WORKBOOKS = {
    "Tensile tests.xlsx": (
        "4d6a87be78951a85684502e959f3982d",
        "95b5d809bb564a2a01ae11ac24ff7c81f62dd8410083b15146186c26264702a1",
        "https://zenodo.org/api/records/19813205/files/Tensile%20tests.xlsx/content",
    ),
    "Hardness.xlsx": (
        "2397c3491f5ba462e7530af694e52002",
        "a38ef0c1809b7a7922ff82c98dcf4b252eeafa04a144a5c908c3877f2ab0ef57",
        "https://zenodo.org/api/records/19813205/files/Hardness.xlsx/content",
    ),
}


def _digests(path: Path) -> tuple[int, str, str, tuple[int, int, int, int, int]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Select a regular local AM316L workbook file")
    before = path.stat()
    sha256, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            size += len(block)
            sha256.update(block)
            md5.update(block)
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size,
                       before.st_mtime_ns, before.st_ctime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size,
                      after.st_mtime_ns, after.st_ctime_ns)
    if identity_before != identity_after or size != after.st_size:
        raise ValueError("AM316L workbook changed while its source hash was being read")
    return size, md5.hexdigest(), sha256.hexdigest(), identity_after


@dataclass(frozen=True, slots=True)
class AM316LWorksheetSnapshot:
    """One worksheet's complete stored cell rectangle and optional raw header row."""

    name: str
    state: str
    max_row: int
    max_column: int
    rows: tuple[tuple[object, ...], ...] = field(repr=False, compare=False)
    header_row_number: int | None = None
    header_values: tuple[object, ...] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Worksheet name must be preserved")
        if self.max_row < 0 or self.max_column < 0 or len(self.rows) != self.max_row:
            raise ValueError("Worksheet dimensions must agree with the retained row rectangle")
        if any(len(row) != self.max_column for row in self.rows):
            raise ValueError("Every retained worksheet row must preserve its full cell width")
        if self.header_row_number is None:
            if self.header_values is not None:
                raise ValueError("Header values require an explicitly selected header row")
        elif (isinstance(self.header_row_number, bool)
              or not isinstance(self.header_row_number, int)
              or not 1 <= self.header_row_number <= self.max_row
              or self.header_values != self.rows[self.header_row_number - 1]):
            raise ValueError("Explicit header row must match its original worksheet cells")


@dataclass(frozen=True, slots=True)
class AM316LWorkbookSnapshot:
    """Workbook cell values plus source-level identity and license attribution."""

    source_path: Path
    file_name: str
    byte_size: int
    publisher_md5: str
    sha256: str
    doi: str
    version: str
    license_id: str
    license_url: str
    source_url: str
    attribution: str
    worksheets: Mapping[str, AM316LWorksheetSnapshot] = field(repr=False, compare=False)
    _file_identity: tuple[int, int, int, int, int] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        path = Path(self.source_path).resolve()
        if path.name != self.file_name:
            raise ValueError("Workbook file name and resolved source path differ")
        for label in ("publisher_md5", "sha256", "doi", "version", "license_id",
                      "license_url", "source_url", "attribution"):
            if not isinstance(getattr(self, label), str) or not getattr(self, label).strip():
                raise ValueError(f"Workbook provenance must include {label}")
        sheets = dict(self.worksheets)
        if not sheets or any(key != value.name for key, value in sheets.items()):
            raise ValueError("Workbook worksheet map must preserve every worksheet name")
        object.__setattr__(self, "source_path", path)
        object.__setattr__(self, "worksheets", MappingProxyType(sheets))

    def require_current(self) -> None:
        """Recheck source path, byte count and publisher/local digests before reuse."""
        path = self.source_path
        size, md5, sha256, identity = _digests(path)
        if (identity != self._file_identity or size != self.byte_size
                or md5 != self.publisher_md5 or sha256 != self.sha256):
            raise ValueError("AM316L workbook snapshot is stale or source bytes changed")


def read_am316l_workbook(directory: str | Path, file_name: str, *,
                         header_rows: Mapping[str, int] | None = None) -> AM316LWorkbookSnapshot:
    """Read one allow-listed Zenodo workbook without interpreting its cells.

    `header_rows` maps exact worksheet names to one-based row numbers. If no
    mapping is supplied, no row is labeled as a header; every cell row remains
    available in its original position. Formulas are retained as formula text
    and never evaluated. The `data` extra is required for the optional
    ``openpyxl`` dependency.
    """
    if file_name not in _WORKBOOKS:
        raise ValueError("Select one of the two allow-listed AM316L dataset workbooks")
    from openpyxl import load_workbook

    path = Path(directory) / file_name
    expected_md5, expected_sha256, source_url = _WORKBOOKS[file_name]
    size, md5, sha256, file_identity = _digests(path)
    if md5 != expected_md5 or sha256 != expected_sha256:
        raise ValueError("AM316L workbook does not match its publisher MD5 and pinned SHA-256")

    selected_headers = {} if header_rows is None else dict(header_rows)
    if any(not isinstance(name, str) or isinstance(row, bool) or not isinstance(row, int) or row < 1
           for name, row in selected_headers.items()):
        raise ValueError("Explicit worksheet header rows must use nonempty names and positive one-based integers")

    workbook = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    worksheets = {}
    try:
        names = tuple(workbook.sheetnames)
        if not names or set(selected_headers) - set(names):
            raise ValueError("Header-row mapping names an absent worksheet")
        for name in names:
            sheet = workbook[name]
            max_row = int(sheet.max_row or 0)
            max_column = int(sheet.max_column or 0)
            rows = tuple(tuple(row) for row in sheet.iter_rows(
                min_row=1, max_row=max_row, min_col=1, max_col=max_column, values_only=True
            )) if max_row and max_column else ()
            header_number = selected_headers.get(name)
            if header_number is not None and header_number > max_row:
                raise ValueError(f"Selected header row exceeds worksheet {name!r} dimensions")
            header_values = None if header_number is None else rows[header_number - 1]
            worksheets[name] = AM316LWorksheetSnapshot(
                name=name, state=sheet.sheet_state, max_row=max_row,
                max_column=max_column, rows=rows,
                header_row_number=header_number, header_values=header_values,
            )
    finally:
        workbook.close()

    final_size, final_md5, final_sha256, final_identity = _digests(path)
    if (final_size, final_md5, final_sha256, final_identity) != (
            size, md5, sha256, file_identity):
        raise ValueError("AM316L workbook changed during worksheet snapshot creation")
    return AM316LWorkbookSnapshot(
        source_path=path,
        file_name=file_name,
        byte_size=size,
        publisher_md5=md5,
        sha256=sha256,
        doi=DOI,
        version=VERSION,
        license_id=LICENSE_ID,
        license_url=LICENSE_URL,
        source_url=source_url,
        attribution=ATTRIBUTION,
        worksheets=worksheets,
        _file_identity=file_identity,
    )


__all__ = ["AM316LWorksheetSnapshot", "AM316LWorkbookSnapshot", "read_am316l_workbook"]
