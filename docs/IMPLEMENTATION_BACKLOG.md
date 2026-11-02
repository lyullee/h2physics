# Implementation backlog and closure record — 2026-10-31

Current source status is maintained in [MODEL_CATALOG.md](MODEL_CATALOG.md),
current accepted and pending execution evidence in [PROGRESS.md](PROGRESS.md),
and active handoff constraints in [HANDOFF.md](HANDOFF.md). At this checkpoint
the catalog contains 82 families (19 implemented, 37 native-adapter-verified,
26 implemented-unverified). The dated entries below are implementation and gap
closure history; intermediate case/catalog totals and Nurion references in those
entries are historical snapshots. Hangang is the active target for later
verification. A coded feature or deferred contract is not a verified or
independently validated model.

The equipment-instrument gap for sampled response-parameter estimation now has
an isolated host API: `adapters.sensor_calibration` fits the first-order H2
concentration sensor time constant from caller-supplied aligned truth/indication
samples, preserving source IDs, clock, basis and units. It is not a full sensor
calibration, has no bundled field data, and does not estimate gain/bias/delay or
uncertainty. Two deferred synthetic contracts are registered in both the Hangang
and Nurion plans; the generated metadata inventory remains pending refresh.

The `facility_accident_consequence` adapter now runs an accepted source/dispersion
chain and passes the exact final handoff to the existing consequence evaluator,
retaining chain context on staged failure. It supplies orchestration only, not
receptor/exposure physics or consequence laws. Its deferred contract is in both
source plans and remains unexecuted.

The closed-charge Cantera engine segment now accepts a source-bound piston-face
heat-flux schedule, passes it into the native moving wall, inserts schedule knots
into requested output times, and retains integrated heat in the sampled first-law
residual. This adds an explicit boundary, not a calibrated wall-transfer model;
its deferred case is unexecuted.

Latest local additions have improved two open receiving seams without closing them:
Request034 now has an exact scheduled mass/enthalpy transfer ledger around the
existing closed-charge engine, and Request032 now has a freshness-checked audit for
provider-issued mixture snapshots from an external native integrator. The first
still lacks valves, cylinder coupling and full-cycle closure; the second still lacks
changing-composition flash/integration and phase-event localization. Their new cases
are deferred to HPC and source-plan metadata has not yet been refreshed.
Request012 now also has a host-side HyRAM plug-to-Gaussian transition auditor for
caller-supplied same-run radial snapshots. It checks flux ledgers but cannot create
trusted native snapshots or repair the source mismatch. The current expected deferred
Request032 now also has a bounded fixed-composition two-phase V/U flash using the
existing CoolProp PQ packet owner. It resolves one equilibrium state but does not
integrate changing inventories, ports or phase events. Request034 now includes a
Cantera prescribed-flow open-cylinder interval using fixed source states and native
mass-flow controllers; it does not model valves or close a full cycle. The expected
deferred plan is 312 cases across 52 profiles and 82 modules; refresh the generated
inventory on the pinned Python 3.12 target before campaign generation.

The BAM hydrogen jet-fire archive (Zenodo DOI 10.5281/zenodo.21026781) is now
catalogued and acquired with verified publisher MD5 and local SHA-256. It adds
measured reference-plate thermocouple and hydrogen-flow traces as a candidate
for thermal-target work. `load_bam_jet_fire_text()` now verifies the Zenodo
record and file checksums, retains the raw cell tokens and unit-bearing channel
labels, and is covered by a synthetic parser case deferred to Nurion. The actual
experiment schema and observation mapping have not been qualified for a thermal
model comparison.

The facility-monitoring API now includes a closed-form first-order concentration-sensor
response for piecewise-linear sampled input and a source-bound direct path into the
existing sampled alarm. The response time constant, initial indication, source origin,
operating mode, episode and evidence remain caller supplied. This adds sensor lag only; chemistry, cross-sensitivity,
noise, communication delay, detector siting/reliability and safety qualification
remain open. Its synthetic accepted-path and lineage contract is deferred to Nurion.

Current data-acquisition plumbing fixes: bare Dryad CC0 grant URLs are resolved
through the same exact license locator allowlist as named grants, and the inventory
writer now filters discovery records from acquisition receipts. The O2-chamber
dataset has two public file records and CC0 rights, but both attachment downloads
returned HTTP 401 on 2026-10-30; zero bytes were acquired. The inventory was
regenerated with that failure recorded. Its in-vitro oxygen-transfer data is not
hydrogen-facility validation evidence.

`h2physics.data.inspect_hdf5_metadata()` now inventories HDF5 groups, datasets,
attributes, and soft/external links without reading array values or assigning units.
The optional `data` dependencies provide h5py. A synthetic metadata-only Nurion
contract is added to `source-data-ingestion`; parsing the acquired engine figure
files into immutable observations still needs schema-specific review. No source
arrays or physics are inferred by this inventory API. `HDF5MetadataInventory.require_current()`
rechecks the original regular-file size and SHA-256 before a retained structural
snapshot is reused; this establishes local byte identity only.

Preferred dispersion admission also rejects truthy/falsy non-bool values for
`require_accepted` at both the scenario facade and direct route functions, before
provider execution. The existing `selection-preferred-dispersion` contract covers
those wrong-type inputs. HyRAM gas/flame, jet projection, SLABx-LH2 run and snapshot
entrypoints enforce the same flag contract, including explicit flame-diagnostic
overrides; their direct inputs are covered by the same deferred contract.

Fermentation and AB2 hydride-tank observation blocks now require reader issuance
and carry content seals so reconstructed public block instances and post-load
mutation cannot inherit source lineage. Their dedicated deferred Nurion cases are
`fermentation-block-issuer-integrity` and `hydride-tank-block-issuer-integrity`;
they exercise forged construction, replacement/mutation rejection, and source-row/
raw-cell alignment against synthetic inputs. No source workbook is part of the
repository. Both cases require the data extra solely for the existing readers'
openpyxl execution path.

The LH2DT reliquefier product boundary now requires issued, current native
steady and dynamic results before collection. This closes result ownership and
staleness gaps; it does not add or qualify reliquefaction physics. The existing
deferred product-guards contract was extended, with no case-count change.

Several additional local API gaps were closed in this continuation. Receipt replay
now preflights selected per-file and aggregate byte budgets and validates rights,
attachment records and hashes before creating its destination or making requests.
Pump and valve command objects reject unknown runtime mode labels at construction.
Facility-operation reports can expose piecewise-linear trapezoidal integrals of
sampled mass/energy residuals; these remain reporting diagnostics rather than
native cumulative inventory or facility closure. The public `GasEnvelope` PT guard
now rejects booleans, nonfinite and nonpositive coordinates before checking its
qualified bounds. Buried-pipeline data tables and column projections can now be
issued only by the checksum-validating loader and their original table, preventing
detached publisher digests from being resealed through direct construction or
dataclass replacement. Hydrogen-channel source-bound cases are also loader-issued
after publisher-byte checks; qualified-table reports are issued only by the native
reference/table comparison; and facility gas chains reject any HyRAM source
projection that was explicitly rejected, even if outer budgets are looser.
Cache audits and receipt replay now reject symbolic-link/junction attachment and
dataset identity paths instead of hashing files or sibling versions through an
alias. The deferred rights/acquisition integrity case covers these paths without
network access.
The bounded mixture density/internal-energy inverse also requires a native
one-shot issuance after solve and residual checks pass.
Native CoolProp phase-partition packets and successful PH inverse summaries now
require one-use issuance and recheck provider, state, phase, root and residual
lineage before accounting. Direct construction, cloning and post-issuance edits are
covered by the deferred gas-composition contract; Request032's missing
changing-composition flash remains native-engine work.
The geological surface-excess provider now verifies its interpolation arrays
against the loader-issued original rows, and the SLABx pool-to-field wrapper
preserves aggregate acceptance including the empty-series `None` state. Adsorption
vessel snapshots and inverse-pressure receipts are solver-issued, and scenario graph
results now revalidate graph-issued nodes and outputs before exposing results.
Finite-speed pump/valve, relief, and transient-flowing-exchanger traces require
issuance from their native run owners. Conditional/facility risk results reject reused
success issuers and require source/frequency evidence to resolve in the native
risk context. CORA
electrode observation values/masks reconstruct from source tokens and the typed
series/dataset receipts are issued only by the workbook reader.
Deferred Nurion contracts were added or extended for each change, but none was
executed. These changes do not close the receiving-native
physics gaps listed below.

Preferred-dispersion scenarios now fingerprint nested mapping/list/array solver
options at construction and reject changes before invoking HyRAM or SLABx-LH2.
This closes a request-integrity seam while leaving native domain objects and
callbacks caller-owned. The existing facility accident-chain Nurion contract now
covers the nested-option mutation boundary; it remains unexecuted.

Facility consequence receipts now bind evaluator code and ordinary captured
configuration before and after callback execution, including partial arguments and
bound receiver state. A callback that changes its configuration while producing a
result is rejected before receipt issuance; later changes also invalidate it. Opaque
external/global dependencies remain caller evidence. The facility-chain contract
covers both boundaries and remains unexecuted.

The microbial current-observation block is now issued only by its pinned workbook
reader. Its source identity, measured origins, worksheet row labels, cached-cell
values and finite masks are checked together; direct construction, cloning with a
changed digest, or changed observation values are covered by the existing deferred
source-integrity case. This preserves the publisher's reported signal only and
does not infer its clock alignment, device role, or hydrogen yield.

KIT counterflow measurement rows, profiles, optical series and spectra now require
one-use issuance by their checksum-reading workbooks. Direct construction and
dataclass replacement cannot assign the publisher file identity to caller values.
The existing counterflow data-ingest contract covers those receipt boundaries; it
remains deferred and supplies no flame-model validation.

Finite solid-reaction traces are now issued only by `FiniteSolidReactionReactor.run()`;
the existing solid-binding contract checks that a copied trace cannot retain run
issuance. The native reaction and caloric method remain unchanged.

The FDS obstacle-dispersion runner now issues its accepted/rejected result only
from the actual native run. The result binds the captured process, artifact index,
parsed tables, summary arrays and residuals against copying or post-capture edits.
Currentness checks rehash the complete artifact tree and reject changed, added,
removed or symbolic-link files. The existing deferred obstacle cases cover this
receipt contract; it adds no CFD physics.

`FiniteSpeedPump.run()` now advances each sampled interval with its left-edge
command, preventing a ramp target from affecting speed before the command's exact
start time. The existing deferred finite-ramp case covers an abrupt ramp-up to
ramp-down transition at the boundary.

OEDI fatigue source records can now be issued only by the checksum-verifying
workbook loader; public constructor metadata alone cannot bind fabricated measured
values to the source file. Direct-construction and altered-value rejection are in
the existing deferred OEDI provenance case.

`HydrideCompressorTrace` now rechecks its retained native samples, stage points and
ledgers before exposing summary values. The existing deferred compressor contract
includes altered-native-array rejection. This is result integrity, not apparatus or
alloy qualification.

`JetRadiationField` is now evaluator-issued with a per-result token; direct
construction and dataclass cloning cannot manufacture a changed radiation result
under an admitted HyRAM flame. The existing jet-radiation integrity contract now
records this guard and remains deferred.

Same-clock detector voting now combines individually latched hydrogen alarm traces
with an explicit k-of-n rule. The original detector/evidence identities and sampled
vote transitions are retained for the existing scheduled protection replay. Its
contract is added to the existing deferred `facility-concentration-alarm` case.
No independence, common-cause or reliability model is inferred.

`TableQualification.meets_speedup_target()` now lets a caller compare the retained
CoolProp-table benchmark ratio against an explicit minimum. This is only a decision
over the recorded timing summary; it neither changes EOS error qualification nor
establishes repeated-run performance. Its contract extends the existing deferred
table case.

Source-only adsorption API closure (2026-10-30): `AdsorptionState` now rejects a
numeric propagated standard-uncertainty vector unless its semantics explicitly
declare covariance propagation and carry evidence identities. The
`adsorption-vessel-uncertainty-lineage` deferred contract includes this mismatch
case. It does not implement covariance estimation or qualify uncertainty values.

Thermal utility readers and finite-allocation accounting now have a unified
`h2physics.adapters` re-export surface. A deferred import-identity case is enrolled
in the thermal-utilities profile; it has not been run.

This is a coding backlog derived from PLAN.md, MODEL_CATALOG.md, the source
interfaces and receiving-project requests. The following totals were the
intermediate metadata snapshot at this audit: 76 families (20 implemented, 37
native-adapter-verified, 19 implemented-unverified and none planned), and 304
cases across 51 profiles and 74 case modules, with six later modules enrolled
for a then-expected 312 cases. They are superseded by the current files linked
above. A failed execution, missing measurement or unsupported scientific premise
does not justify a duplicate solver. No scientific test or model was run for this audit.

Pressure-peaking workbook metadata and bounded concentration blocks now require
one-use issuance by the checksum/schema-qualified reader. Their captured identity,
worksheet metadata, source file and observation payload are rechecked before
projection; the synthetic XLSX deferred contract covers direct construction,
replacement and post-issuance mutation. No workbook data or scientific model was
executed in this coding change.

BiologicalRun is now issued only after the native ADM1 integration and balance audit
complete. The receipt checks its native solver histories, system state, point/balance
records and source/version bindings for currentness. Its dedicated biological-process
deferred profile records a synthetic receipt-integrity contract without claiming
biological calibration or complete energy/water/element closure.

The version-1 MS1700/QP1180 normalized permeation attachment is now source-bound to
its Mendeley metadata, file listing and SHA-256. The MAT reader preserves the two
publisher-described coordinate columns without dimensional conversion. Numeric
load behavior and receipt integrity remain deferred to the `fracture-fatigue`
Nurion profile; no D/S/trap coefficients are inferred.

The integrity family now also exposes a transient finite spherical-shell heat
conduction model beside the cylindrical solver. The host API uses exact
spherical finite-volume measures and caller-owned property/boundary callbacks;
its analytic profile and energy-ledger contract is deferred to Nurion. This does
not add vessel-fluid feedback, cryogenic phase change or stress coupling. A
post-solve audit or assembly failure now retains the accepted SciPy solution and
original cause; the existing radial-heat profile contract covers this path.

`PowerLawSolubilityBoundary` now maps explicit caller fugacity schedules through
the admitted carrier-specific solubility relation using the diffusion solver's own
temperature input. This does not infer material coefficients or add surface kinetics;
the deferred interface contract remains unrun. Request032 and Request033 were also
refined to reflect missing native accepted-state/energy fields, leaving their gates
closed until the receiving owners support those contracts.

The existing long-cylinder thermoelastic BVP now also accepts an explicit
caller-mapped hydrogen concentration eigenstrain through a separate API. It
retains the pressure/thermal baseline, combined stress and component-wise
hydrogen stress increments. The coefficient, concentration basis, reference
concentration and temperature are caller-owned; stress does not feed back to
diffusion. The added synthetic Nurion contract is unexecuted and does not qualify
material parameters.

The same BVP also accepts caller-provided exact-time pressure, temperature and
hydrogen profiles through `radial_hydrogen_eigenstrain_history()`. It performs
independent quasi-static solves and retains sealed exact samples and accepted-prefix
failure information; it adds no diffusion evolution or stress feedback. The deferred
synthetic contract remains unexecuted.

Phase-specific relief-to-line receipts can now be composed across exact shared
event-time samples with continuity checks for cumulative mass and enthalpy. Port
phase evidence remains caller-owned, and the new sequence case is deferred.

PV electrolysis now has a typed post-run handoff to the existing finite stack thermal
solver. The receipt admits only matched shared-stack intervals within declared
temperature/heat budgets; it adds no electrolysis feedback equation. Its deferred
synthetic contract has not run.

The finite-adsorption gas binding now rechecks provider-owned species/fraction/molar-
mass metadata around every state query; providers without that metadata remain
caller-evidenced. Its existing owner-basis contract records provider mutation after
admission. This closes metadata freshness only, not mixture EOS qualification.

The shared `DispersionScenario` constructor now requires the selected family's full
provider keyword set, rejects keys from the other release path, and requires an exact
boolean for its accepted-result policy before engine invocation. Its facility-chain
contract is registered but unexecuted. This improves
Python API admission only; it does not close the native conserved-source or transient
plume gaps in Request012.

`OpenBraytonRun` also seals the native Cantera species thermochemistry, reaction
definitions and multipliers used by the reference cycle. A deferred mutation case
records this stale-mechanism rejection. This is receipt integrity; it does not add
cycle controls, compressor-map matching, shaft balance or independent turbine
qualification under Request035.

`QualifiedGasTable` now binds the identity of its underlying CoolProp state and
module object in addition to backend and qualification metadata. Its deferred
contract rejects replacement of the state object before property evaluation;
this does not add additional table-domain or independent EOS qualification.

The public HyRAM component-flow constructor also revalidates its parent finite
source receipt before accepting or exposing an allocation. The stale-parent
constructor contract is deferred; this does not repair the native HyRAM Gaussian
mass mismatch or establish plume conservation under Request012.

`LiquidAccidentEnergyDiagnostics` now requires a one-use token from its builder,
rejecting direct construction and copied receipts before stage-energy fields can
be consumed. Its existing deferred ledger case records these boundaries. This
preserves stage receipt provenance; global energy closure remains unresolved.

`HydrideCompressorTrace` now requires a one-use native-integration issuer and
checks model evidence, initial clock, segment types, stage continuity and terminal
event time. A dedicated deferred `hydride-compressor` profile now declares both
CoolProp and pinned LH2DT prerequisites. Its synthetic receipt contract remains
unexecuted; this does not qualify MHC material parameters or cyclic performance.

`OperationalScenario.run()` now issues `ScenarioResult` through a one-use token;
direct or replaced result receipts are rejected. Its deferred composition contract
records both guards. This preserves execution provenance and does not validate the
domain outputs produced by each node.

Scenario-result issuance is now created inline only after `OperationalScenario.run()`
has executed and recorded its selected nodes. The former module-level token factory
was removed because callers could invoke it to mint a forged result receipt. The
existing deferred composition case also checks that no callable factory is exported.

Radial failure-history callback signatures now include visible Python defaults,
nested closure state, bound receiver configuration and code-object identity. The
deferred integrity contract covers mutation and method-wrapper stability. Arbitrary
external/global callback dependencies remain caller-owned.

Joint uncertainty output now validates native result-row lineage and is bound to a
successful propagation issuer before exposure or summary. Its deferred contract
rejects scenario relabeling; caller-owned joint-law/dependence validity remains a
qualification task.
The shared `PropagationResult` now also has one-shot issuance from the completed
SciPy QMC propagator and checks every retained output row against the exact design
point. Its existing joint-input contract covers direct construction and cloning;
the case remains deferred.

Latest source-only continuations additionally bind SLABx snapshots to exact parent
clock edges, reconstruct fuel-cell post-run activity receipts from retained native
pressures and references, validate the complete operation/source/dispersion chain,
pin the open-channel and buried-pipeline metadata to publisher listings, and reject
cloned Cantera surface traces that try to reseal history. The pool-energy host gate
and Request033 signs were tightened, but the receiving pool still lacks cumulative
accepted-edge energy fields. Finite-hydride, engine, and mixture-separation receipts
also reject cloned histories; the mixture result rebuilds its phase component and
energy ledgers. Provider-backed line cooldown now binds both endpoint enthalpies to
their native states. These additions have deferred contracts only; they do not
resolve Request012/031/032/033/034/035 receiving physics or scientific qualification.

2026-10-30 source-integrity follow-up: retained numeric/bool NumPy outputs across
shared core, observations, data/fitting, adapters, materials, storage, combustion
and selected thermochemical/composition modules now use immutable bytes backing via
`core.immutable_array()`. A deferred observation contract records write-flag,
scalar-shape and nonnumeric-dtype behavior. Fixed CoolProp equilibrium packets now
expose phase volume/U and bulk residuals; HyRAM receipt construction recomputes
Gaussian flux summaries; radial SIF history preserves signed callback values; and
turbine maps seal source metadata and grids through interpolation. These deferred
contracts are not execution evidence or model qualification; see the current dated
entries in `DEVELOPMENT_LOG.md`.

## Current coding-stage reconciliation

New host levels: `combustion.piston_engine` supplies a closed-charge,
moving-volume H2 cylinder interval through Cantera's native moving wall; it is not
a full reciprocating engine. `combustion.gas_turbine` supplies a single-point open
Brayton reference with caller-bound efficiencies and native Cantera HP equilibrium.
`run_map_bound_open_cycle_brayton()` now composes one turbine-map point with that
reference by applying mapped expansion efficiency and checking pressure ratio and
caller-converted corrected flow. `combustion.turbine_map` admits and interpolates
caller-supplied corrected-flow/efficiency grids with strict in-domain checks. The
new composition is still not a compressor-map, single-shaft or off-design model.
Both cycle levels are
implemented-unverified with deferred contracts. Requests034/035 identify the
remaining cycle/control, map-coupling and independent qualification work. The
current catalog has no planned rows.

`TurbineMapPairingReceipt` now retains one admitted LH2DT compressor-map sample and
one turbine-map sample under explicit caller evidence IDs for their clock/window,
component pairing, shaft-speed basis, flow basis and pressure-ratio basis. It is
only a provenance-bound pairing receipt. It does not certify shared coordinates,
solve the native cycle, or calculate mass/power/shaft closure.

Local continuation: `combustion.EngineBoundarySchedule` now retains source and unit
identity, absolute clock origin, finite support, and linearly interpolated scalar
values while rejecting extrapolation. Both schedule arrays and closed-charge trace
arrays now use immutable byte backing, and the schedule rechecks a sealed source,
units, clock and content before every use. It is not yet consumed by the cylinder
solver and supplies no valve, injector, spark, or heat-transfer physics. Request034
still requires native flow/energy ownership before full-cycle controls can be added.

Current source-only follow-up (2026-10-29): selected data, separator, relief,
hydride and microsphere API boundaries received type-first validation. Selected
lint/compile and current sdist/wheel source matching pass; this does not change
the physical-family inventory or Nurion verification status.

Continued local coding (2026-10-29): operational-scenario receipts now seal their
declared identifiers and retained dynamic inventory/transfer records against
post-binding mutation. Repository metadata and OpenEI HEAD requests reject unsafe
redirect targets before following them; malformed contentUrl types are rejected
before suffix checks. Corresponding deferred contracts are metadata-only and remain
unexecuted. These changes do not complete native receiving requests or validate any
physical result.

Parallel source increments (2026-10-29) additionally reject fuel-cell product-water
activity phases that disagree with the shared reaction-energy basis; expose
component-resolved phase withdrawal masses and available phase enthalpy exports;
and fingerprint preferred-dispersion provider results/evidence against later
mutation. The water-phase and provider-freshness contracts are deferred; the
mixture withdrawal contract extends the existing deferred phase-partition case.
These are boundary/accounting additions, not Request031/032 native solvers or a
HyRAM/SLABx-LH2 plume qualification.

Latest local additions (2026-10-30): finite-hydride beds now accept an optional
same-clock external H2 stream boundary and retain signed mass/enthalpy ledgers;
facility-risk results now revalidate their original dependence/source/protection
objects; an exact-continuation pool-energy handoff keeps stage residuals separate.
The public buried-pipeline V2 data reader preserves the 12 publisher-hashed CSVs'
anonymous headerless fields and blank-cell masks. It assigns no units or measured
quantity labels. These new contracts are deferred and have not run.

The subsequent cross-owner pass fixes a downstream dispersion handoff that used to
re-run receipt construction and thereby replace its original fingerprint; it now
calls the receipt freshness check. Absolute-uptake vessel admission pins the exact
original qualified state object/evidence identity. Pool energy receipts pin energy
reference and vapor phase to the original deposited H2 state. Preferred dispersion
execution objects are now exported from `h2physics` for direct application use.
Each new mutation/identity contract remains deferred.

The radial SIF series additionally binds its reported maximum to the exact sampled
values, finite source clock and valid integer index. This protects summary consumers
from post-return tampering but does not validate the caller's SIF law or add HELPR's
missing total-stress crack-driving solver.

The 2026-10-29 follow-up hardened directly constructible reported-data quantities
and type-first identity validation in selected separator, relief, hydride and
microsphere entrypoints. Additional work added direct mixture endpoint viscosity,
an explicit electrochemical/thermal replay export, and stricter relief/cooldown
receipt revalidation. These changes improve boundary behavior; they do not add a
new calibrated physical model level or change scientific execution coverage.

Additional source-only coding closures on 2026-10-29: the H2 batch receipt now
checks producer/consumer elemental, charge and molar-mass identity, and its actual
PV-to-finite-fuel-cell trace fixture is registered in the deferred plan. Adsorption
vessel uncertainty output now rejects missing source coverage for any site/species
entry. The validation/profile metadata generators were reconciled to the active plan.
Static lint, syntax, path, import-binding, and package archive checks passed. None of
these checks ran a scientific case; execution remains deferred to Nurion.

The earlier static pass below did not prove that source coding was fully complete.
The following rows capture additional required implementation boundaries surfaced
by reconciling the backlog against the original goal and current public APIs. Code
them as additive, provenance-carrying APIs where their laws are sufficiently
specified; for native-engine-owned physics, maintain the receiving request and
implement every local side of the seam. Do not claim coding completion while these
items remain. Scientific execution is still reserved for the user's Nurion campaign.

| Previously missing host path | Current source closure | Remaining boundary |
|---|---|---|
| Liquid mass/stage energy | `finite_liquid_launch.py`, liquid/parcel chain modules, `liquid_accident_ledger.py` and `liquid_accident_energy.py` preserve original stage results and balances. | Launch/impact qualification, shared impact-wall/pool heat and native transient dispersion remain external physics; separate stage residuals do not constitute global energy closure. |
| Mixture inventory and separation | Bounded gas rho-U facade, native PQ/PH phase partition and finite phase packets exist; phase-selective withdrawal admits q=0/q=1 endpoints and exposes component masses and known enthalpy exports. | General evolving-composition two-phase separator inventory, native volume/U flash, phase events and time integration remain Request032. |
| Finite phase-selective vessel | `finite_separator.py` runs actual native pure-fluid stratified phase inventories, heat integration and selected-phase withdrawal; the result has one-use native-run issuance. | Mixture holdup, phase disappearance event localization and native failure-prefix exposure remain receiving work. |
| Transient flowing exchanger | `lh2dt_transient_flowing_exchanger.py` advances both native finite fluid/wall sides with stream callbacks and interval-aware restarts; the closed two-side trace exposes per-side native accepted heat rates and cumulative RK transfer on its original clock. | Distributed axial transport, unknown event roots and hydraulic loss laws are separate levels, not missing code in the declared mixed model. |
| Thermal/material fuel-cell operation | Shared finite coolant RHS, approximate staged material feedback, separated native gas pressure volumes and whole-window unresolved-energy diagnostics exist. | Exact simultaneous pressure/activity/thermal feedback remains Request031; the approximation and unresolved energy are explicit. |
| Native adsorption operation | Native RHS observations, scheduled cycle endpoint audits and finite-window product means reuse actual `PsaDynaBed`/`PsaDynaCycle`. | Accepted internal native trajectories, cryogenic material extensions and qualified absolute uptake remain native/evidence tasks. |
| Geological adsorption calibration inputs | `data.geological_calibration` preserves pinned H2 equilibrium, He calibration and sample-configuration rows, SI quantities and missing-value reasons. A structural report records14 raw CSV member receipts. | No raw logger reduction, He fit, pressure-reference qualification, linked COx workbook resolution, uncertainty propagation or excess-to-absolute conversion is inferred. The raw ingestion case is deferred to Nurion. |
| Catalytic production/conversion | `adapters.cantera_surface_reactor` composes native Cantera gas/surface kinetics with finite gas/adsorbate stock and element/site audits. | Closed rigid prescribed-temperature level only; catalyst heat transfer, finite feed/product flow, spatial reformer behavior, mechanism calibration and independent process validation remain open. |
| Native fuel-cell pressure/activity feedback | In addition to post-run activity receipts, `adapters.fuel_cell_trial` accepts three exact-time H2/O2/H2O channel snapshots, reuses the shared stack/activity APIs, and returns one-use issued stoichiometric molar/mass sources with unresolved energy explicit. | It is a solver-neutral RHS exchange contract, not an integrator. Feedback from evolving compartments, simultaneous native solver states, event handling and combined energy balance remain Request031. Its deferred case is registered but unexecuted. |
| Protection-to-risk receipt integrity | `FacilityRiskResult.require_current()` now binds the actual native conditional result to the exact finite source, accepted protection run and dependence declaration; direct wrapper construction is rejected. | This verifies composition identity only. Harm/consequence validity, conditional-frequency evidence, common-cause assumptions and independent facility-risk qualification remain open. |
| Finite changing-mixture separator | Local `MixturePhaseAmounts` and `MixturePhaseWithdrawal` retain species stocks, current-phase selective removal, exact component balances, native phase enthalpies and q=0/q=1 absent-phase semantics; `MixtureInventoryStateAdmission` admits native packets against target component moles, volume and U with sealed residuals. | Request032 still owns the changing-composition volume/internal-energy equilibrium flash, phase appearance/depletion events and accepted finite-vessel time integration. |
| Finite pool/fire energy handoff | `adapters.pool_energy_ledger` defines strict per-edge host acceptance for native cumulative pool U/H/Q/PdV and optional finite-wall U; `liquid_accident_energy_diagnostics()` can retain it only when bound to the exact original pool continuation, without summing stage residuals. | Current native pool output lacks these terms and is rejected; native accepted-clock energy integration, dryout/cap allocation and finite wall continuation remain Request033 work. |
| Gas concentration alarm logic | `adapters.gas_detection` applies caller-owned sampled trip/reset limits, hysteresis and confirmation counts, and passes source-bound trip evidence into existing scheduled protection replay. | Sensor physics, calibration, setpoint choice, detector siting, communication/actuator reliability and live closed-loop response remain outside the logic model; its deferred contract is unexecuted. |
| Oxygen-criterion reporting window | `evaluate_oxygen_criterion()` can select an exact inclusive span from native room output times and retains that selected clock in the sealed result. `integrate_oxygen_threshold_deficit()` analytically integrates the positive threshold difference on each admitted piecewise-linear interval, preserving fraction·s or Pa·s units. | Off-grid window edges are rejected. Crossings, duration and deficit integral remain reconstructions between retained output samples; no event root, physiological dose, probability or recommended limit is inferred. The integral case is deferred. |
| Cylindrical material diffusion | `DiffusionMesh.cylindrical_shell()` provides exact annular finite volumes, lateral areas and logarithmic radial resistance to the shared mobile/trap solver; steady rate and immutable cell-center profile use the same integrated face conductances. | Axial/end effects, stress-driven chemical-potential transport, material calibration and independent transient measurements remain open. The analytic steady-profile/inventory case is deferred. |
| Adsorption data-to-operation bridge | `adapters.absolute_adsorption_bridge` binds a source-row-complete, independently qualified absolute state to `FiniteAdsorptionVessel` at its exact recorded conditions. | Geological surface-excess calibration still cannot supply absolute uptake without an independently justified conversion or qualified absolute isotherm; no fit or interpolation is inferred by the bridge. |
| Cooldown/relief operational continuity | `ReliefCooldownInterface` joins retained native release samples to caller line-inlet histories on one clock, with typed `ReliefCooldownPort` phase/property/absolute-pressure identities and native-basis checks. | Port evidence remains caller-attested and the join does not couple solvers or prove flow routing. Phase changes must be segmented explicitly; native event handling and coupled relief/cooldown simulation remain receiving work. |
| Cylinder failure history bridge | `evaluate_radial_stress_intensity_samples()` calls a declared SIF calculator at each original exact-clock total-stress sample and retains finite signed values; exact-sample `RadialFailureWindow` views expose bounded subranges. | Callback law/material/flaw applicability remains caller evidence; interpolation, intermediate initiation search, crack growth, independent SIF qualification and native HELPR total-stress support remain Request027 work. |
| Liquefier thermodynamic benchmark | `adapters.liquefaction_performance` computes the ideal reversible flow-exergy work and boundary specific external work from caller-provided, same-reference H2 feed/product states. | The loss-free benchmark is not a refrigeration cycle or plant COP; vent/purge, external heat exergy, ortho-para conversion, staged component behavior and qualified plant data remain outside this API. Its deferred contract is registered under the existing `reliquefier-product` profile. |
| Hydrogen-engine observation ingestion | `hydrogen-engine-flame-wall.toml` pins the TUdatalib item, bundle and bitstream receipts; provider validates UUID/DOI/license and attachment hashes/sizes. `inspect_hdf5_metadata()` inventories structure without loading arrays. The attachment-level review is recorded in [HYDROGEN_ENGINE_DATA_SCHEMA.md](HYDROGEN_ENGINE_DATA_SCHEMA.md). | No attachment presently declares quantity, units, coordinate reference, and sensor location together. Obtain authoritative per-field definitions before issuing observation objects; do not infer pressure or wall-input semantics. This collection does not supply crank-angle pressure/work validation. |
| Turbine-map Brayton power report | Caller-owned compressor and turbine grids can now supply both mapped efficiencies and corrected-flow checks to the existing Cantera/open-Brayton path; the result reports an evidence-linked non-closed shaft residual. | A bounded operating-point solver, one-point/staged cooling, and Cantera plus CoolProp single-stage H2 compression references are now implemented_unverified. The Cantera compressor result can link to the cycle; the CoolProp property basis is kept separate. Coupled machine maps/shafts, pressure-side cooling hardware, auxiliary terms, off-design constraints and equipment qualification remain Request035 work. Deferred cases are registered but unexecuted. |

## Historical coding lanes identified earlier on 2026-10-29

The following tables record the earlier investigation sequence. Statements that a
seam is missing are historical findings superseded by the current reconciliation;
they are not instructions to duplicate the now implemented paths.

| Priority | Concrete deliverable | Existing source to extend/reuse | Completion boundary |
|---|---|---|---|
| 1 | Finite accident-chain composition receipt: accepted equipment outlet, explicit liquid/flash partition, parcel arrival, qualified impact, deposited pool and vapor source | `adapters/facility_protection.py`, `adapters/droplet_transport.py`, `adapters/droplet_impact.py`, `adapters/pool.py`, `sources.py` | Preserve parent clock, location, phase/property basis and per-stage mass/energy ledgers. Require caller closures for launch distribution and deposition; return incomplete boundary diagnostics when a premise is absent. Do not infer a deposited fraction. |
| 1 | Pool-vapor-to-preferred-dispersion composition with explicit per-bin footprint and state evidence | `adapters/pool.py`, `adapters/slabx_lh2.py`, `dispersion.py` | Map native pool output to the existing finite source and quasi-steady slice API without relabelling independent snapshots as a transient plume. Actual transient plume memory depends on the receiving engine. |
| 1 | Complete direct mixture saturation semantics and consumers | `thermo/coolprop_mixture.py`, `adapters/finite_adsorption_vessel.py`, `release.py` | PQ and TQ native partitions retain phase compositions and separately derived mass quality. Bounded single-gas PU inversion now reuses native PT calls only inside a declared monotone temperature interval. General two-phase vessel PU/rho-U, density-U and multiple critical states remain explicit until their native phase-aware branch solvers exist. |
| 2 | Common-clock operational assembly using the existing finite supply, actuation, relief, continuity, protection and utility objects | `adapters/lh2dt_supply.py`, `adapters/lh2dt_dynamics.py`, `adapters/lh2dt_valve_actuator.py`, `adapters/lh2dt_relief.py`, `facility_continuity.py`, `adapters/facility_protection.py`, `adapters/thermal_utilities.py` | `OperationalScenarioReceipt` binds original supply topology, accepted dynamic run, optional actuator/relief/relief-protection, prescribed protected-equipment replay and utility ledger on one clock/window with caller evidence for unencoded owner links. Its currentness seal also fingerprints native link/component identities, power readers, inventory readers and selected pump mode. A protected replay must retain the same accepted dynamic run object. Utility linkage remains caller-attested; no solver coupling, native event roots, or automatic route proof is introduced. |
| 2 | Electrochemical thermal and finite-reactant composition across production and consumption | `electrochemical_thermal.py`, `adapters/pv_electrolysis.py`, `adapters/fuel_cell.py`, `electrochemistry.py` | `HydrogenInventoryHandoff` checks one already-admitted PV-produced H2 batch against finite fuel-cell initial stock, clock, ports, species identity, transfer loss and molar closure. `bind_electrochemical_operation` admits a near-isothermal finite fuel-cell trace against a shared-stack thermal trace with matched heat/current/temperature budgets. Neither is a coupled solver. An actual authored producer/consumer bridge case is now registered; full thermal feedback, pressure/phase/transport closure, feeds/products and crossover/degradation laws remain. |
| 2 | Dynamic adsorption material/thermal composition using existing equilibrium and bed engines | `adsorption.py`, `adapters/psa.py`, `adapters/finite_adsorption_vessel.py`, `adapters/psa_cycle.py` | Couple absolute loading, free gas, source-qualified solid energy and native transfer rates. Signed surface excess is retained as observation and never treated as absolute inventory. Cryogenic native support belongs to Request005. |
| 3 | Spatial target response and source-driven finite fire/exposure composition | `adapters/thermal_target.py`, `adapters/jet_radiation.py`, `adapters/pool_fire.py`, `adapters/hyram_exposure.py`, `materials/radial_heat.py` | Bind incident flux, geometry, absorption and material domains to existing heat solvers. Time-varying flame fields and post-ignition pool evolution need the owning engine, not rescaled stationary output. |
| 3 | Shared joint uncertainty inputs and scenario execution receipts | `uncertainty.py`, `research/fitting.py`, `adapters/conditional_risk.py` | Add explicit dependence and scenario identity around deterministic APIs; retain failed physical evaluations. Do not infer annual occurrence from parameter samples. |

The table specifies implementable composition work, not evidence that every item is
currently absent at every sub-boundary. Re-read the named module before editing;
parallel development may already have completed a smaller part.

## Implemented composition increments in this continuation

These additions narrow specific rows above; they do not remove their physical scope.
All remain unexecuted under the active Hangang scientific execution plan.

| Existing backlog lane | Implemented host seam | Remaining implementation |
|---|---|---|
| Finite accident chain | `adapters/facility_accident_chain.py` prepares finite operation -> exact `FiniteFacilitySource` -> preferred `DispersionScenario`, with source mass/enthalpy budgets. `adapters/parcel_pool_chain.py` continues a qualified deposited batch through the native fixed-area pool and emitted vapor bins. | The two routes are not a predictive equipment liquid leak -> launch distribution -> flight -> impact -> pool chain. Native source/jet partition, launch/impact qualification and a continuous finite impact-wall/pool thermal state remain explicit missing physics. |
| Pool vapor and SLAB | `ParcelPoolContinuation.quasi_steady_dispersion()` retains native pool evaporation and passes its source to independent preferred SLAB snapshots; source and native ledger identities are rechecked. | Native transient plume memory and evolving source/footprint conservation remain receiving-engine work; snapshot selection cannot implement them. |
| Mixture saturation | `MixtureThermoState`, direct PT/PQ/TQ methods and native mole-quality handling in `thermo/coolprop_mixture.py` distinguish molar and mass qualities. | Audit every consumer for exact-type checks and mass-quality assumptions; only single-gas PU inversion has a bounded PT branch. Two-phase vessel PU/rho-U and multiple critical branches still require a declared phase model. |
| Operational assembly | `scenarios.py` adds lazy frozen nodes, explicit value/upstream bindings, deterministic dependency order, target-ancestor execution and original failures/results. The facility chain composes these nodes. | Domain-specific command, utility and inventory builders still need common-clock admission; a DAG alone does not solve simultaneous network feedback or locate physical events. |
| Electrochemical operation | `adapters/electrochemical_operation.py` admits an existing isothermal finite fuel-cell trace against the original thermal stack trace and retains both. | Continuous temperature feedback into polarization and coupled reactant depletion/thermal events remain outside this receipt comparison. Full crossover/species-fate and degradation are separate law/state requirements. |
| Adsorption operation | `adapters/adsorption_operation.py` reconstructs gas plus absolute loading using explicit per-cell adsorbent mass, retains free-volume evidence and native energy, and reports native component-inventory discrepancies. Scoped freshness checks detect changed source/geometry/receipt arrays. | This is an independent inventory audit, not a finite fill/withdrawal thermal driver. Native rates, source-qualified solid energy and accepted-state evolution must be composed without changing native reference or treating excess loading as absolute inventory. |
| Joint uncertainty | `research/joint_uncertainty.py` reuses the independent latent SciPy QMC design and propagation, admits caller joint transforms with law/dependence/revision identities, preserves physical inputs/failures, and adapts an `OperationalScenario` through an explicit output reader. | This does not infer a copula, covariance law, dependent Sobol attribution, structural model discrepancy or annual frequency. The caller transform needs evidence and numerical qualification. |

The native adsorption operation lane now reuses `PsaDynaCycle.run` and separately
observes `PsaDynaBed.rates`; adding another host bed integrator is unnecessary.
Native accepted internal trajectories, cryogenic parameters and additional thermal
boundary callbacks remain receiving-engine/data requirements. See the current
physical increments below for the next host implementation boundary.

## Current physical increments and next host boundary

The shared material diffusion solver now admits axisymmetric radial transport
through a finite-length cylindrical shell. Geometry contributes exact shell volumes,
lateral areas, and log-integrated radial resistance; existing mobile/trap states,
boundaries, units, and ledgers are reused unchanged. Its steady logarithmic profile
and conservation contract is deferred to Nurion. End-face/axial transport,
stress-driven chemical-potential terms, and material-specific transport coefficients
remain outside this level.

| Implemented level | Source | Remaining implementation boundary |
|---|---|---|
| Bounded frozen-mixture density/internal-energy inverse | `thermo/coolprop_mixture.py`, `thermo/mixture_inventory_inverse.py`, `thermo/mixture_inventory_properties.py` | Caller bounds/branch and root uniqueness admission remain necessary. This is not unrestricted multiphase density-energy inversion or a changing-composition fluid inventory. |
| Native PQ equilibrium phase compositions, mole-to-mass partition and bounded PH branch inverse | `thermo/mixture_phase_partition.py`, `adapters/mixture_flash_separator.py` | Finite equilibrium phase packets are available. No separator vessel holdup, level control, disequilibrium mass transfer, phase slip or kinetic nucleation is introduced. |
| Finite stack/coolant shared RHS | `electrochemical_thermal.py`, `adapters/electrochemical_coolant_utility.py` | Stack T and finite isobaric coolant enthalpy evolve together, with explicit external heat. Coolant boiling/flow/pressure and joint finite reactant/depletion feedback remain separate states/physical work. |
| Separated native H2/O2/water-vapor pressure trajectories and post-run activity receipt | `adapters/fuel_cell_compartments.py`, `adapters/fuel_cell_activity_receipt.py` | Independent native volumes evolve under prescribed shared-stack current/T and explicit heat. A sampled host receipt can convert accepted pure ideal-gas channel pressures to referenced activities and evaluate the shared stack after the run. It does not feed back during native integration; nonideal fugacity, simultaneous pressure/thermal/stack feedback, depletion events and combined energy closure remain open in Request031. |
| Transient flowing two-fluid/wall hold-up | `adapters/lh2dt_transient_flowing_exchanger.py`, `adapters/transient_exchanger_utility.py` | Native flow derivatives and native integration now evolve both finite sides with stage current-state streams. Known jumps use interval-aware native segmented restarts carrying full state/ledgers. Spatial counterflow, pressure loss, distributed axial transport, leakage and unknown event localization remain outside this mixed two-side level. |
| Finite-hydride external H2 port | `storage/finite_hydride.py` adds an optional same-clock signed H2 mass-flow boundary with a native stream state; accepted traces retain cumulative external mass and enthalpy and include both in gas/total conservation residuals. | Flow is caller-supplied. Pressure-flow, valve, hose, station-control and vehicle-tank laws remain outside this bed interface and require separately qualified owners. The deferred Nurion case is registered but unrun. |
| Catalytic reactor thermal response | `adapters/cantera_surface_reactor.py` now optionally enables the actual Cantera reactor energy equation and couples it to a caller-parameterized fixed-temperature native wall/reservoir; gas/surface kinetics respond to gas temperature. | This is a single rigid well-mixed gas volume and an imposed thermal boundary. The reported wall-energy integral uses requested output samples and trapezoidal integration. Finite catalyst-support heat capacity, coolant state, spatial transport and independent reactor qualification remain open; its new Nurion contract is deferred. |

Historical investigation, subsequently resolved for pure-fluid native operation by
`finite_separator.py` with mixture inventory requirements in Request032: the proposed
host path was an explicit finite
flash separator **inventory**: reuse the native mixture phase-partition/PH inverse
for each admitted equilibrium state while retaining component mass, internal energy,
liquid/vapor inventories and actual phase-specific withdrawal. The current separator
returns finite equilibrium packets, not a vessel state trajectory. Before adding a
driver, inspect whether the bounded EOS owner supports the necessary total density/U
two-phase branch; if it only supports single-gas inversion, implement declared finite
packet/receiver admission and request the missing native inventory flash instead of
solving an arbitrary branch. Full fuel-cell pressure/activity feedback remains a
receiving-level dependency under Request031 rather than another host wrapper.

## Receiving-project dependencies

### Further implemented native operation seams

`adapters/adsorption_operation.observe_bed_rates()` now calls the reviewed native
`PsaDynaBed.rates` API and retains its original derivative/ambient-heat tuple. It
independently sums gas-plus-absolute-loading molar inventory rates against first-face
minus last-face transport, with explicit clock, native cell masses/free volumes,
boundary enthalpy W and native ambient heat W. It supplies a rate observation,
not an accepted integration step or an independently computed energy derivative.

`adapters/adsorption_cycle_operation.py` wraps the existing `PsaDynaCycle.run`
runner and audits actual native slot/cycle checkpoint states. The checkpoint audit
retains the original run, native clock/period, per-bed inventory audits, aggregate
stream/ambient energy ledgers and vacuum work as a separate utility quantity.
The native bed energy residual excludes vacuum utility work consistently with its
owner. Initial zero-time and slot/cycle counter semantics are admitted explicitly.
The runner does not expose accepted internal solver objects/nodes, so this API does
not reconstruct them. A generic new adsorption ODE is no longer a justified next
step: extend native accepted-state/heat callback support through its receiving API.

`adapters/facility_operation.py` binds original finite-source, continuity, utility
and optional protection receipts on one declared clock. Continuity accumulation
rates remain explicit caller inputs; the receipt does not prove that those rates
are the finite solver's inventory derivatives. If a later frame audit fails during
binding, `FacilityOperationAuditError` retains the exact completed frame/result
prefix and original cause without minting a partial receipt. The deferred contract
is unexecuted. `adapters/liquid_release_chain.py`
and `adapters/parcel_impact_chain.py` now prepare explicit flash/population and
qualified impact composition through existing owners. Launch distributions,
upstream leak/source ownership, applicability evidence and shared impact/pool wall
energy still require their stated physical inputs or receiving model work.

These additions are implemented_unverified composition levels. The then-identified
host gap, now addressed by `finite_liquid_launch.py`, was a source-issued finite
liquid outlet-to-population binding: retain the
actual operation's mass bins and thermodynamic outlet history while allocating each
declared launch group without reusing one fixed EOS state across an evolving source.
This requires native per-interval phase/state output; where unavailable, specify the
receiving output contract and reject the unsupported projection.

These must remain concrete extension requests rather than local replacement physics.

| Capability | Receiving work and local integration point |
|---|---|
| Conserved preferred gas-source establishment and finite/transient LH2 plume source | Request012; `adapters/hyram.py`, `adapters/hyram_jet_source.py`, `adapters/slabx_lh2.py`. Host projection cannot repair a native mass/caloric failure. |
| Nonuniform thermal-stress crack-driving SIF | `docs/REQUEST027_HELPR_THERMAL_STRESS.md` and `adapters/radial_failure_history.py`. The existing pressure/temperature HELPR call does not consume the radial total stress field. The similarly numbered equipment request is a separate document; identify the thermal-stress document by its full path. |
| Native phase/event/accepted-step, utility and rotating equipment enhancements | Requests001, 007, 008, 013–015, 027–030; existing LH2DT adapter modules. Finite speed/map contracts do not provide rotor/surge/cavitation physics. |
| Cryogenic bed, cyclic separation and depletion-root transport | Requests005, 018–020; `adapters/psa.py`, `adapters/psa_cycle.py`, `adapters/cantera_membrane_device.py`. |
| Predictive fire, obstacle CFD and full source/field energy | Requests016, 024–026; existing HyRAM, FDS, pool-fire and flash-front adapters. A material-frame front is not an obstacle-flow flame solver. |
| Cavern geomechanics/porous storage, complete biological calorics and contact physics | Requests017, 019, 022, 025; underground, biological, microbial and impact adapters. These are additional model levels requiring primary scientific support. |

## Qualification and execution work, separate from coding

The reservoir-driven hydride trajectory constructor now requires an integration
receipt and verifies its retained material/initial-state basis, sample axes,
stored-hydrogen relation and reduced-energy ledger. A dedicated case is enrolled
under the finite-hydride profile; its execution remains deferred.

Public data rights, checksum/schema admission, source parameters, kinetics,
mechanisms, contact laws, geometry, sensor clocks and calibration uncertainty must
remain explicit. They cannot be completed by inventing default data. Geological
surface-excess observations still need a justified absolute-uptake conversion before
finite adsorbed inventory use. Field source/footprint and radiometer evidence remain
necessary for preferred dispersion/fire comparisons.

Scientific execution is deferred to Nurion: native installation, case execution,
conservation/refinement checks, measured-data comparisons, benchmarks and installed
artifact checks. Existing authored case counts are not passes. Keep source/plan/setup
hashes pinned when execution resumes through the user's shared connection.

`ReliefIntegrationError` now carries the accepted native intervals, transition
history, aligned output/ledger prefix, trial count, terminal metadata and original
cause when a later relief integration step fails. The deferred
`relief-lift-failure-prefix` case now uses a reviewed native tank, accepts one
valid interval, then supplies an invalid second-interval ambient temperature so
the native tank's own input guard raises. It checks original cause and accepted
prefix retention; this is an input-rejection contract, not an EOS/equipment
failure reproduction. It remains unexecuted pending Hangang.

Native liquid-equipment runs are now issued only by the accepted-output driver,
retain a content fingerprint, and reject post-issuance edits before integration,
cooldown auditing, or operational-scenario binding. The existing deferred
`native-dynamic-line-coolant-audit` contract now also covers fabricated and mutated
run receipts; its synthetic fixtures use the internal issuer and remain unexecuted.

Finite-hydride post-solve assembly failures now retain the exact accepted SciPy
solution together with the last trial state and original exception. The new deferred
`finite-hydride-postsolve-failure-retention` contract injects a failure only after
native integration returns; it remains unexecuted.

## Coding completion rule

A host coding item is complete only when its public typed API, physical boundaries,
source lineage, failure behavior, documentation and deferred execution contract exist.
Mark it implemented_unverified until the authorized cluster execution supplies evidence.
The full programme additionally requires its data, validation and release conditions;
the existence of one wrapper in each catalog family cannot satisfy that objective.


The ELVHYS4.2 cryogenic-room recorder now issues immutable source blocks through a
one-use token. Direct construction and dataclass replacement cannot attach forged
parsed values to the recorder's checksum-bound identity. The deferred
cryogenic-room-block-loader-provenance contract uses a synthetic CSV fixture and
remains unexecuted; it does not reconstruct oxygen depletion or resolve clock units.

`Lh2dtLowLevelProperties` now seals its original provider and native state factory,
and rechecks the underlying low-level state object, backend, fluid identity and
wrapper configuration around each property conversion. Replacing an admitted
CoolProp state can no longer leave the adapter using cached fluid/basis labels. The
existing finite-separator deferred case covers provider-state replacement; no case
count change, calculation or Nurion run is implied.


`RadialHeatResult` is now issued only by the finite-cylinder heat solver. It captures
the immutable output arrays and retained solver/material/boundary identities, rejects
cloned receipts, and checks currentness before thermoelastic or vessel-history consumers
sample the field. The existing radial heat case covers cloning and post-issuance edits;
it remains deferred. This closes receipt lineage only and does not qualify callback
internals or measured material behavior.


The closed-charge Cantera piston segment now reports ClosedChargeEngineError if
native stepping or result assembly fails. It retains the original ReactorNet,
reactor, moving wall, completed requested-output samples, failed target and
exception chain. The existing hydrogen-engine Nurion module now includes a
failure-prefix contract that injects failure after two completed samples. It is
authored only; no native engine case was run.

Prescribed-coolant `ThermalStackTrace` values now require one-use issuance by
`FiniteThermalStack.run()`, retain the exact issuing owner, and fingerprint the
native stage histories plus owner configuration. The electrolysis/thermal bridge
checks this source receipt before admission; direct construction, cloning and
cross-owner pairing are rejected by the existing deferred PV electrolysis thermal
case. No additional case was added, and this does not add live thermal feedback.


ConditionalRiskNative is issued only from the reviewed from_installed() path.
It seals the installed package, module/version, code digest and native callable
identities; the existing conditional-risk contract rejects direct construction and
copied owners. This is provenance ownership, not qualification of the risk model.

ThermalStackTrace is now issued by its actual FiniteThermalStack run and bound to
that exact owner. The electrolysis thermal bridge checks issuance and currentness
before accepting histories or native solver state. Its existing deferred admission
contract covers direct construction, cloning and owner mismatch.


Thermal-effects observation blocks now require one-use issuance from the checked
HDF5 reader, so direct construction or dataclass replacement cannot bind arbitrary
arrays to an admitted source hash. The new thermal-effects-block-loader-provenance
contract uses a synthetic fixture in the existing data profile; it remains
unexecuted.


SobolSensitivity now requires one-use issuance after the native analysis completes.
The receipt cross-checks its retained first/total indices and variance mask against
the native result, preserves the actual input/output batches and evaluation prefix,
and rejects direct construction, cloning and subsequent edits. The existing
joint-input-transform-propagation contract covers fabricated and altered receipts;
case count is unchanged.


TableQualification now fingerprints its admitted property/error/timing summary and
the four nested GasEnvelope limits; report decision methods reject post-issuance
mutation before returning a qualification or speedup claim. The existing
thermo-table-eos-domain-freshness contract covers report and envelope mutation.
This does not establish independent EOS accuracy or benchmark reproducibility.


PIFIRA EffectiveAreaResult now requires one-use issuance from the native-fit
adapter, fingerprints admitted observations/geometry/native functions and fitted
outputs, and is rechecked by contents_equivalent_heat_flux before its area is used.
The deferred thermal-target profile contract covers direct construction, cloning and
downstream rejection after mutation; it adds one case and does not validate PIFIRA
physics or external-fire allocation.


The high-pressure gas-jet receipt now requires one-use issuance from the checked
run_hyram_gas_jet() path. Synthetic native-like records cannot claim accepted HyRAM
execution merely by matching the host-reconstructed Gaussian flux equations. The
existing hyram-finite-source contract covers direct construction and dataclass
replacement; this adds no case definition.


SLABLH2Run now requires one-use issuance by run_slabx_lh2. Direct construction and
dataclass replacement cannot claim native run provenance, and downstream preferred
dispersion keeps the receipt's freshness checks. A dedicated deferred model-selection
case covers direct fabrication; the existing preferred-dispersion case covers clone
rejection. The new case is unexecuted.


The legacy DiffusionSlab projection now preserves the exact issued TransportResult.
DiffusionResult is one-use issued by DiffusionSlab.simulate, reconstructs each
reported array from that owner result, and exposes require_current() for later reads.
The existing material-transport contract covers direct construction, clone replay
and forced post-capture mutation; no new Nurion case was added.


FlashFrontTrace is now one-use issued by run_material_front and checks its retained
native premixed references, arrival/energy summaries and sparse graph arrays before
use. The existing flash-front-binding contract rejects direct construction,
dataclass replacement and post-issuance graph mutation. The case count is unchanged.


AdsorptionVesselDelivery is now issued only by the finite-vessel owner. It reconstructs
all signed species changes and product amount from its exact charged/discharged
snapshots; snapshots and delivery receipts reject post-issuance mutation. The
AdsorptionProductMassFlow projection checks currentness before and after conversion
and exposes `require_current()` for downstream reuse of a retained projection.
The existing storage-product-delivery contract covers direct fabrication, cloning,
forced snapshot/delivery mutation, and stale/tampered projection reuse without adding a case.

CounterflowFlameResult now requires one-use issuance by the native Cantera solver;
the previous seal only compared fields supplied by the same caller and therefore
could not prove solver ownership. The existing counterflow-flame profile adds a
direct-construction and dataclass-replacement contract. The new case remains
unexecuted and adds no physical qualification.

Cantera `EquilibriumResult`, `ReactorTrace`, and `FreeFlameResult` now require
one-use issuance from their native solver. Reactor trace use checks its captured
native endpoint; free-flame use checks the editable native profile and retained
phase lease. The existing `flash-front-binding` deferred case covers fabrication,
replacement, and stale native state for all three result types. This closes the
result-provenance implementation follow-up only; it is not physical validation.


ProtectedEquipmentRun now requires a one-use token issued after execute_protected
returns the exact native run. The token binds driver, prescribed plans, accepted
invocations, mode definition and scenario evidence; direct construction and
dataclass replacement cannot produce a second admitted replay receipt. The existing
facility-protection monitoring guard case covers both constructor and clone rejection.
No risk or actuator physics is added.


JetRadiationField now consumes a one-use issuer token created only by
line_source_irradiance. Instantiating the private issuer class cannot mint a native
result; the existing jet-radiation case covers that path. This strengthens result
provenance only and adds no radiation physics or deferred case.


FuelCellCompartmentTrace now requires one-use issuance from
SeparatedFuelCellCompartments.run(). A self-computed binding tuple no longer proves
native origin; the existing fuel-cell-native contract rejects direct trace creation.
This strengthens the post-run pressure/activity handoff without adding feedback
physics or a new case.


Vessel failure predictions and pressure-capacity reports now require one-use issuance
from their native HELPR adapter owner, seal report fields, and expose currentness
checks. The radial thermal-vessel bridge checks the prediction before handoff. The
existing vessel thermal/capacity contracts cover direct fabrication, cloning and
forced mutation; no failure or pressure-capacity physics is added.


Cantera multiphase equilibrium results are now one-use issued by the native equilibrium
owner. Their retained thermodynamic snapshots, gates, mechanism phases and live
Mixture state are fingerprinted, and amount projection checks freshness. The existing
solid-native-caloric deferred case covers direct construction, clone and mutation;
no new case is added.


OxygenRoomResult's internal binding now consumes a one-use token created only after
CanteraOxygenRoom.run() has completed native trace assembly. This prevents a caller
from attaching a self-computed signature to a fabricated result wrapper; the
oxygen-deficiency profile's deferred contract covers forged binding rejection.


OpenBraytonRun now uses a one-use issuer consumed by run_open_cycle_brayton(), so a
caller cannot attach a self-computed mechanism signature to fabricated station and
work summaries. The existing hydrogen-brayton-summary-integrity contract rejects
direct construction; this is result provenance, not cycle qualification.


ConcentrationAlarmTrace, ConcentrationAlarmVotingTrace, and their event evidence now
consume one-use issuance tokens from the sampled evaluator/bind operations. The
former reusable module sentinels could be imported and used to directly construct
self-consistent traces. The existing facility-concentration-alarm contract covers
direct and dataclass-replacement forgery; case inventory unchanged.


PsaCycleRun is now issued only by the completed PsaDynaCycle.run path. Its sealed
checkpoint/totals/metadata, case/schedule, owner identities and native runner hash
are rechecked before cycle-operation accounting. The existing adsorption-native-cycle
endpoint case covers direct fabrication, cloning and checkpoint mutation; no
additional model or case was added.


UndergroundTrace now requires a one-use issuer minted only after the completed
UH2SC run and host audit. The existing underground-storage case rejects cloning the
trace with dataclasses.replace(); this closes a native-result authenticity gap without
adding a second cavern model or a new case.


PoolFireTrace issuance now uses a one-use opaque token created inline only after the
finite run completes its accepted-step and energy audits. The former private issuer
class/factory could be called directly to attach a self-created owner to a fabricated
trace. The existing pool-fire baseline contract checks arbitrary token rejection;
no new case is added.


OxygenCriterionResult now requires one-use issuance from evaluate_oxygen_criterion.
Its sealed sample flags, crossing estimates and reconstructed duration are bound to
the exact verified OxygenRoomResult and OxygenCriterion; require_current() rechecks
both before use. The existing oxygen-room-result-issuer contract includes direct and
arbitrary-token fabrication rejection. No human-response probability is introduced.


Standalone HyRAM Bauwens peak and threshold result receipts now consume one-use
tokens minted inline after the native correlation and converged root/forward check.
`require_current()` revalidates native output projections and nested receipt state.
The dedicated deferred `hyram-bauwens-result-issuer` case is assigned to a separate
HyRAM profile. Native CJ and frozen-shock results similarly consume one-use tokens
issued only after completed SDToolbox solver/audit paths, with sealed nested phase
and solver state. The dedicated `detonation-result-issuer` case uses the reviewed
native SDToolbox and Cantera profile. Both cases use synthetic inputs, remain
unexecuted, and add no experimental validation claim.


Photochemical PhotoConversion results are now issued only by
convert_photon_exposure(); PhotoOperationTrace is issued only by
run_photochemical_operation(). One-use tokens prevent direct construction and
dataclass replacement from claiming a completed calculation. Nested optical inputs,
reaction inventories and reported energy totals are sealed and checked before
operation summaries; the existing photochemical-adjacent-finite-operation case
covers direct construction, token reuse and nested-source mutation. No new case.


StagedElectrochemicalTrace now requires one-use issuance from the completed
run_staged_electrochemical_operation path. Directly fabricated held-temperature/heat
summaries and dataclass-replaced receipts cannot claim original execution. The
existing electrochemical-staggered-temperature-feedback case covers both boundaries;
no new case was added.


NativeExchangeReceipt is now issued only by the validated finite-HX binder and
rechecks distinct side identities, common native source/window, direction and
equal-and-opposite interval energy whenever consumed. The existing thermal-native-HX
case covers direct same-side construction and consumed-token cloning. No new case.


HydrogenEconomicsResult now requires one-use issuance inside
evaluate_hydrogen_economics(). Its currentness check binds source projection, annual
and financial inputs, native provider/object, LCOH/NPV, annual arrays and window-cost
receipt. The existing economics-native-direct contract rejects direct construction,
token-reuse replacement and post-issuance numeric mutation. This adds no case and
does not qualify the assumed finance scenario.


ParcelTrace is issued only by a completed SaturatedParcelFlight.run() through a
one-use token. Its currentness check fingerprints accepted/trial states, native
SciPy state/event arrays and mass/energy/momentum summaries; population and finite-
impact consumers call it before admission. The existing droplet-transport cases
cover direct construction, token replay and post-issuance mutation. No new case.

HE-Austenite EmbrittlementBlock observations are now one-use issued by the pinned
collection iterator. Their source rows, linked composition records, values, masks
and invalid reasons are sealed, and paired-property summaries require currentness.
The existing austenite-embrittlement deferred case now covers fabricated blocks,
token reuse and post-issuance mutation; no case count change.

The shared diffusion solver now supports a caller-parameterized linear surface-film
resistance using same-carrier solid-basis external concentrations and transfer
velocity. Half-cell solid resistance and film resistance combine at each wall face
while the existing signed flux and inventory ledgers remain authoritative. Its
synthetic steady-profile contract is assigned to `fracture-fatigue` and remains
deferred. No fugacity mapping, surface kinetics, material coefficient or experiment
is inferred. The closed-charge engine also accepts caller crank-angle/value schedules
mapped to absolute time from explicit constant speed and segment origin; this is an
input-clock conversion only, with its own deferred contract and no valve or cycle law.

## Local continuation — diffusion-to-eigenstrain coupling

`h2physics.adapters.bind_cylindrical_transport_to_eigenstrain()` now joins the issued cylindrical finite-volume transport output to the exact-time quasi-static cylinder stress history. It preserves cell-center mobile concentrations and requires the caller to supply inner/outer solid concentrations at each exact time, plus explicit carrier basis, reference state, linear expansion coefficient, clock-mapping and axial-uniformity evidence. The admitted mesh must match the cylinder surfaces. One-use issuance rejects direct cloning; the binding retains both original histories and checks them for mutation. It does not treat trapped concentration as mobile, infer surface values, or add stress/diffusion feedback. A deferred synthetic bridge case is registered; it was not run.

The eigenstrain history now rejects per-sample changes to carrier, concentration basis, reference concentration, expansion coefficient or reference temperature before solving. Result freshness fingerprints the retained geometry, load, material and temperature content as well as stress arrays and object identity, closing stale-input mutation paths identified during source review. Deferred contracts cover those rejections; they remain unexecuted.

## Current mixture implementation reconciliation — 2026-10-30

The earlier Request032 rows above predate `thermo/mixture_inventory_flash.py`,
`thermo/finite_mixture_inventory.py` and `thermo/mixture_inventory_ode.py`.
These source paths now provide bounded multi-seed two-phase V/U state resolution,
finite-interval evolving stocks and a separate host-side SciPy adaptive rate-law
integrator with interior quality/component-floor termination. Their contracts
remain deferred. Remaining implementation work concerns receiving-native solver
ownership, unrestricted phase appearance/disappearance, spin and wall coupling;
independent EOS/parameter/data qualification remains a separate research gate.
Do not create another host ODE to satisfy the dated rows above.

The adaptive mixture ODE now stores its public accepted solver-state matrix in
`core.immutable_array()` bytes-backed storage. This closes the reversible
`setflags(write=False)` gap for retained inventory and energy channels; the
existing deferred mixture ODE contract requires `setflags(write=True)` to be
rejected. It adds no phase-transition handling or native solver ownership.

## Local continuation — transient rotor and alkaline bubble-loss levels

`h2physics.combustion.shaft_transient` advances one rotor's kinetic-energy
inventory under caller-supplied time-varying turbine/compressor power, load
torque, inertia and mechanical-loss inputs. It returns cumulative work,
energy-residual and bounded-speed event records. It does not calculate gas-path
power, map points, combustion, governors, electrical conversion or multiple
spools. Two synthetic Hangang contracts are registered and were not run.

`h2physics.adapters.alkaline_bubbles` adds separate caller-calibrated electrode
coverage and electrolyte gas-void voltage-loss terms around the shared
`HydrogenStack`, preserving its Faradaic rate and existing electrochemical
owner. It assumes the base stack losses exclude these contributions, and it
does not predict bubble growth, detachment, transport, spatial fields, or
coverage/void parameters. The reduced-order contract cites its public primary
methods and is registered as a deferred Hangang case. Numeric coverage and void
data with complete operating-condition mapping remain an open data gap. Both
new levels are implemented-unverified; no local scientific execution occurred.

`h2physics.caloric_pipe_finite_wall` composes one perfectly mixed finite wall
with the existing caloric Euler pipe solver. It advances wall temperature from
the native integrated gas-wall heat and can include separately accounted
constant-UA ambient exchange. Its issued outer result verifies segment
continuity, local-clock span, wall-boundary provenance, temperatures and the
combined energy residual against retained gas traces. Inner traces use local
0-to-dt time and map by sequence onto the outer absolute clock. This is a
first-order split with no axial wall gradient, branched network, friction or
finite-reservoir endpoint. Its synthetic Hangang contract is registered and
unrun; AST and targeted Ruff checks pass.
