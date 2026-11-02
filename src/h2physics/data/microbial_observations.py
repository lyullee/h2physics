"""Pinned published MEC potentiostat observations; source semantics stay explicit.

Cerrillo et al., DOI10.5281/zenodo.13981041, CC BY4.0. Only the reported
instrument recording is admitted here. Computed speciation is not a measurement.
"""

import csv
import hashlib
import io
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..core import Origin
from ..observations import ObservationTable
from .loaders import Column, load_observation_table

SOURCE_DOI = "10.5281/zenodo.13981041"
SOURCE_VERSION = "13981041"
SOURCE_SHA256 = "1badd6826fde0a1624c6baa88f79f9c66f801d47d0790a74480944e52c93002b"
SOURCE_RELATIVE_PATH = Path("microbial-nutrient-recovery")/SOURCE_VERSION/"Dataset struvite GEMBESH.xlsx"
SHEET = "Potentiostat_data"
FIRST_DATA_ROW = 3
LAST_DATA_ROW = 32121
HEADERS = ("Time (d)", "I (mA)")
STATUS = "implemented_unverified"
_PENDING_BLOCK_ISSUERS: set[object] = set()


def _issue_current_block(**values):
    token = object()
    _PENDING_BLOCK_ISSUERS.add(token)
    try:
        return MicrobialCurrentBlock(**values, _issuer_token=token)
    except Exception:
        _PENDING_BLOCK_ISSUERS.discard(token)
        raise


@dataclass(frozen=True, slots=True)
class MicrobialCurrentBlock:
    observations: ObservationTable
    source_rows: tuple[int, ...]
    original_cached_cells: tuple[tuple[object, object], ...]
    invalid_tokens: tuple[tuple[int, str, str], ...]
    source_sha256: str = SOURCE_SHA256
    _issuer_token: object = field(default=None, repr=False, compare=False)
    clock_alignment_resolved: bool = field(default=False, init=False)
    electrode_current_role_resolved: bool = field(default=False, init=False)
    independently_validated_hydrogen: bool = field(default=False, init=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_BLOCK_ISSUERS:
            raise ValueError("Use iter_microbial_current() to issue source-bound observation blocks")
        _PENDING_BLOCK_ISSUERS.remove(self._issuer_token)
        if self.source_sha256 != SOURCE_SHA256:
            raise ValueError("MEC observation block must retain the reviewed source digest")
        if type(self.observations) is not ObservationTable:
            raise TypeError("MEC current blocks must retain the shared ObservationTable type")
        rows = tuple(self.source_rows)
        original = tuple(tuple(row) for row in self.original_cached_cells)
        issues = tuple(tuple(issue) for issue in self.invalid_tokens)
        if (not rows or len(rows) != len(original)
                or len(self.observations.values) != len(rows)
                or self.observations.values.shape[1] != 2):
            raise ValueError("MEC block rows, cached cells and observation columns must align")
        expected_source_id = f"{SOURCE_DOI}:{SOURCE_VERSION}:{SHEET}:{SOURCE_SHA256}"
        if (self.observations.source_id != expected_source_id
                or self.observations.origins != (Origin.MEASURED, Origin.MEASURED)
                or self.observations.row_ids != tuple(f"{SHEET}!{row}" for row in rows)):
            raise ValueError("MEC observations must retain their reviewed source rows and identity")
        if any(type(row) is not int or row < FIRST_DATA_ROW or row > LAST_DATA_ROW for row in rows):
            raise ValueError("MEC observation rows must be valid one-based workbook rows")
        for index, cells in enumerate(original):
            if len(cells) != 2:
                raise ValueError("Each MEC source row must retain both cached cells")
            for column, factor in enumerate((86400.0, 0.001)):
                token, reason = _token(cells[column])
                try:
                    expected = float(token) * factor
                except (TypeError, ValueError, OverflowError):
                    expected = math.nan
                is_valid = math.isfinite(expected) and not reason
                if bool(self.observations.valid[index, column]) != is_valid:
                    raise ValueError("MEC observation mask does not match retained source cells")
                if is_valid and self.observations.values[index, column] != expected:
                    raise ValueError("MEC observation values do not match retained source cells")
        object.__setattr__(self, "source_rows", rows)
        object.__setattr__(self, "original_cached_cells", original)
        object.__setattr__(self, "invalid_tokens", issues)


def _token(value):
    if value is None:
        return "nan", "source_blank"
    if isinstance(value, bool):
        return "nan", "source_boolean"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "nan", "source_nonnumeric"
    # The common observation reader owns numeric conversion and finite masks.
    return str(number), "" if math.isfinite(number) else "source_nonfinite"


def _block(rows, original, issues):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(HEADERS)
    writer.writerows(tuple(_token(v)[0] for v in values) for values in original)
    stream.seek(0)
    source_id = SOURCE_DOI+":"+SOURCE_VERSION+":"+SHEET+":"+SOURCE_SHA256
    columns = (
        Column(HEADERS[0], "reported_time_s", "time", "d",
            basis_id="Publisher day coordinate; epoch, phase and synchronization unresolved"),
        Column(HEADERS[1], "reported_current_a", "current", "mA",
            basis_id="Publisher potentiostat I; electrode/port/polarity/sampling meaning unresolved"),
    )
    context = (
        ("source_doi", SOURCE_DOI), ("source_sha256", SOURCE_SHA256),
        ("worksheet", SHEET), ("source_first_row", str(rows[0])),
        ("source_last_row", str(rows[-1])),
        ("clock_alignment", "unresolved; SI scaling is not a synchronized clock"),
        ("current_role", "unresolved; no absolute value, area or electrode mapping inferred"),
        ("experimental_grouping", "source recording only; experiment phases unresolved"),
        ("measurement_processing", "publisher export; filtering/averaging/calibration unresolved"),
        ("hydrogen_status", "not a measured H2 yield or Faraday-efficiency validation"),
    )
    table = load_observation_table(stream, columns=columns,
        experiment_id=SOURCE_DOI+":potentiostat-recording-phase-unresolved",
        source_id=source_id, origins=(Origin.MEASURED, Origin.MEASURED), context=context)
    table = replace(table, row_ids=tuple(f"{SHEET}!{row}" for row in rows))
    return _issue_current_block(
        observations=table,
        source_rows=tuple(rows),
        original_cached_cells=tuple(original),
        invalid_tokens=tuple(issues),
    )


def iter_microbial_current(raw_root: Path, *, block_rows: int = 2048):
    """Read original row-ordered current observations using the shared SI reader.

    The published half-megabyte workbook is pinned in an immutable byte snapshot
    before opening. No formula, macro, link, model, native current or fit is run.
    Invalid rows remain masked; repeated/backward source coordinates are retained.
    This does not return a TimeSeries or assign an experimental electrode area.
    """
    if type(block_rows) is not int or block_rows <= 0:
        raise ValueError("Supply a positive integer observation block size")
    path = Path(raw_root)/SOURCE_RELATIVE_PATH
    with path.open("rb") as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Published MEC workbook SHA-256/size does not match the reviewed source")
    from openpyxl import load_workbook

    book = load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    try:
        sheet = book[SHEET]
        header = next(sheet.iter_rows(min_row=2, max_row=2, min_col=1, max_col=2, values_only=True))
        if tuple(header) != HEADERS or sheet.max_row != LAST_DATA_ROW:
            raise ValueError("Pinned published instrument sheet/header/support changed")
        rows, original, issues = [], [], []
        for number, cells in enumerate(sheet.iter_rows(min_row=FIRST_DATA_ROW, max_row=LAST_DATA_ROW,
                                                      min_col=1, max_col=2, values_only=True), FIRST_DATA_ROW):
            values = tuple(cells)
            rows.append(number)
            original.append(values)
            for column, value in zip(HEADERS, values, strict=True):
                reason = _token(value)[1]
                if reason:
                    issues.append((number, column, reason))
            if len(rows) == block_rows:
                yield _block(rows, original, issues)
                rows, original, issues = [], [], []
        if rows:
            yield _block(rows, original, issues)
    finally:
        book.close()
