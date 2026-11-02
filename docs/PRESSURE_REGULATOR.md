# Sampled PI pressure-regulator controller

`h2physics.adapters.pressure_regulator.ProportionalIntegralPressureRegulator`
turns a caller-supplied downstream absolute-pressure sample into a bounded
stroke target for the existing `ValveCommand` interface. Its output is designed
to be placed in the contiguous command schedule consumed by
`FiniteStrokeValve.run()`.

## Control law

The controller normalizes the pressure error by a caller-selected pressure
scale:

```text
e[k] = (P_set - P_downstream[k]) / P_scale
I[k+1] = clamp(I[k] + e[k] * dt, -I_max, I_max)
s_raw = s_bias + Kp * e[k] + Ki * I[k+1]
s_target = clamp(s_raw, s_min, s_max)
```

The output command holds `s_target` over the interval from the measurement
timestamp to the next caller-selected timestamp. Low downstream pressure raises
the target stroke; high pressure lowers it. If the raw target is saturated and
the current error would drive farther into saturation, conditional integration
retains the previous integral state. The existing `StrokeActuator` separately
limits how quickly the physical stroke can follow the target. Gains use the
normalized error convention above; tuning evidence and all bounds are caller
inputs.

## Python use

```python
from h2physics.adapters.pressure_regulator import (
    PressureRegulatorMeasurement,
    ProportionalIntegralPressureRegulator,
)

controller = ProportionalIntegralPressureRegulator(
    controller_id="outlet-pressure-loop",
    setpoint_pa_absolute=5.0e6,
    pressure_scale_pa=1.0e5,
    proportional_gain=0.2,
    integral_gain_s_inv=0.01,
    bias_stroke_fraction=0.5,
    minimum_target_stroke_fraction=0.05,
    maximum_target_stroke_fraction=0.95,
    maximum_integral_error_normalized_s=2.0,
    clock_id="plant-run-01",
    evidence_id="approved-controller-tuning",
)
state = controller.initial_state(
    time_s=0.0,
    sensor_id="downstream-pressure",
    sensor_owner_id="measurement-system-01",
)
measurement = PressureRegulatorMeasurement(
    time_s=0.0,
    pressure_pa_absolute=4.9e6,
    sensor_id="downstream-pressure",
    sensor_owner_id="measurement-system-01",
    clock_id="plant-run-01",
    evidence_id="sample-window-00",
)
output = controller.step(state, measurement, end_time_s=0.5)
command = output.command  # Existing ValveCommand; pair with subsequent intervals.
state = output.next_state
```

Every measurement carries sensor, owner, clock and evidence identities.
Successive samples must retain the configured sensor/owner and land exactly on
the previous output end time. A controller state from another regulator or a
measurement from another source/clock is rejected. The output carries the
sample, command, next integral state, normalized error and saturation flag.

## Model boundary

This is a discrete PI command generator, not a complete pressure-regulator
physical model. It does not simulate a sensing line, sensor lag/noise, pneumatic
or spring force balance, pilot dynamics, valve friction, seat leakage, valve
flow, or downstream pressure response. The existing valve/nozzle model owns
mass flow; the finite-stroke actuator owns stroke rate; a caller-owned linepack
or network model owns downstream pressure evolution. The selected controller
gains, setpoint, pressure scale, stroke bounds, sensor interpretation and sample
period need independent tuning/qualification. The deferred Hangang contract
checks only command direction, timing, lineage and saturation arithmetic and
establishes no facility controller qualification.
