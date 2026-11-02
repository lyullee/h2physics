"""Finite-window mass sources whose interval integrals are explicit.

Each bin represents its known mass by a constant mean rate. Rebinning conserves
that representation; it does not recover unresolved subinterval transients.
"""

import hashlib
from dataclasses import dataclass, field

import numpy as np

from .core import Origin, ThermoState, finite, immutable_array
from .release import SourceLocation


@dataclass(frozen=True, slots=True)
class IntervalMassSource:
    location: SourceLocation
    edges_s: np.ndarray
    mass_kg: np.ndarray
    state: ThermoState
    origin: Origin
    evidence_id: str
    end_reason: str
    _fingerprint: str = field(init=False, repr=False, compare=False)
    _original_objects: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.location, SourceLocation):
            raise TypeError("A finite mass source needs an explicit SourceLocation")
        if not isinstance(self.state, ThermoState):
            raise TypeError("A finite mass source needs one explicit representative ThermoState")
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("Declare finite-source projection evidence")
        if not isinstance(self.end_reason, str) or self.end_reason not in {
            "window_end", "isolation", "depleted", "pressure_equalized", "inventory_limit",
        }:
            raise ValueError("Declare a supported finite-source termination meaning")
        edges = np.array(self.edges_s, dtype=float, copy=True)
        mass = np.array(self.mass_kg, dtype=float, copy=True)
        if (edges.ndim != 1 or len(edges) < 2 or not np.all(np.isfinite(edges))
                or np.any(np.diff(edges) <= 0.)):
            raise ValueError("Source edges must be finite and strictly increasing")
        if mass.shape != (len(edges)-1,) or np.any(~np.isfinite(mass) | (mass < 0.)):
            raise ValueError("Each source interval requires a finite nonnegative mass")
        for name, values in (("edges_s", edges), ("mass_kg", mass)):
            values = immutable_array(values, name=name)
            object.__setattr__(self, name, values)
        object.__setattr__(self, "origin", Origin(self.origin))
        object.__setattr__(self, "_original_objects", (
            self.location, self.state, self.edges_s, self.mass_kg,
        ))
        object.__setattr__(self, "_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self) -> str:
        payload = repr((
            self.location, self.state, self.origin, self.evidence_id, self.end_reason,
            self.edges_s.shape, self.edges_s.dtype.str, self.edges_s.tobytes(),
            self.mass_kg.shape, self.mass_kg.dtype.str, self.mass_kg.tobytes(),
        )).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def require_current(self) -> "IntervalMassSource":
        if any(current is not original for current, original in zip(
            (self.location, self.state, self.edges_s, self.mass_kg),
            self._original_objects, strict=True,
        )):
            raise ValueError("Finite source lost its original state, location or bin arrays")
        if self._current_fingerprint() != self._fingerprint:
            raise ValueError("Finite source state, provenance, clock or mass bins changed")
        return self

    @property
    def total_mass_kg(self) -> float:
        self.require_current()
        return float(np.sum(self.mass_kg))

    @property
    def mean_rates_kg_s(self) -> np.ndarray:
        self.require_current()
        values = self.mass_kg/np.diff(self.edges_s)
        values = immutable_array(values, name="source values")
        return values

    @property
    def enthalpy_transfer_j(self) -> float:
        self.require_current()
        return self.total_mass_kg*self.state.enthalpy_j_kg

    def mass_between(self, start_s: float, end_s: float, *, clock_id: str) -> float:
        self.require_current()
        left, right = finite(start_s, "start_s"), finite(end_s, "end_s")
        if clock_id != self.location.clock_id:
            raise ValueError("Source integration requires the declared clock")
        if not self.edges_s[0] <= left <= right <= self.edges_s[-1]:
            raise ValueError("Source integration cannot extrapolate outside its finite window")
        overlap = np.maximum(0., np.minimum(right, self.edges_s[1:])-np.maximum(left, self.edges_s[:-1]))
        return float(np.dot(self.mean_rates_kg_s, overlap))

    def rate_at(self, time_s: float, *, clock_id: str, side: str = "right") -> float:
        """Return the declared piecewise-constant rate at one clock instant.

        At an interior edge the default ``right`` convention selects the
        interval beginning there; ``left`` selects the interval ending there.
        The final source edge is included only with ``side="left"``. These
        conventions make event-driven coupling deterministic without smoothing
        a discontinuity or inventing a rate outside the finite source window.
        """
        self.require_current()
        time = finite(time_s, "time_s")
        if clock_id != self.location.clock_id:
            raise ValueError("Source sampling requires the declared clock")
        if side not in {"left", "right"}:
            raise ValueError("Sampling side must be 'left' or 'right'")
        if time < self.edges_s[0] or time > self.edges_s[-1]:
            raise ValueError("Source sampling cannot extrapolate outside its finite window")
        if time == self.edges_s[-1]:
            if side == "right":
                raise ValueError("No right-sided source rate exists at the final edge")
            index = len(self.mass_kg) - 1
        elif time == self.edges_s[0]:
            if side == "left":
                raise ValueError("No left-sided source rate exists at the initial edge")
            index = 0
        else:
            index = int(np.searchsorted(self.edges_s, time, side=side) - 1)
        return float(self.mean_rates_kg_s[index])

    def integrate(self, edges_s, *, clock_id: str) -> "IntervalMassSource":
        """Project this source onto a solver clock while preserving every jump.

        Requested edges are merged with all original discontinuities before
        interval masses are integrated. This avoids smearing a rate change when
        a receiving solver's output grid does not happen to land on the source
        event clock. No extrapolation or sub-bin reconstruction is performed.
        """
        self.require_current()
        requested = np.asarray(edges_s, dtype=float)
        if (requested.ndim != 1 or len(requested) < 2
                or not np.all(np.isfinite(requested))
                or np.any(np.diff(requested) <= 0.)
                or requested[0] != self.edges_s[0]
                or requested[-1] != self.edges_s[-1]):
            raise ValueError("Integration edges must be ordered and span the full source window")
        merged = np.union1d(requested, self.edges_s)
        mass = np.fromiter((self.mass_between(a, b, clock_id=clock_id)
                            for a, b in zip(merged[:-1], merged[1:], strict=True)),
                           dtype=float, count=len(merged)-1)
        return IntervalMassSource(self.location, merged, mass, self.state,
                                  self.origin, self.evidence_id, self.end_reason)

    def window(self, start_s: float, end_s: float, *, clock_id: str,
               end_reason: str | None = None) -> "IntervalMassSource":
        """Return a finite source segment without erasing internal rate jumps.

        A segment ending before the parent's final edge needs an explicit
        termination meaning, since the original source record cannot establish
        whether a receiving calculation stops by isolation, depletion or a
        deliberately bounded observation window. The initial boundary is a
        computational crop only; no missing pre-window mass is inferred.
        """
        self.require_current()
        left, right = finite(start_s, "start_s"), finite(end_s, "end_s")
        if clock_id != self.location.clock_id:
            raise ValueError("Source windowing requires the declared clock")
        if not self.edges_s[0] <= left < right <= self.edges_s[-1]:
            raise ValueError("Source window must be positive and inside the finite source support")
        if end_reason is None:
            if right != self.edges_s[-1]:
                raise ValueError("A truncated source window needs an explicit end_reason")
            reason = self.end_reason
        else:
            reason = end_reason
        if reason not in {
            "window_end", "isolation", "depleted", "pressure_equalized", "inventory_limit",
        }:
            raise ValueError("Unsupported finite source window end_reason")
        if right == self.edges_s[-1] and reason != self.end_reason:
            raise ValueError("A full-tail window cannot relabel the parent's termination meaning")
        edges = np.r_[left, self.edges_s[(self.edges_s > left) & (self.edges_s < right)], right]
        mass = np.fromiter((self.mass_between(a, b, clock_id=clock_id)
                            for a, b in zip(edges[:-1], edges[1:], strict=True)),
                           dtype=float, count=len(edges)-1)
        return IntervalMassSource(self.location, edges, mass, self.state,
                                  self.origin, self.evidence_id, reason)

    def rebin(self, edges_s, *, clock_id: str) -> "IntervalMassSource":
        self.require_current()
        edges = np.asarray(edges_s, dtype=float)
        if (edges.ndim != 1 or len(edges) < 2 or not np.all(np.isfinite(edges))
                or np.any(np.diff(edges) <= 0.)
                or edges[0] != self.edges_s[0] or edges[-1] != self.edges_s[-1]):
            raise ValueError("Rebinning must preserve the full ordered source window")
        mass = [self.mass_between(a, b, clock_id=clock_id) for a, b in zip(edges[:-1], edges[1:], strict=True)]
        return IntervalMassSource(self.location, edges, np.array(mass), self.state,
                                  self.origin, self.evidence_id, self.end_reason)
