"""Hash-pinned reader for one public ELVHYS 4.3.2 temperature trace."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path


DOI = "10.18710/HDZLJ1"
LICENSE_ID = "CC0-1.0"
README_NAME = "00_README_ELVHYS_WP_4_3_2.txt"
README_SIZE_BYTES = 13_429
README_MD5 = "401b6d98f5bd4d8e1db8fcec41cdf34d"
README_SHA256 = "88bccf0809fad9850587b02b77a63889e24c3e123016ae8c467085b633625c78"
TEMPERATURE_NAME = "ELE432KIT001TEMPL20260819.csv"
TEMPERATURE_SIZE_BYTES = 469_188
TEMPERATURE_MD5 = "b0b4abd12cdea167d6def431ab1a8c59"
TEMPERATURE_SHA256 = "eefb7372902e364e4815fd3fbdb649be3172617990cd9fda4942f1c79728be71"
_PENDING: set[object] = set()


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify(path: Path, size: int, md5: str, sha256: str, label: str) -> None:
    if (path.stat().st_size != size or _digest(path, "md5") != md5
            or _digest(path, "sha256") != sha256):
        raise ValueError(f"ELVHYS 4.3.2 {label} differs from its source receipt")


def _number(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Malformed ELVHYS 4.3.2 {label} value") from exc
    if not (number == number and abs(number) != float("inf")):
        raise ValueError(f"Non-finite ELVHYS 4.3.2 {label} value")
    return number


@dataclass(frozen=True, slots=True)
class ELVHYS432TemperatureRow:
    row_index: int
    time_min: float
    pipe_surface_temperature_k: float
    outlet_process_temperature_k: float


@dataclass(frozen=True, slots=True)
class ELVHYS432TemperatureSample:
    path: Path
    source_sha256: str
    rows: tuple[ELVHYS432TemperatureRow, ...]
    _issuer: object
    _row_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use load_elvhys432_temperature_csv for a pinned sample")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_row_binding", tuple(self.rows))

    def require_current(self):
        _verify(self.path.parent / README_NAME, README_SIZE_BYTES,
                README_MD5, README_SHA256, "README")
        _verify(self.path, TEMPERATURE_SIZE_BYTES, TEMPERATURE_MD5,
                TEMPERATURE_SHA256, "temperature file")
        if self.source_sha256 != TEMPERATURE_SHA256 or tuple(self.rows) != self._row_binding:
            raise ValueError("ELVHYS 4.3.2 temperature rows or source identity changed")
        return self


def load_elvhys432_temperature_csv(raw_root: str | Path) -> ELVHYS432TemperatureSample:
    """Read the exact Test-1 diode trace; retain raw minutes and kelvin values."""
    root = Path(raw_root)
    _verify(root / README_NAME, README_SIZE_BYTES, README_MD5, README_SHA256, "README")
    path = root / TEMPERATURE_NAME
    _verify(path, TEMPERATURE_SIZE_BYTES, TEMPERATURE_MD5,
            TEMPERATURE_SHA256, "temperature file")
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=";")
        header = next(reader, None)
        if header != ["Time (minutes)", "SD1 - Pipe Surface Temperature (K)",
                      "SD2 - Outlet Process Temperature (K)"]:
            raise ValueError("ELVHYS 4.3.2 CSV headers differ from the reviewed Test-1 schema")
        for index, row in enumerate(reader):
            if len(row) != 3:
                raise ValueError("ELVHYS 4.3.2 temperature row is not three columns")
            time_min = _number(row[0], "source time")
            surface = _number(row[1], "pipe-surface temperature")
            outlet = _number(row[2], "outlet temperature")
            if time_min < 0.0 or surface <= 0.0 or outlet <= 0.0:
                raise ValueError("ELVHYS 4.3.2 time must be nonnegative and temperatures positive kelvin")
            rows.append(ELVHYS432TemperatureRow(index, time_min, surface, outlet))
    if len(rows) < 2 or any(a.time_min >= b.time_min for a, b in zip(rows, rows[1:])):
        raise ValueError("ELVHYS 4.3.2 source time must be strictly increasing")
    token = object()
    _PENDING.add(token)
    return ELVHYS432TemperatureSample(path, TEMPERATURE_SHA256, tuple(rows), token)
