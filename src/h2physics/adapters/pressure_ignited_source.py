"""Measured ignited USN flow to the shared finite-source boundary."""

from dataclasses import dataclass, field

import numpy as np

from ..core import Origin, ThermoState, finite
from ..data.pressure_ignited import IgnitedFlowBlock
from ..release import SourceLocation
from ..sources import IntervalMassSource

SOURCE_DOI = "10.23642/usn.17934047.v1"
SOURCE_FILE = "HTE341USN0015READ191111.mat"
SOURCE_SHA256 = "3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4"
SOURCE_ID = f"{SOURCE_DOI}:{SOURCE_FILE}"
_PENDING: set[object] = set()


def _flow_inputs(block, start_s, end_s, flow_rule):
    if type(block) is not IgnitedFlowBlock:
        raise TypeError("Supply a flow block issued by the pinned ignited MAT reader")
    series = block.series
    if (block.source_sha256 != SOURCE_SHA256 or series.source_id != SOURCE_ID
            or series.origin is not Origin.MEASURED
            or series.channels != ("mass_flow_g_s",) or series.units != ("g/s",)
            or series.quantities != ("mass_flow",)):
        raise ValueError("Only the pinned measured ignited SIGMA mass-flow channel is admitted")
    if flow_rule not in {"left_hold", "right_hold", "trapezoid"}:
        raise ValueError("Declare left_hold, right_hold, or trapezoid flow quadrature")
    start_s = finite(start_s, "source interval start")
    end_s = finite(end_s, "source interval end")
    if start_s >= end_s:
        raise ValueError("Source interval must increase")
    times = np.asarray(series.time_s, dtype=float)
    rates_g_s = np.asarray(series.values[:, 0], dtype=float)
    valid = np.asarray(series.valid[:, 0], dtype=bool)
    indices = np.flatnonzero((times >= start_s) & (times <= end_s))
    if (len(indices) < 2 or not np.all(valid[indices])
            or not np.all(np.isfinite(times[indices]))
            or not np.all(np.isfinite(rates_g_s[indices]))
            or np.any(np.diff(times[indices]) <= 0.)):
        raise ValueError("Window requires complete, increasing measured SIGMA flow rows")
    selected_times = times[indices]
    if selected_times[0] != start_s or selected_times[-1] != end_s:
        raise ValueError("Source-window edges must coincide with measured rows; no interpolation is allowed")
    if np.any(rates_g_s[indices] < 0.):
        raise ValueError("Negative measured mass flow is retained and cannot be a release source")
    # The source guide reports SIGMA mass flow in g/s. Convert this channel only.
    rates_kg_s = rates_g_s[indices] * 1e-3
    durations = np.diff(selected_times)
    if flow_rule == "left_hold":
        interval_rates = rates_kg_s[:-1]
    elif flow_rule == "right_hold":
        interval_rates = rates_kg_s[1:]
    else:
        interval_rates = .5 * (rates_kg_s[:-1] + rates_kg_s[1:])
    masses_kg = interval_rates * durations
    if not np.all(np.isfinite(masses_kg)) or np.any(masses_kg < 0.):
        raise ValueError("Mass bins must be finite and nonnegative")
    return (tuple(block.source_rows[i] for i in indices),
            tuple(float(t) for t in selected_times),
            tuple(float(q) for q in rates_kg_s),
            tuple(float(m) for m in masses_kg), series.clock_id)


@dataclass(frozen=True, slots=True)
class IgnitedUSNFiniteSource:
    flow_block: IgnitedFlowBlock
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
            raise TypeError("Issue this source only through project_ignited_usn_flow")
        _PENDING.remove(self._token)
        object.__setattr__(self, "_binding", self._current())

    def _current(self):
        return (id(self.flow_block), id(self.source), self.source_window_s,
                self.flow_rule, self.source_rows, self.time_s, self.mass_flow_kg_s,
                self.release_plane_evidence_id, self.state_projection_evidence_id)

    @property
    def source_sha256(self):
        return self.flow_block.source_sha256

    def require_current(self):
        self.source.require_current()
        if self._current() != self._binding:
            raise ValueError("Ignited flow projection lost its evidence binding")
        rows, times, rates, masses, clock_id = _flow_inputs(
            self.flow_block, *self.source_window_s, self.flow_rule)
        if (rows != self.source_rows or times != self.time_s or rates != self.mass_flow_kg_s
                or not np.array_equal(self.source.edges_s, times)
                or not np.array_equal(self.source.mass_kg, masses)
                or self.source.origin is not Origin.MEASURED
                or self.source.location.clock_id != clock_id):
            raise ValueError("Finite source no longer reproduces from exact ignited SIGMA rows")
        return self


def project_ignited_usn_flow(
        block: IgnitedFlowBlock, *, location: SourceLocation,
        representative_state: ThermoState, source_window_s: tuple[float, float],
        flow_rule: str, release_plane_evidence_id: str,
        state_projection_evidence_id: str) -> IgnitedUSNFiniteSource:
    """Project measured SIGMA mass flow; keep pressure and GEN3i clocks unused.

    Source-plane location, constant representative hydrogen state, clock placement,
    and interval quadrature remain explicit caller evidence. This boundary does not
    infer an ignited release state or make an enclosure-pressure prediction.
    """
    if type(block) is not IgnitedFlowBlock:
        raise TypeError("Supply an issued ignited flow block")
    if type(location) is not SourceLocation or type(representative_state) is not ThermoState:
        raise TypeError("Supply explicit source location and representative H2 state")
    if (representative_state.basis.fluid.lower() not in {"hydrogen", "h2"}
            or representative_state.phase not in {"gas", "supercritical_gas", "supercritical"}):
        raise ValueError("Representative state must describe gaseous hydrogen")
    for label, value in (("release plane", release_plane_evidence_id),
                         ("state projection", state_projection_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {label} evidence")
    if not isinstance(source_window_s, (tuple, list)) or len(source_window_s) != 2:
        raise ValueError("Declare a closed SIGMA-clock window")
    start_s, end_s = (finite(value, "source time") for value in source_window_s)
    rows, times, rates, masses, clock_id = _flow_inputs(block, start_s, end_s, flow_rule)
    if location.clock_id != clock_id:
        raise ValueError("Source location must use this SIGMA recorder clock")
    source = IntervalMassSource(
        location=location, edges_s=np.asarray(times), mass_kg=np.asarray(masses),
        state=representative_state, origin=Origin.MEASURED,
        evidence_id=(f"{SOURCE_ID}:{SOURCE_SHA256}:SIGMA:measured-g-s-to-kg-s:"
                     f"{flow_rule}:{release_plane_evidence_id.strip()}:"
                     f"{state_projection_evidence_id.strip()}"),
        end_reason="window_end",
    )
    token = object()
    _PENDING.add(token)
    try:
        projection = IgnitedUSNFiniteSource(
            block, source, (start_s, end_s), flow_rule, rows, times, rates,
            release_plane_evidence_id.strip(), state_projection_evidence_id.strip(), token,
        )
        return projection.require_current()
    except Exception:
        _PENDING.discard(token)
        raise


__all__ = ["IgnitedUSNFiniteSource", "project_ignited_usn_flow"]
