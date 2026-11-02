"""Spatial jet observations from the reviewed HyTunnel-CS concentration workbooks.

The source tables contain spatial scans and summary statistics, not a common
time series. Header/value conflicts and instrument offsets remain visible.
"""

import hashlib
import io
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..core import Origin
from ..observations import GAS_VOLUME_FRACTION_BASIS as VOLUME_BASIS
from ..observations import ObservationTable, Variable


@dataclass(frozen=True, slots=True)
class AmbientColumnOverride:
    pressure_column: str
    temperature_column: str
    evidence_id: str

    def __post_init__(self):
        if (not self.evidence_id.strip() or self.pressure_column == self.temperature_column
                or any(not re.fullmatch(r"[A-Z]{1,3}", name)
                       for name in (self.pressure_column, self.temperature_column))):
            raise ValueError("A source-column override needs distinct Excel columns and explicit evidence")


@dataclass(frozen=True, slots=True)
class JetDataIssue:
    sheet: str
    cell: str
    code: str


@dataclass(frozen=True, slots=True)
class HyTunnelJetSheet:
    sheet_name: str
    observations: ObservationTable
    mean_cells: tuple[str, ...]
    issues: tuple[JetDataIssue, ...]
    ambient_override: AmbientColumnOverride | None


@dataclass(frozen=True, slots=True)
class HyTunnelJetWorkbook:
    source_id: str
    source_sha256: str
    sheets: tuple[HyTunnelJetSheet, ...]


def _label(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return math.nan
    return float(value)


def load_hytunnel_jet_workbook(
    path: str | Path, *, source_id: str,
    ambient_overrides: Mapping[str, AmbientColumnOverride] | None = None,
    maximum_bytes: int = 10_000_000,
) -> HyTunnelJetWorkbook:
    """Load all concentration sheets, checking coordinate and statistic blocks.

    Gas concentration is reported volume percent; positions are millimetres.
    Ambient columns follow the literal labels unless a per-sheet evidenced
    override is supplied. Implausible labelled room conditions are masked,
    without automatically swapping columns or discarding concentration rows.
    """
    if not source_id.strip():
        raise ValueError("Declare the versioned dataset/workbook identity")
    path = Path(path)
    if path.stat().st_size > maximum_bytes:
        raise ValueError("Workbook exceeds the declared byte budget")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    from openpyxl import load_workbook
    from openpyxl.utils import column_index_from_string, get_column_letter

    workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True, keep_links=False)
    overrides = dict(ambient_overrides or {})
    result = []
    try:
        workbook_units = {_label(value) for row in workbook.worksheets[0].iter_rows(max_row=15, values_only=True)
                          for value in row if "h2-concentration/" in _label(value)}
        if workbook_units != {"h2-concentration/%"}:
            raise ValueError("The workbook must declare H2 concentration percent without conflicting units")
        if set(overrides)-set(workbook.sheetnames):
            raise ValueError("Ambient overrides reference an absent worksheet")
        for sheet in workbook:
            if not sheet.max_row or not sheet.max_column or sheet.max_row*sheet.max_column > 500_000:
                raise ValueError("Unsupported worksheet dimensions")
            grid = list(sheet.iter_rows(values_only=True))
            coordinate_rows = [(i, [j for j, value in enumerate(row) if _label(value) == "x/mm"])
                               for i, row in enumerate(grid)]
            coordinate_rows = [(i, columns) for i, columns in coordinate_rows if len(columns) == 3]
            if not coordinate_rows:
                raise ValueError(f"{sheet.title}: expected a three-block spatial header")
            header, x_columns = coordinate_rows[0]
            headers = grid[header]
            expected_conditions = {"pu/mbar": "ambient_pressure", "tu/°c": "ambient_temperature",
                "[g/s]": "mass_flow", "nachv[bar]": "overpressure", "nozzle/mm": "diameter"}
            conditions = {expected_conditions[_label(value)]: j for j, value in enumerate(headers)
                          if _label(value) in expected_conditions}
            if set(conditions) != set(expected_conditions.values()):
                raise ValueError(f"{sheet.title}: source-condition units/columns differ")
            override = overrides.get(sheet.title)
            if override is not None:
                if not isinstance(override, AmbientColumnOverride):
                    raise TypeError("Supply an AmbientColumnOverride object")
                conditions["ambient_pressure"] = column_index_from_string(override.pressure_column)-1
                conditions["ambient_temperature"] = column_index_from_string(override.temperature_column)-1
            if max(conditions.values()) >= sheet.max_column:
                raise ValueError("A source-condition column lies outside the worksheet")
            blocks = {}
            for block, xcol in enumerate(x_columns):
                stop = x_columns[block+1] if block < 2 else len(headers)
                sensors = [j for j in range(xcol+1, stop)
                           if "y/mm" in _label(grid[header-1][j]) and math.isfinite(_number(headers[j]))]
                if len(sensors) != 9:
                    raise ValueError(f"{sheet.title}: expected nine declared sensor offsets per block")
                labels = {_label(grid[i][j]) for i in range(header)
                          for j in range(xcol, sensors[0]+1)}
                statistic = [name for name in ("average", "maximum", "minimum")
                             if name+"value" in labels]
                if len(statistic) != 1 or statistic[0] in blocks:
                    raise ValueError(f"{sheet.title}: ambiguous concentration statistic")
                unit_labels = {_label(grid[i][j]) for i in range(header)
                               for j in range(xcol, sensors[0]+1)}
                explicit_units = {label for label in unit_labels if "h2-concentration/" in label}
                if explicit_units and explicit_units != {"h2-concentration/%"}:
                    raise ValueError(f"{sheet.title}: H2 concentration percent header differs: {unit_labels}")
                blocks[statistic[0]] = (xcol, sensors, tuple(_number(headers[j]) for j in sensors))
            if set(blocks) != {"average", "maximum", "minimum"}:
                raise ValueError("Average, maximum and minimum blocks must all be present")
            offsets = blocks["average"][2]
            if any(blocks[name][2] != offsets for name in blocks) or len(set(offsets)) != 9:
                raise ValueError("The source statistic blocks do not share unique sensor offsets")
            rows, valid, identities, mean_cells, issues = [], [], [], [], []
            repeated_headers = dict(coordinate_rows[1:])
            tracer_conflict = re.search(r"\bHe\b", sheet.title) is not None
            if tracer_conflict:
                issues.append(JetDataIssue(sheet.title, "A1", "gas_identity_conflict_sheet_He_vs_H2_columns"))

            def issue(row_index, col, code):
                issues.append(JetDataIssue(sheet.title, f"{get_column_letter(col+1)}{row_index+1}", code))

            for i in range(header+1, len(grid)):
                row = grid[i]
                if i in repeated_headers:
                    if repeated_headers[i] != x_columns:
                        raise ValueError("A repeated spatial block changed column positions")
                    new_offsets = [tuple(_number(row[j]) for j in blocks[name][1]) for name in blocks]
                    if (any(values != new_offsets[0] for values in new_offsets)
                            or len(set(new_offsets[0])) != 9
                            or not all(math.isfinite(v) for v in new_offsets[0])):
                        raise ValueError("Repeated spatial blocks have inconsistent sensor offsets")
                    offsets = new_offsets[0]
                    continue
                x_values = [_number(row[blocks[name][0]]) for name in ("average", "maximum", "minimum")]
                if not any(math.isfinite(value) for value in x_values):
                    continue
                if not all(math.isfinite(value) for value in x_values) or len(set(x_values)) != 1:
                    raise ValueError(f"{sheet.title}: statistic blocks have different scan coordinates at row {i+1}")
                x = x_values[0]*.001
                ambient_p = _number(row[conditions["ambient_pressure"]])*100.
                ambient_t = _number(row[conditions["ambient_temperature"]])+273.15
                mass = _number(row[conditions["mass_flow"]])*.001
                gauge = _number(row[conditions["overpressure"]])*1e5
                diameter = _number(row[conditions["diameter"]])*.001
                # This source profile describes an atmospheric laboratory campaign.
                # Values outside this declared room envelope remain present but invalid.
                p_valid = math.isfinite(ambient_p) and 50_000. <= ambient_p <= 150_000.
                t_valid = math.isfinite(ambient_t) and 200. <= ambient_t <= 400.
                for good, label in ((p_valid, "ambient_pressure"), (t_valid, "ambient_temperature")):
                    if not good:
                        issue(i, conditions[label], "labelled_ambient_outside_room_envelope")
                source_valid = (p_valid, t_valid, math.isfinite(mass) and mass > 0.,
                                math.isfinite(gauge) and gauge >= 0.,
                                p_valid and math.isfinite(gauge) and gauge >= 0.,
                                math.isfinite(diameter) and diameter > 0.)
                for channel, offset in enumerate(offsets):
                    concentrations = [_number(row[blocks[name][1][channel]])*.01
                                      for name in ("average", "maximum", "minimum")]
                    c_valid = [math.isfinite(value) and 0. <= value <= 1. for value in concentrations]
                    for good, name in zip(c_valid, ("average", "maximum", "minimum"), strict=True):
                        if not good:
                            issue(i, blocks[name][1][channel], "missing_or_outside_volume_fraction_domain")
                    if all(math.isfinite(v) for v in concentrations):
                        average, maximum, minimum = concentrations
                        if not minimum <= average <= maximum:
                            c_valid = [False]*3
                            issue(i, blocks["average"][1][channel], "inconsistent_statistic_order")
                    if tracer_conflict:
                        c_valid = [False]*3
                    rows.append((x, offset*.001, *concentrations, ambient_p, ambient_t,
                                 mass, gauge, ambient_p+gauge, diameter, float(i+1), float(channel+1)))
                    valid.append((math.isfinite(x) and x >= 0., True, *c_valid, *source_valid, True, True))
                    identities.append(f"{source_id}|{sheet.title}|row-{i+1}|channel-{channel+1}")
                    mean_cells.append(f"{get_column_letter(blocks['average'][1][channel]+1)}{i+1}")
            if not rows:
                raise ValueError("Concentration worksheet has no spatial observations")
            variables = (Variable("x", "length", "m"), Variable("y", "length", "m"),
                *(Variable(name, "volume_fraction", "1", VOLUME_BASIS) for name in
                  ("mean_h2_volume_fraction", "maximum_h2_volume_fraction", "minimum_h2_volume_fraction")),
                Variable("ambient_pressure", "pressure", "Pa", "absolute"),
                Variable("ambient_temperature", "temperature", "K"),
                Variable("source_mass_flow", "mass_flow", "kg/s"),
                Variable("source_overpressure", "pressure_difference", "Pa", "reported pipe gauge pressure"),
                Variable("source_reported_pressure", "pressure", "Pa", "reported pipe pressure; ambient added"),
                Variable("nominal_diameter", "length", "m"),
                Variable("scan_row", "source_row_index", "1"), Variable("channel", "source_channel", "1"))
            origins = [Origin.MEASURED]*len(variables)
            if override is not None:
                for index in (5, 6, 9):
                    origins[index] = Origin.RECONSTRUCTED
            table = ObservationTable(np.array(rows), variables, np.array(valid), tuple(identities),
                (f"{source_id}|{sheet.title}",)*len(rows), tuple(origins), source_id,
                (("workbook_sha256", digest), ("worksheet", sheet.title),
                 ("sampling", "spatial traverse; source scan row and reported gas concentration statistics"),
                 ("ambient_mapping", override.evidence_id if override else "literal source column labels"),
                 ("concentration_units", "workbook percent; source metadata declares gas volume fraction in air"),
                 ("gas_identity", "unresolved He/H2 label conflict" if tracer_conflict else "reported H2"),
                 ("source_pressure", "pipe overpressure; not an asserted nozzle stagnation pressure")))
            result.append(HyTunnelJetSheet(sheet.title, table, tuple(mean_cells), tuple(issues), override))
    finally:
        workbook.close()
    return HyTunnelJetWorkbook(source_id, digest, tuple(result))
