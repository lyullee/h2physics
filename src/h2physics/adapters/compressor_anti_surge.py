"""Evidence-bound static compressor surge-margin admission.

This module consumes an original native compressor-map trace and a caller-
provided surge boundary. It applies no performance correlation, surge model,
controller, recycle-valve law or rotating machinery dynamics.
"""

from dataclasses import dataclass, field
from weakref import WeakValueDictionary

from ..core import finite
from .compressor_map import MappedCompressorTrace


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be explicit")
    return value


@dataclass(frozen=True, slots=True)
class SurgeBoundaryEvidence:
    evidence_id: str
    source_uri: str
    license_id: str
    source_sha256: str
    speed_basis: str = "corrected_speed_rad_s"
    flow_basis: str = "corrected_inlet_mass_flow_kg_s"

    def __post_init__(self):
        for name in ("evidence_id", "source_uri", "license_id", "speed_basis", "flow_basis"):
            _text(getattr(self, name), name)
        digest = self.source_sha256.lower() if isinstance(self.source_sha256, str) else ""
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("source_sha256 must be a 64-character SHA-256 digest")
        if self.speed_basis != "corrected_speed_rad_s":
            raise ValueError("Surge-boundary speed must use corrected rad/s")
        if self.flow_basis != "corrected_inlet_mass_flow_kg_s":
            raise ValueError("Surge-boundary flow must use corrected inlet kg/s")
        object.__setattr__(self, "source_sha256", digest)


@dataclass(frozen=True, slots=True)
class SurgeLinePoint:
    corrected_speed_rad_s: float
    corrected_surge_flow_kg_s: float

    def __post_init__(self):
        finite(self.corrected_speed_rad_s, "corrected_speed_rad_s", positive=True)
        finite(self.corrected_surge_flow_kg_s, "corrected_surge_flow_kg_s", positive=True)


@dataclass(frozen=True, slots=True)
class SurgeBoundary:
    boundary_id: str
    points: tuple[SurgeLinePoint, ...]
    evidence: SurgeBoundaryEvidence

    def __post_init__(self):
        _text(self.boundary_id, "boundary_id")
        points = tuple(self.points)
        if len(points) < 2 or any(not isinstance(point, SurgeLinePoint) for point in points):
            raise ValueError("A surge boundary requires at least two typed speed/flow points")
        if any(b.corrected_speed_rad_s <= a.corrected_speed_rad_s
               for a, b in zip(points, points[1:])):
            raise ValueError("Surge-boundary speeds must be strictly increasing")
        if not isinstance(self.evidence, SurgeBoundaryEvidence):
            raise TypeError("A surge boundary requires source, rights and hash evidence")
        object.__setattr__(self, "points", points)

    def flow_at(self, corrected_speed_rad_s: float) -> float:
        speed = finite(corrected_speed_rad_s, "corrected_speed_rad_s", positive=True)
        if speed < self.points[0].corrected_speed_rad_s or speed > self.points[-1].corrected_speed_rad_s:
            raise ValueError("Corrected speed is outside surge evidence; extrapolation is forbidden")
        for left, right in zip(self.points, self.points[1:]):
            if left.corrected_speed_rad_s <= speed <= right.corrected_speed_rad_s:
                ratio = ((speed-left.corrected_speed_rad_s)
                         /(right.corrected_speed_rad_s-left.corrected_speed_rad_s))
                return left.corrected_surge_flow_kg_s + ratio * (
                    right.corrected_surge_flow_kg_s-left.corrected_surge_flow_kg_s)
        raise ValueError("No surge-boundary interpolation segment contains this speed")


@dataclass(frozen=True, slots=True)
class AntiSurgeMarginPolicy:
    policy_id: str
    minimum_corrected_flow_margin_kg_s: float
    evidence_id: str
    tolerance_kg_s: float = 0.0

    def __post_init__(self):
        _text(self.policy_id, "policy_id")
        _text(self.evidence_id, "evidence_id")
        margin = finite(self.minimum_corrected_flow_margin_kg_s,
                        "minimum_corrected_flow_margin_kg_s")
        tolerance = finite(self.tolerance_kg_s, "tolerance_kg_s")
        if margin < 0 or tolerance < 0:
            raise ValueError("Anti-surge margin and tolerance cannot be negative")
        object.__setattr__(self, "minimum_corrected_flow_margin_kg_s", margin)
        object.__setattr__(self, "tolerance_kg_s", tolerance)


@dataclass(frozen=True, slots=True)
class AntiSurgePoint:
    time_s: float
    mode: str
    corrected_speed_rad_s: float | None
    corrected_flow_kg_s: float | None
    surge_flow_kg_s: float | None
    flow_margin_kg_s: float | None
    required_margin_kg_s: float
    applicable: bool
    admissible: bool
    native_result: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class AntiSurgeTrace:
    compressor_trace: MappedCompressorTrace
    boundary: SurgeBoundary
    policy: AntiSurgeMarginPolicy
    points: tuple[AntiSurgePoint, ...]
    _owner: object = field(repr=False, compare=False)
    _seal: tuple = field(default=(), repr=False, compare=False)

    @property
    def feasible(self) -> bool:
        self.require_current()
        return all(point.admissible for point in self.points)

    def require_feasible(self):
        self.require_current()
        if not all(point.admissible for point in self.points):
            raise ValueError("One or more native compressor points violate the declared surge margin")
        return self

    def require_current(self):
        self._owner.require_trace(self)
        return self


class CompressorAntiSurgeGuard:
    """Check a map trace against an explicit static boundary and margin policy."""

    def __init__(self, boundary: SurgeBoundary, policy: AntiSurgeMarginPolicy):
        if not isinstance(boundary, SurgeBoundary):
            raise TypeError("Supply an evidence-bearing SurgeBoundary")
        if not isinstance(policy, AntiSurgeMarginPolicy):
            raise TypeError("Supply an explicit AntiSurgeMarginPolicy")
        self.boundary, self.policy = boundary, policy
        self._boundary_origin, self._policy_origin = boundary, policy
        self._receipts = WeakValueDictionary()

    def _signature(self, trace):
        return (id(trace.compressor_trace), trace.boundary, trace.policy,
                tuple((p.time_s, p.mode, p.corrected_speed_rad_s, p.corrected_flow_kg_s,
                       p.surge_flow_kg_s, p.flow_margin_kg_s, p.required_margin_kg_s,
                       p.applicable, p.admissible, id(p.native_result)) for p in trace.points))

    def require_trace(self, trace):
        if not isinstance(trace, AntiSurgeTrace):
            raise TypeError("Supply the original AntiSurgeTrace")
        if self.boundary is not self._boundary_origin or self.policy is not self._policy_origin:
            raise ValueError("Original surge-boundary or margin-policy ownership changed")
        trace.compressor_trace.require_current()
        if (self._receipts.get(id(trace)) is not trace or trace._owner is not self
                or trace.boundary is not self.boundary or trace.policy is not self.policy
                or trace._seal != self._signature(trace)):
            raise ValueError("Original anti-surge admission receipt became stale")

    def evaluate(self, compressor_trace: MappedCompressorTrace) -> AntiSurgeTrace:
        if not isinstance(compressor_trace, MappedCompressorTrace):
            raise TypeError("Anti-surge admission requires an original MappedCompressorTrace")
        compressor_trace.require_current()
        points = []
        for mapped in compressor_trace.points:
            command = mapped.command
            if command.mode == "isolated":
                points.append(AntiSurgePoint(command.time_s, command.mode, None, None, None,
                    None, self.policy.minimum_corrected_flow_margin_kg_s, False, True,
                    mapped.native_result))
                continue
            speed, flow = mapped.corrected_speed_rad_s, mapped.corrected_flow_kg_s
            if speed is None or flow is None:
                raise ValueError("An active map point lacks corrected speed or flow")
            surge_flow = self.boundary.flow_at(speed)
            margin = finite(flow-surge_flow, "corrected flow margin")
            admitted = margin+self.policy.tolerance_kg_s >= self.policy.minimum_corrected_flow_margin_kg_s
            points.append(AntiSurgePoint(command.time_s, command.mode, speed, flow, surge_flow,
                margin, self.policy.minimum_corrected_flow_margin_kg_s, True, admitted,
                mapped.native_result))
        receipt = AntiSurgeTrace(compressor_trace, self.boundary, self.policy,
                                 tuple(points), self)
        object.__setattr__(receipt, "_seal", self._signature(receipt))
        self._receipts[id(receipt)] = receipt
        compressor_trace.require_current()
        self.require_trace(receipt)
        return receipt


__all__ = ["SurgeBoundaryEvidence", "SurgeLinePoint", "SurgeBoundary",
           "AntiSurgeMarginPolicy", "AntiSurgePoint", "AntiSurgeTrace",
           "CompressorAntiSurgeGuard"]
