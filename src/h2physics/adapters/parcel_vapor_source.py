"""Mass-conserving vapor source handoff from an evaporating parcel trace."""

from dataclasses import dataclass, field
import hashlib
from math import isclose

import numpy as np

from ..core import Origin
from ..sources import IntervalMassSource
from ..release import SourceLocation

_PENDING_VAPOR_SOURCES: set[object] = set()


@dataclass(frozen=True, slots=True)
class ParcelVaporSourceHandoff:
    parcel_trace: object
    source: IntervalMassSource
    location_projection_evidence_id: str
    _issuer: object = field(default=None, repr=False, compare=False)
    _issued: object = field(default=None, init=False, repr=False, compare=False)
    _seal: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING_VAPOR_SOURCES:
            raise TypeError("Create parcel vapor sources through the typed adapter")
        _PENDING_VAPOR_SOURCES.remove(self._issuer)
        object.__setattr__(self, "_issued", self._issuer)
        object.__setattr__(self, "_seal", self._signature())

    def _signature(self):
        return hashlib.sha256(repr((id(self.parcel_trace), self.parcel_trace._seal,
            id(self.source), self.source._fingerprint,
            self.location_projection_evidence_id)).encode()).hexdigest()

    def require_current(self):
        from .droplet_transport import ParcelTrace

        if self._issuer is not self._issued:
            raise ValueError("Parcel vapor source lost its original issuer identity")
        if type(self.parcel_trace) is not ParcelTrace:
            raise TypeError("Retain the original owner-issued parcel trace")
        self.parcel_trace.require_current()
        self.source.require_current()
        native = self.parcel_trace.native_result
        times = np.asarray(native.t, dtype=float)
        cumulative = np.asarray(native.y[7], dtype=float)
        expected = np.diff(cumulative)
        if (not np.array_equal(self.source.edges_s, times)
                or not np.array_equal(self.source.mass_kg, expected)
                or self.source.location.clock_id != self.parcel_trace.boundary.clock_id
                or self.source.location.coordinate_frame_id != self.parcel_trace.boundary.frame_id
                or self.source.state is not self.parcel_trace.states[0].vapor_state
                or not isclose(float(np.sum(self.source.mass_kg)), self.parcel_trace.evaporated_mass_kg,
                               rel_tol=1e-12, abs_tol=1e-15)
                or self._signature() != self._seal):
            raise ValueError("Vapor source bins, thermodynamic state, location or trace changed")
        return self


def vapor_source_from_parcel_trace(trace, *, location: SourceLocation, origin: Origin,
        evidence_id: str, location_projection_evidence_id: str):
    """Expose accepted parcel evaporation as the existing finite vapor source.

    Cumulative vapor mass comes from the retained native solver output, not from
    endpoint mass differencing or a new evaporation law. The vapor ThermoState is
    retained exactly from the parcel provider. Because the parcel moves while
    evaporating, the caller must explicitly evidence the chosen spatial source
    projection in `location_projection_evidence_id`.
    """
    from .droplet_transport import ParcelTrace

    if type(trace) is not ParcelTrace:
        raise TypeError("Supply an original owner-issued ParcelTrace")
    trace.require_current()
    if type(location) is not SourceLocation:
        raise TypeError("Supply an explicit release location and orientation")
    if (location.clock_id != trace.boundary.clock_id
            or location.coordinate_frame_id != trace.boundary.frame_id):
        raise ValueError("Release location frame/clock must match the parcel trajectory")
    for name, value in (("source evidence", evidence_id),
                        ("location-projection evidence", location_projection_evidence_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Declare {name}")
    origin = Origin(origin)
    if origin == Origin.UNRESOLVED:
        raise ValueError("Resolve the vapor source origin")
    native = trace.native_result
    times = np.asarray(native.t, dtype=float)
    cumulative = np.asarray(native.y[7], dtype=float)
    if (times.shape != (len(trace.states),) or not np.array_equal(
            times, np.asarray([state.time_s for state in trace.states]))
            or cumulative.shape != times.shape or cumulative[0] != 0.
            or np.any(np.diff(times) <= 0.) or np.any(np.diff(cumulative) < 0.)):
        raise ValueError("Native cumulative evaporation must align with finite accepted parcel times")
    vapor = trace.states[0].vapor_state
    if any(state.vapor_state is not vapor for state in trace.states):
        raise ValueError("One IntervalMassSource requires the exact constant vapor state")
    masses = np.diff(cumulative)
    source = IntervalMassSource(location, times, masses, vapor, origin,
        ":".join((evidence_id.strip(), trace.boundary.evidence_id,
                   location_projection_evidence_id.strip())), "window_end")
    token = object()
    _PENDING_VAPOR_SOURCES.add(token)
    try:
        result = ParcelVaporSourceHandoff(trace, source,
            location_projection_evidence_id.strip(), token)
    except Exception:
        _PENDING_VAPOR_SOURCES.discard(token)
        raise
    return result.require_current()
