"""Prescribed sampled-alarm override for the existing finite-stroke valve API.

This module schedules a caller-declared isolation command. It does not model
detector reliability, command transmission, valve motion, flow, or safety credit.
"""

from dataclasses import dataclass, field

from ..core import finite
from .gas_detection import ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence
from .lh2dt_valve_actuator import ValveCommand


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _command_values(commands):
    return tuple((item.start_s, item.end_s, item.target_stroke_fraction,
                  item.command_id, item.mode) for item in commands)


def _compose(alarm_time_s, latency_s, end_s, source_commands, command_prefix):
    if (not source_commands
            or any(type(command) is not ValveCommand for command in source_commands)):
        raise TypeError("Supply a nonempty schedule of typed ValveCommand intervals")
    if len({command.command_id for command in source_commands}) != len(source_commands):
        raise ValueError("Caller valve command identities must be unique")
    for previous, current in zip(source_commands, source_commands[1:]):
        if previous.end_s != current.start_s:
            raise ValueError("Caller valve commands must be ordered and contiguous")
    action_time = alarm_time_s + latency_s
    if action_time >= end_s:
        raise ValueError("Isolation action must begin before the explicit command horizon")
    if action_time < source_commands[0].start_s or end_s > source_commands[-1].end_s:
        raise ValueError("Alarm action and horizon must lie inside the caller command support")

    result = []
    for index, command in enumerate(source_commands):
        if command.start_s >= action_time:
            break
        if command.end_s <= action_time:
            result.append(command)
            continue
        result.append(ValveCommand(
            command.start_s, action_time, command.target_stroke_fraction,
            f"{command_prefix}:pre-trip:{index}", command.mode,
        ))
        break
    result.append(ValveCommand(
        action_time, end_s, 0.0, f"{command_prefix}:isolate", "isolate",
    ))
    if len({command.command_id for command in result}) != len(result):
        raise ValueError("Generated isolation command identity collides with retained plan")
    return tuple(result)


@dataclass(frozen=True, slots=True)
class AlarmValveIsolationSchedule:
    """Caller-owned valve-command schedule retaining its original alarm and plan."""

    alarm_evidence: ConcentrationAlarmEvidence | ConcentrationAlarmVotingEvidence
    source_commands: tuple[ValveCommand, ...]
    commands: tuple[ValveCommand, ...]
    command_clock_id: str
    latency_s: float
    isolation_end_s: float
    command_prefix: str
    action_evidence_id: str
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.alarm_evidence) not in (
            ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence,
        ):
            raise TypeError("Retain source-bound concentration alarm evidence")
        self.alarm_evidence.require_current()
        source = tuple(self.source_commands)
        commands = tuple(self.commands)
        if (not source or any(type(item) is not ValveCommand for item in source)
                or any(type(item) is not ValveCommand for item in commands)):
            raise TypeError("Retain the caller's typed finite-stroke valve commands")
        if len({item.command_id for item in source}) != len(source):
            raise ValueError("Caller valve command identities must be unique")
        for previous, current in zip(source, source[1:]):
            if previous.end_s != current.start_s:
                raise ValueError("Caller valve commands must be ordered and contiguous")
        clock = _text(self.command_clock_id, "command clock")
        if clock != self.alarm_evidence.clock_id:
            raise ValueError("Alarm and valve command schedule must use the same declared clock")
        latency = finite(self.latency_s, "decision-to-isolation latency")
        if latency < 0.:
            raise ValueError("Isolation cannot precede the confirmed sampled alarm")
        end = finite(self.isolation_end_s, "isolation_end_s")
        prefix = _text(self.command_prefix, "command prefix")
        evidence = _text(self.action_evidence_id, "isolation action evidence")
        expected = _compose(
            self.alarm_evidence.time_s, latency, end, source, prefix,
        )
        if _command_values(commands) != _command_values(expected):
            raise ValueError("Output commands do not match the declared alarm override")
        object.__setattr__(self, "source_commands", source)
        object.__setattr__(self, "commands", commands)
        object.__setattr__(self, "command_clock_id", clock)
        object.__setattr__(self, "latency_s", latency)
        object.__setattr__(self, "isolation_end_s", end)
        object.__setattr__(self, "command_prefix", prefix)
        object.__setattr__(self, "action_evidence_id", evidence)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (id(self.alarm_evidence), _command_values(self.source_commands),
                _command_values(self.commands), self.command_clock_id, self.latency_s,
                self.isolation_end_s, self.command_prefix, self.action_evidence_id)

    @property
    def action_time_s(self):
        return self.alarm_evidence.time_s + self.latency_s

    def require_current(self):
        self.alarm_evidence.require_current()
        expected = _compose(
            self.alarm_evidence.time_s, self.latency_s, self.isolation_end_s,
            self.source_commands, self.command_prefix,
        )
        if (self.command_clock_id != self.alarm_evidence.clock_id
                or _command_values(expected) != _command_values(self.commands)
                or self._content() != self._seal):
            raise ValueError("Alarm/clock/action identity or valve command schedule changed")
        return self


def schedule_alarm_valve_isolation(
    alarm_evidence,
    source_commands,
    *,
    command_clock_id: str,
    latency_s: float,
    isolation_end_s: float,
    command_prefix: str,
    action_evidence_id: str,
) -> AlarmValveIsolationSchedule:
    """Override a caller valve schedule with isolation after one confirmed alarm.

    The action starts at ``alarm_evidence.time_s + latency_s`` and persists to
    the caller-selected ``isolation_end_s``. Existing commands are retained up
    to the action instant; if the instant divides a command, that interval is
    split. The caller remains responsible for clock applicability, latency,
    valve dynamics, hydraulics, and interpreting any resulting flow.
    """
    if type(alarm_evidence) not in (
        ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence,
    ):
        raise TypeError("Supply a confirmed typed concentration alarm event")
    alarm_evidence.require_current()
    source = tuple(source_commands)
    latency = finite(latency_s, "decision-to-isolation latency")
    end = finite(isolation_end_s, "isolation_end_s")
    prefix = _text(command_prefix, "command prefix")
    output = _compose(alarm_evidence.time_s, latency, end, source, prefix)
    return AlarmValveIsolationSchedule(
        alarm_evidence, source, output, command_clock_id, latency, end, prefix,
        action_evidence_id,
    ).require_current()


__all__ = ["AlarmValveIsolationSchedule", "schedule_alarm_valve_isolation"]
