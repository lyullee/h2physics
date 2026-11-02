# Sampled hydrogen concentration alarm logic

**Status: implemented_unverified.** The module contains a caller-parameterized
first-order sensor response and a discrete alarm-decision layer for hydrogen
concentration histories. It does not model detector chemistry, cross-sensitivity,
saturation, noise, communication delay, reliability, siting, alarm setpoint choice,
or facility safety performance. No default threshold or response time is supplied.

## First-order sensor indication

`FirstOrderConcentrationSensorConfig` retains sensor/location/clock identity, the
concentration basis and unit, a positive caller-supplied response time constant,
the maximum input-sample gap, and evidence identifiers for the sensor, parameter,
and model. `evaluate_first_order_concentration_sensor()` requires an explicit
initial indication and source identity. Between adjacent true-concentration
samples it assumes a linear input and evaluates the closed-form first-order
solution for that segment, with numerically stable small/large ratio handling:

`dS/dt = (C(t) - S)/tau`.

For `x = dt/tau`, `e = exp(-x)`, and endpoint inputs `C0`, `C1`, the new indication
is `S1 = e*S0 + w0*C0 + w1*C1`, where `w1 = 1-(1-e)/x` and
`w0 = (1-e)/x-e`. The same input concentration basis and unit are retained; this
model adds no calibration gain, bias, noise, clipping, hold delay, or interpolation
beyond the declared piecewise-linear input. The output keeps the source input,
clock, operating mode, episode and origin; `require_current()` rechecks the
computation and its lineage.

`evaluate_concentration_alarm_from_sensor()` requires exact agreement between the
issued sensor identity, location, clock, mode, episode, origin, basis, unit and
sensor evidence and the alarm configuration. The resulting alarm trace retains the
originating sensor response. Sampled threshold confirmation therefore runs on the
filtered indication; sensor lag changes the decision samples but does not create a
continuous crossing time or an independent reliability claim.

`ConcentrationAlarmConfig` requires a detector/location identity, common clock,
operating mode and episode, concentration basis/unit, caller-supported trip and
reset limits, consecutive-sample confirmation counts, a maximum acceptable sample
gap, and sensor/threshold/logic evidence identities. All concentration values and
limits stay in the one declared basis and unit. The library performs no conversion.

`evaluate_concentration_alarm(config, time_s=..., concentration=...)` applies a
sampled hysteretic latch directly to a caller-provided indication. A trip starts when the configured high threshold is met
for the required consecutive samples; reset requires the configured lower threshold
for its own consecutive count. Values between limits preserve the current latch and
cancel an incomplete transition. Non-finite/negative values, non-increasing clocks,
and gaps above the configured bound are rejected. The transition record retains
both its first qualifying and confirmation samples. The decision occurs at the
confirmation sample; no sub-sample crossing time is interpolated.

The resulting `ConcentrationAlarmEvidence.bind(trace, transition)` accepts only an
original confirmed trip. It retains the concentration trace, sensor and decision
evidence, clock, mode and episode. `ScheduledProtection` accepts this evidence
alongside the existing PCA-derived `AlarmEvidence` and adds the explicitly declared
action latency before scheduling the existing equipment command. The action remains
an offline prescribed replay; it does not establish detector calibration, response
probability, or independent protection credit.

For multiple detectors, `evaluate_concentration_alarm_voting()` combines already
latched traces using an explicit integer `votes_required` (k-of-n) rule at each
sample. Every member must have a unique detector identity and exactly the same sampled
clock, operating mode, and episode. Each detector may retain its own concentration
basis, threshold, hysteresis, and confirmation count. The vote adds no second
confirmation delay. Its transition record retains the active detector identities,
and `ConcentrationAlarmVotingEvidence.bind()` can pass an original rising vote
transition to the same scheduled protection replay. Sensor independence, common-cause
failure, missing/asynchronous samples, reliability, and voting suitability remain
explicit application evidence; the library does not infer them.

To include the first-order response before threshold logic, bind the alarm to the
same sensor identity and pass the issued response object:

```python
from h2physics.adapters import (
    ConcentrationAlarmConfig,
    FirstOrderConcentrationSensorConfig,
    evaluate_concentration_alarm_from_sensor,
    evaluate_first_order_concentration_sensor,
)
from h2physics.core import Origin

sensor = FirstOrderConcentrationSensorConfig(
    sensor_id="detector-A", location_id="room-north", clock_id="clock-1",
    concentration_basis="dry mole fraction", concentration_unit="mol/mol",
    response_time_constant_s=0.8, maximum_input_sample_gap_s=0.5,
    sensor_evidence_id="sensor-calibration-A",
    response_parameter_evidence_id="response-fit-A",
    model_evidence_id="first-order-model-revision",
)
response = evaluate_first_order_concentration_sensor(
    sensor, time_s=[0.0, 0.2, 0.4], true_concentration=[0.0, 0.012, 0.02],
    initial_indication=0.0, source_evidence_id="synthetic-room-history",
    operating_mode_id="normal-operation", episode_id="synthetic-episode",
    origin=Origin.SYNTHETIC,
)
alarm_config = ConcentrationAlarmConfig(
    detector_id=sensor.sensor_id, location_id=sensor.location_id,
    clock_id=sensor.clock_id, operating_mode_id="normal-operation",
    episode_id="synthetic-episode", concentration_basis=sensor.concentration_basis,
    concentration_unit=sensor.concentration_unit, trip_threshold=0.01,
    reset_threshold=0.005, trip_confirmation_samples=1,
    reset_confirmation_samples=1, maximum_sample_gap_s=0.5,
    sensor_evidence_id=sensor.sensor_evidence_id,
    threshold_evidence_id="synthetic-threshold", logic_evidence_id="logic-revision",
    origin=Origin.SYNTHETIC,
)
alarm_trace = evaluate_concentration_alarm_from_sensor(alarm_config, response)
alarm_trace.require_current()
```

The following direct-indication example is useful when a sensor response history
has already been produced and qualified by an external model:

```python
from h2physics.adapters import (
    ConcentrationAlarmConfig,
    ConcentrationAlarmEvidence,
    ConcentrationAlarmVotingEvidence,
    evaluate_concentration_alarm,
    evaluate_concentration_alarm_voting,
)
from h2physics.core import Origin

config = ConcentrationAlarmConfig(
    detector_id="detector-A", location_id="compressor-room-north",
    clock_id="campaign-clock-7", operating_mode_id="normal-operation",
    episode_id="synthetic-episode", concentration_basis="synthetic scalar",
    concentration_unit="arb", trip_threshold=0.8, reset_threshold=0.5,
    trip_confirmation_samples=2, reset_confirmation_samples=3,
    maximum_sample_gap_s=0.5, sensor_evidence_id="synthetic-sensor-evidence",
    threshold_evidence_id="synthetic-threshold-evidence",
    logic_evidence_id="synthetic-logic-revision", origin=Origin.SYNTHETIC,
)
trace = evaluate_concentration_alarm(
    config, time_s=[0.0, 0.2, 0.4], concentration=[0.4, 0.82, 0.9]
)
trip = ConcentrationAlarmEvidence.bind(trace, trace.transitions[0])
```

For a multi-detector vote, evaluate one alarm trace per detector with its own
qualified configuration, then combine traces on their exact shared sample grid:

```python
vote = evaluate_concentration_alarm_voting(
    (detector_a_trace, detector_b_trace, detector_c_trace),
    votes_required=2,
    voting_id="synthetic-2oo3",
    logic_evidence_id="synthetic-voting-logic-revision",
)
voted_trip = ConcentrationAlarmVotingEvidence.bind(vote, vote.transitions[0])
```

The values above are illustrative inputs only; the example is not a recommended
hydrogen alarm setpoint. Threshold selection and concentration calibration must be
provided and justified by the application owner. The deferred
`facility-concentration-alarm` contract covers sampled transitions, hysteresis,
single-detector evidence, explicit 2oo3 voting, integration with scheduled protection,
and input/alignment rejection. It has not been run; scientific and safety qualification
remains open.
