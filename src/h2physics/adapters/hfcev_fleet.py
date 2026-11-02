"""Compare an attributed public fleet H2-consumption window to a finite model trace."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite

from ..data.hfcev_fleet import HFCEVOperationSample, SAMPLE_SHA256
from .fuel_cell import FuelCellTrace


_PENDING: set[object] = set()


def _window(sample, start, end):
    if type(sample) is not HFCEVOperationSample or sample.source_sha256 != SAMPLE_SHA256:
        raise TypeError("Supply the checksum-pinned HFCEV sample reader result")
    sample.require_current()
    start_dt = datetime.fromisoformat(start) if isinstance(start, str) else start
    end_dt = datetime.fromisoformat(end) if isinstance(end, str) else end
    if type(start_dt) is not datetime or type(end_dt) is not datetime or start_dt >= end_dt:
        raise ValueError("Supply increasing naive publisher receipt-time edges")
    if start_dt.tzinfo is not None or end_dt.tzinfo is not None:
        raise ValueError("The publisher sample uses naive receipt timestamps; do not attach an unverified zone")
    rows = sample.rows
    left_matches = [i for i, row in enumerate(rows) if row.receipt_time == start_dt]
    right_matches = [i for i, row in enumerate(rows) if row.receipt_time == end_dt]
    if len(left_matches) != 1 or len(right_matches) != 1:
        raise ValueError("Receipt-time edges must identify exactly one source row each")
    left, right = left_matches[0], right_matches[0]
    if right <= left:
        raise ValueError("Window boundaries must match actual publisher rows exactly")
    selected = rows[left:right + 1]
    if (len({(row.vehicle_id, row.unit, row.segment) for row in selected}) != 1
            or any(a.receipt_time >= b.receipt_time for a, b in zip(selected, selected[1:]))):
        raise ValueError("A source window must stay within one vehicle, TBOX unit and reported segment")
    intervals = []
    masses = []
    for row_index in range(left + 1, right + 1):
        row = rows[row_index]
        if ((row.missing_mask & (1 << 26)) != 0
                or (row.counter_backward_mask & (1 << 1)) != 0
                or not row.h2_attributed or row.h2_increment_kg is None):
            raise ValueError("Each included TotH2Kg increment must be present, forward and source-attributed")
        if row.h2_increment_kg < 0:
            raise ValueError("A source-attributed H2 increment cannot be negative")
        previous_index = next((j for j in range(row_index - 1, -1, -1)
                               if rows[j].unit == row.unit
                               and rows[j].h2_kg_restored is not None
                               and (rows[j].missing_mask & (1 << 26)) == 0), None)
        if previous_index is None or previous_index < left:
            raise ValueError("The included H2 increment starts before the selected window or lacks a valid previous counter")
        if previous_index != row_index - 1:
            raise ValueError("A non-adjacent previous-counter increment can overlap intervening rows")
        previous = rows[previous_index]
        if ((previous.missing_mask & (1 << 26)) != 0
                or (previous.counter_backward_mask & (1 << 1)) != 0
                or previous.unit != row.unit or previous.segment != row.segment
                or previous.receipt_time >= row.receipt_time):
            raise ValueError("H2 increment interval must stay within one unit and source segment")
        intervals.append((previous_index, row_index))
        masses.append(row.h2_increment_kg)
    mass = sum(masses)
    if not isfinite(mass) or mass < 0:
        raise ValueError("Attributed H2 mass must be finite and nonnegative")
    return selected, mass, (end_dt - start_dt).total_seconds(), tuple(intervals)


@dataclass(frozen=True, slots=True)
class HFCEVHydrogenConsumptionWindow:
    sample: HFCEVOperationSample
    start_receipt_time: datetime
    end_receipt_time: datetime
    source_rows: tuple[int, ...]
    source_interval_rows: tuple[tuple[int, int], ...]
    measured_h2_consumed_kg: float
    elapsed_receipt_s: float
    window_selection_evidence_id: str
    _token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue this window through select_hfcev_hydrogen_window")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.sample), self.start_receipt_time, self.end_receipt_time,
                self.source_rows, self.measured_h2_consumed_kg, self.elapsed_receipt_s,
                self.source_interval_rows, self.window_selection_evidence_id)

    @property
    def source_sha256(self):
        return self.sample.source_sha256

    def require_current(self):
        if self._current() != self._binding:
            raise ValueError("HFCEV observation window lost its issued source binding")
        rows, mass, elapsed, intervals = _window(self.sample, self.start_receipt_time, self.end_receipt_time)
        expected_rows = tuple(self.sample.rows.index(row) for row in rows)
        if (expected_rows != self.source_rows or mass != self.measured_h2_consumed_kg
                or elapsed != self.elapsed_receipt_s):
            raise ValueError("HFCEV observation no longer replays from the pinned source rows")
        if intervals != self.source_interval_rows:
            raise ValueError("HFCEV increment-to-previous-counter interval mapping changed")
        return self


@dataclass(frozen=True, slots=True)
class HFCEVTimeAlignment:
    """Caller-owned endpoint map from receipt-time window to model seconds."""

    source_start_receipt_time: datetime
    source_end_receipt_time: datetime
    model_start_s: float
    model_end_s: float
    evidence_id: str
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if (type(self.source_start_receipt_time) is not datetime
                or type(self.source_end_receipt_time) is not datetime
                or self.source_start_receipt_time.tzinfo is not None
                or self.source_end_receipt_time.tzinfo is not None
                or self.source_start_receipt_time >= self.source_end_receipt_time):
            raise ValueError("Declare increasing naive source receipt-time endpoints")
        if (type(self.model_start_s) not in {int, float}
                or type(self.model_end_s) not in {int, float}):
            raise TypeError("Model time endpoints must be numeric seconds")
        start_s, end_s = float(self.model_start_s), float(self.model_end_s)
        if (not isfinite(start_s) or not isfinite(end_s) or start_s >= end_s):
            raise ValueError("Declare increasing finite model-second endpoints")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Identify external clock-alignment evidence")
        object.__setattr__(self, "model_start_s", start_s)
        object.__setattr__(self, "model_end_s", end_s)
        object.__setattr__(self, "evidence_id", self.evidence_id.strip())
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (self.source_start_receipt_time, self.source_end_receipt_time,
                self.model_start_s, self.model_end_s, self.evidence_id)

    def require_current(self):
        if self._current() != self._binding:
            raise ValueError("HFCEV source-to-model time map was modified after creation")
        return self


@dataclass(frozen=True, slots=True)
class HFCEVFuelCellComparison:
    observation: HFCEVHydrogenConsumptionWindow
    model_trace: FuelCellTrace
    modeled_h2_consumed_kg: float
    residual_kg: float
    time_alignment: HFCEVTimeAlignment
    _token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue comparisons through compare_hfcev_hydrogen_consumption")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.observation), id(self.model_trace), self.modeled_h2_consumed_kg,
                self.residual_kg, id(self.time_alignment))

    def require_current(self):
        if self._current() != self._binding:
            raise ValueError("HFCEV comparison lost its issued binding")
        self.observation.require_current()
        self.model_trace.require_current()
        self.time_alignment.require_current()
        model_duration = (self.model_trace.steps[-1].command.end_s
                          - self.model_trace.steps[0].command.start_s)
        if (self.time_alignment.source_start_receipt_time != self.observation.start_receipt_time
                or self.time_alignment.source_end_receipt_time != self.observation.end_receipt_time
                or self.time_alignment.model_start_s != self.model_trace.steps[0].command.start_s
                or self.time_alignment.model_end_s != self.model_trace.steps[-1].command.end_s
                or model_duration != self.observation.elapsed_receipt_s
                or self.time_alignment.model_end_s - self.time_alignment.model_start_s
                   != self.observation.elapsed_receipt_s):
            raise ValueError("Explicit source/model endpoint map no longer matches the accepted windows")
        model_mass = (self.model_trace.hydrogen_consumed_mol
                      * self.model_trace.stack.geometry.hydrogen_molar_mass_kg_mol)
        if (model_mass != self.modeled_h2_consumed_kg
                or self.observation.measured_h2_consumed_kg - model_mass != self.residual_kg):
            raise ValueError("HFCEV comparison no longer reproduces from its source and model trace")
        return self


def select_hfcev_hydrogen_window(sample: HFCEVOperationSample, *, start_receipt_time: str,
                                  end_receipt_time: str,
                                  window_selection_evidence_id: str) -> HFCEVHydrogenConsumptionWindow:
    """Select exact-edge, attributed mass increments within one reported segment.

    The reader's server receipt timestamps are retained. This function does not
    treat them as device event time, infer a missing interval, or use voltage,
    current, or pressure to derive hydrogen consumption.
    """
    if (not isinstance(window_selection_evidence_id, str)
            or not window_selection_evidence_id.strip()):
        raise ValueError("Identify the receipt-time window selection basis")
    start = datetime.fromisoformat(start_receipt_time)
    end = datetime.fromisoformat(end_receipt_time)
    rows, mass, elapsed, intervals = _window(sample, start, end)
    token = object()
    _PENDING.add(token)
    return HFCEVHydrogenConsumptionWindow(sample, start, end,
        tuple(sample.rows.index(row) for row in rows), intervals, mass, elapsed,
        window_selection_evidence_id.strip(), token)


def compare_hfcev_hydrogen_consumption(observation: HFCEVHydrogenConsumptionWindow,
                                       model_trace: FuelCellTrace, *,
                                       time_alignment: HFCEVTimeAlignment) -> HFCEVFuelCellComparison:
    """Compare total H2 mass only after caller-provided clock/boundary alignment."""
    if type(observation) is not HFCEVHydrogenConsumptionWindow:
        raise TypeError("Supply an issued source observation window")
    if type(model_trace) is not FuelCellTrace:
        raise TypeError("Supply a current result from the existing FiniteFuelCell model")
    if type(time_alignment) is not HFCEVTimeAlignment:
        raise TypeError("Supply an explicit typed source-receipt to model-time endpoint map")
    observation.require_current()
    model_trace.require_current()
    time_alignment.require_current()
    model_duration = model_trace.steps[-1].command.end_s - model_trace.steps[0].command.start_s
    if (time_alignment.source_start_receipt_time != observation.start_receipt_time
            or time_alignment.source_end_receipt_time != observation.end_receipt_time
            or time_alignment.model_start_s != model_trace.steps[0].command.start_s
            or time_alignment.model_end_s != model_trace.steps[-1].command.end_s
            or model_duration != observation.elapsed_receipt_s
            or time_alignment.model_end_s - time_alignment.model_start_s
               != observation.elapsed_receipt_s):
        raise ValueError("The caller time map must match exact source/model endpoints and elapsed duration")
    modeled = (model_trace.hydrogen_consumed_mol
               * model_trace.stack.geometry.hydrogen_molar_mass_kg_mol)
    residual = observation.measured_h2_consumed_kg - modeled
    token = object()
    _PENDING.add(token)
    return HFCEVFuelCellComparison(observation, model_trace, modeled, residual,
                                   time_alignment, token)
