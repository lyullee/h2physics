# Valve actuator development record

## Decision

The repository already has one pressure-driven equilibrium nozzle and one native
two-port valve adapter. A second valve flow equation would duplicate ownership.
The distinct missing resolution is finite actuator position plus a documented
hardware effective-area relationship. The new composition therefore advances
stroke in time and maps stroke to the existing valve's opening fraction.

## Admission boundary

Only caller-supplied monotone `CdA/CdA_max` data are accepted. Evidence identity,
URI, license, source hash, fluid and absolute-pressure basis are mandatory. The
code does not translate `Cv`/`Kv`, digitize vendor figures, copy tables or assert
that an authored curve represents hardware. The example is original synthetic
input and is explicitly unqualified.

## Implementation boundary

Opening and closing use separate bounded slew rates. Commands are contiguous,
clocked and sampled at every transition. The original `Lh2dtSharedValve` owns
direction, shared-nozzle physics, native result creation and energy interpretation.
Trace fingerprints protect stored inputs/results and owner bindings without
calling native code during inspection.

## Deferred verification

Six cases cover stroke, map interpolation, finite isolation, reverse permission,
schedule rejection and stale provenance. Per current execution policy they were
written but not discovered, imported or executed. Static AST/Ruff/whitespace
review is the only local gate. Manufacturer map conversion, measured transient
stroke, leakage and finite-vessel coupling remain future evidence.
