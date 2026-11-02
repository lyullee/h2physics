# Buoyant hydrogen layer to detector alarm boundary

## Catalog entry

**Facility protection integration — upper-layer hydrogen concentration to a
sampled detector alarm.** It runs the existing reduced two-vent H2 accumulation
model, treats its upper-zone mole fraction as the source signal for the existing
first-order sensor, then applies the existing hysteretic alarm engine. It fills
the missing connection from a physical room-layer state to direct hydrogen
detector logic. The separate oxygen-deficit handoff represents oxygen sensing,
and the preferred-dispersion handoff represents an externally exported plume.

```python
handoff = evaluate_buoyant_layer_h2_alarm(
    layer_config,
    hydrogen_mass_flow_kg_s=1.0e-5,
    duration_s=60.0,
    maximum_step_s=0.25,
    clock_id="scenario-clock-1",
    layer_location_id="compressor-room-upper-layer",
    source_evidence_id="release-case-17",
    zone_mapping_evidence_id="detector-to-upper-layer-applicability-2",
    sensor_config=sensor_config,
    alarm_config=alarm_config,
    initial_sensor_indication=0.0,
    operating_mode_id="normal-operation",
    episode_id="episode-17",
)
handoff.require_current()
```

The sensor and alarm configurations must use basis
`upper-layer-h2-mole-fraction`, units `mol/mol`, and exactly matching location,
clock, detector, mode, episode, and sensor evidence identities. The adapter
preserves the exact room output, sensor trace, alarm trace and confirmed-trip
objects. The layer model itself does not carry a clock label, so the caller
declares that its seconds are on the sensor/alarm clock.

This is an upper-zone screening boundary. The layer model assumes a steady
vertical buoyant source, still air, fixed ambient temperature, a reduced two-zone
representation and two one-way vents. The location mapping evidence must justify
using the upper-layer scalar at the detector. The adapter does not infer sensor
placement, lower-zone or room-average concentration, detector performance,
probability of detection, isolation commands, SIS credit, or facility risk.
Validation is deferred as
`two-vent-hydrogen-layer-concentration-alarm-handoff` and uses synthetic inputs.
