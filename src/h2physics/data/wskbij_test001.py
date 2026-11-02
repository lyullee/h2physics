"""Hash-bound streaming reader for one WSKBIJ measured pressure trace."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


DOI = "10.18710/WSKBIJ"
VERSION = "1.0"
LICENSE_ID = "CC0-1.0"
FILE_ID = 268129
FILE_NAME = "Test001.txt"
FILE_SIZE_BYTES = 207_853_888
FILE_MD5 = "6a2b1e93513c33d9400ba8abf4b9d082"
FILE_SHA256 = "c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703"
_COLUMNS = ("Time", "P01", "P02", "P03", "P04", "PT1", "PT2", "MFR", "Trigger cam")
_UNIT_TOKENS = ("s", "kPa", "kPa", "kPa", "kPa", "V", "v", "V", "V")
_MISSING = {"", "NA", "N/A", "NAN", "--"}
_PENDING: set[object] = set()


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    """Return stable filesystem identity fields for one streaming pass."""
    stat = path.stat()
    return (
        stat.st_dev,
        stat.st_ino,
        stat.st_size,
        stat.st_mtime_ns,
        stat.st_ctime_ns,
    )


def _read_preamble(path: Path):
    source_time_format = None
    first_sample_timestamp = None
    test_title = None
    columns = None
    units = None
    header_line = None
    with path.open("r", encoding="utf-8-sig", errors="strict", newline="") as stream:
        for line_number, line in enumerate(stream, start=1):
            token = line.rstrip("\r\n")
            if token.startswith("Header time format:"):
                source_time_format = token.split(":", 1)[1].strip()
            elif token.startswith("Time of first sample:"):
                first_sample_timestamp = token.split(":", 1)[1].strip()
            elif token.startswith("Title:"):
                test_title = token.split(":", 1)[1].strip()
            elif tuple(token.split("\t")) == _COLUMNS:
                columns = _COLUMNS
                header_line = line_number
                units_line = stream.readline()
                units = tuple(units_line.rstrip("\r\n").split("\t"))
                break
            if line_number > 64:
                break
    if (source_time_format != "Absolute" or not first_sample_timestamp
            or test_title != "Test001" or columns != _COLUMNS
            or units != _UNIT_TOKENS or header_line is None):
        raise ValueError("WSKBIJ Test001 preamble or reviewed nine-channel schema changed")
    return source_time_format, first_sample_timestamp, columns, units, header_line


def _numeric(token: str, *, row: int, column: str) -> float | None:
    text = token.strip()
    if text.upper() in _MISSING:
        return None
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"Nonnumeric WSKBIJ Test001 token at row {row}, column {column!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"Nonfinite WSKBIJ Test001 token at row {row}, column {column!r}")
    return value


@dataclass(frozen=True, slots=True)
class WSKBIJTest001Sample:
    """One row of raw channels; voltages are intentionally not calibrated."""

    source_line_number: int
    source_time_s: float
    pressure_channels_kpa: tuple[float | None, float | None, float | None, float | None]
    upstream_pressure_1_v: float | None
    upstream_pressure_2_v: float | None
    mass_flow_meter_v: float | None
    camera_trigger_v: float | None
    raw_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WSKBIJTest001Trace:
    """Pinned Test001 file metadata plus a repeatable streaming row iterator."""

    source_path: Path
    source_time_format: str
    first_sample_timestamp_token: str
    columns: tuple[str, ...]
    unit_tokens: tuple[str, ...]
    header_line_number: int
    size_bytes: int
    publisher_md5: str
    sha256: str
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue a WSKBIJ trace through read_wskbij_test001_trace")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "source_path", Path(self.source_path).resolve())

    @property
    def doi(self) -> str:
        return DOI

    @property
    def license_id(self) -> str:
        return LICENSE_ID

    def require_current(self):
        path = Path(self.source_path)
        if path.is_symlink() or path.name != FILE_NAME:
            raise ValueError("Select the regular pinned WSKBIJ Test001 member")
        if (path.stat().st_size != FILE_SIZE_BYTES
                or _digest(path, "md5") != FILE_MD5
                or _digest(path, "sha256") != FILE_SHA256):
            raise ValueError("WSKBIJ Test001 no longer matches its publisher/local receipt")
        metadata = _read_preamble(path)
        expected = (self.source_time_format, self.first_sample_timestamp_token,
                    self.columns, self.unit_tokens, self.header_line_number)
        if metadata != expected:
            raise ValueError("WSKBIJ Test001 preamble changed after reader issue")
        return self

    def iter_samples(self) -> Iterator[WSKBIJTest001Sample]:
        """Stream raw rows without allocating the full trace or resampling it."""
        identity_before = _file_identity(self.source_path)
        self.require_current()
        with self.source_path.open("r", encoding="utf-8-sig", errors="strict", newline="") as stream:
            for _ in range(self.header_line_number + 1):
                next(stream)
            for line_number, line in enumerate(stream, start=self.header_line_number + 2):
                text = line.rstrip("\r\n")
                if not text:
                    raise ValueError(f"Unexpected empty WSKBIJ data row {line_number}")
                tokens = tuple(text.split("\t"))
                schema_tokens = tokens[:-1] if len(tokens) == len(_COLUMNS) + 1 and tokens[-1] == "" else tokens
                if len(schema_tokens) != len(_COLUMNS):
                    raise ValueError(f"Wrong WSKBIJ Test001 field count at row {line_number}")
                numeric = tuple(_numeric(token, row=line_number, column=column)
                                for column, token in zip(_COLUMNS, schema_tokens, strict=True))
                time_value = numeric[0]
                if time_value is None:
                    raise ValueError(f"Missing WSKBIJ source time at row {line_number}")
                yield WSKBIJTest001Sample(
                    line_number, time_value,
                    (numeric[1], numeric[2], numeric[3], numeric[4]),
                    numeric[5], numeric[6], numeric[7], numeric[8], tokens,
                )
        # Catch replacement or mutation during the pass without hashing the
        # 208 MB source a second time. Consumers that need a final byte-level
        # receipt can call require_current() after exhausting this iterator.
        if _file_identity(self.source_path) != identity_before:
            raise ValueError("WSKBIJ Test001 changed during the streaming pass")


def read_wskbij_test001_trace(raw_root: str | Path) -> WSKBIJTest001Trace:
    """Issue a streaming reader for the selected original CC0 Test001 trace."""
    root = Path(raw_root)
    path = root / FILE_NAME
    if path.is_symlink() or not path.is_file() or path.name != FILE_NAME:
        raise ValueError("WSKBIJ Test001 must be a regular file in the selected raw-data root")
    size = path.stat().st_size
    md5 = _digest(path, "md5")
    sha = _digest(path, "sha256")
    if size != FILE_SIZE_BYTES or md5 != FILE_MD5 or sha != FILE_SHA256:
        raise ValueError("WSKBIJ Test001 does not match its publisher MD5/local SHA-256 receipt")
    time_format, timestamp, columns, units, header_line = _read_preamble(path)
    token = object()
    _PENDING.add(token)
    try:
        return WSKBIJTest001Trace(
            path, time_format, timestamp, columns, units, header_line,
            size, md5, sha, token,
        )
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = [
    "DOI", "VERSION", "LICENSE_ID", "FILE_ID", "FILE_NAME", "FILE_SIZE_BYTES",
    "FILE_MD5", "FILE_SHA256", "WSKBIJTest001Sample", "WSKBIJTest001Trace",
    "read_wskbij_test001_trace",
]
