"""Finite valve stroke and admitted effective-area maps over the shared nozzle.

This module adds actuator time and a caller-owned ``CdA/CdA_max`` map.  It does
not copy a valve-flow equation: every accepted flow is still produced by the
existing :class:`Lh2dtSharedValve` and its shared equilibrium nozzle.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from ..core import finite
from .lh2dt_equipment import Lh2dtSharedValve, SharedValveEvaluation
from .result_provenance import recorded_content_sha256

_PENDING_ACTUATED_VALVE_TRACE_ISSUERS: set[object] = set()


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _fraction(value: float, name: str) -> float:
    value = finite(value, name)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must lie in [0, 1]")
    return value


@dataclass(frozen=True, slots=True)
class ValveMapEvidence:
    """Identity and interpretation of one caller-supplied effective-area map."""

    evidence_id: str
    source_uri: str
    license_id: str
    source_sha256: str
    fluid_basis: str
    pressure_basis: Literal["absolute"] = "absolute"
    map_basis: Literal["CdA_ratio"] = "CdA_ratio"
    qualified_for_prediction: bool = False

    def __post_init__(self):
        for name in ("evidence_id", "source_uri", "license_id", "fluid_basis"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        digest = _text(self.source_sha256, "source_sha256").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        object.__setattr__(self, "source_sha256", digest)
        if not isinstance(self.qualified_for_prediction, bool):
            raise ValueError("qualified_for_prediction must be bool")


@dataclass(frozen=True, slots=True)
class ValveEffectiveAreaMap:
    """Monotone stroke to relative effective-area data; no extrapolation."""

    map_id: str
    stroke_fraction: tuple[float, ...]
    effective_area_fraction: tuple[float, ...]
    evidence: ValveMapEvidence

    def __post_init__(self):
        object.__setattr__(self, "map_id", _text(self.map_id, "map_id"))
        if type(self.evidence) is not ValveMapEvidence:
            raise TypeError("A valve effective-area map requires its typed source-evidence receipt")
        x = tuple(_fraction(v, "stroke_fraction") for v in self.stroke_fraction)
        y = tuple(_fraction(v, "effective_area_fraction") for v in self.effective_area_fraction)
        if len(x) != len(y) or len(x) < 2:
            raise ValueError("A valve map needs at least two paired points")
        if x[0] != 0 or x[-1] != 1 or y[0] != 0:
            raise ValueError("Map support must span stroke [0, 1] and close at zero")
        if any(b <= a for a, b in zip(x, x[1:])):
            raise ValueError("Stroke support must be strictly increasing")
        if any(b < a for a, b in zip(y, y[1:])):
            raise ValueError("Effective area must be nondecreasing with stroke")
        object.__setattr__(self, "stroke_fraction", x)
        object.__setattr__(self, "effective_area_fraction", y)

    def opening_fraction(self, stroke_fraction: float) -> float:
        stroke = _fraction(stroke_fraction, "stroke_fraction")
        return float(np.interp(stroke, self.stroke_fraction, self.effective_area_fraction))

    def stroke_for_opening(self, effective_area_fraction: float, *,
                           selection: Literal["minimum", "maximum"] = "minimum") -> float:
        """Invert the admitted map, resolving flat-area segments explicitly.

        When a target lies on a plateau, ``selection`` chooses its lowest or
        highest supporting stroke. Targets outside the map's effective-area
        range are rejected; the result is a map lookup only, not a flow target.
        """
        target = _fraction(effective_area_fraction, "effective_area_fraction")
        if selection not in {"minimum", "maximum"}:
            raise ValueError("selection must be 'minimum' or 'maximum'")
        x, y = self.stroke_fraction, self.effective_area_fraction
        if target < y[0] or target > y[-1]:
            raise ValueError("Requested area fraction is outside the admitted map range")
        candidates = []
        for x0, x1, y0, y1 in zip(x, x[1:], y, y[1:]):
            if y0 == y1:
                if target == y0:
                    candidates.extend((x0, x1))
            elif y0 <= target <= y1:
                fraction = (target-y0)/(y1-y0)
                candidates.append(x0 + fraction*(x1-x0))
        if not candidates:
            raise ValueError("Requested area fraction has no support in the admitted map")
        return float(min(candidates) if selection == "minimum" else max(candidates))


@dataclass(frozen=True, slots=True)
class StrokeActuator:
    actuator_id: str
    opening_rate_fraction_s: float
    closing_rate_fraction_s: float
    initial_stroke_fraction: float
    clock_id: str
    evidence_id: str

    def __post_init__(self):
        for name in ("actuator_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("opening_rate_fraction_s", "closing_rate_fraction_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        object.__setattr__(self, "initial_stroke_fraction",
                           _fraction(self.initial_stroke_fraction, "initial_stroke_fraction"))

    def advance(self, stroke: float, target: float, duration_s: float) -> float:
        stroke = _fraction(stroke, "stroke_fraction")
        target = _fraction(target, "target_stroke_fraction")
        duration = finite(duration_s, "duration_s")
        if duration < 0:
            raise ValueError("Actuator duration cannot be negative")
        rate = self.opening_rate_fraction_s if target >= stroke else self.closing_rate_fraction_s
        delta = min(abs(target-stroke), rate*duration)
        return stroke + (delta if target >= stroke else -delta)


@dataclass(frozen=True, slots=True)
class ValveCommand:
    start_s: float
    end_s: float
    target_stroke_fraction: float
    command_id: str
    mode: Literal["operate", "hold", "isolate"] = "operate"

    def __post_init__(self):
        start, end = finite(self.start_s, "start_s"), finite(self.end_s, "end_s")
        if start < 0 or end <= start:
            raise ValueError("Command interval must have 0 <= start < end")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)
        object.__setattr__(self, "target_stroke_fraction",
                           _fraction(self.target_stroke_fraction, "target_stroke_fraction"))
        object.__setattr__(self, "command_id", _text(self.command_id, "command_id"))
        if not isinstance(self.mode, str) or self.mode not in {"operate", "hold", "isolate"}:
            raise ValueError("Valve command mode must be 'operate', 'hold', or 'isolate'")
        if self.mode == "isolate" and self.target_stroke_fraction != 0:
            raise ValueError("An isolate command must target zero stroke")


@dataclass(frozen=True, slots=True)
class ActuatedValvePoint:
    time_s: float
    command: ValveCommand
    stroke_fraction: float
    effective_opening_fraction: float
    result: SharedValveEvaluation = field(repr=False, compare=False)

    @property
    def mass_flow_kg_s(self) -> float:
        return float(self.result.mass_flow_kg_s)

    @property
    def upstream_side(self):
        return self.result.upstream_side


@dataclass(frozen=True, slots=True)
class ActuatedValveTrace:
    actuator: StrokeActuator
    area_map: ValveEffectiveAreaMap
    commands: tuple[ValveCommand, ...]
    points: tuple[ActuatedValvePoint, ...]
    left_state: Any = field(repr=False, compare=False)
    right_state: Any = field(repr=False, compare=False)
    owner: Any = field(repr=False, compare=False)
    input_sha256: str
    output_sha256: str
    _owner_signature: tuple[Any, ...] = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_ACTUATED_VALVE_TRACE_ISSUERS:
            raise TypeError("Create actuated-valve traces through FiniteStrokeValve.run")
        _PENDING_ACTUATED_VALVE_TRACE_ISSUERS.remove(self._issuer_token)

    def require_current(self) -> None:
        if self.owner._signature() != self._owner_signature:
            raise ValueError("Valve, actuator, map or shared-nozzle owner changed after issue")
        expected_input = recorded_content_sha256(
            (self.actuator, self.area_map, self.commands, self.left_state, self.right_state))
        expected_output = recorded_content_sha256(tuple(
            (p.time_s, p.command.command_id, p.stroke_fraction,
             p.effective_opening_fraction, p.result) for p in self.points))
        if expected_input != self.input_sha256 or expected_output != self.output_sha256:
            raise ValueError("Actuated-valve trace content changed after issue")


def _issue_actuated_valve_trace(**values):
    token = object()
    _PENDING_ACTUATED_VALVE_TRACE_ISSUERS.add(token)
    try:
        return ActuatedValveTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_ACTUATED_VALVE_TRACE_ISSUERS.discard(token)
        raise


class FiniteStrokeValve:
    """Own one shared valve and apply finite stroke plus an admitted CdA map."""

    def __init__(self, valve: Lh2dtSharedValve, actuator: StrokeActuator,
                 area_map: ValveEffectiveAreaMap):
        if type(valve) is not Lh2dtSharedValve:
            raise TypeError("Finite stroke must wrap the existing shared valve exactly")
        if area_map.evidence.fluid_basis != valve.bridge.basis.fluid:
            raise ValueError("Valve-map fluid basis differs from the shared property basis")
        self.valve, self.actuator, self.area_map = valve, actuator, area_map
        self._issued = []

    def _signature(self):
        return (
            id(self.valve), id(self.valve.nozzle), id(self.valve.bridge),
            id(self.valve.result_factory), self.valve.allow_reverse,
            recorded_content_sha256(self.valve.opening),
            recorded_content_sha256(self.actuator), recorded_content_sha256(self.area_map),
        )

    @staticmethod
    def _schedule(commands: Sequence[ValveCommand]) -> tuple[ValveCommand, ...]:
        commands = tuple(commands)
        if not commands:
            raise ValueError("At least one explicit valve command is required")
        if len({c.command_id for c in commands}) != len(commands):
            raise ValueError("Valve command identities must be unique")
        for previous, current in zip(commands, commands[1:]):
            if previous.end_s != current.start_s:
                raise ValueError("Valve command schedule must be ordered and contiguous")
        return commands

    @staticmethod
    def _command_at(commands, time_s):
        for index, command in enumerate(commands):
            if command.start_s <= time_s < command.end_s:
                return index, command
        if time_s == commands[-1].end_s:
            return len(commands)-1, commands[-1]
        raise ValueError("Every sample must lie within the command support")

    def run(self, left_state, right_state, commands: Sequence[ValveCommand],
            sample_times_s: Sequence[float], *, clock_id: str) -> ActuatedValveTrace:
        if _text(clock_id, "clock_id") != self.actuator.clock_id:
            raise ValueError("Run clock differs from the actuator clock")
        commands = self._schedule(commands)
        times = tuple(finite(t, "sample_time_s") for t in sample_times_s)
        if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("At least two strictly increasing sample times are required")
        if times[0] != commands[0].start_s or times[-1] != commands[-1].end_s:
            raise ValueError("Samples must include the full command support endpoints")
        boundaries = {c.start_s for c in commands} | {commands[-1].end_s}
        if not boundaries.issubset(times):
            raise ValueError("Every command boundary must be sampled exactly")
        signature = self._signature()
        stroke = self.actuator.initial_stroke_fraction
        points = []
        previous = times[0]
        for time_s in times:
            if time_s != previous:
                index, prior_command = self._command_at(commands, previous)
                if time_s > prior_command.end_s:
                    raise ValueError("A sample interval cannot cross an unsampled command boundary")
                stroke = self.actuator.advance(stroke, prior_command.target_stroke_fraction,
                                               time_s-previous)
                previous = time_s
            _, command = self._command_at(commands, time_s)
            opening = self.area_map.opening_fraction(stroke)
            self.valve.set_opening(opening)
            result = self.valve.evaluate(left_state, right_state)
            points.append(ActuatedValvePoint(time_s, command, stroke, opening, result))
        input_sha = recorded_content_sha256(
            (self.actuator, self.area_map, commands, left_state, right_state))
        output_sha = recorded_content_sha256(tuple(
            (p.time_s, p.command.command_id, p.stroke_fraction,
             p.effective_opening_fraction, p.result) for p in points))
        trace = _issue_actuated_valve_trace(
            actuator=self.actuator, area_map=self.area_map, commands=commands,
            points=tuple(points), left_state=left_state, right_state=right_state,
            owner=self, input_sha256=input_sha, output_sha256=output_sha,
            _owner_signature=signature,
        )
        self._issued.append(trace)
        return trace
