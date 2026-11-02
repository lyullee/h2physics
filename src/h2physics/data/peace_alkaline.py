"""Source-token intake for PEACE pressurized alkaline short-stack CSV exports.

The publisher describes raw tables as semicolon-delimited with comma decimals.
This reader therefore retains strings as supplied and does not infer units,
convert decimal tokens, assign sensor meanings, or align experiment clocks.
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
from dataclasses import dataclass, field, fields
from io import StringIO
from pathlib import Path
from weakref import WeakKeyDictionary

from ..units import convert_to_si


_DESCRIPTION_FILENAME = "column_descriptions.csv"
_RAW_FILENAMES = frozenset({
    "experiment_1_raw.csv", "experiment_2_raw.csv", "experiment_3_raw.csv",
})
_FILE_NAMES = _RAW_FILENAMES | {_DESCRIPTION_FILENAME}
class _IssuerSeal:
    """Private identity marker retained only while an issued wrapper exists."""


_ISSUED_RAW_TOKENS = WeakKeyDictionary()
_ISSUED_DESCRIPTION_TOKENS = WeakKeyDictionary()
_ISSUED_BLOCKS = WeakKeyDictionary()
_ISSUED_NORMALIZED_BLOCKS = WeakKeyDictionary()


@dataclass(frozen=True, slots=True)
class SourceTokenTable:
    """Decoded token view bound to exact bytes when issued by a verified file loader."""

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    preamble: tuple[tuple[str, ...], ...]
    raw_bytes: bytes
    source_filename: str | None = None
    source_size_bytes: int | None = None
    publisher_md5: str | None = None
    source_sha256: str | None = None
    _source_path: Path | None = None
    _header_row: int | None = None
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def require_current(self) -> None:
        """Reject a source path whose current bytes differ from this receipt."""
        if not isinstance(self._issuer_token, _IssuerSeal):
            raise ValueError("table was not issued by the verified PEACE raw-file loader")
        issued_receipt = _ISSUED_RAW_TOKENS.get(self._issuer_token)
        actual_receipt = (
            self._source_path, self.source_filename, self.source_size_bytes,
            self.publisher_md5, self.source_sha256, self._header_row,
        )
        if issued_receipt is None or actual_receipt != issued_receipt:
            raise ValueError("table was not issued by the verified PEACE raw-file loader")
        if (self._source_path is None or self.source_filename is None
                or self._header_row is None):
            raise ValueError("table has no complete source path receipt")
        if self._source_path.name != self.source_filename:
            raise ValueError("source path filename differs from the issued receipt")
        current = self._source_path.read_bytes()
        _verify_bytes(
            current,
            expected_filename=self.source_filename,
            expected_size_bytes=self.source_size_bytes,
            expected_publisher_md5=self.publisher_md5,
            expected_sha256=self.source_sha256,
        )
        if current != self.raw_bytes:
            raise ValueError("current source bytes differ from the retained exact payload")
        parsed = read_raw_token_table(current.decode("utf-8", errors="strict"),
                                      header_row=self._header_row)
        if (parsed.header != self.header or parsed.rows != self.rows
                or parsed.preamble != self.preamble):
            raise ValueError("table fields differ from a fresh parse of the verified source bytes")


def _verify_bytes(
    data: bytes,
    *,
    expected_filename: str,
    expected_size_bytes: int | None,
    expected_publisher_md5: str | None,
    expected_sha256: str | None,
) -> tuple[str, str]:
    if not isinstance(data, bytes):
        raise TypeError("source payload must be bytes")
    if expected_filename not in _FILE_NAMES:
        raise ValueError("receipt filename is not a listed PEACE source file")
    if expected_size_bytes is None or expected_publisher_md5 is None or expected_sha256 is None:
        raise ValueError("byte length, publisher MD5 and local SHA-256 are all required")
    if (isinstance(expected_size_bytes, bool) or not isinstance(expected_size_bytes, int)
            or expected_size_bytes <= 0):
        raise ValueError("expected byte length must be a positive integer")
    if not isinstance(expected_publisher_md5, str) or not isinstance(expected_sha256, str):
        raise TypeError("publisher MD5 and local SHA-256 must be hexadecimal strings")
    if len(data) != expected_size_bytes:
        raise ValueError("source byte length differs from the declared receipt")
    md5 = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{32}", expected_publisher_md5) or md5 != expected_publisher_md5:
        raise ValueError("source bytes do not match the declared publisher MD5")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or sha256 != expected_sha256:
        raise ValueError("source bytes do not match the declared local SHA-256")
    return md5, sha256


def read_raw_token_table(text: str, *, header_row: int = 0) -> SourceTokenTable:
    """Read a raw PEACE-style table without numerical or unit interpretation.

    ``header_row`` is explicit because source preambles/header structure must
    not be guessed. Rows before it are ignored by this table view and must be
    retained separately by the caller when present. Blank trailing lines are
    ignored; CSV-decoded field values remain strings without normalization.
    """
    if not isinstance(text, str):
        raise TypeError("text must be decoded source text")
    if isinstance(header_row, bool) or not isinstance(header_row, int) or header_row < 0:
        raise ValueError("header_row must be a nonnegative integer")
    raw_bytes = text.encode("utf-8")
    records = list(csv.reader(StringIO(text, newline=""), delimiter=";", strict=True))
    while records and not any(cell for cell in records[-1]):
        records.pop()
    if header_row >= len(records):
        raise ValueError("header_row is outside the source table")
    header = tuple(records[header_row])
    if not header or any(not name for name in header):
        raise ValueError("selected header row must contain nonempty source labels")
    rows = tuple(tuple(row) for row in records[header_row + 1:])
    if any(len(row) != len(header) for row in rows):
        raise ValueError("source table row width differs from selected header")
    return SourceTokenTable(
        header=header,
        rows=rows,
        preamble=tuple(tuple(row) for row in records[:header_row]),
        raw_bytes=raw_bytes,
    )


def load_raw_file(
    path: str | Path,
    *,
    expected_filename: str,
    expected_size_bytes: int,
    expected_publisher_md5: str,
    expected_sha256: str,
    header_row: int = 0,
) -> SourceTokenTable:
    """Verify a declared PEACE raw file before UTF-8 decoding and CSV parsing.

    Expected receipt values must come from the source manifest. Only the three
    raw experiment exports are admitted; cleaned derivatives and the channel
    description mapping use separate schemas and are not accepted here.
    """
    if expected_filename not in _RAW_FILENAMES:
        raise ValueError("expected_filename must name one of the three source raw experiment files")
    source_path = Path(path)
    if source_path.name != expected_filename:
        raise ValueError("path basename differs from the declared source filename")
    raw_bytes = source_path.read_bytes()
    publisher_md5, sha256 = _verify_bytes(
        raw_bytes,
        expected_filename=expected_filename,
        expected_size_bytes=expected_size_bytes,
        expected_publisher_md5=expected_publisher_md5,
        expected_sha256=expected_sha256,
    )
    text = raw_bytes.decode("utf-8", errors="strict")
    parsed = read_raw_token_table(text, header_row=header_row)
    token = _IssuerSeal()
    result = SourceTokenTable(
        header=parsed.header,
        rows=parsed.rows,
        preamble=parsed.preamble,
        raw_bytes=raw_bytes,
        source_filename=expected_filename,
        source_size_bytes=len(raw_bytes),
        publisher_md5=publisher_md5,
        source_sha256=sha256,
        _source_path=source_path,
        _header_row=header_row,
        _issuer_token=token,
    )
    _ISSUED_RAW_TOKENS[token] = (
        source_path, expected_filename, expected_size_bytes, publisher_md5, sha256, header_row,
    )
    return result


@dataclass(frozen=True, slots=True)
class PEACEChannelDescription:
    """One exact row from the publisher's channel-description mapping."""

    source_channel_id: str
    publisher_label: str
    publisher_description_text: str


@dataclass(frozen=True, slots=True)
class PEACEColumnDescriptionMap:
    """Checksum-bound source description map; no units are inferred from prose."""

    entries: tuple[PEACEChannelDescription, ...]
    raw_bytes: bytes
    source_filename: str
    source_size_bytes: int
    publisher_md5: str
    source_sha256: str
    _source_path: Path
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def require_current(self) -> None:
        if not isinstance(self._issuer_token, _IssuerSeal):
            raise ValueError("description map was not issued by its verified file loader")
        issued_receipt = _ISSUED_DESCRIPTION_TOKENS.get(self._issuer_token)
        actual_receipt = (
            self._source_path, self.source_filename, self.source_size_bytes,
            self.publisher_md5, self.source_sha256,
        )
        if issued_receipt is None or actual_receipt != issued_receipt:
            raise ValueError("description map was not issued by its verified file loader")
        if self._source_path.name != self.source_filename:
            raise ValueError("description path filename differs from the issued receipt")
        current = self._source_path.read_bytes()
        _verify_bytes(
            current,
            expected_filename=self.source_filename,
            expected_size_bytes=self.source_size_bytes,
            expected_publisher_md5=self.publisher_md5,
            expected_sha256=self.source_sha256,
        )
        if current != self.raw_bytes:
            raise ValueError("current description bytes differ from the retained exact payload")
        parsed = _parse_description_map(current.decode("utf-8", errors="strict"))
        if parsed != self.entries:
            raise ValueError("description entries differ from a fresh parse of verified bytes")


def _parse_description_map(text: str) -> tuple[PEACEChannelDescription, ...]:
    records = list(csv.reader(StringIO(text, newline=""), delimiter=",", strict=True))
    expected_header = ("original_column", "cleaned_column", "description")
    if not records or tuple(records[0]) != expected_header:
        raise ValueError("description file header differs from the source-declared schema")
    entries = []
    seen = set()
    for row in records[1:]:
        if len(row) != 3 or not row[0]:
            raise ValueError("description row is malformed or lacks its source channel ID")
        if row[0] in seen:
            raise ValueError("description map repeats a source channel ID")
        seen.add(row[0])
        entries.append(PEACEChannelDescription(row[0], row[1], row[2]))
    if not entries:
        raise ValueError("description map contains no channel rows")
    return tuple(entries)


def load_column_descriptions(
    path: str | Path,
    *,
    expected_filename: str,
    expected_size_bytes: int,
    expected_publisher_md5: str,
    expected_sha256: str,
) -> PEACEColumnDescriptionMap:
    """Verify and parse the publisher's independently licensed description CSV."""
    if expected_filename != _DESCRIPTION_FILENAME:
        raise ValueError("expected_filename must be column_descriptions.csv")
    source_path = Path(path)
    if source_path.name != expected_filename:
        raise ValueError("path basename differs from the declared description filename")
    raw_bytes = source_path.read_bytes()
    publisher_md5, sha256 = _verify_bytes(
        raw_bytes,
        expected_filename=expected_filename,
        expected_size_bytes=expected_size_bytes,
        expected_publisher_md5=expected_publisher_md5,
        expected_sha256=expected_sha256,
    )
    text = raw_bytes.decode("utf-8", errors="strict")
    entries = _parse_description_map(text)
    token = _IssuerSeal()
    result = PEACEColumnDescriptionMap(
        entries=entries,
        raw_bytes=raw_bytes,
        source_filename=expected_filename,
        source_size_bytes=len(raw_bytes),
        publisher_md5=publisher_md5,
        source_sha256=sha256,
        _source_path=source_path,
        _issuer_token=token,
    )
    _ISSUED_DESCRIPTION_TOKENS[token] = (
        source_path, expected_filename, expected_size_bytes, publisher_md5, sha256,
    )
    return result


@dataclass(frozen=True, slots=True)
class PEACESourceSeries:
    """Source-aligned string values with their verbatim publisher mapping."""

    description: PEACEChannelDescription
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PEACEObservationBlock:
    """Loader-issued immutable projection, deliberately not a numeric observation table."""

    source_row_indices: tuple[int, ...]
    source_header: tuple[str, ...]
    time: PEACESourceSeries
    total_current: PEACESourceSeries
    total_power: PEACESourceSeries
    total_voltage: PEACESourceSeries
    temperatures: tuple[PEACESourceSeries, ...]
    reported_pressure: PEACESourceSeries
    hydrogen_flow: PEACESourceSeries
    hydrogen_quality: PEACESourceSeries
    source_filename: str
    source_size_bytes: int
    source_publisher_md5: str
    source_sha256: str
    description_filename: str
    description_size_bytes: int
    description_publisher_md5: str
    description_sha256: str
    _raw_source: SourceTokenTable
    _description_source: PEACEColumnDescriptionMap
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def require_current(self) -> None:
        if not isinstance(self._issuer_token, _IssuerSeal):
            raise ValueError("observation block was not issued by its source projector")
        issued_owners = _ISSUED_BLOCKS.get(self._issuer_token)
        if issued_owners != (id(self._raw_source), id(self._description_source)):
            raise ValueError("observation block was not issued for these exact source owners")
        self._raw_source.require_current()
        self._description_source.require_current()
        expected = project_source_observations(self._raw_source, self._description_source)
        try:
            for item in fields(self):
                if item.name in {"_raw_source", "_description_source", "_issuer_token"}:
                    continue
                if getattr(self, item.name) != getattr(expected, item.name):
                    raise ValueError(
                        f"observation block field {item.name!r} differs from source projection"
                    )
        finally:
            _ISSUED_BLOCKS.pop(expected._issuer_token, None)


@dataclass(frozen=True, slots=True)
class PEACEUnitSeries:
    """Unit-normalized numeric view retaining exact source tokens and channel identity."""

    source: PEACESourceSeries
    values_si: tuple[float | None, ...]
    quantity: str
    source_unit: str
    si_unit: str
    conversion: str
    semantic_boundary: str


@dataclass(frozen=True, slots=True)
class PEACESIObservationBlock:
    """Safe SI view for explicitly unit-described channels, bound to the raw projection."""

    source: PEACEObservationBlock
    total_current: PEACEUnitSeries
    total_power: PEACEUnitSeries
    total_voltage: PEACEUnitSeries
    temperatures: tuple[PEACEUnitSeries, ...]
    reported_pressure: PEACEUnitSeries
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    @property
    def raw_only_channels(self) -> tuple[PEACESourceSeries, ...]:
        return (self.source.time, self.source.hydrogen_flow, self.source.hydrogen_quality)

    def require_current(self) -> None:
        if not isinstance(self._issuer_token, _IssuerSeal):
            raise ValueError("SI view was not issued by the PEACE normalizer")
        if _ISSUED_NORMALIZED_BLOCKS.get(self._issuer_token) != id(self.source):
            raise ValueError("SI view was not issued for this exact source projection")
        self.source.require_current()
        expected = normalize_unambiguous_channels(self.source)
        try:
            for item in fields(self):
                if item.name in {"source", "_issuer_token"}:
                    continue
                if getattr(self, item.name) != getattr(expected, item.name):
                    raise ValueError(f"normalized field {item.name!r} differs from source tokens")
        finally:
            _ISSUED_NORMALIZED_BLOCKS.pop(expected._issuer_token, None)


_PUBLISHER_SELECTED_CHANNELS = (
    ("ATA00 CE001", "current"),
    ("ATA00 CE002", "power"),
    ("ATA00 CE003", "voltage"),
    ("RAA10 CT001", "temperature"),
    ("RAA10 CT002", "temperature"),
    ("RAA10 CT003", "temperature"),
    ("RAA30 CT001", "temperature"),
    ("RAA20 CT001", "temperature"),
    ("RAA20 CP001", "pressure"),
    ("RAA20 CF002", "hydrogen_flow"),
    ("RAA20 CQ001", "hydrogen_quality"),
)


def project_source_observations(
    raw: SourceTokenTable,
    descriptions: PEACEColumnDescriptionMap,
) -> PEACEObservationBlock:
    """Bind publisher-described columns to immutable source-row-aligned tokens."""
    if raw.source_filename not in _RAW_FILENAMES or raw._source_path is None:
        raise ValueError("projection requires a loaded, source-bound raw experiment file")
    if descriptions.source_filename != _DESCRIPTION_FILENAME:
        raise ValueError("projection requires the bound publisher column-description file")
    raw.require_current()
    descriptions.require_current()
    if len(set(raw.header)) != len(raw.header):
        raise ValueError("raw header repeats a channel ID; projection would be ambiguous")
    column_index = {name: index for index, name in enumerate(raw.header)}
    description_by_id = {item.source_channel_id: item for item in descriptions.entries}
    selected_ids = ("Zeit",) + tuple(item[0] for item in _PUBLISHER_SELECTED_CHANNELS)
    absent = tuple(name for name in selected_ids if name not in column_index)
    if absent:
        raise ValueError(f"raw source header lacks selected publisher channels: {absent}")
    unmapped = tuple(name for name in selected_ids if name not in description_by_id)
    if unmapped:
        raise ValueError(f"description map lacks selected source channel IDs: {unmapped}")

    def series(channel_id: str) -> PEACESourceSeries:
        index = column_index[channel_id]
        values = tuple(row[index] for row in raw.rows)
        return PEACESourceSeries(description_by_id[channel_id], values)

    selected = {channel_id: series(channel_id) for channel_id, _role in _PUBLISHER_SELECTED_CHANNELS}
    temperatures = tuple(
        selected[channel_id]
        for channel_id, role in _PUBLISHER_SELECTED_CHANNELS
        if role == "temperature"
    )
    row_indices = tuple(range(len(raw.rows)))
    series_values = (series("Zeit"), *selected.values())
    if any(len(item.values) != len(row_indices) for item in series_values):
        raise ValueError("selected source channel arrays lost source-row alignment")
    token = _IssuerSeal()
    result = PEACEObservationBlock(
        source_row_indices=row_indices,
        source_header=raw.header,
        time=series("Zeit"),
        total_current=selected["ATA00 CE001"],
        total_power=selected["ATA00 CE002"],
        total_voltage=selected["ATA00 CE003"],
        temperatures=temperatures,
        reported_pressure=selected["RAA20 CP001"],
        hydrogen_flow=selected["RAA20 CF002"],
        hydrogen_quality=selected["RAA20 CQ001"],
        source_filename=raw.source_filename,
        source_size_bytes=raw.source_size_bytes,
        source_publisher_md5=raw.publisher_md5,
        source_sha256=raw.source_sha256,
        description_filename=descriptions.source_filename,
        description_size_bytes=descriptions.source_size_bytes,
        description_publisher_md5=descriptions.publisher_md5,
        description_sha256=descriptions.source_sha256,
        _raw_source=raw,
        _description_source=descriptions,
        _issuer_token=token,
    )
    _ISSUED_BLOCKS[token] = (id(raw), id(descriptions))
    return result


_UNIT_NORMALIZATIONS = {
    "ATA00 CE001": (
        "Total Current (A)", "Total electrical current in amperes", "current", "A", "A",
        "identity",
    ),
    "ATA00 CE002": (
        "Total Power (kW)", "Total electrical power in kilowatts", "power", "kW", "W",
        "multiply by 1000",
    ),
    "ATA00 CE003": (
        "Total Voltage (V)", "Total voltage in volts", "voltage", "V", "V", "identity",
    ),
    "RAA10 CT001": (
        "T_in_lye (°C)", "Inlet lye temperature in degrees Celsius", "temperature",
        "degC", "K", "add 273.15",
    ),
    "RAA10 CT002": (
        "T_out_lyeh2 (°C)", "Outlet lye temperature on H2 side in degrees Celsius",
        "temperature", "degC", "K", "add 273.15",
    ),
    "RAA10 CT003": (
        "T_out_lyeo2 (°C)", "Outlet lye temperature on O2 side in degrees Celsius",
        "temperature", "degC", "K", "add 273.15",
    ),
    "RAA30 CT001": (
        "Oxygen gas temperature after cooling (°C)",
        "O2 gas temperature after cooling stage in degrees Celsius", "temperature",
        "degC", "K", "add 273.15",
    ),
    "RAA20 CT001": (
        "H2 gas Temperature after cooling (°C)",
        "H2 gas temperature after cooling stage in degrees Celsius", "temperature",
        "degC", "K", "add 273.15",
    ),
    "RAA20 CP001": (
        "System Pressure (bar)", "System operating pressure in bar", "reported_pressure",
        "bar", "Pa", "multiply by 100000; pressure basis unresolved",
    ),
}


def _convert_source_series(series: PEACESourceSeries) -> PEACEUnitSeries:
    channel_id = series.description.source_channel_id
    expected = _UNIT_NORMALIZATIONS.get(channel_id)
    if expected is None:
        raise ValueError(f"source channel {channel_id!r} has no admitted SI conversion")
    label, description, quantity, source_unit, si_unit, conversion = expected
    if (series.description.publisher_label != label
            or series.description.publisher_description_text != description):
        raise ValueError(f"publisher description for {channel_id!r} differs from admitted unit evidence")
    numeric = []
    positions = []
    converted: list[float | None] = [None] * len(series.values)
    for index, token in enumerate(series.values):
        if token == "":
            continue
        if not re.fullmatch(r"[+-]?(?:\d+(?:[,.]\d*)?|[,.]\d+)(?:[eE][+-]?\d+)?", token):
            raise ValueError(f"numeric source token {token!r} is not an unambiguous decimal")
        try:
            value = float(token.replace(",", "."))
        except ValueError as error:
            raise ValueError(f"source token {token!r} is not a decimal value") from error
        if not math.isfinite(value):
            raise ValueError("nonfinite numeric source tokens are not admitted")
        numeric.append(value)
        positions.append(index)
    if numeric:
        if quantity == "reported_pressure":
            si_values = convert_to_si(numeric, quantity=quantity, unit=source_unit,
                                      pressure_basis=None)
        else:
            si_values = convert_to_si(numeric, quantity=quantity, unit=source_unit)
        for index, value in zip(positions, si_values, strict=True):
            converted[index] = float(value)
    boundary = (
        "reported total-channel quantity; cell/stack interpretation unresolved"
        if channel_id.startswith("ATA00") else
        "reported pressure converted dimensionally only; absolute/gauge basis unresolved"
        if quantity == "reported_pressure" else
        "publisher-described temperature; sensor calibration and location representativeness unresolved"
        if quantity == "temperature" else
        "publisher-described current; no cell/stack or calibration inference"
    )
    return PEACEUnitSeries(
        source=series,
        values_si=tuple(converted),
        quantity=quantity,
        source_unit=source_unit,
        si_unit=si_unit,
        conversion=conversion,
        semantic_boundary=boundary,
    )


def normalize_unambiguous_channels(
    source: PEACEObservationBlock,
) -> PEACESIObservationBlock:
    """Convert only explicitly unit-described channels; leave ambiguous channels raw."""
    source.require_current()
    total_current = _convert_source_series(source.total_current)
    total_power = _convert_source_series(source.total_power)
    total_voltage = _convert_source_series(source.total_voltage)
    temperatures = tuple(_convert_source_series(item) for item in source.temperatures)
    reported_pressure = _convert_source_series(source.reported_pressure)
    token = _IssuerSeal()
    result = PEACESIObservationBlock(
        source=source,
        total_current=total_current,
        total_power=total_power,
        total_voltage=total_voltage,
        temperatures=temperatures,
        reported_pressure=reported_pressure,
        _issuer_token=token,
    )
    _ISSUED_NORMALIZED_BLOCKS[token] = id(source)
    return result
