"""Integrate caller-declared engine boundary mass and enthalpy schedules.

This module accounts for prescribed stream histories only. It does not model
valve flow, injection, cylinder mixing, combustion, accepted solver edges, or
close the cylinder first law. Positive ledger values are transfers into the
cylinder; exhaust streams are reported with the opposite sign.
"""

from dataclasses import dataclass, field

import numpy as np

from ..core import finite
from .closed_charge_engine import EngineBoundarySchedule

_PENDING_LEDGER_ISSUERS: set[object] = set()


def _issue_token():
    token = object()
    _PENDING_LEDGER_ISSUERS.add(token)
    return token


def _seal(value):
    if not isinstance(value, (int, float, np.floating)) or not np.isfinite(value):
        raise ValueError("Boundary ledger values must be finite scalars")
    return float(value)


@dataclass(frozen=True, slots=True)
class EngineBoundaryStream:
    """One nonnegative prescribed flow with a matching specific enthalpy.

    ``kind`` is one of ``intake``, ``fuel`` or ``exhaust``. Intake and fuel
    enter the control volume; exhaust leaves it. Both schedules use the same
    absolute clock and must cover the complete accounting window. The caller
    owns the enthalpy reference and must use a common reference for all streams.
    """

    identifier: str
    kind: str
    mass_flow: EngineBoundarySchedule
    specific_enthalpy: EngineBoundarySchedule
    enthalpy_reference: str

    def __post_init__(self):
        for name in ("identifier", "enthalpy_reference"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Engine boundary {name} must be a nonblank string")
            object.__setattr__(self, name, value.strip())
        if self.kind not in {"intake", "fuel", "exhaust"}:
            raise ValueError("Engine boundary kind must be intake, fuel or exhaust")
        if type(self.mass_flow) is not EngineBoundarySchedule or type(self.specific_enthalpy) is not EngineBoundarySchedule:
            raise TypeError("Boundary streams require admitted EngineBoundarySchedule objects")
        self.mass_flow.require_current()
        self.specific_enthalpy.require_current()
        if self.mass_flow.quantity != "mass_flow" or self.mass_flow.units != "kg/s":
            raise ValueError("Boundary mass schedule must declare quantity='mass_flow', units='kg/s'")
        if (self.specific_enthalpy.quantity != "specific_enthalpy"
                or self.specific_enthalpy.units != "J/kg"):
            raise ValueError("Boundary enthalpy schedule must declare quantity='specific_enthalpy', units='J/kg'")
        if not np.array_equal(self.mass_flow.time_s, self.specific_enthalpy.time_s):
            raise ValueError("Mass-flow and specific-enthalpy schedules need identical time knots")
        if np.any(self.mass_flow.values < 0):
            raise ValueError("Mass flow magnitudes must be nonnegative; stream kind supplies direction")


@dataclass(frozen=True, slots=True)
class EngineBoundaryContribution:
    """Signed integral for one prescribed stream over a declared window."""

    identifier: str
    kind: str
    mass_into_cylinder_kg: float
    enthalpy_into_cylinder_j: float


@dataclass(frozen=True, slots=True)
class EngineBoundaryLedger:
    """Source-bound quadrature of scheduled stream transfers.

    The ledger is a boundary input summary. Its quadrature is exact for linear
    mass-flow and specific-enthalpy segments (their product is quadratic), but
    it is not coupled to the cylinder's accepted integration steps.
    """

    start_time_s: float
    end_time_s: float
    enthalpy_reference: str
    time_s: np.ndarray
    contributions: tuple[EngineBoundaryContribution, ...]
    mass_into_cylinder_kg: float
    enthalpy_into_cylinder_j: float
    streams: tuple[EngineBoundaryStream, ...] = field(repr=False, compare=False)
    _issuer_token: object = field(repr=False, compare=False)
    _fingerprint: tuple = field(default=(), repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_LEDGER_ISSUERS:
            raise TypeError("Create engine boundary ledgers through integrate_engine_boundary_streams")
        _PENDING_LEDGER_ISSUERS.remove(self._issuer_token)
        times = np.asarray(self.time_s, dtype=float)
        frozen = np.frombuffer(np.array(times, copy=True).tobytes(), dtype=np.float64)
        object.__setattr__(self, "time_s", frozen)
        if len(frozen) < 2 or np.any(np.diff(frozen) <= 0):
            raise ValueError("Boundary ledger clock must contain increasing samples")
        if frozen[0] != self.start_time_s or frozen[-1] != self.end_time_s:
            raise ValueError("Boundary ledger clock must span its declared integration window")
        if not self.contributions or len(self.contributions) != len(self.streams):
            raise ValueError("Every admitted boundary stream needs exactly one ledger contribution")
        _seal(self.mass_into_cylinder_kg)
        _seal(self.enthalpy_into_cylinder_j)

    def require_current(self):
        """Recompute scheduled integrals and reject source/result mutation."""
        for stream in self.streams:
            stream.mass_flow.require_current()
            stream.specific_enthalpy.require_current()
        expected = _calculate(self.streams, self.start_time_s, self.end_time_s)
        actual = (self.time_s.tobytes(), self.contributions,
                  self.mass_into_cylinder_kg, self.enthalpy_into_cylinder_j)
        if expected != actual or self._fingerprint != _stream_fingerprint(self.streams):
            raise ValueError("Engine boundary ledger or source schedule changed after issuance")
        return self


def _stream_fingerprint(streams):
    return tuple((s.identifier, s.kind, s.enthalpy_reference,
                  s.mass_flow._current_content(), s.specific_enthalpy._current_content())
                 for s in streams)


def _calculate(streams, start, end):
    knots = {float(start), float(end)}
    for stream in streams:
        for schedule in (stream.mass_flow, stream.specific_enthalpy):
            schedule.require_current()
            lo, hi = schedule.support_s
            if lo > start or hi < end:
                raise ValueError(f"Stream {stream.identifier!r} does not cover the requested time window")
            knots.update(float(t) for t in schedule.time_s if start < t < end)
    clock = np.asarray(sorted(knots), dtype=float)
    rows = []
    for stream in streams:
        flow = np.asarray(stream.mass_flow.at(clock), dtype=float)
        enthalpy = np.asarray(stream.specific_enthalpy.at(clock), dtype=float)
        # For each interval, linearly interpolated flow times enthalpy is
        # quadratic; Simpson integration is exact for that declared schedule.
        mids = (clock[:-1] + clock[1:]) / 2
        flow_mid = np.asarray(stream.mass_flow.at(mids), dtype=float)
        enthalpy_mid = np.asarray(stream.specific_enthalpy.at(mids), dtype=float)
        dt = np.diff(clock)
        sign = -1.0 if stream.kind == "exhaust" else 1.0
        mass = sign * float(np.sum(dt * (flow[:-1] + flow[1:]) / 2))
        energy = sign * float(np.sum(dt * (flow[:-1] * enthalpy[:-1]
                                           + 4 * flow_mid * enthalpy_mid
                                           + flow[1:] * enthalpy[1:]) / 6))
        rows.append(EngineBoundaryContribution(stream.identifier, stream.kind, mass, energy))
    return (clock.tobytes(), tuple(rows),
            float(sum(row.mass_into_cylinder_kg for row in rows)),
            float(sum(row.enthalpy_into_cylinder_j for row in rows)))


def integrate_engine_boundary_streams(
    streams, *, start_time_s: float, end_time_s: float,
) -> EngineBoundaryLedger:
    """Integrate intake, fuel and exhaust schedules on one absolute-time window.

    Every mass/enthalpy pair must have identical knots; all streams must use
    the same enthalpy reference. Linear interpolation is inherited from the
    source-bound schedule type and extrapolation is rejected.
    """
    items = tuple(streams)
    if not items or any(type(item) is not EngineBoundaryStream for item in items):
        raise TypeError("At least one EngineBoundaryStream is required")
    if len({item.identifier for item in items}) != len(items):
        raise ValueError("Engine boundary stream identifiers must be unique")
    references = {item.enthalpy_reference for item in items}
    if len(references) != 1:
        raise ValueError("All engine boundary streams must share one enthalpy reference")
    start = finite(start_time_s, "boundary accounting start")
    end = finite(end_time_s, "boundary accounting end")
    if end <= start:
        raise ValueError("Boundary accounting end must follow its start")
    for item in items:
        item.mass_flow.require_current()
        item.specific_enthalpy.require_current()
    fingerprint = _stream_fingerprint(items)
    computed = _calculate(items, start, end)
    token = _issue_token()
    return EngineBoundaryLedger(
        start, end, next(iter(references)), np.frombuffer(computed[0], dtype=np.float64),
        computed[1], computed[2], computed[3], items, token, fingerprint,
    )
