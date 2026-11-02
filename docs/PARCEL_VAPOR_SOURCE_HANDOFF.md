# Parcel evaporation to a finite vapor source

`h2physics.adapters.vapor_source_from_parcel_trace` adapts an existing
owner-issued `ParcelTrace` into the repository's `IntervalMassSource`. It adds
no evaporation or dispersion physics. Each output bin is the exact increment
of cumulative vapor mass in two adjacent accepted samples from the retained
native parcel integration. Consequently, the receiving source API represents
each interval with its documented constant mean rate; unresolved within-step
variation is not reconstructed.

Example:

```python
from h2physics.adapters import vapor_source_from_parcel_trace
from h2physics.core import Origin

handoff = vapor_source_from_parcel_trace(
    trace,
    location=source_location,
    origin=Origin.PREDICTED,
    evidence_id="case-specific-vapor-boundary",
    location_projection_evidence_id="case-specific-trajectory-aggregation",
)
handoff.require_current()
finite_source = handoff.source
```

`source_location` must use the parcel boundary's clock and coordinate frame.
Since the parcel moves while it evaporates and `IntervalMassSource` has one
fixed location, the adapter requires a separate projection evidence identity.
The caller chooses and justifies this aggregation location; it is not computed
from the parcel trajectory. Do not interpret it as a resolved spatial vapor
field.

The adapter retains the original trace and checks that it remains current,
that interval boundaries exactly match the accepted native times, that each
bin equals the corresponding cumulative vapor-mass increment, and that the
same typed vapor state and source location remain attached. Both adapter and
source reject stale/tampered content. `end_reason="window_end"` says only that
the recorded source interval ended with the supplied trace window. A ground
incident does not imply that all remaining liquid was deposited or evaporated.

This finite-source handoff can feed consumers already accepting
`IntervalMassSource`, such as explicitly configured release/dispersion routes.
It does not convert initial flash vapor, model phase separation, carry drop
momentum into the gas, infer a leak aperture, or establish any atmospheric
hydrogen dispersion validity. The deferred Hangang case
`parcel-vapor-interval-source-handoff` covers mass-bin identity and stale-source
rejection using an authored constant-heat trace; it is not experimental
validation. It requires the existing droplet-transport profile with CoolProp,
`fluids`, NumPy and SciPy available.
