"""Source-bound, evidence-gated BAM plate-temperature comparison to a target trace."""

from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from ..data.bam_jet_fire import BAMJetFireUnitProjection
from .thermal_target import ThermalTargetTrace

_PENDING: set[object] = set()


@dataclass(frozen=True, slots=True)
class BAMThermalObservationPoint:
    source_row_id: str
    source_time_s: float
    model_time_s: float
    raw_temperature_token: str
    observed_temperature_k: float
    predicted_temperature_k: float
    left_model_index: int
    right_model_index: int
    interpolation_weight: float

    @property
    def residual_k(self):
        return self.predicted_temperature_k - self.observed_temperature_k


def _points(source_projection, target, channel, start, end, offset):
    source_projection.require_current()
    target.require_current()
    source = source_projection.source_table
    if target.history.frame_id == "":
        raise ValueError("Thermal-target trace has no receiver frame identity")
    if "Time [s]" not in source.column_names:
        raise ValueError("BAM member must contain its exact source time channel")
    times, times_valid = source.column("Time [s]")
    temperatures, temperatures_valid = source.column(channel)
    model_times = np.asarray(target.time_s, dtype=float)
    model_temperatures = np.asarray(target.temperature_k, dtype=float)
    if (model_times.ndim != 1 or len(model_times) < 2
            or model_temperatures.shape != model_times.shape
            or np.any(np.diff(model_times) <= 0.)):
        raise ValueError("Thermal model trace must retain increasing paired time and temperature samples")
    selected = (times_valid & temperatures_valid & (times >= start) & (times <= end))
    indices = np.flatnonzero(selected)
    if len(indices) < 2:
        raise ValueError("Select a source window containing at least two valid plate-temperature rows")
    source_times = np.asarray(times[indices], dtype=float)
    source_temperatures_c = np.asarray(temperatures[indices], dtype=float)
    if (not np.all(np.isfinite(source_times)) or not np.all(np.isfinite(source_temperatures_c))
            or np.any(np.diff(source_times) <= 0.)):
        raise ValueError("Selected BAM clock/temperature rows must be finite and strictly ordered")
    points = []
    for index, source_time, temperature_c in zip(indices, source_times,
                                                 source_temperatures_c, strict=True):
        model_time = float(source_time + offset)
        if not model_times[0] <= model_time <= model_times[-1]:
            raise ValueError("Clock-aligned BAM row lies outside the retained target model support")
        right = int(np.searchsorted(model_times, model_time, side="left"))
        if right < len(model_times) and model_times[right] == model_time:
            left, weight, predicted = right, 0., float(model_temperatures[right])
        else:
            if right == 0 or right == len(model_times):
                raise ValueError("Thermal model interpolation would extrapolate")
            left = right - 1
            weight = float((model_time - model_times[left]) /
                           (model_times[right] - model_times[left]))
            predicted = float((1. - weight) * model_temperatures[left]
                              + weight * model_temperatures[right])
        observed = float(temperature_c + 273.15)
        if observed <= 0. or not np.isfinite(predicted) or predicted <= 0.:
            raise ValueError("Absolute temperature mapping must produce positive finite kelvin")
        points.append(BAMThermalObservationPoint(
            source.row_ids[index], float(source_times[index]), model_time,
            source.raw_rows[index][source.column_names.index(channel)], observed,
            predicted, left, right, weight,
        ))
    return tuple(points)


@dataclass(frozen=True, slots=True)
class BAMThermalTargetComparison:
    source_projection: BAMJetFireUnitProjection
    target: ThermalTargetTrace
    channel_label: str
    source_window_s: tuple[float, float]
    clock_offset_s: float
    temperature_interpretation_evidence_id: str
    target_sensor_mapping_evidence_id: str
    clock_alignment_evidence_id: str
    interpolation_evidence_id: str
    points: tuple[BAMThermalObservationPoint, ...]
    _signature: tuple = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue BAM thermal comparisons through the source/model binding API")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "_seal", self._current())

    def _current(self):
        return (id(self.source_projection), id(self.target), self.channel_label,
                self.source_window_s, self.clock_offset_s,
                self.temperature_interpretation_evidence_id,
                self.target_sensor_mapping_evidence_id,
                self.clock_alignment_evidence_id, self.interpolation_evidence_id,
                self.points, self._signature)

    def require_current(self):
        self.source_projection.require_current()
        self.target.require_current()
        if self._current() != self._seal:
            raise ValueError("BAM thermal comparison lost its source/model/evidence binding")
        source = self.source_projection.source_table
        signature = (id(self.source_projection), id(self.target), source.member_sha256,
                     self.source_projection.dataset_doi, self.source_projection.creator,
                     self.source_projection.license_id, self.source_projection.license_url,
                     self.target.history.frame_id, self.target.time_s.tobytes(),
                     self.target.temperature_k.tobytes())
        if signature != self._signature:
            raise ValueError("BAM source or target trace changed after comparison issuance")
        reproduced = _points(self.source_projection, self.target, self.channel_label,
                             *self.source_window_s, self.clock_offset_s)
        if reproduced != self.points:
            raise ValueError("BAM thermal residuals no longer reproduce from current owners")
        return self


def compare_bam_plate_temperature_to_target(source: BAMJetFireUnitProjection,
        target: ThermalTargetTrace, *, channel_label: str,
        source_window_s: tuple[float, float], clock_offset_s: float,
        temperature_interpretation_evidence_id: str,
        target_sensor_mapping_evidence_id: str,
        clock_alignment_evidence_id: str,
        interpolation_evidence_id: str) -> BAMThermalTargetComparison:
    """Compare one caller-qualified BAM plate-TC channel with a current model trace.

    BAM's `T_Platte_Avg [-]` and all flow/pressure channels are excluded. A
    selected `[°C]` plate channel remains ambiguous between absolute temperature
    and a difference, so the caller must explicitly support absolute Celsius.
    Alignment and target-sensor mapping are also caller-owned. Target outputs are
    linearly sampled only between their retained solver points; no flux is
    inferred from measured temperature.
    """
    if type(source) is not BAMJetFireUnitProjection or type(target) is not ThermalTargetTrace:
        raise TypeError("Supply the issued rights-bearing BAM projection and current ThermalTargetTrace")
    source.require_current()
    table = source.source_table
    if not isinstance(channel_label, str) or "Platte" not in channel_label or not channel_label.endswith("[°C]"):
        raise ValueError("Select an exact plate thermocouple channel with a source [°C] unit label")
    if channel_label == "T_Platte_Avg [-]" or channel_label not in table.column_names:
        raise ValueError("Unresolved average/unit or absent channels cannot enter the temperature comparison")
    if (source.dataset_doi != "10.5281/zenodo.21026781"
            or source.license_id != "CC-BY-4.0"
            or not table.member_path.startswith("H2_Data/FRP_exp/")):
        raise ValueError("This adapter is scoped to the published fire-reference-plate members")
    evidence = (temperature_interpretation_evidence_id, target_sensor_mapping_evidence_id,
                clock_alignment_evidence_id, interpolation_evidence_id)
    if any(not isinstance(item, str) or not item.strip() for item in evidence):
        raise ValueError("Temperature, target, clock and model-interpolation evidence IDs are all required")
    if (not isinstance(source_window_s, (tuple, list)) or len(source_window_s) != 2):
        raise ValueError("Declare one finite source-time comparison window")
    start, end = (finite(v, "source comparison time") for v in source_window_s)
    if start >= end:
        raise ValueError("Source comparison window must increase")
    offset = finite(clock_offset_s, "source-to-model clock offset")
    points = _points(source, target, channel_label, start, end, offset)
    signature = (id(source), id(target), table.member_sha256,
                 source.dataset_doi, source.creator, source.license_id, source.license_url,
                 target.history.frame_id, target.time_s.tobytes(), target.temperature_k.tobytes())
    token = object()
    _PENDING.add(token)
    try:
        result = BAMThermalTargetComparison(source, target, channel_label,
            (start, end), offset, *(item.strip() for item in evidence), points,
            signature, _issuer=token)
        return result.require_current()
    except Exception:
        _PENDING.discard(token)
        raise
