"""Explicit DisCha workbook profile, independent clocks and original-byte identity.

Primary apparatus/data provenance: https://doi.org/10.35097/1187
No publisher programs, formulas or plotting instructions are executed.
"""

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

from ..core import Origin, finite
from ..units import convert_to_si
from .excel import ExcelClock, load_excel_sheet
from .loaders import Column, LoadedSeries


@dataclass(frozen=True, slots=True)
class DischaRun:
    source_id: str
    workbook_sha256: str
    nominal_nozzle_diameter_m: float
    initial_pressure_pa: float
    pressure_basis_in_source: str
    reference_pressure_pa: float | None
    ambient: LoadedSeries
    temperatures: LoadedSeries
    weight: LoadedSeries
    fast_pressure: LoadedSeries | None
    relative_humidity_unit_in_source: str | None = None
    clock_method: str = "publisher-synchronized-PNoz-onset; original recorder elapsed time retained"


def load_discha_workbook(source: Path | bytes, *, source_id: str, clock_id: str,
                         pressure_basis: Literal["absolute", "gauge"],
                         reference_pressure_pa: float | None,
                         relative_humidity_unit: Literal["%", "1"] | None = None,
                         include_fast_pressure: bool = False,
                         maximum_bytes: int = 60_000_000) -> DischaRun:
    """Read the declared 2019 exported layout; do not align/interpolate its recorders.

    Pressure basis and any gauge reference are caller declarations. Source column A
    is the author's synchronized clock; column B remains a separate recorded channel.
    Concentration channels and open-junction thermocouples are outside this profile.
    """
    if not source_id.strip() or not clock_id.strip():
        raise ValueError("Source and common clock identities must be explicit")
    if pressure_basis not in {"absolute", "gauge"}:
        raise ValueError("Declare absolute or gauge pressure")
    if relative_humidity_unit not in {None, "%", "1"}:
        raise ValueError("Declare relative humidity as a fraction or percent, or leave it unconsumed")
    if pressure_basis == "gauge":
        if reference_pressure_pa is None:
            raise ValueError("Gauge pressure requires an explicit reference_pressure_pa")
        finite(reference_pressure_pa, "reference_pressure_pa", positive=True)
    elif reference_pressure_pa is not None:
        raise ValueError("Absolute pressure does not take a gauge reference")
    if not isinstance(source, bytes) and Path(source).stat().st_size > maximum_bytes:
        raise ValueError("Workbook exceeds the declared byte limit")
    payload = source if isinstance(source, bytes) else Path(source).read_bytes()
    if len(payload) > maximum_bytes:
        raise ValueError("Workbook exceeds the declared byte limit")
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True, keep_links=False)
    sheets, headers, units = {}, {}, {}
    try:
        for kind, suffix in (("ambient", "-cH2-Amb"), ("temperatures", "-Temp"),
                             ("weight", "-Weight"), ("pressure", "-Press")):
            matches = [name for name in workbook.sheetnames if name.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one DisCha worksheet ending in {suffix}")
            sheets[kind] = matches[0]
            top = list(workbook[matches[0]].iter_rows(min_row=1, max_row=6, values_only=True))
            headers[kind], units[kind] = top[0], top[3]
            if top[5][0] != "Time [s]":
                raise ValueError("DisCha synchronized clock does not have its declared seconds header")
            if kind == "pressure":
                diameter = finite(top[1][0], "nominal nozzle diameter mm", positive=True) * .001
                initial_pressure = float(convert_to_si(top[1][5], quantity="pressure", unit="bar",
                                         pressure_basis=pressure_basis, ambient_pressure_pa=reference_pressure_pa))
                finite(initial_pressure, "initial pressure", positive=True)
    finally:
        workbook.close()

    def pressure(name, target):
        return Column(name, target, "pressure", "bar", pressure_basis, reference_pressure_pa)
    profile = {
        "ambient": ((pressure("PVessel", "vessel_pressure"), pressure("PNozzle", "line_pressure"),
                     Column("F", "reaction_force", "force", "N"),
                     Column("Tamb", "ambient_temperature", "temperature", "degC")),
                    ("bar", "bar", "N", "Grad C")),
        "temperatures": ((*(Column(name, target, "temperature", "K") for name, target in (
            ("T1", "vessel_t1"), ("T2", "vessel_t2"), ("T3", "vessel_t3"),
            ("T4", "line_temperature"), ("TNz", "nozzle_solid_temperature"))),),
                         ("Kelvin",)*5),
        "weight": ((Column("Weight", "total_apparatus_mass", "mass", "kg"),), ("kg",)),
        "pressure": ((pressure("PVes", "vessel_pressure"), pressure("PNoz", "line_pressure")),
                     ("bar", "bar")),
    }
    if relative_humidity_unit is not None:
        columns, expected = profile["ambient"]
        profile["ambient"] = ((*columns, Column("RHamb", "relative_humidity", "relative_humidity",
                                                relative_humidity_unit)), (*expected, "Rel. Feuchte"))
    loaded = {}
    for kind, (columns, expected_units) in profile.items():
        if kind == "pressure" and not include_fast_pressure:
            continue
        for column, expected in zip(columns, expected_units, strict=True):
            positions = [i for i, value in enumerate(headers[kind]) if value == column.source]
            if len(positions) != 1 or units[kind][positions[0]] != expected:
                raise ValueError(f"Unexpected DisCha header/unit for {kind}/{column.source}")
        # Header B1 is a per-recorder descriptive label, not a globally fixed name.
        original_clock = headers[kind][1]
        loaded[kind] = load_excel_sheet(io.BytesIO(payload), sheets[kind],
            columns=(*columns, Column(original_clock, "recorder_elapsed_time", "time", "s")),
            clock=ExcelClock("Time [s]", "numeric", "s"), clock_id=clock_id,
            origin=Origin.MEASURED, source_id=f"{source_id}/{sheets[kind]}",
            header_row=1, clock_header_row=6, data_start_row=7, omit_missing_time=True)
    return DischaRun(source_id, hashlib.sha256(payload).hexdigest(), diameter, initial_pressure,
                     pressure_basis, reference_pressure_pa, loaded["ambient"], loaded["temperatures"],
                     loaded["weight"], loaded.get("pressure"),
                     relative_humidity_unit_in_source=relative_humidity_unit)


def load_discha_member(archive: Path, member: str, **kwargs) -> DischaRun:
    """Read one bounded workbook in place, without archive extraction."""
    maximum = kwargs.get("maximum_bytes", 60_000_000)
    with ZipFile(archive) as container:
        item = container.getinfo(member)
        if item.is_dir() or not member.endswith(".xlsx") or item.file_size > maximum:
            raise ValueError("Select a bounded .xlsx archive member")
        return load_discha_workbook(container.read(item), **kwargs)
