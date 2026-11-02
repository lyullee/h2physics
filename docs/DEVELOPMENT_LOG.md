# Development record

## 2026-11-02 — 78-family representative input checks

Added three focused input-contract suites. Final combined execution: 162 passed in 10.37 s, comprising 161 malformed-input rejections across 78 exact family identities and one manifest invariant; no failures/errors/skips. Normal baselines and relevant exception/message matching prevent generic errors from counting as successful guards. The initial split executions revealed only test-message regex mismatches; the product already rejected those inputs, so no production guard was patched. Source hashes for 419 Python files were unchanged before/after the final run. The campaign does not compare physical predictions or execute complete native process simulations. Exact cases and replay command are in INPUT_CONTRACT_CAMPAIGN.md.

## 2026-11-01 — final content check for native-pipe checkpoint

After the mixture repair the public-tree hygiene audit passed for 1510 files,
and scoped Ruff/diff checks passed. This is a content check, not rights
clearance. Native-pipe delta preparation uses the last remotely verified
02574687 base directly; its receipt must be inspected before any transfer.
The acquired-data metadata check still fails on the single documented Bath
license URI field. All scientific handles from this checkpoint are terminal.

## 2026-11-01 — frozen-mixture actual-use repair

Both native mixture linepack and pressure-wave constructors failed before the
fix with `AttributeError: PropertyBasis has no attribute provider`. The
isothermal wrapper now retains the existing reference ID, fluid/spin values and
composition in a portable identity, with separate native-owner/method snapshots.
Scalar basis snapshots also reject in-place reference/spin edits; the mixture's
unresolved H2 spin is preserved. No pure-fluid EOS section or thermophysical
mixing implementation was added. Final execution passed the two existing native
cases, seven focused definition tests in 20.97 s and scoped Ruff. Details and
physical limits are in REAL_GAS_LINEPACK.md.

The HRS and PEACE metadata repairs were rechecked together: the collection has
zero parse failures, and the acquired-data metadata gate now reports only Bath
cryogenic-kinetics license_url as missing. That known failure remains visible
in DATA_MANIFEST_AUDIT.md; a primary record rights statement is not relabelled
as a distinct license URI. Raw/source response caches remain ignored.

## 2026-11-01 — same-level native pipe integration and provenance checkpoint

The existing quasi-steady network now combines native cell pressures with the
generalized native Darcy function. Final native/legacy cases and cold imports
passed; 17 rejection gates, real maximum-step refinement and inventory-floor
localization are recorded in ISOTHERMAL_GAS_PIPE_NETWORK.md. The executable
fluids/CoolProp example passed at 10/9.9/9.8 MPa, with final absolute pressures
9976693.87224/9900081.74310/9823175.60586 Pa and maximum mass residual
2.22e-16 kg. The example keyword was corrected to the actual public
`maximum_step_s` and then executed. The hydraulics module header was clarified
after scientific execution; only its explanatory docstring changed, while the
executed-function bodies and strong-reference input/results remain unchanged.
Scoped Ruff and diff checks passed; the public-tree audit passed 1509 files.

The 2ce3f34c linepack delta was reconstructed locally using the exact remote
apply code and verified against its target manifest. No shared SSH connection
was opened and no remote transfer/submission occurred. Newer native pipe work
postdates this immutable delta and needs a later source pin before HPC replay.

Primary-response metadata repairs pinned separately dated HRS website HTML and
PEACE repository API bytes without replacing old measurement receipts. The
current acquired-data metadata check still fails on Bath cryogenic-kinetics
license_url alone; primary review found no distinct license link, so none was
invented. Parse failures are zero. These checks do not close file-level rights
or independent model/data qualification. The additional friction-data candidate
is excluded from hydrogen pipeline validation due to missing geometry/composition,
transient observations and unambiguous experimental-data rights.

## 2026-11-01 — native electrolysis charging and unified source withdrawal

Extended the existing electrolysis charge API to the existing real-gas linepack
owner, retaining matched CoolProp HEOS fluid/spin/reference/native definitions.
The supplied storage-energy change is now checked against native endpoint
`m*u` for this route. No source enthalpy path, transfer equipment or temperature
controller is inferred. The native and explicit analytical cases both passed
after sealing nested ledger scalar values; a balanced +100/-100 J post-issue
edit is rejected. Native delivered mass was 5.2876778369e-5 kg, final pressure
11300.6308741 Pa, storage change 142.8516765963 J, mass residual 2.71e-20 kg
and energy residual 0 J. See ELECTROLYSIS_LINEPACK.md for source/transfer scope.

Unified `advance_linepack_to_source` now dispatches native inputs to the existing
real-gas source adapter with an explicit matching property provider. Its full
source-to-fuel-cell case passed: 0.2 kg withdrawal, final pressure
4860514.24137 Pa, mass residual 1.67e-16 kg, energy residual 1.46e-11 J and
15 boundary/provenance rejections. The existing independent native-path
quadrature remains caller evidence, not an inferred production energy path.

Scoped Ruff passed across all four changed adapters and their validation
modules. Metadata regeneration found 353 current Hangang cases/41 profiles and
415 legacy Nurion-plan cases/59 profiles/114 modules; no jobs were submitted.
The AST API index remains 362 modules/1807 public definitions. The public-tree
audit passed for 1506 files; it is content hygiene rather than rights clearance.
Overall effort remains estimated at 30–40%; catalog status remains 57/82
classified (20 implemented, 37 native-adapter-verified, 25 unverified).

## 2026-11-01 — two-vent buoyant-layer contract

- Hangang job 1189567 passed the registered synthetic two-vent H2 buoyant-layer
  case on pin 5ai. H2 mass and vent-flow residuals stayed below `1.58e-16 kg`
  and `3.47e-17 kg/s` in the declared still-air, fixed-ambient, one-way-vent
  regime. This did not use experimental data.
- Prepared a separate three-case array for competitive Langmuir equilibrium,
  power-law solubility/diffusion and k-of-n detector reliability. QOS had five
  user jobs running and refused a singleton Langmuir submission; no job was
  admitted for the three-case array. Submit it as capacity opens.

## 2026-11-01 — validation inventory synchronization

- Rebuilt the generated deferred-case inventory from metadata catalogs only:
  407 case definitions across 59 profiles and 110 modules. No entrypoint,
  model, native engine, scheduler or Nurion job was run.
- Fixed the unmatched closing parenthesis in `validation/cases/vessel_failure.py`
  that blocked catalog import. Added the missing `material-transport` profile
  and four case modules to the Nurion example plan; it remains a configuration
  template and was not executed.
- Added ownership mappings for six implemented-unverified catalog families and
  moved `quasi-steady-permeation-history` from the stale fracture profile to
  the current material-transport profile. The metadata generator completed and
  refreshed `docs/NURION_VALIDATION_PLAN.md`.
- Registered `hydrogen-diffusion-surface-film-boundary` in the Hangang case
  plan and aligned it to the existing `material-transport` profile. It uses
  synthetic coefficients and awaits a fresh pinned Hangang contract run.

## 2026-11-01 — compartment-network case correction

- Hangang job 1189474 failed before the species-ledger and rejection checks
  because the case required positive adjacent-room hydrogen at all output times,
  including the initial state whose declared fraction is zero.
- Changed only the deferred fixture assertion to inspect the final requested
  sample after transport. Static equation review found the expected fixed-`P/T`
  species ODE and matrix-exponential transport path; no source model change was
  made. A fresh pin and Hangang retry are still required.
- The model remains limited to ideal-gas fixed-state, well-mixed compartments
  with caller-prescribed balanced flows; it does not establish real ventilation,
  buoyant dispersion, stratification or facility safety performance.

## 2026-10-31 — PEM current-ripple source reader

- Acquired the Mendeley v2 archive under its CC BY 4.0 declaration and verified
  the publisher-listed 90,759,411-byte SHA-256 receipt. Rights attribution and
  source metadata remain in the research manifest; the archive is not a release
  artifact.
- Added streamed, source-bound readers for unaveraged IV measurements,
  timezone-naive continuous current/voltage logs and the separate reported-fit
  table. CSV members are read inside the ZIP without extracting multi-hundred-MB
  logs; exact source tokens remain streamable, member hashes are retained, and
  observed intervals are not resampled or gap-filled.
- Explicitly left area, cell temperature/pressure, water conditions, sensor
  calibration, timezone and cross-cell alignment unresolved. Fit outputs are
  never treated as independent measurements. No process model was fitted or
  validated from this dataset.
- Added a synthetic Hangang parser/source-integrity contract. Ruff, AST parsing,
  and TOML parsing passed; no scientific test or model calculation ran locally.

## 2026-10-31 — fixed-state multi-compartment hydrogen transport

- Added a fixed-P/T well-mixed network for H2 and one inert carrier using
  caller-owned, directed piecewise-constant molar streams on one common clock.
- Total ideal-gas moles are derived from room P/V/T. Every room's total molar
  inflow and outflow must balance at each interval; no pressure-driven or
  buoyancy-driven ventilation is inferred.
- Matrix-exponential updates retain species-specific external in/out amounts
  and residuals. A numerical failure retains the completed time prefix.
- The synthetic Hangang contract is registered under the existing
  `oxygen-deficiency` profile and remains unrun. No local scientific tests or
  calculations were performed.

## 2026-10-31 — cluster profile inventory synchronization

- The source-generated profile manual had fallen behind the Nurion profile map;
  `gas-compressible-pipe` and `photochemistry` were missing from the curated
  capability declaration. Added both as core-only and regenerated the profile
  requirements from static AST/source reads.
- The generated inventory now accounts for 58 profiles and 113 source module
  associations. This is documentation inventory, not a model test or runtime
  qualification.

## 2026-10-31 — finite-hydride gas-port nozzle-history handoff

- Added an adapter that binds each accepted finite-hydride gas state to the
  existing shared nozzle source history, requiring the native outward-port
  ledger, compatible thermo basis, and explicit location, opening, backpressure,
  origin and evidence. Receipt currentness rechecks the owner trace, SciPy path,
  port transfer and nozzle samples.
- Registered the deferred `finite-hydride-nozzle-source-handoff` contract under
  Hangang `finite-hydride`. It checks the typed data bridge only; it does not
  validate a real tank release or downstream dispersion.
- No local tests or calculations were run.

## 2026-10-31 — finite-hydride nozzle/port mass closure

- The first adapter draft independently evaluated nozzle mass-flow samples
  without checking them against the finite-bed port's already integrated mass.
  That could produce incompatible storage and release inventories.
- Added caller-selected interval quadrature and evidence-bound absolute/relative
  tolerances. Every nozzle interval must now reconcile with its corresponding
  signed bed-port ledger; mismatches are refused. The contract case drives the
  bed through the same nozzle law, audits closure, and doubles opening area to
  verify mismatch rejection.
- This improves physical coupling integrity but remains unexecuted on Hangang;
  no tank-discharge or nozzle validation is claimed.

## 2026-10-31 — hydride shell-boundary contract hardening

- Extended the synthetic Hangang case for the AB2 external shell-temperature
  bridge to reject a cloned receipt with caller-substituted mapping evidence and
  direct boundary construction. The check remains scoped to source ownership and
  API integrity; it does not validate shell-to-bath physical applicability.
- No local tests or calculations were run.

## 2026-10-31 — offline Figshare receipt reconstruction for channel source bridge

- Added `dataset_from_figshare_bytes()` to parse staged original Figshare v2
  response bytes against an independently pinned SHA-256 without network access.
  It deliberately does not mint the online repository-resolution marker.
- Added an offline fixture for one separately hash-pinned channel ZIP and bound
  both source-backed channel cases to that fixture. Hangang case parameters now
  point at the external source attachment directory; raw publisher files remain
  outside the repository and package distributions.
- Updated the channel data manual. No local tests, imports or calculations were
  run; a fresh immutable Hangang snapshot and explicit data staging are required
  before the source-bound cases can execute.

## 2026-10-31 — steady permeation film/bulk resistance API

- Added `steady_permeation_with_surface_resistance()` for a one-dimensional
  steady linear chain of upstream film, Fickian bulk, and downstream film
  resistances. Equilibrium H2 fugacities map to the explicitly declared mobile
  carrier concentration; caller film transfer velocities use that same basis.
- The immutable result retains the signed flux, membrane-side concentrations,
  separate resistances and independent evidence identities. No surface
  reaction, coefficient fit or transient transport is inferred.
- Added the `steady-permeation-surface-resistance` deferred contract and
  updated API/catalog/source-methods docs. It has not been executed; all
  material parameters and independent permeation observations remain unqualified.

## 2026-10-31 — sensor calibration case outcome repair

- Hangang job `1185889` failed because the recovery entrypoint completed its
  calibration assertions but returned no explicit `ValidationOutcome`.
- The recovery case now returns generating/fitted time constants, residual RMS,
  boundary-limited fit status and immutable-sample rejection after its existing
  assertions. The rejection case also reports invalid-input and consumed-receipt
  rejection counts. The local correction is unverified pending retry; this does
  not establish sensor calibration.

## 2026-10-31 — carrier immutable-cache case correction

- Hangang job `1185860` (`carrier-original-binding`) failed when its deferred
  case called `cached.setflags(write=True)` on a bytes-backed immutable array;
  the expected `ValueError` was not caught. This is a test-harness/setup failure
  around the read-only cache contract, not a carrier-model failure.
- The case now expects write-enable rejection and verifies that
  `result.require_current()` still returns the unchanged result. This local
  correction is unverified pending replay; no scientific qualification follows.

## 2026-10-31 — latest verified Hangang snapshot

- Snapshot revision `9048413b68025235753242dcb93efb68d9afc477`; archive SHA-256
  `5a34abfd652c7dbe6ff6ba41ca7981082e42bffc70533e805c638ef33f99250c`
  (3,780,321 bytes); manifest SHA-256
  `9034a8102d3bbe6b53310ab122b5a359acb1d8918ba62dc065343999e10eb4ca`; all
  1,060/1,060 entries verified.
- `1185710` offline core-flood source ingestion passed metadata/listing hash
  checks and four staged workbooks. This is ingestion-only evidence, not physics
  validation. `1185709` CSTR entered and failed the fixed geometry/site-domain
  invariant after initialization and enthalpy fixes; the exact subcondition is
  under investigation, with no accepted CSTR pass. A local diagnostic patch
  separates volume, site-density, and temperature checks and reports native
  values without loosening bounds. Root cause is unknown; retry after a fresh
  snapshot. Both jobs used external logs.
- This snapshot predates the canonical Krg/Krw mobility guard and staged-turbine
  fixture correction; a newer capture is needed to evaluate those changes. From
  older `64a31`, jobs `1185715` (`thermal-target-domain`) and `1185716`
  (`impact-elastic`) passed synthetic/domain-contract checks with outcome JSON
  evidence; they are not independent validation. Earlier failures remain tied
  to their source snapshots.
- Completed `64a31` results: `1185718` (`thermal-target-exposure-history`)
  failed with ValueError because left-held history length did not match
  edge/interval shape; this is a case input/contract issue, not independent
  scientific validation. `1185727` (`impact-native-pool`) initially failed
  because optional dependency `dynamiclh2poolx` was unavailable; `1185752` later
  passed after exact pinned provider installation, for its deferred synthetic
  contract only, not physical qualification.
- `1185719` PIFIRA receipt, `1185720` impact-zero-contact, `1185722` impact-dryout,
  `1185723` impact-prefix, `1185724` impact-history-issuer-integrity, `1185725`
  impact-intercontact-heat, `1185726` impact-missing-heat, `1185729`
  impact-refinement, and `1185730` thermal-target-lossless passed deferred
  synthetic contracts. These passes are not independent scientific validation;
  logs are external.
- `1185735` failed because edge/sample fixture slices had unequal lengths;
  adjacent-pair indexing is corrected locally. `1185736` relief-lift-travel and
  `1185750` relief-lift-leakage failed because their plan omitted
  `fixture_factory`; a local fallback now uses reviewed native LH2DT protection,
  shared nozzle and native state objects with synthetic conditions, including
  wrong-native-state rejection, and remains unverified until recaptured.
- `1185737`–`1185740` failed phase-partition PQ component/mole consistency
  checks, not independent scientific validation. No physical qualification is
  claimed. Logs are external.

## 2026-10-31 — previous Hangang source capture (64a31)

- Verified complete source revision `64a31d2784b72f66d66a77accb01e18e3d711a4f`:
  archive SHA-256 `3811c36a140e38200a81c6b3d622a9ebb547d2d9350bcd36f8d5f9f1848216cb`
  (3,776,678 bytes), manifest SHA-256
  `7bc132d660b514a657068d1b2ad41d6a417849730812437b78eb0fb32583ac1a`,
  1,060/1,060 verified entries and zero raw/processed data.
- Jobs `1185638` (CSTR) and `1185639` (core-flood source ingestion) completed
  but failed after case entry: the Cantera controller was not initialized
  before reading `mass_flow_rate`, and numeric Mendeley version input was
  rejected because a string was required. Local fixes are in progress.
- Jobs `1185646` (mobility) and `1185647` (staged turbine) were accepted after
  initial QOS refusal; results remain pending. Qsub logs/results are outside the
  source tree. Failures against older source `8105` remain historical and do not
  describe this complete snapshot.
- Job `1185687` (`thermal-target-pulse`) passed its deferred synthetic energy
  ledger on `64a31` with maximum residual about `1.14e-8 J`; no scientific
  qualification follows from this synthetic contract. After QOS reopened,
  `1185698` (`thermal-target-domain`) and `1185699` (`impact-elastic`) were
  accepted, with results pending and logs outside the source. Initial QOS
  refusals had no job IDs.
- Jobs `1185661` (`hydrogen-brayton-staged-cooling-pressure-rejection`) and
  `1185662` (`hydrogen-brayton-staged-cooling-evidence-rejection`) were accepted
  from this verified snapshot; results are pending.
- Outcome correction: `1185638` and `1185639` completed with case-entry failures
  (controller was not initialized before reading `mass_flow_rate`; numeric
  Mendeley version was rejected because a string was required). Local fixes are
  in progress. `1185646` failed its synthetic mobility role-rejection assertion,
  now fixed with canonical Krg/Krw phase guard. `1185647`, `1185661`, and
  `1185662` failed before staged-turbine scenario checks because the fixture
  supplied a callable to `run_open_cycle_brayton` instead of a native phase; the
  fixture is corrected locally, not yet replayed. `1185664` and `1185665` passed.
  Four passes total (`1185448`, `1185452`, `1185664`, `1185665`) do not establish
  scientific/source/equipment qualification. `1185550`/`1185557` were launch-
  only log pollution failures against `8105`; external log paths now work.

## 2026-10-31 — Hangang outcome update

- `1185448` thermal-variable and `1185452` fragment entered their cases and
  passed. `1185450` entered CSTR and failed because the installed Cantera
  surface lacked `getPartialMolarIntEnergies`. `1185453` entered core-flood but
  failed importing `validation.fixtures.hydrogen_core_flood`; ingestion did not
  begin.
- Jobs `1185507`, `1185550`, and `1185557` were accepted from older source
  snapshot `8105`. `1185507` entered the synthetic mobility contract and failed
  exact float equality; no physical/source evaluation occurred, and this is now
  fixed with `isclose`. Jobs `1185550` thermal-lossless and `1185557`
  impact-baseline did not enter their cases because PBS logs polluted the
  repository and broke its pinned manifest. This is a packaging/launcher issue,
  not a model failure on older source `8105`. Future logs are written outside
  the source tree. The complete corrected snapshot is now captured and verified
  as documented above. No full scientific qualification is claimed.

## 2026-10-31 — publisher-bound receipt replay

- Receipt replay now requires a repository-issued `Dataset` from
  `resolve_dataset(seed)`; editable receipt fields cannot independently grant
  rights or redirect downloads. Replay validates dataset/version/license and
  metadata identity, supporting-metadata digests, every publisher-listed file
  URL/checksum/size, local paths, completion states and byte totals before it
  creates the cache directory.
- `scripts/replay_data.py` resolves the curated catalog seed before replay. The
  existing `dataset-rights-license-identity-integrity` deferred case now checks
  forged dataset/rights/attachment claims, budgets and cache links through the
  stronger API. No new case or module was added, so structural case/API counts
  are unchanged. No test, import or download was run for this change.

## 2026-10-31 — CC BY 4.0 H2/water core-flood observations

- Acquired four publisher-listed workbooks for DOI `10.17632/rfhf7wjydn.1`
  (three H2 drainage/imbibition stages plus an N2 reference). The data record
  states CC BY 4.0; all four downloaded sizes and SHA-256 digests match the
  publisher listing. Raw files remain in the ignored acquisition cache.
- Added a source-bound reader that exposes original `Kr` worksheet values,
  native headers, and workbook/sheet/row identities. It does not convert units,
  rescale or average saturation, fit curves, or assign model meaning to unclear
  cells. The offline parser receipt and source manual retain the provenance.
- Added `mendeley-hydrogen-core-flood-source-bound-kr-tables` to the shared `source-data-ingestion`
  profile in both cluster plans. It remains unexecuted and does not qualify a
  relative-permeability model. The latest inventory is 371 cases, 56 profiles,
  and 105 modules.
- Added `CoreFloodBranch`, `CoreFloodMobilityPoint`, and
  `build_core_flood_branch` as an implemented-unverified adapter for one explicit
  gas/branch/flowing-phase combination. It requires exact source headers, declared
  field roles, units, bases, scale factors when needed, evidence, and positive
  phase viscosity. It retains raw values and source row identities, interpolates
  linearly only within strictly monotone observed saturation, and seals results
  against source mutation. The synthetic deferred contract
  `core-flood-branch-specific-relative-mobility` is enrolled under
  `source-data-ingestion`; real field semantics and viscosity inputs remain to be
  reviewed, and no measured-data fit has been performed.
- Hangang archive 341c is verified. Initial launch 1185219 failed before case
  entry because only Slurm identity variables were present.
- Follow-up status: 1185237 also failed before case entry because selected-case
  array indices were checked against the full plan. Both launch defects are fixed
  in the source generator; neither failure produced a scientific result.
- The three-case array was refused by QOSMaxSubmitJobPerUserLimit. A one-case
  `thermal-target-variable-capacity` job 1185303 was accepted but failed before
  case entry because the source archive omitted `src/h2physics/data`. No model
  ran. The capture filter was corrected to exclude only ignored raw data, and a
  complete snapshot is being prepared.
- A static review found a missing site-fraction residual assignment in the CSTR
  flow path. The code now computes and gates the site residual, preserves its
  tolerance in the issued trace, and rechecks the native wall/controller links.
  The verified 37752360 archive predates this repair, so only non-CSTR cases may
  run from it. No tests or model calculations were run locally.
- Latest structural counts: 371 cases / 56 profiles / 105 modules; 1,455 public
  API definitions / 241 modules; 1,748 bound relative imports with zero missing
  or unresolved; 3,941 Markdown links / 340 files with zero missing; and Hangang
  97 cases / 19 profiles / 36 modules. Hangang snapshots 341c and 37752360 are
  remotely checksum-verified but incomplete. Snapshot 13e720 is an incomplete
  local candidate, not a remotely verified complete source. No case ran from
  those snapshots. An earlier summary of the latest case outcomes was superseded
  by the outcome JSON audit: jobs 1185448 and 1185452 entered and passed; 1185450
  entered CSTR then failed on unavailable Cantera surface method
  `getPartialMolarIntEnergies`; 1185453 entered core-flood then failed importing
  its absent fixture before ingestion. The passing cases do not provide full
  scientific qualification. A fresh complete snapshot is pending.

## 2026-10-30 — variable-capacity thermal target and flowing catalytic CSTR

- Extended the lumped thermal-target contract to accept a caller-owned total
  heat-capacity function `C(T)`. The state equation uses the local capacity and
  the stored-energy ledger integrates `C(T)` over the temperature change.
- Added a finite-feed ideal-gas catalytic CSTR path built from native Cantera
  mass-flow and pressure-control devices, with an explicit finite thermal wall.
  It checks sampled gas-plus-adsorbate element/mass/energy budgets on the declared
  output grid. Port quadrature remains grid-dependent; no catalyst bulk thermal
  storage, pressure-drop model, packed bed, or plug-flow behavior is claimed.
- Added synthetic deferred contracts, focused API documentation and enrollment
  in the Hangang/Nurion source plans. The current metadata inventory is 368 cases,
  55 profiles and 103 modules. Both new model levels remain
  `implemented_unverified`; neither has run locally or on a compute node yet.
- Parallel static metadata refresh reports 1,442 public definitions across 238
  modules, 1,736 bound relative imports with no missing/unresolved bindings, and
  3,912 resolving Markdown links across 338 files. Public-tree hygiene audit
  passed over 1,050 files; this does not establish licensing clearance.
- Hangang rolling submission continues against a fresh immutable source copy.
  Existing unrelated and earlier wave jobs are not modified; each new batch must
  be tied to its exact source and case plan before submission.

## 2026-10-30 — conditional fragment flight and ground impact

- Added a downstream fragment trajectory owner for caller-specified mass,
  projected area/drag law, launch state, gravity, density and wind. Deterministic
  DOP853 integration terminates at the descending ground event, including the
  localized impact endpoint, and retains drag impulse/work plus momentum and
  mechanical-energy residuals.
- Registered `conditional-fragment-flight-impact` in both cluster plans and
  documented that fragment generation, changing geometry/drag, structure strikes,
  injury/facility effects and rupture frequency are outside this conditional
  flight level. Status is `implemented_unverified`.
- The regenerated inventory is now 369 deferred cases, 56 profiles and 104 case
  modules. Static API inventory contains 1,448 public definitions in 239 modules;
  relative-import audit has 1,738 bindings with no unresolved/missing symbols.
  Scientific execution remains deferred to Hangang.

## 2026-10-30 — staged turbine cooling boundary

- Added `StagedTurbineCoolingInputs` and
  `run_staged_turbine_cooling()` around an issued native Brayton combustor state.
  Caller pressure/efficiency schedules and stage coolant flow/enthalpy rise are
  explicit; Cantera supplies frozen-composition stage expansions and perfect-mix
  station properties.
- Each stage retains inlet, expansion and mixed states, shaft work, coolant heat
  pickup and mass/enthalpy mixing checks. The full boundary recomputes total mass
  and first-law closure and seals the native terminal state.
- Three deferred synthetic cases were added to the Hangang and Nurion plans.
  They have not been run. The model does not resolve blade metal, film cooling,
  local passage flow or heat-transfer coefficients; turbine qualification and
  independent experimental comparisons remain open.

## 2026-10-30 — native hydrogen fuel-compression reference

- Added a single adiabatic pure-H2 compressor stage using caller-owned Cantera
  ideal-gas phases, absolute pressure endpoints, flow, efficiency and evidence
  identities. Native entropy/pressure and enthalpy/pressure setters own the
  reference and actual outlet states.
- Added an exact-point link that verifies the fuel-feed state, flow ratio and
  actual Cantera mechanism against an existing OpenBraytonRun, then reports the
  fuel-compressor power debit separately from gas-path output.
- Added a CoolProp HEOS real-fluid PT/PS/PH path with explicit caller T/P domain,
  single-phase guards, version/backend/basis identity and a separate result type.
  The real-fluid property basis is not silently converted to the Cantera Brayton
  cycle's basis.
- Added five synthetic acceptance cases to both cluster source plans and
  updated the Request035 API, catalog and focused documentation. Their seals and
  mutation guards remain unexecuted. Compressor maps/trains/cooling, dynamic
  control and hardware validation remain open.
- No local scientific test, import, model calculation or cluster job was run.

## 2026-10-30 — porous storage and Hangang campaign continuation

- Added a caller-parameterized single-phase radial Darcy inventory kernel for
  fixed cell temperatures, with explicit well and optional outer-boundary mass
  exchange. Inflow can select its own boundary temperature. Solver results use
  one-use issuance and a content seal over the retained inputs and output ledger.
  Its geology and thermal limits are documented; its synthetic verification case
  includes outer-boundary inflow/outflow, forgery and mutation checks and is
  enrolled in both Nurion and Hangang plans.
- Added a finite-separator callback-stability guard and extended its deferred
  case. The Hangang generator now accepts repeated `--case-id` values so an
  operator can create a smaller parallel array when site QOS rejects a larger
  submission.
- Request031 now has a source-bound, solver-neutral synchronized fuel-cell trial
  exchange. It reuses the existing activity and stack APIs, exposes per-channel
  stoichiometric source rates and leaves unallocated energy unresolved. It does
  not integrate pressure feedback.
- Request035 now has a caller-owned compressor map with bounded interpolation,
  corrected-flow pairing to the existing turbine map and mapped efficiency
  injection into the existing Cantera/Brayton path. It reports the selected-point
  shaft residual without solving for common speed or closure.
- Both new integration contracts are enrolled in the Nurion plan; the fuel-cell
  exchange and Brayton map pair also use Hangang's core Cantera profile, bringing
  that deferred plan to 20 parallel-ready cases. The selected-case generator can
  split the full inventory into smaller arrays if queue policy requires it.
- The model catalog now contains 76 families: 20 implemented, 37
  native-adapter-verified and 19 implemented-unverified. This is a source
  status inventory; the new contracts have not been executed.
- A clean-enumeration source archive was prepared locally with 973 files; its
  digest and byte count are recorded in the operational Hangang note, which is
  excluded from that archive to avoid self-referencing metadata. No remote source
  write or job submission occurred. The run.sh wrapper's
  `hostname; whoami` check hung and then returned a broken-pipe / connection
  closed error, so cluster execution awaits manual reconnection.
- Engine-dataset discovery found conflicting Durham reuse terms (CC BY 4.0 in
  the data record and ODbL in a related institutional record), and the download
  timed out. No file was acquired or parsed; the unresolved candidate is recorded
  in `HYDROGEN_ENGINE_DATA_SCHEMA.md`.
- No local test or model calculation was run. Independent implementation and
  data-review lanes proceeded in parallel; the campaign generator can reduce
  selected case count without serializing the accepted array workers.

## 2026-10-30 — BAM jet-fire data acquisition

- Added the BAM hydrogen jet-fire record to the dataset discovery catalog and
  acquired its 75,221,648-byte archive after confirming open access and
  CC-BY-4.0 in the publisher API record.
- Verified archive size and publisher MD5; recorded the local SHA-256 and exact
  metadata snapshot hash in the research receipt. The archive remains under
  ignored raw storage.
- Inspected archive member names and the provided text headers without
  extraction. Measurement exports identify time, thermocouple, hydrogen-flow,
  sample-rate and local start-time fields. No timezone, unit conversion,
  calibration, experiment-condition mapping or model comparison was inferred.
- The dataset is a candidate source for jet-flame thermal-target work; acquisition
  and an open license do not qualify it for an independent model validation.

## 2026-10-30 — BAM source-bound measurement reader

- Added `h2physics.data.load_bam_jet_fire_text()` and `BAMJetFireTable` for the
  two publisher-declared measurement-text directories. The reader binds the
  exact Zenodo record identity and one-file listing, verifies archive byte count
  and MD5, optionally checks the separately pinned archive SHA-256, rejects
  unsafe/duplicate ZIP members, and retains member and archive digests.
- Preserved metadata fields, exact source channel labels and raw cells, a
  decimal-comma numeric view, blank mask and row identities. No clock
  reconstruction, calibration, unit conversion, experiment-condition mapping,
  or physical-model projection is provided.
- Added a synthetic parser case under `source-data-ingestion`; the case is
  deferred to Nurion and does not parse the acquired data or validate a fire
  model. AST syntax review and whitespace review passed. No case entrypoint,
  scientific test or model calculation was executed.

## 2026-10-30 — first-order gas detector response

- Added a closed-form piecewise-linear-input solution for the caller-parameterized
  first-order sensor lag, retaining its initial indication, time grid, source
  identity, concentration basis/unit, operating mode, episode, origin and
  parameter/model evidence.
- Added source-current response receipts and a direct sensor-to-alarm composition;
  alarm traces now retain the exact issued sensor response and reject mismatched
  detector/location/clock/mode/episode/origin/basis/unit/evidence.
- Extended the facility monitoring deferred contract with an analytic ramp/hold
  response, lagged trip time, and issuer/evidence rejection. Added a reusable
  synthetic example and updated API/selection documentation.
- Ruff passed for the changed Python modules, and AST-only inventories now report
  302 deferred cases, 1,289 public definitions, 1,459 resolved relative imports,
  and 3,372 local Markdown paths with no missing destinations. No scientific
  case, test, model calculation, or cluster job was run.

## 2026-10-30 — parallel hydrogen-engine data schema review

- Reviewed the source-pinned TU Darmstadt HDF5 object metadata in a separate
  implementation lane. All eight local attachments match their receipt sizes and
  SHA-256 values; no HDF5 array values were loaded.
- None of the figure files identifies quantity, unit, coordinate reference and
  measurement location together. Added a per-file schema gap report and linked it
  from the engine guide/backlog. No observation reader was added because doing so
  would require guessing field meanings; obtain authoritative per-field definitions.
- The current static document audit reports 3,372 local paths with no missing
  destinations. No scientific test, model calculation or cluster job was run.

## 2026-10-30 — parallel cluster-source readiness check

- The prescribed shared wrapper reached Hangang CPU and Nurion concurrently.
  A read-only Nurion queue query found pre-existing jobs; none was changed.
- The remote `20261030/source.tar.gz` is rooted at
  `pipeline-integrity-toolkit/`, not this `h2physics` repository. Inspection of
  the prescribed wrapper confirmed SSH stdin is disabled. No current h2physics
  source archive or permitted transfer path is available, so no stale or unrelated
  case was submitted as validation. Remote source handoff is being clarified while
  local coding continues.

## 2026-10-30 — Dryad grant parsing and acquisition inventory

- Fixed provider license parsing when the Dryad API returns a grant URL as a bare
  string; the recognized CC0 locator now admits acquisition under the existing
  exact host/path allowlist.
- Fixed receipt summarization to ignore non-receipt discovery TOML files and to
  reject incomplete files that do claim the acquisition receipt schema.
- Replayed the O2-chamber acquisition after reading its live API metadata. Both
  public file requests still return HTTP 401, so the manifest records CC0 rights,
  two listed files, zero acquired bytes, and both failures. Dryad's web download
  endpoint returned an anti-bot validation page to the non-browser client; no
  challenge was bypassed. Data inventory generation now completes without the
  former `KeyError`/partial-summary crash.
- No scientific tests, data observations, model calculations or cluster jobs were
  run. The current acquisition failure is retained as a real provider-access limit.

## 2026-10-30 — GitHub-bound source tree integrity

- Added `scripts/audit_public_tree.py` to inspect the staged Git index blobs and
  current tracked/non-ignored untracked bytes, including staged/worktree divergence.
- It denies raw research/data document and native-binary formats, credentials,
  local paths, symlinks, submodule pointers, archives and temporary build/output
  directories. Existing untracked wheels under `tmp/` remain untouched and would
  be rejected for a public source snapshot.
- AST parsing and whitespace review passed. The audit itself, unit/scientific
  cases, calculations and Nurion jobs were not run. The audit is not license or
  redistribution clearance.

## 2026-10-30 — operational receipt supply-graph freshness

- `OperationalScenarioReceipt` now seals the native supply graph's boundary and
  junction identities, link endpoints/component owners, power-reader assignments,
  inventory readers, and selected pump mode. Post-bind topology changes invalidate
  the receipt without executing a solver.
- Added a deferred Nurion contract that appends a graph link after receipt issuance
  and requires stale receipt rejection. The contract was authored but not executed.
  No tests, imports, calculations, or Nurion jobs were run for this change.

## 2026-10-30 — synthetic source-block receipt coverage

- Added `fermentation-block-issuer-integrity` and `hydride-tank-block-issuer-integrity` under `source-data-ingestion`.
- Fixtures use minimal synthetic XLSX ZIP/XML with stdlib; the profile includes the data extra for openpyxl used by the reader APIs.
- Coverage targets genuine reader issuance, direct/dataclass-replacement forgery rejection, row alignment, and post-load mutation detection. No acquired source data, tests, imports, calculations or Nurion runs were used.
- Inventory impact: +2 cases, +1 profile, +1 module, +1 profile/module association (295/50/68/71).

## 2026-10-30 — facility continuity audit prefix retention

- `bind_facility_operation()` now preserves earlier continuity-frame audit results
  and the exact failing frame/index when a later frame audit raises. The typed error
  keeps original source/utility owners and the underlying exception, and no partial
  operation receipt is issued.
- Added a deterministic deferred contract using a controlled later-frame failure.
  Only source AST parsing and whitespace checks were used; no facility model or
  Nurion job ran.

## 2026-10-30 — spherical-shell post-solve failure retention

- Wrapped post-integration enthalpy quadrature, boundary-surface readout and result
  assembly failures in `SphericalShellHeatIntegrationError`, retaining the accepted
  SciPy solution and original cause. RHS failures remain distinct because SciPy may
  not return a partial solution when its callback raises.
- Extended the existing spherical-shell deferred contract with a deterministic
  post-solve quadrature failure check. No tests, model runs or Nurion jobs ran.

## 2026-10-30 — uncertainty propagation result lineage

- `PropagationResult` can now be issued only after the shared native QMC propagator
  has completed. Before summaries, it checks each retained evaluation's parameters
  against the exact design row and reconstructs the aggregate outputs from the named
  response fields.
- `JointPropagationResult` rechecks its native latent propagation and each original
  dependent-input response, and cannot be directly created or cloned with a changed
  payload. Existing deferred joint-uncertainty cases cover those boundaries.
- Source files were AST-parsed and static inventories refreshed. No model callback,
  Monte Carlo calculation, validation case or Nurion job was run.

## 2026-10-30 — native VLE phase receipt integrity

- Restricted `MixturePhasePartition` and successful PH inverse creation to one-use
  issuance from the fixed-composition CoolProp phase-flash/inverse provider.
- Bound retained phase properties, native state values, provider identity and
  composition. Packet accounting rejects post-issuance changes; inverse receipts
  also bind root summary, residual and the accepted evaluation sequence. Dataclass
  replacement cannot reuse either provider receipt.
- Extended the deferred gas-composition contract. No VLE calls, tests, model
  calculations or Nurion jobs were run for this change.

## 2026-10-30 — data and consequence receipt audit

- Counterflow workbook-derived extinction rows, temperature/species profiles and
  optical records now require one-use checksum-reader issuance. Direct construction
  and dataclass replacement cannot attach publisher identity to caller-created data.
- Microbial-current blocks are now issued only by the pinned workbook iterator and
  reconstruct their measured values/masks from retained source cells.
- Facility-consequence receipts compare evaluator code/defaults and ordinary
  captured state before and after execution, including partial arguments and bound
  receiver configuration; in-call edits are rejected before receipt issuance.
- Finite solid-reaction traces now require a one-use issuer from the reactor's
  completed run; the existing binding contract covers clone rejection.
- Deferred ingestion and handoff contracts were extended. Only source AST parsing,
  curated metadata audits and whitespace checks were used; no scientific test,
  calculation or Nurion job ran.

## 2026-10-30 — replay budgets, operation diagnostics and command modes

- Added `ReplayBudget` to the receipt replay API. Rights, per-file size, total
  size, filename uniqueness, checksums and remote-file records are preflighted
  before creating a cache directory or issuing a request.
- Rejected unknown valve and pump command modes at construction, with deferred
  acceptance cases and updates to both operator guides.
- Added an explicit trapezoidal quadrature view over facility-operation residual
  samples. It reports sampled-rate integrals and does not claim native inventory
  integration or facility closure.
- Made direct gas-envelope PT queries reject boolean, nonfinite and nonpositive
  coordinates before qualified-bound checks.
- Restricted buried-pipeline table and column receipts to one-shot issuers in the
  publisher-hash-verifying reader, so copied metadata cannot reseal an altered
  publisher digest.
- Applied loader-only issuance to hydrogen-channel source tables and comparison-
  only issuance to CoolProp table qualification reports.
- Restricted measured microbial-current block issuance to the pinned workbook
  iterator and checked row labels, measured origin, source digest, retained source
  cells, reconstructed SI values and masks. The existing integrity contract covers
  direct construction and replacement attempts; it remains deferred to Nurion.
- Facility accident-chain admission now preserves a rejected HyRAM projection as
  a failure and cannot promote it through a looser outer residual budget.
- Geological adsorption isotherms are loader-issued, and the downstream surface-
  excess provider checks its arrays against those retained observations.
- The pool-to-dispersion result now forwards SLABx-LH2 aggregate acceptance,
  including the empty active-snapshot state.
- Pressure-recorder MAT results and their projected row blocks can now be issued
  only by the source-hash-validating reader, preventing caller-built arrays from
  claiming the acquired measurement identity.
- Transient flowing-exchanger traces are now issued only after the original
  native two-side run, preventing a copied summary from resealing its own ledger.
- Pressure-peaking MAT runs/recorders/blocks and shock-tube parsed blocks now
  retain loader-issued source identity; new deferred cases cover caller-forged
  measured data receipts.
- Conditional and facility risk receipts now use one-shot issuance; native risk
  contexts must also resolve the finite source and native-frequency evidence IDs.
- Extended existing deferred Nurion contracts. No validation, model run,
  scientific calculation or cluster job was executed for these changes.

## 2026-10-30 — storage delivery units, robust fitting and permeation data receipt

- Added a postprocessor for converting an accepted finite adsorption-vessel
  delivery into species-resolved signed mass changes and interval-average rates.
  The existing mole ledger remains the source of truth; no time profile is inferred.
- Added explicit SciPy robust-loss and transition-scale options to observation
  fitting. Linear fitting remains the default, and `FitResult` distinguishes
  response-unit RMSE from the optimizer objective metadata.
- Acquired the public CC BY 4.0 MS1700/QP1180 permeation MAT attachment after
  confirming its file-list SHA-256. Its variable schema and normalization basis
  remain unaudited, so it is not yet a coefficient source or model input.
- Registered two additional deferred contracts. No scientific cases, fitting
  calculations or Nurion jobs were run; only source-only AST inventories were
  refreshed.

## 2026-10-30 — pump command boundary timing

- Corrected finite-speed pump evaluation so each elapsed interval applies the
  command active at its left edge. A newly declared speed target no longer changes
  the native pump speed before its sampled start time.
- Expanded the existing deferred pump ramp contract with an abrupt ramp-up to
  ramp-down transition at an exact sampled boundary. No pump model or validation
  case was run.

## 2026-10-30 — OEDI fatigue observations bound to the checked workbook

- `FatigueGrowthSeries` and `OediFatigueDataset` now require one-time issuer
  tokens created only by the loader after it verifies the acquired workbook's
  SHA-256/MD5 and parses the retained rows. Direct construction, altered-value
  records and copied dataset receipts cannot assert source identity from matching
  metadata fields alone.
- The existing deferred OEDI provenance contract now covers direct series and
  dataset construction with detached values. No workbook, model or Nurion case was
  read or run during this change.

## 2026-10-30 — hydride compressor result lineage

- `HydrideCompressorTrace.require_current()` now fingerprints the retained native
  integration arrays, snapshots, typed stage points and ledgers. Public summary
  properties verify that content before access; the existing deferred compressor
  case now covers mutation of an accepted native solution array.
- This detects post-capture edits to an issued result. It does not qualify the
  hydride alloy, apparatus, cycle or native engine. The contract remains deferred.

## 2026-10-30 — jet-radiation receipt issuance

- Restricted `JetRadiationField` creation to the existing line-source evaluator
  with a per-result issuer token. Direct construction and `dataclasses.replace`
  clones cannot reseal a changed radiation result against an accepted HyRAM flame.
- Extended the existing deferred jet-radiation integrity contract to reject direct
  construction/cloning. The source boundary, radiation method and native flame
  remain unchanged; no consequence physics or scientific evidence was added.
- No validation case, test, model calculation or Nurion job was executed.

## 2026-10-30 — explicit table performance target

- `TableQualification.meets_speedup_target()` compares the stored CoolProp table /
  HEOS timing ratio against a caller-selected minimum. It is a convenience decision
  on recorded timings only and does not modify property-error or thermodynamic
  identity qualification. The existing deferred table case covers matching,
  failing, and invalid targets; it remains unexecuted.

## 2026-10-30 — material transport result lineage

- Bound `TransportResult` to a successful `DiffusionDomain.simulate()` owner and
  verified that its mobile/trapped fields, surface inventories, integrated face
  fluxes and residual ledgers reproduce the retained native integration state.
  `require_current()` rechecks this projection and the result's retained arrays.
- Added an altered-field rejection to the existing cylindrical material transport
  case contract. It remains deferred; no model calculation or Nurion run was made.

## 2026-10-30 — same-clock hydrogen detector voting

- Added an explicit k-of-n layer over already evaluated, individually latched
  concentration alarm traces. It requires unique detector IDs and exact alignment
  of the common clock, mode, episode and sample grid; each detector retains its own
  basis, thresholds, hysteresis and confirmation rule.
- Rising/falling vote transitions preserve the active detector IDs. A source-bound
  voted trip can enter the existing scheduled protection replay. Independence,
  common-cause failure, sensor reliability, asynchronous/missing data and setpoint
  selection remain caller-owned and are not inferred.
- Expanded the existing deferred facility alarm contract with a synthetic 2oo3
  handoff and alignment rejection. No case, sensor physics, model calculation or
  Nurion job was executed.

## 2026-10-30 — source receipt and output integrity follow-up

- Audited API-reference symbol paths against package source declarations. The
  documented adapter paths resolve to existing direct Python modules; removed a
  stale hard-coded inventory snapshot from the API reference and directed readers
  to the maintained progress/handoff records instead. No model or deferred case
  was added.
- Reconciled `h2physics.adapters.__all__` with the already documented liquefaction
  benchmark API. Its three imported public names now also appear in the declared
  export list, keeping API enumeration and wildcard import behavior consistent;
  no physical model or deferred scientific case was added.

- Added `thermo.GasStateDiagnostics` for compressibility, heat-capacity ratio,
  Prandtl number, thermal diffusivity, and kinematic viscosity from an existing
  native gas state. Caller supplies the specific gas constant; missing native
  properties are not inferred. Its synthetic arithmetic/phase-gate contract is
  deferred to Nurion and has not been executed.
- Added a bounded axial heat-release integral for the existing native counterflow
  flame profile. It reports signed W/m² and rejects out-of-domain bounds; it adds
  no burner geometry or total-power inference. Its contract remains deferred.
- Added a loading-window capacity calculation for hydride parameters. It reports
  nominal mass only and does not claim kinetic or operating reachability; its
  deferred contract remains unexecuted.
- Added quasi-steady permeation history from caller-supplied temperature and
  fugacity samples using the existing permeation relation. The result is signed
  hydrogen mass per area; transient diffusion and material properties remain
  outside this adapter.
- Added a one-column buried-pipeline data view that preserves source row IDs,
  anonymous labels, raw tokens, validity masks and publisher digest without
  assigning physical meaning to the fields.
- Added direct access to a selected facility node's original mass/energy residual
  series on its exact accepted clock; no interpolation or balance recomputation
  is introduced.
- Added `run_photochemical_operation()` to sequence adjacent caller-qualified
  photon windows through one finite stoichiometric reaction. If a later stage
  exceeds available inventory, `PhotoOperationError` retains the completed
  operation prefix and original failure; no kinetics or automatic shutoff is added.

- Radial failure callback bindings now include Python code-object content,
  recursive defaults/closure state, bound receiver configuration and callable
  attributes/slots. The deferred callback-signature contract remains unexecuted.
- Elastic-cylinder fields now retain immutable finite component arrays, matching
  axes, in-wall radii and a von Mises value consistent with the stored stresses.
  The corresponding contract is deferred.
- Reservoir-driven `HydrideTrajectory` records require one-use integration
  issuance and validate aligned time/state axes, physical domains, stored mass and
  reduced-energy reconstruction. Its direct-construction/clone contract is deferred.
- Liquid accident mass and energy diagnostics now require one-use factory tokens
  before exposing immutable stage ledgers. Their deferred constructor contracts
  remain unexecuted.
- The thermal utility/exchanger API is now directly available through the stable
  `h2physics.adapters` surface, with a deferred identity contract.
- A post-run fuel-cell activity series maps explicit operating rows to every
  accepted native pressure time while preserving reference lineage; it does not
  introduce in-solver pressure feedback or combined energy closure.
- A facility consequence handoff now forwards the exact finite-source/dispersion
  receipt to a caller evaluator and checks freshness before and after. It assigns
  no consequence physics or safety thresholds.
- Facility reporting now groups common-clock residuals and the existing net utility
  ledger without claiming whole-plant closure or inventing prices. Relief/cooldown
  phase receipts can be joined across exact shared event edges. OEDI comparison
  points now recheck the original dataset, owner, definition and values on access.
- `PowerLawSolubilityBoundary` connects caller fugacity histories to the existing
  diffusion domain using its same prescribed temperature; no material properties
  were inferred. Requests031–033 were refined against current native interfaces;
  Request034's existing native-owner boundary was confirmed. The acquired
  materials data still lacks a matched solubility/diffusivity parameter set.
- Added a bounded inverse lookup to the existing valve effective-area map. A flat
  segment requires an explicit endpoint selection; no actuator dynamics are inferred.
- Added a receipt-preserving exposure-to-target boundary that admits only valid
  left-held incident radiant flux. It introduces no damage threshold or exposure
  physics and remains deferred to Nurion.
- Added a sampled-SIF threshold receipt for exact retained samples only; it claims no
  interpolated crossing or fracture initiation.
- Added per-load-block fracture summaries over retained samples and a native
  heat-exchanger wall-transfer series at accepted RK points. Both are reductions
  of original traces, not new event or heat-transfer physics.
- Added exact-clock species inventory views for the native catalytic surface trace
  and UH2SC outputs; neither projection invents states or field meanings.
- Refreshed source metadata only: 260 deferred contracts, 45 profiles, 55 case
  modules and 58 profile/module associations; 1,243 public definitions across 203
  modules; 1,371 bound relative imports with no missing or unresolved targets; and
  3,221 local Markdown paths across 296 files with none missing. No tests,
  calculations, compilation, network activity or Nurion jobs were run.

## 2026-10-30 — issued liquid-accident energy diagnostics

- `LiquidAccidentEnergyDiagnostics` now requires a one-use token from
  `liquid_accident_energy_diagnostics()`. Direct construction and reuse through
  `dataclasses.replace()` reject before exposing an unissued stage-energy receipt.
  The existing deferred liquid-accident ledger case records both paths. No
  accident model or validation case was run.

- Radial failure-history callback fingerprints now include full Python code
  objects, recursively visible closure/default state, bound receiver state and
  ordinary callable attributes/slots. Bound-method identity no longer depends on
  a transient method-wrapper object. The deferred contract records nested closure,
  receiver, keyword-default and code replacement changes. Opaque external/global
  dependencies remain caller-owned; no SIF callback or case was executed.

## 2026-10-30 — graph-issued scenario result receipts

- `ScenarioResult` now requires a one-use issuer token created by
  `OperationalScenario.run()`. Direct construction and `dataclasses.replace()`
  cannot relabel or fabricate a completed scenario record. The deferred scenario
  composition contract records both rejections; no scenario case or model ran.

- Removed the module-level scenario-result token factory after finding it could
  itself be called to mint a forged one-use token. Issuance is now created inline
  only after a graph run has completed and recorded its selected node prefix. The
  existing contract checks that the factory is absent; no case was executed.

## 2026-10-30 — family-bound dispersion scenario admission

- `DispersionScenario` now checks its complete required keyword contract when
  constructed and rejects fields that belong to the other release family. This
  surfaces incomplete or cross-routed Python API requests before a native
  provider can be called. The facility accident-chain deferred contract records
  these admission boundaries; no validation case or provider was run.

- `HydrideCompressorTrace` now requires a one-use issuer produced only after the
  shared native bed/source/receiver integration. Its constructor checks retained
  model evidence, initial clock, typed segments, contiguous stage clocks and
  event endpoint. A new Nurion-only contract exercises clone/direct-construction
  rejection and finite-system residuals with a dedicated thermo+LH2DT profile.
  No model, test or cluster job was run for this addition.

- Refreshed source metadata only: 246 deferred contracts across 45 profiles and
  51 case modules; 54 curated profile/module associations; 1,212 public API
  definitions across 199 modules; 1,307 bound relative imports with zero missing
  or unresolved symbols; and 3,120 local Markdown paths with zero missing targets.
  The four inventories do not invoke validation entrypoints or models.

- `OpenBraytonRun` now retains a canonical signature of its native ideal-gas
  species thermochemistry, elemental definitions, reaction input data and
  reaction multipliers. Revalidating a result after a caller changes the shared
  Cantera phase mechanism rejects the stale receipt. The deferred summary case
  records a reaction-multiplier mutation; no native mechanism was executed for
  this source change.

- `QualifiedGasTable` now includes the wrapped CoolProp `AbstractState` and
  module object identities, synchronization-lock identity, and reported backend
  and fluid names in its qualification binding. Replacing the native state with
  an object for another fluid invalidates the table before property access; a
  deferred mutation contract records that boundary. No CoolProp
  calculation or validation case was run for this source change.

- `HyRAMComponentFlowProjection` now calls `require_current()` on its parent
  finite-source projection during direct construction. Previously, callers could
  construct and inspect a component allocation from a stale parent receipt before
  the later freshness method ran. The deferred HyRAM contract records this
  constructor path; no native HyRAM call or case was run.

## 2026-10-30 — current source and open-channel data reconciliation

- `JointPropagationResult` now requires a one-use issuer from successful
  `propagate_joint()` and validates every retained row against its exact latent
  design, transformed-input bounds, original response and declared outputs.
  `require_current()` and summaries check the content seal without rerunning user
  callbacks. The deferred joint-input contract rejects a copied receipt with a
  changed scenario identity. No QMC propagation or physical model was executed.

- `NozzleSourceProjection` direct construction now rejects quadrature or
  representative-state evidence IDs that are empty or whitespace-only, even if
  a caller forges the matching finite-source evidence string. The source-projection
  contract records this negative case. No nozzle solver, validation case, physical
  calculation or Nurion job was run for this source-only change.

- `FrozenGasBinding` now rechecks provider-owned composition metadata before and
  after every gas state query. Providers exposing species, mole fractions, molar
  masses and a composition ID are rejected if any of those values changes after
  admission; providers without such metadata remain explicitly caller-evidenced.
  The finite-adsorption owner-basis deferred contract records a mutation case.
  No case or physical model was run for this source change.

- The finite thermal-target receipt now requires a one-use token issued by a
  completed target integration, preventing a cloned trace from sealing a changed
  reported maximum or energy ledger. Its deferred pulse contract checks clone
  rejection and accepts either bytes-backed write denial or stale-ledger
  detection. No integration or case was run for this source change.

- The provider-backed cooldown wrapper now binds the scalar inlet and outlet
  enthalpies individually to the retained exact EOS states, in addition to
  matching the enthalpy rise. A deferred contract rejects shifting both scalar
  endpoints by the same offset while leaving the rise unchanged. This is a
  reference-consistency guard; no coolant properties or cooldown calculation ran.

- Refreshed only metadata/source inventories after this implementation pass: 245
  deferred contracts across 44 profiles and 50 case modules; 53 profile/module
  associations; 1,212 public API definitions across 199 modules; 1,307 statically
  bound relative imports with zero missing/unresolved symbols; and 3,120 Markdown
  paths across 291 files with zero missing targets. These commands enumerate source
  and case metadata; they did not execute validation entrypoints or models.

- Continued the host integration review without running scientific cases. The
  SLABx-LH2 snapshot-series admission now requires every retained positive-mass
  native source window to match the exact absolute edges of its parent release
  bin, even when mass and duration are unchanged. A shifted-clock rejection
  contract is authored. The independent steady snapshots still carry no plume
  memory and are not a transient concentration solution.
- Added `FuelCellActivityReceipt` as a post-run bridge from one exact common
  accepted pressure sample across the separate native H2, O2 and water-vapor
  compartments to the existing dimensionless ideal-activity correction and
  `HydrogenStack`. Reference pressures, water phase, current, temperature and
  evidence remain explicit. The receipt is sealed to the original traces and
  fixed to report no pressure feedback or simultaneous energy closure. Its
  deferred contract is authored, not executed.
- Tightened the host pool-energy ledger to reject nonzero-starting, negative or
  decreasing cumulative heat-allocation diagnostics. Request033 now specifies
  accepted-edge field names, signs and residual equations for the native owner.
  The current engine still lacks those accepted-edge cumulative fields, so the
  binder rejects it rather than estimating energy from sparse heat-flux output.
- No tests, physical calculations, benchmarks, SSH actions or Nurion jobs were
  run for these changes. These are source/API and deferred-contract increments;
  native receiving work and scientific qualification remain outstanding.
- Finite adsorption state construction now rejects a propagated standard-
  uncertainty vector unless it is explicitly marked as covariance-matrix
  propagated and carries uncertainty source evidence. This closes a labeling
  path where supplied numeric uncertainty could otherwise remain marked
  unqualified. Covariance propagation itself is still caller-owned; the
  deferred constructor contract has not run.
- The open-channel hydrogen data reader now requires the pinned Figshare
  metadata URL/hash and checks each resolved attachment's name, URL, size and
  publisher MD5 against the file list inside those exact metadata bytes. Its
  deferred intake contract rejects a forged attachment record. No physical
  field meaning or sensor clock was inferred, and the contract has not run.
- The catalytic surface trace now uses a one-time native-run issuer token, so a
  copied or directly constructed historical trace cannot establish a fresh
  integrity seal from fabricated points or relabeled evidence. The deferred
  Cantera contract includes a clone rejection; no native run or case was executed.
- Finite hydride trace construction now also requires a one-use token issued only
  after the native-provider integration returns. This prevents `dataclasses.replace`
  from validating caller-modified port ledgers as a second original run. The
  existing deferred constructor contract now records clone rejection; no trace or
  scientific case was executed for this change. The external port remains a
  caller-supplied signed stream boundary without a pressure-flow law.
- The finite equilibrium-mixture separation receipt now consumes a one-time token
  from its completed admission path, retains both acceptance budgets, and
  recomputes component-mass and phase-enthalpy residuals from the original native
  partition and amount packet. A cloned result with changed residuals is recorded
  as a deferred rejection contract. The changing-composition separator flash and
  its event/time integration remain outside this host receipt; no case or physical
  calculation was run.
- The closed-charge cylinder trace now also requires a one-time issuer created
  only after its native Cantera segment finishes. A copied trace cannot establish
  a new integrity baseline for altered clocks, native owners or summary fields;
  the existing deferred engine contract includes clone rejection. This still
  describes only the sampled segment, not a complete engine cycle. No model or
  Nurion case was run.
- The source-only refresh now reports 245 deferred cases in 44 profiles/50
  modules, 1,212 public definitions in 199 modules, 1,307 bound relative imports
  with zero missing/unresolved symbols, and 3,120 Markdown paths across 291 files
  with zero missing targets. No validation entrypoint was executed.

- The live Figshare V2 API listing matches the local receipt on DOI, version,
  license, all 23 attachment names, sizes and publisher MD5 checksums. Every local
  acquired file also matches its recorded byte count, publisher checksum and
  computed SHA-256. Raw assets remain excluded from Git and package contents; the
  data have not been interpreted or used as model-validation observations.
- The current metadata-only index contains 245 deferred cases across 44 profiles
  and 50 modules, 53 profile/module associations, 1,212 public API definitions
  across 199 modules, 1,307 bound relative imports with no unresolved targets,
  and 3,120 local Markdown paths across 291 files with no missing targets.
- These are source, metadata and file-integrity records only. No model, scientific
  validation case or Nurion job has been executed for this continuation.

## 2026-10-30 — source-bound open-channel release intake

- Added a direct Python reader for one Figshare hydrogen-channel V2 case ZIP. It
  verifies publisher size/checksum (MD5 in the current source listing), computes a
  local SHA-256 fingerprint, requires one safe CSV member, hashes
  that member, and preserves both header rows, original tokens, source record IDs,
  numeric values and missing masks with immutable backing arrays.
- Added a deferred offline acceptance contract and dedicated dataset/API guidance.
  No sensor clock unit, pressure basis, concentration calibration or cross-clock
  alignment is assigned. The API is data intake, not a dispersion validation.
- Raw licensed files remain ignored under `data/raw/` and outside package contents.

## 2026-10-30 — turbine-map point bound to the open Brayton reference

- Added `MapBoundBraytonInputs` and `run_map_bound_open_cycle_brayton()` to
  apply one source-pinned turbine-map efficiency to the existing native Cantera
  expansion. Admission checks the map's explicit total-pressure convention,
  in-domain expansion ratio, caller-provided air flow and evidence-backed
  actual-to-corrected-flow factor. The result retains and rechecks the map point
  and original reference cycle, including every cycle input and its evidence IDs.
- Added deferred `hydrogen-brayton-turbine-map-boundary` acceptance metadata and
  updated Request035, the model catalog, and the reference manual. This does not
  implement compressor maps, a coupled shaft, off-design controls, or machine
  qualification. No tests, model calculations, or Nurion jobs were run.

## 2026-10-30 — engine schedule immutability and source freshness

- `EngineBoundarySchedule` now seals its source, units, absolute clock, support
  and value bytes; it checks freshness before returning support or interpolated
  values. Its NumPy arrays and closed-charge trace arrays use immutable backing
  storage, so callers cannot re-enable writes by toggling the NumPy flag.
- The deferred engine contract now covers rejected write enabling and source
  relabeling with restoration. This remains schedule bookkeeping only; it does
  not add valve, injector, spark, heat-transfer or full-cycle physics and has not
  been executed.

## 2026-10-30 — buried-pipeline intake hardening (prior source snapshot)

- The V2 attachment loader now rejects ambiguous duplicate filenames, requires
  exact publisher-listed byte length and SHA-256, and backs public NumPy arrays
  with immutable bytes so callers cannot re-enable writes. Its deferred contract
  records those guarantees; no case or scientific calculation was executed.
- Refreshed the metadata-only inventories: 239 deferred cases, 42 profiles and
  46 case modules; 197 package modules and 1,203 public API definitions; 1,213
  bound relative imports with no missing or unresolved targets; and 3,014 local
  Markdown paths across 290 files with no missing targets.
- Rebuilt sdist and wheel and compared every packaged Python file byte-for-byte
  with the workspace sources. Both archives contain 197 matching package files.
  This is a packaging-content check only, not a runtime, scientific or rights review.

## 2026-10-30 — bounded storage, safety, pool-energy and data seams

- Finite-hydride simulations now optionally accept a same-clock signed H2 port
  boundary, retaining external mass and stream enthalpy and rebuilding the gas,
  solid and whole-bed ledgers from their retained traces. Existing EOS and kinetic
  owners remain unchanged; no pressure-flow law was added.
- Facility-risk receipts now reject direct issuance and recheck their original
  native result, source, protection run and dependence content. The pool-energy
  handoff accepts only the exact original pool continuation and leaves each stage
  balance separate; neither change claims facility-wide energy/risk closure.
- Acquired the 12 current V2 buried-pipeline CSVs to ignored raw storage. All local
  SHA-256 values match the publisher listing. A source-bound reader preserves raw
  positional fields and blank masks because the files lack headers and a data
  dictionary. Units and physical meanings remain unresolved. Its deferred contract
  is registered and unexecuted.

## 2026-10-29 — separate native pool energy receipt in accident diagnostics

- `liquid_accident_energy_diagnostics()` can now retain a `PoolEnergyLedger` only
  for the exact same original deposited-stock continuation as its exhaustive mass
  ledger. Pool energy stays a separate control-volume receipt; stage residuals are
  not summed and global accident energy closure remains false.
- Added a deferred fixture-backed handoff case. The currently reviewed pool owner
  still lacks the cumulative accepted-edge energy fields, so the valid native path
  cannot yet be exercised. No test, physical calculation or Nurion job was run.

## 2026-10-29 — open hydrogen Brayton reference level

- Added a single-point open Brayton API that delegates ideal-gas properties and
  HP-equilibrium combustion to a caller-supplied Cantera phase. Compressor and
  turbine isentropic efficiencies and combustor pressure recovery are explicit
  caller parameters; turbine expansion freezes combustor composition.
- The result reports specific work and independent element/enthalpy residuals.
  It is not a component-map or coupled-shaft turbine model. Request035 remains open
  for the higher-fidelity model and independent machine data.
- Added two deferred contracts to the existing `hydrogen-engine` profile; no
  validation case, physical model or Nurion job was run.
- A direct-output audit now reconstructs work, efficiency, enthalpy residuals and
  elemental residuals from the retained stations, checks the native terminal
  phase, and rejects forged summary fields in a deferred adversarial contract.

## 2026-10-29 — liquefaction benchmark process-window binding

- The reversible-work benchmark now requires and retains an explicit process
  window identity for its state, mass and external-work quantities. Numeric inputs
  use the project's shared `finite()` guard.
- Deferred cases cover window identity retention and blank-window rejection. The
  liquefier profile remains metadata-only; no model, test or Nurion job was run.

## 2026-10-29 — closed-charge moving-volume hydrogen cylinder seam

- Reviewed Cantera 3.2's official reactor, moving-wall and gaseous-fuel engine
  documentation. Added a narrow premixed H2/oxidizer slider-crank cylinder segment
  using native Cantera integration and chemistry. No external mechanism is bundled.
- Added deferred geometry/input/native trace cases and the `hydrogen-engine`
  cluster profile; no validation case or physical calculation was run.
- Request034 now covers full-cycle flow, ignition/control and evidence gaps.
  Request035 records the missing gas-turbine cycle family.

## 2026-10-29 — engine trace summary reconstruction

- `ClosedChargeEngineTrace` now recomputes sampled pressure-volume work and the
  first-law residual from its retained pressure, volume and internal-energy arrays.
  Forged direct-constructor summary values are rejected.
- The deferred native engine case now includes forged work/residual receipts. The
  metadata plan was refreshed; the added contracts remain unexecuted.

## 2026-10-29 — pool energy direct-construction seal

- `PoolEnergyLedger.__post_init__()` now captures the exact native accepted-edge
  energy fields for both factory and direct construction, then calls its normal
  freshness check before returning. Direct reconstruction cannot omit the source
  seal or bind balanced terms detached from native rows.
- The existing deferred parcel/pool contract requests a reconstructed receipt
  freshness check. No pool engine or physical case was executed.

## 2026-10-29 — relief/cooldown receipt declaration freshness

- The relief-to-line receipt now fingerprints its retained boundary histories,
  evidence IDs, qualified ports and closure tolerances. `require_current()` checks
  that seal instead of rerunning construction, so post-bind evidence relabeling or
  tolerance relaxation cannot weaken an already admitted boundary comparison.
- A scalar string is rejected for the evidence ID sequence, preventing implicit
  character-level identifiers. Deferred mutation/restore and malformed-sequence
  contract coverage was added. No relief or cooldown model,
  case, network request or Nurion job was run.

## 2026-10-29 — dataset license locator integrity

- Supported dataset license IDs now require a matching recognized grant-text
  host/path in typed metadata. Repository discovery normalizes recognized IDs to
  canonical HTTPS license pages while retaining exact provider metadata bytes and
  their SHA-256 separately. Provider license labels are matched against exact
  normalized aliases; nonempty unknown labels, ID/URL conflicts and substring
  lookalikes stay unresolved. A known URL alone is accepted only when the label is
  empty.
- Receipt replay now rejects non-boolean affirmative rights and mismatched license
  locators before creating the cache directory. Historical HTTP official locators
  are accepted only as non-fetched replay provenance. The stdlib manifest audit
  reports ID/URL mismatch, rejects explicit license-port aliases and warns on
  historical HTTP locators.
- Added a deferred adversarial contract for forged IDs/URLs, substring lookalikes,
  conflicting label/URL pairs, explicit nonstandard license ports and the string
  `"false"` bypass. It remains
  unexecuted; no URL or data was fetched.

## 2026-10-29 — radial SIF summary freshness

- `RadialFailureSeries.require_current()` now checks exact finite time coverage,
  integer/non-boolean maximum index and agreement of the maximum value with its
  retained SIF samples. The maximum is included in the content seal, closing a
  post-return mutation path through downstream summary consumers.
- The deferred radial bridge contract specifies mutation and restoration. No SIF
  callback, fracture model, numerical case or Nurion job was executed.

## 2026-10-29 — facility handoff provider freshness

- Fixed `FacilityDispersionHandoff.require_current()` to invoke the retained
  `DispersionExecution.require_current()` seal instead of rerunning `__post_init__`.
  Constructor replay replaced the provider content fingerprint and could conceal a
  post-capture result mutation from downstream use.
- Extended the deferred facility source-prefix contract with a mocked provider
  payload mutation/restore through the actual handoff. The contract remains
  unexecuted; no native provider or physical model ran.

## 2026-10-29 — direct facility handoff evidence gate

`FacilityDispersionHandoff` now rejects blank coupling evidence and calls its
normal freshness/physics-admission path during direct construction, so callers
cannot bypass checks that the scenario assembly already performs. The existing
deferred facility handoff case includes a forged blank-evidence receipt. No
validation case, native solver or physical calculation was run.

## 2026-10-30 — accident-chain output lineage

`FacilityAccidentChain` now admits only the declared ordered finite-operation,
finite-source, preferred-dispersion graph with one chain evidence identity. After
execution it checks that the source retains the exact finite-operation result,
the final handoff retains that source, and the handoff family/evidence match the
chain declaration. The existing deferred source-prefix case includes a graph whose
typed handoff carries unrelated evidence. This protects host lineage; it does not
add liquid leak/launch/deposition or transient-plume physics. No case or physical
calculation was executed.

## 2026-10-29 — absolute adsorption bridge provenance freshness

- `AbsoluteAdsorptionVesselBridge.require_current()` now pins the original typed
  state identity and qualification evidence ID as well as its numerical/source
  fingerprint. Equal-valued state replacement or qualification-ID mutation fails
  closed; the deferred bridge contract records both cases.
- This preserves attribution across the exact-condition vessel handoff and does not
  qualify the underlying evidence, fit data, or convert surface excess. No scientific
  case or Nurion job was run.

## 2026-10-29 — preferred dispersion receipt freshness

- `DispersionExecution.require_current()` fingerprints the provider result,
  acceptance and source evidence. A deferred HyRAM-route contract mutates/restores
  its mocked provider payload and requires stale receipt rejection. This protects
  downstream use without changing either engine's physics.
- The contract is authored only; no provider, physical case or Nurion job was run.

## 2026-10-29 — pool energy phase/reference identity

- `PoolEnergyLedger` now requires its energy reference to match the exact deposited
  `ThermoState` property basis and its vapor outlet phase to match the declared
  normal-hydrogen vapor identity. `require_current()` pins both declarations.
- The deferred parcel/pool contract specifies rejection of mismatched identities.
  This closes a host receipt-labeling gap only; native cumulative energy, dryout
  allocation and finite-wall continuation remain Request033 work.

## 2026-10-29 — repository redirect boundary

- Repository metadata and OpenEI HEAD requests now reject downgrade or credential-
  bearing redirect targets inside the redirect handler before following them.
- OpenEI attachment URL types are checked before suffix handling. The deferred
  mocked transport case covers the pre-follow rejection and malformed lengths; it
  remains unexecuted. No network requests or scientific models were run.

## 2026-10-29 — fuel-cell activity phase contract

- `FuelCellOperatingState` now retains the product-water phase for its dimensionless
  activity and the shared correction rejects a phase mismatch with `ReactionEnergy`.
  The deferred operating-point case specifies the rejection.
- Pressure/fugacity derivation and simultaneous pressure/activity/thermal feedback
  remain receiving-engine work under Request031. No case or physical model was run.

## 2026-10-29 — implementation-stage status and static inventory

- Refreshed source-only metadata: 221 deferred cases, 39 profiles, 40 case modules,
  39 curated cluster profiles/43 profile-module associations, 1,182 public API
  definitions, 2,941 local Markdown links with zero missing targets, and 1,180
  bound relative imports with zero missing/unresolved entries across 192 modules.
- Whole-source Ruff, compileall and `git diff --check` passed after six pre-existing
  audit-script lint findings were corrected. These checks did not import or execute
  scientific case entrypoints.
- Original-scope host coding remains active. The 30–40% effort estimate and 59/72
  historical execution checkpoint remain stale planning evidence, not current tests
  or a measured implementation percentage. No scientific case or Nurion job ran.

## 2026-10-29 — common-clock receipt freshness

- Sealed `OperationalScenarioReceipt` declarations and retained accepted dynamic
  inventory/transfer records with an identity-aware content fingerprint. Currentness
  checks reject changed scenario IDs, evidence declarations or retained ledgers
  without replaying a physical solver.
- Added a deferred mutation contract. It has not been run; no scientific cases or
  Nurion jobs were started.

## 2026-10-29 — H2 handoff and adsorption uncertainty

- Added elemental formula, charge and molar-mass compatibility checks to the
  producer/consumer H2 handoff and registered its original-trace bridge case for the
  later Nurion campaign. It has not been executed.
- Finite adsorption vessel uncertainty now rejects partial site/species source-row
  coverage so a missing uncertainty cannot appear as zero. The matching adversarial
  case is deferred. No scientific calculations or cluster jobs were run.

## 2026 10 29 — shared contracts and safety history integration

- Tightened the radial-to-vessel exact-sample guard: it requires the original typed
  `VesselFailureHistory`/context and rejects a newly attached native trace, native
  loading snapshots or reconstructed sample parents. The deferred bridge case now
  requests rejection of an unrelated trace. No scientific or HELPR run occurred.

- Structured the radial-to-HELPR composition error with precheck, native-evaluation,
  invalid-result and postcheck stages. It retains the radial binding, exact cause and,
  for a post-evaluation integrity failure, the otherwise successful typed prediction.
  The deferred case asserts that stale H2 service context is rejected before HELPR is
  called and that its cause/binding/stage remain inspectable.

- Bound nested geometry, load, typed service-context, history tuple and loading-sample
  identities in the radial failure binding. The deferred bridge case now rejects an
  equal-valued replacement context rather than admitting detached evidence by value.

- Audited the full radial thermal/thermoelastic/vessel chain and found the current
  HELPR bridge sends scalar wall temperature to the material law but leaves the
  crack-driving calculation pressure-derived. Added Request027 with additive native
  stress-field/SIF, flaw orientation, total-field/no-double-count, bounded time
  reconstruction and independent comparison/refinement acceptance contracts. No
  receiving-module code or scientific evidence is claimed.

- Added `RadialThermalVesselBinding.predict_failure()` as a guarded pre/post
  handoff to the existing `HelprVesselFailure` owner. It passes the original typed
  history unchanged, returns the native prediction, and retains both radial source
  and native failure in its composition error. The deferred bridge case requests an
  actual pinned HELPR call and same-history identity check; it remains unexecuted.

- Added `RadialThermomechanicalHistory.require_current()` to bind the issued
  sequential wall-heat/pressure/stress result to original result, load and profile
  objects plus retained output/evidence content. Extended the deferred radial-heat
  case to request rejection after a nested stress-history evidence change. This is
  downstream result integrity only; the scientific case remains unexecuted.

- Made the model ownership catalog a validated Python contract: two-level ASCII
  family IDs, nonempty purpose/owner/evidence fields, a closed status vocabulary,
  unique family IDs and validated filters. Regenerated the catalog view from that
  source. This guards future modular additions without changing model or evidence
  counts; no scientific model was executed.

- Tightened selected cluster evidence path identities: campaign/runtime paths must
  be canonical absolute POSIX paths below `/`, rejecting aliases before collection
  or expectation construction. This is metadata contract hardening only; no results
  were collected and no scheduler, scientific case or remote connection was used.

- Added post-return source/content binding to the radial thermal-to-vessel failure
  bridge. The history and mapped-temperature accessors revalidate pressure, thermal,
  and HELPR-history relationships; the deferred bridge case records nested mapping
  replacement rejection. No scientific execution occurred.

- Bound issued `ConditionalRiskResult` objects to their original native request,
  context, output/receipt, finite source, receptor, branch harms and reviewed engine.
  Added a post-return `require_current()` audit and made the reported annual-harm
  frequency invoke it. The deferred facility-risk case requests replacement-output
  rejection; no native risk evaluation was run for this change.

- Made `DispersionScenario` snapshot its nested `solver_options` mapping as well as
  its top-level request mapping, preventing post-construction caller edits from
  changing a prepared native run. Expanded the deferred preferred-provider case to
  cover the mutation boundary and corrected its direct-wrapper fixture to retain
  the original arguments. No native dispersion run occurred.
- Hardened `DispersionExecution` so evidence IDs are explicit sequences and acceptance
  and source evidence match the retained provider result. The deferred gas-route case
  uses a callback stand-in rather than invoking native HyRAM code, and its cross-family
  check retains the original inputs.

- Extended the shared thermodynamic state with a guarded same-state cp/cv ratio and
  the native frozen Cantera mixture provider with its composition-derived molar mass.
  Expanded the existing deferred Cantera composition-binding case and documented
  the unresolved real-gas and independent-mixture validation scope. No scientific
  execution or Nurion submission occurred.

- Pinned each cluster profile's environment setup script by SHA-256. Generated
  PBS workers check the digest before and after sourcing, and worker records plus
  evidence reconciliation retain and enforce the pin. Added a deferred contract
  case for the generated script ordering; it has not run and no cluster job was
  submitted. Transitive setup dependencies remain separately attestable inputs.

- Added an absolute-pressure Dalton partial-pressure helper and reused it in the
  finite adsorption-vessel and oxygen-inventory assembly paths. The oxygen audit
  retains its separate snapshot-based recomputation.
- Added immutable fixed-composition gas bookkeeping for mole/mass fraction changes,
  molar mass and signed component flows; the adsorption gas binding now delegates
  composition-domain checks to this shared API.
- Connected `GasComposition` to the native Cantera frozen ideal-gas property provider.
  The adapter checks declared component molar masses against mechanism metadata before
  provider construction or native-phase mutation, converts mole fractions to Cantera's
  mass basis and preserves the caller composition ID, which is checked on later state calls.
  The deferred case rejects mismatches, records that the caller-owned phase remains unchanged,
  and rejects identity tampering.
- Hardened native relief trace construction by recomputing mass/energy ledgers from
  accepted native intervals and checking immutable histories and terminal inventory
  events.
- Added a radial wall-temperature-to-existing-vessel-failure history bridge using an
  explicit radius, exact time grids and retained mapping evidence. No new fracture or
  rupture solver was added.
- Added a deferred Cantera-to-composition binding case and refreshed the metadata-only
  Nurion inventory to 226 cases,
  40 profiles and 47 modules. Python compilation, Ruff, and diff checks passed; no
  scientific case was run and no Nurion calculation was submitted.

## 2026 10 26

- Established an active project objective and staged acceptance plan.
- Created an isolated repository folder to keep neighboring private/source material out
  of the publishable tree.
- Selected a Python-native composition design and explicit rights/evidence boundaries.
- Began primary-repository searches for process, storage, release, ventilation and
  electrochemical datasets. Acquisition and validation status will be recorded separately.
- Recorded existing ownership and version conflicts before implementing overlapping models.

## 2026 10 27 — first executable baseline

- Consolidated scope into 72 families: twelve partial executable levels and an additional
  native homogeneous-tank adapter. Higher levels and facility qualification remain open.
- Data-first work secured 23 of 24 cataloged collections: 253 verified files and
  2993132692 bytes. Raw attachments stay outside Git and distributions. Large collections
  are bounded subsets; scientific suitability is documented separately.
- Added rights-aware repository adapters, checksums, native acquisition receipts, container
  inspection, content-addressed metadata snapshots and recorded-hash replay.
- Corrected Dryad checksum types, version labels containing spaces and Dataverse original
  versus archival names/sizes. Dryad public attachment access still fails and remains visible.
- Loaded 22 channel flow cases and seven AB2 shell-temperature records. Removed an early
  assumed sensor-time seconds unit; default concentration-history ingestion now waits for
  an explicit unit declaration. There is no automatic logger alignment.
- Parsed 1027 acoustic observations and compared 761 explicit-composition/pressure points
  against HEOS. Historical outliers and exclusions remain in the public result.
- Implemented reduced hydride equilibrium/kinetics/heat, molar carrier-explicit material
  transport/traps and one electrolyzer/fuel-cell polarization/Faraday/energy core.
- Reused native Cantera equilibrium/reactors/flames and a separately installed LH2DT public
  snapshot. No external mechanism or solver implementation is bundled. Four extension
  requests were prepared; no other repository was modified or messaged.
- Native thermodynamic tables failed the separate energy-identity gate. An explicitly
  selected dependent-u option passed sampled PT/PH/PS property and energy gates, retaining
  raw adjustments and negative results. No differential-consistency claim is made.
- First complete local suite: 44 passed. Ruff and dependency checks passed. Later build
  and archive inspection outcomes are recorded separately.

## Investigated numerical/data issues

- A roughly 0.14 J/kg residual at a Cantera mechanism's 1000 K switch persisted under
  tighter integration and matched a direct thermochemistry discontinuity check.
- A 40-cell diffusion calculation missed its initial error target. An 80-cell calculation
  met it, with approximately fourfold error reduction per grid doubling.
- Cantera's C++ data directory lost non-ASCII Windows characters; Python loading and a
  native phase factory worked without changing the mechanism.
- Missing formula caches, invalid observations, absent times, unresolved pressure/flow
  references and acquisition omissions remain explicit rather than being fitted away.
- The documented isolated build succeeded. A later no-isolation build lacked setuptools
  in the runtime environment; it did not create a new artifact. The final snapshot uses
  a fresh isolated build and a new archive audit, rather than treating old files as a rebuild.

## 2026 10 27 — observation and adsorption continuation

- Added non-time tables with variable/reference identity, per-column origin, original row
  and experiment IDs, masks and content fingerprints. Time-series loaders also retain
  reference bases; unresolved reported pressure cannot be used as absolute pressure.
- Added whole-experiment splits, bounded native prediction fitting, scaled-Jacobian
  diagnostics and group-disjoint comparison. Unresolved/computed targets require explicit
  curve-reproduction purpose; no confidence or validation claim is inferred.
- Ingested 36 cryogenic H2 adsorption/desorption branches (860 records) and 16 SOFC curves
  (9080 records). Source pressure/STP/uptake contradictions remain visible.
- The SOFC reproduction fits three complete temperature curves and holds out 800 °C.
  RMSE is 0.0060712 V on that held-out curve; condition number is about 40907.5. Its
  unresolved source origin and shared apparatus remain limitations, not validated physics.
- Installed the exact MIT PSA-Dyna public snapshot separately and verified nine native
  equilibrium states/derivatives and one closed loading-LDF warm bed. Component and energy
  residuals are about 8.33e-17 mol and 4.41e-8 J respectively.
- Preserved the native 100 K temperature floor. Added request 005 for a proper cryogenic
  property/phase/inventory extension using the implemented native contracts.
- Acquired the open cryogenic source documentation for qualification: the public inventory
  now has 254 verified attachments, 2993321410 bytes across the same 23 acquired collections.
- Full suite after this implementation: 53 passed. Evidence regeneration and distribution
  audit follow the new source snapshot; the active objective remains broader than this milestone.

## 2026 10 27 — shared equilibrium release and native inventory

- Implemented one original isentropic-equilibrium short-nozzle kernel for gas, liquid,
  saturated and two-phase inlet states; these catalog families do not duplicate algorithms.
- Included both pressure endpoints, refined sampled maxima and required grid convergence.
  Explicit state/reference checks and surfaced EOS errors replace silent failed-sample omission.
- Final review found a narrow unsampled maximum adjacent to the back-pressure endpoint
  near the choking transition. Added boundary-cell optimization and analytical regression
  cases immediately below/at/above the transition, with explicit boundary resolution.
- Kept nominal geometry, effective-area factor and opening command distinct. Thrust is
  conditional on the declared area closure; nozzle quality does not create a ground fraction.
- Added immutable source windows with common-clock/spatial/opening identity and explicit
  termination. Native RK stages and retries are not accepted history samples.
- Coupled actual LH2DT homogeneous-tank depletion to the common nozzle. Native equations
  and RK4 remain in LH2DT. Gas and cryogenic bulk cases close mass/energy; accepted-node
  trapezoid errors decrease fourfold with time-step halving. Separate isolation windows
  verify zero subsequent boundary mass. Actual values and hashes are in `native_release.md`.
- Discovered the native negative-flow enthalpy override. Restricted the adapter to bulk
  withdrawal and expanded request 001 for selective liquid/vapor extraction and phase limits.
- Reviewed PRISM's equivalent HEM path and prepared request 006 for delegation to the local
  implementation. Sandia HyRAM+ remains an optional comparison candidate; its GPL solver
  implementation is not bundled in this core. No receiving repository was edited or messaged.
- Full suite: 66 passed; Ruff and dependency checks passed. The catalog now has 16 partial
  implemented families and three native-adapter checks out of 72 families. Experimental
  critical-flow qualification and the full facility objective remain incomplete.

## 2026 10 27 — public discharge data and conditional comparison

- Added the RADAR-KIT public metadata/file adapter for the CC BY 4.0 PRESLHY discharge
  collection, preserving DataCite rights, explicit archive version, file identities and MD5/SHA-256.
  Anonymous UI download links are used; internal backend links are not followed.
- Added explicit extension selection and download spacing. A 429 defers remaining dataset
  network requests without immediate retries and retains Retry-After; cached bytes are audited.
- Added a checked DisCha workbook profile, separate clock/header/data rows for generic
  Excel loading, readonly arithmetic-bin counts and gap-limited interpolation. Original
  recorder times remain alongside the author's synchronized time. Unresolved humidity
  scaling is opt-in; no concentration delay or clock shift is estimated.
- Applied four actual 1 mm warm experiments to an observed-P/T inventory/nozzle consistency
  comparison. A complete approximately 20 bar run is held out. The shared effective factor
  is about 0.6111, fitting RMSE 0.02265 and held-out RMSE 0.003612 of initial-window inventory.
  This uses reconstructed mass and observed temperature; it is not independent flow or
  tank-energy validation. More than 20 K between closed thermocouples remains material.
- Data exposed flat-maximum pressure convergence failures. Local-coordinate optimization
  alone was insufficient for a second state. Consistent single-phase sonic bracketing now
  resolves that maximum without changing the pressure/flux gates. Negative cases are retained.
- More precise liquid-path optimization exposed a tiny out-of-range CoolProp quality.
  Strict behavior remains the default. A bounded explicit budget retains the raw value and
  nozzle adjustment diagnostics; no density/enthalpy correction or physical extrapolation is made.
- Full suite at this stage: 81 passed; actual native tank depletion was rerun after the
  numerical correction. Experimental qualification and the full staged objective remain open.
- This acquisition checkpoint has eight of ten PRESLHY attachments (891491636 bytes).
  Two cold bundles remain deferred after server throttling. The total public inventory is
  25 cataloged / 24 with completed files, 262 files and 3884813046 bytes. No complete-dataset
  or independent-experiment claim is inferred from those file counts.

## 2026 10 27 — native supply network and property reuse

- Added explicit signed equipment transfers, heat/shaft power, missing-momentum semantics
  and native graph snapshots with actual component results. Basis labels cannot override
  a known contradictory native fluid identity.
- Composed existing phase-resolved tank, mapped pump, pipe/vaporizer and shared-kernel valve.
  No new equivalent tank, friction, map, heat-transfer or network solver was copied/created.
  The existing homogeneous engine is also reused in gas mode; filling fidelity remains separate.
- Checked every native RK stage, accepted nozzle histories and full external ledgers across
  three time steps. About 0.00309043 kg is delivered over 2 s with microjoule-scale energy
  residual. A converged but insufficient-NPSH graph is rejected. Pipe laminar limits and
  vaporizer enthalpy integration have separate numerical references.
- Found a native generic-ledger mismatch: two stratified ambient heat terms were omitted.
  The explicit host derivative view preserves native equations and changes a closed 0.1 s
  residual from about 5.52 J to 5.84e-12 J. Request 007 records heat/stage/accepted-step contracts.
- Measured repeated property-flash cost, then added a single-flash HEOS/native-state facade.
  Sixty state queries plus transport/saturation match; property-interface and complete
  same-step network speed ratios are about 22.7 and 2.34. Unsupported native methods stay
  absent; no cold table/fallback is used. The original property path remains a reference.
- Completed the last two PRESLHY attachments after spaced requests: ten files, 1313096235
  bytes, 160 workbook sheets and no container errors. Total inventory is now 264 files /
  4306417645 bytes across 24 acquired of 25 cataloged collections. No download is left running.
- Full suite: 91 passed, with native execution and benchmark records separate. Coverage is
  sixteen partial implemented families plus ten native-adapter family levels out of 72.
  Independent equipment qualification, finite line inventory/isolation and full scope remain open.

## 2026 10 27 — finite stored devices and prescribed command windows

- Reused native finite HEM line and vaporizer states, wall exchange and RK integration.
  Added original inventory/command contracts and a Python driver that partitions command
  times; no equivalent physical solver was introduced. Custom native nodes/readers remain usable.
- Preserved absolute ambient/derivative/control clocks across native local-clock restarts.
  Accepted rows match observed native solution objects by identity, removing a fixed RK-call
  profile from the new driver. Transition records retain both hydraulic limits and continuous inventory.
- Compared three steps for a synthetic mixed-phase line/restrictor/vaporizer. About 4.66e-6 kg
  leaves after feed isolation; after outlet closure, remaining assembly mass is conserved
  during heating/internal redistribution. Per-node residuals are about 1e-18 kg / 1e-13 J.
- Verified reverse transfer and an analytic ramp-ambient wall limit, including a nonzero
  operation clock. Wrong wall storage, missing heat/accepted identity, bad native ledgers
  and attempts to replace conserved fluid boundaries are rejected.
- Unsplit 0.1 s controls changed final mass by about -6.95e-7 kg while conserving their
  own fluxes. Correct scheduled timing and conservation are separate checks.
- Full suite: 99 passed. Coverage remains 72 families, sixteen partial implemented levels
  plus eleven native-adapter family checks. No independent experimental qualification is
  claimed; the combined finite tank/pump/line/vaporizer case, trigger/depletion handling,
  spatial refinement and remaining model families continue under the full plan.

## 2026 10 27 — combined finite supply and explicit equipment modes

- Added a reusable liquid-port tank/pump/stored-line/vaporizer builder accepting actual
  native models, states, factories and explicit power readers. Original native phase,
  friction, heat and integration responsibilities remain intact.
- Added explicit native mode delegation and the two-fluid/two-wall inventory reader.
  The ideal pump-isolation branch reuses the closed shared valve. Native zero-speed,
  rotor/passive-flow/casing capabilities remain in request 008; no failure selects a branch.
- Added accepted-sample integrals with both command limits, signed values and explicit
  basis/units/clock/method metadata. An analytic rate jump verifies the quadrature rule.
- Checked a full finite assembly with three short steps, independent delivery/shaft/ambient
  quadrature and per-node native inventory ledgers. About 3.0352e-5 kg is delivered; roughly
  1.5097e-5 kg leaves after upstream isolation. Same-step original/single-flash paths agree.
- Longer isolated heating reverses internal flow. The first 0.0025/0.00125 s pair closes
  inventory but fails the 1e-6 final-state gate. The tighter 0.00125/0.000625 s pair passes
  that gate. Accepted Darcy pressure loss is independently checked; wrong work and out-of-map
  points fail. Numeric caches remain ignored and are not distribution inputs.
- The finer Darcy check then found a native reported-zero residual inconsistent with its
  own flow/friction by about 44.31 Pa. The same discontinuous native law also fails a
  bracketed residual check despite a root flag. Added one original common Darcy magnitude
  solver and native-result bridge, with an explicitly selected direct fluids 1.3.1
  Churchill_1977 callback in the supply case. Native HEM viscosity remains unchanged;
  correlation choice and numerical convergence are recorded separately. Request 009
  specifies native delegation and public capabilities. No external solver source is copied.
- Full portable suite: 111 passed. The catalog still has 72 families with sixteen partial
  implemented and eleven native-adapter family levels. Nine receiving requests are local.
  Independent plant experiments, spatial/trigger/depletion and remaining scope stay active.

## 2026 10 27 — measured PEM protocols and native impedance observations

- Fully hashed four actual licensed CSV members, totaling 23764321 rows. The initial
  two POL_GEIS counters retain 14971 rows and 144 spectra/3312 frequency readings.
  Data are not treated as four synchronized files or 144 independent cells. Explicit
  SI conversions, masks, source rows, protocol labels, clocks and hashes are preserved.
- Actual zero-Hz/zero-ohm placeholders differ from the nominal missing-value description.
  Ascending sweeps are separated, and preceding DC holds are kept distinct from AC
  samples. Nominal 17-level assumptions were rejected after inspecting 18 actual
  sweeps per counter; counter-1 endpoints include repeated 12 A or actual 14 A.
  A 120 s replay DC-gap gate leaves 28 unknown operating contexts rather than imputation.
  Sparse corrected GC remains protocol-restricted and is not converted to crossover flux.
- Added read-only complex spectra with explicit phasor/origin metadata and correlated
  Cartesian projections into the existing observation/group/least-squares/SVD API.
  Actual MIT impedance 1.7.1 circuit objects retain responsibility for circuit physics.
  Analytic alpha=1 RC-limit agreement is 3.47e-18 ohm. The optional import's missing
  pandas dependency was reproduced, then explicitly declared in the `eis` extra.
- Fitted one complete 12 A sweep per cell with unchanged bounds/starts/topology. Four
  of eight complete repeats fail the predeclared 1 milliohm diagnostic. All three fixed
  Reference coefficient transfers fail. Condition numbers reach about 69680 and the
  Reference inductance reaches its lower bound; those limits remain public evidence.
  Small residuals do not establish unique electrochemical mechanisms or aging laws.
- Demonstrated explicit R0×area callable reuse in the existing OhmicLoss without another
  static stack implementation or automatic membrane interpretation. Detailed replay,
  API/manual/source/rights records and original locally generated plots are reproducible.
- Full suite: 117 passed. The historical 20-dependency environment is preserved; the
  current observed 41-dependency environment is recorded separately. Family coverage
  remains sixteen partial executable plus eleven native-adapter levels out of 72.
  Nine existing receiving requests remain local; other repositories are unchanged.

## 2026 10 27 — native dynamic pool and conservative emitted-mass intervals

- Added actual DynamicLH2PoolX 0.2.0rc2 runner/config/result reuse. GitHub revision and
  PyPI module hashes agree. Surface, radial grid, source history and boundary metadata
  remain caller supplied; no spreading, evaporation or integration implementation is copied.
- Added a finite absolute-clock ground-input binding with explicit saturated normal-
  Hydrogen state and source evidence. Para relabeling fails. Original step integrals
  independently check every native mass ledger, adjustment, escape, phase property and
  interval mean. Ten portable tests cover positive and failed contracts; full suite 127 passed.
- The independent input check exposed a native event/rate comparison inconsistency:
  a near-knot clock gives one extra 0.00025 kg supply step despite an internal residual
  about 7e-18 kg. An explicit 1e-10 s input-clock budget delegates the native rate at
  known knots and retains all corrections; the finest case needs only 4.44e-15 s.
  Default budget remains zero, with unchanged independent mass gates.
- Three coupled coarse pairs fail a fixed 1% inventory/supplied-mass target. Refining
  to dr=0.0025/0.00125 m and maximum dt=0.00125/0.000625 s passes at about 0.734%.
  Separate time checks pass 0.2% but are nonmonotone; no convergence order/uncertainty
  is inferred. Domain enlargement, failed truncation, zero thermal drive and independent
  capped-conduction quadrature are recorded.
- Added one shared read-only finite-interval mass/state source with explicit constant-
  mean representation, clock/window guards and conservative rebinning. Native cumulative
  evaporation gives 0.0282498734 kg, including 0.0244166527 kg after input isolation.
  Sparse last-step-rate trapezoids give 0.0319561560 kg and are retained as a negative case.
  Zero reported radius does not erase liquid/evaporation; tiny residual inventory remains.
- Added E3.4 discovery/rights metadata: 26 cataloged collections, 24 with attachments;
  acquired scope remains 264 files/4306417645 bytes. All eleven CC BY-SA E3.4 attachments
  are withheld under the current policy. No upstream experimental derivatives are copied.
- Added request 010 for native clock correction, explicit property identity, radial
  restart/accepted snapshots, interval-area/mass and independent heat ledgers. It is
  prepared locally only. The catalog has sixteen partial executable levels and twelve
  native-adapter levels out of 72. Independent pool accuracy and complete atmospheric
  geometry/momentum/impact physics remain open. Current environment has 42 recorded dependencies.

## 2026 10 27 — shared gas boundary and actual native calm jets

- Added an optional import-free DEGALI adapter using actual injected expansion/source/
  enthalpy/model objects. A single shared nozzle supplies its throat; gas-phase PH,
  effective pressure area, momentum, h+KE, spin/reference and explicit virtual-plane
  position/vertical-frame checks precede the native jet. No second choking/jet solver
  or source data is copied into this repository.
- Checked exact MIT native revision `6ead182dc19039725a0b40811b48c6d39f947790`, package
  0.3.0, with a module-byte fingerprint. Current PyPI 0.1.0 is not assumed equivalent.
  Added a separate pinned native installation recipe and a 43-package observed main
  environment, including MIT PyAMG 5.3.0 required by broad native imports.
- Retained both native density-profile four-flux initialization failures. An explicitly
  selected independent temperature/composition profile closes initialization. Its density
  differs from the analytic Gaussian density deficit assumed in the native vertical force.
  An original actual-native subclass uses the native radial buoyancy integral for only
  that source, retaining the native Jacobian, profiles, other sources and integration.
  The bridge rejects coflow and does not patch native/global code or fit coefficients.
- The authored normal-H2 jet passes fixed conservation and endpoint/force-integral gates
  at 321 radial points. Initial coarse species/momentum/energy failures remain reported.
  Maximum finest energy error is about 0.025 W against a 0.118 W budget. The cold para-H2
  case fails the energy budget after 81/161/321/641-point refinement: about 0.346 W at
  finest against an unchanged 0.238 W. Its endpoint Y/T and mass/momentum agreement do
  not make it a passed prediction. A preliminary expensive cold DOP853 diagnostic was
  interrupted without a completed solution; switching methods is not claimed as a cure.
- The default host raises with actual failed results retained. Spatial observation tables
  preserve whole-mixture Y, bulk density/T and predicted origin; no fake clock or gas-probe
  mole fraction is invented. Native phase tables are not a complete real-mixture EOS.
  Finite-source travel/development clocks, pool geometry/momentum, phase/probe observations,
  gravitational-energy limitations and independent field accuracy remain open.
- Added twenty-three contract tests; full suite 150 passed, Ruff and pip dependency checks
  passed. The full two-fluid numerical research script intentionally exits nonzero after
  preserving positive and failed results. Added request 011 locally without editing or
  messaging the receiving repository. Catalog: 72 families, sixteen partial implemented
  levels, fourteen native-adapter levels, forty-two planned. No new raw data acquired;
  broad research objective and remaining staged implementation remain active.
- A final output-contract review added raw native retention for malformed arrays/fields,
  alongside rejected physical audits; shape/nonfinite/missing-output negatives are covered.

## 2026 10 27 — measured spatial jets and reference-conditioned native roots

- Completed acquisition of the seven-attachment CC BY 4.0 mechanical-ventilation source.
  The added apparatus description is 706086 bytes, publisher-MD5 verified and SHA-256
  recorded. Current total is 265 attachments / 4307123731 bytes across 24 collections;
  26 collections remain cataloged. Raw data/source illustrations stay excluded.
- Added a spatial workbook profile: 42 sheets / 5256 sensor rows from four concentration
  workbooks, distinct scan rows/channels/cells, moved repeated grids and immutable masks.
  Retained 26 ambient-room conflicts, 36 inconsistent summary-order points, 31 domain/
  missing statistic issues and one He/H2 sheet-identity conflict. The 1 mm / 1 g/s calm
  source conditions are not automatically swapped. Zero readings are not missing values.
- Added measured-flow source conditioning by inverting the one shared nozzle at declared
  T0/area. Equivalent stagnation pressure is reconstructed; the remote pipe pressure,
  source temperature assumption, bracket, sample monotonicity and root error remain explicit.
  No second flow model, measured-pressure relabel or fitted contraction factor is used.
- Added explicit unbounded relative geometry and a Cartesian dry-gas observer using native
  curved trajectories/profiles. Gas-volume approximation, 200-300 K / <=200 kPa dry envelope,
  radial tail choice, axial masks and diagnostic-only failed-run permission are recorded.
  The mixed-box enclosure module was not substituted for these jet scans.
- Identified native initial-root conditioning under near-cancelling source energy. An
  original actual-native subclass expresses E as E+C*H2_mass_flux and shifts its source
  identically, retaining the native root/ODE/tables/profiles. C=source specific KE is a
  numerical reference, not a fitted physical coefficient. Host budgets/scale stay in the
  original reference; raw native and read-only original energy are separately available.
- C/2C initial states agree near 1e-15. Full low-flow/held-out gas-observer RMSE changes
  are about 5.2e-12 / 3.4e-12 with unchanged physical audit classifications. Four of five
  finest measured-source cases pass numerical gates; 4 mm / 1 g/s still fails energy
  (about 0.131 W against 0.00764 W). All five retain failed authored accuracy targets.
  Held-out 4 mm / 5 g/s has about 2.90 volume-percentage points RMSE and 18.07 maximum.
- No concentration coefficients were fitted; source/probe/wall/humidity and historical
  data-overlap limitations remain. Fine-pair agreement and overall valid coverage do not
  make the failed comparisons qualified predictions. Original plots identify both statuses
  and credit the numeric source. Start/end fingerprints detect source edits during a run.
- Added 33 tests; full suite 183 passed, Ruff and pip checks passed. Updated native normal/
  para baseline checks retain the previous cold failure. Extended request 011 locally.
  Current scope remains 16 partial implemented and 14 native-adapter levels out of 72;
  PROGRESS.md records a 25-35% overall effort estimate and the distinct 30/72 coverage metric.
  The full objective stays active; receiving repositories/publication remain unchanged.

## 2026 10 27 — finite carrier reactions and computed data qualification

- Added one shared finite stoichiometric/enthalpy core for supplied conversion. Element,
  charge, atomic-weight basis, finite reverse/forward limits, phase, formation reference
  and T/P domain are explicit. Heat normalization/sign and caller/native objects survive
  deep Python composition. Existing Cantera equilibrium/reactors remain reused.
- Added optional RDKit 2026.9.1 native molecular identities and the actual Cantera
  species-enthalpy adapter; documented BSD core versus MIT wheel-builder license scope.
- Audited the actual 10373-row carrier table. The web table is an exact duplicate;
  canonicalization finds 10345 pairs. All 28 repeated pairs have conflicting heats;
  56 rows are withheld from automatic heat input. No average/first-row repair is used.
  Nine capacity discrepancies remain source issues on the consistent native mass basis.
- Added source-specific reference normalization at 298.15 K/101325 Pa, a full-table
  replay and an independently checked native prescribed-conversion enthalpy example.
  This is computed gas-reference evidence, with liquid, kinetic and experimental scope
  open. Added 21 tests: full suite 204; lint/dependency and distribution checks accompany
  this checkpoint. One partial family advances: 17 implemented + 14 native-adapter,
  41 planned, from 72; the full programme remains active and local.

## 2026 10 27 — user-selected dispersion providers

- User chose HyRAM gas / SLABx-LH2 liquid-origin priority and requested frequent progress
  updates and parallel local development. AGENTS and PROGRESS preserve these requirements.
- Implemented actual-native optional gas/source/SLAB adapters and origin-based selection;
  native objects survive Python composition. Existing DEGALI evidence remains explicit.
- Reproduced HyRAM6.1/SciPy1.18.1 callback failure; compatible SciPy1.16.3 target executes.
  Default and compatible-runtime source suites pass 212 tests at this checkpoint.
- The authored native gas case retains a 23.31% upstream-to-Gaussian H2 initialization gap,
  separate from approximately 1.63e-10 kg/s subsequent transport drift. No fitted source
  correction is applied. Actual steady SLAB vapor source/premise checks pass at 5 m/s;
  0.2 m/s violates its native premise and is rejected. Detailed replay and request012
  preserve both outcomes. Family coverage remains 31/72; overall effort remains 25-35%.

## 2026 10 27 — parallel measured-data and native gas references

- Implemented bounded MAT and streaming XLSX pressure-peaking observations; verified
  all acquired file receipts and inspected over 41 million rows. Preserved signed source
  signals, sensor metadata, unresolved pressure/concentration bases and independent clocks.
- Added native frozen ideal-gas PT/PH/PS with explicit composition/formation/spin identity,
  selected-fit bounds and recorded optional native trial-state sum corrections. Reused
  the one shared nozzle and actual native phases; no additional EOS or choking code.
- Added native finite open nonreacting gas volume with actual reservoir/flow/wall/solver
  objects and appended mass/species/energy integrals. Analytic, independently integrated,
  native limit and refinement gates pass. Appended energy state scaling conditions
  zero-start absolute-clock integration; physical rows and fixed outer gates stay intact.
- Full integrated source suite: 263 passes; new scripts retain actual native outcomes.
  Two partial first-level families advance the catalogue to 17 implemented + 16 native-
  adapter levels, 39 planned, out of72. Overall programme remains active, estimated 25-35%.
  Independent experiment/source/clock/geometry and full facility qualification remain open.

## 2026 10 27 — parallel equipment and finite hydride

- Delegated disjoint native-insulation, compressor and finite-hydride implementations
  while the parent built full-channel AB2 observation qualification. Local numerical
  jobs ran independently; parent reviewed physics identities and integrated evidence.
- Reused actual native LH2DT heat/compressor/property objects, existing power/inventory
  contracts and shared hydride kinetics. Added finite closed gas/solid conservation
  with an explicit chemical internal-energy zero; no duplicated native EOS or rate law.
- Preserved native capability/zero-area failures, imposed cooling/throughput limits,
  small PH ledger discrepancy and unresolved measured clock/unit/sensor semantics.
  Request013 makes receiving changes concrete without editing another repository.
- Added68 source tests (full331 pass), four native/data replays, Python examples,
  public primary references and continuation documentation. Two first executable
  families advance coverage to35/72; hydride depth and data rows add no extra families.
  Programme estimate25-35% remains uncertain and the complete objective stays active.

- Parallel review caught a cross-workbook row-ID collision when physical experiment
  groups are shared. Added source-byte identity without changing that grouping,
  a dedicated regression, and replayed final-source full data qualification.
  Final default331 and compatible330 plus final9 scoped checks pass.

## 2026 10 27 — pressure protection, vents, recovery and observations

- Parallel native tasks implemented transactional pressure relief with physical
  pressure events, finite-UA vent transport and steady/finite recovery. The parent
  added native instrument response and observation qualification. No native source,
  EOS, choking law, cooling equation or response integrator was copied/duplicated.
- Added independent inverse-UA/final-momentum checks and an actual-provider low-Mach
  gate after a small-pressure-drop counterexample. Retained native transition,
  clipping, evaluation-order, cooling-capacity and phase/domain failures explicitly.
- Added75 source tests; full406 cases pass default and compatible SciPy environments.
  Native replays, public examples, source/rights ledgers and request014 are concrete.
  A parallel read-only review found instrument timing/data roles and recovery request
  semantics consistent; the source fingerprints match final bytes.
- Coverage advances35/72 to39/72, without duplicate family inflation. Full programme
  effort is re-estimated30-40% as this equipment/control/observation foundation grows;
  independent experiments, remaining33 families and facility qualification stay open.

## 2026 10 27 — spin, two-fluid heat, reactive flow and compressor observations

- Continued disjoint parallel development and local numerical/data jobs. Native
  spin conversion and two closed finite fluid/wall sides completed while the
  parent extended the existing native volume to gas reactions; another task
  qualified source-specific MHC compressor workbooks. Shared physics was reused.
- Added independently owned native thermochemistry after generic cloning lost
  authored thermo bounds and direct Species/Reaction reuse retained mutable
  aliases. One-time structural coefficient-copy audits and exact owned-definition
  guards separate reconstruction roundtrip from later mutation. Explicit
  time-only callbacks remove the expensive full-definition serialization per RHS.
- Added steam/oxidative gas references, a plain unextended native trajectory and
  separate reaction/boundary/element/U ledgers. Formation energy is counted once.
  Scalar spin enthalpy and closed thermal groups retain their narrower domains.
- Corrected source-clock serialization using reviewed Date/Time headers and the
  workbook epoch, with ISO/German/Excel/1904 and unsupported scalar-clock tests.
  Original signed/missing/source fields and raw/selected experiment dependence
  remain preserved. No coefficient fit or automatic recorder alignment was added.
- Final472 cases pass both default/compatible source suites;66 new tests comprise
  15 spin,12 thermal,9 gas reaction and30 MHC cases. Public source/capability
  documentation and request015 record limits; no receiving repo or remote was changed.
- Read-only review corrected a zero-interwall-conductance interpretation and a
  minimum-composition gate label to match its accepted-output sampling evidence.
  Coverage is42/72 first levels; uncertain full-programme estimate remains30-40%.

## 2026 10 27 — fire diagnostics, conditional blast and inverse heat

- Parallel tasks executed actual native Flame, standalone blast and eight-file
  thermal observations while the parent integrated pifira contents heat and area.
  No native fire/chemistry/EOS/blast equation or coefficient table was copied.
- Kept source/caloric/fuel-origin transport failures under independent quadrature
  and native refinement. Default fire API rejects; diagnostic irradiance does
  not become a wall heat input. Request016 records concrete native corrections.
- Reused actual public static blast evaluation with explicit participation/energy
  rather than a fabricated Jet or an invalid field. Added conditional threshold
  inversion, reference/frame/domain guards and numerical limiting cases.
- Added native pressure-rise contents heat, direct-EOS forward/inverse checks,
  explicit energy scope and native area fit. Read-only review found a bare-height
  offset ambiguity; explicit axial intervals now retain true overlap, including
  zero area, with regressions and provenance in returned objects.
- Acquired three missing thermal files against pinned version1 metadata, preserving
  prior file/supporting-metadata identities. All245 vectors/157964002 elements
  were audited; clocks, signal roles and masks remain unqualified where necessary.
- Added80 cases; native-enabled main/compatible full suites pass552 each. Default
  without explicit native target passes530/skips22; skips are recorded separately.
  The native flat-fit covariance warning and physical fire failures are retained.
- Coverage advances42/72 to44/72 through conditional blast and inverse contents
  heat only. Fire remains planned; full-programme estimate stays30-40%. Receiving
  repositories, remote publication and external communications were not changed.

## 2026 10 27 — cryogenic storage, rotor terms and spherical transport

- Reused disjoint parallel tasks and actual local processes. Native cryogenic
  storage and rotor constitutive interfaces developed while the parent unified
  planar/spherical diffusion and finite cavity gas feedback. A separate task
  qualified the existing biological workbook without inventing model inputs.
- Preserved actual native tank/wall, event, nozzle and property owners. Tested
  fixed-spin high-pressure warming, finite-wall energy, signed heat and real
  pressure opening/floor behavior. Native zero-UA geometry remains rejected;
  request017 specifies exact adiabatic/decoupled support for another session.
- Kept absolute rotor storage distinct from a frozen-EOS correction and U
  distinct from an evidenced H mapping. Native92/primary90 density difference,
  strict composition envelope and mathematical low-ortho limitations remain
  visible. No second spin trajectory ODE or evolving-spin liquid EOS was added.
- Extracted one conservative material core with true spherical volumes and
  integrated radial resistances; legacy slab units and analytic/trap behavior
  remain intact. Finite cavity pressure/fugacity reuse existing native gas
  thermodynamics. Temperature is prescribed; heat/stress/optical scope stays open.
- Cross-review found a completed-trace loss on post-run cryogenic audit errors.
  Corrected wrapping and added actual endpoint/PT/Prho regressions, retaining
  original causes and native state/time/prefix. A second read-only review passed.
- Qualified830 biological rows, preserving masks, reconstructed targets,
  duplicate reported days and source algebra differences. The dataset does not
  identify growth kinetics, reference gas mass or independent reactor replicates.
- Both final full suites pass629 on unchanged194 Python source/test/script
  files; main/compatible runtimes130.60/130.08s. Added77 tests. Native replays
  pass18 cryogenic,18 rotor and14 spherical gates. Ruff/dependencies pass.
- Coverage is46/72 first levels, with18 partial implementations/28 native
  adapters/26 planned. Programme effort remains an uncertain30-40%. Remote
  publication, other repositories and external human communications were unchanged.

## 2026 10 27 — photons, gas/solid conversion and warm multibed cycling

- Continued disjoint parallel native-cycle, multiphase and data work while the
  parent implemented explicit spectral optical/electron accounting and reused
  the existing finite stoichiometric/caloric core. No duplicate equilibrium,
  bed, cycle or reaction trajectory solver was introduced.
- Added actual native Mixture TP/HP states with owned gas/solid definitions and
  extensive SI ledgers. Preserved the real zero-carbon candidate HP failure;
  it is not asserted to be merely a final-temperature limit. Source/owned
  definition hashes, fit bounds, constant-volume density and raw failures remain.
- Executed native two-bed warm pressure/thermal schedules to actual56-cycle CSS.
  Kept startup inventory contribution, final-cycle ratios, native reporting and
  qualified-stream status distinct. Synthetic non-enrichment is retained.
- Cross-review corrected optical coefficient reuse on a different wavelength
  grid and native N2-output gates being applied to host H2 recovery. Added
  regressions and verified the optical fix through direct-construction/result
  replacement probes. Neither repair changes the native physical solver.
- Native Cantera file lookup failed on the workspace's non-ASCII absolute path;
  reading unchanged hashed native YAML bytes through Python preserves the same
  source and parser without a mechanism/environment change.
- Qualified all37 text exports rather than accepting an earlier generic TXT
  numeric0 result. Retained source-derived rate/AQY, masks, ambiguous columns,
  repeated controls and within-study dependence. Missing apparatus evidence
  remains open and no universal catalyst model is fitted.
- Final full suites pass705 each on unchanged206 Python files, main127.44s and
  compatible126.92s. New76 tests and three14-gate native/optical replays pass;
  source/data rights and documentation/request018 are updated together.
- Current first-level coverage49/72 does not finish the full programme:
  19 partial implementations,30 native checks,23 planned; uncertain effort
  remains30-40%. No remote publication or receiving repository was changed.

Final staging found one trailing whitespace in the multiphase replay script.
Its cleanup preserves the parsed Python AST; all production and test bytes
remain identical to the705-case full suites. The native replay was repeated
with the final script bytes and its source identities regenerated.

## 2026 10 27 — porous gases, staged thermal conversion and native biology

- Continued disjoint native transport/caloric/biological development with local
  finite calculations. Parent thermal stages reuse existing reaction conversion
  and common-reference calorimetry; no duplicate native EOS, transport or ODE.
- Added two-point native DustyGas transport with explicit geometry, stationary-
  solid total species flux, SI conversion and source/transport copy guards.
- Added common gas/pure-solid enthalpies with declared authored density evidence,
  fit bounds and source/owned binding guards. Independent review found native
  provider rebinding could retain stale identity; final guards reject it.
- Added finite staged feeds/takeoff, carrier/T/amount closure and signed/gross
  enthalpy ledgers. Reused mutable property buffers and finite-input arithmetic
  overflow have direct regression checks and retained accepted prefixes.
- Actual QSDsan/BioSTEAM finite ADM1 exposed the published initial-array alias.
  Used the official immutable fixed source in an isolated target, preserving
  native equations and solver. Native closed-output and coarse ledger failures
  remain explicit. NCSA installed licenses/source hashes are recorded.
- Checked nonfinite native rates and primary/secondary failure retention.
  Broad host regressions run in parallel shards with an independently isolated
  native biological execution. Detailed numerical evidence is in PROGRESS and
  the four current research reports, with exact source hashes.
- Coverage52/72 first levels,20 partial/32 native/20 planned; programme estimate
  remains uncertain30-40%. No experiment validation, publication or receiving
  repository implementation is inferred from these bounded checks.

## 2026 10 27 — finite separation/compression and statistical composition

- Coupled existing native DustyGas to two actual finite native gas reactors in
  one ReactorNet. Independent derivative units and finite Knudsen exponential
  checks distinguish native ownership from duplicated transport/RHS code.
- Kept same-T thermostat duty, partial-H and U/species ledgers explicit. A first
  native boundary failure is sticky; bounded raw numerical trials and admitted
  output states do not assert internal accepted-step or event-root completeness.
- Extracted one port-capable finite hydride state/rate core and reused it for
  closed simulation and actual finite native source/receiver thermal compression.
  Shared kinetics/reference/nozzle/native vessel derivatives retain ownership.
  Independent review and closed16-case checks pass. Initial/ending bound-H and
  thermal inventories remain visible rather than being forced to CSS.
- Added native independent-input QMC/Sobol analysis around Python models with
  immutable law/unit/basis metadata, coordinates and actual response/raw cases.
  Review found during-callback coordinate rewriting and invalid returned raw
  loss; repaired and added direct regressions/native physical-object probe.
  Retained the real native1x1 scalar failure and no-identifiable-variance meaning.
- Qualified all9 acquired material assets and source-specific property roles.
  Preserved40composition conflicts, dictionary/version discrepancies, missing
  units/pressure bases, formula/cache status and non-independent source lineage.
  No physical fracture fit or independent experiment validation was invented.
- Both final unsharded profiles pass870/11optional skips on unchanged230 Python
  inputs. Native finite membrane/compression/statistical replays pass17/20/13
  gates; current statistics also pass native1.16.3. Shared affected prior
  hydride/microsphere replays were repeated with the refactored source.
- First-level coverage54/72,21partial/33native/18planned; uncertain programme
  effort stays30-40%. Manuals, model inventory, data qualification, source and
  receiving request020 are updated together. Remote repositories/publication
  remain outside this local checkpoint.

## Wave, supplied exposure, BLEVE data and conditional-risk continuation

Three independent implementation/data lanes were combined with local native
runs. Actual SDToolbox was obtained from the official Caltech distribution;
archive and native headers disagree in date labeling, so the original source
hashes identify the reviewed code. It executes with installed Cantera3.2 and
retains its original algorithms and native source/owned phase objects.

Native HyRAM supplies thermal dose/probit/CDF and model-specific pressure
response. A convenience-wrapper discrepancy for unused zero impulse is retained;
the adapter calls the actual selected peak function without a fake impulse.
ELVHYS files were fully inspected, but their LH2 BLEVE initial conditions are
not a homogeneous premix for direct CJ comparison. Unresolved pressure/clock
and temperature-channel semantics stay explicit instead of being repaired.

The host connects supplied finite mass, actual native exposure and explicit
frequency/branch/occupancy evidence to the user's existing native conditional-risk
module. Review found that replacing a cached computed probability could retain
unrelated native evidence. The exposure owner now verifies its original result
by replay before risk binding. Missing physical source state and invalid copied
state are also rejected. Actual native requests/outputs/receipts and original
failures remain available. The script avoids retaining unused failure cycles;
this removes native-object shutdown warnings without dropping library evidence.

These changes add three executable first levels, not a validated full accident
chain. Request021 gives native capability and data clarification work for other
repositories. No receiving project was edited and nothing was published.

Parallel full-suite execution exposed a test-only workspace race: a global
cleanup assertion saw another process's legitimate native YAML bridge. A real
second bridge held open reproduces only that assertion, while the isolated
case passes with its original domain failure/cause/native objects preserved.
Verification factories need separate ASCII workspaces for concurrent campaigns;
the production solver already uses unique temporary subdirectories.

Final frozen-source regression after the workspace correction:970pass/11skip
in main SciPy1.18.1 (258.49s) and compatible1.16.3 (258.57s).
All242 Python inputs remain byte-identical at both run boundaries. Current
catalog57/72 first levels does not complete the full research goal. Full-source
and installed distribution checks are recorded separately after the build.

## Finite O2, ordinary-air thermal state, monitoring and new enclosure data — 2026-10-28

First executable coverage advances57/72 to59/72, about82%:21 partial implemented
families,38 checked native-adapter first levels and13 planned families. O2 and
ordinary-air thermal state are distinct portions of effects.cryogenic, counted
once. Native learned residual monitoring adds the other first level. Full-programme
effort remains an uncertain30-40%; independent validation, remaining physics
and the accepted full facility/accident chain are incomplete.

The two unsharded final profiles each pass1088 cases with11 explicit optional
biological skips: NumPy2.5.4/mainSciPy1.18.1 in306.49s and compatible
SciPy1.16.3 in306.49s. All255 final Python source/test/script hashes
match at start/end and current source. Biological skips are not new execution
evidence. Existing native difficult-event warnings and the inverse-fit warning
remain in ignored logs. They do not turn a rejected physical case into a result.

Actual native O2/thermal/monitoring replays pass23/15/18 gates in both profiles.
The source-specific new data tests pass18cases. Native O2 source/room/nozzle
and caloric references, actual source partitions and U/species/pressure ledgers
are retained. Owner-built results are verified against original native traces
before criteria use their summaries; replaced O2/clock/context records reject.
Native JOS3 owns17segments/85nodes; actual implicit heat storage/rounding and
10/5/2.5s refinement pass within the declared ordinary-air/nonfreezing domain.
Integer-microsecond stepping rejects nonadvancing absolute clocks before execution.
The native global shivering limiter and unsupported custom heat boundaries remain
out of scope. Native learned causal PCA/mode models retain independent whole-run
fitting/calibration/evaluation and native trained state; method/signal rebinding
is rejected. Scores do not identify faults, trigger controls or infer annual risk.

New ELVHYS4.2v1.1 acquisition is198/198assets/1429209739bytes, zero omissions.
Complete195CSV audit covers40actual versus48nominal cases,8150693rows and
89332905sourcecells:85607986finite numeric,72078446ingestion-valid and
17254459masked. All source/MD5/SHA/metadata/receipt/code and alternate-block
checks pass in195.0913613s. These correlated cells are not independent experiments.
No O2 time history or qualified H2 mass release is supplied. Source-normalized/
delay-aligned H2, unresolved clocks/sensor roles/locations and invalid27/28 stay
explicit. The separate Dryad O2 discovery has two HTTP401 attachments and zero
acquired observations. Overall28collections have466successful attachments/
6017963546bytes,25collections with acquired files.

A separately reproduced original SLABx-LH2 diagnostic has positive O2 condensate
with4.3197363% excess remaining-gas saturation and different feed/gas H2 bases.
Its7negative-evidence gates retain the original failure; no host phase repair,
new accepted family or O2/source/dispersion qualification is inferred. Existing
preferred-provider failed physical premises remain rejected.

Current detailed contracts and evidence are OXYGEN_DEFICIENCY.md, JOS3_THERMAL.md,
PROCESS_MONITORING.md, OXYGEN_OBSERVATION_DATA.md and their research reports.
Request022 states native/source-data receiving changes. No receiving repository
was modified and no publication was performed. The full goal remains active.


Cross-review closed three concrete ownership/clock defects: native monitoring
class method forwarding escaped source/model hashes; two already-corrupted
TimeSeries clocks could agree while both empty; replaced O2 summaries could
retain original native traces. Native method/code/current signal revalidation
and native snapshot-bound O2 verification now reject those exact reproductions.
JOS3's large absolute clock could otherwise repeat an unadvanced step; integer
microsecond elapsed time and representability guards close the actual example.
The original failed probes remain ignored and final frozen profiles above pass.

The actual native air diagnostic is recorded with its original saturation/
composition mismatch, not silently fixed or coupled into a room. All work stays
local and original native code remains unmodified. Installation/distribution
execution is recorded separately after the final source build.

## Parallel coding priority; deferred validation — 2026-10-28

The latest user direction supersedes the earlier local-testing workflow: code
models in parallel and run tests later after connecting Nurion. No additional
local pytest, native simulation/replay, benchmark, example or scientific case
execution was performed for the new wave. Only static syntax/lint/TOML/source
and licensing inspection supported development. No scheduler job was submitted.

Three model families now have implemented_unverified source: native PV/directDC
nonlinear electrolysis coupling and finite production/receiver inventory;
actual HELPR hydrogen/Paris constitutive laws with SI mode-I geometry and finite
cycle/events; and shared-kernel finite solid decomposition/hydrolysis with
finite supplies, prescribed takeoff and thermal endpoints. No duplicate PV,
growth, fugacity, reaction or EOS solver was introduced. Their original objects,
raw return/failure evidence and unresolved scopes are in their manuals/development
records. Native API inspection and written cases are not runtime acceptance.

The new increment has22 deferred scientific cases:9PV,4fracture and9solid,
including separate native-caloric solid coverage. Python cases/parameters/outcomes
and an unsubmitted PBS array generator are implemented. The helper and scheduler
integration are themselves unexecuted. Actual cluster paths, native Linux
environments, queue/account/resources and source/plan revision are future inputs;
no credentials or connection are assumed.

Coding inventory:62/72 (about86%) including3unverified; last actually executed
first-level evidence:59/72 (about82%),1088passes/11optional biological skips in
each recorded profile at6eae06c. Full-programme effort remains an uncertain30-40%
with independent validation and a qualified full accident chain unfinished.
Historical source hashes for6eae06c are retained in research/checkpoints/6eae06c.toml.
The current parallel_checkpoint.toml records static development bytes only;
it must not be read as a fresh test pass. The preceding6eae06c build also has
post-build content/installed checks deferred, and the last fully inspected
installed-artifact checkpoint remains785dae7.


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

Read POOL_FIRE.md, VESSEL_FAILURE.md, HYDROGEN_ECONOMICS.md and
DROPLET_TRANSPORT.md for contracts. Incident liquid is not pool deposition;
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
Request025 records specific native APIs, evidence and coupling work. A CC0-claimed
MEC dataset candidate is recorded in research/microbial_electrolysis_data_candidate.toml;
no data assets were acquired, no source schema/units were qualified, and the
existing28 collections/466 acquired files/6,017,963,546bytes are unchanged.

The remaining planned families are obstacle-resolved dispersion and accepted
jet fire. Every partial family also retains the limits in MODEL_CATALOG.md;
70coded families are not70complete models. Last full installed-artifact audit
remains785dae7; later source/artifact acceptance is still deferred.

The prepared cluster worker now runs each case in its unique absolute evidence
working directory, with the pinned repository on the Python import path. Native
relative result/log files cannot default to the shared checkout. The original
working directory is restored before final reporting. This scheduler/worker
change is also unexecuted; static inspection does not prove cluster behaviour.

Static integration review also required owner-issued unchanged impact steps
before pool initial-stock handoff. Changed deposited-mass clones and modified
retained native incident arrays now have rejection definitions in the existing
impact case; the8case count is unchanged. The material-front clock projection
fix received a targeted second static review. Changed Python files passed AST
and Ruff, and changed TOML/text passed syntax/LF checks. No scientific result
is inferred from those inspections.


## Obstacle CFD, fire diagnostics and deep cost/evidence coupling

The new optional FDS6.11.1 adapter generates original three-dimensional obstacle
inputs and audits actual native process/CSV/geometry outputs for a sealed warm
low-Mach reference enclosure. It is implemented_unverified, not a fallback for
preferred HyRAM gas or SLABx-LH2 liquid-origin dispersion. Actual FDS binary,
build/runtime rights, execution and measured-field qualification remain pending.

The HyRAM common-reference species/element mass, formation-enthalpy, kinetic and
radiation ledger is diagnostic only. Original mass/caloric failure remains;
required missing heat is unknown and jet-fire stays planned/rejected. The new
warm authored example is not a successful replay of the earlier failed source.

An actual MEC trace now reaches the existing finite tariff/annual/native pyH2A
owner without a fake PV trace or duplicated financial equations. Generated,
stock and unavailable harvest/sale remain distinct. The narrow subclass and
missing public projection/source-geometry verification hooks are documented in
MICROBIAL_ECONOMICS.md and Request026; this adds no catalog family.

The new read-only campaign collector requires explicit job/source/plan/runtime
identity, retains missing/incomplete/inconsistent/rejected/failed separately,
and hashes native files without loading or executing them. Complete worker
records are not independent scientific qualification. Its large-integer and
nested-metadata error paths were corrected after static peer review; a targeted
second review found no remaining concrete defect in that change. It has not
been invoked, tested or supplied fake result fixtures.

Partial implementation inventory is71/72 (about99%):21 partial implemented,
38 historically checked native adapters,12 unverified and1 planned. Rejected
jet diagnostics do not count as a predictive first level. Last executed coverage
remains59/72 (about82%) at6eae06c; overall programme effort remains an uncertain
30-40%. Every partial family's remaining physics/data/qualification still applies.

New deferred definitions:4obstacle,6jet-conservation and4MEC-economics cases.
The combined pending campaign is76 cases, not76passes or a complete regression
inventory. Legacy source/native/data/installed suites are still required later.
No local scientific calculation, case discovery, native import/installation,
example, test, replay, benchmark, build or remote job was executed for this wave.
Dataset totals remain28collections/466acquired assets/6,017,963,546bytes.

## 2026-10-28 parallel API and observation checkpoint

Implementation remains unexecuted. Parallel coding delivered a common physical
economics projection/quantity contract, producer-issued MEC trace checks with actual
single-cell geometry, and public Cantera source/phase handles and bindings.
Explicit mass-density access avoids display-basis ambiguity; molar-display FreeFlame
startup is rejected. Source-byte verification does not attest transitive resources,
binaries, hidden callback state or scientific accuracy. See CANTERA_FACTORY.md,
HYDROGEN_ECONOMICS.md, MICROBIAL_CELL.md and MICROBIAL_OBSERVATIONS.md.

The open CC-BY-4.0 Zenodo record 13981041 supplied one 494,528-byte workbook;
publisher MD5 and local SHA256 were recorded. Collection totals are now29, with
26 holding assets,467 acquired assets and6,018,458,074 bytes. XML-only inspection
identified measured/context and computed sheets. The new current observation reader
preserves row order, invalid masks and source cells, converts day/mA to second/A,
and makes no clock alignment, current-density or independently validated H2 claim.
CORA candidate DATA2866 remains unacquired; public CC0/file previews do not qualify it.

There are83 deferred case definitions. No numerical model, new reader, case, test,
example, build or installed-package acceptance was executed in this wave. Licensed
data acquisition and raw schema inspection were performed. NumPy1.26 compatibility
was addressed in two integrations using the existing SciPy trapezoid API; this is
source review, not an executed compatibility matrix.

Family counts remain21 partial implemented +38 historical native-adapter levels
+12 implemented_unverified +1 planned =72. Code inventory71/72 is not completion;
last executed first-level evidence59/72 and1088 tests per profile belong to6eae06c.
Full programme effort estimate remains30-40%, with substantial uncertainty.
All affected shared-API regressions, original suites and installed-artifact checks
remain required on the later execution system. No scheduler job or publication occurred.

## 2026-10-28 producer, equipment, carrier and protection checkpoint

Parallel coding added a shared retained-result fingerprint layer and an original
producer-issued PV trace admission. The economics adapter now requires that
original trace before and after quantity snapshot construction. MEC uses the
same fingerprint primitives while retaining its stricter native-state lifecycle.
These checks read stored evidence and definitions; they do not replay physics
or prove hidden callback state.

Finite LOHC/ammonia conversion reuses the existing reaction and thermochemical
kernels. It distinguishes generated, consumed, stocked, fed and actually
withdrawn H2 and binds an original withdrawal packet to one explicit receiving
feed. Extent, temperature and withdrawal remain imposed operations. No catalyst,
equilibrium, separator, purity, pressure-work or industrial performance law was
added; gas-reference QM9 heat is not treated as liquid calorimetry.

The existing LH2 compressor and closed two-inventory heat-exchanger levels now
retain reviewed native-source/callable provenance, actual finite source witnesses,
owner-issued results/traces and failure prefixes. This adds no machine map,
capacity, depletion solver, material port, pressure loss or spatial exchanger.
Historical native-adapter evidence remains historical; the new boundaries are
unexecuted and do not change family counts.

The facility protection bridge binds one original registered held-out alarm row
to explicit latency/action, an accepted native command/inventory transition,
a finite interval source and the existing conditional-risk owner. Every frequency,
opening, ignition, failure probability and dependence factor remains caller
supplied. No extra reliability credit is granted for the same resolved protection
path. This is offline composition, not online control or facility qualification.

Twenty-three deferred definitions were added: one PV producer case, eight carrier
cases, eight compressor/exchanger boundary cases and six facility-protection
cases. The combined campaign is now106 definitions. None was discovered or run;
original regression/native/data/installed-artifact suites remain separately
required. Static AST/TOML/Ruff/whitespace review passed. No native import, model,
example, case, test, replay, benchmark, build, installation, scheduler submission
or scientific calculation was performed in this checkpoint.

Catalog totals remain72 families:21 partial implemented,38 historical
native-adapter levels,12 implemented_unverified and1 planned/rejected jet-fire
family. Partial code inventory remains71/72; last executed first-level evidence
remains59/72 at6eae06c and the old1088-test result does not validate current
source. Overall programme effort remains an uncertain30-40%. Data totals remain
29 collections,26 with assets,467 acquired assets and6,018,458,074 bytes.

## 2026-10-28 exact selection and finite process parallel wave

Four parallel lanes produced exact provider selection, finite fuel-cell
composition, finite source/receiver transfer and thermal-utility accounting.
Existing physics owners were composed rather than duplicated. Twenty-seven
cases take the deferred Nurion plan from106 to133. Static review only was
allowed; no runtime execution occurred. Counts, data,59/72 executed coverage
and the uncertain30-40% programme estimate are unchanged.

## 2026-10-28 adsorption, actuator, relief and continuity wave

Four disjoint lanes added finite adsorption-vessel inventory, valve stroke/map,
relief lift/leak/pickup and facility node continuity. Existing physics owners are
retained. Six, six, six and seven deferred cases respectively increase the
campaign from133 to158. Static inspection only; no runtime execution occurred.

## 2026-10-28 rotating equipment and recovery wave

Four lanes added pump operation, compressor-map admission, flowing exchanger
ports and reliquefier product/cold-budget accounting. Seven plus three groups of
six deferred cases increase the campaign from158 to183. Existing native result
owners are retained. Static inspection only; no runtime execution occurred.

## 2026-10-29 counterflow profile and campaign recovery

The Cantera opposed-flow adapter gained a read-only columnar snapshot for axial
temperature, velocity, density, all species mole/mass fractions and native heat
release. Cantera strain-rate definitions remain named separately. The exact native
solution identity now includes these profile fields. A reproducible H2/air example
and four deferred cases cover profile consistency, strain-rate reporting, bounded
measurement interpolation and pressure admission. Ruff and whitespace checks passed; no local numerical solve or
scientific test was executed.

In parallel, the clean Nurion recovery pin at `502598f` passed manifest/plan,
dependency-import and shell preflight and was submitted as `24229556[]`; collector
`24229557` was held on `afterany`. It covers199 cases and37 profiles. The collector
finished with 199 records, 0 missing, 77 pass states and 122 failure states. Missing
provider packages, incompatible Cantera and absent fixtures account for many failures,
while physical closure and numerical rejections remain visible. The new counterflow
profile increment is outside that frozen pin and awaits the next source revision.
The campaign is not counted as accepted scientific coverage until case-by-case review.

## 2026-10-29 Nurion-driven implementation corrections

Traceback review found compressor-map strict adjacent-pair zips that raised before
testing interpolation/admission, and a finite counterflow heat exchanger whose
residual scale masked the micro-watt small-UA limit. Both implementations were
corrected. Error paths now name energy closure, nonpositive cell heat flow and
temperature crossing separately. Ruff lint and whitespace checks passed; no local
model or numerical tests were run. Three compressor-map cases and the four exchanger
cases need a new pinned Nurion run, alongside the provider/environment corrections.

## KIT NH3/H2 counterflow data and reader — 2026-10-29

Acquired the public RADAR4KIT BagIt archive under its explicit CC BY 4.0 record. Its
785,920-byte package SHA-256 and all eight payload MD5 entries were checked. The five
Excel workbooks contain nine worksheets; per-workbook SHA-256 receipts, layouts and
limits are documented in the dataset ledger and schema audit. Raw source files stay in
the git-ignored data tree. Added a source-bound optional-openpyxl API for the flat
extinction-rate table, retaining its workbook hash, source row, reported mole fractions
and reported rate without reconstructing unstated burner conditions. The API is
implemented_unverified; no model comparison or local scientific test was run.

## Low-UA counterflow failure and rescaled unknowns — 2026-10-29

The focused Nurion set passed four of five checks. For UA = 1e-9 W/K, the exchanger
solver terminated on `xtol` with normalized residual 4.06e-5 against 1e-9. I changed
its nonlinear unknowns from absolute enthalpy and heat-rate values to inlet-relative
enthalpy offsets and duty-scaled heat rates. Physical domain bounds remain enforced;
closure tolerances were not relaxed. This source change is unexecuted and needs a
new source-pinned Nurion case. No local model solve was run.

## Counterflow measured-profile readers and campaign receipt fix — 2026-10-29

Extended the source-bound optional-openpyxl reader to preserve the nine measured
temperature pairs and four groups of H2/NH3/NO profiles, including multirow
conditions, source worksheet rows/columns, workbook SHA-256, explicit missing cells,
and SI coordinates. Expanded the deferred data-ingestion case to check extinction
rows, nine temperature profiles and twelve species profiles. The initial two-case
Nurion submission did not reach either check: source-manifest preflight detected the
generated `SOURCE_REVISION.txt` receipt as modified. The receipt is now excluded from
the payload manifest, since it is campaign metadata and may undergo text newline
conversion. This is infrastructure correction, not a model or data result. Ruff and
format checks pass; local science tests remain deferred.

## Optical counterflow diagnostics API — 2026-10-29

Schema inspection confirmed fifteen spatial signal columns on each of the NHX, NOX,
OHX and visible worksheets, plus three spatial band-integral channels and three
wavelength ranges. Added separate immutable optical records and readers that keep the
source intensity dimensionless and diagnostic-specific, preserve conditions, source
rows/columns, missing cells and workbook hashes, and convert only spatial millimetres
to metres. Spectra retain wavelength in nanometres; band-integral samples preserve the
source's descending axial order. The deferred ingestion case checks all six reader
families and their workbook hashes. This code was added after the active source pin;
it needs its own source-pinned Nurion ingestion run. Ruff, formatting and syntax
checks only; no reader was executed locally.

## Second focused Nurion outcome and correction — 2026-10-29

The full source and data preflight succeeded for array `24229619[]`, but both cases
failed on their declared scientific/data gates. The exchanger residual was
`0.0833333726810391`; inspection found that inlet-relative enthalpy offsets were
converted back to large absolute enthalpies before subtraction, losing precision at
the micro-watt scale. Energy equations now difference the small offsets directly.
The extinction workbook has eight numeric rows at worksheet rows 2-9, followed by
five blank rows; the prior thirteen-row expectation was incorrect and is fixed.
Neither change has run on Nurion yet. The dataset remains a transfer comparison, not
pure-hydrogen or apparatus validation.

## Workbook reader streaming adjustment — 2026-10-29

Changed profile extraction from repeated random cell requests to one `iter_rows`
pass per source profile. This avoids reparsing read-only workbook XML for each cell.
The active `3c47086` Nurion data worker predates this change; that worker's status is
tracked independently. The updated reader still preserves the same source cells,
ordering, hashes, axes and missing-value markers. Static lint/format/syntax checks
only; no local data-reader execution was used as a test.

## Single-case PBS generation — 2026-10-29

The optimized data-only verification plan exposed a scheduler portability edge: this
PBS deployment rejects array range `1-1`. The script generator now emits a regular
single job for one case and keeps PBS arrays for two or more cases; the runner receives
case index one for the regular job. The first qsub attempt was rejected by PBS before
creating a job. Static syntax and lint checks only; the generated single-job script
still requires a new source pin and remote preflight.

The 643e4a8 source and plan preflight succeeded, but its first worker exited before
case execution because the plan exported `cases()` instead of the runner's required
`CASES` tuple. The collector recorded zero outcomes and one missing case. The plan now
exports the tuple, was imported locally as metadata only, and its updated SHA-256 is
pinned in the rerun. An initial retry was rejected because PBS submission came from
the account home directory; no job was created by that attempt. The corrected command
submitted from scratch as job `24229654.pbs`, with collector `24229655.pbs`; both
completed with exit status zero. The data-ingestion case passed in 40.96 s with no
missing outcomes. It checked the 8-row extinction table, nine temperature profiles,
twelve species profiles, 60 normalized optical profiles, three band integrals and
three spectra, retaining 540 missing intensity cells. No flame solve or model-data
comparison ran, and the dataset is not a pure-H2 validation record.

## Parallel PV, surface-impact and cylinder-stress increments — 2026-10-29

Three unverified depth increments are being developed while the counterflow data case
runs separately. PV input now supports bounded piecewise-linear irradiance and cell-
temperature profiles converted to midpoint-held electrolysis stages with retained
clock, origin and source identity. Surface impact now accepts an evidence-bearing
integrated heat result over each interval before an impact, advances finite wall
temperature and checks path extrema; the adiabatic path remains explicitly evidence-
bound. Thick-cylinder materials support now returns an elastic axisymmetric Lamé
radial/hoop stress field and explicit open/closed-end axial stress plus von Mises
stress. Deferred cases cover the added behaviors. None of these increments changes
family or accepted-execution counts. Their Nurion cases are included in the next
combined source pin, not the active 643e4a8 data-only job.

Static Python/Ruff/whitespace checks passed on the assigned files. No numerical tests,
native model execution, scientific calculation, independent experiment comparison or
publication review was performed. All three remain `implemented_unverified`.

The three deferred cases are now pinned to revision `c521f57cd960b4be460c5dc1eefa5788b47d8f0d`,
source manifest `ab8883a04e1c67ab70eaf3851c622214c2f1e83105790dc18b490ebe75636f33` (731 entries),
and plan `6743678c5f2c9da1d0bddd11c00f0cded4a6b0287516e7dcc9ef0241a9193968`. A
source-only pvlib 0.16.1 payload retains its BSD license and exact Python aggregate
hash; its transfer archive SHA-256 is
`f877e99cc1200ae32406d00b5577d4a259d38db47e908198df9f8487ac27eefd`. Remote checks
verified source-manifest entries, plan, scripts, package hash and license. Array
`24229801[]` started three case elements; collector `24229802.pbs` is held. The PV
element exited during setup with PBS status 2 because its setup script looked for the
archive in the incoming root while the archive was under `upload/`; it did not enter
the case entrypoint. The archive is now copied into the expected path and the standalone
retry script passed `bash -n`. The cylinder case passed in 7.37 s with expected radial
boundary tractions, distinct open/closed axial stress and the von Mises invariant. The
impact case passed in 29.58 s with two 0.001 J inter-contact heat inputs and a global
energy residual of `-1.8783e-17 J`. These authored numerical checks do not qualify a
vessel, fatigue law, flaw or LH2 impact behavior. The first collector recorded 2 passes,
0 failures and the PV case missing. The corrected PV retry is submitted as
`24229849.pbs`, with collector `24229850.pbs`.

PV retry `24229849.pbs` passed in 38.52 s; collector `24229850.pbs` exited 0 with
three passed outcomes, zero failures and zero missing cases. The PV outcome records
bounded input interpolation, midpoint integration and finite-ledger invariants. This
does not change accepted first-level family evidence (59/72). A later pressure/time/
radius sample-series implementation has its own deferred case and a newer source pin.

## Sampled cylinder pressure series — 2026-10-29

While the PV retry was active, implementation continued independently. The elastic
cylinder API now maps an ordered sequence of caller pressure records onto requested
time/radius samples and returns read-only stress arrays. It does not interpolate
between load samples or claim continuous-time/wall-wide extrema. A second deferred
case checks pressure scaling and the array contract. This edit postdates the active
`c521f57` pin and has not been executed; include it in a later Nurion source pin.
Local static checks now pass: Ruff lint/format, Python syntax compilation and
`git diff --check`. No scientific test or local model calculation was run.

The series result now carries a required clock identity. A separate adapter maps its
ordered pressure samples and caller-owned wall-temperature samples into the existing
HELPR vessel-history records, retaining H2 property basis, phase, origin and evidence
bindings. A metadata-only case checks mapping and mismatch rejection. The plan example
registers both this bridge case and the pressure-series case. This update is beyond the
completed `c521f57` pin; both cases remain deferred until the user authorizes another
Nurion submission. Static checks pass; no local scientific execution was performed.

## Uniform-temperature cylinder thermoelastic increment — 2026-10-29

The pressure-only Lamé reference now has a separate linear-elastic extension for a
homogeneous isotropic cylinder with a uniform wall temperature and explicit free/fixed
axial expansion. Material constants and their evidence identity are caller-supplied.
The fixed-strain formulation returns the required axial support reaction with a declared
sign convention. A deferred Nurion case checks compatibility, force balance and stress
invariants. Python syntax compilation and whitespace review passed; Ruff was unavailable
in the local workspace. No scientific case or model calculation was run, and no Nurion
job was submitted.

## MEC electrode-data acquisition — 2026-10-29

The publicly available CORA DOI10.34810/data2866 bundle was acquired through the
ordinary publisher OAI and bulk ZIP endpoints. Archive integrity, all 24 extracted
entry SHA-256 values and ten publisher-preview MD5 values pass. The publisher claims
dataset-level CC0, but its exposed metadata has no file-level rights override fields;
raw files remain excluded from public distributions pending that review. ODS schema
inspection identifies electrode LSV, EIS pairs without frequency, and current-density
retention but no hydrogen output, Faradaic efficiency or microbial activity. This
adds observed data for limited electrode research, not MEC validation. The rights,
hashes and schema limitations are recorded in the dedicated research receipt.

## CORA MEC source-bound reader — 2026-10-29

A Python loader now connects the three pinned ODS workbooks to the shared
observation API. It returns the six reported LSV and six current-density series,
paired EIS coordinates, source row/column identities and original numeric
tokens, and retains an incomplete terminal measurement as a masked row with
diagnostics. Declared elapsed-time/current-density conversions use the common
unit registry. Since the EIS sheet has no frequency coordinates, no circuit fit
is exposed. A source/schema case and tamper-integrity case were added to the
deferred Nurion plan. Static review found and fixed an integrity-case assertion
mismatch by making the source-hash rejection state `SHA-256` explicitly. The
reader and cases remain unexecuted; no whole-cell model validation is inferred.
Raw files remain excluded from public distributions pending file-level rights
review.

## Radial-temperature cylinder and hydrogen fatigue source — 2026-10-29

A separate long-cylinder thermoelastic module now solves the isotropic axisymmetric
displacement BVP from a caller-supplied radial absolute-temperature profile, pressure
tractions, and explicit free/fixed axial semantics. It uses non-extrapolating PCHIP
and records solver residual/iteration metadata. A deferred reduction/traction/force
case is registered under the existing fracture-fatigue profile; the model was not
executed or submitted. Its primary-source context is recorded in
`research/radial_thermoelastic_cylinder.md`.

The data search also acquired one NREL/OEDI 4130X fatigue workbook under the public
record's CC BY 4.0 terms. Its workbook labels 45 MPa H2, while a related HyMatBase
record states 4.5 MPa for a similarly named workbook. The source file identity is not
established across those records, so quantitative use is blocked pending reconciliation.
The 58,357-byte raw workbook stays under ignored `data/raw/`; receipt and schema limits
are in `research/data/oedi-hydrogen-materials.toml`. No fit or scientific calculation
was run.
# 2026-10-29 implementation continuation

- Added a radial-temperature thick-cylinder thermoelastic solver using an isotropic
  axisymmetric boundary-value formulation. Boundary equations are normalized to
  dimensionless stress/force scales; the deferred Nurion case records both the
  adaptive residual and normalized boundary residual. No numerical solve was run here.
- Added a checksum-pinned reader for the public 4130X fatigue workbook. It exposes
  source-labeled stress-intensity/crack-growth observations and five experiment
  groups while retaining the unresolved 45 MPa versus 4.5 MPa record discrepancy.
  Quantitative validation remains explicitly inadmissible; no model fit was added.
- Added deferred provenance cases for both modules. Syntax/lint/diff checks were
  performed locally; scientific case execution remains scheduled for Nurion and
  no cluster job was submitted.
- Extended the radial thermoelastic solver with a quasi-static snapshot history
  API that reuses the same BVP for supplied pressure/temperature pairs on one clock.
  It preserves source objects and completed prefixes on solver failure; it does not
  add time integration, thermal conduction or inter-sample extrema. The existing
  deferred radial case now covers this history composition as well. Static checks
  only; the extended case remains unexecuted.

## 2026-10-29 OEDI condition reconciliation

The local OEDI workbook's exact MD5 matches the HyMatBase-linked file, while its own
condition cells and the Sandia study record support 45 MPa H2. The related HyMatBase
4.5 MPa field remains recorded as a metadata disagreement. The source-bound reader now
checks both pinned hashes, and a no-fit native HELPR rate comparison plus deferred
diagnostic case are implemented. This resolves the workbook observation pressure only;
it does not validate the model, identify material heats, or establish component life.
No model case was executed and no Nurion job was submitted.

## 2026-10-29 transient cylindrical wall heat transfer

Added `materials.radial_cylinder_heat_history`: cylindrical finite volumes with exact
logarithmic radial face resistances, temperature-dependent conductivity/heat capacity,
inner/outer adiabatic, face-temperature, inward-positive heat-flux or convection
boundaries, integrated heat/enthalpy ledgers, and immutable temperature histories. A
sample helper converts each result row, including both wall surface temperatures, to the
existing radial thermoelastic profile type. The API, assumptions and deferred thermal
case are documented and registered. Static syntax, Ruff and diff checks passed. No model
calculation or validation case ran; Nurion submission remains unauthorized. The added
solver is an unverified depth extension of materials integrity, not a new family.
Follow-up static review corrected the outer-face sign in the cell energy balance: face
boundary heat is positive into the wall, while internal radial flow is positive outward.
No numerical calculation was used to identify or check this correction; retain the
registered Nurion conservation and steady-profile case as the required verification.
The thermal API now requires a stable history ID; thermoelastic-profile IDs derive from
the parent history and sample time, and the bridge retains the supplied profile evidence.
The governing-balance manual explicitly states the separate internal-flow and boundary
heat signs. Syntax/lint/diff checks remain the only local checks.
The result now also requires a physical `clock_id`; a new `thermoelastic_history` adapter
composes one pressure snapshot per temperature sample and returns a paired thermal/stress
record. It checks exact wall geometry, clock and sample lineage, and preserves the thermal
input plus completed stress prefix when a BVP sample fails. This is sequential quasi-static
composition, not coupled thermomechanical dynamics. The extension is documented and added
to the deferred case; no numerical solve was run.
The handler also covers convection with a time-dependent film coefficient and
temperature-dependent thermal properties; its invariant list was matched against the
implemented case. The paired result carries a concrete stress-history type rather than a
generic object annotation. Static syntax/lint/diff only; calculations remain deferred.
The case invariant wording and implementation now align: it checks both boundary ledger
signs and verifies immutability across every returned thermal array in all authored
scenarios. The case source was only syntax/lint reviewed, never executed.
The radial boundary contract now also supports net radiation using an effective
irradiation temperature, emissivity-view-factor product, a SciPy Stefan-Boltzmann
constant and bracketed surface-temperature root. The deferred thermal case now checks
inner radiant heating against outer radiant cooling and the integrated wall ledger. No
model calculation was run; this level remains unverified. Method and numerical library
references are recorded in `RADIAL_HEAT_TRANSFER.md`.
RHS callback errors and output/enthalpy audit errors now raise
`RadialHeatIntegrationError` with their cause and any available SciPy solution. Its
deferred case checks invalid radiative coefficient rejection and cause preservation.
These remain authored checks only. The stress-history wrapper also validates nonblank
paired-history identities, temperature-reference consistency in constructed results and
explicit axial-restraint lineage. Its deferred thermal case checks that a native BVP failure
on the first requested sample retains the source thermal history, underlying cause and empty
completed-stress prefix. Static syntax/lint/diff only; no integration, model calculation or
cluster submission occurred.

Radial thermoelastic point and history records now validate the von Mises tensor invariant
against their returned radial, hoop and axial stresses. The deferred mechanics case attempts
to construct deliberately inconsistent point and history records and expects rejection.
This output-integrity path is authored, not executed; no numerical model calculation or
Nurion submission occurred.
Stress-result records also enforce that each retained temperature profile spans both exact
cylinder surfaces. The thermal-to-stress profile bridge now requires a nonblank evidence
identity, with rejection cases registered in the deferred plan.
`RadialHeatResult` now verifies its reported global energy residual against enthalpy change
and both cumulative boundary-heat ledgers, requires zero initial integrated heat, and scales
the integrity tolerance from changes rather than the arbitrary enthalpy datum. A modified-
residual rejection case is registered but has not been executed.
Material and thermal-boundary evidence identifiers now validate their string type before
calling string methods, so malformed API input yields a clear `ValueError` rather than an
incidental `AttributeError`. Deferred constructor-level rejection cases and API wording were
updated; numerical validation remains unexecuted.
Thermal boundary construction now also checks that `kind` is a string selector before
set membership, returning a clear `ValueError` for other types. A metadata-only rejection
invariant was added to the deferred thermal case; no model or numerical case was run.

The preferred dispersion helper is now composed with the exact model-selection registry
in a new deferred case. It asserts `hyram` for high-pressure gas and `slabx-lh2` for
liquid-hydrogen-origin releases, builds only those exact provider keys, and rejects a
cross-origin request without fallback. This checks routing contracts only; neither native
dispersion model is run by the case. Static syntax/lint review only.

The preferred-provider route now also has a direct high-pressure entry point that delegates
to the existing HyRAM adapter. A liquid-hydrogen-origin request is stopped before the gas
adapter and reports the missing explicit liquid/pool boundary rather than falling back. The
deferred routing case checks call forwarding with a sentinel, not native engine behavior.

The preferred-provider API now also delegates liquid-hydrogen-origin vapor to the existing
SLABx-LH2 adapter after constructing its explicit steady source/footprint boundary. It
rejects gas-origin input before touching that adapter. The boundary continues to reject
variable vapor intervals; this wrapper does not model liquid release, pool spreading,
evaporation, or transient SLAB sources. Native engines remain unexecuted here.

The deferred routing handler now constructs a bounded metadata stand-in and verifies the
pool factory, width context, runner arguments, premise check, retained result and mass
closure plumbing without loading a SLABx-LH2 installation. Its registry fixtures are
`implemented_unverified`; they are explicitly not marked as native-adapter checks.
This handler has not been executed.

`DispersionScenario` now copies its keyword mapping into a read-only proxy, preventing a
caller from mutating the original mapping and silently changing later dispatch. Referenced
physical objects/callbacks remain caller-owned. The no-fallback registry case now requests a
deliberately missing exact level, so it tests the missing-key branch rather than conflating
that condition with a status-gate rejection. The constructor accepts any Mapping and the
scenario's declared mapping participates in equality. A deferred case records these
contracts; static checks only.

`DispersionScenario.run()` now returns a `DispersionExecution` receipt carrying origin,
provider, source/footprint evidence IDs, adapter-reported acceptance and the raw adapter
result. Provider/configuration errors are chained through `DispersionExecutionError`
with provider identity and any failure result exposed by the underlying exception. The
functional wrappers continue returning their native-adapter result types. The deferred
sentinel case records the receipt and failure contracts but has not run.

The Nurion plan now has a metadata inventory generator. It imports only the declared
case catalogs, checks unique case IDs, declared profile-name consistency and explicit
associations for each implemented-unverified catalog family, then refreshes the current
case/profile summary. At that earlier metadata audit the count was 217 definitions, 39
declared profiles and 43 modules; the latest count follows below. These are unexecuted
plans; no scientific entrypoint, local test or Nurion job was run for that audit.

The inventory now records the concrete case identifiers for each of the 14
implemented-unverified families, including cross-family observation, thermal-target and
economics evidence. Generation checks that each listed identifier exists and belongs to
the listed environment profile, and rejects empty family/profile mappings. The generated
plan distinguishes this traceability from numerical execution or accepted evidence.
Static lint and syntax checks passed; no scientific tests or Nurion jobs were run.

The OEDI 4130X native fatigue comparison now requires a caller-supplied
`temperature_interpretation_id` because the workbook reports only `RT`, and it
retains that mapping in the comparison result. Since workbook gas purity is also
unreported, it now requires `gas_composition_interpretation_id` and preserves that
assumption/evidence in both the typed result and deferred archive; omission or an
empty declaration is rejected structurally. The comparison still accepts an
explicit native mixture state, so users can encode a sourced composition instead
of assuming pure H2. The result constructor checks H2 versus non-H2 series
compatibility against the retained environment. Failures during point evaluation
preserve the composition declaration and expose a compact source/model/completed-prefix
diagnostic mapping. Its deferred output archive now
also records the source hash/URL, series, pressure, interpreted temperature,
temperature-mapping ID, H2 fraction/fugacity, R-ratio and measured frequency next
to source row IDs and rates. This makes reconstruction visible when results are
read apart from their campaign log. It now also retains the dataset license and
publisher, workbook condition label, selected HELPR model/evidence, pinned library
revision, reviewed source-module hashes, environment evidence and native-definition
hash, plus the original workbook columns/reference and log-rate summary. The deferred
case reopens each NPZ with pickle disabled and checks provenance and row alignment.
Case-level point-count, positive-prediction and log-RMSE metrics are sourced from the
archive and checked against the in-memory comparison before being reported.
`OediFatigueComparison` now also validates each retained rate ratio, log-ratio and RMSE
against its observed and predicted vectors; log-ratios use a difference of logarithms
to avoid underflow from forming a very small quotient first.
These interface changes are unexecuted and remain implemented-unverified pending
Nurion verification.

The `OediFatigueComparisonError.diagnostic_record()` failure receipt was expanded to
include dataset license/URL/hash, workbook series columns and test conditions, native
HELPR model/evidence/arguments/source hashes, numeric gas state and evidence IDs, and
the completed source-row prediction prefix. The API manual states that no failure-
injection case currently exercises it. The record also names the failed source row,
the failure stage and exception type while retaining the original Python cause through
exception chaining; completed rows now carry original native returns, and the exception
constructor requires those rows to be the exact valid-observation prefix before the failed
row. The deferred handler checks receipt-field structure around an
already admitted owner with a synthetic exception wrapper, without injecting a failure
into HELPR. This checks serialization semantics only; failure propagation remains open.
No scientific or native run was performed.

The compiled austenitic-steel observation API now enforces structural invariants at
its public result boundaries: source-record and numeric-row order must match, block
masks/reason slots must match the declared schema, and `PairedPropertyCheck` validates
row identity, residual arithmetic, availability masks and tolerance flags. This protects
deep Python consumers that construct or retain these dataclasses directly. Static checks
only; no local scientific data replay or Nurion execution was performed.
Two deferred `fracture-fatigue` cases now cover the austenitic-steel compilation:
`austenite-observation-provenance` checks its CC-BY receipt and source records, and
`austenite-observation-contract-integrity` checks block/paired-property invariants and
malformed-binding rejection. Their external source directory must be staged by the cluster
profile through `H2_DATA_AUSTENITE_ROOT`; no data path or credentials are inferred. The
case catalog was added to the Nurion plan and inventory maps both IDs to the materials
integrity family. Metadata-only generation confirms 219 case definitions across 39
profiles and 44 modules. No scientific case, test or Nurion job was run.
The provenance case now rejects a missing staged-data path and asserts the exact DOI,
record version and CC BY receipt. The contract case also deliberately removes an
invalid-reason row and requires the block constructor to reject it; this checks the new
mask/reason shape invariant rather than only inspecting valid blocks.

`EmbrittlementCollection.from_receipt(directory, receipt)` now provides a direct Python
entry point for the pinned public compilation. It validates the expected dataset DOI,
version, rights flag, unique file names, exact code-pinned SHA-256 values and reviewed
acquired-file set before opening data. The caller still chooses and stages the external
data directory and
parses the repository receipt; this API performs no network access or path discovery.
The deferred provenance case and data-use documentation now exercise the same receipt
constructor. Static checks only; no data replay or scientific validation was run.

Review found that the first receipt API checked digest syntax and dataset metadata but
could accept a forged mapping that replaced every file digest. The collection constructor
now binds all admitted names to the exact code-pinned SHA-256 manifest as well as the DOI;
the existing deferred altered-digest case covers that gate. This is a source-custody
integrity correction; neither the external dataset nor a scientific model was replayed.

The shared `ObservationTable` boundary no longer accepts non-string row, experiment or
source identities, and it preserves typed context without converting arbitrary objects to
text. Nested list input is frozen to immutable string pairs. `Variable.basis_id` is also
type checked; these checks prevent native/deep-Python
consumers from silently binding unlike measurements under normalized-looking labels. A
deferred `observation-table-contract-integrity` case covers malformed identities/context,
quantity mismatch and array immutability. This case is metadata-registered only and has
not run; no experimental or model validation evidence changes.

Package inclusion was reviewed against `pyproject.toml` and `MANIFEST.in`: Python modules
are discovered from `src`, while the source distribution includes manuals, validation
catalogs and public TOML receipts and prunes raw data/build environments. No packaging
configuration defect was found in this pass; no build/install/replay was performed under
the Nurion-only execution policy. English and Korean project indexes now point directly
to the 4130X fatigue/HELPR and transient radial-wall heat manuals.

The OEDI-to-HELPR diagnostic result now binds its exact series to the pinned dataset,
reconciles row IDs and measured values against the retained `ObservationTable`, and checks
that the native owner parameters/environment correspond to the selected law and supplied
condition, including the selected reference pressure and fugacity basis. Its deferred case
specifies row, observation, pressure and basis tampering rejection.
This improves result integrity only; it does not establish fatigue-law accuracy or vessel
qualification and has not executed.
Caller-provided row-ID sequences are copied to immutable tuples and checked against the
admitted series; the deferred case checks both tampering rejection and post-construction
mutation isolation.

The radial thermal-to-thermoelastic composition now also cross-checks the combined
evidence identity against the stress history and each derived temperature profile. The
deferred heat-transfer case tampers with both wrapper and profile evidence to require
rejection. This closes a lineage-binding gap in the sequential Python handoff; it remains
unexecuted and does not establish coupled transient mechanics.

The 4130X `FatigueGrowthSeries` and `OediFatigueDataset` public constructors now also
check their nested source table: fixed SI schema/origin, original source IDs and ordered
workbook rows, checksum/column context, series ordering, material condition and license.
Deferred provenance handlers specify rejection of detached pressure, ordering and hash
context. The workbook loader was not run; static compilation and lint are not source or
fatigue-model validation.

The OEDI source reader and HELPR comparison are now available through one data-facing
import surface: `h2physics.data` lazily resolves the comparison function and result/error
types from their existing adapter module. The adapter remains the sole implementation,
and ordinary data-package initialization does not import the optional HELPR dependency.
This is API discoverability only; no runtime import, model execution or Nurion job was run.

The successful `OediFatigueComparison` now retains the original native scalar returns
aligned with source-row IDs and validates them against accepted SI growth rates. The
failure diagnostic receipt resolves completed and failed source rows back to their ΔK
and observed da/dN values. The deferred archive stores and checks the raw-return vector,
while the receipt schema case verifies the failed point's source values. All scientific
execution remains assigned to Nurion.

The public comparison now exposes a read-only `points` view of immutable per-row diagnostic
records (`OediFatiguePoint`) joining source identity, measured ΔK/da/dN, raw HELPR return,
accepted rate and residual ratios, plus the dataset hash/URL/license, series ID and source
columns. The deferred native comparison case checks row/source metadata alignment and
malformed-ratio rejection. This adds no equation or scientific qualification.

The Korean researcher guide now includes an end-to-end OEDI-to-HELPR diagnostic wiring
example with a separately staged source workbook, lazy data facade, selected native law,
explicit reconstructed temperature and pure-H2 assumption, native fugacity, evidence IDs
and per-row point consumption. It points to the dependency record and states that these
inputs do not constitute model validation; no execution was performed.

The OEDI Nurion validation cases now take `H2_DATA_OEDI_FATIGUE_ROOT` during metadata
collection and retain it as `source_path`; handlers fail with a staging instruction if the
workbook is absent. The validation plan and Nurion example name the same variable. This
fixes source-location wiring only; no job was submitted or executed.

The OEDI source-provenance case now cross-checks the staged workbook SHA-256, publisher
MD5, byte size, URL and license against the committed TOML receipt in addition to the
adapter's pinned checksum checks. It also gates the receipt dataset identity, acquired-file
state and rights-permitted flag, and confirms that the receipt does not label scientific
validation as complete. This is a planned custody contract only; no workbook was read
locally and no fatigue comparison or Nurion job was run.

The HE-Austenite Nurion cases now capture `H2_DATA_AUSTENITE_ROOT` at metadata collection
and pass the staged directory as `source_path`. The provenance gate reconciles every
acquired file against the complete receipt inventory, byte total, file size, pinned
SHA-256 and publisher MD5, while retaining rights-permitted and validation-unqualified
flags. This is still unexecuted custody coverage; it does not validate embrittlement
physics, and no cluster job was submitted.

Added `CoolPropMixtureProperties` as a fixed-composition HEOS adapter over `GasComposition`.
The provider validates CoolProp component names and molar masses, stores composition and
property identity, reapplies the frozen mole fractions for each flash, and exposes PT/PQ/TQ
states. Optional PH/PS/P-density calls use a caller-bounded scalar root over PT states after
single-gas, positive-cp and sampled-monotonicity checks. It does not estimate missing binary
interactions or add a transport mixing rule. The gas-composition deferred Nurion case now
checks bounded inverse round trips, energy identity and direct composition with the shared
isentropic nozzle, including returned basis, entropy and energy ledger. Its earlier
Cantera-only invariant was removed because the handler did not exercise that contract. The
change is unexecuted and makes no experimental EOS or release-data claim.

The finite adsorption-vessel `FrozenGasBinding` now cross-checks providers that expose
their composition identity, species order, mole fractions and molar masses. This lets the
CoolProp mixture provider participate in the common vessel property contract while
rejecting a separately declared, incompatible composition before free-gas inventory is
computed. Opaque generic providers still rely on an explicit caller declaration. The
gas-composition Nurion case includes positive and negative bindings; it has not run.
The adsorption endpoint also accepts the single-phase supercritical tags emitted by
high-pressure real-gas providers, while still rejecting liquid and two-phase states.
The CoolProp mixture provider locks its composition, thermodynamic basis and backend
configuration after construction so the retained fingerprint cannot silently diverge
from later state calculations. The deferred case specifies attempted reassignment rejection.
That same case now passes the checked binding into the existing finite adsorption-vessel
endpoint with its authored isotherm fixture, then checks basis retention and free/adsorbed
component closure. This is API/accounting composition only, not independent adsorption
data validation.

The CoolProp mixture inverse path reuses its five PT domain samples inside `brentq`,
returns an exact sampled target directly and retains a bounded exact-input LRU for repeated
PH/PS/P-density requests. Cache size is configurable (zero disables it), counters are
inspectable and callers can clear the cache. The deferred Nurion contract checks hits,
the configured eviction bound, reset and zero-capacity behavior. No timing benchmark was run and no speedup is
claimed.

An opt-in mixture inverse PT grid can now be prepared over caller-supplied pressure and
temperature nodes. Grid preparation checks sampled gas/supercritical phase, positive cp
and strict per-row monotonicity for enthalpy, entropy and density. At query time, log-pressure
interpolation only suggests a local temperature interval; fresh endpoint flashes at the
requested pressure must confirm a sign-changing bracket, otherwise the interval expands or
the original full-domain path is used. The grid is explicitly prepared and cleared by the
caller, and does not alter the provider composition fingerprint. The deferred Nurion case
checks PH/PS/P-density round trips through the grid. No performance timing or scientific
qualification has been performed, and no Nurion job was submitted.

The sampled values are now retained in the public immutable `MixtureInverseGrid` object,
which can be attached to another provider instance only when the exact composition
fingerprint, property basis and inverse temperature bounds match. Numeric axes and samples
are copied, checked for shape/finiteness/monotonicity and made read-only; the payload has a
stable fingerprint. The deferred gas-composition case now specifies same-provider and
cross-instance reuse plus PH/PS/P-density round trips. No scientific execution or timing
was performed locally; validation remains assigned to Nurion and no job was submitted.

The same deferred case now includes constructor-level grid invariants: read-only arrays
must not alias caller input buffers, monotonicity violations are rejected, and a grid cannot
be reused across a different property basis or inverse-temperature domain. No provider
flash or contract case was run locally.

The mixture bracket search now retains PT endpoint and root-evaluation states within each inverse call. Expanding a bracket no longer re-flashes an endpoint already sampled at the same pressure/temperature pair. This is a call-local reuse change; its wall-time effect is unmeasured and still requires Nurion comparison with the baseline inverse solver.

The deferred mixture case had mixed an H2/N2/H2O bookkeeping fixture into the advertised H2/N2 real-gas test. It now keeps that ternary composition only for component-flow bookkeeping and constructs a separate binary H2/N2 gas composition for CoolProp, nozzle and adsorption binding paths. The grid comparison uses an off-node pressure, compares PH/PS/P-density roots against the no-grid bounded path, and records preparation time, per-inverse wall time and PT flash counts over three repetitions. This corrects case definition and adds diagnostic metrics only; no scientific case was executed.

The gas-composition validation receipt now includes the exact grid/content and provider identity (grid fingerprint, composition SHA-256, property basis, CoolProp version and axes), plus maximum temperature and per-property differences against the bounded no-grid path. Its three measured runs warm both paths, alternate order, disable inverse result caching and report median time and PT flash count. It also derives a benchmark-specific preparation break-even query count when grid queries are faster, or records that no break-even exists. No speed/accuracy threshold is claimed without reviewing the Nurion outcome.

Implementation follow-up: `MixtureInverseGrid` now writes and restores compressed `.npz` archives with numeric/string data only and `allow_pickle=False` on read. Restore checks the schema, axes, monotonicity, property basis and payload fingerprint before returning the immutable grid. The gas-composition deferred case records a round-trip fingerprint and read-only-array checks. This enables cross-session reuse of a bracket hint; it does not create a qualified thermodynamic table. Static compilation and plan metadata checks only; no model case ran.

The quasi-static `RadialThermoelasticStressHistory` now exposes `require_current()` for downstream adapters. It checks captured output-array and source-object identity, then fingerprints stress/time arrays, geometry, load values, elastic declarations and nested radial-temperature data. The deferred radial thermoelastic case now specifies equal-valued output replacement rejection and nested temperature mutation rejection. This guards the host-side stress handoff toward the requested fracture API; it does not add an SIF solution or scientific validation.

Implementation continuation now binds the paired radial heat/thermoelastic result to the existing vessel pressure/temperature binding. The new typed contract requires exact retained heat, geometry and pressure-load objects, an identical clock, and full-wall radial stress support. It accepts only the declared total pressure-plus-thermal convention; a thermal-increment relabel is rejected to prevent double counting. The binding fingerprints the convention evidence against post-bind substitution. The deferred bridge case covers these interfaces and traction boundaries. The binding does not call HELPR with stress data; native thermal-stress SIF integration and its independent comparison remain open.

The radial thermoelastic stress history now preserves each sample's adaptive BVP iteration count and exposes `stress_field_at(index)`. The returned `RadialThermoelasticStressSample` combines the typed field with the exact physical time, clock and source history, and retains load/profile/material identities plus residual diagnostics. Its guard rejects replaced result arrays or altered source history. No time interpolation was added; the deferred fracture-fatigue case specifies valid/invalid index and field-link checks but remains unexecuted.

The vessel stress binding now adds `sample_at(index)`, joining the exact-time total stress field to the same original `VesselLoading`. The returned `RadialThermoelasticVesselSample` verifies source identity and equality of clock, absolute surface pressures and mapped wall temperature. It rejects replacement loading records even when their numeric values match. This prepares a precise input unit for future native stress-field integration; no SIF/HELPR call was added, and the deferred bridge case remains unexecuted.

## Finite source event-clock API — 2026-10-29

`IntervalMassSource` now exposes `rate_at()` with explicit left/right event-edge sampling and finite-window rejection, plus `integrate()` to project onto a receiver clock while merging every original discontinuity. The operation preserves the existing piecewise-constant mass representation and full inventory; it does not reconstruct sub-bin transients. Existing `rebin()` behavior remains unchanged for compatibility. This is a Python composition primitive for transient source consumers; SLABx-LH2 still accepts only a constant vapor rate in the current adapter and has not been extended here. Static compilation, targeted Ruff and whitespace checks passed. No model case, solver, test, benchmark or Nurion job was run.

The oxygen-deficiency room feed staging now calls the shared `IntervalMassSource.rate_at()` at each partition midpoint instead of maintaining a separate NumPy edge-index expression. The room already partitions at all source edges, so the common right-sided sample exactly matches each piecewise-constant stage while centralizing clock/window semantics. No room simulation or deferred case was run.

`IntervalMassSource.window()` now extracts an exact finite subwindow, carries every internal rate edge, computes interval masses from the parent source and requires an explicit termination meaning when cutting off before the parent's final edge. This supports solver partitioning without rate-jump loss or unstated tail semantics. The API manual was corrected: legacy `rebin()` may average across known changes, while `integrate()` preserves them. No source calculations or tests were run.

A metadata-only deferred `finite-source-clock-contract` case was added to the existing facility-protection campaign. Its synthetic state obeys the declared h-u=p/rho identity and is explicitly labeled interface-only. The case specifies rate left/right limits, jump-preserving projection/window, inventory preservation and rejection gates. Metadata inventory now reports 227 definitions across 40 profiles and 47 modules; no entrypoint was called. This is authored contract coverage, not runtime or physical validation.

`SourceHistory.interval_mass_source()` now bridges accepted nozzle-flow samples to the common finite-bin release API with explicit per-interval `left_hold`, `right_hold` or `trapezoid` quadrature. The caller must supply a basis-compatible representative `ThermoState` and separate quadrature/state-projection evidence IDs; the bridge does not pretend sparse samples resolve changing thermodynamic state. `IntervalMassSource` now retains the nozzle history's `pressure_equalized` and `inventory_limit` termination labels as well as window/isolation/depletion. The deferred finite-source contract covers the trapezoidal ledger, evidence requirement and source-end semantics. No model calculation or case was run.

In parallel, `FiniteFacilitySource.energy_projection()` now integrates accepted outlet enthalpy-flow samples using the existing command-aware interval quadrature and compares them per bin with the caller's fixed-state mass×enthalpy projection. Immutable receipts retain native integral metadata, source hash and residuals. It is a discrepancy diagnostic, not a forced closure or an atmospheric source-plane model. The deferred facility-source guard covers identity and residual semantics; no physical case was run.

`SourceHistory.interval_mass_projection()` now returns a `NozzleSourceProjection` receipt alongside the unchanged `interval_mass_source()` convenience API. The receipt records per-sample and interval-integrated mass flow, reservoir withdrawal energy, exit static enthalpy and kinetic power under the selected quadrature, plus separate nozzle energy and representative-state static-enthalpy residuals. `require_current()` detects loss/replacement/mutation of the retained history/source/state boundary and recorded numeric/metadata ledger. A deferred synthetic contract now covers its trapezoid values, both residuals and source-bound check. No model calculation or case was run.

`FiniteAdsorptionVessel.pressure_for_inventory()` adds a fixed-temperature, fixed-composition inverse over a user-supplied pressure bracket. The routine checks sampled species-inventory monotonicity and target range, uses a bracketed scalar root only when its sampled bracket is unique, and returns the final inventory snapshot, immutable sampled pressure/inventory curve and tolerance-bearing residual receipt. A deferred case covers round-trip pressure recovery, out-of-range targets, curve immutability and a deliberately nonmonotone synthetic isotherm. No case or physical calculation ran. Separately, `FiniteFacilitySource.ledger_history()` now exposes cumulative accepted-time mass/energy balances, transport and heat partitions and source-state projection residuals; its dedicated cumulative-ledger case is also planned only. The metadata-only deferred inventory is 230 cases / 40 profiles / 48 modules.

An exact-clock radial stress-path export was added for receiving fracture methods. `RadialThermoelasticStressHistory.stress_path_at()` samples the solved total pressure-plus-thermal stress field on a caller-supplied wall coordinate set, retaining all normal components, von Mises stress, and the exact source sample. Out-of-wall requests are rejected and outputs are immutable/fingerprinted. This is an input handoff only: no crack SIF, initiation criterion, time interpolation, or HELPR extension is implied. The deferred contract was extended; only static compilation/lint/whitespace checks are planned locally, with physical execution deferred.

The radial wall heat API now exports `BoundedRadialProperty` and `guard_radial_material_temperature_domain()`. The helper preflights caller heat-capacity/conductivity callbacks on an explicit temperature grid and returns a material with runtime range guards. The existing radial heat deferred case covers range/nonpositive rejection. This does not certify a material or sample intervals between preflight points; no physical solve ran.

The adsorption-data catalog now follows Zenodo latest record 22305898, replacing the earlier v1 seed whose COx workbook the depositor marked incorrect. The CC BY 4.0 latest archive is staged outside Git with matching publisher MD5 and recorded SHA-256; metadata, ZIP names, README and data dictionary were inspected without extraction or script execution. The data reports signed excess uptake, which is not directly interchangeable with the absolute basis required by finite-vessel inventory. Raw table schema and a supportable excess-to-absolute conversion remain pending.

The four processed isotherm CSVs are now streamed through a caller-path loader; each has 38 columns and six data rows, retained with its signed-excess basis and original field strings. The loader rejects absolute-uptake use. Raw logger/calibration tables, uncertainty interpretation and any excess-to-absolute conversion remain open. A separate transfer-line cooldown API computes a first-law duty and ideal coolant-mass lower bound from caller material/property functions. An admitted stationary HyRAM jet can now become a typed finite source over a caller-selected clock window, with rate and enthalpy residuals retained; native source-mass failures are not corrected. The radial thermoelastic stress path provides exact-time total stress components for receiving fracture software without an invented SIF. Inventory is 233 deferred cases / 42 profiles / 51 modules; no physical model or Nurion job ran in this slice.

The line-cooldown interface now binds to the common `PropertyProvider` contract through `IsobaricEnthalpyPath`. The path fixes pressure, property basis, caller phase domain and evidence identity, so it can serve both as the contained-fluid enthalpy callback and as a checked coolant-state path. `estimate_line_cooldown_with_provider()` retains the exact EOS inlet/outlet states with the energy receipt and rechecks them before returning mass/duty properties. The deferred cooldown metadata covers pressure, basis, phase and endpoint identity gates. Static compilation, Ruff and scoped whitespace checks passed; no property calculation or cooldown case ran.

The line-cooldown receipt now retains both coolant endpoint enthalpies and re-evaluates its source segments in `LineCooldownEstimate.require_current()`. Changed wall heat-capacity or contained-fluid enthalpy outputs are rejected before the energy/mass ledger is consumed; the property-backed wrapper includes this source check with its endpoint re-query. The deferred contract names callback mutation coverage. This is an implementation change only; no model or deferred case was executed.

Native dynamic line runs now connect to cooldown accounting through `audit_dynamic_line_cooldown()`. It uses the accepted native per-node transport/ambient ledgers and inventory change, checks caller gross coolant mass integration against the same clock/window/basis, and reports required mass plus independent residuals. A deferred synthetic ledger contract is authored; no line trajectory or mass quadrature was executed in this change.

The audit receipt now also retains its full start/end window and native boundary mass/energy, verifies both native inventory residuals against the original inventories, and requires explicit caller premises for forward-only flow and coolant-only boundary energy transport. A signed integrated total cannot prove those premises; they remain caller-owned admission evidence. No new scientific evidence was generated.

Forward-flow admission no longer rests on a Boolean assertion: `integrate_unidirectional_equipment_rate()` shares the accepted-sample quadrature path, retains all sampled signed rates, reproduces the integral from those samples and rejects any observed negative rate. Flow reversal between samples remains a step-refinement question. Coolant-only boundary transport is still declared by the caller because the native aggregate node ledger does not assign energy to one named stream.

Added `EquipmentIntegralRefinement` and `compare_unidirectional_equipment_integrals()` for same-window grids. They require one shared caller trajectory ID, nested accepted time points and a normalized tolerance, retain the signed/absolute/normalized integral change and interval refinement ratio, and record the threshold decision for attachment to a dynamic cooldown audit. This is not a truncation-error estimate; numeric behavior awaits execution of the deferred case and native trajectories.

Added `require_current()` fingerprints across the signed sample integral, refinement comparison and dynamic line audit. The guard chain rechecks retained rate/time rows, integral metadata, comparison outputs and audit ledgers, so an edited child sample invalidates parent receipts. The deferred mutation chain is authored but not run.

The unidirectional integral now retains its exact originating `DynamicEquipmentRun`, ordered equipment snapshots and rate reader. `require_current()` replays those sample reads and compares object identity and values, while the cooldown audit rejects mass receipts from a different run. The deferred contract now checks foreign-run rejection and snapshot replacement invalidation. This is lineage hardening only; the case and native trajectory remain unexecuted.

The cumulative finite-facility ledger history now carries its originating source/run binding and fingerprints every time, mass, energy and residual array using the shared stable array snapshot contract. Its `require_current()` revalidates that binding and detects array replacement/mutation; the deferred facility source-energy contract includes detached-history and mutation checks. These are receipt-integrity changes, not model validation, and the scientific case remains unexecuted.

The admitted steady HyRAM H2 source can now use the shared `GasComposition` component algebra for an explicit downstream mixture mass basis. The API allocates caller-declared species flows so the H2 component exactly matches HyRAM, fingerprints the existing source receipt, and returns immutable rates. It intentionally does not infer air entrainment from centerline data or fabricate a mixed-gas EOS state. The synthetic validation contract is authored but unexecuted.

The shared finite utility-cost receipt now fingerprints the exact original tariff objects and all quote fields, physical amounts, cost lines and projection identity. `require_current()` checks this fingerprint before replaying tariff validation and the physical source audit; the shared economics contract covers post-pricing quote mutation. This applies to MEC and PV projections alike, remains unexecuted scientifically, and adds no economics law.

The shared `IntervalMassSource` now retains a content/identity fingerprint over location, state, origin, evidence, termination and exact clock/mass arrays. Its mass, rate, window, integration and rebin APIs check that receipt automatically, while source-hash consumers and preferred SLAB/HyRAM adapters validate it before binding. A metadata-only contract covers writable-array, nested ThermoState and provenance mutation. This closes stale-input acceptance across finite-source handoffs; it does not qualify the physical source itself.

The geological adsorption measurements now adapt to the common `AdsorptionProvider` as a single-temperature, single-component signed surface-excess curve with bounded log-pressure interpolation. The source temperature must be selected explicitly; pressure extrapolation and mixtures are refused, and the immutable provider fingerprints the original dataset and curve. `FiniteAdsorptionVessel` intentionally rejects its `surface_excess` basis. The existing deferred data case was extended for provider interpolation/domain/provenance and vessel rejection. No case or material model was executed.

The geological surface-excess provider now carries immutable `AdsorptionSourceObservation` Python objects through `AdsorptionState.source_observations`. Each per-site receipt has source-row identity, log-pressure weight, and reported standard uncertainty/LOD/LLOQ with explicit mol/kg fields; the numerical values equal mmol/g in this basis. The state enforces receipt type, immutability, valid values and unit-sum source weights. Missing source statistics remain `None`; no combined uncertainty is inferred. The deferred case now records original-value preservation and negative receipt gates. No scientific validation ran.

Finite-vessel source uncertainty now requires a qualified record for every
species/site pair before constructing its component uncertainty vector. This closes
a partial-coverage path that previously left absent components at initialized zero.
The existing vessel uncertainty-lineage case includes a two-species H2-only receipt
and expects rejection; this is a deferred contract, not a scientific test result.

Finite-vessel source uncertainty now requires a qualified record for every
species/site pair before constructing its component uncertainty vector. This closes
a partial-coverage path that previously left absent components at initialized zero.
The existing vessel uncertainty-lineage case includes a two-species H2-only receipt
and expects rejection; this is a deferred contract, not a scientific test result.

The 2026-10-29 coding continuation adds the initial equilibrium-flash API before
isolated droplet transport, aligns the catalog/manual scope, and exposes the native
CoolProp mixture PT/PQ/TQ calls directly. Mixture saturation quality is explicitly
kept on a mole basis. Unsupported PU and density-U mixture flashes now validate their
input domain before refusing the unsupported input pair; no arbitrary root search or
phase label is invented. Static compilation and whitespace checks passed; no model
calculation or scientific test was executed.

## 2026-10-29 parallel host composition

Implemented original Python compositions for explicit parcel populations, unit-count
population-to-impact admission, deposited-stock native pool and SLAB slices,
finite facility source/provider admission, operational dependency graphs,
thermal/material fuel-cell admission and closed-reactant schedules, prescribed
incident-flux radial wall response, native adsorption bed inventory audit and
explicit dependent-input transforms with scenario output readers. All retain the
existing physical owners; their scope and unresolved coupling are recorded in
SCENARIO_COMPOSITION.md, JOINT_UNCERTAINTY.md and IMPLEMENTATION_BACKLOG.md.
New deferred cases are staged, not executed. Local work performed only syntax and
whitespace checks. No native model, numerical case, scientific test, benchmark or
Nurion command ran during this continuation. Full-programme completion is not claimed.

## Continued substantive model levels — 2026-10-29

Added finite_liquid_launch for original native outlet bins with explicit per-bin
liquid-state/enthalpy projection and launch-time approximation. Added staggered
thermal/reactant electrochemical operation using the original solvers with explicit
capacity scope, projection evidence and heat mismatch budgets. Both have deferred
cases and remain unexecuted scientifically. Case metadata refresh reports 252 cases,
42 profiles and 68 modules. Static compilation and whitespace checks passed.
Transient flowing heat-exchanger implementation remains a live parallel task; do not
label the existing steady/post-run port admission as a transient flowing solver.
The full objective remains active and incomplete, with numerical execution deferred.

## Native transient flowing exchanger continuation — 2026-10-29

Added native stage-flow two-side fluid/wall hold-up and explicit per-side transport
ledgers, retaining existing native equations and native integrator. Catalog purpose
now includes this implemented_unverified level; historical closed-side evidence is
not transferred. Internal-transfer heat observation does not generate utility credit.
Read NATIVE_HEAT_EXCHANGER.md. Metadata-only refresh now reports 253 cases / 42
profiles / 69 modules. No scientific calculation, validation or local test ran.
Parallel work continues on known boundary discontinuity admission and native mixture
phase partition, while the full goal remains active and incomplete.

## Finite coolant and native mixture PH continuation — 2026-10-29

The shared electrochemical thermal RHS now optionally integrates finite liquid
coolant enthalpy, retaining opposite stack/coolant heat, imposed-pressure property
domain and independent combined energy residual. Existing prescribed-coolant route
keeps its original API. Read FINITE_ELECTROCHEMICAL_COOLANT.md. Native mixture PH
branch inversion and finite equilibrium separation retain same-flash phase properties,
component amounts, root evaluations, upstream reconstruction and failure context.
These are implemented_unverified model levels, not new executed evidence. Metadata
refresh reports 257 cases / 42 profiles / 73 modules. No scientific model or case ran.

## Bounded native inventory property integration — 2026-10-29

BoundedMixtureInventoryProperties now exposes original frozen composition metadata
and routes rho/U through the explicit bounded native inverse. Authored cases include
actual FrozenGasBinding and LH2DT low-level property seams; their profile requires
the reviewed LH2DT dependency. No native calculation or test ran locally. Deferred
metadata is 261 cases / 42 profiles / 77 modules. The original objective remains
active; implementations and authored definitions do not establish qualification.

## Native compartment/source audit — 2026-10-29

Separated fuel-cell compartment traces now bind original configuration, independent
native reactor identities and accepted species/mass/energy ledger arrays through
require_current. Reaction extent comparisons retain both independent kg/mol budgets,
including native-vs-electrical differences. The combined energy diagnostic continues
to expose unresolved caloric coupling rather than inventing balancing heat.
Pure-fluid phase-selective separator implementation is ongoing over the existing
native StratifiedTank. Request032 records the distinct missing evolving-mixture V/U
flash and withdrawal API; a gas-only inverse cannot implement that phase level.
Static compilation and whitespace checks passed; no science or case execution ran.

## Native phase-selective operation and explicit recipes — 2026-10-29

The pure-fluid finite separator now uses actual native StratifiedTank phase ports,
phase floors, provenance and independent stored-energy/mass audits. Read
FINITE_SEPARATOR.md and Request032 for the separate unsupported mixture level.
examples/native_model_composition.py supplies lazy native-owner recipes for coolant,
separated gas volumes and phase-selective operation without numeric defaults or
model calls at import. Metadata-only inventory is 263 cases / 42 profiles / 79 modules.
No scientific model or validation case ran; the full goal remains active.

## Required host coding audit follow-up — 2026-10-29

The source audit mapped all72 catalog first levels to actual definitions and found
an exhaustive liquid accident terminal mass partition missing from the existing
chain. liquid_accident_ledger.py now implements that composition with original
parents, intermediate vs terminal inventories and explicit stage/final kg budgets.
CODING_COMPLETION_AUDIT.md records its unexecuted status and remaining delivery
requirements. PUBLIC_API_INDEX.md is generated from AST-only inventory and links
184 modules / 1148 definitions at this checkpoint; it does not prove runtime imports.
Catalog descriptions were reconciled without changing implementation/verification
counts. Metadata-only case inventory is264 cases /42 profiles /80 modules. No
scientific execution or local test ran. The full goal remains active and incomplete.

## Static source delivery corrections — 2026-10-29

AST-only API and relative-import reports now cover184 modules /1148 public
definitions and1113 statically bound relative imported symbols, with zero missing
or unresolved bindings under their stated limits. Ruff undefined-name/syntax checks
found a missing local NumPy import in the authored geological adsorption case;
it was corrected. All selected static checks then passed. The chemistry extra now
selects Cantera3.2.x consistent with the finite-volume adapter. Public docs use
generic cluster execution identity placeholders. No scientific imports/tests,
package installation, native run or built-distribution audit was performed.

## Static research continuation requirements — 2026-10-29

Added static cluster-profile requirements and local-document-link generators.
Current AST reports185 modules /1150 public definitions and1115 relative imported
symbols statically bound, zero missing/unresolved under documented limits. Local
Markdown audit reports2829 existing paths across277 files. The accident energy
source diagnostic explicitly leaves missing native substrate/pool/mechanical terms
unresolved; Request033 names required outputs. All scientific execution remains
deferred. Generated reports do not establish runtime compatibility, physical
validation, built-distribution contents or rights clearance. Goal remains active.

## Fresh development artifact content evidence — 2026-10-29

Isolated setuptools84.2.1 built source and wheel in a new ignored output directory.
The initial content gate flagged a generic Windows user-folder example, corrected
to a neutral campaign path. Fresh b artifacts passed scripts/release_audit.py.
Stdlib archive reads confirmed185 package Python files match current source in both
archives,0 mismatches. research/release_audit.md records exact hashes and scope.
No project import, installation, native solver, scientific case or test ran. This
is development packaging evidence only; the original goal remains incomplete and
active, with Nurion/native replay and source/data qualification still required.

## Counterflow dataset metadata reconciliation — 2026-10-29

The official KITopen record was rechecked for DOI10.35097/bnpe6n1ppv92yjw4 and its
explicit CC BY4.0 declaration. The already acquired BagIt descriptive XML member
was hashed without workbook analysis:2414af23c32dc4af163f30440ff52d8e3c393652d6af209af07d8a5557f843fe.
The source manifest now records title, canonical license URL, XML snapshot member/
format/hash and an explicit host research-use decision retaining attribution.
Raw redistribution remains unadmitted and file-level/third-party review remains
visible. DATA_MANIFEST_AUDIT.md now reports no missing checked metadata for that
receipt. No model, numerical case, new raw download or scientific test ran.

## Reproducible data metadata gates — 2026-10-29

The metadata audit CLI now supports --output, strict --check-metadata and explicit
--check-acquired. The latter passed for recorded acquired/historical-acquired
receipts after the KIT counterflow reconciliation. The all-candidate mode correctly
reports unresolved h2-diaphragm-field withheld metadata (no license URL/snapshot/
attribution recorded); no grant was invented to silence the finding. Rights review
flags and raw redistribution remain independent. Only TOML metadata/static source
checks ran; no scientific execution occurred.

## Independent static physics review — 2026-10-29

Cross-author review corrected: transient RK jumps now require interval-specific
endpoint commands rather than mere step alignment; separator phase/domain/floors
are admitted before simulation and boolean domain rejection is honored; coolant
final properties/configuration, numerical result shape/time and provider identity
are guarded; compartment complete-window integrals use last-first; joint propagation
keeps transformed inputs even on output validation failure. Mixture branch sorting
uses requested root coordinates instead of rounded EOS output pressure/quality.
Static compilation and selected Ruff checks passed. No science/model/test ran.
Earlier artifact byte coherence is a recorded checkpoint only and does not cover
these subsequent source changes; a new pinned build is required for publication.

## Scalar admission and unresolved capability receipts — 2026-10-29

Separator phase predicates now admit only validation-by-None or scalar Python/NumPy
booleans; false values reject the native state. The deferred negative case retains
the adapter's FiniteSeparatorError and checks its original ValueError cause.
Transient exchanger deferred cases cover both aligned and unaligned declared jumps
without interval-specific endpoint commands. Compartment receipt pressure-feedback
and combined-energy flags are non-constructor false fields because this level does
not resolve those capabilities. Deferred declarations cover the receipt contract.
No scientific test or native calculation ran locally. Static source checks only.

## Integrated parallel source closure review — 2026-10-29

Independent source review added finite admission to mixture phase/component energy
and preserves failed inverse/amounts/residual evidence. Both prescribed and finite
coolant RHS paths now guard callback-driven owner/configuration mutation. Scenario
receipt-creation failures retain the original successful operation result and stage;
joint transforms reject non-real/nonscalar values and normalize their declared bounds.
Parcel/population and native pool fingerprints protect full retained content; original
flight clocks and independent liquid-plus-evaporated mass closure are checked. Three
authored hydrogen saturation fixtures use 0.8 MPa rather than supercritical 2 MPa.
Existing deferred cases and manuals were amended. These are implementation fixes,
not executed scientific evidence. Within the documented admitted host levels these
parallel reviews found no further required code stub. Receiving-engine requests,
unexecuted verification and independent physical/data qualification remain open.

## Fresh c development package and automated source coherence — 2026-10-29

The release-content script now independently compares every package Python file
in each archive to current working-source bytes (including untracked sources),
rejects missing/extra/different files and duplicate archive member names. Isolated
source/wheel builds completed in artifacts/release_source_20261029c. Actual archive
inspection passed:185 package Python files in each,0 missing/extra/different. Exact
hashes are in research/release_audit.md. Documentation readiness findings were
reconciled to distinguish corrected source metadata from still-pending native
installation. No package import/install, scientific model or test ran. Repository
follow-up documentation may postdate the build; package bytes were checked directly.
The original goal remains active; this is development packaging evidence only.

## Alternate data receipt forms reconciled — 2026-10-29

The metadata audit previously displayed zero acquired file receipts for the KIT
counterflow dataset although its separate BagIt archive receipt and five workbook
member receipts were recorded. Reports now distinguish direct file receipts,
archive-only receipts and workbook members without summing members as additional
downloads. Workbook name/byte/hash metadata are checked; archive-level publisher
checksum status is surfaced independently. The acquired-only metadata gate passed.
No raw values, model, scientific test, download or third-party rights clearance
was performed.28 acquired datasets and1 historical acquired dataset remain recorded;
withheld/failed records and unresolved file-level rights remain visible.

## Original-scope catalytic and source-handoff implementation — 2026-10-29

Broader PLAN-to-source review identified genuine gaps outside the earlier admitted-
level no-stub finding. New cantera_surface_reactor.py uses actual native gas/ideal-
surface kinetics and ReactorNet for closed rigid prescribed-temperature gas and
adsorbate stock. It preserves source/phase/domain and native terminal/result
freshness, independently audits elements/sites, and reports endpoint thermostat
demand without claiming predictive catalyst heat or a flowing industrial reformer.
Deposited-pool fire seeds now retain exact endpoint stock/state/geometry/time and
original-parent freshness under explicit ignition transition evidence and budgets.
Jet line fields now protect original native/field content and hand off point flux
inside explicit original steady support; lumped targets check source freshness.
Quadrature refinement subdivides the same original native polyline rather than
manufacturing an accepted native flame. Qualified table configuration is sealed,
and a genuine table EOS/domain/freshness case is registered for Nurion.
Current metadata:266 deferred cases/42 profiles/82 modules; AST186 package modules,
1155 public definitions,1124 bound relative imports/0 missing or unresolved. Static
syntax/selected lint checks passed; no scientific execution occurred. The c build
report is an earlier185-module checkpoint and does not cover this new wave.
Historical59/72 executable evidence and original programme completion are unchanged.

## Cross-author surface and thermal handoff corrections — 2026-10-29

Native surface initialization now retains progressively created original objects
on failure; accepted surface and gas temperatures must both meet the isothermal
premise. Pool/fire admission rejects nonfinite native endpoint T/rho and mismatched
ambient/saturation pressure, and seals seed provenance identities. Jet transmission
callbacks cannot change retained source/policy/receiver inputs; receiver/flame
frames must match exactly. The deferred example uses the source's actual frame and
namespace-qualified source factory. Thermal target receipts now guard original
source/history/configuration, native arrays and energy ledgers with require_current,
including during RHS/return; the existing pulse declaration includes mutation refusal.
Cross-author native-signature/source review and local static checks only; no models,
tests or scientific cases were executed. Current development artifacts remain older
checkpoints, and none of these source edits supplies new validated physical evidence.

## Raw geological calibration customization — 2026-10-29

Read-only standard-library inspection verified the acquired pinned archive and14
raw CSV member headers/widths/hashes/blank counts; the reproducible structural report
is research/geological_raw_schema.md. No deposited code, fit, EOS or logger mean ran.
The new data.geological_calibration API preserves18 H2 equilibrium rows,33 He
calibration rows and4 sample configurations as immutable source-line/string and SI
quantity receipts. Initial/equilibrium/calibration pressure roles are fixed to source
semantics; absolute/gauge basis is unqualified. Missing He difference and missing
COx mass/reference/sample volumes remain None with reasons. No unrelated geometry
or inferred logger observation fills them. Source DOI/license/hash are retained;
literature-derived comparison data are not admitted for model use or redistribution.
The new deferred case uses the existing separately staged cluster raw-data root.
Metadata inventory267cases/42profiles/83modules; AST187modules/1159public definitions,
1130bound relative imports/0missing/unresolved; local document paths0missing.
Acquired metadata checks and static syntax/selected lint passed. No loader scientific
case, model or test ran locally. Whole-source rights/data qualification remain open.

## Raw adsorption case planning and scope reconciliation — 2026-10-29

Nurion metadata now includes the raw calibration case through the existing
`adsorption-data` profile and `H2_CLUSTER_DATA_RAW_ROOT`; no new setup or numerical
runtime was inferred. The source loader binds the exact acquired archive digest and
preserves fixed initial/equilibrium/calibration column roles, reported (unqualified)
pressure basis and explicit reasons for missing He/COx fields. Qualification and
backlog tables were reconciled: no baseline fit, logger average, pressure-reference
assumption, or excess-to-absolute correction is admitted. Local work this turn was
source/document reconciliation only. No scientific case or test ran.

### Continuation source/package audit

Whole-package Ruff and compileall passed for 188 Python modules. The Markdown local
link audit checked 2,888 links across 281 files with zero missing; the AST relative
import audit found 1,141 bound imports and zero missing/unresolved across 188 modules.
The fresh development sdist/wheel audit matched all 188 package Python members to
working source, with no extra/missing/different entries. Raw-source exclusion checks
passed. This does not install/import native optional dependencies, execute deferred
cases, validate physics, or clear final public distribution rights.

### Follow-up contract correction

Provider-propagated adsorption uncertainty is now defined as an aggregate species
than direct sigma summation. Pool energy accounting distinguishes a prescribed
external reservoir from finite-wall input and requires caller-declared mass and
energy residual budgets. Whole-package lint, syntax compilation and document audits
were repeated. These edits require a fresh build/content audit before release claims.

## Typed cross-module bridges — 2026-10-29

Added `FuelCellOperatingState` and activity correction on the shared reaction-energy
law; a native mixture-phase selective-withdrawal accounting primitive with phase-stock
composition checks; adsorption uncertainty semantics/source checksum retention through
absolute-basis vessel snapshots; exact-clock total-stress sample evaluation callback
receipt; and strict native cumulative pool-energy receipt with finite-wall accounting.
Updated API/model manuals, backlog, Nurion-deferred interface contracts and handoff.
Ruff, compileall, document links and whitespace checks were static only; no tests,
physical cases or Nurion jobs ran. Native receiver contracts and uncertainty/material
qualification remain open. New source supersedes the prior build audit hashes until
a fresh archive build and content audit is performed.

### 2026-10-29 mixture TQ partition follow-up

Added `CoolPropMixtureProperties.phase_partition_tq()` using the native TQ flash and
the same locked phase-composition/mass-quality accounting as PQ. The deferred
`mixture_phase_partition` contract now compares PQ and TQ partition identities at a
shared native state. Full Ruff and compileall passed; the development sdist/wheel
content audit passed for 189 package Python files. No physical validation was run.

### 2026-10-29 common-clock receipts and source-digest contract

Added an operational assembly receipt for existing LH2DT supply, accepted dynamic
run, optional actuator/relief/protection results, and an H2 molar handoff receipt
from admitted PV electrolysis output to finite fuel-cell initial inventory. Both
preserve existing solver ownership and require caller evidence for cross-owner
links; neither is a coupled physical model. The oxygen-deficiency source digest was
already filtering constructor fields by `init`; recorded that static correction and
added a deferred finite-source digest contract. No scientific case or Nurion job ran.
A PV electrolysis to finite fuel-cell H2 inventory handoff contract now carries an
actual producer-issued PV trace into a consumer-issued finite inventory fixture;
producer/consumer hydrogen aliases are checked for formula, charge and molar-mass
basis before comparing moles. The deferred case is registered but unexecuted.
`FiniteAdsorptionVessel.snapshot()` now requires uncertainty source coverage for
every adsorbing site and species; its deferred contract covers partial-coverage
rejection. No physical calculations or Nurion jobs were run for these increments.

Whole source/case Ruff and compileall passed; Markdown audit checked 2,889 local
paths with zero missing, and the relative-import audit found 1,160 bound imports
across 191 modules with zero unresolved entries. The updated development archive
audit is maintained in `research/release_audit.md`.

## 2026-10-30 Request031 receipt hardening

The post-run fuel-cell pressure/activity receipt now retains all three reference
pressures and independently reconstructs its operating state, ideal-activity
correction and shared-stack operating result from the exact native output sample
and explicit current/temperature inputs. Both direct construction and
`require_current()` reject altered or internally inconsistent retained values;
the deferred compartment case records negative contracts for forged sample time,
reference pressure, activities, correction, current and stack result. This remains
a post-run host handoff with no simultaneous pressure feedback or energy closure.
No local tests, calculations, lint or compile action, or Nurion job was run.

## 2026-10-30 immutable array boundary continuation

Added `core.immutable_array()` as a bytes-backed NumPy snapshot so a retained
fixed-width numeric or boolean array cannot regain write access through
`setflags(write=True)`. Object, text, datetime and structured dtypes are rejected;
scalar array shape is retained. Applied the helper to shared observation
and time-series objects, selected data/fitting outputs, uncertainty, mixture,
reaction, adsorption, source and thermochemical values, plus retained arrays in
adapter, materials, storage and combustion APIs. A deferred observation contract
records the re-enable, scalar-shape and object-dtype behaviors. Static source search
shows no remaining reversible `setflags(write=False)` snapshots outside the helper
documentation. Source-only AST inventories now report 198 modules, 1,210 public
definitions, and 1,294 bound relative imports with no missing/unresolved targets.
The contract was authored but not run; no scientific case, calculation or Nurion
job was executed. This protects API receipt integrity and does not qualify the
underlying physical models.

The HyRAM source-boundary continuation now reconstructs the Gaussian H2 section
flux when a `HyRAMJetRun` receipt is constructed. It rejects a direct receipt if
its native upstream rate, entry flux, transport drift, maximum flux residual,
centreline or accepted flag disagrees with the retained native fields. The existing
synthetic deferred case records forged-summary and forged-acceptance rejection; it
was not executed. This guards host-side receipt integrity and does not address the
native ~23.31% plug-to-Gaussian source mismatch or qualify dispersion accuracy.

The 2026-10-30 thermal-failure continuation now preserves the receiving SIF
callback's finite signed outputs, including zero and compressive negative values;
the exact-sample maximum is computed on the declared signed values without an
absolute-value transform. Its deferred contract covers sign/zero retention. This
does not add an SIF law, flaw model, initiation interpolation or HELPR total-field
consumer, and the contract remains unexecuted.

The 2026-10-30 mixture-separation continuation adds phase-resolved volume and
internal-energy properties to a fixed native equilibrium packet, using retained
phase masses, density and enthalpy with the shared pressure. Empty endpoint phases
contribute zero; occupied phases with missing properties reject. The deferred
mixture phase contract records these properties but remains unexecuted. Changing
inventory flashes, phase events and finite-vessel integration remain Request032
receiving work.

A host-side `MixtureInventoryStateAdmission` now checks an existing native phase
packet against target species moles, fixed volume and total internal energy, with
explicit absolute tolerances and a sealed provider/branch/result binding. This lets
a future receiving flash expose a direct Python result to host workflows while
keeping the flash and time integration under native ownership. A deferred synthetic
contract covers residual admission, source evidence and forged summaries. It has
not been executed; this change adds no phase-equilibrium solver.

The metadata plan now includes the existing gas-composition algebra, bounded
mixture-inventory facade and phase-partition contracts under a curated
`gas-composition` profile with thermo and LH2DT prerequisites. The plan now contains
245 deferred cases in 44 profiles and 50 case modules, with 53 curated
profile/module associations; none of these new entries has been executed.

The 2026-10-30 turbine-map continuation seals admitted metadata and grid values.
Interpolation and map-bound result construction reject post-admission edits, and
repeated initialization cannot refresh a stale seal. Deferred mutation guards were
added to the map integrity case; they remain unexecuted and add no cycle physics or
machine qualification.

The finite hydride trace constructor now verifies sample-clock identity, gas/reference
property compatibility, invariant free volume and inferred solid capacity, finite
native states, and exact reconstruction of energy/mass transfer residuals. Added a
CoolProp-enabled `finite-hydride` cluster profile and a deferred direct-constructor
contract for forged energy, time and uptake fields. Source/profile metadata now
contains 222 cases across 40 profiles/41 modules; it is not execution evidence.

Current static refresh: 222 deferred cases across 40 profiles/41 modules; 40 curated
cluster profiles and 44 module associations; 1,183 public definitions; 1,183 bound
relative imports with zero unresolved across 192 modules; and 2,945 local Markdown
links with zero missing across 283 documents. Whole-source/case Ruff and compileall
pass. All deferred contracts remain unexecuted. No scientific model, dataset download,
or Nurion job was run.

Further direct-constructor closure: `JetRadiationField` now requires a matching
accepted HyRAM flame/frame and reconstructs incident flux, segment weighting,
transmissivity summaries and line power before sealing. The CoolProp table report
also rejects negative or boolean seeds. Deferred contracts record forged radiation
summaries and invalid seeds. Neither contract, radiative field, nor table calculation
was executed.

Follow-up on the finite-hydride source adapter hardens direct `HydrideGasThermodynamics`
construction: the property basis and source identity must be typed, native objects
are captured as a tuple, and each advertised optional callback must be callable.
`BoundHydrogenEnergyReference` requires a native `ThermoState` and text evidence ID.
The existing deferred contract now includes malformed-provider/reference cases. No
contract, CoolProp calculation or Nurion job was run.

`FiniteHydrideTrace` direct construction now checks one ordered sample axis, finite
aligned cumulative ledgers, retained native gas/reference bases, constant implied
free volume and solid capacity, and reconstruction of mass/energy residuals from
snapshots and integrated terms. This blocks a fabricated conservation summary
from sealing itself as the trace baseline. Ruff, py_compile and diff checks passed;
no physical run or Nurion validation was executed.

The single-batch PV-to-fuel-cell inventory receipt now seals its original producer
and consumer object identities, source/sink IDs, transfer/conditioning evidence,
loss, tolerance and derived molar ledger. `require_current()` rejects a receipt whose
evidence label is changed after admission. The deferred producer-consumer bridge
case now covers mutation/rejection/restoration. Static checks only; no electrochemical
case, fit, calculation or Nurion job was run. Request031's simultaneous native
pressure/activity/thermal coupling remains outstanding.

Public attachment downloads now share the credential-free HTTPS opener used for
repository metadata, so redirects to HTTP or credential-bearing destinations are
blocked before following. The deferred mocked contract asserts this path without
transferring data. The directly constructed facility dispersion handoff now
requires evidence and its complete admission path before returning. Bed inventory
receipts reconstruct component balances and energy-reference identity before
sealing, while SLAB pool boundaries are rechecked after runner callbacks. These
contracts remain unexecuted and do not establish physical validity or data rights.

The same continued safety-adapter sweep closes a callback mutation window in
`SLABLH2Run`: after native runner and premise callbacks, the finite vapor-pool
boundary is checked again before the result can be admitted. This prevents edited
source values from becoming the receipt baseline. A deferred contract was added;
the native runner and physical outputs remain unexecuted.

An additional direct-constructor audit found that `BedInventoryAudit` could seal
caller-supplied component totals without first rebuilding them from its absolute
native snapshot. The constructor now validates snapshot axes/nonnegative stocks,
positive geometry, native energy reference and exact gas/adsorbed/total/residual
vectors before capturing the seal. Deferred adversarial coverage rejects forged
totals and a changed energy basis. Static checks only; no bed case or scientific
calculation was run.

### 2026-10-29 electrochemical energy-property correction

Corrected the location of `reversible_voltage_v` and `thermoneutral_voltage_v`:
they belong to `ReactionEnergy`, whose Gibbs/enthalpy fields supply the calculation
and whose reversible-potential property is read by `HydrogenStack.evaluate()`. They
had been placed on `FuelCellOperatingState`, which has neither energy field. Added a
deferred synthetic contract for ideal activity correction through the shared stack
and registered it in the Nurion metadata collector. No stack calculation or case
was run. Metadata inventory now contains 269 cases across 42 profiles/84 modules.

### 2026-10-29 relief/cooldown port qualification

Added `ReliefCooldownPort`, requiring explicit port identity, native `PropertyBasis`,
phase, absolute-pressure convention and evidence ID on both the tank-relief outlet
and cooldown-line inlet. The receipt checks matching phase/reference/spin basis and
consistency with the relief provider and cooldown inventory bases, then repeats that
admission on freshness checks. One receipt represents one phase; phase changes must
be segmented and native event/coupled-solver support remains receiving work. The
deferred interface case includes phase-mismatch rejection. No scientific case was
executed. Whole-source Ruff and compileall passed; the AST import audit now reports
1,172 bound imports with zero missing/unresolved across 192 modules. The latest
document audit checked 2,947 local paths. The public API inventory lists 1,180 definitions; deferred metadata remains 268 cases/42 profiles/
83 modules.

### 2026-10-29 endpoint and source-bridge continuation

Added a provenance-complete exact-condition bridge from qualified absolute
adsorption states into `FiniteAdsorptionVessel`; it refuses surface excess,
source-defined loading, incomplete site/species row coverage, nonnumeric query
vectors and off-condition requests. The common-clock LH2DT receipt can retain a
caller-attested thermal utility ledger on the exact operation clock/window.
Mixture phase-selective withdrawal now closes pure-liquid/pure-vapor endpoints and
revalidates directly constructed withdrawal records against native compositions,
quality and enthalpies. Each seam has a deferred contract. Whole-source Ruff and
compileall passed. The document audit checked 2,944 local paths across 283 files;
the relative-import audit found 1,172 bound and zero missing/unresolved across 192
modules. Metadata inventory: 268 cases/42 profiles/83 modules. No tests, physical
models or Nurion jobs were run. Refresh the development archive after these source
changes.

## 2026-10-29 continued API integrity pass

Direct CORA MEC electrode series now require a source-column-consistent series ID,
matching observation provenance and unique ascending worksheet row coordinates.
Direct impedance traces reject invalid/nonordered worksheet rows and columns; the
dataset still requires complete reviewed workbook group coverage. Deferred
integrity metadata covers forged labels, duplicate coordinates and invalid EIS
rows. Generic observation APIs reject bare text as an experiment-ID/table
collection. HyRAM jet snapshots now bind the retained five-column centreline,
acceptance receipt and native mass/Gaussian transport arrays; finite-source
projection checks that snapshot before reuse. All added guards remain unexecuted.
Static inventory: 221 deferred cases / 39 profiles / 40 case modules, 1,182 public
definitions, 1,181 bound imports with zero unresolved, and 2,942 Markdown paths with
zero missing. Whole-source Ruff and compileall passed. A fresh isolated development
sdist/wheel passed archive exclusions and contains 192/192 package Python files
matching the working tree byte-for-byte. No validation case, scientific model or
Nurion job was run.
Whole source/case Ruff and compileall passed; Markdown audit checked 2,889 local
paths with zero missing, and the relative-import audit found 1,160 bound imports
across 191 modules with zero unresolved entries. The updated development archive
audit is maintained in `research/release_audit.md`.

The PV electrolysis area now exposes a typed post-run receipt binding original PV
production heat rows to an existing finite stack thermal trace. It verifies exact
shared stack, clock, intervals, current, caloric basis and explicit temperature/
energy tolerances. A synthetic deferred contract covers acceptance and heat-row
tampering; no execution was performed, and the receipt adds no live temperature
feedback.
The receipt is issued through a one-use token and seals original thermal/PV trace
identity, evidence, tolerances, residual and thermal signature against copying or
post-binding edits; adversarial checks are included in the same deferred contract.

Relief/cooldown phase-specific receipts can now be grouped into a typed sequence.
Composition requires the exact original native histories and port/boundary bases,
shared retained event-time endpoints, and continuous cumulative mass/enthalpy
ledgers. The contract checks overlap rejection and remains unexecuted; no phase
transition behavior or flow routing is inferred.

The thermal utility composition API is now re-exported from `h2physics.adapters`;
the deferred contract checks every source reader, accounting record and helper is
the same original implementation object, preserving owner-bound identity.

The reservoir-driven hydride trajectory API now issues output only from a completed
integration and validates its material/initial-state basis, vector dimensions,
physical state range, stored-mass relation and reduced-energy reconstruction.
A finite-hydride profile case records constructor, clone and ledger-forgery checks;
it is deferred and was not run.

The continued lineage audit found that the receipt fingerprint identified callback
objects but omitted mutable function closure cells and ordinary callable-instance
configuration. A transform or model callback could therefore change its retained
configuration after propagation while the old output receipt still reported current.
The seal now includes function defaults/closure values and ordinary bound/callable
instance attributes and slots without invoking callbacks. The deferred contract now
covers transform and model closure mutation; opaque external state still requires a
caller-declared revision/evidence identity. The case remains deferred and was not run.

## 2026-10-30 liquid accident ledger admission

`LiquidAccidentMassLedger` now requires a single-use token issued by its binding
factory and immutable mapping snapshots. This prevents direct construction from
exposing fabricated terminal branches or residuals before the existing freshness
check. The deferred liquid accident ledger case now records direct-construction
and detached-copy rejection. No case or calculation was run.

## 2026-10-30 absolute adsorption local sensitivity view

The exact-condition absolute-uptake bridge now exposes the provider's retained
site-resolved loading Jacobian when pressure and temperature derivatives are both
available. Its directional result is a first-order adsorbed-loading change only;
it does not project equilibrium conditions or include gas-phase inventory. The
absolute bridge deferred contract records derivative binding and direction mapping.
No case or physical calculation was run.

## 2026-10-30 facility operation reporting view

Added `report_facility_operation()` to compose existing accepted-time node and
component continuity results with the operation's original net utility quantities
and allocation residual. The report checks its retained operation on access and
does not assign costs, create process rates, or assert whole-facility closure. A
project-fixture deferred contract records receipt identity and series reproduction;
it was not executed.
## 2026-10-30 finite spherical-shell thermal model

Added `spherical_shell_heat_history()` as a finite-volume transient conduction
model for a homogeneous spherical wall. It reuses caller-owned radial material
and boundary contracts, uses spherical cell volumes/areas and radial resistance,
and retains independent inner/outer heat and stored-energy ledgers. Added a
deferred authored contract for the steady `A+B/r` limit, sign convention and
energy reconciliation, plus API and scope documentation. No tests, imports,
compilation or physical calculations were run; Nurion execution remains deferred.

## 2026-10-30 radial cylindrical hydrogen transport

`DiffusionMesh.cylindrical_shell()` now supplies radial finite-volume geometry for
a finite-length hollow pipe or vessel wall to the existing shared mobile/trap
transport solver. Annular volumes and lateral areas are exact; face conductance
uses the integrated cylindrical resistance for each radial interval. A deferred
constant-d logarithmic steady-profile, flux, and inventory contract was added under
the existing materials profile. No stress-driven transport, axial/end effect,
material parameter, or uptake correlation was added. The independent analytic
case has not been executed; no import, compilation, physical calculation, or Nurion
job was run.

## 2026-10-30 sampled hydrogen concentration alarm

`adapters.gas_detection` now evaluates an existing concentration history with
caller-declared trip/reset thresholds, hysteresis, consecutive-sample confirmation,
maximum observation gap and explicit sensor/threshold/logic provenance. Confirmed
trip evidence is accepted by the existing prescribed protection replay, which
retains the explicit action latency. This adds no detector response, calibration,
recommended setpoint, safety credit or physical plume calculation. A deferred
facility-protection contract covers trip/reset transitions, action scheduling and
invalid histories; it has not been run. No tests, imports, compilation, model
calculation or Nurion job was run.

Source-only inventory at this dated checkpoint: 74 families (20 implemented, 37
native-adapter-verified, 17 implemented-unverified); 263 deferred cases across 45
profiles and 55 modules; 1,253 public API definitions across 204 modules; 1,386
statically bound relative imports; and 3,253 local Markdown paths across 297 files.
The current inventory is recorded in PROGRESS.md. Static inventory is not scientific
execution or safety qualification.

## 2026-10-30 catalytic gas/surface fixed-wall thermal path

`CanteraCatalyticSurfaceReactor.run()` now supports an optional fixed-temperature
thermal reservoir connected to the closed rigid native reactor through a Cantera
`Wall`. The native reactor energy equation is enabled in this mode, allowing gas
temperature to feed back into the gas/surface reaction rates. It preserves the
existing isothermal path by default. The API retains native wall heat, a sampled
trapezoidal heat integral and its residual against gas-plus-adsorbate internal
energy; the declared budget rejects an output grid that does not close this
approximate ledger. This is an imposed wall-temperature model, not finite catalyst
support storage, spatial conduction, or process validation. Added an explicit
deferred Nurion case, source-method entry, catalog scope, API guide and profile
inventory mapping. No tests, project imports, compilation, physical calculations,
or Nurion jobs were run. Source-only AST and document audits found 1,253 public
definitions, 1,386 bound imports, and 3,253 local links across 297 files; the
validation inventory records 263 planned cases across 45 profiles and 55 modules.

## 2026-10-30 common-clock protection replay handoff

`OperationalScenarioReceipt` can now retain an existing `ProtectedEquipmentRun`
alongside the supply assembly and dynamic result. Admission requires the replay's
exact `DynamicEquipmentRun` object to be the receipt's run, with matching clock,
in-window accepted commands, current ownership checks, and an explicit
`protected_run:<index>` cross-owner evidence key. This composes the already
implemented alarm/action replay with operation receipts; it introduces no new
sensor, actuator, SIS, flow, or risk physics. The existing common-clock deferred
case now names this identity/window contract. No test, project import, compilation,
scientific execution, or Nurion job was run.

Relief integration failures now retain the actual accepted interval and transition
prefix, aligned mass/energy/heat histories, trial count, termination metadata and
original cause in `ReliefIntegrationError`. Added deferred `relief-lift-failure-prefix`
coverage requiring an actual later failure after a committed interval. Documentation
and the implementation backlog record this API boundary. No tests, project imports,
model calculations or Nurion jobs were run.

## 2026-10-31 relief failure-prefix fixture

The deferred failure-prefix case now constructs the reviewed native LH2DT
homogeneous tank, relief, shared nozzle and state objects. It schedules a valid
first 5 ms interval below the relief set pressure, then gives the native tank a
zero-kelvin ambient boundary in the second interval. The native tank rejects
that boundary; `ReliefIntegrationError` must retain the actual exception, native
owners, one accepted interval and aligned ledgers while excluding the failed
candidate. This is a deliberately invalid boundary-input rejection contract,
not a reproduced equipment/EOS failure or scientific qualification. It awaits
a fresh Hangang pin; no local tests, imports or calculations were run.

`DynamicEquipmentRun` can no longer be constructed as an ordinary caller-authored
receipt: the native accepted-output driver issues it once, and its stored native
records are fingerprinted for later freshness checks. Coolant-rate integration,
line cooldown auditing and operational-scenario binding recheck that fingerprint.
The existing deferred `native-dynamic-line-coolant-audit` contract now checks direct
fabrication rejection and post-issuance mutation; the synthetic fixture calls the
internal issuer explicitly. No tests, imports, calculations or Nurion jobs were run.


The ELVHYS4.2 cryogenic-room block API now rejects caller-created or replaced
observations that would otherwise retain its checked recorder source identity. A
synthetic contract was added to the existing shock-tube-data case module. AST-only
parsing and documentation inventory were refreshed; no case, import, calculation,
download or Nurion job was run.


Radial-cylinder heat results now require one-use issuance from the solver and retain a
content fingerprint over reported histories and solver/material/boundary identities.
Thermoelastic and vessel thermal-history consumers check freshness before sampling.
The existing deferred radial heat contract covers receipt cloning and mutation; no
case, import, physical calculation or Nurion job was run for this change.

`Lh2dtLowLevelProperties` now binds its original provider and state factory and
rechecks the underlying CoolProp state identity, backend and fluid around property
evaluation and native-state conversion. The existing finite-separator contract now
rejects replacement of that state object after adapter admission. This is a provider
lineage guard, not a new equation of state; it adds no deferred case. No tests,
imports, calculations or Nurion jobs were run.


## 2026-10-30 — retain closed-charge engine failure prefix

The moving-volume Cantera segment previously let a later native advance exception
escape without carrying the already completed output samples or the actual native
owners. ClosedChargeEngineError now retains the reactor, network, moving wall,
completed requested-output state prefix, failing target and original exception.
The existing hydrogen-engine profile gained the deferred
hydrogen-engine-failure-prefix contract (12 to 13 profile cases; 283 overall).
Its injected failure will be exercised on Nurion; no tests, Cantera imports or
physical calculations were executed locally.

## 2026-10-30 — bind prescribed-coolant trace to its solver

The prescribed-coolant `ThermalStackTrace` is now issued only by the actual
`FiniteThermalStack.run()` owner. The trace retains that owner and seals its
reported interval histories, native solver arrays and owner configuration.
`bind_electrolysis_thermal_operation()` rejects direct trace construction,
dataclass cloning, later mutation and a trace produced by a different thermal
owner. The existing deferred PV electrolysis/thermal case covers these boundaries;
no new case was added. Only AST parsing was used locally; tests, imports, physical
calculations and Nurion execution remain deferred.


## 2026-10-30 risk-owner and electrolysis thermal trace provenance

Conditional-risk native bindings now require issuance from the reviewed installed
package loader and retain package/module/version/digest/native callable identities.
The PV-electrolysis to finite-stack handoff likewise requires a trace issued by the
exact thermal owner and checks its solver histories/configuration before admission.
Both changes extend existing deferred contracts; total case count remains 283. No
tests, imports, physical calculations or Nurion jobs were run.


## 2026-10-30 thermal-effects reader block provenance

ThermalBlock is now issued only by ThermalEffectsFile.iter_blocks() after the checked
HDF5 source path and recorder descriptor are admitted. Direct construction and
dataclass replacement cannot assert the source digest for altered arrays. The
synthetic thermal-effects-block-loader-provenance case was added to the existing
data profile; no test, import, data read, model calculation or Nurion job was run.


## 2026-10-30 native Sobol result provenance

SobolSensitivity is now issued only after native SciPy analysis completes. It seals
the native owner and copied analysis batches, checks output-by-input indices and the
zero-variance mask against the retained native result, and rejects direct creation,
cloning or post-issuance edits. The existing joint uncertainty contract was expanded;
the current deferred plan remains at 284 cases. No test, calculation or Nurion job
was run.


## 2026-10-30 property-table report currentness

Issued TableQualification reports now seal their numeric property, identity-error,
energy-adjustment and timing summaries together with each original GasEnvelope
bound. Pass/error/speedup access checks the receipt before returning a decision.
The existing deferred gas-composition table case covers direct post-issuance report
and nested-envelope mutation; case count is unchanged. No tests, imports, calculations
or Nurion jobs were run.


## 2026-10-30 PIFIRA effective-area receipt binding

The downstream contents-equivalent flux adapter now accepts only a native-fit-issued
EffectiveAreaResult with unchanged observation arrays, fitted values, axial geometry
and native function identities. The existing thermal-target profile gained a
synthetic contract for direct construction, dataclass cloning and post-issuance
mutation. Total deferred cases: 285. This is provenance hardening, not a new fire
model or a PIFIRA validation result; no tests, calculations or Nurion jobs were run.


## 2026-10-30 checked HyRAM gas-jet receipt issuance

HyRAMJetRun now requires one-use issuance from run_hyram_gas_jet(). The existing
finite-source contract rejects direct construction and dataclass replacement while
its synthetic accepted receipt is issued through the same private boundary used by
the adapter. This closes native-execution provenance only and adds no physics or
deferred case. No test, import, calculation or Nurion job was run.


## 2026-10-30 SLABx-LH2 run receipt issuance

SLABLH2Run now accepts a one-use token from run_slabx_lh2 before sealing its source
and native result state. Direct construction is rejected, and dataclass replacement
cannot reuse the consumed issuance. Added a dedicated model-selection contract and
extended preferred-dispersion clone checks. No tests, imports, calculations or Nurion
jobs were run.


## 2026-10-30 slab diffusion result provenance

DiffusionSlab no longer emits an unauthenticated projection object. Its
DiffusionResult carries the exact solver-issued TransportResult, checks every
projected history against that source, and rejects direct construction, dataclass
replacement or later object-level mutation through `require_current()`. The existing
material-transport contract was extended; no test or physical calculation was run.


## 2026-10-30 flash-front output receipt integrity

FlashFrontTrace is now issued only after the native flame/HP and graph calculation
completes. It seals its accepted cells, references, summaries, and native sparse
graph/output arrays; clone or later source/graph mutation is rejected by
`require_current()`. The existing flash-front-binding deferred case covers issuance
and freshness. No test, import, physical calculation or Nurion job was run.


## 2026-10-30 finite adsorption delivery receipt provenance

Finite adsorption-vessel delivery receipts now require one-use issuance by the
vessel owner and reconstruct their component changes from exact charged/discharged
snapshots. Both endpoint snapshots and the delivery receipt seal nested state and
array content; downstream mass-flow conversion checks currentness before and after
projection. The existing storage-product-delivery contract covers fabricated,
cloned and forcibly mutated receipts. It adds no case and no time-resolved flow or
control equation. No tests, calculations or Nurion jobs were run.

## 2026-10-30 counterflow solver-result issuance

CounterflowFlameResult now requires one-use issuance from the native Cantera
diffusion-flame solver. Its former seal was a self-comparison of supplied object
identities and summaries and did not prevent a caller from constructing a matching
receipt. The existing counterflow-flame profile adds direct-construction and clone
rejection. No test, flame calculation or Nurion job was run.

Obstacle FDS result currentness now rehashes its captured native artifact tree,
rejecting changed bytes, added/removed files and symbolic links. The dormant FDS
contract mutates and restores one output artifact to check rejection. This adds no
case and does not run FDS locally.


## 2026-10-30 protected replay result issuance

ProtectedEquipmentRun is now issued only after the delegated native equipment replay
returns; a one-use token binds the exact run, driver, prescribed plans, accepted
invocations, mode identity and scenario evidence. The existing facility-protection
monitoring guard contract now rejects direct fabrication and replacement cloning.
This closes result ownership only; no protection physics or tests were executed.


## 2026-10-30 line-radiation receipt issuer

JetRadiationField now consumes a pending one-use issuance token created by the
native line_source_irradiance calculation. Directly instantiating the internal issuer
type no longer creates an accepted radiation result. The existing deferred
jet-radiation contract covers the forged-issuer attempt. No tests, calculations or
Nurion jobs were run.


## 2026-10-30 separated fuel-cell trace issuance

FuelCellCompartmentTrace now requires one-use issuance by the native separated-volume
driver. Its previous binding tuple could be computed and attached by a caller using
object.__setattr__; the existing native compartment contract now verifies direct
construction rejection. No case, physics level or Nurion run was added.


## 2026-10-30 vessel failure result ownership

VesselFailurePrediction and VesselPressureCapacity now require one-use issuance from
their HELPR adapter owner and seal their retained result fields. The radial thermal
bridge checks report freshness before returning prediction results. Existing vessel
validation contracts cover fabricated construction, clone attempts and forced
post-issuance mutation. No cases were executed and the case count did not change.


## 2026-10-30 Cantera multiphase result provenance

MultiphaseEquilibriumResult now requires one-use issuance from its actual native
equilibrium owner. The result seals snapshots, gates, phase definitions and live
Cantera Mixture state; amount_mol checks freshness before returning a projection.
The existing solid-native-caloric case covers construction, cloning and forced
mutation, with no case-count change. No tests, imports, equilibrium runs or Nurion
jobs were executed.


## 2026-10-30 oxygen-room result issuer and plan coverage

OxygenRoomResult binding issuance now requires a one-use token created only after
CanteraOxygenRoom.run() completes. The existing oxygen source-digest metadata module
now also checks direct binding forgery. That module and its oxygen-deficiency profile
had been omitted from the Nurion case collection; they are now enrolled with the
chemistry capability. No native model or validation entrypoint was run.


## 2026-10-30 biological native-run receipt and deferred profile

BiologicalRun now requires one-use issuance from the completed native ADM1 integration
and balance audit. Its currentness check seals the native solution histories, live
system state, sampled points, balance and source/version bindings. Added the separate
biological-process profile and biological-run-owner-receipt deferred contract, with
the reviewed QSDsan/BioSTEAM/thermosteam setup capability. This contract uses the
authored synthetic process and establishes receipt integrity only; no biological
calibration or full heat/water/H/O closure is claimed. No tests, imports, calculations
or Nurion jobs were run.


## 2026-10-30 Open Brayton result issuer

OpenBraytonRun can now be issued only within run_open_cycle_brayton after the native
station and conservation summaries are assembled. The existing deferred summary
integrity case checks direct-construction rejection. No cycle calculation or
validation case was run.


## 2026-10-30 one-use concentration alarm receipts

Sampled concentration alarm and same-clock voting traces, plus their confirmed-trip
evidence, now consume one-use tokens minted by the evaluator/bind operation. The
previous module-level sentinels could be imported to construct caller-authored
self-consistent results. Extended the existing facility-concentration-alarm contract
with direct-construction and replacement rejection. No tests, alarm execution,
calculations or Nurion jobs were run.


## PSA cycle result owner integrity

PsaCycleRun now requires one-use issuance after PsaDynaCycle.run completes and seals
its reported checkpoints/totals, native metadata, admitted case/schedule, owner
identities and pinned runner code hash. Cycle endpoint accounting verifies freshness
before and after projection. The existing deferred adsorption-cycle contract covers
direct construction, cloning and checkpoint mutation. No tests, imports, calculations
or Nurion jobs were run.


## 2026-10-30 underground native trace issuance

UndergroundTrace construction is now gated by a one-use token created only after
UH2SC completes and the host inventory audit finishes. The existing dormant
underground-storage contract checks dataclass-clone rejection; no case count changed.
No tests, imports, calculations or Nurion jobs were run.


## 2026-10-30 pool-fire trace issuer integrity

PoolFireTrace now consumes an opaque one-use token minted inline after completed
finite native pool-fire audits. Removed the caller-invocable issuer factory; the
existing baseline contract rejects arbitrary caller-created tokens and still checks
cloning/freshness. No tests, imports, calculations, or Nurion jobs were run.


## 2026-10-30 oxygen criterion screening receipt

OxygenCriterionResult now receives a one-use token only after the declared screen has
been computed from a current verified room result. It seals the exact room/criterion
identities, flags, crossing estimates, interpolation and reconstructed duration;
`require_current()` revalidates the room result and criterion before use. The existing
oxygen-room-result-issuer case checks constructor forgery. No test, Cantera execution,
physical calculation or Nurion job was run.


## 2026-10-30 Bauwens and detonation result receipt integrity

Standalone Bauwens peak and threshold results now require one-use issuance from the
native evaluation and converged root/forward-check paths. Their projections and
nested solver receipts are sealed and checked by `require_current()`. Native CJ and
frozen-shock results likewise require issuance from completed SDToolbox solver/audit
paths and seal the retained native phase/solver state. Added two dedicated deferred
synthetic-input contracts and separate capability profiles for native HyRAM and
SDToolbox. Metadata inventory increases by exactly two cases, two profiles, two case
modules and two curated profile/module associations: 292 / 49 / 67 / 70. No tests,
imports, calculations or Nurion jobs were run.


## 2026-10-30 photochemical conversion receipt integrity

PhotoConversion now requires a one-use token from convert_photon_exposure(), while
PhotoOperationTrace requires issuance from run_photochemical_operation(). Content
fingerprints recheck nested photon inputs, reaction result arrays, windows, endpoints
and energy summaries before downstream operation accounting. The existing
photochemical-adjacent-finite-operation contract was extended for direct construction,
dataclass replacement and nested-source mutation; no case was added. No tests,
imports, physical calculations or Nurion jobs were run.


## 2026-10-30 staged electrochemical result issuance

StagedElectrochemicalTrace now consumes a one-use token issued only after the
thermal and finite-material owner schedule completes. The existing staged
electrochemical deferred contract now rejects direct construction and replacement
clones. The calculation remains an explicitly staggered held-temperature
approximation. No tests, imports, calculations or Nurion jobs were run.


## 2026-10-30 native thermal-exchange receipt revalidation

NativeExchangeReceipt now requires one-use issuance from bind() and revalidates the
exact opposite side pair, shared source/window, transfer direction and interval
energy equality before utility accounting. The existing thermal-native-HX deferred
case covers direct same-side receipt construction and clone/token reuse. No case was
added. No tests, imports, calculations or Nurion jobs were run.


## 2026-10-30 native hydrogen-economics result issuance

HydrogenEconomicsResult now consumes a one-use token created inline after the native
financial evaluation; no public helper can mint a result. Its currentness check
revalidates the projection/provider and binds native LCOH/NPV, annual arrays, input
fingerprint, annual/financial basis and optional priced window. The existing
economics-native-direct case covers direct fabrication, replacement and mutation.
No new case; no tests, imports, calculations or Nurion jobs were run.


## 2026-10-30 parcel transport trace provenance

ParcelTrace now requires one-use issuance after a completed native flight run.
Its content check retains accepted/trial records, native SciPy state/event arrays
and all balance summaries; population and finite-impact consumers validate it before
use. The existing droplet-transport case now covers direct construction, consumed
token replay and forced summary mutation. No scientific test, calculation or Nurion
job was run for this change.

HE-Austenite block results now require a one-use token issued by the pinned
collection iterator and fingerprint their observation table, source rows, linked
composition rows and invalid-reason metadata. Paired-property comparison checks the
receipt before calculation. The existing deferred observation contract covers direct
construction, token replay and mutation; no physical validation was run.

## 2026-10-30 pressure-peaking workbook provenance

Pressure-concentration workbook receipts and bounded blocks now require one-use
issuance by the checksum/schema-qualified workbook reader and its iterator. The
receipt revalidates source identity and file digest; blocks fingerprint the retained
observation table, clock strings, issues and clock identity before time-series
projection. Added the synthetic XLSX deferred issuance/mutation contract to the
existing pressure-peaking case module. The fracture-fatigue profile inventory is
now 25 cases and the total metadata inventory is 293. No case, import, calculation,
download or Nurion job was executed.

## 2026-10-30 LH2DT reliquefier result issuance

Native steady reliquefier results and dynamic steps now require one-use
issuance from their evaluation/integration paths and recheck retained result
content before product accounting. The finite product collector and receipt
currentness check enforce this boundary. The existing reliquefier-product
guards contract was extended for direct construction and changed-result
rejection; the case inventory is unchanged at 293. No tests, imports,
calculations or Nurion jobs were run.

## 2026-10-30 Cantera equilibrium result provenance

EquilibriumResult now consumes a one-use issuance token from CanteraGas and
retains the exact native phase handle. Its currentness check rejects altered
result summaries and native phase evolution after capture. The existing
flash-front-binding deferred case now covers fabricated and replaced
equilibrium summaries. ReactorTrace and FreeFlameResult still need equivalent
result-level guards; no tests, imports, calculations or Nurion jobs were run.

## 2026-10-30 Cantera trace and flame result provenance

`ReactorTrace` and `FreeFlameResult` now consume one-use issuance tokens created
only by their native `CanteraGas` solver paths. Reactor trace summaries are
sealed and checked against the retained native reactor endpoint before event
extraction. Free-flame summaries and editable native profile arrays are sealed;
flash-front admission and subsequent reference guards require the result to
remain current. The existing `flash-front-binding` deferred case now covers
direct construction, dataclass replacement, and stale native reactor/flame
state. No validation runs, imports, calculations, or Nurion jobs were performed.
# 2026-10-30 — Synthetic source-block receipt coverage

Added two deferred `source-data-ingestion` contracts for the fermentation and AB2
hydride-tank XLSX readers. Fixtures are generated locally as minimal XLSX ZIP/XML
containers using only the standard library; the profile declares openpyxl because
the exercised reader APIs use it at runtime. Cases cover genuine reader issuance,
direct/replacement forgery rejection, row alignment, and post-load mutation
detection. No acquired source records, tests, imports, calculations, or Nurion runs
were used in authoring this coverage. The metadata plan now totals 295 cases, 50
profiles, 68 case modules, and 71 curated profile/module associations.

# 2026-10-30 — Adsorption product projection currentness

Added `AdsorptionProductMassFlow.require_current()` so an already-created
species mass/rate projection can revalidate its source delivery and derived
ledgers before downstream reuse. The deferred storage-product-delivery contract
now records source-receipt mutation and projection-ledger tampering after
issuance. No Nurion case, test, model calculation or import was executed.


# 2026-10-30 — Schema-neutral HDF5 structure inventory

Added an optional-data API that records HDF5 group/dataset/link paths, dataset
shape and storage metadata, bounded immutable attribute values, HDF5 library
version, file size and SHA-256. Soft and external links are recorded without
following them. The inventory does not load dataset arrays, infer units, or assign
measurement meaning. A synthetic deferred source-data contract covers metadata
retention and object-count limits; it has not run. The acquired engine figure files
still need schema-specific source review before observation blocks can be authored.
No package import, scientific calculation, test execution, or Nurion job was run.

# 2026-10-30 — Mesh-owned steady transport projection

Added `DiffusionMesh.steady_transport_rate_mol_s()` to calculate the signed
constant-diffusivity steady transport rate from the existing mesh's series face
resistance. The analytical cylindrical-shell rate is now included in the existing
deferred cylindrical diffusion contract, so the steady check shares the same
geometry owner as transient mobile/trap transport rather than introducing a second
geometry implementation. The method excludes transient storage, traps,
concentration-dependent diffusivity and surface kinetics. No validation case,
calculation, or Nurion job was run.


# 2026-10-30 — Facility chain family callback admission

`assemble_facility_accident_chain()` now rejects a gas-only HyRAM source projection
callback on the LH2-origin path before the graph can invoke its finite-operation
node. The existing `facility-accident-chain-source-prefix` deferred contract records
this wrong-family configuration rejection. No test, import, model calculation, or
Nurion job was run.

# 2026-10-30 — CoolProp constructor admission before optional import

Moved pure Python configuration checks for fluid, backend, internal-energy policy
and quality-roundoff budget ahead of optional CoolProp import and native state
construction. Malformed calls now fail with the documented type/domain errors
without requiring the optional thermo dependency to be present. The existing
`thermo-gas-envelope-input-guard` deferred case records this boundary; it has not
run. EOS behavior, table speed, phase coverage and experimental qualification are
unchanged and still await the Nurion campaign.

# 2026-10-30 — Valve-map evidence admission

`ValveEffectiveAreaMap` now rejects values that are not the typed `ValveMapEvidence`
receipt during construction. This replaces a later attribute error at valve binding
with a direct configuration error and prevents an evidence-free area curve from
entering the actuator API. The existing `valve-actuator-map` deferred contract records
the invalid evidence path. No tests, imports, calculations, or Nurion jobs were run.


# 2026-10-30 — Preferred-dispersion acceptance policy admission

`DispersionScenario` now requires a real Python boolean when callers override its
`require_accepted` policy. This prevents integers and strings from silently acquiring
truthy/falsy diagnostic or rejection semantics in the selected HyRAM/SLABx-LH2 route.
The existing `selection-preferred-dispersion` deferred contract now covers integer,
string and `None` substitutes. The contract remains unexecuted; AST parsing and a
whitespace check only were performed.

# 2026-10-30 — Native dispersion and flame flag admission

The direct HyRAM gas/flame, HyRAM jet-source projection, and SLABx-LH2 run and
quasi-steady snapshot APIs now require actual Python booleans for acceptance policy.
The flame radiation API likewise checks diagnostic rejection and kernel-acceptance
overrides explicitly before consulting its retained native flame. This closes a
truthiness admission gap only; it does not change provider physics or acceptance
criteria. The existing preferred-dispersion deferred case now includes direct adapter
inputs with invalid flag values. No case, native engine, or scientific calculation
was run; changed Python sources were AST-parsed only.

# 2026-10-30 — Mesh-consistent steady diffusion profiles

`DiffusionMesh.steady_concentration_profile_mol_m3()` now reconstructs the
constant-diffusivity cell-center profile from the same integrated face conductances
used by transient transport. It returns a read-only array and is documented as a
reference/initial condition only; traps, finite surface inventories, and transient
lag remain outside this steady solution. The existing deferred cylindrical-shell
case now checks profile immutability and reverse-boundary symmetry alongside its
analytic flux and inventory checks. No case, test, import, or model calculation ran.

# 2026-10-30 — Local implementation continuation

The mesh now returns a read-only steady cell-center concentration profile from its
integrated face resistances. The same resistance calculation rejects values outside
floating-point range for both the profile and signed rate; the cylindrical deferred
case records reversed-boundary symmetry and this rejection.

Three parallel API increments reuse existing owners. The HDF5 metadata receipt can
recheck source file byte identity before reuse. The map-bound open Brayton receipt
reports compressor, gross turbine and net gas-path reference powers at caller air
flow, excluding mechanical/generator/cooling/bleed/auxiliary closure. Oxygen-criterion
screens can select exact output-sample windows and retain the original selected grid;
off-grid boundaries are rejected. Corresponding contracts remain deferred. Static AST
parsing and Markdown-link audit only were performed; no model, test or Nurion work ran.

HDF5 metadata receipts now also use one-use reader issuance and a content seal. Direct
construction, dataclass cloning, and post-inspection inventory edits are covered by
the existing synthetic source-data-ingestion contract; only local AST parsing was
performed. The snapshot remains structural metadata and retains no measurement values.

# 2026-10-30 — Exact-window and non-ideal activity handoffs

`RadialFailureSeries.sampled_window()` now creates a sealed inclusive view bounded by
exact original thermal sample times, preserving signed SIF values and global indices.
The post-run fuel-cell activity receipt now also accepts a caller-owned typed fugacity
callback for actual/reference fugacity at the same explicit temperature; ideal-gas
pressure ratios remain the default. The HDF5 metadata inventory was further sealed
against direct construction, cloning and post-inspection edits. Existing deferred
contracts were extended. These are interfaces/receipt boundaries only; no SIF law,
EOS, coupled fuel-cell solve, HDF5 measurement semantics or physical validation was
added. No tests or model calculations ran.

# 2026-10-30 — Gas diagnostic result integrity

`GasStateDiagnostics` now retains a signature over its input state, explicit
specific gas constant and derived projections. `require_current()` rejects an
altered projection before downstream admission. The deferred diagnostic contract
includes edited-copy rejection. This is result integrity only; it does not
qualify EOS or transport properties. No validation case or model was executed.

# 2026-10-30 — Crank-angle boundary schedule conversion

Added `engine_schedule_from_crank_angle()` to map caller-supplied angle/value
samples onto the closed-charge engine's absolute clock using the declared
constant speed and segment origin. The helper preserves the existing schedule
source/units contract and adds no valve, injection, spark or heat law. The
deferred engine profile now records clock mapping and invalid-window cases. No
validation case, import or model calculation was run.

# 2026-10-30 — Radial hydrogen concentration eigenstrain

Added `HydrogenConcentrationEigenstrainProfile` and
`radial_hydrogen_eigenstrain_cylinder()` by extending the existing long-cylinder
thermoelastic BVP. The profile requires an explicit carrier/basis, reference
concentration and temperature, linear expansion coefficient and evidence ID.
The result retains pressure/thermal baseline, combined stress, and separate
hydrogen stress increments. The model is one-way and static; it does not couple
stress back into concentration transport or provide a material coefficient.
Its synthetic deferred Nurion contract remains unexecuted; no local model or
scientific case was run.

# 2026-10-30 — Hangang source staging and dispersion execution lanes

Transferred a source-only archive through the existing KISTI shared-connection
wrapper, checked the archive SHA-256 remotely, and installed Python 3.12.9 core
and common thermodynamic/data dependencies in a private virtual environment. An
editable install and import smoke check succeeded after BLAS/OpenMP thread counts
were capped; no scientific case or PBS job ran. The local source advanced after
that first remote snapshot. A later sync was attempted after the user reported
reconnection, but both Hangang CPU and GPU wrappers reported that no shared master
was available, so remote work stopped without authentication attempts.

Added optional caller-owned executor support for independent quasi-steady
SLABx-LH2 source bins, preserving original interval slots and collecting failures
without claiming real-provider thread safety. Added a deferred synthetic HPC case
and a concrete HyRAM native receiving contract for same-run mass, momentum and
energy flux closure. Review of BAM's source labels found no justified mapping
from plate temperatures/flows to incident heat flux or cylindrical wall state;
the missing measurement contract is documented. No local scientific tests or
calculations ran.

# 2026-10-30 — Engine boundary transfer ledger

Added `EngineBoundaryStream` and `integrate_engine_boundary_streams()` as a caller-
schedule ledger on the existing absolute-time piston-engine schedule API. Intake,
fuel, and exhaust transfers preserve distinct signs, common time support and a
declared enthalpy reference. Mass uses trapezoids and the product of two piecewise-
linear schedules uses exact Simpson integration on each common segment. A deferred
`hydrogen-engine` contract is registered in the Nurion and Hangang plans. The ledger
does not connect to valve/injector physics or accepted cylinder solver steps and
does not close a full engine cycle. No scientific test or calculation was run.

# 2026-10-30 — Mixture separator accepted-history audit

Added a typed post-run audit for externally accepted, phase-resolved mixture
inventory snapshots. The audit checks fixed vessel volume, species ordering,
provider molar-mass identity, admitted phase properties and cumulative component-
mole/internal-energy closure at each exact time. Its contract is registered under
the existing `gas-composition` Nurion profile. It does not flash changing
composition, integrate an inventory, locate phase events or establish native-run
ownership. The case remains unexecuted; no scientific test or calculation was run.

Hardening follow-up: the issued receipt now retains the exact accepted-point objects
and seals their inventory-admission, provider and native phase-packet identities.
`require_current()` revalidates nested admissions and recomputes the per-row balance
summaries. The deferred case includes post-issuance mutations to both an admission
and an accepted-point ledger; both must stale the enclosing audit. It remains a
post-run consistency check only, and no scientific case was run.

# 2026-10-30 — HyRAM plug-to-Gaussian transition snapshot audit

Added a host-side audit over provider-issued, immutable, same-run radial plane
snapshots. It reports separate H2 and total-mixture mass-flow, axial-momentum
(including pressure correction when available), and excess enthalpy-plus-kinetic
energy ledgers with independent closure and quadrature-error budgets. Unsupported
or incomplete transfers remain explicitly incomplete. The deferred case is listed
in the Hangang and Nurion plans. This audit neither runs nor modifies HyRAM and
does not establish native snapshot accuracy or validate the physical model. No
tests or calculations were run.

# 2026-10-30 — Bounded two-phase mixture V/U flash

Added `flash_two_phase_inventory_vu()` as a single-state equilibrium resolver
around the existing fixed-composition CoolProp PQ packet provider. It solves in
bounded pressure and vapor quality against caller-declared total volume, internal
energy and component moles. Multiple explicit seeds must meet closure limits and
cluster to one root; the result records native packet and SciPy solver diagnostics.
A deferred `gas-composition` Nurion case and API/source documentation are registered.
The resolver does not integrate a changing mixture inventory, process ports, or
localize phase events. The full 311-case metadata count is expected but unrefreshed;
no imports, compilation, tests or scientific calculations were run.

# 2026-10-30 — Prescribed-flow open-cylinder segment

Added `run_open_cylinder_segment()` as a distinct Request034 model level. Cantera 3.2 owns the reacting ideal-gas reactor and integration. Fixed, source-bound feed states enter through scheduled native mass-flow controllers; scheduled outlets remove the current well-mixed cylinder gas; the existing slider-crank geometry drives a native moving wall. The result retains requested accepted samples, native owners, species-transfer and sampled mass/energy diagnostics. Failure retains native objects and the accepted output prefix. Valve/nozzle flow, spark, wall heat, direct injection, accepted-step conservation certification, complete-cycle closure and experimental qualification remain unimplemented. One deferred case is added to the `hydrogen-engine` profile in both Nurion and Hangang plan sources. The expected metadata inventory is 312 cases/52 profiles/82 modules (84 associations), pending the target Python 3.12 refresh. No import, test, compilation or calculation was run.

# 2026-10-30 — Sampled concentration-sensor time-constant fit

Added `fit_first_order_sensor_time_constant()` in a separate adapter module. It
fits only the time constant of the already-declared piecewise-linear-input,
first-order, unity-gain sensor from aligned sampled truth and measured indication.
The fit requires exact clock, concentration basis/unit, initial indication,
separate series-source evidence, calibration evidence, origin, sample-gap limit
and positive search bounds. The immutable receipt retains source samples,
calibrated config, residuals, RMS and a boundary-limited flag. It estimates no
gain, bias, dead time, noise or uncertainty and does not certify a detector or
safety function. Two deferred synthetic contracts are registered under
`facility-protection`; the metadata inventory was not refreshed. No tests,
imports, numerical calculations or cluster work were run.

# 2026-10-30 — Oxygen threshold-deficit metric

Added an exact interval integral of the positive part of an already-admitted
oxygen criterion's threshold deficit under its declared piecewise-linear sample
reconstruction. The result retains interval and total values with criterion-derived
units (mole-fraction·s or Pa·s). It is explicitly not a physiological dose or
probability. A synthetic analytic contract is deferred under `oxygen-deficiency`;
the code has not been executed.

# 2026-10-30 — Accident consequence and engine boundary composition

Added `run_facility_accident_consequence()` to pass the exact accepted final
dispersion handoff into the existing consequence evaluator. Chain/handoff/result
failures retain their stage and completed context; this composes owners without
adding receptor or consequence physics. Added a source-bound caller-specified
piston-face heat-flux schedule to the closed-charge Cantera moving-wall segment
and integrated it into the sampled first-law summary. Added crank-angle mapping for
a caller-prescribed fixed-state fuel mass-flow trace through the existing native
open-cylinder feed boundary. These are boundary/composition levels only; engine
heat-transfer qualification, injector geometry, spray and jet-momentum coupling,
and complete-cycle closure
remain open. Deferred contracts are in the campaign sources; none has run.

# 2026-10-30 — PEACE alkaline process data

Cataloged the PEACE pressurized alkaline short-stack record under record-level
CC BY 4.0. Acquired the column map and three raw experiments from public record
download links into ignored raw storage (11,514,333 bytes); each publisher MD5
matches and each local SHA-256 is pinned in the manifest. The files share an
identical 131-field header. The source-bound reader verifies both hashes and
projects selected publisher-described tokens without converting units or clocks.
Issuer seals and source reconstruction reject forged/replaced channel maps, raw
tables and projections. Four deferred contracts use synthetic files only; no
observation fitting or model validation has been run. The distinct TU/e flow-cell dataset has explicit
DataCite CC BY metadata, but 4TU's file inventory/schema was unreachable, so no
file, parser or validation case is claimed for it.

# 2026-10-30 — source-bound accident/consequence uncertainty adapter

Added `facility_accident_consequence_uncertain_model()` as an adapter that returns
the existing `UncertainModel`; caller-owned joint transforms and the native QMC
engine still perform all sampling/propagation. Each response retains the accepted
chain/consequence run and original scalar-reader response. `JointPropagationResult`
now invokes an optional `require_current()` guard carried by `ModelOutput.raw`, so
mutated source-bound outputs invalidate the propagation receipt. Added one
synthetic deferred acceptance case to both Hangang and Nurion plans, plus the
joint-uncertainty/campaign documentation. No import, test, calculation or HPC job
was run.

# 2026-10-30 — direct property-provider binding for porous storage

`PorousReservoir.from_property_provider()` now accepts the shared Python
`PropertyProvider` interface, including `CoolPropProperties`, while retaining
the prior explicit density/viscosity callback API. Provider mode preserves the
exact `PropertyBasis`, obtains density and viscosity from one returned state,
and rejects non-gas or undefined-viscosity states instead of silently applying
single-phase Darcy flow. A deferred HEOS boundary case is enrolled in the
existing porous-reservoir profile; that profile now declares the optional
thermo dependency. No runtime model calculations or tests were run locally.

# 2026-10-30 — shared-nozzle open-cylinder feed

Added `OpenCylinderNozzleInlet` to connect the shared homogeneous isentropic
nozzle to live Cantera cylinder pressure, using a native mass-flow controller
only to apply the accepted nozzle rate. The source and cylinder must share the
exact Cantera frozen-gas mechanism/property basis; nozzle results and failure
prefixes remain attached to the cylinder trace. The deferred case is included
in the existing `hydrogen-engine` module. This provides nozzle mass-flow and
choking behavior, but no injector geometry, jet momentum transfer or spray
physics. No runtime tests or calculations were run.

# 2026-10-30 — measured channel views and impact composition

The PEACE alkaline and BAM jet-fire loaders now offer optional unit-normalized
views only for channels with explicit publisher labels, while preserving raw
tokens, source hashes and unresolved semantics. Time/reference-volume, pressure
basis, calibration and measurement geometry remain explicit gaps. A sequential
parcel-population adapter also sends distinct unit-count impacts through one
existing finite surface/wall owner in event order; it does not multiply a
representative group or simulate simultaneous impacts. These deferred cases
are metadata plans only; no model/data validation was run.

# 2026-10-30 — cryogenic adsorption source binding and impact-trace integrity

Added `h2physics.data.load_cryo_mof_isotherm()` for the public, explicitly
licensed version-1.1 cryogenic MOF record. The API verifies the resolved dataset
identity, exact listed CSV member, publisher size/checksum and independent
acquisition SHA-256. It retains raw tokens, source rows and separate adsorption/
desorption branches, assigning only reviewed unit views while keeping 20 K
reference-gas and 77/87 K pressure semantics unresolved. Raw files remain ignored.
One synthetic deferred source-contract case is enrolled in both Hangang and
Nurion plans; it has not run and does not establish adsorption-model validation.

Finite-wall `SurfaceImpactTrace` now requires a one-use owner issuance. Its
currentness audit checks original step identity/order and reconstructs aggregate
mass, residual and final-wall values from those steps. The sequential population
adapter calls the audit before accepting or reusing a trace. A synthetic issuer/
mutation contract was added to the existing impact profile and registered in
both plans. It remains unexecuted; no material-impact accuracy claim is made.

## 2026-10-31 — parcel impact deferred-fixture correction

Hangang 1185904 `parcel-population-finite-impact-sequence` failed because the
previous synthetic parcel launches produced no ground-crossing event. The case now
uses shorter launch heights and a larger downward launch speed so its two unit
parcels contact the finite patch at distinct times while keeping the authored low-
Reynolds/low-Weber assumptions. No flight or surface-impact rule was relaxed. The
sensor rejection return correction associated with 1185906 is also local and is
queued for the next capture. Both changes await a fresh source snapshot and retry;
no physical qualification is claimed.

## 2026-10-31 — PBS pinned script import path

Hangang jobs 1185918/1185919 failed in the risk helper because workers exposed the
pinned snapshot's `/src` but not `/scripts`, while `scripts/check_finite_supply.py`
imports sibling `check_equipment_network` as a top-level module. `write_pbs_array()`
now orders worker import paths as pinned `/src`, pinned `/scripts`, then inherited
`PYTHONPATH`, preserving the package-source precedence and resolving sibling helper
imports from the same source capture. The existing `cluster-setup-script-pin`
deferred contract now asserts this generated path order. This fix is local and needs
a fresh snapshot/retry; no tests or calculations ran and no safety-model validation
is established.

## 2026-10-31 — porous schedule shape and fuel-cell receipt corrections

The porous-reservoir schedule no longer compares initial cell pressures with the
number of time samples. Its constructor continues to require a nonempty positive
pressure vector and exact well-flow/time alignment; `PorousReservoir.run()` checks
the pressure vector against radial cell count. The existing one-cell two-sample
fixture therefore represents the declared shapes, and the deferred case adds a
misaligned well-flow rejection input. This addresses the 1185901 API-contract
failure without relaxing schedule chronology or pressure validation.

The reported 1185898 fuel-cell currentness issue was traced statically: the sealed
content tuple created fresh `dict(...)` copies of immutable source-rate mappings,
while `recorded_content_sha256` deliberately includes mapping identity. Rechecking
an unchanged receipt therefore fingerprints different temporary objects. The seal
now uses the original retained mapping proxies directly; it still binds their
identity and content. The remote attempt record presently says running and has no
outcome receipt, so this is a source-grounded local correction, not a confirmed job
result. Both fixes await a new pinned capture/retry; no local tests, imports or
calculations were run.

## 2026-10-31 — current5g catalytic thermal sampling invariant

The immutable current5g archive has SHA-256
`fd5106853ea82036d4df04e4df444a20d02d6bb431da396399a02962e411bc55`; its
1,123-entry source manifest verifies on Hangang. Job 1186567 passed the source
and plan checks and entered the catalytic wall heat contract, then rejected the
sampled state with `Native finite isothermal gas/surface domain changed`. The
previous undefined-flow-bound reference is fixed, so this is a distinct code
path. Inspect the wall-heated surface/gas temperature invariant before the next
replay. This is a software boundary failure, not scientific model evidence; no
local model tests or calculations were run.

## 2026-10-31 — current5g sensor handoff execution

Independent current5g Hangang job 1186578 passed
`cantera-reactor-hydrogen-sensor-alarm-handoff`. Its synthetic retained trace
reported a 0.06 s alarm trip while H2 mole fraction was 0.10. This confirms the
sensor/alarm API case executed and its recorded invariant was accepted; it does
not qualify a physical detector, sensor, alarm setpoint or facility response.
The case was submitted while catalytic heat failure analysis and current5h
transfer proceeded in parallel. No local tests or calculations were run.

## 2026-10-31 — hydrogen acoustic source hash reconciliation

Downloaded the Zenodo 21355851 ZIP and record response through the authorized
Hangang `run.sh` route. The publisher ZIP is 45,826 bytes with SHA-256
`38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553`; the
6,458-byte record response is
`1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`. The
record's DOI, title, version and four file entries match the pinned Zenodo
source; the archive MD5 and byte count also match the publisher listing. Fixed
two transcription errors in code, Hangang case, research inventory and guide,
then atomically promoted both checked staged files. This confirms source
identity only. The pointwise EOS diagnostic still awaits a fresh pinned run and
cannot establish independence from EOS training data. No local tests or model
calculations were run.

## 2026-10-31 — photon-path Gibbs energy bound

`PhotoGibbsEnergyBudget` now accepts caller-supplied reaction affinities over a
strictly monotone finite-extent path. It reconstructs intermediate species amounts
from the retained balanced stoichiometry, integrates `ΔrG dξ` with the declared
piecewise-linear path, binds to the photochemical condition-state identity, and
compares positive integrated Gibbs increase with absorbed optical energy. The
result is a photon-only necessary energy bound. It does not infer radiation
exergy, conversion kinetics, thermal-work equivalence or reactor feasibility.
Its deferred contract uses synthetic values and is registered for Hangang and
Nurion. No test, import, local calculation or scientific validation was run.

## 2026-10-31 — lumped pipeline linepack

Added an immutable fixed-volume ideal-gas linepack state and interval ledger for
caller-prescribed inlet/outlet rates. Pressure follows inventory, fixed
temperature, and fixed molecular mass. The step rejects a requested net
withdrawal that reaches the caller's mass floor. It does not model flow
momentum, wave propagation, friction, energy or species evolution. The API and
synthetic deferred case use the existing gas-compressible-pipe profile; no
local test or calculation was run.

## 2026-10-31 — detector voting failure probability

Added exact heterogeneous Poisson-binomial fail-to-alarm probability for an
explicit k-of-n detector vote, combined with a separately supplied
common-cause event probability. The input receipt retains channel order,
mission, voting logic, and caller evidence IDs. The case uses synthetic
probabilities and does not infer rates, repair, common-cause groups, test
coverage, or setpoints. It is registered under facility-protection for the
next Hangang pin; no local test or calculation was run.

The same family now also accepts an immutable, source-versioned record of
simultaneous equal-duration demand windows and summarizes observed system and
common-cause fail-to-alarm frequencies. This empirical route preserves observed
cross-channel dependence rather than imposing an independent-channel formula.
It does not verify the source file, compute confidence intervals, or extrapolate
future rates. Its second synthetic Hangang case is in the same case module.

## 2026-10-31 — catalytic CSTR accepted-state sampling

The Cantera catalytic CSTR sampler now restores its native reactor thermo and
surface phase handles from accepted integrator state before reading phase
temperatures. This retains the strict equilibrium invariant and addresses the
stale-handle discrepancy seen in Hangang 1186160 without tolerancing it away.
The current result belongs to the earlier pin; retry awaits fresh capture.

## 2026-10-31 — mixture event fixture backend boundary

Hangang 1186192 rejected the initial 50/50 H2/N2 partition at 5 MPa and
vapor-mole quality 0.5: the native CoolProp phase compositions left component
closure residuals of about `1.3685e-5`, above the declared `1e-7` bound. The
exception occurs before the adaptive integrator or event callback runs. No
solver tolerance was widened and no alternate synthetic state was guessed in
the absence of a separately demonstrated valid point. The failure and exact
stage are documented in `FINITE_MIXTURE_ODE.md`; a fresh pinned backend case is
required to identify a valid starting state or property route.

## 2026-10-31 — hydrostatic fragment flight fixture correction

Current-pin case 1186210 reached the trajectory API but the synthetic launch
did not contact the ground during its declared 30 s interval. The local fixture
now starts at 250 m, inside the unchanged altitude profile, and asserts that
the impact time falls on the sampled interval. The physical model's profile
domain and acceptance bounds were preserved. On the same pin, 1186209 native-
pool impact, 1186226 conditional fragment flight/impact and 1186227 impact
intercontact heat passed their synthetic contracts. The fixture correction
awaits a fresh source pin.

## 2026-10-31 — turbine map point freshness contract

Hangang 1186268/1186269 exposed a shared cooling-bleed result calling a
nonexistent `TurbineMapPoint.require_current()` method. Added the method as the
point's freshness owner: it rechecks the admitted component map and reconstructs
the interpolation at retained coordinates, without executing a cycle. The
Brayton bleed case now checks freshness and rejects a changed map-point value;
the turbine pairing receipt delegates to the same contract. A new source pin
and Hangang retry are pending; no tests or calculations were run locally.

## 2026-10-31 — fuel-cell callback fixture binding

Hangang 1186272 failed before its first accepted sample because the native
connection considered a callback changed. The synthetic thermal-partition
function was nested in the case runner and closed over a locally imported
`FuelCellThermalPartition` class. The case now uses a module-level callback
that imports the class inside its invocation, avoiding that captured class
cell while preserving exact callback binding and all physical tolerances. This
fixture-only change awaits a fresh source pin and retry.

## 2026-10-31 — fuel-cell deferred fixture follow-up

Follow-up Hangang results found a second callback-binding instance in the
synthetic zero-current case. Its thermal partition now uses a module-level
function with a function-local type import, preserving the adapter's strict
freshness check. A separate current-limit fixture now requests 2000 A/m²,
above its independently calculated oxygen cap (about 1608 A/m²), so the
expected oxygen-limited branch is exercised while the cap formula is unchanged.
Both are fixture-only corrections; a fresh immutable source pin is required
before deferred Hangang retries. No local tests, imports or calculations were
run.

## 2026-10-31 — synchronized fuel-cell callback provenance

Current2 Hangang case 1186418 failed in the callback freshness guard before the
first accepted sample. The saved failure identifies the callback pair but does
not expose which member's binding differed, so no production freshness rule was
relaxed. The constant-current fixtures are now module-level functions, like
the thermal-partition fixtures, eliminating runner-local function bindings.
The adapter reports current-density and thermal-partition callback changes
separately on the next retry. This fixture/diagnostic update needs the next
immutable source pin; no local tests or calculations were run.

## 2026-10-31 — finite-source gate bool normalization

Hangang 1186378 stopped during accident-chain projection initialization because
NumPy-backed rate comparisons produced a `numpy.bool_`, while the immutable
projection contract intentionally requires an exact Python `bool`. The
mass/enthalpy gate now normalizes its final conjunction with `bool(...)`; the
gate conditions and thresholds are unchanged. The failed job did not enter the
accident-chain trajectory. This source fix requires a fresh pin and independent
retry; no local tests or calculations were run.

## 2026-10-31 — moving-cylinder geometry tolerance

Two current-pin Hangang engine cases rejected the native cylinder volume at
the analytic slider-crank check. The check used a fixed 1e-10 relative bound,
which was tighter than the ReactorNet default relative tolerance of 1e-9. It
now compares the accepted volume residual against the configured solver budget
(`atol + rtol * |V_geometry|`) and includes native volume, geometric volume,
residual, and allowance in a rejection. The geometry consistency check remains
active; its numerical allowance now follows the caller's integration settings.
A fresh immutable Hangang pin is required. No local test or calculation was
run.

## 2026-10-31 — flowing CSTR accepted-state temperature view

Hangang current-pin case 1186364 reported a 0.0321 K difference between the
accepted gas temperature and the caller-visible surface phase after the native
integrator advanced. The first attempted synchronization through
`ExtensibleReactor.restore_surface_state(0)` produced a Cantera 3.2 direction
warning, and direct assignment to `Interface.T` failed because that property is
read-only (case 1186427, before integration). The adapter now restores the gas
view from the accepted reactor state and accesses the connected
`ReactorSurface.phase` property, whose Python binding invokes native
`restoreState()`, then strictly checks the reactor, gas, and surface
temperatures. This uses Cantera's native surface restore path and does not
overwrite accepted integrator state or coverages. It remains unverified until a
fresh immutable Hangang pin runs the CSTR contract. No local tests, imports or
calculations were run. API basis: [Cantera 3.2 Python binding](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/reactor.pyx)
and [ReactorSurface native implementation](https://cantera.org/3.2/cxx/df/ddb/ReactorSurface_8cpp_source.html).

## 2026-10-31 — open-cylinder moving-wall residual margin

Hangang current4 job 1186448 reached its native open-cylinder sample, then
rejected a slider-crank volume residual of `-9.36232e-13 m3` against the
configured `6.58499e-13 m3` geometry budget. The residual is small but above
the declared solver-scaled allowance, so the geometric invariant is retained.
ReactorNet now runs at one tenth of caller relative/absolute tolerances while
the public acceptance bound remains unchanged. This may cost more runtime and
must be evaluated on a fresh immutable Hangang pin; no local tests or
calculations were run.

## 2026-10-31 — GrInHy2 normalized CSV source header

Hangang current4 ingestion case 1186449 reached the first source reader and
rejected the exact tracked CSV header because the implementation compared
source labels directly with normalized API field names. The loader now checks
the six exact CSV labels (including `hydrogen_to_HPU_Nm3_h`) separately, then
maps the source ordered values to normalized `GrInHy2FlowSeries` fields. The
file hash, source rows, negative readings and unresolved Nm3 basis remain
strictly preserved. The README records the distinction. Fresh Hangang retry
required; no local tests or calculations were run.

## 2026-10-31 — source-bound core-flood power-law summary

Added an optional Corey-type empirical compression for one explicitly selected
Mendeley core-flood gas/branch/phase table. Caller-provided irreducible-water
and residual-gas saturations remain fixed inputs with an evidence ID; the fit
does not infer endpoints from observed extrema. It retains every source row ID,
endpoint permeability, exponent, fit method and residual metrics, and refuses
queries outside the source-observed saturation range. This summarizes already
reported derived relative-permeability values and is not an independently
qualified reservoir law. A synthetic Hangang contract is registered; no local
test or calculation was run.

## 2026-10-31 — accident consequence callback fixture binding

Current2 Hangang jobs 1186386 and 1186387 did not complete consequence
handoff or uncertainty rows: the callback integrity check detected fixture
callbacks whose captured mutable state changed during evaluation. The handoff
fixture now uses a module-level evaluator/result owner without a mutated
observation list. The uncertainty fixture uses a module-level result owner and
`partial` with a fixed per-row scale instead of a nested class/lambda closure.
Production freshness rules and consequence physics are unchanged. These
fixture-only changes require a fresh pin; no local tests or calculations were
run.

## 2026-10-31 — cylinder-wall state vector compatibility

Hangang current-pin case 1186370 failed while Cantera read the extensible
reactor state because assigning a tuple to a state-vector slice was treated as
one scalar value. The three wall state entries are now written individually as
floats. The energy equations and state ordering are unchanged. This source fix
requires a fresh immutable Hangang pin; no local tests or calculations were
run.

## 2026-10-31 — DataverseNO X044QK condition-matrix reader

Added a reader for the CC0 1.0 DataverseNO X044QK workbook attachment
`Matrix and H2 flow results.xlsx` (14,199 bytes; SHA-256
`c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`; publisher
MD5 `6c929ee530ac393ee8e76f6db2eff05c`). It preserves the 40 experiment rows,
source columns, formula/cached views and stable file/sheet/row identities. The
deferred Hangang contract checks the source fields and descriptive summary only.
The publisher says MFR is calculated from pressure; pressure basis and channel
calibration remain unresolved. Raw EXP_022 is missing, 39 pressure histories
and six video bundles remain unacquired, and no pressure/flow conversion or
dispersion validation is claimed. No local tests or calculations were run.

## 2026-10-31 — current5f catalytic heat handoff exception

Hangang jobs 1186522 and 1186523 stopped before case entry because scheduler
logs modified the immutable source tree. Jobs 1186526, 1186530 and 1186534
reached `cantera-catalytic-wall-heat-utility-handoff` and raised `NameError`:
the closed finite-reactor path referenced `flow_boundary`, which exists only in
the separate flowing-reactor path. The nonnegative gas-inventory check now
uses the closed path's declared `element_absolute_tolerance_mol` budget. This
fix requires the next immutable source capture and Hangang replay. It is a
software defect, not a failed physical-model qualification. No local model
tests or calculations were run.

## 2026-10-31 — solid-reaction heat-duty integration

Added a core-only bridge from an accepted finite solid-reaction trace to the
shared `HeatDuty` accounting API. It maps the producer's signed step heat
commands without rescaling, requires a contiguous same-clock window and common
caloric reference, and rechecks whole-system mass, elemental and enthalpy
budgets. Freshness retains the reaction kernel, kinetics, caloric provider and
steps. A deferred Hangang case checks the boundary contract only; utility
availability and heat-transfer performance are not inferred. No local tests or
calculations were run.

## 2026-10-31 — current5h adapter handoff failures

The immutable current5h source archive
`55d69728b9a34e0eab3027a6f558bfa5de2f84bbbe8599d3789b519780f3c4c3` passed its
1,127-entry source manifest. Independent jobs 1186595, 1186596 and 1186597
entered the BAM observation, reaction heat and reaction H2 source cases. BAM
source admission failed because its reader metadata SHA constant differed from
the exact staged/case-pinned record hash; this transcription is corrected.
Both solid-reaction adapters attempted nonexistent
`FiniteThermochemicalCycle._enthalpy`; they now use source-bound provider
enthalpies to reconstruct whole-system budgets. These are software defects, not
physical-model evidence. All three corrections require a newer immutable pin;
no local tests or calculations were run.

## 2026-10-31 — acoustic data checksum correction

The Zenodo 21355851 ZIP and record metadata were downloaded and hashed on
Hangang. ZIP SHA-256 is
`38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553`; metadata
SHA-256 is `1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`.
Both source pins were corrected in the loader, validation case, research
inventory and guide, then the checked bytes were promoted to the staged source
directory. The matching DOI/title/version/file list and publisher MD5 were
confirmed. `unzip -t` reported no archive errors and the exact Carey 1974
normal-H2 member required by the deferred case is present. No EOS diagnostic or
local model test has run yet.

## 2026-10-31 — current5i catalytic restore replay submitted

Current5i (`a6877cf9dd55c8a94e4b4ebf1a79b8eae62417f7`) is remotely pinned with
1,132 source entries, manifest SHA-256
`b905ef7c1cd474f92e8c7c3148ff4b2667948d75244525f2aea389a3240fef46`, and
archive SHA-256
`7b8c52e0429e9d9f076b7fca07ff9cf6f1a2e356c783da6373d8bd573ff060a5`.
All manifest entries verify. Catalytic heat handoff replay 1186610 passed with
accepted-state restoration: 20 interval heat-duty bins matched the native
wall-energy ledger and summed to `-0.0010711399253343593 J` into the process.
This verifies the Cantera-to-HeatDuty software boundary only; the wall is
imposed and utility availability is not modeled. No local tests or calculations
were run.

## 2026-10-31 — additional finite-source adapter routes and API audit

Added a solid-reaction product bridge that converts only accepted per-step
hydrogen takeoff into an `IntervalMassSource` and requires an explicit product
state and source-plane mapping. Added a slab-diffusion bridge that converts
accepted outward right-face molar flux into a finite mass source using explicit
area and carrier molar mass; reverse flow and un-evidenced atomic-H
recombination are rejected. Both preserve producer freshness and impose caller
clock/spatial/state assumptions rather than creating downstream pipe or
dispersion physics. Current5h exposed the solid-reaction provider API mismatch;
the provider-backed ledger now also validates exact kernel/provider identity,
species tuple ordering and caloric basis, plus positive finite state and
nonnegative inventory. Deferred contracts reject provider substitution and
species reordering. A fresh immutable pin is required. A bounded
static audit of 13 adapters found and fixed duplicate exports and repeated
exposure prose. No local tests or calculations were run.

## 2026-10-31 — current5m pin audit and recapture

The current5m snapshot (`60fdb…`) was preserved before transfer. Exact-case
audit found it omitted the newly registered TiO2 AQY and hydrogen-engine
metadata-gap cases; those cases remain useful evidence checks but were not
submitted against the incomplete pin. The BAM, solid-reaction, acoustic,
diffusion and SOE cases plus source metadata were present. A fresh current5n
will be built after the API export/index fixes and complete plan registration.
The BAM comparator was also added to `h2physics.adapters.__all__`, and the
public API/audit indexes now list solid-heat, solid-H2, diffusion, acoustic,
BAM, SOE and TiO2 boundaries. No tests, imports or calculations were run.

## 2026-10-31 — Hangang current5n BAM and diffusion case follow-up

The remotely verified current5n campaign established six deferred contract passes and two actionable case defects. BAM's publisher `Number of channels: 21` describes the 21 measurement signals; the `Time [s]` field is an additional coordinate, so the source parser now compares the declared number with header width minus the time column. The finite-source fixture now passes a time callback returning its previously authored fixed-flux `SlabBoundary`, matching the accepted `DiffusionSlab` interface. No numerical tolerances or physical bounds were relaxed. Retries require a new immutable source pin. See `PROGRESS.md` for exact archive, manifest and job receipts.

## 2026-10-31 — Current5q–5s deferred Hangang outcomes

Current5q gas-volume handoff 1186734 failed before science/model work because `CanteraFrozenGasProperties` referenced `_composition` before initialization. PCT/alkaline-bubble/carbon-H2 cases were refused by the scheduler QOS and produced no job IDs. The current5p radial shell API case 1186719 exposed an incorrect sign assertion in the synthetic case: positive left-to-right flow has positive accumulated inflow at the left and positive outflow at the right. The case and transport documentation now state that convention. Follow-up pin membership and hashes are documented in `PROGRESS.md`; the adapter correction and complete Bath source documentation are assigned to current5t.

## 2026-10-31 — Pump process handoff static control-flow correction

Static review of `pump_operation_to_process_connections()` found its result issuance/sealing block unreachable after `_boundary_content()` returned. The block was moved back inside the adapter function so a successful call returns a sealed source-bound `ConnectionTransfer` receipt. The pump trace retains receiver absolute pressure per accepted sample and includes it in the output digest. This remains source-only until a fresh Hangang pin runs `pump-operation-shaft-connection-boundary`; no local imports, tests or calculations were run.

## Finite relief source handoff (source-only)

Added a typed composition from inventory-closing accepted relief withdrawal receipts to the common finite interval source. It preserves exact native owner/sample lineage and rejects representative-state enthalpy mismatch. Registered deferred Hangang case
elief-withdrawal-finite-source-handoff under the existing finite-relief-lift profile. No local tests/calculations were run; cluster validation remains pending.


## Finite relief accepted-withdrawal source bridge (source-only)

Added `relief_source_from_accepted_withdrawals()` to connect accepted finite-relief inventory receipts to the shared interval source API. The adapter rechecks original adjacent samples and phase inventory balances, preserves interval mass/clock/property basis, and requires a caller-evidenced representative state to close the withdrawal enthalpy within an explicit tolerance. Registered deferred case `relief-withdrawal-finite-source-handoff` in the existing Hangang `finite-relief-lift` profile. This lane received static review only; no imports, local calculations or tests were run, and cluster execution remains pending.

## Shared radiation-to-radial-wall core and pool-fire route (source-only)

Factored surface projection, radial-wall execution and freshness checks into `RadiationRadialWallCore`. The HyRAM facade now delegates those shared responsibilities while retaining its own source-window and receiver geometry checks. Added `run_pool_fire_radial_wall()` to bind the selected native pool-fire receptor history to the same core, retaining exact source owner/clock/frame and requiring caller evidence for the receptor-to-surface projection and uniform radial applicability. Registered deferred case `pool-fire-radial-wall-handoff` under the already-discovered `pool-fire` profile. No tests/imports/calculations were run locally.

## Elastic fragment bound to conditional flight adapter (source-only)

Added `run_elastic_bound_fragment_flight()` to compose the existing pressure-loaded elastic-cylinder strain-energy speed ceiling with the conditional rigid-fragment flight integrator. It replays the ceiling from original geometry/load/material inputs, requires exact fragment mass identity, and checks both speed and kinetic energy before flight. First flight time must equal the declared event time; launch mapping remains caller-owned and evidenced. Deferred Hangang case `elastic-bound-fragment-flight-handoff` is registered in the existing fragment-trajectory case module. No local tests/imports/calculations were run.

## HELPR initiation to conditional fragment flight (source-only)

Added `run_vessel_failure_fragment_flight()` to bind the actual issued HELPR initiation pressure/time/clock/frame and shell dimensions to the existing elastic-bound fragment-flight facade. The caller explicitly supports the shell-to-cylinder geometry mapping, long-section length/end condition, elastic constants, fragment energy share and launch state. No breach, fragment generation or launch kinematics are inferred. Deferred case `vessel-failure-fragment-flight-handoff` is registered in `validation.cases.vessel_failure` under the existing HELPR-enabled `fracture-fatigue` profile. No local tests/imports/calculations were run.

Hangang discovery for the HELPR fragment route now uses a dedicated `validation.cases.vessel_failure_fragment_flight` module, avoiding execution of unrelated fracture-profile cases. `hangang_plan.py` adds the `fracture-fatigue` profile and injects `H2_HANGANG_HELPR_PACKAGES` as `native_packages` when configured. Source transfer remains pending next immutable pin.

## PV electrolysis batch to compressor inlet boundary (source-only)

Added `bind_electrolysis_compressor_inlet()` to bind an admitted PV electrolysis trace to existing `HydrogenRealFluidCompressionInputs`. It checks exact product P/T and CoolProp basis, the common source clock, declared withdrawal interval, and net produced-H2 mass availability. No intermediate pressure-control/conditioning, receiver depletion trajectory or compressor execution is introduced. Deferred case `pv-electrolysis-real-fluid-compressor-inlet-handoff` was added to the existing electrochemical handoff case module and the `pv-electrolysis` profile. Package export is left for shared capture to avoid overlapping edits. No local tests/imports/calculations were run.

## Synchronized fuel-cell coolant energy to HeatDuty (source-only)

Added `bind_cantera_fuel_cell_coolant_heat()` to expose the accepted cumulative stack coolant ledger through the shared thermal duty API. The adapter requires exact accepted time endpoints and retains the source sign convention, clock, energy reference, and native receipt. It does not infer recoverable waste heat or add a heat exchanger. Deferred case `cantera-fuel-cell-coolant-heat-duty-handoff` was added to the existing synchronized Cantera fuel-cell contract module/profile. Package export is left for shared capture. No local tests/imports/calculations were run.

## Finite hydride pressure history to vessel failure input (source-only)

Added `history_from_finite_hydride()` as a typed projection from accepted finite-bed H2 pressure states to the existing `VesselFailureHistory`. The API preserves absolute pressure, EOS source and basis, exact operation clock, snapshot ownership and caller-mapped shell temperatures. It requires shell/geometry/evidence identity matches and does not infer a wall field from solid temperature. `FiniteHydrideTrace.require_current()` rechecks retained provider states, and the HELPR history guard reconstructs the projection before failure analysis. Deferred case `finite-hydride-vessel-failure-history-handoff` is registered under the existing `finite-hydride` profile. No local tests, imports, or calculations were run; Hangang evaluation remains pending.

## 2026-10-31 — adsorption product to linepack composition

Implemented a typed adapter between accepted finite adsorption-vessel H2
product mass and the ideal-H2 lumped pipeline linepack inventory. The boundary
requires caller-provided process-clock mapping and hydrogen-basis evidence and
checks exact product species, molecular-mass basis and mass closure. Added a
deferred synthetic contract to the already-discovered adsorption delivery case
module, public API documentation and handoff notes. No local tests or scientific
calculations were run; Hangang execution is pending a fresh manifest-verified
source snapshot.

## Adsorption H2 outlet to finite-hydride gas port (source-only)

Added `bind_adsorption_to_finite_hydride()` to map the completed adsorption model's accepted H2 outlet bins onto the existing finite-hydride gas port. It preserves native interval times and cumulative mole increments, checks H2 molar-mass/property-basis identity, and requires a caller-provided gas state and enthalpy-closure evidence for every bin. Clock alignment and transfer hydraulics are explicit caller evidence; no valve, pressure-loss or transport law is inferred. Deferred case `adsorption-to-finite-hydride-gas-port-handoff` is in `validation/cases/adsorption_finite_hydride_port.py`, using the existing `finite-hydride` profile. API limits and accounting details are in `docs/ADSORPTION_FINITE_HYDRIDE_PORT.md`. Package exports and Hangang discovery registration are intentionally left for shared capture. No local tests, imports or calculations were run; Hangang execution is pending.

## Reliquefier product to native liquid separator inlet (source-only)

Added `bind_reliquefier_product_to_separator()` to expose collected, all-liquid reliquefier product as a native liquid `MassEnergyFlow` over its exact declared collection window. The bridge checks owner receipt freshness, exact property basis, clock alignment, receiver assignment, mass rate and product-state enthalpy; the native separator continues to own inventory, pressure and energy response. No line loss, flashing or conditioning is inferred. Deferred case `reliquefier-product-native-separator-liquid-inlet-handoff` is in `validation/cases/reliquefier_separator_inlet.py` using the existing `finite-transfer` profile. API limits are documented in `docs/RELIQUEFIER_SEPARATOR_INLET.md`. Exports and plan discovery are left for shared capture. No local tests, imports or calculations were run.

## Finite separator pressure history to HELPR (source-only)

Added `history_from_finite_separator()` to map exact accepted pure-H2 separator pressure/time rows into the existing HELPR vessel history. It binds absolute pressure basis, native source/property identity, exact clock and accepted liquid/vapor states; wall temperatures and external pressure remain caller-provided and evidence-bound. `vessel_failure.py` now replays this source-specific projection during HELPR history freshness checks. It adds no wall heat transfer, failure, breach or release physics. Deferred case `finite-separator-vessel-failure-history-handoff` is in `validation/cases/finite_separator_vessel_failure.py` under the existing `finite-transfer` profile. Details and limits are in `docs/FINITE_SEPARATOR_VESSEL_FAILURE.md`. Exports and Hangang discovery are left for shared capture. No local tests, imports or calculations were run.

## HyRAM irradiance to lumped thermal target (source-only)

Added `incident_heat_history_from_hyram_radiation()` to compose accepted HyRAM observer irradiance with the existing left-held incident heat boundary and lumped thermal-target solver. The source guard reissues the original observer/window projection; target surface mapping and any irradiance projection are explicit caller evidence. Target optical, material and heat-transfer inputs remain separately supplied. No view factor, transient fire, injury or failure physics is added. Deferred case `hyram-radiation-lumped-thermal-target-handoff` is in `validation/cases/hyram_thermal_target.py` under the existing `jet-fire-conservation` profile. API limitations are in `docs/HYRAM_LUMPED_THERMAL_TARGET.md`. Exports and plan discovery are left for shared capture. No tests, imports or calculations were run.

## Compressor to finite-hydride gas port (source-only)

Added a scoped coupling from an existing CoolProp HEOS pure-H2 compressor
result to the existing finite-hydride gas port. It checks receiver-basis
pressure, temperature, density, enthalpy and entropy against the accepted
compressor point; binds explicit caller clock, hydraulic transfer and state
projection evidence; and reports one held-flow interval's H2 mass and
enthalpy. The deferred Hangang contract also carries that port into the native
bed and checks the existing storage ledgers. No compressor, valve, line-flow,
or bed solver was duplicated. Local tests, imports and calculations were not
run; physical validation remains pending.

## 2026-10-31 — pinned-source syntax preflight on Hangang

The cluster case runner now applies Python's in-memory `compile()` to every
`src/h2physics/**/*.py` file in the pinned repository before importing the
selected validation case. The attempt report records the number of checked
package sources. This catches syntax defects that otherwise consume a scheduler
slot and fail before the case body, as happened to job 1187110. The preflight
does not import or execute those package modules and is not physical validation.
No local check or scientific case was run for this change; it awaits a fresh
Hangang source pin and execution.

## Finite-hydride desorption to mechanical compressor (source-only)

Added `bind_finite_hydride_to_compressor()` to connect exact outward H2
withdrawal and enthalpy from an accepted `FiniteHydrideTrace` to one original
real-fluid HEOS compressor result per interval. The adapter checks matching
provider release and property basis, selected accepted edge state, positive
compressor throughput, negative-into-bed source-ledger increments, energy
closure, unique process-window IDs, and caller clock/direct-transfer/state
evidence. The compressor input has no timestamps; no time is derived from run
ordering. Existing compressor and bed solvers remain unchanged. Deferred case
`finite-hydride-desorption-mechanical-compressor-handoff` is registered but
unexecuted. No local test, import, or calculation was run.

## HEOS compressor to isothermal linepack (source-only)

Added `charge_linepack_from_compressor()` to use the existing CoolProp HEOS
compressor receipt and isothermal ideal-H2 `IsothermalLinepackState.advance()`.
The bridge closes the interval mass ledger, requires compressor discharge
pressure above the final linepack pressure, and accepts only a receiver
`ThermoState` replayed at linepack pressure/fixed temperature. The signed inlet
conditioning-energy ledger must close against the source-to-conditioned H2
enthalpy difference. This does not create linepack stored-energy closure or
pipe/valve/heat-transfer physics. Deferred case registered and unrun; no local
test, import or calculation was performed.

## Licensed inventory ingestion and campaign preflight

Added a hash-pinned reader for Wasserstoffatlas `Bestand.csv`, with per-row source strings and lineage preserved, attribution based on the file-specific CC BY 4.0 declaration, and no inferred units/CRS or model validation claim. Its source-ingestion Hangang case awaits remote hash verification. The separate WSKBIJ summary-only source case is likewise awaiting remote copy receipt. The 5aq campaign preparation failure was a missing `dataclasses.field` import in `hfcev_fleet.py`; fixed locally, with no scheduler submission. See `docs/WASSERSTOFFATLAS_INVENTORY.md` and `docs/LARGE_SCALE_H2_EXPLOSION_SUMMARY.md`.

## Storage candidate schema decision

Reviewed the CC BY 4.0 Clashach H2 μCT dataset README and retained only the README as an ignored raw artifact with exact MD5/SHA-256 receipt. PNM pore/throat data are 16-bit image label volumes with known voxel scale and label ranges, but lack a direct current porous-reservoir input/measurement bridge. A source-gap case is registered; the larger pore/throat archives were not acquired.

## Leaky-coating source reader

Added source-specific typed traces for selected measured Pd membrane sorption channels under CC BY 4.0. It checks exact publisher/local hashes and retains clocks, mbar tokens, and separate UHV/feed signal semantics. The licensed measurements do not directly supply a calibrated solid concentration or absolute feed-pressure boundary, so no existing diffusion or hydride model was fitted. A deferred Hangang ingestion-only case is registered; remote stage receipt is pending.

## Conda environment diagnostic and finite-reservoir nozzle bridge — 2026-10-31

Confirmed the existing `h2physics-py312` Conda environment (Python 3.12.14) has the editable project plus CoolProp 8.0.0, Cantera 3.2.0, fluids 1.3.1, openpyxl 3.1.5, h5py 3.16.0, NumPy 2.5.3, SciPy 1.18.1 and pytest 9.2.0. Added `scripts/check_environment.py` with `core` and `research` profiles and an opt-in `--imports` mode; the `research` availability report completed successfully. The report distinguishes a missing distribution from an installed package that fails to import. This checks installation and importability only, not scientific behavior.

Integrated `FiniteReservoirNozzleCoupling` with the branched isothermal pipe-wave solver. The start-of-step nozzle mass rate is debited together with the signed endpoint Rusanov flux, the whole-network ledger includes cumulative nozzle loss, and source projection requires left-hold integration to reproduce the accepted loss ledger. Two Hangang contracts cover mass/source closure and EOS mapping rejection. All six modified Python sources passed local AST parsing after the final rate-cache edit; no local scientific calculation or test was run. The current immutable 5ad/e8 source pin predates this bridge; it is queued for inclusion in the next pin, not retrofitted into an archive already being transferred.

Regenerated `docs/PUBLIC_API_INDEX.md` using its AST-only generator: 327 Python modules and 1,682 public top-level definitions. Hangang's bounded 5ad transfer remains in progress; new model contracts await a later immutable pin and cluster execution.

## HyRAM finite transient-source receiving request — 2026-10-31

Prepared Request 037 after the host-side finite pipe-reservoir source bridge. It defines a direct Python receiving contract for an upstream-computed, already-debited time-varying H2 source, prohibits silently recomputing/replacing source flow, and distinguishes transient plume memory from independent steady snapshots. The request specifies clock/source-plane identity, mass gates, failure retention and acceptance contracts without copying HyRAM code or claiming that the present HyRAM version supports the requested mode. See `requests/037_hyram_transient_finite_source.md` and `docs/FINITE_PIPE_RESERVOIR_NOZZLE_SINK.md`.

## Public-tree data hygiene follow-up — 2026-10-31

The first `scripts/audit_public_tree.py` run identified two untracked forbidden-format files: the derived GrInHy2 CSV and the alkaline bubble publisher listing JSON. The derived CSV was moved to ignored `data/processed/grinhy2/` (32,736 bytes; SHA-256 `04cf4c65676bac11024cc35aaa83ce55c94165044108a17a89abc065a4f28612`), and both the source manifest and deferred-case relative path now point to that cache. The original Mendeley listing JSON and publisher prose README were moved to ignored `data/raw/`; all 35 file-list metadata entries were transcribed to `research/data/alkaline-bubble-observations-file-list.toml`. Its parsed count and summed size match the publisher listing (35 files, 375,513,822 bytes); the original response SHA-256 `6dfcf1e0c455ddf0320639ef15452a12b37ba18283dc665c0f70e772ec90b5f1` and README SHA-256 remain verified against the ignored originals. A repeat public-tree content-hygiene audit passed across 1,370 files. This gate does not determine copyright, license scope or redistribution rights.

## Transient gas-turbine shaft dynamics

Added `h2physics.combustion.integrate_shaft_transient()` for a single spool driven by caller-supplied turbine/compressor power histories and load torque. The solver advances the rotor kinetic-energy state and cumulative work channels together, retains energy residual and SciPy status, and terminates exactly at declared speed limits without clipping. This adds rotor inertia response to the previously steady Brayton/map levels; it does not derive boundary powers from component maps, close multiple spools, or model governor/generator control. Synthetic steady-balance and overspeed-event contracts are deferred to Hangang. Static Ruff/AST/diff checks only; no local scientific execution.
# 2026-10-31 — finite-capacity caloric pipe wall

Implemented a host-owned one-node finite wall thermal capacity around the
caloric Euler gas pipe model. The wrapper advances gas with a frozen wall state
per requested outer interval, then updates wall energy from the accepted gas
heat ledger and optional constant-UA ambient exchange. The immutable summary
replays energy, heat, wall provenance, EOS identity and geometry against its
run-issued gas traces. A synthetic Hangang case and API/catalog documentation
were registered. Only AST inventory and Ruff static checks were run; no
scientific model run or HPC submission was performed. The first-order split,
perfect-mix assumption, closed endpoint scope and lack of axial wall conduction
remain explicit limitations.

## Transient shaft Hangang outcome-contract correction — 2026-10-31

The deferred Brayton shaft case returned `ValidationOutcome` without its
required `accepted` field, so the harness rejected the outcome after the
scenario logic completed. The case now reports explicit acceptance, scenario
and termination diagnostics, and its declared synthetic limitations. A fresh
maximum-speed retry case is included in the already-discovered Hangang module.
Targeted Ruff and AST parsing passed; the scientific case was not run locally
and no HPC job was submitted.
# Two-vent layer oxygen-composition projection — 2026-11-01

Added `h2physics.adapters.layer_oxygen_projection.project_layer_oxygen()` as
an object-level composition bridge from the existing two-vent buoyant H2 layer.
It only handles H2 mixed with a caller-declared fixed dry-air carrier, computes
the upper-layer O2 mole-fraction series, and retains the original layer result
and exact timestamp tuple. It does not produce a homogeneous room result,
partial pressure, alarm decision, exposure-duration measure or human-response
prediction. The feature is registered as `implemented_unverified` under the
existing dispersion/facility-protection families, with a dedicated guide and
deferred synthetic Hangang/Nurion contract. Metadata inventory is 408 cases,
59 profiles and 111 modules. Ruff passed on the changed Python/plan files; no
scientific local calculation or case execution was performed. The feature is
not in immutable pin 5ak. It was included in verified pin 5al and its synthetic
composition contract passed Hangang job `1189682`; independent physical
validation remains open.

## Upper-layer oxygen-deficit sensor/alarm handoff — 2026-11-01

Added `h2physics.adapters.layer_oxygen_alarm_handoff` to project the retained
upper-layer oxygen trace to an explicitly referenced nonnegative deficit
signal, then reuse the existing first-order sensor and concentration-alarm
engines. The API keeps the layer trace and exact timestamps, requires explicit
clock/location applicability evidence and source/mode/episode identity, and
rechecks the issued sensor/alarm/trip chain for mutation. It models only the
upper-layer sensor location and adds no oxygen-room average, exposure duration
or human-response calculation. A synthetic contract and guide are registered;
no scientific local test or calculation ran. It is included in verified pin
5am; its corrected one-case script, generated from the exact remote tree, was
submitted as job `1189857` and passed its six-sample synthetic contract in
1.29 s. Clock/location mappings, caller-owned sensor/alarm settings, trip
evidence and context-change rejection passed. No field sensor or facility
qualification follows from this result.



## 2026-11-01 prioritized work 2–7

- Confirmed the repaired 5af trio had already passed on pin 5ag; retained earlier failure receipts and did not duplicate the run.
- Reconciled the PEM source cache against publisher and manifest checksums. The CC BY 4.0 source record, attribution, schema and known calibration/state gaps remain documented; raw cache is excluded from code snapshots.
- Added provider-neutral exact-grid receptor sampling with explicit metre axes, H2 mole-fraction values and source/frame/clock identity. It accepts exact coordinate matches only and does not interpolate or validate provider-specific extraction.
- Added alarm-to-finite-stroke command scheduling on the existing actuator model. Added Request032 receiver-boundary notes rather than creating a duplicate native mixture solver.
- Built and remotely verified a 1,449-entry base pin, then applied and verified a 17-file delta. Campaign generation found and fixed a Windows/POSIX path construction defect.
- Generated a three-case contract array. The first submission had an invalid default working directory; the corrected /scratch submission was refused by QOS with no job ID. No scientific case from this batch ran. Existing account jobs were left untouched.
- Static checks: targeted Ruff passed for new modules, plan and transfer helper. No local scientific tests or calculations were run.

## 2026-11-01 parallel implementation continuation

Three independent code lanes added (1) a reduced two-vent upper-layer H2 to existing sensor/alarm handoff, (2) a source-bound PEM current-ripple IV to shared `HydrogenStack` diagnostic bridge, and (3) a HyRAM high-pressure gas release-rate ledger for an existing ignition-risk binding. These reuse existing model owners and preserve caller evidence; they do not add duplicate solvers, fitted source parameters, protection credit or new risk calculations. Their module APIs, dedicated docs, synthetic Hangang contracts, catalog notes, package exports, and plan registrations were integrated centrally.

The first metadata-only plan import exposed an existing class-scope dataclass `field` shadowing collision in the preferred dispersion alarm handoff. Renaming the imported helper to `dataclass_field` restored module import. Re-running metadata discovery returned 319 cases and included all six current priority contracts. No scientific execution occurred locally. A fresh source pin and explicit raw PEM staging still precede remote execution; the last live queue snapshot showed five existing jobs running and the immediately preceding batch was QOS-rejected without a job ID.
## Meter-bound electrochemical hydrogen storage round trip — 2026-11-01

Added `h2physics.adapters.account_electrochemical_storage_round_trip()` to compose the existing admitted electrolysis-to-fuel-cell H2 inventory receipt with integrated charge/discharge electrical meters. It checks meter identity seals, one physical clock, common electrical basis and system boundary, complete sequential trace windows, and meter-to-native-stack energy bounds. Boundary-meter and stack-only electricity remain separate outputs; the H2 production/delivery/use/remnant/loss ledger is inherited from the prior handoff. The API does not infer compression, power-electronics or auxiliary loads. It is registered as a deferred Hangang contract and remains unexecuted. Independent logical review found and fixed post-issue meter metadata mutation not covered by the initial receipt seal. Targeted Ruff, syntax compilation and scoped diff checks passed; no scientific tests or calculations ran.

## AEM electrolysis crossover source ingestion — 2026-11-01

Acquired Zenodo record 10.5281/zenodo.20068087 v1 under CC BY 4.0 with its official metadata snapshot, publisher MD5 and local SHA-256. The source-bound reader preserves raw workbook cell values, formulas, types, formats, sheet order, dimensions and A1 lineage; it assigns no units and performs no fitting. Its ingestion-only deferred case checks source identity/schema, not polarization or crossover physics. AEM data is kept outside version control. The same workbook bytes were staged to Hangang scratch through the existing wrapper, where final SHA-256 matched. Local checks were limited to provenance, workbook structure, metadata discovery and lint; no physical model was run.

## 2026-11-01 CoolProp calorimetry correction

The finite illustrative fuel-cell example now evaluates state enthalpies with
`CoolPropMolarEnthalpy`, reusing native HEOS states and explicit reference offsets.
Both water phases share the liquid formation reference at 298.15 K, 101325 Pa
(-285830 J/mol, NIST Chemistry WebBook); CoolProp supplies the vaporization
enthalpy. Adding a vapor formation offset to a liquid EOS reference would double
count that difference and is rejected by the revised construction. Declared
species phases are checked against the actual CoolProp phase after each flash;
property bounds reject extrapolation. Reaction bookkeeping uses one consistent
H/O atomic mass basis derived from native H2/O2 molar masses; native Water EOS
molar enthalpy retains its own library molar basis. This distinction is explicit.
The reversible electrical energy and ohmic loss remain authored example inputs,
so this example does not establish device thermodynamics or polarization validity.

Under the user's newer local-fallback instruction, local Conda execution passed
finite Faraday/mass accounting (mass residual 9.74e-21 kg), energy accounting
(residual 0 J; heat into -69.3151031783 J), and three incompatible reaction
reference/phase/enthalpy rejection cases. Vapor operation at 410 K executed with
splitting enthalpy 243089.806795 J/mol H2. These are numerical/component checks,
not measured-data validation. Hangang shared-wrapper observation confirmed five
existing running jobs; none was changed or newly submitted at the observed cap.
Programme effort remains approximately 30–40%; 56/82 catalog status is separate.

Primary references: https://coolprop.org/coolprop/LowLevelAPI.html and
https://webbook.nist.gov/cgi/cbook.cgi?Name=water&cTC=on&cTG=on .

Local H2 handoff and metered round-trip contracts also passed after the CoolProp
change: produced 0.0267654306283 mol H2, consumed 0.000621856179376 mol,
charge meter 7548.38178429 J and discharge meter 102.6 J. The illustrative
ratio 0.0135923172585 reflects partial batch consumption and authored loads;
it is not a measured or complete-cycle storage efficiency.

Six finite fuel-cell cases passed locally after replacing fixed caloric
expectations with native CoolProp enthalpy differences: charge, heat, feeds,
depletion, idle/domain guards and finite source. Feed conditioning was
-1.74218238655 J. The binding case exposed a fixture assumption that cached
arrays could be made writable; it now accepts immediate NumPy write rejection
as well as receipt rejection of an actually mutable altered array.

The repaired binding case then passed locally with six original-result
mutation rejections. All seven non-Cantera finite fuel-cell cases now have
local component-contract execution evidence for this revision. The separate
native Cantera case and independent measured-data qualification remain pending.


## 2026-11-01 CoolProp production and measured acoustic replay

The PV-electrolysis example now uses CoolProp for Water/Hydrogen/Oxygen state
enthalpies. Its water reference offset preserves native H2/O2 absolute zeros
and gives liquid-water splitting H=285830 J/mol at 298.15 K, 101325 Pa. Local
PV execution and the metered H2 round-trip contract passed after the change;
Gibbs energy and electrical-loss parameters remain authored example inputs.
The native H2 product-port enthalpy consistency gate remains satisfied.

The acoustic replay first rejected a local metadata snapshot with SHA-256
6f567113990ab4a2dff5436045dd39590f108dd93b7a51671cf76a61f35e6861.
The original metadata was recovered from Hangang through the approved shared
wrapper and verified against the existing 1d83651f...ee3ad pin before restoring
local bytes; the mismatched snapshot remains in the ignored source cache.
No source hash acceptance rule was relaxed.

Local source-bound HEOS replay now covers 761 of 1027 literature rows across
30 source members; 266 rows are explicitly excluded for missing/non-positive
conditions, unsupported states or unspecified/intermediate spin composition.
See HYDROGEN_ACOUSTIC_REPLAY.md for per-member residuals and exclusions.
The exact Carey normal-H2 subset has 18 comparisons, zero exclusions, RMS
error 8.69721755526 m/s and maximum absolute relative error 1.65935450273%,
over 291.08–299.19 K and 0.146–11.02 MPa. These measured literature comparisons
have unresolved EOS-development overlap and are diagnostics, not independent
validation. No universal accuracy threshold was imposed. The registered case
now reports quantitative residuals and rejects a zero-comparison run.

Reproduce with Python 3.12 and the thermo extra:
`python scripts/compare_hydrogen_acoustics.py --output docs/HYDROGEN_ACOUSTIC_REPLAY.md`.
Raw data remain outside Git. Source attribution, hashes and CoolProp version
are included in the aggregate-only report. Hangang still showed five running
pre-existing jobs; none was changed or submitted. Overall estimate remains
30–40%; catalog implementation status remains separate at 56/82.


Acoustic diagnostic follow-up: the largest VanDael-1965 normal-H2 discrepancy
is 65.6881% and its native PT flash returns gas. Other rows in that file flash
as liquid. Source phase/metastability, measurement provenance and transcription
remain unresolved; no row was deleted or corrected. The report now identifies
each compared member's largest-error row and its native phase to support a
source-specific phase review. This discrepancy prevents an accuracy claim for
the full set and is retained as an open scientific issue.


## 2026-11-01 acoustic phase lineage

`AcousticEOSPoint` now retains the source-declared phase and actual CoolProp
PT phase. Its `phase_matches` classifies liquid and gas families, including
CoolProp's subcritical-temperature/high-pressure `supercritical_liquid` and
supercritical-temperature/low-pressure `supercritical_gas` labels; unsupported
source states and fully supercritical states remain unclassified. The report
retains all 761 comparisons and flags phase conflicts without modifying rows.
The full replay was executed again after the phase fields were introduced.

The pinned VanDael liquid row loop-1:row-28 has source pressure 0.411535% below
normal-H2 saturation pressure at its stated temperature, and the native PT
flash selects gas. A separate registered diagnostic checks that the liquid
source label, gas EOS label and 65.6881% residual are all preserved together.
No pressure correction or forced metastable liquid calculation is applied.
This isolates a phase-selection conflict but does not establish whether source
rounding, transcription, experimental state or EOS saturation accuracy caused it.
The API guide, source guide and aggregate replay retain this open scientific issue.


The phase-family diagnostic passed locally after recognizing the documented
CoolProp liquid-like/gas-like labels: the VanDael member retains 175 compared
rows and exactly one explicit liquid/gas conflict. The 0.411535% below-saturation
pressure distance is diagnostic only; source values remain untouched. Targeted
Ruff passed for the adapter, registered case and aggregate report generator.


## 2026-11-01 finite adsorption CoolProp migration

The 90/10 H2/N2 finite adsorption-vessel example now uses the existing
GasComposition/CoolPropMixtureProperties HEOS owner. The authored ideal density
and zero enthalpy/internal-energy/entropy provider was removed; native H2/N2
molar masses are used. The adsorption equilibrium is still an authored fixture
and does not establish material or vessel performance validation.

All nine existing finite-vessel contracts passed locally after this migration.
The 10-to-1 MPa delivery example gives 311.22523700808125 mol H2, and the 5 MPa
pressure inverse has a 2.55795384874e-13 mol inventory residual. Void volume
checks now use a numerical tolerance; owner binding verifies both immutable
native identity rejection and mutation rejection through a mutable metadata view.
Uncertainty cases yielded reported sigma 0.42 mol, independent sigma
0.469574275275 mol and covariance sigma 0.63 mol, with unjustified interpolation
and unqualified propagated-array inputs rejected.

These tests exposed an existing, independent production provenance defect:
snapshot() collected source IDs but did not return them as uncertainty source
IDs in the observation path. It now preserves the sorted source/dependence IDs;
the uncertainty-lineage case passed after the correction. Targeted Ruff and
scoped whitespace checks passed. No independent adsorbent measurements were
introduced. Source/model status and rough overall progress remain unchanged
(approximately 30–40%; catalog implementation classes 56/82).

The AST API index was regenerated: 360 modules, 1802 public definitions. The
legacy Nurion metadata inventory remains 413 cases, 59 profiles, 114 modules;
it does not include all Hangang-only source-data cases. The new acoustic phase
diagnostic is registered in the active Hangang plan with staged source paths.


## 2026-11-01 pinned Hangang continuation

A fresh worktree snapshot was verified locally with base revision
1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738 and source manifest
78e727dd64822c35a6a530f560ec616d6ef994b5ca2aea7be4f5c9b56be01a71.
It contains 1494 manifest entries; source.tar.gz is 14404933 bytes with SHA-256
a27673d8ce279280867f2a2ab1115fc4c4f21b35d2dae334ecb874558ed7de25.
The archive is under the local external staging directory
hangang-20261101-coolprop-acoustics-03. Shared-wrapper transfer to
/scratch/CLUSTER_USER/h2physics-jobs/verified-coolprop-78e727dd is in progress,
with per-part SHA checks; the last observed progress was 25/721 parts.
No full remote-manifest verification or new submitted-job receipt exists yet.
A selected eight-case campaign is being generated against this exact snapshot.
These execution pins do not cover later live-worktree corrections.

Parallel local PV regression checked 13 cases: 11 passed, 2 exposed implementation
failures requiring correction. Zero effective irradiance entered the native
De Soto scalar division path; the host adapter must preserve the native
zero-input limit. The finite-process error wrapper also discarded typed
unresolved-Faradaic-loss failure metadata. Both are under active correction,
with scientific and immutable-caloric identity regressions required afterwards.
The earlier passing baseline does not prove these boundary paths correct.
The current Hangang queue observation still showed five pre-existing running
jobs; no unrelated jobs were modified. Overall estimate remains 30–40%.


Campaign generation against source pin 78e727dd rejected three requested IDs:
pv-baseline, fuel-cell-finite-charge and fuel-cell-isothermal-heat. Inspection
showed that the active Hangang plan omitted the existing base PV/fuel-cell
case modules and the fuel-cell profile. They are now added in the live plan.
This is a live-worktree correction requiring a new pin/delta before execution;
the already transferring 78e727dd snapshot is preserved unchanged. No PBS
submission or validation pass is inferred from the failed generation.

The two PV production defects were corrected and their focused replays passed:
dark returns blocked-insufficient-voltage and isolation returns isolated;
unresolved Faradaic fraction and the original failure code/energy-path survive
the finite-run wrapper. Native pvlib source is unchanged. The caloric owner
signature now includes species, fluids, offsets, bounds, backend/version,
method and native-state pointers. A full 13-case regression including nine
caloric-definition mutation checks is still running; it is not yet a pass.
The full source transfer has reached 100/721 SHA-verified chunks. Development
continues independently; remote manifest verification and submission remain pending.


The full corrected PV regression subsequently completed: all 13 cases passed,
including nine caloric-definition mutation rejection paths in original-result
admission. Maximum caloric residual was 1.82e-12 J, DC residual 1.41e-10 J and
mass residual 9.89e-19 kg. These are component/software checks with authored
electrical parameters, not measured plant qualification. The earlier two
failures are resolved in the live source and need the newer execution pin.


## 2026-11-01 coupling verification and transfer reduction

Verified the local 46209831 source base against all 1471 manifest members
without failures. The full 14.4 MB transfer was intentionally terminated at
175/721 verified parts to reduce transfer overhead; this was an optimization,
not an inferred connection failure. Partial chunks remain isolated in incoming
storage. A direct delta from the already verified remote 46209831 tree contains
81 changed files, no deletions, and is 848062 bytes, reducing transfer bytes by
approximately 94%. Its target manifest is
025746875ba33bf767d4eda2ba7e77da18e226d1cd6e3199d1aad85cb29fbc5e;
archive SHA-256 is
65289073009ba775d1c279a12a03a727b254e90a80539af2e7b8315cc8de649e.
Transfer/application uses four shared-wrapper workers and a fresh destination;
full remote verification remains pending. Later live edits need a further delta.

Local coupling execution passed production-to-fuel-cell inventory, compressor
inlet projection and metered round-trip accounting. The explicit ideal-linepack
feed fixture now maps the receiver inlet separately with CoolProp at the cell
boundary, preserving the ideal source owner's density basis. It passed with
zero energy residual and explicit conditioning/reference inputs. The production
H2 species phase now uses the canonical gas descriptor expected by the public
coupling contracts; property-library identity remains in the caloric reference.

The electrolysis-to-linepack charge replay exposed an existing production bug:
require_current treated the tuple returned by _derive as a receipt object.
It now maps every returned value to its receipt field, including the pressure
margin, and rechecks time boundaries from the derived ledger. Its replay passed:
transferred H2=0.0262301220158 mol, mass residual 2.71e-20 kg and energy residual
0 J. Invalid loss, clocks, reference mappings, nonclosing energy and receipt
reissuance were rejected. The fixture's subtraction equality uses a declared
floating-point tolerance. These are synthetic component checks, not facility
validation. The direct native real-gas source/feed route is being implemented
with the existing EOS owner and independently integrated test-path enthalpy.


## 2026-11-01 native real-gas linepack/fuel-cell composition

Added RealGasLinepackSourceHandoff and advance_real_gas_linepack_to_source,
reusing RealGasLinepackState, CoolPropIsothermalEOS and CoolPropProperties.
The source receipt retains native EOS/property definitions, exact port masses,
clock, held temperature and pressure endpoints. It checks representative-state
native density/caloric/transport values. The existing fuel-cell feed adapter
now accepts both issued ideal and issued real-gas source receipts, with the
same explicit integrated-energy/reference/conditioning ledger. Native inlet
pressure roundoff is checked before using the exact declared cell pressure.
No extra EOS, regulator, pipe momentum or conditioning solver is introduced.
See REAL_GAS_LINEPACK_FUEL_CELL.md. Public exports and Hangang case registration
are present; the catalogue retains the existing equipment.gas_pipe family.

The new real-gas end-to-end local case passed using 0.2 kg withdrawal from a
5 MPa, 320 K, 2 m3 inventory: final P=4.860514241 MPa; cell feed=99.2122546977
mol H2. Test-side independent quadrature of the prescribed withdrawal path
through the existing EOS and CoolProp gives source enthalpy 853864.135765904 J
with quadrature error estimate 9.48e-9 J. Mass residual is 1.67e-16 kg and feed
energy residual is 1.46e-11 J. These are numerical/component results using an
authored schedule, not measured-data validation. The initial run included
seven negative paths; a final eleven-path mutation/input regression and the
existing ideal-linepack regression are still running. Do not infer their pass
from the initial result. The three new/changed implementation files are frozen
for the next source pin. Current full-programme estimate remains 30–40%.


The final native real-gas case passed with eleven invalid-state, clock, energy,
clone and provider/callable/ledger/evidence mutation rejections. The existing
ideal-feed regression also passed after the common feed-pressure roundoff guard;
its energy residual is 0 J. Targeted Ruff and scoped diff checks passed.
The public API index is now 361 modules / 1804 definitions; Hangang metadata
contains exactly one new real-gas feed case and no missing profile definitions.

The direct 848062-byte delta was applied remotely and fully verified at
/scratch/CLUSTER_USER/h2physics-jobs/verified-coolprop-02574687, manifest
025746875ba33bf767d4eda2ba7e77da18e226d1cd6e3199d1aad85cb29fbc5e.
This is a source-integrity receipt, not job execution. The new real-gas API,
later coupling repairs and their documentation postdate that pin and require
the next delta. Local reconstruction of the exact 02574687 tree is running to
support that small follow-up delta and reproducible campaign generation.
Overall progress remains a rough 30–40%; implementation classes 56/82 remain
separate from independent measured-data validation.


## 2026-11-01 independent coupling review and final guards

An independent read-only review identified two physical/provenance gaps in the
common feed handoff. A source with known spin composition could previously be
mapped to a different or unspecified spin, and caller origin could relabel a
synthetic source as measured. The adapter now requires a known source spin to
match the conditioned inlet spin and preserves the source origin exactly.
Unknown-spin ideal reference sources keep their explicit legacy path. No
spin-conversion model or substitute measurement evidence is inferred.

The final real-gas replay passed fifteen invalid-boundary/mutation tests,
including actual CoolProp ParaHydrogen inlet, unspecified inlet spin, inlet
pressure mismatch and synthetic-to-measured origin rejection. The ideal-feed
regression also passed. Mass residual remains 1.67e-16 kg, feed energy residual
1.46e-11 J. Ruff and scoped diff checks passed. No measured-data qualification
is claimed. Implementation files are frozen for the next delta.

The exact local reconstruction of remote source 02574687 is verified after
copying only manifest-declared members from the older base; the first attempt
had rejected extra local files rather than weakening complete-tree verification.
An eight-case campaign was generated against the exact source/plan pin, with
plan SHA 5e4a364a91d5a4f68c217ffa211ccbe162b28d07eb208d94cfe14a27d132af03.
It is split into 3/3/2-case arrays to keep each submission bounded, and explicitly
exports the staged AEM source path so runtime plan parameters match generation.
Staging/syntax verification is in progress; no new scheduler job is claimed.
Latest queue query showed five existing running jobs, all left untouched.
Overall programme estimate remains 30–40%; numerical contracts and source
integrity checks are tracked separately from independent data validation.


## 2026-11-01 staged CoolProp/acoustic campaign

The exact 02574687 source and plan produced eight selected cases, split into
bounded arrays 1–3, 4–6 and 7–8. Runtime scripts explicitly export the staged
AEM data path to preserve the generation-time source parameters. All three
scripts were staged through the existing shared CPU wrapper, SHA-256 checked,
and passed remote bash -n:

- campaigns/h2cp0257a.pbs: 3c72b18c140a396883cc5ca79b0ad9daeaf6ca7a9863fe1b1701af6abfca6dcc
- campaigns/h2cp0257b.pbs: 3bb3ec1cda6a912897903bdce448c6b21e3fa8bfb24a29396e41fade9e3edcc4
- campaigns/h2cp0257c.pbs: 96528b44a2eb2a89ed1a4e8b16cc8b24dcd425a72b35f8dec383fbba3c72746d

Paths are relative to /scratch/CLUSTER_USER/h2physics-jobs. The latest queue read
still shows five existing running user jobs; no new job was submitted and none
was modified. Source staging and syntax checks are not case execution results.
The newest real-gas API/guards are being packaged separately from 02574687;
that earlier campaign does not execute the later API.

An independence review record now isolates the Nguyen-2024 acoustic member:
research/hydrogen_acoustic_independence.toml. The primary publisher describes
new measured normal-H2 data and a newer EOS, while the installed CoolProp fluid
metadata reports Leachman-JPCRD-2009. The temporal/model distinction makes
these measurements a candidate external comparison for the older EOS; it does
not independently validate the newer model fitted in the same publication.
The 57-row replay has RMS residual 3.45030441 m/s and maximum absolute relative
error 0.444311708%. Source-table/uncertainty and coefficient-history checks
remain pending, and validation_qualified remains false. Thermophysical EOS
coefficients will not be transcribed into a duplicate local implementation.


Latest code is pinned in the 16-file follow-up delta (652167 bytes; archive
SHA-256 24601fbd74bcc2a7cafdbf3374d82c4de9a2c5cfb353a6f00e21a8d75b763022).
It transitions source manifest 025746875ba33bf767d4eda2ba7e77da18e226d1cd6e3199d1aad85cb29fbc5e
to 7195212fd0e102b81cc1b484457f10341e79ffdf06bb05e283912be65f7b467a.
Shared-wrapper transfer/application to verified-realgas-7195212f is running;
no final remote receipt exists yet. Observe the current transfer rather than
starting another copy. The source-only hygiene audit passed for 1498 files.


## 2026-11-01 primary acoustic table and uncertainty audit

The independently accessible CC BY 4.0 Nguyen-2024 manuscript was acquired to
the ignored raw cache (2379686 bytes; SHA-256
718f08874e2881beeebd5d5067b8a847a131ed2bd4082ffa7a7dc6fb049bef90).
Table 4 headings, units and two-column layout were visually inspected. The new
source audit script verifies that all 57 compiled T/p/w triplets exactly match
the primary table and attaches its reported expanded sound-speed uncertainties
(k=2) for diagnostics. No manuscript, raw table or copied source text is included
in the public tree. The aggregate report is NGUYEN_ACOUSTIC_SOURCE_AUDIT.md.

Only 19/57 native CoolProp residuals fall within the experimental expanded
uncertainty; the largest |residual|/U(w) is 9.78707615045. Thus table integrity
passed, but matching measurement-uncertainty accuracy is not established.
Correlated experimental errors, EOS model uncertainty and coefficient revision
history remain unresolved. No universal accuracy threshold or fit is inferred.
The research record now closes the primary-table and coverage-factor checks;
validation_qualified remains false. Reproduce the audit with the thermo/data
runtime and pdfplumber, passing the ignored document path and public report path.

The latest real-gas delta transfer terminated with wrapper exit 255 before a
verified destination receipt. A separate required-wrapper hostname/whoami check
returned 'No usable cpu shared connection'; no new connection or authentication
was attempted. Manual user reconnection was requested. Remote work is stopped
until the user restores READY cpu; partial incoming chunks are preserved for
hash-checked resume. Local source analysis continues. Transfer error reporting
now omits full base64 command payloads and keeps a bounded wrapper error message.

## 2026-11-01 table qualification and shared caloric binding

Corrected the GasTable issuer from positional to named fields and retained
per-property errors/timing/counts in its executed case result. All three table
cases passed; detailed results and workload limitations are recorded in
THERMO_ACCELERATION_QUALIFICATION.md. Added coolprop_carrier_caloric and native
definition signatures so fuel-cell callers reuse a common native ownership
probe. Heat accounting and eleven binding/backend guards passed. The example
now identifies its actual normal-H2 spin. Latest restart actions are summarized
at the top of HANDOFF.md. No new remote login or job submission was attempted.

An additional H2/O2/water molar-enthalpy probe at 90 MPa, 320 K was rejected
by a native melting-line domain check. It is not a passing extension of the
reaction provider envelope and is distinct from the qualified pure-H2 gas
table. The provider retains the native error and does not extrapolate through
a substitute EOS. The AST public index now counts 361 modules and 1805 public
definitions. No new remote session or scheduler job was attempted.

The separate 5 MPa, 320 K H2/O2/water direct-HEOS probe did execute and
returned finite molar enthalpies after the gas/supercritical and liquid-like
phase classification correction. The example reports its actual normal-H2
spin and its finite fuel-cell energy residual remained 0 J. This pointwise
check does not extend the declared example pressure envelope automatically.

## 2026-11-01 storage cold import and HEOS refinement

Fixed the storage product-delivery/adapters circular import without relaxing
its runtime concrete delivery check. Four fresh-interpreter imports passed
(pytest, 108.32 s). The three prior porous-reservoir cases and a new dynamic
HEOS injection/refinement case all passed from a cold process. The native
solver is unchanged; complete authored inputs and measured convergence/mass
residuals are recorded in POROUS_RESERVOIR.md. No site data were fitted.

## 2026-11-01 held-current inventory event

Added run_fuel_cell_until_reserve and its issued request/prefix/native-trace
receipt. The existing finite owner executes the localized prefix once; complete
start-boundary feeds, pre-withdrawal order and original source bindings are
preserved. Positive-time H2/O2/tie events, zero reserves, idle/horizon limits,
eight rejection paths and retained requested-versus-consumed source allocation
passed. The core driver failure policy is unchanged. FUEL_CELL_INVENTORY_EVENT.md
records inputs, floating endpoint policy, actual times/residuals and scope.
Live native ReactorNet depletion events remain open.

Integrated event exports/plan/docs and regenerated the model/API inventories.
Active Hangang metadata contains 349 cases, including the new held-command
event and HEOS porous-refinement cases, with no missing profiles. The public
index has 362 modules and 1807 definitions. Fresh-interpreter import regression
was rerun after export changes and passed 4/4 in 88.53 s. Targeted Ruff passed.
New local code remains outside the last accepted remote source pin; remote
access awaits the user-restored shared connection.

## 2026-11-01 native safety/caloric checks and status update

Finite-relief-lift cases passed 10/10 after correcting a brittle failure-text
fixture; actual native revision/hash and scope are in FINITE_RELIEF_LIFT.md.
Cantera 3.2 native caloric/chemical-potential fuel-cell execution passed with
1.14e-13 J enthalpy/energy residual scale; see FINITE_FUEL_CELL.md.
The defined porous-reservoir numerical level is now marked implemented after
its four local analytic/native/refinement cases passed. Catalog labels are
20 implemented, 37 native-adapter-verified and 25 implemented-unverified:
57/82 classified (about 70%), separate from the 30–40% whole-programme estimate.
The generated legacy case inventory is 414/59 profiles/114 modules.

The two caloric finite-reservoir/nozzle cases were newly executed and did
not pass: the positive pressure-jump case reached a rejected two-phase pipe
primitive, while an oversized-opening negative test reached a temperature
domain rejection before its intended mass-floor rejection. Read-only
diagnosis identified a right closed-wall Rusanov orientation defect: the
end face used reflected/inside ordering intended for the start face, reversing
the dissipative momentum term. Correction and an endpoint-orientation
regression are in progress, retaining the original pressure jump, CFL and
phase/domain gates. These two cases remain unresolved until re-executed.


## 2026-11-01 completed public-data replay

The full local four-experiment, three-bin-width PRESLHY replay completed with
exit 0. Source archive/workbook identities were checked by the existing script,
all twelve endpoint diagnostics returned, and the conditional fitting/held-out
report was regenerated at research/discha_inventory_comparison.md.
The fitted shared effective-area factor is 0.611074310718; fitting RMSE is
0.0226498819126 and held-out RMSE is 0.00361222122091 of initial-window inventory.
Held-out maximum absolute error is 0.00703731797345. The original train/test
fingerprints and experiment separation remain unchanged; the new values closely
reproduce the prior recorded comparison. Current code hashes are in the report.

This is conditional inventory/nozzle consistency: both reconstructed inventory
and nominal nozzle flow use the same measured P/T and native EOS. Temperature
is observed forcing and not a predicted tank-energy response. Therefore the
0.3612% normalized held-out RMSE is not independent flow accuracy, a universal
flow coefficient or complete blowdown qualification. Measurement uncertainties,
spatial thermal representativeness and independent flow metrology remain open.
The replay is finished; its previous source-file freeze can be released.


## 2026-11-01 local compartment and concentration verification

Read-only local Conda execution completed ten existing contracts without
failure: fixed-state compartment mixing, two-vent hydrogen layer, dry-air O2
projection, layer O2 sensor/alarm, three oxygen source/issuer/window metadata
contracts, native Cantera static-room O2 alarm, threshold-deficit integration,
and layer H2 alarm. No model or case files were modified for this campaign.

The actual two-room species transfer had external H2 input 0.2 mol, exhaust
2.67852619896e-9 mol, maximum H2 balance residual 7.43215038857e-18 mol and
carrier residual 1.17600373883e-13 mol. An independently evaluated one-room
closed-form solution differed by 4.16333634234e-17 mole fraction; constant-rate
coarse/fine matrix-exponential time partitions differed by 2.77555756156e-17.
These verify the existing ideal, fixed-total-molar-stock balance model. They
are not an alternative fluid EOS or real-fluid property qualification.

The 600 s layer run had maximum H2 mass residual 1.57859836314e-16 kg and
vent continuity residual 3.46944695195e-17 kg/s. Its final interface was
2.63514875893 m with upper H2 mole fraction 0.00195055776255. Separate 20 s
RK4 runs at 0.5/0.25/0.125 s gave successive-difference ratios 16.7328 for
interface height, 16.3007 for H2 mole fraction and 16.3854 for cumulative H2
exhaust, consistent with fourth-order numerical convergence. Finest-run mass
residual was 6.07153216592e-18 kg. Prescribed conditions and reduced-order
assumptions remain explicit; no independent measured-data validation follows.

Layer O2 and H2 sampled alarms tripped at 0.4 and 0.25 s respectively. The
Cantera room case retained static O2=0.15 and deficit=0.0595 with trip at 0.4 s;
it did not validate transient oxygen displacement. Digest/issuer/window cases
are metadata-only. The threshold integral 0.025 mole-fraction seconds is a
piecewise-linear mathematical metric, not a human-response or facility result.
No permanent cases were added; current implementation priority remains native
CoolProp thermophysical integration.


## 2026-11-01 caloric-network wall and nozzle ledger corrections

Executed finite-relief-lift contracts using separately installed reviewed LH2DT
revision b2f276333c1b1793c39f25763703d196d36742ec. Actual native source SHA-256
5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 matched the
recorded pin. Nine cases passed initially. The remaining failure-prefix case
used an obsolete exact ambient-error string; its check now retains ValueError,
ambient/temperature/positive meaning, original cause identity, native owner,
accepted state, histories and clock. Its replay passed with one accepted
interval, two native trials and accepted time 5.005 s. These sampled lift cases
use actual CoolProp nozzle/native protection but prescribed synthetic pressure
and phase-stock points; the failure-prefix case enters actual native tank
integration and then rejects an invalid later boundary. They are not device
validation.

The subsequent actual caloric tank/pipe/nozzle run exposed two independent
network defects. Closed right-wall ghost arguments had the left-wall order,
which reversed the dissipative momentum sign and led to unsupported cold pipe
states. The end wall now uses inside/reflected order while the start uses
reflected/inside. A native-HEOS +/-5 m/s one-step regression verified all four
endpoint momentum updates against an independent Rusanov expression and the
mirrored solutions; maximum error was 1.77635683940e-15 kg/(m2 s). Zero wall
mass and energy flux alone would not have exposed that momentum defect.

Nozzle outflow was correctly debited from tank stocks but incorrectly
subtracted again in combined residuals. Independent native one-step stock and
withdrawal values proved the erroneous residual equalled minus twice the
outflow. Correcting the two diagnostic signs restored the closed-system
stock-change-plus-withdrawal identity without changing physical gates.

The frozen corrected network then passed all three cases in
validation/cases/caloric_reservoir_nozzle.py, including the original 10 MPa
tank / 4 MPa pipe jump, maximum CFL 0.2 and 0.02 s duration in choked and
back-pressure-limited regimes. Choked withdrawal was 0.000676511832075 kg and
2697.87082455 J; tank P/T ended at 9.75139496989 MPa / 299.055276579 K. The
back-pressure-limited maximum residuals were 2.93710368526e-16 kg and
6.78483047523e-10 J. Wrong property basis, pressure-domain exit and unequivocal
mass depletion rejected. See CALORIC_PIPE_NETWORK_WAVES.md for source pins,
regression names, inputs and limits. The full numerical run took 510.564 s;
only report formatting was changed afterwards to bound interval-array output.
These results verify native-property numerical accounting, not independent
measured pressure-wave/blowdown or facility performance.

## 2026-11-01 compressor charge to native CoolProp linepack

Extended the existing `charge_linepack_from_compressor()` receipt and projection
to accept `RealGasLinepackState` and its existing native ledger alongside the
explicit analytic-reference state. The original owner advances the inventory;
no EOS or compressor solver was duplicated. Native charging requires direct
HEOS fluid, spin and version compatibility and endpoint-density agreement with
the compressor's retained CoolProp provider. The receipt seals native-state
pointers and property methods and explicitly retains the final EOS owner.

The final frozen source passed both legacy and native actual local validation
with CoolProp 8.0.0. The native case added 0.001 kg over 20.0–20.1 s, producing
1,125,281.109224105 Pa final pressure, -3,282.3489534652567 J signed inlet
conditioning, zero conditioning residual and -8.673617379884035e-19 kg mass
residual. Eight native mismatch/mutation paths rejected; the original receipt
remained current after each definition was restored. Scoped Ruff passed for
the adapter and validation module. This verifies synthetic mass accounting and
inlet-state energy projection only; storage thermal control, device data and
facility qualification remain open. See COMPRESSOR_LINEPACK.md.


## 2026-11-01 native adsorption product to linepack mass connection

Extended the existing adsorption-product charge API and receipt to accept
RealGasLinepackState with its direct pure-H2 CoolProp HEOS owner alongside the
explicit analytic reference. The original inventory advance is reused. Native
molar mass, fluid/spin identity, state-pointer/method definitions, mapped clock,
source product issuance and mass/pressure endpoints are retained and rechecked.
No new EOS or flow solver is implemented.

Known source spin must match the native target. Unresolved mixed-source spin
requires hydrogen_spin_composition and hydrogen_spin_evidence_id; the retained
mapping is a caller claim, not native-derived source qualification. A known
non-H2 source or contradictory source spin cannot be overridden by that claim.
Only mass enters this connection. Source enthalpy, conditioning energy,
compression, purification and pressure compatibility are not inferred.

The existing product projection and analytic-reference cases passed locally.
The native case also passed, including fifteen invalid-input/mutation paths:
0.5489952138406358 kg product produced 0.5489952138406355 kg inventory increase,
with linepack pressure 5 MPa to 5.352985210522568 MPa and mass residual
2.220446049250313e-16 kg. The pure source uses native gas properties with an
authored zero-uptake numerical limit. Explicit unresolved-mixture spin mapping
was checked separately. Ruff and scoped diff checks passed. This verifies
source-bound component mass/EOS accounting, not measured material or facility
performance. See ADSORPTION_LINEPACK.md for exact keywords and execution scope.


## 2026-11-01 independent native short-pipe momentum check

Read-only rederivation confirmed the native isothermal Darcy integral and its
fixed-temperature sonic denominator. Added one separate reproducible case,
`native-isothermal-real-gas-short-pipe-reference`, in
validation/cases/real_gas_hydraulics.py; the previous long-pipe entrypoint and
production kernels were unchanged. The short benchmark deliberately makes the
acceleration term 0.216145566457 comparable with friction length 0.5, exposing
wrong log signs/factors more strongly than a long friction-dominated pipe.

The new entrypoint actually passed locally in Conda Python 3.12 / CoolProp 8.0.0.
Independent direct-native density-coordinate quadrature/root and density ODE
returned 10.10994294646489 kg/s versus production 10.109942946464903 kg/s
(relative 1.33226762955e-15). Independent/production outlet errors were
+2.98023223877e-8 / -2.23517417908e-8 Pa, with isothermal Mach 0.593912202202.
Native small-drop comparisons at 1 Pa and 0.00100000202656 Pa differed by
1.71423254480e-8 and 1.71420655448e-11 relatively. Native-derived sonic,
liquid-phase and equal-pressure cases all rejected. Source density, viscosity
and derivatives came from CoolProp; no fitted or handwritten fluid EOS was
introduced. The local-density expression is only an independently checked
constant-friction small-drop asymptote.

Kernel SHA-256 123510ccc4f4a103399bf3821e3f152b74d6ce6b1a2d9967d27b97e6e44577ca;
case SHA-256 4da6fa2f3f31971ea4cceab862f504503c3ca27cc0954c7c8f6c73f28690a10a.
Ruff passed; detailed inputs, exact case name and limitations are appended to
HYDRAULICS.md. These are native-EOS numerical checks, not independent measured
pipe or friction validation. No remote access, download or package installation
was performed in this lane.


## Extreme-value checkpoint — 2026-11-02

Completed the explicitly requested parallel extreme-value campaign:108/108 cases passed across66 of78 scoped families, zero failures/errors/skips in final execution. The other12 selected native cores remain outside internal-physics validation. Scope is29 model-numerical families,31 supporting-numerical families,1 computed-domain rejection,1 exposed-field endpoint mapping and4 declared-domain-edge-only families. These narrower checks are not exhaustive family physics qualification. Final three-process execution took71.69s wall for the slowest lane; all368 pinned product/campaign Python files were unchanged. See [EXTREME_CONTRACT_CAMPAIGN.md](EXTREME_CONTRACT_CAMPAIGN.md) and artifacts/extreme-contracts-20261102/coverage-78.json.

Fixed nonfinite stack output admission and material solubility overflow handling. Source-affected nominal regressions passed14 tests. Existing native internal physics was not independently validated. Earlier input and nominal-equation receipts remain preserved; no module-connection campaign was started. Implementation family census is unchanged.



## Basic connection checkpoint — 2026-11-02

The latest user instruction limits connection tests to basic input/output delivery, units, material identity and clock support. Additional deep checks and full-chain campaigns are stopped. No current worker remains active. Existing execution evidence is preserved: selected normal handoffs cover72/78 topic families;2 are rejection-only boundaries,2 blocked/unavailable external paths and2 terminal outputs without an existing consumer. The recorded57 passing cases include deeper checks executed before this scope reduction and must not be described as57 basic-only tests. No further calculation is planned in this stage. See [CONNECTION_CONTRACT_CAMPAIGN.md](CONNECTION_CONTRACT_CAMPAIGN.md).



## Basic regression / representative-run checkpoint — 2026-11-02

The explicitly requested basic stage finished:50/50 selected existing regression tests across12 original files, and6/6 representative input-to-output runs passed; zero failures/errors/skips in final runs. Three independent tasks were used. No product source changed, and all recorded pins still match current source. This is selected regression and six examples, not78/78 full end-to-end qualification. One pre-existing compartment arithmetic-guard warning remains recorded; finite outputs and basic checks pass without deeper work. The previous72normal/2rejection/2blocked/2terminal connection classification is unchanged. See [REGRESSION_REPRESENTATIVE_CAMPAIGN.md](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) and artifacts/regression-e2e-20261102/summary.json. No further testing is running or automatically scheduled.



## Measured-data comparison checkpoint — 2026-11-02

Four selected own-model closures were compared with real experiments using separated calibration/evaluation data: effectivepermeance(64train/32heldout),normalizedhydridekinetics(100train/44heldoutcurves),PEMpolarizationlosses(46train/56heldoutcontexts),andfixed-coefficientgasnozzle(13train/22heldoutscanrows). Results are conditional measured comparisons, not formal qualification; qualifiedcount remains0. Permeance heldoutMARE2.15–4.06%; hydride mean-curveRMSE4.49/4.86percentagepoints; PEMRMSE23.102mV; nozzleMARE29.83%. Native engine internal physics and whole-facility physics were excluded. All365productPythonfiles match the prior basic checkpoint; no productionmodel/default changed. See [PHYSICAL_VALIDATION_CAMPAIGN.md](PHYSICAL_VALIDATION_CAMPAIGN.md), its source/identifiability limits and artifacts/physical-validation-20261102/summary.json. Raw datasets remain ignored; two original public source-metadata ledgers and four replay scripts were added. No further calculation is running.

