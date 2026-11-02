# Facility protection-event composition

**Status: implemented_unverified.** Source code, an authored example and six
deferred cases are written. No target-module/native import, model, example,
case discovery, test, replay, installation, benchmark or job has run locally.
AST/Ruff/LF checks do not establish protection reliability or facility safety.

`h2physics.adapters.facility_protection` is a narrow contract bridge among
existing native monitoring, LH2DT finite equipment and conditional risk. It
does not replace the scenario orchestrator, event localization, native tank/
network solver, shared nozzle, detector or probability aggregator. It calls
the existing owners and retains their actual objects and original failures.

## Explicit observation to command

`AlarmEvidence.bind(owner, evaluation, row_index=..., observed_mode_id=...,
sensor_evidence_ids=..., decision_evidence_id=...)` requires an actual
`NativeResidualMonitor` and an original `MonitoringEvaluation` registered by
that calibrated owner. It rechecks the native source and trained-state digest,
original fitting/calibration/evaluation batches, score/mask/alarm semantics and
copied versus original native result arrays. Fitting/calibration scores,
unalarmed rows, invalid causal windows and unknown/mismatched modes cannot trip
an action. There is no automatic first-alarm search or future-row selection.
The current monitor has no public result-verification method; the bridge
explicitly reuses its existing `_guard()` for original settings/model/partition
admission and binds that method/code. This private source seam is version-bound
and performs no fit, score or physical solve; a public owner hook remains an
upstream API improvement.

Every observed channel needs a sensor-evidence ID. Original channels, physical
Variable/unit/basis/location, source observations/predictions, episode, causal
decision time, native model and uncertainty-scale evidence remain under the
monitoring owner. The alarm retains the selected mode, clock and evidence and
guards their correspondence. Labels do not establish sensor calibration,
physical cause, leak classification or independence. A PCA score or an alarm is
never converted into a failure/ignition probability.

`ProtectionAction` declares target, protection mechanism, isolation or mode
change, prior/resulting actuator modes, nonnegative latency, origin and evidence.
Its interpretation must be `prescribed-counterfactual-replay`. Latency is an
explicit scenario input, not a predicted detection, communication, stroke or
proof-test delay. Autonomous native relief is a separate record below.

```python
from h2physics.adapters.facility_protection import (
    ProtectionAction, ScheduledProtection, execute_protected,
)
from h2physics.core import Origin

action = ProtectionAction(
    "feed-isolation", "feed-protection-mechanism", "pump-assembly", "isolation",
    "running", "isolated", 0.003, "explicit-latency-and-mode-evidence",
    "prescribed-counterfactual-replay", Origin.SYNTHETIC,
)
plan = ScheduledProtection(
    alarm, action, target=assembly.pump, native_context=assembly.network.native,
    read_mode=lambda target: target.mode_id,
    apply=lambda at, context: assembly.pump.set_mode("isolated"),
)
answer = execute_protected(
    assembly.driver, (plan,), duration_s=0.15, time_step_s=0.001,
    start_time_s=0.0, clock_id=alarm.clock_id,
    mode_definition_id="explicit-operating-mode-definition",
    scenario_evidence_id="explicit-prescribed-protection-path",
)
```

These are synthetic example values. `execute_protected` checks exact clock,
supported decision/command times, actual native context and unused plans, then
delegates to `Lh2dtDynamicEquipment.run` with the existing
`ScheduledEquipmentCommand` objects. The native driver owns command partitioning,
network solves, integration and inventory closure. No state is reset at isolation.
The callback must observe its declared prior mode and establish its declared
new mode. Duplicate invocation, wrong context/time or failed callbacks reject.

An `ActionInvocation` means the callback completed. `AcceptedProtection` also
requires the actual command ID/time in the original returned native
`EquipmentCommandTransition`. These are different facts. Only the original
`ProtectedEquipmentRun` issued after native return passes its result admission;
it can only be constructed by `execute_protected`, with a one-use owner token that
binds the exact returned native run, driver, prescribed plans, accepted commands,
mode definition and scenario evidence. Direct construction or replacement cannot
mint a second accepted protected replay receipt.
copy/replace does not issue a new result. Accepted solver snapshots are retained.
The raw command signature contains no clock; use the bridge entrypoint to enforce
its clock preflight. Passing a raw command to unrelated application code cannot
acquire that preflight guarantee.

This is an offline prescribed replay using one selected monitoring result. It
does not close a live sensor/controller/actuator loop, re-evaluate monitoring
against the protected trajectory, model actuator mechanics or prove that an
alarm was caused by the release. PRISM remains the higher-level scenario owner.

## Finite inventory and source ownership

`sampled_interval_source(run, component_id=..., location=..., state=...,
evidence_id=...)` reads an explicit outward one-way component at the external
boundary of all stored nodes. It reuses `integrate_equipment_rate` separately
on each original accepted interval, retaining both sides of command transitions.
The result is the existing `IntervalMassSource`: bins preserve those mass
integrals and represent only a constant mean rate within each bin. No new
hydraulic, critical-flow, EOS or quadrature implementation is supplied.

`FiniteFacilitySource.bind(...)` requires exact accepted edges/clock and
`window_end`, actual `InventoryBalance`/`ConservedInventory` objects and declared
`InventoryTolerances`. Existing per-node mass, stored energy, transported enthalpy
and external heat closure gates are reused. Each source bin must match the
accepted-sample integral and total mass must reconcile with native net inventory
boundary mass plus the caller's explicitly evidenced other net external mass.
That other boundary amount may be zero only when explicitly supplied with its
complete inventory/boundary scope. Source origin and property/spin/energy basis
remain explicit. A command does not imply source termination or erase downstream
line/vaporizer inventory. Depletion/isolation termination is not inferred.

The binding retains actual run, source/state/location, accepted native state and
solution identities, host ledgers, native cumulative ledgers and content hashes.
It rechecks those contents before/after risk evaluation. This is structural
original-object/content correspondence plus shared accounting, not native solver
replay or a producer seal for an arbitrarily fabricated pre-bind raw run.
Hidden native/callback state and concurrent mutation are not qualified.

The fixed source `ThermoState` and location are caller evidence. Mass-bin
verification does not establish an atmospheric/nozzle plane, varying exit
enthalpy, momentum, phase partition, deposition, room mixing or a consequence
field. `state_projection_evidence_id` is mandatory and its limitation remains
in `verification_scope`. Sampled quadrature versus native integrated inventories
requires case-specific refinement and the declared error gate; passing a
tolerance does not establish experimental accuracy.

## Native relief records

`ReliefProtectionRecord.bind(trace, transition, target_id=..., mechanism_id=...,
evidence_id=...)` retains an original `ReliefTankTrace` and one of its actual
`ReliefTransition` objects. Clock/support, native latch change, opening/reseat
kind, absolute pressure thresholds, localization bracket, actual native tank
state and original before/after nozzle results remain bound. Altered native
threshold/latch/state evidence invalidates the record. The original relief
driver owns hysteresis, event localization and finite tank physics.

A standalone relief trace is not coupled to the protected supply run merely
because a clock or label matches. This risk bridge accepts only protection
actions in the same actual finite equipment run. Coupling an autonomous relief
record into a shared facility inventory requires that physical owner/port
integration first; the record alone supplies no protected source or reliability.

## Conditional probability boundaries

`ConditionalDependence` declares scenario/operating case/mode/clock, conditioning,
factorization and annual-frequency-scope evidence, an exact map from every native
factor ID to its physical mechanism, and all protection mechanisms resolved by
this path. Every branch includes upstream-frequency, branch-probability, harm
and post-factor ownership. Different IDs mapped to the same mechanism within
one branch reject, as does additional numerical credit for a protection mechanism
already resolved by the physical trajectory. Separate branches may share a
mechanism because the native engine owns their exclusive partition.

The caller must justify conditional probability meanings and dependence through
the explicit factorization evidence. The bridge cannot discover hidden common
causes or validate an independence declaration. It performs no probability
multiplication, branch summation or frequency estimate. A supplied conditional
annual LOC frequency remains mandatory; no incident frequency, opening,
ignition, demand rate or failure probability is derived from the trajectory.

`evaluate_facility_risk` revalidates actual native `RiskInput`/`Context` fields,
exact physical run/source ownership and mode/clock, resolves source/action/sensor/
dependence evidence in the native context, then calls the original
`conditional_risk`. The native toolkit owns input/partition/credit validation,
aggregation and receipts. Its original request/context/output/receipt and source
remain in `FacilityRiskResult.native_conditional_result`. The result stays a
single conditional prescribed-path result, with no complete facility risk claim.
`FacilityRiskResult.require_current()` also rechecks the exact original native risk
result, finite-source receipt, accepted protection run and dependence declaration.
Direct wrapper construction, unchanged `dataclasses.replace()` cloning, and
replacement with a different dependence object are rejected. The facility result
and its nested native conditional-risk receipt each use a one-use issuer bound to
their original parents. This protects receipt ownership and does not validate the
declared harm model or conditional probabilities.
The existing harm-binding limitations remain: declared harm/field assumptions
are not a validated consequence solution.

An explicit sampled hydrogen concentration alarm is also admitted through
`ConcentrationAlarmEvidence` from `h2physics.adapters.gas_detection`. It uses
caller-specified trip/reset thresholds and confirmation sample counts; it supplies
no sensor-response physics or default setpoint. Multiple already-latched detector
traces may use an explicit same-clock k-of-n vote; this does not infer channel
independence, common-cause failure, or voting suitability. See
[GAS_CONCENTRATION_ALARM.md](GAS_CONCENTRATION_ALARM.md).

Individual alarm traces, voted traces and their confirmed-trip evidence require a
consumed one-use token minted by their evaluator or bind operation. Direct public
constructor calls and dataclass replacement cannot reuse the module's prior reusable
sentinel. The existing facility-concentration-alarm deferred contract covers these
issuer boundaries. This is receipt provenance, not detector-performance validation.

`FacilityProtectionError` retains the original cause, attempted driver/plan,
native context/time when available, completed invocations, accepted records,
returned native run/result and any lower-level failure. A failed callback may
leave its real target partly changed; no rollback, successful transition or
missing partial native run is invented. Native failure cannot switch providers.

## Deferred cases and rights

[The authored example](../examples/facility_protection.py) uses actual reviewed
native monitoring and the existing finite LH2DT supply fixture. Its monitor
reference/noise/latency and conditional annual risk inputs are synthetic.
The supply solver and monitoring outputs are not a measured closed-loop process.
It separately constructs a small actual native relief case without joining it
to the supply trace. The facility-protection profile also contains a deferred
concentration-alarm contract. The other deferred cases in
[facility_protection.py](../validation/cases/facility_protection.py) cover native
composition, admission/clock/masks, source/cache mutation, dependence, partial
action failure and original relief records. Profile: `facility-protection`.

No dependency is installed or added. Existing MIT monitoring/LH2DT and
Apache-2.0 conditional-risk rights/source receipts apply; code, training weights,
coefficients and external observations are not copied. Primary project identities
and exact existing receipts are recorded in
[the development record](../research/facility_protection_development.md).
