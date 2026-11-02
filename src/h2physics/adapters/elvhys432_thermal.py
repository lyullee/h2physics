"""Source-to-model observation comparison for an explicit radial wall mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from ..data.elvhys432 import ELVHYS432TemperatureSample, ELVHYS432TemperatureRow
from ..materials.radial_heat import RadialHeatResult


_PENDING: set[object] = set()


def _evaluate(sample, result, row_indices, *, surface, model_time_offset_s,
              sensor_location_evidence_id, pipe_to_domain_evidence_id,
              clock_alignment_evidence_id):
    sample.require_current()
    if type(result) is not RadialHeatResult:
        raise TypeError("Supply the actual native radial cylinder heat result")
    result.require_current()
    if surface not in {"inner", "outer"}:
        raise ValueError("Select the radial model surface explicitly")
    if type(model_time_offset_s) not in {int, float} or not isfinite(float(model_time_offset_s)):
        raise ValueError("Declare a finite source-to-model offset in seconds")
    if any(not isinstance(item, str) or not item.strip() for item in (
            sensor_location_evidence_id, pipe_to_domain_evidence_id,
            clock_alignment_evidence_id)):
        raise ValueError("Sensor position, pipe/domain and clock mappings need caller evidence")
    selected = []
    for index in row_indices:
        if type(index) is not int or not 0 <= index < len(sample.rows):
            raise IndexError("Choose valid integer source row indices")
        row = sample.rows[index]
        if type(row) is not ELVHYS432TemperatureRow or row.row_index != index:
            raise ValueError("Selected source row differs from the pinned table")
        selected.append(row)
    if not selected or tuple(sorted({row.row_index for row in selected})) != tuple(
            row.row_index for row in selected):
        raise ValueError("Select nonempty, ordered, unique source rows")
    model_times = {}
    for i, time_s in enumerate(result.time_s):
        model_times.setdefault(float(time_s), []).append(i)
    points = []
    values = (result.inner_surface_temperature_k if surface == "inner"
              else result.outer_surface_temperature_k)
    for row in selected:
        source_time_s = row.time_min * 60.0
        candidates = model_times.get(source_time_s + float(model_time_offset_s), ())
        if len(candidates) != 1:
            raise ValueError("Each selected reading needs one exact model time; interpolation is not allowed")
        model_index = candidates[0]
        observed = row.pipe_surface_temperature_k
        modeled = float(values[model_index])
        points.append((row.row_index, source_time_s, observed, modeled, observed - modeled))
    return tuple(points)


@dataclass(frozen=True, slots=True)
class ELVHYS432SurfaceTemperatureComparison:
    sample: ELVHYS432TemperatureSample
    model_result: RadialHeatResult
    source_row_indices: tuple[int, ...]
    surface: str
    model_time_offset_s: float
    sensor_location_evidence_id: str
    pipe_to_domain_evidence_id: str
    clock_alignment_evidence_id: str
    points: tuple[tuple[int, float, float, float, float], ...]
    _issuer: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue comparisons through compare_elvhys432_surface_temperature")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.sample), id(self.model_result), self.source_row_indices,
                self.surface, self.model_time_offset_s, self.sensor_location_evidence_id,
                self.pipe_to_domain_evidence_id, self.clock_alignment_evidence_id, self.points)

    def require_current(self):
        if self._current() != self._binding:
            raise ValueError("ELVHYS 4.3.2 comparison has changed since issuance")
        points = _evaluate(
            self.sample, self.model_result, self.source_row_indices,
            surface=self.surface, model_time_offset_s=self.model_time_offset_s,
            sensor_location_evidence_id=self.sensor_location_evidence_id,
            pipe_to_domain_evidence_id=self.pipe_to_domain_evidence_id,
            clock_alignment_evidence_id=self.clock_alignment_evidence_id,
        )
        if points != self.points:
            raise ValueError("ELVHYS 4.3.2 residuals no longer replay from current inputs")
        return self


def compare_elvhys432_surface_temperature(
        sample: ELVHYS432TemperatureSample, model_result: RadialHeatResult, *,
        source_row_indices: tuple[int, ...], surface: str,
        model_time_offset_s: float, sensor_location_evidence_id: str,
        pipe_to_domain_evidence_id: str, clock_alignment_evidence_id: str,
) -> ELVHYS432SurfaceTemperatureComparison:
    """Compare SD1 Kelvin readings with an explicitly selected radial model face.

    The function only computes pointwise residuals. It does not infer heat flux,
    material properties, axial sensor location, or a pipe-to-model map. SD2 is
    preserved by the reader but is not a radial wall-surface observable.
    """
    indices = tuple(source_row_indices)
    points = _evaluate(
        sample, model_result, indices, surface=surface,
        model_time_offset_s=model_time_offset_s,
        sensor_location_evidence_id=sensor_location_evidence_id,
        pipe_to_domain_evidence_id=pipe_to_domain_evidence_id,
        clock_alignment_evidence_id=clock_alignment_evidence_id,
    )
    token = object()
    _PENDING.add(token)
    return ELVHYS432SurfaceTemperatureComparison(
        sample, model_result, indices, surface, float(model_time_offset_s),
        sensor_location_evidence_id.strip(), pipe_to_domain_evidence_id.strip(),
        clock_alignment_evidence_id.strip(), points, token,
    )
