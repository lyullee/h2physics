"""Qualified AB2 workbook blocks with unresolved instrument bases preserved.

Profile source: https://doi.org/10.17632/8km9z62tct.1 (CC BY 4.0).
Workbook formula caches are observations of the export, never executed code.
"""

import math
import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from pathlib import Path

import numpy as np

from ..core import Origin
from ..observations import ObservationTable, Variable
from .pressure_peaking import file_sha256

PROFILE_ID = "ab2-tank-v1-profile-1"
HEADERS = ("No", "Date", "Time", "Flow", "Pressure", "TC1", "TC2", "TC3", "TC4",
           "TC5", "Volume", "Total Volume")
FLOW_BASIS = "MFC reference-volume output; reference pressure/temperature unresolved"
PRESSURE_BASIS = "exported pressure; unit and absolute/gauge basis unresolved"
_PENDING_BLOCK_ISSUERS: set[object] = set()


def _issue_block(**values):
    token = object()
    _PENDING_BLOCK_ISSUERS.add(token)
    try:
        return HydrideTankBlock(**values, _issuer_token=token)
    except Exception:
        _PENDING_BLOCK_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class HydrideTankBlock:
    observations: ObservationTable
    source_rows: tuple[int, ...]
    raw_cells: tuple[tuple[object, ...], ...]
    _issuer_token: object = dataclass_field(default=None, repr=False, compare=False)
    _seal: str = dataclass_field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_BLOCK_ISSUERS:
            raise ValueError("Hydride tank blocks must be issued by the qualified workbook reader")
        _PENDING_BLOCK_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        object.__setattr__(self, "source_rows", tuple(self.source_rows))
        object.__setattr__(self, "raw_cells", tuple(tuple(row) for row in self.raw_cells))
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self):
        return hashlib.sha256(repr((self.observations.content_sha256, self.source_rows,
                                    self.raw_cells)).encode("utf-8")).hexdigest()

    def require_current(self):
        if self._content_fingerprint() != self._seal:
            raise ValueError("Hydride tank source block changed after reader issuance")
        return self


@dataclass(frozen=True, slots=True)
class WorkbookSummaryCell:
    coordinate: str
    label: str
    cached_value: object
    formula: str | None


def hydride_summary_cells(path: str | Path, sheet_name: str) -> tuple[WorkbookSummaryCell, ...]:
    """Retain the four source summary cells and their literal formulas without execution.

    These summaries may select an intermediate row rather than the final sample.
    They are derived export fields, not additional independent measurements.
    """
    from openpyxl import load_workbook

    cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    formulas = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        rows = list(cached[sheet_name].iter_rows(min_row=1, max_row=2, max_col=17,
                                               values_only=True))
        expressions = next(formulas[sheet_name].iter_rows(min_row=2, max_row=2, max_col=17,
                                                         values_only=True))
        return tuple(WorkbookSummaryCell(f"{chr(65+i)}2", str(rows[0][i]), rows[1][i],
                     expressions[i] if isinstance(expressions[i], str)
                     and expressions[i].startswith("=") else None)
                     for i in range(13, 17) if rows[0][i] is not None)
    finally:
        cached.close()
        formulas.close()


def _numeric(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return math.nan


def iter_hydride_tank_blocks(path: str | Path, sheet_name: str, *, source_id: str,
                            experiment_id: str, clock_id: str, datetime_origin: datetime,
                            expected_sha256: str | None = None, block_rows: int = 10_000,
                            maximum_bytes: int = 64_000_000) -> Iterator[HydrideTankBlock]:
    """Stream all source rows; missing clocks/values stay masked at their original row.

    Flow and volume use the reported litre scale only. No mass conversion, pressure
    conversion, clock repair, summary recomputation or sensor averaging is implied.
    Consume the iterator completely to obtain its final source-stability check.
    Raw cells include Date, original Time and the first twelve export columns.
    """
    from openpyxl import load_workbook

    if not all(isinstance(x, str) and x.strip() for x in (source_id, experiment_id, clock_id)):
        raise ValueError("Declare source, experiment and local clock identities")
    if not isinstance(datetime_origin, datetime):
        raise ValueError("Declare the source datetime origin explicitly")
    for name, value in (("block_rows", block_rows), ("maximum_bytes", maximum_bytes)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    path = Path(path)
    if path.stat().st_size > maximum_bytes:
        raise ValueError("Workbook exceeds the declared compressed byte budget")
    digest = file_sha256(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Workbook SHA-256 differs from the recorded bytes")
    variables = (
        Variable("datetime_elapsed", "time", "s", clock_id),
        Variable("source_counter", "source_counter", "1"),
        Variable("exported_elapsed", "time", "s", "source formula cache; not clock authority"),
        Variable("mfc_reference_volume_flow", "reference_volume_flow", "m3_ref/s", FLOW_BASIS),
        Variable("instrument_pressure", "reported_pressure", "unresolved", PRESSURE_BASIS),
        *(Variable(f"shell_{i}", "temperature", "K", f"external shell thermocouple TC{i}")
          for i in range(1, 6)),
        Variable("exported_increment_volume", "reference_volume", "m3_ref", FLOW_BASIS),
        Variable("exported_total_volume", "reference_volume", "m3_ref", FLOW_BASIS))
    origins = (Origin.RECONSTRUCTED,) * 3 + (Origin.MEASURED,) * 7 + (
        Origin.RECONSTRUCTED,) * 2
    context = (("profile", PROFILE_ID), ("file_sha256", digest), ("worksheet", sheet_name),
               ("datetime_origin", datetime_origin.isoformat()), ("clock_id", clock_id),
               ("temperature_location", "shell, not bed"),
               ("flow_direction", "unsigned instrument output; run direction not inferred"))
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        sheet = workbook[sheet_name]
        header = next(sheet.iter_rows(min_row=1, max_row=1, max_col=12, values_only=True))
        if header != HEADERS:
            raise ValueError("Unreviewed AB2 worksheet header/schema")
        values, raw, source_rows = [], [], []

        def block():
            data = np.array(values, dtype=float)
            valid = np.isfinite(data)
            valid[:, 5:10] &= data[:, 5:10] > 0
            table = ObservationTable(data, variables, valid,
                tuple(f"{source_id}|{digest}|{experiment_id}|{sheet_name}|row-{row}"
                      for row in source_rows),
                (experiment_id,) * len(source_rows), origins, source_id, context)
            return _issue_block(observations=table, source_rows=tuple(source_rows), raw_cells=tuple(raw))

        for number, cells in enumerate(sheet.iter_rows(min_row=2, max_col=12,
                                                       values_only=True), start=2):
            elapsed = math.nan
            if isinstance(cells[1], datetime):
                elapsed = (cells[1] - datetime_origin).total_seconds()
            numeric = [_numeric(cells[i]) for i in (0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)]
            numeric[2] *= 1e-3 / 60
            numeric[4:9] = [value + 273.15 for value in numeric[4:9]]
            numeric[9:] = [value * 1e-3 for value in numeric[9:]]
            values.append([elapsed, *numeric])
            raw.append(cells)
            source_rows.append(number)
            if len(values) == block_rows:
                yield block()
                values, raw, source_rows = [], [], []
        if values:
            yield block()
    finally:
        workbook.close()
    if file_sha256(path) != digest:
        raise ValueError("Source workbook changed during decoding")
