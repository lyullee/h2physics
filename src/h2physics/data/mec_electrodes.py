"""Source-bound observations for the public CORA MEC electrode dataset.

Raw ODS files are kept outside the package. This reader exposes reported LSV,
impedance-pair and current-density measurements without fitting an electrode or
whole-cell model. Missing EIS frequency and the source's incomplete terminal
current-density row remain explicit.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import numpy as np

from ..core import Origin
from ..observations import ObservationTable
from .loaders import Column, load_observation_table

SOURCE_DOI = "10.34810/data2866"
SOURCE_VERSION = "1.0"
SOURCE_LICENSE = "CC0-1.0"
SOURCE_DIRECTORY = "mec_data2866_1.0"
SOURCE_SHEET = "Hoja1"
LSV_FILE = "LSV_Catalysts_CarbonCloth.ods"
EIS_FILE = "EIS_Catalysts_Electrodes.ods"
CURRENT_DENSITY_FILE = "Current density_Alloys.ods"
SOURCE_SHA256 = MappingProxyType(
    {
        LSV_FILE: "22116a643f43ef981835550c04a9fac14341420bd7a0da751c6e9d1539f98256",
        EIS_FILE: "2ae4220f58c02fb7f29a882281c3006990bf6cffd75f9395ee5f14f6f12ca1f3",
        CURRENT_DENSITY_FILE: "940b8ba42266774077cc488c19f1700e9fec921fa00b9d3ed7f8790830993996",
    }
)

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
_MAX_ODS_BYTES = 2_000_000
_MAX_CONTENT_XML_BYTES = 8_000_000
_MAX_ROWS = 10_000
_MAX_COLUMNS = 16
_PENDING_SERIES_ISSUERS: set[object] = set()
_PENDING_DATASET_ISSUERS: set[object] = set()


def _issue_series(**values):
    token = object()
    _PENDING_SERIES_ISSUERS.add(token)
    try:
        return MecElectrodeSeries(**values, _issuer_token=token)
    except Exception:
        _PENDING_SERIES_ISSUERS.discard(token)
        raise


def _issue_dataset(**values):
    token = object()
    _PENDING_DATASET_ISSUERS.add(token)
    try:
        return MecElectrodeDataset(**values, _issuer_token=token)
    except Exception:
        _PENDING_DATASET_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class MecDataIssue:
    """A source-format or incomplete-row condition retained by the loader."""

    source_file: str
    worksheet: str
    source_row: int
    source_column: int
    raw_token: str
    reason: str
    repeated_rows: int = 1


@dataclass(frozen=True, slots=True)
class MecElectrodeSeries:
    """One measured LSV or current-density trace as a shared observation table."""

    series_id: str
    electrode_label: str
    source_file: str
    source_sha256: str
    source_column: int
    observations: ObservationTable
    raw_coordinate_tokens: tuple[str, ...]
    raw_response_tokens: tuple[str, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    source_coordinate_column: int = field(default=1, init=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_SERIES_ISSUERS:
            raise ValueError("Use the checksum-validating CORA loader to issue source-bound electrode series")
        _PENDING_SERIES_ISSUERS.remove(self._issuer_token)
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.series_id, self.electrode_label, self.source_file)
        ):
            raise ValueError("Electrode observations require source and series identities")
        if (
            self.source_file not in {LSV_FILE, CURRENT_DENSITY_FILE}
            or self.source_sha256 != SOURCE_SHA256[self.source_file]
            or type(self.source_column) is not int
            or self.source_column not in range(2, 8)
        ):
            raise ValueError(
                "Electrode series must bind to a reviewed workbook hash and response column"
            )
        if type(self.observations) is not ObservationTable:
            raise TypeError("Electrode series must retain an ObservationTable")
        coordinate_tokens = tuple(self.raw_coordinate_tokens)
        response_tokens = tuple(self.raw_response_tokens)
        count = len(self.observations.row_ids)
        if len(coordinate_tokens) != count or len(response_tokens) != count:
            raise ValueError("Retain the original ODS numeric tokens for every admitted source row")
        if any(not isinstance(token, str) for token in (*coordinate_tokens, *response_tokens)):
            raise TypeError("Raw source-cell tokens must remain text")
        values = self.observations.values
        valid = self.observations.valid
        if values.shape != (count, 2) or valid.shape != values.shape:
            raise ValueError("Electrode observation values must align with the retained source-cell pairs")
        conversion = (1., 1.) if self.source_file == LSV_FILE else (86400., 10.)
        reconstructed = np.full((count, 2), np.nan)
        reconstructed_valid = np.zeros((count, 2), dtype=bool)
        for row_index, tokens in enumerate(zip(coordinate_tokens, response_tokens, strict=True)):
            for column_index, (token, factor) in enumerate(zip(tokens, conversion, strict=True)):
                if not token.strip():
                    continue
                try:
                    number = float(token.strip())
                except (ValueError, OverflowError):
                    continue
                if math.isfinite(number):
                    reconstructed[row_index, column_index] = number*factor
                    reconstructed_valid[row_index, column_index] = True
        if (not np.array_equal(values, reconstructed, equal_nan=True)
                or not np.array_equal(valid, reconstructed_valid)):
            raise ValueError("Electrode observation values/mask must reconstruct from exact raw workbook tokens")
        expected_source_id = (
            f"{SOURCE_DOI}:{SOURCE_VERSION}:{self.source_file}:"
            f"{self.source_sha256}:{self.series_id}"
        )
        context = dict(self.observations.context)
        expected_series_prefix = (
            "lsv" if self.source_file == LSV_FILE else "current-density"
        )
        if self.series_id != f"{expected_series_prefix}:{self.source_column}:{self.electrode_label}":
            raise ValueError("Series identity does not match its reviewed workbook column")
        if (
            self.observations.source_id != expected_source_id
            or context.get("source_doi") != SOURCE_DOI
            or context.get("source_file") != self.source_file
            or context.get("source_sha256") != self.source_sha256
            or context.get("series_id") != self.series_id
        ):
            raise ValueError("ObservationTable provenance does not match its typed series")
        if any(
            not isinstance(row_id, str)
            or not row_id.startswith(f"{SOURCE_SHEET}!")
            or not row_id[len(SOURCE_SHEET) + 1 :].isdigit()
            for row_id in self.observations.row_ids
        ):
            raise ValueError("Observation rows must retain one-based source sheet coordinates")
        source_row_numbers = tuple(
            int(row_id[len(SOURCE_SHEET) + 1 :]) for row_id in self.observations.row_ids
        )
        if any(row < 2 for row in source_row_numbers) or any(
            right <= left for left, right in zip(source_row_numbers, source_row_numbers[1:])
        ):
            raise ValueError("Observation row coordinates must be unique and source ordered")
        object.__setattr__(self, "raw_coordinate_tokens", coordinate_tokens)
        object.__setattr__(self, "raw_response_tokens", response_tokens)


@dataclass(frozen=True, slots=True)
class MecImpedanceTrace:
    """Reported Nyquist coordinate pairs without an invented frequency axis."""

    electrode_label: str
    source_file: str
    source_sha256: str
    source_columns: tuple[int, int]
    source_rows: tuple[int, ...]
    real_impedance_ohm: tuple[float, ...]
    reported_second_component_ohm: tuple[float, ...]
    source_second_header: str
    raw_real_tokens: tuple[str, ...]
    raw_second_component_tokens: tuple[str, ...]
    frequency_hz: None = field(default=None, init=False)

    def __post_init__(self):
        if (not isinstance(self.electrode_label, str) or not self.electrode_label.strip()
                or self.source_file != EIS_FILE):
            raise ValueError("Impedance data require an explicit source/condition identity")
        if (
            self.source_file != EIS_FILE
            or self.source_sha256 != SOURCE_SHA256[EIS_FILE]
        ):
            raise ValueError("Impedance trace must bind to the reviewed EIS workbook snapshot")
        if (
            len(self.source_columns) != 2
            or any(type(column) is not int for column in self.source_columns)
            or min(self.source_columns) < 1
        ):
            raise ValueError("Retain both one-based source columns")
        if (
            not self.source_rows
            or any(type(row) is not int or row < 2 for row in self.source_rows)
            or any(right <= left for left, right in zip(self.source_rows, self.source_rows[1:]))
            or len(self.source_rows) != len(self.real_impedance_ohm)
        ):
            raise ValueError("Impedance coordinates must retain one source row per pair")
        if len(self.source_rows) != len(self.reported_second_component_ohm):
            raise ValueError("Both impedance components must preserve matching rows")
        if len(self.raw_real_tokens) != len(self.source_rows):
            raise ValueError("Retain the source token for each real-impedance coordinate")
        if len(self.raw_second_component_tokens) != len(self.source_rows):
            raise ValueError("Retain the source token for each paired impedance coordinate")
        raw_real = tuple(self.raw_real_tokens)
        raw_second = tuple(self.raw_second_component_tokens)
        if any(not isinstance(token, str) for token in (*raw_real, *raw_second)):
            raise TypeError("Raw impedance source tokens must remain text")
        if (not isinstance(self.source_second_header, str)
                or not self.source_second_header.strip()):
            raise ValueError("Retain the original second-component header, including errors")
        if any(not math.isfinite(value) for value in self.real_impedance_ohm):
            raise ValueError("Real impedance observations must be finite")
        if any(not math.isfinite(value) for value in self.reported_second_component_ohm):
            raise ValueError("Second-component impedance observations must be finite")
        object.__setattr__(self, "source_columns", tuple(self.source_columns))
        object.__setattr__(self, "source_rows", tuple(self.source_rows))
        object.__setattr__(self, "real_impedance_ohm", tuple(self.real_impedance_ohm))
        object.__setattr__(
            self,
            "reported_second_component_ohm",
            tuple(self.reported_second_component_ohm),
        )
        object.__setattr__(self, "raw_real_tokens", raw_real)
        object.__setattr__(self, "raw_second_component_tokens", raw_second)


@dataclass(frozen=True, slots=True)
class MecElectrodeDataset:
    """Measured electrode traces tied to immutable published ODS snapshots."""

    source_doi: str
    archive_version: str
    dataset_license: str
    lsv_series: tuple[MecElectrodeSeries, ...]
    impedance_traces: tuple[MecImpedanceTrace, ...]
    current_density_series: tuple[MecElectrodeSeries, ...]
    issues: tuple[MecDataIssue, ...]
    source_sha256: Mapping[str, str]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    file_level_rights_exceptions_reviewed: bool = field(default=False, init=False)
    whole_cell_hydrogen_validation_qualified: bool = field(default=False, init=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_DATASET_ISSUERS:
            raise ValueError("Use the checksum-validating CORA loader to issue a source-bound dataset")
        _PENDING_DATASET_ISSUERS.remove(self._issuer_token)
        if (self.source_doi, self.archive_version, self.dataset_license) != (
            SOURCE_DOI,
            SOURCE_VERSION,
            SOURCE_LICENSE,
        ):
            raise ValueError("Only the reviewed CORA source identity is admitted")
        lsv = tuple(self.lsv_series)
        eis = tuple(self.impedance_traces)
        density = tuple(self.current_density_series)
        issues = tuple(self.issues)
        if len(lsv) != 6 or len(eis) != 8 or len(density) != 6:
            raise ValueError(
                "The reviewed source must expose six LSV, eight EIS and six density traces"
            )
        if any(type(value) is not MecElectrodeSeries for value in (*lsv, *density)):
            raise TypeError("Retain the typed measured electrode series")
        if any(type(value) is not MecImpedanceTrace for value in eis):
            raise TypeError("Retain the typed source impedance pairs")
        hashes = dict(self.source_sha256)
        if hashes != SOURCE_SHA256:
            raise ValueError(
                "Source file identities/hashes differ from the reviewed publisher snapshot"
            )
        if any(
            value.source_file != LSV_FILE
            or value.source_sha256 != hashes[LSV_FILE]
            or value.source_column not in range(2, 8)
            or value.observations.row_ids != tuple(
                f"{SOURCE_SHEET}!{row}" for row in range(2, 3003)
            )
            or tuple(variable.name for variable in value.observations.variables)
            != ("potential_v", "current_a")
            for value in lsv
        ) or {value.source_column for value in lsv} != set(range(2, 8)):
            raise ValueError("LSV series do not match the reviewed workbook provenance")
        if any(
            value.source_file != CURRENT_DENSITY_FILE
            or value.source_sha256 != hashes[CURRENT_DENSITY_FILE]
            or value.source_column not in range(2, 8)
            or value.observations.row_ids != tuple(
                f"{SOURCE_SHEET}!{row}" for row in range(2, 3676)
            )
            or tuple(variable.name for variable in value.observations.variables)
            != ("elapsed_time_day", "current_density_ma_cm2")
            for value in density
        ) or {value.source_column for value in density} != set(range(2, 8)):
            raise ValueError("Current-density series do not match the reviewed workbook provenance")
        if any(
            value.source_file != EIS_FILE
            or value.source_sha256 != hashes[EIS_FILE]
            or value.source_columns[0] not in range(1, 17, 2)
            or value.source_columns[1] != value.source_columns[0] + 1
            or value.source_rows != tuple(range(3, 41))
            for value in eis
        ) or {value.source_columns for value in eis} != {
            (column, column + 1) for column in range(1, 17, 2)
        }:
            raise ValueError("EIS traces do not match the reviewed workbook provenance")
        object.__setattr__(self, "lsv_series", lsv)
        object.__setattr__(self, "impedance_traces", eis)
        object.__setattr__(self, "current_density_series", density)
        object.__setattr__(self, "issues", issues)
        object.__setattr__(self, "source_sha256", MappingProxyType(hashes))

    @property
    def circuit_fit_supported(self) -> bool:
        """Frequency-dependent fitting is unavailable because no frequencies are reported."""
        return False


def _is_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _text(cell: ElementTree.Element) -> str:
    value = cell.get(f"{{{_NS['office']}}}value")
    if value is not None:
        return value
    paragraphs = cell.findall(".//text:p", _NS)
    return " ".join("".join(paragraph.itertext()) for paragraph in paragraphs).strip()


def _row_values(row: ElementTree.Element, maximum_columns: int) -> tuple[str, ...]:
    values: list[str] = []
    for cell in row:
        if cell.tag not in {
            f"{{{_NS['table']}}}table-cell",
            f"{{{_NS['table']}}}covered-table-cell",
        }:
            continue
        token = _text(cell)
        raw_repeat = cell.get(f"{{{_NS['table']}}}number-columns-repeated", "1")
        try:
            repeat = int(raw_repeat)
        except ValueError as exc:
            raise ValueError("ODS cell has an invalid repetition count") from exc
        if repeat < 1:
            raise ValueError("ODS cell repetition count must be positive")
        if repeat > maximum_columns and token:
            raise ValueError("Repeated nonempty ODS cells exceed the reviewed row width")
        values.extend([token] * min(repeat, maximum_columns - len(values)))
        if len(values) == maximum_columns:
            break
    values.extend([""] * (maximum_columns - len(values)))
    return tuple(values)


def _table_rows(
    raw: bytes, source_file: str
) -> tuple[tuple[tuple[int, tuple[str, ...]], ...], tuple[MecDataIssue, ...]]:
    if len(raw) > _MAX_ODS_BYTES:
        raise ValueError(f"{source_file} exceeds the declared ODS size limit")
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256[source_file]:
        raise ValueError(f"{source_file} SHA-256 differs from the reviewed CORA snapshot")
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            try:
                info = archive.getinfo("content.xml")
            except KeyError as exc:
                raise ValueError(f"{source_file} lacks ODS content.xml") from exc
            if info.file_size > _MAX_CONTENT_XML_BYTES:
                raise ValueError("ODS content.xml exceeds the declared ingestion limit")
            if archive.testzip() is not None:
                raise ValueError(f"{source_file} ZIP integrity check failed")
            root = ElementTree.fromstring(archive.read(info))
    except BadZipFile as exc:
        raise ValueError(f"{source_file} is not a valid ODS archive") from exc

    tables = [
        table
        for table in root.findall(".//table:table", _NS)
        if table.get(f"{{{_NS['table']}}}name") == SOURCE_SHEET
    ]
    if len(tables) != 1:
        raise ValueError(f"{source_file} must contain exactly one reviewed {SOURCE_SHEET} sheet")

    rows: list[tuple[int, tuple[str, ...]]] = []
    issues: list[MecDataIssue] = []
    logical_row = 1
    for element in tables[0].findall(".//table:table-row", _NS):
        values = _row_values(element, _MAX_COLUMNS)
        raw_repeat = element.get(f"{{{_NS['table']}}}number-rows-repeated", "1")
        try:
            repeat = int(raw_repeat)
        except ValueError as exc:
            raise ValueError("ODS row has an invalid repetition count") from exc
        if repeat < 1:
            raise ValueError("ODS row repetition count must be positive")
        nonempty = any(value.strip() for value in values)
        if not nonempty:
            issues.append(
                MecDataIssue(
                    source_file,
                    SOURCE_SHEET,
                    logical_row,
                    1,
                    "",
                    "empty_ods_rows_skipped",
                    repeat,
                )
            )
            logical_row += repeat
            continue
        if repeat > 1_000:
            raise ValueError("Repeated nonempty ODS rows exceed the reviewed observation limit")
        if logical_row + repeat > _MAX_ROWS:
            raise ValueError("ODS worksheet exceeds the declared row limit")
        rows.extend((logical_row + offset, values) for offset in range(repeat))
        logical_row += repeat
        if logical_row > _MAX_ROWS:
            raise ValueError("ODS worksheet exceeds the declared row limit")
    if not rows:
        raise ValueError(f"{source_file} contains no source rows")
    return tuple(rows), tuple(issues)


def _number(token: str, *, source_file: str, row: int, column: int, issues: list[MecDataIssue]):
    normalized = token.strip()
    if not normalized:
        return None
    try:
        value = float(normalized)
    except (ValueError, OverflowError):
        issues.append(
            MecDataIssue(
                source_file, SOURCE_SHEET, row, column, normalized, "nonnumeric_measurement"
            )
        )
        return None
    if not math.isfinite(value):
        issues.append(
            MecDataIssue(
                source_file, SOURCE_SHEET, row, column, normalized, "nonfinite_measurement"
            )
        )
        return None
    return value


def _observation_table(
    rows: tuple[tuple[int, tuple[str, ...]], ...],
    *,
    source_file: str,
    source_hash: str,
    series_id: str,
    coordinate_column: Column,
    response_column: Column,
    coordinate_index: int,
    response_index: int,
    issues: list[MecDataIssue],
) -> ObservationTable:
    stream = io.StringIO()
    writer = csv.writer(stream)
    headers = (coordinate_column.source, response_column.source)
    writer.writerow(headers)
    retained_rows: list[int] = []
    for source_row, values in rows:
        coordinate = _number(
            values[coordinate_index],
            source_file=source_file,
            row=source_row,
            column=coordinate_index + 1,
            issues=issues,
        )
        response = _number(
            values[response_index],
            source_file=source_file,
            row=source_row,
            column=response_index + 1,
            issues=issues,
        )
        if response is None:
            issues.append(
                MecDataIssue(
                    source_file,
                    SOURCE_SHEET,
                    source_row,
                    response_index + 1,
                    values[response_index],
                    "measurement_missing_with_source_row_retained",
                )
            )
        writer.writerow(
            (
                "" if coordinate is None else repr(coordinate),
                "" if response is None else repr(response),
            )
        )
        retained_rows.append(source_row)
    stream.seek(0)
    source_id = f"{SOURCE_DOI}:{SOURCE_VERSION}:{source_file}:{source_hash}:{series_id}"
    context = (
        ("source_doi", SOURCE_DOI),
        ("source_file", source_file),
        ("source_sha256", source_hash),
        ("worksheet", SOURCE_SHEET),
        ("series_id", series_id),
        ("coordinate_semantics", coordinate_column.basis_id),
        ("response_semantics", response_column.basis_id),
        ("experiment_grouping", "one reported trace; run/replicate grouping not established"),
        (
            "clock_alignment",
            "unresolved; the reported day coordinate has no epoch or synchronization",
        ),
        ("whole_cell_hydrogen_validation", "not supplied by this electrode dataset"),
    )
    table = load_observation_table(
        stream,
        columns=(coordinate_column, response_column),
        experiment_id=series_id,
        source_id=source_id,
        origins=(Origin.MEASURED, Origin.MEASURED),
        context=context,
    )
    return replace(
        table,
        row_ids=tuple(f"{SOURCE_SHEET}!{source_row}" for source_row in retained_rows),
    )


def _load_one(path: Path, source_file: str):
    if not path.is_file():
        raise FileNotFoundError(f"Required public CORA source file is missing: {source_file}")
    with path.open("rb") as source:
        raw = source.read(_MAX_ODS_BYTES + 1)
    if len(raw) > _MAX_ODS_BYTES:
        raise ValueError(f"{source_file} exceeds the declared ODS size limit")
    return raw, _table_rows(raw, source_file)


def load_cora_mec_electrode_dataset(raw_root: Path) -> MecElectrodeDataset:
    """Load measured electrode traces from the ignored CORA version-1.0 snapshot.

    ``raw_root`` is the directory containing ``mec_data2866_1.0/``. The reader
    verifies each workbook hash before parsing, retains worksheet rows and labels,
    converts day and current-density units through the shared observation loader,
    and keeps malformed/incomplete cells as issues or invalid masks. It does not
    infer geometric area, a synchronized process clock, catalyst performance,
    hydrogen production, Faradaic efficiency or a fitted impedance circuit.
    """
    root = Path(raw_root) / SOURCE_DIRECTORY
    issues: list[MecDataIssue] = []
    parsed: dict[str, tuple[tuple[int, tuple[str, ...]], ...]] = {}

    for source_file in (LSV_FILE, EIS_FILE, CURRENT_DENSITY_FILE):
        raw, (rows, row_issues) = _load_one(root / source_file, source_file)
        parsed[source_file] = rows
        issues.extend(row_issues)
        if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256[source_file]:
            raise ValueError(f"{source_file} changed after source parsing")

    lsv_rows = parsed[LSV_FILE]
    if len(lsv_rows) != 3002 or lsv_rows[0][0] != 1:
        raise ValueError("LSV source row count/header differs from the reviewed workbook schema")
    lsv_headers = lsv_rows[0][1]
    lsv_series = []
    for column_index in range(1, 7):
        label = lsv_headers[column_index].strip()
        if not label:
            raise ValueError(f"LSV response header in source column {column_index + 1} is blank")
        series_id = f"lsv:{column_index + 1}:{label}"
        table = _observation_table(
            lsv_rows[1:],
            source_file=LSV_FILE,
            source_hash=SOURCE_SHA256[LSV_FILE],
            series_id=series_id,
            coordinate_column=Column(
                "potential_v",
                "potential_v",
                "voltage",
                "V",
                basis_id="Reported potential vs Ag/AgCl; no reference-electrode conversion applied",
            ),
            response_column=Column(
                "current_a",
                "current_a",
                "current",
                "A",
                basis_id=(
                    "Reported potentiostat current; geometric area and electrode role unresolved"
                ),
            ),
            coordinate_index=0,
            response_index=column_index,
            issues=issues,
        )
        lsv_series.append(
            _issue_series(
                series_id,
                label,
                LSV_FILE,
                SOURCE_SHA256[LSV_FILE],
                column_index + 1,
                table,
                tuple(values[0] for _, values in lsv_rows[1:]),
                tuple(values[column_index] for _, values in lsv_rows[1:]),
            )
        )

    current_rows = parsed[CURRENT_DENSITY_FILE]
    if len(current_rows) != 3675 or current_rows[0][0] != 1:
        raise ValueError(
            "Current-density source row count/header differs from the reviewed workbook schema"
        )
    current_headers = current_rows[0][1]
    current_series = []
    for column_index in range(1, 7):
        label = current_headers[column_index].strip()
        if not label:
            raise ValueError(
                f"Current-density response header in source column {column_index + 1} is blank"
            )
        series_id = f"current-density:{column_index + 1}:{label}"
        table = _observation_table(
            current_rows[1:],
            source_file=CURRENT_DENSITY_FILE,
            source_hash=SOURCE_SHA256[CURRENT_DENSITY_FILE],
            series_id=series_id,
            coordinate_column=Column(
                "elapsed_time_day",
                "reported_time_s",
                "time",
                "d",
                basis_id=(
                    "Elapsed-day coordinate only; epoch, experiment boundaries and clock "
                    "alignment unresolved"
                ),
            ),
            response_column=Column(
                "current_density_ma_cm2",
                "current_density_a_m2",
                "current_density",
                "mA/cm2",
                basis_id=(
                    "Publisher-reported density; area, sign convention and biological activity "
                    "unresolved"
                ),
            ),
            coordinate_index=0,
            response_index=column_index,
            issues=issues,
        )
        current_series.append(
            _issue_series(
                series_id,
                label,
                CURRENT_DENSITY_FILE,
                SOURCE_SHA256[CURRENT_DENSITY_FILE],
                column_index + 1,
                table,
                tuple(values[0] for _, values in current_rows[1:]),
                tuple(values[column_index] for _, values in current_rows[1:]),
            )
        )

    impedance_rows = parsed[EIS_FILE]
    if len(impedance_rows) != 40 or impedance_rows[0][0] != 1 or impedance_rows[1][0] != 2:
        raise ValueError("EIS source row count/headers differ from the reviewed workbook schema")
    labels, headers = impedance_rows[0][1], impedance_rows[1][1]
    traces = []
    for pair_start in range(0, 16, 2):
        label = labels[pair_start].strip()
        first_header, second_header = headers[pair_start].strip(), headers[pair_start + 1].strip()
        if not label or first_header != "Re(Z)/Ohm":
            raise ValueError(
                f"EIS source pair at columns {pair_start + 1}-{pair_start + 2} changed"
            )
        if second_header != "#NAME?":
            raise ValueError(
                "EIS second-component header differs from the retained source error token"
            )
        issues.append(
            MecDataIssue(
                EIS_FILE,
                SOURCE_SHEET,
                2,
                pair_start + 2,
                second_header,
                "source_header_error_token; publisher README identifies this as the "
                "negative-imaginary Nyquist ordinate",
            )
        )
        real_values, second_values, real_tokens, second_tokens, source_rows = [], [], [], [], []
        for source_row, values in impedance_rows[2:]:
            real = _number(
                values[pair_start],
                source_file=EIS_FILE,
                row=source_row,
                column=pair_start + 1,
                issues=issues,
            )
            second = _number(
                values[pair_start + 1],
                source_file=EIS_FILE,
                row=source_row,
                column=pair_start + 2,
                issues=issues,
            )
            if real is None or second is None:
                continue
            real_values.append(real)
            second_values.append(second)
            real_tokens.append(values[pair_start])
            second_tokens.append(values[pair_start + 1])
            source_rows.append(source_row)
        traces.append(
            MecImpedanceTrace(
                label,
                EIS_FILE,
                SOURCE_SHA256[EIS_FILE],
                (pair_start + 1, pair_start + 2),
                tuple(source_rows),
                tuple(real_values),
                tuple(second_values),
                second_header,
                tuple(real_tokens),
                tuple(second_tokens),
            )
        )

    if any(len(trace.source_rows) != 38 for trace in traces):
        raise ValueError("EIS numeric pair count differs from the reviewed 38-row source schema")
    if any(len(series.observations.row_ids) != 3_001 for series in lsv_series):
        raise ValueError("LSV series must preserve all 3,001 reported potential/current rows")
    if any(len(series.observations.row_ids) != 3_674 for series in current_series):
        raise ValueError(
            "Current-density series must preserve 3,673 rows and its incomplete terminal row"
        )

    return _issue_dataset(
        source_doi=SOURCE_DOI,
        archive_version=SOURCE_VERSION,
        dataset_license=SOURCE_LICENSE,
        lsv_series=tuple(lsv_series),
        impedance_traces=tuple(traces),
        current_density_series=tuple(current_series),
        issues=tuple(issues),
        source_sha256=SOURCE_SHA256,
    )
