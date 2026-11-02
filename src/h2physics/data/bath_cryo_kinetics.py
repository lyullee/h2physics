"""Source-bound kinetic observations for cryogenic H2 adsorption in two materials.

The reader preserves Bath's whole-sample excess-uptake units and recorded state
channels. It does not normalize by an unreported sample mass or feed the data to
the absolute-uptake finite-vessel model.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

SOURCE_DOI = "10.15125/BATH-00099"
SOURCE_RIGHTS = "No restrictions"
KINETIC_FILENAME = "Kinetic_data_-_MIL-101_and_AX-21.xlsx"
KINETIC_SHA256 = "d0ed4668dc98a014e159c993d33edc85b5d4f971a3bbb2eb2263af9d3daee611c"
_SHEETS = {
    "MIL-101 (Cr) at 77 K": ("MIL-101 (Cr)", 77.0),
    "MIL-101(Cr) at 90 K": ("MIL-101 (Cr)", 90.0),
    "AX-21 at 90 K": ("AX-21", 90.0),
}
_HEADERS = (
    "Time (min)", "Excess uptake (micromols)", "Pressure (MPa)",
    "Sample Temperature (K)",
)


@dataclass(frozen=True, slots=True)
class BathKineticObservation:
    source_row: int
    time_min: float
    excess_uptake_umol: float
    pressure_mpa: float
    sample_temperature_k: float

    def __post_init__(self):
        if isinstance(self.source_row, bool) or not isinstance(self.source_row, int) or self.source_row < 3:
            raise ValueError("Retain the original kinetic workbook row number")
        for name in ("time_min", "excess_uptake_umol", "pressure_mpa", "sample_temperature_k"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite source value")
        if self.pressure_mpa < 0.0 or self.sample_temperature_k <= 0.0:
            raise ValueError("Pressure must be nonnegative and sample temperature positive")


@dataclass(frozen=True, slots=True)
class BathKineticSeries:
    sheet_name: str
    material_id: str
    nominal_temperature_k: float
    source_doi: str
    source_filename: str
    source_sha256: str
    rights_statement: str
    observations: tuple[BathKineticObservation, ...]

    def __post_init__(self):
        if self.source_doi != SOURCE_DOI or self.rights_statement != SOURCE_RIGHTS:
            raise ValueError("Bath source identity and rights statement must remain explicit")
        if self.source_filename != KINETIC_FILENAME or self.source_sha256 != KINETIC_SHA256:
            raise ValueError("Only the checksum-pinned Bath kinetic workbook is admitted")
        if self.sheet_name not in _SHEETS or not self.observations:
            raise ValueError("Retain one named source sheet with observations")
        if any(type(point) is not BathKineticObservation for point in self.observations):
            raise TypeError("Kinetic observations must use the source reader's typed rows")
        rows = tuple(point.source_row for point in self.observations)
        if rows != tuple(sorted(set(rows))):
            raise ValueError("Source row identity/order must be preserved")

    @property
    def uptake_basis(self) -> str:
        return "whole-sample surface excess; micromol H2"

    def require_finite_adsorption_dynamics_basis(self):
        """Reject implicit use as absolute site loading for the finite-vessel model."""
        raise ValueError(
            "Bath kinetics report whole-sample excess micromols; the finite adsorption model requires absolute mol/kg loading and a documented sample-mass mapping"
        )


def load_bath_kinetic_workbook(path: str | Path) -> tuple[BathKineticSeries, ...]:
    """Load the measured kinetic workbook only after exact local SHA-256 pinning."""
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != KINETIC_SHA256:
        raise ValueError("Bath kinetic workbook bytes do not match the pinned record file")
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise ImportError("Install h2physics[data] to read the Bath kinetic workbook") from error
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        if tuple(workbook.sheetnames) != tuple(_SHEETS):
            raise ValueError("Bath kinetic workbook sheet identities/order differ from the pinned schema")
        result = []
        for sheet_name, (material_id, nominal_temperature) in _SHEETS.items():
            sheet = workbook[sheet_name]
            headers = tuple(sheet.cell(2, col).value for col in range(1, 5))
            if headers != _HEADERS:
                raise ValueError(f"Bath kinetic schema changed in sheet {sheet_name}")
            points = []
            for source_row, row in enumerate(
                sheet.iter_rows(min_row=3, max_col=4, values_only=True), start=3,
            ):
                if all(value is None for value in row):
                    continue
                if any(value is None for value in row):
                    raise ValueError(f"Partial Bath source row {source_row} requires explicit review")
                values = []
                for value in row:
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError(f"Nonnumeric Bath source cell in row {source_row}")
                    values.append(float(value))
                points.append(BathKineticObservation(
                    source_row, values[0], values[1], values[2], values[3],
                ))
            result.append(BathKineticSeries(
                sheet_name=sheet_name,
                material_id=material_id,
                nominal_temperature_k=nominal_temperature,
                source_doi=SOURCE_DOI,
                source_filename=source.name,
                source_sha256=digest,
                rights_statement=SOURCE_RIGHTS,
                observations=tuple(points),
            ))
        return tuple(result)
    finally:
        workbook.close()
