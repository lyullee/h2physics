"""Pointwise vent-composition comparison against the existing oxygen-room model."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from ..data.elvhys41 import ELVHYS41ConcentrationSample, ELVHYS41ConcentrationRow
from .oxygen_deficiency import OxygenRoomResult, verify_oxygen_room_result


_PENDING: set[object] = set()


def _positive_rows(sample, source_row_indices):
    if type(sample) is not ELVHYS41ConcentrationSample:
        raise TypeError("Supply the issued CC0 ELVHYS 4.1 concentration sample")
    sample.require_current()
    indices = tuple(source_row_indices)
    if (not indices or any(type(i) is not int for i in indices)
            or tuple(sorted(set(indices))) != indices):
        raise ValueError("Select ordered, unique integer source row indices")
    selected = []
    for index in indices:
        if index < 0 or index >= len(sample.rows):
            raise IndexError("Selected ELVHYS source row is outside the acquired file")
        row = sample.rows[index]
        if type(row) is not ELVHYS41ConcentrationRow or row.row_index != index:
            raise ValueError("Selected row no longer matches the issued sample table")
        o2, h2 = row.oxygen_vol_percent, row.hydrogen_vol_percent
        if o2 < 0.0 or h2 < 0.0 or o2 > 100.0 or h2 > 100.0 or o2 + h2 > 100.000001:
            raise ValueError("Raw sensor values are not a physically admissible gas composition; values are never clipped")
        selected.append(row)
    return tuple(selected)


def _compare(sample, result, rows, *, model_time_offset_s,
             vent_to_region_evidence_id, volume_state_evidence_id,
             composition_basis_evidence_id, clock_alignment_evidence_id):
    sample.require_current()
    if type(result) is not OxygenRoomResult:
        raise TypeError("Supply a current native OxygenRoomResult")
    verify_oxygen_room_result(result)
    if not all(name in result.species_names for name in ("O2", "H2")):
        raise ValueError("The native room mechanism must retain both H2 and O2")
    if (type(model_time_offset_s) not in {int, float}
            or not isfinite(float(model_time_offset_s))):
        raise ValueError("Declare a finite source-to-model time offset in seconds")
    if any(not isinstance(value, str) or not value.strip() for value in (
            vent_to_region_evidence_id, volume_state_evidence_id,
            composition_basis_evidence_id, clock_alignment_evidence_id)):
        raise ValueError("Declare vent-to-region, volume/state, gas-fraction and clock evidence")
    offset = float(model_time_offset_s)
    snapshots_by_time = {}
    for snapshot in result.snapshots:
        snapshots_by_time.setdefault(float(snapshot.time_s), []).append(snapshot)
    points = []
    for row in rows:
        target = row.time_s + offset
        candidates = snapshots_by_time.get(target, ())
        if len(candidates) != 1:
            raise ValueError("Every selected source time needs exactly one model snapshot; no interpolation is allowed")
        snapshot = candidates[0]
        model_o2 = float(snapshot.mole_fractions["O2"])
        model_h2 = float(snapshot.mole_fractions["H2"])
        points.append((row.row_index, row.time_s, row.oxygen_vol_percent / 100.0,
                       row.hydrogen_vol_percent / 100.0, model_o2, model_h2,
                       row.oxygen_vol_percent / 100.0 - model_o2,
                       row.hydrogen_vol_percent / 100.0 - model_h2))
    return tuple(points)


@dataclass(frozen=True, slots=True)
class ELVHYS41CompositionComparison:
    sample: ELVHYS41ConcentrationSample
    room_result: OxygenRoomResult
    source_row_indices: tuple[int, ...]
    points: tuple[tuple[int, float, float, float, float, float, float, float], ...]
    model_time_offset_s: float
    vent_to_region_evidence_id: str
    volume_state_evidence_id: str
    composition_basis_evidence_id: str
    clock_alignment_evidence_id: str
    _token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue comparisons through compare_elvhys41_vent_composition")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.sample), id(self.room_result), self.source_row_indices, self.points,
                self.model_time_offset_s, self.vent_to_region_evidence_id,
                self.volume_state_evidence_id, self.composition_basis_evidence_id,
                self.clock_alignment_evidence_id)

    def require_current(self):
        if self._current() != self._binding:
            raise ValueError("ELVHYS 4.1 comparison lost its issued binding")
        selected = _positive_rows(self.sample, self.source_row_indices)
        actual = _compare(self.sample, self.room_result, selected,
                          model_time_offset_s=self.model_time_offset_s,
                          vent_to_region_evidence_id=self.vent_to_region_evidence_id,
                          volume_state_evidence_id=self.volume_state_evidence_id,
                          composition_basis_evidence_id=self.composition_basis_evidence_id,
                          clock_alignment_evidence_id=self.clock_alignment_evidence_id)
        if actual != self.points:
            raise ValueError("ELVHYS 4.1 residuals no longer replay from current model and source")
        return self


def compare_elvhys41_vent_composition(
        sample: ELVHYS41ConcentrationSample, room_result: OxygenRoomResult, *,
        source_row_indices: tuple[int, ...], model_time_offset_s: float,
        vent_to_region_evidence_id: str, volume_state_evidence_id: str,
        composition_basis_evidence_id: str, clock_alignment_evidence_id: str,
) -> ELVHYS41CompositionComparison:
    """Compare raw admitted O2/H2 vent observations without fitting or time interpolation.

    The caller must support the mapping from the vent sample to the modeled
    homogeneous region and the source/model clock offset. Negative or over-range
    sensor readings are retained by the reader and rejected from comparison.
    """
    rows = _positive_rows(sample, source_row_indices)
    points = _compare(sample, room_result, rows,
                      model_time_offset_s=model_time_offset_s,
                      vent_to_region_evidence_id=vent_to_region_evidence_id,
                      volume_state_evidence_id=volume_state_evidence_id,
                      composition_basis_evidence_id=composition_basis_evidence_id,
                      clock_alignment_evidence_id=clock_alignment_evidence_id)
    token = object()
    _PENDING.add(token)
    return ELVHYS41CompositionComparison(
        sample, room_result, tuple(source_row_indices), points, float(model_time_offset_s),
        vent_to_region_evidence_id.strip(), volume_state_evidence_id.strip(),
        composition_basis_evidence_id.strip(), clock_alignment_evidence_id.strip(), token,
    )
