"""Source-bound positive SIGMA mass-flow bins for an existing finite safety source."""

from dataclasses import dataclass, field

import numpy as np

from ..core import Origin, ThermoState, finite
from ..data.pressure_peaking import RecorderBlock
from ..release import SourceLocation
from ..sources import IntervalMassSource

SOURCE_DOI = "10.23642/usn.17932439.v1"
SOURCE_FILE = "HTE242USN_00003_READ190621.mat"
SOURCE_SHA256 = "f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0"
SOURCE_ID = f"{SOURCE_DOI}:{SOURCE_FILE}"
_PENDING: set[object] = set()


def _flow_inputs(block, start, end, flow_rule):
    if type(block) is not RecorderBlock:
        raise TypeError("Supply an issued pressure-peaking SIGMA recorder block")
    series = block.series
    if (block.matrix_name != "SIGMA" or block.source_sha256 != SOURCE_SHA256
            or series.source_id != SOURCE_ID or series.origin is not Origin.MEASURED
            or series.channels != ("signed_mass_flow", "meter_reported_pressure")
            or series.units != ("kg/s", "Pa") or series.quantities[0] != "mass_flow"):
        raise ValueError("Only the pinned measured USN SIGMA mass-flow export is admitted")
    if flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
        raise ValueError("Declare left_hold, right_hold, or trapezoid source-flow quadrature")
    start = finite(start, "source interval start")
    end = finite(end, "source interval end")
    if start >= end:
        raise ValueError("Source interval must increase")
    times = np.asarray(series.time_s, dtype=float)
    rates = np.asarray(series.values[:, 0], dtype=float)
    valid = np.asarray(series.valid[:, 0], dtype=bool)
    selected = (times >= start) & (times <= end)
    indices = np.flatnonzero(selected)
    if (len(indices) < 2 or not np.all(valid[indices])
            or not np.all(np.isfinite(times[indices]))
            or not np.all(np.isfinite(rates[indices]))
            or np.any(np.diff(times[indices]) <= 0.)):
        raise ValueError("Selected source window needs complete increasing measured flow rows")
    chosen_times = times[indices]
    chosen_rates = rates[indices]
    if chosen_times[0] != start or chosen_times[-1] != end:
        raise ValueError("Source-window edges must coincide with measured rows; extrapolation is unsupported")
    if np.any(chosen_rates < 0.):
        raise ValueError("Signed negative meter flow is retained; it cannot be clipped into a release source")
    durations = np.diff(chosen_times)
    if flow_rule == "left_hold":
        interval_rates = chosen_rates[:-1]
    elif flow_rule == "right_hold":
        interval_rates = chosen_rates[1:]
    else:
        interval_rates = .5 * (chosen_rates[:-1] + chosen_rates[1:])
    masses = interval_rates * durations
    if not np.all(np.isfinite(masses)) or np.any(masses < 0.):
        raise ValueError("Measured flow interval masses must be finite and nonnegative")
    return (tuple(int(block.source_rows[i]) for i in indices),
            tuple(float(value) for value in chosen_times),
            tuple(float(value) for value in chosen_rates),
            tuple(float(value) for value in masses), series.clock_id)


@dataclass(frozen=True, slots=True)
class PressurePeakingFiniteSource:
    recorder_block: RecorderBlock
    source: IntervalMassSource
    source_window_s: tuple[float, float]
    flow_rule: str
    source_rows: tuple[int, ...]
    time_s: tuple[float, ...]
    mass_flow_kg_s: tuple[float, ...]
    release_plane_evidence_id: str
    state_projection_evidence_id: str
    _token: object = field(default=None, repr=False, compare=False)
    _binding: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._token not in _PENDING:
            raise TypeError("Issue USN finite sources only through the source-bound projector")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.recorder_block), id(self.source), self.source_window_s,
                self.flow_rule, self.source_rows, self.time_s, self.mass_flow_kg_s,
                self.release_plane_evidence_id, self.state_projection_evidence_id)

    @property
    def source_sha256(self):
        return self.recorder_block.source_sha256

    def require_current(self):
        self.source.require_current()
        if self._current() != self._binding:
            raise ValueError("USN flow projection lost its source/evidence binding")
        rows, times, rates, masses, clock_id = _flow_inputs(
            self.recorder_block, *self.source_window_s, self.flow_rule,
        )
        if (rows != self.source_rows or times != self.time_s or rates != self.mass_flow_kg_s
                or not np.array_equal(self.source.edges_s, times)
                or not np.array_equal(self.source.mass_kg, masses)
                or self.source.origin is not Origin.MEASURED
                or self.source.location.clock_id != clock_id):
            raise ValueError("Finite source bins no longer reproduce from the exact measured flow rows")
        return self


def project_pressure_peaking_flow_to_finite_source(
        block: RecorderBlock, *, location: SourceLocation,
        representative_state: ThermoState, source_window_s: tuple[float, float],
        flow_rule: str, release_plane_evidence_id: str,
        state_projection_evidence_id: str) -> PressurePeakingFiniteSource:
    """Project a selected positive measured SIGMA flow window to `IntervalMassSource`.

    The USN source reports mass flow in g/s and the reader converts it to kg/s.
    This adapter uses only that flow channel and the recorder's own clock. It
    does not use the unresolved meter-pressure basis, clip negative flow, infer
    a release plane, or determine a representative thermodynamic state. Both
    of those physical mappings and the interval quadrature are caller-owned.
    """
    if type(block) is not RecorderBlock:
        raise TypeError("Supply an issued pressure-peaking RecorderBlock")
    if type(location) is not SourceLocation or type(representative_state) is not ThermoState:
        raise TypeError("Supply an explicit finite-source location and representative gas state")
    if (representative_state.basis.fluid.lower() not in {"hydrogen", "h2"}
            or representative_state.phase not in {"gas", "supercritical_gas", "supercritical"}):
        raise ValueError("Representative source state must explicitly describe gaseous hydrogen")
    for label, value in (("release plane", release_plane_evidence_id),
                         ("state projection", state_projection_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label} evidence for this measured finite source")
    if (not isinstance(source_window_s, (tuple, list)) or len(source_window_s) != 2):
        raise ValueError("Declare a closed, finite source-clock window")
    start, end = (finite(value, "source time") for value in source_window_s)
    rows, times, rates, masses, clock_id = _flow_inputs(block, start, end, flow_rule)
    if location.clock_id != clock_id:
        raise ValueError("Finite-source location must use the measured SIGMA recorder clock")
    finite_source = IntervalMassSource(
        location=location, edges_s=np.asarray(times), mass_kg=np.asarray(masses),
        state=representative_state, origin=Origin.MEASURED,
        evidence_id=(f"{SOURCE_DOI}:{SOURCE_FILE}:{SOURCE_SHA256}:SIGMA:mass-flow-g-s->kg-s:"
                     f"{flow_rule}:{release_plane_evidence_id.strip()}:"
                     f"{state_projection_evidence_id.strip()}"),
        end_reason="window_end",
    )
    token = object()
    _PENDING.add(token)
    try:
        result = PressurePeakingFiniteSource(
            recorder_block=block, source=finite_source,
            source_window_s=(start, end), flow_rule=flow_rule,
            source_rows=rows, time_s=times, mass_flow_kg_s=rates,
            release_plane_evidence_id=release_plane_evidence_id.strip(),
            state_projection_evidence_id=state_projection_evidence_id.strip(),
            _token=token,
        )
        return result.require_current()
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["PressurePeakingFiniteSource", "project_pressure_peaking_flow_to_finite_source"]
