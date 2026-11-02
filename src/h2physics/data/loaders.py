"""Declared columns, units and clocks; no automatic physical interpretation."""

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from zipfile import ZipFile

import numpy as np

from ..core import Origin, TimeSeries
from ..observations import ObservationTable, Variable
from ..units import convert_to_si

SI_UNITS = {
    "time": "s", "temperature": "K", "pressure": "Pa", "pressure_difference": "Pa",
    "mass_flow": "kg/s", "mass": "kg", "length": "m", "volume_fraction": "1",
    "mole_fraction": "1", "mass_fraction": "1", "voltage": "V", "current": "A", "current_density": "A/m2",
    "energy": "J", "force": "N", "relative_humidity": "1",
    "normalized_pressure": "1", "specific_amount": "mol/kg",
    "reference_specific_volume": "m3/kg",
    "reported_pressure": "Pa",
}


@dataclass(frozen=True, slots=True)
class Column:
    source: str
    target: str
    quantity: str
    unit: str
    pressure_basis: str | None = None
    ambient_pressure_pa: float | None = None
    basis_id: str = ""

    def convert(self, values):
        return convert_to_si(values, quantity=self.quantity, unit=self.unit,
                             pressure_basis=self.pressure_basis,
                             ambient_pressure_pa=self.ambient_pressure_pa)

    def variable(self):
        basis = self.basis_id
        if not basis and self.quantity in {"pressure", "pressure_difference"}:
            basis = "absolute" if self.quantity == "pressure" else "differential"
        return Variable(self.target, self.quantity, SI_UNITS[self.quantity], basis)


@dataclass(frozen=True, slots=True)
class LoadReport:
    source_rows: int
    omitted_missing_time_rows: int
    invalid_measurement_values: int
    interpolation_performed: bool = False


@dataclass(frozen=True, slots=True)
class LoadedSeries:
    series: TimeSeries
    report: LoadReport


def load_delimited(
    source: TextIO, *, columns: tuple[Column, ...], time_column: str,
    time_unit: str, clock_id: str, origin: Origin, source_id: str,
    delimiter: str = ",", omit_missing_time: bool = False,
    missing_tokens: tuple[str, ...] = ("", "nan", "NaN", "#N/A", "NA"),
) -> LoadedSeries:
    if not columns or any(column.quantity not in SI_UNITS for column in columns):
        raise ValueError("At least one supported physical column is required")
    reader = csv.DictReader(source, delimiter=delimiter)
    required = {time_column, *(column.source for column in columns)}
    if reader.fieldnames is None or required - set(reader.fieldnames):
        raise ValueError(f"Missing declared columns: {required - set(reader.fieldnames or [])}")
    times, rows = [], []
    total = omitted = 0
    for row in reader:
        total += 1
        token = (row.get(time_column) or "").strip()
        if token in missing_tokens:
            if not omit_missing_time:
                raise ValueError("Missing time needs an explicit omission policy")
            omitted += 1
            continue
        times.append(float(token))
        values = []
        for column in columns:
            token = (row.get(column.source) or "").strip()
            values.append(np.nan if token in missing_tokens else float(token))
        rows.append(values)
    if not rows:
        raise ValueError("No observations remain under the declared clock policy")
    data = np.asarray(rows, dtype=float)
    for index, column in enumerate(columns):
        data[:, index] = column.convert(data[:, index])
    valid = np.isfinite(data)
    series = TimeSeries(convert_to_si(times, quantity="time", unit=time_unit), data,
                        tuple(c.target for c in columns), tuple(SI_UNITS[c.quantity] for c in columns),
                        valid, clock_id, origin, source_id, tuple(c.quantity for c in columns),
                        tuple(c.variable().basis_id for c in columns))
    return LoadedSeries(series, LoadReport(total, omitted, int(np.count_nonzero(~valid))))


def load_csv_file(path: Path, **declarations) -> LoadedSeries:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        return load_delimited(source, **declarations)


def load_csv_member(archive_path: Path, member: str, **declarations) -> LoadedSeries:
    with ZipFile(archive_path) as archive:
        item = archive.getinfo(member)
        if item.file_size > 250_000_000:
            raise ValueError("CSV member exceeds the declared ingestion limit")
        with archive.open(item) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as source:
                return load_delimited(source, **declarations)


def load_observation_table(source: TextIO, *, columns: tuple[Column, ...],
                            experiment_id: str, source_id: str,
                            origins: tuple[Origin, ...], delimiter: str = ",",
                            context: tuple[tuple[str, str], ...] = (),
                            missing_tokens: tuple[str, ...] = ("", "nan", "NaN", "#N/A", "NA")) -> ObservationTable:
    """Read numeric columns with no time coordinate and no row omission/sorting.

    Repeated or decreasing abscissas are allowed. Each source record retains its
    row identity, masks, group and per-column origin. A reference volume remains
    a reference volume until its gas state and measurement basis are established.
    """
    if not columns or any(column.quantity not in SI_UNITS for column in columns):
        raise ValueError("Declare supported observation quantities")
    variables = tuple(column.variable() for column in columns)
    reader = csv.DictReader(source, delimiter=delimiter)
    required = {column.source for column in columns}
    if reader.fieldnames is None or required - set(reader.fieldnames):
        raise ValueError(f"Missing declared observation columns: {required - set(reader.fieldnames or [])}")
    rows = []
    for row in reader:
        values = []
        for column in columns:
            token = (row.get(column.source) or "").strip()
            values.append(np.nan if token in missing_tokens else float(token))
        rows.append(values)
    if not rows:
        raise ValueError("No observation records found")
    values = np.asarray(rows, dtype=float)
    for index, column in enumerate(columns):
        values[:, index] = column.convert(values[:, index])
    return ObservationTable(values, variables, np.isfinite(values),
                             tuple(f"{source_id}:record-{i+1}" for i in range(len(rows))),
                             (experiment_id,)*len(rows), origins, source_id, context)
