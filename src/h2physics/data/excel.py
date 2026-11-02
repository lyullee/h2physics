"""Explicit worksheet observations; formulas are read from cached values only."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Literal

import numpy as np

from ..core import Origin, TimeSeries
from ..units import convert_to_si
from .loaders import SI_UNITS, Column, LoadedSeries, LoadReport


@dataclass(frozen=True, slots=True)
class ExcelClock:
    column: str
    kind: Literal["numeric", "datetime"]
    unit: str | None = None
    datetime_origin: datetime | None = None

    def __post_init__(self):
        if self.kind == "numeric":
            if self.unit is None or self.datetime_origin is not None:
                raise ValueError("A numeric clock needs a unit and no datetime origin")
        elif self.kind == "datetime":
            if self.unit is not None or self.datetime_origin is None:
                raise ValueError("A datetime clock needs an explicit datetime origin")
        else:
            raise ValueError("Unsupported worksheet clock kind")

    def seconds(self, value):
        if self.kind == "numeric":
            return float(convert_to_si(float(value), quantity="time", unit=self.unit))
        if not isinstance(value, datetime):
            raise ValueError("Expected a datetime cell; Excel serial floats are not inferred")
        return (value - self.datetime_origin).total_seconds()


def load_excel_sheet(path: Path | BinaryIO, sheet_name: str, *, columns: tuple[Column, ...],
                     clock: ExcelClock, clock_id: str, origin: Origin, source_id: str,
                     header_row: int = 1, clock_header_row: int | None = None,
                     data_start_row: int | None = None,
                     omit_missing_time: bool = False) -> LoadedSeries:
    """Read declared numeric columns into SI; retain invalid measurements as masked NaN.

    This reader does not execute formulas, macros or links. A missing formula cache
    is a missing value. Duplicate/backward clocks are rejected, with no averaging,
    sorting or deduplication. Undeclared worksheet summary columns are not read.
    """
    from openpyxl import load_workbook

    if not columns or any(c.quantity not in SI_UNITS for c in columns):
        raise ValueError("Declare supported observation quantities")
    if header_row < 1 or (clock_header_row is not None and clock_header_row < 1):
        raise ValueError("Worksheet rows are one-based")
    clock_header_row = header_row if clock_header_row is None else clock_header_row
    data_start_row = max(header_row, clock_header_row) + 1 if data_start_row is None else data_start_row
    if data_start_row <= max(header_row, clock_header_row):
        raise ValueError("Data must begin after both declared header rows")
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    rows, times, omitted, source_rows = [], [], 0, 0
    try:
        sheet = workbook[sheet_name]
        header = next(sheet.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
        clock_header = next(sheet.iter_rows(min_row=clock_header_row, max_row=clock_header_row,
                                            values_only=True))
        required = [(clock.column, clock_header), *((c.source, header) for c in columns)]
        positions = {}
        for name, selected_header in required:
            matches = [i for i, value in enumerate(selected_header) if value == name]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one worksheet column named {name!r}")
            positions[name] = matches[0]
        for row in sheet.iter_rows(min_row=data_start_row, max_col=max(positions.values())+1,
                                   values_only=True):
            source_rows += 1
            time = row[positions[clock.column]]
            if time is None:
                if not omit_missing_time:
                    raise ValueError("Missing worksheet time needs an explicit omission policy")
                omitted += 1
                continue
            times.append(clock.seconds(time))
            values = []
            for column in columns:
                value = row[positions[column.source]]
                if value is None or (isinstance(value, str) and value.strip() in {"", "#N/A", "NA", "nan"}):
                    values.append(np.nan)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    values.append(float(value))
                else:
                    raise ValueError(f"Nonnumeric worksheet observation in {column.source!r}")
            rows.append(values)
    finally:
        workbook.close()
    if not rows:
        raise ValueError("No worksheet observations remain")
    data = np.asarray(rows, dtype=float)
    for index, column in enumerate(columns):
        data[:, index] = column.convert(data[:, index])
    valid = np.isfinite(data)
    series = TimeSeries(np.asarray(times), data, tuple(c.target for c in columns),
                        tuple(SI_UNITS[c.quantity] for c in columns), valid,
                        clock_id, origin, source_id, tuple(c.quantity for c in columns),
                        tuple(c.variable().basis_id for c in columns))
    return LoadedSeries(series, LoadReport(source_rows, omitted, int(np.count_nonzero(~valid))))
