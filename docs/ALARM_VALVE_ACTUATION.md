# Alarm linked finite stroke actuation

`h2physics.adapters.alarm_valve_actuation` connects two existing model stages:
confirmed, source bound concentration alarm evidence and the finite stroke valve
actuator. The adapter creates the explicit isolation schedule through
`schedule_alarm_valve_isolation`, then passes that exact schedule and the caller's
sample grid to `FiniteStrokeValve.run`.

```python
result = execute_alarm_valve_isolation(
    alarm_evidence, valve, left_state, right_state, source_commands, sample_times_s,
    clock_id="plant-clock",
    mapped_sensor_location_ids=("compressor-room",),
    physical_valve_id="XV-101",
    actuator_id=valve.actuator.actuator_id,
    location_mapping_evidence_id="approved-layout-revision-7",
    latency_s=0.25,
    isolation_end_s=12.0,
    command_prefix="trip-episode-4",
    action_evidence_id="operator-response-plan-2",
)
```

## Required applicability inputs

The declared clock must match the alarm and actuator clocks exactly. The mapped
sensor locations must cover the alarm evidence locations exactly; the caller
provides the physical valve identifier and a stable evidence identifier for its
location mapping. The sample grid is caller controlled, must span the whole
schedule, and must contain every generated command boundary. No hidden resampling
or clock conversion occurs.

## Output and freshness

`AlarmValveActuation` retains the exact alarm object, generated command schedule,
finite stroke valve, and resulting `ActuatedValveTrace`. The trace contains the
existing valve model's actuator and flow calculation outputs. Call
`result.require_current()` before consuming it downstream; this also checks that
the alarm, command, actuator, mapping, and issued trace identities remain bound.

The isolation command is a prescribed input to the actuator model. This adapter
does not estimate detector reliability, infer a sensor to valve placement, model
signal transmission, grant detector credit, or establish a safety instrumented
function or safety performance. Valve motion and any flow fields come solely from
the supplied `FiniteStrokeValve` and its declared data. The included validation
case uses synthetic inputs and authored, unqualified actuator rates.

The validation fixture constructs the repository's `Lh2dtSharedValve` bridge
around `HomogeneousIsentropicNozzle` and `CoolPropProperties`; it does not import
the external `lh2dt` package or call the example finite-transfer workflow. Small
immutable records adapt property-state fields and carry the computed nozzle
result fields across the bridge. They contain no flow equations or replacement
physics. CoolProp remains an optional provider dependency (`h2physics[thermo]`)
and is not installed by the case.
