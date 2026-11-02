"""Execute a confirmed concentration-alarm isolation schedule on the shared valve.

The adapter composes existing alarm evidence, command scheduling and finite-stroke
valve dynamics. It adds no detector, interlock, valve-flow or safety-credit model.
"""

from dataclasses import dataclass, field

from ..core import finite
from .alarm_valve_isolation import (
    AlarmValveIsolationSchedule,
    schedule_alarm_valve_isolation,
)
from .gas_detection import (
    ConcentrationAlarmEvidence,
    ConcentrationAlarmVotingEvidence,
)
from .lh2dt_valve_actuator import (
    ActuatedValveTrace,
    FiniteStrokeValve,
)

_PENDING_BINDINGS: set[object] = set()


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Declare {name}")
    return value.strip()


def _alarm_locations(evidence) -> tuple[str, ...]:
    if type(evidence) is ConcentrationAlarmEvidence:
        traces = (evidence.trace,)
    elif type(evidence) is ConcentrationAlarmVotingEvidence:
        traces = evidence.trace.traces
    else:
        raise TypeError("Supply confirmed single-detector or voted alarm evidence")
    locations = tuple(sorted({trace.config.location_id for trace in traces}))
    if not locations:
        raise ValueError("Alarm evidence must retain at least one sensor location")
    return locations


def _command_content(commands):
    return tuple((command.start_s, command.end_s, command.target_stroke_fraction,
                  command.command_id, command.mode) for command in commands)


@dataclass(frozen=True, slots=True)
class AlarmValveActuation:
    """Issued physical valve trace bound to its original confirmed alarm."""

    alarm_evidence: ConcentrationAlarmEvidence | ConcentrationAlarmVotingEvidence
    command_schedule: AlarmValveIsolationSchedule
    valve: FiniteStrokeValve = field(repr=False, compare=False)
    trace: ActuatedValveTrace = field(repr=False, compare=False)
    sample_times_s: tuple[float, ...]
    clock_id: str
    mapped_sensor_location_ids: tuple[str, ...]
    physical_valve_id: str
    actuator_id: str
    location_mapping_evidence_id: str
    _issuer_token: object = field(repr=False, compare=False)
    _seal: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_BINDINGS:
            raise TypeError("Create alarm-actuator bindings through execute_alarm_valve_isolation")
        _PENDING_BINDINGS.remove(self._issuer_token)
        if type(self.alarm_evidence) not in (
            ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence,
        ):
            raise TypeError("Retain the original confirmed alarm evidence")
        if type(self.command_schedule) is not AlarmValveIsolationSchedule:
            raise TypeError("Retain the generated alarm isolation command schedule")
        if type(self.valve) is not FiniteStrokeValve or type(self.trace) is not ActuatedValveTrace:
            raise TypeError("Retain the original finite-stroke valve and its issued trace")
        self.alarm_evidence.require_current()
        self.command_schedule.require_current()
        self.trace.require_current()
        clock = _text(self.clock_id, "actuator clock")
        raw_mapped = tuple(_text(item, "mapped sensor location")
                           for item in self.mapped_sensor_location_ids)
        if len(set(raw_mapped)) != len(raw_mapped):
            raise ValueError("Mapped sensor location identities must be unique")
        mapped = tuple(sorted(raw_mapped))
        expected_locations = _alarm_locations(self.alarm_evidence)
        if mapped != expected_locations:
            raise ValueError("Location applicability must identify every alarm sensor location exactly")
        if clock != self.alarm_evidence.clock_id or clock != self.valve.actuator.clock_id:
            raise ValueError("Alarm, isolation schedule and finite-stroke actuator must share one clock")
        if self.command_schedule.alarm_evidence is not self.alarm_evidence:
            raise ValueError("Command schedule must retain the exact confirmed alarm object")
        if self.command_schedule.command_clock_id != clock:
            raise ValueError("Isolation schedule uses a different clock")
        if self.trace.owner is not self.valve or self.trace.actuator is not self.valve.actuator:
            raise ValueError("Actuated trace must come from the supplied finite-stroke valve")
        if self.trace.area_map is not self.valve.area_map:
            raise ValueError("Actuated trace must retain the supplied valve area map")
        if (len(self.trace.commands) != len(self.command_schedule.commands)
                or any(left is not right for left, right in
                       zip(self.trace.commands, self.command_schedule.commands))):
            raise ValueError("Actuated trace must execute the exact issued isolation commands")
        times = tuple(finite(item, "sample time") for item in self.sample_times_s)
        if (times != tuple(point.time_s for point in self.trace.points)
                or len(times) < 2 or any(b <= a for a, b in zip(times, times[1:]))):
            raise ValueError("Retained sample grid must exactly match the increasing valve trace")
        if times[0] != self.command_schedule.commands[0].start_s or \
                times[-1] != self.command_schedule.isolation_end_s:
            raise ValueError("Valve trace must span the full pre-trip and isolation schedule")
        physical_valve = _text(self.physical_valve_id, "physical valve id")
        declared_actuator = _text(self.actuator_id, "actuator id")
        if declared_actuator != self.valve.actuator.actuator_id:
            raise ValueError("Declared actuator identity differs from the executed actuator")
        mapping_evidence = _text(self.location_mapping_evidence_id, "location mapping evidence")
        object.__setattr__(self, "clock_id", clock)
        object.__setattr__(self, "sample_times_s", times)
        object.__setattr__(self, "mapped_sensor_location_ids", mapped)
        object.__setattr__(self, "physical_valve_id", physical_valve)
        object.__setattr__(self, "actuator_id", self.valve.actuator.actuator_id)
        object.__setattr__(self, "location_mapping_evidence_id", mapping_evidence)
        object.__setattr__(self, "_seal", self._content())

    def _content(self):
        return (
            id(self.alarm_evidence), id(self.command_schedule), id(self.valve), id(self.trace),
            _command_content(self.command_schedule.commands), self.sample_times_s,
            self.clock_id, self.mapped_sensor_location_ids, self.physical_valve_id,
            self.actuator_id, self.location_mapping_evidence_id,
        )

    def require_current(self):
        self.alarm_evidence.require_current()
        self.command_schedule.require_current()
        self.trace.require_current()
        if (_alarm_locations(self.alarm_evidence) != self.mapped_sensor_location_ids
                or self.clock_id != self.alarm_evidence.clock_id
                or self.clock_id != self.valve.actuator.clock_id
                or self.trace.owner is not self.valve
                or self.trace.actuator is not self.valve.actuator
                or self.trace.area_map is not self.valve.area_map
                or self.actuator_id != self.valve.actuator.actuator_id
                or self._content() != self._seal):
            raise ValueError("Alarm-to-actuator identity, applicability or issued trace changed")
        return self


def execute_alarm_valve_isolation(
    alarm_evidence,
    valve: FiniteStrokeValve,
    left_state,
    right_state,
    source_commands,
    sample_times_s,
    *,
    clock_id: str,
    mapped_sensor_location_ids,
    physical_valve_id: str,
    actuator_id: str,
    location_mapping_evidence_id: str,
    latency_s: float,
    isolation_end_s: float,
    command_prefix: str,
    action_evidence_id: str,
) -> AlarmValveActuation:
    """Schedule and run one explicit isolation response on the existing valve.

    The alarm time plus caller-specified latency starts a zero-stroke isolate
    command. Every command boundary is evaluated by ``FiniteStrokeValve`` on the
    caller grid. The sensor-to-valve location mapping and physical valve identity
    are explicit evidence inputs; no safety credit or automatic interlock is
    inferred.
    """
    if type(alarm_evidence) not in (
        ConcentrationAlarmEvidence, ConcentrationAlarmVotingEvidence,
    ):
        raise TypeError("Supply confirmed source-bound concentration alarm evidence")
    if type(valve) is not FiniteStrokeValve:
        raise TypeError("Supply the existing FiniteStrokeValve model")
    alarm_evidence.require_current()
    clock = _text(clock_id, "actuator clock")
    actuator = _text(actuator_id, "actuator id")
    physical_valve = _text(physical_valve_id, "physical valve id")
    locations = tuple(mapped_sensor_location_ids)
    mapped_locations = tuple(_text(item, "mapped sensor location") for item in locations)
    if (len(set(mapped_locations)) != len(mapped_locations)
            or tuple(sorted(mapped_locations)) != _alarm_locations(alarm_evidence)):
        raise ValueError("Explicit location mapping must cover the original alarm sensor locations")
    if actuator != valve.actuator.actuator_id:
        raise ValueError("Declared actuator identity differs from the supplied valve actuator")
    schedule = schedule_alarm_valve_isolation(
        alarm_evidence, source_commands, command_clock_id=clock,
        latency_s=latency_s, isolation_end_s=isolation_end_s,
        command_prefix=command_prefix, action_evidence_id=action_evidence_id,
    )
    times = tuple(finite(item, "sample time") for item in sample_times_s)
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Supply an increasing actuator sample grid")
    boundaries = {command.start_s for command in schedule.commands}
    boundaries.add(schedule.commands[-1].end_s)
    if (times[0] != schedule.commands[0].start_s
            or times[-1] != schedule.isolation_end_s
            or not boundaries.issubset(times)):
        raise ValueError("Sample grid must include the full schedule and every generated command boundary")
    trace = valve.run(
        left_state, right_state, schedule.commands, times, clock_id=clock,
    )
    token = object()
    _PENDING_BINDINGS.add(token)
    try:
        return AlarmValveActuation(
            alarm_evidence, schedule, valve, trace, times, clock,
            locations, physical_valve, actuator, location_mapping_evidence_id, token,
        ).require_current()
    except Exception:
        _PENDING_BINDINGS.discard(token)
        raise


__all__ = ["AlarmValveActuation", "execute_alarm_valve_isolation"]
