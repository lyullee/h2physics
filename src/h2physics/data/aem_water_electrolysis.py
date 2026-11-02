"""Source-bound access to the acquired AEM electrolysis workbook.

Cell values are exposed as returned by openpyxl with formulas left unevaluated.
The reader assigns no units, aliases, corrections, fitted parameters, or model
interpretations to the publisher's workbook cells.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

DOI = "10.5281/zenodo.20068087"
VERSION = "v1"
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SOURCE_URL = "https://zenodo.org/records/20068087"
METADATA_URL = "https://zenodo.org/api/records/20068087"
METADATA_SHA256 = "bd56cdc61eab1904d7436e8708e3dd332fd743a7161a6c3cd0b98a62e6c254ea"
WORKBOOK_NAME = "SI2_raw_data.xlsx"
WORKBOOK_SIZE_BYTES = 1_780_457
WORKBOOK_MD5 = "9d5a8655039f014431d3b9bc81e0d3f7"
WORKBOOK_SHA256 = "f9729dfc0b068962843ceb089bedbc6f6eb1ea8f52e214cd7eba6550d6c334ad"
ATTRIBUTION = (
    "Witte, J.; Trinke, P.; Bensmann, B.; Becker, M.; Olszok, V.; Weber, A. P.; "
    "Hanke-Rauschenbach, R.; Turek, T. (2026). Data for the Publication: Impact of "
    "Electrolyte Feed and Catalyst-Coated Substrate Properties on Cell Performance and "
    "Hydrogen Crossover in AEM Water Electrolysis, v1. Zenodo. "
    "https://doi.org/10.5281/zenodo.20068087"
)
_SHEET_DIMENSIONS = (
    ("Pol_curve_wet-dry", 46, 56),
    ("Pol_curve_individual_runs", 7_329, 45),
    ("Pol_curve_individual_runs_BoT", 139, 41),
    ("Crossover_wet-dry", 77, 37),
    ("Crossover_individual_runs", 72_069, 19),
    ("H2_and_H2O_transport", 10, 6),
)
_PENDING_ISSUERS: set[object] = set()


def _has_linklike_component(path: Path) -> bool:
    current = Path(path).absolute()
    while True:
        is_junction = getattr(current, "is_junction", None)
        if current.is_symlink() or (callable(is_junction) and is_junction()):
            return True
        if current.parent == current:
            return False
        current = current.parent


def _digests(path: Path) -> tuple[int, str, str, tuple[int, int, int, int, int]]:
    if _has_linklike_component(path) or not path.is_file():
        raise ValueError("Select a regular acquired AEM workbook or metadata file")
    before = path.stat()
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            size += len(block)
            sha256.update(block)
            md5.update(block)
    after = path.stat()
    first = (before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns)
    last = (after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns)
    if first != last or size != after.st_size:
        raise ValueError("AEM source changed while its receipt was being checked")
    return size, md5.hexdigest(), sha256.hexdigest(), last


def _column_name(column_number: int) -> str:
    label = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        label = chr(65 + remainder) + label
    return label


@dataclass(frozen=True, slots=True)
class AEMWorkbookCell:
    """One source cell with its one-based coordinates and raw reader value."""

    worksheet_name: str
    row_number: int
    column_number: int
    coordinate: str
    raw_value: object = field(repr=False)
    data_type: str
    number_format: str


@dataclass(frozen=True, slots=True)
class AEMWorksheetSnapshot:
    """A dense immutable worksheet rectangle preserving blank cell positions."""

    name: str
    state: str
    max_row: int
    max_column: int
    rows: tuple[tuple[object, ...], ...] = field(repr=False, compare=False)
    data_types: tuple[tuple[str, ...], ...] = field(repr=False, compare=False)
    number_formats: tuple[tuple[str, ...], ...] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))
        object.__setattr__(self, "data_types", tuple(tuple(row) for row in self.data_types))
        object.__setattr__(
            self, "number_formats", tuple(tuple(row) for row in self.number_formats)
        )
        if (not self.name or self.max_row < 0 or self.max_column < 0
                or len(self.rows) != self.max_row
                or len(self.data_types) != self.max_row
                or len(self.number_formats) != self.max_row):
            raise ValueError("AEM sheet rows and recorded dimensions must agree")
        if any(len(row) != self.max_column for row in self.rows):
            raise ValueError("AEM source values must retain every original column position")
        if (any(len(row) != self.max_column for row in self.data_types)
                or any(len(row) != self.max_column for row in self.number_formats)):
            raise ValueError("AEM cell types and formats must align with original source values")

    def cell(self, row_number: int, column_number: int) -> AEMWorkbookCell:
        """Return a one-based cell reference without changing its stored value."""
        if (isinstance(row_number, bool) or not isinstance(row_number, int)
                or isinstance(column_number, bool) or not isinstance(column_number, int)
                or not 1 <= row_number <= self.max_row
                or not 1 <= column_number <= self.max_column):
            raise IndexError("Select an in-range one-based source cell position")
        row_index, column_index = row_number - 1, column_number - 1
        coordinate = f"{_column_name(column_number)}{row_number}"
        return AEMWorkbookCell(
            self.name, row_number, column_number, coordinate,
            self.rows[row_index][column_index],
            self.data_types[row_index][column_index],
            self.number_formats[row_index][column_index],
        )

    def iter_cells(self, *, include_empty: bool = False) -> Iterator[AEMWorkbookCell]:
        """Iterate in workbook order; optionally include all blank source cells."""
        for row_number, row in enumerate(self.rows, start=1):
            for column_number, value in enumerate(row, start=1):
                if include_empty or value is not None:
                    yield self.cell(row_number, column_number)


def _issue_workbook(**values) -> AEMElectrolysisWorkbook:
    issuer = object()
    _PENDING_ISSUERS.add(issuer)
    try:
        return AEMElectrolysisWorkbook(**values, _issuer=issuer)
    except Exception:
        _PENDING_ISSUERS.discard(issuer)
        raise


@dataclass(frozen=True, slots=True)
class AEMElectrolysisWorkbook:
    """Immutable workbook snapshot bound to the acquired Zenodo source bytes."""

    source_path: Path = field(repr=False, compare=False)
    metadata_path: Path = field(repr=False, compare=False)
    doi: str
    version: str
    license_id: str
    license_url: str
    source_url: str
    attribution: str
    byte_size: int
    publisher_md5: str
    sha256: str
    metadata_sha256: str
    worksheets: Mapping[str, AEMWorksheetSnapshot] = field(repr=False, compare=False)
    _file_identity: tuple[int, int, int, int, int] = field(repr=False, compare=False)
    _metadata_identity: tuple[int, int, int, int, int] = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer not in _PENDING_ISSUERS:
            raise TypeError("Use load_aem_electrolysis_workbook() to issue source-bound cells")
        _PENDING_ISSUERS.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        supplied_source, supplied_metadata = Path(self.source_path), Path(self.metadata_path)
        if (_has_linklike_component(supplied_source) or _has_linklike_component(supplied_metadata)):
            raise ValueError("AEM source and metadata paths cannot contain symlinks or junctions")
        source_path, metadata_path = supplied_source.resolve(), supplied_metadata.resolve()
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(self, "metadata_path", metadata_path)
        sheets = dict(self.worksheets)
        if (source_path.name != WORKBOOK_NAME or self.doi != DOI or self.version != VERSION
                or self.license_id != LICENSE_ID or self.license_url != LICENSE_URL
                or self.source_url != SOURCE_URL or self.attribution != ATTRIBUTION
                or self.byte_size != WORKBOOK_SIZE_BYTES or self.publisher_md5 != WORKBOOK_MD5
                or self.sha256 != WORKBOOK_SHA256 or self.metadata_sha256 != METADATA_SHA256
                or tuple(sheets) != tuple(spec[0] for spec in _SHEET_DIMENSIONS)):
            raise ValueError("AEM workbook provenance or sheet inventory differs from its receipt")
        for name, expected_rows, expected_columns in _SHEET_DIMENSIONS:
            sheet = sheets[name]
            if (sheet.name != name or sheet.max_row != expected_rows
                    or sheet.max_column != expected_columns):
                raise ValueError("AEM workbook worksheet dimensions differ from its pinned schema")
        object.__setattr__(self, "worksheets", MappingProxyType(sheets))
        object.__setattr__(self, "_seal", self._payload())

    def _payload(self) -> tuple:
        return (
            self.source_path, self.metadata_path, self.doi, self.version, self.license_id,
            self.license_url, self.source_url, self.attribution, self.byte_size,
            self.publisher_md5, self.sha256, self.metadata_sha256,
            tuple((name, sheet.state, sheet.max_row, sheet.max_column,
                   sheet.rows, sheet.data_types, sheet.number_formats)
                  for name, sheet in self.worksheets.items()),
            self._file_identity, self._metadata_identity,
        )

    def require_current(self) -> AEMElectrolysisWorkbook:
        """Reject mutated parsed values or a changed source/metadata file."""
        if self._payload() != self._seal:
            raise ValueError("AEM workbook cells or provenance changed after source admission")
        file_state = _digests(self.source_path)
        if file_state != (WORKBOOK_SIZE_BYTES, WORKBOOK_MD5, WORKBOOK_SHA256,
                          self._file_identity):
            raise ValueError("AEM workbook no longer matches its publisher receipt")
        metadata_state = _digests(self.metadata_path)
        if metadata_state[0] <= 0 or metadata_state[2] != METADATA_SHA256:
            raise ValueError("Zenodo metadata snapshot no longer matches its source receipt")
        if metadata_state[3] != self._metadata_identity:
            raise ValueError("Zenodo metadata file identity changed after source admission")
        return self


def load_aem_electrolysis_workbook(directory: str | Path) -> AEMElectrolysisWorkbook:
    """Read the acquired workbook while preserving sheet, cell, and byte lineage.

    ``openpyxl`` is imported only when the optional workbook reader is called.
    The reader uses ``data_only=False`` so stored formulas remain formulas; it
    does not evaluate formulas or coerce cell values into physical quantities.
    ``directory`` is the single acquired version directory containing both the
    workbook and ``zenodo-record.json``.
    """
    supplied_root = Path(directory)
    if _has_linklike_component(supplied_root) or not supplied_root.is_dir():
        raise ValueError("Provide the regular local AEM dataset-version directory")
    root = supplied_root.resolve()
    source_path = root / WORKBOOK_NAME
    metadata_path = root / "zenodo-record.json"
    source_state = _digests(source_path)
    metadata_state = _digests(metadata_path)
    if source_state[:3] != (WORKBOOK_SIZE_BYTES, WORKBOOK_MD5, WORKBOOK_SHA256):
        raise ValueError("AEM workbook bytes differ from the pinned publisher receipt")
    if metadata_state[2] != METADATA_SHA256:
        raise ValueError("Zenodo record bytes differ from the pinned metadata snapshot")

    try:
        record = json.loads(metadata_path.read_bytes())
        metadata = record["metadata"]
        files = [entry for entry in record["files"] if entry.get("key") == WORKBOOK_NAME]
        if (record.get("doi") != DOI or metadata.get("publication_date") != "2026-07-26"
                or metadata.get("access_right") != "open"
                or metadata.get("license", {}).get("id") != "cc-by-4.0"
                or len(files) != 1 or files[0].get("size") != WORKBOOK_SIZE_BYTES
                or files[0].get("checksum") != f"md5:{WORKBOOK_MD5}"):
            raise ValueError("Zenodo dataset identity, license, or workbook receipt changed")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("Pinned Zenodo record is malformed or incomplete") from error

    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise ImportError(
            "AEM workbook reading requires the optional 'data' extra (openpyxl)"
        ) from error

    workbook = load_workbook(source_path, read_only=True, data_only=False, keep_links=False)
    worksheets: dict[str, AEMWorksheetSnapshot] = {}
    try:
        if tuple(workbook.sheetnames) != tuple(spec[0] for spec in _SHEET_DIMENSIONS):
            raise ValueError("AEM workbook sheet names differ from the pinned workbook")
        for name, expected_rows, expected_columns in _SHEET_DIMENSIONS:
            sheet = workbook[name]
            max_row, max_column = int(sheet.max_row or 0), int(sheet.max_column or 0)
            if (max_row, max_column) != (expected_rows, expected_columns):
                raise ValueError(f"AEM worksheet {name!r} dimensions differ from the source receipt")
            rows: list[tuple[object, ...]] = []
            data_types: list[tuple[str, ...]] = []
            number_formats: list[tuple[str, ...]] = []
            for cells in sheet.iter_rows(
                    min_row=1, max_row=max_row, min_col=1, max_col=max_column,
                    values_only=False):
                rows.append(tuple(getattr(cell, "value", None) for cell in cells))
                data_types.append(tuple(getattr(cell, "data_type", "n") for cell in cells))
                number_formats.append(tuple(
                    getattr(cell, "number_format", "General") for cell in cells
                ))
            worksheets[name] = AEMWorksheetSnapshot(
                name=name,
                state=sheet.sheet_state,
                max_row=max_row,
                max_column=max_column,
                rows=tuple(rows),
                data_types=tuple(data_types),
                number_formats=tuple(number_formats),
            )
    finally:
        workbook.close()

    if _digests(source_path) != source_state or _digests(metadata_path) != metadata_state:
        raise ValueError("AEM workbook or metadata changed during its cell snapshot")
    snapshot = _issue_workbook(
        source_path=source_path,
        metadata_path=metadata_path,
        doi=DOI,
        version=VERSION,
        license_id=LICENSE_ID,
        license_url=LICENSE_URL,
        source_url=SOURCE_URL,
        attribution=ATTRIBUTION,
        byte_size=source_state[0],
        publisher_md5=source_state[1],
        sha256=source_state[2],
        metadata_sha256=metadata_state[2],
        worksheets=worksheets,
        _file_identity=source_state[3],
        _metadata_identity=metadata_state[3],
    )
    return snapshot.require_current()


__all__ = [
    "AEMElectrolysisWorkbook",
    "AEMWorkbookCell",
    "AEMWorksheetSnapshot",
    "ATTRIBUTION",
    "DOI",
    "LICENSE_ID",
    "LICENSE_URL",
    "METADATA_SHA256",
    "SOURCE_URL",
    "VERSION",
    "WORKBOOK_MD5",
    "WORKBOOK_SHA256",
    "load_aem_electrolysis_workbook",
]
