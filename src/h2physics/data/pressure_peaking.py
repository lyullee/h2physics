"""Qualified views of the USN unignited pressure-peaking exports.

Primary data: Lach and Gaathaug, https://doi.org/10.23642/usn.17932439.v1.
Recorder clocks, reported pressure bases and point-sensor identity stay separate.
"""

import hashlib
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ..core import Origin, TimeSeries, immutable_array
from ..observations import ObservationTable, Variable
from ..units import convert_to_si
from ._mat_export import decode_recorded_mat

PROFILE_ID = "usn-pressure-unignited-v1-profile-1"
METER_BASIS = "Coriolis outlet/meter reported pressure; absolute/gauge basis unresolved"
P1_BASIS = "exported GEN3i P1; reported overpressure; guide column-3 mapping unresolved"
CONCENTRATION_BASIS = "XEN H2 Output (%); point sensor; volume/mole convention unresolved"
SIGMA_DIMENSIONS = ("s", "g/s", "bar")
SIGMA_LABELS = ("time", "Mass Flow", "Pressure at mass flow meter")
GEN_DIMENSIONS = ("s", "kPa", "V", "")
GEN_LABELS = ("Time", "P1", "Trigger", "Ev", *(
    item for prefix in ("A09", "B17") for number in range(1, 9)
    for item in (f"{prefix}_{number:02}", "Ev")))[:-1]

_PENDING_MAT_ISSUERS: set[object] = set()
_PENDING_BLOCK_ISSUERS: set[object] = set()
_PENDING_RUN_ISSUERS: set[object] = set()
_PENDING_CONCENTRATION_WORKBOOK_ISSUERS: set[object] = set()
_PENDING_CONCENTRATION_BLOCK_ISSUERS: set[object] = set()


def _issue_mat_record(**values):
    token = object()
    _PENDING_MAT_ISSUERS.add(token)
    try:
        return PressureRecorder(**values, _issuer_token=token)
    except Exception:
        _PENDING_MAT_ISSUERS.discard(token)
        raise


def _issue_recorder_block(**values):
    token = object()
    _PENDING_BLOCK_ISSUERS.add(token)
    try:
        return RecorderBlock(**values, _issuer_token=token)
    except Exception:
        _PENDING_BLOCK_ISSUERS.discard(token)
        raise


def _issue_mat_run(**values):
    token = object()
    _PENDING_RUN_ISSUERS.add(token)
    try:
        return PressureMatRun(**values, _issuer_token=token)
    except Exception:
        _PENDING_RUN_ISSUERS.discard(token)
        raise


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for payload in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(payload)
    return digest.hexdigest()


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _identity(source_id, experiment_id):
    if not source_id.strip() or not experiment_id.strip():
        raise ValueError("Declare source and source-experiment identities")


def _hash_check(path, expected_sha256, maximum_bytes):
    _positive_integer(maximum_bytes, "maximum_bytes")
    if path.stat().st_size > maximum_bytes:
        raise ValueError("Source exceeds the declared compressed byte budget")
    digest = file_sha256(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Source SHA-256 differs from the recorded bytes")
    return digest


@dataclass(frozen=True, slots=True)
class PressureDataIssue:
    code: str
    channel: str
    count: int
    first_source_row: int | None = None


@dataclass(frozen=True, slots=True)
class RecorderBlock:
    series: TimeSeries
    source_rows: NDArray[np.int64]
    experiment_id: str
    source_sha256: str
    matrix_name: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_BLOCK_ISSUERS:
            raise ValueError("Recorder blocks must be projected from a qualified MAT recorder")
        _PENDING_BLOCK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        rows = np.array(self.source_rows, dtype=np.int64, copy=True)
        if (rows.shape != self.series.time_s.shape or np.any(rows < 1)
                or np.any(np.diff(rows) <= 0)):
            raise ValueError("Source MATLAB rows must match the ordered block")
        rows = immutable_array(rows, name="source_rows")
        object.__setattr__(self, "source_rows", rows)

    @property
    def observations(self) -> ObservationTable:
        """Materialize row identities only for the requested bounded block."""
        series = self.series
        variables = (Variable("recorder_time", "time", "s", series.clock_id), *(
            Variable(name, quantity, unit, basis) for name, quantity, unit, basis in zip(
                series.channels, series.quantities, series.units, series.basis_ids, strict=True)))
        return ObservationTable(np.column_stack((series.time_s, series.values)), variables,
            np.column_stack((np.ones(len(series.time_s), dtype=bool), series.valid)),
            tuple(f"{series.source_id}|{self.matrix_name}|row-{i}" for i in self.source_rows),
            (self.experiment_id,) * len(self.source_rows), (Origin.MEASURED,) * len(variables),
            series.source_id, (("file_sha256", self.source_sha256), ("profile", PROFILE_ID),
                ("clock_id", series.clock_id), ("source_matrix", self.matrix_name)))


@dataclass(frozen=True, slots=True)
class PressureRecorder:
    """Read-only exported matrix; SI conversion and row strings are block bounded."""

    raw: NDArray[np.float64]
    matrix_name: str
    dimension_labels: tuple[str, ...]
    channel_labels: tuple[str, ...]
    source_id: str
    source_sha256: str
    experiment_id: str
    clock_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_MAT_ISSUERS:
            raise ValueError("Pressure recorders must be issued by load_pressure_mat")
        _PENDING_MAT_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        if self.matrix_name not in {"SIGMA", "GEN3i"}:
            raise ValueError("Unknown pressure-peaking recorder")
        expected = 3 if self.matrix_name == "SIGMA" else 2
        raw = np.asarray(self.raw, dtype=np.float64)
        if raw.ndim != 2 or raw.shape[1] != expected or not len(raw):
            raise ValueError("The recorder export has an unreviewed matrix shape")
        # Check in bounded temporary arrays, including each inter-block boundary.
        previous = -math.inf
        for first in range(0, len(raw), 100_000):
            time = raw[first:first + 100_000, 0]
            if (not np.all(np.isfinite(time)) or time[0] <= previous
                    or np.any(np.diff(time) <= 0)):
                raise ValueError("Recorder time is not finite and strictly increasing")
            previous = time[-1]
        raw = immutable_array(raw, name="pressure recorder raw matrix")
        object.__setattr__(self, "raw", raw)

    def iter_blocks(self, *, block_rows: int = 100_000, first_row: int = 1,
                    last_row: int | None = None,
                    time_window_s: tuple[float, float] | None = None) -> Iterator[RecorderBlock]:
        """Yield closed source-row / closed time-window intersections without resampling.

        MATLAB v5 compressed matrices must first be decoded by SciPy as a whole;
        this API bounds subsequent SI arrays/identities, not decompression memory.
        """
        _positive_integer(block_rows, "block_rows")
        _positive_integer(first_row, "first_row")
        last = len(self.raw) if last_row is None else _positive_integer(last_row, "last_row")
        if first_row > last or last > len(self.raw):
            raise ValueError("Requested source rows lie outside the exported matrix")
        first, stop = first_row - 1, last
        if time_window_s is not None:
            window = np.asarray(time_window_s, dtype=float)
            if window.shape != (2,) or not np.all(np.isfinite(window)) or window[1] < window[0]:
                raise ValueError("Declare a finite ordered closed recorder-time window")
            first = max(first, int(np.searchsorted(self.raw[:, 0], window[0], side="left")))
            stop = min(stop, int(np.searchsorted(self.raw[:, 0], window[1], side="right")))
        sigma = self.matrix_name == "SIGMA"
        channels = (("signed_mass_flow", "meter_reported_pressure") if sigma
                    else ("exported_p1_reported_overpressure",))
        quantities = ("mass_flow", "reported_pressure") if sigma else ("reported_pressure",)
        bases = ("signed Coriolis output; zero/negative values retained", METER_BASIS) if sigma else (P1_BASIS,)
        for start in range(first, stop, block_rows):
            end = min(start + block_rows, stop)
            raw = self.raw[start:end]
            if sigma:
                values = np.column_stack((convert_to_si(raw[:, 1], quantity="mass_flow", unit="g/s"),
                    convert_to_si(raw[:, 2], quantity="reported_pressure", unit="bar")))
            else:
                values = convert_to_si(raw[:, 1:], quantity="reported_pressure", unit="kPa")
            series = TimeSeries(raw[:, 0], values, channels,
                ("kg/s", "Pa") if sigma else ("Pa",), np.isfinite(values), self.clock_id,
                Origin.MEASURED, self.source_id, quantities, bases)
            yield _issue_recorder_block(series=series,
                source_rows=np.arange(start + 1, end + 1), experiment_id=self.experiment_id,
                source_sha256=self.source_sha256, matrix_name=self.matrix_name)


@dataclass(frozen=True, slots=True)
class PressureMatRun:
    source_id: str
    source_sha256: str
    experiment_id: str
    sigma: PressureRecorder
    gen3i: PressureRecorder
    issues: tuple[PressureDataIssue, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_RUN_ISSUERS:
            raise ValueError("MAT runs must be issued by load_pressure_mat")
        _PENDING_RUN_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        if (self.sigma.source_sha256 != self.source_sha256
                or self.gen3i.source_sha256 != self.source_sha256
                or self.sigma.source_id != self.source_id
                or self.gen3i.source_id != self.source_id
                or self.sigma.experiment_id != self.experiment_id
                or self.gen3i.experiment_id != self.experiment_id
                or self.sigma.matrix_name != "SIGMA" or self.gen3i.matrix_name != "GEN3i"):
            raise ValueError("MAT recorder identities do not match the issued run")


def _mat_strings(array):
    return tuple("".join(np.asarray(item).ravel().astype(str)) for item in array.ravel())


def load_pressure_mat(path: str | Path, *, source_id: str, experiment_id: str,
                      expected_sha256: str | None = None, maximum_bytes: int = 100_000_000,
                      maximum_array_bytes: int = 160_000_000) -> PressureMatRun:
    """Decode only reviewed numeric/metadata variables, without executing source code."""
    _identity(source_id, experiment_id)
    _positive_integer(maximum_array_bytes, "maximum_array_bytes")
    path = Path(path)
    if path.is_symlink():
        raise ValueError("MAT path cannot be a symbolic link")
    path = path.resolve()
    digest = _hash_check(path, expected_sha256, maximum_bytes)
    metadata_names = ("SIGMAdimensions", "SIGMAunits", "GENdimensions", "GENunits")
    path, data, shapes = decode_recorded_mat(
        path, expected_sha256=digest, expected_file_bytes=path.stat().st_size,
        maximum_file_bytes=maximum_bytes, maximum_array_bytes=maximum_array_bytes,
        numeric_columns={"SIGMA": 3, "GEN3i": 2}, metadata_names=metadata_names,
    )
    metadata = {name: _mat_strings(data[name]) for name in metadata_names}
    if (metadata["SIGMAdimensions"] != SIGMA_DIMENSIONS or metadata["SIGMAunits"] != SIGMA_LABELS
            or metadata["GENdimensions"] != GEN_DIMENSIONS or metadata["GENunits"] != GEN_LABELS):
        raise ValueError("MAT dimensions/channel labels differ from the reviewed profile")
    recorders = [_issue_mat_record(raw=data[name], matrix_name=name,
        dimension_labels=metadata[dimensions], channel_labels=metadata[labels],
        source_id=source_id, source_sha256=digest, experiment_id=experiment_id,
        clock_id=f"{source_id}|{name}|independent-recorder")
        for name, dimensions, labels in (("SIGMA", "SIGMAdimensions", "SIGMAunits"),
                                         ("GEN3i", "GENdimensions", "GENunits"))]
    return _issue_mat_run(source_id=source_id, source_sha256=digest,
        experiment_id=experiment_id, sigma=recorders[0], gen3i=recorders[1], issues=(
        PressureDataIssue("guide_overpressure_column_3_but_export_has_2_columns", "GEN3i", 1),
        PressureDataIssue("metadata_describes_unexported_channels", "GEN3i", len(GEN_LABELS) - 2),
        PressureDataIssue("absolute_gauge_basis_unresolved", "SIGMA:column-3", 1),
        PressureDataIssue("independent_recorder_alignment_unresolved", "SIGMA/GEN3i", 1)))


CONCENTRATION_HEADERS = ("Iteration", "Time", "Output (%)", "Transfer (V/W)", "Pt100 (°C)",
    "Tsens (°C)", "RH (%)", "AH (kPa)", "Corr transfer (-)", "Utp (mV)", "Ih (mA)",
    "Uh (mV)", "Ph (mW)", "Usyst (V)", "Ubat (V)", "Bat (%)", "Alarm")
CONCENTRATION_VARIABLES = (
    Variable("iteration", "source_iteration", "1"),
    Variable("recorder_time_of_day", "time", "s", "local time of day; date/timezone unresolved"),
    Variable("reported_h2_concentration", "reported_concentration", "1", CONCENTRATION_BASIS),
    Variable("transfer", "sensor_transfer", "V/W"),
    Variable("pt100_temperature", "temperature", "K", "XEN Pt100; spatial/thermal role unresolved"),
    Variable("sensor_temperature", "temperature", "K", "XEN Tsens; not assigned room temperature"),
    Variable("relative_humidity", "relative_humidity", "1"),
    Variable("ah_reported_pressure", "reported_pressure", "Pa", "source AH (kPa); meaning unresolved"),
    Variable("corrected_transfer", "sensor_transfer_ratio", "1"),
    Variable("utp", "voltage", "V"), Variable("ih", "current", "A"),
    Variable("uh", "voltage", "V"), Variable("ph", "power", "W"),
    Variable("system_voltage", "voltage", "V"), Variable("battery_voltage", "voltage", "V"),
    Variable("battery_fraction", "reported_battery_fraction", "1"),
    Variable("alarm", "source_alarm_code", "1"))


def _wallclock(value):
    # The acquired source uses these strings, despite the guide describing seconds.
    if not isinstance(value, str):
        return math.nan
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})(\.\d+)?", value)
    if match is None:
        return math.nan
    hour, minute, second = (int(match[i]) for i in (1, 2, 3))
    if hour >= 24 or minute >= 60 or second >= 60:
        return math.nan
    return hour * 3600. + minute * 60. + second + float(match[4] or 0.)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return math.nan
    return float(value)


@dataclass(frozen=True, slots=True)
class ConcentrationBlock:
    observations: ObservationTable
    raw_clock_strings: tuple[object, ...]
    issues: tuple[PressureDataIssue, ...]
    clock_id: str
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_CONCENTRATION_BLOCK_ISSUERS:
            raise ValueError("Concentration blocks must be emitted by the qualified workbook iterator")
        _PENDING_CONCENTRATION_BLOCK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        object.__setattr__(self, "raw_clock_strings", tuple(self.raw_clock_strings))
        object.__setattr__(self, "issues", tuple(self.issues))
        if len(self.raw_clock_strings) != len(self.observations.values):
            raise ValueError("Raw clock labels must align with the retained source observations")
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self) -> str:
        table = self.observations
        payload = (
            table.content_sha256, self.raw_clock_strings, self.issues, self.clock_id,
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def require_current(self) -> "ConcentrationBlock":
        if self._content_fingerprint() != self._seal:
            raise ValueError("Concentration observation block changed after reader issuance")
        return self

    def as_time_series(self) -> TimeSeries:
        """Require a valid strictly increasing file clock; do not unwrap or reorder it."""
        self.require_current()
        table = self.observations
        time, good = table.column("recorder_time_of_day")
        if not np.all(good) or any(issue.code.startswith("clock_not_increasing") for issue in self.issues):
            raise ValueError("Invalid/non-increasing clock cells remain in the observation table")
        indices = tuple(i for i in range(len(table.variables)) if i != 1)
        variables = tuple(table.variables[i] for i in indices)
        result = TimeSeries(time, table.values[:, indices], tuple(v.name for v in variables),
            tuple(v.unit for v in variables), table.valid[:, indices], self.clock_id,
            Origin.MEASURED, table.source_id, tuple(v.quantity for v in variables),
            tuple(v.basis_id for v in variables))
        self.require_current()
        return result


@dataclass(frozen=True, slots=True)
class PressureConcentrationWorkbook:
    path: Path
    source_id: str
    source_sha256: str
    experiment_id: str
    sheet_name: str
    headers: tuple[str, ...]
    metadata_headers: tuple[object, ...]
    metadata_values: tuple[object, ...]
    clock_id: str
    issues: tuple[PressureDataIssue, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        token = self._issuer_token
        if token not in _PENDING_CONCENTRATION_WORKBOOK_ISSUERS:
            raise ValueError("Concentration workbooks must be issued by load_pressure_concentration")
        _PENDING_CONCENTRATION_WORKBOOK_ISSUERS.remove(token)
        object.__setattr__(self, "_issuer_token", None)
        object.__setattr__(self, "path", Path(self.path))
        for name in ("headers", "metadata_headers", "metadata_values", "issues"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        _identity(self.source_id, self.experiment_id)
        if (not self.sheet_name or not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256)
                or file_sha256(self.path) != self.source_sha256):
            raise ValueError("Workbook source identity/hash do not match the captured file")
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self) -> str:
        return hashlib.sha256(repr((
            str(self.path.resolve()), self.source_id, self.source_sha256,
            self.experiment_id, self.sheet_name, self.headers, self.metadata_headers,
            self.metadata_values, self.clock_id, self.issues,
        )).encode("utf-8")).hexdigest()

    def require_current(self) -> "PressureConcentrationWorkbook":
        if (self._content_fingerprint() != self._seal
                or file_sha256(self.path) != self.source_sha256):
            raise ValueError("Qualified concentration workbook changed after admission")
        return self

    def iter_blocks(self, *, block_rows: int = 2048, first_row: int = 4,
                    last_row: int | None = None) -> Iterator[ConcentrationBlock]:
        """Stream original worksheet rows; missing, alarm and invalid rows remain present."""
        from openpyxl import load_workbook

        self.require_current()
        _positive_integer(block_rows, "block_rows")
        _positive_integer(first_row, "first_row")
        if first_row < 4 or (last_row is not None and (
                _positive_integer(last_row, "last_row") < first_row)):
            raise ValueError("Select original source data rows beginning at row 4")
        if file_sha256(self.path) != self.source_sha256:
            raise ValueError("Workbook changed after schema qualification")
        workbook = load_workbook(self.path, read_only=True, data_only=True, keep_links=False)
        previous = None
        try:
            sheet = workbook[self.sheet_name]
            rows, clocks, identities = [], [], []
            for number, row in enumerate(sheet.iter_rows(min_row=first_row, max_row=last_row,
                                                        values_only=True), start=first_row):
                if len(row) != len(CONCENTRATION_HEADERS):
                    raise ValueError("Source worksheet row width differs")
                values = [_number(cell) for cell in row]
                values[1] = _wallclock(row[1])
                rows.append(values)
                clocks.append(row[1])
                identities.append(number)
                if len(rows) == block_rows:
                    block_values = self._block(rows, clocks, identities, previous)
                    previous = values[1]
                    token = object()
                    _PENDING_CONCENTRATION_BLOCK_ISSUERS.add(token)
                    yield ConcentrationBlock(*block_values, _issuer_token=token)
                    self.require_current()
                    rows, clocks, identities = [], [], []
            if rows:
                block_values = self._block(rows, clocks, identities, previous)
                token = object()
                _PENDING_CONCENTRATION_BLOCK_ISSUERS.add(token)
                yield ConcentrationBlock(*block_values, _issuer_token=token)
                self.require_current()
        finally:
            workbook.close()
        self.require_current()

    def _block(self, rows, clocks, identities, previous):
        values = np.asarray(rows, dtype=float)
        for column in (2, 6, 15):
            values[:, column] *= .01
        for column in (4, 5):
            values[:, column] = convert_to_si(values[:, column], quantity="temperature", unit="degC")
        values[:, 7] = convert_to_si(values[:, 7], quantity="reported_pressure", unit="kPa")
        for column in (9, 10, 11, 12):
            values[:, column] *= .001
        valid = np.isfinite(values)
        issues = []

        def issue(mask, code, column):
            count = int(np.count_nonzero(mask))
            if count:
                issues.append(PressureDataIssue(code, CONCENTRATION_VARIABLES[column].name,
                    count, identities[int(np.flatnonzero(mask)[0])]))

        for column in range(values.shape[1]):
            issue(~valid[:, column], "missing_or_nonnumeric", column)
        for column in (2, 6, 15):
            outside = np.isfinite(values[:, column]) & ((values[:, column] < 0.) | (values[:, column] > 1.))
            valid[:, column] &= ~outside
            issue(outside, "outside_reported_fraction_domain", column)
        for column in (4, 5):
            outside = np.isfinite(values[:, column]) & (values[:, column] <= 0.)
            valid[:, column] &= ~outside
            issue(outside, "nonpositive_absolute_temperature", column)
        time = values[:, 1]
        pairs = np.isfinite(time[1:]) & np.isfinite(time[:-1]) & (np.diff(time) <= 0.)
        violations = np.r_[previous is not None and math.isfinite(previous)
                           and math.isfinite(time[0]) and time[0] <= previous, pairs]
        issue(violations, "clock_not_increasing_no_automatic_unwrap", 1)
        table = ObservationTable(values, CONCENTRATION_VARIABLES, valid,
            tuple(f"{self.source_id}|{self.sheet_name}|row-{row}" for row in identities),
            (self.experiment_id,) * len(rows), (Origin.MEASURED,) * len(CONCENTRATION_VARIABLES),
            self.source_id, (("file_sha256", self.source_sha256), ("profile", PROFILE_ID),
                ("clock_id", self.clock_id), ("sheet", self.sheet_name),
                ("device_id", str(self.metadata_values[0])),
                ("factory_device_id", str(self.metadata_values[1])),
                ("measurement_mode", str(self.metadata_values[3]))))
        return table, tuple(clocks), tuple(issues), self.clock_id


def load_pressure_concentration(path: str | Path, *, source_id: str, experiment_id: str,
                                expected_sha256: str | None = None,
                                maximum_bytes: int = 10_000_000) -> PressureConcentrationWorkbook:
    """Qualify metadata and literal headers, then stream measurements on demand."""
    from openpyxl import load_workbook

    _identity(source_id, experiment_id)
    path = Path(path)
    digest = _hash_check(path, expected_sha256, maximum_bytes)
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("Expected the reviewed single-sheet XEN export")
        sheet = workbook.worksheets[0]
        if sheet.max_column != 17 or not sheet.max_row or sheet.max_row > 1_000_000:
            raise ValueError("Unreviewed concentration worksheet dimensions")
        metadata_headers, metadata_values, headers = tuple(sheet.iter_rows(max_row=3, values_only=True))
        normalized = tuple(str(value).replace("ｰC", "°C") for value in headers)
        if normalized != CONCENTRATION_HEADERS:
            raise ValueError("Literal concentration measurement headers/units differ")
        if metadata_headers[:4] != ("Device ID", "Factory Device ID", "Firmware", "Measurement mode"):
            raise ValueError("The XEN device metadata schema differs")
        if metadata_values[3] != "H2" or not metadata_values[0] or not metadata_values[1]:
            raise ValueError("Expected explicit H2 mode and device identities")
        issues = [PressureDataIssue("guide_seconds_but_export_wallclock_strings", "Time", 1),
            PressureDataIssue("point_sensor_geometry_response_and_fraction_basis_unresolved", "Output (%)", 1),
            PressureDataIssue("independent_recorder_alignment_unresolved", "Time", 1)]
        if metadata_values[0] != metadata_values[1]:
            issues.append(PressureDataIssue("device_factory_identity_mismatch", "Device ID", 1))
        token = object()
        _PENDING_CONCENTRATION_WORKBOOK_ISSUERS.add(token)
        return PressureConcentrationWorkbook(path, source_id, digest, experiment_id, sheet.title,
            headers, metadata_headers, metadata_values,
            f"{source_id}|{sheet.title}|device-{metadata_values[0]}|independent-wallclock",
            tuple(issues), _issuer_token=token)
    finally:
        workbook.close()
