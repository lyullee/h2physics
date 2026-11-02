# Concentration alarm to valve isolation command

`h2physics.adapters.schedule_alarm_valve_isolation()` composes an already
confirmed `ConcentrationAlarmEvidence` or `ConcentrationAlarmVotingEvidence`
with the existing `ValveCommand` intervals. It splits a caller command at the
declared action time (`alarm time + latency`), retains the earlier commands,
then emits an `isolate` command with zero target stroke through a caller-selected
horizon. The alarm clock must match the explicit command clock, and the alarm,
command support and post-trip horizon must align.

```python
from h2physics.adapters.alarm_valve_isolation import schedule_alarm_valve_isolation

override = schedule_alarm_valve_isolation(
    alarm_evidence,
    normal_valve_commands,
    command_clock_id="facility-clock-v3",
    latency_s=0.35,
    isolation_end_s=12.0,
    command_prefix="h2-trip-17",
    action_evidence_id="reviewed-isolation-mapping-v2",
)
override.require_current()
valve_trace = finite_stroke_valve.run(
    upstream_state, downstream_state, override.commands,
    sample_times_s=sample_grid_including_command_boundaries,
    clock_id=override.command_clock_id,
)
```

The schedule is an explicit caller-prescribed override, not an autonomous
interlock. It does not establish detector reliability, alarm setpoint
appropriateness, communication or logic-system delay, valve closure dynamics,
leak-tight isolation, process-flow response, risk reduction, or safety integrity
level. `FiniteStrokeValve` remains the owner of actuator stroke and shared-valve
flow evaluation. The caller must supply the pre-trip command schedule, clock
applicability, action evidence, latency and end time. The output ends at that
declared horizon and is suitable for composition with the existing finite-stroke
actuator when that actuator supports the same command mode.

The deferred Hangang case
`concentration-alarm-finite-stroke-valve-isolation-schedule` checks synthetic
time splitting, clock agreement, horizon guards and the zero-stroke isolate
command. It is an API contract only and does not verify actuator or process
physics.
