# Thermal utility coupling development record

2026-10-28: **implemented_unverified**. The user deferred scientific validation
until Nurion connection. This lane read existing source/API/rights and used only
static AST/Ruff/LF/diff inspection. No target module/native package import,
model/example/cases()/test/replay/benchmark/install or job was executed. Deferred
assertions and authored numeric fixtures are not observed results.

## Responsibility and source selection

`adapters/thermal_utilities.py` provides original Python contracts over existing
owners. It does not implement physical heat equations, pinch/utility optimization,
refrigeration cycle/COP, exergy equations, prices or annualization. The source
selection is intentionally specific:

- Actual validated PV/MEC `PhysicalCostProjection` bindings retain original
  trace/producer/quantity-unit identities. PV stack rejection is sign-reversed
  into the common positive-into-process convention; receiver heat and MEC
  required isothermal heat retain their original sign.
- Actual `CarrierConversionResult.require_current()` retains shared-kernel
  stage heat, caloric/reference and finite material ownership. Net stage heat
  preserves unresolved within-stage conditioning/reaction direction/timing.
- Actual `HeatExchangerTrace.require_current()` retains both native finite
  fluid/wall sides, native integrated interwall heat and original result seal.
  Those side heats are internal to a closed pair, not external utility energy.
- Raw accepted dynamic vaporizer/reliquefier runs supply existing cumulative
  external heat ledger differences. Internal wall-to-fluid heat is excluded
  from the external fluid-plus-wall boundary. The original inventory-node
  binding, native component/source provenance and explicit linking evidence
  remain retained. Existing inventory balance/tolerance gates are reused.
- Actual supplied steady `SteadyReliquefierResult` and native `VaporizerResult`
  supply original signed W. A mandatory caller-evidenced steady hold window
  converts W to J; no finite material stream, operation duration or annual
  representative period is inferred from that point.

The public `HeatDutyAdapter`/`HeatSnapshot` contract allows additional original
sources without JSON or replacing their physics. `HeatDuty.bind` checks source
and adapter contents/callable binding before and after a read-only snapshot,
retains original identities and issues an original profile. Current-source,
native metadata, owner-defined result seal and cache changes reject later.
Actual source diagnostics and reported endpoint temperatures remain available;
they do not become interface-temperature bounds automatically.

## Finite accounting and temperature meaning

All snapshots preserve their entire exact source clock/window/interval edges.
Joint accounting requires equal clocks and bins. Caller evidence must support
within-bin coincidence; no interpolation, storage or clock offset is supplied.
`TemperatureLevel` declares absolute-K bounds, actual interface and evidence.
Passive recovery requires conservative hot/cold bound compatibility and an
explicit approach. An absent bound cannot become a recoverable heat stream.

`ExergyReference` retains environment temperature/pressure/composition and
evidence, or unresolved status. The API carries reference identity and checks
consistency without evaluating work potential or a Carnot factor. Process
caloric reference, hydrogen spin and phase identities remain separate. Heat
increments across closed sides with different energy zeros do not authorize
mixing fluids or altering formation/reference offsets.

`HeatAvailability` requires finite recoverable J, original budget or explicit
scenario-assumption owner, boundary/evidence and origin. No utility availability
is derived from a required duty, UA, temperature difference, nameplate, cold
reservoir or heat capacity. Native removed cold-side heat is not refrigerator
work or warm condenser rejection. Recoverable budget is bounded by actual
reported interval rejection but is still an independent scenario/input claim.

Each explicit allocation supplies taken, delivered and loss J, temperature
levels, contact/reference/loss/coincidence evidence and source/sink identity.
The ledger checks finite per-bin and complete external energy balance and
retains tolerance residuals. It does not select an optimal network or maximum
recovery. One budget per original source, cumulative physical source/demand
limits and shared owner/component identities prevent copied/aliased budget and
boundary double credit. Hidden aliasing represented by unrelated owner objects
or unsupported evidence labels remains the caller's unresolved responsibility.

Native closed-HX receipt allocation is stricter: both sides must be the same
actual original trace, opposite interval heat must agree in one direction,
the whole original native transfer is retained once and no external loss is
invented. Internal native transfer is excluded from external utility totals.
An unrelated closed HX cannot qualify a process port by equal Q/time labels.
General cross-process recovery remains declared allocation until an existing
physical owner actually connects thermal boundaries and re-integrates states.

Registry outputs reuse original `required_heat_input_j`/`required_heat_rejection_j`
SI definitions and explicit boundary records. Declared ambient loss remains in
total external rejection. For the original synthetic finite fixture, the
intended independent ledger is40J source rejection,30J useful heat,2J explicit
loss and8J unallocated source rejection; external rejection therefore totals10J.
That arithmetic is an unrun acceptance oracle, not a measured saving or a
utility cost. No price or annual product denominator is added to the API.

## Native ownership and limitations

PV/MEC/carrier/finite-HX original producer hooks are reused without physical
replay. Native raw steady results and `DynamicEquipmentRun` do not expose the
same issued-result attestation. Their reader checks supplied actual classes,
native source/method provenance, current parameter/reference definitions,
original node linkage evidence and post-bind contents. It cannot prove that
an arbitrarily supplied pre-bind point was computed under unchanged parameters.
The raw dynamic run does not independently attest its originating component;
the original node binding/evidence is required rather than silently inferred.

The initial wall temperature is explicitly unavailable in a generic dynamic
run when the original state is not exposed there. Net accepted heat cannot
recover substep reversals or true gross duty. Declared temperature bounds are
not reconstructed from endpoint values or qualified by checking only retained
native points. Infinite/prescribed utility baths in upstream models remain
infinite/prescribed, even when their finite observed-duty window is reported.

Current-source checks read stored objects and definitions. No callback purity,
hidden opaque native state, concurrent-access safety, mechanism validity,
heat-transfer coefficient qualification or experiment is established. Original
exceptions and source/adapter/profile/allocation/native context are retained by
`ThermalUtilityError`. Failure cannot insert an alternate heat law, utility,
COP, source value or price.

Concrete receiving improvements, for parent coordination:

- Public issued-result/native-parameter admission for steady vaporizer and
  reliquefier results, matching the actual producer result and exact evaluated
  point/boundary/hold assumptions without rerunning physics.
- A public original-owner/node/component/clock seal on `DynamicEquipmentRun`,
  with accepted external heat increments and actual initial wall state. That
  removes caller-only component ancestry and the unavailable initial temperature.
- Shared physical process heat ports bound to actual source/sink owner state,
  interface/temperature support, finite utility inventory and native HX coupling.
  Equal postprocessed duty quantities alone cannot implement that closure.
- An explicit validated economic adjustment contract, if net thermal accounting
  is later priced, that replaces corresponding gross utility charges exactly
  once while retaining original product/annual/material basis and unresolved
  pressure work. Current registry records do not automatically become such a
  financial projection or an energy-saving claim.

## Rights, public references and deferred cases

All new host code and numeric examples are original. No third-party source,
property table, figure, measured observation or native implementation is copied.
No dependency is installed, added or bundled. Existing separately reviewed
Cantera/pvlib/CoolProp/LH2DT rights and receipts apply. Primary interfaces include
[LH2DT exact revision](https://github.com/lyullee/lh2dt_models/tree/b2f276333c1b1793c39f25763703d196d36742ec),
[Cantera thermodynamic properties](https://cantera.org/3.2/python/thermo.html) and
[pvlib source](https://github.com/pvlib/pvlib-python/tree/v0.16.1).
Existing host manuals/receipts preserve the underlying caloric, reaction and
native license/reference boundaries. The LH2DT source tree is MIT at revision
`b2f276333c1b1793c39f25763703d196d36742ec`, reviewed source SHA256
`5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.

Six metadata-only cases are added under profile `thermal-utilities`:

| Identifier | Intended acceptance, unrun |
|---|---|
| thermal-declared-balance | Explicit finite taken/delivered/loss and complete external energy accounting; original budgets and SI registry |
| thermal-negative-gates | Wrong clocks, aliased physical boundaries, absent availability/temperature, temperature lift, differing exergy references and copied budgets reject |
| thermal-native-HX | Actual original two finite native sides and opposite integrated heat; one already-settled transfer, no external utility credit |
| thermal-process-readers | Original PV stack/receiver, MEC and carrier signs/ledgers; no automatic clock alignment or utility availability |
| thermal-native-devices | Actual steady reliquefier/vaporizer W with explicit finite hold; actual dynamic external fluid-plus-wall heat without wall-heat duplication |
| thermal-mutation-failure | Original source/native definition and returned-array mutation reject with original native cause/objects preserved |

The future environment needs the existing reviewed native targets and repository
scripts used by original examples. Case import/discovery and scientific
entrypoints have not run locally. Native compatibility, numerical behavior,
performance and all expected metrics remain unverified until authorized cluster
execution. The parent owns catalog/central manuals/source-plan pins, Nurion
submission and evidence reconciliation. This lane changes only its five new
files and adds no new catalog family.
