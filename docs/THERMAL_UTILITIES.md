# Finite heat recovery and utility contracts

**Status: implemented_unverified.** Source, examples and six deferred cases are
written. No target-module/native import, model, case discovery, example, test,
replay, benchmark, installation or job has run locally. Static AST/Ruff/LF
checks are not numerical or experimental verification.

`h2physics.adapters.thermal_utilities` reads original heat duties and audits
explicit finite allocations. Existing process, property, native equipment and
integration owners retain all physical calculations. This API supplies no pinch
solver, heat-network optimization, heat-storage model, utility capacity model,
COP, exergy calculation, tariff, saving estimate or annualization rule.

The stable composition surface is re-exported from `h2physics.adapters`,
including `HeatDuty`, source-specific readers, finite availability/allocation
records, native exchange receipts, the ledger and `account_heat`. These names
are direct references to the implementation types, so imports retain the same
provider-owned identity and freshness checks. The `thermal-public-adapter-exports`
case checks that export contract and remains deferred.

## Source-bound interval heat

`HeatDutyAdapter.snapshot(source, window) -> HeatSnapshot` is the provider-neutral
Python contract. `HeatDuty.bind(source, adapter, HeatWindow(...))` retains the
actual source, owner/function/code identity, original native objects, energy
reference, evidence, interval edges and signed J. Positive heat enters the
declared process boundary. Source/adapter definitions are checked before and
after the read-only audit; later source/cache/array/callable changes invalidate
the issued profile. A copy/replace does not issue a new `HeatDuty`.

`HeatWindow` has explicit physical seconds, start/end, clock and evidence. Every
adapter preserves the complete original window. Accounting requires identical
clock IDs and exactly equal interval edges across all profiles. There is no
clock repair, cropping, interpolation, hidden storage, resampling or implicit
within-bin timing. Arrays are copied, finite, one-dimensional and read-only.

| Adapter | Actual source and signed meaning |
|---|---|
| `ProjectionHeatAdapter("pv-stack")` | Validated physical-economic projection of an original PV trace; negative of original stack rejected J |
| `ProjectionHeatAdapter("pv-receiver")` | Original receiver heat into fluid-plus-inventory J; distinct from stack duty |
| `ProjectionHeatAdapter("mec")` | Original producer-issued MEC required isothermal heat into process J |
| `CarrierHeatAdapter()` | Original producer-issued carrier thermochemical stage `heat_required_j`; conditioning and reaction remain under the shared kernel |
| `FiniteExchangerHeatAdapter(side_id)` | Original native finite HX side's cumulative interwall heat differences; internal to the closed pair |
| `DynamicDeviceHeatAdapter(...)` | Original vaporizer/reliquefier node's accepted external fluid-plus-wall heat ledger differences; internal wall-to-fluid heat is excluded |
| `SteadyNativeHeatAdapter(...)` | Actual supplied native vaporizer/reliquefier point W times an explicitly evidenced hold duration; no native residence time or finite material supply is inferred |

PV/MEC projections retain the public `physical_economics` source-binding contract
and original producer verification hooks. Carrier and finite HX hooks also
verify their issued original results without replaying physics. Native source
and method provenance is retained for device readers. Raw dynamic runs and
steady native points have no equivalent producer result seal: their binding
audits supplied actual objects/current definitions and subsequent mutation,
not arbitrary pre-bind execution authenticity. Dynamic node/component linkage
therefore also needs the actual retained inventory binding and explicit evidence.

Required duty is not supplied utility. A cold-side removal is not refrigerator
electrical work or a warm condenser heat stream. A steady capacity is not a
seasonal available-energy budget. Stage/accepted-interval net heat does not
resolve opposing heat directions or timing within that interval; it cannot
recover missing gross heating/cooling histories. Those limitations remain on
`HeatSnapshot.verification_scope` and the original source.

`reported_temperature_k` retains original process/wall values, including an
unavailable initial wall temperature where the raw run does not expose it.
Endpoint values are not automatically promoted to interval extrema or the
temperature of an external utility interface.

## Temperature, references and finite availability

`TemperatureLevel` requires explicit minimum/maximum absolute K, actual interface
identity and supporting evidence for each interval. `None` is unresolved and
cannot authorize positive recovery. `ExergyReference` separately retains the
environment temperature/pressure/composition and its evidence, or an explicit
unresolved status. No Carnot factor, work potential or exergy value is derived.
The two sides must retain the same declared environment context; differing
references reject. Separate process caloric zeros, phases and hydrogen spin
bases remain on their original sources. Cross-boundary heat increments do not
convert species, enthalpy references or fluid inventories.

`HeatAvailability` is mandatory for a source allocation. It holds explicit
recoverable J per original interval, finite-boundary identity, actual budget or
scenario-assumption owner, evidence and origin. Its budget cannot exceed the
original interval heat rejection. Missing availability is never filled from
the duty, a UA, temperature difference, a nameplate, an infinite bath or a
capacity factor. One original budget record must be reused for all allocations
from that source. A second copied/renamed budget cannot create more supply.

For example, caller-provided quantities can be passed directly:

```python
from h2physics.adapters.thermal_utilities import (
    HeatAvailability, HeatAllocation, account_heat,
)

budget = HeatAvailability(
    donor, explicit_recoverable_j, availability_evidence_id,
    finite_boundary_id, original_budget_owner, origin,
)
transfer = HeatAllocation(
    identifier="explicit-contact", availability=budget, sink=sink,
    taken_j=explicit_taken_j, delivered_j=explicit_delivered_j,
    loss_j=explicit_loss_j, source_levels=source_levels, sink_levels=sink_levels,
    minimum_approach_k=explicit_approach_k, thermal_contact_id=contact_id,
    reference_compatibility_evidence_id=reference_evidence_id,
    loss_boundary_evidence_id=loss_evidence_id,
    coincidence_evidence_id=within_bin_timing_evidence_id,
)
ledger = account_heat(
    (donor, sink), (transfer,), evidence_id=accounting_evidence_id,
    energy_tolerance_j=explicit_energy_tolerance_j,
)
```

All amounts and assumptions in this pattern are caller inputs. No maximum
recovery amount or favorable contact is selected automatically.

## Allocation and double-count gates

`account_heat` checks each bin's explicit taken = delivered + loss, finite
availability, cumulative source rejection and cumulative sink demand. Positive
recovery needs declared source minimum K at least the sink maximum K plus the
explicit nonnegative approach. A passive connection cannot lift heat to a
higher temperature. Positive ambient loss additionally needs a compatible
explicit environment temperature. The within-bin coincidence evidence is
required even when bin edges match; matching clocks alone does not establish
simultaneous availability or heat-storage capability.

The ledger retains original physical owner/component identities. Repeated or
aliased/aggregate representations of the same boundary reject. Allocations
share one finite source budget, retain source/sink identity, cannot exceed the
same physical supply/demand in aggregate and cannot credit a native transfer
twice. These gates check declared identities; they cannot discover hidden
duplicate equipment represented by unrelated owners or false evidence labels.

The result exposes per-profile remaining demand/rejection, total declared loss,
native internal transfer recorded once and a complete finite external energy
residual. Original process duties/states are untouched. Differences within an
explicit tolerance remain visible rather than being clipped to zero.
Positive utility totals still must be nonnegative.

The existing public quantity registry supplies `required_heat_input_j` and
`required_heat_rejection_j` and their SI/boundary records. Total external
rejection includes both unallocated process rejection and declared heat loss;
loss cannot disappear into an unpriced zero boundary. These are conditional
energy-accounting outputs, not proven utility-device loads or prices. They are
not automatically admitted as a new `PhysicalCostProjection`; original gross
quotes must not be billed alongside an adjustment for the same heat. H2
generation/stock/sale basis, price, refrigeration work and annual finance remain
separate original-owner inputs.

## Already settled native heat transfer

`NativeExchangeReceipt.bind(donor, receiver, ...)` accepts only the two actual
sides of the same original finite HX trace. It reads the native integrated
opposite side heats, requires one declared direction and equal opposite energy
within the explicit tolerance, and retains both original profiles and trace.
No new UA law or transfer integration is implemented.

An internal HX profile cannot become an independent free utility. Its allocation
requires that exact native receipt, complete native transfer amount, zero
external loss and a single receipt use. `native_internal_transfer_j` records
the already settled transfer once; internal pair heat is excluded from external
utility quantities. The separate native fluid/reference/wall objects remain
available. The API cannot attach an unrelated closed HX trace to a PV/MEC/
carrier process just because its heat amount, clock or label matches.

Other cross-process allocations remain declared thermal-boundary scenarios.
They do not rerun the source/sink at altered temperatures or prove an actual
process-to-HX port connection. A physically coupled facility still needs its
existing owner to connect those thermal boundaries and re-integrate states.

## Original objects, failure and deferred execution

`require_current()` rechecks source-owned seals/definitions, original native
objects, owned cache arrays, budgets, allocations and returned residual arrays.
It does not evaluate kinetics, heat transfer, EOS or another physical model.
`ThermalUtilityError` keeps the actual original cause, source/adapter when binding,
or original profiles/allocations when accounting. No missing utility, repaired
temperature, fallback source or cost is inserted. Opaque hidden native/callback
state and concurrent access are outside this correspondence audit.

[The examples](../examples/thermal_utilities.py) contain an authored finite
accounting fixture, actual native closed-HX receipt, separate original PV/MEC/
carrier readers and native vaporizer/reliquefier readers. No example has run.
[Six deferred cases](../validation/cases/thermal_utilities.py) use profile
`thermal-utilities`: finite balance, domain/reference/clock/budget gates, actual
native HX, original process readers, native devices and mutation/failure
retention. The existing optional native environments are required later; no new
dependency is installed or bundled. Exact source/rights and remaining API gaps
are recorded in [the development record](../research/thermal_utilities_development.md).

`NativeExchangeReceipt` is issued only by its validating `bind()` path. A receipt
rechecks that its duties are distinct opposite sides of the same native exchanger,
share the exact interval grid, and retain equal-and-opposite interval heat. The
existing `thermal-native-HX` deferred case rejects direct same-side construction
and reuse of a consumed receipt token; it remains unexecuted.
