"""Read the small RODARE pressurized-alkaline experiment condition index.

The file is a condition lookup only. It contains no voltage, bubble, gas-fraction,
or time-series measurements and cannot calibrate an electrochemical loss model.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from weakref import WeakKeyDictionary

DOI = "10.14278/rodare.4547"
VERSION = 1
LICENSE_ID = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
SOURCE_FILENAME = "Summary.csv"
SOURCE_SIZE_BYTES = 1499
SOURCE_MD5 = "0b500cf14501034033e5471de46341b1"
SOURCE_SHA256 = "24cf3cd688215f99cc28fc4c1c0f10899caa1a5fba03b22c4819c0525ede181f"
_HEADER = ("", "ID", "Electrode", "Pressure in bar", "Current Density in mA/cm²")
_ELECTRODES = frozenset({"LS_30", "LS_40", "LS_60", "LS_100", "Ref"})
_PRESSURES_BAR_ABS = frozenset({1.0, 2.0, 4.0, 6.0})
_CURRENT_DENSITIES_MA_CM2 = frozenset({-25.0, -50.0, -100.0})
_ISSUED: WeakKeyDictionary = WeakKeyDictionary()


class _IssuerSeal:
    """Private reader-issued key used to reject fabricated receipt wrappers."""


@dataclass(frozen=True, slots=True)
class RODAREAlkalineBubbleCondition:
    """One publisher-listed operating condition, with its native identifiers."""

    source_row_index: int
    measurement_id: str
    electrode_id: str
    pressure_bar_abs: float
    current_density_mA_cm2: float
    raw_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True, weakref_slot=True)
class RODAREAlkalineBubbleIndex:
    """Immutable source-bound condition index; not a measured response table."""

    conditions: tuple[RODAREAlkalineBubbleCondition, ...]
    raw_bytes: bytes
    source_path: Path
    source_size_bytes: int
    publisher_md5: str
    source_sha256: str
    _issuer_token: _IssuerSeal = field(repr=False, compare=False)

    def require_current(self) -> RODAREAlkalineBubbleIndex:
        receipt = _ISSUED.get(self._issuer_token)
        actual = (self.source_path, self.source_size_bytes,
                  self.publisher_md5, self.source_sha256)
        if receipt is None or receipt != actual:
            raise ValueError("index was not issued by the verified RODARE condition reader")
        raw = self.source_path.read_bytes()
        if len(raw) != self.source_size_bytes:
            raise ValueError("current RODARE condition index byte count changed")
        if hashlib.md5(raw).hexdigest() != self.publisher_md5:
            raise ValueError("current RODARE condition index publisher MD5 changed")
        if hashlib.sha256(raw).hexdigest() != self.source_sha256 or raw != self.raw_bytes:
            raise ValueError("current RODARE condition index SHA-256 or bytes changed")
        if _parse_conditions(raw) != self.conditions:
            raise ValueError("condition projection differs from a fresh source parse")
        return self


def _parse_conditions(raw: bytes) -> tuple[RODAREAlkalineBubbleCondition, ...]:
    try:
        text = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("RODARE condition index must be UTF-8 text") from exc
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    rows = tuple(tuple(row) for row in reader)
    if not rows or rows[0] != _HEADER:
        raise ValueError("RODARE condition-index header differs from the reviewed source schema")
    conditions = []
    for expected_index, row in enumerate(rows[1:]):
        if len(row) != len(_HEADER):
            raise ValueError("RODARE condition-index row width differs from its header")
        try:
            index = int(row[0])
            pressure = float(row[3])
            current_density = float(row[4])
        except ValueError as exc:
            raise ValueError("RODARE condition-index row has an invalid numeric token") from exc
        if index != expected_index:
            raise ValueError("publisher row index is missing, duplicated, or reordered")
        if not row[1].strip() or row[2] not in _ELECTRODES:
            raise ValueError("condition row has an unknown measurement/electrode identifier")
        if pressure not in _PRESSURES_BAR_ABS or current_density not in _CURRENT_DENSITIES_MA_CM2:
            raise ValueError("condition row lies outside the reviewed publisher condition grid")
        conditions.append(RODAREAlkalineBubbleCondition(
            source_row_index=index,
            measurement_id=row[1],
            electrode_id=row[2],
            pressure_bar_abs=pressure,
            current_density_mA_cm2=current_density,
            raw_fields=row,
        ))
    expected_grid = {
        (electrode, pressure, current)
        for electrode in _ELECTRODES
        for pressure in _PRESSURES_BAR_ABS
        for current in _CURRENT_DENSITIES_MA_CM2
    }
    observed_grid = {
        (item.electrode_id, item.pressure_bar_abs, item.current_density_mA_cm2)
        for item in conditions
    }
    if len(conditions) != 60 or len({item.measurement_id for item in conditions}) != 60:
        raise ValueError("reviewed source index must contain 60 unique condition rows")
    if observed_grid != expected_grid:
        raise ValueError("source rows do not cover the reviewed electrode/pressure/current grid")
    return tuple(conditions)


def load_rodare_alkaline_bubble_index(
    path: str | Path,
    *,
    expected_size_bytes: int = SOURCE_SIZE_BYTES,
    expected_publisher_md5: str = SOURCE_MD5,
    expected_sha256: str = SOURCE_SHA256,
) -> RODAREAlkalineBubbleIndex:
    """Load only exact bytes admitted by the version-1 source receipt.

    The checksum defaults pin the reviewed public file. Callers can supply a
    separately reviewed receipt for a future version; the schema/grid checks
    still apply. Pressure is the record-declared absolute cell pressure. Current
    density is retained with the publisher's negative cathodic sign convention.
    """
    source_path = Path(path).resolve(strict=True)
    if source_path.name != SOURCE_FILENAME:
        raise ValueError(f"expected the exact source filename {SOURCE_FILENAME}")
    if (isinstance(expected_size_bytes, bool) or not isinstance(expected_size_bytes, int)
            or expected_size_bytes < 1):
        raise ValueError("expected_size_bytes must be a positive integer")
    if (not isinstance(expected_publisher_md5, str)
            or re.fullmatch(r"[0-9a-f]{32}", expected_publisher_md5) is None):
        raise ValueError("expected_publisher_md5 must be a lowercase hexadecimal MD5")
    if (not isinstance(expected_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None):
        raise ValueError("expected_sha256 must be a lowercase hexadecimal SHA-256")
    raw = source_path.read_bytes()
    if len(raw) != expected_size_bytes:
        raise ValueError("RODARE condition index byte count differs from the declared receipt")
    md5 = hashlib.md5(raw).hexdigest()
    digest = hashlib.sha256(raw).hexdigest()
    if md5 != expected_publisher_md5:
        raise ValueError("RODARE condition index publisher MD5 differs from the declared receipt")
    if digest != expected_sha256:
        raise ValueError("RODARE condition index SHA-256 differs from the declared receipt")
    conditions = _parse_conditions(raw)
    token = _IssuerSeal()
    result = RODAREAlkalineBubbleIndex(
        conditions, raw, source_path, len(raw), md5, digest, token,
    )
    _ISSUED[token] = (source_path, len(raw), md5, digest)
    return result

