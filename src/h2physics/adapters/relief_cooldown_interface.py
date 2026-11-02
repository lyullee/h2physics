"""Evidence-bound interface between native tank relief and line cooldown runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from ..core import immutable_array, PropertyBasis, finite
from .lh2dt_dynamics import DynamicLineCooldownAudit
from .lh2dt_relief import ReliefTankTrace
from .result_provenance import recorded_content_sha256


class ReliefCooldownInterfaceError(ValueError):
    """Raised when two native results cannot be admitted as one time history."""


@dataclass(frozen=True, slots=True)
class ReliefCooldownPort:
    """Caller-qualified single-phase port on one declared thermodynamic basis."""

    port_id: str
    basis: PropertyBasis
    phase: Literal["liquid", "gas", "two_phase", "supercritical", "supercritical_gas",
                   "supercritical_liquid"]
    evidence_id: str
    pressure_basis: Literal["absolute"] = "absolute"

    def __post_init__(self) -> None:
        for value, name in ((self.port_id, "port_id"), (self.evidence_id, "evidence_id")):
            if not isinstance(value, str) or not value.strip():
                raise ReliefCooldownInterfaceError(f"{name} must be explicit")
        if type(self.basis) is not PropertyBasis:
            raise TypeError("Port basis must be an explicit PropertyBasis")
        if self.phase not in {"liquid", "gas", "two_phase", "supercritical",
                              "supercritical_gas", "supercritical_liquid"}:
            raise ReliefCooldownInterfaceError("Declare one supported thermodynamic phase")
        if self.pressure_basis != "absolute":
            raise ReliefCooldownInterfaceError("Relief/cooldown port pressure must be absolute")


@dataclass(frozen=True, slots=True)
class ReliefCooldownInterface:
    """A receipt joining two existing calculations without re-solving either.

    `line_inlet_*` are caller supplied, independently obtained native boundary
    samples. The receipt compares them with released tank totals at exact shared
    times. It does not claim the line's cooldown energy is caused by relief flow.
    """

    relief: ReliefTankTrace
    cooldown: DynamicLineCooldownAudit
    time_s: np.ndarray
    relief_mass_kg: np.ndarray
    relief_enthalpy_j: np.ndarray
    line_inlet_mass_kg: np.ndarray
    line_inlet_enthalpy_j: np.ndarray
    mass_difference_kg: np.ndarray
    enthalpy_difference_j: np.ndarray
    boundary_id: str
    evidence_ids: tuple[str, ...]
    relief_port: ReliefCooldownPort
    line_port: ReliefCooldownPort
    mass_tolerance_kg: float
    enthalpy_tolerance_j: float
    _content_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.relief) is not ReliefTankTrace:
            raise TypeError("relief must be a ReliefTankTrace")
        if type(self.cooldown) is not DynamicLineCooldownAudit:
            raise TypeError("cooldown must be a DynamicLineCooldownAudit")
        if type(self.relief_port) is not ReliefCooldownPort or type(self.line_port) is not ReliefCooldownPort:
            raise TypeError("Both sides require an explicit ReliefCooldownPort")
        self.relief.require_current()
        self.cooldown.require_current()
        if self.relief.clock_id != self.cooldown.clock_id:
            raise ReliefCooldownInterfaceError("Relief and cooldown clock identities differ")
        if isinstance(self.evidence_ids, (str, bytes)):
            raise ReliefCooldownInterfaceError("Evidence IDs must be a sequence of complete identities")
        evidence_ids = tuple(self.evidence_ids)
        if (not isinstance(self.boundary_id, str) or not self.boundary_id.strip()
                or not evidence_ids
                or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)):
            raise ReliefCooldownInterfaceError("Boundary identity and evidence IDs are required")
        if self.relief_port.port_id == self.line_port.port_id:
            raise ReliefCooldownInterfaceError("Relief outlet and line inlet need distinct port identities")
        if (self.relief_port.phase != self.line_port.phase
                or self.relief_port.basis != self.line_port.basis):
            raise ReliefCooldownInterfaceError(
                "Relief outlet and line inlet phase/property bases must match within one receipt"
            )
        if not {self.relief_port.evidence_id, self.line_port.evidence_id}.issubset(evidence_ids):
            raise ReliefCooldownInterfaceError("Retain evidence for both qualified interface ports")
        native_basis = getattr(getattr(self.relief.native_tank, "properties", None), "basis", None)
        if type(native_basis) is not PropertyBasis:
            raise ReliefCooldownInterfaceError("Native relief owner does not expose its property basis")
        native_basis.require_compatible(self.relief_port.basis)
        self.cooldown.initial.basis.require_compatible(self.line_port.basis)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        times = np.asarray(self.time_s, dtype=float)
        if times.ndim != 1 or times.size < 2 or np.any(~np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise ReliefCooldownInterfaceError("Interface time must be finite and increasing")
        if (times[0] < self.relief.time_s[0] or times[-1] > self.relief.time_s[-1]
                or times[0] < self.cooldown.start_time_s or times[-1] > self.cooldown.end_time_s):
            raise ReliefCooldownInterfaceError("Interface times exceed one of the retained source windows")
        relief_indexes = np.searchsorted(self.relief.time_s, times)
        if (np.any(relief_indexes >= self.relief.time_s.size)
                or not np.allclose(self.relief.time_s[relief_indexes], times, rtol=0., atol=1e-10)):
            raise ReliefCooldownInterfaceError("Interface times must be retained native relief samples")
        for name in ("relief_mass_kg", "relief_enthalpy_j", "line_inlet_mass_kg",
                     "line_inlet_enthalpy_j", "mass_difference_kg", "enthalpy_difference_j"):
            values = np.array(getattr(self, name), dtype=float, copy=True)
            if values.shape != times.shape or np.any(~np.isfinite(values)):
                raise ReliefCooldownInterfaceError(f"{name} must match the finite interface time grid")
            values = immutable_array(values, name="values")
            object.__setattr__(self, name, values)
        times = np.array(times, copy=True)
        times = immutable_array(times, name="times")
        object.__setattr__(self, "time_s", times)
        if not np.allclose(self.relief_mass_kg, self.relief.released_mass_kg[relief_indexes],
                           rtol=0., atol=1e-12):
            raise ReliefCooldownInterfaceError("Retained relief mass differs from native accepted samples")
        if not np.allclose(self.relief_enthalpy_j, self.relief.released_enthalpy_j[relief_indexes],
                           rtol=0., atol=1e-8):
            raise ReliefCooldownInterfaceError("Retained relief enthalpy differs from native accepted samples")
        if (np.any(self.line_inlet_mass_kg < 0)
                or np.any(np.diff(self.line_inlet_mass_kg) < -1e-12)):
            raise ReliefCooldownInterfaceError("Line inlet cumulative mass must be nonnegative and nondecreasing")
        if np.any(np.diff(self.relief_mass_kg) < -1e-12) or np.any(np.diff(self.relief_enthalpy_j) < -1e-8):
            raise ReliefCooldownInterfaceError("Relief cumulative releases must be nondecreasing")
        if not np.allclose(self.mass_difference_kg, self.relief_mass_kg-self.line_inlet_mass_kg,
                           rtol=0, atol=1e-12):
            raise ReliefCooldownInterfaceError("Mass difference does not match retained boundary histories")
        if not np.allclose(self.enthalpy_difference_j,
                           self.relief_enthalpy_j-self.line_inlet_enthalpy_j, rtol=0, atol=1e-8):
            raise ReliefCooldownInterfaceError("Enthalpy difference does not match retained boundary histories")
        mass_tolerance = finite(self.mass_tolerance_kg, "mass_tolerance_kg")
        enthalpy_tolerance = finite(self.enthalpy_tolerance_j, "enthalpy_tolerance_j")
        if mass_tolerance < 0 or enthalpy_tolerance < 0:
            raise ReliefCooldownInterfaceError("Interface tolerances must be nonnegative")
        object.__setattr__(self, "mass_tolerance_kg", mass_tolerance)
        object.__setattr__(self, "enthalpy_tolerance_j", enthalpy_tolerance)
        object.__setattr__(self, "_content_sha256", self._current_content_sha256())

    def _current_content_sha256(self) -> str:
        """Seal interface declarations and caller boundary samples after admission."""
        return recorded_content_sha256((
            id(self.relief), id(self.cooldown), self.time_s,
            self.relief_mass_kg, self.relief_enthalpy_j,
            self.line_inlet_mass_kg, self.line_inlet_enthalpy_j,
            self.mass_difference_kg, self.enthalpy_difference_j,
            self.boundary_id, self.evidence_ids,
            self.relief_port, self.line_port,
            self.mass_tolerance_kg, self.enthalpy_tolerance_j,
        ))

    @property
    def admitted(self) -> bool:
        return bool(np.all(np.abs(self.mass_difference_kg) <= self.mass_tolerance_kg)
                    and np.all(np.abs(self.enthalpy_difference_j) <= self.enthalpy_tolerance_j))

    def require_current(self) -> ReliefCooldownInterface:
        if self._current_content_sha256() != self._content_sha256:
            raise ReliefCooldownInterfaceError(
                "Interface evidence, closure tolerances or retained boundary histories changed"
            )
        self.relief.require_current()
        self.cooldown.require_current()
        if not self.admitted:
            raise ReliefCooldownInterfaceError("Tank release and line inlet boundary histories do not close")
        return self


@dataclass(frozen=True, slots=True)
class ReliefCooldownSequence:
    """Compose contiguous, independently qualified phase intervals on one boundary."""

    segments: tuple[ReliefCooldownInterface, ...]
    _content_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        segments = tuple(self.segments)
        if not segments or any(type(segment) is not ReliefCooldownInterface for segment in segments):
            raise TypeError("A relief/cooldown sequence requires original interface segments")
        for segment in segments:
            segment.require_current()
        first = segments[0]
        for left, right in zip(segments, segments[1:]):
            if (left.relief is not first.relief or left.cooldown is not first.cooldown
                    or left.boundary_id != first.boundary_id
                    or left.relief_port.port_id != first.relief_port.port_id
                    or left.line_port.port_id != first.line_port.port_id
                    or left.relief_port.basis != first.relief_port.basis
                    or left.line_port.basis != first.line_port.basis):
                raise ReliefCooldownInterfaceError(
                    "Sequence segments must retain the same traces, boundary, ports and property bases"
                )
            if left.time_s[-1] != right.time_s[0]:
                raise ReliefCooldownInterfaceError(
                    "Phase-segment histories must meet at one retained event-time sample"
                )
            mass_tolerance = max(left.mass_tolerance_kg, right.mass_tolerance_kg)
            enthalpy_tolerance = max(left.enthalpy_tolerance_j, right.enthalpy_tolerance_j)
            if (abs(left.relief_mass_kg[-1]-right.relief_mass_kg[0]) > mass_tolerance
                    or abs(left.line_inlet_mass_kg[-1]-right.line_inlet_mass_kg[0]) > mass_tolerance):
                raise ReliefCooldownInterfaceError(
                    "Cumulative mass ledgers must remain continuous across a segment boundary"
                )
            if (abs(left.relief_enthalpy_j[-1]-right.relief_enthalpy_j[0]) > enthalpy_tolerance
                    or abs(left.line_inlet_enthalpy_j[-1]-right.line_inlet_enthalpy_j[0])
                    > enthalpy_tolerance):
                raise ReliefCooldownInterfaceError(
                    "Cumulative enthalpy ledgers must remain continuous across a segment boundary"
                )
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "_content_sha256", self._current_content_sha256())

    def _current_content_sha256(self) -> str:
        return recorded_content_sha256(tuple(
            (id(segment), segment._content_sha256, segment.relief_port, segment.line_port,
             segment.time_s, segment.relief_mass_kg, segment.relief_enthalpy_j,
             segment.line_inlet_mass_kg, segment.line_inlet_enthalpy_j)
            for segment in self.segments
        ))

    @property
    def phase_intervals(self):
        return tuple((segment.relief_port.phase, float(segment.time_s[0]),
                      float(segment.time_s[-1])) for segment in self.segments)

    @property
    def time_s(self):
        return np.concatenate((self.segments[0].time_s,
                               *(segment.time_s[1:] for segment in self.segments[1:])))

    def require_current(self) -> "ReliefCooldownSequence":
        if self._current_content_sha256() != self._content_sha256:
            raise ReliefCooldownInterfaceError("Relief/cooldown sequence segments changed after composition")
        for segment in self.segments:
            segment.require_current()
        return self


def bind_relief_cooldown_sequence(
    segments: Sequence[ReliefCooldownInterface],
) -> ReliefCooldownSequence:
    """Join phase-specific receipts at exact retained event-time samples."""
    if isinstance(segments, (str, bytes)):
        raise TypeError("Supply interface segments as a sequence, not a text identity")
    return ReliefCooldownSequence(tuple(segments))


def bind_relief_to_line_cooldown(
    relief: ReliefTankTrace,
    cooldown: DynamicLineCooldownAudit,
    *,
    time_s: Sequence[float],
    line_inlet_mass_kg: Sequence[float],
    line_inlet_enthalpy_j: Sequence[float],
    boundary_id: str,
    evidence_ids: Sequence[str],
    relief_port: ReliefCooldownPort,
    line_port: ReliefCooldownPort,
    mass_tolerance_kg: float,
    enthalpy_tolerance_j: float,
) -> ReliefCooldownInterface:
    """Compare caller supplied line-inlet cumulative flows with tank releases."""
    if type(relief) is not ReliefTankTrace or type(cooldown) is not DynamicLineCooldownAudit:
        raise TypeError("Native relief trace and dynamic cooldown audit are required")
    relief.require_current()
    cooldown.require_current()
    if relief.clock_id != cooldown.clock_id:
        raise ReliefCooldownInterfaceError("Relief and cooldown clock identities differ")
    if isinstance(evidence_ids, (str, bytes)):
        raise ReliefCooldownInterfaceError("Evidence IDs must be a sequence of complete identities")
    if (not isinstance(boundary_id, str) or not boundary_id.strip() or not evidence_ids
            or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)):
        raise ReliefCooldownInterfaceError("A named physical boundary and trace evidence are required")
    if type(relief_port) is not ReliefCooldownPort or type(line_port) is not ReliefCooldownPort:
        raise TypeError("Both sides require an explicit ReliefCooldownPort")
    t = np.asarray(time_s, dtype=float)
    if t.ndim != 1 or t.size < 2 or np.any(~np.isfinite(t)) or np.any(np.diff(t) <= 0):
        raise ReliefCooldownInterfaceError("Provide at least two increasing common-clock samples")
    if t[0] < relief.time_s[0] or t[-1] > relief.time_s[-1]:
        raise ReliefCooldownInterfaceError("Requested interface times exceed the retained relief trace")
    if t[0] < cooldown.start_time_s or t[-1] > cooldown.end_time_s:
        raise ReliefCooldownInterfaceError("Requested interface times exceed the retained cooldown interval")
    indexes = np.searchsorted(relief.time_s, t)
    if (np.any(indexes >= relief.time_s.size)
            or not np.allclose(relief.time_s[indexes], t, rtol=0., atol=1e-10)):
        raise ReliefCooldownInterfaceError(
            "Common times must be retained relief samples; interpolation could smear valve events"
        )
    released_mass = relief.released_mass_kg[indexes]
    released_enthalpy = relief.released_enthalpy_j[indexes]
    inlet_mass = np.asarray(line_inlet_mass_kg, dtype=float)
    inlet_enthalpy = np.asarray(line_inlet_enthalpy_j, dtype=float)
    if inlet_mass.shape != t.shape or inlet_enthalpy.shape != t.shape:
        raise ReliefCooldownInterfaceError("Boundary cumulative flow histories must match the common time grid")
    return ReliefCooldownInterface(
        relief, cooldown, t, released_mass, released_enthalpy, inlet_mass, inlet_enthalpy,
        released_mass-inlet_mass, released_enthalpy-inlet_enthalpy,
        boundary_id, tuple(evidence_ids), relief_port, line_port,
        finite(mass_tolerance_kg, "mass_tolerance_kg"),
        finite(enthalpy_tolerance_j, "enthalpy_tolerance_j"),
    )
