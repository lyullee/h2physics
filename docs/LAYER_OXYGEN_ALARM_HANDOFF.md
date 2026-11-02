# Upper-layer oxygen-deficit sensor and alarm handoff

`evaluate_layer_oxygen_deficit_alarm()` feeds an existing first-order
concentration sensor and sampled concentration alarm from an existing
`LayerOxygenProjection`. It evaluates only one explicit upper-layer signal.
It does not turn that signal into a room average, exposure-duration result,
safety certification or human-response prediction.

## Signal definition and provenance

The projection supplies the upper-layer oxygen mole fraction, using the
caller-declared fixed dry-air carrier described in
[`LAYER_OXYGEN_PROJECTION.md`](LAYER_OXYGEN_PROJECTION.md). Mole fraction is
amount of constituent divided by total amount of mixture; see the
[IUPAC Gold Book definition](https://goldbook.iupac.org/terms/view/A00296).
This handoff defines a nonnegative deficit signal as

\[
d_{O_2}(t)=\max\left(x_{O_2,ref}-x_{O_2,layer}(t),\,0\right).
\]

The reference value and all applicability evidence are caller inputs. The
positive-part operation is only a signal convention that prevents a negative
deficit from entering the existing concentration sensor. It is not a toxicity
law or a regulatory threshold.

The adapter reuses `evaluate_first_order_concentration_sensor()` and
`evaluate_concentration_alarm_from_sensor()` from
[`GAS_CONCENTRATION_ALARM.md`](GAS_CONCENTRATION_ALARM.md). It adds no sensor
response equation, alarm latch rule, threshold selection or detector reliability
model.

## Required caller declarations

The caller provides the oxygen reference mole fraction and evidence ID; the
reference and projection clock/location IDs; evidence IDs mapping the reference
to the projection clock and location; source evidence and origin; existing
sensor/alarm configuration objects; initial sensor indication; and operating
mode and episode IDs. The sensor clock/location must equal the declared
projection clock/location. The alarm must match the sensor, basis, origin, mode
and episode.

Clock and location mapping IDs document the caller's applicability assertion.
No timestamp conversion, location interpolation or sensor-placement model is
performed. The exact `LayerOxygenProjection` object and its timestamp tuple are
retained. `require_current()` rechecks the projection, every deficit sample,
sensor output, alarm trace, and all trip evidence against those retained inputs.

## Python use

Build the sensor and alarm using the same exact basis label:

```python
from h2physics.adapters.gas_detection import (
    ConcentrationAlarmConfig,
    FirstOrderConcentrationSensorConfig,
)
from h2physics.adapters.layer_oxygen_alarm_handoff import (
    evaluate_layer_oxygen_deficit_alarm,
    layer_oxygen_deficit_basis,
)
from h2physics.core import Origin

origin = Origin.PREDICTED
reference_evidence_id = "site-reference-measurement-v1"
basis = layer_oxygen_deficit_basis(reference_evidence_id)
sensor = FirstOrderConcentrationSensorConfig(
    sensor_id="upper-layer-o2-detector",
    location_id="upper-layer-location",
    clock_id="scenario-clock",
    concentration_basis=basis,
    concentration_unit="mole_fraction",
    response_time_constant_s=2.0,
    maximum_input_sample_gap_s=1.0,
    sensor_evidence_id="sensor-identity-v1",
    response_parameter_evidence_id="response-calibration-v1",
    model_evidence_id="first-order-lag-premise-v1",
)
alarm = ConcentrationAlarmConfig(
    detector_id=sensor.sensor_id,
    location_id=sensor.location_id,
    clock_id=sensor.clock_id,
    operating_mode_id="normal-operation",
    episode_id="release-episode-17",
    concentration_basis=basis,
    concentration_unit="mole_fraction",
    trip_threshold=0.02,
    reset_threshold=0.01,
    trip_confirmation_samples=2,
    reset_confirmation_samples=2,
    maximum_sample_gap_s=1.0,
    sensor_evidence_id=sensor.sensor_evidence_id,
    threshold_evidence_id="approved-threshold-record-v1",
    logic_evidence_id="alarm-logic-record-v1",
    origin=origin,
)

handoff = evaluate_layer_oxygen_deficit_alarm(
    projection,
    reference_oxygen_mole_fraction=0.2095,
    reference_evidence_id=reference_evidence_id,
    reference_clock_id="reference-clock",
    reference_location_id="reference-location",
    projection_clock_id=sensor.clock_id,
    projection_location_id=sensor.location_id,
    clock_mapping_evidence_id="reference-clock-map-v1",
    location_mapping_evidence_id="reference-location-map-v1",
    source_evidence_id="upper-layer-source-v1",
    origin=origin,
    sensor_config=sensor,
    alarm_config=alarm,
    initial_sensor_indication=0.0,
    operating_mode_id=alarm.operating_mode_id,
    episode_id=alarm.episode_id,
)
handoff.require_current()
```

The scalar reference is declared constant over the evaluated projection window;
the supplied mapping evidence must support that applicability. This API does not
translate different time bases. If the source and detector clocks differ, the
caller must produce an explicitly mapped projection and provide evidence for
that mapping before using this handoff.

## Scope and validation status

The deferred contract
`two-vent-layer-oxygen-deficit-sensor-alarm-handoff` uses synthetic composition,
reference, sensor parameters and alarm thresholds. It checks clock/location and
signal/evidence bindings; it is not a field-sensor comparison. The model still
inherits the layer model's still-air, fixed-temperature, single upper-layer and
one-way two-vent limits. No room-average oxygen value or human-response result
is emitted.
