# Fixed-flow quasi-steady gas-source snapshots

`h2physics.adapters.run_hyram_finite_source_snapshots()` is a host-side
integration contract for a receiving gas-dispersion implementation that
accepts caller-prescribed hydrogen mass flow at the source plane. It consumes
an owner-issued `NozzleSourceProjection` made with `flow_rule="left_hold"`.
Each positive source interval is sent to an injected receiver as one independent
steady snapshot. Zero-flow intervals remain in the result with no native call.

The project's direct `run_hyram_gas_jet()` path does **not** implement this
receiver contract. It asks native HyRAM to calculate its own orifice flow. Do
not pass a finite-source rate to that stationary API or describe its output as
preserving the upstream flow. A compatible, separately supplied receiver must
implement `HyRAMFixedFlowReceiver.run_fixed_flow_snapshot()` and return a
`HyRAMFixedFlowRun` with both the requested and admitted source-plane H2 rates.
If the receiving version cannot accept and report an externally prescribed
rate, it is incompatible and this snapshot bridge cannot be used with it.

## Inputs and flow ownership

For each interval, the bridge sends the left-end nozzle state, interval opening,
original source location and clock, the interval mean flow from the source
projection, caller-owned ambient state and native atmosphere, state-mapping
evidence, atmospheric evidence, and immutable scalar solver options. The
receiver is responsible for documenting how its fixed-flow source boundary is
applied and for retaining its native output. The host compares the receiver's
admitted H2 rate with the requested rate using an explicit absolute budget; it
does not rescale either value. Native solver acceptance and source-plane rate
closure remain separately visible.

```python
from h2physics.adapters import (
    HyRAMFixedFlowCondition,
    run_hyram_finite_source_snapshots,
)

condition = HyRAMFixedFlowCondition(
    ambient=ambient_state,
    native_atmosphere=native_atmosphere,
    atmosphere_evidence_id="weather-record:...",
    state_mapping_evidence_id="property-map:...",
    solver_options={"max_distance_m": 100.0},
)
conditions = tuple(
    None if rate == 0.0 else condition
    for rate in projection.source.mean_rates_kg_s
)
series = run_hyram_finite_source_snapshots(
    projection,
    receiver=receiver_with_external_mass_flow_support,
    conditions=conditions,
    receiver_identity="receiver-package/version/method",
    source_rate_budget_kg_s=1e-7,
    require_accepted=False,
)
```

An interval exception is retained against its original index and time window.
When `require_accepted=False`, source mismatch and solver failure remain
diagnostics in the returned ordered series; otherwise the raised
`HyRAMFiniteSourceSnapshotError.series` contains the same interval records.
The bridge does not turn failed runs into accepted results.

## Method limit

The series method identifier is
`independent_quasi_steady_fixed_flow_snapshots` and
`plume_memory_included` is always false. Each interval starts an independent
calculation. Results do not interpolate between snapshots and do not support
continuous-time concentration or dose. A plume-memory transient requires a
receiver that evolves its atmospheric state on the declared absolute source
clock and integrates the supplied interval forcing; no such solver is included
here.

The API provides no new plume physics, HyRAM source code, copied equations,
validation evidence, or assurance that an external receiver's fixed-flow
boundary is implemented correctly. The native stationary HyRAM source gate,
the upstream nozzle/source mass ledger, and independent dispersion validation
remain distinct evidence items.
