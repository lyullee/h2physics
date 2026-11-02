"""Source-bound readers for measured PEM current-ripple campaign exports.

The original ZIP is read in place; large continuous logs are never extracted.
Only channel names and units explicitly declared by the deposited README are
interpreted. Campaign timestamps remain timezone-naive offsets from each file's
first token, and gaps are retained without filling or resampling.
"""

from __future__ import annotations

import array
import csv
import hashlib
import io
import math
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from weakref import WeakKeyDictionary

import numpy as np

from ..core import immutable_array

_SOURCE_SHA256 = "47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab"
_SOURCE_SIZE = 90_759_411
_SOURCE_MEMBER_ROOT = "PEM_ripple_degradation_data/"
_OFFICIAL_DEFAULT = (
    Path(__file__).resolve().parents[3]
    / "data/raw/pem-ripple-degradation/2/PEM_ripple_degradation_data.zip"
)
_ISSUED_ARCHIVES: WeakKeyDictionary = WeakKeyDictionary()
_ISSUER_RECEIPTS: WeakKeyDictionary = WeakKeyDictionary()
_RIPPLE_CONDITIONS = {
    "PEM1": (300.0, 50.0), "PEM2": (0.0, 0.0),
    "PEM3": (600.0, 50.0), "PEM4": (1200.0, 50.0),
}


class _Issuer:
    """Private weak-referenceable token for loader-issued wrappers."""


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


class _HashingReader(io.RawIOBase):
    def __init__(self, stream):
        self._stream = stream
        self.digest = hashlib.sha256()

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        block = self._stream.read(len(buffer))
        buffer[:len(block)] = block
        self.digest.update(block)
        return len(block)


def _csv_reader(member: zipfile.ZipExtFile, digesting: _HashingReader):
    text = io.TextIOWrapper(io.BufferedReader(digesting), encoding="utf-8-sig", newline="")
    return csv.DictReader(text, strict=True), text


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PemRippleArchive:
    """Verified handle to the official Mendeley v2 measurement archive."""

    path: Path
    size_bytes: int
    sha256: str
    _issuer: _Issuer = field(repr=False, compare=False)

    def require_current(self) -> None:
        issued = _ISSUED_ARCHIVES.get(self._issuer)
        if issued != (self.path, self.size_bytes, self.sha256):
            raise ValueError("PEM ripple archive was not issued by its official source loader")
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("PEM ripple source path is not a regular file")
        size, digest = _hash_file(self.path)
        if size != self.size_bytes or digest != self.sha256:
            raise ValueError("PEM ripple archive bytes differ from the publisher-verified receipt")

    def _member(self, relative_name: str) -> tuple[zipfile.ZipInfo, zipfile.ZipFile]:
        if (not relative_name or relative_name.startswith(("/", "\\"))
                or ".." in Path(relative_name).parts or "\\" in relative_name):
            raise ValueError("Unsafe ZIP member name")
        archive = zipfile.ZipFile(self.path, "r")
        member_name = _SOURCE_MEMBER_ROOT + relative_name
        try:
            info = archive.getinfo(member_name)
        except KeyError:
            archive.close()
            raise ValueError(f"Member is not listed in the official archive: {relative_name!r}") from None
        if info.is_dir() or info.file_size > 300_000_000:
            archive.close()
            raise ValueError("Member is a directory or exceeds the bounded reader size")
        return info, archive


def _load_archive(path: str | Path, expected_size_bytes: int,
                  expected_sha256: str) -> PemRippleArchive:
    unresolved = Path(path)
    if unresolved.is_symlink():
        raise ValueError("PEM ripple source must not be reached through a symbolic link")
    source = unresolved.resolve(strict=True)
    if not source.is_file():
        raise ValueError("PEM ripple source must be a regular, non-symlink file")
    size, digest = _hash_file(source)
    if size != expected_size_bytes or digest != expected_sha256:
        raise ValueError("ZIP bytes differ from the declared acquisition receipt")
    # The archive SHA-256 covers every ZIP byte. Individual members are fully
    # streamed and CRC-checked when requested, avoiding a second ~900 MB inflate.
    token = _Issuer()
    result = PemRippleArchive(source, size, digest, token)
    _ISSUED_ARCHIVES[token] = (source, size, digest)
    return result


def load_pem_ripple_archive(path: str | Path = _OFFICIAL_DEFAULT) -> PemRippleArchive:
    """Verify and issue the official CC BY 4.0 Mendeley Data v2 archive handle."""
    return _load_archive(path, _SOURCE_SIZE, _SOURCE_SHA256)


def _require_archive(archive: PemRippleArchive) -> None:
    if type(archive) is not PemRippleArchive or archive._issuer not in _ISSUED_ARCHIVES:
        raise ValueError("archive must come from load_pem_ripple_archive")
    archive.require_current()


def _projection_fingerprint(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _issue_member(archive: PemRippleArchive, relative_name: str, digest: str,
                 row_count: int, projection_sha256: str) -> _Issuer:
    token = _Issuer()
    _ISSUER_RECEIPTS[token] = (
        archive._issuer, relative_name, digest, row_count,
        archive.path, archive.size_bytes, archive.sha256, projection_sha256,
    )
    return token


def _check_issued_member(token: _Issuer, archive: PemRippleArchive,
                         relative_name: str, digest: str, row_count: int,
                         projection_sha256: str) -> None:
    if _ISSUER_RECEIPTS.get(token) != (
        archive._issuer, relative_name, digest, row_count,
        archive.path, archive.size_bytes, archive.sha256, projection_sha256,
    ):
        raise ValueError("member data is not bound to this publisher-verified archive and receipt")
    archive.require_current()


def _iter_source_rows(archive: PemRippleArchive, relative_name: str,
                      expected_sha256: str, expected_rows: int, expected_header: tuple[str, ...]):
    """Yield exact CSV strings and verify the streamed member before exhaustion."""
    _require_archive(archive)
    _, zipped = archive._member(relative_name)
    seen = 0
    try:
        with zipped, zipped.open(_SOURCE_MEMBER_ROOT + relative_name, "r") as member:
            hashing = _HashingReader(member)
            rows, text = _csv_reader(member, hashing)
            try:
                if tuple(rows.fieldnames or ()) != expected_header:
                    raise ValueError("Source token header differs from the admitted CSV schema")
                for row in rows:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(f"Ragged source row {rows.line_num}")
                    seen += 1
                    yield tuple(row[name] for name in expected_header)
            finally:
                text.detach().close()
            actual_sha256 = hashing.digest.hexdigest()
    except (csv.Error, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ValueError(f"Unable to stream source tokens from {relative_name!r}") from error
    if seen != expected_rows or actual_sha256 != expected_sha256:
        raise ValueError("Source token stream differs from the issued member receipt")


def _cell(value: str) -> str:
    if value not in {"PEM1", "PEM2", "PEM3", "PEM4"}:
        raise ValueError("cell_id must be PEM1, PEM2, PEM3 or PEM4")
    return value


def _cycle(value: str | int) -> str:
    if isinstance(value, bool):
        raise ValueError("cycle must be Initial or an integer from 1 through 8")
    if (type(value) is int and value == 0) or (type(value) is str and value == "Initial"):
        return "Initial"
    if isinstance(value, int) and 1 <= value <= 8:
        return f"Cycle{value}"
    if isinstance(value, str) and value in {f"Cycle{i}" for i in range(1, 9)}:
        return value
    raise ValueError("cycle must be Initial or an integer from 1 through 8")


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PemRippleIVCurve:
    """Unaveraged polarization rows with source-declared A, V and step index."""

    cell_id: str
    cycle: str
    current_a: np.ndarray = field(repr=False, compare=False)
    voltage_v: np.ndarray = field(repr=False, compare=False)
    step_index: np.ndarray = field(repr=False, compare=False)
    source_member: str
    source_member_sha256: str
    _archive: PemRippleArchive = field(repr=False, compare=False)
    _issuer: _Issuer = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.cell_id not in {"PEM1", "PEM2", "PEM3", "PEM4"}:
            raise ValueError("Unknown PEM ripple cell identifier")
        current = immutable_array(self.current_a, dtype=float, name="current_a")
        voltage = immutable_array(self.voltage_v, dtype=float, name="voltage_v")
        step = immutable_array(self.step_index, dtype=np.int64, name="step_index")
        if (current.ndim != 1 or not len(current) or voltage.shape != current.shape
                or step.shape != current.shape or not np.all(np.isfinite(current))
                or not np.all(np.isfinite(voltage)) or np.any(step < 0)):
            raise ValueError("IV curve arrays must be finite, nonempty, one-dimensional and aligned")
        object.__setattr__(self, "current_a", current)
        object.__setattr__(self, "voltage_v", voltage)
        object.__setattr__(self, "step_index", step)
        fingerprint = _projection_fingerprint(
            self.cell_id.encode(), self.cycle.encode(), current.tobytes(), voltage.tobytes(),
            step.tobytes(),
        )
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(current), fingerprint)

    def require_current(self) -> None:
        fingerprint = _projection_fingerprint(
            self.cell_id.encode(), self.cycle.encode(), self.current_a.tobytes(),
            self.voltage_v.tobytes(), self.step_index.tobytes(),
        )
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(self.current_a), fingerprint)

    def iter_source_rows(self):
        """Stream exact source tokens `(current_A, voltage_V, step_index)`."""
        self.require_current()
        return _iter_source_rows(
            self._archive, self.source_member, self.source_member_sha256, len(self.current_a),
            ("current_A", "voltage_V", "step_index"),
        )

    @property
    def ripple_frequency_hz(self) -> float:
        return _RIPPLE_CONDITIONS[self.cell_id][0]

    @property
    def ripple_magnitude_percent(self) -> float:
        return _RIPPLE_CONDITIONS[self.cell_id][1]


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PemRippleContinuousTrace:
    """Per-cell ~1 Hz trace retaining exact millisecond clock offsets and gaps."""

    cell_id: str
    timestamp_origin_token: str
    timestamp_offset_ms: np.ndarray = field(repr=False, compare=False)
    current_a: np.ndarray = field(repr=False, compare=False)
    voltage_v: np.ndarray = field(repr=False, compare=False)
    source_member: str
    source_member_sha256: str
    clock_id: str
    timezone_status: str
    _archive: PemRippleArchive = field(repr=False, compare=False)
    _issuer: _Issuer = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.cell_id not in {"PEM1", "PEM2", "PEM3", "PEM4"}:
            raise ValueError("Unknown PEM ripple cell identifier")
        if self.timezone_status != "timezone not declared; source timestamps are naive":
            raise ValueError("Do not assign a timezone absent from the source")
        offsets = immutable_array(self.timestamp_offset_ms, dtype=np.int64,
                                  name="timestamp_offset_ms")
        current = immutable_array(self.current_a, dtype=float, name="current_a")
        voltage = immutable_array(self.voltage_v, dtype=float, name="voltage_v")
        if (offsets.ndim != 1 or not len(offsets) or current.shape != offsets.shape
                or voltage.shape != offsets.shape or offsets[0] != 0
                or np.any(np.diff(offsets) <= 0.) or not np.all(np.isfinite(current))
                or not np.all(np.isfinite(voltage))):
            raise ValueError("Continuous trace arrays must be finite, aligned and strictly clocked")
        object.__setattr__(self, "timestamp_offset_ms", offsets)
        object.__setattr__(self, "current_a", current)
        object.__setattr__(self, "voltage_v", voltage)
        fingerprint = _projection_fingerprint(
            self.cell_id.encode(), self.timestamp_origin_token.encode(), offsets.tobytes(),
            current.tobytes(), voltage.tobytes(), self.clock_id.encode(),
            self.timezone_status.encode(),
        )
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(offsets), fingerprint)

    def require_current(self) -> None:
        fingerprint = _projection_fingerprint(
            self.cell_id.encode(), self.timestamp_origin_token.encode(),
            self.timestamp_offset_ms.tobytes(), self.current_a.tobytes(), self.voltage_v.tobytes(),
            self.clock_id.encode(), self.timezone_status.encode(),
        )
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(self.timestamp_offset_ms), fingerprint)

    def iter_source_rows(self):
        """Stream exact `(timestamp, current_A, voltage_V)` source tokens."""
        self.require_current()
        return _iter_source_rows(
            self._archive, self.source_member, self.source_member_sha256,
            len(self.timestamp_offset_ms), ("timestamp", "current_A", "voltage_V"),
        )

    @property
    def ripple_frequency_hz(self) -> float:
        return _RIPPLE_CONDITIONS[self.cell_id][0]

    @property
    def ripple_magnitude_percent(self) -> float:
        return _RIPPLE_CONDITIONS[self.cell_id][1]

    @property
    def elapsed_s(self) -> np.ndarray:
        return immutable_array(self.timestamp_offset_ms.astype(float) / 1000.,
                               dtype=float, name="elapsed_s")

    @property
    def interval_s(self) -> np.ndarray:
        return immutable_array(np.diff(self.timestamp_offset_ms).astype(float) / 1000.,
                               dtype=float, name="interval_s")


@dataclass(frozen=True, slots=True)
class PemRippleFitRecord:
    """One reported fitted-parameter row; not an independent measurement."""

    cell_id: str
    cycle: str
    membrane_resistance_ohm: float
    alpha_reported: float
    exchange_current_a: float
    limiting_current_a: float
    fit_rmse_v: float


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PemRippleFitTable:
    """Source-bound table of publisher-reported fitted values."""

    records: tuple[PemRippleFitRecord, ...]
    source_member_sha256: str
    source_member: str
    _archive: PemRippleArchive = field(repr=False, compare=False)
    _issuer: _Issuer = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        records = tuple(self.records)
        if not records or any(type(row) is not PemRippleFitRecord for row in records):
            raise ValueError("Fit table must contain parsed reported-fit records")
        object.__setattr__(self, "records", records)
        fingerprint = _projection_fingerprint(
            repr(records).encode("utf-8"),
        )
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(records), fingerprint)

    def require_current(self) -> None:
        fingerprint = _projection_fingerprint(repr(self.records).encode("utf-8"))
        _check_issued_member(self._issuer, self._archive, self.source_member,
                             self.source_member_sha256, len(self.records), fingerprint)


def load_pem_ripple_iv_curve(
    archive: PemRippleArchive,
    *,
    cell_id: str,
    cycle: str | int,
) -> PemRippleIVCurve:
    """Stream one IV file and retain each measured A/V row without conversion."""
    _require_archive(archive)
    cell = _cell(cell_id)
    selected_cycle = _cycle(cycle)
    filename = f"{cell}_{selected_cycle}.csv"
    relative = f"IV_curves/{cell}/{filename}"
    _, zipped = archive._member(relative)
    currents, voltages, steps = array.array("d"), array.array("d"), array.array("q")
    try:
        with zipped, zipped.open(_SOURCE_MEMBER_ROOT + relative, "r") as member:
            hashing = _HashingReader(member)
            rows, text = _csv_reader(member, hashing)
            try:
                if tuple(rows.fieldnames or ()) != ("current_A", "voltage_V", "step_index"):
                    raise ValueError("IV member header differs from source README")
                for row in rows:
                    if None in row or any(value is None or value == "" for value in row.values()):
                        raise ValueError(f"Ragged or empty IV row {rows.line_num}")
                    current, voltage = float(row["current_A"]), float(row["voltage_V"])
                    step_raw = row["step_index"]
                    step_value = int(step_raw)
                    if (not math.isfinite(current) or not math.isfinite(voltage)
                            or step_raw.strip() != str(step_value) or step_value < 0):
                        raise ValueError(f"Invalid numeric value in IV row {rows.line_num}")
                    currents.append(current)
                    voltages.append(voltage)
                    steps.append(step_value)
            finally:
                text.detach().close()
            member_digest = hashing.digest.hexdigest()
    except (csv.Error, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ValueError(f"Unable to read official IV member {relative!r}") from error
    if not currents:
        raise ValueError("IV member has no data rows")
    current = np.frombuffer(currents.tobytes(), dtype=np.float64)
    voltage = np.frombuffer(voltages.tobytes(), dtype=np.float64)
    step = np.frombuffer(steps.tobytes(), dtype=np.int64)
    fingerprint = _projection_fingerprint(cell.encode(), selected_cycle.encode(),
                                          current.tobytes(), voltage.tobytes(), step.tobytes())
    token = _issue_member(archive, relative, member_digest, len(currents), fingerprint)
    return PemRippleIVCurve(cell, selected_cycle, current, voltage, step,
                            relative, member_digest, archive, token)


def load_pem_ripple_continuous_trace(
    archive: PemRippleArchive,
    *,
    cell_id: str,
) -> PemRippleContinuousTrace:
    """Stream one large continuous log, preserving naive clock offsets and gaps."""
    _require_archive(archive)
    cell = _cell(cell_id)
    relative = f"Continuous_voltage/{cell}_continuous_voltage.csv"
    _, zipped = archive._member(relative)
    offsets, currents, voltages = array.array("q"), array.array("d"), array.array("d")
    origin: datetime | None = None
    origin_token = ""
    previous_ms: int | None = None
    try:
        with zipped, zipped.open(_SOURCE_MEMBER_ROOT + relative, "r") as member:
            hashing = _HashingReader(member)
            rows, text = _csv_reader(member, hashing)
            try:
                if tuple(rows.fieldnames or ()) != ("timestamp", "current_A", "voltage_V"):
                    raise ValueError("Continuous member header differs from source README")
                for row in rows:
                    if None in row or any(value is None or value == "" for value in row.values()):
                        raise ValueError(f"Ragged or empty continuous row {rows.line_num}")
                    timestamp_token = row["timestamp"]
                    stamp = datetime.fromisoformat(timestamp_token)
                    if stamp.tzinfo is not None:
                        raise ValueError("Source timestamp unexpectedly specifies a timezone")
                    if stamp.microsecond % 1000:
                        raise ValueError("Source timestamp precision exceeds retained millisecond clock")
                    if origin is None:
                        origin, origin_token = stamp, timestamp_token
                    delta = stamp - origin
                    offset_ms = (delta.days * 86_400_000 + delta.seconds * 1000
                                 + delta.microseconds // 1000)
                    current, voltage = float(row["current_A"]), float(row["voltage_V"])
                    if (not math.isfinite(current) or not math.isfinite(voltage)
                            or (previous_ms is not None and offset_ms <= previous_ms)):
                        raise ValueError(f"Invalid measurement or non-increasing clock at row {rows.line_num}")
                    offsets.append(offset_ms)
                    currents.append(current)
                    voltages.append(voltage)
                    previous_ms = offset_ms
            finally:
                text.detach().close()
            member_digest = hashing.digest.hexdigest()
    except (csv.Error, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ValueError(f"Unable to read official continuous member {relative!r}") from error
    if not offsets or origin is None:
        raise ValueError("Continuous member has no data rows")
    timestamp_offsets = np.frombuffer(offsets.tobytes(), dtype=np.int64)
    current = np.frombuffer(currents.tobytes(), dtype=np.float64)
    voltage = np.frombuffer(voltages.tobytes(), dtype=np.float64)
    clock_id = f"pem-ripple/{cell}/naive-source-time"
    timezone_status = "timezone not declared; source timestamps are naive"
    fingerprint = _projection_fingerprint(
        cell.encode(), origin_token.encode(), timestamp_offsets.tobytes(), current.tobytes(),
        voltage.tobytes(), clock_id.encode(), timezone_status.encode(),
    )
    token = _issue_member(archive, relative, member_digest, len(offsets), fingerprint)
    return PemRippleContinuousTrace(
        cell, origin_token, timestamp_offsets, current, voltage, relative, member_digest,
        clock_id, timezone_status, archive, token,
    )


def load_pem_ripple_fit_table(archive: PemRippleArchive) -> PemRippleFitTable:
    """Read the publisher's fitted values as derived records with stated units only."""
    _require_archive(archive)
    relative = "Fitted_parameters.csv"
    _, zipped = archive._member(relative)
    records = []
    try:
        with zipped, zipped.open(_SOURCE_MEMBER_ROOT + relative, "r") as member:
            hashing = _HashingReader(member)
            rows, text = _csv_reader(member, hashing)
            try:
                expected = ("PEM", "Cycle", "R_mem", "alpha", "i_0", "I_lim", "RMSE")
                if tuple(rows.fieldnames or ()) != expected:
                    raise ValueError("Fitted-parameter member header differs from source README")
                for row in rows:
                    if None in row or any(value is None or value == "" for value in row.values()):
                        raise ValueError(f"Ragged or empty fit row {rows.line_num}")
                    cell = _cell(row["PEM"])
                    cycle_token = row["Cycle"]
                    cycle = "Initial" if cycle_token == "Initial" else "Cycle" + cycle_token.removeprefix("C")
                    cycle = _cycle(cycle)
                    numbers = tuple(float(row[name]) for name in expected[2:])
                    if not all(math.isfinite(value) for value in numbers):
                        raise ValueError(f"Nonfinite fitted value at row {rows.line_num}")
                    records.append(PemRippleFitRecord(cell, cycle, *numbers))
            finally:
                text.detach().close()
            member_digest = hashing.digest.hexdigest()
    except (csv.Error, UnicodeDecodeError, zipfile.BadZipFile) as error:
        raise ValueError("Unable to read the official fitted-parameter member") from error
    expected_keys = {
        (f"PEM{cell_number}", cycle)
        for cell_number in range(1, 5)
        for cycle in ("Initial", *(f"Cycle{i}" for i in range(1, 9)))
    }
    if (len(records) != 36
            or {(record.cell_id, record.cycle) for record in records} != expected_keys):
        raise ValueError("Expected one reported fit for each of four cells and nine characterizations")
    fingerprint = _projection_fingerprint(repr(tuple(records)).encode("utf-8"))
    token = _issue_member(archive, relative, member_digest, len(records), fingerprint)
    return PemRippleFitTable(tuple(records), member_digest, relative, archive, token)


__all__ = [
    "PemRippleArchive", "PemRippleIVCurve", "PemRippleContinuousTrace", "PemRippleFitRecord",
    "PemRippleFitTable", "load_pem_ripple_archive", "load_pem_ripple_iv_curve",
    "load_pem_ripple_continuous_trace", "load_pem_ripple_fit_table",
]
