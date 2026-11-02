"""Source-hash-bound experiment matrix for open-atmosphere H2 jet ignition tests.

The publisher workbook reports experiment conditions and pressure-derived
release-rate summaries. This reader preserves its declared values; it does not
convert pressure basis or reinterpret the reported mass-flow calculation.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

_DOI = "10.18710/X044QK"
_DATASET_PID = "doi:10.18710/X044QK"
_MATRIX_FILE_PID = "doi:10.18710/X044QK/JH7P7P"
_MATRIX_FILENAME = "Matrix and H2 flow results.xlsx"
_MATRIX_SIZE = 14_199
_MATRIX_MD5 = "6c929ee530ac393ee8e76f6db2eff05c"
_MATRIX_SHA256 = "c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557"
_LICENSE = "CC0-1.0"
_SHEET = "Sheet1"
_TITLE_CELL = "Experimental result, mass flow rate is calculated based on the experimental pressure"
_HEADERS = (
    "EXP Number", "Max Pressure [bar]", "Max MFR [kg/s]", "Avg Pressure [bar]",
    "Avg MFR [kg/s]", "Ignition place", "Obstacle distance from the nozzle [cm]",
    "H2 release time [s]", "Ignition delay time [s]", "comments",
)
_PENDING = set()


def _hash_file(path: Path) -> tuple[str, str, int]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            md5.update(block)
            sha256.update(block)
            size += len(block)
    return md5.hexdigest(), sha256.hexdigest(), size


def _issue(**values):
    token = object()
    _PENDING.add(token)
    try:
        return IgnitedHydrogenJetMatrix(**values, _issuer=token)
    except Exception:
        _PENDING.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class IgnitedJetExperiment:
    """One matrix row, retaining source-stated headings and identities."""

    source_row_id: str
    experiment_number: int
    reported_max_pressure_bar: float
    pressure_derived_max_mass_flow_kg_s: float
    reported_average_pressure_bar: float
    pressure_derived_average_mass_flow_kg_s: float
    ignition_location_code: int
    obstacle_distance_raw: float | str
    hydrogen_release_time_s: float
    ignition_delay_time_s: float
    comment: str | None
    raw_cells: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class IgnitedHydrogenJetMatrix:
    """Pinned workbook contents and immutable row-level experiment records."""

    source_doi: str
    source_dataset_pid: str
    source_file_pid: str
    source_filename: str
    license_id: str
    source_md5: str
    source_sha256: str
    source_size_bytes: int
    sheet_name: str
    title_note: str
    headers: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    experiments: tuple[IgnitedJetExperiment, ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise ValueError("Use load_ignited_hydrogen_jet_matrix() to issue a pinned matrix")
        _PENDING.remove(self._issuer)
        if (self.source_doi != _DOI or self.source_dataset_pid != _DATASET_PID
                or self.source_file_pid != _MATRIX_FILE_PID
                or self.source_filename != _MATRIX_FILENAME or self.license_id != _LICENSE
                or self.source_md5 != _MATRIX_MD5 or self.source_sha256 != _MATRIX_SHA256
                or self.source_size_bytes != _MATRIX_SIZE or self.sheet_name != _SHEET
                or self.title_note != _TITLE_CELL or tuple(self.headers) != _HEADERS):
            raise ValueError("Matrix provenance differs from the admitted DataverseNO source")
        rows = tuple(tuple(row) for row in self.rows)
        experiments = tuple(self.experiments)
        if (len(rows) != 40 or len(experiments) != 40
                or tuple(row[0] for row in rows) != tuple(range(1, 41))
                or tuple(item.experiment_number for item in experiments) != tuple(range(1, 41))):
            raise ValueError("The admitted version-1 matrix must preserve experiment rows 1 through 40")
        object.__setattr__(self, "headers", tuple(self.headers))
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "experiments", experiments)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "_seal", self._fingerprint())

    def _fingerprint(self):
        return hashlib.sha256(repr((
            self.source_doi, self.source_dataset_pid, self.source_file_pid,
            self.source_filename, self.license_id, self.source_md5,
            self.source_sha256, self.source_size_bytes, self.sheet_name,
            self.title_note, self.headers, self.rows, self.experiments,
        )).encode("utf-8")).hexdigest()

    def require_current(self):
        if self._seal != self._fingerprint():
            raise ValueError("Source matrix contents changed after reader issuance")
        return self

    def experiment(self, experiment_number: int) -> IgnitedJetExperiment:
        self.require_current()
        if isinstance(experiment_number, bool) or not isinstance(experiment_number, int):
            raise ValueError("experiment_number must be an integer")
        if not 1 <= experiment_number <= len(self.experiments):
            raise ValueError("Experiment number is outside the published matrix")
        return self.experiments[experiment_number - 1]

    def summary(self) -> dict[str, float | int]:
        """Return descriptive extrema of publisher-reported matrix columns only."""
        self.require_current()
        return {
            "experiment_rows": len(self.experiments),
            "max_reported_pressure_bar": max(x.reported_max_pressure_bar for x in self.experiments),
            "max_pressure_derived_mfr_kg_s": max(
                x.pressure_derived_max_mass_flow_kg_s for x in self.experiments
            ),
            "max_reported_average_pressure_bar": max(
                x.reported_average_pressure_bar for x in self.experiments
            ),
            "max_pressure_derived_average_mfr_kg_s": max(
                x.pressure_derived_average_mass_flow_kg_s for x in self.experiments
            ),
        }


def load_ignited_hydrogen_jet_matrix(path: str | Path) -> IgnitedHydrogenJetMatrix:
    """Read the exact public condition matrix after byte-level source checks.

    The 40-row sheet is a condition/summary table. Its title states that mass
    flow is calculated from experimental pressure; these are not independent
    direct flow measurements. Pressure absolute/gauge basis is not declared in
    the matrix and therefore remains unresolved.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    md5, sha256, size = _hash_file(path)
    if (size != _MATRIX_SIZE or md5 != _MATRIX_MD5 or sha256 != _MATRIX_SHA256):
        raise ValueError("Matrix bytes do not match the pinned public DataverseNO attachment")

    from openpyxl import load_workbook

    cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    formulas = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        if _SHEET not in cached.sheetnames or _SHEET not in formulas.sheetnames:
            raise ValueError("Matrix worksheet name differs from the reviewed source")
        sheet, formula_sheet = cached[_SHEET], formulas[_SHEET]
        title = sheet.cell(1, 1).value
        header = tuple(cell.value for cell in next(
            sheet.iter_rows(min_row=2, max_row=2, max_col=len(_HEADERS), values_only=False)
        ))
        if title != _TITLE_CELL or header != _HEADERS:
            raise ValueError("Matrix title or exact source headers changed")
        row_values: list[tuple[object, ...]] = []
        experiment_rows: list[IgnitedJetExperiment] = []
        for row_number in range(3, 43):
            cells = tuple(cell.value for cell in next(formula_sheet.iter_rows(
                min_row=row_number, max_row=row_number, max_col=len(_HEADERS), values_only=False
            )))
            cached_cells = tuple(cell.value for cell in next(sheet.iter_rows(
                min_row=row_number, max_row=row_number, max_col=len(_HEADERS), values_only=False
            )))
            if any(cell.data_type == "f" for cell in next(formula_sheet.iter_rows(
                    min_row=row_number, max_row=row_number, max_col=len(_HEADERS), values_only=False
            ))):
                raise ValueError("Formula cells are not evaluated or admitted as reported data")
            if cells != cached_cells or len(cells) != len(_HEADERS):
                raise ValueError("Formula and cached workbook views disagree")
            number = cells[0]
            if isinstance(number, bool) or not isinstance(number, int) or number != row_number - 2:
                raise ValueError("Experiment row identity is missing, duplicated, or out of order")

            def number_at(index: int, label: str) -> float:
                value = cells[index]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"{label} must be a numeric source cell")
                value = float(value)
                if not math.isfinite(value):
                    raise ValueError(f"{label} must be finite")
                return value

            ignition = number_at(5, "ignition location code")
            if ignition != int(ignition):
                raise ValueError("Ignition location code must retain its integral value")
            obstacle = cells[6]
            if isinstance(obstacle, bool) or not isinstance(obstacle, (int, float, str)):
                raise ValueError("Obstacle distance must remain a numeric or text source token")
            if isinstance(obstacle, float) and not math.isfinite(obstacle):
                raise ValueError("Obstacle distance numeric source cell must be finite")
            comment = cells[9]
            if comment is not None and not isinstance(comment, str):
                raise ValueError("Comment must retain its source text or blank value")
            row_values.append(cells)
            experiment_rows.append(IgnitedJetExperiment(
                source_row_id=f"{_MATRIX_FILE_PID}:{_SHEET}:row-{row_number}",
                experiment_number=number,
                reported_max_pressure_bar=number_at(1, "maximum reported pressure [bar]"),
                pressure_derived_max_mass_flow_kg_s=number_at(2, "maximum pressure-derived MFR [kg/s]"),
                reported_average_pressure_bar=number_at(3, "average reported pressure [bar]"),
                pressure_derived_average_mass_flow_kg_s=number_at(4, "average pressure-derived MFR [kg/s]"),
                ignition_location_code=int(ignition), obstacle_distance_raw=obstacle,
                hydrogen_release_time_s=number_at(7, "hydrogen release time [s]"),
                ignition_delay_time_s=number_at(8, "ignition delay time [s]"),
                comment=comment, raw_cells=cells,
            ))
        matrix = _issue(
            source_doi=_DOI, source_dataset_pid=_DATASET_PID,
            source_file_pid=_MATRIX_FILE_PID, source_filename=_MATRIX_FILENAME,
            license_id=_LICENSE, source_md5=md5, source_sha256=sha256,
            source_size_bytes=size, sheet_name=_SHEET, title_note=title,
            headers=header, rows=tuple(row_values), experiments=tuple(experiment_rows),
        )
    finally:
        cached.close()
        formulas.close()
    if _hash_file(path) != (md5, sha256, size):
        raise ValueError("Matrix source changed during workbook reading")
    return matrix

