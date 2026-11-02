"""Finite speed commands and evidence gates for an original native pump.

The native pump remains the pressure/flow/enthalpy owner.  This module advances
only a declared shaft-speed actuator and compares each retained native result to
a caller-supplied normalized evidence curve.  It is not a cavitation, rotor or
hydraulic-network solver.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from ..core import finite
from .result_provenance import recorded_content_sha256

_PENDING_PUMP_TRACE_ISSUERS: set[object] = set()


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value.strip()


def _fraction(value: float, name: str, *, positive: bool = False) -> float:
    value = finite(value, name)
    if value < 0 or value > 1 or (positive and value == 0):
        interval = "(0, 1]" if positive else "[0, 1]"
        raise ValueError(f"{name} must lie in {interval}")
    return value


@dataclass(frozen=True, slots=True)
class PumpMapEvidence:
    evidence_id: str
    source_uri: str
    license_id: str
    source_sha256: str
    fluid_basis: str
    pressure_basis: Literal["absolute"] = "absolute"
    flow_basis: Literal["mass"] = "mass"
    qualified_for_prediction: bool = False

    def __post_init__(self):
        for name in ("evidence_id", "source_uri", "license_id", "fluid_basis"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        digest = _text(self.source_sha256, "source_sha256").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
        object.__setattr__(self, "source_sha256", digest)
        if not isinstance(self.qualified_for_prediction, bool):
            raise TypeError("qualified_for_prediction must be bool")


@dataclass(frozen=True, slots=True)
class NormalizedPumpMap:
    """One reference-speed curve used only to admit native operating points."""

    map_id: str
    reference_speed_rpm: float
    reference_mass_flow_kg_s: float
    reference_pressure_rise_pa: float
    reference_npsh_required_m: float
    flow_fraction: tuple[float, ...]
    pressure_rise_fraction: tuple[float, ...]
    efficiency: tuple[float, ...]
    npsh_required_fraction: tuple[float, ...]
    evidence: PumpMapEvidence
    relative_admission_tolerance: float = 1e-6

    def __post_init__(self):
        object.__setattr__(self, "map_id", _text(self.map_id, "map_id"))
        for name in ("reference_speed_rpm", "reference_mass_flow_kg_s",
                     "reference_pressure_rise_pa", "reference_npsh_required_m",
                     "relative_admission_tolerance"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))
        x = tuple(finite(v, "flow_fraction") for v in self.flow_fraction)
        head = tuple(finite(v, "pressure_rise_fraction") for v in self.pressure_rise_fraction)
        efficiency = tuple(_fraction(v, "efficiency", positive=True) for v in self.efficiency)
        npsh = tuple(finite(v, "npsh_required_fraction", positive=True)
                     for v in self.npsh_required_fraction)
        if len(x) < 2 or not (len(x) == len(head) == len(efficiency) == len(npsh)):
            raise ValueError("A normalized pump map needs at least two complete curve points")
        if x[0] != 0 or any(v < 0 for v in x) or any(b <= a for a, b in zip(x, x[1:])):
            raise ValueError("Flow support must start at zero and increase strictly")
        if any(v < 0 for v in head) or any(b > a for a, b in zip(head, head[1:])):
            raise ValueError("Pressure-rise fraction must be nonnegative and nonincreasing")
        object.__setattr__(self, "flow_fraction", x)
        object.__setattr__(self, "pressure_rise_fraction", head)
        object.__setattr__(self, "efficiency", efficiency)
        object.__setattr__(self, "npsh_required_fraction", npsh)

    def admit(self, *, speed_fraction: float, mass_flow_kg_s: float,
              pressure_rise_pa: float, npsh_required_m: float):
        speed = _fraction(speed_fraction, "speed_fraction", positive=True)
        flow = finite(mass_flow_kg_s, "mass_flow_kg_s")
        rise = finite(pressure_rise_pa, "pressure_rise_pa")
        required = finite(npsh_required_m, "npsh_required_m")
        if flow < 0:
            raise ValueError("The admitted native pump level does not reverse flow")
        reduced_flow = flow / (self.reference_mass_flow_kg_s * speed)
        if reduced_flow < self.flow_fraction[0] or reduced_flow > self.flow_fraction[-1]:
            raise ValueError("Native pump flow is outside the admitted map support")
        head_fraction = float(np.interp(reduced_flow, self.flow_fraction,
                                        self.pressure_rise_fraction))
        expected_rise = self.reference_pressure_rise_pa * speed**2 * head_fraction
        expected_npsh = self.reference_npsh_required_m * speed**2 * float(np.interp(
            reduced_flow, self.flow_fraction, self.npsh_required_fraction))
        head_error = abs(rise-expected_rise) / max(abs(expected_rise), 1.0)
        npsh_error = abs(required-expected_npsh) / max(abs(expected_npsh), 1e-12)
        return reduced_flow, expected_rise, expected_npsh, head_error, npsh_error


@dataclass(frozen=True, slots=True)
class PumpSpeedActuator:
    actuator_id: str
    clock_id: str
    initial_speed_fraction: float
    ramp_up_fraction_s: float
    ramp_down_fraction_s: float
    evidence_id: str

    def __post_init__(self):
        for name in ("actuator_id", "clock_id", "evidence_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "initial_speed_fraction",
                           _fraction(self.initial_speed_fraction, "initial_speed_fraction"))
        for name in ("ramp_up_fraction_s", "ramp_down_fraction_s"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=True))

    def advance(self, current: float, target: float, duration_s: float) -> float:
        current = _fraction(current, "current_speed_fraction")
        target = _fraction(target, "target_speed_fraction")
        duration = finite(duration_s, "duration_s")
        if duration < 0:
            raise ValueError("Pump actuator duration cannot be negative")
        rate = self.ramp_up_fraction_s if target >= current else self.ramp_down_fraction_s
        change = min(abs(target-current), duration*rate)
        return current + (change if target >= current else -change)


@dataclass(frozen=True, slots=True)
class PumpSpeedCommand:
    command_id: str
    start_s: float
    end_s: float
    target_speed_fraction: float
    mode: Literal["operate", "hold", "stop"] = "operate"

    def __post_init__(self):
        object.__setattr__(self, "command_id", _text(self.command_id, "command_id"))
        start, end = finite(self.start_s, "start_s"), finite(self.end_s, "end_s")
        if start < 0 or end <= start:
            raise ValueError("Pump command interval must have 0 <= start < end")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)
        target = _fraction(self.target_speed_fraction, "target_speed_fraction")
        if not isinstance(self.mode, str) or self.mode not in {"operate", "hold", "stop"}:
            raise ValueError("Pump command mode must be 'operate', 'hold', or 'stop'")
        if self.mode == "stop" and target != 0:
            raise ValueError("A stop command must target zero speed")
        object.__setattr__(self, "target_speed_fraction", target)


@dataclass(frozen=True, slots=True)
class PumpOperatingPoint:
    time_s: float
    receiver_pressure_pa: float
    command: PumpSpeedCommand
    speed_fraction: float
    reduced_flow_fraction: float
    expected_pressure_rise_pa: float
    expected_npsh_required_m: float
    pressure_rise_relative_error: float
    npsh_relative_error: float
    npsh_margin_m: float
    capacity_admissible: bool
    npsh_admissible: bool
    native_result: Any = field(repr=False, compare=False)

    @property
    def accepted(self) -> bool:
        return self.capacity_admissible and self.npsh_admissible


@dataclass(frozen=True, slots=True)
class PumpOperationTrace:
    actuator: PumpSpeedActuator
    pump_map: NormalizedPumpMap
    commands: tuple[PumpSpeedCommand, ...]
    points: tuple[PumpOperatingPoint, ...]
    left_state: Any = field(repr=False, compare=False)
    right_state: Any = field(repr=False, compare=False)
    owner: Any = field(repr=False, compare=False)
    input_sha256: str
    output_sha256: str
    _owner_signature: tuple[Any, ...] = field(repr=False, compare=False)
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_PUMP_TRACE_ISSUERS:
            raise TypeError("Create pump operation traces through FiniteSpeedPump.run")
        _PENDING_PUMP_TRACE_ISSUERS.remove(self._issuer_token)

    def require_current(self):
        if self.owner._signature() != self._owner_signature:
            raise ValueError("Pump, property, map or actuator owner changed after issue")
        expected_input = recorded_content_sha256(
            (self.actuator, self.pump_map, self.commands, self.left_state, self.right_state))
        expected_output = recorded_content_sha256(tuple(
            (p.time_s, p.receiver_pressure_pa, p.command.command_id, p.speed_fraction, p.reduced_flow_fraction,
             p.expected_pressure_rise_pa, p.expected_npsh_required_m,
             p.pressure_rise_relative_error, p.npsh_relative_error, p.npsh_margin_m,
             p.capacity_admissible, p.npsh_admissible, p.native_result)
            for p in self.points))
        if expected_input != self.input_sha256 or expected_output != self.output_sha256:
            raise ValueError("Pump-operation trace content changed after issue")
        return self


def _issue_pump_operation_trace(**values):
    token = object()
    _PENDING_PUMP_TRACE_ISSUERS.add(token)
    try:
        return PumpOperationTrace(**values, _issuer_token=token)
    except Exception:
        _PENDING_PUMP_TRACE_ISSUERS.discard(token)
        raise


class FiniteSpeedPump:
    """Apply finite speed commands to one original native mapped pump."""

    def __init__(self, native_pump, actuator: PumpSpeedActuator,
                 pump_map: NormalizedPumpMap):
        for name in ("evaluate", "properties", "speed_rpm", "reference_speed_rpm"):
            if not hasattr(native_pump, name):
                raise TypeError("FiniteSpeedPump requires the original native mapped-pump API")
        if not callable(native_pump.evaluate):
            raise TypeError("Native pump evaluate must be callable")
        if pump_map.evidence.fluid_basis != getattr(native_pump.properties, "fluid", None):
            raise ValueError("Pump-map fluid basis differs from the native property owner")
        reference = finite(native_pump.reference_speed_rpm, "native reference_speed_rpm", positive=True)
        if abs(reference-pump_map.reference_speed_rpm) > max(1e-9, 1e-12*reference):
            raise ValueError("Native and evidence-map reference speeds differ")
        self.native, self.actuator, self.pump_map = native_pump, actuator, pump_map

    def _signature(self):
        return (
            id(self.native), id(self.native.properties), id(getattr(self.native.evaluate, "__func__", self.native.evaluate)),
            finite(self.native.reference_speed_rpm, "reference_speed_rpm"),
            recorded_content_sha256(self.actuator), recorded_content_sha256(self.pump_map),
        )

    @staticmethod
    def _schedule(commands: Sequence[PumpSpeedCommand]):
        commands = tuple(commands)
        if not commands or any(not isinstance(c, PumpSpeedCommand) for c in commands):
            raise ValueError("At least one explicit PumpSpeedCommand is required")
        if len({c.command_id for c in commands}) != len(commands):
            raise ValueError("Pump command identities must be unique")
        for previous, current in zip(commands, commands[1:]):
            if previous.end_s != current.start_s:
                raise ValueError("Pump command intervals must be contiguous")
        return commands

    @staticmethod
    def _command_at(commands, time_s):
        for command in commands:
            if command.start_s <= time_s < command.end_s:
                return command
        if time_s == commands[-1].end_s:
            return commands[-1]
        raise ValueError("Every pump sample must lie inside the command support")

    def run(self, left_state, right_state, commands: Sequence[PumpSpeedCommand],
            sample_times_s: Sequence[float], *, clock_id: str,
            require_qualified_map: bool = False, require_accepted: bool = True):
        if _text(clock_id, "clock_id") != self.actuator.clock_id:
            raise ValueError("Run clock differs from the pump actuator clock")
        if require_qualified_map and not self.pump_map.evidence.qualified_for_prediction:
            raise ValueError("This pump map is not qualified for predictive use")
        commands = self._schedule(commands)
        times = tuple(finite(t, "sample_time_s") for t in sample_times_s)
        if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("Pump samples must be finite and strictly increasing")
        if times[0] != commands[0].start_s or times[-1] != commands[-1].end_s:
            raise ValueError("Samples must cover the exact pump-command support")
        boundaries = {c.start_s for c in commands} | {commands[-1].end_s}
        if not boundaries.issubset(times):
            raise ValueError("Every pump-command boundary must be sampled exactly")
        signature = self._signature()
        speed = self.actuator.initial_speed_fraction
        previous_time = times[0]
        points = []
        for sample_index, time_s in enumerate(times):
            command = self._command_at(commands, time_s)
            if sample_index:
                # A command beginning at ``time_s`` acts after that instant.
                # Advance the elapsed interval using its left-edge command so a
                # new target cannot alter speed before its declared start time.
                interval_command = self._command_at(commands, previous_time)
                speed = self.actuator.advance(
                    speed, interval_command.target_speed_fraction,
                    time_s-previous_time,
                )
            previous_time = time_s
            if speed == 0:
                raise ValueError("Zero speed needs a separately declared stopped/bypass component")
            self.native.speed_rpm = self.pump_map.reference_speed_rpm * speed
            result = self.native.evaluate(left_state, right_state)
            rate = finite(result.mass_flow_kg_s, "native mass_flow_kg_s")
            receiver_pressure = finite(right_state.pressure_Pa, "native receiver absolute pressure", positive=True)
            rise = finite(receiver_pressure-left_state.pressure_Pa,
                          "native pressure rise")
            npsh_required = finite(result.npsh_required_m, "native npsh_required_m")
            reduced, expected_rise, expected_npsh, head_error, npsh_error = self.pump_map.admit(
                speed_fraction=speed, mass_flow_kg_s=rate, pressure_rise_pa=rise,
                npsh_required_m=npsh_required)
            margin = finite(result.npsh_available_m-result.npsh_required_m, "native npsh margin")
            tolerance = self.pump_map.relative_admission_tolerance
            capacity_ok = (head_error <= tolerance and npsh_error <= tolerance
                           and bool(getattr(result, "operating_point_physical_valid", False)))
            point = PumpOperatingPoint(time_s, receiver_pressure, command, speed, reduced, expected_rise,
                expected_npsh, head_error, npsh_error, margin, capacity_ok, margin >= 0, result)
            if require_accepted and not point.accepted:
                raise ValueError("Native pump point is outside the admitted capacity/NPSH envelope")
            points.append(point)
        trace = _issue_pump_operation_trace(
            actuator=self.actuator, pump_map=self.pump_map, commands=commands,
            points=tuple(points), left_state=left_state, right_state=right_state,
            owner=self,
            input_sha256=recorded_content_sha256(
                (self.actuator, self.pump_map, commands, left_state, right_state)),
            output_sha256=recorded_content_sha256(tuple(
                (p.time_s, p.receiver_pressure_pa, p.command.command_id, p.speed_fraction, p.reduced_flow_fraction,
                 p.expected_pressure_rise_pa, p.expected_npsh_required_m,
                 p.pressure_rise_relative_error, p.npsh_relative_error, p.npsh_margin_m,
                 p.capacity_admissible, p.npsh_admissible, p.native_result)
                for p in points)),
            _owner_signature=signature,
        )
        trace.require_current()
        return trace
