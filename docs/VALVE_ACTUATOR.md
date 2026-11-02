# Finite valve stroke and admitted effective-area maps

`h2physics.adapters.lh2dt_valve_actuator` adds a time-resolved actuator boundary
to the existing `Lh2dtSharedValve`. It does not introduce another pressure-flow
law. Every flow evaluation remains owned by the shared homogeneous-equilibrium
nozzle and retains the original native `ValveResult` plus complete nozzle result.

## Python API

- `ValveMapEvidence` identifies the source, license, SHA-256, fluid and pressure
  basis of a caller-supplied map. A qualification flag is descriptive and never
  changes admission behavior.
- `ValveEffectiveAreaMap` accepts monotone `(stroke, CdA/CdA_max)` pairs on the
  exact `[0,1]` support. Interpolation is linear and extrapolation is impossible.
  Construction also requires the typed `ValveMapEvidence` receipt; a free-form
  or missing evidence object is rejected before the map can be bound to a valve.
  `stroke_for_opening()` performs an inverse lookup for a requested area ratio;
  if the ratio falls on a flat segment, `selection="minimum"` or `"maximum"`
  chooses one end of its supporting stroke interval. Targets beyond the map's
  area range are rejected. This does not invert target flow into valve position
  or provide a pressure controller.
- `StrokeActuator` advances position with distinct finite opening and closing
  rates on one explicit clock.
- `ValveCommand` declares contiguous `operate`, `hold` or `isolate` intervals;
  runtime construction rejects any other label, and `isolate` requires zero
  target stroke.
- `FiniteStrokeValve.run` requires all command boundaries among the sample times,
  evaluates the existing valve at the mapped opening and issues an immutable
  `ActuatedValveTrace`.

The map deliberately uses a dimensionless effective-area ratio. Converting a
vendor `Cv`, `Kv`, rated gas capacity or incompressible test curve requires an
independently reviewed basis and is not inferred here. The wrapped
`NozzleOpening` still owns maximum effective area and its area interpretation.

## Direction, clocks and ownership

Reverse flow is exactly the wrapped valve's explicit `allow_reverse` setting.
Negative native mass flow remains negative; it is not clipped. Actuator commands
do not infer pressure control or a filling protocol. Samples must span the exact
command support and include every boundary, preventing an unsampled command
transition from being hidden inside a step.

The trace is issued only by `FiniteStrokeValve.run()` after native valve
evaluations; direct construction and dataclass replacement are rejected. It seals
actuator/map inputs, endpoint states, original native results and the shared
valve/nozzle owner. `require_current()` rejects rebinding or retained content
changes. This is a stale-result guard, not a solver replay or scientific
validation claim.

## Limits

This level has no torque, motor current, pneumatic pressure, spring, stiction,
backlash, seat leakage, hysteresis, fail-safe transient, check-valve dynamics,
thermal storage, erosion or controller. Endpoint states are held inputs during
one trace. Real map conversion, apparatus data and coupled finite-inventory
execution remain separate qualification tasks. Eight Nurion cases are defined but
have not been imported or run. One case covers unknown command-mode rejection.
