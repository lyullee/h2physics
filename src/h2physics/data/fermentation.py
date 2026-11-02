"""Source-specific dark-fermentation observations; no inferred growth or gas basis.

Roberto Hernández, https://doi.org/10.17632/2nwcdx9hst.2, CC BY 4.0.
Publisher-calculated columns and source formulas are not independent measurements.
"""

import math
import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np

from ..core import Origin
from ..observations import ObservationTable, Variable
from ..units import convert_to_si
from .pressure_peaking import file_sha256

PROFILE_ID = "dark-fermentation-v2-profile-1"
SOURCE_SHA256 = "f13352e6ae633878aa7cf47a9b7d79f859ad815cda24000c11f04abf32b60729"
DAY_S = 86400.
LITRE_PER_DAY_TO_M3_PER_S = 1e-3 / DAY_S
GAS_BASIS = "source reported gas volume; pressure/temperature/wet-dry/reference state unresolved"
FRACTION_BASIS = "source gas vol%; sampling/wet-dry/normalization to listed gases unresolved"
HEADERS = ("Nr.", "R", "Duration (d)", "Temperature (°C)", "pH", "HRT (d)", "BP (L/d)",
    "CO2 (vol%)", "CH4 (vol%)", "H2 (vol%)", "HP (L/d)", "HY (L/g)", "HPR (L/(L/d))",
    "MP (L/d)", "MPR (L/(L/d))", "OLR (COD) (g/L/d)", "COD in (g/L)", "COD out  (g/L)",
    "Hac (g/L)", "HPr_1 (g/L)", "Hbu (g/L)", "Hva (g/L)", "Hca (g/L)", "tVFA (g/L)")
DERIVED_COLUMNS = frozenset((10, 11, 12, 13, 14))
ORIGINS = (Origin.RECONSTRUCTED,) * 3 + (Origin.MEASURED,) * 2 + (Origin.UNRESOLVED,
    Origin.MEASURED, Origin.MEASURED, Origin.MEASURED, Origin.MEASURED) + (
    Origin.RECONSTRUCTED,) * 5 + (Origin.UNRESOLVED,) + (Origin.MEASURED,) * 8
_PENDING_BLOCK_ISSUERS: set[object] = set()


def _issue_block(**values):
    token = object()
    _PENDING_BLOCK_ISSUERS.add(token)
    try:
        return FermentationBlock(**values, _issuer_token=token)
    except Exception:
        _PENDING_BLOCK_ISSUERS.discard(token)
        raise


def _numeric(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), "" if math.isfinite(value) else "source_nonfinite"
    if value is None:
        return math.nan, "source_blank"
    if isinstance(value, str):
        text = value.strip()
        if text == "--":
            return math.nan, "source_missing_placeholder"
        if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
            number = float(text)
            return number, "" if math.isfinite(number) else "source_nonfinite"
    return math.nan, "source_nonnumeric"


def _reactor_label(value):
    number, _ = _numeric(value)
    return f"R-{int(number)}" if math.isfinite(number) and number > 0 and number.is_integer() else "R-unresolved"


def fermentation_variables(clock_id):
    return (
        Variable("source_nr", "source_record_number", "1"),
        Variable("reactor_code", "reported_reactor_identifier", "1"),
        Variable("duration_s", "reported_duration", "s", clock_id),
        Variable("temperature", "temperature", "K", "source reactor temperature; sensor/location unresolved"),
        Variable("pH", "reported_pH", "1", "source pH; measurement/medium activity convention unresolved"),
        Variable("HRT_s", "reported_hydraulic_retention_time", "s",
                 "source HRT in days; working volume/feed-flow/averaging unresolved"),
        Variable("BP", "reported_total_gas_volume_rate", "m3_reported/s", GAS_BASIS),
        *(Variable(name, "reported_gas_volume_fraction", "1", FRACTION_BASIS) for name in ("CO2", "CH4", "H2")),
        Variable("HP", "reported_component_gas_volume_rate", "m3_reported/s", GAS_BASIS + "; H2; publisher-derived"),
        Variable("HY", "reported_specific_gas_volume", "m3_reported/kg_reported",
                 GAS_BASIS + "; source L/g; substrate/COD/added/consumed mass denominator unresolved"),
        Variable("HPR", "reported_hydrogen_productivity", "source L/(L/d)",
                 "literal printed unit retained; intended normalization/volume unresolved"),
        Variable("MP", "reported_component_gas_volume_rate", "m3_reported/s", GAS_BASIS + "; CH4; publisher-derived"),
        Variable("MPR", "reported_methane_productivity", "source L/(L/d)",
                 "literal printed unit retained; intended normalization/volume unresolved"),
        Variable("OLR_COD", "reported_cod_loading_rate", "kg_COD/(m3*s)",
                 "source COD g/L/d; liquid/reactor-volume denominator and feeding averaging unresolved"),
        *(Variable(name, "reported_cod_concentration", "kg_COD/m3",
                   "source COD g/L; soluble/total and analytical basis unresolved; not substrate species mass")
          for name in ("COD_in", "COD_out")),
        *(Variable(name, "reported_component_concentration", "kg/m3",
                   f"source {name} g/L; analyte/speciation and analytical basis unresolved")
          for name in ("Hac", "HPr_1", "Hbu", "Hva", "Hca", "tVFA")),
    )


@dataclass(frozen=True, slots=True)
class FermentationIssue:
    code: str
    source_row: int
    column: str


@dataclass(frozen=True, slots=True)
class FermentationBlock:
    observations: ObservationTable
    source_rows: tuple[int, ...]
    raw_cells: tuple[tuple[object, ...], ...]
    formula_cells: tuple[tuple[str, str], ...]
    invalid_reasons: tuple[tuple[str, ...], ...]
    reactor_id: str
    issues: tuple[FermentationIssue, ...]
    _issuer_token: object = field(default=None, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_BLOCK_ISSUERS:
            raise ValueError("Fermentation blocks must be issued by the qualified workbook reader")
        _PENDING_BLOCK_ISSUERS.remove(self._issuer_token)
        object.__setattr__(self, "_issuer_token", None)
        for name in ("source_rows", "raw_cells", "formula_cells", "invalid_reasons", "issues"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "_seal", self._content_fingerprint())

    def _content_fingerprint(self):
        return hashlib.sha256(repr((self.observations.content_sha256, self.source_rows,
            self.raw_cells, self.formula_cells, self.invalid_reasons, self.reactor_id,
            self.issues)).encode("utf-8")).hexdigest()

    def require_current(self):
        if self._content_fingerprint() != self._seal:
            raise ValueError("Fermentation source block changed after reader issuance")
        return self

    def as_time_series(self):
        raise ValueError("Duration is a per-reactor reported day coordinate; no automatic clock repair/TimeSeries")


class FermentationWorkbook:
    """One reviewed worksheet, streamed into blocks that never mix reactor clocks.

    All reactors remain in one study experiment group: independent replicate or
    held-out-study status is not established by the R column.
    """

    def __init__(self, path: str | Path, *, source_id: str, study_id: str,
                 expected_sha256: str = SOURCE_SHA256, maximum_bytes: int = 4_000_000,
                 maximum_expanded_bytes: int = 16_000_000, maximum_rows: int = 10_000):
        if not all(isinstance(value, str) and value.strip() for value in (source_id, study_id, expected_sha256)):
            raise ValueError("Declare source, study and expected source SHA-256")
        for value in (maximum_bytes, maximum_expanded_bytes, maximum_rows):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("Workbook budgets must be positive integers")
        self.path, self.source_id, self.study_id = Path(path), source_id, study_id
        self.expected_sha256 = expected_sha256
        self.maximum_bytes, self.maximum_expanded_bytes, self.maximum_rows = maximum_bytes, maximum_expanded_bytes, maximum_rows
        self._cached = self._formulas = None

    def __enter__(self):
        from openpyxl import load_workbook

        if self.path.stat().st_size > self.maximum_bytes:
            raise ValueError("Workbook compressed bytes exceed budget")
        self.sha256 = file_sha256(self.path)
        if self.sha256 != self.expected_sha256:
            raise ValueError("Fermentation workbook SHA-256 differs from receipt")
        with ZipFile(self.path) as archive:
            infos = archive.infolist()
            if (len(infos) > 200 or len({i.filename for i in infos}) != len(infos)
                    or sum(i.file_size for i in infos) > self.maximum_expanded_bytes):
                raise ValueError("Workbook expanded bytes/member count exceed budget")
            for item in infos:
                if (".." in PurePosixPath(item.orig_filename).parts or ":" in item.orig_filename
                        or "\\" in item.orig_filename or item.orig_filename.startswith("/")
                        or item.flag_bits & 1 or item.file_size > self.maximum_expanded_bytes):
                    raise ValueError("Unreviewed workbook ZIP member")
        self._cached = load_workbook(self.path, read_only=True, data_only=True, keep_links=False)
        try:
            self._formulas = load_workbook(self.path, read_only=True, data_only=False, keep_links=False)
            if self._cached.sheetnames != ["Data"] or self._formulas.sheetnames != ["Data"]:
                raise ValueError("Unreviewed fermentation worksheet identity")
            sheet = self._cached["Data"]
            if sheet.max_column != 24 or not 2 <= sheet.max_row <= self.maximum_rows:
                raise ValueError("Unreviewed fermentation dimensions")
            if next(sheet.iter_rows(max_row=1, values_only=True)) != HEADERS:
                raise ValueError("Literal fermentation column headers/units differ")
            self.source_last_row = sheet.max_row
            return self
        except Exception:
            self._cached.close()
            if self._formulas:
                self._formulas.close()
            raise

    def __exit__(self, *args):
        self._cached.close()
        self._formulas.close()
        self._cached = self._formulas = None
        if file_sha256(self.path) != self.sha256:
            raise ValueError("Fermentation workbook changed during observation decoding")

    def iter_blocks(self, *, block_rows: int = 128, first_row: int = 2,
                    last_row: int | None = None) -> Iterator[FermentationBlock]:
        if self._cached is None:
            raise ValueError("Consume observations inside the source context manager")
        if isinstance(block_rows, bool) or not isinstance(block_rows, int) or not 1 <= block_rows <= 1000:
            raise ValueError("block_rows must be an integer in [1, 1000]")
        last = self.source_last_row if last_row is None else last_row
        if (any(isinstance(v, bool) or not isinstance(v, int) for v in (first_row, last))
                or first_row < 2 or last < first_row or last > self.source_last_row):
            raise ValueError("Source row window lies outside the worksheet")
        cached = self._cached["Data"].iter_rows(min_row=first_row, max_row=last, max_col=24)
        formulas = self._formulas["Data"].iter_rows(min_row=first_row, max_row=last, max_col=24)
        raw, expressions, numbers, reasons, source_rows, issues = [], [], [], [], [], []
        current, previous = None, {}

        def block():
            clock_id = f"{self.source_id}|{self.sha256}|Data|{current}|source Duration(d); day-zero/continuity unresolved"
            variables = fermentation_variables(clock_id)
            values = np.asarray(numbers, dtype=float)
            values[:, 2] *= DAY_S
            values[:, 3] = convert_to_si(values[:, 3], quantity="temperature", unit="degC")
            values[:, 5] *= DAY_S
            values[:, (6, 10, 13)] *= LITRE_PER_DAY_TO_M3_PER_S
            values[:, 7:10] *= .01
            # 1 L/g = 1 m3/kg: the reported volume/mass bases remain unresolved.
            values[:, 15] /= DAY_S
            valid = np.isfinite(values)
            for i, variable in enumerate(variables):
                if variable.quantity == "temperature":
                    valid[:, i] &= values[:, i] > 0
                if i in (0, 1):
                    valid[:, i] &= (values[:, i] > 0) & (values[:, i] == np.floor(values[:, i]))
                if i == 5:
                    valid[:, i] &= values[:, i] > 0
                if i in (7, 8, 9):
                    valid[:, i] &= (values[:, i] >= 0) & (values[:, i] <= 1)
            finalized = []
            for i, row in enumerate(reasons):
                rr = list(row)
                for j in range(24):
                    if not valid[i, j] and not rr[j]:
                        rr[j] = "outside_declared_column_domain"
                    if rr[j]:
                        valid[i, j] = False
                finalized.append(tuple(rr))
            table = ObservationTable(values, variables, valid,
                tuple(f"{self.source_id}|{self.sha256}|Data|row-{row}" for row in source_rows),
                (self.study_id,) * len(source_rows), ORIGINS, self.source_id,
                (("profile", PROFILE_ID), ("file_sha256", self.sha256), ("source_file", self.path.name),
                 ("worksheet", "Data"), ("reactor_id", current), ("clock_id", clock_id),
                 ("replicate_status", "R labels are reactor identifiers; independent replicates unqualified"),
                 ("experiment_grouping", "all R values share one study; no automatic replicate holdout"),
                 ("gas_basis", GAS_BASIS), ("derived_target_status", "HP/HY/HPR/MP/MPR are not independent measurements")))
            return _issue_block(observations=table, source_rows=tuple(source_rows), raw_cells=tuple(raw),
                                formula_cells=tuple(expressions), invalid_reasons=tuple(finalized),
                                reactor_id=current, issues=tuple(issues))

        for row_number, (cells, expression_cells) in enumerate(zip(cached, formulas, strict=True), first_row):
            original = tuple(cell.value for cell in cells)
            reactor = _reactor_label(original[1])
            if source_rows and reactor != current:
                yield block()
                raw, expressions, numbers, reasons, source_rows, issues = [], [], [], [], [], []
            current = reactor
            converted = [_numeric(value) for value in original]
            values, problems = [c[0] for c in converted], [c[1] for c in converted]
            for column, expression in enumerate(expression_cells):
                if expression.data_type == "f":
                    expressions.append((expression.coordinate, str(expression.value)))
                    if original[column] is None:
                        problems[column] = "source_formula_cache_missing"
                    elif ORIGINS[column] == Origin.MEASURED:
                        problems[column] = "source_formula_cache_not_independent_measurement"
            if math.isfinite(values[2]):
                if reactor in previous and values[2] <= previous[reactor]:
                    issues.append(FermentationIssue("nonincreasing_duration_retained", row_number, "Duration (d)"))
                previous[reactor] = values[2]
            raw.append(original)
            numbers.append(values)
            reasons.append(problems)
            source_rows.append(row_number)
            if len(source_rows) == block_rows:
                yield block()
                raw, expressions, numbers, reasons, source_rows, issues = [], [], [], [], [], []
        if source_rows:
            yield block()


def component_production_check(block: FermentationBlock) -> ObservationTable:
    """Same-export algebra only: BP times reported gas fraction, not reaction validation.

    No density, STP, molar yield, gas/liquid partition or reactor volume is inferred.
    Results retain the parent's rows, study grouping and unresolved gas convention.
    """
    table = block.observations
    block.require_current()
    required = fermentation_variables(table.variables[2].basis_id)
    if table.variables != required:
        raise ValueError("Component check requires the qualified fermentation variable contracts")
    bp, bp_valid = table.column("BP")
    h2, h2_valid = table.column("H2")
    ch4, ch4_valid = table.column("CH4")
    hp, hp_valid = table.column("HP")
    mp, mp_valid = table.column("MP")
    values = np.column_stack((bp * h2, hp - bp * h2, bp * ch4, mp - bp * ch4,
                              table.values[:, 7:10].sum(axis=1) - 1))
    valid = np.column_stack((bp_valid & h2_valid, bp_valid & h2_valid & hp_valid,
                            bp_valid & ch4_valid, bp_valid & ch4_valid & mp_valid,
                            np.all(table.valid[:, 7:10], axis=1)))
    variables = tuple(Variable(name, "reported_component_gas_volume_rate", "m3_reported/s",
                     GAS_BASIS + "; same-export algebra; not an independent measurement")
                     for name in ("H2_from_BP_fraction", "HP_residual", "CH4_from_BP_fraction", "MP_residual")) + (
        Variable("listed_gas_fraction_closure", "reported_fraction_closure", "1", FRACTION_BASIS),)
    return ObservationTable(values, variables, valid, table.row_ids, table.experiment_ids,
        (Origin.RECONSTRUCTED,) * 5, table.source_id,
        table.context + (("operator", "same-export BP*fraction; common reported volume convention only"),
                         ("parent_observations_sha256", table.content_sha256)))
