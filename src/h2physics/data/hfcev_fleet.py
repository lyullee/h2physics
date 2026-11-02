"""Pinned subset reader for the public heavy-duty H2 fleet sample.

Only one publisher-listed operation sample is parsed. The source receipt clock,
counter quality flags and raw electrical channels are retained; this module does
not reconstruct controller cadence or infer stack conditions.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


DOI = "10.5281/zenodo.23477229"
LICENSE_ID = "CC-BY-4.0"
SAMPLE_NAME = "sample_operation_V001_2025-12-23.csv"
SAMPLE_SIZE_BYTES = 2_363_398
SAMPLE_MD5 = "dea3bc817b59232931e4af6f40b7efaf"
SAMPLE_SHA256 = "709cb310102649dce0b03553f532eace131c1a455f8dadf66be7d62bcd6fdec2"
DICTIONARY_SHA256 = "e3b7c99203d2d2988078e6fab0512c970df699cc437521108fafb44df44e0e75"
README_SHA256 = "e49fb4dda0b5fe10e505c92f4c4a6b498b34b6470c321e0ac90abac6039c7787"
FIELD_BITS_SHA256 = "372b4b3285e12f51afe7d6dfebfa92659ae31eceea1f2020192ff52a4e2ee337"
_SUPPORTING = {
    "README.md": (3_599, "c4af7a5fb1f5888dd20e20a1056eb913", README_SHA256),
    "dictionary.csv": (15_472, "0a7260b0128fcb6c61d80cfd756bc610", DICTIONARY_SHA256),
    "field_bits.csv": (914, "a42517be9762f2177c8512d1bca9a9c6", FIELD_BITS_SHA256),
}
_COLUMNS = (
    "vehicle_id", "unit", "time", "time_device", "time_device_status", "segment",
    "main_state", "FcVol", "FcCur", "HyBottleP", "CoolInActTemp", "EnvTemp",
    "missing_mask", "counter_backward_mask", "correction_status", "h2_kg_restored",
    "h2_increment", "h2_attributed",
)
_PENDING: set[object] = set()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_supporting(root: Path):
    for name, (size, md5, sha256) in _SUPPORTING.items():
        supporting_path = root / name
        if (supporting_path.stat().st_size != size or _md5(supporting_path) != md5
                or _sha256(supporting_path) != sha256):
            raise ValueError(f"HFCEV source support file {name} differs from its pinned receipt")
    with (root / "field_bits.csv").open("r", encoding="utf-8-sig", newline="") as stream:
        bit_rows = {row["field"]: int(row["bit"]) for row in csv.DictReader(stream)}
    if bit_rows.get("TotH2Kg") != 26 or bit_rows.get("counter:TotH2Kg") != 1:
        raise ValueError("HFCEV H2 counter missing/backward flag assignments changed")


def _number(value: str, name: str, *, optional: bool = False):
    if value == "" and optional:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric {name} in pinned truck sample") from exc
    if not (number == number and abs(number) != float("inf")):
        raise ValueError(f"Non-finite {name} in pinned truck sample")
    return number


@dataclass(frozen=True, slots=True)
class HFCEVOperationRow:
    vehicle_id: str
    unit: int
    receipt_time: datetime
    device_time: str
    device_time_status: str
    segment: int
    main_state: float | None
    stack_voltage_v: float | None
    stack_current_a: float | None
    tank_pressure_mpa: float | None
    coolant_inlet_c: float | None
    ambient_c: float | None
    missing_mask: int
    counter_backward_mask: int
    correction_status: str
    h2_kg_restored: float | None
    h2_increment_kg: float | None
    h2_attributed: bool


@dataclass(frozen=True, slots=True)
class HFCEVOperationSample:
    path: Path
    source_sha256: str
    rows: tuple[HFCEVOperationRow, ...]
    _issuer: object
    _row_binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Use read_hfcev_operation_sample for a hash-pinned source sample")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_row_binding", tuple(self.rows))

    def require_current(self):
        _verify_supporting(self.path.parent)
        if (self.path.stat().st_size != SAMPLE_SIZE_BYTES
                or _md5(self.path) != SAMPLE_MD5
                or _sha256(self.path) != self.source_sha256
                or self.source_sha256 != SAMPLE_SHA256
                or tuple(self.rows) != self._row_binding):
            raise ValueError("HFCEV source file or parsed-row seal changed after issuance")
        return self


def read_hfcev_operation_sample(raw_root: str | Path) -> HFCEVOperationSample:
    """Read the single CC-BY sample after verifying its exact publisher checksum."""
    root = Path(raw_root)
    _verify_supporting(root)
    path = root / SAMPLE_NAME
    if path.stat().st_size != SAMPLE_SIZE_BYTES:
        raise ValueError("HFCEV sample byte size differs from the publisher record")
    if _md5(path) != SAMPLE_MD5:
        raise ValueError("HFCEV sample MD5 differs from the publisher record")
    digest = _sha256(path)
    if digest != SAMPLE_SHA256:
        raise ValueError("HFCEV sample SHA-256 differs from the reviewed source receipt")
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or any(name not in reader.fieldnames for name in _COLUMNS):
            raise ValueError("HFCEV sample is missing reviewed operation fields")
        for record in reader:
            if record.get("vehicle_id") != "V001":
                raise ValueError("Pinned sample contains an unexpected vehicle identifier")
            if record.get("h2_attributed") not in {"True", "False"}:
                raise ValueError("Malformed source hydrogen attribution flag")
            timestamp = datetime.fromisoformat(record["time"])
            rows.append(HFCEVOperationRow(
                vehicle_id=record["vehicle_id"],
                unit=int(record["unit"]),
                receipt_time=timestamp,
                device_time=record.get("time_device", ""),
                device_time_status=record.get("time_device_status", ""),
                segment=int(record["segment"]),
                main_state=_number(record.get("main_state", ""), "main state", optional=True),
                stack_voltage_v=_number(record.get("FcVol", ""), "stack voltage", optional=True),
                stack_current_a=_number(record.get("FcCur", ""), "stack current", optional=True),
                tank_pressure_mpa=_number(record.get("HyBottleP", ""), "tank pressure", optional=True),
                coolant_inlet_c=_number(record.get("CoolInActTemp", ""), "coolant inlet", optional=True),
                ambient_c=_number(record.get("EnvTemp", ""), "ambient temperature", optional=True),
                missing_mask=int(record["missing_mask"]),
                counter_backward_mask=int(record["counter_backward_mask"]),
                correction_status=record.get("correction_status", ""),
                h2_kg_restored=_number(record.get("h2_kg_restored", ""), "restored H2 counter", optional=True),
                h2_increment_kg=_number(record.get("h2_increment", ""), "H2 increment", optional=True),
                h2_attributed=(record["h2_attributed"] == "True"),
            ))
    if len(rows) < 2 or any(a.receipt_time > b.receipt_time for a, b in zip(rows, rows[1:])):
        raise ValueError("Pinned sample receipt timestamps must be ordered")
    token = object()
    _PENDING.add(token)
    return HFCEVOperationSample(path, digest, tuple(rows), token)
