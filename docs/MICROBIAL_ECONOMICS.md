# MEC ledger to native economics

**Status: implemented_unverified.** The bridge and six deferred HPC cases are
written. No scientific/native import, model, example, case discovery, test,
replay, installation or benchmark was run locally. This is a coupling level
within existing models. It adds no catalog family or validation claim.

`h2physics.adapters.microbial_economics` takes the actual `MicrobialCellTrace`
through the public common physical-economics contract and calls the existing
native pyH2A owner. No microbial/current, reaction, thermal, tariff, annualization,
discount, tax or depreciation algorithm is copied or replaced. Read
[MICROBIAL_CELL.md](MICROBIAL_CELL.md) and
[HYDROGEN_ECONOMICS.md](HYDROGEN_ECONOMICS.md) for their separate domains.

## Actual source and finite reporting

```python
from h2physics.adapters.physical_economics import ReportingWindow
from h2physics.adapters.microbial_economics import MicrobialCostProjection

window = ReportingWindow(
    trace.steps[0].stage.start_s, trace.steps[-1].stage.end_s,
    trace.evidence.clock_id, "explicit-complete-MEC-window", "generated_h2_kg",
)
projection = MicrobialCostProjection.from_microbial_cell(
    trace, window, hydrogen_id="hydrogen",
)
```

`MicrobialCostProjection` is a named factory returning the actual common
`PhysicalCostProjection`. It is not a PV-annotated subclass. The equivalent
public form uses `PhysicalCostProjection.from_source(trace,
MicrobialSourceAdapter(), window, hydrogen_id=...)`. No fake PV trace, receiver
or physical solver is constructed and no private economics helper is imported.

The window must match the source's entire physical seconds and original clock.
The actual source, original initial/final inventories, step/rate/kernel/native
point/root identities and phase/electrode/caloric/H2 molar-mass references are
retained. Canonical quantities have public SI and product/billing-role records.
Portable snapshots preserve reported native arrays, trials, conversions,
voltage/current, heat/work and biological source metadata without recomputation.

Every source audit calls `trace.require_current()` before and after reading it.
This delegates to the actual `FiniteMicrobialCell.verify_result(trace)` and
requires the exact producer-issued original trace. The retained geometry, owner,
admission, current-root/tolerance/kinetic/caloric bindings, content hash, owner
configuration hash and native-state hash remain bound. Copies/replacements of
the result, altered root caches and changed retained electrode state fail the
producer seal. The common binding additionally guards its original audit
callable/code, cache and identity records before and after native finance.

This verification reads stored evidence; it does not call microbial kinetics,
native electrode rates, root solving, caloric queries or the finite kernel.
Current native scratch state must still match issuance. Reusing the native
objects for another physical operation may stale a valid old trace. Opaque
hidden callback state and physical experimental accuracy are outside this seal;
upstream `implemented_unverified` is unchanged. `projection.verification_kind`
preserves that scope rather than labelling it a physical replay.

The projection separates:

- `generated_h2_kg`: source-generated mol converted by the actual H2 molar mass;
- `initial_h2_stock_kg`, `final_h2_stock_kg`, `h2_stock_increase_kg`, plus
  explicit legacy `cell_*` aliases: finite batch stocks;
- `harvested_h2_kg=None`, `sold_h2_kg=None`, `exported_sale_h2_kg=None`:
  no resolved harvest or observed sale;
- `transferred_electrons_mol` and `biomass_generated_mol`: circuit electron
  transfer and declared biomass formula-unit amount;
- `electrical_work_into_j`, gross `required_heat_input_j` and
  `required_heat_rejection_j`, and `signed_required_heat_j`: actual applied
  external work and required isothermal heat duties.

Only explicitly generated H2 or the checked equal batch-stock increase may be
selected here. Receiver-stock, harvest and sale bases reject. No gas-reference
volume, harvest efficiency, feed conversion, wastewater credit, substrate price,
biomass disposal fee, markup, GHG factor or current grid price is inferred.

## Shared pricing and annual finance

The common public `price_projection_window` implements finite amount × USD/J
once. A `UtilityTariff` needs actual quantity, currency, base year, source,
billing boundary and origin. Canonical electrical/heating/rejection keys are
preferred; legacy `stack_electricity_j`, `stack_heat_input_j` and
`stack_heat_rejection_j` remain explicit MEC aliases. Transfer-component
identities prevent billing a canonical key and its alias twice even when quote
labels differ. Required cooling is a charge magnitude, not an inferred heat sale.
Missing or unavailable utilities reject pricing; they do not become free.

The original annual owner requires explicit representativeness, annual seconds,
generated and gate kg, closed normal-year H2 stocks, nonproduct output, grade,
absolute product pressure, startup assumptions and cost-scope evidence. A batch
is never automatically repeated for a year. Inter-window feeds/resets and annual
gate assumptions do not create observed harvest/sale. Named unresolved costs
include feed/nutrients/biomass handling, anode/activity support, product
conditioning/pressure work, thermal utility availability and plant auxiliaries.

`evaluate_microbial_economics(projection, basis, inputs, native=provider,
window_cost=priced_window)` calls the original `evaluate_hydrogen_economics` and
returns its original `HydrogenEconomicsResult`. Native pyH2A0.0a8 retains DCF,
tax/depreciation, cash-flow/NPV and native denominator ownership. Full-dict
financial input, exact historical lookup-year/MACRS admission, all financial
evidence, annual arrays and actual native objects remain under that owner.
MIT code and CC BY4.0 noncode rights are recorded in the unchanged
[dependency receipt](../research/economics_dependency.toml).

`MicrobialEconomicsError` preserves the original cause, actual source/projection,
annual inputs and economic error. Attempted native object, input and stdout
remain accessible. A late source audit also retains an already returned actual
financial result. Common `SourceAuditError` retains a failing source hook and
its original exception. Neither layer substitutes prices, quantities or engines.

## Deferred execution

[The example](../examples/microbial_economics.py) reuses the original actual
Cantera MEC fixture only when called later, then applies authored synthetic
tariffs, annual resets, grade and financial inputs. No price, culture, mechanism
or annual representativeness is qualified by it.
[Six metadata-only cases](../validation/cases/microbial_economics.py) use profile
`microbial-economics`: owner/native identity, finite tariff linkage,
window/reference/annual guards, original financial failure retention, public
projection/producer/geometry admission and root-cache/electrode-state mutation.
The explicit future environment needs reviewed Cantera3.2 and pyH2A0.0a8.
The MEC path requires no PV or ADM1 engine. No case has been discovered or run
locally. The [development record](../research/microbial_economics_development.md)
records the implemented common seam and remaining physical limits.
