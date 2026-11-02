# Hydrogen economics implementation checkpoint

Status: **implemented_unverified**, 2026-10-28. The user prioritized parallel
coding and deferred scientific validation until Nurion is connected. This lane
performed static source/API/license inspection, artifact checksums, AST syntax
and Ruff only. No financial/PV calculation, native package import/installation,
pytest, replay, example, case discovery or benchmark was executed. Planned
assertions and original synthetic arithmetic are not observed results.

## Provider decision and provenance

The official [ProFAST release](https://github.com/NatLabRockies/ProFAST/releases)
and PyPI identify1.0.6. Its actual
[license](https://github.com/NatLabRockies/ProFAST/blob/main/LICENSE) restricts
use to noncommercial internal research and restricts redistribution. No ProFAST
engine artifact was downloaded/installed. It is excluded from this native lane;
the host does not silently substitute engines at runtime.

[pyH2A](https://github.com/jschneidewind/pyH2A), Jacob Schneidewind, is an
independent H2A-based hydrogen cost framework with direct Python-dict input.
The current [PyPI metadata](https://pypi.org/pypi/pyH2A/json) resolves0.0a8.
The actual wheel contains MIT code license and separate CC BY4.0 noncode
license; its METADATA says License UNKNOWN but includes the actual license
files and MIT classifier. The actual license files, not that incomplete label,
were inspected. The
[primary DCF API](https://pyh2a.readthedocs.io/en/latest/pyH2A/discounted_cash_flow.html)
documents direct dict input and inspectable native results. The underlying
[DOE H2A framework](https://www.hydrogen.energy.gov/program-areas/systems-analysis/h2a-analysis)
provides methodology context, not this project's costs, utilization or market
forecast.

The1,041,802-byte wheel was acquired only into ignored
`artifacts/economics_dependency_review/`, SHA256
`e7ec4e860bfeaa7625710e128ec338f017f7243c1f884d74570643f85a4048d0`.
Its73 archive members total2,104,158 uncompressed bytes. Only bounded read-only
archive/source/metadata inspection occurred; no included program was executed.
The66-file package tree (relative names plus original bytes, case-sensitive
ordering, excluding future bytecode caches) hashes to
`a69e8c5a3e89dbd6ee6ff1f5477c0707560b6bf95d2d3b04171382dcfd078d84`.
The public receipt `research/economics_dependency.toml` records exact native
source, licenses and used lookup checksums. No native source, defaults,
historical financial table, figure or source prose is copied into host code.
The optional package is not bundled or added to the main environment.
This is a pre-release published API; compatibility with the selected current
HPC Python/NumPy/SciPy stack remains unexecuted and must pass there. Package
metadata availability does not establish maintained-platform compatibility.

Code review found concrete native boundaries before implementation:

- String input merges native Defaults.md; direct dict input does not. The host
  assembles a complete terminal dict and accepts no arbitrary native plugin.
- Native historical index and MACRS helpers select nearest values. The host
  requires exact monetary-year membership and an actual depreciation header.
  Ref/basis/current capital years must match the explicit monetary year, so no
  hidden cross-year cost adjustment is used. The four source index datasets
  have different finite historical coverage; they do not supply current costs.
- Native replacement processing zeroes construction-year entries. The host
  refuses nonzero requested replacements in those positions.
- Native debt/depreciation labels do not select general alternative laws.
  The bridge admits only its actual Constant/MACRS implementation.
- Native cash_flow prints an NPV diagnostic rather than raising and returns
  NPV of cumulative cash flow, not an annual cash-flow vector. The host retains
  the original return/annual native arrays, rejects computational Warning:
  diagnostics and does not recreate financial equations to fill this API gap.
- The native optional processing-marker check expects plugin-created tables.
  Complete host terminal inputs use check_processing=False; the host fixed
  schema and explicit evidence validate all inputs instead. This does not
  disable native financial calculations or suppress captured diagnostics.

## Actual physical integration and ownership

The adapter directly reads existing `PVElectrolysisTrace` steps, with exact
source/state continuity, H2 molar-mass basis and a matched ReportingWindow.
Actual generated extent, initial/final receiver inventories, PV/stack energy,
signed heat and gross utility directions are retained. Native PV, stack,
caloric and gas ownership remains in the existing source model. No extra
power-cycle, electrolyser, fuel or thermal solver is introduced here.

`PhysicalCostProjection` now uses the public source-neutral API in
`adapters/physical_economics.py`. `PhysicalSourceAdapter` returns actual
`SourceSnapshot` content, original pointers, registered SI quantities and
`QuantityBoundary` records. A factory-issued `ValidatedSourceBinding` audits
the actual owner callback and binds its owner/function/code, cached metadata,
actual source/window/material and original identities. The finance owner checks
the actual binding and cache, rather than relying on an arbitrary protocol
object's own `require_current` implementation. The common projection Protocol,
registry, stable snapshot/hash, finite-sum and callable-identity hooks are public.

The PV source factory and old imports remain available, including explicit
legacy tariff names. A six-argument PV constructor requires a fresh actual
source audit and exact supplied-cache correspondence. `PVSourceAdapter` reads
the original native IV/scaled-IV cache and PV system definition, step/conversion
metadata/arrays, caloric bounds and retained callable/code bindings. Source,
cache/proof and native-system changes are checked on each subsequent audit.
It does not prove upstream solver authenticity
by rerunning it. The current source remains implemented_unverified; its
unresolved external pressure work, missing full-plant energy/auxiliary closure,
thermal utility availability and water/O2 vessel dynamics remain explicit.
There is no observed sale/export output, so that quantity remains None.
Neither None nor absence of a tariff is converted to zero physical cost.

Finite `UtilityTariff` billing is only explicit quantity×USD/J with source/year/
boundary/origin. Duplicate pricing of the same direct PV-to-stack DC transfer
is rejected through explicit source transfer-component identities, including
canonical/legacy aliases and aggregate heat plus a component. Gross heat input
and rejection are summed by actual step sign;
the accounting does not net opposing utilities into a free boundary. No
implicit fuel, water charge, markup, GHG factor, carbon price, credit, heat
sale, exchange rate or current-price query exists.

The native annual bridge requires either independent annual inputs or explicit
window multiplicity, annual duration and generated kg consistency. With explicit
repetition, priced window utility×that same factor plus an independently
declared additional annual variable cost must equal the supplied native annual
variable-cost total. Annual factor is never inferred from a60s/day trajectory,
weather or capacity factor. All native financial scalars have per-field
evidence; scalar cost/annualization domains are revalidated before invocation.

Annual initial/final H2 stocks must close for the constant repeated normal year;
generated H2 equals gate production plus nonproduct removal. Startup stock
therefore cannot silently fund repeated annual product. Grade, absolute gate
pressure, product boundary, inventory reconciliation and long-term repetition
remain explicit evidence. The native startup fractions affect native financial
annual_sales/cost arrays; no physical startup or finite downstream sales engine
is inferred. Financial scope declarations resolving physical gaps are scenario
assumptions, not experimental closure or an independent plant qualification.

The host preserves native `h2_cost`, NPV/contribution dictionaries, actual DCF
object, native annual arrays and opaque cash_flow return. The complete native
input, annual evidence/financial fields, physical identity and tariff records
are fingerprinted. Native source/version/actual module/class/function bindings
are checked around the call. A failed constructor still leaves the allocated
actual native object for inspection; cause, raw inputs, stdout and physical/
annual/pricing bases remain on HydrogenEconomicsError. There is no finance
fallback and no financial formula is duplicated in this module.

## Deferred execution plan

`validation.cases.hydrogen_economics:cases` contains seven metadata-only
ValidationCase records using profile `hydrogen-economics`. Imports/catalog
construction do not instantiate native engines or run a physical calculation.
The explicit later HPC environment must include the reviewed pyH2A0.0a8
artifact/dependencies and existing reviewed pvlib/CoolProp environment needed
by the reused physical example. Actual interpreter/queue/account/resource/
revision/plan hashes are parent-owned cluster inputs, not inferred here.

| Deferred identifier | Intended acceptance |
|---|---|
| economics-native-direct | Actual native object identity and exact full-dict DCF result correspondence; original physical trace, unavailable sales and isolated annual arrays retained |
| economics-finite-link | Actual finite electrical tariff reaches explicit annual native variable cost and a larger tariff increases native LCOH; startup stock stays separate |
| economics-undiscounted | Independent finite lifetime cost/production accounting agrees for the specially authored zero-discount/tax/inflation/debt fixture |
| economics-negative | Clock/window mismatch, missing cost scope, annual inventory drawdown, inconsistent annual utility linkage, duplicate DC billing and absent exact native lookup year reject |
| economics-failure-retention | An authored finite-input overflow retains original cause, direct input and actual partially/completely attempted native object; no nonfinite result admitted |
| economics-public-projection | Public SI/product/boundary admission, preserved original PV factory/tariff behavior, alias-overlap rejection and no duck-typed or unavailable-harvest promotion |
| economics-source-cache | Mutated actual native IV cache, cached source proof and actual native PV system definition reject without changing the source to repair them |

The zero-discount finite oracle is a small independent verification case, not
a second general finance implementation. The example's2010 USD/J quote,
capital/costs and525600 explicit repetitions of a60s pattern are original
synthetic inputs. The hypothetical inter-window reset/product takeoff, grade
and additional31USD/year scope do not establish real missing source physics.
No value is a current price, vendor quotation, investment recommendation or
reported financial performance. Future HPC acceptance must retain actual
software/native hashes, source clock/annual evidence, metrics and all failures.

The shared refactor also serves the original MEC economics adapter through its
actual producer verification hook; its six deferred cases are described in
`research/microbial_economics_development.md`. These two profiles contain13
deferred definitions, four added in this refactor; none was discovered or run.
Common snapshots explicitly label raw nonfinite diagnostics, reject nonfinite
physical quantities and impose item/depth/array-byte budgets. Source hook
failures retain the original source, adapter, cache and cause in SourceAuditError.
All source admission repeats before/after native finance without financial or
physical replay.

All owned files remain implemented_unverified after static review. This lane
changed only the two owned economic sources/manuals/reports/examples/case files
and the new shared helper. Native installation, catalogs, requirements and other
agents' sources were not changed. No family/test-pass/experimental-validation
increment is claimed; the parent integrates metadata and deferred cases.
