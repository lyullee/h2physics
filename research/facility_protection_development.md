# Protection-event composition development record

2026-10-28 status: **implemented_unverified**. User instructions require coding
first and defer scientific validation until Nurion connection. This lane read
source/API/rights and ran only static AST/Ruff/LF/diff checks. No target module
or native package was imported/executed; no test, model, example, cases(),
replay, benchmark, install or job was started. Deferred assertions are not passes.

## Scope and original owners

The new narrow `adapters/facility_protection.py` connects existing native objects:

| Responsibility | Existing owner retained |
|---|---|
| Residual features, trained PCA, calibration, mode-specific alarms | `process_monitoring.NativeResidualMonitor`, original registered `MonitoringEvaluation` and actual Process Monitoring Toolkit |
| Prescribed command partition, network solution and finite stored-device integration | `ScheduledEquipmentCommand`, `Lh2dtDynamicEquipment`, actual native LH2DT solver/results |
| Mass/energy accounting and accepted-sample integration | Original `ConservedInventory`, `InventoryBalance.violations`, `integrate_equipment_rate` |
| Hysteresis, accepted latch and localized pressure events | Existing `Lh2dtReliefTankDriver`, original `ReliefTankTrace`/`ReliefTransition` |
| Source/receptor/harm admission and probability aggregation/receipts | Existing `conditional_risk` and actual native toolkit |
| Higher-level scenario orchestration | PRISM; no new scenario scheduler in this bridge |

The facility bridge introduces no detector, EOS, nozzle, time integrator,
event locator, failure/ignition correlation, probability sum/product or accident
frequency model. Accepted data are read through original Python objects.
The stable source snapshot/hash/callable hooks are reused from the public
`physical_economics` helper; no financial owner or native DCF is called here.

## Implemented event and source contracts

`AlarmEvidence.bind` selects an explicit held-out native alarm row. It retains
original owner/model/result/data and sensor/location/unit/basis/source/evidence
correspondence, rechecks actual native source and trained model digest, and
rejects warmup/invalid/unknown-mode/unalarmed rows. It does not infer a fault or
turn a score into probability. Native monitor registration is a structural
ownership gate, not a newly implemented producer-replay seal.
There is no public monitor result-verification method. The bridge calls the
existing owner's `_guard()` before/after reading its result and binds that
actual method/code, so prior settings/model/partition mutation is not admitted.
This reuses the original source guard without fit/score/model execution. A
public `NativeResidualMonitor.verify_result(result) -> same original result`
with original registered result/config/cache evidence would remove that exact
private seam; parent coordination can specify it without changing native code.

`ProtectionAction` requires an explicit target/mechanism, prior/resulting mode,
nonnegative latency, provenance and prescribed-counterfactual interpretation.
`ScheduledProtection` compiles that action to the original command type and
guards actual callback/function/code/context/target/time identity. Callback
completion and an actual returned accepted native transition are separate
records. `execute_protected` delegates to the actual existing finite driver;
only its original issued `ProtectedEquipmentRun` passes admission. Copy/replace
does not issue a successful run. No inventories are reset on isolation.

This offline replay does not feed the protected source back to the detector or
simulate detection/communication/stroke mechanics. It cannot establish causation,
safety integrity, proof-test coverage or device reliability. Clock identities
and full physical seconds/support must match exactly; no offset/resampling or
sensor-pressure reference repair occurs.

`sampled_interval_source` reuses the existing accepted-sample integration on
each original interval, including both command limits. The source retains
constant-bin-mean mass representation; unresolved substep transients remain
unresolved. `FiniteFacilitySource` checks every existing inventory/energy ledger,
exact edges/clock, source bin integrals, native accepted state/solution pointers
and cumulative ledgers. Total source mass must reconcile to all selected stored
nodes plus an explicit evidenced other-net-external-mass amount. There is no
implicit zero feed, inventory erase or source truncation at a feed-isolation
command. Source state/phase/energy/spin basis is explicit caller evidence;
the bridge validates mass ownership, not a resolved enthalpy/momentum or
atmospheric/ground source plane. Only window_end is admitted by this dynamic
source path. Native depletion/localization is not invented.

`ReliefProtectionRecord` separately binds actual original native latch events,
before/after native objects and nozzle results, tank state, threshold pressure,
kind, time/bracket/clock/support and explicit protection evidence. It does not
run the latch policy or event locator. It cannot be joined to an independent
finite supply inventory by time labels alone; a shared physical port/inventory
owner is still required before a coupled relief source can enter this bridge.

`ConditionalDependence` requires source-path conditioning, factorization and
frequency-scope evidence and maps every native upstream/branch/harm/post-factor
ID to an explicit physical mechanism. Renamed duplicate mechanisms within one
branch and numerical reliability credit for already resolved protections reject.
The same mechanism across separate exclusive native branches is allowed. This
gate checks declared ownership, not actual statistical independence or hidden
common ancestry. Annual frequency and every probability remain supplied inputs.
Native `RiskInput`/`Context.model_copy` edits are revalidated through the original
native model contract before original `conditional_risk` is called.

The returned facility object retains original native risk results/receipt,
physical source, protected run and dependence assumptions. Original failure
causes, actual targets (including partial mutation), attempted plans, completed
invocations and any actually returned native prefix/result remain inspectable.
If the native driver throws without returning a run, `native_run` remains None;
the lower original error and actual driver/actuator are retained. No fabricated
accepted prefix, automatic rollback or alternative provider repairs the failure.

## Reuse, rights and source limits

The existing primary native projects are
[Process Monitoring Toolkit](https://github.com/lyullee/process-monitoring-toolkit),
[LH2DT](https://github.com/lyullee/lh2dt_models) and
[Process Risk Consequence Toolkit](https://github.com/lyullee/process-risk-consequence-toolkit).
Their existing reviewed records are `research/monitoring_dependency.toml`,
`research/risk_dependency.toml` and the exact LH2DT revision/source record in
the existing native integration documentation. Monitoring is MIT at revision
`79b4cf52a0acd0d0cbd3addbe82c3d98d6385e5a`; LH2DT is MIT at
`b2f276333c1b1793c39f25763703d196d36742ec`, reviewed tree SHA256
`5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
The existing conditional toolkit0.1.0 is Apache-2.0 with native code digest
`0d5239de3ba9a919a0a0b38a912fc86899d92f10da5e6a9e7a563d8abeec9152`.
No new native installation, dependency, dataset acquisition, copied native code,
source table/figure/prose, trained weights or external observation is introduced.
Optional engines stay separately installed and retain their original notices.

The example reuses the existing original finite-supply fixture through an
explicit future validation environment containing the repository scripts and
reviewed optional targets. That fixture retains its original synthetic pump/
orifice/heat/geometry assumptions and native source gates. The new authored
monitor reference is expressly prescribed synthetic data, not native physical
output or a measured leak. Annual frequency1e-4/year, branch fractions0.2/0.8,
conditional harm0.4/0,0.003s latency and other example numbers are synthetic
scenario assumptions, never calibrated performance or a facility frequency.

Structural snapshots reject bound content/identity changes but do not prove
arbitrary pre-bind raw-run authenticity, callback purity, hidden native state
or concurrent access safety. Existing field/harm model and sampled-quadrature
limitations are preserved. Independent observation comparison, action timing
experiments, reliability/dependence evidence, native result-owner admission
for raw dynamic traces and common-inventory autonomous-relief composition remain
unresolved work. No new catalog family or software/experimental qualification
increment follows from these written contracts.

## Six deferred cases

Profile `facility-protection` adds six metadata-only case definitions:

| Identifier | Intended acceptance, unrun |
|---|---|
| facility-native-chain | Actual native monitor alarm, accepted command/source/inventory and original native risk; finite release continues from downstream stock after feed isolation |
| facility-monitor-guards | Invalid warmup, wrong mode, altered evidence, negative latency and unmapped clock reject without successful command |
| facility-source-guards | Changed source bins and original accepted native cumulative ledger reject |
| facility-dependence | Resolved protection credit and renamed duplicate physical mechanisms reject before risk aggregation |
| facility-action-failure | Original callback cause and partly changed real actuator retained; no invented returned native run |
| facility-relief-record | Actual small native latch trace preserved; altered native threshold invalidates it; no independent-trace coupling claim |

These entrypoints require the existing reviewed native monitoring stack, LH2DT,
CoolProp/shared hydraulic dependencies and conditional-risk/Pydantic stack.
The future cluster profile must select their explicit targets plus repository
root/scripts paths; the production adapter never installs or changes paths.
Module discovery/cases() execution and all model/native checks were deferred.
The parent owns environment/source/plan pins, Nurion submission, result
reconciliation and central catalog/progress changes.

## Static source snapshot

Read-only dependency byte hashes at this checkpoint (not executed model results):

| File | SHA256 |
|---|---|
| adapters/process_monitoring.py | `971a5ba6227e393d5f4bb970ad4b1d1f15f3e7e153131ab950be404aa310b1f8` |
| adapters/conditional_risk.py | `bb24080cc51f3fbf3d4dd5c583aa47dfc33debc4433657bd418e624d53a12c7e` |
| adapters/lh2dt_dynamics.py | `24d47555c295cfd7850459933a2077b1c37bf5ffcffa292045b962cd93daec69` |
| adapters/lh2dt_relief.py | `4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282` |
| dynamics.py | `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd` |
| adapters/physical_economics.py | `7d88a8a0694938dd5d075f311c210264ce1bedd054d082850500bc94a1a36f72` |
| research/monitoring_dependency.toml | `380a5be8b7ef8b4ad3e78ef7bfe6e03b1ce2837eaca6e9188206645a1ef1255c` |
| research/risk_dependency.toml | `9e8bb997527c23362a60480635a65d16618c4a2242acabad2e092dce9e2ede6c` |

The first six paths are relative to `src/h2physics/`. Reading the51 native LH2DT
top-level Python files as original filenames plus bytes reproduced the existing
reviewed tree SHA above, without importing or executing any native module.
The five owned files alone are new; existing sources/receipts and central
documentation were not edited by this lane. Static acceptance commands use
`ast.parse` over the three owned Python texts, Ruff check/format and explicit
LF byte inspection of all five files. The final own-file hashes are reported
at freeze rather than adding a self-referential report checksum.
