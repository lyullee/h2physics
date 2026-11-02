"""Evidence-gated MHC logger temperature comparison with a native hydride-compressor trace."""

from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from ..data.hydride_compressor import LoggerBlock
from ..storage.hydride_compressor import HydrideCompressorTrace

_PENDING: set[object] = set()


@dataclass(frozen=True, slots=True)
class MHCCompressorTemperaturePoint:
    source_row_id: str
    source_time_s: float
    model_time_s: float
    observed_temperature_k: float
    predicted_bed_solid_temperature_k: float
    left_model_index: int
    right_model_index: int
    interpolation_weight: float

    @property
    def residual_k(self):
        return self.predicted_bed_solid_temperature_k - self.observed_temperature_k


def _source(block: LoggerBlock, channel_name: str, window: tuple[float, float], offset: float):
    table = block.observations
    context = dict(table.context)
    member_hash = context.get("member_sha256", "")
    if (block.archive_receipt_verified is not True
            or context.get("archive_sha256") != "91755fb1e555e0eb32d160ac140a4261b6bb47d24944c7e717b723fe2a641e32"
            or len(member_hash) != 64 or any(ch not in "0123456789abcdef" for ch in member_hash)
            or context.get("export_role") != "raw logger export"
            or table.source_id != "doi:10.5281/zenodo.19036733/v1.2"):
        raise ValueError("Use a raw logger block from the checksum-pinned MHC v1.2 archive")
    names = tuple(variable.name for variable in table.variables)
    if channel_name not in names or names[0] != "local_datetime_elapsed":
        raise ValueError("Select a measured channel from a reviewed raw logger block")
    variable = table.variables[names.index(channel_name)]
    if variable.quantity != "temperature" or variable.unit != "K":
        raise ValueError("Only an explicitly reported temperature channel in K can be compared")
    if table.origins[names.index(channel_name)].value != "measured":
        raise ValueError("Reconstructed cycle/calibration channels are not independent measurements")
    times, time_valid = table.column(names[0])
    temperatures, temperature_valid = table.column(channel_name)
    keep = (time_valid & temperature_valid & (times >= window[0]) & (times <= window[1]))
    indices = np.flatnonzero(keep)
    source_times = np.asarray(times[indices], dtype=float)
    values = np.asarray(temperatures[indices], dtype=float)
    if (len(indices) < 2 or not np.all(np.isfinite(source_times))
            or not np.all(np.isfinite(values)) or np.any(np.diff(source_times) <= 0.)
            or np.any(values <= 0.)):
        raise ValueError("Selected measured temperature rows need positive K values and increasing source time")
    clock_id = context.get("clock_id")
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("MHC source block has no exact logger clock identity")
    return table, indices, source_times, values, clock_id


def _make_points(block, target, channel_name, window, offset):
    table, indices, source_times, values, _ = _source(block, channel_name, window, offset)
    model_times, model_values = [], []
    for point in target.points:
        model_times.append(float(point.snapshot.time_s))
        model_values.append(float(point.snapshot.bed.solid_temperature_k))
    model_times = np.asarray(model_times, dtype=float)
    model_values = np.asarray(model_values, dtype=float)
    if (len(model_times) < 2 or model_values.shape != model_times.shape
            or not np.all(np.isfinite(model_times)) or not np.all(np.isfinite(model_values))
            or np.any(np.diff(model_times) < 0.) or np.any(model_values <= 0.)):
        raise ValueError("Current compressor trace must retain ordered paired bed-temperature samples")
    # Stage boundaries can contribute two samples at the same physical time.
    # They are collapsible only when the carried bed state is exactly continuous.
    unique_times, unique_values = [], []
    for time_s, temperature in zip(model_times, model_values, strict=True):
        if unique_times and time_s == unique_times[-1]:
            if temperature != unique_values[-1]:
                raise ValueError("Compressor stage boundary has an ambiguous bed-temperature state")
            continue
        unique_times.append(float(time_s))
        unique_values.append(float(temperature))
    model_times = np.asarray(unique_times)
    model_values = np.asarray(unique_values)
    if len(model_times) < 2 or np.any(np.diff(model_times) <= 0.):
        raise ValueError("Compressor model trace has insufficient unique time support")
    result = []
    for source_index, source_time, observed in zip(indices, source_times, values, strict=True):
        model_time = float(source_time + offset)
        if model_time < model_times[0] or model_time > model_times[-1]:
            raise ValueError("Clock-mapped MHC measurement falls outside model support")
        right = int(np.searchsorted(model_times, model_time, side="left"))
        if right < len(model_times) and model_times[right] == model_time:
            left = right
            weight = 0.0
            predicted = float(model_values[right])
        else:
            if right == 0 or right == len(model_times):
                raise ValueError("Model interpolation would extrapolate")
            left = right - 1
            weight = float((model_time - model_times[left]) /
                           (model_times[right] - model_times[left]))
            predicted = float((1.0 - weight) * model_values[left] + weight * model_values[right])
        result.append(MHCCompressorTemperaturePoint(
            table.row_ids[int(source_index)], float(source_time), model_time, float(observed),
            predicted, left, right, weight,
        ))
    return tuple(result)


def _source_signature(block):
    table = block.observations
    return (table.content_sha256, tuple(table.context), block.schema,
            tuple(block.source_rows), tuple(block.raw_cells),
            tuple(block.invalid_reasons), tuple(block.formula_cells))


@dataclass(frozen=True, slots=True)
class MHCCompressorTemperatureComparison:
    source: LoggerBlock
    target: HydrideCompressorTrace
    channel_name: str
    source_window_s: tuple[float, float]
    clock_offset_s: float
    sensor_to_bed_evidence_id: str
    clock_alignment_evidence_id: str
    interpolation_evidence_id: str
    points: tuple[MHCCompressorTemperaturePoint, ...]
    _signature: tuple = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue MHC temperature comparisons through the binding API")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "_seal", self._current())

    def _current(self):
        return (id(self.source), id(self.target), self.channel_name, self.source_window_s,
                self.clock_offset_s, self.sensor_to_bed_evidence_id,
                self.clock_alignment_evidence_id, self.interpolation_evidence_id,
                self.points, self._signature)

    def require_current(self):
        self.target.require_current()
        if self._current() != self._seal:
            raise ValueError("MHC source/model/evidence comparison changed after issuance")
        signature = (_source_signature(self.source), self.target.evidence,
                     tuple((p.snapshot.time_s, p.snapshot.bed.solid_temperature_k)
                           for p in self.target.points))
        if signature != self._signature:
            raise ValueError("MHC source block or compressor trace is no longer current")
        if _make_points(self.source, self.target, self.channel_name,
                        self.source_window_s, self.clock_offset_s) != self.points:
            raise ValueError("MHC comparison rows no longer reproduce from retained owners")
        return self


def compare_mhc_temperature_to_compressor_bed(source: LoggerBlock,
        target: HydrideCompressorTrace, *, channel_name: str,
        source_window_s: tuple[float, float], clock_offset_s: float,
        sensor_to_bed_evidence_id: str, clock_alignment_evidence_id: str,
        interpolation_evidence_id: str) -> MHCCompressorTemperatureComparison:
    """Compare one mapped measured logger temperature to modeled bed solid T.

    MHC channel names do not establish bed location. The caller must supply
    independent sensor-to-bed and clock evidence. Only the raw experiment sheet,
    exact source time support, and in-domain linear model sampling are accepted.
    This is a diagnostic residual, never a fitted heat-transfer law or validation
    claim. Logger temperature-to-bed assignment remains caller-owned.
    """
    if type(source) is not LoggerBlock or type(target) is not HydrideCompressorTrace:
        raise TypeError("Supply an issued MHC raw logger block and a current native compressor trace")
    target.require_current()
    if (not isinstance(channel_name, str) or not channel_name.strip()
            or not isinstance(source_window_s, (tuple, list)) or len(source_window_s) != 2):
        raise ValueError("Select a named source temperature and finite increasing time window")
    start, end = (finite(item, "source time window") for item in source_window_s)
    offset = finite(clock_offset_s, "source to model clock offset")
    if start >= end:
        raise ValueError("Source window and clock offset must be finite and ordered")
    evidence = (sensor_to_bed_evidence_id, clock_alignment_evidence_id, interpolation_evidence_id)
    if any(not isinstance(item, str) or not item.strip() for item in evidence):
        raise ValueError("Sensor mapping, clock alignment and interpolation evidence IDs are required")
    _, _, _, _, source_clock_id = _source(source, channel_name, (start, end), offset)
    if source_clock_id == "":
        raise ValueError("MHC source clock identity is empty")
    points = _make_points(source, target, channel_name, (start, end), offset)
    table = source.observations
    signature = (_source_signature(source), target.evidence,
                 tuple((p.snapshot.time_s, p.snapshot.bed.solid_temperature_k)
                       for p in target.points))
    token = object()
    _PENDING.add(token)
    try:
        result = MHCCompressorTemperatureComparison(
            source, target, channel_name, (start, end), offset,
            *(item.strip() for item in evidence), points, signature, _issuer=token,
        )
        return result.require_current()
    except Exception:
        _PENDING.discard(token)
        raise
