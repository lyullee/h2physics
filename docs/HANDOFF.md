# Research handoff — 2026-10-31

## Measured-data comparison checkpoint — 2026-11-02

Four selected own-model closures were compared with real experiments using separated calibration/evaluation data: effectivepermeance(64train/32heldout),normalizedhydridekinetics(100train/44heldoutcurves),PEMpolarizationlosses(46train/56heldoutcontexts),andfixed-coefficientgasnozzle(13train/22heldoutscanrows). Results are conditional measured comparisons, not formal qualification; qualifiedcount remains0. Permeance heldoutMARE2.15–4.06%; hydride mean-curveRMSE4.49/4.86percentagepoints; PEMRMSE23.102mV; nozzleMARE29.83%. Native engine internal physics and whole-facility physics were excluded. All365productPythonfiles match the prior basic checkpoint; no productionmodel/default changed. See [PHYSICAL_VALIDATION_CAMPAIGN.md](PHYSICAL_VALIDATION_CAMPAIGN.md), its source/identifiability limits and artifacts/physical-validation-20261102/summary.json. Raw datasets remain ignored; two original public source-metadata ledgers and four replay scripts were added. No further calculation is running.

## Basic regression / representative-run checkpoint — 2026-11-02

The explicitly requested basic stage finished:50/50 selected existing regression tests across12 original files, and6/6 representative input-to-output runs passed; zero failures/errors/skips in final runs. Three independent tasks were used. No product source changed, and all recorded pins still match current source. This is selected regression and six examples, not78/78 full end-to-end qualification. One pre-existing compartment arithmetic-guard warning remains recorded; finite outputs and basic checks pass without deeper work. The previous72normal/2rejection/2blocked/2terminal connection classification is unchanged. See [REGRESSION_REPRESENTATIVE_CAMPAIGN.md](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) and artifacts/regression-e2e-20261102/summary.json. No further testing is running or automatically scheduled.


## Basic connection checkpoint — 2026-11-02

The latest user instruction limits connection tests to basic input/output delivery, units, material identity and clock support. Additional deep checks and full-chain campaigns are stopped. No current worker remains active. Existing execution evidence is preserved: selected normal handoffs cover72/78 topic families;2 are rejection-only boundaries,2 blocked/unavailable external paths and2 terminal outputs without an existing consumer. The recorded57 passing cases include deeper checks executed before this scope reduction and must not be described as57 basic-only tests. No further calculation is planned in this stage. See [CONNECTION_CONTRACT_CAMPAIGN.md](CONNECTION_CONTRACT_CAMPAIGN.md).


## Extreme-value checkpoint — 2026-11-02

Completed the explicitly requested parallel extreme-value campaign:108/108 cases passed across66 of78 scoped families, zero failures/errors/skips in final execution. The other12 selected native cores remain outside internal-physics validation. Scope is29 model-numerical families,31 supporting-numerical families,1 computed-domain rejection,1 exposed-field endpoint mapping and4 declared-domain-edge-only families. These narrower checks are not exhaustive family physics qualification. Final three-process execution took71.69s wall for the slowest lane; all368 pinned product/campaign Python files were unchanged. See [EXTREME_CONTRACT_CAMPAIGN.md](EXTREME_CONTRACT_CAMPAIGN.md) and artifacts/extreme-contracts-20261102/coverage-78.json.

Fixed nonfinite stack output admission and material solubility overflow handling. Source-affected nominal regressions passed14 tests. Existing native internal physics was not independently validated. Earlier input and nominal-equation receipts remain preserved; no module-connection campaign was started. Implementation family census is unchanged.


## Calculation-check checkpoint — 2026-11-02

The user resumed the paused campaign. All 67 selected nominal test cases pass across 66 of the 78 scoped topic families: 30 model-equation comparisons, 35 supporting geometry/integration/accounting checks and one thermodynamic identity. The other 12 selected cores belong to existing engines and are excluded from independent internal-physics validation, not counted as passes. There are no pending selected host checks. This is not full-equation or experimental qualification of all 78 families. Input checks remain 78/78. Extreme-value and module-connection campaigns have not begun.

Execution exposed and repaired two product defects: unstable temporary-serialization identity in pool-fire seals, and an absent CellBurn.time_s reference in flash-front seals (correct field arrival_s). Genuine traces are accepted and altered result fields rejected. See [FORMULA_CONTRACT_CAMPAIGN.md](FORMULA_CONTRACT_CAMPAIGN.md) for all 78 classifications and pinned execution receipts. The three test lanes ran independently in parallel; final source pins were checked during execution.

## Latest checkpoint — 2026-11-02 input checks

The explicit user instruction enabled the targeted input campaign after the implementation-only wave. All 78 scoped families passed representative input checks (161 malformed-input cases + 1 manifest check; 162 passed, no skips). Final combined execution took 10.37 s, with 419 pinned Python files unchanged. See INPUT_CONTRACT_CAMPAIGN.md and artifacts/input-contracts-20261102/all-78.xml, all-78-run.json and coverage-78.json. No broader numerical/experimental or native-engine physical validation is implied. The earlier historical six-category review is superseded for this input-campaign scope only; other test categories remain unchanged.

## Current restart checkpoint — 2026-11-01

- Buoyant-layer production now uses native CoolProp HEOS H2/N2/O2/Ar density,
  molar mass and stock inversion. Four focused native cases plus Ruff passed.
  Oxygen projection binds the full carrier tuple; its strengthened integration
  rerun is pending. This does not clear other possible property-default gaps.
- Frozen-mixture Darcy/network source and focused guards are implemented. Final
  focused tests passed 12/12 in 33.93 s; the old full three-level network process
  (historical PID 1093004/session 22728) is now absent and its final outcome was
  not retrieved. Do not relaunch merely because an observation timed out, or
  infer a result from its former CPU activity. The recorded case remains
  unverified until an actual outcome is available from a pinned run.
- Table inverse query v2 fixes the mismatched log-linear inverse. The optional
  pressure-derivative cT mode passed 13 focused inverse/algebra/artifact tests
  and a native 16-point holdout qualification within 1%. Sampled-cT schema1
  artifacts and identity remain compatible; the new query mode has its own
  identity/schema2. Historical v1-qualified receipts reject; unqualified grids
  require requalification. Tables remain outside Darcy/network types.

- Overall programme estimate remains 30–40%. Catalog labels are 20 implemented,
  37 native-adapter-verified and 25 implemented-unverified across 82 families;
  they do not prove complete facility or independent measured-data validation.
- User directs native CoolProp thermophysical properties and qualified tables.
  Local scientific work is explicitly authorized when Hangang is slow/unavailable.
- The latest property instruction prohibits a handwritten fluid-property library.
  The isothermal pipe-wave default now selects the existing CoolProp HEOS EOS;
  three native-default regressions passed locally (24.35 s): direct HEOS density
  at 70 MPa/300 K, missing dependency without fallback, and native liquid-phase
  rejection at 1 MPa/20 K. Scoped Ruff passed for the four changed source/test files.
  Legacy analytical linepack paths remain explicitly selected references;
  the quasi-steady network now also supports native pure and frozen-mixture
  properties. Compressor, adsorption and electrolysis charging now also accept
  the existing CoolProp real-gas state; native and legacy calculations passed.
  Unified source withdrawal delegates native inputs to the existing real-gas
  adapter, and its full fuel-cell coupling case passed with 15 rejection gates.
  Electrolysis verifies native endpoint inventory energy (142.8516765963 J in
  its authored case) and seals nested ledger values against balanced mutation.
  Adsorption retains mass-only scope; unknown source spin requires explicit
  caller mapping evidence. See the dedicated linepack documents. These changes
  do not convert every analytical model or establish independent validation.
- Caloric reservoir/nozzle verification finished: all three cases passed after
  correcting the right closed-wall ghost ordering and nozzle residual signs.
  Original 10/4 MPa, 0.02 s and CFL 0.2 were retained. The documentation records
  executed source hashes and separates a later reporting-only metric reduction.
- Latest accepted remote tree: `/scratch/CLUSTER_USER/h2physics-jobs/verified-coolprop-02574687`.
  The follow-up `7195212f...` delta is locally pinned but transfer failed with
  wrapper exit 255. A separate check confirmed no usable shared CPU connection.
  Manual user `READY cpu` is required before further remote operations. Never
  start a new SSH connection or perform password/OTP authentication.
- A newer local delta is ready at
  `../tmp/hangang-native-linepack-07-delta/delta.tar.gz`: 69 files, 994375 bytes,
  SHA-256 `5498d10392525d796d8eb5f02f8da1df0a8d237534175655e77c3e84171c30ae`.
  It applies directly to the last verified `.../verified-coolprop-02574687`
  base and targets manifest
  `2ce3f34cf3c87b8ecae47df09bc04aebf424acfe4c94eabee6a71cd953314755`.
  After manual READY, use `scripts/transfer_apply_hangang_delta.py` with that
  archive, incoming `.../incoming-linepack-2ce3f34c`, destination
  `.../verified-linepack-2ce3f34c`, target cpu, workers 4. Ellipses denote
  `/scratch/CLUSTER_USER/h2physics-jobs`. This avoids resuming the older incomplete
  7195212f delta. Verify the final remote manifest receipt; no new transfer or
  submission has occurred. Preserve unrelated account jobs.
- Subsequent native quasi-steady hydraulic/network development and these newer
  checkpoint notes postdate the 2ce3f34c snapshot. Pin a later delta before
  executing those newer changes remotely; never treat the live worktree as that
  immutable archive.
- The next package staging path is `../tmp/hangang-native-pipes-08-delta`.
  Check for its completed `receipt.json` and validate the archive hash before
  selecting it; a directory name or running preparation is not a completed
  receipt. It must apply directly to the remote 02574687 base because neither
  the 7195212f nor 2ce3f34c tree has been verified remotely. Its later source
  content supersedes the linepack-only pin once preparation succeeds.
- Snapshot08 preparation completed: 86 changed files, 1059947 bytes, archive
  SHA-256 `8408f0cfd4967cb7877f633dab394fa5d918f518858f1d2b6bebb3f587226629`,
  target manifest `3ee9662a38df6a13f2acec6106bcdca929f8c05870e5878d88a882214bda51da`.
  Exact local remote-apply reconstruction passed at
  `../tmp/hangang-local-3ee9662a`. It has not been transferred remotely.
  Later blend, data-reader and preparation-speed changes postdate this pin.
- Metadata startup now resolves root exports lazily while retaining all 81
  public bindings. One local fresh-process comparison observed 19.395 s before
  versus 0.423 s after for importing `h2physics.cluster_validation`; the latter
  loaded no NumPy/SciPy/CoolProp. This is an import-workload observation, not an
  overall simulation speed claim. Nine export/cold-import/delta tests passed.
  The follow-up delta-path membership regression passed: four focused tests in
  351.03 s cover actual remote-apply reconstruction, deterministic archives,
  corrupt-base rejection, captured forbidden content and consistent runtime-path
  exclusions. Scoped Ruff passed. This does not establish overall packaging speed.
- Actual AHSS1300 ingestion was repaired: row-1 headers in both sheets, E3
  material label, 1260/599 observations and an actual microampere header. SI
  current conversion and source/schema guards passed. Missing exposed electrode
  area and boundary/initial history still prevent a qualified diffusion fit.
- Native quasi-steady pipe extension is now locally exercised at the same model
  level: the existing Darcy function uses CoolProp density integration and a
  separately reconstructed pressure ODE; the existing network mass ODE now uses
  native cell pressures and those same links. Hydraulics passed 13 tests plus
  the legacy momentum case and a strong short-pipe independent reference.
  Network native/legacy calculations, cold imports, real integration-step
  refinement and 17 rejection gates passed. Use canonical CoolProp fluid names
  (`Hydrogen`, not alias `H2`) for this level. Use `maximum_step_s`, not an
  output-grid change, for refinement. The standalone native example passed at
  10/9.9/9.8 MPa with installed fluids friction and held native viscosity.
  See HYDRAULICS.md and ISOTHERMAL_GAS_PIPE_NETWORK.md for exact scope/results.
- Current plan metadata: Hangang 358 cases/41 profiles; the separately maintained
  legacy Nurion plan 418 cases/59 profiles/115 modules. These are registered
  cases, not completed calculations. The source API index remains 362 modules
  and 1807 public definitions. No new remote submission occurred.
- The acquired-data metadata gate currently fails on exactly one known field:
  `bath-cryo-kinetics.toml:license_url`. The official record was rechecked and
  still supplies a record-level rights statement without a separate license
  URI; do not invent one. HRS and PEACE metadata SHA-256 omissions were repaired
  using exact separately dated primary responses in ignored storage, preserving
  historical file receipts. Parse failures are zero; file-level rights review
  remains distinct. See DATA_MANIFEST_AUDIT.md for the current failed gate.
- Frozen-mixture actual use confirmed and fixed `PropertyBasis.provider`
  AttributeError in the isothermal EOS bridge. Full reference/fluid/spin and
  composition now form the portable identity; native owners and scalar basis
  values are guarded separately. Both native linepack/wave cases and seven
  definition tests passed, including in-place basis mutations. See
  REAL_GAS_LINEPACK.md; pure EOS code was untouched. These results do not
  qualify changing composition, phase events or independent mixture data.
- Three pinned prior-source arrays `campaigns/h2cp0257{a,b,c}.pbs` are remotely
  staged and syntax/hash checked; none was submitted. The last queue query
  showed five existing running jobs at the previously observed QOS limit.
- Latest local numerical results: PV 13 cases passed; adsorption-vessel 9 cases
  passed; real-gas linepack/fuel-cell composition passed 15 invalid-boundary
  tests plus the ideal reference regression. See their dedicated documents.
- CoolProp gas-table construction had an issuer-call defect, now fixed; all
  three existing table cases passed. Native BICUBIC mixed PT/PH/PS was 3.92x
  faster locally; the separate Python isothermal table was about 6x slower.
  See THERMO_ACCELERATION_QUALIFICATION.md for budgets, envelope and limitations.
- Primary acoustic table audit matched 57/57 T/p/w triplets; only 19/57 EOS
  residuals are within the reported expanded experimental uncertainty. Neither
  that audit nor table-EOS agreement establishes independent EOS qualification.
- Continue cross-module scientific verification and missing native/data work
  from IMPLEMENTATION_REQUIREMENTS.md and IMPLEMENTATION_BACKLOG.md; do not
  reduce the original objective to these recent thermophysical connections.

- Latest implementation adds held-current positive-time H2/O2 reserve events
  through the original finite fuel-cell owner. Eight rejection paths and exact
  feed/source-prefix allocation passed; live ReactorNet depletion stays open.
- Porous-reservoir checks now pass 4/4 including dynamic HEOS injection and
  time/radial refinement. See POROUS_RESERVOIR.md; no site data were fitted.
- After the new public exports, fresh-process import checks passed 4/4 again
  (88.53 s). The active Hangang plan discovers 349 cases, including both new
  cases, with no missing profile definitions. The API index is 362 modules /
  1807 public definitions. These live changes postdate the pending remote pin.

- Safety execution: ten finite-relief-lift cases passed; Cantera native
  fuel-cell caloric path also passed. Detailed scopes/inputs are recorded in
  FINITE_RELIEF_LIFT.md and FINITE_FUEL_CELL.md.
- PRESLHY full four-experiment/three-bin replay completed with exit 0 and
  regenerated its source/code-fingerprinted report. Conditional held-out
  normalized inventory RMSE is 0.00361222122091. This does not independently
  validate mass flow. The prior replay source-file freeze is released.
- Caloric finite-reservoir/nozzle cases newly failed. Diagnosis found a right
  closed-wall Rusanov face-orientation defect; the assigned agent is correcting
  it and will rerun the original pressure-jump case without weakening gates.
  Treat those two cases as unresolved until their actual new results arrive.
  The native-CP ±5 m/s endpoint momentum regression has passed (four flux
  comparisons, max error 1.78e-15 kg/m2/s, direction mirror verified). The
  original pressure-jump blowdown remains live in agent session 32813. Do not
  restart it just because no new output has arrived.

The dated entries below retain historical source pins and intermediate results.

## Metadata plan synchronization — 2026-11-01

The generated validation inventory now reports 409 deferred cases, 59 profiles
and 112 case modules. Generation imports metadata catalogs only and did not run
scientific cases or use Nurion. Synchronization fixed a syntax error in the
vessel-failure case catalog, added the missing material-transport example
profile, filled six family-to-case mappings and moved quasi-steady permeation
to its current material-transport profile.

Added `adapters.layer_oxygen_projection.project_layer_oxygen()` to preserve the
existing two-vent layer trace while projecting O2 composition for an explicit
fixed dry-air carrier. It is an algebraic composition projection only, not a
homogeneous-room, alarm, exposure-duration or physiological model. Its new
synthetic case is assigned to existing families; it passed as Hangang job
1189682 on verified pin 5al. This remains a software contract, not a physical
validation.

Added `adapters.layer_oxygen_alarm_handoff.evaluate_layer_oxygen_deficit_alarm()`
to route the upper-layer oxygen projection through the existing first-order
sensor and sampled-alarm engines. The handoff requires caller-supplied
reference, clock/location mapping, source, mode and episode evidence; it retains
the exact projection and emits no room-average or human-response result. Its
deferred synthetic case is registered under existing facility-protection and
monitoring families. Immutable source 5am is verified remotely at
`/scratch/CLUSTER_USER/h2physics-jobs/verified-5am-delta-09f2feef`; the corrected
single-case script was generated from that exact tree and submitted as Hangang
job `1189857`. It passed its synthetic six-sample sensor/alarm contract in
1.29 s. This does not validate a field detector, a whole-room oxygen field or
human response.

Job `1189567` passed the synthetic two-vent buoyant-layer contract on pin 5ai
(10.22 s; H2 and vent residuals below `1.58e-16 kg` and `3.47e-17 kg/s`). The
5al pin then passed five independent synthetic contracts: O2 composition
projection (`1189682`), surface-film diffusion (`1189687`), K-of-N reliability
(`1189688`), competitive Langmuir (`1189694`) and power-law material diffusion
(`1189695`). Their result limits and exact metrics are in `PROGRESS.md` and
`HANGANG_EXECUTION.md`. No dataset qualification or facility validation follows
from these authored-value contracts.

The standalone `hydrogen-diffusion-surface-film-boundary` contract was missing
from Hangang discovery. It is now registered under `material-transport` and is
included in the remotely verified 5ak pin and its prepared four-case campaign.
The case uses synthetic coefficients and does not fit experimental material
data. The 5al campaign array remains unsubmitted; its five one-case alternatives
were used as QOS slots opened.

## Current correction — 2026-11-01

Job `1189474` on pin 5ah failed because its synthetic case asserted H2 in the
adjacent room at the zero-concentration initial sample. The fixture now checks
the last output time after transport instead. This was a harness defect. The
correction passed on pin 5ai as job `1189504`, scoped to a synthetic fixed-state
compartment contract.

Static equation review found the fixed-inventory linear transport construction
consistent with the stated model boundary. Flow-balance tolerance must remain
small relative to scheduled flows because inventories are held exactly fixed.
The model excludes pressure-driven ventilation, buoyancy and stratification;
job 1189474 did not reach its ledger assertions.

## Latest continuation — 2026-11-01

The fixed-state compartment-network contract also passed on corrected pin 5ai
as job `1189504`; H2/carrier conservation residuals were `7.43e-18` and
`1.18e-13 mol`. The 1,425-entry pin manifest verified with SHA-256
`8df457da9154af9e3ade032e1190b14a1814ea38bce8013233d3aad0ecbbd3a2`. The first
attempt failed only because the synthetic assertion included the initial zero
H2 sample. This result covers ideal-gas fixed-P/T, perfectly mixed prescribed
flows; it does not validate ventilation, buoyancy or stratification.

The PEM ripple reader source, rights metadata, documentation and discovered
synthetic case are sealed in Hangang pin 5ah
(`1fe679d69162ef1a551f997e00bf9e5ec8c4418f`). All 1,425 manifest entries passed
remote SHA verification; raw ZIP bytes were excluded. Job `1189469` passed
`pem-ripple-streaming-reader-source-integrity` in 1.15 s. It preserved 2 IV
rows, 3 continuous rows, 36 publisher-fit rows and source clock gaps, and
detected modified projections/source bytes. No publisher observations were
evaluated; this is not physical model validation. Exact pin, plan, and outcome
details are in `docs/HANGANG_EXECUTION.md`.

## Latest continuation update — 2026-10-31

Corrected immutable Hangang pin 5ag is revision
`f43e8f636829e1fae2a4aa38f397b6049a88628e`; the archive, manifest and all 1,421
source entries verified. Jobs 1189381, 1189394 array elements 1 and 2, and
1189400 passed the finite-wall, Brayton nominal shaft, alkaline bubble-loss and
Brayton terminal-speed-event software contracts. The reports, metrics and
limitations are in `docs/HANGANG_EXECUTION.md`. These are synthetic API
contracts, not physical validation.

The first generated job was launcher-rejected by an incorrect setup-script
digest (`1189334`, failed before case entry); the actual digest was checked from
the verified pin, and corrected submissions completed. QOS refused the initial
three-case array, so submission was split into a singleton and a two-case
array. Do not touch unrelated queue jobs. PEM ripple ingestion is implemented
and registered in the live plan, but is absent from 5ag and awaits a later pin.

## Current continuation — 2026-10-31

Continue local implementation while Hangang transfers/verifications proceed in
parallel. Conda environment `h2physics-py312` uses Python 3.12.16, as declared
by the project `environment.yml`. The approved `run.sh cpu` probe
reached `clogin03` as `r1021a02`. Its read-only queue snapshot showed three
running jobs (1186716, 1187147, 1188529) and one completed job (1189044);
unrelated work was left untouched.

The new `h2physics.compartment_network` model and deferred Hangang case are
registered. It advances H2 and inert carrier over fixed-P/T rooms using balanced
caller-owned flows, with species ledgers and accepted-prefix error retention.
Ruff and AST checks passed; no scientific execution was done locally. Current
inventory is 343 package modules / 1,749 public definitions and 82 catalog
families (19 implemented, 37 native-adapter-verified, 26 implemented-unverified).
Overall completion remains roughly 30–40% across coding, data rights/qualification,
cross-model integration and HPC evidence.

The PEM current-ripple Mendeley v2 archive is acquired locally under CC BY 4.0
(90,759,411 bytes; SHA-256 matches the published receipt). Source-bound streamed
readers now cover unaveraged IV rows, continuous per-cell current/voltage logs,
and the separate publisher-fit table. Exact source rows can be streamed; raw
naive timestamps are represented by their first token plus millisecond offsets,
so clock gaps remain visible. Unknown active area, test state, calibration,
timezone and cell synchronization are recorded as gaps. Synthetic reader case
`pem-ripple-streaming-reader-source-integrity` is now registered in the live
`validation/hangang_plan.py`. It is absent from sealed pin 5ag, so a later source
pin must include it before any Hangang submission. Ruff and AST/TOML checks pass;
no scientific execution ran. Refreshed API index: 343 modules / 1,749 definitions.

Snapshot 5af is sealed locally at `93c86863c13957c73b09cc9f32548aadf709385d`
(1,415 manifest records; manifest SHA-256
`7bd7f2100dcbfb8d57d2d1b16fe0c54931cede75526beda3b59e6dee14f7572d`; archive
SHA-256 `b3f56b254eda38046058cbcc506b66f493350bacfe27057e6b2daa356e9adb3e`). It
contains the current finite-wall, shaft-transient and alkaline-bubble Hangang
cases. All 1,183/1,183 5af chunks have matching local/remote SHA-256 values.
Remote archive `/scratch/CLUSTER_USER/h2physics-jobs/incoming-5af-93c86863/source.tar.gz`
is 14,185,810 B with SHA-256
`b3f56b254eda38046058cbcc506b66f493350bacfe27057e6b2daa356e9adb3e`. Extracted
pin `/scratch/CLUSTER_USER/h2physics-jobs/verified-5af-93c86863` has revision
`93c86863c13957c73b09cc9f32548aadf709385d`, manifest SHA-256
`7bd7f2100dcbfb8d57d2d1b16fe0c54931cede75526beda3b59e6dee14f7572d`, and
1,415/1,415 source entries verified. The independent 5ae transfer remains parked
at 792/1,173 verified chunks.

The verified pin has a prepared 3-case array at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5af-three-core-validation.pbs`,
SHA-256 `e6bff847067bfc41fbd853f17ce6696beb22d78705af1097e9dffae0cb6ec0e2`.
It covers the finite-wall caloric pipe, transient shaft balance, and alkaline
bubble-loss contracts. The first `qsub` at five active user jobs was QOS-refused;
a retry after two jobs completed was admitted as array 1189215. Elements
1189215–1189217 all ran their cases but failed software-contract checks. The
finite-wall and shaft outcome records are repaired, the bubble fixture no longer
clamps invalid inputs, and the shaft maximum-speed retry case is registered.
Targeted Ruff/AST checks passed. The existing jobs were untouched. Do not retry
immutable 5af; pin the corrected source first.

Mendeley Data v2 `pem-ripple-degradation` was acquired to ignored raw storage:
90,759,411 B, publisher SHA-256
`47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`, verified
by range assembly and the project receipt API. It has 36 polarization CSVs,
four continuous-voltage CSVs and one fitted-parameter table; measurements and
fits must remain distinguished. Reader work should stream ZIP members and keep
source tokens, stated A/V units, original timestamps and gaps. Cell geometry,
calibration and several apparatus conditions are still unknown. The archive is
not included in the Git tree; no independent stack validation is established.

## Hydrogen ignition-probability integration — 2026-10-31

`h2physics.adapters.hyram_ignition` now provides a typed, optional call into
the installed HyRAM+ native rate-bin ignition function. It supports caller
evidence-bound H2 probability tables and capture of the installed H2 default,
checks table/domain constraints, and records HyRAM package version and kernel
source SHA-256. Deferred case
`hyram-hydrogen-ignition-probability-native-contract` is registered under
`hyram-overpressure`; it has not run. No local Python runtime was available
through the WindowsApps `python` shim when this note was first drafted. The
project Conda environment `h2physics-py312` has since been located and its
environment checker reports the core profile ready; the adapter source also
parses with Python 3.12.14 using AST. No scientific test, native HyRAM call or
calculation was run locally.
This adapter adds no ignition correlation or facility risk model. HyRAM+ is
optional and GPL-3.0-only, while this project is Apache-2.0; same-process use
and any combined distribution require a separate license-compatibility review.
See `docs/HYRAM_IGNITION_PROBABILITY.md`.

## Current verification handoff — 2026-10-31

Current5f is sealed at temporary revision `457e6931cd1b9c2163285587e48f55fdc98ad8f1`,
with 1,110 files, manifest SHA-256
`9026f468431a4f42464e00e16d592d0209a4fca4aed4ad4fd56fff2f1eb4e7dc`, archive
SHA-256 `fce4047bbddfb2a05cc1ab8dbbc4fbaf615c2489a3b311184fbb0633b8a2cc6e`.
The staged hydrogen-channel metadata and ZIP match their pinned sizes and
SHA-256. The repository archive matches its SHA-256, all 1,110 source-manifest
entries verify, and the forbidden-member audit is empty. Current5f jobs 1186522
and 1186523 failed before case entry because scheduler log files changed the
pinned tree. Jobs 1186526, 1186530 and 1186534 entered the catalytic wall heat
handoff and found an undefined `flow_boundary` reference in a closed-reactor
path. Live source now uses its declared element tolerance. Re-run that contract
with current5g; no physical model acceptance has been established. External
`qsub -o/-e` paths and bytecode suppression are in use.
Current5g is now sealed and remotely verified at revision
`28cb04858fefa7b2447cb5ac86f992402694a992`, with 1,123 manifest entries,
manifest SHA-256
`741799a4ee9d49564e601f30c39f43c81a497f0454b4d0957969303fb313724b`, and
archive SHA-256
`fd5106853ea82036d4df04e4df444a20d02d6bb431da396399a02962e411bc55`.
Hangang verified every source-manifest entry. Job 1186567 entered the catalytic
wall heat case, then found a software invariant error at the sampled gas/surface
state. It requires a source fix and current5h replay; no physical-model result
was established. Separate sensor/alarm case 1186578 passed with a synthetic
trip at 0.06 s; this is API contract evidence, not detector qualification.
Current5h archive `55d69728b9a34e0eab3027a6f558bfa5de2f84bbbe8599d3789b519780f3c4c3`
passed its remote manifest. Jobs 1186595/96/97 entered the BAM, reaction-heat
and reaction-H2 cases, then exposed two software defects: BAM record-origin
admission failed, and both reaction adapters called a nonexistent
`FiniteThermochemicalCycle._enthalpy`. The adapters are being corrected; no
physical qualification was established. The BAM admission failure was a
reader metadata-SHA transcription mismatch; the constant now matches the
staged response and case pin. Current live source replaces both reaction
adapter `_enthalpy` calls with provider-backed inventory-energy reconstruction.
Replay all three in a fresh pin. The BAM archive and metadata are separately
staged with exact size and SHA-256. Current5i is sealed and verified
at revision `a6877cf9dd55c8a94e4b4ebf1a79b8eae62417f7`, with 1,132 entries,
manifest SHA-256
`b905ef7c1cd474f92e8c7c3148ff4b2667948d75244525f2aea389a3240fef46`, archive
SHA-256 `7b8c52e0429e9d9f076b7fca07ff9cf6f1a2e356c783da6373d8bd573ff060a5`.
The catalytic accepted-state-restore replay 1186610 passed: 20 exact heat-duty
intervals, total signed heat `-0.0010711399253343593 J`. It tests the native
handoff and freshness only; the wall is imposed and plant utility performance
is not inferred. current5l/current5m captures were preserved after exact-plan
audits found stale or missing source entries; neither was submitted. The next
planned current5n capture will include the BAM/solid fixes, acoustic route and
new metadata-only data-gap contracts after the plan is frozen.
An acoustic-
data → CoolProp pointwise diagnostic is also live. Its Zenodo ZIP (45,826 B,
SHA-256 `38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553`)
and metadata (6,458 B, SHA-256
`1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`) are
staged at `/scratch/CLUSTER_USER/h2physics-source-attachments/hydrogen-sound-speed/1.0.0/`.
The downloaded byte hashes corrected two earlier transcription pins. Include
this diagnostic in current5n; it is not independent EOS validation.
The live tree also includes a core-only finite solid-reaction heat → `HeatDuty`
bridge and deferred case `solid-reaction-heat-utility-handoff`; include it in
the next compatible source pin.

Current4 jobs 1186462 (native fuel-cell callback guard) and 1186463
(open-cylinder geometry tolerance) failed before a qualifying integration
result. Do not repeat the known current4 failures. Current5e
(`825e206735c0e5cb44f726a1d3df76c1d02a2661`) is stale compared with live source;
preserve it as a historical capture and create a fresh manifest for new cases.
At the last queue check, 1186457, 1186438 and 1186395 were unrelated running
jobs, with no hydrogen-project job active.

The hydrogen-channel bridge reconstructs its Dataset from exact pinned Figshare
metadata bytes and a separately SHA-pinned archive using an offline fixture. Its
Hangang source path and data are staged and hash-verified. Oxygen alarm,
Cantera catalytic-wall thermal and Cantera gas-species
sensor/alarm handoffs have deferred Hangang contracts, not physical-model
qualification. Current catalog status is
56/80 families (70%) at implemented or native-adapter-verified level, not overall
completion.

The AB2 shell thermocouple bridge projects one explicitly authorized external
shell reading series into the existing finite-hydride bath boundary. Its
synthetic Hangang contract rejects direct construction and altered mapping
evidence. The mapping premise remains caller evidence; no bed or bath equivalence
is inferred by the module.

The finite-hydride nozzle bridge uses only accepted outward gas-port intervals
and the existing shared nozzle model to build a source history. The deferred
Hangang contract checks trace/currentness and interval linkage; physical tank
release, nozzle qualification and dispersion remain separate evidence gaps.

A static conservation audit found the initial adapter could report nozzle flow
inconsistent with the finite-bed gas-port mass. The bridge now requires a
caller-selected output-grid quadrature and evidence-bound mass tolerance, audits
each interval and rejects mismatch rather than rescaling either model. The
synthetic contract now uses the nozzle as the bed outlet law and adds an
oversized-opening rejection case. This correction postdates current5f and needs
a new immutable current5g source before this route is submitted.

Current4 CSTR job 1186427 failed before integration: assigning the read-only
Cantera `Interface.T` attribute raised `AttributeError`. The adapter now uses
the `ReactorSurface.phase` Python property to invoke native `restoreState()`
after restoring reactor thermodynamics, while retaining strict shared-phase
temperature checks. This correction is unverified and requires a fresh
immutable pin; do not treat the failed job as a physical result. Current5d
revision `20f54aefa0fd8f95e1fd0618caf8ddeef5926fde` contains 1,093 files and
the CSTR correction, but predates later source and document edits. Current4
linepack job 1186441 passed with maximum mass residual
`5.662137425588298e-15 kg`; current4 reactant-current policy case 1186459 also
passed. Neither establishes physical qualification. Current4 cases 1186447/48/49
failed respectively on fixture boundary direction, a native moving-wall volume
residual above its declared budget, and an exact CSV-header mismatch. Engine
case 1186461 on current4 reproduced the same old-pin geometry residual; it
does not include the local 0.1x tolerance correction. Local corrections exist
and require a new immutable pin. Current4 cases 1186462 and 1186463 were newly
submitted in parallel and were running alongside three unrelated jobs at the
latest queue snapshot. Continue implementation while submitted work runs.

The verified current4 immutable archive is transferred to Hangang. Its source
manifest contains 1,086/1,086 matching files, with 1,088 regular archive
members and zero forbidden raw binary/source-attachment members. Current4 does
not contain edits made afterward to the HyRAM finite-source boolean gate,
accident consequence fixtures, the core-flood power-law summary, the
compressor-to-finite-mixture-vessel handoff, or the DataverseNO X044QK reader
and case. These need current5 or a later pin. The matrix file (14,199 bytes,
SHA-256 `c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`,
publisher MD5 `6c929ee530ac393ee8e76f6db2eff05c`) is local under ignored
`data/raw/ignited-hydrogen-jets-x044qk/1/` and has been separately transferred
to `/scratch/CLUSTER_USER/h2physics-source-attachments/ignited-hydrogen-jet-x044qk/1/`
through the existing `run.sh cpu` channel; remote size and SHA-256 match. It is
excluded from the source archive. Dataset DOI is `10.18710/X044QK`, license CC0 1.0.
The 40-row matrix notes MFR is pressure-derived; pressure calibration and
absolute/gauge basis remain unresolved. Raw EXP_022 is absent, the other 39
pressure-history CSVs and all six video bundles are unacquired, and no pressure
conversion or dispersion validation is claimed.

On current2, 1186388 relief accepted-edge ledger, 1186390 invalid-edge
rejection, 1186405 sensor calibration recovery, and 1186410 sensor calibration
rejection completed. Jobs 1186386 and 1186387 failed in consequence evaluator
binding before an output was admitted; 1186418 failed before an accepted sample
because a synchronized fuel-cell callback was reported changed. Do not treat
these synthetic contracts as equipment or physical validation. Current2
current statuses and immutable revision remain listed below.

New local interfaces awaiting a follow-up immutable pin include the
caller-bounded source-row-preserving core-flood power-law summary and the typed
real-fluid H2 compressor to finite-mixture vessel interval handoff. The latter
checks the actual HEOS fluid mapping, molar mass, shared energy-reference ID,
receiver pressure direction, and retained owner freshness. Its synthetic case
is not experimental receiver qualification.

## Active implementation and Hangang campaign — 2026-10-31

Historical snapshot (superseded): the catalog tracked 79 model families: 20
`implemented`, 37 `native_adapter_verified`, 22 `implemented_unverified`, and
0 `planned` (57/79 stronger-status ratio). Current counts are maintained at the
top of `MODEL_CATALOG.md`; they are not an overall completion or scientific
qualification measure.

The newly acquired H2SAFE indoor-release archive is CC BY 4.0, 3,766,528 bytes,
SHA-256 `f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e`.
Its first-party reader and ingestion case are registered in the local plan;
the archive was transferred to the Hangang external data path using only
the existing shared `run.sh` channel; remote size and SHA-256 were verified and
temporary chunks removed. The case leaves sensor calibration,
concentration basis, clock, and coordinate interpretation unresolved. These are
helium-surrogate experiments; they are not hydrogen dispersion or sensor-response
measurements and do not directly validate a hydrogen release model.

Fresh Hangang capture `cb6e00d48943cff36728c8ee88d683c5b8f5fb68` is now
transferred and verified. Its source manifest has 1,086/1,086 matching files,
manifest SHA-256 `7ed9e5f3afae46a55ff46412e5f03b59b3f8c524015116a7258b369cd3f08711`,
and archive SHA-256
`e977c7477e3317fb41608886fe8266b619f1c81257af4c069e150a5ac2d75994`. The
archive has 1,088 regular members including the manifest/revision files and
zero forbidden binary raw-data/document attachment members. It includes H2SAFE
case registration, segmented pipe network, API exports and current model/fixture
fixes. The QOS queue was full at capture verification; new-pin singleton
campaigns are being submitted as slots open. H2SAFE external-archive ingestion
`1186346` passed its source identity/schema/token contract. The data are helium
surrogate measurements, not hydrogen dispersion evidence. Segmented pipe-
network, linepack, CSTR, engine, detector, fuel-cell and risk cases are staged
for submission as capacity opens; the segmented network is admitted as
`1186359` and is pending. The fugacity-driven surface-film contract
`1186338` passed on the previous pin. Fuel-cell case `1186339` remains blocked
on its callback-currentness pre-sample guard and is held for the follow-up pin.

Follow-up local edits made after this immutable capture are intentionally not
part of `cb6e00d`: the native relief failure-prefix fixture for `1186301`, the
2,000 A/m² reactant-limit fixture for `1186330`, and the module-level callback
for zero-current fuel-cell case `1186331`, and `TurbineMapPoint.require_current`
for Brayton cases `1186268`/`1186269`. They require a later fresh pin. Hold the
affected cases on `cb6e00d`; the archive still lacks those corrections.

New-pin current2 job `1186359` exposed a case import name mismatch in the
segmented network deferred contract; its imports now match the public
`IsothermalPipeCell`/`IsothermalPipeLink` types for a follow-up pin. `1186363`
linepack exposed unsupported `nonnegative=` arguments to shared `finite()`;
`pipeline_linepack.py` now validates finite nonnegative inputs with a local
helper. Neither case reached its assertions on current2.

New local API levels include lumped linepack and a segmented quasi-steady
isothermal gas-pipe inventory network (both reuse separate scopes over the
existing Darcy solver), common-cause-aware detector voting, and immutable
source-versioned empirical detector trial summaries. The catalytic CSTR
sampling adapter now restores Cantera accepted reactor/surface states before
reading phase temperatures, without relaxing the equality bound. The engine-wall case resolves its
mechanism from Cantera data directories and reports a sampled refinement
sequence rather than assuming a universal energy tolerance. New and corrected
deferred cases are collected in the local Hangang plan; none have been executed
on the next source pin yet.

On immutable revision `3374d5ec87eeac05eb4311aab51af1de149966c9`, synthetic
contracts `1186148`, `1186149`, `1186151`, `1186155`–`1186158`, `1186168`,
`1186171`, `1186209`, `1186226`, `1186227`, and `1186234` passed. `1186210`
failed because its synthetic fragment trajectory did not contact the ground
within the declared time horizon; only the fixture launch altitude has since
changed, pending repin. Other failures remain tied to that exact pin: GrInHy2
byte checksum versus line endings (`1186145`), a strict float comparison
(`1186146`), catalytic CSTR phase handle sync (`1186160`, now corrected
locally), engine fixture import (`1186166`/`1186167`, corrected), engine-wall
mechanism/tolerance placeholders (`1186169`, corrected), missing external
LH2DT artifact wiring (`1186175` and related retries, repaired on that remote
tree), uncertainty fixture issuance (`1186183`, corrected for next pin) and
accident-chain consequence callback closure (`1186184`, module-scope synthetic
owner/result now used in the fixture),
and mixture-flash residual above its existing threshold (`1186192`, under
separate numerical review). Do not attribute those results to later code or
weaken a physical invariant to turn a failure into a pass.

On this same pinned revision, six additional independent relief contracts were
submitted as singletons: `1186237` travel, `1186238` leakage, `1186239` phase,
`1186240` inventory, `1186241` accepted-withdrawal ledger and `1186242`
invalid-edge rejection. `1186237`–`1186240` stopped at worker setup because
the external LH2DT package path was not in `PYTHONPATH`. The last two entered
their cases and exposed missing fixture factories. These are setup/case-wiring
failures, not relief-model evidence. The clock, source-binding and failure-
prefix cases hit the account QOS submission limit and remain to resubmit when
capacity opens. After adding the external native package path, retries
`1186250` leakage and `1186251` phase passed; `1186255` inventory, `1186256`
clock and `1186257` binding are running/pending. Independent jobs `1186252`
HyRAM source-transition ledger, `1186253` SLABx executor snapshots and
`1186254` accepted-edge pool energy also passed their software contracts.
Thermal contracts `1186260`–`1186262` and `1186264`–`1186266` also passed on
the same pin; the PIFIRA effective-area receipt was QOS-rejected and has no ID.
Brayton bleed cases `1186268` and `1186269` were admitted but fail on an
invalid `require_current` call against `TurbineMapPoint`; this adapter defect
is corrected locally by an owner-bound point freshness check; retry needs a
fresh pin. Cooling and staged-turbine contracts are
still QOS-rejected without job IDs. Fuel-cell thermal coupling `1186272` also
failed at a pre-sample callback freshness guard because its synthetic callback
captured a class namespace. The fixture callback now lives at module scope;
retry needs a fresh pin. Fuel-compression contract `1186274` passed. The core-flood table
ingestion `1186277` passed its offline source identity/table contract. Later
singleton retries `1186306` native fuel compression and `1186310` source-bound
core-flood relative mobility also passed. `1186301` relief failure-prefix
stopped before model entry because its fixture factory was absent. A native
fixture now accepts one 5 ms interval before LH2DT rejects the invalid next
ambient boundary and preserves the accepted prefix; it tests input-failure
prefix handling, not an equipment/EOS failure. The fix awaits a follow-up pin.

The next capture must wait until active code edits are settled, then include
the `.gitattributes` raw CSV byte-preservation rule, updated model APIs/cases,
Cantera synchronization and wall-energy changes, fragment fixture correction,
and the latest risk/mixture/data work. Preserve the current pin's results as
immutable evidence; start the next independent singleton submissions as soon as
the queue/QOS permits, without waiting for all earlier jobs.

## Sensor calibration deferred-case status — 2026-10-31

Job `1185889` (`sensor-time-constant-calibration-recovery`) failed because the
entrypoint returned without an explicit `ValidationOutcome`. Both sensor
calibration deferred entrypoints now return named outcome metrics after retaining
the original assertions. The change is unverified pending retry and does not
constitute a calibration result.

## Latest Hangang result — 2026-10-31

Job `1185860` (`carrier-original-binding`) failed at `cached.setflags(write=True)`:
the bytes-backed cache correctly raised `ValueError`, which the deferred case
did not catch. The local case now asserts write-flag rejection and verifies
`result.require_current()` on the unchanged output. This is a harness failure,
not a carrier model failure; the fix is unverified until replay. It is not
scientific qualification.

## Latest verified Hangang source — 2026-10-31

Snapshot revision `9048413b68025235753242dcb93efb68d9afc477`; archive SHA-256
`5a34abfd652c7dbe6ff6ba41ca7981082e42bffc70533e805c638ef33f99250c`
(3,780,321 bytes); manifest SHA-256
`9034a8102d3bbe6b53310ab122b5a359acb1d8918ba62dc065343999e10eb4ca`; all
1,060/1,060 entries verified. `1185710` (offline core-flood source ingestion)
passed offline metadata/listing hash checks and four staged workbooks. This is
ingestion-only evidence; it does not validate physics. `1185709` CSTR entered and
failed the fixed geometry/site-domain invariant after initialization and
enthalpy fixes. The exact failed subcondition is under investigation; no CSTR
pass is accepted. The local diagnostic patch separates volume, site-density, and
temperature checks with native diagnostics without relaxing bounds. The root
cause is unknown; retry after a fresh snapshot. Both jobs used external logs.
This capture predates the
canonical Krg/Krw mobility guard and staged-turbine fixture correction, so a
newer snapshot is needed to evaluate them. From older `64a31`, `1185715`
(`thermal-target-domain`) and `1185716` (`impact-elastic`) passed synthetic
domain-contracts with outcome JSON evidence; this is not independent validation.
Keep earlier failures tied to their original source snapshots.
Completed `64a31` outcomes: `1185718` thermal-target-exposure-history failed
with ValueError because left-held history length did not match edge/interval
shape, a case input/contract issue, not independent scientific validation.
`1185727` impact-native-pool passed after installing exact pinned optional
`dynamiclh2poolx`, limited to its deferred synthetic contract, not physical
qualification. `1185719` PIFIRA receipt, `1185720`
impact-zero-contact, `1185722` impact-dryout, `1185723` impact-prefix, `1185724`
impact-history-issuer-integrity, `1185725` impact-intercontact-heat, `1185726`
impact-missing-heat, `1185729` impact-refinement, and `1185730`
thermal-target-lossless passed their deferred synthetic contracts. These results
are not independent scientific validation. Logs are external.
From `64a31`, `1185735` failed because edge/sample fixture lengths differed; the
interval helper's adjacent-pair indexing is corrected locally. `1185736`
relief-lift-travel and `1185750` relief-lift-leakage failed because their plan
omitted `fixture_factory`; a local fallback uses reviewed native LH2DT
protection/nozzle/state objects and synthetic conditions, including explicit
wrong-native-state rejection, and remains unverified pending recapture.
`1185737`–`1185740` failed the phase-partition PQ component/mole consistency
checks, not independent validation. `1185752` impact-native-pool passed after
exact pinned optional-provider installation, only for the deferred synthetic
contract. No physical qualification is claimed. Logs are external.

## Previous verified Hangang source — 2026-10-31

Complete snapshot revision `64a31d2784b72f66d66a77accb01e18e3d711a4f` has archive
SHA-256 `3811c36a140e38200a81c6b3d622a9ebb547d2d9350bcd36f8d5f9f1848216cb`
(3,776,678 bytes) and manifest SHA-256
`7bc132d660b514a657068d1b2ad41d6a417849730812437b78eb0fb32583ac1a`; 1,060 of
1,060 entries verified, zero raw/processed data. Jobs `1185638` (CSTR) and
`1185639` (core-flood ingestion) failed after case entry: the Cantera controller
was not initialized before reading `mass_flow_rate`, and numeric Mendeley version
input was rejected because a string was required; local fixes are in progress.
`1185646` failed its synthetic mobility role-rejection assertion, now corrected
to the canonical Krg/Krw phase guard. `1185647`, `1185661`, and `1185662` failed
before staged-turbine scenario assertions because the fixture passed a callable
where `run_open_cycle_brayton` requires a native phase; the fixture is corrected
locally but unverified. `1185664` impact-baseline and `1185665`
thermal-target-refinement passed. Four passes (`1185448`, `1185452`, `1185664`,
`1185665`) do not establish scientific/source/equipment qualification. The
mobility/staged-turbine jobs were accepted after initial QOS refusal. Qsub logs
and results are outside the source tree. `1185550`/`1185557` were launch/log-only
failures from older `8105`; PBS logs polluted the pinned source, and external
log paths now work. Older-source outcomes remain historical.
Job `1185687` (`thermal-target-pulse`) passed its deferred synthetic energy
ledger on `64a31` (maximum residual about `1.14e-8 J`); this gives no scientific
qualification. After QOS reopened, `1185698` (`thermal-target-domain`) and
`1185699` (`impact-elastic`) were accepted; results are pending with external
logs. Initial QOS refusals had no job IDs.

## Prior Hangang result matrix from snapshot 64a31 — 2026-10-31

Jobs `1185448`, `1185452`, `1185664`, and `1185665` entered and passed. Job
`1185450` encountered the Cantera surface API issue and `1185453` failed fixture
import before ingestion. Details of the later 64a staged-turbine precondition
failures and local fixture correction appear above. Older `8105` failures,
including the `1185550`/`1185557` launch/log-only failures, are historical;
external log paths now work. These case results do not establish full
scientific/source/equipment qualification.

## Current continuation — 2026-10-30

Three additional local model increments are now in the deferred plan: a lumped
thermal target with caller-supplied temperature-dependent total heat capacity
and integrated stored-energy accounting; a finite-feed catalytic stirred reactor
using native Cantera mass-flow/pressure control with sampled closure budgets; and
conditional rigid-fragment flight/ground impact from caller-supplied launch data.
The thermal target, catalytic CSTR and fragment flight/impact are
`implemented_unverified`. A source-bound core-flood reader preserves publisher
rows without normalization or fitting; its four CC BY 4.0 workbooks pass the
publisher-listed hashes. The current metadata inventory is 371 cases, 56
profiles and 105 modules; API inventory is 1,455 definitions across 241 modules,
relative imports are 1,748 bound with none missing/unresolved, and 3,941 links
resolve across 340 files with none missing. The Hangang plan contains 97 cases,
19 profiles and 36 modules. These are structural checks only. Hangang snapshots
`341c`, `37752360`, and `13e720` are incomplete, and no case ran from those
snapshots. An earlier summary of the latest Hangang batch was superseded by the
outcome JSON audit: jobs `1185448` and `1185452` entered and passed; `1185450`
entered the CSTR case and failed on unavailable Cantera surface method
`getPartialMolarIntEnergies`; `1185453` entered core-flood and failed importing
its absent fixture before ingestion. These results do not provide full scientific
qualification; a fresh complete snapshot is pending. The
remote archive/manifest checks for `341c` and `37752360` passed, but both omit
`src/h2physics/data`; `13e720` is only an incomplete local candidate, not a
remotely verified complete source. Job `1185303` was accepted by the scheduler,
then failed before entry because snapshot `37752360` omitted
`src/h2physics/data`; a corrected full capture is under construction. Hangang snapshot
341c was verified and its two-case array, job 1185219, failed at launcher
preflight because the site exposes Slurm job variables but the script expected
PBS names; neither case started. Retry `1185237` also stopped before case entry:
subset array indices were being applied to the full plan rather than the selected
case IDs. The local generator now maps the Slurm variables, supplies a temporary
directory, and resolves each pinned expected case ID directly in the plan.
Neither launch failure produced scientific results. The three-case non-CSTR array
was refused by the QOS limit; single-case job `1185303` was accepted by the
scheduler, then failed before its
entrypoint with `ModuleNotFoundError` because capture 377 omitted
`src/h2physics/data`. No model ran. The archive/manifest checks matched the files
in that incomplete capture, so it is not valid for this project. A complete
source capture is being rebuilt from the tracked/nonignored file list.

Static review also found and corrected an uninitialized site-fraction residual
in the flowing CSTR result path. Checksum-verified archive `37752360`
(`37752360ffd3f403ecc57ec7f74b4b3541538b82776061df7ff1f7c673da2b3`) predates
that repair and omitted the full data package. No scientific cases will be
launched from it; a corrected complete snapshot is being prepared.

The current catalog classification is 57/77 (74%) first-level coverage,
not overall completion. No model family was promoted by these changes.

## Latest continuation — 2026-10-30

The first-order concentration-sensor time-constant fitter, accident-chain to
consequence orchestration and shared-nozzle engine boundary are implemented
locally. This continuation also adds unit-safe PEACE channel normalization,
sequential finite-wall parcel impact composition and a source-bound accident /
consequence uncertainty adapter that reuses the existing QMC engine. Deferred
cases are in the Hangang and Nurion source plans. BAM jet-fire labels with
unambiguous units now have a source-bound numeric view, and the porous-reservoir
kernel can bind directly to CoolProp HEOS. Generated case metadata has been
refreshed, but the source archive has not been rebuilt. No scientific cases,
calculations were run locally. The API index now covers 1,442 public definitions
in 238 modules; the relative-import audit finds 1,736 bindings with none
missing/unresolved, and 3,912 Markdown links across 338 files resolve. These
inventories are structural only. The 57/76 catalog classification and historical
59/72 execution checkpoint contain no new verification evidence. Hangang upload
and independent job submission are currently in progress; consult the latest
receipt and scheduler record before treating any case as submitted or complete.

## Latest continuation

The catalog currently has 76 families: 20 implemented, 37 native-adapter-verified,
and 19 implemented-unverified. The single-phase fixed-temperature porous-reservoir
kernel is now registered in the Hangang and Nurion plans; its synthetic case remains
unexecuted. A synchronized fuel-cell trial exchange and a caller-owned compressor
map composition now cover additional Request031/035 boundaries without adding an
integrator or solver-speed solution. A caller-schedule boundary mass/enthalpy ledger
is now added for the piston-engine level, and a phase-resolved mixture separator
history audit strengthens Request032 acceptance without supplying its missing native
integrator. The audit retains accepted-point objects, rechecks nested packet
admissions and recomputes closure summaries on `require_current()`. A HyRAM
plug-to-Gaussian radial snapshot audit is also in both plans; it reports incomplete
when required flux/profile terms are absent and does not verify native HyRAM output.
These contracts remain unexecuted. Hangang now includes a dedicated droplet-impact
profile and sequence case; mixture history is enrolled in the Nurion plan only. The
finite pure-fluid separator callback
guard and selectable small Hangang arrays are source changes only. Refresh the case
inventory and rebuild the source archive before campaign generation.

The bounded mixture inventory V/U flash resolves one fixed-composition equilibrium
state. Finite-volume and adaptive ODE runners now advance changing component stocks using
integrated phase-selective ports and reflashes each endpoint through a provider
constructed for that composition. The runner is explicit first order with
caller-selected steps and bounded to two-phase states; continuous-rate integration,
phase-event localization and wall dynamics remain open. Its Nurion case is unexecuted.
A new
Cantera 3.2 prescribed-flow open-cylinder interval composes fixed-state inlet
reservoirs, scheduled native mass-flow controllers, a bulk-mixture exhaust, and the
existing moving-wall geometry. It records sampled transfer/conservation diagnostics
and retains native owners/failure prefixes; it is not a valve or full-cycle model.
Its single deferred case is enrolled in both Hangang and Nurion plans. The prior
metadata snapshot was 345 cases/54 profiles/94 case modules; the regenerated
Nurion plan contains 362 cases/55 profiles/101 modules and the Hangang plan
contains 79 cases/17 profiles/31 modules. Rebuild the source archive before each
campaign build.
Request035 now has separate Cantera ideal-gas and CoolProp HEOS real-fluid
single-stage H2 compression contracts; only the Cantera result links to Brayton
because the real-fluid/Cantera state conversion is not qualified.

Request029 now adds a single-species dynamic adsorption vessel with LDF uptake,
thermal storage and explicit feed/outlet/heat ledgers, plus phase-specific relief
withdrawal accounting over accepted edges. Request030 adds an evidence-bound
static compressor surge-line margin receipt over existing native map points.
Their six deferred cases are unexecuted; the additional fuel-cell inventory
limiter is accepted-trial feedback and the three cylinder-wall cases remain
unexecuted. No spatial bed, surge dynamics, native depletion event or within-edge
relief depletion physics is claimed.

Request035 now adds a bounded multi-start operating-point solve around the existing
Cantera Brayton reference, with three explicit unknowns and three map/shaft
residuals. A unique result is withheld if any seed fails; multiple roots remain
visible. Request034 adds an optional native Cantera pressure-responsive Valve
boundary with caller-owned opening and coefficient. Its one-way linear pressure-
drop law does not stand in for a compressible nozzle or calibrated valve.

Request032 also has a bounded host-side adaptive ODE with accepted solver states and quality/inventory event termination; it remains distinct from an external native receiver. Request033 adds a host-side accepted-edge record contract, but DynamicLH2PoolX
still does not issue cumulative native integrals; the new case checks the contract
with synthetic Python records only. Request031 now adds simultaneous Cantera 3.2
integration of H2, O2 and water-vapor compartments plus finite stack temperature
inside one ReactorNet. Current policy and thermal partition are explicit caller
callbacks, while depletion events and automatic shutdown remain open. These
requests have new deferred cases; no scientific tests or calculations have run.

Hangang storage directories responded during a read-only preflight, but a later
shared-wrapper status call hung and ended with a broken-pipe/connection-closed
error. No updated archive was transferred and no job was submitted. The latest
973-file source-only archive is prepared locally; its digest and case plan are in
`HANGANG_EXECUTION.md`. Resume remote work only after the user manually
reconnects, using the prescribed `run.sh cpu` path. Never fall back to a new SSH or
SCP connection.

Most recent follow-up checks after the user's reconnection notice returned
`No usable cpu shared connection` and `No usable gpu shared connection`. Neither
wrapper opened a new SSH session or attempted password/OTP authentication, and no
remote calculation was launched.

An additional Durham free-piston engine data candidate is not admitted: its
institutional records conflict on reuse terms and the download timed out. See
`HYDROGEN_ENGINE_DATA_SCHEMA.md`; no files were acquired.

Latest source continuation adds a caller-scheduled intake/fuel/exhaust boundary
mass-and-enthalpy ledger for the piston-engine level plus a post-run, phase-resolved
mixture history closure audit. The engine schedule is not tied to accepted cylinder
steps; the mixture audit neither evolves the flash nor integrates the vessel. Their
deferred cases are staged for later HPC replay, and the source snapshot must be
rebuilt before any campaign. The previous 973-file archive is stale.

Checkpoint sections below retain the development history. Read the final
continuation section and PROGRESS.md for the latest execution evidence.

Current continuation (2026-10-30): a closed-form first-order concentration sensor
response is implemented for caller-supplied piecewise-linear inputs and binds its
issued trace directly to the existing alarm path. The acceptance contract is
registered under the facility-protection Nurion profile and remains unexecuted.
Dryad license URL parsing and acquisition-inventory filtering were fixed; the
O2-chamber file requests still return HTTP 401, so the files remain unacquired.
No local scientific tests or calculations were run. See GAS_CONCENTRATION_ALARM.md,
DEVELOPMENT_LOG.md and the oxygen-chamber receipt for details.

Latest operation-receipt increment: `OperationalScenarioReceipt` fingerprints
the retained LH2DT supply graph (boundary/junction identities, links/component
owners, power readers, inventory readers and selected pump mode). Its deferred
common-clock contract adds a link after receipt issuance and expects stale-receipt
rejection. This is source-identity protection only; the contract is unexecuted and
does not add native coupling or prove route correctness.

The adsorption product mass-flow projection now revalidates its source delivery and
derived mass/rate ledger before reuse; its deferred contract covers post-issuance
source and result mutation. `scripts/audit_public_tree.py` now scans both staged Git
index blobs and current tracked/non-ignored untracked working-tree bytes. It denies
raw-data/document and native binary formats, local paths, common credential markers,
symlinks, submodule pointers, archives and temporary build/output directories. The prior
generic Windows destination example was neutralized in the working tree and Git index;
the latest audit inspected 939 files and passed. `/tmp/` is ignored. This hygiene gate
does not establish copyright or redistribution clearance.

## Actual state

The previous metadata snapshot is 304 cases/51 profiles/74 case modules/76
profile-module associations; eight new deferred case modules are now enrolled, for
an expected 312 cases/52 profiles/82 modules pending refresh. Refresh case/API/
import/link inventories under Python 3.12 before claiming current counts. The last
captured 3,397-link audit, 1,459 relative-import
bindings and 1,291 public definitions are earlier static structural inventories.
Older counts below are dated snapshots.

The full objective in PLAN.md remains active and incomplete. The current catalog
contains 76 consolidated families: 20 implemented, 37 native-adapter-verified,
19 implemented-unverified and none planned. These are catalog implementation states.
The last accepted execution evidence remains 59/72 at checkpoint 6eae06c. The
earlier 30–40% full-programme effort estimate belongs to that historical checkpoint
and is not a current completion estimate; newly added source modules, native-owner
work and deferred scientific evidence are not represented by it.
The dated checkpoint notes below preserve historical counts; use PROGRESS.md,
MODEL_CATALOG.md and the pinned Nurion receipts for current status. Gas/liquid/two-phase
release share one kernel, not three duplicated solvers. This remains a first-model/API
baseline, not full facility qualification.
The last recorded deferred plan contains 304 case definitions across 51 profiles,
74 case modules and 76 curated profile/module associations, before three new case
modules were added. These metadata entries
are plans only and have not been run. The last source audit reported 1,289 public
definitions across 209 modules, 1,459 bound relative imports and 3,397 checked
Markdown paths with no unresolved targets. Refresh the source catalog/profile mapping
before claiming family-level coverage.
The latest source-only additions include explicit single-phase gas diagnostics,
a native-profile counterflow heat-release integral, a hydride loading-window
capacity result, quasi-steady permeation history, anonymous pipeline-column
lineage, selected facility residual series, bounded valve-map inversion,
observation partition provenance, an exposure-to-thermal-target bridge,
bounded single-gas mixture P-U inversion, staged photochemical conversion, sampled
SIF threshold and per-load-block summaries, accepted heat-exchanger wall-transfer
series, gas/surface species-inventory views, a typed native UH2SC output-series view,
finite spherical-shell conduction, cylindrical-shell diffusion, caller-threshold
sampled hydrogen concentration alarm logic with same-clock k-of-n voting, and
native energy-on catalytic gas/surface response against a fixed-temperature
boundary.
Their new contracts are deferred and do not close native receiving-engine work or
scientific qualification.
The common-clock operational receipt also accepts explicit scheduled protection
replays only when they retain the exact accepted dynamic run, clock/window and
caller binding evidence; the path remains offline and prescribed.
The cylindrical transport result now rechecks that its mobile/trapped fields,
surface amounts, face integrals and inventory residuals still reproduce the exact
successful integration it retains. Its altered-output contract is registered in the
existing cylindrical diffusion case and remains deferred.
The native hydride-compressor trace likewise rechecks its solver arrays, stage
snapshots, audited points and ledgers before returning summaries; its mutation
contract is deferred to Nurion.
The finite-speed pump now applies a new speed target only after its exact command
start sample; each completed interval uses the command active at its left edge.
Its boundary-transition contract is deferred to Nurion.
OEDI fatigue series and dataset records likewise require one-time issuance from the
checksum-validating workbook reader, so direct source-labelled observations cannot
claim the pinned workbook provenance. The negative contract is deferred.
The line-source jet-radiation field now requires a per-result evaluator issuer;
direct construction and dataclass copies cannot reseal altered outputs against an
admitted HyRAM flame. Its existing radiation integrity case remains deferred.
The obstacle-resolved FDS result likewise requires its original runner issuer and
fingerprints the captured process, native artifact index, parsed tables and audit
arrays. Direct construction, copied receipts and post-capture mutation are covered
by its existing dormant cases.
The open hydrogen Brayton reference uses native Cantera HP equilibrium and
frozen-composition expansion with caller-owned efficiencies. A new optional path
binds one admitted turbine map point to that reference through explicit pressure,
flow-conversion and evidence terms; compressor maps, shaft closure and qualification
remain Request035.
Recent source additions include a bounded single-gas mixture PU inverse, a sealed
exposure-to-target input bridge, valve effective-area inverse selection, hydride
loading-window capacity, quasi-steady permeation history, anonymous pipeline-column
lineage, counterflow heat-release integration, and direct facility-node residual
series. Their new contracts are deferred; none supplies a missing native solver or
confers model qualification.

The source-only inventory records 45 curated cluster profiles with 58 profile-module
associations, 1,253 public API definitions across 204 modules, 3,255 local Markdown
paths across 297 files with zero missing paths, and 1,388 bound relative imports with zero missing
or unresolved entries. The deferred metadata plan is 263 cases across 45 profiles
and 55 case modules. These inventories inspect source and case metadata only; no
case entrypoint, physical model or Nurion job has been run for this continuation.
They do not establish physical accuracy.

This continuation adds a callback-state signature for radial failure histories,
immutable and self-consistent elastic-cylinder fields, integration-issued reduced
hydride traces, and factory-issued liquid-accident mass/energy receipts. It also
adds public thermal utility exports, post-run PV-electrolysis/thermal and fuel-cell
activity composition, site-resolved local adsorption sensitivity at the qualified
anchor, a typed per-bin SLABx-LH2 source/run ledger, and a consequence-evaluator
handoff that preserves accepted source/provider objects. The post-run bridges do
not introduce feedback, transient plume memory or consequence physics. All related
cases remain deferred; no test, model, compilation or Nurion execution was performed.
Additional local interfaces expose an original-receipt facility operation report,
join contiguous relief/cooldown phase receipts at exact shared events, and recheck
OEDI fatigue comparison freshness before returning reported points.
The materials transport bridge also connects caller-supplied solubility/fugacity
inputs to finite-volume diffusion at its existing temperature state. Request032 and
Request033 remain fail-closed because their native owners do not yet supply the
required changing-mixture accepted states or pool energy terms.
Current seam review also keeps Request031 (simultaneous multi-reactor fuel-cell
feedback) and Request034 (native engine flow/control and accepted-cycle ownership)
open. Acquired embrittlement observations do not contain a matched solubility/
diffusivity set, so no material coefficients were fitted or assumed.

The latest source continuation adds `MixtureInventoryStateAdmission` for accepting
an existing native mixture packet against target species moles, vessel volume and
internal energy, plus phase-resolved volume/U diagnostics. It also hardens immutable
array snapshots, HyRAM Gaussian result summaries, signed radial SIF outputs and
turbine-map source seals. Four additional gas-composition deferred cases are now
registered under the CoolProp/LH2DT profile; none has been executed. Request012,
Request027, Request032 and Request035 receiving boundaries remain incomplete.

Latest local additions (2026-10-30): finite-hydride ported integration, facility-risk
receipt freshness, exact-continuation pool-energy handoff, and two source-bound data
readers. The buried-pipeline reader retains 12 CC BY 4.0 CSVs' publisher hashes and
anonymous columns. The open-channel reader retains two CSV header rows and source
records from 22 publisher-listed CC BY 4.0 case ZIPs; the 23rd attachment is the
ReadMe. Current Figshare metadata and all local file sizes/checksums match. It does
not infer sensor time units or physical
column meanings. These deferred cases have not run; mapping, native receiving work
and scientific qualification remain open.

## Local continuation — 2026-10-30

`DispersionScenario` now validates the required provider inputs at construction and
rejects fields from the other release family. `OpenBraytonRun` binds native species
thermochemistry, reaction definitions and multipliers to its result. `QualifiedGasTable`
binds the underlying CoolProp state/module/lock identities and reported backend/fluid
names. `HyRAMComponentFlowProjection` revalidates its parent finite-source receipt
before exposing component allocations. `TableQualification.meets_speedup_target()`
compares the retained reference/table time-per-call ratio against an explicit caller
target. This does not change property-error or enthalpy-identity qualification and
does not provide a repeatability guarantee beyond the recorded timing sample.
`ScenarioResult` now requires a one-use
issuer from `OperationalScenario.run()`, rejecting direct construction and
`dataclasses.replace()` copies. `HydrideCompressorTrace` requires a one-use native
integration issuer with evidence, segment-clock and event-endpoint checks. These
contracts have deferred cases; no
validation case, physical calculation, benchmark, compile, SSH or Nurion job was run.
Request012/031/032/033/034/035 receiving work remains open.

Latest source metadata is refreshed above after the 2026-10-30 continuation; see that
current snapshot for the case/API/import/document totals. Older dated sections retain
their original counts as historical records.
These inventories describe source structure and do not establish scientific validity.

All later dated checkpoint narratives in this file preserve historical snapshots.
Their old inventories and percentages are not current; use the snapshot above and
the latest continuation entry in PROGRESS.md.

Latest source increment hardened `OperationalScenarioReceipt` post-bind content
integrity and repository metadata redirects; unsafe targets are rejected before
following, and OpenEI attachment URLs are type-checked before suffix handling.
Parallel coding added a fuel-cell water-phase/activity consistency gate, mixture
phase-withdrawal mass/enthalpy ledgers, and a freshness guard for preferred-dispersion
execution receipts. Their deferred contracts are registered, not executed. Request031
simultaneous feedback, Request032 changing-mixture flash/events, and external HyRAM/
SLABx-LH2 finite/transient source contracts remain open. Pool energy receipts now
pin energy reference/vapor phase, adsorption bridges pin original qualification and
state identity, and facility handoffs cannot reseal mutated provider receipts. The
preferred-dispersion API is exported from `h2physics`. The development build
contains all192 current package Python files byte-for-byte in both wheel and source
archive and passed exclusion/marker audits. Exact hashes are recorded in
`research/release_audit.md`; that report is intentionally excluded from the archive
to avoid a self-referential checksum.

Historical deferred counts below preserve their dated checkpoints only. The earlier
mapping of14 implemented_unverified families to case IDs is not current plan coverage.
After the later 2026-10-29 continuation, current metadata is 222 deferred cases,
40 profiles and 41 case modules; 1,183 public definitions; 1,183 bound relative
imports; and 2,945 checked local Markdown paths. Direct CORA source-row/series
identity, observation-collection, and HyRAM native-result freshness guards were
added with deferred contracts. Read PROGRESS.md for this checkpoint; the ongoing
implementation goal is still active and scientific/Nurion verification remains
deferred.
The same continuation also checks SLABx-LH2 finite-source freshness after callbacks,
requires evidence and full admission for directly constructed facility-dispersion
handoffs, and reconstructs absolute bed inventory totals before direct audit sealing.
Those additional guards are deferred, not scientifically executed.
Attachment downloads now use the credential-free HTTPS redirect opener, and H2
batch-handoff evidence/ledger identity is sealed against post-bind relabeling. These
contracts also await the future Nurion campaign.
The direct finite-hydride trace gate is registered as a CoolProp-enabled deferred
profile for forged-ledger rejection; current counts are 222 cases / 40 profiles /
41 modules. No case, model, or Nurion job was executed.
The repository is local on main; no remote publication was performed. Other repositories
were not edited or messaged. Read AGENTS.md, RIGHTS_AND_PROVENANCE.md and ARCHITECTURE.md.

The detailed Korean user/research manual is USER_GUIDE_KO.md. API.md and
SOURCES_AND_METHODS.md describe native contracts and public scientific sources.

The last executed source checkpoint6eae06c provides59/72 first levels, about82%. Actual
finite O2 transport, ordinary-air native multisegment thermal state and learned
native physical-residual monitoring add explicitly bounded partial capabilities.
The full-programme effort estimate stays30-40%; independent apparatus/field
validation and the accepted full accident chain remain open. Jet-fire remains
diagnostic/rejected where mass/caloric acceptance fails. Request022 and the
latest checkpoint section below give exact receiving/reproduction boundaries.

## PEM EIS to stack-ohmic integration — 2026-10-29

`adapters.PemOhmicLossBinding.from_fit(...)` binds an exact PEM sweep or an
explicitly ordered set of sweeps' shared complex-observation `FitResult` to the
archived PEM source/member and preceding non-EIS DC context. For multi-sweep fits,
the fit row sequence and fingerprint must match the ordered concatenation and
the caller must select the operating sweep used for stack context. The bridge
maps fitted cell R0 times active cell area to the existing `OhmicLoss` and is now
used by `scripts/fit_pem_impedance.py`; no new circuit, stack or process solver
was added. `extend_loss_mapping()` returns `PemStackLossMap`, which can be passed
directly into `HydrogenStack`, retains the source binding and any evidence for
coexisting ohmic terms, and prevents accidental name replacement/double counting.
Bridge admission requires a full numerical fit rank and a non-bound selected coefficient;
rank/condition diagnostics are retained and any maximum condition gate is caller-declared.
The report script keeps curve diagnostics when only the stack transfer is withheld.
Whole-cell effective R0 may include contacts/leads and is not an
identified membrane term or qualified DC loss. A caller-owned temperature
multiplier is optional and is not inferred from EIS. The case contract is in
`validation/cases/model_selection.py`; it is authored only. Static syntax/lint
checks passed, while the contract, data replay and every physical model remain
unexecuted under the current Nurion-first verification preference. The metadata
plan contains228 cases across40 profiles and47 modules, not execution evidence.

## Reproduce executable evidence

From the repository root with Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[thermo,data,chemistry,hydraulics,eis,pool,test,dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check src tests scripts
.venv\Scripts\python -m pip check
.venv\Scripts\python scripts/model_inventory.py
.venv\Scripts\python scripts/verify_reduced_models.py
.venv\Scripts\python scripts/check_cantera_integration.py
.venv\Scripts\python scripts/benchmark_properties.py
```

Historical native-enabled full suites at the earlier consequence checkpoint:552 pass with main SciPy1.18.1 (124.21s) and552
with compatible SciPy1.16.3 (164.73s). Default without the separate HyRAM target
passes530/skips22; those skips are not execution evidence. Ruff/dependency checks
pass. Prior local commits
are `cd1ad53` (first baseline, 44 tests), `f5b48be` (observation/PSA, 53 tests) and
`281b760` (shared nozzle, 66 tests), `e564c8e` (public discharge data, 81 tests) and
`9ca8e6b` (native equipment/property reuse, 91 tests) and
`801ea49` (finite-device isolation, 99 tests), `b84f224` (combined finite supply/Darcy, 111 tests)
and `1067e69` (measured PEM spectra, 117 tests), `64e4e20` (dynamic pool/source, 127 tests),
`74e3ed5` (native gas-plane/jet contracts, 150 tests).
The equipment continuation adds native phase-resolved supply composition, explicit
heat/power ledgers and a checked single-flash native property facade.
The next continuation adds finite line/vaporizer storage, prescribed isolation windows,
accepted-solution identity matching and per-device fluid/wall conservation.
The combined supply continuation adds the reusable finite phase-port tank/pump/line/
vaporizer builder, explicit native modes, command-aware sampled integrals and two-wall reader.
Historical
Windows/CPython 3.12.14 PEM environment (41 recorded dependencies, excluding this project) is in
`requirements/validation-windows-py312-pem-2026-10-27.txt`. The earlier 20-dependency
equipment snapshot remains in `requirements/validation-windows-py312-2026-10-27.txt`.
These are observed reproduction records, not cross-platform locks.
The pool environment has 42 recorded dependencies and is in
`requirements/validation-windows-py312-pool-2026-10-27.txt`. The latest jet environment
has 43 in `requirements/validation-windows-py312-jets-2026-10-27.txt`, plus a separately
installed exact DEGALI source snapshot from `requirements/native-degali-pinned.txt`.
Re-run relevant checks after changes; do not infer unperformed validation from test count.

## Data and exact replay

At this checkpoint 26 collections are cataloged; 24 have acquired attachments: 268 files,
4588753807 bytes. Raw files are local under ignored `data/raw/`. Public receipts retain
versions, DOI, authors, rights, SHA-256, publisher checksums and omissions/failures.
All required baseline acquisitions have ended; no download process must remain running.

The complete MHC compressor qualification now covers29 experiments/186 sheets/
182 recorder exports,35 member hashes and all stored XML numeric/formula/error
content. The final bounded local scan took311.92s. Read HYDRIDE_COMPRESSOR_DATA.md:
520726 populated recorder rows retain clocks, masks, source/experiment dependence
and unresolved gauge/reference-flow/spatial roles. Raw/selected copies are not
independent validation splits. The final data script/loader/tests are fingerprinted;
no full data-audit process needs to remain running after this checkpoint.

```powershell
.venv\Scripts\python scripts/replay_data.py hydrogen-channel hydrogen-sound-speed ab2-hydride-tank
.venv\Scripts\python scripts/acquire_data.py --keys hydride-compressor --maximum-mb 500 --maximum-file-mb 500
.venv\Scripts\python scripts/acquire_data.py --keys elvhys-shock-tube --maximum-mb 1000
.venv\Scripts\python scripts/audit_data.py
.venv\Scripts\python scripts/check_channel_ingestion.py
.venv\Scripts\python scripts/check_hydride_ingestion.py
.venv\Scripts\python scripts/compare_acoustic_data.py
.venv\Scripts\python scripts/check_static_ingestion.py
.venv\Scripts\python scripts/fit_sofc_reproduction.py
```

Replay pins recorded bytes; discovery acquisition may see newer metadata. ELVHYS has
42 numeric/text files (39 CSVs); media are excluded. Earlier long-job version-label and
checksum parsing failures were repaired. PEM acquisition succeeded. Dryad access still
returns 401/403 and is not claimed acquired. Read DATA_QUALIFICATION.md before fitting:

- Channel: 22 source-flow experiments; concentration clock unit/alignment unresolved.
- AB2: seven sheets, 355388 shell-temperature records; pressure/MFC reference unresolved.
- Compressor v1.2: actual workbooks; logger offsets, a reported bad sensor and an argon
  thermal case mean not every column/workbook is a synchronized hydrogen experiment.
- Acoustics: 761 of 1027 points compared; spin/pressure exclusions and EOS-development
  overlap remain explicit. Large historical deviations are retained.
- LOHC/PCT/photo/dispatch records include computed/simulated values, not independent measurements.
- Cryogenic MOF record uses Etalab-2.0, updated 2026-08-25T11:13:19Z; preserve source/date.
- Non-time ingestion covers 36 MOF branches/860 rows and 16 SOFC curves/9080 records.
  MOF pressure/STP/uptake ambiguity remains explicit. SOFC voltage origin remains unresolved.
  The held-out 800 °C curve reproduction gives RMSE 0.0060712 V, with scaled condition
  number about 40907.5; it is not independent experimental validation.
- Independent free-spreading LH2 pool/impact and material permeation evidence remain priorities.
- PRESLHY: all ten published attachments (1313096235 bytes) acquired and checksum verified.
  The two previously throttled cold bundles completed after explicitly spaced requests.
  Container inspection finds 160 workbook sheets with no errors; sheets are not independent
  experiment counts. Four 1 mm warm experiments are used in the conditional comparison below.
  No download process remains active at this checkpoint.

## Native engines and numerical decisions

The optional MIT LH2DT public snapshot is installed separately:

```powershell
.venv\Scripts\python -m pip install --no-deps --target artifacts/native_packages https://github.com/lyullee/lh2dt_models/archive/b2f276333c1b1793c39f25763703d196d36742ec.zip
.venv\Scripts\python scripts/check_lh2dt_integration.py
```

Version 0.1.2: exact property agreement at sampled states; 0.01 kg synthetic tank mass
increase over 10 s; about 7.04e-10 J energy residual. This checks the selected native
homogeneous boundary, not experimental accuracy or spatial-model qualification.
PRISM/SLAB and station SciPy incompatibilities are documented in DEPENDENCIES.md.

Cantera 3.2.0 receives a native phase factory and explicit mechanism hash/domain.
Python reads the installed mechanism because C++ lookup loses non-ASCII Windows paths.
A 1000 K fitted-thermochemistry jump remains visible in energy diagnostics. Flame grid
and domain refinement and reactor conservation are in `research/native_cantera.md`.

For 0.1–90 MPa and 230–400 K, qualification uses 1000 interior PT states plus four corners
and 2000 additional PH/PS evaluations. Native BICUBIC/TTSE energy fails the 1e-7 scaled
identity gate despite small property errors. Explicit `derive_from_h_p_rho` passes sampled
gates and records corrections. It does not establish complete differential consistency.
The default remains library energy; no gate is relaxed. Timing uses full public mixed-input calls.

PSA-Dyna 0.1.0 is separately installed at public MIT revision
`a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6` in the same ignored native-package target:

```powershell
.venv\Scripts\python -m pip install --no-deps --target artifacts/native_packages https://github.com/lyullee/psa-dyna/archive/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6.zip
.venv\Scripts\python scripts/check_psa_integration.py
.venv\Scripts\python scripts/check_psa_bed.py
```

Nine equilibrium/gradient states agree; a closed warm loading-LDF bed has component/energy
residuals about 8.33e-17 mol / 4.41e-8 J. Native Bed temperature guards remain 100–1000 K;
request 005 specifies the proper property/phase/inventory extension. See NATIVE_ADSORPTION.md.
No PSA cycle or cryogenic bed qualification is implied.

`ObservationTable`, `Variable`, group splitting and the native fitting API are implemented.
Input/model fingerprints, per-column origins and bounds/rank diagnostics are retained.
Reference-dependent bases survive time-series loading too. No artificial time or silent
absolute-pressure declaration is introduced for unresolved static data.

## Shared release and actual tank depletion

`h2physics.release` implements one homogeneous isentropic equilibrium nozzle for all
inlet phases. Inputs include the full stagnation state, explicit back pressure and effective
area interpretation. Endpoint-inclusive pressure search and refinement retain diagnostics;
EOS failures are surfaced. NASA ideal-gas formulas and CoolProp gas/liquid/saturation/two-phase
paths are checked in thirteen added tests, including immediately around the choking
transition. No independent real-fluid critical-flow validation is claimed.

```powershell
.venv\Scripts\python scripts/check_release_integration.py
```

The script uses the exact optional LH2DT snapshot above. Gas releases 0.00942058856 kg
over 5 s and the equilibrium cryogenic bulk case releases 0.0115929510 kg over 2 s.
Maximum tank energy residual after the numerical correction is about 2.20e-9 J; independent accepted-node quadrature
errors decrease approximately fourfold per step halving. Separate isolation windows give
zero subsequent boundary mass. Source/clock/spatial identity and explicit window termination
are retained; no atmosphere/ground transfer is inferred from nozzle quality.

The native tank overrides every negative flow's enthalpy with bulk enthalpy. Consequently
`Lh2dtBulkNozzleOutflow` is bulk-only; request 001 now specifies phase-selective withdrawal
and phase-depletion acceptance. Request 006 specifies PRISM delegation to this shared HEM
kernel, fixing ambiguous P/T input and omitted back-pressure endpoints without retaining
equivalent solvers. See RELEASE_AND_SOURCE.md and `research/native_release.md`.

## Public discharge observations and conditional comparison

The new `radar-kit` provider supports the CC BY 4.0 PRESLHY collection 10.35097/1187.
Read the receipt for actually acquired/deferred files; a 429 stops further dataset network
requests and retains Retry-After. Original bytes/metadata stay under ignored `data/raw`.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys preslhy-discharge --maximum-mb 1400 --maximum-file-mb 260 --include-suffixes .zip .pdf --minimum-download-interval-s 60
.venv\Scripts\python scripts/compare_discha_release.py
```

The 1 mm warm bundle contains four workbooks. `data.preslhy` retains separate recorder
series, source synchronized/original clocks, units and byte hashes. `data.sampling` requires
explicit common clocks, edges/counts or interpolation gaps; it does not infer alignment.
Generic Excel loading supports different measurement/time header and data-start rows.

The conditional balance uses measured P/T and EOS-reconstructed inventory over 2–10 s.
One complete approximately 20 bar run is held out; the fitted effective-area factor is
0.6110743, fitting RMSE 0.0226499 and held-out RMSE 0.00361222 of initial-window inventory.
Mass and temperature are not independent predictions, closed-TC gradients exceed 20 K,
and valve/line and reference assumptions remain. No independent flow qualification is claimed.
See PRESLHY_COMPARISON.md and `research/discha_inventory_comparison.md`.

Data exposed flat maxima that failed the original pressure gate. Single-phase sonic
bracketing and local coordinates preserve the unchanged gates; negative results and both
regression states are in `research/nozzle_search_coordinates.md`. Quality roundoff remains
strict by default; explicitly budgeted endpoint adjustments retain raw state/maximum diagnostics.

## Native equipment, finite supply and property cost

```powershell
.venv\Scripts\python scripts/check_lh2dt_property_provider.py
.venv\Scripts\python scripts/check_equipment_network.py
```

`Lh2dtEquipmentNetwork` composes actual native components and state factories with signed
port transfers, separate heat/shaft power and independent node/boundary ledgers. A checked
structural graph validates every RK stage. `Lh2dtSharedValve` delegates to the shared nozzle;
its `.nozzle` source state differs from the remote mixed enthalpy used by the two-port graph.
Actual native component results remain available. Missing momentum is not zero.

The native stratified liquid port feeds a mapped pump, heated pipe/vaporizer and shared
valve. Authored synthetic parameters deliver about 0.00309043 kg over 2 s. External mass/
energy residuals are about 1e-12 kg / 3.4e-6 J; three steps meet the declared agreement gates.
A mathematically closed but insufficient-NPSH point is rejected. Finite pipe/vaporizer
storage, complete isolation and independent equipment qualification remain open.

The original generic network omits the stratified derivative's two ambient heat terms.
`stratified_node_with_heat_ledger` only exposes their sum; the 0.1 s closed-tank residual
changes from about 5.52 J to 5.84e-12 J with identical native phase equations. Request 007
specifies receiving heat/accepted-step/stage-admissibility contracts. The evidence currently
asserts the pinned five-solves-per-step profile and retains only accepted source samples.

`Lh2dtLowLevelProperties` supplies only the tested native property subset through protected
HEOS states. Sixty mixed native-state queries agree; measured state-interface/complete-solver
speed ratios are about 22.7 / 2.34 respectively. Same-step delivered mass/pressure differences
are about 4.2e-12 / 9.1e-14 relative. No cold table/fallback is used. The explicit 1e-8 quality
budget matches the reviewed native endpoint policy; diagnostic raw values are retained on
the host facade. Unsupported native methods/type-checking constructors remain unsupported.
See NATIVE_EQUIPMENT.md and `research/native_*provider.md` / `native_equipment_network.md`.

## Finite stored devices and prescribed isolation

```powershell
.venv\Scripts\python scripts/check_dynamic_inventory.py
```

`Lh2dtDynamicEquipment` delegates integration and physical equations to the existing
native finite pipe/vaporizer nodes. It stops at declared command times and translates
derivative/ambient/continuous-control callbacks to the absolute operation clock. Accepted
rows match actual checked native solutions by identity, without a five-call profile.
Every node declares external heat and independently closes fluid-plus-wall storage.
The new portable tests include missing heat, wrong ledgers/identity and overwritten-boundary
failures. DYNAMIC_INVENTORY.md contains the public API and restart/left-right-limit semantics.

The synthetic pair closes feed/outlet at 0.137 / 0.411 s. About 4.6627e-6 kg continues
discharging after feed closure. Three steps (0.1 / 0.05 / 0.025 s) agree; per-node mass/
energy residuals are around 1e-18 kg / 1e-13 J. After both ports close, assembly mass stays
fixed while heat and internal transfer continue. Reversed transfer and an absolute-clock
analytic wall limit pass. Unsplit controls bias final mass by about -6.95e-7 kg despite
closing their fluxes. Wrong wall storage and replacement of a conserved fluid boundary fail.

The earlier cases are now combined by the following public assembly builder. Pressure-trigger
localization, phase/mass exhaustion, finite valve stroke and independent experiments remain
unfinished. No new dataset or receiving-repository change was needed for these levels.

## Combined finite supply, native modes and sampled integrals

```powershell
.venv\Scripts\python scripts/check_finite_supply.py
```

`assemble_lh2dt_supply` accepts actual native models, initial states, factories and explicit
branch power readers. It returns the checked network/driver, commandable pump assembly,
original outlet and native models. `Lh2dtModeSwitch` delegates the selected native branch
and preserves the actual result plus its power. Unknown modes, invalid maps and missing
power are errors; failures never select isolation. The ideal isolated branch uses an
already closed shared valve. Real rotor/casing dynamics and native zero-speed behavior
are the subject of new request 008, prepared locally and not sent.

The synthetic full assembly uses a finite two-phase/two-wall tank, mapped pump, stored
line, explicit restriction, stored vaporizer and outlet. Commands occur at 0.037/0.073 s.
The short case delivers about 3.0352e-5 kg, including 1.5097e-5 kg after feed isolation.
Native per-node balances and independent sampled delivery/shaft/ambient quadrature pass;
the latter recomputes heat from actual wall temperatures and declared UAs. The original
property path agrees with the single-flash path at a common step. Timings in the new record
describe this separate workload rather than extrapolating earlier ratios.

Isolated heating to 1 s reverses internal transfer. The initial 0.0025/0.00125 s pair
conserves mass/energy but fails the unchanged 1e-6 final-state gate. The 0.00125/0.000625 s
pair passed its final-state gate, but a finer accepted transition point then exposed a
separate native constitutive failure: reported momentum 0 Pa versus about 44.31 Pa from
reported friction/flow. A bracketed root with the same discontinuous friction law also
fails its residual gate. The corrected supply case now explicitly selects the direct
MIT fluids 1.3.1 Churchill_1977 correlation and the one shared `solve_darcy_flow` kernel.
Native HEM viscosity and fluid/thermal states remain native. This is a declared empirical
closure change, not proof of greater experimental accuracy. Corrected accepted Darcy loss
is checked at 0.01 Pa alongside the retained time/inventory gates. HYDRAULICS.md and new
request 009 specify consolidation and public native correlation/viscosity capabilities.
`integrate_equipment_rate` retains both command limits and returns explicit linear-sample
quadrature metadata including basis/units/clock. It is separate from native RK-stage flux
integration. FINITE_SUPPLY.md and `research/native_finite_supply.md` contain exact APIs,
parameters, positive/negative results and hashes. Local numeric debug caches are ignored.

## Measured PEM continuation

The measured PEM continuation is reproducible with:

```powershell
.venv\Scripts\python scripts/replay_data.py pem-crossover
.venv\Scripts\python scripts/check_pem_ingestion.py
.venv\Scripts\python scripts/fit_pem_impedance.py
```

Read PEM_IMPEDANCE.md, `research/pem_ingestion.md` and `research/pem_impedance.md`.
The full four-member hash audit covers 23764321 rows; selected initial protocols yield
144 spectra with 3312 frequency readings, not 144 independent cells. There are 18
sweeps/counter instead of the nominal 17 levels. Instantaneous AC samples do not establish
DC setpoints; the explicit 120 s gap leaves 28 operating contexts unknown. Raw/processed
GC and block/reaction temperature remain distinct. The checksum-pinned archive and all
normalized caches are local ignored files. After the first full-member audit,
`check_pem_ingestion.py --use-cache` accepts only matching archive/profile/content hashes.

The native optional impedance 1.7.1 CustomCircuit predicts through the original common
observation/estimation API; package source hash and analytic RC-limit verification are
recorded. The extra explicitly includes pandas because the native modern-Altair import
otherwise failed. It does not require JSON or execute source notebooks. Fitting one
12 A spectrum per cell gives small in-sample errors, but four of eight whole repeats
and all three fixed Reference coefficient transfers fail the unchanged diagnostic.
Scaled Jacobians are ill-conditioned and Reference L0 reaches a bound. Do not interpret
the CPE/whole-cell R0 as uniquely identified catalyst/membrane properties. R0×area reuse
in OhmicLoss demonstrates units/API only. No new receiving-project change is necessary
for this level. Native plotting/fit/serialization, linearity/KK consistency, low-frequency
mechanisms, crossover, thermal inventory and degradation remain unqualified. Extending
measured production must preserve these failed targets and source-specific boundaries.

## Native pool and interval-source continuation

```powershell
.venv\Scripts\python -m pip install -e ".[pool,test]"
.venv\Scripts\python scripts/check_pool_integration.py
```

Read NATIVE_POOL.md, request 010 and `research/native_pool.md`. The native PyPI pre-release
0.2.0rc2 matches GitHub revision `6a700e8e183039bbb81803bacc416f6c9117ed71` by module
bytes. Actual config/input/result objects remain available. The ground input is already
saturated normal-Hydrogen liquid at ambient pressure, with a finite named absolute clock;
para labels, unknown rainout and initial radial inventory are not silently supported.

An independent step-input integral catches an extra native 0.00025 kg supply step at a
near-knot isolation time, even though native internal mass closes. The retained positive
profile explicitly chooses a 1e-10 s boundary clock budget and records corrections; the
finest maximum is about 4.44e-15 s. Default budget is zero. Three coupled coarse pairs
fail the fixed 1% inventory/supply agreement target, and the 0.0025/0.00125 m pair passes
at about 0.734%. Time comparisons pass 0.2% but are nonmonotone; do not infer an order.

Conservative cumulative-evaporation intervals emit 0.0282498734 kg, including 0.0244166527 kg
after input isolation. Sparse last-step-rate trapezoids give 0.0319561560 kg. A zero reported
radius is not a dry pool. Final tiny liquid remains and the source ends as window_end.
`IntervalMassSource` preserves mass under explicit constant-mean rebinning, with clock and
window guards. Current vapor state is explicit saturation; interval footprint, vertical
momentum and independent heat are missing physical work, not default zeros.

E3.4 metadata establish eleven CC BY-SA attachments; all remain withheld by the current
permissive-data policy. No upstream digitised points or private observations are reused.
The source receipt retains authors/version/license/metadata hashes and omissions. Request
010 specifies native event correction, explicit fluid/spin/reference providers, radial
checkpoints/restart, source area-time distributions and independent heat accounting.
No receiving repository was edited or messaged. Keep the independent clock/input failure
and unsuccessful coarse gates when continuing; complete pool/atmospheric validation is open.

## Native gas-plane and calm-jet continuation

The host adapter is `src/h2physics/adapters/degali.py`; working Python composition is
in NATIVE_JETS.md. Install the exact separately reviewed native snapshot rather than
assuming the PyPI 0.1.0 release is equivalent to its 0.3.0 source version:

```powershell
.venv\Scripts\python -m pip install -r requirements/native-degali-pinned.txt
.venv\Scripts\python scripts/check_degali_integration.py --plot
```

The native snapshot used here is isolated at `artifacts/native_dispersion_packages`;
add `--native-packages artifacts/native_dispersion_packages` when reproducing that layout.
PyAMG 5.3.0 is needed by the broad actual native import. The main 43-dependency snapshot
does not include that separately installed DEGALI source; keep both reproduction records.

The full two-fluid research command currently **exits nonzero by design after writing
the report**, because its para-H2 energy gate fails. It must not be counted as a passed
integration run or grouped into a shell command that hides its status. The normal-H2
321-point run passes all declared gates. The complete report is `research/native_degali.md`.

The one shared nozzle supplies actual native ambient expansion, preserving mass,
effective-area pressure momentum and h+KE for normal/para gas. Virtual plane position
and the pressure-area interpretation are explicit. Native source enthalpy carries the
static ambient difference and separate real-H2 reference before native ideal-component
conversion. A declared orthonormal global section maps the actual source; liquid,
reference/frame mismatch and unqualified ground intersection are rejected.

The native density-profile four-flux roots fail for both authored cases. Explicit T/Y
profiles initialize correctly. The native analytic Gaussian-density force is inconsistent
with their actual density, so an original thin native subclass replaces only that
vertical source by the actual native radial integral. No solver, coefficients, native
file or global function is replaced. The version-sensitive protected Jacobian hook and
its public replacement are documented in request 011.

Warm finest species/M errors are about 1e-8; energy error about 0.025 W against 0.118 W.
Cold 81/161/321/641 energy errors are about 2.525/2.769/0.524/0.346 W against a fixed
0.238 W budget. Even though cold endpoint/spatial and mass/momentum checks improve,
the default API rejects it and retains actual failed results. Do not relax the budget,
reset the reported energy or cite the endpoint agreement as full conservation. The
preliminary tight DOP853 cold diagnostic was interrupted; no completed success is claimed.

Twenty-three new contract tests bring the full suite to 150. Malformed native fields/
arrays retain the actual result at `error.native` without a misleading physical audit.
Whole-mixture predicted spatial
observations are immutable and carry phase semantics, without a fake time or all-gas
gas-mole-fraction conversion. Numerical verification does not qualify a finite isolated
source, a pool launch, a probe operator, crosswind/ground interaction or field accuracy.
No new external observation files were acquired in this continuation. Existing data
qualification and rights records remain applicable; the broad objective remains active.

## Measured spatial jet continuation

Planning effort estimate remains 25-35% for the full programme; 30/72 families with a
first executable level is about 42% coverage, not full completion. Read PROGRESS.md for
the requirement/stage distinction. Native-adapter and partial implemented counts stay
fourteen and sixteen; this continuation deepens existing families rather than inventing
new coverage entries for a loader or numerical reference transform.

Read HYTUNNEL_JETS.md and `research/hytunnel_jets.md`. Acquisition now includes all seven
mechanical-ventilation attachments; the extra source-description file adds 706086 bytes.
Four concentration workbooks contain 42 sheets and 5256 spatial sensor rows. These are
jet scans, not time series or a well-mixed enclosure inventory. Repeated coordinate grids,
ambient header/value conflicts, a He/H2 label conflict, offsets and inconsistent summary
order stay explicit. No guessed column swap, tracer rename or negative-to-zero repair is
applied. The source flow-velocity workbook still needs a qualified spatial wind boundary.

```powershell
.venv\Scripts\python scripts/acquire_data.py --keys mechanical-ventilation --include-suffixes .xlsx .zip .pdf --maximum-mb 20 --maximum-file-mb 15 --workers 1
.venv\Scripts\python scripts/compare_hytunnel_jets.py --native-packages artifacts/native_dispersion_packages --plot
```

The full command currently exits nonzero after retaining the report. `--case`/`--quick`
diagnostics write ignored partial reports, preserving the full public record. Matplotlib
is optional for plots. Source code hashes are captured at run start and checked again
before finalizing the record, so edits during an integration cannot be hidden by a final
hash of different source bytes.

`release_inverse.py` conditions an equivalent stagnation pressure on measured mean flow,
declared T0/area and the same forward nozzle. It records reconstructed origin, evidence,
sampled monotonicity, bracketing and flow closure. Source T0=mean ambient and virtual-plane
colocation are assumptions; instrumented pipe pressure is not silently a nozzle inlet.
`jet_observations.py` projects actual Cartesian points onto native curved trajectories,
requires dry 200-300 K / <=200 kPa gas, and explicitly declares radial masks or native
analytic Gaussian tails. None ground reference is an explicit unbounded model, with no
fictitious physical height/clearance. Failed runs require explicit diagnostic observation.

Near-cancelling physical source energies make two unshifted native initial roots fail.
An original thin native subclass expresses E as E+C*H2_mass_flux and shifts source targets
identically, with C=source specific KE. It retains native physical tables/profiles/root/ODE.
Host audits convert back before applying the original energy scale/limits. Native raw
energy and read-only `run.physical_energy_flux_w` remain distinct. C/2C initial states agree
at about 1e-15; full-trajectory gas-observer RMSE changes are about 5.2e-12 and 3.4e-12 for
the low-flow and held-out cases, without changing their physical audit classifications.

Five unambiguous calm configurations are compared without concentration coefficient fits.
Four finest native balances pass; the 4 mm / 1 g/s energy defect stays about 0.131 W against
0.00764 W. All five fail at least one authored field target. Held-out 4 mm / 5 g/s RMSE is
about 2.90 volume-percentage points and maximum error 18.07 points. Valid coverage is
complete for the declared dry analytic-profile observer, but this does not qualify its
point/probe, thermal, pressure, wall or historical data-independence assumptions.

Thirty-three new inverse/data/geometry/reference tests bring the full suite to 183.
Both previous authored native normal/para cases were rerun with the updated adapter;
the original cold energy failure remains. Request 011 now includes the concrete measured
fixtures and public energy-reference/conservative integration work. No receiving
repository was edited or messaged, and no GitHub publication was performed.

## Next work, in order

1. Finish apparatus/unit/clock mapping for selected acquired release, cryogenic, ventilation
   and hydride cases. Use the new non-time observation contracts and retain unresolved
   meanings until primary evidence resolves them.
2. Apply the new fitting/held-out machinery to qualified experiments with predeclared
   observation operators and acceptance metrics. Preserve identifiability limitations;
   reproduction of an unresolved curve is not measured validation.
3. Extend the combined finite supply beyond its synthetic envelopes. Localize pressure
   triggers and phase/mass depletion,
   and extend operating/domain cases. Complete atmospheric/
   droplet/impact boundaries rather than promoting nozzle liquid to ground liquid.
   Eleven concrete requests are prepared in `requests/`.
4. Extend beyond the checked PSA equilibrium/warm bed to native process scheduling and
   qualified transport; extend the native pool boundary and the actual native gas/jet adapter.
   Retain the cold energy failure and implement request 011's force/flux/phase/clock contracts. Resolve compatible
   PRISM/SLAB versions rather than suppressing dependency conflicts.
5. Extend distinct gaps: shared reaction/carrier/production core, finite gas-inventory hydrides,
   release partition/impact, facility clocks/isolation and uncertainty. Avoid equivalent duplicate
   solvers per catalyst or storage label. Advanced CFD/fracture/detonation need specialized engines.
6. Complete independent experimental comparisons and the remaining staged implementation scope.

## Distribution review

```powershell
.venv\Scripts\python -m build
.venv\Scripts\python scripts/release_audit.py
```

Read the actual result/hashes in `research/release_audit.md`. Build review is separate from
publication and legal clearance. Raw data, private paths, caches and separately installed
engines must remain excluded. After edits, rebuild and audit the new artifacts.

## Carrier/reaction continuation checkpoint

The current catalog is 72 families: 17 partial implemented, 14 native-adapter checked,
41 planned. Programme effort remains an uncertain 25-35%, distinct from 31/72 first-level
coverage. Full source tests are 204 passed; Ruff/pip checks pass. The extra `molecules`
installs separately reviewed RDKit 2026.9.1; installed Cantera 3.2.0/SciPy are reused.
Observed environment: requirements/validation-windows-py312-carriers-2026-10-27.txt.

Reproduce with `python scripts/check_reaction_models.py` after acquiring lohc-enthalpies
and installing chemistry/molecules extras. It audits the exact acquired archive without
executing/extracting third-party programs, retains raw/member row identity, performs
native molecular checks and verifies finite conversion/reference duty/native calorimetry.
Public details are CARRIER_REACTIONS.md, API.md, research/carrier_reactions.md and
research/rdkit_dependency.toml. The default data path must be the dataset-level audit;
row-local checks cannot detect contradictory duplicates. Actual 10373 rows map to
10345 canonical pairs; 28 repeated pairs conflict in heat, so their 56 rows' heats are
withheld. Nine source capacities retain reporting differences. No input is repaired.

The shared host core owns supplied extent and material/enthalpy ledgers. Existing native
Cantera still owns equilibrium/kinetic reactors, and its actual phase owns species
thermochemistry. No receiving repository edit or new external message was needed for
this additive contract. External data, mechanisms and compiled dependency code remain
outside distributions. No publication was performed.

Next carrier work is qualified liquid/mixture formation and sensible thermochemistry,
source-specific catalyst kinetics/equilibrium evidence, and finite coupled gas/wall/reactant
inventories. Do not extrapolate single gas-reference heats or label an imposed extent a
predicted reactor conversion. Other planned production, combustion, integrity and coupled
facility scopes also remain active. Numerical accounting success is separate from measured
validation and actual accident-source completeness.

## Preferred provider checkpoint and parallel continuation

User-selected priority is HyRAM for high-pressure gas and SLABx-LH2 for LH2-origin
vapor/cloud dispersion. AGENTS records this and progress-report cadence. New APIs are
h2physics.dispersion, adapters.hyram and adapters.slabx_lh2; detailed contracts are
PREFERRED_DISPERSION.md and local request012. Native targets are ignored artifacts/
native_hyram_packages (HyRAM6.1 plus SciPy1.16.3) and native_slabx_packages (SLABx1.0.8,
SLABx-LH2 0.2.0 exact revisions in requirements/native-preferred-dispersion.txt).
The preferred-provider checkpoint passed 212 tests in default SciPy1.18.1 and compatible
SciPy1.16.3 runtimes. Native replay intentionally returns 1 because the gas-source gate
fails; read research/preferred_dispersion.md rather than treating that as a package test.

The Gaussian source carries about 0.76687 of upstream H2 flow, with little subsequent
ODE drift. Preserve this strict interface failure and the raw Jet; no scalar correction
or implicit DEGALI fallback. The steady LH2 vapor source preserves 0.02 kg over 20 s at
fixed area; 5 m/s premise passes and 0.2 m/s fails. Arbitrary histories, footprints,
phase/momentum/energy and observation qualification remain receiving/research work.

The user explicitly authorized parallel development/local calculation. Separate workers
are building actual pressure-data ingestion, frozen native mixture properties and finite
open gas-volume accounting. Treat only their inspected committed evidence as implemented.
The gas-volume path is a thermodynamic control-volume/reference level; it does not replace
the user-selected native dispersion providers. Independent recorder clocks, signed sensor
signals and helium surrogate identity must be preserved. No external repository was edited
or messaged, and no publication occurred.

## Integrated parallel checkpoint

Actual full source suite: 263 passes, Ruff and pip checks pass. Catalogue: 72 contains
17 partial implemented and 16 native-adapter levels, leaving 39 planned; first execution
coverage is 33/72, about 46%. Overall effort remains uncertain 25-35%, roughly 30%.
The user authorizes parallel agent work/local compute; each source owner used disjoint
files, then the parent integrated the result. No remote edits/messages/publication.

Reproduce pressure ingestion with `scripts/check_pressure_peaking_data.py`, frozen
mixtures with `scripts/check_cantera_properties.py`, open volume with
`scripts/check_cantera_volume.py`, and selected dispersion with
`scripts/check_preferred_dispersion.py` plus the native target arguments. The last command
intentionally returns 1 for the retained HyRAM strict source failure. Other three pass
at this checkpoint. Raw and normalized external data, native engines and mechanisms
stay outside distributions. New detailed guides are PRESSURE_PEAKING_DATA.md,
FROZEN_GAS_PROPERTIES.md, OPEN_GAS_VOLUME.md and PREFERRED_DISPERSION.md.

The new open-volume energy state scale is explicit (`energy_ledger_scale_j`, default 1e6);
SI results and native scale vector are retained, with raw-J reference mode 1. This changes
numerical error weighting of appended integrals, not physical derivatives or an energy
reference. Analytic/refinement/SI-ledger acceptance gates remain unchanged. Native warnings
from explicit raw-reference/negative cases are retained. Trial-composition corrections
are optional evidence-identified off-simplex extensions; do not call them measured gas
composition or physical clipping. Cantera H2 spin remains mechanism-unresolved.

Next work can use these qualified blocks for source-specific parameter/clock/apparatus
mapping and additional equipment/production/fire/integrity levels. Avoid repeatedly
chasing a native discrepancy after its reproducible request is concrete. Preferred
HyRAM initialization/compatibility and SLAB arbitrary-source gaps are in request012;
receiving changes belong in their own authorized session. The control volume is a
thermodynamic reference and never silently substitutes for preferred spatial dispersion.

## Parallel insulation, compression and finite-hydride checkpoint

Current executable coverage is35/72 (about49%):17 implemented partial +18 native-
adapter checked +37 planned. The programme remains active/incomplete, estimated
25-35% effort, roughly30%. Two first equipment levels advance; finite hydride is
an extension of the existing dynamic-storage family, without extra family inflation.

- NATIVE_INSULATION.md: native radiation/MLI/support/residual gas/bridges, explicit
  area/path allocation, absolute-clock wall callback, actual layered tank and
  independent fluid/wall inventory.21 authored tests; native signed heating/cooling
  and refinement gates pass. Native zero-area partition and low-level derivative
  limitations remain retained; original native properties are explicitly selected.
- NATIVE_COMPRESSION.md: native gas operating-point stages and serial prescribed
  cooling, dry-gas and EOS/envelope/energy checks, actual native objects and22 tests.
  54 ideal-limit and72 HEOS points pass established equipment budgets. A para-H2
  PH residual4.17e-5W fails an exploratory1e-5W subgate and is retained. No machine
  capacity/map/startup or predicted cooling hardware is inferred.
- FINITE_HYDRIDE.md: native gas/solid finite H2 and two-temperature/U accounting,
  shared kinetics and explicit bound-H energy reference.16 tests and14 replay
  gates include isothermal analytic limit, independent native PT mass/U, reference
  work, energy-zero invariance, thermal reversal, refinement and positive gas floor.
  No gas ports/porous transport/shell mapping or calibrated alloy is claimed.
- HYDRIDE_DATA.md:9 tests and a complete365402-row/7-sheet AB2 profile with10014
  missing-datetime rows preserved. All3 acquired workbooks match their receipts;
  MFC standard P/T, pressure unit/basis and shell-to-bed mapping remain unresolved.
  Source summary caches/formulas are derived metadata, not independent measurements.

Full default SciPy1.18.1 source suite:331 passes; lint and pip checks pass. The
compatibility-run and installed-distribution results are recorded in VALIDATION.md
and research/release_audit.md after completion. Raw CVODE warnings from explicit
reference/negative cases are preserved and are not new measured validation.

Reproduce the new authored/native evidence locally:

```powershell
.venv\Scripts\python -X utf8 scripts/check_insulation_integration.py
.venv\Scripts\python -X utf8 scripts/check_compressor_integration.py
.venv\Scripts\python -X utf8 scripts/check_finite_hydride.py
.venv\Scripts\python -X utf8 scripts/check_hydride_tank_data.py
```

Request013 describes concrete receiving APIs/acceptance cases for zero-area
partitions, callable finite-pipe heat, property capabilities, machine maps/modes
and predicted cooling. Other repositories and external records remain unchanged.
Data acquisition totals stay265 attachments/4307123731bytes; qualification advanced
without inventing additional downloads. Continue the complete remaining PLAN scope.

Final row-identity review added the source workbook SHA to row IDs while preserving
shared physical experiment groups. The final default suite passes331 tests in96.94s.
Compatible SciPy1.16.3 passed the preceding330-test full suite and all9 final AB2
profile tests after that isolated correction. The complete7-sheet data audit was
replayed on final source bytes. No model/test source changed after these checks.

## Pressure protection, vents, recovery and observations

Latest full source suites:406 pass in the default SciPy1.18.1 environment (159.07s)
and406 pass with the separately selected compatible SciPy1.16.3 target (152.76s).
Ruff, pip and diff checks pass. Four first native equipment levels advance coverage
to39/72 (about54%):17 implemented partial +22 native-adapter checked +33 planned.
The full objective remains active and incomplete; overall effort is re-estimated
at30-40%. Test/family counts do not prove independent apparatus/facility validation.

New source tests:12 relief,24 vent,27 recovery and12 instrument =75 above331.
Individual actual-native replays retain host/native begin/end fingerprints:

- NATIVE_RELIEF.md: actual native binary latch and tank integration, shared nozzle,
  accepted copies unaffected by probes, bracketed open/reseat and positive floor,
  pre/post source limits and mass/U/wall heat ledgers. Endpoint bracketing does not
  guarantee detection of arbitrary hidden within-step nonmonotonic excursions.
- NATIVE_VENT.md: actual finite-UA stack, explicit original/shared hydraulic closure,
  final Darcy/gravity/Re audits, required provider sound speed and Mach<=0.3 gates,
  reverse-heat orientation and PH transport outlet.20/100 original native transition
  cases fail independent momentum; coarse/clamped heat paths remain failures.
  Energy is enthalpy-only; kinetic/potential diagnostics do not close a source plane.
- NATIVE_RELIQUEFACTION.md: native saturation/capacity cooling and finite fluid/wall
  storage, actual flowing recovery through shared valves, distinct internal/external
  heat caps and absolute cold-side clock. Net liquid, liquid hold-up and collected
  product remain distinct. No refrigeration electrical power/COP is inferred.
- NATIVE_INSTRUMENTATION.md: actual native held-input response and indication effects,
  explicit initial native state/time and variable/unit/reference/location. Bounds
  stay deterministic, not sigma. Actual unresolved USN meter pressure is rejected as
  absolute headspace process pressure; no calibration is invented from that record.

```powershell
.venv\Scripts\python -X utf8 scripts/check_relief_integration.py
.venv\Scripts\python -X utf8 scripts/check_vent_integration.py
.venv\Scripts\python -X utf8 scripts/check_reliquefier_integration.py
.venv\Scripts\python -X utf8 scripts/check_instrumentation_integration.py
```

Request014 specifies native pure trial/commit protection state, public flow/pipe
composition, acoustic/thermal diagnostics, cold-side cap/callback semantics and
state/calibration observation identities. It has been reviewed against actual
interfaces; no receiving repository or external record was edited. Installed build
and archive evidence is in research/release_audit.md after the final build.

Next work retains the full PLAN: a conserved qualified facility/accident chain,
remaining exchanger/cryo-compressed/production/separation/fire/integrity levels and
independent source-specific data. Preferred HyRAM initialization and low-wind SLAB
failures remain unchanged. Do not re-choke an already owned nozzle/source boundary
or assign missing physical states/frequencies from these protection/reference cases.

## Spin, two-side thermal, reactive gas and complete MHC continuation

```powershell
.venv\Scripts\python -X utf8 scripts/check_spin_integration.py
.venv\Scripts\python -X utf8 scripts/check_heat_exchanger_integration.py
.venv\Scripts\python -X utf8 scripts/check_reactive_process.py
.venv\Scripts\python -X utf8 scripts/check_cantera_volume.py
.venv\Scripts\python -X utf8 scripts/check_hydride_compressor_data.py --workers 2
```

Native LH2DT revision/license/source aggregate remain unchanged. Spin delegates
native rate/equilibrium/heat, with an explicit held-pressure enthalpy calorimeter
and independent sensible-Cp evidence; it is not a native tank spin integration.
The thermal pair holds both actual native fluids/walls at common native stages,
retains separate bases and closes side/global U. Its representative port-free
scheduling state is not a physical aggregate pressure or a flowing process side.

Reactive gas uses the existing CanteraOpenGasVolume with explicit finite_rate.
Boundary transport and native reaction species are separate; elemental and U/h
ledgers catch reference/energy mistakes. Fresh independently owned native
definitions preserve exact thermo coefficients/bounds and runtime multipliers.
Source/owned hashes and coefficient-roundtrip records are separate from native
rate/state error. Explicit time-only callbacks avoid repeated definition
serialization; phase-exposing callbacks retain exact per-RHS guards. Actual GRI30
steam-only/oxidative references and plain-native trajectory checks pass, without
claiming catalytic/industrial process qualification. Existing frozen defaults and
their replay remain verified.

The MHC loader now recognizes only schema-evidenced typed/ISO/German/Excel-serial
Date/Time with explicit workbook epoch. Unqualified scalar clocks are rejected.
The final all-member/all-experiment audit completed after a genuine vanished
process was replaced with a hidden detached bounded job and durable checkpoints.
No running job or partial report is needed to continue from the final record.
`--resume` accepts only exact matching source/member identities. Metadata, source
notes and detailed arrays/diagnostics stay ignored, while original aggregate
counts, rights and source hashes remain public.

Current source integration is472 passes in each default/compatible runtime;
research/parallel_checkpoint.toml records62 scoped final source hashes. Detailed
native/data results and acceptance gates are in research/native_spin.md,
native_heat_exchanger.md, reactive_process.md and hydride_compressor_data.md.
The final build, actual installed-wheel replays and content/source audit are
recorded separately in research/release_audit.md after building. That excluded
record must be regenerated after any further public source/documentation change.

Continue the full programme: source-qualified hydride compressor ports/thermal
observations, flowing native thermal groups, evolving-spin material capability,
catalytic/surface/solid processes, remaining separation/production routes,
fire/radiation/overpressure/integrity and conserved facility/accident composition.
Resolve preferred-provider failures through their native contracts; do not hide
them with another engine or manufacture missing source/clock/reference evidence.

## Fire, conditional blast, inverse heat and thermal observations

Reproduction with the reviewed optional native targets:

```powershell
.venv\Scripts\python -X utf8 scripts/check_hyram_overpressure.py
.venv\Scripts\python -X utf8 scripts/check_pifira_heat.py
.venv\Scripts\python -X utf8 scripts/check_thermal_effects_data.py --workers 2
.venv\Scripts\python -X utf8 scripts/check_hyram_flame.py --hyram-packages artifacts/native_hyram_packages
```

The final Flame command intentionally exits1: diagnostic verification passes,
but native mass/caloric physical acceptance remains rejected. The raw native
objects and four-case refinement report are retained. Do not turn its diagnostic
irradiance into incident wall heat, an accepted fire family or an experimental fit.

Full main tests require explicitly locating separately installed HyRAM without
replacing main SciPy. In a fresh shell with no compatibility PYTHONPATH:

```powershell
.venv\Scripts\python -X utf8 -c "import scipy,sys,pathlib,pytest; assert scipy.__version__=='1.18.1'; sys.path.insert(0,str(pathlib.Path('artifacts/native_hyram_packages').resolve())); raise SystemExit(pytest.main(['-q']))"
```

The compatible run uses the same test suite with native_hyram_packages selected
before SciPy import. The standalone blast replay separately records both runtimes.
Source contracts retain actual public native class/function/raw pressure, explicit
participation/energy/centre/frame and domain. It supplies neither a cloud nor
impulse/DDT/safe-distance qualification. Inverse heat retains actual pifira0.3.0,
fixed-mass/volume two-phase contents U, direct-HEOS audits, explicit angular and
offset axial geometry and clock/source-matched energy allocation. Contents heat
is distinct from incident radiation, wall storage, work and loss. Flat-fit native
covariance warnings are retained.

The thermal collection is complete at10 attachments/693385633bytes. The final
LF receiptSHA705caf63d8a4bfb8e75f507f50425167e7b3b935647d15773b6e2d52dc6e3e69
matches the42.42s all-eight-MAT audit. All245 vectors/157964002 scalar elements
are consumed exactly once with original indices/shape, signed values and masks.
RHF3/timech7 remain separate by default, Exp2 Vent/T survives fully unclocked,
and time units/synchronization/THF processing remain unresolved. Native model
verification is not a measured thermal comparison. No audit job remains necessary.

Read NATIVE_JET_FIRE.md, NATIVE_OVERPRESSURE.md, NATIVE_FIRE_HEAT.md,
THERMAL_EFFECTS_DATA.md and their research records. Request016 captures native
conservation, caloric/solver metadata, heat allocation and observation prerequisites.
The exact current checkpoint and post-build installed/archive evidence remain
research/parallel_checkpoint.toml and the excluded research/release_audit.md.
The full PLAN remains active at44/72 first levels and an uncertain30-40% effort;
28 planned families and substantial source-specific physics/validation remain.

## Current cryogenic, rotor and spherical-storage continuation

The current executable first-level coverage is46/72:18 partial implementations,
28 checked native adapters and26 planned families. Full-programme effort remains
an uncertain30-40%; independent validation and complete model/plant scope are
still open. The data acquisition total stays268 files/4588753807bytes; the new
fermentation work qualifies already acquired data.

With the reviewed optional native targets and actual raw data available:

```powershell
.venv\Scripts\python -X utf8 scripts/check_cryo_compressed.py
.venv\Scripts\python -X utf8 scripts/check_pifira_spin.py
.venv\Scripts\python -X utf8 scripts/check_microsphere_storage.py
.venv\Scripts\python -X utf8 scripts/check_fermentation_data.py
```

Read CRYO_COMPRESSED_STORAGE.md, NATIVE_SPIN_THERMOCHEMISTRY.md,
MICROSPHERE_STORAGE.md and FERMENTATION_DATA.md with their research reports.
The cryogenic composition uses one native tank/wall/event engine and shared
nozzle. Opening and localized positive floor remain different from a pressure
stop. Post-run native/domain/EOS failures retain the completed trace, actual
failing state/time, audited prefix and original cause. Native zero-UA geometry
is unsupported; preserve that failure rather than introducing a hidden epsilon.

The pifira bridge is constitutive: native U/Cv/gap/gap derivative and bounded
natural kinetics, without another calorimeter ODE. Keep absolute rotor storage
separate from a frozen-EOS correction; require an explicit PV assumption for H.
Primary90kg/m3 admission differs from the installed native92 limit. The finite
verification path stays in its admitted high-ortho interval, and a mathematical
detailed-balance probe does not grant low-ortho long-duration applicability.

The material core now serves planar and spherical transport, with true volumes,
face resistances, finite surface amounts and one BDF integration. Cavity gas
properties reuse the existing HydrideGasThermodynamics contract. A uniform
temperature history is prescribed; duty, stress, rupture and optical response
remain unresolved. Exact steady face resistance does not imply exact transient
wall integration; use the independent series and mesh-refinement evidence.

Fermentation observations preserve830 rows, reactor-specific reported days,
missing fields, reconstructed production and source inconsistency. Do not fit
growth from derived gas columns or infer reactor volume, gas standard state,
substrate species or independent replicates. Request017 specifies native
event/energy/property and material/biological prerequisites for other sessions.

Next research work includes source-qualified biological liquid/gas inventories,
photocatalytic observations and photon/material boundaries, evolving-spin thermal
coupling, remaining production/separation/integrity families and the conserved
facility/accident chain. Preferred-provider physical failures remain retained.
Check the latest parallel checkpoint and excluded post-build audit before
reusing a packaged result. The complete PLAN remains active.

Final integrated main/compatible suites each pass629 (130.60/130.08s); all194
Python input hashes remain unchanged across both runs. New native replays and
source identities are in the four current reports. Post-build installed-wheel
and distribution evidence is appended only to excluded research/release_audit.md.

## Current spectral, multiphase and cyclic-separation checkpoint

Current first-level coverage is49/72:19 partial implementations,30 checked
native adapters and23 planned families. The full programme remains active at
an uncertain30-40% effort estimate. No independent catalyst, gasifier or PSA
apparatus validation is claimed by the authored numerical cases.

Reproduce with the existing reviewed optional native targets and acquired data:

```powershell
.venv\Scripts\python -X utf8 scripts/check_photochemistry.py
.venv\Scripts\python -X utf8 scripts/check_photocatalysis_data.py
.venv\Scripts\python -X utf8 scripts/check_cantera_multiphase.py
.venv\Scripts\python -X utf8 scripts/check_psa_cycle.py
```

Read the corresponding PHOTOCHEMISTRY, PHOTOCATALYSIS_DATA,
MULTIPHASE_CONVERSION and NATIVE_PSA_CYCLE manuals and research reports.
Photon coefficients bind to exact wavelength-grid/representation identity;
matching length is insufficient. Yield binds separately to complete light and
conditions, incident yield is not attenuated twice, and rejected diagnostics
cannot enter finite chemistry. Steady depletion is rejected without source
termination. Required thermal duty does not establish chemical/exergy feasibility.

The TiO2 audit retains all37 text members, line/column/raw/mask identities,
reconstructed rate/AQY and duplicate/shared-control dependence. Its bounded
two-partition digest and source hashes are reproducible. Missing full SI,
photon power, calibration, T/P and uncertainty remain unresolved.

Multiphase equilibrium preserves actual source and privately owned gas/solid
definitions, finite SI amounts and native Mixture. Populated chemical-potential
and absent-solid gates have explicit trace thresholds. HP internal trial T is
unavailable; supplied/final admission is separate from native convergence.
Zero-carbon candidate and intentionally restricted-envelope failures retain
actual partial/completed objects and cause, without automatic phase deletion.

Native PSA uses warm loading-LDF and a distinct CvT0/CpT0/binding reference.
The first H2-specific host API requires native H2 reporting. A separate audit
Network is not the original integrating instance. Actual internal temporary
I/O is explicit; arbitrary Python histories/original object hooks remain
request018 work. State CSS, startup ratio, final-cycle recovery and experimental
stream qualification are distinct. Synthetic CSS does not enrich H2.

Continue the full plan: material/photonic/kinetic inputs and independent
experiments, native membrane transport and finite receiving inventories,
remaining biological/thermochemical/solid-storage processes, qualified
integrity/consequence paths and conserved full facility/accident composition.
Keep preferred-provider failures visible; do not manufacture a missing boundary.

Final source suites each pass705, main/compatible127.44/126.92s, with206 Python
input hashes unchanged. Current reports and parallel_checkpoint.toml identify
executed sources. Rebuild and regenerate the excluded post-build audit after
any further release-input edits.

Next membrane path: actual Cantera3.2 DustyGas two-point multicomponent/Knudsen/
Darcy flux was probed read-only with13 small numerical gates. Native units are
kmol/(m2 s), requiring1000 for mol/(m2 s), and signed total transport is not a
zero-sum relative diffusion velocity. Native pore/thickness/composition guards
are insufficient; require explicit positive geometry, normalized composition,
permeability and admitted warm/isothermal phase. Reuse the native transport
owner, preserve source/native objects and validate species/reference/clock
boundaries. This feasibility is not an implemented membrane device or a
recovery prediction. Finite feed/permeate/retentate and thermal inventories are
still required for a full unit operation. The primary interface is the
[Cantera DustyGas flux API](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport.molar_fluxes).

Final staging found one trailing whitespace in the multiphase replay script.
Its cleanup preserves the parsed Python AST; all production and test bytes
remain identical to the705-case full suites. The native replay was repeated
with the final script bytes and its source identities regenerated.

## Membrane, staged thermal and native biological checkpoint

First executable coverage advances49/72 to52/72, about68% to72%:20 partial
implementations,32 checked native adapters and20 planned families. The uncertain
full-programme effort estimate remains30-40%. This increment adds bounded
porous-gas transport, finite prescribed thermal stages and native anaerobic
liquid/headspace dynamics. Gas/pure-solid calorimetry deepens the common reaction
interface without creating another family or property solver.

Independent review corrected a reused caloric-array alias, extensive overflow,
native gas-provider binding changes and nonfinite biological audit arithmetic.
Native biological startup exposed the published BioSTEAM initial-state alias;
the admitted official fixed revision preserves the exact initial trajectory.
Closed zero-flow native output-finalization failure and a coarse sampled ledger
rejection remain visible. Numerical success does not establish high H2 yield:
the native community contains H2-consuming organisms and the authored dry gas
export H2 fraction is about0.002068.

Verification is sharded to overlap computation with disjoint development. The
781-case non-biological regression shard passes in main SciPy1.18.1 and
compatible1.16.3, 148.70/148.68s, with its215 Python
inputs unchanged. The final biological shard is checked separately in each
host profile; optional native skips are explicitly not execution evidence.
A separate reviewed native biological environment executes all18 biological
tests. Together the two host shards cover788 passed/11 optional skips per
profile; native execution covers the remaining optional cases. Final218 Python
source/test/script hashes match the union of those frozen shard inputs.

Native membrane, caloric and staged thermal replays pass14,16 and14 gates.
The biological final report records actual native objects, sample-refined
component/COD/C/N budgets and retained native failures. No independent membrane,
solid-cycle or biological experiment qualification is claimed. Source-qualified
materials/kinetics, heat/work/phase feasibility, finite separator inventories
and the full conserved facility/accident composition remain open. Request019
specifies receiving capabilities. Acquired process-data counts stay268 files /
4,588,753,807bytes. Remote publication and receiving repositories are unchanged.

Reproduce membrane, caloric and finite thermal cases with:

```powershell
.venv\Scripts\python -X utf8 scripts/check_cantera_membrane.py
.venv\Scripts\python -X utf8 scripts/check_cantera_caloric.py
.venv\Scripts\python -X utf8 scripts/check_thermochemical_cycle.py
```

For biological reproduction use NATIVE_BIOLOGICAL_PROCESS.md and the pinned
requirements/native-biological.txt/receipt. Keep its native SciPy stack separate
from host compatibility profiles. Read NATIVE_MEMBRANE_TRANSPORT,
MULTIPHASE_CALORIMETRY and THERMOCHEMICAL_CYCLES for complete Python examples.
Preserve native total-flux frame, formation energy, phase and clock identities;
no automatic membrane recovery, thermal feasibility or biological calibration
is supplied. Continue the complete PLAN. The post-build audit remains excluded
from distributions and must be regenerated after any release-input edit.

## Finite membrane, thermal compression, material observations and uncertainty

First executable family coverage advances52/72 to54/72, about72% to75%:
21 partial implementations,33 checked native adapters and18 planned families.
The uncertain full-programme effort estimate remains30-40%. Actual finite
thermal compression and native independent-input uncertainty add two families.
Finite two-side membrane composition deepens the existing transport family;
material observation qualification does not create a fracture-law family.

Both unsharded host profiles pass870 cases with11 explicit optional-native
biological skips: main SciPy1.18.1,216.34s; compatible1.16.3,216.22s. Added82
cases cover17 finite-membrane,18 compressor,13 material-profile and34 uncertainty
checks. All230 Python source/test/script inputs remain unchanged across both
full runs and equal the final source snapshots. Previously executed isolated
biological cases are not presented as newly run by these optional skips.

Finite membrane replay passes17 gates: native two-side species/U/H/thermostat
ledgers, independent hook units/area, reversal/refinement and finite Knudsen
limit. Maximum side energy defect is3.842e-12J. The same prescribed T is explicit;
raw native numerical extensions, sampled admission and hidden native internal
steps differ. An inventory rejection is not an exact stopping-root prediction.

Finite compression replay passes20 gates in105.044s. It admits
0.00144023053kg and delivers0.00105626799kg
above evolving finite source pressure; maximum total-H2 defect is
6.93889e-18kg and total-U defect2.69836e-10J.
Final solid loading0.0948648585 differs from initial0.01 despite
returning to300.000064K. Startup inventory, non-CSS
loading and finite bath/thermal duties remain visible. Shared closed-bed and
microsphere replays pass again after the rate-core extraction; their current
source identities are refreshed. No native EOS/kinetics/tank/nozzle is duplicated.

Uncertainty replay passes13 gates in each native SciPy profile,37.8503/34.4667s.
Actual normal-H2 inventory QMC mean/variance defects versus independent tensor
quadrature are6.19e-9/1.62e-6relative. Independent seed/base2 index change is
3.24e-5. Input distributions and independence are authored. Coordinate mutation
and invalid-returned-raw retention defects found in review have regressions;
native1x1 shape failure, constant variance and numerical overflow/underflow stay
distinct. No measured law/covariance, facility frequency or model validation
is inferred from numerical statistical convergence.

All9 acquired austenitic compilation attachments are qualified, including
113condition/property records, five properties,31linked composition rows and
102mappings. Forty elemental disagreements remain separate;103absolute pairs
and10ratio-only records preserve source roles. Pressure/purity/strain definitions
and specimen/study dependence remain unresolved where source evidence is missing.
Acquisition totals stay268 files/4,588,753,807bytes. Request020 specifies receiving
capabilities. Full experimental, remaining model-level and facility/accident
qualification keeps the original programme active; no remote publication occurred.

Reproduce current native/data checks with:

```powershell
.venv\Scripts\python -X utf8 scripts/check_membrane_device.py
.venv\Scripts\python -X utf8 scripts/check_hydride_compressor.py --native-target artifacts/native_packages
.venv\Scripts\python -X utf8 scripts/check_embrittlement_data.py
.venv\Scripts\python -X utf8 scripts/check_uncertainty.py
```

Read FINITE_MEMBRANE_DEVICE, HYDRIDE_COMPRESSOR, EMBRITTLEMENT_DATA and
UNCERTAINTY manuals plus their research reports/request020. The full host
regression commands follow VALIDATION.md, with the previous sharded ignore
argument removed to execute the current whole suite. Keep the isolated
biological dependency stack separate from both host numerical profiles.
Source/owned state, fluid/spin/reference, raw-trial versus output clocks,
statistical law and observation lineage must survive composition. Continue
remaining families, source material/experiment qualification and full conserved
facility/consequence coupling. After any release-input change regenerate the
parallel checkpoint and build/install/archive audit.

## Native wave, supplied-exposure and conditional-risk checkpoint — 2026-10-28

First executable coverage advances54/72 to57/72, about79%:21 partial implemented
families,36 checked native-adapter first levels and15 still planned. The uncertain
full-programme effort estimate remains30-40%. Independent calibration/experiments,
remaining physics and a qualified full facility accident chain are incomplete.

Both unsharded host profiles pass970 cases with11 explicit optional biological
skips: main SciPy1.18.1 in258.49s and compatible SciPy1.16.3
in258.57s (NumPy2.5.4). All242 final Python source/test/script
fingerprints match at run start/end and current source. Skips are not newly
executed biological evidence; the previous isolated native biological record
remains separately scoped. Native Sundials warnings in deliberately difficult
existing event cases remain in the ignored logs, not silently rewritten results.

Actual native HyRAM supplied-field exposure passes22 gates; SDToolbox/Cantera
CJ/frozen-shock replay passes18; native conditional-risk composition passes15
in both numerical profiles. These establish the stated numerical/API boundaries,
not experimental harm calibration, a source-to-field chain or total-facility QRA.
A replaced cached native probability/model is rejected by the exposure owner's
replay; absent/invalid source state is rejected before conditional risk.

A real simultaneous native YAML bridge reproduces an initial global cleanup
assertion failure. Verification factories now use separate ASCII UUID workspaces,
and a real two-owner regression checks that one open bridge does not invalidate
another owner's cleanup. Production native wave algorithms are unchanged. The
initial failed main run and its full passing compatible peer remain in ignored
logs; the two final runs above execute the corrected frozen inputs.

All42 acquired ELVHYS assets (38 recorder signals) and534609893bytes are
hash-verified. Complete scan:4886225 rows,48526984 finite numeric cells,
48034198 valid and492786 invalid T2e dummy cells, with27 duplicate/nonincreasing
temperature clocks retained. BLEVE/membrane-rupture observations lack homogeneous
premixed initial-state/CJ-speed evidence; direct CJ validation is inadmissible.
Pressure-reference, sampling and synchronization conflicts remain explicit.
Overall acquisition stays268attachments/4588753807bytes; no new raw data
were needed for this checkpoint.

Exact inputs, native raw objects/diagnostics, acceptance and limits are in
research/native_exposure.md, native_detonation.md, conditional_risk.md and
shock_tube_data.md. Request021 specifies source data/native state/search,
calibration and direct risk-object capabilities for receiving projects. No
receiving repository was edited and no publication occurred.


Reproduce the final native endpoint cases after installing reviewed dependencies:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/check_hyram_exposure.py --hyram-packages artifacts/native_hyram_packages --no-report
.venv/Scripts/python.exe -X utf8 scripts/check_detonation.py
.venv/Scripts/python.exe -X utf8 scripts/check_conditional_risk.py --risk-packages artifacts/native_risk_packages --hyram-packages artifacts/native_hyram_packages --report artifacts/replayed_conditional_risk.md
.venv/Scripts/python.exe -X utf8 scripts/check_shock_tube_data.py --output artifacts/replayed_shock_tube_audit.json
```

Use --use-main-scipy for the exposure/risk scripts to exercise installed main
SciPy before inserting the compatible target. Keep exact dependency receipts,
original native notices and package targets distinct. The three new optional
providers are not bundled in host distributions. Core imports must work with
all domain providers blocked. Final actual distribution/installed replay hashes
are recorded after build in research/release_audit.md (excluded from its own
source archive). Run release checks again after public edits.

Next remaining work: continue the15 planned families and the unqualified levels
inside executable families; prioritize actual existing native ownership and
source-specific evidence over another duplicate equation. A read-only cold/
oxygen-deficiency provider review is being retained in ignored artifacts for
the next implementation decision; it adds no coverage claim here.

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


Reproduction uses the observed main environment snapshot
requirements/validation-windows-py312-cold-monitoring-2026-10-28.txt plus the
separate native-thermal/native-monitoring profiles and exact receipts. The main
snapshot does not install native source targets or establish cross-platform locks.

```powershell
.venv/Scripts/python.exe -X utf8 scripts/check_oxygen_deficiency.py --no-report
.venv/Scripts/python.exe -X utf8 scripts/check_jos3_thermal.py --report artifacts/replayed_thermal.md --details artifacts/replayed_thermal.json
.venv/Scripts/python.exe -X utf8 scripts/check_process_monitoring.py --no-report
.venv/Scripts/python.exe -X utf8 scripts/check_air_condensation_boundary.py --report artifacts/replayed_air_boundary.md --details artifacts/replayed_air_boundary.json
.venv/Scripts/python.exe -X utf8 scripts/check_oxygen_observation_data.py --output artifacts/replayed_cold_room/audit.json --workers 2
```

The thermal and learned-monitoring providers are separate optional targets;
read their manuals before native imports. The O2 script uses already installed
Cantera and shared owners. For compatible replay preloadSciPy1.16.3 before
native targets, retain the selected version and never silently switch engines.
The full all-source data scan is deliberate; --resume is only an explicit exact-
source checkpoint continuation, not a substitute for an unperformed scan.

After final included edits, rebuild wheel/sdist and audit actual members/bytes,
all public checkpoint/report hashes, and actual installed native/full-data calls.
The final post-build report is research/release_audit.md, deliberately excluded
from its own archive. Re-run after included edits. Remaining planned families
and partial-level validation remain the full objective. A read-only next energy-
coupling/provider/data review is retained under ignored artifacts; it adds no
coverage claim to this checkpoint.

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


Continue coding against AGENTS.md's current execution priority. Do not restart
local tests because older checkpoint sections contain reproduction commands.
After Nurion connection, configure validation/nurion_plan_example.py and actual
profiles, pin a clean source revision/plan, then use the deferred case definitions.
NURION_VALIDATION_PLAN.md describes assumptions/worker records. Missing/rejected
jobs remain incomplete, not successful. Required existing full regressions,
native/data and installed-artifact checks still belong to the eventual campaign.
No newer wheel or deployment is created by this unverified coding checkpoint.


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

Six catalog families remain planned: underground storage, microbial-cell
production, surface impact/deposition, obstacle-resolved dispersion, accepted
jet fire and flash fire. Partial implemented families also retain substantial
physics and independent validation work;66coded families are not66completed
models. Preferred HyRAM gas and SLABx-LH2 liquid-origin ownership is unchanged.


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

## Exact selection and finite process continuation — 2026-10-28

The unexecuted continuation adds `ModelRegistry`, `FiniteFuelCell`,
`Lh2dtFiniteTransfer` and `ThermalUtilityLedger`. Read MODEL_SELECTION.md,
FINITE_FUEL_CELL.md, FINITE_TRANSFER.md and THERMAL_UTILITIES.md before use.
The Nurion queue now contains133 deferred definitions (+27). No import, model,
example, case, test, build or scheduler submission was run. Family/status and
data totals are unchanged; executed evidence remains59/72 at6eae06c.

## Finite adsorption, actuation, relief and continuity continuation

Read FINITE_ADSORPTION_VESSEL.md, VALVE_ACTUATOR.md,
FINITE_RELIEF_LIFT.md and FACILITY_CONTINUITY.md. New profiles add25 deferred
definitions and bring the queue to158. No local import, model, case or test ran;
family, data and executed-evidence counts are unchanged.

## Rotating equipment and recovery continuation

Read PUMP_OPERATION.md, COMPRESSOR_MAP.md, FLOWING_HEAT_EXCHANGER.md and
FINITE_RELIQUEFIER_PRODUCT.md. New profiles add25 deferred definitions and take
the queue to183. Native results, map evidence, ports, states and clocks remain
explicit. No import, model, case, example or test was run.

## Active continuation — 2026-10-29

A focused Nurion verification array for compressor-map and spatial counterflow-HX
corrections completed as `24229573[]` (five elements); collector `24229574.pbs`
finished with exit status zero. Four case records passed and the low-UA exchanger
case failed its equation residual gate. Source revision is `1134c7bd12b66889c8e840932f78a800e662c86a`,
source-manifest digest is `95ee766491e335c5e50080d69768c4a42f353200337aef6d0d8f2b2f90fdc6ba`,
and plan digest is `04dfb9ab91895383d34dfac849cc04bf4fdc210a3b80c730b68d40107f362f38`.
The solver was rescaled afterward; that change is not in this pin and still needs a
new focused Nurion execution.

The CC BY 4.0 KITopen NH3/H2 counterflow package was acquired to the ignored
`data/raw/` directory; publisher payload hashes and five workbook schemas were
checked. `h2physics.data.counterflow_flame` exposes the extinction table, nine
temperature profiles, and twelve H2/NH3/NO profiles with source hashes, row/column
identity and conditions. A deferred ingestion case checks these structures, but a
previous Nurion run stopped in source-manifest preflight because the generated
revision receipt was included in the hash list. The receipt is now excluded; submit a
fresh pinned campaign including the low-UA exchanger and all data-reader paths. No
experiment comparison is established because inlet/strain mapping is unresolved. See
`docs/COUNTERFLOW_FLAME.md` and `research/data/nh3_h2_counterflow_flame.toml`. Ruff
checks pass; local scientific tests and flame solves remain deferred.

The corrected source pin is `31c0ea86f2f5c43b758d5fcb18dfe36b8d581422`; its 728-entry
manifest, plan hash, archive hash and all eight BagIt payload checksums passed the
remote preflight. Array `24229619[]` completed and both cases failed: low-UA exchanger
equation residual `0.0833333727`; source-row gate expected thirteen records although
the workbook contains eight observations at rows 2-9 and five blank trailing rows.
The source was corrected to use enthalpy offsets directly in energy residuals and the
reader case now matches the audited rows. Those edits need another pinned run. The
newer optical-series reader was added after this pin and also needs source-pinned
ingestion. This was followed by revision `3c470862395e03cef21a803a6eb6d4e98f4c969e`,
which corrects the relative enthalpy closure equations, uses the eight actual ESR
observations, and includes optical readers. Array `24229638[]` low-UA case passed at
`1.7600134e-6 W` limiting duty. The data case was stopped after CPU time stayed at
13 s over more than 4 min and produced no outcome. The read-only reader now uses one
row-stream pass per profile; this optimization requires a fresh source pin and Nurion
case. Do not use the available result to claim experimental flame validation.

## Parallel coding and fresh data-ingestion retry — 2026-10-29

The next data-only source is pinned to `643e4a8d1765a35170141b5a3a2af115340403cd`,
728-entry source-manifest digest `6397d0fdbc3caa9b23b070598a152657e9d1cee64aaf451f08e86741e8be8945`.
Its updated plan digest is `b12dbc50a82b3b0072dfd68fecc5de3f399e08bececabe4d69dba9b026c39b21`.
The first worker ran on Nurion but stopped before the case because the plan exported a
function instead of required `CASES`; its collector has 0 outcomes/1 missing case. A
corrected plan was metadata-imported locally and resubmitted from scratch as
`24229654.pbs`, collector `24229655.pbs`. Both finished successfully; the summary is
under `results/fixcheck_643e4a8/summary.json` through the user's existing Nurion
wrapper. The one data-ingestion case passed in 40.96 s: 8 extinction observations,
9 temperature profiles, 12 species profiles, 60 normalized optical profiles, 3 band
integrals, 3 spectra and 540 retained missing optical cells. This is not a flame solve,
model-data comparison, or pure-H2 validation.

In parallel, the current working tree adds bounded PV-profile midpoint forcing,
evidence-bearing integrated surface heat between impacts, and an elastic Lamé
thick-cylinder stress field. The impact and cylinder cases were added to the Nurion
collection; all three increments are outside the 643e4a8 source pin. Do not mix their
results with the data-reader retry. Static checks only have run; these families remain
`implemented_unverified`. Overall planning effort stays 30-40%, and last accepted
first-level execution remains 59/72 (about 82%).

The implementation revision `c521f57cd960b4be460c5dc1eefa5788b47d8f0d` is now submitted
as a three-case array. Its 731-entry source-manifest SHA is
`ab8883a04e1c67ab70eaf3851c622214c2f1e83105790dc18b490ebe75636f33`, plan SHA is
`6743678c5f2c9da1d0bddd11c00f0cded4a6b0287516e7dcc9ef0241a9193968`, array is
`24229801[]`, collector `24229802.pbs`. The cases cover inter-contact impact heat,
thick-cylinder pressure stresses and the bounded PV profile. PV element `[3]` exited
before its case because setup looked for the archive in the wrong incoming directory;
the archive is in the expected path and a standalone retry script was syntax-checked.
Cylinder element `[2]` passed its authored stress-field invariants in 7.37 s; impact
element `[1]` passed in 29.58 s with a global wall-energy residual of `-1.8783e-17 J`.
These checks do not qualify vessel integrity, crack growth, fatigue or LH2 impact
behavior. PV element `[3]` failed during setup before entering its case; the archive
path was corrected and retry `24229849.pbs` is running. Collector `24229850.pbs` is held
until that retry ends. The queue still reports two retained passing outcomes and the
PV case missing; accepted family-level evidence remains 59/72 until the PV outcome is
collected and reviewed.

After that source pin, a sampled pressure/time/radius Lamé series API and deferred case
were added. They are absent from `c521f57` and remain unverified; include them in the
next source-pinned campaign. Static syntax review only is permitted on this PC.

The PV retry passed in 38.52 s; collector `24229850.pbs` exited 0 with three passed
outcomes, zero failures and no missing cases. The PV case checked bounded input
interpolation, midpoint integration and finite ledgers. These authored checks do not
change accepted first-level family evidence (59/72, about 82%).

The current unpinned implementation adds `clock_id` to sampled Lamé pressure results
and `bind_cylinder_samples_to_vessel_history`, which maps the existing pressure loads
and explicit wall-temperature samples into `VesselFailureHistory`. It verifies source,
clock, origin, temperature evidence, phase and sample identity without interpolating or
calculating fracture. Deferred cases `elastic-cylinder-pressure-samples` and
`cylinder-pressure-vessel-history-bridge` are registered in the metadata plan. Ruff,
syntax and diff checks pass; do not count either case as run. No new Nurion job was
submitted because the user requires a separate request for each new campaign.

The implementation now also includes `thermoelastic_lame_stress_field` for uniform
wall-temperature changes with free/fixed axial expansion. Its validation case is
registered but unrun; include it in a future separately authorized Nurion source pin.
The fixed-restraint mode returns an axial support reaction and requires actual support
evidence before application. Radial temperature gradients and vessel qualification remain
outside the model. Public data screening found the 90 MPa mechanical diaphragm compressor
records are internal/not public; no raw data were acquired. The existing MHC dataset is
not a mechanical diaphragm-compressor validation substitute. See
`research/elastic_cylinder_development.md` and `docs/HYDROGEN_COMPRESSOR_DATA.md`.

The CORA MEC electrode dataset DOI10.34810/data2866 is now acquired from its public
Dataverse bulk endpoint under the record-level CC0 grant. All 24 extracted entries
match the saved SHA-256 inventory and archive integrity passes; ten source-preview
MD5 values agree. The 23 actual dataset files provide limited electrode LSV/EIS and
current-density evidence, not complete MEC hydrogen output. File-level rights override
metadata is absent, so raw assets remain outside public distributions pending review.
The updated inventory is29 collections,27 with data,490 dataset data files and
6,033,439,460 uncompressed source bytes (not counting the publisher manifest). The
receipt, ODS limitations and source metadata are in
`research/microbial_electrolysis_data_candidate.toml`; no model case or Nurion job was run.

The CORA source-bound ODS reader is implemented at
`src/h2physics/data/mec_electrodes.py` and exported by `h2physics.data`; details
are in `docs/MICROBIAL_OBSERVATIONS.md`. It verifies the three pinned workbook
hashes, returns six LSV and six current-density observation tables plus eight
paired impedance traces, preserves raw numeric tokens and source coordinates,
and uses shared SI conversion. It makes no frequency, area, performance or
hydrogen-output inference. Deferred cases `mec-electrode-data-provenance` and
`mec-electrode-data-integrity` are registered under `microbial-observations`;
they have not run. Raw files remain excluded from public distributions pending
file-level rights review. Continue implementation independently; any Nurion
submission requires the user's separate instruction.

### 2026-10-29 OEDI condition reconciliation and native-rate implementation

The local OEDI workbook is checksum-pinned by SHA-256 and MD5. Its MD5 matches the
HyMatBase-linked file, but the local Environment sheet and Sandia study record identify
45 MPa H2 while the associated HyMatBase metadata says 4.5 MPa. Admit 45 MPa for these
workbook observations and retain the catalog discrepancy as metadata; do not use the
older instruction above to block source-bound comparison. `h2physics.data.oedi_fatigue`
verifies both hashes, and `h2physics.adapters.oedi_fatigue` composes observed delta-K
points with actual native HELPR point rates without fitting. The deferred
`oedi-helpr-rate-comparison-diagnostic` case is registered in the plan. Its temperature
and purity inputs are explicit reconstructions, HELPR does not consume the source's
frequency, and material-heat identity is incomplete. This is a diagnostic, not a model
acceptance or vessel-life result. Neither the case nor any scientific calculation has
been run locally; no Nurion campaign has been submitted for this code.

The materials-integrity family now also contains
`h2physics.materials.radial_thermoelastic_cylinder`, which solves the isotropic
axisymmetric radial-displacement BVP for a caller-supplied radial temperature profile.
The package export and deferred case are registered; `elastic-cylinder-radial-
thermoelasticity` is configured under `fracture-fatigue`. It has only static review,
not numerical execution. The new P0 source receipt
`research/data/oedi-hydrogen-materials.toml` records an acquired 4130X fatigue workbook
(CC BY 4.0 dataset record, 58,357 bytes). Its labeled 45 MPa H2 condition conflicts
with a related 4.5 MPa HyMatBase record; do not quantitatively compare or fit before
resolving which file/condition is represented. Raw source data remain ignored.

### 2026-10-29 transient wall heat model

`h2physics.materials.radial_cylinder_heat_history` now provides a conservative radial
finite-volume thermal history through a finite cylindrical wall. Material heat capacity
and conductivity are replaceable temperature callbacks; each wall face takes an explicit
adiabatic, temperature, heat-flux or convection condition. Returned surface temperatures
and cell temperatures can be packaged with `RadialHeatResult.thermoelastic_profile` for
the existing axisymmetric thermoelastic BVP. A global enthalpy/face-heat residual is
reported. Case `finite-cylinder-radial-heat-transfer` is registered under
`thermal-utilities`, including adiabatic, prescribed-heat and logarithmic steady-profile
checks. The module and case received static syntax/lint/diff checks only; neither was
executed, and no Nurion task was submitted. No axial conduction, phase change or fluid
feedback is represented. Continue implementation while preserving this execution split.
Static source review after implementation also corrected the outer boundary's sign in
the cell heat balance. Because no model calculation was run, verify both inner and outer
face heat directions and the global ledger in the registered Nurion case before relying
on this module.
The history API now requires a stable `history_id`; thermoelastic profiles generated
from samples carry that history, index and time in their ID. The manual states the
separate signs for positive-outward internal rates and positive-into-wall boundary rates.
`RadialHeatResult.thermoelastic_history` now composes pressure and thermal samples on that
same clock and returns both input/output histories with sample-level lineage checks. The
new deferred case constructs this composition but remains unexecuted. It is a sequence of
static BVP solves; don't infer dynamic or two-way thermal/mechanical coupling.
The deferred case also exercises convection with a time-varying film coefficient and
temperature-dependent conductivity/heat capacity. It remains outside all prior
source-pinned results.
Its assertions match the manifest for both boundary heat signs and immutability of every
returned thermal array; this was confirmed by static source review only, not case execution.
The latest extension adds a net-radiation wall boundary using SciPy's Stefan–Boltzmann
constant and bracketed scalar root. The deferred case exercises radiant heating at the
inner face and cooling at the outer face, with surface temperatures and the global energy
ledger. This code remains unexecuted; caller-supplied irradiation temperature and
emissivity-view factor do not represent gas radiation or infer flame/environment geometry.
`RadialHeatIntegrationError` retains the exception and any available SciPy solve output;
the deferred case now checks an invalid emissivity callback. Neither radiation nor failure
preservation has been run on Nurion.

## Stress history failure-path contract — 2026-10-29

The radial thermal-to-stress wrapper now validates nonblank paired-history identities, temperature-reference consistency in constructed results and explicit axial-restraint lineage. Its deferred thermal case forces a native BVP failure on the first requested sample and checks retention of the original heat history, underlying cause and empty completed-stress prefix. These checks are authored and statically reviewed only; no model calculation, scientific test or Nurion submission occurred.

## Current Python dispersion entry points

`h2physics.dispersion.DispersionScenario` accepts an explicit release origin and a
read-only copy of named Python inputs. Its `run()` routes high-pressure gas only through
the preferred HyRAM adapter and LH2-origin vapor only through the preferred SLABx-LH2
steady vapor/footprint adapter. It does not convert between source types, create the LH2
vapor boundary from liquid release, or substitute DEGALI on failure. Functional
`run_preferred_gas_dispersion` and `run_preferred_lh2_dispersion` APIs are also available.
The deferred route case covers callback argument plumbing with non-engine stand-ins and
is tagged `implemented_unverified`; it has not run. This addition does not change the last
executed first-level evidence (59/72) or the uncertain full-programme estimate (30–40%).
Static syntax, Ruff and diff checks passed; no new Nurion work was submitted. Read
`docs/PREFERRED_DISPERSION.md`, `docs/API.md` and `docs/MODEL_SELECTION.md` for the
source and ownership limits.
`DispersionScenario.run()` returns a `DispersionExecution` receipt. Failures are chained
through `DispersionExecutionError`, preserving provider identity and any underlying
failure result. The direct functional helpers retain their adapter-native return types.

## HE-Austenite deep Python receipt API — 2026-10-29

`EmbrittlementCollection.from_receipt(data_directory, parsed_receipt)` is now exported
from `h2physics.data`. It validates the pinned Zenodo DOI/version, CC-BY rights flag,
acquired-file set/status and every SHA-256 against the code-pinned file manifest before returning the existing bounded
collection API. Callers still stage and name the external directory and parse the local
TOML receipt; the package does not fetch or infer files. Deferred provenance/contract
cases now include receipt tamper rejection and are registered in the Nurion plan, but
they have not run. Static `py_compile` and `git diff --check` pass; Ruff is unavailable
in the current Windows shell. No scientific calculation or Nurion job was started.

The shared `ObservationTable` contract now rejects non-string row, experiment and source
identities and retains caller context as immutable typed key/value pairs, even when the
input uses nested lists. The deferred
`observation-table-contract-integrity` case covers these guards, variable basis typing,
quantity compatibility and immutable arrays. It has not run; this is API integrity work,
not data or physics validation.

English and Korean README indexes now link to the 4130X fatigue/HELPR and transient
radial heat manuals. `pyproject.toml` discovers Python packages from `src`; `MANIFEST.in`
includes docs, validation definitions and TOML rights receipts while pruning `data/`,
builds and binary research attachments. This was a source-configuration review only;
no build or installed-package replay was performed.

The OEDI fatigue diagnostic result now rechecks the selected HELPR law parameters and
environment, including reference pressure and fugacity basis, exact source-series identity
and measured rows. Its deferred case includes mutations of returned row IDs, observation
values, gas pressure and fugacity basis; these rejection checks
are unrun. Caller row-ID sequences are frozen at construction and the case checks post-
construction mutation isolation. This is an implemented-unverified API integrity guard,
not experimental law validation.

The radial heat-to-thermoelastic sequence now binds the wrapper evidence ID to the stress
history and to every derived radial temperature profile. Its deferred case checks altered
wrapper/profile evidence rejection. The sequence remains quasi-static, one-way and
unexecuted; it adds no dynamic or experimental validation claim.

The 4130X `FatigueGrowthSeries` and `OediFatigueDataset` public constructors now bind
their nested source table's fixed SI schema/origin, workbook row IDs, checksum/column
context, series order, pressure and license. The deferred provenance case specifies
detached pressure/order/hash rejection. These constructor checks are unrun and do not
replace checksum-verified file loading or independent fatigue validation.

### Shared partial-pressure input contract (2026-10-29)

`h2physics.partial_pressure_pa` takes absolute pressure in Pa and mole
fraction, applies the ideal-mixture Dalton relation, supports NumPy broadcasting,
returns immutable arrays, and rejects invalid pressure/fraction domains. The finite
adsorption-vessel endpoint and oxygen-inventory result assembly call this helper;
the oxygen result audit independently recomputes pressure times wet oxygen fraction
from retained native snapshots. A deferred case was added under the finite adsorption
profile. Only static compile/lint/diff checks are allowed locally; no scientific case,
engine replay, data load, benchmark or Nurion submission has been run for this change.

### Shared mixture and thermal-failure integration (2026-10-29)

`h2physics.mixtures.GasComposition` now provides identified immutable fixed-gas
composition bookkeeping and signed component-flow conversion. The finite adsorption
gas binding delegates composition validation to it; property/EOS ownership remains
separate. Adsorption component-inventory arrays also reject boolean/string values
through the shared real-numeric boundary. `CanteraFrozenGasProperties.from_gas_composition`
checks species molar masses against Cantera metadata before provider construction or
native phase mutation, then maps it to the native ideal-gas provider. Subsequent state calls
reject a changed composition label. The provider also exposes native mixture molar mass,
and `ThermoState.heat_capacity_ratio` derives cp/cv only from derivatives on that state.
The deferred integration case records those contracts; it is unexecuted and adds no
experimental-mixture qualification.
`bind_radial_thermal_history_to_vessel`
samples a retained radial wall heat
field at an explicit radius and binds it to existing typed pressure/HELPR histories.
It requires exact clocks/time grids and matching cylinder surfaces; the radial-to-flaw
mapping still requires independent engineering evidence. Their added Nurion cases are
authored but unrun. Static compilation, Ruff, metadata-only inventory and diff checks
passed; no scientific model execution or cluster job submission occurred.

### Native relief trace integrity (2026-10-29)

`ReliefTankTrace` construction now freezes its aligned output arrays, verifies that
each accepted native interval spans the corresponding clock samples, recomputes
cumulative released mass/enthalpy and external heat, and checks the mass and total
energy residual histories from the retained native endpoint states. Inventory-floor
termination must retain a matching final event/state. The deferred
`facility-relief-trace-integrity` case requests a mutated-energy-history rejection.
This improves result integrity for the existing native relief model; it adds no
physical validation. Only static checks are allowed locally; no scientific replay or
Nurion submission was performed.

### Preferred-dispersion request snapshot (2026-10-29)

`DispersionScenario` now copies a supplied `solver_options` mapping into a read-only
scenario-owned snapshot, in addition to copying the top-level request mapping. This
prevents caller edits after construction from changing a later native run while
preserving the identity of physical native objects and callbacks. The existing
`selection-preferred-dispersion` deferred case checks the mutation boundary and direct
wrapper argument forwarding. Its receipt must match the provider result's acceptance and
source evidence, and its gas route uses a callback stand-in. It has not run; native engine status and the separate
HyRAM/SLABx physical limits remain unchanged.

### Conditional-risk result integrity (2026-10-29)

`ConditionalRiskResult.require_current()` now binds post-return use to the original
request/context identities, their owned native copies, source content, receptor and
branch-harm objects, native package functions/code, typed output and complete receipt
payload. The annual conditional-frequency accessor rechecks this binding. The deferred
facility chain includes output/receipt replacement rejection. This is object and
provenance integrity only; it does not improve physical validation. The entrypoint is
unexecuted; only compile, Ruff, diff and metadata-only inventory checks are permitted
locally. Do not submit it to Nurion without a separate user request.

### Radial heat-to-vessel history integrity (2026-10-29)

`RadialThermalVesselBinding.require_current()` now revalidates original pressure,
radial thermal and typed failure-history relationships before returning mapped data.
It fingerprints retained arrays, loads, evidence, mapped samples and declared callback
identities; `history` and `wall_temperature_k` access are guarded. A deferred bridge
case requests rejection after nested source replacement. Callback closure state and
all scientific radial-field/mechanics claims remain outside this integrity check. The
case is unexecuted; static compile/Ruff/diff and metadata-only inventory are permitted
locally, and no Nurion submission is authorized by this change.

### Cluster evidence path identity (2026-10-29)

The read-only result collector now rejects cluster environment/results paths that
are absolute but noncanonical aliases (duplicate separators, dot segments or a
trailing separator), parent traversal, root itself, backslashes and control
characters. This prevents ambiguous path strings from entering campaign/runtime
identity metadata. No collection or scheduler access was performed; local review
was static only.

### Model registry contract (2026-10-29)

`ModelSpec` validates each two-part ASCII family key, required ownership/purpose/
evidence descriptions and the closed status vocabulary. `model_catalog()` rejects
duplicate family IDs and invalid family/status filters. The generated catalog and API
manual were refreshed. This does not change the family count or executed evidence; its
metadata/API behavior remains pending the authorized Nurion campaign for runtime
validation.

## Isothermal EOS lookup acceleration

`src/h2physics/thermo/isothermal_eos_table.py` provides
`IsothermalEOSTable.from_eos(...)` for an immutable caller-bounded rho-T table
of pressure and isothermal characteristic speed. `linear` and `log_linear`
interpolation are explicit; pressure must be monotone with density and queries
outside the density, temperature, or implied pressure envelope fail closed.
The digest identifies the source EOS, interpolation mode and exact grid arrays.
`qualify_isothermal_eos_table(...)` compares seeded held-out pressure, inverse
density and cT samples with the same direct source EOS, and records error limits
and query timings. This is a property-provider comparison, not independent EOS
or pipeline validation. Case `isothermal-eos-table-interpolation-accuracy` is
registered in the Hangang `isothermal-eos` profile and has not run. Local static
AST review passed; no property table was generated locally. Focused usage and
limits: `docs/ISOTHERMAL_EOS_TABLE.md`.

### Sequential radial thermomechanical result guard (2026-10-29)

`RadialThermomechanicalHistory.require_current()` binds the coupled wall-heat and
quasi-static stress results to their original geometry, material, loads and temperature
profiles and fingerprints retained numerical arrays/evidence. The radial heat-transfer
deferred case requests rejection after changing nested stress evidence. Callback closure
state remains outside the guard. This has not been scientifically executed; no local
solver run or Nurion submission occurred.

### Guarded radial-to-HELPR handoff (2026-10-29)

`RadialThermalVesselBinding.predict_failure()` now checks the radial source binding
before and after calling the exact existing `HelprVesselFailure` owner. The sampled
`VesselFailureHistory` is passed through without reconstruction; the original typed
prediction is returned. `RadialThermalVesselFailureError` keeps the binding and native
cause/result when evaluation or post-call provenance fails. A Nurion-deferred case now
requests a real HELPR call and asserts prediction history identity. This is unexecuted
and supplies no vessel-life qualification or acceptance evidence.

### Radial thermal history to HELPR scope boundary (2026-10-29)

The guarded `RadialThermalVesselBinding.predict_failure()` handoff sends the original
scalar-temperature/pressure `VesselFailureHistory` to HELPR and retains the native
prediction. It does not consume the separate `RadialThermoelasticStressHistory`; HELPR
currently computes SIF/reference stress from its pressure difference and flaw geometry.
Therefore, this is a temperature-dependent material-property route, not a thermally
stressed crack-driving calculation. `docs/RADIAL_FAILURE_HISTORY_BRIDGE.md` now defines
the receiving request: an additive typed total-field path, explicit flaw orientation,
no pressure double counting, a native arbitrary-stress SIF method, bounded time
reconstruction and independent SIF/refinement checks. The user-facing claim must retain
this boundary until that receiving API and evidence exist.
The actionable request is maintained as `docs/REQUEST027_HELPR_THERMAL_STRESS.md`;
no code was changed in the receiving HELPR repository.
The radial bridge guard additionally requires the original typed failure history and
context, rejects an attached `native_trace`, and disallows native/reconstructed sample
states on its exact-grid route. A deferred case specifies unrelated-trace rejection;
it remains unexecuted.
The HELPR composition error exposes `stage`, `cause`, the original binding and any
prediction produced before a postcheck failure. The stale-context deferred assertion
ensures rejection occurs before the native evaluator call.
The issued binding also freezes identity ownership for the geometry, pressure loads,
service context, sample tuple and individual loading samples; equal-valued replacements
are specified for rejection in the deferred case.

The OEDI result now retains original HELPR scalar returns aligned with accepted SI
growth rates. Failure receipts link completed and failing rows to the measured source
Delta-K and da/dN; the deferred plan checks these fields and archive alignment. These
are unexecuted contracts; no scientific or failure-propagation evidence was added.

The OEDI observation reader and no-fit HELPR comparison can be imported together from
`h2physics.data`. Comparison symbols resolve lazily from the existing adapter when
requested; no duplicate solver or eager HELPR import is introduced. The error diagnostic
constructor validates completed source rows as an ordered prefix with the failed row next
and retains raw native returns for completed points. Nurion has not executed the receipt
schema case or actual HELPR failure propagation.

`OediFatigueComparison.points` also yields immutable row records joining source IDs,
dataset hash/URL/license, series/columns, measured ΔK/da/dN and raw/accepted HELPR rates.
The deferred case checks alignment and ratio-contract rejection only; those checks remain
unexecuted on Nurion.

The HE-Austenite source cases now capture `H2_DATA_AUSTENITE_ROOT` into each deferred
case's `source_path` at metadata collection. The Nurion provenance entrypoint checks
the exact nine-file acquired set, aggregate acquired bytes, each staged file's byte
size/SHA-256/publisher MD5, publisher-checksum verification marker, CC-BY permissions
and `validation_qualified = false`. `validation/cases/austenite_embrittlement.py` and
`validation/nurion_plan_example.py` pass static compile/Ruff; metadata-only inventory
remains 226 cases/40 profiles/47 modules. These are still unexecuted Nurion custody
checks; no scientific execution or submission occurred. First-level execution evidence
remains 59/72, and the full-programme estimate remains an uncertain 30-40%.

The Korean guide now has a complete comparison wiring snippet. It uses reconstructed
298.15 K and pure-H2 conditions only as declared assumptions, requires user evidence IDs,
and reads per-row outputs through `comparison.points`. It does not claim that the snippet
has executed or validates fatigue life.
Before collecting Nurion cases, set `H2_DATA_OEDI_FATIGUE_ROOT` to the staged OEDI XLSX
directory. Both OEDI validation case parameter mappings capture this `source_path`; missing
files produce a staging-specific error. No cluster job has been submitted for these cases.
The source-provenance case also parses `research/data/oedi-hydrogen-materials.toml` and
compares the staged file's SHA-256, MD5 and size plus dataset URL/license against that
receipt and the loader's own code pins. This remains an unexecuted custody check.
It also asserts the receipt key/identifier, acquired state, rights-permitted flag and
`validation_qualified = false`; this does not establish independent model validity.

`CoolPropMixtureProperties` is a new unexecuted fixed-composition HEOS mixture provider.
It takes `GasComposition`, optional species-to-CoolProp names and a bounded molar-mass
reconciliation tolerance; native PT/PQ/TQ calls are supplemented by optional caller-bounded
PH/PS/P-density scalar inversions on a sampled single-gas monotone interval. It rejects inverse
requests without configured bounds. The gas-composition deferred case exercises H2/N2
round trips, state identity/energy closure, and calls the shared isentropic nozzle with
basis, entropy and energy-ledger checks. `FrozenGasBinding` also checks the provider's
composition ID/species/mole fractions/molar masses against the gas declaration before
adsorption-vessel inventory calls; the deferred case specifies matching and tampered
bindings but remains unexecuted. Its endpoint gate admits gas, supercritical gas and
supercritical states while excluding liquid/two-phase states. Provider composition, basis
and backend fields are locked after initialization to prevent fingerprint drift; mutation
rejection is specified but unexecuted. The same deferred handler routes the bound provider
through an authored `FiniteAdsorptionVessel.snapshot` and checks free plus adsorbed component
closure; this demonstrates API/accounting composition only, not adsorption performance.
the Nurion `gas-composition` profile must install the optional `thermo` extra. No local
scientific execution or Nurion submission was done. Model evidence remains 59/72.
Inverse solving reuses its PT domain samples within `brentq` and caches repeated exact
PH/PS/P-density requests in a bounded LRU (default 512; zero disables). `inverse_cache_info`
and `clear_inverse_cache()` are available. The deferred case checks a two-entry cap, an
exact-key hit and reset; no timing benchmark has run.
The optional immutable `MixtureInverseGrid` stores PT samples for enthalpy, entropy and
density inversion and can be shared with a second provider only when its composition
fingerprint, property basis and inverse-temperature domain match. Candidate brackets are
checked with fresh states at the requested pressure. The deferred gas-composition case now
specifies grid reuse and composition-mismatch rejection; it remains unexecuted and does not
establish a speedup or qualify mixture EOS accuracy.
The same deferred case also specifies caller-buffer isolation, nonmonotone-array rejection,
and property-basis/temperature-domain mismatch rejection. These checks have been authored
but not executed.

The real-gas portion now uses a separate binary H2/N2 composition; the H2/N2/H2O object remains only for component bookkeeping. Grid PH/PS/P-density results are compared with the no-grid bounded baseline at an off-node pressure, and the deferred case records grid preparation cost, wall time and PT flash counts over three repetitions. These are synthetic runtime/performance diagnostics, not independent mixture-EOS validation; run them on Nurion.

The `gas-composition` result metrics now preserve grid fingerprint, composition digest, CoolProp version, property-basis reference and axes, with maximum temperature and property-specific absolute differences against the baseline inverse path. The timed comparison warms each provider, alternates run order, disables inverse-result caching and reports median wall time/PT flash count over three repetitions. It derives the inverse-query count needed to repay grid preparation when the sampled path is faster per query; otherwise the receipt states that no break-even exists. This is a benchmark-specific diagnostic, not a performance qualification. The case remains unexecuted and no Nurion job has been submitted.

Current implementation continuation adds `MixtureInverseGrid.write_npz(path)` and
`MixtureInverseGrid.read_npz(path)` for pickle-free cross-session storage. Restoration
revalidates the schema, arrays and fingerprint. A deferred Nurion contract checks the
round trip; it is not run. Keep this archive classified as a bracket hint, not a qualified
EOS table.

The quasi-static `RadialThermoelasticStressHistory` now exposes `require_current()` before
downstream coupling. It checks original output/source identities and fingerprints the
pressure loads, material, profiles and stress arrays. Its Nurion-deferred case specifies
same-valued output replacement and nested-profile mutation rejection. No SIF/fracture route
consumes this history yet; Request027 remains the receiving-project contract for that gap.

The new `RadialThermoelasticVesselBinding` composes an admitted vessel pressure/temperature
binding with the actual `RadialThermomechanicalHistory`. It requires exact source heat,
geometry, pressure-load and clock identity, full-wall stress support, and the explicit
`total_pressure_plus_thermal` convention. The deferred bridge case checks pressure
tractions, rejects an increment convention and checks convention-evidence mutation. It preserves the stress field for future
native integration; HELPR still receives only its pressure-driven history and no SIF
result is claimed.

The radial thermoelastic history API now exposes `stress_field_at(index)` returning a
guarded exact-time `RadialThermoelasticStressSample`. It carries BVP iteration/residual
diagnostics and the original load/profile/material objects. It never reconstructs an
intermediate time. The deferred case has index, identity and replacement checks authored;
run it with the designated Nurion fracture-fatigue profile before treating it as executed.

For vessel coupling, `RadialThermoelasticVesselBinding.sample_at(index)` returns a
`RadialThermoelasticVesselSample` joining that field to the original `VesselLoading`.
Its guard checks retained identity, exact time/clock, absolute pressures and mapped wall
temperature. It does not trigger HELPR: `HelprVesselFailure.predict()` remains a separate
pressure-driven route until Request027's receiving SIF API exists.

## Coding-first continuation — 2026-10-29

The finite adsorption-vessel adapter now also solves isothermal, fixed-composition
species inventory for pressure over an explicit caller bracket. It returns a
snapshot-backed residual receipt and rejects out-of-range targets, ambiguous sampled
matches and observed nonmonotonicity. The new `adsorption-vessel-pressure-inverse`
contract is planned only. It adds no fill or bed dynamics and was not executed.

`FiniteFacilitySource.ledger_history()` exposes immutable accepted-time cumulative
source, stored inventory, external mass/energy, transported enthalpy, ambient heat and
fixed-state source projection histories, with mass, energy and projection residuals.
Its dedicated `facility-source-cumulative-ledger` contract was added to the deferred
plan; the metadata-only inventory is now 230 cases across 40 profiles and 48 modules.
Static checks do not establish numeric closure or facility validity.

The radial wall heat API has an optional `guard_radial_material_temperature_domain()`
wrapper for caller heat-capacity/conductivity functions. It checks sampled values over
an explicit absolute-temperature domain, then enforces that same domain at each solver
property request. It preserves original callback behavior inside the domain and makes no
between-sample or material-qualification claim. Existing radial heat deferred invariants
cover range and positivity rejection; they remain unexecuted.

For adsorption observations, the data seed now targets Zenodo latest record
22305898. Its CC BY 4.0 archive is outside Git, with publisher MD5 and local SHA-256
verified. The local receipt pins rights and version metadata; the archive listing,
README and data dictionary were read without running bundled analysis code. The
reported signed uptake is excess loading, so it cannot be passed into the absolute-
uptake finite vessel as-is. Raw source CSV schema, uncertainty, and a licensed
excess-to-absolute correction remain unreviewed. The old v1 COx workbook record is
retained for provenance and marked superseded.

The exact-time stress-path export is available as
`RadialThermoelasticStressHistory.stress_path_at(sample_index, radius_m)`. It provides
immutable total radial/hoop/axial/von-Mises values on an explicit radial wall grid and
retains the source stress sample. It performs no time interpolation or extrapolation and
does not calculate SIF; connect it only to a receiving fracture method that explicitly
accepts nonuniform total stress fields. The authored Nurion case has not run.

## Latest implementation continuation

Implementation added four reusable seams without launching physical cases: the geological adsorption loader now parses the four processed signed-excess tables with pinned source hash and fails closed on absolute-uptake requests; `estimate_line_cooldown()` accounts for caller-supplied line-segment heat duties and retains source segments; an admitted steady HyRAM run can project onto a caller-defined `IntervalMassSource` with separate mass-rate/enthalpy gates; and the exact-time radial thermoelastic stress path supplies total stress components to receiving fracture software without generating an SIF. The associated metadata inventory is 233 deferred cases / 42 profiles / 51 modules. Local checks are limited to py_compile, Ruff, TOML parsing, metadata inventory refresh and diff whitespace. No scientific entrypoint, test suite, remote validation or cluster submission ran.

Next implementation targets remain the full coupled facility chain, dynamic gas line inventory/cooldown, nonuniform-stress receiving fracture API, raw adsorption logger/calibration uncertainty audit and source/field validation for the preferred HYRAM and SLABx-LH2 paths. Do not label these seams as independently validated models.

A follow-up equipment integration adds `IsobaricEnthalpyPath` and `estimate_line_cooldown_with_provider()` in `h2physics.cooldown`. This passes an existing `PropertyProvider` (including the optional CoolProp HEOS provider) into cooldown energy accounting while retaining pressure, basis, phase, evidence and exact coolant endpoint states. `PropertyBackedLineCooldownEstimate.require_current()` rechecks provider states before a caller consumes its mass/duty outputs. The existing thermal-utilities deferred case covers this API; it remains unexecuted. Only py_compile, Ruff and scoped diff checks ran.

The raw line-cooldown ledger now has the same `require_current()` boundary. Construction-time fingerprinting binds its retained segment declarations, callback identities, duties, evidence IDs and mass/energy fields; each access check re-evaluates the wall/fluid duties before downstream use. The deferred contract now names post-estimation receipt mutation. This is implementation only and remains unexecuted scientifically.

The raw estimate's public mass and energy properties now invoke that check automatically. Its original constructor keyword names are preserved through a custom initializer backed by private frozen numeric fields. Static checks passed; no deferred scientific case or remote job ran.

The shared-EOS path and provider-backed wrapper now have independent receipt fingerprints for provider identity, declared path metadata and endpoint states. Their public result properties reject post-capture mutation and re-query provider endpoints. Deferred endpoint-mutation coverage was added but not run.

The native line audit now consumes `integrate_unidirectional_equipment_rate()` output. That typed receipt retains signed sample rates and rejects observed reverse flow before `audit_dynamic_line_cooldown()` compares gross coolant mass with native cumulative enthalpy/ambient ledgers. Matching clock/window and property basis are mandatory; coolant-only boundary energy remains an explicit caller premise. Between-sample reversal and accepted-sample quadrature convergence still require refinement. Its synthetic deferred contract was updated but not executed.

`compare_unidirectional_equipment_integrals(coarse, fine, normalized_tolerance=...)` now requires one shared trajectory ID and nested accepted times, and records signed, absolute, normalized and interval-count changes for same-clock/window accepted quadratures, plus the caller-threshold decision. The dynamic-line audit can retain that comparison. The decision is not an error bound. No dynamic run was executed and no convergence claim is supported yet.

The signed rate integral, refinement receipt and dynamic audit now fingerprint their retained samples and derived fields, with `require_current()` checks before downstream use. The deferred case mutates a retained rate sample and requires invalidation to propagate through the refinement and line audit. It remains unexecuted.

The accepted finite-facility cumulative mass/energy history now carries its exact issuing source/run binding and fingerprints all returned ledger arrays, including residuals. Call `history.require_current()` before downstream use; detached reconstructed results remain analytical copies and are not admitted receipts. A deferred case checks detached-history forgery and post-capture array mutation. No physical execution was performed.

The admitted HyRAM finite-source receipt now exposes `component_flow(GasComposition)` for explicit multicomponent mass-rate handoff. It preserves exact H2 flow under the declared composition and returns a guarded read-only rate vector. It makes no entrainment or mixture-property inference; a downstream EOS and state projection must remain caller-selected. The deferred contract includes component closure and mutation checks; it has not run.

The source-neutral `WindowUtilityCost` receipt now fingerprints original tariff identity/content, amount and cost lines plus its bound projection. Its `require_current()` refuses changed quotes and then replays the existing source audit/pricing. Shared hydrogen-economics metadata now includes post-price tariff mutation coverage; no finance case was executed.

`IntervalMassSource` now has a shared issuance fingerprint across its source/location/state/evidence/end reason and exact bins. `require_current()` is called by source mass/rate/window/rebin operations and by preferred SLAB, HyRAM, source hashing, conditional-risk and oxygen-deficiency admission paths. New deferred metadata case `finite-source-immutable-lineage` covers nested state/provenance and array mutation; it was not run. Current inventory is 235 case definitions / 42 profiles / 52 modules; executed first-level evidence remains 59/72.

The four geological-material tables now also expose a bounded `GeologicalSurfaceExcessProvider` implementing the existing `AdsorptionProvider` protocol for one caller-selected measured temperature and pure H2 pressure curve. It linearly interpolates loading in log pressure only inside measured bounds, retains the signed `surface_excess` basis, and fingerprints source points/arrays. The finite-vessel owner explicitly rejects this basis. The data case was extended but remains unexecuted; inventory counts do not change because this extends its existing case.


## 2026-10-29 continuation

The geological surface-excess adsorption provider now retains weighted source-row IDs and reported uncertainty/LOD/LLOQ in immutable `AdsorptionSourceObservation` objects on `AdsorptionState.source_observations`. Fields explicitly use mol/kg; the selected source values are mmol/g and are numerically equivalent. Per-site weights must sum to one; missing fields stay `None`, and no statistical propagation is inferred. The deferred provider case checks source-value retention, immutability and invalid receipt gates but is unexecuted. The supplied wrapper confirms host `CLUSTER_LOGIN_HOST` and user `CLUSTER_USER`; `python/3.12.5`, queue `normal`, account `ALLOCATION_ACCOUNT`, and the public Zenodo archive endpoint are available. No matching hydrogen-model job or staged source archive exists. The current legacy pins cover completed cases only; the next step is to create an exact source snapshot and launch this case under the user's standing Nurion-validation instruction.

The finite-vessel uncertainty bridge also rejects partial source coverage before
building a species vector: every declared species at every adsorption site must be
covered. The existing `adsorption-vessel-uncertainty-lineage` case now checks that
an H2-only uncertainty receipt cannot be reported as zero uncertainty for N2. It
remains deferred and has not run.

The latest remote setup attempt returned `No usable nurion shared connection` before running any shell command. No environment, data file or PBS job was created by that attempt. Per the user's connection rule, stop remote commands and ask for manual reconnection; do not retry authentication. A local immutable campaign snapshot also remains pending because the tool rejected the temporary-index commit-object command with `blocked by policy`. The current package work remains unexecuted.

Coding-first continuation: `ParcelInitialFlash` and `flash_initial_liquid_release()` now link
the native PH equilibrium state and saturated endpoints to a finite phase-mass ledger. The
receipt checks basis, pressure, quality, evidence identity, mass closure and enthalpy closure;
the remaining liquid mass is directly consumable by the parcel-flight API. The new
`parcel-initial-flash` deferred contract includes two-phase, mass/energy and refusal gates.
Korean user documentation now describes its API and scope. This case is authored only and
has not run; no local scientific test was executed. Nurion remains unavailable under the
approved shared-session method, so remote verification cannot proceed until the user
manually reconnects. Full programme implementation is not complete.

The fixed-composition CoolProp route now exposes direct PT/PQ/TQ state calls. Its
`MixtureThermoState` keeps CoolProp mixture quality in `vapor_mole_fraction` and
leaves the pure-fluid `vapor_mass_fraction` unset, so saturation status cannot be
silently reinterpreted on a mass basis. The deferred gas-composition contract now
includes quality-basis and invalid-input gates; these cases remain unexecuted.
Unsupported mixture PU and density-U input pairs validate scalar domains before
raising their explicit unsupported-operation error. Static syntax and whitespace
checks passed; no thermodynamic calculation or scientific test was run.

Parallel implementation now adds `scenarios.py` for explicit lazy dependency
composition and `adapters/parcel_pool_chain.py` for admitted deposited-stock native
pool continuation with conservative vapor intervals. Read SCENARIO_COMPOSITION.md
and IMPLEMENTATION_BACKLOG.md for API boundaries and remaining host/receiving work.
Counterflow PH callbacks now check returned pressure/enthalpy; flowing-exchanger
trace indices preserve supported negative indexing while validating bounds.
All additions remain unexecuted scientifically. Static compilation and whitespace
checks passed; no local scientific case or Nurion command ran.

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

The long-running goal was resumed through the app Resume goal control on 2026-10-29
and get_goal subsequently confirmed active. Keep the goal active while continuing
implementation; do not mark it complete based on catalog coverage. Metadata-only
inventory currently reports 249 cases / 42 profiles / 65 modules. No scientific
case was executed. The next parallel lanes are cycle-mean adsorption product
handoff and operation-bound facility economics; actual transient native source and
thermal-feedback gaps remain tracked in IMPLEMENTATION_BACKLOG.md.

`adapters.facility_economics.price_facility_operation()` prices an admitted exact
operation through the existing source-neutral tariff API. Product boundaries remain
explicit; net thermal utility quantities, component set and basis must match the
original operation. `adsorption_product_window()` reports actual native cumulative
species increments over selected checkpoints as an explicit mean stream; it makes
no intra-cycle flow or CSS inference. Oxygen source admission now excludes init=False
fingerprint fields when reconstructing validation copies, fixing constructor rejection
introduced by source provenance fields. New code is unexecuted scientifically.

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

For declared boundary jumps, `run(interval_boundary_streams=...,
boundary_change_times_s=...)` restarts the same native simulator class at each
explicit interval, carrying the exact final physical state and augmented ledgers
into the next initial state. The interval callback receives exact physical time
and interval bounds so the caller declares the appropriate endpoint command.
`native_segments` retains each simulator and its original relative rows. The
continuous callback route admits declared changes only on its native fixed grid;
unknown event roots and unresolved jump-limit conventions are not inferred.

`CoolPropMixtureProperties.phase_partition_pq()` now obtains native VLE phase
compositions and exposes separate mass/mole quality plus finite phase component
amounts. See API.md. These new states and segmented heat runs remain unexecuted.

`adapters.mixture_flash_separator.separate_equilibrium_mixture()` uses the
explicit bounded native PH branch inverse for a finite equilibrium throttle.
Native liquid/vapor enthalpy and density are read from the SAME equilibrium flash
through phase keyed outputs, not by reflashing the overall mixture at Q=0/1.
Explicit upstream/downstream pressure, equilibrium and negligible mechanical-energy
premises, branch evidence and component-mass/total-enthalpy budgets admit this
finite split. Original native compositions and finite amounts remain available.
This implemented_unverified equilibrium level does not resolve nucleation delay,
phase slip, jets, droplets or separator hydraulics. No scientific case was run.

## Finite coolant and native mixture PH continuation — 2026-10-29

The shared electrochemical thermal RHS now optionally integrates finite liquid
coolant enthalpy, retaining opposite stack/coolant heat, imposed-pressure property
domain and independent combined energy residual. Existing prescribed-coolant route
keeps its original API. Read FINITE_ELECTROCHEMICAL_COOLANT.md. Native mixture PH
branch inversion and finite equilibrium separation retain same-flash phase properties,
component amounts, root evaluations, upstream reconstruction and failure context.
These are implemented_unverified model levels, not new executed evidence. Metadata
refresh reports 257 cases / 42 profiles / 73 modules. No scientific model or case ran.

## Separated native gas compartments

`adapters.fuel_cell_compartments` runs distinct frozen pure-H2, pure-O2 and water-
vapor native gas volumes using prescribed shared-stack Faraday rates, explicit
volumes and separate thermal boundaries. Each volume evolves its own pressure,
temperature, species and internal-energy ledger. The compartments never share a
reactor. This level does not close combined reaction-energy allocation or feed
pressure back into voltage. Request031 specifies the actual missing pressure/
activity-sensitive stack and simultaneous multivolume driver. The authored native
case and all physical execution remain pending on Nurion.

## Bounded native inventory property integration — 2026-10-29

BoundedMixtureInventoryProperties now exposes original frozen composition metadata
and routes rho/U through the explicit bounded native inverse. Authored cases include
actual FrozenGasBinding and LH2DT low-level property seams; their profile requires
the reviewed LH2DT dependency. No native calculation or test ran locally. Deferred
metadata is 261 cases / 42 profiles / 77 modules. The original objective remains
active; implementations and authored definitions do not establish qualification.

`adapters.fuel_cell_compartment_energy` compares actual independently integrated
native reaction-port masses as H2-equivalent extents. Shared callbacks alone do not
prove identical adaptive quadratures. The complete-window diagnostic retains actual
compartment internal-energy changes, conversion-plane enthalpy, compartment heat,
solid/coolant storage, original electrical energy and external thermal heat. A
signed unresolved combined energy residual remains explicit; the diagnostic does
not infer a missing membrane/caloric coupling term or declare reaction energy closed.
Exact common stack, clock/window and allocation evidence are required.

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

`adapters.liquid_accident_energy.liquid_accident_energy_diagnostics()` reads the
original mass-ledger parents and preserves separate flash enthalpy, weighted flight
heat/work/escaping vapor energy, selected impact internal/kinetic/interfacial energy
and pool-vapor reference enthalpy. It never adds residuals from different control
volumes into a global closure claim. Native fixed-area output lacks cumulative
substrate heat and pool U/PV-work fields; flash/launch/rebound/unselected mechanical
boundaries also remain explicit unresolved terms. Request033 defines the needed
native energy outputs and finite-wall continuation. No sparse heat-flux quadrature
or balancing heat is invented. The existing deferred mass-ledger case now includes
these energy diagnostic scopes but has not run.

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

Current follow-up work has hardened repository acquisition metadata contracts:
exact raw metadata/hash pairing, safe cache keys/version labels, bounded HTTPS metadata
responses with downgrade-redirect rejection, explicit publisher checksum normalization,
and attachment basename collision rejection. Missing provider DOI/author values remain
permitted metadata gaps; recognized license labels with identifier-only values receive
their canonical public license URI. These source changes are unverified. A fresh build
then matched all187 Python package files in the wheel/sdist and passed archive exclusion
checks. Current artifact hashes are recorded in PROGRESS.md and research/release_audit.md;
later source edits require another pinned build before release review.

Shared core identity and observation constructors now validate required strings,
units, quantities, bases and context pair types before use. Observation context is
copied into nested immutable tuples; `SourceLocation` and `IntervalMassSource` now
require explicit typed provenance and finite state/geometry objects. Existing
scientific equations and model ownership are unchanged; no case or solver was run.

Follow-on API hardening validates direct `ReportedSIQuantity` construction and
fails closed when a raw reported pressure is requested as EOS-ready absolute Pa.
This protects the known unresolved gauge/absolute basis at the public data boundary;
it is not a new pressure qualification or a scientific result. No local model/test
was run for this follow-up.
Native finite separator and relief APIs also reject non-string clock/source identities
before invoking string methods. No native simulation was executed for these edits.
Finite hydride, relief-lift and microsphere public paths now apply the same type-first
identity validation. No scientific or native executions were added.
After the additional native clock-boundary edits, a second fresh sdist/wheel build
and archive audit matched all187 package Python files to current source with zero
missing, extra or byte-different members. Excluded raw
data/credential/path checks passed. This is packaging evidence only; the artifacts
are local development outputs, not a publication or Nurion execution snapshot.

The finite pure-fluid separator's clock identifier now receives an explicit string
type check before whitespace validation, yielding a clear input error for invalid
types. The operation still assigns absolute time from its caller-declared start.

Following the shared core identity/observation/source API hardening, the release
snapshot was rebuilt again and compared byte-for-byte: 187/187 Python members match
source in both archives; excluded data/content checks pass. The current hashes are
in research/release_audit.md and PROGRESS.md. These remain local development
artifacts, not publication or validation evidence.

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

## Goal continuation — 2026-10-29

Current source additions: typed fuel-cell operating/activity correction; native
mixture partition selective component-withdrawal accounting; adsorption source and
state uncertainty provenance through absolute-basis vessel snapshots; caller SIF
evaluation over exact-clock total-stress samples; strict native accepted-edge pool
energy ledger adapter. Deferred contract metadata was updated for these interfaces.
Ruff, compileall and document-link audit passed statically. No scientific case, model,
standard test or Nurion run was performed. Request031 simultaneous stack/compartment
feedback, Request032 changing-mixture inventory flash and vessel driver, Request033
native pool energy integration/finite wall, Request027 native total-field SIF, and
absolute geological uptake qualification remain unresolved; do not report complete.
The current development wheel/sdist audit predates these source edits and must be
rebuilt before any release/snapshot claim. Preserve all untracked files.

Latest follow-up on 2026-10-29: rebuilt sdist/wheel after the above edits. Release
content audit passed with 191/191 package Python members matching both archives,
zero missing/extra/different source files, and excluded raw data checks passing.
Artifact SHA-256 values are maintained in `research/release_audit.md`; this is a
development packaging result only, not installed-Nurion execution or public-release
clearance. Full Ruff and compileall over `src/h2physics` and `validation/cases`,
document links (2,908 paths) and relative-import audit (191 modules, 0 unresolved)
passed. No tests or scientific models were run.

Subsequent focused review corrected uncertainty aggregation (independent errors use
weighted variance; provider-propagated state uncertainty is an aggregate species
vector, not summed site sigmas) and separated finite-wall heat inputs from prescribed
external-reservoir mode. `bind_native_pool_energy_ledger` now requires explicit mass
and energy budgets. These newest edits have passed lint/compile/doc audits but the
archive report must be refreshed again if packaging status is cited.

Further follow-up added `bind_relief_to_line_cooldown`: this records a common-clock
closure comparison between native relief cumulative release and caller-supplied line
inlet cumulative mass/enthalpy. It does not calculate routing, transform states, or
couple solvers, and must not be described as a complete facility operating sequence.
The deferred contract is `validation/cases/relief_cooldown_interface.py`; do not run
locally. The request now accepts only retained relief sample times to avoid smearing
valve events. Full source lint/compile and the refreshed source/wheel content audit
pass; no scientific case ran. Current archive hashes and source-member counts are in
`research/release_audit.md`.

Later follow-up exported `OperationalScenarioReceipt` and
`HydrogenInventoryHandoff` through `h2physics.adapters`. They join existing native
results on declared clocks and explicit caller evidence; they do not couple solvers.
The operational receipt permits absent actuator/relief/protection components. The
oxygen source digest was confirmed to copy dataclass init fields only; its added
deferred finite-source contract uses synthetic provenance. Current static checks and
archive audit are recorded below after integration.

## Current continuation — 2026-10-30

The current source inventory is 75 families (20 implemented, 37 native-adapter-
verified, 18 implemented-unverified), 279 deferred cases across 45 profiles and
63 case modules, with 66 curated profile/module associations. Source-only audits
report 1,260 public definitions across 206 modules, 1,407 bound relative imports
with no unresolved targets, and 3,286 Markdown paths across 300 files with no
missing destinations. These inventories are not model validation.

Recent local integrity work restricts counterflow workbook and microbial-current
observation provenance to their checksum-validating readers; solid-reaction traces
and CoolProp phase/inverse results require owner-issued receipts; QMC summaries
reconstruct from their exact design rows; and facility-consequence handoffs detect
changed evaluator code/configuration. Spherical-wall post-solve failures retain the
successful SciPy integration and original exception. Dataset cache/replay guards reject
symbolic-link and junction aliases without claiming redistribution clearance. All
corresponding cases remain deferred.
AST parsing, static inventories and `git diff --check` were used; no scientific
tests, model calculations or Nurion jobs were run.

The local goal remains active. The major unresolved physics are owned by receiving
engines through Requests012, 027 and 031–035, alongside data qualification and the
full 279-case Nurion campaign. The older 30–40% programme estimate and 59/72
execution checkpoint describe an earlier state and are not current completion
percentages.

## Latest engine-model continuation — 2026-10-29

Cantera 3.2 official documentation supports a native moving piston Wall and an
illustrative gaseous-fuel engine configuration. The local reciprocating addition is
a premixed closed H2/oxidizer interval, with no valve flow, spark/injector, wall
heat, flame propagation, complete cycle or shaft/brake output. The open Brayton
reference is a separate single-point Cantera HP-equilibrium cycle; it has no maps,
coupled shaft losses or qualification. Both are implemented-unverified and share
the `hydrogen-engine` chemistry profile. Six deferred cases cover the two bounded
levels and direct-summary integrity; no case or native calculation was run. See
ENGINE_CYCLE.md, OPEN_BRAYTON_REFERENCE.md, Request034 and Request035.

That engine-model checkpoint was followed by additional work summarized at the top
of this handoff. The current inventory is 263 deferred cases across 45 profiles
and 55 modules, 58 curated profile/module associations, and 74 catalog families
(20 implemented, 37 native-adapter-verified, 17 implemented-unverified, none planned).
The closed-charge hydrogen cylinder and open Brayton reference remain unverified;
Requests034/035 define higher-fidelity engine levels. These are source counts, not
validation evidence. The overall research objective remains active and incomplete.

### Continued source implementation

`adapters.bind_absolute_adsorption_state()` now connects the existing finite-vessel
API to a source-row-complete, independently qualified absolute loading state at its
exact recorded condition. It rejects surface excess/source-defined loading and does
not fit or interpolate an isotherm. The common-clock LH2DT scenario receipt also
accepts an optional thermal utility ledger whose profiles match the native run clock
and full window, with explicit caller-supplied `utility_to_dynamic` evidence. This
does not couple utility duty to the LH2DT solver or prove heat-source ownership.

Whole-package Ruff/compileall passed; document audit checked 2,947 local paths across
283 Markdown files with zero missing; relative-import audit found 1,172 bound
imports and zero missing/unresolved across 192 modules. Deferred metadata inventory
is 268 cases across 42 profiles/83 modules. No deferred case, unit/scientific test,
physical model or Nurion job was run. A fresh isolated sdist/wheel build and
`scripts/release_audit.py` subsequently passed: 192/192 package Python files match
working source in both archives, and raw-data/credential/path exclusion checks
passed. Exact hashes are in `research/release_audit.md`. This is packaging content
evidence only. The full programme remains incomplete: estimated progress 30–40%,
accepted first-level evidence 59/72.

The subsequent mixture-separator follow-up hardens direct `MixturePhaseWithdrawal`
construction against forged component/enthalpy receipts and supports q=0/q=1
withdrawal by requiring zero stock and withdrawal in the absent phase. It checks
phase-total consistency against native mole quality. The deferred phase-partition
contract covers forged receipts and both endpoints. Request032 still needs a
native changing-composition volume/internal-energy flash, phase events and accepted
time integration; this host ledger is not an inventory simulator.

`ReliefCooldownPort` now adds a typed phase/property/absolute-pressure contract to
the relief-to-cooldown receipt. It requires matching phase and full PropertyBasis,
checks those bases against the native relief provider and line inventory, and keeps
port evidence in the receipt. Phase changes need separate receipts; this is still
not native event handling or a coupled relief/cooldown solver. The deferred contract
checks phase mismatch. Scientific cases remain deferred.

The electrochemical voltage-property mismatch was also fixed by moving reversible
and thermoneutral voltage properties onto `ReactionEnergy`, where their Gibbs and
enthalpy fields live and where `HydrogenStack.evaluate()` reads the reversible
potential. New `electrochemical_activity` metadata covers the synthetic activity
correction path without executing it. Deferred inventory: 269 cases/42 profiles/84
case modules. Request031's evolving channel-pressure/activity/thermal feedback is
still a receiving-owner implementation, not closed by this algebraic contract.

The H2 handoff seam is now covered by a deferred actual PV/fuel-cell fixture and
`OperationalScenarioReceipt` now detects post-bind mutation of its declarations and
retained dynamic inventory/transfer content. Its deferred adversarial case includes
this guard; execute it on Nurion with the full LH2DT profile later. This remains a
receipt integrity check and does not bind caller-attested external rates to a solver.


species-basis compatibility guard. Adsorption uncertainty output now rejects
partial source-row coverage rather than implying zero uncertainty for an absent
site/species. Both remain unexecuted and must be included in the next source-pinned
Nurion plan. `scripts/validation_inventory.py` and `scripts/cluster_profile_requirements.py`
now reconcile the active case/profile plan; the generated inventory reports 221
deferred definitions across 39 profiles and 40 modules, all unexecuted.


The scoped host coding backlog has been reconciled: the local absolute-adsorption
handoff, common-clock utility receipt and native mixture phase-withdrawal endpoints
are implemented with deferred cases. The remaining open source items are explicitly
owned by receiving native engines (Requests 027, 031–033 and others in the backlog)
or require separately qualified scientific measurements and constitutive inputs.
No host-side replacement solver is inferred for those limits. At this checkpoint the
whole research goal is still incomplete (uncertain 30–40% effort estimate; 59/72
historical first-level execution evidence); all new cases remain unrun for the later
Nurion campaign.

Later follow-up exported `OperationalScenarioReceipt` and
`HydrogenInventoryHandoff` through `h2physics.adapters`. They join existing native
results on declared clocks and explicit caller evidence; they do not couple solvers.
The operational receipt permits absent actuator/relief/protection components. The
oxygen source digest was confirmed to copy dataclass init fields only; its added
deferred finite-source contract uses synthetic provenance. Current static checks and
archive audit are recorded below after integration.


## Continuation update — 2026-10-30 (latest)

The LH2DT relief interval driver preserves accepted native intervals, transitions,
aligned ledgers, trial counts, terminal metadata, and the original exception if a
later interval fails. Finite-hydride post-solve assembly failures likewise retain the
accepted native solution and original cause. ELVHYS4.2 recorder blocks now reject
direct and replaced observations that claim checked source identity. Their deferred
contracts were added to the finite-relief-lift, finite-hydride and fracture-fatigue
profiles. The plan has 295 cases across 50 profiles and 67
case modules. AST-only inventories report 1,262 public definitions across 206
modules, 1,411 bound relative imports with no unresolved targets, and 3,295
document paths across 300 files with no missing targets. These are static checks
only; no tests, imports, physical calculations, downloads, or Nurion jobs were run.

The Cantera closed-charge engine now retains its native reactor/network/wall,
accepted crank/time/state prefix, failed target and original exception when an
advance or trace assembly fails. The deferred hydrogen-engine-failure-prefix
contract adds a failure after two accepted samples. This brings the plan to 295
cases; no model or validation case was executed.


Conditional-risk native bindings now require the reviewed installed-owner issuance;
the PV-electrolysis handoff accepts only the exact finite thermal-stack owner's
current solver-issued trace. Both strengthen existing deferred cases without
changing the 295-case count. No tests, calculations or Nurion jobs were run.


ThermalEffectsFile now issues its observation blocks through the checked HDF5 reader;
caller-created or replaced ThermalBlock values cannot claim that file's digest. The
existing shock-tube-data contract covers parser issuance and forgery rejection. The
plan now contains 295 deferred cases; none of these new contracts has been executed.


Sobol sensitivity summaries now require a completed native analysis receipt; native
indices, masks, batches and evaluation lineage are retained and checked for currentness.
The existing joint-propagation case was extended, so the plan remains 295 cases. No
tests, calculations or Nurion jobs were run.


Thermodynamic table qualification decisions now recheck their sealed report values
and nested GasEnvelope bounds before reporting accuracy or speedup. The existing
table freshness case covers post-issuance mutation; the 295-case plan is unchanged.


PIFIRA EffectiveAreaResult is now issued only from the source-bound effective-area
calculation and checks its retained fit, geometry, arrays and native function before
thermal-target heat-flux use. Its existing deferred contract adds fabrication,
clone and forced-mutation rejection; the plan has 295 cases.


The SLABx-LH2 gas-jet run receipt is now issued only by run_slabx_lh2; direct
construction and clone replacement cannot assert native provenance. The new
slabx-lh2-run-issuer case and preferred-dispersion clone check bring the plan to
295 deferred cases, with 10 model-selection cases.


DiffusionSlab result projections now retain their exact solver-issued TransportResult
and check it before use. The existing material-transport case adds fabrication,
cloning and post-capture mutation checks; total remains 295.


FlashFrontTrace now requires native run_material_front() issuance and freshness of
its retained sparse graph and output arrays before downstream use. The existing
flash-front binding case covers cloning and graph mutation; the plan remains 295.


Finite adsorption product-delivery receipts now require the vessel owner, reconstruct
their component and total deltas from sealed endpoint snapshots, and are freshness
checked around mass-flow conversion. The existing deferred handoff case covers
fabrication, cloning and mutation; total remains 295.


CounterflowFlameResult now requires a one-use receipt issued by the native
solve_counterflow_diffusion_flame path; a caller cannot reproduce its old self-seal
around fabricated output. The existing counterflow-flame profile gained this issuer
case, bringing the plan to 295 cases.


Native FDS artifact receipts now verify the complete captured file set and hashes
before use, rejecting edits, additions, removals and symlink aliases. The existing
dormant obstacle-dispersion case covers mutation; total remains 295.


ProtectedEquipmentRun now requires post-execution one-use issuance bound to the exact
native run, driver, plans and accepted actions. The existing facility-protection
contract covers fabrication and clone rejection; the 295-case plan is unchanged.


JetRadiationField now requires the one-use result token issued inside
line_source_irradiance; direct construction of its former private issuer cannot mint
a result. The existing jet-radiation case covers this; 295 cases remain.


FuelCellCompartmentTrace now requires one-use issuance from SeparatedFuelCellCompartments.run()
before a self-consistent binding can be established. The existing separated-pressure
contract covers direct construction; total remains 295.


HELPR vessel failure/capacity results now require native-method one-use issuance and
seal their fields. The radial thermal-vessel handoff checks prediction freshness; the
existing vessel cases cover fabrication, cloning and mutation. The plan stays 295.


MultiphaseEquilibriumResult now requires native Cantera equilibrium issuance, seals
its state/phase/snapshot bindings and checks freshness before amount projections.
The existing solid-native-caloric contract covers fabrication and mutation; total
remains 295.


The missing oxygen-deficiency profile is now enrolled with its source-digest and
oxygen-room-result issuer cases. Current metadata inventory is 295 deferred cases
across 50 profiles, 68 case modules and 71 curated associations.


BiologicalRun now requires issuance after the native QSDsan integration and balance
audit, and seals solver histories, live state, balances and source/version bindings.
A dedicated QSDsan/BioSTEAM biological-process profile covers the new receipt case.
The current plan is 295 cases, 50 profiles, 68 case modules and 71 associations.


OpenBraytonRun now requires issuance from run_open_cycle_brayton(); a self-computed
mechanism signature no longer proves native output. The existing summary-integrity
case covers direct construction; total remains 295.


ScenarioResult can now be issued only inline after OperationalScenario.run() records
the graph output; its former token factory could be called independently. The existing
scenario-composition case covers this, with 295 total cases.


Gas concentration alarm and voting receipts now require one-use object-specific
issuance; reusable module sentinels could previously be imported to fabricate them.
The existing facility-concentration-alarm case covers cloning and token replacement;
total remains 295.


PsaCycleRun now requires native-cycle completion issuance and seals its checkpoints,
totals, schedule and owner identity. Cycle accounting checks currentness before and
after projection; the existing adsorption-cycle case covers fabrication/cloning.


UndergroundTrace now requires issuance by the completed native UH2SC run after audit;
dataclass replacement cannot claim that identity. The existing underground-storage
case covers it; the 295-case plan is unchanged.


PoolFireTrace now uses an opaque one-use token minted only after native execution and
audits; callers cannot invoke a token factory to fabricate a fire run. The existing
pool-fire-baseline case covers token forgery and cloning; 295 total.


OxygenCriterionResult now requires evaluator issuance, binds the exact room and
criterion, and rechecks source currentness plus the sealed screening summary. The
existing oxygen-result contract covers missing/arbitrary tokens; total remains 295.


Bauwens overpressure and native CJ/frozen-shock results now require one-use issuance
and currentness. Their prior missing verification coverage was filled with two
synthetic deferred cases and capability-specific profiles. Current plan: 295 cases,
50 profiles, 68 modules and 71 associations.


PhotoConversion and PhotoOperationTrace now require native operation issuance, seal
nested inputs and arrays, and check currentness before downstream summaries. The
existing photochemical operation case covers forgery and mutation; the plan remains
295 cases.


StagedElectrochemicalTrace now requires issuance after all native owner runs complete;
direct construction and dataclass replacement are rejected in the existing staged
electrochemical contract. Total remains 295.


NativeExchangeReceipt now issues only from bind(), validating distinct sides and
equal/opposite interval heat. Its consumer rechecks source, side, clock and energy
balance; the existing thermal-native-HX contract covers fabrication and cloning.


HydrogenEconomicsResult now requires evaluator issuance and seals its physical
projection, provider, finance inputs, window cost and native LCOH/NPV arrays. The
existing economics-native-direct case covers fabrication, clone and mutation; total
remains 295.


ParcelTrace now requires successful SaturatedParcelFlight.run() issuance, seals
accepted/trial/native histories and mass-energy-momentum summaries, and is checked
before population/impact consumption. Existing droplet-transport cases cover forgery
and mutation; total remains 295.


EmbrittlementBlock now requires reader issuance and seals observation/source/composition
rows before paired-property use. Its existing Austenite contract covers direct
fabrication, token reuse and post-issuance mutation; 295 cases remain.


Pressure-peaking workbook/block receipts now require checked-reader issuance and
source/content currentness. The synthetic XLSX loader-provenance case raises the
plan to 295; fracture-fatigue now contains 25 deferred contracts.


LH2 reliquefier steady results/dynamic steps and finite product receipts now require
native issuance, owner binding and currentness before product collection. Pump traces
were already guarded. Existing reliquefier-product-guards coverage was expanded;
total remains 295.


Cantera EquilibriumResult now requires owner issuance, binds its exact phase handle and
checks summary/native phase currentness before flash-front use. Existing
flash-front-binding coverage rejects direct construction and cloning; 295 total.


Cantera ReactorTrace and FreeFlameResult now require native one-use issuance and
sealed reactor/flame state; temperature-rise and flash-front consumers check
currentness. Existing flash-front-binding coverage includes fabrication, clone replay
and native mutation; the 295-case plan is unchanged.


Two synthetic XLSX provenance contracts now cover the fermentation and hydride-tank
readers in the source-data-ingestion profile. At this prior checkpoint the inventory was 295 cases, 50
profiles, 68 case modules and 71 curated associations.


ClosedChargeEngineTrace now rechecks terminal native pressure, temperature, mass,
internal energy and composition against its retained history. The existing closed-
charge Nurion case covers state advancement after issuance; 295 cases remain.


`AdsorptionProductMassFlow.require_current()` now rechecks its source delivery and
sealed mass/rate projection before downstream reuse. The existing deferred storage
product-delivery case covers source mutation and projection-ledger alteration; total
remains 295. No execution or Nurion activity occurred.


The TU Darmstadt hydrogen-engine flame/wall record (DOI 10.48328/tudatalib-2291)
adds an official-host metadata provider and a metadata-only deferred source-ingestion
contract in the shared source-block case module. Eight attachments are locally
acquired to ignored raw storage with publisher MD5 and size checks, while exact
DSpace snapshots are recorded by SHA-256. Raw redistribution remains disabled
pending component-level rights review. The observables are not full-cycle
pressure/work evidence. The profile plan now has 296 cases, 50 profiles, 68 modules
and 71 curated associations. The provider contract is queued for Nurion; no tests,
imports or model calculations were run.


## Latest local continuation — 2026-10-30

The optional-data API now includes `inspect_hdf5_metadata()` to inventory HDF5
structure and attributes without loading measurements or inferring units. Its
synthetic metadata contract is deferred in the source-data-ingestion profile; the
acquired engine flame/wall arrays remain unmapped pending schema review. TUdatalib
metadata requests and redirects are constrained to its official host. The exact
HyRAM registry example shows application-owned native provider binding. Latest
static source totals are 297 planned cases, 50 profiles, 68 modules, 71 associations,
1,265 public definitions in 207 modules, 1,418 relative imports, and 3,311 checked
Markdown paths with no missing destinations. These counts are structural only; no
validation case, model calculation or Nurion job ran. The full coding objective and
receiving-native gaps remain open.

The parallel continuation also added a shared-mesh steady transport projection and
registered its cylindrical analytic check in an existing deferred case. Facility-chain
admission now rejects a gas-only projection callback on the LH2-origin path. Additional
examples demonstrate exact HyRAM provider selection and an explicit Python-native
producer/consumer hydrogen batch receipt. These paths remain unexecuted and retain
all previously documented domain limitations.


Additional parallel additions on this checkpoint expose the finite-hydride and
hydride-compressor types through lazy `h2physics.storage` exports, expose the staged
electrochemical runner from `h2physics.adapters`, reject non-bool dispersion
acceptance flags, add a shared-mesh steady hydrogen-transport projection, and reject
a gas-only HyRAM projection callback for LH2-origin accident chains. Examples cover
an exact provider registry and an evidence-bound completed electrolysis/fuel-cell
batch. All deferred contracts remain unexecuted; these additions do not qualify
material parameters, dispersion physics, facility routing, or production hardware.


Latest admission pass additionally validates CoolProp configuration before optional
provider loading, requires typed evidence for valve effective-area maps, and enforces
real-bool diagnostic/acceptance flags through preferred and direct HyRAM/SLABx-LH2
routes, finite-source projection and flame irradiance. These extend existing deferred
contracts only. The goal remains active; no scientific tests or Nurion jobs were run.

Latest source continuation adds `DiffusionMesh.steady_concentration_profile_mol_m3()`
using the transient mesh's integrated face conductances, returning read-only cell-center
concentrations for constant-D reference/initialization. The existing cylindrical-shell
case now declares immutability and boundary-reversal checks; it remains deferred to
Nurion. This does not add material coefficients or replace transient diffusion. The
implementation objective remains active.

Latest local parallel work adds a steady cell-center concentration profile on the
shared finite-volume mesh, rejects unrepresentable steady resistance, adds a current
source-byte check to metadata-only HDF5 inventories, reports inlet-air-scaled reference
powers for the map-bound Brayton gas path, and admits oxygen-criterion windows only at
exact room output times. Existing deferred contracts were expanded; none was run.
Structural inventory remains 300 deferred cases across 50 profiles and 71 modules,
1,277 public top-level definitions in 208 source modules, 1,442 relative imports, and
3,340 local Markdown paths without missing destinations. No tests, model calculations,
or Nurion jobs ran. The overall objective remains incomplete.

Release hygiene now passes for both the working tree and Git index: the prior generic
Windows destination example was neutralized, and `/tmp/` is ignored. The latest audit
inspected 939 files. This audit does not assess licenses or copyright clearance.
The HDF5 inventory now also rejects direct construction, cloning and changed metadata
content through one-use reader issuance plus a seal; its deferred synthetic source case
covers these boundaries. It still reports schema-neutral metadata only and does not
map published measurements or establish rights to distribute the raw attachments.

Latest code also adds a sealed exact-sample `RadialFailureWindow` view and caller-owned
non-ideal fugacity activities for post-run fuel-cell receipts. The default fuel-cell
route remains ideal pressure ratios, and neither bridge adds a native coupled solve or
new constitutive law. HDF5 metadata receipts now reject direct construction, cloning and
post-inspection edits as well as changed source bytes. Existing deferred contracts
cover these boundaries; none was run.

The gas-state diagnostic result is now sealed to its retained property state and
caller-supplied gas constant. Call `require_current()` before passing it
downstream. The altered-copy contract is deferred and unexecuted; this is not
property validation.

The closed-charge engine API also converts caller-supplied crank-angle schedules
to absolute time using an explicit constant-speed slider-crank and segment clock
origin. `EngineBoundarySchedule` retains source identity, quantity, units and
support, rejecting extrapolation. This remains input coordination only; engine
valve/flow, injection, spark, heat transfer and full-cycle closure remain open
under Request034. Its new Nurion contract is deferred and has not run.

Material diffusion now accepts a linear surface-film boundary on either wall
through `SurfaceFilmCondition` in the shared finite-volume `TransportBoundary`.
The external concentration must already be mapped to the same mobile-entity and
solid basis; the caller supplies a transfer velocity in m/s. The model combines
that film resistance with the mesh half-cell resistance and reports through the
existing signed flux and inventory ledgers. Its synthetic profile contract is
deferred, and surface kinetics/fugacity mapping/coefficients remain caller-owned.

## Current local continuation — 2026-10-30 (eigenstrain result boundary)

`RadialHydrogenEigenstrainResult` now has an issuer boundary and content fingerprint, with `require_current()` guarding its combined von Mises projection. The profile eigenstrain mapper rejects negative and nonfinite concentration inputs. Its deferred synthetic contract declares forgery and invalid-input checks but was not executed. The authorized Hangang CPU probe succeeded (`clogin02`, `r1021a02`); GPU shared connection is unavailable, and no SSH/authentication attempt was made. No scientific cases, tests, or model calculations ran. The coding goal remains active and incomplete.

`radial_hydrogen_eigenstrain_history()` now composes caller-supplied pressure, temperature and concentration snapshots on an explicit increasing clock. It performs independent static solves, returns sealed exact-time samples with no interpolation, and retains the completed prefix and cause on failure. The deferred synthetic contract now records this interface; it remains unexecuted.

## Local continuation — diffusion-to-eigenstrain coupling

`h2physics.adapters.bind_cylindrical_transport_to_eigenstrain()` now joins the issued cylindrical finite-volume transport output to the exact-time quasi-static cylinder stress history. It preserves cell-center mobile concentrations and requires the caller to supply inner/outer solid concentrations at each exact time, plus explicit carrier basis, reference state, linear expansion coefficient, clock-mapping and axial-uniformity evidence. The admitted mesh must match the cylinder surfaces. One-use issuance rejects direct cloning; the binding retains both original histories and checks them for mutation. It does not treat trapped concentration as mobile, infer surface values, or add stress/diffusion feedback. A deferred synthetic bridge case is registered; it was not run.

The eigenstrain history now rejects per-sample changes to carrier, concentration basis, reference concentration, expansion coefficient or reference temperature before solving. Result freshness fingerprints the retained geometry, load, material and temperature content as well as stress arrays and object identity, closing stale-input mutation paths identified during source review. Deferred contracts cover those rejections; they remain unexecuted.

## Current continuation — source-bound AHSS 1300 intake

`h2physics.data.load_ahss1300_permeation()` exposes the separately acquired
CC BY 4.0 grade-1300 workbook after pinned metadata/listing/file-hash checks. It
keeps both worksheet time/value columns, row IDs, material/temperature labels,
the damaged current header and immutable arrays. The unit is unresolved; do not
derive hydrogen flux or a material diffusivity. Contract:
`mendeley-ahss1300-source-bound-observations`, deferred under `fracture-fatigue`.
Latest local static inventory: 301 deferred cases, 50 profiles, 72 case modules,
75 profile/module associations, 1,279 public definitions and 1,449 resolved
relative imports. Hangang CPU command access is open, but the provided wrapper has
no file-transfer operation and the campaign runner requires a committed Git
archive. No calculation was staged or submitted. Preserve the dirty worktree;
resume cluster execution when a pinned source revision and allowed transfer path
are available.

The source-ingest contract now uses a project-owned offline fixture builder rather
than a placeholder. It expects the exact XLSX, Mendeley metadata snapshot and file
listing under `H2_AHSS1300_SOURCE_DIR`; it reconstructs the `Dataset` after all
three SHA-256 checks. The deferred contract rejects missing/replaced attachments,
changed listing/workbook bytes and actual post-load observation mutation. The
mutation contract has not been executed; static metadata and lint do not prove it.

## Hangang CPU continuation — 2026-10-30

The prior transfer blocker is resolved. A source-only snapshot reached
`$HOME/h2physics/source/repository` via base64 chunks passed to the
user's prescribed `run.sh cpu` invocation; its archive SHA-256 was checked before
extraction. The private Python 3.12.9 virtual environment has the core dependencies,
and an editable install plus import smoke check succeeded with BLAS/OpenMP capped
to one thread. No scientific case was run or submitted.

The source has changed since that first transfer, so rebuild the snapshot and
manifest before queueing the first PBS array. `docs/HANGANG_EXECUTION.md` records
the current target, first-wave case plan and thread limits. The planned cases cover
finite carrier conversion, thermal target response, the synthetic BAM text parser,
and synthetic SLABx-LH2 parallel orchestration. That last contract does not establish
thread safety of a real native SLABx-LH2 provider. The HyRAM native receiving plan
keeps the existing mass rejection closed until same-run conserved plane data exist.

## HyRAM transition snapshot audit — 2026-10-30

The host-side plug-to-Gaussian transition ledger and synthetic deferred case are now
registered in both Hangang and Nurion source plans. The API audits provider-issued
same-run radial snapshots for H2 and total-mixture mass, axial momentum (with
pressure correction when available), and excess enthalpy-plus-kinetic energy, with
separate closure and quadrature-error budgets. Missing transfer fields remain
incomplete. This is a snapshot audit only: it does not run or modify native HyRAM,
validate the Gaussian transition model, or establish the accuracy of provider data.
No tests or calculations ran in this documentation integration.

## Hangang source snapshot uploaded — 2026-10-30

The user re-established Hangang access. Through the prescribed `run.sh cpu` wrapper, source revision `f4eb4c4a7e4352777d5fb6fde51e125f6be4bcc0` was uploaded to `$HOME/h2physics/source/repository-live-20261030-e84ba5fa/repository`. Archive SHA-256 `e84ba5fa596231b8582f07b0e4007bce8812fb4496b8a1871bfc5baf149186cd` matched before extraction; all 1,047 source-manifest entries passed remote SHA-256 verification (manifest digest `4214eacbb432581c9eee301af89a743d070771cfbb9bf6e06428038226c445a7`). No scientific test, model calculation, benchmark, install or scheduler job was run or submitted. Coding remains active and incomplete; this transfer does not count as model validation.

## Latest Hangang source snapshot — 2026-10-30

The working tree now also contains `h2physics.data.load_cryo_mof_isotherm()` and
its source-bound immutable table for one licensed cryogenic MOF H2 CSV at a time.
The loader keeps acquisition and publisher hashes attached, preserves row order,
branch direction, raw tokens and missing cells, and does not infer absolute
pressure or uptake convention. Its synthetic case is in Hangang/Nurion plans.
`SurfaceImpactTrace` now has a one-use issuer and recomputed aggregate audit, with
a deferred integrity case in the impact profile. The Hangang plan registers that
profile and currently selects 90 contracts across 17 profiles and 33 modules;
the Nurion metadata inventory is 364 cases, 55 profiles and 102 modules. These
are deferred source-plan counts only. The current source snapshot now includes
these changes and is ready for a later user-authorized cluster run. Its path,
source revision and checksums are recorded in `docs/HANGANG_EXECUTION.md`; no
test or calculation was submitted with this upload.

The cryogenic MOF loader now hashes and parses one bounded byte buffer, preventing a file replacement between checksum verification and parsing from issuing mismatched source lineage. Currentness checks likewise hash the same bytes they reconstruct. Scientific cases remain deferred; this local correction postdates the latest uploaded archive.

The cryogenic MOF table now projects either branch into the existing ObservationTable API, preserving unresolved bases, source hashes, row masks and one file-level experimental group. This connects source ingestion to the existing fitting machinery without inventing pressure semantics or independent replicates. The deferred contract was extended; it remains unexecuted.

Cryogenic MOF currentness checks now reject changed attachment sizes before bounded reads. The source manual includes a receipt-pinned Dataset-to-ObservationTable example with metadata-change rejection and explicit complete-row selection. This documentation example and the deferred contracts have not been executed locally.

Reconciled the mixture catalog/API/backlog against the implemented host adaptive ODE. Earlier text incorrectly described all continuous integration as absent. The distinction is now explicit: bounded host integration exists and is unverified; receiving-native ownership, unrestricted phase appearance, spin/wall coupling and independent qualification remain open. This prevents duplicate host solvers being built from stale backlog rows.

Mixture ODE diagnostics now require event status, event identity and event time to agree; completed/failure summaries cannot carry a terminal-event claim. The existing deferred ODE contracts include contradictory-status rejection. AST/diff checks are structural only; no scientific run was executed.

Mixture ODE failure diagnostics now retain a separately measured attempted_rhs_calls count, including the failing call. SciPy returned counters remain distinct and are not fabricated for an interrupted solve. The API/manual and handoff record this source-only increment; cluster execution remains deferred.

The adaptive mixture runner now rejects initial vapor qualities on/outside terminal quality thresholds before invoking boundary-rate callbacks. Directional solve_ivp events only detect crossings, so previously an already-outside isolated initial state could complete without termination. The isolated deferred contract now covers the rejected initial domain; no scientific run has executed locally.

Adaptive mixture trace admission now explicitly requires zero initial component-transfer and energy-integral ledgers, including every solver ledger channel. The deferred ODE contracts assert the initial stocks and attempted callback counter. This closes the possibility of offsetting initial inlet/outlet summaries satisfying only net balance. No model or scientific test was executed locally.

Finite solid-reaction traces are now issued only after the whole-system mass/element/enthalpy audit and provider binding checks pass. Previously the exception could expose an owner-issued trace created before its final audit failed. Failed audits still retain current inventory, completed steps, supplies and original cause; their trace remains absent. This source change awaits the cluster reaction contracts.

SolidReactionError now exposes computed whole-system elemental, mass and enthalpy residuals directly, retaining None for any stage not reached. This preserves failed-audit evidence while accepted trace issuance remains gated after the final audit. Updated SOLID_REACTION.md to match the actual failure contract. AST/diff checks only; runtime verification is deferred.

The finite solid-feed failure contract now checks that an unreached whole-system audit exposes no final trace or residuals. This complements retained completed-step inventories and original failure cause without confusing missing diagnostics with zero residuals. The existing case ID/profile are retained and no runtime test was executed.

Added MixtureVesselODETrace.boundary_energy_history() as a direct Python integration seam for downstream facility/utility reporting. Named immutable arrays expose accepted-clock original solver-integrated boundary energies and net transfer, preserving export/sign conventions and avoiding duplicate host quadrature. Runtime verification remains deferred.

Adaptive mixture results now expose component_inventory_history(): immutable time-by-species component inventories and cumulative inlet/outlet mole arrays with explicit species order. Existing deferred cases check shape, source equality and immutable arrays alongside the energy-history API. No execution evidence was added.

The existing mixture component-history API now includes immutable kg projections using retained species-ordered template molar masses. This supports facility mass-ledger consumers without a second solver or caller-side species reordering. The deferred contract verifies conversion against the same molar stocks; no model run was executed.

Adaptive mixture flash caching now keys only exact component inventories and U, excluding time/cumulative ledger coordinates that do not affect equilibrium. Cached physical packets are paired with a fresh trial-clock state for every callback. This reduces redundant expensive flashes without interpolation or approximate-state reuse; speed benefit remains unmeasured until Hangang execution.

Mixture ODE diagnostics now count actual equilibrium flash attempts separately from RHS calls, excluding exact-state cache hits and including failed attempts. This provides a measurable cluster cost indicator for the cache optimization. No benchmark or model run was executed locally.

## Rolling Hangang dispatch authorization

The user's latest direction authorizes independent Hangang job dispatch concurrent
with local coding and completed-result analysis. CPU wrapper access succeeded on
clogin03 as r1021a02 and scheduler tools are available. Existing account physics-wave
jobs require source/ownership/result inspection before reuse; unrelated jobs remain
untouched. A dedicated orchestration worker is auditing these paths and preparing
bounded independent batches from the pinned uploaded source. No new job ID is yet
claimed by this local note. Implementation workers continue catalytic finite-flow
and variable-capacity target physics concurrently.
The retry job `1185237` is now submitted for those two cases with Slurm/PBS IDs
mapped and the compute-local temporary path initialized; results are not yet
available. Additional disjoint batches and a fresh source snapshot are being
prepared concurrently.

Local deferred-case updates after the f2086 snapshot: job 1185904 reported no
admitted ground impacts in `parcel-population-finite-impact-sequence`. The fixture
now uses shorter launch elevations and faster downward velocities to create two
separate impact times inside the explicit flight-domain gates; model behavior is
unchanged. The 1185906 sensor rejection path now returns its explicit deferred
outcome. These corrections are not part of that pinned snapshot and require a new
capture/retry. They do not establish physical impact or sensor validation.

Fresh-capture item: launcher jobs 1185918/1185919 failed because the PBS array
omitted the pinned repository `scripts/` directory from `PYTHONPATH`, breaking the
risk helper's sibling import. The generator correction preserves pinned `src/`
first and adds pinned `scripts/` before inherited paths; the existing generator
contract now checks that exact order. This requires a new source snapshot and retry
and does not establish risk-model qualification.

Pending source capture: the porous schedule now validates initial pressure length
against geometry in `PorousReservoir.run()` while retaining strict well-flow/time
sample alignment and positive/bounded pressure checks. The one-cell fixture uses
one radial initial pressure and multiple time-aligned flow samples. Fuel-cell trial
exchange seals now fingerprint the same retained immutable mapping proxies across
construction and recheck, correcting a source-identified identity mismatch from
fresh `dict` copies. Job 1185898 was reported with a currentness issue, but its
latest remote attempt metadata remains running and has no outcome. Include both
changes in a fresh snapshot; no validation claim follows.
## GrInHy2 producer-linkage evidence boundary — 2026-10-31

The existing source reader and producer models were audited statically. GrInHy2
has only time plus vent/HPU/grid/demand boundary flows reported in Nm³/h. It has
no stack current/current density, electrical input, cell/stack temperature, or
declared normalized-volume reference state. HPU channel semantics and measurement
plane are also unestablished. Accordingly, no parameter fit, electrolysis
forcing, molar/mass conversion, or extrapolation was added. The deferred
Hangang case `grinhy2-electrolyzer-coupling-evidence-gap` is registered through
the existing case module and reports this exact evidence boundary. This is a
data-suitability result, not producer-model validation; local tests/calculations
were not run.
## PEACE alkaline existing-stack model bridge — 2026-10-31

Added a source-bound bridge from normalized PEACE current, total-voltage and
one caller-selected temperature channel to the existing `HydrogenStack`
electrolysis evaluation. The profile retains original source-row order/time
tokens, explicitly reports rows omitted for missing channels, and evaluates
observed rows only. It requires caller evidence for sensor-state and electrical
scope mappings and compatible active area/series-cell count; the publisher's
aggregate labels do not resolve cell-versus-stack semantics. The returned trace
retains the exact model owner/source hashes, and its freshness check reproduces
the outputs. No fitting, H2-flow conversion, interpolation, or extrapolation
is performed. Hangang case `peace-alkaline-existing-stack-model-bridge` is
discovered by the existing ingestion plan and uses synthetic files only. It is
pending remote execution and is not physical stack validation.
## Dryad PEM system dataset access gap — 2026-10-31

The current Dryad record describes synchronized experimental signals for a
60 kW PEM system (power commands/measured subsystem power and H2 flow) and a
simulation archive. Dryad documents CC0 1.0 for its datasets. Both API file
downloads and current publisher file-stream links were denied (401/403), so no
attachments, units, file schema or measurement hashes were acquired. The
metadata-only Hangang case `pem-grid-application-data-access-gap` is registered;
it checks the local provenance gap and is not a data/model validation. A
source-bound reader should follow payload access and actual schema/hash review.

## Current4 Hangang outcomes — 2026-10-31

Pinned revision `26845bb9815963b5ce0a337ffcfd9e9bca8afbc7`, source-manifest SHA `3755f73fada945b8e17322fc126ccf3669dc456ac623413ae86c1496ba280a23`.

- 1186427 CSTR failed before integration: Cantera 3.2 made `ThermoPhase.T` read-only; a corrected `native_surface.phase` refresh is local and needs a new pin.
- 1186441 lumped isothermal linepack passed its synthetic ledger case; maximum mass residual `5.662137425588298e-15 kg`. It provides no real-gas, spatial, thermal, or experimental qualification.
- 1186447 segmented pipe network failed only its fixture’s boundary-direction assertion; internal links dominated the injected/withdrawn rates. The synthetic fixture now uses long/narrow links; this correction awaits a new pin.
- 1186448 forced-flow cylinder failed strict geometry audit: volume residual `-9.36232e-13 m³` exceeded solver-scaled allowance `6.58499e-13 m³`. The local adapter now tightens internal solver tolerances to 0.1x while preserving the public geometry gate. Hold retries until that change is pinned; do not weaken the check.
- 1186449 GrInHy2 ingestion failed because the acquired CSV header differed from the reader’s reviewed six-column schema. The local reader now separates exact source CSV headers from normalized API field names. Hold retry until that correction is pinned.
- 1186450 H2SAFE source ingestion passed: 2,542 rows, 24 channels, verified CC BY 4.0 archive SHA `f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e`. It is helium-surrogate ingestion with unresolved units/calibration/room conditions.
- 1186452 power-law surface-film contract passed synthetic interface, carrier rejection, and result-integrity checks; no material qualification.

Current4 manifest SHA `3755f73fada945b8e17322fc126ccf3669dc456ac623413ae86c1496ba280a23`; archive SHA `5f540044df5675557b7027a8ff15d8bda886cdc16e5b611ce87bae0a7942b67b`.
Current4 outcomes are terminal. The latest scheduler snapshot contained unrelated jobs 1186451, 1186438 and 1186395.

1186459 `fuel-cell-reactant-current-limit-boundary` passed its synthetic policy-only contract: oxygen limited current at `1608.0888687218305 A/m²`, and the reserve case returned zero. No Cantera coupling/event/control qualification follows.

1186461 `hydrogen-engine-native-pressure-valve-boundary` failed on the old current4 pin at the same strict volume residual as 1186448. Current4 jobs 1186462 (`cantera-native-fuel-cell-zero-current-boundary`) and 1186463 (`hydrogen-engine-crank-angle-fuel-delivery-native-flow`) were active at the latest queue snapshot, together with unrelated 1186457, 1186438, and 1186395. No current4 retry is scheduled for source cases whose fixes are post-pin.
## Hydrogen-channel finite safety-source bridge — 2026-10-31

Added an adapter from the acquired, source-hash-bound flow time (s) and H2 mass
flow (g/s) channels to `IntervalMassSource`. The caller must provide explicit
quadrature, source location/clock and representative hydrogen state. Mass bins
cover only the measured flow-clock window and retain archive/member hashes.
Sensor time remains unaligned, and filling pressure is not used because its
basis/source-plane interpretation is unresolved. Hangang case
`hydrogen-channel-measured-finite-source-bridge` is registered via the existing
case module and remains deferred. It prepares a safety-source boundary only;
no jet/plume comparison or dispersion validation is claimed.

## Current4 follow-up admissions — 2026-10-31

1186461 `hydrogen-engine-native-pressure-valve-boundary` failed the same old-pin geometry guard as 1186448 (`-9.36232e-13 m³` residual vs `6.58499e-13 m³` allowance, `rtol=1e-9`, `atol=1e-13`). It predates the local 0.1x internal-solver tightening and adds no separate physical finding. Jobs 1186462 and 1186463 later failed on the old current4 pin: 6462 hit the callback-binding guard before its first accepted sample; 6463 repeated the geometry-gate residual. Neither is a physical-model result. The first crank-angle submission request was refused by QOS and created no job; 1186463 is the later accepted ID.
# AB2 shell-temperature hydride boundary bridge — 2026-10-31

For the AB2 tank record (Mendeley DOI `10.17632/8km9z62tct.1`, CC BY 4.0),
`bind_hydride_shell_temperature()` now maps a chosen measured shell TC to the
existing finite-hydride bath boundary only after the caller supplies a mapping
evidence identity. The trace retains source block/hash, sensor and clock; it
rechecks currentness and bounds callback support to the actual measured clock.
Hangang case `ab2-shell-temperature-finite-hydride-boundary` is registered under
`source-data-ingestion` and uses a synthetic workbook, so pinning this case needs
no raw source staging. An actual record replay must stage one of the three
manifest-listed workbooks with its exact recorded SHA-256. No local tests or
calculations were run. Shell-to-bed equivalence, pressure basis, MFC reference
state, mass conversion, fit and physical validation are not established.

## AB2 shell-temperature hydride boundary bridge — 2026-10-31

For Mendeley AB2 tank data (DOI `10.17632/8km9z62tct.1`, CC BY 4.0), `bind_hydride_shell_temperature()` maps one selected shell TC to the existing finite-hydride bath boundary only after the caller supplies an evidence identity for the mapping. The binding retains source block/hash, sensor and clock, rechecks source currentness and bounds callback support to measured time. Hangang case `ab2-shell-temperature-finite-hydride-boundary` is registered under `source-data-ingestion`; it uses a synthetic workbook and requires no raw-source staging. A future experiment replay must stage one manifest-listed workbook with the exact recorded SHA-256. No local tests/calculations were run. Shell-to-bed equivalence, pressure basis, MFC reference state, mass conversion, fit and physical validation are not established.

## Cryogenic MOF source-to-Langmuir handoff — 2026-10-31

`compare_cryo_mof_with_langmuir()` binds the existing absolute-loading Langmuir model to exact 77/87 K MOF source points under three explicit caller-evidence IDs (absolute H2 pressure, absolute H2 uptake on the exact adsorbent-mass basis, and source material mapping). Trace currentness checks the source file and reproduces predictions from the retained model owner. 20 K is not admitted. Hangang case `cryo-mof-source-to-langmuir-diagnostic-bridge` is registered and synthetic, requiring no raw-data restaging; real comparisons require one of the already acquired manifest-listed files staged with its existing SHA-256 and Etalab license receipt. No local tests/calculations were run. No fit or physical validation is claimed.

## X044QK finite-source bridge handoff — 2026-10-31

The new `project_ignited_jet_average_source()` adapter converts a selected pinned matrix row to one `IntervalMassSource` interval using the reported average pressure-derived MFR unchanged and the source H2 release duration. Explicit source gas state, location, clock placement, flow acceptance and clock mapping evidence are mandatory. It does not use peak MFR or convert pressure; constant average rate does not recover the missing transient. Hangang case `x044qk-average-flow-finite-hydrogen-source-bridge` is registered and reads the same staged 14,199-byte CC0 matrix file as the existing ingestion case; use the existing manifest SHA-256 `c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`. State/location are synthetic, so this remains boundary projection only. No local tests/calculations were run.

## BAM thermal observation bridge handoff — 2026-10-31

The new comparator connects one selected FRP plate channel to `ThermalTargetTrace` as a measured response, not a heat-flux boundary. Explicit evidence is required for absolute Celsius, target sensor identity, source/model clock offset, and interpolation method. Hangang case `bam-fire-plate-temperature-thermal-target-observation-bridge` requires the raw BAM archive and its metadata response staged at `/scratch/CLUSTER_USER/h2physics-source-attachments/bam-hydrogen-jet-fire/21026781/` (`H2_Data.zip`, 75,221,648 B, SHA-256 `c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed`; `zenodo-record.json`, SHA-256 `646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0`). The case uses a synthetic thermal target and is not fire/target validation. The existing license scope excludes redistribution of bundled thermographic assets; the comparator reads only a permitted text member. No local tests/calculations were run.

## BAM remote staging verified — 2026-10-31

Per the parent session, Hangang staging through the mandated `run.sh` completed; both received files matched expected byte counts and SHA-256: `H2_Data.zip` 75,221,648 B, `c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed`; `zenodo-record.json` 5,232 B, `646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0`. The registered `bam-fire-plate-temperature-thermal-target-observation-bridge` can now be included in Hangang pin preparation. This verifies staging identity only, not parser execution or thermal/fire model behavior. No tests or calculations were run in this turn.

## BAM measured-origin admission correction — 2026-10-31

The deferred `bam-fire-plate-temperature-thermal-target-observation-bridge` now builds its metadata-backed `Dataset` with exact origin string `"measured"`, the representation required by `bam_jet_fire._check_dataset`. The reader metadata SHA-256 constant was corrected from a transcription typo to `646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0`, matching the captured Zenodo response and manifest. DOI, metadata bytes, CC BY 4.0, open-access status, one-file record and archive hashes remain pinned. The case is registered in `validation/hangang_plan.py` for the current5k/next campaign pin. No tests/calculations were run.

## SOE fault-operation acquisition gap — 2026-10-31

Zenodo 10.5281/zenodo.10648884 declares CC BY 4.0 and lists eleven files totaling 1,092,175,741 B, with zero local payload bytes. Metadata-only Hangang case `soe-fault-operation-data-schema-gap` is registered under `source-data-ingestion`. The MAT field schema, file/fault/repeat mapping, channel units/sign, common clock, flow reference state, sensor locations/calibration and fault event boundaries remain unresolved. See `docs/SOE_FAULT_OPERATION_DATA.md` and the prepared not-sent `requests/soe_fault_operation_data_request.md`. No `HydrogenStack` or process-monitoring mapping, data fit, or validation claim is admitted. No tests/calculations run.

## Brookite photocatalysis AQY evidence gap — 2026-10-31

The 1.95 MB CC BY 4.0 brookite H2-evolution archive is acquired and hash-pinned. Its reader exposes native wavelength/AQY (%) and a reviewed specific-rate mapping, but the missing row-matched spectral photon supply, incident-versus-absorbed electron-equivalent convention, catalyst/geometry/medium/T/P and gas-collection evidence prevent replay through existing `PhotonYield` / `photon_hydrogen_rate`. Metadata-only Hangang case `tio2-brookite-aqy-model-link-evidence-gap` tracks the open boundary; prepared author request `requests/photocatalysis_aqy_condition_mapping.md` is not sent. No physical comparison, fitting or calculation is admitted.

## Hydrogen engine HDF5 model-link gap — 2026-10-31

TUdatalib `10.48328/tudatalib-2291` is open CC BY 4.0 with eight acquired HDF5 bitstreams (8,828,090 B), each hash-pinned in the research manifest. Current HDF5 inventory reads structure/attributes only, not dataset arrays. Missing figure-level quantity, sensor location, crank-angle/spatial reference, sample pairing, cycle/aggregation and uncertainty metadata block source-to-engine/wall model mapping; third-party component rights remain to be reviewed. Hangang case `hydrogen-engine-figure-data-model-link-gap` is metadata-only and registered. The exact prepared not-sent request is `requests/hydrogen_engine_figure_data_mapping.md`; overview is `docs/HYDROGEN_ENGINE_DATA_LINK_GAP.md`. No physical comparisons, tests or calculations were run.

## Dark-fermentation model linkage boundary — 2026-10-31

Mendeley `10.17632/2nwcdx9hst.2` is an acquired 165,296-byte CC BY 4.0 workbook with source hash `f13352e6ae633878aa7cf47a9b7d79f859ad815cda24000c11f04abf32b60729`. The reader retains source rows/units and detects same-export HP/MP inconsistency, but reported BP remains unreferenced gas volume and gas fractions are not qualified mole fractions aligned to it. Clock, process initial state/feed/biomass, reactor volumes and replicate independence remain unresolved. Metadata-only Hangang case `dark-fermentation-h2-process-model-link-gap` is registered. Prepared request `requests/dark_fermentation_gas_basis_request.md` has not been sent. Do not fit or replay `QsdSanAdm1Digester` until its observation basis is supported. No tests/calculations run.

## Nanoporous-carbon H2 chemisorption data boundary — 2026-10-31

Mendeley `10.17632/vyp4wbhxzr.1` is a 26,374-byte CC BY 4.0 collection. The H2 total-chemisorption table is manifest-pinned; its first columns are Material, Pressure (torr), Volume (STP cm3/g) and additional blank-header columns. The record gives H2 973 K, but STP P/T, absolute-pressure convention, absolute/total uptake, material-column mapping and row-specific condition/uncertainty meaning are absent from the admitted schema. No conversion to the `ExtendedLangmuirIsotherm` mol/kg basis is admitted. Hangang case `carbon-h2-chemisorption-model-link-gap` is metadata-only; prepared author request `requests/carbon_h2_chemisorption_basis_request.md` is not sent. No model fit, tests or calculations run.

The materials diffusion catalog now exposes `HydrogenDiffusionShell` for spherical or finite-length cylindrical radial diffusion using the shared `DiffusionDomain` solver. Its deferred Hangang case is `radial-hydrogen-diffusion-shell-api`, registered through the existing `validation.cases.material_transport` module and `material-transport` profile. The API returns whole-shell molar inventories and face transfers and does not include axial/end, stress or heat transport. No test or calculation has been run locally.

Mendeley v2 alkaline bubble observations are recorded as a metadata-only linkage gap. Case `alkaline-bubble-electrolysis-model-link-gap` is included via the source-data-ingestion profile. No payload files or videos were obtained; the CC BY 4.0 declaration is recorded with a file-content review limitation. Schema and condition mapping are missing, and no bubble-dependent HydrogenStack parameter is inferred. See `research/data/alkaline-bubble-observations.toml` and `docs/ALKALINE_BUBBLE_MODEL_LINK_GAP.md`.

The existing five-workbook simulated hydride PCT dataset is documented as a source-regression candidate with unresolved pressure/loading bases and generating-model lineage. Hangang case `hydride-pct-simulated-equilibrium-model-link-gap` is registered through the source-data-ingestion profile. It is metadata-only; no workbook row conversion, fit, model comparison or independent validation claim is made. See `research/data/hydride-pct-simulation.toml` and `docs/HYDRIDE_PCT_MODEL_LINK_GAP.md`.

### Hangang run checkpoint — 2026-10-31

Current5n immutable source and current5o source/manifest hashes, case IDs, and outcomes are recorded in `PROGRESS.md`. Six current5n deferred contracts passed; the BAM count interpretation and diffusion boundary fixture need the corrections documented there and must be retried on a new source revision. Current5o's dark-fermentation metadata-gap case 1186681 passed; cases 1186684/1186685 (acoustic and SOE) are pending. QOS refusals created no job IDs. Source-backed outputs remain software/data contracts only, not physical validation.

Geological adsorption v2 provenance is recorded separately from historical v1. API record-level CC BY 4.0 and README attribution guidance are explicit; third-party embedded data provenance remains an open rights-review boundary, while the included Liberation Serif font has its own OFL-1.1 notice. Publisher/archive and internal checksums match. Existing `geological-adsorption-excess-loader` case is now in Hangang under `adsorption-data`; it exercises source-bound signed-excess rows and bounded interpolation, not a fit or absolute uptake. No bundled code execution, tests, or scientific calculations were performed.
# Bath cryokinetics lane — current5s candidate

Case: `bath-cryo-kinetics-source-schema-gap` (`source-data-ingestion`). Reader:
`src/h2physics/data/bath_cryo_kinetics.py`; provenance:
`research/data/bath-cryo-kinetics.toml`; documentation:
`docs/BATH_CRYO_KINETICS.md`, `docs/DATA_INVENTORY.md`, and
`docs/DATA_QUALIFICATION.md`. Plan registration is present in
`validation/hangang_plan.py`. Raw workbooks are ignored local inputs and should
be acquired/pinned by the cluster-data staging contract using their TOML paths
and SHA-256 values. Only the two xlsx files are selected; Origin/image assets
are excluded. No local tests/calculations were run. The contract checks source
metadata and kinetic-sheet schema only; it does not establish model validity.

# Dryad PEM grid dataset audit — metadata-only case

Case `pem-grid-application-data-access-gap` remains the correct Hangang contract
for DOI `10.5061/dryad.8931zcs64`. The primary record identifies a common time
file and synchronized command/stack/SMPS/chiller/subsystem power and H2-flow
files, but attachment bytes remain inaccessible (README stream HTTP 403; API
previously HTTP 401). No file hashes, experimental units/reference conditions,
sample interval, uncertainty, calibration, or boundary/sensor mapping can be
validated. The simulated grid input's MW basis is not an experimental channel
unit. A future bridge should target a measured system-boundary diagnostic only
after acquiring source files and qualifying their conditions; direct cell-level
HydrogenStack polarization is not currently supported. No local tests or
calculations were run.


### Pin handoff — current5q through current5s

Current5q remote manifest verified. The gas-volume case 1186734 failed during setup on an uninitialized Cantera adapter field, with the fix reserved for current5t. PCT, alkaline-bubble and carbon-H2 cases were QOS denied and remain eligible for retry. 1186719 radial-shell case failed only because its test expected the outer face ledger with the wrong sign; corrected fixture/docs are in current5r. Current5r includes geological plan registration and the radial correction but not the later membrane case module. Current5s includes membrane and the Bath case/plan modules but not all 11 Bath metadata/code/docs paths or the Cantera adapter fix; current5t is the complete follow-up target. No job completion implies scientific validation.
# MHC measured-temperature bridge — current5t candidate

API: `h2physics.adapters.compare_mhc_temperature_to_compressor_bed`; case:
`mhc-compressor-temperature-observation-contract` (`source-data-ingestion`).
Changed files: `src/h2physics/adapters/mhc_compressor_temperature.py`,
`src/h2physics/adapters/__init__.py`, `validation/cases/mhc_compressor_temperature.py`,
`validation/hangang_plan.py`, `docs/HYDRIDE_COMPRESSOR_DATA.md`,
`docs/DATA_QUALIFICATION.md`, `docs/PROGRESS.md`, and `docs/HANDOFF.md`.
The source receipt remains `research/data/hydride-compressor.toml`; archive is
already acquired at 377,874,239 B, SHA-256
`91755fb1e555e0eb32d160ac140a4261b6bb47d24944c7e717b723fe2a641e32` (CC BY 4.0).
`LoggerBlock` issuance now distinguishes workbook snapshots from a reader-issued
verified outer archive; the comparator rejects caller-created fixture blocks.
The Hangang case reads a three-row window and checks that clone/direct-block
forgery paths fail. Actual comparisons still need independent sensor-to-bed and
clock evidence. No local tests/calculations were run.

# USN measured flow source bridge — current5t candidate

API: `h2physics.adapters.project_pressure_peaking_flow_to_finite_source`; case:
`usn-unignited-measured-flow-finite-source-contract` (`source-data-ingestion`).
Changed files: `src/h2physics/adapters/pressure_peaking_source.py`,
`src/h2physics/adapters/__init__.py`, `validation/cases/pressure_peaking_source.py`,
`validation/hangang_plan.py`, `research/data/pressure-unignited.toml`,
`docs/PRESSURE_PEAKING_DATA.md`, `docs/DATA_QUALIFICATION.md`,
`docs/PROGRESS.md`, and `docs/HANDOFF.md`. Source file is the already-acquired
CC BY 4.0 `HTE242USN_00003_READ190621.mat`, 37,466,494 B, SHA-256
`f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0`. The
adapter uses measured kg/s only; negative/missing rows reject, and explicit
quadrature, recorder clock, release plane and H2 state are required. It does
not validate dispersion or pressure peaking. No tests/calculations were run.

# ELVHYS LH2 source/model gap — current5t candidate

Case `elvhys-lh2-rupture-model-link-evidence-gap` (`source-data-ingestion`) is
registered in `validation/hangang_plan.py`. Files changed: `research/data/elvhys-shock-tube.toml`,
`validation/cases/elvhys_model_link_gap.py`, `validation/hangang_plan.py`,
`docs/ELVHYS_MODEL_LINK_GAP.md`, `docs/DATA_QUALIFICATION.md`, `docs/PROGRESS.md`,
`docs/HANDOFF.md`, and prepared request
`requests/elvhys_shock_tube_model_link_evidence.md`. Source rights are CC0-1.0;
receipt states 42/133 files and 534,609,893 B. No numerical source rows are
read. No model comparison is admitted until rupture-clock mapping, pressure
calibration/baseline and station positions, and tube-side gas/liquid state are
evidenced. No local tests/calculations were run.

# USN exact-window-edge check — current next pin

The Hangang plan injects `raw_data_root=/scratch/CLUSTER_USER/h2physics-source-attachments`
only for `usn-unignited-measured-flow-finite-source-contract`. The case reads
`pressure-unignited/1/HTE242USN_00003_READ190621.mat` through
`load_pressure_mat`; staged receipt: 37,466,494 bytes, SHA-256
`f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0`. It finds
actual positive/negative SIGMA row pairs and a valid triplet, then checks
positive-bin issuance, negative-flow rejection and non-row-aligned edge
rejection. Synthetic state/location/evidence placeholders are only API
fixtures; they carry no experiment meaning. The raw root is absent from local
and default plans. Updated case file:
`validation/cases/pressure_peaking_source.py`; supporting notes:
`docs/PRESSURE_PEAKING_DATA.md`, `docs/DATA_QUALIFICATION.md`,
`docs/PROGRESS.md`, and `docs/HANDOFF.md`. 5z predates the staged receipt;
Hangang execution verification is pending for 5aa+. No local tests/calculations
were run.

## USN ignited measured-flow source bridge (current5af candidate)

Case `usn-ignited-measured-flow-finite-source-contract` is registered under
`source-data-ingestion`. The shared decoder `data._mat_export.decode_recorded_mat`
is used by both USN pressure-peaking MAT profiles; ignited records preserve the
SIGMA 7-column and GEN3i 3-column layouts and distinct recorder clocks. Only the
documented SIGMA mass-flow channel is eligible for finite-source projection.
Staging was confirmed through the authorized `run.sh` wrapper at
`/scratch/CLUSTER_USER/h2physics-source-attachments/pressure-ignited/1/HTE341USN0015READ191111.mat`,
40,666,968 bytes, SHA-256
`3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4`.
Hangang plan injects only the shared attachment root for this case. The adapter
requires exact source-row window endpoints, explicit quadrature and caller
release-plane/state evidence, and rejects negative measured flow. GEN3i column 2
remains unresolved and unused. Pressure/ignition comparisons remain an evidence
gap. Implementation files: `src/h2physics/data/_mat_export.py`,
`src/h2physics/data/pressure_ignited.py`,
`src/h2physics/adapters/pressure_ignited_source.py`,
`validation/cases/pressure_ignited_source.py`, and `validation/hangang_plan.py`;
focused source/rights notes are in `docs/IGNITED_PRESSURE_PEAKING_SOURCE.md`.
No local tests/calculations were run.

## PV/PEM dispatch archive model-link evidence gap

The metadata-only case `pv-pem-dispatch-figure-output-model-linkage-gap` is
registered in `validation/hangang_plan.py` under `source-data-ingestion`. The
CC BY 4.0 record's cached archive is pinned at 47,443 bytes and SHA-256
`2fb59438156bd9ccfd8caad6e9540dd68648ffa08816a5c2eedde0043be96b39`. The
archive contains manuscript figure reconstructions and dispatch outputs. These
do not provide the measured irradiance, PV array/module parameters, cell and
stack temperatures, aligned electrical measurements, and response lineage
needed to drive or validate `PVElectrolysis`. No reader or model projection was
added because the source does not establish those inputs. See
`docs/PV_PEM_DISPATCH_DATA.md` and `research/data/pv-pem-dispatch.toml`.


## Current integration lane: adsorption product to linepack

The in-tree adapter `charge_linepack_from_adsorption_product` composes the
accepted finite adsorption-vessel H2 product ledger with the existing
ideal-H2 pipeline linepack inventory. It requires an explicit common time
window, hydrogen-basis evidence, and caller evidence for the injection path's
pressure/thermal interface; the synthetic case is
`adsorption-product-h2-linepack-charge-handoff` in the already-discovered
`finite-adsorption-vessel` case module. No local test was run. Include the new
adapter and case module in the next Hangang source pin; treat any result as a
software contract only, not plant qualification.

## Dryad hypoxia chamber linkage gap

Case `oxygen-hypoxia-chamber-gas-transfer-model-link-gap` is registered under
`source-data-ingestion`. The primary Dryad version 6 page describes a CC0
workbook with ten measurement sheets covering gas/liquid oxygen, inlet oxygen
and flow, temperatures, evaporation and probe delay. The two listed file
downloads remain unacquired (captured HTTP 401; publisher hashes only). Do not
use the README variable inventory as a row schema or infer inlet mass flow.
`CanteraOxygenRoom` is a possible gas-phase O2 comparison target once the exact
workbook, flow units/reference, inlet composition, room/vent boundary, clock and
sensor delay are established; liquid oxygen transfer is outside the API. See
`docs/OXYGEN_HYPOXIA_CHAMBER_DATA_LINK_GAP.md` and
`research/data/oxygen-hypoxia-chamber.toml`. No tests/calculations run.

## USN carpark unignited → FDS linkage gap

Metadata-only case `usn-carpark-unignited-fds-boundary-evidence-gap` is
registered under `source-data-ingestion`. The CC BY 4.0 Figshare v2 manifest
has 22 of 23 files cached; selected `Exp03.mat` is 3,174,901 bytes with SHA-256
`2c74d3575c00fe84757ffcd9580f36f29bd3be43af58f1c9814a1544ac799cb4`. A
metadata-only HDF5 audit found MFM mass flow labeled g/s and 38 sensor records
with time `sec` / concentration `%vol`. It does not establish MFM clock units/
origin or synchronization, sensor coordinate unit/frame, calibration, flow
direction, release plane or expansion temperature. The file-handling guide is
not acquired. See `docs/CARPARK_UNIGNITED_FDS_LINK_GAP.md`. No MAT arrays or
FDS calculations are used.

## Adsorption to finite-hydride inlet adapter

`bind_adsorption_to_finite_hydride` connects the accepted completed adsorption
outlet bins to the finite-hydride gas port. It requires explicit source-clock,
hydraulic and per-bin state-projection evidence, then checks interval mass and
enthalpy accounting. The Hangang case is
`adsorption-to-finite-hydride-gas-port-handoff` under `finite-hydride`; it is
synthetic contract coverage only. Include the source, case module, exports and
plan discovery in the next clean source pin. No local tests were run.

## DataverseNO large-scale explosion case

Case `large-scale-h2-explosion-fds-observation-link-gap` is registered under `source-data-ingestion`. Include its case module, the Hangang plan, source manifest and focused gap document, plus qualification/progress updates, in the next source pin. Dataset-level CC0-1.0 is declared by the v1.0 primary record; no payload was acquired (official file page HTTP 403), no alternate route was tried, and no FDS comparison is claimed.

## Residential hydrogen pilot source gap

Case `residential-h2-pilot-license-and-physical-boundary-gap` is registered under `source-data-ingestion`. Include `validation/cases/residential_h2_pilot_gap.py`, `validation/hangang_plan.py`, `research/data/residential-h2-pilot.toml`, `docs/RESIDENTIAL_H2_PILOT_DATA_GAP.md`, and the qualification/progress updates in the next source pin. The primary Zenodo page's License field is empty, so no payload was acquired despite the documented channels; no reuse rights or model comparison are claimed.

## HFCEV fleet H2 consumption bridge

Case `hfcev-fleet-hydrogen-consumption-model-comparator` is registered under `source-data-ingestion`. Include `src/h2physics/data/hfcev_fleet.py`, `src/h2physics/adapters/hfcev_fleet.py`, both package export files, `validation/cases/hfcev_fleet_data.py`, `validation/hangang_plan.py`, `research/data/hfcev-fleet-telemetry.toml`, `docs/HFCEV_FLEET_TELEMETRY.md`, and inventory/qualification/progress updates in the next pin. Stage the four receipt-pinned files from ignored `data/raw/hfcev-fleet/1/` under the plan's remote root `/scratch/CLUSTER_USER/h2physics-source-attachments/hfcev-fleet/1` using the authorized transfer wrapper; do not stage GPS or larger archives. No local tests/calculations were run. The deferred Hangang case reads the exact publisher sample and checks row-window semantics; it does not execute the model comparator.

## ELVHYS 4.1 vent concentration source

Case `elvhys41-vent-composition-source-ingest` is registered under `source-data-ingestion`. Include `src/h2physics/data/elvhys41.py`, `src/h2physics/adapters/elvhys41_concentration.py`, both package export files, `validation/cases/elvhys41_concentration.py`, `validation/hangang_plan.py`, `research/data/elvhys41-condensed-explosion.toml`, `docs/ELVHYS41_CONDENSED_EXPLOSION.md`, and inventory/qualification/progress updates in the next pin. Stage the three small CC0 inputs from ignored `data/raw/elvhys-condensed-explosion/1/` under `/scratch/CLUSTER_USER/h2physics-source-attachments/elvhys-condensed-explosion/1` through the authorized wrapper. No other campaign files are needed for the ingestion contract. The adapter exposes only pointwise vent composition comparison to the existing oxygen-room snapshots with exact time support and external mapping evidence; no room calculation or explosion validation has been run. No local tests/calculations were run.
## Reliquefier to separator liquid inlet

`bind_reliquefier_product_to_separator` maps an accepted collected liquid
product receipt to the native separator liquid callback. It retains the exact
collection window and product enthalpy and requires caller clock, receiver, and
pressure/thermal transfer-boundary evidence. The case
`reliquefier-product-native-separator-liquid-inlet-handoff` is registered under
`finite-transfer`; its synthetic contract is not equipment validation. A
source pin must include the adapter, export, case module, and current transfer
boundary argument before execution.

## Finite separator to HELPR history

`history_from_finite_separator` is registered as
`finite-separator-vessel-failure-history-handoff` under `finite-transfer`.
Its new adapter and `vessel_failure.py` freshness dispatch preserve the source
separator trace. It requires separate wall-temperature and external-pressure
rows plus shell/geometry/absolute-pressure evidence; fluid temperatures are
never used as wall temperatures. Package export and Hangang discovery are in
the live tree after current5al and require a new source pin. The synthetic
case does not run HELPR failure prediction or qualify a vessel.

## HyRAM radiation to lumped thermal target

`incident_heat_history_from_hyram_radiation` is exported and registered as
`hyram-radiation-lumped-thermal-target-handoff` under `jet-fire-conservation`.
It reuses accepted HyRAM observer irradiance and the existing lumped target
solver, with caller-evidenced target-surface/projection mapping. No radiation
solver or target property inference is added. Include the adapter, case module,
export, and plan discovery in the next clean source pin; no local tests were run.

## ELVHYS 4.3.2 transfer-line temperature observations

Case `elvhys432-pipe-surface-temperature-source-ingest` is registered under
`source-data-ingestion`. The capture must include
`src/h2physics/data/elvhys432.py`,
`src/h2physics/adapters/elvhys432_thermal.py`, both package export files,
`validation/cases/elvhys432_thermal.py`, `validation/hangang_plan.py`,
`research/data/elvhys432-fireline.toml`,
`docs/ELVHYS432_FIRELINE.md`, and inventory/qualification/progress updates.
Stage only the two receipt-pinned files in ignored
`data/raw/elvhys-fireline/1/` to
`/scratch/CLUSTER_USER/h2physics-source-attachments/elvhys-fireline/1` through the
authorized wrapper: README 13,429 B, SHA-256
`88bccf0809fad9850587b02b77a63889e24c3e123016ae8c467085b633625c78`; Test-1
TEMPL 469,188 B, SHA-256
`eefb7372902e364e4815fd3fbdb649be3172617990cd9fda4942f1c79728be71`. No
pressure, thermocouple, or video files are needed by the ingestion case. The
optional SD1-to-radial-surface comparator is exact-time only and requires
caller evidence for position, pipe/domain and clock mapping. No remote staging,
local tests or model calculations have been performed by this lane.

## Current5am source correction

Job 1187110 exited before the case due to missing `in` syntax in
`src/h2physics/adapters/jet_radiation_radial_wall.py`. The live source is now
corrected. The 5am case was not retried; include the adapter correction in the
next 5aq source pin. The failure is not a scientific model result.

The ELVHYS 4.1 source reader now rejects duplicate and non-increasing source
timestamps before any linkage; the focused guide and progress log record this
admission invariant. This was a reader boundary clarification only.

## Compressor to finite-hydride port handoff

`bind_compressor_to_finite_hydride()` is in `src/h2physics/adapters/compressor_finite_hydride_port.py`.
It admits an existing HEOS H2 compressor result and maps its discharge onto one
explicit finite-hydride gas-port interval. Caller evidence supplies clock
alignment, hydraulic transfer, and state mapping; the adapter closes interval
mass/enthalpy, and replays source/provider state mapping on every port callback.
It adds no flow or storage solver. Deferred case:
`hydrogen-compressor-finite-hydride-gas-port-handoff` in
`validation/cases/compressor_finite_hydride_port.py`. Focused contract:
`docs/COMPRESSOR_FINITE_HYDRIDE_PORT.md`. The case is registered but unrun.

## WSKBIJ selected summary bundle and 5aq audit (2026-10-31)

DataverseNO record `10.18710/WSKBIJ` declares CC0 1.0. The local ignored subset
is `data/raw/large-scale-h2-explosion-wskbij/1/`: `00_Readme.txt` (6,753 B,
publisher MD5 `5642ccb734e8449bf52c0be83e4d0f23`, SHA-256
`cb7d4651d700cbd8da67cb69c3cec63ebabc4ffadbf6d5e1a2a38d63b622fb99`) and
`Experimental_results_.xlsx` (21,165 B, publisher MD5
`73ee4f29ca08612f46b7a37980cbe4df`, SHA-256
`5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34`). The
source reader is `h2physics.data.read_wskbij_experiment_summary`; its Hangang
ingestion case is `large-scale-h2-explosion-summary-source-ingest` at remote
root `/scratch/CLUSTER_USER/h2physics-source-attachments/wskbij-explosion/1`.
Remote data-file verification has been requested and its receipt is pending.
The workbook gives test-level pressure summaries, not pressure-time traces. It
does not establish ambient history, sensor coordinates, or full source/obstacle
geometry, so there is no FDS or explosion-pressure comparison.

## Finite-hydride desorption to mechanical compressor

`bind_finite_hydride_to_compressor()` is in
`src/h2physics/adapters/finite_hydride_compressor_inlet.py`. It maps one
owner-issued `FiniteHydrideTrace` withdrawal interval to one existing
`HydrogenRealFluidCompressionRun`, with exact edge-state identity and mass and
enthalpy closure. Source ledger sign is positive into the bed; compressor inlet
flow/energy are positive, so accepted desorption deltas are negated. Caller
clock, process-window, direct-transfer and state-evidence identities are
retained. The compressor input has no timestamps; sequence order does not
establish time. Deferred case:
`finite-hydride-desorption-mechanical-compressor-handoff` in
`validation/cases/finite_hydride_compressor_inlet.py`; details in
`docs/FINITE_HYDRIDE_COMPRESSOR_INLET.md`. No local tests/imports/calculations
were run, and no physical validation is claimed.

The 5aq source pin was independently audited after the jet-radiation syntax fix:
revision `ddaeb32137971c1c07cdd8fa71af03bff5c62c46`, archive 4,208,650 B,
SHA-256 `b7e532ee2dcba77681612ee456d21c53122bd2a88ecb6ab9fe91c8e55b1a18f3`,
manifest SHA-256 `eb313f0258910ab2e1c6e79421185f2b86dc0830111941415f234c0005f1bb11`,
1,241/1,241 entries valid and zero forbidden members. The WSKBIJ change landed
after this capture and must be included in the next source pin. No new scheduler
job was submitted from 5aq because the latest account queue was full.

## Real-fluid compressor to pipeline linepack

`charge_linepack_from_compressor()` is in
`src/h2physics/adapters/compressor_linepack.py` and exported from
`h2physics.adapters`. It uses the existing isothermal linepack `advance()` and
one accepted real-fluid compressor run. It requires H2 basis and mass closure,
final linepack pressure below compressor discharge, caller time/transfer
evidence, a CoolProp state at final linepack pressure and fixed temperature,
and signed conditioning energy equal to the enthalpy change. The linepack has
no energy-storage ledger, so this receipt only accounts for inlet conditioning.
Deferred case: `hydrogen-real-fluid-compressor-linepack-charge-handoff` in
`validation/cases/compressor_linepack.py`. No tests/imports/calculations were
run; no pipeline qualification is claimed.

## Campaign metadata gate before next Hangang submission

The pinned `hfcev_fleet.py` source had a missing `dataclasses.field` import,
which prevented campaign case metadata from being generated. The source is
fixed locally; 5aq was not submitted. Before another job is queued, the exact
next pin must pass Hangang campaign-generator metadata import/preflight. The
preflight is a submission gate, not a physical-model result.

## WSKBIJ and Hydrogen Map data lanes

WSKBIJ selected official source files total 27,918 B (README and Excel summary) and are locally hash-pinned. The source reader/case has no time-history or sensor-coordinate basis, so it claims source/schema ingestion only. Its remote Hangang copy still needs size, publisher MD5, and SHA-256 receipts before case exposure.

Wasserstoffatlas `Bestand.csv` is locally acquired (181,145 B; MD5 `078c7049bbef5967194105c35e2af720`; SHA-256 `050e7b8a5a45d554640c2668ab87b6e9c3d0d4658e7ee4a572d7a0864092e8fe`). The reader exposes 1,049 typed rows, preserving raw quantity tokens, provider lineage, and WKT. The per-file CC BY 4.0 term is used with attribution even though record metadata says CC0. This is inventory screening context, not physical validation. Hangang case `wasserstoffatlas-facility-inventory-source-ingest` is deferred pending remote receipt. See `docs/WASSERSTOFFATLAS_INVENTORY.md` and `research/data/wasserstoffatlas-hydrogen-map.toml`.

Campaign generation also revealed a missing `dataclasses.field` import in `hfcev_fleet.py`; fixed locally. 5aq was not submitted, and the next pin requires metadata preflight before any submission.

## Clashach pore-network source screening

The CC BY 4.0 Clashach record's README was acquired and audited for data shape. Its pore/throat PNM archives are image label stacks, not numeric pore/throat radii, conductance, porosity or flow tables. They lack a time-to-experiment, pressure/flow or saturation mapping needed to bridge the current continuum porous-reservoir model. PNM archives remain unacquired; a metadata-only Hangang case records the precise missing link. See `docs/CLASHACH_H2_PNM_MODEL_LINK_GAP.md`.

## Compressor discharge finite-release boundary

`bind_compressor_discharge_source()` and its package export are registered.
The deferred Hangang case is discoverable as
`compressor-discharge-finite-release-source-handoff` under
`gas-compressible-pipe`. It projects caller-declared bounded H2 flow from an
accepted pure-H2 HEOS compressor discharge to `IntervalMassSource`, preserving
the exact outlet state and closing released mass and enthalpy. Callers own the
release clock mapping, location, origin and flow evidence. No leak law, nozzle,
dispersion or consequence physics is introduced. The case has not been run;
include this source and registration in the next immutable Hangang pin.

## Leaky-coating sorption source

Four CC BY 4.0 Figure 4 traces from the Empa Zenodo record are acquired locally and checked against publisher MD5/local SHA-256 pins. The typed reader retains feed-pressure-change versus UHV-MS channels on their original time axes. No arbitrary UHV-to-solid concentration scaling or absolute pressure reconstruction is performed; no model fitting or comparison is claimed. The Hangang source-ingestion case is registered and awaits remote hash confirmation. See `docs/LEAKY_COATING_HYDRIDE_SORPTION.md`.

Remote receipt update: the four selected Empa source files are staged at `/scratch/CLUSTER_USER/h2physics-source-attachments/leaky-coating-hydride-sorption/1/` and exact size/MD5/SHA-256 checks pass for each. The Hangang ingestion case has its verified raw-data root available; no model comparison is part of that case.

Remote receipt update — source lanes promoted:

- WSKBIJ files are verified at `/scratch/CLUSTER_USER/h2physics-source-attachments/wskbij-explosion/1/`: `00_Readme.txt` 6,753 B (MD5 `5642ccb734e8449bf52c0be83e4d0f23`, SHA-256 `cb7d4651d700cbd8da67cb69c3cec63ebabc4ffadbf6d5e1a2a38d63b622fb99`) and `Experimental_results_.xlsx` 21,165 B (MD5 `73ee4f29ca08612f46b7a37980cbe4df`, SHA-256 `5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34`).
- Wasserstoffatlas `Bestand.csv` is verified at `/scratch/CLUSTER_USER/h2physics-source-attachments/wasserstoffatlas/1/Bestand.csv`: 181,145 B (MD5 `078c7049bbef5967194105c35e2af720`, SHA-256 `050e7b8a5a45d554640c2668ab87b6e9c3d0d4658e7ee4a572d7a0864092e8fe`).

These receipts supersede earlier pending-transfer statements in this handoff. Both Hangang source-ingestion roots now have publisher-matching raw files.

## Linepack withdrawal to compressor inlet boundary

`bind_linepack_compressor_inlet()` maps an accepted `LinepackSourceHandoff`
to existing `HydrogenRealFluidCompressionInputs`. Source interval edges and
integrated outlet mass determine the compressor inlet flow; the representative
H2 pressure and temperature are preserved and replayed through HEOS. The caller
supplies transfer, clock, state, efficiency, domain, and signed enthalpy
conditioning evidence. This returns inputs only; it adds no pressure-loss or
heat-transfer solver and does not execute compression. Deferred Hangang case
`hydrogen-linepack-compressor-inlet-handoff` is registered under
`gas-compressible-pipe`, unrun. Include the adapter, case, plan registration,
exports, and focused documentation in the next immutable pin.

## Hangang 5av prepared case

Pin `7e0e369ae2cda55bb2dec0f3ec8faf0ddc3115b3` passed remote archive and manifest verification: archive SHA-256 `17edb714c13a1f6e0faba9e6509f241ce3e8f698a5ebc46b9ed752e8bbe3d26f`, manifest SHA-256 `75c68b71fdad3136cba463397f0f8a04b7bcc1988b6d7a6d7baf8c7a0a3a6182`, 1,267 entries OK, forbidden scan zero. The source-ingestion script for `pd-leaky-coating-sorption-source-ingest` is generated and awaits a QOS slot; no qsub was submitted. Its external script path is `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5av-leaky-17edb714.pbs` and plan SHA is `dfff30d6696ff80ce2de7fe771b4d612c8d98aa3ffa6c0654686e232b0295be1`.

5av dispatch update: Hangang accepted `pd-leaky-coating-sorption-source-ingest` as job `1187298`, with stdout/stderr under `/scratch/CLUSTER_USER/h2physics-jobs/results/5av-leaky-17edb714/logs/`. The job has not yet been analyzed.

5av result `1187298`: `pd-leaky-coating-sorption-source-ingest` entered its deferred reader and failed on source token `--` (ValueError while converting the first-column time at `src/h2physics/data/leaky_coating_sorption.py:91`). This is an ingestion parser failure; no model fit or scientific comparison ran. Keep the receipt external and retry only from a new pin after the reader correction.

## Finite-hydride to fuel-cell H2 feed

The new `bind_finite_hydride_fuel_cell_feed()` adapter connects one accepted
finite-hydride outward gas interval to the existing finite fuel-cell input
packet. Exact step clock/edges are required; positive feed mass and enthalpy
are the signed negative bed-port deltas. All hydride state samples remain in
the source trace, and the caller supplies the single receiving feed state and
signed energy-reference conditioning ledger. The adapter only returns a
`ThermochemicalFeed` plus amended `FuelCellStep`; it executes no fuel-cell or
conditioning solver. Deferred case `finite-hydride-fuel-cell-hydrogen-feed-handoff`
is registered under `finite-hydride`, not run. Include it in the next pin.
### 5ay candidate: cryogenic observation ingestion and leaky-coating parser repair

Cryogenic LH2 source reader, manifest, focused guide, public data exports/catalog seed, inventory qualification, and deferred case `cryo-neutron-lh2-phase-change-source-ingestion` are registered. The selected Mendeley version-2 CC BY 4.0 subset is `Jan(H2)/jan_tc1/jan_tc1_run1`; selected total 499,266 B. Member CRC32/SHA-256 checks are encoded in the source-bound loader. It is ready for the next Hangang immutable pin, with no fit/validation claim. The model-use boundary and unresolved phase-rate unit are explicit in `docs/CRYO_NEUTRON_PHASE_CHANGE_DATA.md`.

Leaky-Coating source case job 1187298 failed during ingestion on source token `--`, before fitting or model comparison. The reader correction retains raw source rows/token pairs, supports both source row layouts, and creates numeric samples only from complete finite pairs. Deferred-case assertions cover 59,328 pairs, 1,785 missing-time tokens, 137 missing-value tokens, and 1,922 incomplete pairs. Include both lanes in pin 5ay. No local tests/imports/scientific calculations were run.


The source-only API index was refreshed after the Cryo-Neutron reader and current adapters: 310 Python modules and 1,637 public top-level classes/functions. This was AST-only inventory, not runtime or validation evidence.

## PV electrolysis to linepack bridge

`charge_linepack_from_electrolysis()` transfers a selected amount from an admitted PV H2 batch over a distinct post-production window into `IsothermalLinepackState`. Its source-side mole ledger reconciles initial/post-production stock, withdrawal, loss, delivered/retained batch and post-transfer stock; it does not mutate or EOS-reflash the producer trace. The receipt retains the transfer clock/window and caller-evidenced pressure and temperature bounds. Its signed energy-reference ledger is tied to delivered mass and checks integrated source transfer enthalpy, reference offset, conditioning energy and caller-declared linepack energy change, without a source-path, internal-energy or heat-transfer solver. Deferred Hangang case `pv-electrolysis-isothermal-linepack-charge-handoff` is registered under `pv-electrolysis`, not run. Focused API and scope are in `docs/ELECTROLYSIS_LINEPACK.md`.

## Underground cavern withdrawal to compressor inlet

`bind_underground_compressor_inlet()` projects one accepted dry-H2
`UndergroundWithdrawalProjection` bin into the existing HEOS compressor input
contract. The source-bin edges and integrated mass set the inlet flow; its
representative P/T are replayed by CoolProp. The receipt retains native and
representative-state enthalpies separately, while caller-supplied signed energy
and clock/state/transfer/domain evidence are required. It returns compressor
inputs only; no cavern, wellbore, pressure-loss, conditioning, or compressor
solver is executed. Hangang case `underground-cavern-compressor-inlet-handoff`
is registered under `underground-storage`, unrun. Include this delta in the
next immutable pin.


Latest source-only API index: 312 Python modules and 1,642 public top-level classes/functions after the two new adapter lanes. Generated with AST parsing only; this is inventory evidence, not runtime validation.

### Cryo-neutron source staging receipt (2026-10-31)

The selected Mendeley CC BY 4.0 subset is staged outside the source archive at `/scratch/CLUSTER_USER/h2physics-source-attachments/cryo-neutron-phase-change/2/Jan(H2)/jan_tc1/jan_tc1_run1/`. The approved Hangang wrapper transfer assembled 27/27 chunks and verified each file's size, SHA-256, and MD5 before promotion:

- `jan_tc1_run1_exp_daq.csv`: 302,376 B; SHA-256 `0589fedf062cf036993fd48ffbed81c8b4a1ee502cd19b6a23935839aab37851`; MD5 `370f599cdebe441ebfbd6057ec15ca13`.
- `jan_tc1_run1_exp_img.csv`: 195,985 B; SHA-256 `abfbb4fc35f7008ca4224daed6e27ae5cb182901140f93aab4100ae5162768e0`; MD5 `d1bc2f654c814cf16b808855f80e5485`.
- `jan_tc1_run1_exp_img_rate.csv`: 905 B; SHA-256 `dd62eabc62a15c32f3ed0457649240b9f5990e57db1d45e5d829b8f0808aad16`; MD5 `a493c2e4185664773c38118360ca2ea8`.

Case `cryo-neutron-lh2-phase-change-source-ingestion` is registered locally but remains unsubmitted pending a complete immutable pin and available QOS capacity. No fit or validation claim is made.


Latest API inventory after adding typed PV-to-linepack source/energy ledgers: 312 modules and 1,643 public top-level definitions, generated from AST only.

### Linepack to finite fuel-cell feed boundary

Include `linepack_fuel_cell_feed.py`, its deferred case, package/plan registration, and focused/API/catalog/progress docs in the next immutable capture. The adapter preserves exact linepack interval mass and clock and emits an existing finite H2 feed packet without running the cell. Linepack has no native energy integral: caller supplies source interval enthalpy/reference ID, receiver energy-basis ID, reference offset and conditioning energy, closing as `H_source + offset + conditioning - H_feed = 0`. The deferred case is unrun; no linepack energy or fuel-cell solver is added.


Latest source-only API index after the linepack-to-fuel-cell adapter registration: 313 Python modules and 1,645 public top-level definitions, AST-generated only.

## WSKBIJ Test001 trace lane

The selected raw member is Test001.txt, official DataverseNO file ID 268129 / PID doi:10.18710/WSKBIJ/PIQIIP. Publisher MD5 6a2b1e93513c33d9400ba8abf4b9d082, raw size 207,853,888 B and SHA-256 c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703; compressed transfer receipt 66,314,797 B / SHA-256 da3673ff937db2f230e2f2d98638aac6023edda38464b7310a066a3aa4db4d32. Reader h2physics.data.read_wskbij_test001_trace verifies source receipt and streams original rows. Deferred case is large-scale-h2-test001-pressure-trace-source-ingest (source-data-ingestion) at /scratch/CLUSTER_USER/h2physics-source-attachments/wskbij-explosion/1. Confirm remote decompression and raw MD5/SHA receipt before queuing it. The case preserves raw voltage sensors and does not claim a calibrated or model-linked physical boundary. No local tests/imports/calculations were run.
# Grid-power to electrolyzer boundary

`src/h2physics/adapters/grid_electrolysis_dispatch.py` exports
`GridPowerInterval`, `GridElectrolysisStep`, `GridElectrolysisSchedule`, and
`dispatch_grid_power_to_electrolysis`. It translates explicit, contiguous AC
power intervals into the highest feasible sampled current using the admitted
shared `HydrogenStack.evaluate` API, checks fixed auxiliary power and declared
AC/DC efficiency, and emits held `ThermalStackStage` commands for the already
existing thermal solver. It does not run that solver, model bus/rectifier
dynamics, own material inventories, or add a second stack kernel.

Focused API and limits are in `docs/GRID_ELECTROLYSIS_DISPATCH.md`; the model
catalog and Hangang plan are updated. The synthetic case is
`validation/cases/grid_electrolysis_dispatch.py`, case ID
`grid-ac-power-to-electrolysis-stack-dispatch`, profile `grid-electrolysis`.
It is registered but unrun. Local verification is AST parsing only; no import,
scientific test, parameter fit or physical validation was performed. Next:
queue its pinned synthetic contract when Hangang capacity and source snapshot
allow, then compare at finer current-density resolutions and acquire independent
metered AC/auxiliary, stack polarization, temperature and hydrogen-flow evidence.

### WSKBIJ Test001 raw source receipt (2026-10-31)

DataverseNO public file ID `268129` was fetched through the approved Hangang wrapper. The final raw attachment is staged outside Git at `/scratch/CLUSTER_USER/h2physics-source-attachments/wskbij-explosion/1/Test001.txt`: 207,853,888 B, SHA-256 `c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703`, publisher MD5 `6a2b1e93513c33d9400ba8abf4b9d082`. The public API's publisher MD5 and expected SHA/size all match. A locally compressed gzip differed bytewise from the proposed pin, so the verified raw file was staged directly under the manifest's expected basename. The new Test001 reader/case must be included in a later immutable pin; this is source staging only, with no ingestion or model validation claim.

## Native isothermal pipeline pressure-wave level

Files: `src/h2physics/isothermal_pipe_waves.py`, `validation/cases/isothermal_pipe_waves.py`, `docs/ISOTHERMAL_PIPE_WAVES.md`. Public classes and EOS providers are exported from `h2physics`; the shared `IsothermalSinglePhaseEOS` hooks are `density_pt`, `pressure_rho_t`, and `isothermal_sound_speed_rho_t`. The synthetic `gas-compressible-pipe` case `hydrogen-pipeline-isothermal-pressure-wave-dynamics` is in the Hangang plan, unrun. Model scope: 1D isothermal Euler, first-order Rusanov FV, pluggable homogeneous EOS (ideal H2 default; direct HEOS CoolProp single-phase provider), closed ends, constant Darcy drag, CFL <= 0.5, nonpositive density rejected. Friction is applied with the exact local solution of the frozen-density momentum source ODE after each FV flux update. Trace `maximum_cfl` is observed; `cfl_limit` is the configured cap; face mass flow includes pipe cross-sectional area; `eos_closure_id` preserves the property basis identity. Primary equation reference is Gugat, Krug and Martin, DOI 10.1007/s11081-021-09690-4. Static AST review only; no local case/test/calculation was run. Energy, reservoir/leak/network boundaries and measured pipeline qualification remain open.

## Reusable isothermal EOS and pipeline data boundary

`src/h2physics/thermo/isothermal_eos.py` exports `IsothermalSinglePhaseEOS`
and `CoolPropIsothermalEOS`; methods are `density_pt`, `pressure_rho_t`, and
`isothermal_sound_speed_rho_t`. The last uses the direct isothermal derivative
`sqrt(1/(rho*kappa_T))`, not adiabatic sound speed. Plant finite-volume wave
integration consumes the Protocol. Source/license audit and limits are in
`docs/PIPELINE_TRANSIENT_DATA_GAP.md`; no new dataset payload was acquired.
`requests/036_hydrogen_pipeline_transient_data.md` requests a licensed,
synchronized measured H2 pipe pressure/flow package. AST parsing passed for the
provider and thermo exports; the AST-only public API inventory is now 317
modules and 1,657 top-level public definitions. No local import, runtime test
or scientific calculation has run.

`validation/cases/coolprop_isothermal_eos.py` adds the deferred provider-specific
Hangang case `coolprop-isothermal-single-phase-eos` in profile `isothermal-eos`.
It checks HEOS round trips, numerical `c_T^2` consistency and rejection paths.
The case is registered but unrun; it does not represent pipeline or facility
validation.

### New dispersion family: two-vent H2 buoyant layer

The next immutable source capture should include `src/h2physics/buoyant_layer.py`, top-level exports, `validation/cases/two_vent_hydrogen_layer.py`, Hangang discovery, and the focused usage document plus catalog/API/progress entries. Family is `dispersion.buoyant_layer`; public call is `run_two_vent_hydrogen_layer(TwoVentHydrogenLayerConfig(...), hydrogen_mass_flow_kg_s=..., duration_s=..., maximum_step_s=...)`. The model assumes still air, fixed temperature, an ideal H2/air mixture and one-way lower/upper vent flow; it solves vent mass continuity and retains H2 inventory residuals. The deferred synthetic case is unrun. Equations were independently implemented from the cited NIST 2011 two-vent analytical work; no article text/tables are included. No local tests/imports/calculations were run.

## Finite-reservoir pipe wave boundary follow-up (2026-10-31)

Live source adds `FiniteReservoirPressureBoundary` and optional pressure-history
inputs to `IsothermalPipeWaveModel.simulate()`. Exact clock/EOS/temperature
identity, full simulation time support and EOS pressure replay are required.
Subsonic characteristic ghosts must remain within the local density bracket;
supersonic and unsupported states reject. Boundary signed mass flow is retained
at output times, cumulative inward/outward mass is integrated over internal
steps, and the pipe mass residual uses `M - M0 - m_in + m_out`. Deferred case
`hydrogen-pipeline-isothermal-wave-finite-reservoir-boundaries` covers these
contracts and the rejection paths; it is not executed or a facility validation.
No reservoir depletion, valve/orifice law, energy balance or thermal transient
is included. Static AST parsing and AST-only API inventory only; no runtime
imports/tests/calculations were run. Current catalog summary is the 80-family
count at the top of `docs/MODEL_CATALOG.md`; older 79-family counts in this file
are historical snapshots.

## Isothermal EOS artifact handoff

`h2physics.thermo.isothermal_eos_artifact` adds safe, bounded persistence for
immutable EOS tables using numeric arrays and canonical TOML metadata, with
checksums and atomic replacement. The deferred case
`isothermal-eos-table-artifact-roundtrip-integrity` checks reload identity,
corruption rejection and envelope limits; it is storage-integrity evidence,
not EOS/model accuracy qualification. No runtime execution was performed.

### HyRAM ignition-to-risk handoff (2026-10-31)

New files: `src/h2physics/adapters/hyram_ignition_risk.py`,
`validation/cases/hyram_ignition_risk_handoff.py`, and
`docs/HYRAM_IGNITION_RISK_HANDOFF.md`. Public function
`bind_hyram_ignition_to_risk()` maps the absolute per-release immediate/delayed
probabilities plus the no-ignition complement into the existing conditional-risk
engine's branches conditional on one caller-supplied LOC. The exact native
`Frequency` object, table evidence/content SHA, package version, provider module
path/hash and partition identity are retained. Caller supplies branch IDs,
probability-factor IDs, partition evidence and each typed harm binding. A
single-use host token rejects direct binding construction and dataclass-copy
mutation; the lineage digest is recomputed against retained fields. This does
not authenticate the upstream HyRAM result itself and does not load HyRAM or
execute the risk engine. The synthetic Hangang case is registered under
`facility-protection`; it uses authored output values and remains unrun.

The source-only API index was regenerated with the repository AST tool:
323 modules and 1,672 public top-level class/function definitions. No imports,
native runtime, risk calculation or scientific tests ran locally. The optional
HyRAM GPL-3.0-only dependency is not bundled; Apache-2.0 combined redistribution
is not cleared.

### 5aw prior-pin singleton readiness (2026-10-31)

The verified 5aw source pin remains usable for independent cases whose source files and profile are unchanged. For `hydrogen-linepack-compressor-inlet-handoff`, adapter, case, and focused-doc SHA-256 values match between 5aw and 5ay; the 5aw discovered plan includes the case under `gas-compressible-pipe`. This case has no raw-data or optional-provider requirement and has no prior result on 5aw.

Pin: revision `12b3585d56ccf94be3bf04cb17ab40ca6431bc0c`; archive SHA-256 `3e45a37a071a91fa9da1c71b4c68f974b380010c7c2994f86f91aa2c2a8c0d94`; manifest SHA-256 `180e92726483dec8695681f3488cf49576ddbf01e3b8cafeb7c2abb88cef10fe`; 1,267 entries, all checks passed, forbidden count zero. A one-case 30-minute PBS script is prepared at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5aw-linepack-inlet-ready.pbs` (SHA-256 `61ac64a799f5e07b321e3b7934092354e1eef6f1952ef6493e93eb296881417c`) using the existing Hangang Python 3.12 venv. It has not been submitted because the latest qstat showed five active user jobs (1186716, 1186978, 1187147, 1187427, 1187566); no job ID or scientific result exists.

#### 5aw linepack inlet submission attempt (2026-10-31)

The prepared singleton `hydrogen-linepack-compressor-inlet-handoff` was attempted with the authorized `run.sh cpu`/`qsub` wrapper. First submission was refused before admission because the wrapper was invoked from `/home01/r1021a02`; the cli filter requires submission cwd under `/scratch` or `/appsdata`. Retried after creating and changing into `/scratch/CLUSTER_USER/h2physics-jobs/results/5aw-linepack-inlet`; Slurm returned `QOSMaxSubmitJobPerUserLimit` and no job ID. No existing job was touched. Immediate qstat still showed five running jobs: 1186716, 1186978, 1187147, 1187427, and 1187566. Script remains prepared at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5aw-linepack-inlet-ready.pbs` (SHA-256 `61ac64a799f5e07b321e3b7934092354e1eef6f1952ef6493e93eb296881417c`) for retry when QOS admits it.

## Hangang source pin 5az — 2026-10-31

The immutable 5az source pin is revision `45d406843085ba7aebe9ff52cb91f5e0d1d8d695` (tree `c96f0762587497f00f23f0d31f7e32bf3a06a936`). Its deterministic archive is 4,324,966 bytes with SHA-256 `6636abac4c10fb4c00edb217bf87fc299b9ee227e9a79d55942cfab6d9fcc2ac`. The canonical LF sidecar manifest is 135,948 bytes, has 1,316 entries, and SHA-256 `f0e3e31785794c0dd6ff5bc4a0631b1f5a6e8645bab9018914a977eea0687bba`. Archive and manifest are under `/scratch/CLUSTER_USER/h2physics-jobs/live-6636abac4c10fb4c00edb217bf87fc299b9ee227e9a79d55942cfab6d9fcc2ac/`.

Remote audit confirmed 1,316/1,316 manifest entries, matching embedded revision and manifest, 1,342 tar members, and zero unsafe or forbidden members. `LICENSE`, `NOTICE`, and `docs/RIGHTS_AND_PROVENANCE.md` are present; 56 `research/data/*.toml` records declare a `license_id`. Raw attachments remain outside the source archive. The archive was built with normalized tar/gzip metadata and repeated locally with the same SHA-256.

The pinned Hangang metadata preflight passed using the verified `/scratch/CLUSTER_USER/h2physics-jobs/pinned-6636abac4c10/.venv/bin/python` (resolves to Python 3.12), setup SHA-256 `c0921d837af00b481df4915f60e867830cecf8f7aa4cb728f02c585e381abfb5`, and pinned plan SHA-256 `5a999602a728130e88db4468a8a721f4783fce4feafc05815074a16747a0fdd1`. Eight singleton PBS scripts are prepared under `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5az/` for WSKBIJ summary ingestion, WSKBIJ Test001 streaming ingestion, Hydrogen Map ingestion, Leaky-Coating ingestion, isothermal pipe waves, two-vent buoyant layer, linepack-to-fuel-cell handoff, and isothermal EOS table qualification. The source inputs for the four ingestion cases were rechecked by remote size, MD5, and SHA-256. These scripts have not been submitted and have no case outcomes.

The Cryo-neutron raw files were staged and verified externally, but the 5az Cryo case still defaults to a path under the source checkout. It is not eligible from 5az. The live plan now binds the case to the verified external run directory; this follow-up is a new immutable pin (5aa), and the 5az archive remains unchanged.

The latest qstat snapshot had five running user jobs (1186716, 1186978, 1187147, 1187427, 1187716). No 5az job was submitted while QOS was full. Current project tracking estimates overall software progress at roughly 30–40%; the model catalog reports 80 implemented, 19 native-adapter verified, 37 unverified, and 24 planned entries. The public API inventory is 323 modules and 1,672 definitions. These are inventory/status measures, not an overall scientific validation percentage. No local runtime tests or calculations were run for this pin; the preflight was metadata import and script generation only.

## 5az Cryo path follow-up — 2026-10-31

The Cryo files remain externally staged and checksum-verified. The immutable 5az plan still resolved `cryo-neutron-lh2-phase-change-source-ingestion` under the repository's ignored `data/raw` directory, which is absent from worker source archives. The live plan now binds `run_directory` to `/scratch/CLUSTER_USER/h2physics-source-attachments/cryo-neutron-phase-change/2/Jan(H2)/jan_tc1/jan_tc1_run1`. This correction is captured separately as the 5aa follow-up pin; 5az remains unchanged and no Cryo case has been submitted from it. The profile is `source-data-ingestion`; this is a path-binding correction only, not an ingestion result.

## Branched pipe-wave network follow-up

The new network fidelity is in `h2physics.isothermal_pipe_network_waves` and
is publicly exported from `h2physics`. Its deferred Hangang case is
`hydrogen-pipeline-branched-isothermal-wave-network` under
`gas-compressible-pipe`. The implementation uses a shared fixed-temperature
`IsothermalSinglePhaseEOS`, finite-volume pipe edges, closed terminal walls,
and caller-bounded common-pressure junction roots. Junction roots reject
non-monotone/unbracketed residuals and unsupported supersonic states; their
outward Rusanov mass flux is the same flux used in the edge update, closing the
network mass ledger. No runtime tests/imports/calculations were run; Python AST
parsing only. See `docs/BRANCHED_ISOTHERMAL_PIPE_WAVES.md` for provenance and
limits. The catalog remains 80 families because this is another fidelity level
within `equipment.gas_pipe`.

### Network-wave validation suite count update

`validation.cases.isothermal_pipe_network_waves` is one Hangang discovery entry
that expands to five deferred case IDs: base conservation, reversed orientation
and insertion order, unequal branch areas, nonzero friction, and pressure-bound
failure. All five share the `gas-compressible-pipe` profile and remain unrun.
The API and focused limits documents list the same IDs and scope.

## Current continuation checkpoint — 2026-10-31

The immutable 5aa source pin is revision `2cf43439cdb6cf94d406a65f40a17ac944628b26`, archive SHA-256 `db124855e54edf86f095fe61d1e3abca473ead59a94fff741ff6b8b41a360cbb`, and canonical 1,316-entry manifest SHA-256 `a2e44170daf7cdce8618f92ac55b58cc44f9b5950dd545469bc2f1cb21666640`. Its remote audit passed 1,316/1,316 manifest entries, 1,342 tar members, and forbidden count zero. The 5aa metadata preflight passed; the Cryo-neutron singleton script is prepared under `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5aa` with SHA-256 `cc2bfbc9355722873c84a8ce2c76e4ba1a4833170470576065963bf33ace52c4`. It is not submitted.

The 5ab delta adds the publicly exported branched isothermal pipe-wave network, its five separate `gas-compressible-pipe` Hangang cases, and the Cal State LA HRS data-access audit. The API index lists 324 source modules and 1,676 public top-level definitions; the catalog remains 80 families (19 implemented, 37 native-adapter-verified, 24 implemented-unverified, zero planned). 5ab is sealed locally and transferring for remote audit.

The Cal State LA HRS research record is not admitted as reusable raw data: official university repository pages report no associated files, and an article license does not establish rights for absent source files. See `docs/CAL_STATE_LA_HRS_DATA_ACCESS.md` and `research/data/cal-state-la-hrs-operational.toml`. The record corrects the back-to-back article DOI to `10.1016/j.jclepro.2021.129737`; raw file IDs, URLs, hashes, and a raw-data license remain unavailable.

Latest Hangang CPU queue snapshot: five user jobs are running (1186716, 1186978, 1187147, 1187716, 1187777). Do not submit until account capacity opens; keep coding and preparing independent scripts meanwhile. When capacity opens, submit the prepared cases as separate jobs through the existing WSL `run.sh cpu` wrapper, capture each job ID, and do not touch unrelated jobs. Overall completion is still estimated at 30–40%; this is an engineering-status estimate, not validation completion.

## Prescribed-pressure boundaries for branched pipe waves

Post-5ab source adds degree-one `reservoir` terminal nodes to the branched
network model, reusing `FiniteReservoirPressureBoundary` and its clock/EOS/T
and time-support contract. The trace records the caller pressure history,
identity/owner/evidence/clock, and cumulative pipe-side exchange. Global mass
closure includes only pipe mass and those signed boundary exchanges; no source
reservoir inventory or depletion is modeled. Two deferred contracts cover a
valid time-varying history with mass closure and rejection of clock/EOS/T,
time-support, provenance and missing-map mismatches. The seven branched-network
contracts have no Hangang result. All five core 5ab contracts and both
pressure-history boundary contracts have local synthetic software-contract
evidence; the two boundary cases were run against a source overlay, not a
complete 5ac archive.

## Local 5ab synthetic contract evidence — 2026-10-31

The immutable local archive SHA-256 is `5cc94307d25c1702a739577947602b1d0d7b31000a0d28f7a596c8c2e2370a81`. Its WSL ext4 copy matched that hash. On Python 3.12.16, NumPy 2.5.4 and SciPy 1.18.1, all five 5ab branched-network entrypoints returned without assertion or numerical error: base conservation, orientation/insertion-order invariance, unequal branch areas, Darcy friction, and pressure-bracket rejection. This is local synthetic software-contract evidence only; it is neither measured-data validation nor a Hangang result. The two pressure-history terminal cases are post-5ab 5ac work and were not included.

## Local 5ac boundary integration overlay — 2026-10-31

The 5ab WSL ext4 extraction was overlaid with the exact current 5ac solver and boundary-case files. Their hashes matched the working tree: solver `0c7a44ff01ed26cd00c9091e743d9b28b2d95071ffee3aa2706e42a2f5da77b8`; case `6ba8c0328ed4e5c3f5f9c1372b03fd0f51b1af1d87996d7dd174b2616840f269`. All seven branched-network entrypoints completed without assertion or numerical error on Python 3.12.16, NumPy 2.5.4 and SciPy 1.18.1. This is a local synthetic integration overlay, not a complete 5ac archive execution, measured-data validation, facility qualification, or Hangang result.

## Finite inventory reservoir endpoint — post-5ac source lane

Immutable archive 5ac sealed at revision `1d8d1057a866fc267cefbdef3d70e5d0d65973bc`, archive SHA-256 `4f202c820d136ab057bf4c47255db81794972168d826748e08567e20a5e4be22`, manifest SHA-256 `459936b2f26ad10add1cab3214e576dd31b4237d6be416b575e4cd6c986595aa`. All finite-inventory changes below are post-5ac and must be captured in a later immutable archive.

The new network terminal type is `kind="finite_reservoir"`; callers provide one `FiniteIsothermalPipeReservoir` per such node via `simulate(..., finite_reservoirs=...)`. The provider owns an initial mass, fixed volume/T, state owner/evidence, clock, EOS identity, mass floor/ceiling, and origin. The network derives pressure with the shared EOS and updates stock from the exact same signed endpoint Rusanov rate used for the neighboring pipe face. Positive outward flux transfers mass from reservoir to pipe. EOS identity/domain, inventory bounds/depletion, clock/T/node/provenance mismatch, or sonic/supersonic endpoint flow reject the step.

The trace retains finite inventory mass/pressure histories and provider provenance. For this mode `total_mass_kg` is pipe plus finite inventory, and the global residual subtracts only the exchange through separate prescribed-pressure boundaries. Thus the finite endpoint exchange cancels internally; the old `FiniteReservoirPressureBoundary` remains a pressure-history source without reservoir inventory/depletion. New files include `src/h2physics/finite_pipe_reservoir.py`, `validation/cases/finite_isothermal_pipe_reservoir.py`, `validation/cases/finite_pipe_reservoir_network.py`, `docs/FINITE_ISOTHERMAL_PIPE_RESERVOIR.md`, and `examples/isothermal_pipe_network_finite_reservoir.py`; the network solver, top-level exports, Hangang discovery, API/catalog/branched-network docs, progress and public API index were updated. API index: 325 modules / 1,677 public definitions. AST-only parse passed for all changed Python files; no runtime checks/calculations were run by this lane. Four deferred synthetic contracts are registered, but are not evidence until executed. Still required: root local contract run against the exact current source, immutable capture of this post-5ac delta, and Hangang replay. This feature does not solve vessel energy/thermal dynamics, mixing, valve/orifice/regulator flow, two-phase storage, or structural qualification.

## Local Conda finite-reservoir contract run — 2026-10-31

Created the reusable `h2physics-py312` Conda environment from the repository root definition and installed the project editable with the `data` extra. Confirmed `h2physics` imports outside the repository working directory (Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1). In the live post-5ac tree, all four finite-isothermal-reservoir entrypoints returned `accepted=True`, covering inventory-pressure behavior, bounds/identity rejection, network-coupled inventory evolution and combined pipe-plus-source closure. This is local synthetic software-contract evidence; it is not independent physical validation, measured-facility qualification, or a Hangang result. The changes remain a post-5ac delta until the next immutable source pin is captured.
## Local AM316L workbook-ingestion smoke run — 2026-10-31

Using the Conda Python 3.12.14 environment with openpyxl 3.1.5, ran `validate_tensile_workbook` and `validate_hardness_workbook` against the acquired CC BY 4.0 payload. Both returned `accepted=True`; the cases verify publisher MD5 and pinned SHA-256, workbook worksheet inventory, and lossless source-cell snapshots. This is local data-ingestion contract evidence only. No transformed values, specimen pairing, fitted material parameters, or independent model-validation claim are produced. Hangang execution is pending.
## Hangang 5ab network contracts — 2026-10-31

Two singleton cases completed with `status=passed` against revision `01833161eb4fcbb900594b39677df0f2f56010d3`, plan SHA-256 `5fe70c87eaf40ab3af200c5d943ad5a8b6b2f8ee47ef2b2c1101debf94aee30c`, and manifest SHA-256 `3e70d1a3d1510abe0cf5f12a42138e46d2baafa894c79057fddd87e2e1ff1323`: base branched network job `1188066` and pressure-bound rejection job `1188092`. Both wrote `outcome.json` with passed status and retained setup/runtime fingerprints. These are synthetic model-contract computations, not measured-data or facility validation. Reversed orientation, unequal-area, Darcy-friction and Cryo singleton cases remain pending. The CPU account is at its five-job QOS cap; concurrent submissions for three additional cases were refused with `QOSMaxSubmitJobPerUserLimit`, so they will be submitted as capacity opens.
The reversed-orientation/order case also completed with `status=passed` on Hangang CPU as job `1188103`, using the same immutable 5ab revision and plan/manifest hashes above. Unequal-branch-area case job `1188116` has been submitted as the next independent case. Darcy-friction and Cryo cases remain ready; the four unrelated long-running user jobs still occupy the other CPU QOS slots.
## Additional open electrolysis-data intake — 2026-10-31

The official Mendeley Data v2 record for alkaline-electrolysis bubble imagery (DOI `10.17632/r6np4f7gmf.2`) declares CC BY 4.0. Its public file API lists 35 root assets totaling 375,513,822 bytes: one README, 17 videos and 17 PNGs. Only the 1,274-byte README was acquired and its local SHA-256 matches the publisher value `21946b964b3b260361f7bf797583f28a7fc6c1db3c02ddca1f77d9d956fc0c57`. No tabular measurement payload is exposed in the resolved root listing; the remaining 34 media files are not copied into the repository. A direct quantitative reader/model link is deferred until the stated processed-data folders and observable definitions are available. This adds a rights-qualified production-process source candidate, not independent model validation.
Hangang CPU contract results progressed: reversed orientation/order (`1188103`) and unequal branch areas (`1188116`) both wrote passed outcomes against immutable 5ab. Darcy-friction case `1188127` is now submitted as the next slot became available; the remaining Cryo case waits for a later slot. All these cases are synthetic numerical contracts, not experimental validation.
Two more independent Hangang jobs were submitted in parallel as CPU capacity opened: 5ab Cryo ingestion `1188136` and 5ac prescribed-pressure reservoir history/pipe-side ledger `1188135`. The second job uses exact 5ac revision `1d8d1057a866fc267cefbdef3d70e5d0d65973bc`, archive SHA `4f202c820d136ab057bf4c47255db81794972168d826748e08567e20a5e4be22`, and 5ac plan SHA `332117cefde3eb9dca1caa9b7637f76b9d7f6c4b8d10c84916acecd90747da8c`. Outcomes are pending; results will be checked from recorded JSON files.
## Reuse-qualified safety-data shortlist — 2026-10-31

The safety-data audit consolidated rights and access evidence for the already acquired BAM hydrogen jet-fire collection (CC BY 4.0, 75,221,648 bytes; publisher MD5 and local SHA-256 match) and USN open-channel hydrogen-dispersion collection (CC BY 4.0, 23/23 files; about 49.2 MB). Both are source-bound measured evidence candidates; their test configurations and model-domain limitations remain separately documented. A 53 MB NIST helium-dispersion archive was excluded because the archive record provides no file-level license grant. No new safety dataset was downloaded in this pass and no model validation was run; see `docs/OPEN_HYDROGEN_SAFETY_DATA.md`.
## Cryo-neutron clock-contract correction — 2026-10-31

The immutable 5ab Cryo ingestion job `1188136` failed its pre-existing strict-increase assertion. Inspection of the hash-pinned source found 5,391 DAQ rows with four adjacent duplicate timestamp pairs, no decreasing values, and one initial zero. The source reader already preserved original order and values; the case had imposed an unsupported strict-clock condition. Updated the current case to require a nondecreasing source clock, preserve all rows, and pin the four duplicate pairs. The corrected local Conda entrypoint returned `accepted=True` with duplicate count 4. The 5ab failure remains in the historical record; a Hangang rerun is pending in the next source pin. No measurements were deduplicated or resampled.
The 5ac prescribed-pressure reservoir-history contract completed with `status=passed` as Hangang job `1188135` against the verified 5ac source/plan pin. Its separate contract-rejection case is submitted as job `1188159`; outcome pending. This boundary retains caller-supplied pressure only and does not model source inventory depletion.
The 5ac prescribed-pressure reservoir contract-rejection case completed `status=passed` as job `1188159`, including rejection of mismatched boundary/source contracts. A 5ac base network regression case was submitted as `1188163` to check the source revision that also carries the pressure-history feature. The current 5ac boundary feature now has both Hangang contracts passed; full source release/facility qualification remains outside this synthetic suite.
The same Conda environment was expanded to match the repository developer extras (`thermo,data,chemistry,hydraulics,test`) and the import surface was checked from outside the repository. Verified installed versions: CoolProp 8.0.0, Cantera 3.2.0, fluids 1.3.1, openpyxl 3.1.5, h5py 3.16.0, SciPy 1.18.1 and NumPy 2.5.3. The checked-in `environment.yml`, README and Korean user guide now describe this setup.
The 5ac base branched network regression (`1188163`) completed `status=passed`, confirming the prior 5ab network contract still holds in the exact 5ac source archive. There are now 8 passed Hangang hydrogen network cases across 5ab/5ac (five 5ab network cases, two 5ac pressure-history cases, and one 5ac base regression) and one separate 5ab Cryo-ingestion failure explained and corrected for the next pin. The 5ac suite's other repetitive base/darcy/etc. cases are not all rerun; source-specific changes are covered by their dedicated cases.


Follow-up on the alkaline-electrolysis Mendeley dataset located the folder API behavior: the anonymous website folder route returned HTTP 404, and the documented Mendeley public-dataset folder endpoint returned HTTP 401 with OAuth specified. No authentication was attempted. The processed figure folders and quantitative tables therefore remain inaccessible from the anonymous listing; the source manifest and gap note now record the observed statuses. This is an access limitation, not a model-data interpretation.
## Finite pipe-reservoir nozzle sink

Post-5ad implementation adds `FiniteReservoirNozzleCoupling` over the existing nozzle and network reservoir APIs. The accepted left-end nozzle rate is debited within the same substep as the exact pipe Rusanov boundary flux; the final nozzle sample is diagnostic only. The network ledger subtracts cumulative leak-out, and `project_nozzle_source()` requires left-hold mass projection to close against that debit. Deferred contracts cover source/ledger closure and EOS mapping rejection. No tests, calculations, or HyRAM run were performed by this lane. The update does not model reservoir energy depletion, a dynamic valve, time-varying opening, external dispersion, or source reservoir thermodynamics beyond fixed-T mapped state. See `docs/FINITE_PIPE_RESERVOIR_NOZZLE_SINK.md`.

## Caloric pipe-wave model handoff

`CaloricPipeWaveModel` adds an energy-conserving, non-isothermal 1-D compressible
Euler fidelity for gas-pipeline transients. It preserves conservative mass,
momentum and total energy and uses a caller-pluggable single-phase rho-u EOS.
The trace retains geometry, clock, EOS identity, boundary state provenance and
ledger residuals. It is implemented but unverified; its four `gas-compressible-pipe`
Hangang contracts remain deferred. No local scientific tests/calculations were
run. Read `docs/CALORIC_PIPE_WAVES.md` for equations, API and limits.

## Fixed-flow HyRAM receiver contract

`h2physics.adapters.hyram_finite_source_snapshots` exposes an injected
fixed-flow receiver interface over the host's `NozzleSourceProjection`. It
preserves exact left-hold source bins and requires the receiver to report its
admitted source-plane H2 rate. The existing stationary HyRAM route is not
adapted because it calculates its own nozzle rate. Results are independent
quasi-steady snapshots without plume memory. The
`hyram-finite-source-fixed-flow-snapshots` Hangang case is deferred, and
`dispersion.fixed_flow_snapshots` is `implemented_unverified`. No native HyRAM
execution or scientific validation is claimed. The current AST inventory has
331 modules and 1,701 public top-level definitions; see `PROGRESS.md` for the
catalog and HPC transfer checkpoint.

## Caloric branched pipe-network wave model

`h2physics.caloric_pipe_network_waves.CaloricPipeNetworkWaveModel` adds a
distinct non-isothermal graph-level extension using shared single-pipe caloric
Euler fluxes. The junction closure is a zero-volume adiabatic perfect-mixing
plenum at rest, with pressure and temperature solved from mass and energy
fluxes applied to connected pipe ends. It requires caller bounds and rejects
unresolved roots, balance errors or negative entropy production. Optional
caller-evidenced Darcy friction and fixed-wall heat transfer now apply per edge
through the shared single-pipe source contracts and are included in source/energy
ledgers. Fixed-volume finite caloric reservoirs update mass/internal energy from
the same signed endpoint fluxes and contribute their stocks to combined global
balances; the prescribed-state reservoir mode stays separate. Detailed tee
momentum/loss, finite junction storage, gravity, phase change, valves and
composition change remain outside this level. Six Hangang software contracts
are deferred; the model remains `implemented_unverified`. No scientific
run or measurement validation is claimed. See
`docs/CALORIC_PIPE_NETWORK_WAVES.md`.

## Caloric tank nozzle source handoff — 2026-10-31

`CaloricFiniteReservoirNozzleCoupling` now connects one finite caloric network
tank to the existing shared `HomogeneousIsentropicNozzle`. It requires exact
network/tank/nozzle `PropertyBasis`, source clock/location, node and edge
identity, owner, evidence, opening and back pressure. For each internal step,
the nozzle evaluates the currently accepted tank rho-u state; the same result
debits mass and `withdrawal_energy_w` together with the pipe endpoint flux.
Pipe/tank candidates are committed only after validation. The network retains
the accepted internal-clock `SourceHistory`, leak mass/energy histories and
global balance signs. Its left-hold source projection requires explicit
representative-state and projection evidence and is checked against accepted
debit mass. Fixed-state reservoirs and finite tanks without a nozzle retain
their existing behavior. Two provider-backed Hangang cases cover choked and
subcritical thermal blowdown/source projection, plus basis/domain/depletion
rejection. Status: `implemented_unverified`; no model run or local scientific
test was performed for this addition. See
`docs/CALORIC_PIPE_NETWORK_WAVES.md`.

## Current continuation checkpoint — 2026-10-31

Project environment `h2physics-py312` uses Python 3.12.14. Activate it from a
fresh PowerShell session with `conda activate h2physics-py312` after running the
installed Conda shell hook.

The source catalog lists 81 families: 19 implemented, 37 native-adapter-verified,
25 implemented-unverified and zero planned. This classification does not imply
all fidelity levels are implemented or independently validated. The AST-based
public API index contains 335 modules and 1,711 definitions.

Local implementation has added an EOS-backed real-gas isothermal linepack
inventory and deferred Hangang contract, alongside finite caloric reservoir
and shared-nozzle source-history coupling. Both additions are documented in the
package API and catalog; static review is complete. No local scientific tests or
calculations were run for these additions.

Hangang job `1188659` completed with exit code 0 and a `passed` receipt for
`hydrogen-pipeline-network-wave-reservoir-contract-rejections` on immutable
5ac. It is synthetic rejection-contract evidence only. The latest transfer
snapshot reported 1,035/1,171 verified parts for 5ad and 372/1,173 for 5ae;
both remain incomplete. At the last scheduler snapshot, three user jobs were
running; no unique unrun cases remained in older verified 5ab/5ac plans. New-pin
cases await complete 5ad/5ae transfer and manifest verification. See
`PROGRESS.md` for the job receipt path and archive hashes.

The rough whole-program estimate remains 30–40%, pending a full audit across
all requested models, data rights, validation and documentation.

## Prior local lanes and data staging — 2026-10-31 (superseded below)

New API additions after the earlier checkpoint: `CoolPropMixtureIsothermalEOS` + `state_rho_t` support a fixed-composition real-gas linepack; `ProportionalIntegralPressureRegulator` emits the existing valve command intervals; and the HySaM source reader has a deferred schema-only ingestion contract. The data inventory writer now supports the repository's selected-member cryogenic receipt schema. Current public API inventory is 335 modules / 1,711 definitions.

HySaM v1.0 data from Zenodo 20590842 is CC BY 4.0. Three XLSX members (1,022,797 bytes) passed publisher-MD5 and local-SHA checks. Their tags, units, calibration, pressure basis and time origins remain unresolved. All three XLSX files and the exact Zenodo metadata JSON are assembled under `/scratch/CLUSTER_USER/h2physics-source-attachments/hysam-sampling-system/v1.0`; remote bytes match sizes, publisher MD5 and local SHA-256. Temporary chunks were removed. No HPC validation case was submitted from this dataset yet.

The newest Hangang code pins were still transferring at this checkpoint: 5ad 1,045/1,171 and 5ae 382/1,173 per-part SHA matches. Job 1188659 was the latest accepted result at that time and was synthetic rejection-contract evidence only. New code cases awaited a complete source/manifest/plan pin.

## Current local, data and Hangang continuation — 2026-10-31

The current Windows Conda environment `h2physics-py312` was updated from
`environment.yml`; it has Python 3.12, editable `h2physics`, research extras and
the `dev` extra. PowerShell setup now documents both Conda initialization and
updating an existing environment. No scientific tests were run locally.

Spatial catalytic reforming now has a separate source-bound Cantera 3.2 PFR
level using native `FlowReactor` and `ReactorSurface`, with configurable feed,
surface coverage, geometry, axial outputs and tolerance parameters. It is
registered in the Hangang plan and consolidated under `production.reforming`;
the explicit envelope remains adiabatic and frictionless. The new case awaits a
later immutable source pin. The mixture-EOS pipe-wave case is also registered.
AST inventory is 338 modules / 1,724 public definitions; ten recent source and
case files parsed statically. A generic `GenericCascadeRefillSequencer` now
selects one caller-configured pressure bank at a time without owning flow,
valves, temperature, or a standard fueling procedure. Its deferred case is
registered under finite-transfer. The H2-Stations workbook has a typed
source-bound reader and deferred schema case; its 15,024-byte workbook is staged
on Hangang with matching SHA-256
`87378bed700330ddad64c364b542a69ae34e14d71c800b241c9d92cf112ea02a`. A separate rights audit found no directly reusable versioned raw
per-fill fueling traces and recorded the gap, leaving registry/aggregate sources
as non-validating metadata only.

The reporting writer now supports the selected-member Cryo receipt and legacy
acquisition fields; inventory regeneration succeeded. H2-Stations workbook
snapshot is 166×7 and CC BY 4.0, facility inventory only; no per-fill measured
physics data is exposed in that snapshot. HySaM remains schema-only because its
channel units, calibration and timing basis are unresolved.

5ad transfer completed at 1,171/1,171 per-part SHA matches. Remote archive
SHA-256 is `5a7703fd2261a06703460d1ecd82dec070069c0e1c5680f82ec06f0f963c1231`;
the embedded 1,360-entry manifest and forbidden scan passed. On this immutable
pin, independent Hangang jobs were submitted without waiting serially:

- `1188822` Cryo source ingestion: passed; 5,391 DAQ rows and three selected
  CC BY files were receipt checked.
- `1188823` leaky-coating source ingestion: failed because one trace had fewer
  than two complete numeric samples. The local reader now preserves aligned
  zero/one-sample numeric projections with the raw pairs; resubmission waits for
  a newer immutable pin.
- `1188839` WSK Test001 source ingestion: passed; 2,500,001 rows were streamed.
- `1188850` USN unignited source ingestion: passed.
- `1188878` finite-inventory reservoir: passed; maximum combined mass residual
  was 8.9e-15 kg.
- `1188879` finite-inventory rejection contracts: passed.

The separate 5ae archive transfer was last reported at 572/1,173 parts and is
continuing in bounded batches. The next snapshot must include local changes made
after 5ad, including the PFR, cascade sequencer, H2-Stations reader and leaky-reader
fix, before those cases are queued.
Whole-program effort remains a rough 30–40% estimate pending comprehensive scope,
model, data-rights and scientific-validation re-audit.

Latest parallel continuation (2026-10-31): 5ad jobs `1188909` ELVHYS432,
`1188910` ELVHYS41, `1188914` HFCEV source, and `1188918` Wasserstoffatlas
source ingestion passed. Retained row counts were 16,975; 27,058; 8,448; and
1,049. These are ingestion/schema receipts only. Three unrelated jobs were still
running at the latest qstat snapshot. The 5ae immutable archive transfer is at
602/1,173 SHA-matched parts; do not submit cases from it until complete archive,
manifest, plan and setup hashes verify. Local coding continues in independent
lanes; the current Conda environment is `h2physics-py312` and the AST API index
is 341 modules / 1,734 top-level definitions. No local scientific test ran.
Since that snapshot, job `1188935` (X044QK ignition matrix source ingestion)
passed on 5ad with 40 rows after the 14,199-byte attachment matched its recorded
SHA-256. Its pressure basis remains source-stated and unresolved; it does not
validate an ignition model. USN-ignited ingestion was
QOS-denied without a job ID; do not retry until queue capacity changes. The 5ae
transfer has reached 632/1,173 matched parts.
Latest source/coding update: Hangang `1188956` passed WSK Test001 pressure-trace
ingestion with 2,500,001 rows and nine raw channels. `1188955` failed before
parsing because its case still expected an obsolete two-file, 27,918-byte
acquisition; the current manifest has three selected files totaling 207,881,806
bytes. The reader correctly rejected the stale case scope. The local case/docs
now verify current three-file rights/hash metadata while distinguishing the
two-file summary read from the separately ingested trace. Do not retry e8. The 5ae
transfer is now 662/1,173 per-part SHA matches. The AST-only API index has been
refreshed to 341 modules / 1,734 definitions after three model additions and
pressure-aware bubble operating context. No local scientific calculations or
tests were run.
Three new deferred model levels now need the next complete immutable plan/source
pin: `combustion.shaft_transient` (single-spool finite rotor energy response)
and `adapters.alkaline_bubbles` (caller-calibrated alkaline-electrolyzer bubble
loss contributions around the shared stack owner), plus
`caloric_pipe_finite_wall` (single mixed finite wall coupled to caloric gas
waves). Their Hangang cases are registered but have not been submitted. None
has local runtime or
scientific execution evidence.
Latest queue status: USN unignited ingestion `1188850` passed. USN-ignited was
first QOS-denied, then accepted as `1188998`; it failed MAT variable-name profile
preflight despite a matching attachment size/SHA. This is a schema/profile defect,
not a physical-model result. Inspect publisher/source variable metadata and make a
narrow profile fix for the next pin; do not retry e8. The 5ae transfer reached
682/1,173 verified parts; its next 10-part batch is active. The corrected WSK
summary case passed AST parsing and targeted Ruff lint, and also awaits a fresh
pin.

A finite-capacity lumped wall is integrated with the existing caloric Euler pipe
model. AST parsing and targeted Ruff checks pass; the code has a deferred Hangang
case. No runtime/scientific execution was run locally. Continue implementation
concurrently with independent queue and transfer work.

RODARE v1 pressurized-alkaline bubble data is rights-qualified CC BY 4.0, but
only its 1,499-byte condition-index CSV is acquired. The 8,586,456,345-byte
numeric HDF5 archive could not be acquired because byte-range requests were not
honored; it cannot yet support model calibration or validation. This gap and
the exact file receipt are documented.
Latest queue update: `1189012` (WSKBIJ FDS source-observation gap metadata)
failed on the stale 5ad pin because its case expected the old two-file
acquisition scope. The local case is corrected and awaits a fresh pin. It records
unresolved sensor geometry/calibration and does not compare raw traces with a
model. The 5ae transfer is now 732/1,173 SHA-matched parts, with another batch
in flight. Continue independent source jobs and local code in parallel.
The former `1188998` USN-ignited preflight mismatch is corrected locally: the
staged MAT has a legitimate `Tavg` array in addition to documented `SIGMA` and
`GEN3i`; its units/meaning are unresolved. The reader preserves `Tavg` raw and
immutable without projecting it into physics, and now reports extra/unreviewed
variable names. Targeted AST/Ruff pass; no local model test. Do not retry e8;
include this reader/case change in the next fresh pin. The 5ae transfer is at
732/1,173 hashes matched.
WSKBIJ FDS link-gap metadata job `1189012` also failed on e8 for the same stale
two-file/27,918-byte acquisition expectation. Its local gap contract is corrected
to verify the current three-file/207,881,806-byte acquisition and linkage state,
while preserving the unresolved sensor/model-comparison boundary. Targeted
AST/Ruff pass; do not retry e8. The latest 5ae transfer count is 732/1,173,
with another 10-part batch in flight.
Refuelling-process data discovery now tracks ten public/conditional leads and
zero reusable raw per-fill trace files. CARB HyStEP is report-only with plots,
NREL records are aggregate, HSDS is partner-restricted, H2FillS is gated by
registration terms, and H2-Stations has no per-fill sensor history. No chart
data was digitized. See `HYDROGEN_REFUELLING_PROCESS_DATA_GAP.md` and its TOML
manifest before pursuing these candidates.

## Continuation checkpoint — 2026-11-01

The campaign generator now checks plan bytes against the source manifest,
verifies the complete pinned tree/revision, accepts explicit remote POSIX paths,
and builds `PYTHONPATH` with POSIX semantics. Static AST, Ruff and diff checks
pass for that change. The local worktree itself still lacks generated
`SOURCE_MANIFEST.sha256` and `SOURCE_REVISION.txt`, so campaigns must be made
from a complete immutable snapshot.

Three parallel implementation additions are registered locally: exact
Clopper–Pearson bounds for source-bound detector demand windows with caller
declared independence; an explicit sampled concentration-alarm to existing
finite-stroke valve isolation command bridge; and a checksum/schema-bound
reader for the RODARE 60-condition CSV index. The condition CSV is staged on
Hangang with matching 1,499-byte size, publisher MD5 and SHA-256. The numeric
HDF5 archive is still unacquired. All three new contracts require a new source
pin and have not run. The AST-only public API index now lists 357 modules and
1,791 public definitions.

The 5af array job `1190000` completed all three elements, but none passed:
finite-wall job `1190001` exposed duplicate `ValidationOutcome` class identity
between module execution as `__main__` and the imported package module; shaft
job `1190002` used a pinned case missing the required `accepted` field; alkaline
bubble job `1190000` hit an out-of-domain void-fraction assertion that needs
guard-versus-fixture review. The mutable worktree now aliases the cluster runner
module before case imports, records explicit acceptance in the shaft case, and
labels the three alkaline-domain checks separately. The latter needs a fresh
remote replay to resolve; none of these local corrections are in pin 5af.
Preserve the exact old results and replay only after corrections are included in
a newly verified immutable pin. Current overall
programme effort remains a rough 30–40%; the catalog's 56/82 implementation
status is not a measure of qualification.


## 2026-11-01 next execution state

- The 5af three-case software failures remain preserved; the corresponding corrected 5ag contracts passed. Do not count these synthetic contracts as field or independent physical validation.
- PEM current-ripple raw data is locally complete and checksum-bound (90,759,411 bytes; SHA-256 `47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`). Do not ship ignored raw cache into the code archive. The 41-member schema and CC BY 4.0 source record are documented.
- Hangang base tree `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-fc76b2cd` passed full manifest verification. Its source receipt is recorded in HANGANG_EXECUTION.md. Use `scripts/prepare_hangang_delta.py` and `scripts/transfer_apply_hangang_delta.py` for the newer exact-grid/valve plan; both use the existing `run.sh` wrapper and verify a fresh full manifest.
- Before submitting, generate campaigns from that refreshed immutable tree for `preferred-dispersion-receptor-alarm-contract`, `preferred-dispersion-exact-receptor-grid-contract`, and `concentration-alarm-finite-stroke-valve-actuation-trace`. Check QOS immediately before submission and preserve unrelated jobs. Submit the preferred-dispersion and facility-protection profiles independently; do not wait for completions before continuing local coding.
- Request032 requires the external LH2DT native mixture-result owner. Keep this repository's host ODE out of that role; hand off the required native accepted-state and ledger contract in REQUEST032_RECEIVER_BOUNDARY.md.
- Current programme estimate remains 30–40%; catalog implementation status is 56/82 (68%). New exact-grid and finite-stroke contracts remain unexecuted.


## 2026-11-01 current pinned campaign handoff

- Latest verified code tree: /scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-final-3d883a85, full manifest SHA-256 3d883a85642ad0f26bb8cb2d0e39947cb9b9b6ea448cf861e74df9dd1a4bcd4d. It was produced as a 17-file delta over the verified 1,449-file base snapshot.
- The campaign plan contains 316 cases. The generated three-case PBS script and digest are recorded in HANGANG_EXECUTION.md. Submit it from a /scratch working directory; the previous corrected attempt was QOS-rejected and received no job ID.
- At the last immediate queue check, four user jobs were running. Preserve them and recheck QOS before another attempt. Do not treat generated/queued jobs as results.
- The exact-grid sampler and alarm-to-valve trace contract are implemented and registered, but neither has executed on Hangang. No raw PEM or hydride workbook was included in the code delta.
- Request032 remains an external LH2DT native-result ownership issue. Do not substitute this repository's host SciPy mixture solver.
- Keep programme effort at 30–40%; catalog status is 56/82 (68%), which is not scientific validation.

## Parallel continuation after priority 2–7 handoff — 2026-11-01

Three additional synthetic contracts were added and are registered in `validation/hangang_plan.py`:

- `two-vent-hydrogen-layer-concentration-alarm-handoff`
- `pem-ripple-iv-to-hydrogen-stack-diagnostic`
- `preferred-gas-dispersion-hyram-ignition-risk-ledger`

The latter two compose existing model owners with a checksum-qualified public PEM dataset and the preferred HyRAM gas-source boundary, respectively. The PEM raw archive remains outside source snapshots and must be staged to the declared scratch path before its case can run. The earlier verified priority 2–7 tree predates these edits; build and verify a fresh source pin before any new submission. The most recent `qstat` observation showed five existing jobs running. The prior campaign's QOS rejection returned no job ID; leave account jobs untouched and check capacity again before submitting.

A metadata-only registry import after integration returned 319 cases and all six priority 2–7 plus new continuation IDs. This is case discovery evidence only, not execution or model validation. A `PreferredDispersionAlarmHandoff` dataclass name-shadowing import defect was fixed before pinning. Current programme estimate remains 30–40%; catalog status remains 56/82 (68%).

## Current continuation — 2026-11-01

Priority 2–7 adapters and limitations were re-audited; no API defects were found.
The repaired three-case priority rerun still lacks execution evidence. A fresh
Hangang queue query through the required shared `run.sh cpu` path showed five
user jobs running; none was modified and no job was submitted at the observed
QOS cap.

Added `adapters.isothermal_pipe_observations` for explicitly identified
absolute-pressure and signed-flow measurements against the existing
isothermal-pipe-wave trace. Spatial mapping stays within represented support,
times must exactly match solver samples, and uncertainty-scaled residuals are
diagnostics. The synthetic case is registered but unrun; Request036 remains
open because no qualified measured H2 pipeline transient dataset was found.
Official-source searches classified H2-SimNet as simulated, GasLib/TRR154 as
benchmark scenarios, and other leads as incomplete for measurement plane,
rights or channel definitions. Request036 evidence is in the data-gap TOML and
dedicated documentation.

The refuelling-data search rechecked the already acquired CC BY 4.0 HySaM
sampling-system files against all three recorded checksums. They are not
vehicle-fill histories and remain non-validating. The storage-data search
rechecked existing AB2, hydride-compressor, cryo-neutron and PRESLHY file hashes;
no new raw PCT or LH2 storage self-pressurization series met the reuse/schema
gate. Gap inventories are under `research/data/*data-gap.toml` and their
matching `docs/*DATA_GAP.md` files.

The current API index reports 357 modules / 1,791 public top-level definitions.
Metadata-only Hangang plan discovery reports 322 cases across 40 profiles,
including exactly one `hydrogen-pipeline-wave-observation-operator` case.
`audit_public_tree.py` passed for 1,477 GitHub-bound files. A fresh wheel/sdist
build passed `scripts/release_audit.py`; the wheel has 363 package Python
members and the sdist has 1,460 members, with byte-identical package sources,
zero omissions and no detected excluded/private content. Archive hashes are
recorded in `research/release_audit.md`. These are content-hygiene/package
checks, not rights clearance or scientific validation. Overall programme
estimate remains 30–40%; catalog implementation remains 56/82 (68%).
# 2026-11-01 continuation: priorities 2–7 closeout

The priority-2 through priority-7 local interface/API/documentation lane has no newly identified missing local adapter for the ranked items. Outstanding work is distinguished from local implementation: Hangang QOS rejected the corrected case rerun while five existing user jobs were active; Request032 requires a native result from the external LH2DT owner; rights-cleared measured plume and pipeline data are still unavailable. Do not report these as passed validation.

ML-HYDPARK v0.0.5 was acquired with CC BY 4.0 attribution, publisher MD5 and local SHA-256 recorded. The raw CSV and metadata snapshot are ignored locally and were staged into Hangang scratch using the existing wrapper; both remote SHA-256 checks matched. The lossless reader exposes source tokens without asserting units, fitting properties or qualifying validation.

The data-manifest metadata audit was regenerated after eight targeted records were completed. No parse failures remain, but the audit returns incomplete for three authoritative fields intentionally left unresolved: Bath license URI, H2-Stations fixed metadata snapshot hash, and PEACE fixed metadata snapshot hash. Checksum availability and third-party rights review cautions remain visible in `DATA_MANIFEST_AUDIT.md`. The source-only API index is 358 modules / 1,794 public definitions. Current rough overall completion is 30–40%; catalog coverage is 56/82 (68%), which is a separate measure.
# 2026-11-01 continuation: AEM data and metered H2 round-trip API

Added `electrochemical_round_trip` as a composition of the admitted finite electrolyzer/fuel-cell traces, existing H2 inventory handoff and caller-provided integrated electrical meters. It separates meter boundary energy from stack-only ledger values, requires common clock/energy basis/system boundary and complete sequential trace windows, and does not synthesize compression or auxiliary loads. A logical audit added immutable meter-content seals after finding that mutable meter evidence could otherwise change after issuance. Deferred Hangang case: `electrochemical-hydrogen-storage-metered-round-trip-ledger`.

Added a source-bound AEM workbook reader and ingestion-only case for Zenodo DOI 10.5281/zenodo.20068087 v1 (CC BY 4.0). The source workbook and metadata snapshot are staged under the remote Hangang scratch data tree with matching hashes. Case `aem-water-electrolysis-crossover-ingestion` preserves the exact sheet/cell schema and does no physical evaluation. To generate its campaign, set `H2_AEM_ELECTROLYSIS_DATA_ROOT` to `/scratch/CLUSTER_USER/h2physics-jobs/data/aem-water-electrolysis-crossover/20068087` before importing `validation.hangang_plan`; otherwise its metadata defaults to the local ignored data cache path.

Catalog generation states 82 families: 19 implemented, 37 native-adapter-verified, and 26 implemented-unverified. The 56/82 total classifies implementation labels only. Model verification remains deferred. Current queue snapshot before these additions showed three running and four completed pre-existing jobs; no jobs were modified. Before submission, create and verify a fresh worktree snapshot and re-check qstat through the exact existing `run.sh cpu` wrapper. Submit only the selected independent case array; keep existing jobs untouched and do not wait for completion before continuing local work.

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
