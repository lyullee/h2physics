"""Evidence-bearing compressor-map admission over native stage results.

The native compressor remains the thermodynamic and shaft-power owner.  This
module only corrects caller operating coordinates, interpolates declared map
limits and admits original native results inside those limits.
"""

from dataclasses import dataclass, field
from math import sqrt
from weakref import WeakValueDictionary

from ..core import ThermoState, finite
from .lh2dt_compressor import CompressorStageResult, Lh2dtCompressorStage


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be explicit")
    return value


@dataclass(frozen=True, slots=True)
class CompressorMapEvidence:
    evidence_id: str
    source_uri: str
    license_id: str
    source_sha256: str
    pressure_basis: str = "absolute"
    flow_basis: str = "inlet_mass_flow"

    def __post_init__(self):
        for name in ("evidence_id", "source_uri", "license_id", "pressure_basis", "flow_basis"):
            _text(getattr(self, name), name)
        if len(self.source_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_sha256.lower()):
            raise ValueError("source_sha256 must be one lowercase hexadecimal SHA-256")
        if self.pressure_basis != "absolute" or self.flow_basis != "inlet_mass_flow":
            raise ValueError("Only absolute pressure and inlet mass-flow map bases are admitted")


@dataclass(frozen=True, slots=True)
class CompressorMapLine:
    corrected_speed_rad_s: float
    minimum_corrected_flow_kg_s: float
    maximum_corrected_flow_kg_s: float
    minimum_pressure_ratio: float
    maximum_pressure_ratio: float
    minimum_isentropic_efficiency: float
    maximum_isentropic_efficiency: float

    def __post_init__(self):
        finite(self.corrected_speed_rad_s, "corrected_speed_rad_s", positive=True)
        for name in ("minimum_corrected_flow_kg_s", "maximum_corrected_flow_kg_s"):
            finite(getattr(self, name), name, positive=True)
        if self.minimum_corrected_flow_kg_s >= self.maximum_corrected_flow_kg_s:
            raise ValueError("Corrected-flow map bounds must increase")
        for name in ("minimum_pressure_ratio", "maximum_pressure_ratio"):
            finite(getattr(self, name), name, positive=True)
        if self.minimum_pressure_ratio <= 1 or self.minimum_pressure_ratio > self.maximum_pressure_ratio:
            raise ValueError("Compressor pressure-ratio limits must be ordered above one")
        for name in ("minimum_isentropic_efficiency", "maximum_isentropic_efficiency"):
            finite(getattr(self, name), name, positive=True)
        if (self.minimum_isentropic_efficiency > self.maximum_isentropic_efficiency
                or self.maximum_isentropic_efficiency > 1):
            raise ValueError("Efficiency limits must be ordered inside (0, 1]")


@dataclass(frozen=True, slots=True)
class CompressorMapLimits:
    corrected_speed_rad_s: float
    minimum_corrected_flow_kg_s: float
    maximum_corrected_flow_kg_s: float
    minimum_pressure_ratio: float
    maximum_pressure_ratio: float
    minimum_isentropic_efficiency: float
    maximum_isentropic_efficiency: float


@dataclass(frozen=True, slots=True)
class CompressorOperatingMap:
    map_id: str
    reference_temperature_k: float
    reference_pressure_pa: float
    lines: tuple[CompressorMapLine, ...]
    evidence: CompressorMapEvidence

    def __post_init__(self):
        _text(self.map_id, "map_id")
        finite(self.reference_temperature_k, "reference_temperature_k", positive=True)
        finite(self.reference_pressure_pa, "reference_pressure_pa", positive=True)
        lines = tuple(self.lines)
        if len(lines) < 2 or any(not isinstance(row, CompressorMapLine) for row in lines):
            raise ValueError("A compressor map requires at least two admitted speed lines")
        speeds = tuple(row.corrected_speed_rad_s for row in lines)
        if any(b <= a for a, b in zip(speeds, speeds[1:])):
            raise ValueError("Corrected-speed lines must be strictly increasing")
        if not isinstance(self.evidence, CompressorMapEvidence):
            raise TypeError("A compressor map requires source evidence")
        object.__setattr__(self, "lines", lines)

    def corrected_coordinates(self, inlet: ThermoState, mass_flow_kg_s: float, shaft_speed_rad_s: float):
        flow = finite(mass_flow_kg_s, "mass_flow_kg_s", positive=True)
        speed = finite(shaft_speed_rad_s, "shaft_speed_rad_s", positive=True)
        theta = inlet.temperature_k / self.reference_temperature_k
        delta = inlet.pressure_pa / self.reference_pressure_pa
        return flow * sqrt(theta) / delta, speed / sqrt(theta)

    def limits(self, corrected_speed_rad_s: float) -> CompressorMapLimits:
        speed = finite(corrected_speed_rad_s, "corrected_speed_rad_s", positive=True)
        if speed < self.lines[0].corrected_speed_rad_s or speed > self.lines[-1].corrected_speed_rad_s:
            raise ValueError("Corrected speed is outside the admitted map; extrapolation is forbidden")
        left, right = self.lines[0], self.lines[-1]
        for candidate, following in zip(self.lines, self.lines[1:]):
            if candidate.corrected_speed_rad_s <= speed <= following.corrected_speed_rad_s:
                left, right = candidate, following
                break
        fraction = ((speed-left.corrected_speed_rad_s)
                    /(right.corrected_speed_rad_s-left.corrected_speed_rad_s))
        def blend(name):
            return getattr(left, name)+fraction*(getattr(right, name)-getattr(left, name))
        return CompressorMapLimits(speed, blend("minimum_corrected_flow_kg_s"),
            blend("maximum_corrected_flow_kg_s"), blend("minimum_pressure_ratio"),
            blend("maximum_pressure_ratio"), blend("minimum_isentropic_efficiency"),
            blend("maximum_isentropic_efficiency"))


@dataclass(frozen=True, slots=True)
class CompressorCommand:
    time_s: float
    shaft_speed_rad_s: float
    mass_flow_kg_s: float
    mode: str = "compressing"

    def __post_init__(self):
        finite(self.time_s, "time_s")
        finite(self.shaft_speed_rad_s, "shaft_speed_rad_s")
        finite(self.mass_flow_kg_s, "mass_flow_kg_s")
        if self.mode not in {"compressing", "isolated"}:
            raise ValueError("Choose an explicit compressing or isolated command")
        if self.mode == "compressing" and (self.shaft_speed_rad_s <= 0 or self.mass_flow_kg_s <= 0):
            raise ValueError("Compressing mode requires positive speed and flow")
        if self.mode == "isolated" and (self.shaft_speed_rad_s != 0 or self.mass_flow_kg_s != 0):
            raise ValueError("Isolated mode requires zero speed and flow")


@dataclass(frozen=True, slots=True)
class MappedCompressorPoint:
    command: CompressorCommand
    corrected_flow_kg_s: float | None
    corrected_speed_rad_s: float | None
    limits: CompressorMapLimits | None
    native_result: CompressorStageResult


@dataclass(frozen=True, slots=True, weakref_slot=True)
class MappedCompressorTrace:
    clock_id: str
    points: tuple[MappedCompressorPoint, ...]
    map_id: str
    evidence_id: str
    _owner: object = field(repr=False, compare=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def require_current(self):
        self._owner.require_trace(self)


class MappedCompressor:
    """Admit scheduled native stage points against a caller-owned map envelope."""

    def __init__(self, stage: Lh2dtCompressorStage, operating_map: CompressorOperatingMap):
        if not isinstance(stage, Lh2dtCompressorStage):
            raise TypeError("MappedCompressor requires an actual Lh2dtCompressorStage")
        if not isinstance(operating_map, CompressorOperatingMap):
            raise TypeError("MappedCompressor requires CompressorOperatingMap")
        self.stage, self.operating_map = stage, operating_map
        self._stage_origin, self._map_origin = stage, operating_map
        self._map_stamp = repr(operating_map)
        self._traces = WeakValueDictionary()

    def _require_identity(self):
        if self.stage is not self._stage_origin or self.operating_map is not self._map_origin:
            raise ValueError("Original compressor/map ownership changed")
        if repr(self.operating_map) != self._map_stamp:
            raise ValueError("Admitted compressor map changed")

    @staticmethod
    def _seal(trace):
        return (trace.clock_id, trace.map_id, trace.evidence_id,
                tuple((p.command, p.corrected_flow_kg_s, p.corrected_speed_rad_s,
                       p.limits, id(p.native_result)) for p in trace.points))

    def require_trace(self, trace: MappedCompressorTrace):
        if not isinstance(trace, MappedCompressorTrace):
            raise TypeError("Supply an original MappedCompressorTrace")
        self._require_identity()
        if self._traces.get(id(trace)) is not trace or trace._owner is not self or trace._seal != self._seal(trace):
            raise ValueError("Original mapped compressor trace became stale")
        for point in trace.points:
            point.native_result.require_current()

    def evaluate(self, inlet: ThermoState, commands, *, clock_id: str,
                 upstream_node: str | None = None, downstream_node: str | None = None):
        self._require_identity()
        _text(clock_id, "clock_id")
        schedule = tuple(commands)
        if not schedule or any(not isinstance(row, CompressorCommand) for row in schedule):
            raise ValueError("Supply one or more explicit CompressorCommand rows")
        if any(b.time_s <= a.time_s for a, b in zip(schedule, schedule[1:])):
            raise ValueError("Compressor command times must be strictly increasing")
        points = []
        for command in schedule:
            result = self.stage.evaluate(inlet, command.mass_flow_kg_s, mode=command.mode,
                upstream_node=upstream_node, downstream_node=downstream_node)
            if command.mode == "isolated":
                points.append(MappedCompressorPoint(command, None, None, None, result))
                continue
            corrected_flow, corrected_speed = self.operating_map.corrected_coordinates(
                inlet, command.mass_flow_kg_s, command.shaft_speed_rad_s)
            limits = self.operating_map.limits(corrected_speed)
            if not limits.minimum_corrected_flow_kg_s <= corrected_flow <= limits.maximum_corrected_flow_kg_s:
                raise ValueError("Corrected flow is outside surge/choke admission limits")
            if not limits.minimum_pressure_ratio <= result.pressure_ratio <= limits.maximum_pressure_ratio:
                raise ValueError("Native pressure ratio is outside the admitted map limits")
            if not (limits.minimum_isentropic_efficiency <= result.isentropic_efficiency
                    <= limits.maximum_isentropic_efficiency):
                raise ValueError("Native efficiency is outside the admitted map limits")
            points.append(MappedCompressorPoint(command, corrected_flow, corrected_speed, limits, result))
        trace = MappedCompressorTrace(clock_id, tuple(points), self.operating_map.map_id,
            self.operating_map.evidence.evidence_id, self)
        object.__setattr__(trace, "_seal", self._seal(trace))
        self._traces[id(trace)] = trace
        return trace
