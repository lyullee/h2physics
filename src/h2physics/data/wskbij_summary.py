"""Source-bound parser for the WSKBIJ large-scale explosion summary table."""

from __future__ import annotations

import hashlib
import math
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree


DOI = "10.18710/WSKBIJ"
LICENSE_ID = "CC0-1.0"
README_NAME = "00_Readme.txt"
WORKBOOK_NAME = "Experimental_results_.xlsx"
README_SIZE_BYTES = 6_753
README_MD5 = "5642ccb734e8449bf52c0be83e4d0f23"
README_SHA256 = "cb7d4651d700cbd8da67cb69c3cec63ebabc4ffadbf6d5e1a2a38d63b622fb99"
WORKBOOK_SIZE_BYTES = 21_165
WORKBOOK_MD5 = "73ee4f29ca08612f46b7a37980cbe4df"
WORKBOOK_SHA256 = "5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34"

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_PENDING: set[object] = set()


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify_file(root: Path, name: str, size: int, md5: str, sha256: str) -> Path:
    path = root / name
    if path.stat().st_size != size:
        raise ValueError(f"WSKBIJ source file {name} differs from its pinned size")
    if _digest(path, "md5") != md5 or _digest(path, "sha256") != sha256:
        raise ValueError(f"WSKBIJ source file {name} differs from its publisher/local receipt")
    return path


def _cell_column(reference: str) -> str:
    match = re.match(r"([A-Z]+)", reference)
    if match is None:
        raise ValueError("WSKBIJ workbook contains a malformed cell reference")
    return match.group(1)


def _xlsx_cells(path: Path):
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("WSKBIJ summary is not a readable OOXML workbook") from exc
    with archive:
        required = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
        if not required.issubset(set(archive.namelist())):
            raise ValueError("WSKBIJ workbook lacks required OOXML workbook metadata")
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        sheet = workbook.find(f"{{{_MAIN_NS}}}sheets/{{{_MAIN_NS}}}sheet")
        if sheet is None:
            raise ValueError("WSKBIJ workbook has no worksheet")
        relationship_id = sheet.attrib.get(f"{{{_REL_NS}}}id")
        relation = next((item for item in relationships
                         if item.attrib.get("Id") == relationship_id), None)
        if relation is None:
            raise ValueError("WSKBIJ workbook worksheet relationship is missing")
        target = relation.attrib.get("Target", "")
        sheet_name = posixpath.normpath(posixpath.join("xl", target))
        if sheet_name not in archive.namelist():
            raise ValueError("WSKBIJ workbook worksheet target is absent")

        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared.findall(f"{{{_MAIN_NS}}}si"):
                strings.append("".join(node.text or "" for node in item.iter()
                                        if node.tag == f"{{{_MAIN_NS}}}t"))

        root = ElementTree.fromstring(archive.read(sheet_name))
        rows = []
        for row in root.findall(f".//{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row"):
            values = {}
            for cell in row.findall(f"{{{_MAIN_NS}}}c"):
                column = _cell_column(cell.attrib.get("r", ""))
                value = cell.find(f"{{{_MAIN_NS}}}v")
                if cell.attrib.get("t") == "inlineStr":
                    inline = cell.find(f"{{{_MAIN_NS}}}is")
                    values[column] = "" if inline is None else "".join(
                        node.text or "" for node in inline.iter()
                        if node.tag == f"{{{_MAIN_NS}}}t")
                elif value is None:
                    values[column] = ""
                elif cell.attrib.get("t") == "s":
                    index = int(value.text or "-1")
                    if not 0 <= index < len(strings):
                        raise ValueError("WSKBIJ workbook has an invalid shared-string index")
                    values[column] = strings[index]
                else:
                    values[column] = value.text or ""
            rows.append(values)
        return rows


def _numeric(value: str, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"WSKBIJ summary has an invalid {name} value") from exc
    if not math.isfinite(number):
        raise ValueError(f"WSKBIJ summary has a non-finite {name} value")
    return number


def _parse_rows(path: Path):
    rows = _xlsx_cells(path)
    expected = (
        "Nr", "Nozzle diameter [mm]", "Pressure reservoir [bar]", "ignition position",
        "Pressure sensor_1 [kPa]", "Pressure sensor_2 [kPa]",
        "Pressure sensor_3 [kPa]", "Pressure sensor_4 [kPa]",
    )
    header_index = None
    columns = None
    for index, row in enumerate(rows):
        ordered = tuple(row.get(chr(ord("A") + column), "") for column in range(8))
        if ordered == expected:
            header_index, columns = index, ordered
            break
    if header_index is None or columns != expected:
        raise ValueError("WSKBIJ workbook summary columns differ from the reviewed schema")

    parsed = []
    for index, row in enumerate(rows[header_index + 1:], start=header_index + 1):
        values = tuple(row.get(chr(ord("A") + column), "") for column in range(8))
        if not any(value.strip() for value in values):
            continue
        if not values[0].strip():
            continue
        test = _numeric(values[0], "test number")
        ignition = _numeric(values[3], "ignition position code")
        if not test.is_integer() or test <= 0 or not ignition.is_integer():
            raise ValueError("WSKBIJ test and ignition-position identifiers must be integer codes")
        parsed.append(WSKBIJExperimentSummaryRow(
            workbook_row=index + 1,
            test_number=int(test),
            nozzle_diameter_mm=_numeric(values[1], "nozzle diameter mm"),
            reservoir_pressure_bar_reported=_numeric(values[2], "reported reservoir pressure bar"),
            ignition_position_code=int(ignition),
            pressure_sensor_summary_kpa=tuple(
                _numeric(values[column], f"pressure sensor {column - 3} kPa")
                for column in range(4, 8)
            ),
        ))
    if not parsed or len({row.test_number for row in parsed}) != len(parsed):
        raise ValueError("WSKBIJ workbook needs unique, nonempty experiment summary rows")
    return tuple(parsed)


@dataclass(frozen=True, slots=True)
class WSKBIJExperimentSummaryRow:
    workbook_row: int
    test_number: int
    nozzle_diameter_mm: float
    reservoir_pressure_bar_reported: float
    ignition_position_code: int
    pressure_sensor_summary_kpa: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class WSKBIJExperimentSummary:
    raw_root: Path
    rows: tuple[WSKBIJExperimentSummaryRow, ...]
    readme_sha256: str
    workbook_sha256: str
    _issuer: object = field(repr=False, compare=False)
    _row_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use read_wskbij_experiment_summary for a source-bound table")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_row_binding", tuple(self.rows))

    def require_current(self):
        readme = _verify_file(self.raw_root, README_NAME, README_SIZE_BYTES,
                              README_MD5, README_SHA256)
        workbook = _verify_file(self.raw_root, WORKBOOK_NAME, WORKBOOK_SIZE_BYTES,
                                WORKBOOK_MD5, WORKBOOK_SHA256)
        if (self.readme_sha256 != README_SHA256
                or self.workbook_sha256 != WORKBOOK_SHA256
                or tuple(self.rows) != self._row_binding
                or _parse_rows(workbook) != self.rows):
            raise ValueError("WSKBIJ summary rows or source provenance changed after issue")
        if not readme.is_file():
            raise ValueError("WSKBIJ README is missing")
        return self


def read_wskbij_experiment_summary(raw_root: str | Path) -> WSKBIJExperimentSummary:
    """Read the pinned CC0 test-summary table without inferring missing physics."""
    root = Path(raw_root)
    readme = _verify_file(root, README_NAME, README_SIZE_BYTES, README_MD5, README_SHA256)
    workbook = _verify_file(root, WORKBOOK_NAME, WORKBOOK_SIZE_BYTES,
                            WORKBOOK_MD5, WORKBOOK_SHA256)
    text = readme.read_text(encoding="utf-8-sig")
    if "10.18710/WSKBIJ" not in text or "CC0 1.0" not in text:
        raise ValueError("WSKBIJ README no longer matches the reviewed record identity and terms")
    rows = _parse_rows(workbook)
    token = object()
    _PENDING.add(token)
    return WSKBIJExperimentSummary(root, rows, README_SHA256, WORKBOOK_SHA256, token)


__all__ = [
    "DOI", "LICENSE_ID", "WSKBIJExperimentSummaryRow", "WSKBIJExperimentSummary",
    "read_wskbij_experiment_summary",
]
