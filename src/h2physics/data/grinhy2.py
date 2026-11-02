"""Source-bound reader for the attributed GrInHy2 plant-flow time series.

The input is a CC BY 4.0 adaptation. Flow units and values are kept exactly
as reported; no reference-state conversion or gap interpolation is attempted.
"""

import csv
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np

from ..core import immutable_array

DOI = "10.5281/zenodo.7612826"
HEADERS = (
    "elapsed_s", "source_excel_time_serial", "hydrogen_to_vent_Nm3_h",
    "hydrogen_to_hpu_Nm3_h", "hydrogen_to_grid_Nm3_h", "hydrogen_demand_Nm3_h",
)
CSV_HEADERS = (
    "elapsed_time_s_from_start", "source_time_excel_serial",
    "hydrogen_to_vent_Nm3_h", "hydrogen_to_HPU_Nm3_h",
    "hydrogen_to_grid_Nm3_h", "hydrogen_demand_Nm3_h",
)


@dataclass(frozen=True, slots=True)
class GrInHy2FlowSeries:
    """Immutable observed plant-boundary schedule with exact file lineage."""

    source_path: Path
    source_sha256: str
    elapsed_s: np.ndarray
    excel_time_serial: np.ndarray
    vent_nm3_h: np.ndarray
    hpu_nm3_h: np.ndarray
    grid_nm3_h: np.ndarray
    demand_nm3_h: np.ndarray
    source_id: str = DOI

    def __post_init__(self):
        path = Path(self.source_path).resolve()
        object.__setattr__(self, "source_path", path)
        for name in HEADERS:
            field = {
                "elapsed_s": "elapsed_s", "source_excel_time_serial": "excel_time_serial",
                "hydrogen_to_vent_Nm3_h": "vent_nm3_h", "hydrogen_to_hpu_Nm3_h": "hpu_nm3_h",
                "hydrogen_to_grid_Nm3_h": "grid_nm3_h", "hydrogen_demand_Nm3_h": "demand_nm3_h",
            }[name]
            object.__setattr__(self, field, immutable_array(getattr(self, field), dtype=float, name=field))
        n = len(self.elapsed_s)
        if (not self.source_id or not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) or n < 2
                or any(len(getattr(self, name)) != n for name in
                       ("excel_time_serial", "vent_nm3_h", "hpu_nm3_h", "grid_nm3_h", "demand_nm3_h"))
                or any(not np.all(np.isfinite(getattr(self, name))) for name in
                       ("elapsed_s", "excel_time_serial", "vent_nm3_h", "hpu_nm3_h", "grid_nm3_h", "demand_nm3_h"))
                or self.elapsed_s[0] != 0 or np.any(np.diff(self.elapsed_s) <= 0)):
            raise ValueError("GrInHy2 rows must be finite, aligned and strictly time ordered")

    def require_current(self):
        digest = sha256(self.source_path.read_bytes()).hexdigest()
        if digest != self.source_sha256:
            raise RuntimeError("GrInHy2 source CSV changed after loading")
        return self

    @property
    def intervals_s(self):
        return immutable_array(np.diff(self.elapsed_s), dtype=float, name="intervals_s")


def load_grinhy2_flow(path, *, expected_sha256):
    """Read the reviewed CSV only when its full-file SHA-256 is supplied."""
    source = Path(path).resolve()
    digest = sha256(source.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError("GrInHy2 CSV SHA-256 differs from the declared receipt")
    with source.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CSV_HEADERS:
            raise ValueError("GrInHy2 CSV schema differs from the reviewed six-column layout")
        rows = []
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(row.get(name) is None for name in CSV_HEADERS):
                raise ValueError(f"Unexpected field count at CSV row {row_number}")
            try:
                values = tuple(float(row[name]) for name in CSV_HEADERS)
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid numeric source token at CSV row {row_number}") from exc
            if len(values) != len(HEADERS):
                raise ValueError(f"Unexpected field count at CSV row {row_number}")
            rows.append(values)
    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or data.shape[1] != len(HEADERS):
        raise ValueError("GrInHy2 source must contain at least one complete observation")
    return GrInHy2FlowSeries(source, digest, *(data[:, i] for i in range(6)))
