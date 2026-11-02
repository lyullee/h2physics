"""Verified single-member view of the PEM ripple IV archive."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import math
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from weakref import WeakKeyDictionary

import numpy as np

from ..core import immutable_array

PARENT_ARCHIVE_SHA256 = "47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab"
MEMBER_PATH = "PEM_ripple_degradation_data/IV_curves/PEM1/PEM1_Initial.csv"
MEMBER_SIZE_BYTES = 915_460
MEMBER_SHA256 = "a054dad7a1d5ce1f2154b60a79a1adea4f84d5ec00e23c12ca72639ffcddcf0d"
MEMBER_ROW_COUNT = 20_040
MEMBER_HEADER = ("current_A", "voltage_V", "step_index")
GZIP_SIZE_BYTES = 100_159
GZIP_SHA256 = "46e2e7e08cb5d7eb371df30f7b3b6ee221f9c1e5ae46cd40c544b3c21bccfa90"
_MEMBER_FILE_NAME = "PEM1_Initial.csv.gz"
_ISSUED: WeakKeyDictionary = WeakKeyDictionary()


def _read_payload(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.name != _MEMBER_FILE_NAME:
        raise ValueError("Supply the exact non-symlink PEM1 Initial CSV gzip member")
    compressed = path.read_bytes()
    if len(compressed) != GZIP_SIZE_BYTES or hashlib.sha256(compressed).hexdigest() != GZIP_SHA256:
        raise ValueError("Gzip member differs from the reviewed size/SHA-256 receipt")
    try:
        raw = gzip.decompress(compressed)
    except (OSError, EOFError, zlib.error) as exc:
        raise ValueError("PEM IV member is not a complete valid gzip stream") from exc
    if len(raw) != MEMBER_SIZE_BYTES or hashlib.sha256(raw).hexdigest() != MEMBER_SHA256:
        raise ValueError("Inflated member differs from the reviewed member size/SHA-256 receipt")
    return raw


def _parse_rows(raw: bytes) -> tuple[list[float], list[float], list[int]]:
    try:
        text = io.StringIO(raw.decode("utf-8-sig"), newline="")
        reader = csv.DictReader(text, strict=True)
        if tuple(reader.fieldnames or ()) != MEMBER_HEADER:
            raise ValueError("PEM IV member header differs from the reviewed CSV schema")
        currents, voltages, steps = [], [], []
        for row in reader:
            if None in row or any(value is None or value == "" for value in row.values()):
                raise ValueError(f"Ragged or empty PEM IV row {reader.line_num}")
            current = float(row["current_A"])
            voltage = float(row["voltage_V"])
            step_token = row["step_index"]
            step = int(step_token)
            if (not math.isfinite(current) or not math.isfinite(voltage) or step < 0
                    or step_token.strip() != str(step)):
                raise ValueError(f"Invalid numeric token in PEM IV row {reader.line_num}")
            currents.append(current)
            voltages.append(voltage)
            steps.append(step)
    except (csv.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("PEM IV member does not match the reviewed row schema") from exc
    if len(currents) != MEMBER_ROW_COUNT:
        raise ValueError(f"PEM IV member row count is {len(currents)}, expected {MEMBER_ROW_COUNT}")
    return currents, voltages, steps


def _fingerprint(curve: PemRippleIVMemberCurve) -> tuple:
    return (
        str(curve.source_path), curve.parent_archive_sha256, curve.source_member,
        curve.source_member_sha256, curve.compressed_sha256, curve.compressed_size_bytes,
        curve.current_a.tobytes(), curve.voltage_v.tobytes(), curve.step_index.tobytes(),
    )


@dataclass(frozen=True, slots=True, weakref_slot=True)
class PemRippleIVMemberCurve:
    """Immutable PEM1 Initial curve read from its source-bound gzip member."""

    source_path: Path
    cell_id: str
    cycle: str
    current_a: np.ndarray = field(repr=False, compare=False)
    voltage_v: np.ndarray = field(repr=False, compare=False)
    step_index: np.ndarray = field(repr=False, compare=False)
    source_member: str
    source_member_sha256: str
    parent_archive_sha256: str
    compressed_sha256: str
    compressed_size_bytes: int
    _issuer: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is None:
            raise TypeError("Issue compressed member curves only through load_pem_ripple_iv_member")
        path = Path(self.source_path)
        current = immutable_array(self.current_a, dtype=float, name="current_a")
        voltage = immutable_array(self.voltage_v, dtype=float, name="voltage_v")
        steps = immutable_array(self.step_index, dtype=np.int64, name="step_index")
        if (path.name != _MEMBER_FILE_NAME or self.cell_id != "PEM1" or self.cycle != "Initial"
                or current.ndim != 1 or len(current) != MEMBER_ROW_COUNT
                or voltage.shape != current.shape or steps.shape != current.shape):
            raise ValueError("Compressed source curve identity or vector shape differs from its receipt")
        object.__setattr__(self, "source_path", path)
        object.__setattr__(self, "current_a", current)
        object.__setattr__(self, "voltage_v", voltage)
        object.__setattr__(self, "step_index", steps)

    @property
    def source_archive_sha256(self) -> str:
        return self.parent_archive_sha256

    def require_current(self) -> PemRippleIVMemberCurve:
        sealed = _ISSUED.get(self)
        if sealed is None or sealed != _fingerprint(self):
            raise ValueError("Curve was not issued by the verified member reader or its arrays changed")
        if (self.parent_archive_sha256 != PARENT_ARCHIVE_SHA256
                or self.source_member != MEMBER_PATH
                or self.source_member_sha256 != MEMBER_SHA256
                or self.compressed_sha256 != GZIP_SHA256
                or self.compressed_size_bytes != GZIP_SIZE_BYTES):
            raise ValueError("PEM member source lineage differs from its pinned receipt")
        raw = _read_payload(self.source_path)
        currents, voltages, steps = _parse_rows(raw)
        if (not np.array_equal(self.current_a, currents)
                or not np.array_equal(self.voltage_v, voltages)
                or not np.array_equal(self.step_index, steps)):
            raise ValueError("Curve arrays no longer match their verified source member")
        return self

    def iter_source_rows(self):
        """Iterate the original CSV tokens after verifying both gzip and member digests."""
        self.require_current()
        raw = _read_payload(self.source_path)
        text = io.StringIO(raw.decode("utf-8-sig"), newline="")
        rows = csv.reader(text, strict=True)
        if tuple(next(rows, ())) != MEMBER_HEADER:
            raise ValueError("PEM IV member header differs from the reviewed CSV schema")
        for values in rows:
            if len(values) != len(MEMBER_HEADER):
                raise ValueError("PEM IV member row width differs from the reviewed schema")
            yield tuple(values)


def load_pem_ripple_iv_member(path: str | Path) -> PemRippleIVMemberCurve:
    """Read the exact gzip'd PEM1 Initial CSV member without the parent ZIP.

    The reviewed parent archive digest, member path/digest, CSV header, row count,
    and deterministic gzip receipt are pinned in this module. The Hangang reader
    checks the transferred member against those receipts; it does not claim to
    possess or re-hash the complete parent ZIP.
    """
    unresolved = Path(path)
    if unresolved.is_symlink():
        raise ValueError("PEM IV gzip member must not be reached through a symbolic link")
    source = unresolved.resolve(strict=True)
    raw = _read_payload(source)
    currents, voltages, steps = _parse_rows(raw)
    compressed = source.read_bytes()
    result = PemRippleIVMemberCurve(
        source, "PEM1", "Initial", np.asarray(currents), np.asarray(voltages),
        np.asarray(steps), MEMBER_PATH, MEMBER_SHA256, PARENT_ARCHIVE_SHA256,
        hashlib.sha256(compressed).hexdigest(), len(compressed), object(),
    )
    _ISSUED[result] = _fingerprint(result)
    return result


__all__ = [
    "PARENT_ARCHIVE_SHA256",
    "MEMBER_PATH",
    "MEMBER_SIZE_BYTES",
    "MEMBER_SHA256",
    "MEMBER_ROW_COUNT",
    "GZIP_SIZE_BYTES",
    "GZIP_SHA256",
    "PemRippleIVMemberCurve",
    "load_pem_ripple_iv_member",
]

