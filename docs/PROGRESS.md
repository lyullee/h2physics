# Current release checkpoint — 0.2.0

The eight-work-package implementation was checked as 0.2.0.dev0 and is packaged
as 0.2.0 with unchanged physical equations/defaults. Current service outcomes
and archive/source identities are in [publication status](PUBLICATION_STATUS.md)
and the [0.2.0 receipt](REGISTRY_ARCHIVE_RECEIPT_0_2_0.md). See
[the extension evidence and continuation record](ENHANCEMENTS_20261102.md) for
focused tests, actual native integrations, artifact checks and remaining scientific
limits. Implementation and software verification do not establish experimental
qualification. The records below are historical campaign snapshots, not the
latest source inventory.

# Research handoff — 2026 10 30

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

## 2026-11-02 — input-rejection campaign

The final combined campaign passed 78/78 scoped families, with at least two malformed inputs per family: 161 input-rejection cases plus one manifest check, 162 passed, zero failures/errors/skips in 10.37 s. All 419 pinned Python source/test files were unchanged during execution. This confirms those representative input contracts only; it is not full model, physical-accuracy or external-engine qualification. No production guard was changed; initial expected-message mismatches were fixed in the test code. See [INPUT_CONTRACT_CAMPAIGN.md](INPUT_CONTRACT_CAMPAIGN.md) for exact APIs, scenarios, command and receipts.

## Current programme checkpoint — 2026-11-01

### Continuing CoolProp integration

The existing quasi-steady Darcy/network level now accepts a frozen native
CoolProp mixture without adding a second solver. Rates and inventories are
total mixture masses; changing composition and automatic hydrogen-only
projection remain outside this level. Twelve final focused definition/property
tests passed in 33.93 s with scoped Ruff. The earlier full three-level mixture
network worker is no longer observable by its recorded process/session, and
its final outcome was not collected. Its integration/refinement case remains
unverified; worker disappearance is not a scientific pass or failure.

The table log-linear inverse now uses the same linear-density coordinates as
its forward pressure query. Seven inverse/identity/artifact tests passed.
The corrected 512-point HEOS comparison measured maximum relative pressure,
density and cT errors of 0.0029764607, 0.0029717171 and 0.0000981969. This Python
table was slower than direct HEOS in that workload (speed ratio 0.1778), so it
was not promoted as a faster default. Its sampled cT remains independent of
the interpolated pressure derivative; generalized Darcy/network types reject
it. The optional `sound_speed_mode="pressure_derivative"` now derives cT from
the exact pressure interpolant while preserving sampled cT as the default.
Thirteen inverse/algebra/artifact checks passed; a native CoolProp grid with
16 seeded holdout points stayed within 1% for pressure, density and cT. These
results qualify only that bounded query. No speed gain or Darcy/network
admission is claimed.

The buoyant-layer production density and hydrogen-stock inversion now use native
CoolProp HEOS H2/N2/O2/Ar properties. Four focused native density, composition,
conservation and rejection cases passed; Ruff passed. Oxygen projection now
binds the complete normalized carrier tuple to the native trace, including
mutation rejection when O2 alone stays unchanged. The strengthened projection
integration rerun is pending, so that cross-module change is not yet accepted.
Neither this work nor the table checks changes the 30–40% whole-programme estimate.

The overall effort estimate remains 30–40%; the full original objective remains
incomplete. Current catalog labels are 20 implemented, 37 native-adapter-verified
and 25 implemented-unverified across 82 families. The classified status ratio
is now 57/82 (about 70%); it is separate from whole-programme completion.

The latest fluid-property direction requires native CoolProp or qualified
CoolProp-derived tables, with no handwritten production EOS or silent ideal
fallback. The pipe-wave implicit ideal default has been replaced by the existing
HEOS provider; three native/default and dependency/phase rejection regressions
passed locally in 24.35 s, with scoped Ruff passing. These checks are separate
from the catalog counts. Compressor, adsorption and electrolysis charging now
also use existing native real-gas states, and unified withdrawal delegates to
the existing native source adapter. Native and explicit analytical paths passed
their scoped calculations; see the dedicated linepack documents for energy and
spin limits. This does not complete the programme or all property integration.

The same-level quasi-steady pipe extension now uses native CoolProp cell
pressures and a generalized density-integral Darcy relation. Thirteen
hydraulics tests, the original ideal momentum case and a strong short-pipe
independent reference passed. Native network mass balance, actual step-limit
refinement, event localization, 17 rejection gates and cold imports passed.
The executable network example also passed with a library friction law and
native reference viscosity held constant. This is numerical/native evidence;
measured hydrogen pipeline qualification is still open. Current registered
metadata is 358 Hangang cases/41 profiles and 418 legacy Nurion cases/59
profiles/115 modules; neither number is an executed-case count.

Frozen-mixture actual-use tests additionally exposed and fixed a nonexistent
property-basis attribute in the EOS wrapper. The existing mixture linepack and
pressure-wave cases now pass, along with seven definition/mutation regressions.
The portable identity preserves the real reference, composition and unresolved
spin declaration; it introduces no local thermophysical mixing rule.

Acquired-data metadata review repaired missing HRS and PEACE metadata hashes
without replacing their historical raw-file receipts. The full acquired-data
gate still fails on Bath cryogenic-kinetics `license_url`; the primary record
has no separate license URI. Parse failures are zero, and unresolved rights
scope is retained. Numerical successes do not close that data-publication gate.

The porous-reservoir numerical level moved from implemented-unverified to
implemented after four actual local cases covered analytic balance, prescribed
well pressure, direct HEOS binding and dynamic time/mesh refinement. Geological
or independent experimental qualification is still open. Its explicit scope and
results are in POROUS_RESERVOIR.md. Dated counts below remain historical.

Current restart instructions and remote connection/pin state are at the top of
HANDOFF.md. Local verification continues while the shared CPU session requires
manual user reconnection. Never infer a queued job or a source hash as a pass.

## Campaign portability correction — 2026-11-01

The local Hangang campaign generator now checks the plan bytes against their
source-manifest digest, verifies all files against the pinned source manifest
and revision, and requires explicit absolute POSIX paths for the
remote repository and plan. The scheduler script writer uses POSIX path
composition rather than the workstation's host path rules and rejects
backslashes/control characters in remote path values. This closes a
cross-platform script-generation defect discovered while preparing immutable
Hangang pins. No remote job was submitted for this change; generator use still
requires a complete immutable source snapshot. Targeted AST parsing passed for
the generator; no scientific tests or calculations were run locally.
The 5af three-case array was submitted once from the approved `/scratch` working
area after the first CLI-filter refusal; the corrected attempt was QOS-rejected
without a job ID. No case result exists for that attempt; see
`docs/HANGANG_EXECUTION.md`.
After a later fresh queue snapshot, the same pinned three-case 5af array was
accepted as job `1190000`. Its three array elements completed but all failed
the software contract/reporting path: finite-wall pipe `1190001` did not return
an explicitly accepted result because the runner loaded a duplicate
`ValidationOutcome` class identity; shaft transient `1190002` omitted the
required constructor field in that pin; alkaline bubble losses `1190000` reached
an out-of-domain void-fraction rejection assertion. The finite-wall issue is a
runner defect, the shaft issue is case reporting, and the last needs
guard-versus-fixture review. No physical validation result is inferred; see
`docs/HANGANG_EXECUTION.md`.
Those corrections were included in fresh pin 5ag and all three repaired
contracts passed there; see the immutable outcomes below. The current alkaline
fixture additionally names the exact guard boundary in any later rejection.

## Detector trial confidence intervals — 2026-11-01

Added `interval_for_kofn_trials()` for two-sided Clopper–Pearson intervals on
source-bound simultaneous detector demand-window outcomes. It supports system
fail-to-alarm, common-cause outage, and fail-to-alarm conditional on no
common-cause outage. The caller must provide an identity for evidence that the
windows are independent and identically designed; this software does not verify
that assumption or infer annual frequency, SIL, field representativeness, or
detector qualification. The synthetic Hangang contract is registered and
unexecuted. Targeted AST parsing passed for the changed implementation and case;
no local scientific tests or calculations were run. The facility detector
reliability family remains `implemented_unverified`.

## Alarm-to-valve isolation command bridge — 2026-11-01

Added `schedule_alarm_valve_isolation()` to compose a confirmed concentration
alarm with existing `ValveCommand` intervals. It preserves pre-trip commands,
splits the active interval at alarm time plus caller-declared latency, and
issues a zero-stroke `isolate` command through an explicit horizon. Alarm and
command clocks must match; the command horizon must fit the supplied schedule.
This schedules an override only: it adds no detector credit, actuator dynamics,
flow response, or SIS performance. A synthetic Hangang contract is now in the
plan and is unexecuted. The family remains `implemented_unverified` pending
remote execution and physical validation.

## Alarm-to-valve finite-stroke execution bridge — 2026-11-01

Added `execute_alarm_valve_isolation()` to pass the scheduled override through
the existing `FiniteStrokeValve` model. The immutable result retains the exact
alarm evidence, command schedule, valve and issued trace. It checks exact clock
agreement, exact declared sensor-location applicability, actuator identity and
the caller sample grid against generated command boundaries and the full
horizon. A deferred synthetic Hangang contract covers the execution boundary
and rejection paths; it has not been run. AST parsing and Ruff passed. No local
science run or HPC submission was made. This is explicit schedule execution
only: it adds no detector credit, signal path, SIS claim or new flow model.
The family remains `implemented_unverified`.

## RODARE alkaline-bubble condition-index reader — 2026-11-01

Added a checksum-bound reader for the publicly available RODARE v1
`Summary.csv`. It preserves 60 experiment/electrode IDs with the publisher's
absolute-pressure and signed-current-density condition grid, rejects altered
bytes or schema, and adds an index-only Hangang ingestion contract. The data
contains no voltage or bubble response, so it does not calibrate or validate the
alkaline bubble-loss model; the 8.6 GB HDF5 measurement archive remains
unacquired. Raw data stays outside Git. The reader and contract have no model
execution evidence; the 1,499-byte CSV is staged remotely with size, publisher
MD5 and SHA-256 verified, and static source/schema checks passed. The source
case still awaits an immutable code pin. See
`RODARE_ALKALINE_BUBBLE_INDEX.md` and the RODARE entry in
`DATA_QUALIFICATION.md`.

The generated source-only API index now includes 357 Python modules and 1,791
public top-level definitions; it was regenerated by AST inspection only.

## Parallel continuation — 2026-11-01

Re-audited the 2–7 priority interfaces and found their code consistent with the
documented input, identity and scope boundaries; no source changes were needed.
The five currently running Hangang jobs were left untouched, and no new job was
submitted while the account was at its observed five-job QOS limit. A fresh
source/wheel build overlapped a new Request036 API implementation. Its audit
flagged that the artifact snapshot did not match the source tree at audit time;
that build is rejected as stale evidence. `MANIFEST.in` now explicitly includes
package Python sources. After the code lane settled, a fresh build passed the
distribution-content audit: the wheel contains 363 package Python files and the
sdist contains 1,460 files, with every package source byte-matching the current
tree and zero omitted or changed Python members. Exact archive hashes are in
`research/release_audit.md`. Independently, the GitHub-bound working-tree hygiene
audit passed for 1,477 files; neither audit grants dataset/code rights. The
AST-only API index was regenerated at 357 modules and 1,791 public definitions.
No scientific tests or calculations ran locally.

Request036 now has a host-side measured pressure/mass-flow observation operator
for the existing isothermal pipe-wave trace. It requires explicit units, sensor
locations, source/mapping identities and a common clock; spatial interpolation
is bounded to represented support and measurement times must match solver samples
exactly. The synthetic Hangang contract is registered but unrun. A separate
source search found no suitable licensed experimental H2 pipeline transient
dataset: open H2-SimNet files are simulation outputs; TRR154/GasLib are benchmark
inputs; other leads lack raw measurements or the required channel definitions.
The existing HySaM fuel-sampling records were rehashed but remain unrelated to
vehicle-refuelling validation. These gaps are recorded without promoting
synthetic or adjacent data to physical validation.

The metadata-only acquired-manifest audit currently counts 46 acquired records
and found eight with required source/file receipt fields missing. A scoped
remediation lane is filling fields only where local receipts or authoritative
provider metadata establish the values; the check-acquired gate remains open
until a refreshed audit passes. Hangang plan discovery reports 322 registered
cases across 40 profiles, including exactly one Request036 observation-operator
case; discovery does not execute any entrypoint.

Added a reusable checksum-pinned Hangang data stager for future source-backed
contracts. It transfers bounded chunks in parallel through the existing wrapper,
verifies remote part and final SHA-256 receipts, and accepts only destinations
under the project scratch data root. Targeted Ruff, AST and scoped whitespace
checks passed. It has not yet been used to transfer or execute a new dataset.

## Metadata plan synchronization — 2026-11-01

The prepared three-case Hangang array was retried after a fresh queue snapshot;
the scheduler explicitly refused it with `QOSMaxSubmitJobPerUserLimit` while
five user jobs were active. No existing job was changed. Keep local coding and
the next pinned campaign preparation moving independently; do not count this
submission attempt as execution evidence.

The 5ak immutable source pin is now remotely verified: revision
`8f0a901d9b54e86a8cadac508beb2e9e1422082f`, 1,425 manifest entries, manifest
SHA-256 `294cc21ca4c4e20e5ba376d87887e27c1f4eb3fcbbc8cd0475e0664447651206`,
archive SHA-256 `a5a819f58f1a740e66fccbe429b98b0df7c63e4012b05b9f7608c60f413f84c2`.
The 1,186 transferred parts and all remote manifest checksums matched. Its
inventory includes the surface-film diffusion contract under
`material-transport`. The Langmuir contract ran as job `1189678` on 5ak.
The four-element 5ak campaign for Langmuir, diffusion, k-of-n detector
reliability and surface-film diffusion is prepared at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5ak-storage-transfer-safety.pbs`
(SHA-256 `510e99b80114d33b56fc17e7d14c0e6b05b73fd7dbdabc0e20df0290bcf4776f`).
It is pinned to the verified source, plan, manifest and setup identities. The
array remains unsubmitted; single-case jobs are used as QOS slots become free.

Pin 5al, including the layer-to-O2 projection, is remotely verified: revision
`cb0bde5da039c64e957858cbd539bb936232911e`, 1,428 manifest entries, manifest
SHA-256 `f3f8bb907c3aa5d3bffd044afbdf995d38d84918780c7ecacbc7d54542d4775c`,
archive SHA-256 `54c78141b44dfd420b3882e5ebc0b3160b382fcc447b3e0d3ab154068198d2ef`.
All chunks and remote member hashes matched. The 5-case array and five
one-case alternatives are prepared; the array remains unsubmitted under the
QOS cap. Individual jobs 1189682 (layer O2 projection), 1189687 (surface-film
diffusion) and 1189688 (k-of-n reliability) passed their synthetic contracts.
Jobs 1189694 (Langmuir) and 1189695 (power-law diffusion) were submitted; their
synthetic contracts passed in 1.02 s and 0.95 s respectively. The five cases
in 5al are now all passed on the immutable pin; independent material and
facility validation remain open.

Added `adapters.layer_oxygen_projection.project_layer_oxygen()` as a narrow
composition bridge from the existing two-vent upper-layer H2 trace. It accepts
only a caller-declared fixed dry-air carrier and computes the corresponding
upper-layer O2 mole-fraction samples while retaining the exact source object and
clock. It does not produce a room-average result or an exposure/physiology
prediction. Its synthetic case is registered under existing dispersion and
facility-protection profiles. Its synthetic software contract passed on 5al
(job 1189682, 1.17 s). The module remains implemented_unverified because this
contract is not independent physical or facility validation.

Regenerated the metadata-only validation inventory: 409 deferred case
definitions across 59 profiles and 112 case modules. It imports case catalogs
only, with no entrypoints or Nurion jobs. The pass exposed and fixed an
unmatched closing parenthesis in `validation/cases/vessel_failure.py`, the
missing `material-transport` profile in the Nurion example plan, six missing
family ownership mappings, and a stale permeation mapping. The generated
inventory in `docs/NURION_VALIDATION_PLAN.md` is synchronized. This is plan and
syntax work, not model verification. Programme effort remains roughly 30–40%;
first-level executed coverage does not increase for unrun code.

The subsequent 5am source package is sealed locally at revision
`09f2feefc0f11df0750d554890e5f4139ab8b36e`, with 1,431 manifest entries
(manifest SHA-256 `c9f48817e66f73bfde9e424f40371d70340720d4e9d1a6ec68951787fed0b75e`)
and archive SHA-256 `ad11fa87681c5add1df60202b42d32117c9c5de0de67c4d70129f7a7e023017b`.
The remote tree was reconstructed from verified 5al plus a 699,304-byte,
19-path delta and passed exact path-set plus all 1,431 target-file hashes at
`/scratch/CLUSTER_USER/h2physics-jobs/verified-5am-delta-09f2feef`. Its archived
plan SHA-256 is `fb9f98443251224d3528d0c8a415bc61479239d4b575b3058c4af2483d5dced1`.
The first staged PBS script had stale local plan/path values and was held from
submission; it was removed after a corrected script was generated from the
verified remote tree. The corrected one-case job `1189857` passed in 1.29 s.
It checked six aligned upper-layer samples, caller-owned clock/location mapping
evidence, sensor response, alarm trip and mutation/context rejection. This is a
synthetic software contract, not field detector or facility validation.

The standalone synthetic H2 surface-film/diffusion contract was missing from
Hangang discovery. It is now registered under `material-transport`, with the
Nurion example profile and family ownership mapping aligned. It is included in
verified pins 5ak and 5al and passed as job `1189687`; its synthetic boundary
does not qualify material-specific coefficients or kinetics.

Job `1189567` passed the two-vent buoyant-layer contract on pin 5ai in 10.22 s.
Its H2 mass and vent-flow residuals stayed below `1.58e-16 kg` and
`3.47e-17 kg/s`. This reduced-model contract does not establish experimental
or facility accuracy. An earlier 5ai three-case array for Langmuir equilibrium,
material diffusion and detector reliability was refused by QOS while five jobs
were active. Those and related 5al cases later passed as individual jobs when
QOS slots opened.

## Current correction — 2026-11-01

The first Hangang run of `hydrogen-fixed-state-compartment-network-mixing-
closure` (job `1189474`, pin 5ah) exposed a fixture assertion that incorrectly
required H2 in the adjacent room at the initial time, despite a declared zero
initial fraction. The assertion now checks the final output sample after
transport. It passed the corrected synthetic contract on pin 5ai as job
`1189504`. This does not qualify facility ventilation physics.

## Latest continuation — 2026-11-01

The corrected fixed-state compartment-network contract passed on fresh pin 5ai
(job `1189504`, 1.08 s): H2 and carrier ledger residuals were `7.43e-18` and
`1.18e-13 mol`. The first attempt only failed because a synthetic assertion
included the declared zero-concentration initial sample. Its fixture correction,
pin identity and model limits are in `docs/HANGANG_EXECUTION.md`.

The source-bound PEM ripple reader and its discovered Hangang contract are now
in immutable pin 5ah (`1fe679d69162ef1a551f997e00bf9e5ec8c4418f`): 1,425 source
entries verified, no forbidden files, and no raw ZIP in the pin. Job `1189469`
passed the synthetic reader contract in 1.15 s, preserving source IV/log tokens,
timestamp gaps and publisher fit rows while rejecting altered result/source
bytes. This does not use publisher measurements and does not qualify an
electrochemical model. Full pin and result identities are recorded in
`docs/HANGANG_EXECUTION.md`.

Along with the four 5ag API contracts, the PEM reader, compartment network and
two-vent model, this continuation has seven new deferred software-contract
passes.
Whole-project completion remains roughly
30–40%; scientific model acceptance, measured-data comparison and many native
provider integrations remain outstanding. Speed measure: keep validation as
small pinned independent cases under current QOS, while coding proceeds in
parallel; no raw dataset transfer is needed for this synthetic reader case.

## Latest continuation update — 2026-10-31

The 5ag immutable Hangang pin (`f43e8f636829e1fae2a4aa38f397b6049a88628e`,
1,421 manifest entries) has passed remote archive and full member verification.
All three corrected cases from the 5af harness failure have now passed on the
fresh pin, as has the Brayton terminal-speed-event retry. This adds four
deferred software/API contract passes; none is physical-model qualification.
Per-case results and limitations are recorded in `docs/HANGANG_EXECUTION.md`.

The first generated script used a mistaken setup-script digest and stopped
before entering its case. The actual setup hash was read from the verified pin,
and subsequent jobs passed the source, plan and setup identity checks. A
three-element submission hit the user QOS cap; submitting a one-case job and
then a two-case array opened a parallel route. Existing Hangang jobs were left
untouched. The PEM current-ripple reader is implemented and registered in the
live plan, but was intentionally excluded from 5ag and needs a subsequent pin.

Overall completion remains roughly 30–40% across the whole project: broad model
implementation, source qualification, native-provider integration and
scientific validation remain. Speed action: continue small independent batches
that fit the current QOS headroom while implementation and data ingestion work
advance in parallel.

## Current continuation — 2026-10-31

The project Conda environment `h2physics-py312` runs Python 3.12.16. The
reproducible environment definition is `environment.yml`.
The native Hangang CPU wrapper is reachable (`clogin03`, account `r1021a02`). A
read-only queue snapshot showed three running jobs (1186716, 1187147, 1188529)
and one completed job (1189044); unrelated jobs were left untouched.

New local implementation: fixed-state multi-compartment hydrogen/inert mixing
with caller-prescribed balanced flows, per-species ledgers and accepted-prefix
failure reporting. Its Hangang case is registered but not submitted. Targeted
Ruff passed; no model calculation ran locally. Current AST API inventory is 343
modules / 1,749 public definitions; catalog inventory is 82 families (19
implemented, 37 native-adapter-verified, 26 implemented-unverified). These are
inventory counts, not a completion percentage. Overall project progress remains
a rough 30–40% engineering estimate because data qualification, integration,
rights review and broad cluster evidence remain incomplete.

Additional data acquisition: the PEM current-ripple v2 archive is now present in
ignored raw storage (90,759,411 B; publisher SHA-256 verified) under CC BY 4.0.
The reader streams source IV, continuous logs and reported fits from ZIP members,
keeps exact source-row token iteration and each per-cell clock gap, and leaves
unknown geometry/state/calibration unresolved. Its synthetic ingestion/integrity
case is now registered in the live Hangang plan; it is absent from sealed pin
5ag, so a later source pin is required before submission. The reader and docs
passed Ruff, AST/TOML parsing and static API-index refresh; no model or scientific
case was run. API inventory is now 343 modules / 1,749 public definitions. The
reader paths were excluded from pin 5ag.

The immutable 5af snapshot is locally sealed at revision
`93c86863c13957c73b09cc9f32548aadf709385d`: 1,415 manifest entries,
manifest SHA-256 `7bd7f2100dcbfb8d57d2d1b16fe0c54931cede75526beda3b59e6dee14f7572d`,
archive SHA-256 `b3f56b254eda38046058cbcc506b66f493350bacfe27057e6b2daa356e9adb3e`.
The archive includes Hangang cases for the finite-wall caloric pipe, shaft
transient and alkaline-bubble model. All 1,183/1,183 archive chunks have matching
local/remote SHA-256 values. Remote archive
`/scratch/CLUSTER_USER/h2physics-jobs/incoming-5af-93c86863/source.tar.gz` is
14,185,810 B with SHA-256
`b3f56b254eda38046058cbcc506b66f493350bacfe27057e6b2daa356e9adb3e`. The
extracted pin at `/scratch/CLUSTER_USER/h2physics-jobs/verified-5af-93c86863` has
revision `93c86863c13957c73b09cc9f32548aadf709385d`, manifest SHA-256
`7bd7f2100dcbfb8d57d2d1b16fe0c54931cede75526beda3b59e6dee14f7572d`, and
1,415/1,415 source entries verified. The independent 5ae transfer is parked at
792/1,173 verified chunks. No Nurion work is planned.

A 3-case 5af Hangang array script is prepared at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5af-three-core-validation.pbs`
(SHA-256 `e6bff847067bfc41fbd853f17ce6696beb22d78705af1097e9dffae0cb6ec0e2`)
for `hydrogen-caloric-pipe-finite-wall-energy-closure`,
`hydrogen-brayton-transient-shaft-balance`, and
`alkaline-bubble-electrode-and-electrolyte-losses`. Its first submission was
refused at five active user jobs; retry after two jobs completed was admitted as
array `1189215`. All three elements entered their cases but failed harness
contracts (finite-wall case omitted its outcome return; shaft outcome omitted
`accepted`; bubble fixture clamped invalid values before adapter validation).
The finite-wall return, shaft acceptance record and bubble fixture are now
corrected; the shaft maximum-speed event case was also added. Targeted Ruff/AST
checks pass on these fixes. They are not model-acceptance results; do not retry
immutable 5af. Existing jobs were not touched.

Open-data acquisition also advanced: Mendeley Data v2 PEM current-ripple ZIP is
in ignored `data/raw/` storage, 90,759,411 B, with publisher SHA-256
`47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab` verified
by both the parallel byte-range assembly and the project acquisition receipt.
The archive contains 36 polarization CSVs, four continuous-voltage CSVs and a
derived fitted-parameter table. The README specifies A/V channel units and
current-step meaning; cell-area, calibration and several apparatus conditions
remain unresolved. No raw data is redistributed in the repository, and no
independent model validation has been claimed. A streaming source-bound reader
and deferred Hangang ingestion contract are under implementation.

## Active follow-up — 2026-10-31, current5g

Latest Hangang check: hydrogen-channel source inputs are staged and hash-verified
(metadata 13,106 B; selected ZIP 1,893,720 B). Current5f is sealed at
temporary revision `457e6931cd1b9c2163285587e48f55fdc98ad8f1`, with 1,110 files,
manifest SHA-256 `9026f468431a4f42464e00e16d592d0209a4fca4aed4ad4fd56fff2f1eb4e7dc`,
and source archive SHA-256 `fce4047bbddfb2a05cc1ab8dbbc4fbaf615c2489a3b311184fbb0633b8a2cc6e`.
The remote archive matches; all 1,110 source-manifest entries verify and no
forbidden members are present. Current5f jobs 1186522/1186523 failed before
case entry because scheduler log files changed the immutable source tree. Jobs
1186526/1186530/1186534 entered the catalytic wall heat handoff and exposed a
real adapter defect: a closed reactor path read an undefined `flow_boundary`
instead of its declared element tolerance. That reference is corrected in live
source; rerun this case with current5g. No physical model acceptance has been
established. External scheduler log paths and bytecode suppression are in use.
Current5g is now sealed and remotely verified at revision
`28cb04858fefa7b2447cb5ac86f992402694a992`, 1,123 manifest entries,
manifest SHA-256 `741799a4ee9d49564e601f30c39f43c81a497f0454b4d0957969303fb313724b`,
and archive SHA-256
`fd5106853ea82036d4df04e4df444a20d02d6bb431da396399a02962e411bc55`.
All 1,123 source entries verify remotely. Job 1186567 entered the catalytic
wall heat handoff and found another software invariant failure:
`Native finite isothermal gas/surface domain changed` at the sampled catalytic
state. This is not a physical-model failure. Fix and replay on a newer pin.
Cantera sensor/alarm contract job 1186578 passed on current5g; its synthetic
trace recorded a trip at 0.06 s. This checks API execution only, not detector
performance or physical alarm qualification.
The current5h archive is sealed at
`ad010b936178c63738ee5cf81242a3494fa94e6c`, with 1,127 manifest entries,
manifest SHA-256 `1363f72d451067fedc17bfff343bf44122ba170248d57b39d151f994eb797f34`
and archive SHA-256
`55d69728b9a34e0eab3027a6f558bfa5de2f84bbbe8599d3789b519780f3c4c3`.
Jobs 1186595 (BAM comparator), 1186596 (reaction heat) and 1186597 (reaction
H2 source) entered independently and exposed code issues: the BAM reader's
metadata SHA-256 constant differed from the staged record by a transcription
error; both reaction adapters called nonexistent
`FiniteThermochemicalCycle._enthalpy`. The BAM hash and both energy adapters are
corrected in the live tree. These are software defects, not physical-model
results; replay in the next source pin.
An additional acoustic-data → CoolProp pointwise diagnostic is now implemented.
Its Zenodo ZIP and record metadata are staged at the documented Hangang path.
Downloaded bytes exposed two incorrect transcription pins; code, research
inventory and the data guide now use the verified ZIP hash
`38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553` and
metadata hash `1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`.
current5i through current5m captures predate one or more of these routes; the
next planned current5n will include all of them after plan audit. The
Hangang data/EOS case is still pending, not yet an EOS validation result.
Current5i is sealed remotely at revision
`a6877cf9dd55c8a94e4b4ebf1a79b8eae62417f7`, with 1,132 source entries;
its archive and manifest verify. Catalytic accepted-state-restore replay
1186610 passed: 20 heat-duty intervals reconstructed the native wall ledger,
with total heat into the process `-0.0010711399253343593 J`. The wall remains
an imposed boundary, and this contract does not qualify utility availability or
reactor performance. Current5k will include the source corrections discovered
in current5h plus the acoustic source route; those contracts will be queued
independently.
Current4 job 1186462 failed before integration
in the native fuel-cell callback guard; 1186463 repeated the known open-cylinder
geometry residual from an older pin. Neither is a physical result. The adapter
split callback diagnostics without weakening the guard. Current5e
`825e206735c0e5cb44f726a1d3df76c1d02a2661` is preserved but stale; current5f is
verified and being retried with external log paths. The nozzle/port mass-closure
fix is post-current5f and requires current5g.

The hydrogen-channel source bridge now has an offline Figshare metadata-byte
parser and fixture for the pinned metadata and one source archive. Its Hangang
data directory is configured and both external source files are staged with
matching expected hashes. New deferred Python handoffs cover oxygen-room alarm,
Cantera catalytic-wall heat utility and Cantera gas-species sensor/alarm
integration; these do not validate physical models. The current catalog has 80
families: 19 implemented, 37 native-adapter-verified and 24
implemented-unverified. Its 56/80 (70%) stronger-status share is not total
project completion.

An AB2 tank shell-temperature bridge is also implemented for caller-authorized
forcing into the finite hydride heat boundary. Its Hangang contract now includes
mapping-clone and direct-construction rejection. The bridge requires explicit
shell-to-bath evidence and is not a shell/bed physical validation.

The finite-hydride gas-port trace now has a typed bridge through the existing
shared nozzle model into `SourceHistory`. The caller provides release location,
opening and backpressure; source ownership, interval port accounting and solver
path are retained. Its Hangang case is a contract check, not a release/dispersion
validation.

A conservation review found that nozzle rates were not reconciled with the bed's
integrated outlet ledger. The bridge now requires explicit flow quadrature and
an evidence-backed absolute/relative tolerance, checks every interval, and
rejects mismatches. The synthetic contract now derives the bed outlet from the
same nozzle law and exercises oversized-opening rejection. This correction is
post-current5f and requires a fresh current5g pin; it is not yet Hangang-verified.

Current4 CSTR job 1186427 failed before integration because the adapter tried
to assign Cantera's read-only `Interface.T` property. The Cantera 3.2 API path is
now corrected to read the accepted surface phase through
`ReactorSurface.phase`, which invokes native `restoreState()`; strict reactor,
gas and surface temperature checks remain. The fix is in current5d but still
needs a new-pin retry; the failed job is not a physical-model result.

Current4 linepack case `hydrogen-pipeline-lumped-isothermal-linepack`
1186441 passed against revision `26845bb9815963b5ce0a337ffcfd9e9bca8afbc7`
with maximum mass residual `5.662137425588298e-15 kg`. Current4 reactant-current
policy case 1186459 also passed; neither is physical qualification. Current4
cases 1186447/48/49 exposed a fixture direction condition, moving-wall residual
slightly above the declared geometry budget, and GrInHy2 header mapping mismatch.
Corrections are local and need a new pin. A second current4 engine case,
1186461, reproduced the same old-pin geometry residual; the tightened solver
code is not in that revision. Current5d
`20f54aefa0fd8f95e1fd0618caf8ddeef5926fde` contains 1,093 files and the CSTR
correction, but predates later code and documentation edits. The latest queue
snapshot had five active jobs: three unrelated jobs plus current4 cases 1186462
and 1186463. Code and data work continue independently; no running result is
awaited before the next implementation task.

Current2 singleton Hangang outcomes: relief withdrawal accepted-edge ledger
1186388 and invalid-edge rejection 1186390 completed; sensor calibration
recovery 1186405 and rejection 1186410 completed. Accident consequence handoff
1186386 and source-bound uncertainty 1186387 failed in the evaluator-binding
guard before a consequence output was admitted. Synchronized fuel-cell thermal
coupling 1186418 failed before its first accepted sample because the native
connection reported that a current/thermal-partition callback changed; no
physical integration result was produced. These are software-contract outcomes,
not physical validation. The accident fixtures and a callback fix are being
prepared for a later immutable source pin.

Current4 was captured, transferred, and verified against its immutable archive
SHA and 1,086-file manifest. Its local follow-up code set includes the
solver-scaled open-cylinder geometry check, CSTR state synchronization,
linepack/network corrections, and several existing callback/fixture updates.
Newer edits to the finite-source boolean gate, accident consequence fixtures,
core-flood curve summary, and compression-to-mixture-vessel handoff are not in
that pin; they are reserved for current5. New singleton submissions continue
against a pin only when their source revision matches the implementation under
review.

Added an optional source-bound Corey-type power-law compression for a selected
hydrogen/nitrogen core-flood relative-permeability branch. It requires caller-
evidenced irreducible-water and residual-gas saturations, retains exact source
row IDs and fit residuals, and refuses queries outside the observed range. The
existing interpolation API still does no extrapolation. Its synthetic deferred
Hangang case does not interpret measured workbook headers or qualify a field
law.

Added a typed compressor-to-finite-mixture-vessel handoff. It checks CoolProp
HEOS hydrogen/fluid and molar-mass mapping, shared enthalpy-reference identity,
accepted receiver state, pressure direction and constant-flow interval
accounting. This stream translation does not model a valve, receiver pressure
control, or transient compression. The deferred Hangang case is synthetic.

Added a source-hash-bound matrix reader for DataverseNO X044QK (CC0 1.0,
DOI `10.18710/X044QK`): local attachment SHA-256
`c50162c995c01bb37c407e7ce0f132301297bf3b2562518c86940fb758ae2557`, publisher
MD5 `6c929ee530ac393ee8e76f6db2eff05c`, 14,199 bytes. The 40-row matrix reader
and deferred Hangang case `dataverse-x044qk-open-atmosphere-ignited-hydrogen-jet-matrix`
are registered for current5. The matrix was transferred through the existing
`run.sh cpu` channel to Hangang's external source path; remote size and SHA-256
match. Publisher-reported MFR is pressure-derived. Raw
EXP_022 is absent; the other 39 pressure histories and six video bundles remain
unacquired. Pressure-channel calibration and absolute/gauge basis are unresolved;
the reader performs no pressure/flow conversion and claims no dispersion or
overpressure validation.

## Local implementation update — 2026-10-31

The existing rigid-fragment trajectory can now be paired with an analytic
Lamé-field elastic strain-energy ceiling. Its result bounds speed for one
caller-selected fragment mass and caller-selected energy fraction; it does not
predict rupture, fragment formation, or a launch state. Its standalone
synthetic Hangang contract is registered for the next source snapshot. The
catalog now tracks 80 families: 19 implemented, 37 native-adapter-verified,
and 24 implemented-unverified, with zero planned rows. Thus every catalog family
has a coded implementation level, while 56/80 (70%) are at the stronger catalog
statuses and the other 24 await verification. Family-row coverage is not an
overall completion estimate or proof that all fidelity extensions are complete.
No local test or calculation was run.

Added `ExtendedLangmuirIsotherm`, a caller-parameterized competitive
multicomponent provider with per-site capacity and analytic pressure/optional
temperature derivatives. Its synthetic Hangang case is deferred, not executed,
and does not qualify material parameters. No independent parameter evidence is
implied by its API-level case.

Added a fixed-volume, lumped isothermal pipeline linepack model with explicit
interval mass accounting and inventory-floor handling. It is a gas-pipe
capability level and intentionally does not claim spatial momentum, wave
propagation, or real-gas/thermal behavior. Its synthetic Hangang case is
registered for the next pin.

Added a segmented quasi-steady gas-pipe network extension that reuses the
existing compressible Darcy link solver across finite ideal-gas cells, carries
signed boundary/link mass ledgers, and localizes a caller-declared cell
inventory floor. This adds spatial pressure/inventory nodes while retaining
fixed T/composition and no pipe inertia or wave claims. Its deferred case is
registered under `gas-compressible-pipe`; no local test or calculation ran.

Added exact heterogeneous k-of-n detector fail-to-alarm probability with a
separately supplied common-cause event input, plus a source-versioned immutable
evidence reader that reports empirical simultaneous-demand frequencies without
assuming independent channels. Both deferred cases are synthetic and do not
infer failure rates, repair, test intervals, setpoints, or confidence bounds.
They are registered under the facility-protection Hangang profile for the next
pin.

The line-source radiation receipt now binds its original HyRAM flame and
rejects direct or cloned results. Its deferred issuer-integrity case awaits a
Hangang profile with both the CoolProp and preferred-dispersion environments;
the core-only campaign profile is not suitable for that case.

The acquired GrInHy2 plant-flow CSV now has a first-party, checksum-pinned
Python API (`h2physics.data.grinhy2`) returning immutable aligned observations
and preserved irregular timing. Its deferred Hangang ingestion contract is
registered on the source-data profile. Hangang job `1186145` reached the reader
but exposed a Windows CRLF versus canonical archive LF hash mismatch. A
per-file Git attribute now preserves the reviewed CSV bytes across operating
systems; retry is pending a new immutable pin.

Added a source-hash-bound H2SAFE indoor-release ZIP reader with
immutable time-series, raw-token retention and same-lab channel/sensor mapping.
It leaves concentration units/basis, calibration, clock and coordinates
unresolved. The reviewed tests are helium surrogate releases, not measured
hydrogen dispersion or hydrogen-sensor response. The CC BY 4.0 archive
(3,766,528 bytes; SHA-256
`f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e`) has been
staged at the Hangang external path via the existing shared `run.sh` channel;
remote size and SHA-256 match, and temporary transfer chunks were removed. Its
deferred ingestion case is registered for the next pin using that path; no
dispersion validation is implied.

New Hangang pin `cb6e00d48943cff36728c8ee88d683c5b8f5fb68` is now staged and
verified: 1,086/1,086 source manifest entries match, manifest SHA-256
`7ed9e5f3afae46a55ff46412e5f03b59b3f8c524015116a7258b369cd3f08711`, archive
SHA-256 `e977c7477e3317fb41608886fe8266b619f1c81257af4c069e150a5ac2d75994`,
and forbidden-file scan count 0. The capture includes the H2SAFE case/path,
detector trial evidence, segmented pipe network, CSTR/engine-wall and the
first set of fixture corrections. A subsequent `TurbineMapPoint` freshness
fix was made after this capture, so hold Brayton bleed cases on this pin; the
same follow-up pin must also add the later relief and fuel-cell fixture fixes.
New-pin singleton submissions proceed as QOS slots open; current-pin jobs keep
running independently.

On immutable revision `3374d5ec87eeac05eb4311aab51af1de149966c9`, Hangang
contracts `1186148` (quasi-steady permeation), `1186149` (steady film/bulk
permeation), `1186151` (adjacent photochemical operations), `1186155`
(cylindrical-shell diffusion), `1186156` (pressure-driven porous well),
`1186157` (compressible gas-pipe momentum), and `1186158` (competitive
extended Langmuir)
passed synthetic contracts only; none qualifies a physical model against
independent evidence. `1186146` (time-varying solubility boundary) failed an
exact-float fixture assertion; it now uses a tight relative tolerance. Retry
is pending a new source pin. `1186160` native finite-flow catalytic CSTR failed
its strict gas/surface temperature-equilibrium invariant by 0.032 K; the
Cantera accepted-state synchronization fix is now local, preserving the strict
invariant and awaiting a fresh-pin retry. Engine jobs `1186166` and `1186167`
failed before model entry because the deferred case omitted its `OpenCylinderInlet`
import; the import is fixed locally, pending a new source pin.
`1186168` (prescribed engine boundary-stream ledger) and `1186171`
(synchronized finite fuel-cell trial exchange) passed on the same revision.
`1186169` wall-energy ledger stopped before model integration because its case
parameters still contained mechanism and energy-tolerance placeholders. The
case now resolves `h2o2.yaml` through Cantera data directories and reports a
72/144/288-sample residual-refinement sequence without asserting a universal
energy tolerance. It requires a fresh immutable source pin and a Cantera
environment exposing that mechanism; no physical qualification is implied.

Further independent singletons on the same immutable revision passed:
`1186209` native-pool impact, `1186226` conditional fragment flight/impact,
`1186227` impact intercontact heat, and `1186234` photochemical Gibbs-path
energy bound. `1186210` reached the hydrostatic
fragment-flight fixture but did not produce its expected ground-contact event;
the local fixture now starts lower within the same declared 0–5000 m profile
and keeps the 30 s horizon. Its retry awaits a fresh pin. `1186183`
uncertainty and `1186184` accident-chain cases exposed deferred owner-binding
issues, and `1186192` rejected its initial native mixture phase split because
the material-balance residual exceeded the declared bound before ODE
integration began. The case now records this as an unresolved backend/fixture
qualification gap. The accident-chain consequence fixture now uses module-level
synthetic result/owner types while retaining all captured-configuration and
provider-output mutation checks; no shared currentness guard was weakened.
These are being handled as separate items; no acceptance bounds are being
relaxed. Current-pin passing cases remain software contracts only.

Six more current-pin relief contracts are submitted concurrently as singleton
jobs `1186237`–`1186242` (travel, leakage, phase, inventory, accepted-withdrawal
ledger, and invalid-edge rejection). The first four stopped at worker setup
because the external LH2DT package path was absent from `PYTHONPATH`; the last
two entered their cases but require explicit deferred fixture factories. They
are environment/case-wiring failures, not native model results. Three other
independent cases hit the per-user QOS submission cap and will be retried as
capacity opens.

The remote PATH correction enabled immediate retries: `1186250` leakage and
`1186251` phase passed, as did `1186252` HyRAM source-transition ledger,
`1186253` SLABx caller-executor snapshots, and `1186254` native-pool accepted-
edge energy contract. Relief inventory, clock, and binding retries are now
submitted as `1186255`–`1186257`; `1186256` clock and `1186257` binding passed,
while `1186255` still exposed a missing depleted-state fixture on the old pin.
The next-pin fixture now supplies zero selected-phase inventory and retains the
inventory-floor rejection assertion. These are all deferred software
contracts, not physical qualification.

Six thermal contract cases on the same pin also passed: `1186260` variable
capacity, `1186261` refinement, `1186262` domain rejection, `1186264` pulse
response, `1186265` lossless reduction, and `1186266` exposure-history handling.
The PIFIRA effective-area receipt case hit QOS and has no job ID yet.
Two additional gas-turbine boundary contracts, `1186268` zero-limit bleed and
`1186269` mixed-turbine bleed, were admitted concurrently; cooling and staged-
turbine singletons hit QOS and remain ready to retry. Both admitted bleed cases
entered the adapter but failed on an invalid `require_current` call against a
`TurbineMapPoint`. A source-bound point-level method now rechecks the retained
map and interpolation coordinates without rerunning the cycle; retry requires
a fresh pin.
The synchronized Cantera fuel-cell thermal-coupling case `1186272` was also
admitted but failed before its first accepted sample because its synthetic
heat-partition callback closed over a class object whose namespace token was
unstable. The fixture callback now lives at module scope with a function-local
class import, preserving the adapter's freshness check; retry requires a new
pin. Related zero-current/current-
limit cases hit QOS and remain queued. The native fuel-compression case
`1186274` passed its deferred contract.
The Mendeley hydrogen core-flood source-bound table case `1186277` was admitted
using its already-staged external workbook path and passed its offline source
identity/table contract. No unit inference or calibration claim is made. The
relative-mobility contract hit QOS and remains ready without a job ID.
After QOS capacity opened, `1186306` native hydrogen fuel-compression and
`1186310` source-bound core-flood relative-mobility contracts were resubmitted
as independent singletons; results are pending.
Both passed on the old pin: `1186306` native fuel compression and `1186310`
source-bound core-flood relative mobility. `1186301` relief failure-prefix
stopped at a missing `failure_fixture_factory`; a native-owner fixture now
accepts one 5 ms interval, then exercises LH2DT rejection of an invalid second-
interval boundary while retaining accepted-prefix provenance. This checks
input-failure prefix handling, not an equipment/EOS failure, and awaits a
follow-up pin.
Current-pin case `1186329` PIFIRA effective-area receipt passed. `1186330`
reactant current-limit stopped because the synthetic 1,000 A/m² demand was
below the derived ~1,608 A/m² oxygen cap, so the API correctly returned no
limiting reactant. The fixture now requests 2,000 A/m² for the follow-up pin.
`1186331` zero-current native fuel-cell case hit the callback namespace
freshness issue; its callback is now module-scoped for the follow-up pin. New
singleton jobs
`1186338` fugacity-driven films and `1186339` reserve-current limiting are
`1186338` fugacity-driven films passed its software contract. `1186339` reserve-
current limiting hit the same callback-currentness guard and is held for the
fuel-cell follow-up pin. On current2, `1186346` H2SAFE source-bound archive
ingestion passed its source identity/schema/token contract. The source is a
helium surrogate and this result is not hydrogen dispersion validation.
`1186359` segmented pipe network failed before its assertions because the
deferred case imported `IsothermalGasPipeCell` while the public type is named
`IsothermalPipeCell`; the case and guide imports are corrected locally for a
follow-up pin. `1186363` lumped linepack similarly failed during state
construction because its new code passed unsupported `nonnegative=` keywords
to the shared `finite()` helper. The API now uses a local finite-and-nonnegative
validator; no linepack assertions ran on current2. Linepack, CSTR, engine,
detector, fuel-cell and risk
singletons are prepared for submission as QOS slots open; no result is claimed
before an outcome artifact. The first segmented-network contract is admitted as
`1186359` on revision `cb6e00d`; its result is pending.

The PV/direct-DC electrolysis runner now rejects repeated source-stage IDs
before native solving. Profile-generated stages retain both original input
knot IDs in an immutable tuple. Deferred contract cases cover unique stage
keys and source-pair preservation; they have not been executed. Those changes
do not advance physical verification or validation status.

Cantera catalytic CSTR samples now synchronize the reactor thermo and surface
phase handles from the accepted native state before checking strict thermal
equilibrium. This addresses the 0.032 K stale-handle failure from job
`1186160` without loosening the invariant. The result needs a fresh immutable
pin and Hangang retry.

The `materials.permeation` family gained an optional two-film/bulk steady
series-resistance API with separate boundary and surface evidence IDs, typed
surface concentrations, and a deferred contract. Its new level is
implemented-unverified. No test or scientific calculation was run.

Further Python API increments add a caller-pressure-driven porous-reservoir well
boundary, steady horizontal isothermal ideal-gas pipe flow with acceleration,
and an altitude-bounded hydrostatic ideal-gas density profile for fragment flight.
Each has a deferred synthetic or analytic contract and explicit model limits;
these new increments have not been scientifically validated or compared against
independent measurements. New-source recapture is pending while the current
immutable Hangang campaign continues.

Data discovery added four nonduplicate open experimental sources. The GrInHy2.0
plant H2-flow workbook (1 file, 27,069 bytes, Zenodo record CC BY 4.0) is acquired
locally and normalized to an attributed 447-row tracked CSV. Its timezone,
normalized-volume reference state and logger gap remain unresolved; see
`data_sources/grinhy2/README.md`. A large-scale open-atmosphere explosion
collection (59 public
files, 96,861,179,314 bytes, DataverseNO dataset-level CC0 1.0, 0/59
acquired). The latter's text-filter view reports 52 files; the full metadata API
reports 59 (52 text/plain plus 7 other MIME types). Its file metadata has no
separate license property; file contents and embedded rights were not reviewed.
The large explosion collection remains a selective-acquisition candidate. A
third source is SOE fault-operation measurements
(11 files, 1,092,175,741 bytes, Zenodo record CC BY 4.0, 0/11 acquired), with
polarization, temperature, pressure and flow measurements across four stated
fault conditions. Its MAT files and channel mappings remain unreviewed.

A fourth distinct source, HyDelta D6A.1 closed-space outflow, is now cataloged
from its Zenodo record/API (CC BY 4.0, 2 report PDFs / 14,260,186 bytes,
0/2 acquired). It covers four release rates, H2/natural-gas comparison,
ventilation configurations and a 3×3×6 sensor grid. This is a report/table
extraction candidate, not raw time-series validation data; no files or tables
were downloaded or transcribed. The three non-GrInHy sources remain candidates
pending file/schema and measurement-convention review. The GrInHy table is a
boundary-flow data asset only and does not validate stack electrochemistry or
plant efficiency.

## Latest Hangang result — 2026-10-31

Job `1185860` (`carrier-original-binding`) failed in the deferred case when it
attempted `cached.setflags(write=True)` on a bytes-backed immutable array; the
case did not catch the expected `ValueError`. This is a case assertion/setup
failure around the read-only cache contract, not a carrier-model failure. The
case now expects write-enable rejection and calls `result.require_current()` to
confirm the untouched result remains current. The local case correction is
unverified and has not been replayed; no scientific qualification follows.

## Latest verified Hangang source — 2026-10-31

Snapshot revision `9048413b68025235753242dcb93efb68d9afc477`; archive SHA-256
`5a34abfd652c7dbe6ff6ba41ca7981082e42bffc70533e805c638ef33f99250c`
(3,780,321 bytes); manifest SHA-256
`9034a8102d3bbe6b53310ab122b5a359acb1d8918ba62dc065343999e10eb4ca`; all
1,060/1,060 entries verified. From this snapshot, `1185710` (offline core-flood
source ingestion) passed its metadata/listing hash checks and four staged
workbooks. This is source-ingestion evidence only, not physical-model validation.
`1185709` (CSTR) entered but failed the fixed geometry/site-domain invariant
after initialization and enthalpy fixes; the exact subcondition is under
investigation, so there is no accepted CSTR result. A local diagnostic patch now
separates volume, site-density, and temperature checks and reports native values
without relaxing bounds. The root cause remains unknown; retry after a fresh
snapshot. Jobs `1185709`/`1185710`
used external logs. This snapshot predates the canonical Krg/Krw mobility guard
and staged-turbine fixture correction; a newer snapshot is needed for those
changes. Separately, from older `64a31`, `1185715` (`thermal-target-domain`) and
`1185716` (`impact-elastic`) passed their synthetic/domain contracts with outcome
JSON evidence; these are not independent validation. Earlier failures remain
scoped to their pinned source snapshots.
Also accepted from `64a31`: `1185718` (`thermal-target-exposure-history`),
`1185719` (`pifira-effective-area-receipt`), and `1185720`
(`impact-zero-contact`), plus `1185722` (`impact-dryout`), `1185723`
(`impact-prefix`), `1185724` (`impact-history-issuer-integrity`), `1185725`
(`impact-intercontact-heat`), `1185726` (`impact-missing-heat`), `1185727`
(`impact-native-pool`), `1185729` (`impact-refinement`), and `1185730`
(`thermal-target-lossless`) have completed on `64a31`. `1185718` failed with a
ValueError because left-held history length did not match edge/interval shape;
this is a case input/contract issue, not independent scientific validation.
`1185727` passed after installing exact pinned optional `dynamiclh2poolx`, only
for its deferred synthetic contract; this is not physical qualification. The
other listed jobs passed their deferred synthetic contracts.
These case-level passes do not establish independent scientific validation.
Logs are external.
From `64a31`, `1185735` failed because its edge/sample fixture slices had
unequal lengths; adjacent-pair indexing is now corrected locally. `1185736`
relief-lift-travel and `1185750` relief-lift-leakage failed because the plan
omitted `fixture_factory`; a local fallback now builds synthetic scenarios with
actual reviewed LH2DT protection/nozzle/native state types, including explicit
wrong-state rejection. It remains unverified pending recapture. `1185737`–`1185740`
failed phase-partition PQ component/mole consistency checks, not independent
scientific validation. `1185752` impact-native-pool passed after installing the
exact pinned optional provider, scoped only to the deferred synthetic contract.
No physical qualification is established. Logs are external.

## Previous verified Hangang source — 2026-10-31

The complete snapshot is revision `64a31d2784b72f66d66a77accb01e18e3d711a4f`,
archive SHA-256 `3811c36a140e38200a81c6b3d622a9ebb547d2d9350bcd36f8d5f9f1848216cb`
(3,776,678 bytes), manifest SHA-256
`7bc132d660b514a657068d1b2ad41d6a417849730812437b78eb0fb32583ac1a`, with
1,060/1,060 entries verified and zero raw or processed data files. Jobs `1185638`
(CSTR) and `1185639` (core-flood source ingestion) failed after case entry: the
Cantera controller was not initialized before reading `mass_flow_rate`, and a
numeric Mendeley version was rejected because a string was required. Local fixes
are in progress. From this snapshot, `1185646` failed its synthetic mobility
role-rejection assertion (now corrected to use the canonical Krg/Krw phase
guard). Jobs `1185647`, `1185661`, and `1185662` failed before their staged-
turbine scenario assertions because the fixture passed a callable where the
open-Brayton API requires a native Cantera phase; that fixture is now corrected
locally, unverified. Jobs `1185664` (impact-baseline) and `1185665`
(thermal-target-refinement) entered and passed. Four cases passed overall:
`1185448`, `1185452`, `1185664`, and `1185665`; this does not establish source,
equipment, or scientific qualification. Jobs `1185646` and `1185647` were
accepted after initial QOS refusal; `1185661` and `1185662` were also accepted.
Results are preserved outside the source tree. Jobs `1185550`/`1185557` were
launch/log-only failures from older `8105` when PBS logs polluted the pinned
source; external log paths now work. Earlier `8105` outcomes remain historical.
Job `1185687` (`thermal-target-pulse`) passed its deferred synthetic energy
ledger on `64a31`, with maximum residual about `1.14e-8 J`; this is not scientific
qualification. After QOS reopened, `1185698` (`thermal-target-domain`) and
`1185699` (`impact-elastic`) were accepted; results are pending and logs are
external. Earlier QOS refusals had no job IDs.

## Prior Hangang outcomes from snapshot 64a31 — 2026-10-31

Jobs `1185448` (thermal-variable), `1185452` (fragment), `1185664`
(impact-baseline), and `1185665` (thermal-target-refinement) entered and passed.
The other case-level failures and fixture corrections for source `64a31` are
recorded in the current snapshot block above. Job `1185450` had the Cantera
surface API issue; `1185453` failed fixture import before ingestion. From older
source `8105`, `1185507` failed exact float equality in a synthetic contract
without physical/source evaluation, now fixed with `isclose`; `1185550` and
`1185557` did not enter cases because PBS logs polluted the pinned source.
External log paths now work. None of these results establishes full scientific,
source, or equipment qualification.


## Local changes after the latest uploaded source

The pinned Hangang snapshot `782d9a7326f85a94bdbfaeb651fd380809fba724`
contains the first cryogenic MOF reader and impact-trace integrity increment.
The current local tree additionally includes:

- One-buffer, bounded cryogenic MOF checksum/parsing and currentness reads,
  plus branch projection into the existing `ObservationTable` fitting API.
- Adaptive mixture initial-quality admission, exact zero initial transfer
  ledgers, consistent event diagnostics and an independently counted attempted
  RHS-call diagnostic, including interrupted solver callbacks.
- Catalog/API/backlog reconciliation that distinguishes the existing bounded
  host adaptive solver from the remaining receiving-native integration request.
- Variable total heat-capacity thermal response using caller-provided `C(T)` and
  its integrated stored-energy ledger, plus a finite-feed catalytic CSTR using
  native Cantera flow controllers and sampled closure accounting.
- Conditional rigid-fragment flight and ground-impact integration from explicit
  launch/environment inputs, with momentum and mechanical-energy residuals.
- A source-bound reader for four publisher-licensed H2/water core-flood
  workbooks, preserving raw relative-permeability rows and source identities.
  Publisher-listed CC BY 4.0 metadata, sizes, and SHA-256 values are recorded;
  no conversions, averages, or fits are inferred.
- Hangang array generation now pins the selected checkout on `PYTHONPATH` and
  maps Slurm worker IDs to the runner's PBS-compatible identity fields.

The verified Hangang snapshot `341c2a1375f41a74` contains the CSTR and variable
capacity thermal cases. Arrays `1185219` and `1185237` both failed before model
entry: first, Slurm job variables lacked PBS aliases; second, selected-subset
indices were compared against the full plan ordering. Neither scientific case
started. The local generator now maps both ID schemes, creates a compute-local
temporary directory, pins the source `/src` on `PYTHONPATH`, and resolves each
case by its pinned ID. A separate static CSTR review found and fixed an
uninitialized site-fraction residual that would have stopped the flowing case at
its first output. The verified `37752360` archive is staged in the user's Hangang
scratch directory as `h2physics-jobs/live-37752360ffd3f403/repository`; archive SHA-256
`37752360ffd3f403ecc57ec7f74b4b3541538b82776061df7ff1f7c673da2b3`, with all 976
manifest entries verified. It includes fragment/core-flood code and launcher
fixes but predates the CSTR correction and omitted `src/h2physics/data`. Its
three-case array was refused by the user's active-job QOS limit; the single
`thermal-target-variable-capacity` job `1185303` was accepted by the scheduler,
then failed on that missing package
before the case entrypoint. No model ran. The checksum-consistent capture was
incomplete relative to the repository. Snapshots `341c`, `37752360`, and `13e720` are
all incomplete and no case ran from those snapshots. A corrected full capture is
under construction; no scientific validation or family-status promotion follows
from source/checksum checks. Snapshots `341c` and `37752360` have remote archive/
manifest checks but omit `src/h2physics/data`; `13e720` is an incomplete local
candidate and is not a remotely verified complete source. An earlier summary of
the latest Hangang batch was superseded by the outcome JSON audit: jobs `1185448`
and `1185452` entered and passed; `1185450` entered the CSTR case and failed on
unavailable Cantera surface method `getPartialMolarIntEnergies`; `1185453` entered
core-flood and failed importing its absent fixture before ingestion. These
outcomes do not provide full scientific qualification. A fresh complete snapshot
is pending before another launch.

## Progress snapshot

The 77-family catalog has a first code or native-adapter level in all 77 families.
The catalog classifies 57/77 (74%) as `implemented` or
`native_adapter_verified`; another 20/77 are `implemented_unverified`. This is
first-level catalog coverage only, not the percentage completion of the full
research programme. Scientific progress since the 59/72 historical accepted
execution checkpoint is unverified until the deferred Hangang campaign runs.
The full programme percentage cannot be defended from source or case counts alone.

The regenerated Python 3.12 deferred metadata inventory records 371 cases, 56
profiles and 105 case modules. The prior generated snapshot had 370/56/105; the
inventory now covers subsequent additions and is the current source for campaign
counts. It inspects case metadata only and is not scientific test evidence.

Latest structural inventories: public API 1,455 definitions across 241 modules;
relative-import audit 1,748 bound imports with zero missing or unresolved symbols;
Markdown link audit 3,941 links across 340 files with zero missing paths. The
current Hangang plan contains 97 cases across 19 profiles and 36 modules. These
are metadata/source checks, not execution evidence.

2026-10-30 latest source increment adds a source-bound reader for the licensed
cryo-MOF H2 adsorption branches. It verifies listed attachment size/checksum and
an acquisition SHA-256, preserves raw source tokens/missing cells and separates
the 20 K normalized-pressure/reference-volume semantics from the unresolved
77/87 K reported-pressure basis. Its synthetic parser contract is deferred.
Finite-wall parcel-impact history now requires one-use native issuance and
recomputes sequence summaries from retained steps, closing caller-forged summary
admission in the population adapter. The new deferred `impact-history-issuer-integrity`
case is also registered. Neither change was executed. Static public API inventory
now records 1,455 public definitions across 241 source modules; these figures are
navigation metadata, not model verification.

2026-10-30 latest local increment: a separate paired-sample fitter now estimates
only the existing first-order H2 concentration sensor time constant, with source,
clock, basis/unit, initial-state and bounded-search evidence retained. Two
`facility-protection` acceptance cases are registered in the Hangang and Nurion
source plans; the regenerated plan inventory now counts 362 Nurion and 79 Hangang
cases. Gain, bias, delay,
uncertainty and field/safety qualification remain open. No local tests, model
calculations or cluster jobs were run.

The PEACE pressurized alkaline short-stack record has a CC BY 4.0 provenance seed
and source-token-only reader. Three raw runs plus the column map (11,514,333 bytes)
were downloaded from public record file links. All four publisher MD5s match; local
SHA-256 values are in the manifest. The identical 131-field headers were inspected,
but many channels remain unnamed. Its four synthetic parser/integrity/projection cases are in
both plans; no
measurements have been mapped or used for model validation.

A separate PEACE/TU/e flow-cell electrochemical dataset is recorded as a second
process-data candidate. Its DataCite DOI record exposes CC BY 4.0 and v1 metadata,
but the 4TU repository endpoint was unreachable and the DOI record lists no files.
No measurements or schema were inferred and no parser was added.

The PEACE source-token reader now has a file loader that requires the declared
raw filename, size, publisher MD5 and manifest SHA-256 before UTF-8 decoding.
Returned tables retain source bytes and preamble, and `require_current()` rejects
stale path contents. A deferred synthetic integrity case covers same-path
mutation; it was not run and does not open ignored source data.

The PEACE description-map loader separately verifies its CSV receipt. A new
immutable projection binds publisher-described time, total electrical channels,
five temperatures, reported pressure, H2 flow and H2 quality to source-row indices
as string tokens with both file hashes. Normal-volume basis, calibration, clock
rollover and cell/stack semantics remain unresolved. A synthetic projection case
is deferred and does not access ignored raw files.

Loader-issued seals now prevent direct wrapper admission; `require_current()`
reconstructs raw rows, description entries and projected channel content from
their exact hash-verified owners, detecting dataclass replacement and object-level
mutation. A synthetic forgery-rejection case was added and remains unrun.

An opt-in unit view now keeps raw tokens and adds A/W/V/K plus reported Pa only
where the publisher's description fixes units. H2 flow/quality and `Zeit` remain
raw; no normal-volume, composition, pressure-basis or stack-semantic inference is
made. Its synthetic deferred case also rejects direct/replaced SI wrappers.

The source-to-dispersion accident chain now feeds its exact admitted final handoff
to the existing facility-consequence evaluator and preserves failure-stage context.
Its deferred case is in both campaign source plans. The closed-charge Cantera
piston segment now also accepts a caller-issued W/m² heat-flux schedule through its
native moving wall, includes the integrated input in the sampled first-law ledger,
and is enrolled through the existing `hydrogen-engine` case module. An open-cylinder
helper maps a caller-prescribed crank-angle fuel mass-flow trace to the existing
Cantera feed path; it does not add injector or nozzle physics. Oxygen-deficiency
reporting now integrates positive threshold deficit exactly over each admitted
piecewise-linear sample interval and rejects human-dose/probability interpretation.
These contracts are enrolled in both campaign plans and remain unexecuted; receptor
physics and engine heat-transfer qualification remain open.

## Latest source implementation increment — 2026-10-30

Seventeen additional deferred API contracts have been enrolled since the previous
metadata snapshot: shared-nozzle pressure-responsive engine feed, unit-safe
normalization of PEACE publisher-described channels, and ordered sequential impact
contacts on one finite wall. The latter reuses the existing impact owner and retains
its coupled contact history; it does not multiply representative event counts or
introduce simultaneous-impact physics. A facility accident/consequence adapter now
reuses the existing joint uncertainty engine and carries source freshness through
the retained raw model output. The porous-reservoir model also accepts a shared
`PropertyProvider` directly, including CoolProp HEOS, and rejects non-gas states;
the deferred case now requires the profile's thermo extra. The acquired BAM
jet-fire reader also provides a source-bound numeric projection for labels with
explicit units while retaining unresolved channels as raw tokens. These additions
are source-plan only and remain unexecuted on the cluster.

The open-cylinder hydrogen feed can now use the shared homogeneous isentropic
nozzle against the live native-cylinder pressure, with Cantera's native
mass-flow-controller serving only as the mass-rate adapter. The exact Cantera
frozen-gas property basis is required; nozzle acceptance records and failure
prefixes remain attached to the trace. The deferred case joins the existing
hydrogen-engine campaign module. It introduces no injector, spray, jet momentum,
or experimental engine qualification and remains unexecuted.

Request031 now has a Cantera 3.2 single-ReactorNet model for three finite gas
compartments and one stack thermal state, with explicit current/heat-partition
callbacks and an optional H2/O2 reserve feedback taper (not an event locator or
validated shutdown policy). Request032 now has a changing-composition finite-interval marcher and a
SciPy adaptive ODE that re-flashes changing stocks and localizes selected inventory
and quality events. This host-side ODE does not replace a receiving native engine
or independent EOS qualification. Request033
has a stricter host contract for solver-issued pool accepted-edge energy records,
but the external pool owner still lacks those records. Request034 adds a native
one-way pressure-responsive Cantera Valve and an optional finite lumped wall node
in the same open-cylinder ReactorNet, with caller UA, external heat, and combined
energy ledger; its three cases are deferred. Request029 adds single-species adaptive
adsorption with LDF rates and thermal/feed/outlet ledgers, plus phase-specific relief
withdrawal mass/enthalpy trapezoids over accepted edges. Request030 adds an evidence-
bound static compressor surge-line margin receipt around existing native map points.
Request035 adds a bounded multi-start map operating point, one compressor-air
bleed at the turbine inlet, multi-stage turbine cooling stations, and Cantera
ideal-gas and CoolProp HEOS real-fluid single-stage H2 compression paths. The
Cantera result can link to a matching Brayton point; the separate real-fluid path
retains its EOS boundary. All new contracts are registered in Hangang/Nurion plans
and remain unexecuted. Blade metal and film physics, compressor maps/trains/cooling
and independent machine data remain open.

The Hangang `cpu` and `gpu` shared-wrapper probes both reported no usable shared
connection after the user's reconnection notice. No new login/authentication or
remote job was attempted. Hangang was selected for the next parallel campaign;
the source-plan metadata now contains 79 cases across 17 profiles and 31 modules.
It remains unexecuted pending wrapper availability.

## Latest data increment

The BAM hydrogen jet-fire dataset (Zenodo DOI 10.5281/zenodo.21026781) is
catalogued and its 75.22 MB archive is acquired in ignored raw storage. Publisher
MD5 and local SHA-256 match the recorded values. Inspection found source text
exports for thermocouples and hydrogen mass flow, with source-native units and
sample-rate metadata. A bounded raw reader and synthetic parser case are now
implemented; the case is deferred to Nurion. No measured archive parsing or
thermal-model comparison was run.

Checkpoint sections below retain the development history. Read the final
continuation section and PROGRESS.md for the latest execution evidence.

Latest operation-receipt increment: `OperationalScenarioReceipt` fingerprints
the retained LH2DT supply graph (boundary/junction identities, links/component
owners, power readers, inventory readers and selected pump mode). Its deferred
common-clock contract adds a link after receipt issuance and expects stale-receipt
rejection. This is source-identity protection only; the contract is unexecuted and
does not add native coupling or prove route correctness.

`uncertainty.py` now supports caller-supplied joint scenario mappings with explicit
parameter domains, dependence/source evidence, seeded PCG64 draws, per-row scenario
identity and retained failure prefixes. Its synthetic deferred case is registered
only in the separate Hangang plan, which now has 21 cases; it is not part of the
Nurion metadata inventory. This remains implemented-unverified and does not infer
probabilities or validate an empirical joint law.

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

The earlier 304/51/74 snapshot progressed to 345/54/94, then 362/55/101; the latest metadata is 364 deferred cases across 55 profiles and 102 modules. The current AST API inventory covers 1,439 public top-level definitions across 238 modules. The current AST relative-import inventory covers 1,733 bindings across 238 modules with zero missing or unresolved symbols. The refreshed Markdown link audit checks 3,906 local paths across 338 files with none missing. These structural inventories do not validate model accuracy.

Latest coding continuation: the fixed-temperature porous-reservoir kernel now
issues sealed results, admits a separate external boundary temperature and
tracks signed outer-boundary mass. Its synthetic contract covers inflow/outflow,
closure, forgery and mutation. The finite pure-fluid separator rejects callback
code/captured-state changes through native integration. Hangang campaigns can
select smaller independent batches with repeated `--case-id`. Request031 now has
a solver-neutral exact-trial fuel-cell exchange with stoichiometric source terms
and unresolved energy; it does not integrate pressure feedback. Request035 now
composes caller-owned compressor and turbine maps with existing Cantera/Brayton
physics and reports a non-closed shaft residual. All three cases are deferred to
Nurion; the new fuel-cell and Brayton cases are also in the Hangang plan, now at
21 cases. None has run, and no local scientific tests/calculations were performed.

The engine boundary ledger integrates caller-scheduled intake, fuel and exhaust
mass/enthalpy on absolute time and remains disconnected from valve/injector physics
and accepted cylinder steps. Request032 also now has a post-run history auditor for
source-issued mixture phase packets and exact component/energy ledgers; it cannot
integrate a changing-composition vessel. Both increments have deferred contracts,
and mixture-history is included in the Nurion plan only. No local scientific tests
or calculations were performed; rebuild the stale source archive before staging.

Current continuation (2026-10-30): the facility-monitoring API now includes an
closed-form first-order response to piecewise-linear concentration input and passes its
issued, source-bound indication directly into the existing sampled alarm. An
analytic ramp/hold and source/evidence alignment contract is deferred under the
existing `facility-protection` profile. No local scientific tests or model runs
were performed. Dryad bare-grant parsing and receipt inventory handling were
corrected; its O2-chamber attachments remain inaccessible to the public client
(HTTP 401), so no observations were acquired. Full objective remains active.


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

The open Brayton turbine-map composition now has a separate evidence-bound shaft
power ledger: caller-supplied mechanical loss is applied after the retained
air-flow-scaled gas-path balance, then caller-supplied generator efficiency yields
electrical output. The immutable result recomputes all terms from its map-bound
cycle and rejects shaft deficits. Its existing deferred hydrogen-engine contract
now covers this conversion and guard; no local thermodynamic test was run.

The facility concentration-alarm protection contract now explicitly replays an
accepted voted event through the scheduled callback and asserts that callback
completion does not imply a physical actuator mode change. Sensor evidence and
declared delay remain bound to the original same-clock 2oo3 transition. This
strengthens the deferred `facility-concentration-alarm` case only; no sensor
reliability, actuator dynamics, or safety integrity claim is introduced, and the
case has not been executed.
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

## Local continuation — 2026-10-30 (eigenstrain result integrity)

`RadialHydrogenEigenstrainResult` now requires solver issuance and rejects changed projections through `require_current()`; direct eigenstrain mapping rejects negative and nonfinite concentrations. Its deferred case records these API contracts but remains unexecuted. The authorized Hangang CPU probe reached `clogin02` as `r1021a02`; GPU has no usable shared connection. No new connection or authentication was attempted. No scientific tests, cases, or model calculations ran. Overall coding remains active and incomplete.

The same cylinder BVP now accepts an exact-time quasi-static sequence of caller-provided pressure, temperature and hydrogen concentration profiles through `radial_hydrogen_eigenstrain_history()`. The sealed result exposes exact samples only and an integration failure retains its accepted prefix and original cause. The deferred synthetic contract was extended; no case or numerical solve was run. This adds no diffusion evolution or stress feedback.

## Hangang CPU staging and parallel-dispersion coding — 2026-10-30

The current source snapshot was transferred to Hangang through the exact shared
connection wrapper as bounded command-argument chunks. The 953-file, 3,441,510-byte
archive matched its SHA-256 before extraction into
`$HOME/h2physics/source/repository`. Python 3.12.9, NumPy, SciPy,
pytest and packaging are installed in a private virtual environment; editable
installation and package import succeeded after capping BLAS/OpenMP threads at
one. No scientific case or PBS job has run yet.

New deferred work adds caller-owned executor support for independent SLABx-LH2
source-bin snapshots, with original bin order and aligned failures, plus a
receiving-side specification for closing HyRAM plug-to-Gaussian conserved fluxes.
The HyRAM source remains rejected when its current mass gate fails; no host-side
rescaling was introduced. A source-schema review found no justified path from BAM
plate temperatures and flow labels to incident flux or cylindrical wall conditions;
the missing measurement contract is documented rather than inferred. The metadata
plan includes the BAM parser and SLAB parallel contract. A fresh source hash and
PBS array must be generated after the final local changes are synchronized.

The pure-fluid finite-separator trace now uses a one-use issuer consumed only
after the native run reaches its requested endpoint and the host balances pass.
Direct construction and dataclass replacement are added to its existing deferred
finite-transfer contract. This protects operation provenance; it does not add
mixture flash or phase-depletion events.

## Local continuation — diffusion-to-eigenstrain coupling

`h2physics.adapters.bind_cylindrical_transport_to_eigenstrain()` now joins the issued cylindrical finite-volume transport output to the exact-time quasi-static cylinder stress history. It preserves cell-center mobile concentrations and requires the caller to supply inner/outer solid concentrations at each exact time, plus explicit carrier basis, reference state, linear expansion coefficient, clock-mapping and axial-uniformity evidence. The admitted mesh must match the cylinder surfaces. One-use issuance rejects direct cloning; the binding retains both original histories and checks them for mutation. It does not treat trapped concentration as mobile, infer surface values, or add stress/diffusion feedback. A deferred synthetic bridge case is registered; it was not run.

The eigenstrain history now rejects per-sample changes to carrier, concentration basis, reference concentration, expansion coefficient or reference temperature before solving. Result freshness fingerprints the retained geometry, load, material and temperature content as well as stress arrays and object identity, closing stale-input mutation paths identified during source review. Deferred contracts cover those rejections; they remain unexecuted.

## Local continuation — AHSS 1300 data intake

The CC BY 4.0 Mendeley version-1 MS AHSS grade 1300 workbook is acquired and its file hash matches the publisher listing. `load_ahss1300_permeation()` preserves both sheets, all time/current rows, worksheet row identities, exact attachment URL, corrupted header, publisher metadata and immutable values. The current-unit label is damaged and unresolved; the data are not converted to hydrogen flux and do not support a diffusivity fit. Its deferred `fracture-fatigue` contract now builds a `Dataset` receipt offline from three explicitly staged, hash-checked raw-cache files and covers altered receipt/listing/workbook bytes and stale observation mutation. It has not been run. Static Ruff, source inventory, relative-import, document-link and public-tree checks pass. Hangang CPU connectivity is confirmed, but no case was submitted or executed; the full coding and scientific qualification objectives remain incomplete.

The reader also keeps the corrupted current header verbatim for audit. The original first sheet contains a header row followed by 1,260 observations; the second sheet contains 600 observations beginning in row 1. The fixture contract checks these row boundaries, exact receipt identity, observation order, immutability and source freshness. The cluster wrapper provides remote commands only, so transferring an executable source snapshot remains a separate campaign setup requirement.

The HyRAM plug-to-Gaussian transition snapshot audit and its synthetic deferred case
are listed in both Hangang and Nurion source plans. It checks provider-issued same-run
radial plane ledgers with separate mass, momentum and excess-energy closure/error
budgets; incomplete inputs are reported as incomplete. This does not validate the
physical model or the provider's data. No tests or calculations were run.

Latest local correction: Hangang job 1185904 reported that the original
`parcel-population-finite-impact-sequence` synthetic launch did not reach the ground,
so the impact owner received no event. The deferred fixture now uses lower launch
heights and faster downward velocities to produce distinct ground-event times within
the declared low-Re/low-We domain; model rules were not changed. Job 1185906's sensor
rejection outcome-return correction is also present locally. Both changes require a
fresh pinned source capture and retry; neither is verified, and neither implies
physical impact or sensor qualification.
# 2026-10-30 — PEACE alkaline stack dataset lane

Cataloged Zenodo record 10.5281/zenodo.19605474 as a non-duplicate measured
alkaline electrolysis dataset with record-level CC BY 4.0 evidence. Added a
source-token reader contract, synthetic deferred ingestion case, and rights /
schema notes. The API endpoints returned HTTP 403, but public record file links
worked: three raw runs and the description table were acquired (11,514,333 bytes).
All publisher MD5 values match and local SHA-256 receipts are recorded. Source
fields remain unmapped; the synthetic parser case is in both campaign plans and
does not provide model validation. Generated plan metadata remains stale.

The source delta also includes named immutable accepted-time mixture energy and
species inventory/port histories (mol and kg), plus solid-reaction audit-gated
trace issuance with direct failed-audit residual diagnostics. These additions
reuse existing integrations and do not promote family verification status.

## Hangang deferred-contract results — 2026-10-31

Revision `f2086cad639364c8ccca9bddd86d5f0e6d156c1e` (archive SHA `68828c63d88db6edb0ede57c170ae94ed0239de55e2bc8f8bebae34445cafc80`, manifest SHA `a006207f9e45c8e54d543ffdb87f98c325d5c83a62023ac216cee8f2a55fb2df`) has these deferred contract passes: 1185847, 1185853, 1185854, 1185858, 1185863, 1185864, 1185866, 1185867, 1185868, 1185870, 1185871, 1185873, 1185885, and 1185888. These are synthetic/API or data-ingestion contracts only and do not constitute physical-model validation.

Cases requiring a source fix before retry: 1185848 adsorption issuance; 1185860 immutable carrier binding assertion; 1185874 oxygen interval slicing; 1185876/77 staged-turbine native phase fixture; 1185884 Brayton native phase fixture; 1185886 engine fixture mechanism metadata. Job 1185889 failed because its sensor calibration entrypoint omitted an explicit `ValidationOutcome`; both calibration deferred entrypoints now return named outcome metrics after their existing assertions. This local correction is unverified pending retry. Initial jobs 1185822/23/25/26/27/28/30/31 failed before case entry due the profile interpreter path; a scoped symlink now resolves that path to verified Python 3.12.9. Rejected QOS submissions received no job IDs. Full details are in `docs/HANGANG_EXECUTION.md`.

Additional f2086 deferred-contract outcomes are recorded in `docs/HANGANG_EXECUTION.md`: passes 1185847, 1185853, 1185854, 1185858, 1185863, 1185864, 1185866, 1185867, 1185868, 1185870, 1185871, 1185873, 1185885, and 1185888; contract/fixture failures 1185848, 1185860, 1185874, 1185876/77, 1185884, 1185886, 1185889, 1185892/93, and 1185895/96. The latter do not establish physical validation. Launcher failures 1185822/23/25/26/27/28/30/31 are separate from these case outcomes.

PBS array jobs 1185918/1185919 exposed a pinned-script import omission: the risk
helper imported a sibling script module, but generated workers placed only pinned
`/src` on `PYTHONPATH`. The generator now keeps pinned `/src` first and adds pinned
`/scripts` before inherited entries. The existing deferred generator contract
checks this order. A fresh capture/retry is pending; these launcher failures and
static contract changes do not qualify the risk model.

Local follow-up API corrections: the porous-reservoir schedule now enforces
well-flow/time length equality while leaving initial-pressure length to the selected
geometry check in `run()`; positive pressure and bounds checks remain. The 1185901
fixture shape is therefore admissible without weakening strict schedule validation.
The fuel-cell exchange currentness seal now fingerprints its retained immutable
mapping proxies directly; fresh temporary dict copies had changed mapping identity
on every seal check. A failure was reported for 1185898, but the available remote
attempt record currently has no outcome and remains marked running. These source
corrections are unverified pending fresh capture and retry.
## GrInHy2 producer-linkage audit — 2026-10-31

Static review found that the admitted GrInHy2 CSV contains time and four plant
boundary flow channels (`Nm³/h`) only. Current, electrical power, cell/stack
temperature, stack-plane identity and the normal-volume reference state are
absent or unresolved. As a result the data cannot identify an electrolysis
parameter or provide a defensible forcing profile for the existing producer
model. No conversion, fit, interpolation across the 8,205 s gap, or extrapolation
was added. Added deferred Hangang case
`grinhy2-electrolyzer-coupling-evidence-gap` alongside ingestion, plus explicit
scope in the source README and data qualification/inventory. Plan discovery is
automatic through the already registered `validation.cases.grinhy2_ingest`
module. Neither case was run locally or remotely in this change.

## PEACE alkaline source-to-stack bridge — 2026-10-31

The acquired source-bound PEACE projection contains same-row publisher-described
current, total voltage and temperature channels with declared units. Added
`h2physics.adapters.bind_peace_alkaline_electrolysis_profile()` to pass complete
observed rows into the existing `HydrogenStack.evaluate()` API, retain measured
voltage residuals, and record rows omitted for missing channels. The caller
must declare the electrical-scope and temperature mapping evidence and provide
compatible active area and series-cell count. The returned trace retains the
exact model owner and both source hashes, and rechecks by reproducing results.
No model parameter fit, flow conversion, temporal
interpolation, or extrapolation is performed. Added deferred Hangang case
`peace-alkaline-existing-stack-model-bridge` using synthetic source-shaped files;
the existing plan discovers it through `validation.cases.peace_alkaline_ingest`.
Documentation/API and data inventory were updated. No local tests/calculations
or raw publisher-file model evaluations were run.

## Dryad PEM system dataset access-gap contract — 2026-10-31

Revisited the primary Dryad page for DOI `10.5061/dryad.8931zcs64`. It describes
a 60 kW NEL C-Series PEM system and synchronized experimental power/H2-flow
channels, as well as simulation outputs; the record lists a README and
72.10 MB archive. Dryad's reuse guidance states CC0 1.0. API downloads returned
HTTP 401 and the current public file-stream links HTTP 403, so no payload bytes,
payload hashes, exact units or file schema were acquired. Updated the provenance
record and qualification/inventory docs with this dated access gap. Added
`pem-grid-application-data-access-gap`, a metadata-only deferred Hangang case
discovered by the existing plan. It does not create a reader or assert process
validation. No tests, calculations or attachment conversion were performed.


## Hangang current4 follow-up — 2026-10-31

All outcomes below use immutable source revision `26845bb9815963b5ce0a337ffcfd9e9bca8afbc7` (manifest `3755f73fada945b8e17322fc126ccf3669dc456ac623413ae86c1496ba280a23`); they are deferred synthetic/source-ingestion contracts, not physical validation.

- 1186427 `cantera-finite-flow-catalytic-cstr`: failed before integration. Cantera 3.2 exposed `ThermoPhase.T` as read-only; assigning `surface.T = reactor.T` raised `AttributeError`, wrapped as `CatalyticSurfaceError`. The source now reads `native_surface.phase` to refresh the interface state; retry is pending a fresh pin.
- 1186441 `hydrogen-pipeline-lumped-isothermal-linepack`: passed. Maximum mass residual was `5.662137425588298e-15 kg`. This covers an ideal-gas, fixed-temperature, fixed-composition lumped ledger only; no spatial transient, real-gas correction, heat balance, or experimental qualification.
- 1186447 `segmented-isothermal-gas-pipe-inventory-network`: failed at the case’s local direction assertion because intercell Darcy flow outweighed the boundary rates. The model’s prior conservation/flow checks completed. The synthetic fixture now uses long/narrow links to make boundary forcing observable; retry awaits a new pin.
- 1186448 `hydrogen-engine-open-control-volume-forced-flow`: failed the native geometry audit. Native volume was `0.00055849860451576637 m³`, geometric volume `0.00055849860545199848 m³`, residual `-9.36232e-13 m³` versus a solver-scaled allowance of `6.58499e-13 m³` (`rtol=1e-9`, `atol=1e-13`). No public geometry tolerance was relaxed. The local adapter now integrates with 0.1x caller tolerances while preserving the original geometry gate; retry awaits a new pin.
- 1186449 `grinhy2-flow-source-ingestion`: failed before its checks because the source header did not match the reviewed six-column schema. The reader/source mapping fix separates exact source CSV headers from normalized API field names; retry awaits a new pin.
- 1186450 `h2safe-indoor-source-bound-experiment-ingestion`: passed source-bound ingestion for 2,542 rows and 24 channels from the verified CC BY 4.0 archive (`f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e`). It remains helium-surrogate ingestion; units, calibration and room/ventilation boundaries are unresolved.
- 1186452 `power-law-solubility-diffusion-boundary`: passed the synthetic interface contract, including carrier mismatch rejection and issued-result forgery/clone/mutation rejection. It qualifies no material coefficient.
- 1186461 `hydrogen-engine-native-pressure-valve-boundary`: failed the same native slider-crank volume residual as 1186448 on old revision `26845bb9815963b5ce0a337ffcfd9e9bca8afbc7`; the 0.1x solver tolerance correction is newer and awaits a fresh pin.
- 1186462 `cantera-native-fuel-cell-zero-current-boundary` failed before its first accepted sample at the fuel-cell callback-binding guard. 1186463 `hydrogen-engine-crank-angle-fuel-delivery-native-flow` repeated the old-pin geometry-gate failure. Both fixes await a new pin; neither is physical validation.

1186447/48/49 failures are source- or fixture-contract findings, not model qualification. Current4 retries are excluded until their fixes are pinned.
That intermediate queue snapshot preceded admissions 1186462 and 1186463; the later active jobs are recorded in the handoff above.

1186459 `fuel-cell-reactant-current-limit-boundary` passed the synthetic feedback-policy contract: oxygen was limiting at `1608.0888687218305 A/m²`, and current was zero at the declared reserve. This does not test Cantera integration, event localization, or control qualification. After this case the queue had four active jobs: unrelated 1186457, 1186458, 1186438 and 1186395; the remaining current4 native cylinder/CSTR/fuel-cell cases depend on known post-pin fixes.
## Hydrogen-channel measured-flow safety-source bridge — 2026-10-31

The already acquired Figshare V2 source provides a publisher-labelled flow
clock in seconds and H2 mass flow in g/s for 22 experiments under the record's
CC BY 4.0 license. Added `project_hydrogen_channel_finite_source()` to convert
only those explicitly labelled columns to a measured `IntervalMassSource`, with
caller-selected interval quadrature, location and representative H2 state.
The bridge stops at observed flow-clock endpoints, retains archive/member hashes,
and does not align sensor time or interpret filling pressure. Deferred Hangang
case `hydrogen-channel-measured-finite-source-bridge` is registered and uses the
existing offline source-fixture contract; not run here. Docs/API/qualification
inventory were updated. No local tests/calculations were performed.


## Current4 additional engine/fuel-cell admissions — 2026-10-31

1186461 `hydrogen-engine-native-pressure-valve-boundary` failed the same strict moving-volume audit as 1186448 on the old current4 pin: residual `-9.36232e-13 m³` exceeded allowance `6.58499e-13 m³` at `rtol=1e-9`, `atol=1e-13`. This predates the local 0.1x internal-tolerance adjustment and is not a second independent geometry finding. No gate was relaxed.

Jobs 1186462 and 1186463 later failed on the old current4 pin: the zero-current case hit the callback-binding guard before any accepted sample, and the crank-angle case repeated the geometry residual. The first crank-angle submission was refused with `QOSMaxSubmitJobPerUserLimit` and created no job; 1186463 is the later accepted job. Neither failure is physical validation.
# AB2 shell-temperature hydride boundary bridge — 2026-10-31

Added an evidence-gated adapter from one AB2 tank shell thermocouple to the
existing `FiniteHydrideHeatBoundary`. It requires an explicit caller mapping
identity, binds the immutable source block/file digest and clock, performs only
piecewise-linear interpolation within measured support, and rejects out-of-range
calls. Added deferred synthetic Hangang case
`ab2-shell-temperature-finite-hydride-boundary` to `source-data-ingestion`.
Raw source workbook values are not converted or fitted; shell-to-bed/bath mapping,
MFC reference conditions and pressure basis remain unresolved. No local tests or
calculations were run. A real workbook replay would require separately staging
the source workbook at its manifest hash.
# AB2 shell-temperature hydride boundary bridge — 2026-10-31

Added an evidence-gated adapter from one AB2 tank shell thermocouple to the
existing `FiniteHydrideHeatBoundary`. It requires an explicit caller mapping
identity, binds the immutable source block/file digest and clock, performs only
piecewise-linear interpolation within measured support, and rejects out-of-range
calls. Added deferred synthetic Hangang case
`ab2-shell-temperature-finite-hydride-boundary` to `source-data-ingestion`.
Raw source workbook values are not converted or fitted; shell-to-bed/bath mapping,
MFC reference conditions and pressure basis remain unresolved. No local tests or
calculations were run. A real workbook replay would require separately staging
the source workbook at its manifest hash.

## AB2 shell-temperature hydride boundary bridge — 2026-10-31

Added an evidence-gated adapter from one AB2 tank shell thermocouple to the existing `FiniteHydrideHeatBoundary`. It requires an explicit caller mapping identity, binds the immutable source block/file digest and clock, performs only piecewise-linear interpolation within measured support, and rejects out-of-range calls. Deferred synthetic Hangang case `ab2-shell-temperature-finite-hydride-boundary` is registered under `source-data-ingestion`. Source values are not converted or fitted; shell-to-bed/bath mapping, MFC reference conditions and pressure basis remain unresolved. No local tests/calculations were run. Real workbook replay requires staging a source workbook at its manifest hash.

## Cryogenic MOF Langmuir diagnostic bridge — 2026-10-31

Added `compare_cryo_mof_with_langmuir()` to connect exact rows from an acquired Etalab-2.0 H2 isotherm file at 77/87 K to the existing `ExtendedLangmuirIsotherm`. It requires caller evidence for absolute-pressure interpretation, absolute-uptake and material-mass basis, and material identity; no fitting, interpolation or extrapolation is performed. The 20 K normalized-pressure/reference-volume branch is rejected. Hangang case `cryo-mof-source-to-langmuir-diagnostic-bridge` is registered under `source-data-ingestion` and uses synthetic source bytes only. No local tests/calculations were run; it is not experimental validation.

## X044QK finite safety-source projection — 2026-10-31

Added a source-row adapter from the admitted DataverseNO CC0 matrix to the existing `IntervalMassSource`. It uses only source-reported average pressure-derived MFR and release duration, preserving the matrix row/hash. The caller must provide source location, gas state, clock placement and distinct evidence for accepting pressure-derived MFR and duration-to-clock mapping. The result is one constant-mean-rate bin: no pressure conversion, nozzle recalculation, transient reconstruction, peak-flow use or ignition/dispersion validation. Hangang case `x044qk-average-flow-finite-hydrogen-source-bridge` is registered under `source-data-ingestion` and uses the staged matrix with synthetic location/state. No local tests/calculations were run.

## BAM plate-temperature observation comparator — 2026-10-31

Added `compare_bam_plate_temperature_to_target()` for an exact BAM FRP thermocouple channel and an existing `ThermalTargetTrace`. The caller must evidence absolute-Celsius interpretation, sensor-to-target mapping, clock alignment and linear interpolation between retained model output samples. The sealed result retains the rights-bearing unit projection, archive/member hashes, raw tokens/rows and exact target trace; freshness rechecks both owners. It does not infer heat flux, fit target properties or qualify fire/thermal physics. Hangang case `bam-fire-plate-temperature-thermal-target-observation-bridge` uses the staged CC BY 4.0 archive/metadata with a synthetic target trace. No local tests/calculations were run.

## BAM Hangang staging receipt — 2026-10-31

The parent reports that required-command staging (`run.sh`) completed and both remote source-file checks passed: `H2_Data.zip`, 75,221,648 bytes, SHA-256 `c4e199a20960174845f27dbbb6521b65c797740ba3f503463ee96073cf2d8bed`; `zenodo-record.json`, 5,232 bytes, SHA-256 `646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0`. This unblocks pinning the BAM plate-temperature observation contract. No tests or model calculations were run here.

## BAM measured-origin admission correction — 2026-10-31

The deferred `bam-fire-plate-temperature-thermal-target-observation-bridge` reconstructs its `Dataset.origin` using the exact repository classification string `"measured"` required by `_check_dataset`; it no longer forwards the catalog seed value. The audit also corrected the reader's metadata SHA-256 constant to match the captured Zenodo response and manifest (`646af606bdb6fd16a982dcf8b1b89dcdfa4ec16d11c0d804ff40ff265a3852f0`), replacing a transcription typo. DOI, open-access status, CC BY 4.0 and attachment receipts remain enforced. The case is registered in `validation/hangang_plan.py` for the next pin (current5k-ready). No local tests/calculations were run.

## SOE fault-operation data evidence gap — 2026-10-31

Catalog audit selected Zenodo 10.5281/zenodo.10648884 as a high-value but currently unusable candidate: CC BY 4.0, eleven files / 1,092,175,741 B listed, zero acquired. No file-to-fault map, MAT variable schema, units, synchronized clock, flow reference basis, sensor mapping or fault onset semantics are reviewed. Added manifest gap fields, `docs/SOE_FAULT_OPERATION_DATA.md`, a prepared not-sent author/repository request, and metadata-only Hangang case `soe-fault-operation-data-schema-gap`. Candidate existing APIs are HydrogenStack and process_monitoring; no source/model bridge is admitted until evidence resolves the mapping. No tests/calculations were run.

## Brookite photocatalysis AQY-to-model evidence gap — 2026-10-31

Audited the existing small, acquired CC BY 4.0 TiO2 photocatalytic-H2 dataset against `PhotonYield`/`photon_hydrogen_rate`. Existing reader maps only source-declared wavelength/AQY percent and cited specific-rate units. The AQY interpretation still lacks row-matched incident/absorbed electron-equivalent basis and `PhotonSupply`, geometry, catalyst, medium, T/P and independent gas-collection evidence. Added explicit gap fields to the source manifest, request `requests/photocatalysis_aqy_condition_mapping.md` (prepared, not sent), and metadata-only Hangang contract `tio2-brookite-aqy-model-link-evidence-gap`. No AQY is reinterpreted as a model input; no fit/calculation or model result is claimed.

## Hydrogen engine HDF5 model-linkage gap — 2026-10-31

Reviewed the eight acquired CC BY 4.0 TUdatalib attachments (8,828,090 bytes) against existing engine pressure/thermal APIs. The HDF5 metadata inspection is structure-only. Figure fields lack critical pressure-sensor location/crank-angle origin, flame-map quantity/spatial transform, temperature-difference reference, heat-flux plane/sample mapping, aggregation/uncertainty and condition/run semantics; component-level rights review is also open. Added source manifest gap fields, detailed gap note, prepared not-sent author request, and deferred Hangang metadata-only case `hydrogen-engine-figure-data-model-link-gap`. No values were assigned to engine/thermal models. No tests/calculations were run.

## Dark-fermentation hydrogen-process linkage gap — 2026-10-31

Audited the acquired Mendeley v2 CC BY 4.0 workbook (165,296 B) and existing source reader against native `QsdSanAdm1Digester`. Workbook observations and source algebra are preserved, but BP lacks reference P/T and wet/dry gas basis; H2 fractions lack denominator/species/sampling alignment; Duration clock/event and cadence are unresolved; reactor volumes, initial feed/COD/biomass and R1/R2/R3 independence are not established. Added manifest gap fields, `docs/DARK_FERMENTATION_MODEL_LINK_GAP.md`, a prepared not-sent author request, and metadata-only Hangang case `dark-fermentation-h2-process-model-link-gap`. No source values are converted or fitted. No tests/calculations were run.

## Nanoporous-carbon H2 chemisorption model-link gap — 2026-10-31

Audited the 26,374-byte acquired Mendeley v1 CC BY 4.0 carbon characterization dataset. Only `total_chemisorption_isotherms.csv` is an H2 table (record says 973 K); the other 18 CSVs concern CO2/N2 physisorption at different temperatures. The H2 table schema labels pressure torr and uptake STP cm3/g but does not resolve STP reference, pressure basis, uptake definition or material columns, blocking the existing mol/kg `ExtendedLangmuirIsotherm` basis. Added source manifest gap fields, focused data-link manual, prepared not-sent author request, and metadata-only Hangang case `carbon-h2-chemisorption-model-link-gap`. No conversion, fit, source-row evaluation, tests or calculations were run.

## Radial hydrogen diffusion shell API — 2026-10-31

Added `HydrogenDiffusionShell` as a typed public façade for spherical and finite-length cylindrical shell geometry over the existing `DiffusionDomain`. It constructs the matching finite-volume mesh, forwards caller-owned material/trap/boundary parameters, and documents the extensive mol and mol/s result basis. Added deferred Hangang case `radial-hydrogen-diffusion-shell-api` to the already registered `validation.cases.material_transport` module; the plan uses the existing `material-transport` profile. Catalog and `docs/MATERIAL_TRANSPORT.md` now record the API, radial-only scope and unverified status. No tests or local calculations were run; Hangang execution is pending.

## Alkaline electrolysis bubble observation linkage gap — 2026-10-31

Reviewed Mendeley Data v2 DOI `10.17632/r6np4f7gmf.2`. The primary record declares CC BY 4.0 and describes raw data for figures plus videos, but exposes no file rows/README in the accessible response; the Mendeley public metadata API returned HTTP 401. No payload was acquired. Added `research/data/alkaline-bubble-observations.toml`, inventory/qualification entries, a focused model-link gap note, and Hangang case `alkaline-bubble-electrolysis-model-link-gap` registered in `validation/hangang_plan.py`. Existing `HydrogenStack` has no bubble closure and the current source metadata cannot establish quantitative observation-to-model mapping. No tests/calculations were run.

## Simulated metal-hydride PCT source/model gap — 2026-10-31

Read-only workbook-header inspection for the five acquired Mendeley CC BY 4.0 PCT workbooks found pressure columns labeled bar, temperature columns labeled °C/K, and concentration labels NL/kg for three materials and wt% for two, on absorption/desorption sheets. The reviewed schema does not resolve pressure basis, NL/kg reference/denominator, wt% loading basis, or generating-model lineage. Added manifest evidence requirements, `docs/HYDRIDE_PCT_MODEL_LINK_GAP.md`, and Hangang case `hydride-pct-simulated-equilibrium-model-link-gap` via the `source-data-ingestion` profile. No rows were converted/fitted; no local test/calculation was run. A future comparison is source regression only unless an independent dataset is established.

### Hangang current5n/current5o contract status (2026-10-31)

Pinned current5n source revision `d8ab381196e6b52dbde46f6c484566b0ac8d8070` (archive SHA-256 `2f692461127dde9c1af05f773f85b41c090db559a10f3047d8800bc574d131c9`, manifest SHA-256 `ab6cabfe74036b4f124086379d038ae9984f7f197ebc5ee31e9575b608e5b7f6`, 1,142 entries) was uploaded and remotely verified. Its eight deferred contracts were submitted as singletons: 1186645 BAM thermal observation, 1186646 solid heat utility, 1186647 engine data-link gap, 1186652 solid H2 finite-source handoff, 1186653 acoustic-to-CoolProp diagnostic, 1186662 diffusion-to-finite-source handoff, 1186663 SOE data-schema gap, and 1186680 TiO2 AQY evidence gap. Contract passes: 1186646, 1186647, 1186652, 1186653, 1186663, 1186680. Failures requiring a new pin: 1186645 exposed that the publisher's `Number of channels` excludes the leading `Time [s]` coordinate; the parser now counts non-time columns. 1186662 exposed a fixture API mismatch: `DiffusionSlab.simulate` requires a boundary callback or explicit `PowerLawSolubilityBoundary`; its fixture now wraps the unchanged fixed-flux `SlabBoundary` in a callback. These are deferred software-contract outcomes, not experimental or physical-model qualification.

Pinned current5o revision `f338dbdce0f076b819d66195da9f716bfc64cb70` (archive SHA-256 `6caefff56acb0fff8220b85d30edd771f9f4a5847fcf2417869e4a70901ff019`, manifest SHA-256 `b0c9ef4633a6730000e84ee243d09c448d0b23ce9abc0e9b5b58bbc983d01369`, 1,145 entries) passed remote manifest verification with zero forbidden raw/cache members. The dark-fermentation metadata gap passed as 1186681. Acoustic and SOE gap replays were submitted as 1186684 and 1186685; both were accepted and pending at last report. The later carbon-H2 gap was added after this pin and is deferred to the next snapshot.

## Geological adsorption v2 archive/rights audit and Hangang registration — 2026-10-31

Confirmed Zenodo API latest pointer resolves DOI `10.5281/zenodo.22305898` (publication 2026-09-14) with open access and `license=cc-by-4.0`; the record's separate `rights` field is null. README says to use the record license and gives article/dataset citation guidance; the included Liberation Serif font carries an OFL-1.1 file. v2 archive is 5,063,714 B, publisher MD5 matches, local SHA-256 `40c16cca5099e2c69dc44aceb43300854307b3a6c8351c43013afc9967e60dc6`; all 81 internal SHA-256 entries match, and the authoritative COx source workbook hash matches README. No archive code was run. Existing v2 signed-excess loader/model binding case `geological-adsorption-excess-loader` is now registered via the `adsorption-data` profile in the Hangang plan; no duplicate model adapter was added. Updated v2 provenance manifest with rights/checksum observations and marked v1 inventory row historical/superseded. No local tests or scientific calculations were run.
# Bath cryokinetics source bridge (2026-10-31)

Added source-hash-bound Bath kinetic workbook reader and deferred case
`bath-cryo-kinetics-source-schema-gap` (profile `source-data-ingestion`). The case
is registered in `validation/hangang_plan.py`. Two workbooks only are staged in
ignored raw storage; their SHA-256 values and file scope are in
`research/data/bath-cryo-kinetics.toml`. The reader preserves source units and
raw observations. It does not calibrate, convert excess uptake, or fit a model.
The existing finite adsorption dynamics API cannot be coupled until the kinetic
specimen dry mass and sample/isotherm mapping are evidenced. No local tests or
calculations were run; the Hangang contract is pending.

# Dryad grid-connected PEM evidence audit (2026-10-31)

Rechecked the primary Dryad page for DOI `10.5061/dryad.8931zcs64`. Its embedded
README names a common timestamp and synchronized command, stack/SMPS/chiller/
subsystem power, and two hydrogen-flow trace files. The page still lists only a
small README and a 72.10 MB simulation archive; its current README stream returns
HTTP 403 and the API attachment path was previously HTTP 401. No bytes or payload
hashes are available. Experimental units, sampling support, flow reference
basis, uncertainty, calibration, and sensor/system boundary mapping remain
unknown; the separate simulation inputs' MW convention is not transferred to
experimental traces. Existing case `pem-grid-application-data-access-gap` now
records these exact boundaries. No reader/model bridge, data fit, local test, or
calculation was performed.


### Follow-on Hangang pins and contract outcomes (2026-10-31)

Current5q is pinned at revision `edc40f34663dd3bc92a96d7751cbc5e44455c53d` (manifest SHA-256 `5e0dd7da017411f1badf9a4f0b8c1dcf71f50bf34c8f14bb75d917a138b7d622`, 1,159 entries; archive SHA-256 `aac1f1212070a62bd30df995ee75f497d740081385c5324a78c7295b7d791188`). Its remote manifest verified. It includes the PCT metadata-gap, Cantera gas-volume handoff, alkaline-bubble gap and carbon-H2 gap. PCT (metadata only), alkaline and carbon submissions were QOS-rejected with no job IDs. Cantera gas-volume job 1186734 entered the case environment and failed before model work because `CanteraFrozenGasProperties` read `_composition` before initialization; an adapter fix is assigned to a later pin. No physics result was produced.

Current5p's `radial-hydrogen-diffusion-shell-api` case 1186719 failed its signed face-ledger assertion: for the declared left-to-right concentration gradient both left inflow and right outflow are positive in the native face convention. The case assertion and `MATERIAL_TRANSPORT.md` explanation were corrected; this is a fixture expectation correction, not a model failure. It is included in the current5r pin, revision `5ce6586456308b8492526c0836573170fa85088b` (1,164 entries; manifest SHA `491160bc4b20ad88121c0263da06aea595c946bdf2f049f53e89c96652be46bd`; archive SHA `bb202bfefe1c36510ea85a4ae213f6140f1ec8dee1335038cd10ee6784af2bc1`).

Current5r also registers the geological adsorption case and membrane adapter route, but its snapshot predates the membrane case module. Current5s, revision `ed74d1f46816451af578800ebcc0aa1da44c4b7b` (1,165 entries; manifest SHA `731600e9e11e6985512d2a285fc54603c92b2064914316fe3bc1ee58cbc73770`; archive SHA `193d1bbe0c85aaeae99722432c05372698120cb68f07a644ed82c4e0f93dda12`), includes membrane and Bath case/plan modules, but predates the complete Bath documentation update and the Cantera gas-property constructor fix. The full Bath source lane has 11 metadata/code/docs paths; raw payload remains ignored and excluded from archives. Complete lane and Cantera fixes are queued for current5t.
# MHC logger temperature observation diagnostic (2026-10-31)

Added `compare_mhc_temperature_to_compressor_bed` for a checksum-bound raw
temperature channel versus the existing native finite hydride-compressor trace.
It requires explicit sensor-to-bed, clock-alignment, and interpolation evidence,
retains source row identities, rejects reconstructed/calibration exports, and
forbids extrapolation. It produces diagnostic temperature residuals only.
Reader blocks now carry an unforgeable one-use archive-verification issuer;
test/fixture workbook snapshots remain explicitly unverified and are rejected by
the comparator. Hangang case `mhc-compressor-temperature-observation-contract`
opens a three-row workbook window through the verified archive reader and rejects
block cloning/direct construction; physical comparison remains evidence-gated.
No local tests or calculations were run.

# USN unignited measured flow to finite safety source (2026-10-31)

Added `project_pressure_peaking_flow_to_finite_source` for selected nonnegative
mass-flow windows from the pinned USN SIGMA experiment-00003 MAT file. It uses
the existing reader's measured kg/s and exact recorder s clock, caller-selected
quadrature, and explicit release-plane/representative-H2-state evidence.
Negative signed meter flow and missing values reject the projection; no pressure
channel, clipping, absolute-value transform, fit, or pressure-peaking comparison
is included. Hangang case `usn-unignited-measured-flow-finite-source-contract`
checks manifest/hash/API only. No local tests or calculations were run.

# Pump process connection source-only correction (2026-10-31)

Static inspection found the `pump_operation_to_process_connections` result
issuance block unreachable after its helper return. The adapter now issues and
seals the `ConnectionTransfer` receipt inside the public function. Accepted
receiver absolute pressure remains recorded per sample and covered by the trace
digest. The source fix and `pump-operation-shaft-connection-boundary` deferred
case require inclusion in a fresh Hangang pin; no local test or calculation
validates this change yet.

# HyRAM radiation to radial wall composition (2026-10-31)

Added `run_jet_radiation_radial_wall` to bind one accepted HyRAM receiver flux
to the existing radial heat target over the source's evidenced steady window.
The caller provides point index, location frame inherited from the field,
surface-projection factor/evidence, absorptivity, wall geometry, and uniform
circumference evidence. Hangang case
`jet-radiation-radial-wall-source-handoff` is registered under
`jet-fire-radiation`; execution and physical qualification remain pending a
fresh immutable pin.

# ELVHYS LH2 rupture model-link gap audit (2026-10-31)

Audited acquired DataverseNO ELVHYS v1.0 (DOI 10.18710/M5LOLM, CC0-1.0; 42/133
files, 534,609,893 B). Existing source reader preserves recorder-specific clocks
and signed waveforms. Current data do not provide rupture synchronization,
calibrated pressure response/baseline and station geometry, or tube-side initial
phase/composition/inventory. Missing D4.8 station mapping also blocks a sensor
operator. Added a focused evidence-gap manifest, `docs/ELVHYS_MODEL_LINK_GAP.md`,
prepared not-sent request, and Hangang case
`elvhys-lh2-rupture-model-link-evidence-gap`. No source values were converted or
compared; no local tests/calculations were run.

# USN source-window edge qualification (2026-10-31)

Updated Hangang case `usn-unignited-measured-flow-finite-source-contract` to
load the pinned MAT file through `load_pressure_mat`, then find actual positive
and negative measured SIGMA row pairs plus a valid triplet. The Hangang plan
injects `raw_data_root=/scratch/CLUSTER_USER/h2physics-source-attachments` only for
this case; the manifest relative path resolves to
`pressure-unignited/1/HTE242USN_00003_READ190621.mat`. The staged receipt is
37,466,494 bytes, SHA-256
`f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0`. The case
checks positive measured interval bins, negative-flow rejection, and
midpoint/non-row-aligned endpoint rejection. A synthetic thermodynamic
state/location is used only as a clearly labelled API fixture; it is not an
experiment mapping or physical calculation. The raw root is absent from the
local/default plan. Verification is pending for the next Hangang capture; 5z
predates this staged receipt. No local tests were run.


Finite relief withdrawal → finite-source adapter and deferred Hangang contract are implemented as source changes. Case `relief-withdrawal-finite-source-handoff` is registered in the existing `finite-relief-lift` profile; it is not yet execution evidence.

Pool-fire receiver radiation → radial wall composition and shared HyRAM/pool-fire radial-wall core are source-complete. `pool-fire-radial-wall-handoff` is registered under the existing `pool-fire` Hangang profile and awaits cluster execution; it is not validation evidence.

Elastic pressure-energy fragment ceiling → conditional flight adapter is source-complete. Deferred case `elastic-bound-fragment-flight-handoff` is registered under the existing provider-free `fragment-trajectory` profile; cluster execution remains pending.

HELPR failure initiation → elastic fragment ceiling → conditional fragment flight source adapter is implemented. Case `vessel-failure-fragment-flight-handoff` is discoverable in the existing `fracture-fatigue` profile; Hangang validation remains pending.

Finite hydride → HELPR loading-history projection is source-complete. Case `finite-hydride-vessel-failure-history-handoff` is discoverable under the existing `finite-hydride` profile. It requires explicit shell temperature rows and geometry evidence and never treats bed temperature as wall temperature. Hangang validation is pending; no local tests/calculations were run.

PV-electrolysis → real-fluid hydrogen-compressor inlet boundary is implemented in source with case `pv-electrolysis-real-fluid-compressor-inlet-handoff` under the existing `pv-electrolysis` profile. Package export and case-module discovery through `electrochemical_hydrogen_handoff` are now present in the shared tree; runtime validation remains deferred.

Synchronized Cantera fuel-cell coolant ledger → shared `HeatDuty` projection is source-complete. Case `cantera-fuel-cell-coolant-heat-duty-handoff` is added to the existing `fuel-cell-native` case module/profile; it remains unvalidated pending Hangang.

USN ignited release data now has a measured-SIGMA-flow source adapter and deferred case `usn-ignited-measured-flow-finite-source-contract`. The shared MATLAB v5 decoder is reused by both ignited and unignited pressure-peaking readers. The case expects the 40,666,968-byte MAT file at the Hangang source-attachment root with SHA-256 `3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4`. It checks the explicit flow-to-`IntervalMassSource` boundary with synthetic state/location placeholders. The measured source's pressure/ignition comparison remains blocked by unresolved recorder clocks, sensor interpretation/calibration, and experiment release-state mapping. No local tests/calculations were run.

PV/PEM dispatch archive review now records the exact boundary for case `pv-pem-dispatch-figure-output-model-linkage-gap`. The 47,443-byte CC BY 4.0 source ZIP contains manuscript figure reconstructions and dispatch outputs, not a measured PV/PEM boundary schedule. Since it lacks the measured irradiance, PV array/cell and stack state inputs required by `PVElectrolysis`, no source-to-model values are inferred. The metadata-only case is registered for Hangang; no model calculations or local tests were run.

Dryad hypoxia-chamber record `10.5061/dryad.t1g1jwtg9` was reviewed as a possible measured gas-O2 observation source for the existing oxygen-deficiency boundary. The primary record describes a CC0 workbook with ten sheets, including gas-phase O2 response, inlet oxygen/flow patterns, temperatures and probe delay. The publisher file downloads currently have no acquired bytes (captured HTTP 401), so no row-level schema or inlet-flow reference basis is available. Metadata-only Hangang case `oxygen-hypoxia-chamber-gas-transfer-model-link-gap` is registered; it makes no model calculation and keeps liquid oxygen transfer outside the current API. No local tests/calculations were run.

USN carpark unignited data received a metadata-only HDF5 structure audit for `Exp03.mat` and case `usn-carpark-unignited-fds-boundary-evidence-gap`. The exact MAT hash is retained in the source manifest. MFM metadata identifies mass flow in g/s; sensor metadata identifies `sec` and `%vol`, but MFM source time lacks a declared unit/origin, recorder synchronization is unknown, and sensor position units/frame plus release expansion state remain unresolved. The file-handling guide is not acquired. Case and notes are registered; no MAT measurement arrays, local tests, or FDS calculations were run.

## Adsorption product to H2 linepack boundary (2026-10-31)

Added `charge_linepack_from_adsorption_product` to connect an accepted finite
adsorption-vessel H2 delivery receipt to the existing lumped ideal-H2 pipeline
linepack. The caller maps the delivery interval onto the pipe clock and declares
the product species basis and transfer-boundary evidence; source averaging
time, linepack clock and integrated product mass are checked. The adapter adds
no purification, compression, or flow-profile model. Deferred case
`adsorption-product-h2-linepack-charge-handoff` uses authored fixtures and is
registered through the existing `finite-adsorption-vessel` case module. Hangang
execution is pending. No local tests/calculations were run.

## Hangang recovery and current parallel lanes (2026-10-31)

A remotely manifest-verified 5af archive (1,194 entries; zero forbidden
members) could not reach qsub: the generated plan failed on an unclosed tuple
in `validation/cases/finite_relief_lift.py`. That source syntax defect is now
corrected; the failed generator produced no job ID, and no execution is claimed.
A fresh wrapper queue check reports one PENDING and four unrelated RUNNING jobs;
no H2 job is active, so the account is at its observed five-job limit and no
additional submission is being retried until capacity changes. A new source
capture is being prepared with the syntax repair, exact USN ignited recorder
schema, PV-electrolysis/compressor contract, adsorption-product/linepack
contract, coolant-heat handoff, and metadata-only PV/PEM and hypoxia linkage
gaps. Those case registrations are being checked before transfer. No local
scientific tests or calculations were run. Current catalog classification
is 80 families: 19 implemented, 37 native-adapter-verified, and 24
implemented-unverified (56/80, 70% stronger-status share); this is not an
overall programme-completion percentage or independent physical validation.

## Adsorption outlet to finite-hydride inlet (2026-10-31)

Added `bind_adsorption_to_finite_hydride` as a composition of the accepted
`AdsorptionDynamicsTrace` H2 outlet ledger and the existing finite-hydride gas
port. It preserves the original interval grid, checks H2 molar-mass compatibility
and per-bin state enthalpy closure, and requires caller evidence for clock
alignment, hydraulic transfer, and state projection. Case
`adsorption-to-finite-hydride-gas-port-handoff` is registered under
`finite-hydride`; public API exports and discovery were added. This is a
synthetic software contract only; no local tests or calculations were run.

The adsorption-to-finite-hydride bridge was tightened before pinning: every
caller-supplied inlet ThermoState must match the exact accepted source-bin
pressure and temperature. This rejects unsupported state changes instead of
assuming an unmodeled pressure or thermal transfer. The deferred case and
focused guide record this boundary; no local tests/calculations were run.

## DataverseNO large-scale explosion linkage gap

Registered metadata-only Hangang case large-scale-h2-explosion-fds-observation-link-gap under source-data-ingestion. The primary v1.0 record declares CC0-1.0 and lists 59 public files (96,861,179,314 B); the selected 6.6 KB README and 20.7 KB results workbook remain unacquired because the official file page returned HTTP 403. No alternate download route was attempted. The manifest pins publisher file IDs and MD5 values; docs state that raw file schema, release boundary, synchronized clock, sensor location/calibration and test mapping are still missing. No local tests/calculations or model comparisons were run.

## Residential hydrogen pilot license/boundary gap

Added source manifest `research/data/residential-h2-pilot.toml`, guide `docs/RESIDENTIAL_H2_PILOT_DATA_GAP.md`, and metadata-only Hangang case `residential-h2-pilot-license-and-physical-boundary-gap` under `source-data-ingestion`. The official Zenodo v1 page documents five-second PLC channels and gives the listed CSV MD5, but its License field is empty. The payload is not acquired. The note preserves explicitly listed units and identifies unresolved normal-liter reference state, pressure basis, clock/break semantics, and equipment boundary. No tests/calculations were run.

## HFCEV fleet H2 consumption observation bridge

Added a selective, source-bound reader for Zenodo 10.5281/zenodo.23477229 and adapter `select_hfcev_hydrogen_window` / `compare_hfcev_hydrogen_consumption` against an existing current `FuelCellTrace`. Four small CC BY 4.0 files (README, dictionary, field-bit map, one V001 daily CSV; total 2,383,383 B) are in gitignored raw storage with publisher MD5 and local SHA-256 receipts. The reader rechecks those source receipts and parsed-row seal. The adapter sums only publisher-attributed nonnegative counter increments, requires an adjacent previous valid counter row inside exact unique receipt-time edges to prevent overlap, and stores each row pair; source missing/backward bits are enforced. Source receipt time is not called device event time; the model comparison requires a typed endpoint-to-endpoint time map and external evidence. Hangang case `hfcev-fleet-hydrogen-consumption-model-comparator` expects the staged attachment root and exercises the source-window contract against actual rows. No local tests/calculations or model comparisons were run.

## ELVHYS 4.1 vent composition observation bridge

Added a source-hash-bound reader for DataverseNO CC0 1.0 DOI `10.18710/YGHHTR`, plus `compare_elvhys41_vent_composition` to the existing `OxygenRoomResult` boundary. Three selected files (README, metadata and Test-1 concentration CSV; 1,035,075 B total) are in gitignored raw storage. The reader preserves raw 1 Hz source-relative timestamps and H2/O2 vol% values, including negative sensor values; the comparator rejects physically inadmissible readings and requires exact model times, explicit model clock offset, and caller evidence for vent-to-region mixing, volume/state, and vol%-to-mole-fraction basis. Deferred Hangang case `elvhys41-vent-composition-source-ingest` reads the acquired source but runs no gas model. The outlet flow source remains unaquired; source documentation flags its calculated flow channel as awaiting calibration. No local tests/calculations were run.

## Reliquefier product to native separator inlet (2026-10-31)

Added `bind_reliquefier_product_to_separator` to pass an owner-issued,
collected all-liquid reliquefier product into the existing native LH2 separator
liquid callback. It preserves collected mass, state enthalpy, and exact product
window; requires clock alignment, receiver assignment, and explicit transfer
boundary evidence for pressure/thermal feasibility. No line-loss, flashing, or
conditioning solver is added. Deferred case
`reliquefier-product-native-separator-liquid-inlet-handoff` is registered under
`finite-transfer` and remains unexecuted.

## Finite separator to HELPR pressure-history bridge (2026-10-31)

Added `history_from_finite_separator` to project owner-accepted pure-H2
separator pressure/time rows into the existing HELPR vessel-history input.

## ELVHYS 4.3.2 transfer-line temperature observations (2026-10-31)

Acquired only the public CC0 README and Test-1 diode CSV (482,617 B) for DOI
10.18710/HDZLJ1; both publisher MD5 and local SHA-256 receipts are pinned in
`research/data/elvhys432-fireline.toml`. The source reader retains source time
in minutes and SD1 pipe-surface/SD2 outlet temperatures in kelvin. An optional
pointwise SD1 comparator reuses native `RadialHeatResult` surface-temperature
vectors, requires exact mapped times and caller evidence for sensor position,
pipe/domain mapping and clock alignment, and performs no flux inference or fit.
Hangang case `elvhys432-pipe-surface-temperature-source-ingest` reads source
rows only; it is registered but unexecuted. The README says the diodes were not
calibrated. The other 12 public files were not acquired. No local
tests/calculations were run.

## Current5am outcome 1187110

Job 1187110 failed before entering its scientific case because of missing `in`
syntax in `jet_radiation_radial_wall.py`. The source syntax is corrected in the
live tree; this is an entrypoint failure, not a scientific case failure. The
case was not retried on 5am and needs a fresh source pin in 5aq. No physical
result was produced.

The existing ELVHYS 4.1 reader also now rejects duplicate or non-increasing
source timestamps at ingestion, before source/model linkage. Its focused guide
records this boundary; no model changes were made.
Every row requires separate caller-mapped shell-wall temperature and external
absolute pressure plus explicit geometry, clock, pressure-basis, and source
identity evidence. HELPR now replays the native separator history projection
when checking freshness. No liquid temperature is inferred as wall temperature
and no failure criterion or release law is added. Deferred case
`finite-separator-vessel-failure-history-handoff` is registered under
`finite-transfer`; no local tests/calculations were run.

## HyRAM radiation to lumped thermal target (2026-10-31)

Added `incident_heat_history_from_hyram_radiation` to compose an accepted HyRAM
observer's steady scalar incident irradiance with the existing
`IncidentHeatHistory` and lumped thermal-target solver. Caller evidence must map
the observer to the target surface and state whether irradiance projection is
already applied; absorptivity and target properties remain caller-owned. The
case `hyram-radiation-lumped-thermal-target-handoff` is registered under
`jet-fire-conservation`; it is a synthetic interface contract only.

## Compressor to finite-hydride gas port (2026-10-31)

Added `bind_compressor_to_finite_hydride()` to map one owner-issued CoolProp
HEOS H2 compressor discharge point into the existing finite-hydride gas port.
The mapping checks the compressor discharge against a receiver-provider state,
then retains explicit clock, hydraulic-transfer and state-projection evidence
for one held-flow interval. It seals transferred mass and specific enthalpy and
replays compressor and receiver-property state mapping on each port callback.
No transient compressor,
line-flow, valve or bed model was duplicated. Deferred Hangang case
`hydrogen-compressor-finite-hydride-gas-port-handoff` is registered under
`finite-hydride`; it has not been executed or physically qualified.

## Hangang pinned-source syntax preflight (2026-10-31)

The Hangang case runner now compiles every pinned `src/h2physics/**/*.py` source
in memory before importing the selected case, and records the checked file count
in the attempt outcome. This addresses the pre-entry syntax failure in job
1187110; it does not execute the compiled module code or substitute for physical
validation. The change awaits a fresh Hangang run.

## WSKBIJ large-scale explosion summary acquisition (2026-10-31)

Acquired the official CC0 1.0 dataset's 6,753 B README and 21,165 B test-summary
workbook through individual DataverseNO file API links after the web file pages
timed out. Publisher MD5 and local SHA-256 receipts are recorded in
`research/data/large-scale-open-hydrogen-explosion.toml`; raw data remains under
the ignored `data/raw` tree. Added a standard-library OOXML reader that retains
test ID, nozzle diameter, the reported reservoir-pressure label, ignition code
and four signed pressure summary channels in source units. The source-ingestion
Hangang case verifies exact bytes and schema. These summaries are not
time-resolved measurements; absent ambient conditions, absolute sensor
coordinates, and transient histories prevent a quantitative comparison with the
current FDS boundary or an explosion-pressure model. No comparison or fit is
claimed. The WSKBIJ code and case landed after the audited 5aq capture and must
enter a later source pin; raw-file remote verification is pending.

The 5aq syntax-repaired capture itself passed its independent remote audit:
revision `ddaeb32137971c1c07cdd8fa71af03bff5c62c46`, 1,241/1,241 manifest
entries, forbidden members 0, archive size 4,208,650 B, SHA-256
`b7e532ee2dcba77681612ee456d21c53122bd2a88ecb6ab9fe91c8e55b1a18f3`, manifest
SHA-256 `eb313f0258910ab2e1c6e79421185f2b86dc0830111941415f234c0005f1bb11`.
No new job was submitted from this snapshot while the account queue was full.

## Finite-hydride desorption to mechanical compressor (2026-10-31)

Added `bind_finite_hydride_to_compressor()` to pair each accepted outward H2
bed interval with its existing HEOS mechanical-compressor result. The finite-bed
external ledgers use positive-into-bed sign; the adapter reverses each negative
desorption increment and checks positive compressor inlet mass and enthalpy.
It requires an exact accepted bed edge state, one run/window/evidence set per
interval, and a caller-supplied clock mapping. The compressor input has no time
fields, so no timestamps are inferred from run order. No compressor, bed, valve
or line-flow solver was duplicated. Deferred Hangang case
`finite-hydride-desorption-mechanical-compressor-handoff` is registered under
`finite-hydride`; it is unrun and does not establish transfer or equipment
qualification.

## Real-fluid compressor to pipeline linepack (2026-10-31)

Added `charge_linepack_from_compressor()` to transfer one existing CoolProp
HEOS H2 compressor result through the isothermal ideal-H2 linepack's native
`advance()` method. It checks compressor discharge head over the final linepack
pressure and closes compressor mass flow over the caller interval to the native
linepack mass ledger. Because the compressor discharge is real-fluid and the
linepack is fixed-temperature ideal gas, the caller must supply an exact
CoolProp state at final linepack pressure/fixed temperature and a signed thermal
conditioning-energy ledger that closes the enthalpy difference. This is an
inlet-conditioning receipt, not a stored-energy balance for the linepack.
Deferred Hangang case `hydrogen-real-fluid-compressor-linepack-charge-handoff`
is registered under `gas-compressible-pipe`; execution and pipeline
qualification remain pending.

## Hangang campaign metadata preflight finding (2026-10-31)

The source case discovery/generation path exposed a missing `dataclasses.field`
import in `src/h2physics/adapters/hfcev_fleet.py`; the import is now present.
The 5aq campaign was not submitted. Before any next submission, the pinned
tree must pass the Hangang campaign-generator metadata import/preflight so
case discovery failures do not consume a scheduler slot. No local import or
test was run.

## WSKBIJ summary-source ingestion (2026-10-31)

The selected DataverseNO files `00_Readme.txt` and `Experimental_results_.xlsx` are locally acquired and publisher MD5/local SHA-256 pinned in `research/data/large-scale-open-hydrogen-explosion.toml`. Their size is 27,918 B. The typed source reader and Hangang case preserve the reported per-test summary values. No transient pressure series, sensor coordinates, or ambient history is available in the selected summary, so no explosion/FDS model comparison is claimed. The current Hangang staging receipt confirms the remote copies by exact size, publisher MD5 and SHA-256: `00_Readme.txt` 6,753 B (MD5 `5642ccb734e8449bf52c0be83e4d0f23`, SHA-256 `cb7d4651d700cbd8da67cb69c3cec63ebabc4ffadbf6d5e1a2a38d63b622fb99`) and `Experimental_results_.xlsx` 21,165 B (MD5 `73ee4f29ca08612f46b7a37980cbe4df`, SHA-256 `5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34`).

## Wasserstoffatlas inventory reader (2026-10-31)

Added `read_hydrogen_map_inventory()` for the 181,145-byte `Bestand.csv` (1,049 rows; 20 columns). It preserves source tokens and the `Quelle` lineage field, pins exact source bytes/schema, and retains creator/DOI attribution. The record-level license says CC0 while the more specific file table names CC BY 4.0; the manifest and guide follow that file-level term. The typed inventory is intended for location/category screening only; quantity units, measurement basis and CSV geometry CRS remain unresolved, and no process or safety model validation is claimed. Deferred Hangang source-ingestion case `wasserstoffatlas-facility-inventory-source-ingest` is registered and awaiting remote hash receipt. Details: `docs/WASSERSTOFFATLAS_INVENTORY.md` and `research/data/wasserstoffatlas-hydrogen-map.toml`.

## Hangang campaign metadata preflight finding (2026-10-31)

The 5aq preparation exposed a missing `dataclasses.field` import in `src/h2physics/adapters/hfcev_fleet.py`; the import is now present. 5aq was not submitted. Require the exact next pinned tree to pass campaign-generator metadata import/preflight before scheduler submission. No local import or test was run.

## Clashach H2 micro-CT/PNM schema gate (2026-10-31)

The official Zenodo v2 record explicitly declares CC BY 4.0. Only publisher README `00_Readme.pdf` was acquired (214,983 B; MD5 `b824c43446213e7006f33f38ea116a87`; SHA-256 `afede36d45a59f967647453f06c87a67e705af0d4789c039c282d03b9d84a4d9`). It documents 29_Pore_PNM and 30_Throat_PNM as 800×800×1207, 7 μm, unsigned 16-bit labels; pore IDs 1–20,980, throat IDs 1–56,126, background/rock 0. The data files are image label volumes, not pore/throat property tables; no time/flow/pressure/saturation maps are provided. Since they do not directly parameterize `porous_reservoir`, the 6.8/5.3 MB archives were not acquired. Hangang metadata-gap case `clashach-h2-pnm-porous-reservoir-link-gap` is registered. Details: `docs/CLASHACH_H2_PNM_MODEL_LINK_GAP.md` and `research/data/clashach-h2-pnm-gap.toml`.

## Compressor discharge to finite release-source boundary (2026-10-31)

Added `bind_compressor_discharge_source()` to preserve an accepted pure-H2
CoolProp HEOS compressor outlet state while projecting a caller-declared,
time-bounded release flow into the existing `IntervalMassSource`. The adapter
checks exact owner-replayed outlet properties, explicit location/clock and
evidence IDs, one-phase gas status, and that the declared leak flow does not
exceed accepted compressor throughput. It does not infer an opening, leak law,
nozzle state, flow rate, or dispersion consequence. A deferred Hangang case
`compressor-discharge-finite-release-source-handoff` covers conservation and
rejection invariants. Package-level adapter exports are registered. The case
has not run and provides no physical qualification.

## Open hydride sorption-data candidate (2026-10-31)

Zenodo record 10.5281/zenodo.6670268 states CC BY 4.0 and describes a Pd
membrane with a Cu leak coating. Its publisher preview has time-series traces
for feed-pressure deltas and UHV H2 mass-spectrometer pressure at 85°C and
105°C. These are useful sorption observations, but their pressure-to-solid
concentration calibration is not established; the observations are not being
fit to a hydride or diffusion model. Data acquisition and a source-only reader
are being evaluated separately.

## Empa leaky-coating sorption observations (2026-10-31)

Added a typed, source-pinned reader for four selected measured Figure 4 files from Zenodo 10.5281/zenodo.6670268 (explicit CC BY 4.0), totaling 468,409 B. Each file's publisher MD5 and local SHA-256 are recorded in `research/data/leaky-coating-hydride-sorption.toml`: `Fig4a_deltap_f.txt` 56,082 B (MD5 `953db55792ad0dc329ba1d424face23e`, SHA-256 `992fcadc72fd30396c2094f2e1f573aa9a79e32bcf522bcd6ccd79dc18460cd4`); `Fig4a_pUHV.txt` 211,933 B (MD5 `221f4f79c67d7589dc5430379e9e496e`, SHA-256 `3acf2f492fe715a84de724ef059532d8ee8255680ed74d114fd7802140013f18`); `Fig4c_deltap_f.txt` 58,697 B (MD5 `cc652265e9cdf807323db95c626f1bee`, SHA-256 `8a5749998f1d57e27b67758af8116259430528e581d8becbad1d5d47ebe414f1`); `Fig4c_pUHV.txt` 141,697 B (MD5 `9075e77cfc586c19ee89b0e07327a35b`, SHA-256 `4f026f852b2ba4a5804efd7898382b0a6540f6befe23b69dbf2981b9fa83f23d`). The files carry mbar feed-pressure-change and UHV mass-spectrometer signals against seconds for 105 °C / 85 °C Pd membrane cases. The reader preserves individual source clocks/channels, including separate channel clocks and mismatched Figure 4c sampling lengths. It does not convert pressure deltas to absolute feed pressure or UHV signal to solid concentration; no kinetic/diffusion model fit or validation is claimed. Hangang ingestion case `pd-leaky-coating-sorption-source-ingest` is registered; remote staging is pending. Details: `docs/LEAKY_COATING_HYDRIDE_SORPTION.md`.

Remote staging update: `pd-leaky-coating-sorption-source-ingest` files are now promoted and verified at `/scratch/CLUSTER_USER/h2physics-source-attachments/leaky-coating-hydride-sorption/1/`. All four remote files pass exact source size, MD5 and SHA-256 checks; this supersedes the pending-transfer status in the initial lane note. The verified per-file receipts are the four mappings listed immediately above.

## Linepack withdrawal to real-fluid compressor inlet (2026-10-31)

Added `bind_linepack_compressor_inlet()` to map one accepted
`LinepackSourceHandoff` into the existing `HydrogenRealFluidCompressionInputs`.
It preserves the source interval and integrated withdrawal mass, derives the
compressor mass-flow input from that ledger, and replays the exact linepack
pressure/temperature using the caller-selected HEOS property owner. A caller
signed enthalpy-conditioning ledger and explicit clock, transfer, state,
efficiency, domain, and provider identity evidence are required. The adapter
returns inputs only; it does not run compression or add pressure-loss/thermal
conditioning physics. Deferred case `hydrogen-linepack-compressor-inlet-handoff`
is registered under `gas-compressible-pipe` and remains unrun.

The source-only public API index was regenerated with the project virtual
environment using AST parsing only: 308 modules and 1,629 public top-level
classes/functions. No package, model, native engine, validation case, or
scientific calculation was executed by the index generator.

## Linepack withdrawal to compressor inlet handoff (2026-10-31)

Added `bind_linepack_compressor_inlet()` to map one accepted
`LinepackSourceHandoff` into the existing `HydrogenRealFluidCompressionInputs`
contract. Integrated linepack withdrawal mass and interval edges determine
the compressor inlet flow; source H2 pressure/temperature are replayed by the
HEOS property owner. The caller supplies time/transfer/state/domain/efficiency
evidence and the signed enthalpy-conditioning ledger. Deferred case
`hydrogen-linepack-compressor-inlet-handoff` is registered under
`gas-compressible-pipe`. It creates compressor inputs only; no pressure-loss,
conditioning, or compressor solver is added. Case remains unrun.

## Hangang source pin 5av

The immutable source pin is revision `7e0e369ae2cda55bb2dec0f3ec8faf0ddc3115b3` (1,267 manifest entries). Archive SHA-256 is `17edb714c13a1f6e0faba9e6509f241ce3e8f698a5ebc46b9ed752e8bbe3d26f`; manifest SHA-256 is `75c68b71fdad3136cba463397f0f8a04b7bcc1988b6d7a6d7baf8c7a0a3a6182`. Hangang verification reported 1,267/1,267 entries OK, 0 mismatches, and 0 forbidden raw/binary members. The worker profile path fix uses `/scratch/CLUSTER_USER/h2physics-jobs/.venv/bin/python`; campaign metadata import succeeded from the verified remote extraction. A standalone PBS script for `pd-leaky-coating-sorption-source-ingest` was prepared at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5av-leaky-17edb714.pbs`, pinned to plan SHA `dfff30d6696ff80ce2de7fe771b4d612c8d98aa3ffa6c0654686e232b0295be1`. It was not submitted because the five-job QOS limit was full at the last queue check. No validation outcome exists for this script.

5av dispatch update: `pd-leaky-coating-sorption-source-ingest` was accepted as Hangang job `1187298`. Logs are external at `/scratch/CLUSTER_USER/h2physics-jobs/results/5av-leaky-17edb714/logs/leaky.out` and `leaky.err`. No case outcome has been read yet.

5av case result: job `1187298` entered `pd-leaky-coating-sorption-source-ingest` and failed during source parsing with `ValueError: could not convert string to float: '--'` at `leaky_coating_sorption.py:91`. No fitting/model comparison ran. The four raw source files passed their staged receipt checks. Hold retry until the reader handles the publisher's `--` field and that fix is pinned.

## Finite-hydride to fuel-cell H2 feed boundary (2026-10-31)

Added `bind_finite_hydride_fuel_cell_feed()` to project one accepted outward
bed gas-port interval into the existing fuel-cell `ThermochemicalFeed` and
`FuelCellStep` APIs. It retains exact interval edges and common clock, derives
positive H2 feed mass and outlet enthalpy from negative cumulative bed-ledger
deltas, checks H2 species/molar-mass identity, and requires a caller-declared
feed state plus signed energy-reference conditioning ledger. It returns an
amended input step only; it does not run a fuel cell, pressure regulator, or
conditioning model. Deferred case `finite-hydride-fuel-cell-hydrogen-feed-handoff`
is registered under `finite-hydride`; unrun.
### Cryogenic LH2 data ingestion and Leaky-Coating parser correction (5ay preparation)

Registered `cryo-neutron-lh2-phase-change-source-ingestion` as a deferred Hangang case and exposed the typed `load_cryo_neutron_phase_change_run` reader. The selected Mendeley CC BY 4.0 run is three files (DAQ 302,376 B, image 195,985 B, rate 905 B; total 499,266 B), with each selected member's source ZIP CRC32 and local SHA-256 pinned in the reader and `research/data/cryo-neutron-phase-change.toml`. It preserves separate DAQ/image clocks and source units/tokens; source nominal capture intervals are descriptive only. No model fit or validation claim is made because cell-to-model boundary mapping and the reported rate unit remain unresolved. Focused guide: `docs/CRYO_NEUTRON_PHASE_CHANGE_DATA.md`.

Hangang job 1187298 previously failed while parsing a first-party Leaky-Coating `--` token. This was a source-schema ingestion failure; no scientific model result was produced. The reader now retains each raw time/value token pair with its original row, represents only complete finite pairs in the numeric view, and handles both shared-time and alternating time/value channel layouts. The deferred case asserts 59,328 retained pairs, 1,785 missing-time tokens, 137 missing-value tokens, and 1,922 incomplete pairs. This correction is prepared for the next immutable pin (5ay); no local tests were run.


Static API inventory refreshed after the Cryo-Neutron reader and current integration adapters: docs/PUBLIC_API_INDEX.md now lists 310 Python modules and 1,637 public top-level classes/functions. Generation used the project virtual environment and AST parsing only; it did not import the package or run cases/calculations.

## PV electrolysis to linepack bridge (2026-10-31)

Added `charge_linepack_from_electrolysis()` and an issuer-bound receipt to transfer a selected amount from an admitted PV-electrolysis H2 batch over a separate post-production window into the existing fixed-volume isothermal linepack ledger. It enforces shared clock, transfer start/end, neutral gaseous H2/molar-mass identity, explicit source withdrawal/loss, caller-evidenced minimum source pressure and temperature bounds, and product-temperature compatibility. The source mole ledger closes initial/post-production/withdrawn/lost/retained/post-transfer stock but does not mutate or reflash the producer trace. A signed energy ledger binds to delivered mass and checks caller-integrated source transfer enthalpy, reference offset, conditioning energy and caller-declared linepack energy change; it computes no source-state trajectory, receiver internal energy or heat transfer. Deferred Hangang case `pv-electrolysis-isothermal-linepack-charge-handoff` is registered under `pv-electrolysis` and covers synthetic acceptance plus clock/reference/energy rejection. No compressor, valve, pressure-drop or pipeline-flow model was added. Code/docs are implemented-unverified; the case has not run and no local tests/imports/calculations were performed.

## Underground cavern withdrawal to compressor inlet boundary (2026-10-31)

Added `bind_underground_compressor_inlet()` to map one admitted
`UndergroundWithdrawalProjection` bin to existing HEOS compressor inputs. The
source bin's exact edges/mass determine interval-average flow; the native dry-H2
enthalpy integral and representative-state projected enthalpy remain separately
recorded. The caller supplies the energy-reference mapping and transfer/clock/
state/provider/process evidence. The adapter returns inputs only and adds no
cavern, well, pressure-loss, conditioning, or compressor model. Deferred case
`underground-cavern-compressor-inlet-handoff` is registered under
`underground-storage`; case remains unrun.


After the two new integration adapters were registered, the AST-only public API index was regenerated: 312 Python modules and 1,642 public top-level classes/functions. No package import, validation case, native engine, or scientific calculation was run.

### Cryo-neutron source staging receipt (2026-10-31)

The selected three-file Mendeley CC BY 4.0 subset was staged outside the source archive through the approved Hangang `run.sh cpu` wrapper. All 27 base64 chunks were assembled and size, SHA-256, and MD5 were checked before promotion to `/scratch/CLUSTER_USER/h2physics-source-attachments/cryo-neutron-phase-change/2/Jan(H2)/jan_tc1/jan_tc1_run1/`:

- `jan_tc1_run1_exp_daq.csv`: 302,376 B; SHA-256 `0589fedf062cf036993fd48ffbed81c8b4a1ee502cd19b6a23935839aab37851`; MD5 `370f599cdebe441ebfbd6057ec15ca13`.
- `jan_tc1_run1_exp_img.csv`: 195,985 B; SHA-256 `abfbb4fc35f7008ca4224daed6e27ae5cb182901140f93aab4100ae5162768e0`; MD5 `d1bc2f654c814cf16b808855f80e5485`.
- `jan_tc1_run1_exp_img_rate.csv`: 905 B; SHA-256 `dd62eabc62a15c32f3ed0457649240b9f5990e57db1d45e5d829b8f0808aad16`; MD5 `a493c2e4185664773c38118360ca2ea8`.

This is source-file staging only. The deferred ingestion case has not been submitted or scientifically evaluated.


The public API index was refreshed after adding the two typed transfer ledgers to the PV-electrolysis/linepack adapter: 312 modules and 1,643 public top-level definitions (AST-only).

### Linepack withdrawal to fuel-cell feed adapter

Added `bind_linepack_fuel_cell_feed()` and deferred case `linepack-fuel-cell-hydrogen-feed-handoff` under `gas-compressible-pipe`. It maps one exact linepack mass interval and clock to existing fuel-cell `ThermochemicalFeed`/`FuelCellStep` inputs. Linepack has no energy integral, so callers supply source interval enthalpy/reference ID, receiver energy-basis ID, signed reference offset and conditioning energy, closing as `H_source + offset + conditioning - H_feed = 0`. The case is deferred; this lane ran no tests, imports, or calculations.


After registering the linepack-to-fuel-cell adapter, the AST-only public API inventory was regenerated: 313 modules and 1,645 public top-level classes/functions. No import or runtime validation was performed by the inventory command.

## WSKBIJ Test001 raw trace ingestion (2026-10-31)

Acquired official 207,853,888-byte Test001 pressure trace (DataverseNO file ID 268129; persistent ID doi:10.18710/WSKBIJ/PIQIIP). Publisher MD5 is 6a2b1e93513c33d9400ba8abf4b9d082; raw SHA-256 is c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703. Lossless gzip transfer object is 66,314,797 bytes with SHA-256 da3673ff937db2f230e2f2d98638aac6023edda38464b7310a066a3aa4db4d32. Reader and deferred Hangang case stream rows, verify raw receipt and schema, retain the absolute timestamp token and elapsed time column separately, and leave voltage channels uncalibrated. Hangang receipt and full-stream case remain pending; this lane ran no tests, imports or calculations and made no physical model comparison.
# Grid-powered electrolyzer dispatch — 2026-10-31

Added `h2physics.adapters.grid_electrolysis_dispatch` as a grid-fed boundary
around the shared `HydrogenStack` and existing `ThermalStackStage`. It selects
the highest grid-feasible current from a caller-declared finite current-density
grid for each contiguous, held AC interval; records auxiliary demand, AC/DC
conversion loss, stack DC power and curtailment; and exposes thermal commands
for the existing finite thermal owner. Added the deferred synthetic case
`grid-ac-power-to-electrolysis-stack-dispatch`, package exports and focused API,
catalog and scope documentation. The case is registered under the Hangang
`grid-electrolysis` profile and has not been run. No local import, test or
scientific calculation was run. This does not qualify a grid-connected plant.

### WSKBIJ Test001 raw source receipt (2026-10-31)

DataverseNO public file ID `268129` was fetched through the approved Hangang wrapper. The final raw attachment is staged outside Git at `/scratch/CLUSTER_USER/h2physics-source-attachments/wskbij-explosion/1/Test001.txt`: 207,853,888 B, SHA-256 `c5f2a991c611dff77f3f2c027da2a1505e1c7843b212cdddd90b0eb9b44ec703`, publisher MD5 `6a2b1e93513c33d9400ba8abf4b9d082`. The public API's publisher MD5 and expected SHA/size all match. A locally compressed gzip differed bytewise from the proposed pin, so the verified raw file was staged directly under the manifest's expected basename. The new Test001 reader/case must be included in a later immutable pin; this is source staging only, with no ingestion or model validation claim.

## Native single-pipe pressure-wave level (2026-10-31)

Added `h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel`, a distinct one-dimensional fixed-temperature isothermal-Euler model for momentum storage and pressure-wave travel in a closed hydrogen pipe segment. It uses first-order Rusanov finite volumes, a pluggable `IsothermalSinglePhaseEOS` closure, caller-selected maximum CFL no greater than 0.5, impermeable end faces, and constant Darcy momentum drag. The friction step is an operator-split exact update of the frozen-density source ODE, `u_new = u_old / (1 + k*abs(u_old)*dt)`. Trace output separates actual maximum CFL from its configured limit, records EOS identity and reports face mass flow in kg/s. Package exports, model catalog, API docs and deferred case `hydrogen-pipeline-isothermal-pressure-wave-dynamics` are registered. AST-only review passed; the case remains unrun and no package import or scientific calculation was performed. Real-fluid closure is pluggable; energy/wall heat, leak/reservoir/network boundaries, and independent pipeline validation remain open.

## Isothermal EOS closure and hydrogen pipeline transient data gap — 2026-10-31

Added `IsothermalSinglePhaseEOS` and `CoolPropIsothermalEOS` in
`h2physics.thermo.isothermal_eos`. The speed closure uses CoolProp's documented
isothermal compressibility for homogeneous gas/supercritical states; it never
uses the adiabatic speed-of-sound property. The finite-volume wave adapter is
being wired to this protocol by the parallel plant lane. No runtime checks or
calculations were run locally. Documented the pipeline transient data gap and
rights audit: current CC-BY open-channel hydrogen source data are already
acquired but are not in-pipe pressure-wave observations; the H2-SimNet record
has no explicit data license; and the open air/water large-pipe candidate has
no data-specific license. No additional payload was acquired. Request 036
specifies the missing measured data package and observation acceptance contract.

The AST-only public API index was refreshed after this EOS addition: 317 Python
modules and 1,657 public top-level definitions. No package import or runtime call
was part of the inventory refresh.

The CoolProp-specific isothermal EOS provider case is registered for Hangang
and remains unrun. It exercises fixed-temperature EOS round trips and compares
the returned isothermal characteristic speed squared with an independent
centered pressure-density finite difference. The case does not invoke a local
runtime; only AST parsing was performed here.

## Bounded isothermal-EOS lookup table (2026-10-31)

Added `h2physics.thermo.IsothermalEOSTable`, a distinct rho-T pressure and
isothermal-characteristic-speed lookup backend for repeated gas-wave calls.
Existing `QualifiedGasTable` only wraps CoolProp PT/PH/PS backends and does not
provide this rho-T/cT API. The table stores immutable caller-selected axes and
property arrays, the source EOS identity, interpolation mode, and grid SHA-256;
it rejects nonmonotone pressure and does not extrapolate. `linear` and
positive-preserving `log_linear` modes are available. The held-out qualification
receipt records seeded relative pressure/density/cT errors and direct/table
per-query timing separately. Synthetic deferred case
`isothermal-eos-table-interpolation-accuracy` is registered under
`isothermal-eos`; it remains unrun. The table agrees only against the selected
direct EOS and does not qualify the solver or facility. AST parsing passed for
the provider, package exports, case and Hangang plan. No runtime import, table
generation, test or scientific calculation was run locally.

### Two-vent hydrogen buoyant-layer core model

Added `dispersion.buoyant_layer` with `TwoVentHydrogenLayerConfig` and `run_two_vent_hydrogen_layer()`. The fixed-temperature two-layer model advances upper volume and H2 inventory with a RK4 march, computes pure-source plume entrainment and closes two-vent flow through the mass relation `rho_air*Q_lower + m_dot_H2 = rho_layer*Q_upper`. Its synthetic Hangang case is registered under `facility-protection`, deferred and unrun. Source basis: the open NIST Prasad, Yang and Pitts analytical two-vent hydrogen compartment model (2011), DOI 10.1016/j.ijhydene.2010.08.040. Current scope excludes wind, intermediate vents, multiple sources, thermal effects, combustion and CFD. This lane had no local runtime tests, imports or calculations.

## Finite-reservoir pipe pressure boundaries (2026-10-31)

Extended `IsothermalPipeWaveModel` with optional caller-owned left/right pressure histories via `FiniteReservoirPressureBoundary`. The coupling uses subsonic isothermal characteristic states with an EOS-bounded density bracket; histories require exact clock, EOS identity and temperature, cover the full simulation interval, and do not extrapolate. Signed face mass flow is integrated into cumulative inflow/outflow and checked against finite-volume pipe mass. Deferred synthetic case `hydrogen-pipeline-isothermal-wave-finite-reservoir-boundaries` covers interpolation, mass closure, past/future and insufficient-support rejection, clock/EOS/temperature mismatch, out-of-bracket pressure, and supersonic rejection. Reservoir depletion, valves/nozzles, thermal dynamics and empirical pipeline qualification remain out of scope. Static AST-only checks and API inventory were performed; no runtime case/tests/imports/calculations were run.

### Isothermal EOS table persistence artifact

Added a versioned, single-file artifact format for immutable EOS tables: numeric NumPy arrays plus canonical TOML metadata, checksums, bounded size/schema checks, and atomic publication. Loading rejects payload tampering, source-EOS identity mismatch and out-of-envelope queries. The deferred Hangang case `isothermal-eos-table-artifact-roundtrip-integrity` checks round-trip identity and corruption rejection; it does not assess EOS accuracy. Static source review/API inventory only; runtime case remains deferred.

## HyRAM+ hydrogen ignition-probability adapter (2026-10-31)

Added a typed optional adapter that calls the separately installed native
`hyram.qra.ignition_probs.get_ignition_probability` function for a caller-owned
hydrogen mass-release rate and evidence-bound threshold table. The installed
default H2 table is captured on request rather than copied into this project.
Results retain immediate/delayed absolute probabilities relative to a release,
package version and native source SHA-256. The deferred Hangang contract covers
custom rate bins, exact threshold behavior, invalid input and missing optional
dependency rejection, and provider identity. No local import, runtime test or
scientific calculation was run. The adapter is implemented-unverified and does
not validate ignition likelihood for a facility or replace event-tree
assumptions. HyRAM+ is GPL-3.0-only while this project is Apache-2.0; combined
installation/redistribution is not cleared and requires a separate review.

## HyRAM ignition result to native conditional-risk branches (2026-10-31)

Added `h2physics.adapters.hyram_ignition_risk.bind_hyram_ignition_to_risk()`.
It maps release-relative immediate/delayed outputs and their complement to the
existing native risk engine's mutually exclusive conditional-on-LOC branches.
The exact caller `Frequency` object is retained; no LOC rate, annualization,
conditional-on-ignition conversion, harm value or consequence is inferred.
Explicit branch IDs, probability-factor IDs, partition evidence and typed harm
bindings are required. Table/provider lineage is retained as a digest, not a
signature authenticating the upstream HyRAM evaluation. The deferred synthetic
case uses authored values and does not load or execute HyRAM; it remains unrun.
The GPL-3.0-only HyRAM dependency is not bundled or added to project metadata;
combined redistribution with this Apache-2.0 project is not cleared. The bridge
and Hangang case passed AST parsing only; no risk calculation or facility
validation was performed.

The AST-only source API index now contains 323 Python modules and 1,672 public
top-level class/function definitions. This is source navigation, not execution
or scientific verification evidence.

### 5aw prior-pin singleton readiness (2026-10-31)

The verified 5aw source pin remains usable for independent cases whose source files and profile are unchanged. For `hydrogen-linepack-compressor-inlet-handoff`, adapter, case, and focused-doc SHA-256 values match between 5aw and 5ay; the 5aw discovered plan includes the case under `gas-compressible-pipe`. This case has no raw-data or optional-provider requirement and has no prior result on 5aw.

Pin: revision `12b3585d56ccf94be3bf04cb17ab40ca6431bc0c`; archive SHA-256 `3e45a37a071a91fa9da1c71b4c68f974b380010c7c2994f86f91aa2c2a8c0d94`; manifest SHA-256 `180e92726483dec8695681f3488cf49576ddbf01e3b8cafeb7c2abb88cef10fe`; 1,267 entries, all checks passed, forbidden count zero. A one-case 30-minute PBS script is prepared at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5aw-linepack-inlet-ready.pbs` (SHA-256 `61ac64a799f5e07b321e3b7934092354e1eef6f1952ef6493e93eb296881417c`) using the existing Hangang Python 3.12 venv. It has not been submitted because the latest qstat showed five active user jobs (1186716, 1186978, 1187147, 1187427, 1187566); no job ID or scientific result exists.

#### 5aw linepack inlet submission attempt (2026-10-31)

The prepared singleton `hydrogen-linepack-compressor-inlet-handoff` was attempted with the authorized `run.sh cpu`/`qsub` wrapper. First submission was refused before admission because the wrapper was invoked from `/home01/r1021a02`; the cli filter requires submission cwd under `/scratch` or `/appsdata`. Retried after creating and changing into `/scratch/CLUSTER_USER/h2physics-jobs/results/5aw-linepack-inlet`; Slurm returned `QOSMaxSubmitJobPerUserLimit` and no job ID. No existing job was touched. Immediate qstat still showed five running jobs: 1186716, 1186978, 1187147, 1187427, and 1187566. Script remains prepared at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5aw-linepack-inlet-ready.pbs` (SHA-256 `61ac64a799f5e07b321e3b7934092354e1eef6f1952ef6493e93eb296881417c`) for retry when QOS admits it.

## Current programme snapshot (2026-10-31)

- Overall completion remains a rough **30–40%** estimate across implementation,
  open-data qualification, rights review, reproducible documentation and
  independent scientific validation. It is not the catalog coverage fraction.
- The catalog currently tracks **80 families**: 19 implemented, 37 with
  native-adapter-verified status and 24 implemented-unverified; no family is
  marked planned. These are software status labels, not physical validation.
- The AST-only source API index contains **324 Python modules and 1,676 public
  top-level definitions**. This is a navigation inventory, not runtime evidence.
- Current coding additions include bounded EOS-table artifacts, transient pipe
  waves with caller-owned reservoir pressure boundaries, HyRAM ignition
  probability and conditional-risk handoffs, the two-vent buoyant-layer model,
  streaming WSKBIJ Test001 ingestion, and a branched isothermal pipe-wave
  network. The network has five independently schedulable deferred Hangang
  cases; all remain unexecuted on the current source pin.
- The Guo buried-hydrogen blend dataset has an explicit CC BY 4.0 publisher
  record and 12 staged, checksum-verified CSV files outside Git, but its
  unlabeled columns lack physical units/clock/sensor mappings and cannot qualify
  the pipe-wave model. Request 036 remains open for semantically resolved
  transient pipe measurements.
- Latest confirmed Hangang CPU queue snapshot contains five running jobs. A
  verified 5aw linepack-compressor-inlet singleton was refused by
  `QOSMaxSubmitJobPerUserLimit`; no job ID was created. The source and script
  remain prepared for submission after account capacity opens. No active job
  was changed, no local runtime test was run, and no new physical result is
  claimed.

The branched-pipe cases and the Cal State LA data-access audit were added after
5aa was sealed. The API index now reports 324 modules and 1,676 definitions.
5ab is sealed locally and transferring for remote audit. Five synthetic 5ab
contracts completed locally on Python 3.12.16 without assertion or numerical
errors; this is software-contract evidence, not independent scientific
validation. The post-5ab source adds pressure-history terminals as a 5ac delta.

## Hangang source pin 5az — 2026-10-31

The immutable 5az source pin is revision `45d406843085ba7aebe9ff52cb91f5e0d1d8d695` (tree `c96f0762587497f00f23f0d31f7e32bf3a06a936`). Its deterministic archive is 4,324,966 bytes with SHA-256 `6636abac4c10fb4c00edb217bf87fc299b9ee227e9a79d55942cfab6d9fcc2ac`. The canonical LF sidecar manifest is 135,948 bytes, has 1,316 entries, and SHA-256 `f0e3e31785794c0dd6ff5bc4a0631b1f5a6e8645bab9018914a977eea0687bba`. Archive and manifest are under `/scratch/CLUSTER_USER/h2physics-jobs/live-6636abac4c10fb4c00edb217bf87fc299b9ee227e9a79d55942cfab6d9fcc2ac/`.

Remote audit confirmed 1,316/1,316 manifest entries, matching embedded revision and manifest, 1,342 tar members, and zero unsafe or forbidden members. `LICENSE`, `NOTICE`, and `docs/RIGHTS_AND_PROVENANCE.md` are present; 56 `research/data/*.toml` records declare a `license_id`. Raw attachments remain outside the source archive. The archive was built with normalized tar/gzip metadata and repeated locally with the same SHA-256.

The pinned Hangang metadata preflight passed using the verified `/scratch/CLUSTER_USER/h2physics-jobs/pinned-6636abac4c10/.venv/bin/python` (resolves to Python 3.12), setup SHA-256 `c0921d837af00b481df4915f60e867830cecf8f7aa4cb728f02c585e381abfb5`, and pinned plan SHA-256 `5a999602a728130e88db4468a8a721f4783fce4feafc05815074a16747a0fdd1`. Eight singleton PBS scripts are prepared under `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5az/` for WSKBIJ summary ingestion, WSKBIJ Test001 streaming ingestion, Hydrogen Map ingestion, Leaky-Coating ingestion, isothermal pipe waves, two-vent buoyant layer, linepack-to-fuel-cell handoff, and isothermal EOS table qualification. The source inputs for the four ingestion cases were rechecked by remote size, MD5, and SHA-256. These scripts have not been submitted and have no case outcomes.

The Cryo-neutron raw files were staged and verified externally, but the 5az Cryo case still defaults to a path under the source checkout. It is not eligible from 5az. The live plan now binds the case to the verified external run directory; this follow-up is a new immutable pin (5aa), and the 5az archive remains unchanged.

The latest qstat snapshot had five running user jobs (1186716, 1186978, 1187147, 1187427, 1187716). No 5az job was submitted while QOS was full. Current project tracking estimates overall software progress at roughly 30–40%; the model catalog reports 80 implemented, 19 native-adapter verified, 37 unverified, and 24 planned entries. The public API inventory is 323 modules and 1,672 definitions. These are inventory/status measures, not an overall scientific validation percentage. No local runtime tests or calculations were run for this pin; the preflight was metadata import and script generation only.

## 5az Cryo path follow-up — 2026-10-31

The Cryo files remain externally staged and checksum-verified. The immutable 5az plan still resolved `cryo-neutron-lh2-phase-change-source-ingestion` under the repository's ignored `data/raw` directory, which is absent from worker source archives. The live plan now binds `run_directory` to `/scratch/CLUSTER_USER/h2physics-source-attachments/cryo-neutron-phase-change/2/Jan(H2)/jan_tc1/jan_tc1_run1`. This correction is captured separately as the 5aa follow-up pin; 5az remains unchanged and no Cryo case has been submitted from it. The profile is `source-data-ingestion`; this is a path-binding correction only, not an ingestion result.

## Branched isothermal pressure-wave network (2026-10-31)

Added `h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkWaveModel`, a separate 1-D isothermal-Euler fidelity level for connected pipe graphs. Edges retain explicit geometry and provenance; junctions have caller-owned pressure bounds and solve a common EOS-backed pressure from the area-weighted sum of outward Rusanov mass fluxes. That same mass flux is applied to finite-volume edge faces, so junction transfers cancel in the total network mass ledger. Closed terminal nodes impose zero mass flow and pressure traction. The deferred synthetic Hangang case `hydrogen-pipeline-branched-isothermal-wave-network` checks edge/node output dimensions, junction continuity, global mass closure, provenance, unbracketed-root rejection, and supersonic-state rejection. It remains unrun. Limits include one shared EOS/fixed temperature, horizontal single-phase pipes, no gravity, no detailed junction loss/mixing model, no valves/compressors, and no network measurement qualification. Equation sources and derivation limits are documented in `docs/BRANCHED_ISOTHERMAL_PIPE_WAVES.md`. Python AST parse passed; no runtime tests/imports/calculations were performed.

### Branched pipe-wave case expansion (2026-10-31)

The registered network-wave module now returns five independently schedulable deferred Hangang cases, all under `gas-compressible-pipe`: (1) the base junction/network conservation contract; (2) reversed edge orientation plus reversed node/edge insertion order; (3) unequal branch areas with area-weighted mass continuity; (4) nonzero Darcy friction compared with zero friction; and (5) explicit pressure-bracket failure. Existing base checks retain provenance, output dimensions, terminal wall flux, junction continuity, global mass residual, and supersonic rejection. `validation/hangang_plan.py` discovers the module once; its `cases()` metadata expands it into five IDs. None has been run.

## Network prescribed-pressure terminal boundaries (2026-10-31)

The branched isothermal pipe-wave network now accepts prescribed pressure-history terminal nodes using `FiniteReservoirPressureBoundary`. The network requires exact node-map coverage, owner/evidence agreement, compatible clock/EOS/fixed temperature, and full time support; EOS pressure replay is checked at history knots and substep interpolants. Subsonic characteristic states are required. The trace retains reservoir identity and sampled pressure, cumulative pipe-side inflow/outflow, and global residual `M_pipe - M_pipe,0 - m_in + m_out`. These exchange ledgers describe the pipe side only; source reservoir inventory and depletion are not modeled. Added two deferred Hangang contracts (valid histories/closure and contract rejection), bringing the network-wave suite to seven case IDs across two discovery modules. All seven synthetic entrypoints completed locally on Python 3.12.16; the complete 5ac source archive has not yet been pinned or remotely validated.

## Local 5ab contract run — 2026-10-31

Copied the sealed 5ab archive to WSL ext4 and confirmed its SHA-256 remained `5cc94307d25c1702a739577947602b1d0d7b31000a0d28f7a596c8c2e2370a81`. The five frozen network case entrypoints completed without assertion or numerical errors using Python 3.12.16, NumPy 2.5.4 and SciPy 1.18.1. Covered base junction conservation, reversed orientation/order, unequal branch areas, Darcy friction, and out-of-bracket pressure rejection. This is a local synthetic software-contract run against the 5ab source archive; it is not measured-data validation, facility qualification, or a Hangang result. The later prescribed-pressure terminal feature and its two cases were added after 5ab and were not part of this run.

## Local 5ac boundary integration run — 2026-10-31

Copied the 5ab extraction to WSL ext4, then overlaid the current 5ac solver and reservoir-case files. Their SHA-256 values matched the live working tree: solver `0c7a44ff01ed26cd00c9091e743d9b28b2d95071ffee3aa2706e42a2f5da77b8`; case `6ba8c0328ed4e5c3f5f9c1372b03fd0f51b1af1d87996d7dd174b2616840f269`. All seven contracts completed without assertion or numerical error under Python 3.12.16, NumPy 2.5.4 and SciPy 1.18.1. This overlay smoke run does not represent a complete 5ac archive, measured-data validation, facility qualification, or a Hangang result.

## Finite inventory reservoir endpoint (post-5ac)

Immutable archive 5ac is now locally sealed at revision `1d8d1057a866fc267cefbdef3d70e5d0d65973bc` (archive SHA-256 `4f202c820d136ab057bf4c47255db81794972168d826748e08567e20a5e4be22`, manifest SHA-256 `459936b2f26ad10add1cab3214e576dd31b4237d6be416b575e4cd6c986595aa`). The finite-inventory work below is a subsequent source delta and is not in that archive.

Added `FiniteIsothermalPipeReservoir` and integrated a distinct `kind="finite_reservoir"` terminal into the branched isothermal pipe-wave network. Pressure is computed from current inventory divided by fixed vessel volume at the caller-declared fixed network temperature through the exact shared single-phase EOS identity; the density-pressure inverse is replay-checked. Each step applies the same signed endpoint Rusanov mass rate to the adjacent pipe finite-volume face and reservoir stock (`m_next = m_current - dt*F_out`). Owner/evidence/node/clock/EOS/temperature identity, explicit inventory bounds, and source origin are required. Out-of-range/depleted stock, EOS failures, and sonic/supersonic endpoint flux states reject without clipping.

The trace now carries per-endpoint reservoir mass and pressure histories with identity/provenance. Where finite inventory endpoints are present, `total_mass_kg` and `global_mass_balance_residual_kg` include pipe plus reservoir stock; the separate prescribed-pressure boundary exchange remains an external pipe-side ledger. The legacy `FiniteReservoirPressureBoundary` remains a prescribed pressure/time trace with no source mass inventory or depletion. Added four deferred synthetic contracts across network/state modules and a focused runnable example. Public API inventory was regenerated by AST only: 325 source modules and 1,677 public definitions. Changed Python files passed AST parsing; no runtime case, import, calculation, local numerical test, or Hangang job was run in this lane. A local contract run and remote Hangang replay remain pending; this is not measured-data validation or vessel qualification. Limits and source basis are in `docs/FINITE_ISOTHERMAL_PIPE_RESERVOIR.md` and `docs/BRANCHED_ISOTHERMAL_PIPE_WAVES.md`.

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
## Finite reservoir nozzle sink (deferred)

Implemented the start-of-internal-step shared-nozzle withdrawal as an explicit sink in the finite-inventory network update. The same accepted nozzle rate is debited from reservoir stock alongside the signed Rusanov pipe exchange; endpoint nozzle evaluations are diagnostic samples. Cumulative leak-out enters the combined global mass closure. Source projection is restricted to left-hold and verifies projected mass against the accepted leak ledger. The Python composition API, focused usage/limits document, and two deferred contracts are registered under `gas-compressible-pipe`. The contract requires the network EOS identity, caller caloric property basis/mapping evidence, declared density tolerance, opening/back-pressure/location/clock evidence, and source-state P/T/phase/density checks. No local or Hangang validation result has been recorded, and no HyRAM dispersion execution is claimed.

## Current continuation status — 2026-10-31

The rough whole-program effort estimate remains 30–40% and has not been fully re-audited this turn. The source catalog lists 81 families: 19 implemented, 37 native-adapter-verified, and 25 implemented-unverified, with no planned-only row. This is first-level source classification, not family completion or scientific validation. The AST-only public API inventory was regenerated this turn at 331 modules and 1,701 top-level public definitions.

The local `h2physics-py312` Conda `research` dependency check reports ready. Recent solver and adapter additions passed only AST checks; no scientific calculation, local model test, benchmark, or native replay was run. The finite-reservoir nozzle bridge has two deferred `gas-compressible-pipe` Hangang contracts and remains unexecuted.

Hangang immutable 5ad/e8 transfer is in progress: 565 of 1,171 archive parts have matching local/remote SHA receipts at the latest adapter report. The two earlier multiplex refusals (5ad parts 0475 and 0484) were retried and verified individually. A separate local 5ae archive was sealed at revision `e018655e4f70f22ffecdd22fd52ba0a8b26d427d` with 1,372 manifest entries; its local manifest check passed and forbidden-member scan was empty. Archive SHA-256 is `7601cff2f52d38264516c4255673b0bce656a846ba06198104ea05f9a955b976`. Its remote transfer is underway independently; 70 of 1,173 parts have matching local/remote SHA receipts. Bounded concurrent wrapper transfer is stable at 12 sessions (10 for 5ad and 2 for 5ae), with per-part SHA receipts; no archive verification or source-stage receipt is implied by partial transfer. The nozzle-sink delta is not inserted into the immutable 5ad archive. A direct GPU-target qstat snapshot showed four running user jobs and one completed entry; the active transfer lane did not submit those jobs. No new job was submitted while queue ownership was checked. No queued or running job is counted as a result.

Hangang result update — 2026-10-31: job `1188659` reached terminal state `C`, `sacct` reported `COMPLETED / ExitCode 0:0` (19:59:14–19:59:32, 18 s), and its outcome file at `/scratch/CLUSTER_USER/h2physics-jobs/results/5ac-4f202c82/1188659/hydrogen-pipeline-network-wave-reservoir-contract-rejections/outcome.json` reports `passed`. The case was run against immutable source revision `1d8d1057…`, plan SHA `332117ce…`, and setup SHA `c0921d83…`. It checks rejection contracts for clock, EOS, temperature and time support, owner, and missing boundary evidence. This is a synthetic API/numerical-contract result, not experimental or facility validation. At the latest scheduler snapshot there were three running user jobs and this completed job; no other case from the verified 5ab/5ac plans remained distinct and unrun. New-pin cases will be submitted after 5ad/5ae source verification. No result was inferred from job submission or a running state.

## Receiver-side HyRAM extension requirement — 2026-10-31

Prepared [Request 037](../requests/037_hyram_transient_finite_source.md) after completing the host-side finite pipe-reservoir nozzle source contract. The existing direct HyRAM adapter is a single-state stationary jet call whose native solver calculates its own orifice flow. The request specifies how a future receiving API can consume an already-debited time-varying H2 source without replacing its rates, and explicitly separates true plume-memory transient results from independent quasi-steady snapshots. Host source/ledger contracts are locally AST-checked but remain unexecuted; no HyRAM run or transient-dispersion claim is made.

## Caloric compressible pipe waves — implemented, unverified

Added a 1-D non-isothermal compressible Euler pipe solver conserving mass,
axial momentum and total energy with explicit CFL-limited Rusanov fluxes and a
pluggable single-phase rho-u EOS. Optional caller-evidenced Darcy momentum
friction and fixed-wall heat are integrated into the same update and energy
ledger. Trace provenance includes EOS identity, geometry, run clock, source and
boundary owner/evidence identifiers, and mass/energy residuals. Four deferred
`gas-compressible-pipe` Hangang contract cases are registered. Status remains
`implemented_unverified`; no scientific tests or calculations were run locally.
Scope excludes finite reservoir depletion, junctions, valves/nozzles, phase
transitions and measured-pipeline validation. See `CALORIC_PIPE_WAVES.md`.

## Fixed-flow finite-source HyRAM snapshot boundary — implemented, unverified

Request 037 now has a host-side Python contract for independent quasi-steady
receiver snapshots from a time-varying finite nozzle-source projection. Each
positive left-hold interval is sent to an injected receiver and its admitted
source-plane H2 mass rate is compared with the upstream rate; zero-rate bins
remain in order without a receiver call. A mismatch or receiver failure is
retained as a rejected interval result. The existing stationary HyRAM adapter
is explicitly incompatible because it calculates its own orifice flow. These
snapshots carry no plume memory and make no transient-exposure claim. The
`hyram-finite-source-fixed-flow-snapshots` Hangang contract is deferred; no
HyRAM run or scientific test was run. Catalog status is
`dispersion.fixed_flow_snapshots: implemented_unverified`.

## Source documentation and public API refresh — 2026-10-31

Architecture/backlog summaries now use the current 81-family catalog and
331-module/1,701-definition AST API inventory rather than stale intermediate
counts. The legacy Nurion plan is explicitly marked historical; Hangang is the
current validation target. The existing Conda environment `h2physics-py312` is installed and the
environment checker reports its core profile ready. No scientific tests,
calculations, benchmarks or native replays were run. The updated public-tree
content-hygiene audit inspected 1,376 GitHub-bound files and passed; this does
not assess license clearance.

## Caloric branched pipe-network waves — implemented, unverified

Added `CaloricPipeNetworkWaveModel` as a distinct non-isothermal network
fidelity level over the single-segment caloric Euler model. Each pipe edge
advances mass, axial momentum and total energy. A junction is explicitly a
zero-volume, adiabatic, perfectly mixed node at rest; common pressure and
temperature are solved from the exact signed Rusanov mass and energy fluxes
applied to connected edges. Caller-declared pressure/temperature brackets,
balance residuals and nonnegative perfect-mixing entropy production are gates.
Trace provenance retains node/edge geometry and origin, endpoint identity,
boundary/source conditions, clock, EOS and global ledgers. Optional
caller-evidenced Darcy friction and fixed-wall heat can be assigned per edge;
the same source contracts and energy-accounting rules as the single-pipe model
are reused. Six deferred `gas-compressible-pipe` Hangang contracts are
registered. Status remains `implemented_unverified`; no scientific
calculation/test or Hangang run was performed. The plenum closure omits
junction momentum/pressure loss, finite node storage, gravity, phase change,
valves and composition change. See `CALORIC_PIPE_NETWORK_WAVES.md`.

## Finite caloric reservoir endpoint — 2026-10-31

Added `FiniteCaloricPipeReservoir` for a caller-evidenced, fixed-volume,
well-mixed gas inventory with explicit initial mass/internal energy, EOS and
property-basis identity, mass limits, pressure/temperature domain bounds,
clock, owner, evidence and origin. `CaloricPipeNetworkWaveModel` now supports a
separate `kind="finite_reservoir"` terminal while preserving the original
prescribed-state `kind="reservoir"` mode. Each internal step updates vessel
mass and U from the exact signed endpoint Rusanov mass/energy rates already
applied to the adjacent pipe face; proposed rho-u states must pass the shared
EOS and caller bounds before either state is committed. Combined network totals
include finite tank stock, so pipe-to-tank transfer cancels in global mass and
energy residuals. Depletion, EOS failures and pressure/temperature domain
violations reject without clipping. Two deferred Hangang contracts cover
accepted blowdown/combined ledgers at both edge orientations and mass/domain/
evidence rejection. The API and catalog now include this unverified level.
AST parsing passed for all five changed Python files; the public API index was
regenerated by AST at 331 modules / 1,701 public definitions. No scientific
test, calculation or remote job was run. This single-state boundary adds no
wall thermal mass, stratification, valve/nozzle flow, phase change or vessel
qualification.

## Current-target guide alignment — 2026-10-31

The droplet-impact, fracture/fatigue, obstacle-dispersion and vessel-failure
guides were recovered from the clean project archive and aligned to current
Hangang contracts and source APIs. The catalytic-surface-reactor and scenario-
composition guides were reconstructed from their current Python APIs and
deferred cases because no clean prior copies were available. All six were
checked as strict UTF-8, with no PDF references, stale current-Nurion target
instructions, corruption tokens, trailing whitespace or broken relative
links. The two reconstructed guides replace lost prose and should be expanded
from future code changes rather than treated as exact copies of earlier drafts.
# Caloric finite-reservoir shared-nozzle release — 2026-10-31

Added `CaloricFiniteReservoirNozzleCoupling` to connect an existing finite
caloric network reservoir to the shared `HomogeneousIsentropicNozzle`. The
nozzle provider must use the exact reservoir/network `PropertyBasis`; each
accepted step derives its upstream state from current tank mass and internal
energy through the network rho-u EOS and cross-checks provider P/T/density.
One step-start nozzle result debits mass and withdrawal energy alongside the
same signed pipe endpoint flux. Candidate tank and pipe states must both pass
before commit. Prescribed fixed-state reservoirs and finite reservoirs with no
nozzle retain their former paths.

Traces now retain nozzle coupling provenance, exact internal-clock source
histories, cumulative leak mass/energy, and combined pipe/tank ledger signs.
`project_nozzle_source()` requires a representative state plus two evidence
identifiers, fixes integration to left-hold, and checks projected mass against
the accepted solver debit. Two provider-backed cases are deferred to Hangang:
choked/subcritical thermal blowdown and source projection; basis/domain/depletion
rejections. The new coupling and cases are `implemented_unverified`. Only AST
and static API metadata checks are allowed for this lane; no scientific model,
local test, benchmark, or remote job has been run.

## Real-gas linepack — 2026-10-31

Added `RealGasLinepackState`, a separate fixed-volume, fixed-temperature
inventory that obtains pressure from a retained `IsothermalSinglePhaseEOS`
instead of the perfect-gas formula in the existing lumped linepack. Initialization
checks pressure/density inverse consistency and provider identity; steps preserve
explicit inlet/outlet mass and reject inventory-floor, pressure-domain, phase,
or EOS-identity failures without flow clipping. The immutable step ledger now
checks the reported mass residual against its port and inventory fields. A
deferred Hangang contract covers CoolProp hydrogen EOS inversion, charging,
mass closure, pressure limits and provider mutation. The Python package exports,
API guide and gas-pipe catalog were updated. This remains a lumped isothermal
submodel without wall-heat calculation, composition evolution or spatial flow;
no local runtime test or scientific calculation was run.

## Additional open facility-data lead — 2026-10-31

Added HyDelta pressure-reducing-station ventilation record 10.5281/zenodo.8164602
to the dataset catalog after checking the Zenodo version-2 record and API. It
declares CC BY 4.0 and lists two report files totaling 17,156,658 bytes with
publisher MD5 values. Neither report was acquired. The record has no separate
machine-readable sensor history, so it is recorded as a mixed-origin discovery
lead only; no plot-derived values or validation use are claimed. `research/data/`
metadata, dataset seeds, inventory and qualification notes now preserve the
source and rights boundary.

## Latest parallel execution snapshot — 2026-10-31

The source transfer lane most recently confirmed 1,035/1,171 5ad parts and
372/1,173 5ae parts with matching local/remote SHA receipts. Both immutable
archives remain incomplete. Three Hangang jobs were running at the latest
queue snapshot; the only newly accepted result is job 1188659 recorded above.
No distinct unrun case remained in the verified 5ab/5ac plans, so new-pin
submissions await 5ad/5ae transfer and manifest verification. Local coding
continued independently in the EOS real-gas linepack and caloric finite-tank
nozzle-coupling lanes; the AST API inventory is now 335 modules / 1,711
definitions. No local scientific test or calculation was run.

## Prior parallel implementation/data snapshot — 2026-10-31 (superseded below)

Added `CoolPropMixtureIsothermalEOS` to adapt the immutable, fixed-composition CoolProp HEOS provider to the mass-basis isothermal EOS protocol. The real-gas linepack now has a deferred H2/N2 blend contract covering PT↔rho-T, isothermal derivative closure, mass-port ledger, pressure bounds and phase rejection. No composition evolution or measured blend-pipeline validation is claimed.

Added `ProportionalIntegralPressureRegulator`, a sampled PI command generator that emits existing bounded `ValveCommand` intervals with sensor/owner/clock lineage and conditional-integration anti-windup. Its deferred Hangang case checks controller arithmetic and identity boundaries; the valve, flow, sensor and downstream pressure physics remain owned by existing models.

Acquired the HySaM v1.0 public sampling-system workbook subset (Zenodo 20590842, CC BY 4.0): 3/3 XLSX files, 1,022,797 bytes, all publisher MD5 and local SHA-256 checks verified. The source-bound reader retains bytes and workbook schemas without interpreting instrument tags. No channel units, calibration, pressure reference or aligned clock are supplied, so this is ingestion/schema evidence only. Deferred case `hysam-source-bound-workbook-schema` is registered. Remote staging is complete: all three XLSX files and the exact Zenodo metadata JSON were assembled on Hangang; size, publisher MD5 and local SHA-256 match. Temporary chunks were removed; no job was submitted.

The data-inventory summary now handles selected ZIP members and legacy acquisition fields. Regeneration completed successfully: the cryogenic observation receipt records 3 selected from 2 listed containers, HySaM records 3/3 workbooks, and the H2-Stations row records one 166×7 rolling facilities workbook. H2-Stations has no per-fill physical trace and is infrastructure metadata only.

AST-generated public API index: 335 modules / 1,711 definitions. Current Hangang source transfer: 5ad 1,045/1,171 parts, 5ae 382/1,173, all with matching per-part SHA receipts; both archives remain incomplete. No new-pin model case has been submitted. No local runtime tests, scientific calculations or model benchmarks were run.

## Local development continuation — 2026-10-31

The Windows Conda environment `h2physics-py312` was updated from the repository
`environment.yml`; the `h2physics` package is installed editable with the
thermo, data, chemistry, hydraulics and dev extras. Environment inspection
confirmed Python 3.12 and the declared optional libraries. This only confirms
dependency availability; no scientific test was run. README and user-guide
instructions now cover PowerShell Conda initialization and updating an existing
environment.

The public API index was regenerated by its AST-only script and now records 338
modules / 1,724 public definitions. AST parsing passed for ten current PFR,
mixture-EOS, station-reader, cascade-sequence, data-reader and Hangang-plan
source/case files. The new frozen-mixture
isothermal pipe-wave case is registered for deferred Hangang discovery. A separate
spatial catalytic PFR uses Cantera 3.2 `FlowReactor`/`ReactorSurface`, retains native
axial gas and surface states, exposes caller-set mechanism, coverage, geometry,
feed and output grid, and is registered as a deferred Hangang case. It remains an
adiabatic, frictionless fidelity level; pressure drop, pore transport, catalyst
thermal storage and process yield remain outside it. Ruff passed on the added
PFR, cascade, H2-Stations and source-reader modules/cases. The full-tree
`git diff --check` still reports whitespace findings in the accumulated
development log and two case-file EOFs; these are source-hygiene issues,
not runtime or numerical evidence.

The inventory-only H2-Stations registry now has a source-bound Python workbook
reader and deferred schema-ingestion case. It verifies the local size/SHA receipt,
one-sheet seven-column schema, retains every source row/value, and makes no
physical status or performance inference. Remote staging completed through the
approved CPU wrapper at
`/scratch/CLUSTER_USER/h2physics-source-attachments/h2-stations/2026-10-31/hrs-list-2026-10-31.xlsx`;
15,024 bytes and SHA-256 `87378bed700330ddad64c364b542a69ae34e14d71c800b241c9d92cf112ea02a`
match the local receipt. No case was submitted from this newer, unpinned code.
The raw fueling-trace source search found no public, rights-qualified per-fill
pressure/temperature/flow dataset with verifiable files, so a gap receipt and
report were added instead of chart-derived data.

`GenericCascadeRefillSequencer` adds a distinct supervisory layer for ordered
multi-bank pressure selection. Caller-defined switch thresholds, headroom
margins, sensor identities and common clock control mutually exclusive bank
permits. The deferred Hangang contract covers stage transitions and exclusive
permits; the API rejects changed sensor/owner/clock identity. No flow, valve
actuation or standard procedure is claimed.

Hangang CPU access was confirmed through the approved wrapper (`clogin03`,
`r1021a02`). The immutable 5ad transfer reached 1,171/1,171 SHA-matched parts;
the assembled remote archive is 14,046,117 bytes, SHA-256
`5a7703fd2261a06703460d1ecd82dec070069c0e1c5680f82ec06f0f963c1231`, and its
1,360-entry manifest and forbidden-content scan passed. Independent cases were
submitted without serial waiting: 1188822 Cryo ingestion passed; 1188823
leaky-coating ingestion failed in the reader because a source channel had fewer
than two usable numeric samples; 1188839 WSK Test001 ingestion passed, retaining
2,500,001 streamed rows; and 1188850 USN unignited source ingestion passed.
Locally the leaky reader was changed to permit aligned zero- or one-sample source
traces while retaining all raw pairs; no local replay was run. The immutable
5ad pin was also used for two additional independent cases: 1188878
`finite-inventory-reservoir` and 1188879 `finite-inventory-rejections` both
passed; the reservoir case's maximum combined mass residual was 8.9e-15 kg.
These are synthetic contract/model evidence, not measured-facility validation.
Current transfer progress on the separate 5ae archive is 572/1,173 verified
parts. The 5ad plan predates the new PFR, cascade, H2-Stations reader and
leaky-reader fix, so none of those cases ran on 5ad; a new immutable pin is
required before their Hangang execution.

## Parallel continuation — 2026-10-31

Hangang source-ingestion jobs were launched independently on the immutable 5ad
pin while local model coding continues. Jobs `1188909` (ELVHYS432) and `1188910`
(ELVHYS41) passed, retaining 16,975 and 27,058 rows respectively without
projecting them into a physical model. Job `1188914` (HFCEV fleet source) passed
with 8,448 source rows and its exact two-row window; job `1188918`
(Wasserstoffatlas inventory) passed with 1,049 CSV rows. These receipts establish
source-byte/schema ingestion only, not model calibration or validation. At the
latest queue snapshot, three unrelated user jobs remained running and these
source jobs were terminal. The separate 5ae archive transfer advanced to
602/1,173 SHA-matched parts and continues in bounded batches; no case is launched
from that incomplete pin.

The next independent source case, `1188935` (X044QK ignition matrix), passed on
the same 5ad pin with 40 source rows after confirming its 14,199-byte Matrix
attachment against the local SHA-256 receipt. The pressure basis remains
source-stated and unresolved; this is not ignition-model validation. The separate
USN-ignited ingestion attempt was denied by the queue's
QOS policy and has no job ID; retry is deferred until capacity changes. The 5ae
transfer advanced to 632/1,173 SHA-matched parts.

Hangang job `1188956` passed the WSK Test001 pressure-trace ingestion, streaming
2,500,001 rows across nine raw channels with no normalization or model claim.
Job `1188955` (WSK source summary) failed before parsing because its case
preflight still expected an obsolete two-file/27,918-byte acquisition while the
current manifest records three selected files totaling 207,881,806 bytes. The
reader correctly rejected that mismatch. The local case and focused docs now
match the three-file rights/hash manifest, distinguish the summary's two-file
read scope from the separately ingested Test001 trace, and use the current
linkage label. This is a case-scope correction, not a physical-model failure;
the failed e8 case will not be retried. The 5ae transfer reached 662/1,173
SHA-matched parts. AST-only API
inventory now records 341 modules / 1,734 public definitions after current model
additions. No local scientific execution was performed.

Three distinct implementation lanes have added unverified model levels. The
single-spool Brayton-shaft model integrates rotor kinetic energy from explicitly
supplied turbine/compressor powers, load torque, inertia and loss inputs, with
work ledgers and terminal speed events; it adds no gas-path model. The alkaline
bubble adapter adds caller-calibrated electrode-coverage and electrolyte-void
voltage losses to the shared HydrogenStack while preserving its Faradaic rate.
Each callback receives mandatory absolute pressure and optional electrolyte/
electrode context, with no ambient-pressure default. It does not predict bubble
fields or calibration parameters. Both have deferred
synthetic Hangang cases. Their inputs and assumptions are documented; no local
runtime/model execution has been performed. A finite-capacity, well-mixed pipe
wall now composes with the existing caloric Euler solver through an explicit
outer split, with gas/wall/ambient ledgers and one-use trace issuance. Its scope
excludes axial wall gradients and branching/finite-reservoir boundaries; the
synthetic Hangang contract is deferred.

Open-data work located RODARE v1 (`10.14278/rodare.4547`, CC BY 4.0) for
pressurized alkaline bubble/electrode observations. The acquired 1,499-byte CSV
is only a 60-condition index; its 8,586,456,345-byte numeric HDF5 archive could
not be acquired because byte-range requests were not honored. No measurements
were acquired or transcribed, so it cannot yet calibrate or validate the new
bubble-loss module. Its rights, inventory and schema gap are recorded.

Latest queue/transfer update: `1188850` USN unignited source ingestion passed.
USN-ignited was initially QOS-denied, then accepted as `1188998`; it failed
source-reader preflight because MAT variable names differed from the reviewed
profile. Its attachment size/SHA matched, so this is a schema/profile defect,
not transfer or physics evidence. The reader profile is under review for a
narrow fix; do not retry the e8 pin. The 5ae transfer reached 682/1,173
SHA-matched parts, with the next 10-part batch in flight. Independent jobs and
local implementation continue concurrently.

The 5ae part transfer advanced again to 672/1,173 matching hashes; the next
10-part batch is active. The WSK summary scope correction has been statically
AST-parsed and its case import lint now passes; no local ingestion or model run
was made.

A finite-capacity, single-node pipe-wall model is integrated around the existing
caloric Euler gas solver. It freezes wall temperature per caller outer interval
and closes gas/wall/ambient heat ledgers, with splitting and well-mixed wall
limits documented. Its deferred case is registered but has not run. Targeted
AST and Ruff checks pass; no local scientific execution occurred.

The Conda environment `h2physics-py312` was synchronized with the repository
`environment.yml`, including the editable package and development extras. The
AST-only public API inventory was regenerated and remains 341 source modules /
1,734 public definitions. Parallel local coding lanes are addressing distinct
model gaps; no scientific calculations or tests were run locally. Overall
programme progress remains a rough 30–40% estimate, not a catalog ratio.

Hangang accepted `1189012`, the WSKBIJ FDS source-observation gap contract; it
records unresolved sensor geometry/calibration and makes no raw model
comparison. It subsequently failed on the stale pin because the case still
expected the old two-file acquisition scope. The local case is corrected and
awaits a fresh pin; the 5ae transfer advanced to 732/1,173 SHA-matched parts.

The `1188998` USN-ignited source-reader failure is now scoped: the staged,
hash-matched MAT contains the documented `SIGMA`/`GEN3i` arrays plus raw
`Tavg` with no reviewed units or meaning. The source-bound reader now retains
`Tavg` as an uninterpreted immutable vector and reports unreviewed names rather
than rejecting extra raw fields; the case and data note preserve that boundary.
Targeted Ruff and AST checks pass; no model calculations were run. Do not retry
the old pin. The 5ae transfer advanced to 722/1,173 matched parts.

Job `1189012` (WSKBIJ FDS link-gap metadata) also failed on the old pin for the
same stale 27,918-byte/two-file acquisition scope. The local case now checks the
current three-file, 207,881,806-byte manifest and current linkage labels while
keeping the FDS/measurement gap explicit. Its focused documentation distinguishes
the acquired Test001 trace and its separate ingestion case. Static checks pass;
do not retry e8. The 5ae transfer has since reached 732/1,173 matching parts;
another 10-part batch is active.

Open-data search for high-pressure refuelling traces is refreshed to ten
candidate leads and zero reusable raw files. CARB HyStEP provides measured
plots/report summaries but no raw trace package or reuse grant; NREL sources are
aggregate composites, HSDS data is partner-restricted, H2FillS has registration
terms, and H2-Stations operational records expose no per-fill sensor histories.
No chart values were transcribed. The detailed blockers and qualification
contract are recorded in the source-gap manifest and data ledger.


## 2026-11-01 priority 2–7 follow-through

- Priority 2 is covered by the retained 5af failure evidence and the corrected 5ag replay: all three independent synthetic contracts passed on 5ag. These are API/software checks, not measured physical validation.
- Priority 3 PEM current-ripple acquisition is complete. The 90,759,411-byte archive matches publisher and manifest SHA-256 `47c908a780fb61636ac87dcb0cc2891edfd2a8f2e4437d7e6169cfece3639eab`. Rights, attribution and the 41 CSV members are recorded; the source reader and deferred ingestion case remain synthetic until a data-backed campaign is authorized.
- Priority 4 base snapshot was transferred through the existing Hangang wrapper and its complete remote tree passed manifest verification. Revision `1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738`, 1,449 manifest entries, manifest SHA-256 `fc76b2cdc49adfae1fc2b5af0953e3ff1cb881f11c0fa4ce3ee3467638d4747a`, archive SHA-256 `ff2758bbf353ea31b4336a43702f41f5bb47987b23989d6f9a16fa644aa8202c`. This base pin predates the latest exact-grid and Request032 audit additions; an incremental pin is next.
- Priority 5 API and model catalog now describe the alarm-to-finite-stroke bridge and exact-grid receptor sampling, including their limitations. Catalog status remains 56/82 (68%) and overall programme effort remains an approximate 30–40%; these are separate measures.
- Priority 6 Request032 is recorded as an external LH2DT native-owner dependency. This repository must not substitute its host-side SciPy mixture solver for the requested native accepted-state result contract.
- Priority 7 added an exact-coordinate receptor sampler and safety/rights audit. It does not interpolate, infer provider grid extraction, or claim plume validation; no redistribution-cleared measured plume benchmark was identified.

No local scientific tests or model calculations were run. Newly added exact-grid and finite-stroke cases are registered for Hangang but remain unexecuted.


## 2026-11-01 priority 2–7 execution update

The refreshed delta pin applies 17 changed files to the previously verified base tree. It passed full remote manifest verification at /scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-final-3d883a85; target manifest SHA-256 is 3d883a85642ad0f26bb8cb2d0e39947cb9b9b6ea448cf861e74df9dd1a4bcd4d. It includes the exact-grid sampler, alarm-to-finite-stroke adapter, corrected POSIX campaign paths, and updated records.

A three-case Hangang array was generated from that immutable tree and plan: preferred-dispersion-receptor-alarm-contract, preferred-dispersion-exact-receptor-grid-contract, and concentration-alarm-finite-stroke-valve-actuation-trace. The first submission was rejected because the wrapper's initial directory was outside the approved scratch roots; this was corrected. The second attempt from /scratch was rejected by QOSMaxSubmitJobPerUserLimit with no job ID. No case ran. Four existing user jobs were left untouched.

Priority 2 remains evidenced by the corrected 5ag synthetic contracts; priority 3 PEM acquisition/schema is complete; priority 4 source transfer and full manifests are verified; priority 5 API/catalog/development records are updated; priority 6 is documented as an external LH2DT native-owner boundary; priority 7 rights gaps and exact-grid receptor scope are documented. The three new contracts await QOS capacity. No local scientific calculations or tests were run.

Programme effort remains approximately 30–40%. Model catalog implementation status remains 56/82 (68%); this status ratio is not physical validation or overall completion.


## 2026-11-01 parallel continuation

Three disjoint implementation lanes added API compositions: the two-vent upper-layer H2 trace now has an explicit link to the existing sensor/alarm owners; the acquired CC BY 4.0 PEM single-cell IV observations can be mapped to the existing `HydrogenStack` using caller-evidenced area and temperature; and an accepted preferred HyRAM high-pressure-gas source can be linked to the existing ignition-risk binding after an exact source-rate consistency check. These adapters add no replacement process solver, inferred sensor credit, fitted PEM parameters, or new risk calculation. SLABx-LH2 is excluded from the ignition ledger because that ignition-table applicability is unestablished.

The new APIs are exported from `h2physics.adapters` and listed in the catalog/API reference. Their three synthetic Hangang contracts are registered alongside the existing priority-2–7 contracts. A metadata-only registry import confirmed 319 total cases and all six targeted contract IDs. That check exposed and corrected a dataclass `field` name collision in `preferred_dispersion_alarm`; no scientific calculation was run.

The verified 2–7 delta snapshot predates these changes, so a refreshed immutable source pin and raw PEM archive staging are required before their remote execution. The latest Hangang queue observation showed five of the user's existing jobs running; the prior submission had been rejected by QOS and created no job ID. Existing jobs remain untouched. Overall programme effort remains approximately 30–40%; the model-catalog status ratio remains 56/82 (68%) and is a separate measure.

The initial attempt to stage the full 90,759,411-byte PEM ZIP used 18 KiB command-line-safe chunks and reached 32/4,925 per-part checks before it was stopped for throughput. No final archive was installed. To avoid spending hours moving unrelated continuous logs, the Hangang ingestion/model bridge is being narrowed to the exact PEM1 baseline IV member: the full ZIP remains locally acquired and hash-verified, while a member-bound receipt will preserve its parent archive identity and only transfer the required compressed member. The last live `qstat` snapshot showed five running user jobs; no new validation job has an ID.

The first six-case parallel Hangang execution is now recorded in `HANGANG_EXECUTION.md`: job 1190418 completed with three metadata/source-contract passes and three fixture failures. The failed valve, layer-array comparison, and optional risk-package assumptions were corrected locally. The PEM source-data bridge passed its source hash/schema contract, while its model callback is explicitly synthetic. A refreshed delta and rerun remain pending; no physical-performance qualification is claimed. Overall programme effort remains approximately 30–40%; the separate model-catalog ratio remains 56/82 (68%).

The corrected eight-file delta passed full remote manifest verification at `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-46209831` (manifest `46209831a033dea24c7aaaa58398a5412fe44ea039852feff0c78f2e029a42df`). A three-case corrected rerun was refused by `QOSMaxSubmitJobPerUserLimit` while five user jobs were running; no new job ID or execution evidence exists. Retry after queue capacity returns. Overall effort remains approximately 30–40%; model-catalog implementation status is 56/82 (68%), a separate non-validation measure.
## 2026-11-01 axial annulus API

Added `AxialAnnulusDiffusion`, an axial-only annular-cylinder facade that reuses
the planar mesh and shared `DiffusionDomain`. It retains caller carrier,
diffusivity callback and trap lineage, with exact constant annular face area and
area-times-width cell volumes. Added the metadata contract
`axial-annulus-diffusion-geometry-contract` to the existing
`validation.cases.material_transport` discovery group in
`validation/hangang_plan.py`. Scope explicitly excludes radial/r-z transport
and material qualification. No local scientific calculations, tests or Hangang
access were performed; only targeted Ruff, AST and scoped-diff inspection were
performed. Targeted Ruff passed for the new module and package exports; the
case module passed Ruff with legacy E501/I001 exclusions and AST parsing. Its
metadata contract checks geometry and API lineage only and has not run on Hangang.

## 2026-11-01 priority 2–7 and data closeout

The 2–7 implementation lane has no newly identified missing local API among the requested interfaces. Priority-2 corrected three-case run evidence exists on 5ag; later six-case run evidence is three passes and three fixture failures, with the corrections registered locally but a corrected rerun still blocked at submission by Hangang QOS. Priority 3 source-backed PEM and ML-HYDPARK readers/ingestion contracts are in place. Priority 4 immutable source transfer is verified for its recorded pin, but newer code still needs its own pin before execution. Priority 5 API/catalog documentation is updated. Priority 6 remains an explicit external LH2DT native-owner dependency documented in Request032; this repository does not substitute a host-side result. Priority 7 exact-grid receptor sampling and rights boundaries are documented; no qualifying measured plume set is available.

ML-HYDPARK v0.0.5 was acquired under CC BY 4.0 with publisher MD5 and local SHA-256 verified. Its lossless token reader, deferred ingestion case and metadata are recorded; the raw CSV and Zenodo metadata snapshot were staged to Hangang scratch and their remote SHA-256 values matched. This is screening data and does not validate a physical model.

The full data-manifest report was regenerated after completing eight targeted records. No TOML parse failures remain. The metadata audit remains intentionally non-green: three identity/license fields lack authoritative fixed values (Bath license URI, H2-Stations fixed metadata hash, and PEACE fixed metadata hash), while publisher checksums and third-party rights reviews also remain unverified for multiple datasets. These are disclosed in the generated report; no values were invented. The AST public API index now lists 358 modules and 1,794 public definitions. Hangang currently reports five pre-existing running jobs; no new job was submitted and none was modified. Overall programme effort remains a rough 30–40%; catalog coverage is 56/82 (68%), separate from validation.
## 2026-11-01 continued implementation and source acquisition

Added the meter-bound electrochemical storage round-trip API on top of the existing accepted electrolysis/fuel-cell traces and finite H2 handoff. Its boundary-meter readings and native-stack electricity remain separate; it requires shared clock, energy basis, system boundary and full sequential trace windows, and never infers unmetered compression/auxiliary loads. A focused Hangang contract is registered. An independent logic review identified a post-issue meter metadata mutation gap; the receipt now seals and rechecks every meter identity, evidence, clock, basis, window and energy field. Scoped Ruff, compile and diff checks passed; no model calculation was run.

Added a lossless source-bound reader for Zenodo AEM electrolysis/crossover workbook v1 (CC BY 4.0), preserving six worksheets, exact cell values/formulas/types/number formats and source coordinates. Its ingestion-only case is registered as `aem-water-electrolysis-crossover-ingestion`; it performs no fitting, unit interpretation or physics validation. Source bytes (1,780,457 B; SHA-256 `f9729dfc0b068962843ceb089bedbc6f6eb1ea8f52e214cd7eba6550d6c334ad`) and the Zenodo metadata snapshot were verified locally; the workbook was staged through the approved Hangang wrapper and the final remote SHA-256 matched. Raw files remain ignored.

Regenerated model coverage and validation inventory after the new interfaces: 82 physical families (19 implemented, 37 native-adapter-verified, 26 implemented-unverified), with the 56/82 ratio denoting catalog implementation-status classes only; the deferred-case inventory is 413 cases, 59 profiles and 114 modules. The AST API index is 360 modules and 1,801 public definitions. Hangang queue observation showed three running and four completed existing jobs; none were changed. The new code still needs a byte-pinned source snapshot and parallel remote execution. Overall programme progress remains a rough 30–40%; that estimate is separate from the 56/82 catalog status ratio.

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

## 2026-11-01 executed thermophysical acceleration

All three existing table cases passed after fixing the report issuer call.
See [qualification report](THERMO_ACCELERATION_QUALIFICATION.md): native
BICUBIC mixed PT/PH/PS measured 3.92x faster locally, while Python isothermal
lookup measured 0.1668x. EOS interpolation checks are distinct from independent
measurements. The fuel-cell common CoolProp binding passed heat accounting
and eleven result/definition/report rejections. Programme estimate stays
30–40%; new remote execution remains pending manual user reconnection.

## 2026-11-01 storage execution

Cold-package import regression passed 4/4 after fixing a circular import.
Porous-reservoir contracts passed 4/4, including direct HEOS dynamic injection,
time self-convergence order 0.9745 and decreasing radial differences. See
[executed problem and limits](POROUS_RESERVOIR.md). This is numerical evidence,
not measured geological validation. Programme estimate remains 30–40%.

## 2026-11-01 held-current event implementation

The new held-command finite fuel-cell reserve-event API and native-prefix
case passed, including complete boundary feeds, source allocation and eight
invalid-request/mutation paths. See [API and results](FUEL_CELL_INVENTORY_EVENT.md).
Its numerical evidence does not close coupled ReactorNet event or measured
device qualification. The original programme remains active at a rough 30–40%.

## 2026-11-01 public discharge and native safety execution

The complete PRESLHY comparison replay finished with its four-experiment split
and twelve bin diagnostics intact. Conditional held-out normalized inventory
RMSE is 0.00361222122091; this is not independent flow validation. Native relief
cases passed 10/10 and the native Cantera caloric path passed. A newly executed
caloric pipe/nozzle case exposed a right-wall reflection-order defect; correction
and rerun remain active. The accepted porous-reservoir numerical-level status
is now implemented, making catalog classes 57/82 (about 70%); whole-programme
effort is still estimated at 30–40%.
