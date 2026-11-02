"""Pinned parser for one public ELVHYS 4.1 vent-concentration CSV."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path


DOI = "10.18710/YGHHTR"
LICENSE_ID = "CC0-1.0"
CONCENTRATION_NAME = "ELE401HSE001CONC20251021.csv"
CONCENTRATION_SIZE_BYTES = 1_025_015
CONCENTRATION_MD5 = "65c081d72b84e6fe47617c6c603b16f3"
CONCENTRATION_SHA256 = "f2239638dc86a1d482a87f1e886951a9f5cdadbdc4594109f925c654ce9da9a6"
_SUPPORT = {
    "00_ELVHYSWP4_1 README.txt": (
        7_769, "a8649100dab484f0ce9e89a14cd75142",
        "afaaf3f55823f6d9c6ee9cb71df7e50a2d7d2755c85e03195da892f9ca0b05d1",
    ),
    "ELE401HSEMETA.csv": (
        2_291, "637bbc863c18d3110a90567e9afe3824",
        "625ecee98de0ef3ca5a6b574b67f7f09d5efe9331da9a16f3bc7b058574de798",
    ),
}
_PENDING: set[object] = set()


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _verify_support(root: Path):
    for name, (size, md5, sha256) in _SUPPORT.items():
        path = root / name
        if (path.stat().st_size != size or _digest(path, "md5") != md5
                or _digest(path, "sha256") != sha256):
            raise ValueError(f"ELVHYS 4.1 supporting source file {name} changed")


def _number(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Malformed ELVHYS 4.1 {label} reading") from exc
    if not (number == number and abs(number) != float("inf")):
        raise ValueError(f"Non-finite ELVHYS 4.1 {label} reading")
    return number


@dataclass(frozen=True, slots=True)
class ELVHYS41ConcentrationRow:
    row_index: int
    time_s: float
    oxygen_vol_percent: float
    hydrogen_vol_percent: float


@dataclass(frozen=True, slots=True)
class ELVHYS41ConcentrationSample:
    path: Path
    source_sha256: str
    rows: tuple[ELVHYS41ConcentrationRow, ...]
    _issuer: object
    _row_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use load_elvhys41_concentration_csv for a hash-pinned sample")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_row_binding", tuple(self.rows))

    def require_current(self):
        _verify_support(self.path.parent)
        if (self.path.stat().st_size != CONCENTRATION_SIZE_BYTES
                or _digest(self.path, "md5") != CONCENTRATION_MD5
                or _digest(self.path, "sha256") != self.source_sha256
                or self.source_sha256 != CONCENTRATION_SHA256
                or tuple(self.rows) != self._row_binding):
            raise ValueError("ELVHYS 4.1 concentration payload or issued rows changed")
        return self


def load_elvhys41_concentration_csv(raw_root: str | Path) -> ELVHYS41ConcentrationSample:
    """Read the exact publisher test-1 concentration file, retaining invalid values raw."""
    root = Path(raw_root)
    _verify_support(root)
    path = root / CONCENTRATION_NAME
    if path.stat().st_size != CONCENTRATION_SIZE_BYTES:
        raise ValueError("ELVHYS 4.1 concentration file size differs from its publisher listing")
    if _digest(path, "md5") != CONCENTRATION_MD5:
        raise ValueError("ELVHYS 4.1 concentration file MD5 differs from its publisher listing")
    digest = _digest(path, "sha256")
    if digest != CONCENTRATION_SHA256:
        raise ValueError("ELVHYS 4.1 concentration file SHA-256 differs from its source receipt")
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if header is None or tuple(header[:3]) != ("Time Interval", "O2 vol%", "H2 vol%"):
            raise ValueError("ELVHYS 4.1 concentration CSV no longer has its reviewed channel headers")
        for row_index, row in enumerate(reader):
            if len(row) < 3:
                raise ValueError("ELVHYS 4.1 concentration row is truncated")
            rows.append(ELVHYS41ConcentrationRow(
                row_index=row_index,
                time_s=_number(row[0], "time"),
                oxygen_vol_percent=_number(row[1], "oxygen concentration"),
                hydrogen_vol_percent=_number(row[2], "hydrogen concentration"),
            ))
    if (len(rows) < 2 or any(a.time_s >= b.time_s for a, b in zip(rows, rows[1:]))):
        raise ValueError("ELVHYS 4.1 sample needs strictly increasing source times")
    token = object()
    _PENDING.add(token)
    return ELVHYS41ConcentrationSample(path, digest, tuple(rows), token)
