# Implementation plan

## Fluid-property ownership — 2026-11-01

Extend existing quasi-steady pipe physics at the same level rather than replacing
it with a wave solver. Native cell pressures and the generalized steady Darcy
density integral must use the same CoolProp identity; changing only cell density
would retain an incompatible ideal flow relation. Numerical proof includes an
independent density-variable momentum ODE, pressure reconstruction, low-density
limit, phase/sonic rejection, real integration-step refinement and native owner
currentness. Experimental pipeline qualification remains a separate gap.

Use native CoolProp for fluid density, caloric properties, phase equilibrium and
transport properties. Reuse the existing pure-fluid, mixture and molar-enthalpy
providers. Acceleration uses qualified CoolProp-derived tables with bounded
domains and measured error/speed evidence. Do not build a competing property
library or silently recover from a native failure using an ideal formula.
Migrate implicit ideal property defaults first; retain explicitly selected
analytical closures only as identifiable numerical references. Existing
ideal-only coupling contracts require an explicit migration to their native
real-fluid counterparts rather than changing the meaning of stored states.

## RODARE alkaline-bubble source index

`h2physics.data.load_rodare_alkaline_bubble_index()` now reads the small,
rights-qualified 60-condition summary with byte-receipt and schema/grid checks.
It is an input-integrity route only; the numeric HDF5 measurement archive is
still unavailable, and no response channel is inferred. The Hangang source
contract is registered but unexecuted. See
`docs/RODARE_ALKALINE_BUBBLE_INDEX.md` and
`docs/PRESSURIZED_ALKALINE_BUBBLE_DATA.md`.

## Concentration-alarm valve isolation command schedule

`h2physics.adapters.schedule_alarm_valve_isolation()` binds a confirmed,
source-bound concentration alarm to the existing finite-stroke valve command
API. It splits the caller's command plan at the explicit alarm-plus-latency
instant and schedules zero target stroke in `isolate` mode through an explicit
end time. It adds no actuator, flow, online interlock, reliability-credit or SIS
model. A synthetic Hangang contract is registered; execution and any facility
qualification remain pending. See `docs/ALARM_VALVE_ISOLATION.md`.

## Empirical detector-demand uncertainty boundary

`h2physics.detector_reliability.interval_for_kofn_trials()` adds a two-sided
Clopper–Pearson interval for caller-selected system miss, common-cause outage,
or conditional miss counts. It is tied to the immutable, source-versioned trial
evidence and rejects counts that do not reconstruct from those observations.
The caller must supply a separate independence-evidence identity for
identically designed Bernoulli demand windows; no software inference establishes
independence, representativeness, annual frequency, or SIL. The synthetic
Hangang contract is registered; field data and inferential qualification remain
open. See `docs/DETECTOR_RELIABILITY.md`.

## Caller-calibrated alkaline electrolysis bubble losses

Added `h2physics.adapters.alkaline_bubbles.evaluate_alkaline_bubbles()` as an
optional correction to the shared `HydrogenStack`. It separately applies
caller-supplied electrode coverage through Tafel effective-area terms and
electrolyte gas void through a Bruggeman-form conductivity loss. Coverage and
void are not inferred from each other or from operating conditions. This is a
quasi-steady loss boundary, not a bubble-dynamics solver, and remains
implemented_unverified. Deferred Hangang contract
`alkaline-bubble-electrode-and-electrolyte-losses` checks its composition and
accounting; no local physical execution or independent calibration has been
performed. See `docs/ALKALINE_BUBBLE_LOSSES.md`.

## Finite PV-electrolysis batch to pipeline linepack

Added `charge_linepack_from_electrolysis()` as an object-level bridge between
the existing admitted PV-electrolysis inventory trace and the existing lumped
isothermal linepack state. It transfers only the net neutral gaseous H2 delta
over a separate post-production interval, applies an explicit molar transfer
loss, and checks caller-evidenced pressure and temperature bounds for that
window. A source-side mole ledger records initial stock, produced batch,
withdrawal, transfer loss, retained batch and post-transfer H2 stock; it does
not mutate or reflash the producer trace. A signed energy-reference ledger ties integrated source enthalpy,
reference offset and conditioning energy to the transferred mass and a
caller-declared linepack energy change. It adds no compressor, valve,
pressure-drop, pipeline-flow, internal-energy, or thermal solver. Deferred Hangang case
`pv-electrolysis-isothermal-linepack-charge-handoff` is registered and unrun.
See `docs/ELECTROLYSIS_LINEPACK.md`; no local tests/calculations were run.

## Hydrogen ignition probability from native HyRAM+

Added `h2physics.adapters.hyram_ignition` as an optional object-level seam to
HyRAM+'s native hydrogen release-rate threshold model. It accepts either the
installed default H2 table or an explicitly parameterized and evidence-bound
typed table, and preserves immediate/delayed probabilities as absolute
release-relative branches. It adds no ignition physics, risk frequency,
detection credit or consequence model. Deferred case
`hyram-hydrogen-ignition-probability-native-contract` is registered under the
`hyram-overpressure` profile and remains unrun. HyRAM+ remains an optional
separately installed GPL-3.0-only dependency and is not added to this project's
dependency metadata; any combined distribution needs a separate license
compatibility review. See `docs/HYRAM_IGNITION_PROBABILITY.md`.

`h2physics.adapters.hyram_ignition_risk.bind_hyram_ignition_to_risk()` maps
that result into the existing conditional-risk native `Branch` and `RiskInput`
objects. It forms a three-way no/immediate/delayed partition conditional on
one explicit LOC and preserves the exact caller-created native `Frequency`.
It requires caller branch/factor/evidence IDs and typed harm bindings; it does
not infer annual frequency, occupancy, consequence, or probabilities
conditioned on ignition. Its synthetic handoff case uses authored values and
does not load HyRAM. It remains unrun; see
`docs/HYRAM_IGNITION_RISK_HANDOFF.md`.

## Hydrogen pipeline linepack and detector voting reliability — 2026-10-31

Added a fixed-volume lumped isothermal pipeline linepack state with explicit
interval inlet/outlet mass accounting. It assumes caller-prescribed rates and
fixed temperature/composition; it does not model spatial pressure waves, line
friction, or real-gas/thermal effects. A separate detector reliability module
evaluates heterogeneous k-of-n fail-to-alarm probability and a separately
supplied common-cause event over an explicit mission. Neither API infers
physical input parameters or evidence. Both have deferred synthetic Hangang
contracts registered in the next source plan; neither was run locally.

The pipe family now also includes a segmented quasi-steady transient network
level. It reuses the existing compressible Darcy relation between finite
ideal-gas cells, integrates caller-declared boundary mass rates, audits the
whole-network mass residual, and localizes a caller-defined cell inventory
floor. Its limits remain fixed temperature/composition, no momentum storage or
pressure waves, and no real-gas or energy equation. The deferred case is
registered in the local Hangang plan; physical comparison remains open.

## Elastic-energy ceiling for fragment scenarios — 2026-10-31

Added a separate compositional bound from the existing Lamé cylinder stress
field. A caller-provided differential pressure load, cylinder length, elastic
constants, fragment mass, and energy allocation produce stored elastic strain
energy and a maximum speed conditional on that allocation. The API makes no
rupture, fragmentation, or launch-state prediction. Its deferred synthetic
contract is in `validation/cases/fragment_energy_bound.py` and is registered in
the local Hangang plan for the next capture. No tests or calculations were run.

## Competitive multicomponent adsorption equilibrium — 2026-10-31

`h2physics.adsorption.ExtendedLangmuirIsotherm` implements an absolute-uptake
competitive Langmuir model with multiple sites, caller-owned temperature-
dependent affinities, and analytic cross-species pressure derivatives. Its
synthetic contract checks capacity, derivative axes, optional thermal
derivatives, domain enforcement and immutable results. Hangang execution is
pending; fitted material parameters and independent uptake data remain open.
The new catalog family is `implemented_unverified`.

## GrInHy2 source-bound plant-flow interface — 2026-10-31

Added `h2physics.data.grinhy2.load_grinhy2_flow`, a checksum-required loader
for the attributed six-column CSV. The immutable result retains all four
reported boundary-flow channels, source time coordinates, irregular intervals
and source-file identity; it does not convert normalized volume to mass flow or
fill the logger gap. A Hangang source-ingestion case checks row/schema/hash
preservation and stale-source detection. Hangang job `1186145` was admitted on
revision `3374d5e` but its reader rejected the Windows/Unix line-ending hash
difference. A file-specific Git attribute now preserves the bytes tied to the
receipt. Retry requires a new immutable snapshot; the ingestion case does not
qualify a physical process model.

## Hangang outcomes from revision 3374d5e — 2026-10-31

Synthetic deferred contracts passed: `1186148` quasi-steady permeation,
`1186149` steady film/bulk permeation, `1186151` adjacent photochemical
operations, `1186155` cylindrical-shell diffusion, and `1186156`
pressure-driven porous-reservoir well, `1186157` isothermal compressible-pipe
momentum, and `1186158` competitive extended-Langmuir equilibrium. These
results confirm only the
registered software contracts under that exact source/setup pin; they do not
validate model accuracy against independent physical evidence.

`1186146` failed on an exact floating-point fixture comparison in the
time-varying fugacity boundary. The case now uses a tight relative tolerance;
it awaits a new pin. Re-captured cases will also include the competitive
multicomponent Langmuir contract, which hit the user's per-account QOS limit
when first attempted. Further standalone cases are being submitted as queue
slots open.

`1186160` failed the catalytic CSTR's gas/surface temperature-equilibrium
invariant by 0.032 K. Cantera 3.2's reactor-surface synchronization is being
checked against its native state API; the temperature tolerance remains
unchanged. `1186166` and `1186167` exited before the engine model because the
case omitted `OpenCylinderInlet`; the missing import is corrected locally.
`1186168` prescribed engine boundary-stream ledger and `1186171` synchronized
finite fuel-cell trial exchange passed their synthetic contracts. `1186169`
wall-energy ledger exited before integration because the case still supplied
placeholder mechanism and energy-tolerance metadata; it needs a local fix and
new immutable source pin before retry.

## Steady permeation surface-resistance level — 2026-10-31

`materials.permeation` now offers a separate planar steady path with two
caller-supplied linear film transfer velocities in series with bulk Fick
diffusion. The API retains the film and bulk resistances, both membrane-side
concentrations, carrier identity, and independent IDs for the boundary mapping
and surface coefficients. A deferred algebraic case covers closure and sign
reversal; it has not run. Surface kinetics, fitted coefficients, transient
membrane response, and material qualification remain open. The family is
`implemented_unverified` for this expanded level; overall catalog classification
remains 57/78 (73%).

## PV/direct-DC stage lineage — 2026-10-31

The energy-coupling runner now rejects duplicate `PVStage.identifier` values
before the first native load-line calculation. Profile-generated stages also
retain their two original knot identifiers as a tuple, without making
downstream consumers parse a joined string. Deferred Hangang cases cover the
pre-solve rejection and source-pair preservation; they have not been executed
and provide no physical-model validation. The catalog remains 57/77
implementation-classified families (74%); these bounded API corrections do not
change family coverage.

## Sensor calibration deferred-case status — 2026-10-31

Hangang job `1185889` (`sensor-time-constant-calibration-recovery`) failed
because its entrypoint returned without a `ValidationOutcome`. The recovery and
rejection case entrypoints now return explicit named metrics after preserving
their existing calibration, boundary-limit, immutability and rejection
assertions. This correction is local and unverified pending retry; the job was a
case-reporting failure, not an independent calibration result.

## Latest Hangang result — 2026-10-31

`1185860` (`carrier-original-binding`) failed because the deferred case tried to
make a bytes-backed immutable array writable and did not catch the resulting
`ValueError`. The case harness is corrected to require rejection at
`setflags(write=True)` and then confirm `result.require_current()` succeeds
without mutation. This is a case setup/assertion failure, not a model failure;
the correction remains unverified pending replay. No scientific qualification
is implied.

## Latest verified Hangang source — 2026-10-31

Snapshot revision `9048413b68025235753242dcb93efb68d9afc477`; archive SHA-256
`5a34abfd652c7dbe6ff6ba41ca7981082e42bffc70533e805c638ef33f99250c`
(3,780,321 bytes); manifest SHA-256
`9034a8102d3bbe6b53310ab122b5a359acb1d8918ba62dc065343999e10eb4ca`; all
1,060/1,060 entries verified. `1185710` (offline core-flood source ingestion)
passed metadata/listing hash checks and four staged workbooks; this is ingestion
evidence only, not physical validation. `1185709` CSTR entered but failed the
fixed geometry/site-domain invariant after initialization/enthalpy fixes. The
failing subcondition remains under investigation; no CSTR pass is recorded. A
local diagnostic patch separates volume, site-density, and temperature checks
with native-value diagnostics without loosening bounds. The root cause remains
unknown; retry after a fresh snapshot. Both jobs used external logs. This capture
predates the canonical Krg/Krw mobility
guard and staged-turbine fixture correction, requiring a newer snapshot to
evaluate those changes. From older `64a31`, jobs `1185715`
(`thermal-target-domain`) and `1185716` (`impact-elastic`) passed synthetic
domain-contract checks with outcome JSON evidence; neither is independent
validation. Earlier failures remain scoped to their source snapshots.
Completed `64a31` outcomes: `1185718` (`thermal-target-exposure-history`) failed
with ValueError because left-held history length did not match edge/interval
shape, a case input/contract issue rather than independent scientific validation;
`1185727` (`impact-native-pool`) passed after installing exact pinned optional
`dynamiclh2poolx`, for its deferred synthetic contract only, not physical
qualification. `1185719` PIFIRA receipt, `1185720`
impact-zero-contact, `1185722` impact-dryout, `1185723` impact-prefix, `1185724`
impact-history-issuer-integrity, `1185725` impact-intercontact-heat, `1185726`
impact-missing-heat, `1185729` impact-refinement, and `1185730`
thermal-target-lossless passed their deferred synthetic contracts. These passes
do not constitute independent scientific validation. Logs are external.
From `64a31`, `1185735` failed on unequal edge/sample fixture lengths; adjacent
interval indexing is corrected locally. `1185736` relief-lift-travel and
`1185750` relief-lift-leakage failed because their plan omitted `fixture_factory`;
the local fallback builds synthetic scenarios around real reviewed LH2DT
protection/nozzle/native-state types, including wrong-state rejection, and is
unverified pending recapture. `1185737`–`1185740` failed phase-partition PQ
component/mole consistency checks, not independent validation. `1185752`
impact-native-pool passed after exact pinned optional-provider installation,
limited to its deferred synthetic contract. No physical qualification follows.
Logs are external.

## Previous verified Hangang source — 2026-10-31

Complete source revision `64a31d2784b72f66d66a77accb01e18e3d711a4f` was captured
as archive SHA-256 `3811c36a140e38200a81c6b3d622a9ebb547d2d9350bcd36f8d5f9f1848216cb`
(3,776,678 bytes), manifest SHA-256
`7bc132d660b514a657068d1b2ad41d6a417849730812437b78eb0fb32583ac1a`; all
1,060/1,060 entries verified, with zero raw/processed data. Jobs `1185638` CSTR
and `1185639` core-flood ingestion failed after entry: controller initialization
preceded the `mass_flow_rate` read incorrectly, and a numeric Mendeley version
was rejected for not being a string; local fixes are in progress. `1185646`
failed its synthetic mobility role-rejection assertion, now corrected to the
canonical Krg/Krw phase guard. `1185647`, `1185661`, and `1185662` failed before
staged-turbine scenario assertions because the fixture supplied a callable where
`run_open_cycle_brayton` requires a native phase; the fixture is corrected locally
but unverified. `1185664` impact-baseline and `1185665` thermal-target-refinement
passed. Four passes total (`1185448`, `1185452`, `1185664`, `1185665`) do not
establish scientific/source/equipment qualification. Mobility/staged-turbine
jobs were accepted after initial QOS refusal. Qsub logs/results are outside the
source tree. `1185550`/`1185557` were launch/log-only failures against older
`8105`; PBS log pollution broke the pinned source, while external log paths now
work. Prior `8105` outcomes remain historical.
Job `1185687` (`thermal-target-pulse`) passed the deferred synthetic energy
ledger on `64a31` (maximum residual about `1.14e-8 J`), which does not establish
scientific qualification. After QOS reopened, jobs `1185698`
(`thermal-target-domain`) and `1185699` (`impact-elastic`) were accepted; results
are pending and logs are external. Initial QOS refusals had no job IDs.

## Prior Hangang result matrix from snapshot 64a31 — 2026-10-31

Jobs `1185448`, `1185452`, `1185664`, and `1185665` passed after case entry.
See the current verified snapshot block above for case-entry failures and the
local staged-turbine fixture correction. Earlier 8105 failures are historical;
the `1185550`/`1185557` attempts were launch/log-only and external log paths now
work. No case results establish scientific/source/equipment qualification.

## Current source-only status — 2026-10-30

The current catalog has 77 families with a first code or native-adapter level:
20 implemented, 37 native-adapter-verified, 20 implemented-unverified and none
planned. The newly added porous-reservoir level is a single-phase fixed-temperature
radial Darcy inventory model with caller-owned properties; it does not close
geological laws, geomechanics, multiphase behavior, or site qualification.
Higher-fidelity levels and full-family completion remain open. The previous
metadata snapshot recorded 304 deferred cases across 51 profiles and 74 case
modules (76 curated profile/module associations). This continuation adds deferred
porous-reservoir, exact-trial and synchronized-native fuel-cell coupling,
compressor/turbine maps and bounded operating-point solve, prescribed and
pressure-responsive engine boundaries, mixture history audit and finite/adaptive
evolving-stock V/U vessels, HyRAM transition audit, pool accepted-edge energy,
cooled Brayton/bleed, synchronized Cantera fuel-cell coupling, staged turbine
cooling, and Cantera ideal-gas plus CoolProp HEOS real-fluid single-stage hydrogen
compression.
The latest regenerated inventory contains 371 cases across 56 profiles and
105 modules (110 curated profile/module associations); it replaces the prior
370/56/105 metadata snapshot. The newest contracts add a variable-heat-capacity
lumped thermal target, a finite-feed Cantera catalytic CSTR, and conditional
fragment flight/impact; these remain implemented_unverified and await Hangang
execution.
Refresh the source archive before campaign submission on the target
Python 3.12 environment. Current static API inventory records 1,455 public
definitions across 241 modules; the AST relative-import inventory records 1,748
bound imports with zero missing or unresolved references. The refreshed document-link
audit covers 3,941 local links across 340 files with none missing. The current
Hangang plan contains 97 cases across 19 profiles and 36 modules. These
are structural inventory results, not
scientific execution or validation. The last accepted execution evidence is the
historical 59/72 checkpoint at `6eae06c`; later coding remains unverified pending
the user-directed Hangang campaign. Hangang snapshots `341c`, `37752360`, and
`13e720` are incomplete; no case ran from those snapshots. Snapshots `341c` and
`37752360` have remote archive/manifest checks but omit `src/h2physics/data`;
`13e720` is an incomplete local candidate, not a remotely verified complete
source. Job `1185303` was accepted by the scheduler, then failed before case
entry because snapshot `37752360` omitted `src/h2physics/data`. A corrected full
capture is under construction. An earlier summary of the latest Hangang batch
was superseded by the outcome JSON audit: jobs `1185448` and `1185452` entered
and passed; `1185450` entered the CSTR case and failed on unavailable Cantera
surface method `getPartialMolarIntEnergies`; `1185453` entered core-flood and
failed importing its absent fixture before ingestion. These results do not provide full scientific
qualification. A fresh complete snapshot is pending. Dated continuation sections
below preserve their historical scope and counts.

## Objective

Build a reusable Python library spanning the major hydrogen facility and safety model
families, with explicit parameters, measured-data interfaces, qualified property services,
native coupling to existing engines and enough evidence to continue the research from the
repository alone. Consolidate equivalent formulations; use separate model levels only when
they change the resolved physics, spatial detail or justified application domain.

## Acceptance principles

1. Parameters, geometry, property functions, kinetics and boundary histories are replaceable.
2. Public process and experiment data are acquired and audited before a model is called validated.
3. Original code, public primary references and explicit third-party rights support release.
4. Modern, maintained methods are preferred after domain, license, accuracy and cost comparison.
5. CoolProp is the reference pure-fluid backend; acceleration must pass declared error gates.
6. Existing engines retain their physical responsibilities and version-specific validity.
7. Python contracts are the integration surface; no mandatory wire or service layer.
8. Every stage records implementation, verification, validation, decisions and remaining work.
9. Receiving-project changes are specified as requests rather than edited in this repository.
10. No target is complete merely because a wrapper, schema, synthetic example or unit test exists.

## Delivery sequence

| Stage | Work | Exit evidence |
|---|---|---|
| P0 | Scope, reuse ownership, public primary sources, dataset discovery and rights | Coverage catalog; reproducible acquisition; per-file hashes; limitations and missing inputs |
| P1 | Units, states, streams, histories, evidence, property service, data loaders | Executable typed API; domain guards; independently checked conversions and ingestion |
| P2 | CoolProp reference and qualified acceleration | HEOS comparisons; holdout points; phase/critical-region guards; measured speed and errors |
| P3 | Equipment and storage models through existing native engines | Version-pinned adapter checks; conservation and event tests; applicable experimental comparisons |
| P4 | Release, multiphase/near-field and pool/dispersion handoffs | Inventory, mass, momentum and energy closure; independent source/field cases |
| P5 | Adsorption, hydride, carrier and production/conversion gaps | Source-specific parameters; identifiable calibration; held-out experiment assessment |
| P6 | Fire, combustion, overpressure, transport through materials and integrity | Stated fidelity; qualified coefficients/mechanisms; numerical and experimental comparisons |
| P7 | Facility composition and uncertainty | Common-clock coupled runs; source identity; sensitivity/convergence; documented missing paths |
| P8 | Release readiness and continuation | Clean distribution inventory; license audit; tutorials; reproducible validation; extension requests |

## Scope by physical family

- Thermodynamics: pure-fluid EOS, hydrogen spin identity, phase equilibrium, flashes,
  thermodynamic derivatives, gas mixtures through appropriate providers and qualified tables.
- Equipment: gas and cryogenic tanks, wall/insulation heat transfer, compressors, pumps,
  valves, relief devices, pipes, vaporizers, reliquefaction, vents and instrumentation.
- Physical storage: compressed, liquid and cryo-compressed hydrogen; adsorption equilibrium,
  usable capacity, transport kinetics and thermal response.
- Chemical storage and carriers: metal hydride equilibrium/kinetics/heat, reversible carriers,
  decomposition and catalytic reaction modules with source-specific mechanisms.
- Production/conversion: water electrolysis and fuel cells, solar/photo processes,
  thermochemical cycles, reforming/gasification and biological production where usable
  public kinetic and process evidence exists. Shared reaction/energy machinery avoids
  creating a new solver for every catalyst or feedstock.
- Materials/containment: solubility, permeation, diffusion, trapping and hydrogen-assisted
  degradation; fracture/fatigue require the applicable mechanical and material evidence.
- Accident physics: blowdown, gas/liquid/two-phase critical flow, jets, flash and droplets,
  ground partition, spreading, evaporation, atmospheric dispersion and enclosure ventilation.
- Fire/combustion: heat input, jet/pool/flash fire, radiation and dose, reaction kinetics,
  ignition, deflagration/detonation criteria and overpressure within declared model levels.
- Composition: facility modes, isolation, residual inventory, protection responses,
  uncertainty, conditional consequences and optional frequency/risk consumers.

This list describes research scope. The executable catalog must distinguish planned,
implemented, software-verified, externally compared and domain-qualified capabilities.
Missing experimental evidence remains visible rather than being replaced with invented data.

## Historical 72-family checkpoint: finite spin, two-fluid heat and reacting gas

Three previously planned families now have a checked first native level:
thermo.spin, equipment.heat_exchanger and production.reforming. They respectively
resolve constant-pressure spin enthalpy, two closed finite fluid/wall inventories,
and finite homogeneous gas carbon/steam conversion. At that checkpoint, first
executable coverage advanced to 42/72, with 17 partial implementations and 25
checked native adapters; 30 families were still planned. Those counts are historical
and are superseded by the current 76-family catalog in `MODEL_CATALOG.md`, which
has no planned family rows. Unimplemented fidelity levels, native receiving
requests, unqualified inputs and unverified code remain open even when a catalog
family has an implementation status. The 30–40% full-programme estimate is also
a historical checkpoint, not recalculated here.

These levels do not finish evolving-spin liquid EOS/tank coupling, flowing/spatial
heat-exchanger hardware, catalytic reformer/shift qualification or industrial
yield prediction. Shared existing native physical cores remain preferred over
new duplicate solvers. MHC compressor data qualification strengthens the existing
observation foundation without adding a completed compressor family. Request015
specifies the native capability and measurement prerequisites for the next level.

## Current measured-production checkpoint

The initial P5 electrochemical data path now includes a full-member measured PEM audit,
explicit DC/frequency grouping and native small-signal circuit estimation using the
existing observation/SVD framework. Conditional whole-sweep and fixed-coefficient
cross-cell failures are retained. This advances one electrical observation level; it
does not complete thermal inventory, gas crossover/recombination or degradation. Those
require separately qualified boundaries and identifiable observations. The catalog
at that checkpoint had 72 families with sixteen partial executable levels and twelve
additional native-adapter checks; the full research objective remains active.

The P4 pool continuation now reuses an actual native spreading/evaporation engine and
advances finite ground-input and conservative vapor-interval contracts. Independent
input checks, a retained native clock failure, explicit bounded boundary correction,
coarse/fine numerical comparisons and source-mass accounting are executable. The related
share-alike experiment attachments remain withheld by the default data policy. Para
properties, radial restart, source geometry/momentum, independent heat and experimental
qualification remain explicit receiving/research work, without inventing jet deposition.

The P4 gas continuation now connects the one shared nozzle to actual native DEGALI
ambient-plane and calm-jet objects. Explicit effective-area pressure force, PH state,
spin/reference and vertical-frame contracts preserve the source boundary. A declared
profile-integrated buoyancy bridge retains the native solver. The short normal-H2 case
passes numerical gates; the cold para-H2 case retains a failed energy gate after four
refinements and is rejected. This raises native-adapter families to fourteen while
keeping sixteen other partial levels out of 72. Full outdoor dispersion, finite-source
clocks, phase-aware probes and experimental qualification remain open. Request 011
records the concrete receiving work; no second jet or choking solver is introduced.

The measured spatial-jet continuation now reads all 42 concentration worksheets and
conditions five calm sources through an inverse of the one existing nozzle. Native
energy-reference conditioning and phase-guarded Cartesian observation are independently
checked, without fitting concentration coefficients. Four finest numerical cases pass;
all five retain field-target failures and one retains a strict energy defect. The current
planning estimate is 25-35% of the full programme; 30/72 first executable families is a
separate coverage metric. PROGRESS.md keeps stage/requirement completion distinct from
data volume, test count and partial model availability. The full objective remains active.

## First coupled facility case

An outdoor liquid-hydrogen storage/supply network: tank, transfer line, pump, valves,
vaporizer and vent. Start with storage heat ingress and a defined transfer-line release,
then isolate the affected inventory and hand resolved source histories to qualified pool
and dispersion providers. Add fire/exposure after the source boundary is conserved.

The P5 carrier continuation now qualifies the acquired G4MP2 table at its gas-reference
conditions and adds finite prescribed-conversion material/heat accounting. Actual native
molecular checks cover 10373 rows / 10345 canonical pairs; 56 contradictory-pair rows'
heats are withheld, admitting 10317 reference-heat rows. Native Cantera species enthalpy
and a supplied-extent production example reuse the same thermochemistry engine.
This advances one partial carrier level: 17 implemented + 14 native-adapter families,
41 planned, out of 72. Liquid thermochemistry, catalyst kinetics, finite gas/thermal
dynamics and independent reactor evidence remain required. The full objective and
25-35% programme effort estimate remain unchanged.

User steering selects HyRAM for high-pressure gas dispersion and SLABx-LH2 for LH2-origin
dispersion. Current execution checks retain a HyRAM Gaussian-entry source mass failure
and a SLAB low-wind premise failure. DEGALI stays as explicit comparison evidence. Extend
and qualify the preferred source boundaries under request012; do not hide source gaps by
switching providers. Parallel work on measured enclosure-data qualification, native frozen
mixture properties and finite open gas-control-volume balances continues the full scope.
These work items are not counted as complete merely because they have been dispatched.

The parallel continuation completes first native frozen-mixture and finite open-volume
reference levels plus full qualification of the acquired pressure recorder files. That
adds two partial catalogue families: 17 implemented + 16 native-adapter checked, 39 planned,
out of 72. Open-volume pressure response is a thermodynamic reference; preferred native
HyRAM/SLABx dispersion remains separate. No new measured validation is inferred from
bulk recorder row counts or numerical conservation. Independent source/clock/phase and
field evidence, remaining equipment/production/fire/integrity models and full facility
composition still define the requested programme scope.

The next equipment/storage checkpoint advances two first executable families:
native vacuum insulation and native staged gas compression. Closed finite gas/solid
hydride inventories deepen the existing storage.hydride_dynamic family without
inventing another family or a duplicate kinetic model. The complete AB2-channel
profile retains 365402 source rows in seven sheets and separates derived summaries.
Catalogue counts become 17 implemented + 18 native-adapter checked + 37 planned =72;
first executable coverage is35/72 (about49%). Overall programme effort remains an
uncertain25-35%; numerical authored checks do not complete source-specific validation.

Continue with unresolved facility equipment (relief/vent/exchanger/recovery and
instrumentation), qualified source-specific material/equipment data, additional
production/separation and fire/integrity levels, and the conserved accident chain.
Request013 specifies native receiving gaps for the now concrete insulation and
compression contracts. Preferred dispersion failures/request012 remain open.

Pressure protection, vents, recovery and instrumentation now add four partial first
native levels:17 implemented +22 native-adapter checked +33 planned =72,39/72 first
executable families. Programme effort is re-estimated at30-40% after this wider
equipment/control/observation foundation, with the full objective unchanged. These
are authored native/interface/conservation checks, not sizing/certification or
independent measured qualification. Request014 defines remaining native state,
thermal/acoustic/capacity/cold-clock and observation-identity capabilities.

Continue toward a conserved facility/accident chain with explicit source-plane
ownership and qualified measured observations, while adding remaining exchanger/
cryo-compressed/production/separation/fire/material-integrity levels. Do not hide
preferred HyRAM/SLAB source/applicability failures or treat a bulk vent PH state
as another solved nozzle plane. Independent data and appropriate physical fidelity
remain exit conditions throughout the original plan.

## Fire and contents-heat continuation

Conditional native unconfined peak blast and fixed-mass two-phase contents heat
advance first executable coverage to44/72:17 partial implementations,27 checked
native levels and28 planned families. The programme effort estimate stays30-40%.
Actual native Flame diagnostics add evidence and an actionable receiving request
but no accepted fire family because mass/caloric gates fail under refinement.
The complete thermal observation collection is ingested with unresolved clock/
sensor roles preserved. Next work keeps source conservation, actual incident/wall
heat allocation, independent experiment qualification and the remaining full
facility/accident scope; neither a diagnostic kernel nor data volume closes it.

## Native cryogenic and finite spherical-storage continuation

First-level coverage is46/72:18 partial implementations,28 checked native
adapters and26 planned families. The uncertain full-programme estimate remains
30-40%. Cryo-compressed storage reuses the existing native fluid/wall/event/nozzle
owners; microspheres reuse the existing mobile/trap solver and native finite-gas
properties. Source-qualified parameters, experimental validation, coupled thermal
and mechanical storage behavior and the full facility chain remain required.

Temperature-dependent rotor calorics deepen the existing spin family without
a second trajectory ODE or an evolving-spin liquid EOS claim. Complete biological
observation qualification precedes a growth model: the acquired fermentation
workbook does not establish biomass, substrate species, independent replicates
or gas-reference conditions. Request017 records native driver/property/event,
material and biological prerequisites. The full staged objective remains active.

## Spectral production, multiphase conversion and cyclic separation

First-level coverage advances to49/72:19 partial implementations,30 checked
native adapters and23 planned families. The uncertain full-programme estimate
remains30-40%. Three formerly planned levels now execute: photon-accounted
prescribed-yield chemistry, native finite gas/solid equilibrium and native warm
multibed pressure cycles. These do not complete photocatalytic mechanisms,
heterogeneous reactor kinetics or source-qualified purification equipment.

The TiO2 source profile now consumes every reviewed text member and preserves
unknown units/axes, reconstructed rate/AQY, duplicate members and shared controls.
Optical/catalyst/apparatus inputs still need qualification before a comparison.
Native HP candidate failure and synthetic PSA non-enrichment remain visible.
Request018 records native object/step/phase and photon/measurement prerequisites.
The full staged objective, remaining families and independent validation remain active.

## Membrane and staged thermal continuation

The next bounded P5 separation/production increment reuses native porous-gas
transport and gas/pure-solid calorimetry, with shared finite staged reactions.
A two-point transport closure precedes finite feed/permeate/retentate coupling.
Prescribed cycle heat/material ledgers precede source-qualified phase stability,
kinetics, separation/pressure work, heat recovery and utility qualification.
Native biological calculation remains separately admitted by actual source and
finite liquid/headspace numerical evidence. Request019 specifies receiving
capabilities; writing it does not implement them. The full programme stays active.

## Finite compression, separation and uncertainty continuation

P3/P5 now move from constitutive/closed inventories to actual finite membrane
and hydride-compression assemblies. Keep source/receiver depletion, gas/solid
reference work, heat duties, loading/CSS and native event limitations explicit.
P6 material observations are qualified before choosing a fracture law. P7 uses
independent-input native uncertainty around existing deterministic model APIs;
source covariance, structural error and frequency/risk qualification remain open.
Request020 carries native/event/thermal/statistical and material-data receiving
requirements. The complete original programme remains active.

## Safety endpoint and scenario continuation

P6 now adds actual native CJ/frozen-shock endpoints and supplied receptor dose/
response; P7 connects declared source, exposure and frequency to a native single-
LOC risk record. Keep endpoint/field, incidence/absorption, rate/probability,
source/field window and conditional/facility scope distinct. Native internal
search/trial limitations and mechanism bounds stay explicit. P0 qualifies all
acquired BLEVE signal files before any apparatus comparison; those experiments
lack the homogeneous premixed-state evidence for direct CJ validation.
Request021 records native API/search/state, exposure-calibration, source-data
and risk-object receiving capabilities. Complete remaining physics, independent
evidence and conserved full facility/accident composition remain the goal.

## Finite O2, cold-side state and monitoring continuation

Implement the oxygen-displacement part through the existing finite species/
energy owner, with exact source commands, native state/reference compatibility
and independently checked mixing/pressure/heat limits. Keep ordinary-air native
multisegment thermal state separate from H2-rich/cold contact/injury physics.
Reject inconsistent native air-phase diagnostics and specify receiving fixes.

Connect actual physical/instrument observations to native learned causal mode
monitoring with independent fitting/calibration/evaluation and original failures.
Acquire and inspect complete ELVHYS4.2 files before any apparatus comparison.
Unresolved clocks/locations, processed H2 traces and absent O2/source mass-flow
measurements remain qualification gaps. Request022 gives concrete next native
and source-data capabilities; remaining13 planned families and the unqualified
levels inside executable families remain part of the full objective.

## User priority change: code now, validate later on Nurion

On2026-10-28 the user explicitly deferred local tests/replays/benchmarks in
favor of parallel implementation. Three disjoint lanes now implement native
PV/directDC electrolysis, native-law finite fracture growth and shared-kernel
finite solid reactions. They are implemented_unverified, not accepted runtime
capabilities.22 scientific case definitions and a metadata-only PBS preparation
API are supplied for later cluster execution; none has been run or submitted.

Track coding coverage separately:62/72 families have some implementation code,
including3 unverified increments. Last actual executable first-level evidence
is59/72 at6eae06c. The full objective and scientific acceptance principles are
unchanged; verification and independent qualification have been scheduled later,
not removed from completion. No additional local suite or installation replay
should start until the user's execution preference changes.


## Parallel coding continuation — 2026-10-28

Four additional partial families have code: conditional finite pool fire,
HELPR vessel-failure initiation, physical-window/native hydrogen economics,
and saturated parcel transport. All are `implemented_unverified`. Coding
inventory is66/72 (about92%):21 partial implemented,38 historically checked
native adapters,7 unverified and6 planned. Last executed coverage remains59/72
(about82%) at6eae06c; full-programme effort remains an uncertain30-40%.
No local scientific execution, benchmark, test, build or remote submission was
performed for this continuation. Old1088pass results do not validate new code.

The new19 deferred cases comprise8pool fire,4vessel,5economics and2parcel cases;
the combined pending campaign has41 cases. Native HELPR vessel cases reuse the
fracture profile. Pool, economics and parcel profiles require separately declared
cluster interpreters/setup files; the example plan has no guessed login/queue.
No cluster connection or `qsub` was attempted.

Read [POOL_FIRE.md](POOL_FIRE.md), [VESSEL_FAILURE.md](VESSEL_FAILURE.md), [HYDROGEN_ECONOMICS.md](HYDROGEN_ECONOMICS.md) and
[DROPLET_TRANSPORT.md](DROPLET_TRANSPORT.md) for contracts. Incident liquid is not pool deposition;
wall-failure initiation is not a hole or blast; supplied ignition/burn flux is
not a predictive pool-fire solver; explicit annual financial inputs are not
inferred product sales. ProFAST was rejected on redistribution/use terms;
optional pyH2A is statically reviewed and remains unexecuted. Request024
records native API and qualified-data work for other sessions.


## Cavern, microbial cell, impact and material front — coding checkpoint

Four further partial first levels now have code: actual UH2SC cavern/rock audits,
native-electrode finite microbial electrolysis, finite surface-impact phase and
mechanical energy, and a native premixed material-path front reference. All are
`implemented_unverified`. Code inventory is70/72 (about97%):21 partial implemented,
38 historical native-adapter checks,11 unverified and2 planned. Last executed
coverage remains59/72 (about82%) at6eae06c. Full-programme effort remains an
uncertain30-40%; more code does not establish independent physical validity.

New21 deferred cases comprise4underground,5microbial,8impact and4front cases.
The combined pending campaign is62 case definitions. No model, example, case,
test, replay, benchmark, build, installed replay or cluster job was executed.
The static syntax/lint/source/license review is not numerical acceptance.

UH2SC's suspected GHE indexing/capacity/energy conventions are retained for strict
independent rejection rather than patched. Its well is ideal/prescribed-flow,
not a finite well inventory. MEC organism/activity/thermochemical data remain
qualified caller inputs. Impact contact/outcome data and a continuous finite-wall
pool handoff are unresolved. The front is a material-frame discrete reference,
not lab flame propagation, obstacle flow or a person heat-injury prediction.
Preferred HyRAM gas and SLABx-LH2 liquid-origin ownership remains unchanged.

Read UNDERGROUND_STORAGE.md, MICROBIAL_CELL.md, DROPLET_IMPACT.md and FLASH_FRONT.md.
Request025 records specific native APIs, evidence and coupling work. CORA DOI
10.34810/data2866 is acquired with publisher hashes and an audited ODS schema;
the observations support electrode research only, not whole-cell MEC validation.
Raw files remain outside release artifacts pending review of file-specific rights.

The remaining planned families are obstacle-resolved dispersion and accepted
jet fire. Every partial family also retains the limits in MODEL_CATALOG.md;
70coded families are not70complete models. Last full installed-artifact audit
remains785dae7; later source/artifact acceptance is still deferred.


## New unexecuted integration interfaces

Read [OBSTACLE_DISPERSION.md](OBSTACLE_DISPERSION.md) for actual optional FDS
case/mesh/source/process/ledger interfaces, [JET_FIRE_CONSERVATION.md](JET_FIRE_CONSERVATION.md)
for rejected-native-path energy diagnostics, [MICROBIAL_ECONOMICS.md](MICROBIAL_ECONOMICS.md)
for the actual MEC-to-existing-cost-owner bridge, and [CLUSTER_EVIDENCE.md](CLUSTER_EVIDENCE.md)
for read-only selected-result reconciliation. These source additions have not
been executed. The76pending case definitions do not establish model accuracy.

Request026 specifies native reacting-establishment/chemistry/radiating-energy,
CFD build/runtime/source boundaries, a provider-neutral cost protocol, public
MEC geometry/result verification and separate campaign acceptance. Source/plan,
clock, material, phase and energy-reference ownership remain explicit. Preferred
HyRAM/SLABx ownership is unchanged; no failed native prediction is promoted.

Current unexecuted API checkpoint: see CANTERA_FACTORY.md, HYDROGEN_ECONOMICS.md, MICROBIAL_CELL.md and MICROBIAL_OBSERVATIONS.md; execution status is recorded in PROGRESS.md.

Request027 specifies the missing native HELPR interface for nonuniform radial
thermal-stress crack driving, including total-field/no-double-count semantics,
flaw orientation, bounded time reconstruction and independent SIF/refinement
acceptance. The current radial-to-HELPR bridge passes scalar wall temperature and
pressure history only; it is not a thermal-gradient crack-driving model.

The next cluster campaign also includes producer-issued PV results, finite
LOHC/ammonia conversion and withdrawals, LH2 compressor/exchanger provenance,
and facility alarm-to-action/source/risk bindings. See RESULT_PROVENANCE.md,
LIQUID_CARRIER_AMMONIA.md, NATIVE_COMPRESSION.md,
NATIVE_HEAT_EXCHANGER.md and FACILITY_PROTECTION.md. These additions preserve
existing kernels and do not add a duplicate solver or model family.

The parcel-population finite-impact deferred case has a local fixture correction
after Hangang job 1185904 found no ground-crossing event in the prior launch setup.
The lower/faster synthetic trajectories preserve the native applicability checks
and create distinct contact times; job 1185906's sensor-rejection case now returns
an explicit deferred outcome. Include both in a fresh source capture before retry;
they remain unverified contract changes, not physical qualifications.
The next Nurion campaign also includes exact provider selection, finite fuel-cell
composition, finite source/receiver transfer and thermal-utility allocation.
These add27 deferred definitions (133 total) without changing the72-family catalog
or the uncertain30-40% programme estimate.
Finite adsorption-vessel accounting, valve actuation, relief lift/pickup and
facility node continuity add25 more deferred definitions (158 total). They deepen
P3/P7 composition without adding a duplicate EOS, nozzle or network solver.
Pump/compressor map admission, flowing heat-exchanger ports and reliquefier
product recovery add25 deferred definitions (183 total). These deepen P3 while
retaining native equipment ownership and the uncertain30-40% programme estimate.

The PBS generator now exposes the exact pinned `scripts/` directory after `src/`
on worker `PYTHONPATH`, because Hangang jobs 1185918/1185919 showed that the
finite-supply risk helper needs to import a sibling script module. Package-source
precedence remains `src` first. The source-level generator contract records this
order. Include the correction in the next pinned campaign before retry; it is not
risk-model verification.

Follow-up implementation corrects the porous-reservoir schedule contract: initial
pressure is per radial cell and validated against geometry at execution, while
well-flow samples still exactly match the strictly increasing time samples and
pressures remain positive/bounded. It also fixes the fuel-cell exchange freshness
fingerprint to bind its retained mapping proxies instead of constructing temporary
mappings whose identities change across checks. Hangang 1185898 has a reported
currentness issue, but the latest available remote attempt metadata is still running
with no outcome. Both fixes require a fresh capture/retry and do not qualify either
physical model.

## Caloric gas-pipeline transients

Implemented an explicit 1-D caloric Euler pipe-wave solver with a pluggable
single-phase rho-u closure, reflective ends, fixed ghost-reservoir option,
and geometry/clock/provenance-preserving trace. Status: implemented-unverified;
two Hangang contract cases are registered and deferred. No scientific tests or
calculations were run locally. Independent pipeline/decompression validation,
wall heat/friction, finite source depletion, detailed junction losses and phase
transitions remain planned gaps. See `CALORIC_PIPE_WAVES.md`.

A distinct branched-network level now advances several caloric pipe edges on one
CFL-limited clock and closes zero-volume, adiabatic perfect-mixing nodes with a
bounded common-pressure/temperature solve from the exact applied mass and
total-energy face fluxes. It also rejects negative entropy generation. The
network trace retains topology, geometry, boundary states and evidence IDs.
Three synthetic Hangang contracts cover equal-state equilibrium, unequal
temperature mixing and a fixed terminal reservoir; all remain deferred. This
level does not model finite node storage, momentum closure, tee losses,
friction, wall heat, phase change or measured-network behavior. See
`CALORIC_PIPE_NETWORK_WAVES.md`.

A finite-capacity lumped wall has now been coupled to the single-pipe caloric
Euler solver. The wrapper consumes accepted gas wall-heat integrals, advances
wall energy, and supports constant ambient UA with an analytic lumped update.
The model uses first-order operator splitting and its synthetic Hangang
energy-balance case is registered but deferred. It does not model wall axial
conduction, branches, or finite endpoints; see
`CALORIC_PIPE_FINITE_WALL.md`.

A fixed-state hydrogen compartment network now advances H2 and inert-carrier
mole fractions across caller-declared room-to-room and exterior streams. Each
room derives its total ideal-gas moles from fixed P/V/T and rejects interval
schedules whose molar in/out rates do not balance. Exact piecewise-constant
matrix-exponential updates retain species-wise external ledgers and residuals;
a numerical failure retains the last completed output prefix. The synthetic
Hangang contract is registered and deferred. Prescribed flows do not imply a
pressure-driven vent, buoyant, or exposure model; see
`HYDROGEN_COMPARTMENT_NETWORK.md`.
