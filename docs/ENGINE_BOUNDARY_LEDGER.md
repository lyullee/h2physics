# Engine boundary schedule ledger

`h2physics.combustion.engine_boundary_ledger` combines the existing absolute-time
`EngineBoundarySchedule` with a source-bound mass-flow and specific-enthalpy pair.
It integrates intake, direct fuel-feed, and exhaust transfers over an explicitly
selected interval. Intake and fuel count positive into the cylinder; exhaust counts
negative. Every stream must use the same caller-declared enthalpy reference.

```python
from h2physics.combustion.closed_charge_engine import EngineBoundarySchedule
from h2physics.combustion.engine_boundary_ledger import (
    EngineBoundaryStream,
    integrate_engine_boundary_streams,
)

# Construct flow and enthalpy schedules on an identical absolute-time grid.
# Include source identity, units and clock origin in each schedule.
stream = EngineBoundaryStream(
    identifier="intake-port-a",
    kind="intake",
    mass_flow=flow_schedule,              # quantity=mass_flow, units=kg/s
    specific_enthalpy=enthalpy_schedule,  # quantity=specific_enthalpy, units=J/kg
    enthalpy_reference="project:declared-h0-v1",
)
ledger = integrate_engine_boundary_streams(
    [stream], start_time_s=absolute_start, end_time_s=absolute_end,
)
ledger.require_current()
```

The flow magnitude must be nonnegative; direction comes from the stream kind.
For the accepted piecewise-linear histories, mass is integrated trapezoidally.
Enthalpy transfer is the integral of mass flow times specific enthalpy; their
product is quadratic between common knots, so midpoint Simpson quadrature exactly
integrates that declared interpolation. No extrapolation is allowed.

This ledger accounts for requested boundary schedules only. It does not calculate
valve flow, injector physics, spark deposition, cylinder mixing, combustion, or
accepted native solver edges. In particular, the result must not be subtracted
from a cylinder's internal-energy change and reported as first-law closure unless
the receiving solver independently confirms those exact transfers at accepted
steps. The existing moving-volume model remains a closed-charge segment; complete
four-stroke cycle integration, gas exchange, controls and engine qualification
remain open under [Request 034](../requests/034_hydrogen_engine_cycle.md).

The deferred case `hydrogen-engine-boundary-stream-ledger` checks synthetic sign,
reference, support, schedule-integral and stale-source contracts. It has not been
executed. It is software-contract coverage, not validation against a hydrogen
engine experiment.
