# Finite facility source energy projection

`FiniteFacilitySource` binds a mass-only outlet source to an accepted finite
equipment run. The declared `state_projection_evidence_id` identifies the
caller-selected fixed `ThermoState` used by downstream consumers. That state is
not automatically the actual thermodynamic state at the equipment's outlet
plane.

## Python API

```python
projection = finite_source.energy_projection()
native_j = projection.native_transport_enthalpy_j
projected_j = projection.projected_enthalpy_j
residual_j = projection.residual_j
```

The method revalidates the original `FiniteFacilitySource`, then integrates the
selected component's `outlet_enthalpy_flow_w` over each accepted source interval
with the same command-aware accepted-sample quadrature used by its mass bin.
The diagnostic compares this native transmitted-state energy against the
caller-declared fixed-state projection:

```text
projected_j[i] = source.mass_kg[i] * source.state.enthalpy_j_kg
residual_j[i]  = native_j[i] - projected_j[i]
```

`native_integrals` retains each `SampledEquipmentIntegral` with its native
clock, interval bounds, rate/integral units and sample count. The result also
retains the finite source SHA-256, component identity and state-projection
evidence identity. `total_residual_j` sums the interval discrepancies.

## Cumulative facility ledger

`finite_source.ledger_history()` exposes all selected inventory ledgers on one
absolute accepted-time axis. It returns `FiniteFacilityLedgerHistory`; all
series are copied and read-only. At each point it reports cumulative selected
source mass, total selected inventory mass/energy change, native external
boundary ledgers, source-outlet enthalpy and caller-state projected enthalpy.
The residual arrays use these definitions:

```text
mass_residual = inventory_mass_change - native_boundary_mass
other_net_boundary_mass = native_boundary_mass + source_mass
energy_residual = inventory_energy_change - native_boundary_energy
boundary_energy_partition_residual = native_boundary_energy
                                     - transported_enthalpy - ambient_heat
source_enthalpy_projection_residual = native_source_enthalpy
                                       - projected_source_enthalpy
```

`other_net_boundary_mass` is the inferred aggregate of all other external mass
transfers in the selected inventory set; it does not identify individual
feed/vent streams. Its final value is reconciled with the declared net other
boundary mass retained by `FiniteFacilitySource.bind()`. This API exposes the
accepted cumulative history for plots and cross-module handoff while preserving
the distinction between native cumulative balances and accepted-sample source
quadrature.

`adapters.facility_operation.report_facility_operation()` builds a read-only,
common-clock view over an admitted `FacilityOperationReceipt`. It groups original
node mass/energy residuals by node, retains equipment component-energy residuals
with their sample times, and carries the original net utility quantities and
utility allocation residual. The report rechecks its operation and does not add
prices, product sales, rates, new boundary assignments, or a whole-facility
closure decision. `report.node_residual_series(node_id)` returns one selected
node's mass and energy residual tuples together with the exact common accepted
clock, without interpolation or balance recomputation. Unknown node identities
are rejected. Its deferred fixture contract is not yet executed.

`integrate_facility_operation_residuals(report)` optionally integrates the
reported instantaneous node and component residuals using piecewise-linear
trapezoidal quadrature over the original accepted samples. It returns per-node
mass integrals in kg and per-node/component energy integrals in J, retaining the
source report and checking it again on access. This is a sampled-rate diagnostic;
it neither reconstructs native cumulative inventory nor proves whole-facility
closure. The same deferred report contract records its units, identities and
quadrature rule.

During `bind_facility_operation()`, continuity frames are audited in accepted-clock
order. If a later frame fails, `FacilityOperationAuditError` retains the original
source/auditor/utility objects, failed frame and index, completed frames/results,
and the original exception as `cause` and `__cause__`. It does not create a partial
operation receipt or imply that the retained prefix is a complete facility audit.
The deferred `facility-operation-audit-prefix-retention` contract covers this
failure boundary; it has not been executed.

## Interpretation

This is an interface diagnostic, not a new outlet thermodynamics model. A
nonzero residual quantifies the mismatch between accepted component-port
enthalpy transport and the selected fixed-state representation. The method does
not force the residual to zero, tune the caller's state, or claim that the
component port is an atmospheric release plane. The accepted-sample quadrature
is not the native RK-stage integral; interval refinement and comparison with
native balances are needed before using it as an energy-closure gate. No gas
mixing, pressure relaxation, kinetic-energy recovery, jet expansion or ambient
partition is inferred.

`validation.cases.facility_protection:validate_source_guards` has a deferred
contract for source identity, per-bin native integration and residual reporting.
`validation.cases.facility_source_energy:validate_cumulative_ledger` checks the
time-aligned whole-system balances, inferred residual mass history and immutable
series. Neither case has been executed; this work adds API/contract code and
static checks only.
