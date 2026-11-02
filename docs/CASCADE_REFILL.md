# Generic cascade-bank refuelling sequence

`GenericCascadeRefillSequencer` selects at most one eligible source bank from a
caller-ordered set using caller-declared absolute-pressure switch thresholds
and source-to-receiver headroom margins. Its role is supervisory sequencing. It
does not calculate flow, pressure drop, gas temperature, fill time, vehicle-tank
thermal response, or a standardized refuelling schedule.

## API and composition

Define one `CascadeBankStage` per physical bank in the desired sequence. Every
non-final stage has a strictly increasing receiver-pressure switch threshold;
the final stage has no switch threshold. Each stage also has an explicit
minimum source pressure headroom. These are parameters, not inferred protocol
values.

`CascadeRefillMeasurement` accepts aligned absolute-pressure samples for the
receiver and every bank. Sensor ID, sensor owner, clock and evidence IDs are
retained. `initial_state()` binds one sequence to this exact sensor set and
clock. Each `step()` advances the stage monotonically and returns:

- `selected_bank_id` and a tuple of `CascadeBankPermit` values, with no more
  than one enabled bank;
- a `selected`, `waiting_for_headroom`, or `complete` status;
- the transition reason and next sample-boundary state.

When no configured bank has sufficient measured pressure headroom, every bank
permit is disabled. When the receiver reaches the caller's target pressure, all
bank permits are disabled and the sequence is marked complete. A completed
state cannot resume. The stage index never moves backwards, so a later rise in
an earlier bank's pressure does not silently reverse the chosen sequence.

```python
from h2physics.adapters.cascade_refill import (
    CascadeBankStage, CascadeRefillMeasurement, GenericCascadeRefillSequencer,
)

sequencer = GenericCascadeRefillSequencer(
    controller_id="station-cascade-A",
    target_receiver_pressure_pa_absolute=30e6,  # caller's example target
    stages=(
        CascadeBankStage("low", 4e6, 0.5e6),
        CascadeBankStage("medium", 16e6, 0.5e6),
        CascadeBankStage("high", None, 0.5e6),
    ),
    clock_id="station-run-01",
    evidence_id="caller-approved-threshold-set",
)
state = sequencer.initial_state(
    time_s=0.0,
    receiver_sensor_id="vehicle-pressure",
    receiver_sensor_owner_id="station-measurement-system",
    bank_sensor_ids={"low": "low-bank-pressure", "medium": "medium-bank-pressure",
                     "high": "high-bank-pressure"},
    bank_sensor_owner_ids={"low": "station-measurement-system",
                           "medium": "station-measurement-system",
                           "high": "station-measurement-system"},
)
measurement = CascadeRefillMeasurement(
    time_s=0.0,
    receiver_pressure_pa_absolute=1e6,
    bank_pressure_pa_absolute={"low": 5e6, "medium": 17e6, "high": 32e6},
    receiver_sensor_id="vehicle-pressure",
    receiver_sensor_owner_id="station-measurement-system",
    bank_sensor_ids={"low": "low-bank-pressure", "medium": "medium-bank-pressure",
                     "high": "high-bank-pressure"},
    bank_sensor_owner_ids={"low": "station-measurement-system",
                           "medium": "station-measurement-system",
                           "high": "station-measurement-system"},
    clock_id="station-run-01", evidence_id="sample-000",
)
decision = sequencer.step(state, measurement, end_time_s=0.5)
```

The decision is a separate supervisory input to the actuator layer. A caller may
combine the selected-bank permit with the existing PI controller's stroke target
and `FiniteStrokeValve`; the sequencer does not override PI gains or prescribe
valve opening. `Lh2dtFiniteTransfer` or another admitted finite-inventory model
continues to own actual source/receiver thermodynamics, flow and energy ledgers.

## Scientific and operational boundary

This is a configurable generic state machine, not an implementation of SAE,
ISO, or other refuelling procedures. Example numbers are authored fixtures,
not limits or recommendations. The model does not infer permissible vehicle
pressure/temperature, ramp rates, pre-cooling, communication protocol, bank
capacity, compressor replenishment, thermal soak, sensor uncertainty, leak
response, or emergency shutdown. The caller must qualify measurements, choose
thresholds and establish any required independent protection. No physical
calculation or process validation is claimed by this module.

Threshold crossing is sampled at caller-provided measurements; the code does
not locate between-sample crossings, filter signals, or debounce noise. The
sequencer refuses source/clock identity changes rather than aligning them
implicitly. Its exclusive permit list is not itself a safety-rated interlock.
