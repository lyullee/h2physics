"""Bounded, source-specific MHC v1.2 logger observations; no clock alignment.

Lukas Fleming, https://doi.org/10.5281/zenodo.19036733, CC BY 4.0.
Only cached workbook values are decoded. Included code, links and macros never run.
"""

import hashlib
import math
import posixpath
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np

from ..core import Origin
from ..observations import ObservationTable, Variable
from .pressure_peaking import file_sha256

PROFILE_ID = "mhc-v1.2-logger-profile-1"
ARCHIVE_SHA256 = "91755fb1e555e0eb32d160ac140a4261b6bb47d24944c7e717b723fe2a641e32"
ARCHIVE_BYTES = 377874239
SOURCE_ID = "doi:10.5281/zenodo.19036733/v1.2"
REFERENCE_FLOW_BASIS = "source ln/min; normal reference pressure/temperature unresolved"
GAUGE_BASIS = "source barg; gauge reference pressure unresolved"
PRESSURE_BASIS = "source bar; absolute/gauge basis unresolved"
LABVIEW_ALIASES = ("Date", "Time", "Seconds", "P-4", "P-5", "MF-1", "T_HTF-1",
                   "MF-2", "T_HTF-2", "P-1", "P-2", "P-3", "MFC-1", "MFC-2", "MFC-3")
LABVIEW_UNITS = ("bar", "barg", "l/min", "°C", "l/min", "°C", "barg", "barg",
                 "barg", "ln/min", "ln/min", "ln/min")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_PENDING_LOGGER_BLOCK_ISSUERS: set[object] = set()
_PENDING_VERIFIED_ARCHIVE_ISSUERS: set[object] = set()


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    compressed_bytes: int = 450_000_000
    expanded_bytes: int = 500_000_000
    member_bytes: int = 25_000_000
    workbook_expanded_bytes: int = 250_000_000
    workbook_member_bytes: int = 60_000_000
    members: int = 500
    compression_ratio: int = 2000
    worksheet_rows: int = 100_000
    worksheet_columns: int = 200

    def __post_init__(self):
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
               for value in (getattr(self, field) for field in self.__dataclass_fields__)):
            raise ValueError("Archive budgets must be positive integers")


@dataclass(frozen=True, slots=True)
class SourceCell:
    sheet: str
    coordinate: str
    value: object


@dataclass(frozen=True, slots=True)
class Channel:
    column: int
    hardware_label: str
    sensor_label: str
    source_unit: str
    unit_evidence: SourceCell
    variable: Variable
    scale: float = 1.
    offset: float = 0.


@dataclass(frozen=True, slots=True)
class LoggerSchema:
    identity: str
    role: str
    clock_columns: tuple[int, ...]
    channels: tuple[Channel, ...]
    headers: tuple[SourceCell, ...]
    first_data_row: int
    clock_kind: str = "source-local-calendar"
    clock_encoding: str = "source Date/Time headers; typed/ISO/day.month.year/workbook Excel serial"


@dataclass(frozen=True, slots=True)
class LoggerBlock:
    observations: ObservationTable
    schema: LoggerSchema
    source_rows: tuple[int, ...]
    raw_cells: tuple[tuple[object, ...], ...]
    invalid_reasons: tuple[tuple[str, ...], ...]
    formula_cells: tuple[SourceCell, ...]
    archive_receipt_verified: bool = False
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_LOGGER_BLOCK_ISSUERS:
            raise TypeError("MHC logger blocks are issued only by the verified workbook reader")
        _PENDING_LOGGER_BLOCK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        table = self.observations
        context = dict(table.context)
        rows = tuple(self.source_rows)
        raw_cells = tuple(tuple(row) for row in self.raw_cells)
        reasons = tuple(tuple(row) for row in self.invalid_reasons)
        formulas = tuple(self.formula_cells)
        if (not isinstance(table, ObservationTable) or not isinstance(self.schema, LoggerSchema)
                or not rows or len(set(rows)) != len(rows)
                or rows != tuple(sorted(rows))
                or len(raw_cells) != len(rows) or len(reasons) != len(rows)
                or len(table.values) != len(rows) or len(table.row_ids) != len(rows)
                or context.get("profile") != PROFILE_ID
                or context.get("archive_sha256") != ARCHIVE_SHA256
                or len(context.get("member_sha256", "")) != 64
                or any(ch not in "0123456789abcdef" for ch in context.get("member_sha256", ""))
                or table.source_id != SOURCE_ID
                or type(self.archive_receipt_verified) is not bool
                or context.get("logger_export") != self.schema.identity
                or context.get("export_role") != self.schema.role):
            raise ValueError("MHC logger block lost source-row or archive/member provenance")
        if any(not isinstance(cell, SourceCell) for cell in formulas):
            raise TypeError("Formula provenance must use typed source cells")
        object.__setattr__(self, "source_rows", rows)
        object.__setattr__(self, "raw_cells", raw_cells)
        object.__setattr__(self, "invalid_reasons", reasons)
        object.__setattr__(self, "formula_cells", formulas)


@dataclass(frozen=True, slots=True)
class SheetAudit:
    sheet: str
    dimension: str
    stored_rows: int
    populated_rows: int
    numeric_rows: int
    numeric_cells: int
    formula_cells: int
    missing_formula_caches: int
    error_cells: int
    nonfinite_numeric_cells: int


def _safe_inventory(archive, *, total_limit, member_limit, limits):
    infos = archive.infolist()
    if len(infos) > limits.members or len({i.filename for i in infos}) != len(infos):
        raise ValueError("Archive member count or duplicate path violates the budget")
    total = 0
    for info in infos:
        # ZipInfo normalizes the platform separator on Windows. Validate the
        # original directory name as well, before any such normalization.
        name = info.orig_filename
        parts = PurePosixPath(name).parts
        if (not parts or name.startswith(("/", "\\")) or "\\" in name
                or ":" in name or ".." in parts or "\x00" in name
                or stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1):
            raise ValueError("Unsafe, encrypted or symbolic archive member")
        if (info.file_size > member_limit or info.file_size < 0
                or info.file_size / max(1, info.compress_size) > limits.compression_ratio):
            raise ValueError("Archive member exceeds expansion/ratio budget")
        total += info.file_size
    if total > total_limit:
        raise ValueError("Archive exceeds expanded byte budget")
    return tuple(infos)


def _number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else math.nan


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _excel_clock(value, epoch):
    from openpyxl.utils.datetime import from_excel

    if (epoch is not None and isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 <= value <= 2958465):
        try:
            return from_excel(value, epoch=epoch)
        except (OverflowError, ValueError):
            return None
    return None


def _local_datetime(cells, columns, *, excel_epoch=None):
    if len(columns) == 1:
        value = cells[columns[0] - 1]
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?", value):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        elif isinstance(value, str) and re.fullmatch(r"\d\d\.\d\d\.\d{4}\s+\d\d:\d\d:\d\d", value):
            try:
                value = datetime.strptime(value, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                return None
        elif isinstance(value, (int, float)):
            value = _excel_clock(value, excel_epoch)
        return value if isinstance(value, datetime) and value.tzinfo is None else None
    day, clock = (cells[i - 1] for i in columns)
    if isinstance(day, datetime):
        day = day.date() if day.tzinfo is None else None
    elif isinstance(day, (int, float)) and not isinstance(day, bool) and math.isfinite(day):
        text = str(int(day)) if day == int(day) else ""
        try:
            if len(text) == 8:
                day = datetime.strptime(text, "%Y%m%d").date()
            else:
                decoded = _excel_clock(day, excel_epoch)
                day = decoded.date() if isinstance(decoded, datetime) else None
        except ValueError:
            day = None
    if isinstance(clock, (int, float)) and not isinstance(clock, bool) and 0 <= clock < 1:
        clock = _excel_clock(clock, excel_epoch)
    if isinstance(day, date) and isinstance(clock, time) and clock.tzinfo is None:
        return datetime.combine(day, clock)
    return None


class HydrideCompressorArchive:
    """Verified immutable member snapshots; context exit rechecks the outer bytes.

    No extraction is needed. At most one experiment payload is required at a time.
    The expected digest defaults to the reviewed receipt; fixtures declare theirs.
    """

    def __init__(self, path: str | Path, *, expected_sha256: str = ARCHIVE_SHA256,
                 expected_bytes: int | None = ARCHIVE_BYTES, limits: ArchiveLimits = ArchiveLimits()):
        self.path, self.limits = Path(path), limits
        self.expected_sha256, self.expected_bytes = expected_sha256, expected_bytes
        self._zip = None

    def __enter__(self):
        size = self.path.stat().st_size
        if size > self.limits.compressed_bytes or (self.expected_bytes is not None and size != self.expected_bytes):
            raise ValueError("Archive compressed size differs from receipt/budget")
        self.sha256 = file_sha256(self.path)
        if self.sha256 != self.expected_sha256:
            raise ValueError("Archive SHA-256 differs from the declared receipt")
        self._zip = ZipFile(self.path)
        try:
            self.inventory = _safe_inventory(self._zip, total_limit=self.limits.expanded_bytes,
                member_limit=self.limits.member_bytes, limits=self.limits)
            self.experiments = {}
            for item in self.inventory:
                match = re.fullmatch(r"[^/]+/Dataset/Experiment ([1-9][0-9]*)\.xlsx", item.filename)
                if match:
                    number = int(match[1])
                    if number in self.experiments:
                        raise ValueError("Duplicate experiment identity")
                    self.experiments[number] = item.filename
            return self
        except Exception:
            self._zip.close()
            self._zip = None
            raise

    def __exit__(self, *args):
        self._zip.close()
        self._zip = None
        if file_sha256(self.path) != self.sha256:
            raise ValueError("Archive bytes changed during observation decoding")

    def read_member(self, name):
        if self._zip is None:
            raise ValueError("Use the archive within its context manager")
        # ZipFile.read verifies CRC. No archive pathname is ever written to disk.
        payload = self._zip.read(name)
        return payload, hashlib.sha256(payload).hexdigest()

    def overview(self):
        """Literal cached overview fields with cell identity, without inferred units."""
        from openpyxl import load_workbook

        names = [i.filename for i in self.inventory if i.filename.endswith("/Experiment Overview.xlsx")]
        if len(names) != 1:
            raise ValueError("A unique source experiment overview is required")
        payload, digest = self.read_member(names[0])
        with ZipFile(BytesIO(payload)) as archive:
            _safe_inventory(archive, total_limit=self.limits.workbook_expanded_bytes,
                member_limit=self.limits.workbook_member_bytes, limits=self.limits)
        workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True, keep_links=False)
        try:
            sheet = workbook.worksheets[0]
            fields = tuple(SourceCell(sheet.title, cell.coordinate, cell.value)
                for row in sheet.iter_rows(max_row=100, max_col=8) for cell in row if cell.value is not None)
            cases = {}
            for row in sheet.iter_rows(min_row=3, max_row=100, max_col=8):
                number = row[0].value
                if isinstance(number, int) and not isinstance(number, bool):
                    if number in cases:
                        raise ValueError("Duplicate source overview case")
                    cases[number] = tuple(SourceCell(sheet.title, cell.coordinate, cell.value) for cell in row)
            return names[0], digest, fields, cases
        finally:
            workbook.close()

    def experiment(self, number: int):
        if isinstance(number, bool) or number not in self.experiments:
            raise ValueError("Experiment is absent from the verified archive")
        payload, digest = self.read_member(self.experiments[number])
        token = object()
        _PENDING_VERIFIED_ARCHIVE_ISSUERS.add(token)
        try:
            return HydrideCompressorWorkbook(payload, experiment=number,
                archive_sha256=self.sha256, member_name=self.experiments[number],
                member_sha256=digest, limits=self.limits, _archive_issuer_token=token)
        except Exception:
            _PENDING_VERIFIED_ARCHIVE_ISSUERS.discard(token)
            raise


class HydrideCompressorWorkbook:
    """One source workbook snapshot, distinct raw/selection/calibration export groups."""

    def __init__(self, payload: bytes, *, experiment: int, archive_sha256: str,
                 member_name: str, member_sha256: str, limits: ArchiveLimits = ArchiveLimits(),
                 _archive_issuer_token=None):
        from openpyxl import load_workbook

        self._archive_verified = _archive_issuer_token in _PENDING_VERIFIED_ARCHIVE_ISSUERS
        if self._archive_verified:
            _PENDING_VERIFIED_ARCHIVE_ISSUERS.remove(_archive_issuer_token)

        if len(payload) > limits.member_bytes or hashlib.sha256(payload).hexdigest() != member_sha256:
            raise ValueError("Workbook member size or SHA-256 mismatch")
        self.payload, self.experiment, self.limits = payload, experiment, limits
        self.archive_sha256, self.member_name, self.member_sha256 = archive_sha256, member_name, member_sha256
        with ZipFile(BytesIO(payload)) as archive:
            self.inventory = _safe_inventory(archive, total_limit=limits.workbook_expanded_bytes,
                member_limit=limits.workbook_member_bytes, limits=limits)
            self._paths = _sheet_paths(archive)
        self._workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True, keep_links=False)
        self.sheet_names = tuple(self._workbook.sheetnames)
        self.raw_sheet = f"Cycle Definition Exp.{experiment}"
        self.selected_sheets = tuple(name for name in self.sheet_names if re.fullmatch(
            rf"Cycle(?: [12])? Data Exp\.{experiment}", name))
        if self.raw_sheet not in self.sheet_names or not self.selected_sheets:
            self.close()
            raise ValueError("Unreviewed source experiment worksheet structure")
        for sheet in self._workbook:
            if (sheet.max_row > limits.worksheet_rows or sheet.max_column > limits.worksheet_columns):
                self.close()
                raise ValueError("Worksheet dimensions exceed the source profile budget")
        self._formulas = {}
        self._schemas = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._workbook.close()

    def notes(self):
        """Retain pre-header source fields, including protocol and qualification notes."""
        schema = self.schemas(self.raw_sheet)
        header = schema[0].first_data_row - 3
        return tuple(SourceCell(self.raw_sheet, cell.coordinate, cell.value)
            for row in self._workbook[self.raw_sheet].iter_rows(max_row=header - 1)
            for cell in row if cell.value is not None)

    @property
    def gas_context(self):
        # These explicit profile cases refer to the source overview and notes,
        # not gas identities inferred from generic MFC column headings.
        if self.experiment == 1:
            return "argon thermal case; not a hydrogen experiment (definition A4:A5)"
        if self.experiment == 2:
            return "thermal case without hydrogen; fill gas unresolved (overview)"
        return "reported hydrogen capacity/compression case; gas purity/spin unresolved"

    def schemas(self, sheet_name: str) -> tuple[LoggerSchema, ...]:
        if sheet_name in self._schemas:
            return self._schemas[sheet_name]
        if sheet_name != self.raw_sheet and sheet_name not in self.selected_sheets:
            raise ValueError("Only raw logger grids and explicit selected cycles are observation profiles")
        sheet = self._workbook[sheet_name]
        top = tuple(sheet.iter_rows(max_row=85, max_col=sheet.max_column, values_only=True))
        raw = sheet_name == self.raw_sheet
        matches = [i for i, row in enumerate(top) if row[0] == "Labview"]
        if len(matches) != 1:
            raise ValueError("Unreviewed logger group header")
        group_index = matches[0]
        alias_index = group_index + (2 if raw else 1)
        aliases, hardware = top[alias_index], top[group_index + 1]
        loading_station = self.experiment in (6, 7)
        expected_tail = ("Time", "Flow-3", None if self.experiment == 6 else "MFC-3") if raw else (
            None, "Flow-3", "MFC-3" if self.experiment == 6 else None)
        expected_aliases = LABVIEW_ALIASES[:12] + expected_tail if loading_station else LABVIEW_ALIASES
        if tuple(aliases[:15]) != expected_aliases:
            raise ValueError("Unreviewed Labview aliases")
        unit_sheet = self.selected_sheets[0] if raw else sheet_name
        if raw:
            selected = self._workbook[unit_sheet]
            unit_top = tuple(selected.iter_rows(max_row=20, max_col=41, values_only=True))
            unit_indices = [i for i, row in enumerate(unit_top) if row[0] == "Labview"]
            if len(unit_indices) != 1:
                raise ValueError("Raw Labview units require the selected-cycle unit row")
            unit_index = unit_indices[0]
            units = unit_top[unit_index]
        else:
            units, unit_index = top[group_index], group_index
        expected_units = LABVIEW_UNITS[:9] + ((None, "ln/min", "ln/min" if self.experiment == 6 else None)
            if loading_station else (("nl/min",) * 3 if self.experiment == 4 else LABVIEW_UNITS[9:]))
        if tuple(units[3:15]) != expected_units or units[2] != "s":
            raise ValueError("Unreviewed source units; no automatic unit inference")
        first_row = alias_index + 2

        def evidence(column, value, *, selected_units=False):
            return SourceCell(unit_sheet if selected_units else sheet_name,
                f"{_column_name(column)}{unit_index + 1 if selected_units else group_index + 1}", value)

        channels = [Channel(3, str(hardware[2]), "Seconds", "s", evidence(3, "s", selected_units=True),
            Variable("Seconds", "time", "s", "Labview source elapsed counter; epoch unresolved"))]
        for column in range(4, 13 if loading_station else 16):
            name, unit = str(aliases[column - 1]), str(units[column - 1])
            basis, quantity, si, scale, offset = "", "", "", 1., 0.
            if unit in ("bar", "barg"):
                quantity, si, scale = "reported_pressure", "Pa", 1e5
                basis = PRESSURE_BASIS if unit == "bar" else GAUGE_BASIS
            elif unit == "l/min":
                quantity, si, scale = "volume_flow", "m3/s", 1e-3 / 60
                basis = "HTF instrument volume flow; no density or mass conversion"
            elif unit in ("ln/min", "nl/min"):
                quantity, si, scale = "reference_volume_flow", "m3_ref/s", 1e-3 / 60
                basis = REFERENCE_FLOW_BASIS
            elif unit == "°C":
                quantity, si, offset = "temperature", "K", 273.15
                basis = "source HTF temperature channel; not bed temperature"
            channels.append(Channel(column, str(hardware[column - 1]), name, unit,
                evidence(column, unit, selected_units=True), Variable(name, quantity, si, basis), scale, offset))
        groups = [(1, "Labview", (1, 2), tuple(channels), "raw logger export" if raw else "publisher-selected cycle")]
        if loading_station:
            station_channels = []
            for column in (14, 15):
                label = str(aliases[column - 1]) if aliases[column - 1] is not None else f"unassigned-column-{_column_name(column)}"
                unit = units[column - 1]
                variable = (Variable(label, "reference_volume_flow", "m3_ref/s", REFERENCE_FLOW_BASIS)
                    if unit == "ln/min" else Variable(label, "reported_numeric", "unresolved", "source unit/role unresolved"))
                station_channels.append(Channel(column, str(hardware[column - 1]), label,
                    str(unit) if unit is not None else "", evidence(column, unit, selected_units=True),
                    variable, 1e-3 / 60 if unit == "ln/min" else 1.))
            groups.append((13, "Loading Station MFC", (13,), tuple(station_channels),
                           "separate time-of-day export; date/relationship to Labview clock unresolved"))
        for column, value in enumerate(top[group_index], 1):
            if value not in ("Graphtec Pt100 Probes", "Picolog Thermometer"):
                continue
            if aliases[column - 1] != "Date & Time":
                raise ValueError("Unreviewed recorder Date/Time header; numeric clock decoding forbidden")
            width = 12 if raw or value == "Picolog Thermometer" else 10
            if top[group_index][column] != "°C":
                raise ValueError("Temperature export group lacks explicit degree-C unit")
            sensors = []
            for source_column in range(column + 1, column + width + 1):
                alias = aliases[source_column - 1]
                hardware_label = str(hardware[source_column - 1])
                label = str(alias) if alias is not None else f"unassigned-{hardware_label}"
                sensors.append(Channel(source_column, hardware_label, label, "°C",
                    evidence(column + 1, "°C"), Variable(label, "temperature", "K",
                    "source sensor identity; spatial/bed/shell observation role unresolved"), 1., 273.15))
            role = "raw logger export" if raw else "publisher-selected cycle"
            if self.experiment == 2 and raw and column == 48:
                role = "separate thermometer calibration export; definition A18; clock not merged"
            groups.append((column, str(value), (column,), tuple(sensors), role))
        if len(groups) != (4 if loading_station or (raw and self.experiment == 2) else 3):
            raise ValueError("Unreviewed number of recorder export groups")
        schemas = []
        for column, name, clock_columns, sensors, role in groups:
            end = max(c.column for c in sensors)
            headers = tuple(SourceCell(sheet_name, f"{_column_name(c)}{r + 1}", top[r][c - 1])
                for r in range(group_index, alias_index + 1) for c in range(column, end + 1))
            schemas.append(LoggerSchema(f"{name}@{_column_name(column)}", role, clock_columns,
                sensors, headers, first_row,
                "source-time-of-day" if name == "Loading Station MFC" else "source-local-calendar",
                "HH:MM:SS or typed time; numeric calendar decoding forbidden" if name == "Loading Station MFC"
                else "reviewed Date/Time headers; typed/ISO/day.month.year/Excel serial at workbook epoch"))
        self._schemas[sheet_name] = tuple(schemas)
        return self._schemas[sheet_name]

    def _sheet_formulas(self, sheet_name):
        if sheet_name not in self._formulas:
            formulas = {}
            with ZipFile(BytesIO(self.payload)) as archive, archive.open(self._paths[sheet_name]) as stream:
                for _, element in ET.iterparse(stream, events=("end",)):
                    if element.tag == NS + "c":
                        formula = element.find(NS + "f")
                        if formula is not None:
                            formulas[element.attrib["r"]] = formula.text or "<shared/array formula>"
                        element.clear()
                    elif element.tag == NS + "row":
                        element.clear()
            self._formulas[sheet_name] = formulas
        return self._formulas[sheet_name]

    def iter_blocks(self, sheet_name: str, *, datetime_origin: datetime,
                    block_rows: int = 4096, start_row: int | None = None,
                    stop_row: int | None = None) -> Iterator[tuple[LoggerBlock, ...]]:
        """One worksheet pass, separate recorder tables, source-row windows inclusive.

        All grid rows survive, including empty padding. Raw caches at formula cells
        are retained but masked as measurements. Selected cycles are reconstructed
        exports of the same experiment, never additional independent measurements.
        The caller declares the naive calendar origin; no recorder is shifted.
        """
        if not isinstance(datetime_origin, datetime) or datetime_origin.tzinfo is not None:
            raise ValueError("Declare a naive source-calendar datetime origin (timezone unresolved)")
        if isinstance(block_rows, bool) or not isinstance(block_rows, int) or block_rows < 1:
            raise ValueError("block_rows must be a positive integer")
        if block_rows > self.limits.worksheet_rows:
            raise ValueError("Block exceeds row budget")
        schemas = self.schemas(sheet_name)
        sheet = self._workbook[sheet_name]
        first = schemas[0].first_data_row if start_row is None else start_row
        last = sheet.max_row if stop_row is None else stop_row
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (first, last)):
            raise ValueError("Source row window must use integer row identities")
        if first < schemas[0].first_data_row or last < first or last > sheet.max_row:
            raise ValueError("Source row window is outside the logger grid")
        formulas = self._sheet_formulas(sheet_name)
        rows, cells = [], []

        def blocks():
            output = []
            for schema in schemas:
                origin_id = datetime_origin.isoformat() if schema.clock_kind == "source-local-calendar" else "midnight; date unresolved"
                clock_id = (f"{SOURCE_ID}/{self.member_sha256}/{sheet_name}/{schema.identity}/"
                            f"{schema.clock_kind}/{origin_id}/excel-epoch-{self._workbook.epoch.isoformat()}")
                variables = (Variable("source_time_of_day" if schema.clock_kind == "source-time-of-day" else "local_datetime_elapsed",
                                     "time", "s", clock_id),
                             *(channel.variable for channel in schema.channels))
                values, reasons, raw, expressions = [], [], [], []
                used_columns = (*schema.clock_columns, *(c.column for c in schema.channels))
                for number, row in zip(rows, cells, strict=True):
                    stamp = (_local_datetime(row, schema.clock_columns, excel_epoch=self._workbook.epoch)
                             if schema.clock_kind == "source-local-calendar" else None)
                    clock_value = (stamp - datetime_origin).total_seconds() if stamp else math.nan
                    if schema.clock_kind == "source-time-of-day":
                        source_time = row[schema.clock_columns[0] - 1]
                        if isinstance(source_time, str) and re.fullmatch(r"\d\d:\d\d:\d\d(?:\.\d+)?", source_time):
                            try:
                                source_time = time.fromisoformat(source_time)
                            except ValueError:
                                source_time = None
                        if isinstance(source_time, time) and source_time.tzinfo is None:
                            clock_value = (source_time.hour * 3600 + source_time.minute * 60
                                           + source_time.second + source_time.microsecond / 1e6)
                    numeric = [clock_value]
                    reason = ["" if math.isfinite(clock_value) else "missing_or_invalid_source_clock"]
                    for column in schema.clock_columns:
                        coordinate = f"{_column_name(column)}{number}"
                        if coordinate in formulas:
                            expressions.append(SourceCell(sheet_name, coordinate, formulas[coordinate]))
                    for channel in schema.channels:
                        coordinate = f"{_column_name(channel.column)}{number}"
                        value = _number(row[channel.column - 1]) * channel.scale + channel.offset
                        problem = "" if math.isfinite(value) else "missing_or_invalid_source_numeric"
                        if channel.variable.quantity == "temperature" and math.isfinite(value) and value <= 0:
                            problem = "nonphysical_absolute_temperature"
                        if coordinate in formulas:
                            expressions.append(SourceCell(sheet_name, coordinate, formulas[coordinate]))
                            if sheet_name == self.raw_sheet:
                                problem = "source_formula_cache_not_independent_measurement"
                        if (self.experiment == 1 and schema.identity.startswith("Picolog")
                                and channel.sensor_label == "T-2_1"):
                            problem = "source_declared_defective_sensor_definition_A18"
                        numeric.append(value)
                        reason.append(problem)
                    values.append(numeric)
                    reasons.append(tuple(reason))
                    raw.append(tuple(row[c - 1] for c in used_columns))
                array = np.array(values, dtype=float)
                valid = np.array([[not reason for reason in row] for row in reasons], dtype=bool)
                origin = Origin.MEASURED if sheet_name == self.raw_sheet else Origin.RECONSTRUCTED
                context = (("profile", PROFILE_ID), ("archive_sha256", self.archive_sha256),
                    ("member", self.member_name), ("member_sha256", self.member_sha256),
                    ("worksheet", sheet_name), ("logger_export", schema.identity),
                    ("export_role", schema.role), ("gas_context", self.gas_context),
                    ("datetime_origin", datetime_origin.isoformat() if schema.clock_kind != "source-time-of-day" else "unused; midnight time-of-day only"),
                    ("clock_kind", schema.clock_kind), ("clock_id", clock_id),
                    ("clock_encoding", schema.clock_encoding),
                    ("workbook_excel_epoch", self._workbook.epoch.isoformat()),
                    ("clock_timezone", "unresolved; source local calendar"),
                    ("independence", "raw/selected/calibration exports share one experiment group"))
                table = ObservationTable(array, variables, valid,
                    tuple(f"{self.archive_sha256}|{self.member_name}|{self.member_sha256}|{sheet_name}|"
                          f"{schema.identity}|row-{row}" for row in rows),
                    (f"{SOURCE_ID}/experiment-{self.experiment}",) * len(rows),
                    (Origin.RECONSTRUCTED,) + (origin,) * len(schema.channels), SOURCE_ID, context)
                token = object()
                _PENDING_LOGGER_BLOCK_ISSUERS.add(token)
                try:
                    output.append(LoggerBlock(
                        table, schema, tuple(rows), tuple(raw), tuple(reasons), tuple(expressions),
                        archive_receipt_verified=self._archive_verified, _issuer_token=token,
                    ))
                except Exception:
                    _PENDING_LOGGER_BLOCK_ISSUERS.discard(token)
                    raise
            return tuple(output)

        max_column = max(c.column for schema in schemas for c in schema.channels)
        for number, row in enumerate(sheet.iter_rows(min_row=first, max_row=last,
                                                     max_col=max_column, values_only=True), first):
            rows.append(number)
            cells.append(row)
            if len(rows) == block_rows:
                yield blocks()
                rows, cells = [], []
        if rows:
            yield blocks()

    def audit(self) -> tuple[SheetAudit, ...]:
        """Count all stored XML cells/rows, numeric caches and missing formula caches.

        Numeric counts include dates, formula results and derived sheets; they are
        storage counts, not counts of independent physical measurements.
        """
        audits = []
        with ZipFile(BytesIO(self.payload)) as archive:
            for name, path in self._paths.items():
                counts = dict(stored_rows=0, populated_rows=0, numeric_rows=0, numeric_cells=0,
                    formula_cells=0, missing_formula_caches=0, error_cells=0, nonfinite_numeric_cells=0)
                dimension, populated, numeric = "", False, False
                with archive.open(path) as stream:
                    for _, element in ET.iterparse(stream, events=("end",)):
                        if element.tag == NS + "dimension":
                            dimension = element.attrib.get("ref", "")
                        elif element.tag == NS + "c":
                            value, formula = element.find(NS + "v"), element.find(NS + "f")
                            text = value.text if value is not None else None
                            has_value = text is not None or element.find(NS + "is") is not None
                            populated |= has_value or formula is not None
                            if formula is not None:
                                counts["formula_cells"] += 1
                                counts["missing_formula_caches"] += int(text is None)
                            if element.attrib.get("t") == "e":
                                counts["error_cells"] += 1
                            elif element.attrib.get("t", "n") == "n" and text is not None:
                                counts["numeric_cells"] += 1
                                numeric = True
                                try:
                                    counts["nonfinite_numeric_cells"] += int(not math.isfinite(float(text)))
                                except ValueError:
                                    counts["nonfinite_numeric_cells"] += 1
                            element.clear()
                        elif element.tag == NS + "row":
                            counts["stored_rows"] += 1
                            counts["populated_rows"] += int(populated)
                            counts["numeric_rows"] += int(numeric)
                            populated, numeric = False, False
                            element.clear()
                audits.append(SheetAudit(name, dimension, **counts))
        return tuple(audits)


def _sheet_paths(archive):
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {}
    for relationship in relationships:
        if not relationship.attrib.get("Type", "").endswith("/worksheet"):
            continue
        if relationship.attrib.get("TargetMode") == "External":
            raise ValueError("External worksheet relationships are not observations")
        target = relationship.attrib["Target"]
        path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target))
        if path.startswith("../") or not path.startswith("xl/"):
            raise ValueError("Worksheet relationship escapes the workbook")
        targets[relationship.attrib["Id"]] = path
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    return {sheet.attrib["name"]: targets[sheet.attrib[
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
        for sheet in workbook.find(NS + "sheets")}
