# Physical reporting and native hydrogen economics

**Status: implemented_unverified.** The adapter and seven deferred HPC cases are
written; no local economic/PV calculation, native import, example, pytest,
replay or benchmark has been executed. Static syntax/lint inspection is not
financial verification, experimental validation or an investment assessment.

`h2physics.adapters.hydrogen_economics` connects a validated finite physical
projection to optional native pyH2A0.0a8. The host owns reporting,
physical units, explicit cost boundaries and input/output admission. pyH2A owns
discounting, depreciation, taxes, financing, startup financial adjustments,
cash-flow calculations, cost contributions and native levelized hydrogen cost.
No host replacement finance formula is supplied.

## Public source and quantity contracts

`h2physics.adapters.physical_economics` owns the common reporting API.
`PhysicalSourceAdapter.snapshot(source, window, hydrogen_id)` returns a
`SourceSnapshot` containing the actual source, explicit SI quantities,
`QuantityBoundary` records, unavailable-cost identities, portable content and
original object identities. `ValidatedSourceBinding.bind(...)` runs that source
audit and seals its audit-function/code binding, content and original pointers.
`PhysicalCostProjection.from_source(...)` returns the common projection.
The finance owner admits `PhysicalEconomicProjection` only through an actual
validated binding and checks the projection against that binding itself; a
duck-typed `require_current()` alone cannot admit invented quantities.

`QUANTITY_REGISTRY` and `quantity_definition()` expose quantity, unit, oriented
boundary, product role and billing rules. Canonical keys include
`generated_h2_kg`, `initial_h2_stock_kg`, `final_h2_stock_kg`,
`h2_stock_increase_kg`, `harvested_h2_kg`, `sold_h2_kg`,
`electrical_work_into_j`, `required_heat_input_j` and
`required_heat_rejection_j`. A registered key does not imply that a particular
source reports it. Absent quantities reject pricing; `None` means unavailable,
never zero. Source-specific aliases remain explicitly labelled.

Public `finite_sum`, `stable_snapshot`, `snapshot_sha256` and
`callable_identity` support source adapters without private cross-module
helpers. Snapshots retain array dtype, shape and a digest of copied C-order
bytes; opaque native objects need an explicit content mapper and separate
identity record. Item/depth/array-byte budgets bound snapshot construction.
Raw nonfinite diagnostics are labelled in snapshots, while reported physical
amounts must be finite. None of these hooks runs a physical or financial solver.

Existing imports of `ReportingWindow`, `PhysicalCostProjection`, `UtilityTariff`
and `WindowUtilityCost` from `hydrogen_economics` still resolve to the public
common classes. The old PV factory and PV tariff aliases remain available.
The six-argument projection constructor now performs a real PV source audit
and requires the supplied cache/fingerprint to match it. New sources should use
the public source factory rather than constructing a subclass with PV meaning.

## Reviewed provider

[pyH2A](https://github.com/jschneidewind/pyH2A), by Jacob Schneidewind, is an
H2A-based Python economic engine. The actual reviewed PyPI artifact is
version0.0a8; its code license is MIT and its noncode content is declared
CC BY4.0. Attribution, original artifact/license/source/resource checksums are
in [economics_dependency.toml](../research/economics_dependency.toml). Its wheel
was inspected under ignored artifacts, never installed or executed locally.
Optional HPC installation is separate from the main environment and host wheel.
No native implementation, financial defaults, historical lookup table or source
figure is copied into the host distribution.

The official [ProFAST1.0.6 license](https://github.com/NatLabRockies/ProFAST/blob/main/LICENSE)
limits use to noncommercial internal research and restricts redistribution.
It was excluded from this adapter. No ProFAST engine was downloaded or installed.
pyH2A is an explicit provider choice, not a runtime fallback after ProFAST fails.

## Finite physical reporting

```python
from h2physics.adapters.hydrogen_economics import (
    PhysicalCostProjection, ReportingWindow,
)

window = ReportingWindow(
    trace.initial.time_s, trace.final.time_s, trace.evidence.clock_id,
    "explicit-window-evidence", "generated_h2_kg",
)
projection = PhysicalCostProjection.from_pv_electrolysis(
    trace, window, hydrogen_id="hydrogen",
)
```

The window must match the entire original trace's exact seconds, clock and
contiguous original step/state boundaries. There is no implicit cropping,
resampling, extrapolation or daily-to-annual conversion. H2 molecular identity
and molar mass must match the actual inventory and stack basis. The projection
retains the actual trace and fingerprints the reported quantities/identities;
`require_current()` rejects subsequent correspondence changes. This is a
reporting audit, not a replay proving that a caller's trace came from an
unmodified physical solver. Upstream PV/electrolysis remains unverified.

`PVSourceAdapter` performs the actual PV-specific audit. It reads the original
native IV/scaled-IV caches, native PV system definition, original steps,
conversion arrays, source definitions, public caloric bounds and callable/code
identities before and after the reporting operation. Replacing or mutating
these bound objects/caches invalidates the projection. The PV owner does not
yet issue an original-result seal: this structural audit cannot authenticate an
already fabricated pre-bind trace or arbitrary hidden callback state, and it
does not replay the EOS/current/physical model. Its `verification_kind` states
that limitation. [The MEC adapter](MICROBIAL_ECONOMICS.md) uses the same public
contract with its producer-issued original-result verification hook.

The projection exposes generated H2, initial/final receiver H2 stocks and stock
increase separately. It reads actual step electricity, PV electricity, signed
stack rejection and receiver heat. Gross input/rejection sums preserve separate
positive/negative step directions rather than netting away utility obligations.
Source `extent_mol_h2` becomes kg through the declared actual molar mass; the
reported H2 stock change is checked against generated extent. Initial stock is
never called production.

There is no product sale/export ledger in the current PV owner:
`harvested_h2_kg`, `sold_h2_kg` and legacy `exported_sale_h2_kg` stay `None`.
Required external pressure work remains its
actual unresolved value, rather than zero. Missing full-plant energy closure,
thermal utility availability and water/O2 vessel dynamics are explicit gaps.
The adapter predicts no additional generator, grid import/export, fuel use,
compression, water treatment, auxiliary load or product separator.

`UtilityTariff` supplies explicit USD/J, monetary base year, source, billing
boundary and origin. `projection.price_window(tariffs)` makes finite amount ×
price line items and retains each quote; it does not fetch current prices.
Every billable source boundary declares original transfer-component identities.
Billing both PV generation and the same direct-DC stack energy is rejected,
as are canonical/legacy aliases and a gross heat aggregate plus one of its
component duties. Caller quote labels cannot remove that overlap.
Fuel or other unobserved utility quantities are not manufactured. Missing tariff
coverage does not mean free utility: annual cost-scope evidence must identify
what is included independently. Tariffs are nonnegative charges; supplier
markup, credit, GHG factor, carbon price, exchange rate and heat sale are not
inferred.

## Explicit annual basis and finance inputs

`AnnualFinancialBasis` is mandatory before native LCOH. It declares USD/base
year, annual time convention, annual generated and gate-product kg, nonproduct
H2 removal, initial/final annual H2 stock, grade/absolute product pressure,
product-gate evidence, capacity-factor meaning and long-term repetition scope.
The constant repeated normal-year bridge requires closed initial/final annual
H2 stocks and explicit generated = gate-product + nonproduct reconciliation;
startup inventory cannot fund product every year. Native startup financial
fractions are separate assumptions and do not create a physical startup process.

Two annual input modes are admitted:

- `independent_annual_inputs`: independently supported annual quantities and
  inventory/gate evidence; the finite window is retained context and is not scaled.
- `explicit_window_repetition`: caller-supplied positive multiplicity, annual
  duration, generated kg and inventory/gate reconciliation. Multiplicity must
  match both the declared window duration and annual physical generated kg.
  Priced window utility × that same explicit factor plus separately declared
  additional annual variable cost must equal the complete native annual variable
  cost input. No factor is derived from the trace duration or a capacity factor.

Every physical gap requires named `unresolved_cost_resolutions` evidence. Those
caller declarations support the economic scenario; they do not turn unavailable
pressure work, thermal utility or product sales into measured physical closure.
The selected window role remains labelled generated, stock increase, harvest or
sale. A selected role must actually be available from the source. Explicit
repetitions match generated/stock-change mass to annual generated mass and
harvest/sale mass to the independently declared annual gate mass. Stock change
is accepted as generated mass only when the actual source also reports equal
generation. The current PV/MEC sources have no harvest/sale ledger; only explicit
annual gate evidence supplies the native denominator.

`AnnualFinancialInputs` requires all21 native financial fields with a per-field
evidence mapping, ordered construction fractions, capital/fixed/variable annual
costs, additional annual variable cost, complete replacement schedule and named
capital/utility/native-lookup scope. No packaged finance default is loaded.
Financial rates are decimal fractions, monetary quantities are USD at the
declared base year, replacement amounts cover construction plus operating years,
and unsupported debt/depreciation labels fail. This restricted bridge admits
the native Constant debt/MACRS path and nonnegative rates/charges only.

The native API can silently choose nearest historical cost-index years and
MACRS lengths. The bridge rejects that substitution: ref/basis/capital-cost
years must all equal the supplied monetary base year and be actually present
in all four native index resources; depreciation length must be an actual
MACRS header. This restricts the current cost-index envelope rather than
pretending to provide today's costs. Explicit future startup year/inflation
remains a financial scenario assumption. Capacity factor is metadata with
explicit evidence or an explicit not-applicable declaration; it is not applied
again to already annual production.

## Native call and retained results

Only `NativeHydrogenEconomics.from_installed()` performs the optional native
import. It checks version and exact reviewed package/resource tree. Actual
module/class/function bindings and source hashes are checked again around the
financial call. There is no installation, path mutation or provider substitution.

`evaluate_hydrogen_economics(projection, annual_basis, inputs, native=provider,
window_cost=priced_window)` revalidates inputs and creates a complete direct
Python dict for the actual `Discounted_Cash_Flow` constructor. String/Markdown
input and plugins are not used, so native `Defaults.md` merging cannot insert
assumptions. Native `check_processing=False` is deliberate: its optional marker
check targets plugin-created intermediate tables, while the host provides an
exact complete schema of terminal annual inputs and validates every field.
Native computational diagnostics remain captured; a native `Warning:` rejects
the result rather than becoming a successful cost.

The result retains native LCOH (`h2_cost`, USD/kg in reference-year dollars),
original native object, native NPV dictionary/contributions, copied read-only
annual arrays, original direct input dictionary, finite projection, annual
basis, quotes and complete input fingerprint. The denominator label preserves
native `Output per Year at Gate`, `annual_sales`/startup-revenue and discounted
`h2_sales` semantics; it does not relabel receiver stock as observed sales.

The native `cash_flow()` return is the native NPV of a cumulative cash-flow
sequence, not a raw annual cash-flow array or the zero-NPV residual. The opaque
original return is labelled `native_cash_flow_return` and retained as such.
Available original annual expense/income/tax arrays and native object remain
accessible. The host does not reconstruct a missing cash-flow series by copying
the financial equations. Raw native objects/dictionaries remain inspectable and
mutable; copied annual arrays are isolated from caller aliases.

`HydrogenEconomicsError` retains the original cause, attempted native object
(allocated before constructor execution), direct inputs, stdout, annual/physical
bases, priced window and native provider. Nonfinite results, native warnings,
changed source/input correspondence or mismatched annual array grids fail.
No guessed cost or alternate finance engine replaces a failed native call.
`SourceAuditError` separately preserves the actual source, source adapter,
window, cached snapshot when available and original source-owner exception.
All physical admission is repeated around the native financial call. The
binding is a correspondence guard, not a concurrency lock or experimental
qualification of opaque callbacks/native engines.

## Deferred validation

[The example](../examples/hydrogen_economics.py) reuses the existing actual
native PV/electrolysis example, then applies original synthetic quote/finance/
repetition assumptions. It has not run. Its hypothetical inter-window feeds,
product takeoff, grade and unresolved-cost allowances are scenario declarations,
not measured boundaries or vendor quotations.

[Seven metadata-only cases](../validation/cases/hydrogen_economics.py) use profile
`hydrogen-economics`: native-direct equality, finite tariff-to-native linkage,
independent zero-discount finite accounting, negative annual/window/index guards
and actual native overflow/failure retention. Two additional cases cover public
SI/role admission, old PV factory/tariff compatibility, overlapping alias billing
and actual source/native/cache/proof mutation. The future explicit environment
needs reviewed pyH2A0.0a8 plus the existing pvlib/CoolProp dependencies of the
physical example. No case discovery, scientific entrypoint or example was
executed locally. See [the development record](../research/hydrogen_economics_development.md).

## PV producer result boundary

The PV source binding calls the physical producer's `trace.require_current()`
before and after snapshot construction. This rejects reconstructed traces and
changed retained native caches without replaying the PV/electrolysis model.
It remains a provenance and cache-correspondence check, not scientific
validation or proof of hidden callback state.


## Result ownership and currentness

HydrogenEconomicsResult is issued only by evaluate_hydrogen_economics() after the
reviewed native provider returns. The result binds its physical projection, annual
basis, financial inputs, window-cost receipt, native object/provider, discounted
outputs, and copied annual arrays. Call require_current() before consuming a retained
result; it checks source/provider freshness, input fingerprint, native LCOH/NPV and
annual-output integrity. Direct construction, dataclass replacement, or post-issuance
mutation is rejected by the deferred economics-native-direct contract. This guards
result provenance; it does not validate the assumed financial scenario or provide
investment advice.
