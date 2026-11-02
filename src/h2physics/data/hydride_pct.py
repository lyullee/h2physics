"""Checksum-bound access to simulated metal-hydride PCT workbook cells.

The reader preserves workbook cells and formula text. It does not resolve the
reported pressure or loading bases and does not qualify a hydride equilibrium
model.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from weakref import WeakKeyDictionary

DATASET_DOI = "10.17632/trpnk55pmz.1"
DATASET_VERSION = "1"
LICENSE_ID = "CC-BY-4.0"


@dataclass(frozen=True, slots=True)
class HydridePCTSourceReceipt:
    """Caller-declared byte receipt for one PCT workbook."""

    file_name: str
    material_label: str
    size_bytes: int
    sha256: str
    license_id: str = LICENSE_ID
    dataset_version: str = DATASET_VERSION
    sheet_dimensions: tuple[tuple[str, int, int], ...] | None = None

    def __post_init__(self):
        if not isinstance(self.file_name, str) or not self.file_name.endswith(".xlsx"):
            raise ValueError("Declare one exact .xlsx source file name")
        if not isinstance(self.material_label, str) or not self.material_label.strip():
            raise ValueError("Retain a source-specific material label")
        if (isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int)
                or self.size_bytes < 1):
            raise ValueError("Source byte count must be a positive integer")
        if (not isinstance(self.sha256, str) or len(self.sha256) != 64
                or any(char not in "0123456789abcdef" for char in self.sha256)):
            raise ValueError("Source SHA-256 must be 64 lowercase hexadecimal characters")
        if self.license_id != LICENSE_ID:
            raise ValueError("This reader is restricted to the reviewed CC BY 4.0 dataset")
        if self.dataset_version != DATASET_VERSION:
            raise ValueError("This reader is pinned to the reviewed dataset version 1")
        if self.sheet_dimensions is not None:
            dimensions = tuple(self.sheet_dimensions)
            if (len(dimensions) != 2 or tuple(item[0] for item in dimensions) != ("ABS", "DES")
                    or any(len(item) != 3 or any(
                        isinstance(value, bool) or not isinstance(value, int) or value < 1
                        for value in item[1:]
                    ) for item in dimensions)):
                raise ValueError("Reviewed sheet dimensions must declare ABS and DES row/column sizes")
            object.__setattr__(self, "sheet_dimensions", dimensions)


_RECEIPTS = (
    HydridePCTSourceReceipt(
        "V75Ti10Zr7.5Ni7.5 Simulated Isotherm data.xlsx", "V75Ti10Zr7.5Ni7.5",
        1_833_482, "75d6973a7374dabaa6acaed821d2f396b89953ee577c09a5e1ce66294e959260",
        sheet_dimensions=(("ABS", 10_005, 12), ("DES", 10_005, 12)),
    ),
    HydridePCTSourceReceipt(
        "Ti1.15Fe Simulated Isotherm data.xlsx", "Ti1.15Fe", 1_941_572,
        "cbf16a17571e84a206069bb38e4ceace1f20530e1369330d0fbfa7b28ba95dfc",
        sheet_dimensions=(("ABS", 10_004, 12), ("DES", 10_004, 12)),
    ),
    HydridePCTSourceReceipt(
        "La0.8Ce0.2Ni5 Simulated Isotherm data.xlsx", "La0.8Ce0.2Ni5", 2_221_176,
        "81492a7fe6b41253801ecb06ed371e7cde04466583b99297307cc7681ea992bd",
        sheet_dimensions=(("ABS", 10_004, 14), ("DES", 10_004, 15)),
    ),
    HydridePCTSourceReceipt(
        "LaNi4.9Sn.01 Simulated Isotherm data.xlsx", "LaNi4.9Sn.01", 2_571_096,
        "cb34db0ab43a6ad430c4a1f931f5c390d609c14a1c80e722a4ce1549f78129a0",
        sheet_dimensions=(("ABS", 10_004, 16), ("DES", 10_004, 16)),
    ),
    HydridePCTSourceReceipt(
        "LaNi4.8Sn0.2 Simulated Isotherm data.xlsx", "LaNi4.8Sn0.2", 4_571_413,
        "8e06124e7db6d6ff4af0b46d717bfc3ffc4168434d211a217b254f82ca9a489c",
        sheet_dimensions=(("ABS", 10_004, 26), ("DES", 10_004, 26)),
    ),
)
_RECEIPTS_BY_NAME = {receipt.file_name: receipt for receipt in _RECEIPTS}


@dataclass(frozen=True, slots=True)
class HydridePCTSheetInfo:
    """Workbook sheet dimensions and exact initial cell values."""

    name: str
    max_row: int
    max_column: int
    initial_rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True, slots=True)
class HydridePCTRow:
    """One worksheet row retaining one-based Excel row identity and raw values."""

    row_number: int
    values: tuple[object, ...]


_ISSUED: WeakKeyDictionary = WeakKeyDictionary()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class HydridePCTWorkbook:
    """Reader-issued immutable view of one source workbook."""

    source_path: Path
    receipt: HydridePCTSourceReceipt
    source_sha256: str
    sheet_infos: tuple[HydridePCTSheetInfo, ...]
    _issuer_token: object = field(repr=False, compare=False)

    def __post_init__(self):
        if type(self.receipt) is not HydridePCTSourceReceipt:
            raise TypeError("Retain a typed source receipt")
        path = Path(self.source_path)
        if not path.is_absolute() or path.name != self.receipt.file_name:
            raise ValueError("Retain the resolved path of the exact receipted workbook")
        if not isinstance(self.sheet_infos, tuple) or len(self.sheet_infos) != 2:
            raise ValueError("Retain the reviewed ABS/DES worksheet inventory")
        if tuple(sheet.name for sheet in self.sheet_infos) != ("ABS", "DES"):
            raise ValueError("Hydride PCT workbooks must contain ABS and DES sheets in that order")
        object.__setattr__(self, "source_path", path)

    @property
    def material_label(self) -> str:
        return self.receipt.material_label

    def require_current(self) -> HydridePCTWorkbook:
        sealed = _ISSUED.get(self)
        if sealed is None or sealed != _fingerprint(self):
            raise ValueError("Workbook snapshot was not issued by the verified PCT reader or was changed")
        try:
            raw = self.source_path.read_bytes()
        except OSError as exc:
            raise ValueError("Receipted PCT workbook is no longer available") from exc
        if len(raw) != self.receipt.size_bytes:
            raise ValueError("PCT workbook byte count changed after reading")
        if hashlib.sha256(raw).hexdigest() != self.receipt.sha256:
            raise ValueError("PCT workbook SHA-256 changed after reading")
        if _inspect_workbook(raw, self.receipt) != self.sheet_infos:
            raise ValueError("PCT workbook worksheet inventory changed after reading")
        return self

    def iter_rows(self, sheet_name: str) -> Iterator[HydridePCTRow]:
        """Stream raw formula-preserving cell values for one selected sheet."""
        self.require_current()
        if sheet_name not in {sheet.name for sheet in self.sheet_infos}:
            raise KeyError(f"Unknown workbook sheet: {sheet_name}")
        from openpyxl import load_workbook

        workbook = load_workbook(self.source_path, read_only=True, data_only=False, keep_links=False)
        try:
            worksheet = workbook[sheet_name]
            for row_number, cells in enumerate(worksheet.iter_rows(values_only=False), 1):
                yield HydridePCTRow(row_number, tuple(cell.value for cell in cells))
        finally:
            workbook.close()
            self.require_current()


def _fingerprint(value: HydridePCTWorkbook) -> tuple:
    return (id(value._issuer_token), str(value.source_path), value.receipt,
            value.source_sha256, value.sheet_infos)


def _inspect_workbook(raw: bytes, receipt: HydridePCTSourceReceipt) -> tuple[HydridePCTSheetInfo, ...]:
    from io import BytesIO

    from openpyxl import load_workbook

    try:
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    except Exception as exc:
        raise ValueError("Receipted PCT source is not a readable .xlsx workbook") from exc
    try:
        if tuple(workbook.sheetnames) != ("ABS", "DES"):
            raise ValueError("PCT workbook sheet set differs from the reviewed ABS/DES schema")
        infos = []
        for worksheet in workbook.worksheets:
            if worksheet.max_row < 3 or worksheet.max_column < 1:
                raise ValueError("PCT workbook sheet is shorter than the reviewed header region")
            initial_rows = tuple(
                tuple(row)
                for row in worksheet.iter_rows(min_row=1, max_row=3, values_only=True)
            )
            infos.append(HydridePCTSheetInfo(
                worksheet.title, worksheet.max_row, worksheet.max_column, initial_rows,
            ))
        result = tuple(infos)
    finally:
        workbook.close()
    if receipt.sheet_dimensions is not None:
        observed = tuple((item.name, item.max_row, item.max_column) for item in result)
        if observed != receipt.sheet_dimensions:
            raise ValueError("PCT worksheet dimensions differ from the reviewed source receipt")
    return result


def load_hydride_pct_workbook(
    path: str | Path,
    *,
    receipt: HydridePCTSourceReceipt | None = None,
) -> HydridePCTWorkbook:
    """Open one exact source workbook while preserving raw cells/formulas.

    The known v1 receipts are selected by the exact source filename. A caller
    may provide a separate typed receipt for a compatible CC BY 4.0 workbook.
    Pressure and loading units/bases are deliberately left uninterpreted.
    """
    source_path = Path(path).resolve(strict=True)
    if receipt is None:
        try:
            receipt = _RECEIPTS_BY_NAME[source_path.name]
        except KeyError as exc:
            raise ValueError("Supply an explicit reviewed receipt for this workbook name") from exc
    if type(receipt) is not HydridePCTSourceReceipt or source_path.name != receipt.file_name:
        raise ValueError("Workbook name must match the typed source receipt")
    raw = source_path.read_bytes()
    if len(raw) != receipt.size_bytes:
        raise ValueError("PCT workbook byte count differs from the source receipt")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != receipt.sha256:
        raise ValueError("PCT workbook SHA-256 differs from the source receipt")
    infos = _inspect_workbook(raw, receipt)
    token = object()
    result = HydridePCTWorkbook(source_path, receipt, digest, infos, token)
    _ISSUED[result] = _fingerprint(result)
    return result


__all__ = [
    "HydridePCTSourceReceipt",
    "HydridePCTSheetInfo",
    "HydridePCTRow",
    "HydridePCTWorkbook",
    "load_hydride_pct_workbook",
]
