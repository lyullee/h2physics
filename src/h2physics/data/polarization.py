"""Read explicitly declared two-header polarization grids into non-time tables."""

import csv
from typing import TextIO

import numpy as np

from ..core import Origin
from ..observations import ObservationTable, Variable
from ..units import convert_to_si


def load_polarization_grid(source: TextIO, *, source_id: str, group_prefix: str,
                            temperature_unit: str, current_density_unit: str, voltage_unit: str,
                            voltage_origin: Origin = Origin.UNRESOLVED,
                            delimiter: str = "\t") -> tuple[ObservationTable, ...]:
    """First header carries temperatures; second header identifies j and voltages.

    Units are caller declarations, not inferred from partially corrupted header
    glyphs. Declared temperatures are conditions, not measured thermocouple data.
    Each curve gets a grouping identity, without claiming apparatus independence.
    """
    reader = csv.reader(source, delimiter=delimiter)
    temperature_header, value_header = next(reader), next(reader)
    tokens = list(temperature_header[1:])
    while tokens and not tokens[-1].strip():
        tokens.pop()
    if not tokens or not temperature_header[0].startswith("T/") or not value_header[0].startswith("j/"):
        raise ValueError("The declared two-header polarization grid was not found")
    count = len(tokens)
    if any(value != "E/" + voltage_unit for value in value_header[1:count+1]) or len(value_header) < count+1:
        raise ValueError("Polarization voltage headers conflict with the declared unit")
    temperatures = convert_to_si([float(t) for t in tokens], quantity="temperature", unit=temperature_unit)
    if len(set(temperatures)) != count:
        raise ValueError("Temperature conditions must be unique")
    rows, record_ids = [], []
    for index, row in enumerate(reader):
        if not row or not any(token.strip() for token in row):
            continue
        if any(token.strip() for token in row[count+1:]):
            raise ValueError("Unexpected populated polarization columns")
        tokens = list(row[:count+1]) + [""]*max(0, count+1-len(row))
        rows.append([float(token) if token.strip() and token.strip() not in {"NA", "nan", "#N/A"}
                     else np.nan for token in tokens])
        record_ids.append(index+1)
    if not rows:
        raise ValueError("No polarization observations found")
    values = np.asarray(rows, dtype=float)
    current = convert_to_si(values[:, 0], quantity="current_density", unit=current_density_unit)
    variables = (Variable("current_density", "current_density", "A/m2"),
                 Variable("temperature", "temperature", "K"), Variable("voltage", "voltage", "V"))
    tables = []
    for column, temperature in enumerate(temperatures):
        voltage = convert_to_si(values[:, column+1], quantity="voltage", unit=voltage_unit)
        data = np.c_[current, np.full(len(current), temperature), voltage]
        group = f"{group_prefix}/T={temperature:.12g}K"
        context = (("temperature_header", temperature_header[0]), ("current_header", value_header[0]),
                   ("unit_policy", "explicit caller declarations"))
        tables.append(ObservationTable(data, variables, np.isfinite(data),
            tuple(f"{source_id}:T={temperature:.12g}:record-{i}" for i in record_ids),
            (group,)*len(data), (Origin.UNRESOLVED, Origin.RECONSTRUCTED, voltage_origin), source_id, context))
    return tuple(tables)
