"""Synthetic contract for an explicit alarm-to-valve isolation command bridge."""

from h2physics.adapters.alarm_valve_isolation import schedule_alarm_valve_isolation
from h2physics.adapters.gas_detection import (
    ConcentrationAlarmConfig,
    ConcentrationAlarmEvidence,
    evaluate_concentration_alarm,
)
from h2physics.adapters.lh2dt_valve_actuator import ValveCommand
from h2physics.cluster_validation import ValidationCase, ValidationOutcome
from h2physics.core import Origin


def cases():
    return (ValidationCase(
        identifier="concentration-alarm-finite-stroke-valve-isolation-schedule",
        profile="facility-protection",
        entrypoint=__name__ + ":validate_alarm_valve_isolation",
        invariants=(
            "confirmed-source-bound-alarm-and-valve-plan-share-an-explicit-clock",
            "decision-latency-splits-the-existing-command-interval-exactly",
            "caller-selected-horizon-is-covered-by-an-isolate-mode-zero-stroke-command",
            "invalid-clock-latency-or-horizon-is-rejected",
            "command scheduling adds no detector-credit-actuator-flow-or-SIS-physics",
        ),
    ),)


def validate_alarm_valve_isolation(*, work_directory, **parameters):
    del work_directory, parameters
    config = ConcentrationAlarmConfig(
        "synthetic-h2-detector", "compressor-room", "alarm-valve-clock",
        "normal-operation", "episode-7", "dry mole fraction", "mol/mol",
        0.01, 0.005, 2, 2, 0.5, "synthetic-sensor", "synthetic-trip-limit",
        "synthetic-alarm-logic", Origin.SYNTHETIC,
    )
    trace = evaluate_concentration_alarm(
        config, time_s=(0., 0.5, 1.0, 1.5),
        concentration=(0.001, 0.012, 0.014, 0.008),
    )
    trip = next(item for item in trace.transitions if item.alarm_active)
    alarm = ConcentrationAlarmEvidence.bind(trace, trip)
    source = (
        ValveCommand(0., 1., 0.35, "normal-0"),
        ValveCommand(1., 2., 0.55, "normal-1"),
        ValveCommand(2., 4., 0.7, "normal-2"),
    )
    result = schedule_alarm_valve_isolation(
        alarm, source, command_clock_id="alarm-valve-clock", latency_s=0.2,
        isolation_end_s=3.0, command_prefix="synthetic-action-1",
        action_evidence_id="synthetic-isolation-mapping",
    )
    if (result.action_time_s != 1.2 or len(result.commands) != 3
            or result.commands[0] is not source[0]
            or result.commands[1].start_s != 1.
            or result.commands[1].end_s != 1.2
            or result.commands[1].target_stroke_fraction != 0.55
            or result.commands[2].start_s != 1.2
            or result.commands[2].end_s != 3.0
            or result.commands[2].target_stroke_fraction != 0.0
            or result.commands[2].mode != "isolate"):
        raise AssertionError("Alarm command did not split and override the schedule at its declared time")
    result.require_current()
    rejected = 0
    for kwargs in (
        {"command_clock_id": "different-clock"},
        {"latency_s": -0.1},
        {"isolation_end_s": 5.0},
    ):
        arguments = {
            "command_clock_id": "alarm-valve-clock", "latency_s": 0.2,
            "isolation_end_s": 3.0, "command_prefix": "rejected-action",
            "action_evidence_id": "synthetic-isolation-mapping",
        }
        arguments.update(kwargs)
        try:
            schedule_alarm_valve_isolation(alarm, source, **arguments)
        except ValueError:
            rejected += 1
    if rejected != 3:
        raise AssertionError("Clock, latency, and command-horizon errors must be rejected")
    return ValidationOutcome(True, {
        "confirmed_alarm_time_s": alarm.time_s,
        "action_time_s": result.action_time_s,
        "isolation_end_s": result.isolation_end_s,
        "generated_command_count": len(result.commands),
        "rejected_invalid_requests": rejected,
        "action_evidence_id": result.action_evidence_id,
    }, (
        "Synthetic command-schedule composition only; no detector credit, actuator motion, flow, or SIS performance",
    ))
