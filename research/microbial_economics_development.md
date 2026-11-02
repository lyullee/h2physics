# Microbial economics public-contract checkpoint

Status on 2026-10-28: **implemented_unverified**. This coupling remains within
existing models. The user deferred scientific/native execution until Nurion:
no scientific module/native import, case discovery, model/example/test/replay,
benchmark, installation or job was run. Source/API inspection and static
AST/Ruff/LF checks are the only local checks. Deferred assertions are not results.

## Original owners and resolved API seam

The actual finite MEC retains native Cantera cathode points, shared reaction/
thermochemical-kernel conversions, molar material/electron ledgers and electrical/
isothermal-heat duties. Its physical coefficients, biological/thermochemical
references and isothermal boundaries remain unverified. Native pyH2A0.0a8
continues to own DCF, depreciation, tax, finance, native startup adjustments,
NPV/cash-flow and native gate-output LCOH. No physical or financial law is copied.

The earlier temporary PV subclass/private-helper seam has been replaced:

- Public `PhysicalSourceAdapter`, `SourceSnapshot`, `ValidatedSourceBinding` and
  `PhysicalEconomicProjection` live in `adapters/physical_economics.py`.
- Public `QUANTITY_REGISTRY`, `QuantityBoundary`, `finite_sum`, `stable_snapshot`,
  `snapshot_sha256` and `callable_identity` define explicit SI/boundary records
  and bounded portable content without an economics-owner private import.
- `MicrobialSourceAdapter` supplies actual source audit/content/pointer records.
  `MicrobialCostProjection.from_microbial_cell` returns the actual common
  `PhysicalCostProjection`; it is no longer a PV-annotated subclass.
- The finance owner independently requires the actual factory-issued binding
  and matching cache. A structurally matching duck object cannot bypass source
  admission by returning itself from a custom validation method.
- Old PV factory/import paths and explicit tariff aliases are preserved. The
  same finite tariff implementation handles both actual source types. Original
  pyH2A input schema, native years/MACRS rules, arrays and error path remain.

No fake PV source, native phase, receiver or physical object is constructed.
The common registry is a declared vocabulary, not evidence that every source
reports every quantity. Canonical work/heat keys replace temporary MEC stack
labels in the example; legacy aliases remain explicitly mapped to the same
transfer components. Alias or aggregate/component double billing rejects even
when quote source/billing labels differ. No absent utility becomes zero cost.

## Actual producer binding

The separately owned `microbial_cell.py` now exposes actual retained geometry,
owner and `MicrobialResultAdmission` on the original trace. The public
`trace.require_current()` delegates to the actual producer implementation and
returns that exact trace only. Admission retains geometry, tolerance/current-root
settings, evidence, kinetic/caloric/kernel references, original-trace weakref,
content SHA, owner-configuration SHA, native-state SHA and verification scope.
It is issued only after actual model completion and is not reissued by copy or
replace. Weak registrations do not make the owner retain abandoned traces.

Each economics source snapshot calls that public hook before and after reading
the original trace, binds actual owner/geometry/admission and audit function/code
identities, and records all three producer hashes and scope. It also retains
original inventory/step/rate/kernel/native point/root identities and reported
native arrays/trials/conversions, current/potential references, original H2
molar mass and phase/caloric definitions. Shared binding audits repeat around
the native financial call and reject cached proof/content/pointer changes.

Static contract comparison used final native-owner module SHA256
`99b44ca2b6d7e6f31067b7762b3736459a28c8303f9633ab0a111ab3fcc5f991`.
The economics lane did not edit that module. Verification reads stored native
state/definitions and cached result evidence; it does not invoke native electrode
rates/current, a root, microbial kinetics, caloric queries or the finite kernel.
Thus altered root diagnostics/electrode state or a replaced result reject
without rerunning science. This is a strict current-scratch-state seal: a later
use of shared native objects can stale a previously valid trace. Hidden mutable
callback state outside the producer's declared evidence, concurrent mutation
and independent physical accuracy are not established by the seal.

## Finite material, utility and annual boundaries

Generated H2, initial/final batch stock and stock increase are distinct kg roles.
The source has no resolved harvest or sale: `harvested_h2_kg`, `sold_h2_kg` and
legacy `exported_sale_h2_kg` remain None. Generated H2 or a source-checked equal
batch-stock increase may be selected; a downstream receiver/harvest/sale basis
rejects. Actual circuit electron mol and biomass formula-unit mol remain separate.
Applied electrical work is J at the component boundary, not automatically grid
purchase. Required signed isothermal heat and gross heating/rejection remain
separate; rejection is not heat-sale revenue. No gas-reference volume is invented.

Annual representation, seconds, gate product/grade/absolute pressure, initial/
final annual H2 inventory, nonproduct removal, startup fractions and cost scope
are explicit original finance-owner inputs. Normal-year stocks must close and
generated H2 must reconcile to gate plus nonproduct output. Independent annual
inputs stay independent; repetitions use only caller-supplied multiplicity and
consistent duration/selected mass/finite tariff linkage. A batch does not create
its own annual repetition or a product takeoff/reset process.

The unresolved-cost set preserves feed/nutrients/biomass handling, anode/activity
boundary support, harvest/sale, pressure/conditioning work, thermal utility and
plant auxiliaries. Caller cost-scope evidence is an economic scenario, not
experimental closure. No feed price, supplier markup, credit, GHG factor,
current price or harvest efficiency is fetched or assumed.

`evaluate_microbial_economics` returns the original `HydrogenEconomicsResult`.
The actual native object, original direct inputs/stdout, NPV and read-only copied
annual arrays keep original ownership/denominator labels. `SourceAuditError`
retains source, hook, cache when available and original owner exception.
`MicrobialEconomicsError` preserves the original exception chain and physical/
annual/pricing/native context, including an already returned actual financial
result when a late source check fails. There is no financial/provider fallback.

## Dependencies and deferred acceptance

No new dependency or license was introduced. Existing Cantera3.2 and pyH2A0.0a8
receipts apply. pyH2A MIT code and CC BY4.0 noncode rights remain in
[economics_dependency.toml](economics_dependency.toml), unchanged SHA256
`4d29ff759823e1c55a0e65d9a017d6239b2200ac045fd0cd96f4156218616138`.
The primary [pyH2A repository](https://github.com/jschneidewind/pyH2A) and
[native API](https://pyh2a.readthedocs.io/en/latest/pyH2A/discounted_cash_flow.html)
are the existing finance references. No source default, table, prose or fixture
was copied; the example reuses the original host MEC fixture.

Six metadata-only ValidationCases use profile `microbial-economics`:

| Case | Intended acceptance, unexecuted |
|---|---|
| mec-economics-owner | Original MEC/pyH2A pointers and unchanged financial owner result; unavailable harvest/sale |
| mec-economics-link | Actual finite applied work reaches explicit annual native cost via common tariffs |
| mec-economics-guards | Window/product/reference/scope guards and changed source caches reject |
| mec-economics-failure | Original failed native object/input/stdout/cause preserves the actual MEC source |
| mec-economics-public-projection | Actual common projection/geometry/producer hook and SI registry; pre-bind replaced trace rejects |
| mec-economics-producer-mutation | Altered original root cache and actual retained native electrode state reject |

Two definitions were added here; the hydrogen-economics profile adds two and
contains seven, giving13 deferred definitions across the two owned files and
four added by this shared-contract refactor. Neither cases() nor any entrypoint
was called. Native actual integration/failure/alias behavior is still unverified
until authorized cluster execution. The MEC path needs Cantera3.2/pyH2A0.0a8,
not PV or ADM1 execution; the PV profile additionally uses its original providers.

The synthetic example explicitly assumes a2s pattern repeated15768000 times,
31536000 annual seconds, inter-window feeds/resets, grade/gate assumptions,
USD2010 tariffs/capital and additional37USD/year scope. Those are not observed
harvest, measured annual stability, vendor quotes or a facility business case.
Parent-owned catalog/HPC plans/evidence reconciliation are updated separately.
