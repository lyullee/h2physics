# Hangang CPU execution workspace

## Explicit local session configuration

The optional Windows staging utilities never contain a personal WSL or cluster
account default. Before using an already-open shared session, set
`H2PHYSICS_WSL_USER`, `H2PHYSICS_RUN_WRAPPER` (an absolute normalized path to
that session's `run.sh`) and `H2PHYSICS_REMOTE_ROOT` (an explicit workspace
beneath `/scratch/`). `H2PHYSICS_WSL_DISTRIBUTION` defaults to `Ubuntu-22.04`.
These values are local task configuration, not repository credentials. Keep them
outside version control. The tools still invoke only `wsl.exe ... /bin/bash
run.sh`; they do not create SSH connections or perform password/OTP login.
They refuse missing configuration, traversal, malformed paths and a wrapper
whose filename is not `run.sh`. Publication preparation checked syntax/lint
only and did not run a remote operation.

For byte-pinned snapshots that include current uncommitted source, use
[`HANGANG_WORKTREE_SNAPSHOTS.md`](HANGANG_WORKTREE_SNAPSHOTS.md). A base commit
receipt alone does not identify dirty working-tree bytes.

## Cross-platform campaign-generation safeguards — 2026-11-01

The local PBS campaign generator now treats the source manifest as the authority
for the exact `validation/hangang_plan.py` bytes. It refuses to create a script
if the file digest differs from its manifest entry. Remote repository and plan
locations must be supplied explicitly as absolute POSIX paths, so a Windows
workstation path cannot leak into the worker `PYTHONPATH` or plan argument. The
generator also verifies the complete local source snapshot against its manifest
and pinned revision before writing a campaign. The
PBS writer builds those remote paths with POSIX path semantics and rejects
backslashes, traversal segments and control characters. Campaign generation still requires a
complete pinned snapshot (`SOURCE_MANIFEST.sha256` and `SOURCE_REVISION.txt`);
the mutable checkout is not itself a submission source. This change does not
submit or execute a job.

The prepared 5af three-case array was retried from the allowed `/scratch`
working area after an initial CLI-filter refusal from `/home01`. The corrected
submission was rejected with `QOSMaxSubmitJobPerUserLimit` and received no job
ID. No other user's or account's jobs were changed; wait for QOS headroom before
another attempt.

The 5af three-case array was later accepted as job `1190000` after the queue
cleared. It uses script SHA-256
`e6bff847067bfc41fbd853f17ce6696beb22d78705af1097e9dffae0cb6ec0e2` and covers
the finite-wall caloric pipe, Brayton shaft transient and alkaline bubble-loss
contracts. Acceptance is not a result; collect each array element's terminal
receipt before recording any pass or failure.

All three elements completed but failed their software contracts, so no family
passed on this pin: `1190001` (finite-wall pipe) returned the right outcome
shape, but the worker rejected it because `python -m h2physics.cluster_validation`
loaded a duplicate `ValidationOutcome` class under `__main__`; this is a runner
identity defect. `1190002` (shaft transient) raised a constructor error because
that pinned case omitted the required `accepted` field. `1190000` (alkaline
bubble losses) reached an assertion that expected an out-of-domain void
fraction to be rejected, but the call was admitted. That assertion is under
guard/fixture review; it is not yet classified as a physical-model defect. Any
correction requires a fresh source pin before replay. The original immutable
outcomes remain unchanged.

The immutable 5af outcomes remain unchanged. Follow-up fixes were included in
fresh pin 5ag: the runner aliases its `__main__` module to
`h2physics.cluster_validation` before importing cases, the shaft case supplies
the required `accepted` result field, and the alkaline fixture no longer clamps
invalid callback outputs before the adapter guard. All three corrected contracts
passed on 5ag, as recorded below; this establishes API/software checks only, not
physical qualification. The current local alkaline fixture also reports each
domain boundary separately.

## RODARE condition-index staging — 2026-11-01

The 1,499-byte public RODARE v1 condition-index CSV is staged at
`/scratch/CLUSTER_USER/h2physics-source-attachments/rodare-alkaline-bubble-pressure/4547/Summary.csv`.
The remote SHA-256 `24cf3cd688215f99cc28fc4c1c0f10899caa1a5fba03b22c4819c0525ede181f`
and publisher MD5 `0b500cf14501034033e5471de46341b1` match the local source
receipt. This transfer does not run a case. Submit the index-ingestion contract
only after an immutable source pin contains its reader, case and plan entry.

The new cases `kofn-detector-exact-binomial-interval`,
`concentration-alarm-finite-stroke-valve-isolation-schedule`, and
`rodare-alkaline-bubble-condition-index-source-contract` were added after pin
5af was frozen. They are registered locally but absent from that verified
remote tree; no stale 5af resubmission can exercise them. A new source manifest,
archive, remote tree verification and queue-capacity check are required first.

## Two-vent buoyant-layer contract result — 2026-11-01

## Immutable source pin 5ak — 2026-11-01

5ak is remotely assembled and verified at
`/scratch/CLUSTER_USER/h2physics-jobs/verified-5ak-8f0a901d`. Its source revision is
`8f0a901d9b54e86a8cadac508beb2e9e1422082f`; the archive is 14,225,457 B with
SHA-256 `a5a819f58f1a740e66fccbe429b98b0df7c63e4012b05b9f7608c60f413f84c2`.
The manifest contains 1,425 entries and has SHA-256
`294cc21ca4c4e20e5ba376d87887e27c1f4eb3fcbbc8cd0475e0664447651206`.
All 1,186 transfer chunks matched their per-part digests; remote verification
reported 1,425 matching files and no mismatches. The source, plan, setup and
surface-film case digests are recorded in the pin receipt. This is archive
identity evidence only; no 5ak case has been submitted or executed.

The four-element 5ak campaign is prepared at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5ak-storage-transfer-safety.pbs`
with SHA-256 `510e99b80114d33b56fc17e7d14c0e6b05b73fd7dbdabc0e20df0290bcf4776f`.
It covers the competitive Langmuir, power-law material diffusion, common-cause
k-of-n detector, and surface-film diffusion contracts. Each element requests one
CPU for at most 30 minutes. It has not been submitted; the latest queue snapshot
still showed five running user jobs.

The next source pin, 5al, adds the layer-to-O2 composition projection and its
deferred synthetic case. Its frozen revision is
`cb0bde5da039c64e957858cbd539bb936232911e`; the 1,428-entry manifest SHA-256 is
`f3f8bb907c3aa5d3bffd044afbdf995d38d84918780c7ecacbc7d54542d4775c`, and the
14,229,190 B archive SHA-256 is
`54c78141b44dfd420b3882e5ebc0b3160b382fcc447b3e0d3ab154068198d2ef`. The local
archive audit passed (license/notice present, forbidden content absent, no
manifest mismatches). Its plan SHA-256 is
`9f42eb6b8a48b956d9b2ea7a8e2efa87af45cab60137bdb5e0f858183fe875ea`, setup
SHA-256 `c0921d837af00b481df4915f60e867830cecf8f7aa4cb728f02c585e381abfb5`,
projection case SHA-256
`ff54616209b2863f0b2235e13da861054b362bf3aad895bbd0421ef0b9d22bed`, and
adapter SHA-256
`e10e3a729652275754be566164c9943d5e2dd1707430290864e836bd5c5d02fa`. Remote
transfer and full verification passed at
`/scratch/CLUSTER_USER/h2physics-jobs/verified-5al-cb0bde5d`; all 1,428 manifest
entries matched and no forbidden-content or license-file audit findings were
reported.

## 5al synthetic contracts — 2026-11-01

The 5al layer-O2 composition projection passed as job `1189682` in 1.17 s.
It retained five source samples and mapped the declared fixed dry-air carrier
to upper-layer O2 mole fractions from `0.1885500033` to `0.1914696484`. The
case rejects unsupported carrier basis and preserves the exact source clock;
it is not a homogeneous-room, exposure or human-response result.

The surface-film diffusion boundary passed as job `1189687` in 1.56 s. The
synthetic two-wall ledger residual was `1.36e-20 mol`; no material-specific
coefficient or surface kinetics is qualified. K-of-N detector reliability
passed as job `1189688` in 0.89 s, giving synthetic independent fail-to-alarm
`0.098` and combined common-cause fail-to-alarm `0.11604`. No detector
reliability data or SIL is qualified.

The competitive Langmuir contract passed on 5ak as job `1189678` in 1.29 s:
two species and two sites, maximum site loading fraction `0.4117647`, and
cross-pressure derivative `-4.15225e-7` in its declared basis. It is a
synthetic equilibrium/API contract, not a fitted material isotherm.

The 5al five-element array and five independent single-case alternatives are
prepared. The array remains unsubmitted; single jobs `1189694` (5al Langmuir)
and `1189695` (power-law material diffusion) passed in 1.02 s and 0.95 s.
Together with `1189682`, `1189687` and `1189688`, all five 5al contracts passed.

The layer-oxygen sensor/alarm handoff is frozen for pin 5am at revision
`09f2feefc0f11df0750d554890e5f4139ab8b36e` with 1,431 manifest entries.
Its local manifest SHA-256 is
`c9f48817e66f73bfde9e424f40371d70340720d4e9d1a6ec68951787fed0b75e`; its
archive SHA-256 is
`ad11fa87681c5add1df60202b42d32117c9c5de0de67c4d70129f7a7e023017b`. Remote
tree `/scratch/CLUSTER_USER/h2physics-jobs/verified-5am-delta-09f2feef` has an exact
1,431-path match and all target manifest entries passed. Its archived plan SHA
is `fb9f98443251224d3528d0c8a415bc61479239d4b575b3058c4af2483d5dced1`. The
first single-case script contained stale local paths/hash values and was held
from submission, then removed. A replacement was generated from the verified
remote tree at `/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5am-layer-oxygen-alarm-handoff-verified.pbs`
(SHA-256 `31f19a0800e03f3f8482e02f2ee7f9bd376862901009fd5cee531f6aa8b43477`).
It matches the remote revision/manifest/plan/setup. Job `1189857` passed in
1.29 s. The synthetic six-sample upper-layer deficit trace reached one
caller-configured alarm trip at 0.4 s; exact clock/location mapping,
sensor/alarm/evidence binding and context-mutation rejection checks passed.
The authored reference/sensor/threshold values do not validate a real detector
or qualify facility exposure. The signal remains upper-layer only, with no
room-average or human-response output.

The array path is
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5al-storage-transfer-safety.pbs`
(SHA-256 `252a7961b0d6588355b9e3680378072a2c4fe3aa71a85d670b0b082f93db0620`).
Single-case scripts are `5al-langmuir.pbs` (SHA-256
`bfec6c9fd8361b8524c6183761096fef2052b91efb211863daf21c642f446f67`),
`5al-power-law.pbs` (`7568fe60162d51f26a2a89cab945883d365bd53ae29c0eb7870f1f018e063b3e`),
`5al-kofn.pbs` (`b20d87c1284fdd31ff4db52e33e829632428e520a7b6f82691a40a79c2481095`),
`5al-surface-film.pbs` (`6c489b25274f767896dd764e455ae14bedfd04c9334bd8efe2e865921e2b740b`),
and `5al-layer-o2.pbs` (`d9b9e01fd5c24f5f6e1af7813e12889569dcd9251b58604417764de628cf3298`).
Each one-case script requests one CPU and a 30-minute ceiling. Only the
individual jobs listed above were submitted; the array remains untouched.

The prepared 5ai three-case array was checked again on 2026-11-01. Submission
was explicitly refused by the scheduler with `QOSMaxSubmitJobPerUserLimit`;
no case entered the queue and no job ID was issued. The queue snapshot showed
five running user jobs. Existing jobs were preserved.

Job `1189567` on immutable pin 5ai
(`3ce801fa7a1e7f2e8f6c2afdb3037e000c9a691f`) passed
`two-vent-hydrogen-buoyant-layer-accumulation` in 10.22 s. Its synthetic
trajectory retained H2 mass residual below `1.58e-16 kg` and maximum vent mass
residual below `3.47e-17 kg/s`, within the declared interface/flow regime. The
result is limited to a vertical buoyant source in still air, fixed ambient
temperature and two one-way vents; it is not experimental, CFD or facility
qualification.

The next short independent array is prepared at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5ai-short-storage-material-safety.pbs`.
It covers competitive Langmuir equilibrium, power-law surface solubility to
diffusion, and k-of-n detector reliability. No job ID was issued while five
current/user jobs occupied the observed QOS headroom; unrelated jobs were left
untouched.

## Compartment-network fixture correction — 2026-11-01

The first pinned synthetic compartment-network case, job `1189474` on pin 5ah,
failed an assertion before its ledger and rejection checks. The case required
the adjacent-room H2 fraction to be positive at every requested time, including
the initial sample where its declared initial fraction is zero. This was a
fixture assertion defect, not evidence of a model conservation failure. The
local correction checks the final requested sample after transport. It was
included in pin 5ai and job `1189504` passed the complete synthetic contract.
The original job result is retained unchanged under
`/scratch/CLUSTER_USER/h2physics-jobs/results/5ah-compartment-network/1189474`.

Static equation review confirms each room uses fixed `N_i=P_i V_i/(R T_i)` and
the prescribed stream balance before solving a linear H2-fraction transport
system with a matrix exponential and external H2/carrier ledgers. The current
model accepts the configured numerical tolerance for flow balance while holding
room inventories exactly fixed, so keep that tolerance small compared with the
scheduled flows. This model assumes ideal gas, fixed P/T, complete mixing and
caller-supplied flows; it does not represent pressure-driven ventilation,
buoyancy or stratification. The failed job ended before its ledger checks; job
1189504 later ran those checks on the corrected pin.

## PEM reader contract result — 2026-11-01

The 5ah source pin `1fe679d69162ef1a551f997e00bf9e5ec8c4418f` was transferred
and verified at `/scratch/CLUSTER_USER/h2physics-jobs/verified-5ah-1fe679d6`.
Archive SHA-256 is
`4925bb14751bf010e5b6bdc9c5608169d52ef75b8f5e37ebb436430706da9d42`; manifest
SHA-256 is `9b917bed40f6d62675d563a97c238f84861ab8dcab6156d2913946798b2a18e7`,
with all 1,425 entries verified. The `pem-ripple-streaming-reader-source-
integrity` case passed as job `1189469` in 1.15 s. Its synthetic archive retained
2 IV rows, 3 continuous-log rows and 36 reported-fit rows; source intervals
remained `[1.007, 3.997] s`, and altered result projections and changed archive
bytes were both rejected. No publisher data was staged or evaluated. This is a
reader/API integrity contract only, not a calibrated electrochemical model or
physical-data validation.

## Latest result — corrected 5ag contracts — 2026-10-31

Fresh immutable snapshot `f43e8f636829e1fae2a4aa38f397b6049a88628e`
(`5ag`) was transferred and verified at
`/scratch/CLUSTER_USER/h2physics-jobs/verified-5ag-f43e8f63`. Archive SHA-256 is
`fff279881ca27a844b6b0b719ec18d182b3ddd9ad2bf068d14db8371f7057b0b`, and all
1,421/1,421 source manifest entries passed. The source manifest SHA-256 is
`3bd713cd8967f5acebfef45a872dc9fa34232bd2d676fc6d8fb110aea2b5818a`. The pin
contains the three harness corrections and the Brayton speed-event retry; it
does not contain the PEM ripple reader lane.

Four corrected deferred contracts passed on this pin:

- Job `1189381`, `hydrogen-caloric-pipe-finite-wall-energy-closure`: 1.84 s;
  maximum combined energy residual `5.25e-11 J`.
- Two elements of array `1189394` passed: `alkaline-bubble-electrode-and-
  electrolyte-losses` (1.12 s; three invalid coverage/void inputs rejected
  independently) and `hydrogen-brayton-transient-shaft-balance` (1.19 s;
  kinetic-energy ledger residual `0 J` in the nominal synthetic fixture).
- Job `1189400`,
  `hydrogen-brayton-transient-shaft-speed-event-retry-20261031`: 1.02 s; the
  speed limit is terminal and retains the event without clipping speed.

These are synthetic API/software contracts, not physical-model qualification.
The finite-wall fixture uses one mixed wall node and first-order splitting; the
bubble and shaft cases use prescribed synthetic inputs. Job `1189334` failed
before case entry because the first locally generated script carried an
incorrect setup-script SHA-256 (`...fb2`); the verified file hash is
`c0921d837af00b481df4915f60e867830cecf8f7aa4cb728f02c585e381abfb5`. The
generator was rerun with the observed hash, and the four listed outcomes are
bound to the correct setup digest. A three-case submit was refused at the QOS
limit; splitting into one job plus a two-element array allowed the cases to
run without touching other jobs.

## Fresh source pin and current submission attempt — 2026-10-31

Source revision `93c86863c13957c73b09cc9f32548aadf709385d` (snapshot `5af`)
was staged through the existing Windows WSL `run.sh cpu` connection. All
1,183 transfer chunks matched their local SHA-256 receipts. Remote archive
`/scratch/CLUSTER_USER/h2physics-jobs/incoming-5af-93c86863/source.tar.gz` is
14,185,810 B with SHA-256
`b3f56b254eda38046058cbcc506b66f493350bacfe27057e6b2daa356e9adb3e`. It was
extracted to `/scratch/CLUSTER_USER/h2physics-jobs/verified-5af-93c86863`; the
revision, 147,321-byte source manifest, manifest digest
`7bd7f2100dcbfb8d57d2d1b16fe0c54931cede75526beda3b59e6dee14f7572d`, and all
1,415/1,415 manifest entries verified.

A three-element array was generated at
`/scratch/CLUSTER_USER/h2physics-jobs/campaigns/5af-three-core-validation.pbs`
(SHA-256 `e6bff847067bfc41fbd853f17ce6696beb22d78705af1097e9dffae0cb6ec0e2`).
It targets the finite-wall, transient-shaft and alkaline-bubble cases using
queue `5thEx_cpu`, account `na1620`, 30-minute wall time and pinned
`field=che;appl=in_house` metadata. The first submission at five active user
jobs was refused by QOS; a fresh queue check after two jobs completed allowed
array `1189215`. All three workers ran, then exposed harness defects described
below. No physical-model acceptance is claimed.

## Initial 5af result — 2026-10-31

Three independent 5af cases were submitted as array `1189215` after QOS
capacity opened. Array elements `1189216`, `1189217`, and `1189215` all reached
the case entrypoint and completed in about 1–2 seconds, but all three failed
their validation harnesses:

- `hydrogen-caloric-pipe-finite-wall-energy-closure` (`1189216`): the finite-wall
  simulation and assertions ran, but the case returned `None` rather than an
  explicit `ValidationOutcome`. The case now returns an explicit acceptance
  record with thermal and energy-ledger metrics.
- `hydrogen-brayton-transient-shaft-balance` (`1189217`): the result constructor
  omitted the required `accepted` argument. It now returns explicit acceptance,
  scenario/termination data and declared limitations; a maximum-speed event
  retry case is also registered for the next source pin.
- `alkaline-bubble-electrode-and-electrolyte-losses` (`1189215`): the adapter's
  `[0, 1)` guard was correct, but the case fixture used `min(0.95, value)` in
  every callback, silently clamping invalid test inputs before they reached the
  guard. The fixture now passes its pressure-adjusted callback values through
  unchanged and checks invalid anode coverage, cathode coverage, and electrolyte
  void fraction independently. This is a deferred-case fixture defect; the
  adapter's invalid-value guard was not at fault. Targeted Ruff and AST checks
  pass for the repaired bubble case. Retry only from a fresh pin containing all
  three corrections.

These are software-contract failures, not accepted physical results. Do not
retry the immutable 5af pin; prepare and verify a fresh source pin after the
repairs, then submit independent cases when QOS admits them.

Job `1185860` (`carrier-original-binding`) failed because the case attempted to
enable writes on a bytes-backed immutable cache and did not catch the expected
`ValueError`. The case now treats that rejection as the contract and checks
`result.require_current()` before/after no mutation. This was a deferred-case
harness issue, not a model failure. The correction has not been replayed and
does not count as scientific qualification.

## Latest verified source and accepted jobs — 2026-10-31

Snapshot revision `9048413b68025235753242dcb93efb68d9afc477`; archive SHA-256
`5a34abfd652c7dbe6ff6ba41ca7981082e42bffc70533e805c638ef33f99250c`
(3,780,321 bytes); manifest SHA-256
`9034a8102d3bbe6b53310ab122b5a359acb1d8918ba62dc065343999e10eb4ca`; all
1,060/1,060 entries verified. `1185710` (offline core-flood source ingestion)
passed offline metadata/listing hash checks and four staged workbooks; this is
source-ingestion evidence only, not physical validation. `1185709` CSTR entered
but failed the fixed geometry/site-domain invariant after initialization and
enthalpy fixes; the exact subcondition is under investigation, so no CSTR pass
is recorded. A local diagnostic patch separates volume, site-density, and
temperature checks with native-value diagnostics without loosening bounds. Root
cause remains unknown; retry after a fresh snapshot. Both used external logs.
This capture predates the canonical
Krg/Krw mobility guard and staged-turbine fixture correction; a newer snapshot
is required to evaluate those changes. From older `64a31`, `1185715`
(`thermal-target-domain`) and `1185716` (`impact-elastic`) passed synthetic
domain-contract checks, supported by outcome JSON; they are not independent
validation. Earlier failures remain pinned to their source revisions.
Completed `64a31` outcomes: `1185718` thermal-target-exposure-history failed
with ValueError because left-held history length did not match edge/interval
shape (case input/contract issue, not independent validation). `1185727`
impact-native-pool passed after exact pinned optional `dynamiclh2poolx`
installation, scoped to its deferred synthetic contract only; it is not physical
qualification. `1185719` PIFIRA receipt, `1185720`
impact-zero-contact, `1185722` impact-dryout, `1185723` impact-prefix, `1185724`
impact-history-issuer-integrity, `1185725` impact-intercontact-heat, `1185726`
impact-missing-heat, `1185729` impact-refinement, and `1185730`
thermal-target-lossless passed deferred synthetic contracts. These passes do not
establish independent scientific validation. Logs are external.
From `64a31`, `1185735` failed on unequal edge/sample fixture shape; adjacent
pair indexing is corrected locally. `1185736` relief-lift-travel and `1185750`
relief-lift-leakage failed because the plan omitted `fixture_factory`; a local
fallback now constructs synthetic cases using reviewed native LH2DT protection,
shared nozzle and native state types, including wrong-state rejection. It remains
unverified pending recapture. `1185737`–`1185740` failed phase-partition PQ
component/mole consistency checks, not independent validation. `1185752`
impact-native-pool passed after exact pinned optional dependency installation,
limited to the deferred synthetic contract. No physical qualification is
established. Logs are external.

## Previous verified source snapshot — 2026-10-31

Verified snapshot revision `64a31d2784b72f66d66a77accb01e18e3d711a4f`; archive
SHA-256 `3811c36a140e38200a81c6b3d622a9ebb547d2d9350bcd36f8d5f9f1848216cb`
(3,776,678 bytes); manifest SHA-256
`7bc132d660b514a657068d1b2ad41d6a417849730812437b78eb0fb32583ac1a`.
All 1,060/1,060 entries verified; raw/processed data count is zero. Jobs
`1185638` (CSTR) and `1185639` (core-flood ingestion) failed after case entry:
Cantera controller initialization preceded the `mass_flow_rate` read
incorrectly, and numeric Mendeley version input was rejected because a string
was required; local fixes are in progress. `1185646` failed its synthetic
mobility role-rejection assertion, now corrected to use canonical Krg/Krw phase
guard. `1185647`, `1185661`, and `1185662` failed before staged-turbine scenario
assertions because the fixture passed a callable where the open-Brayton API
requires a native phase. The fixture is corrected locally but unverified.
`1185664` impact-baseline and `1185665` thermal-target-refinement passed. Four
passes total (`1185448`, `1185452`, `1185664`, `1185665`) do not establish
scientific/source/equipment qualification. Mobility/staged-turbine jobs were
accepted after initial QOS refusal; qsub logs/results are outside the source
tree. `1185550`/`1185557` were launch/log-only failures against older `8105`
when PBS logs polluted the pinned source; external log paths now work. Those
older outcomes remain historical.
Job `1185687` (`thermal-target-pulse`) passed its deferred synthetic energy
ledger on `64a31` with maximum residual about `1.14e-8 J`; this does not qualify
the model scientifically. After QOS reopened, `1185698` (`thermal-target-domain`)
and `1185699` (`impact-elastic`) were accepted; results are pending, with logs
outside the source tree. Initial QOS refusals had no job IDs.

## Prior Hangang result matrix from snapshot 64a31 — 2026-10-31

- `1185448` thermal-variable, `1185452` fragment, `1185664` impact-baseline, and
  `1185665` thermal-target-refinement entered and passed.
- `1185450` entered CSTR then failed on unavailable Cantera method
  `getPartialMolarIntEnergies`; `1185453` entered core-flood then failed fixture
  import before ingestion.
- On source `64a31`, `1185646` failed synthetic mobility role-rejection, now
  corrected with the canonical Krg/Krw phase guard. `1185647`, `1185661`, and
  `1185662` failed the staged-turbine phase guard before their scenario checks:
  fixture passed a factory to `run_open_cycle_brayton`, which expects a native
  phase. The fixture is corrected locally, still unverified.
- On older `8105`, `1185507` failed exact float equality in its synthetic
  contract with no physical/source evaluation; now fixed with `isclose`.
  `1185550`/`1185557` were launch/log-only attempts whose PBS logs polluted the
  pinned repository. External log paths now work.

The complete corrected snapshot is now captured and verified as documented
above. The earlier `8105` errors do not establish full scientific qualification.

This note tracks the user's current Hangang CPU campaign setup. All remote
commands use the existing `run.sh` shared connection; this project does not open
SSH/SCP connections or store credentials.

## Workspace and source snapshot

- Remote workspace: `$HOME/h2physics`
- Python: 3.12.9
- Core environment: `.venv` with NumPy, SciPy, pytest and packaging
- Additional providers available in the shared environment: Cantera, CoolProp,
  fluids, openpyxl and h5py
- Original snapshot: `source/repository`
- Prior pinned snapshot: `source/repository-live-20261030-1ecfaef1`
- Current verified job snapshot: `/scratch/CLUSTER_USER/h2physics-jobs/live-341c2a1375f41a74/repository`
- Deferred case output: `results`
- Source transport uses bounded base64 pieces as arguments to the required
  `run.sh cpu` command. The locally generated archive excludes Git-ignored raw
  datasets and local build outputs. Its remote SHA-256 is checked before
  extraction. No public repository or third-party storage is used.

## Current Hangang batch — 2026-10-31

Both two-case attempts failed before model entry. Job `1185219` lacked PBS aliases
for the site's Slurm job variables; retry `1185237` then exposed a separate
selected-subset/full-plan index mismatch. Neither scientific case started. The
corrected generator maps `SLURM_JOB_ID`/`SLURM_ARRAY_TASK_ID`, creates a per-job
compute-local `/tmp` fallback, prepends pinned `/src` to `PYTHONPATH`, and
resolves each expected case ID in the full plan. The immutable source used for
those attempts is revision `1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738`,
archive SHA-256 `341c2a1375f41a747cbc5c853fd0d42abdf1cc6d159a4b43a005d5fb234ac4f3`
(3,513,400 bytes), with all 973 source-manifest entries verified; manifest SHA-256
is `7797f828c08d2f215302b058dc06e6cae242aadbf980ac44d7c30c252f230ca5`. The
array plan SHA-256 is `f2b0fd8a020411f5386dbd5ad70e8a2c8187222eaa25b14225268c81c0b014a5`;
the corrected scratch-remapped campaign SHA-256 is
`3c8ee0ce320a64f1253716010a0f2b076223740802fed1b21495d482ff6c1e2c`. The
two cases are `cantera-finite-flow-catalytic-cstr` and
`thermal-target-variable-capacity`. The generated array explicitly prepends the
pinned checkout's `src` to `PYTHONPATH`, avoiding the virtual environment's old
editable-install target. Results are written under this scratch project. The
341c campaign is superseded after the two launcher defects. The replacement
37752360 archive hash and its own manifest checks passed, but the capture was
incomplete: it omitted the `src/h2physics/data` package. Its three-case array was
rejected at the QOS submission limit; single-case job `1185303` was accepted by
the scheduler, then failed before
the model entrypoint with `ModuleNotFoundError: No module named 'h2physics.data'`.
The 341c capture had the same omission. Neither snapshot can validate affected
contracts, despite internal archive/manifest consistency. The partial replacement
archive was halted; the next capture must include all source files while excluding
only ignored raw/cache paths. CSTR correction is also required before that case.

The four CC BY 4.0 H2/water core-flood workbooks have been staged separately in
the user's scratch allocation under `h2physics-core-flood-20261031-8759d1a8054c`.
Hangang SHA-256
checks and byte sizes match all four publisher entries (9,825,388 bytes total).
The transfer receipt is outside the repository. These data are not in the source
archive, and no data interpretation or curve fit was performed.

## Latest checksum-verified but incomplete snapshot — 2026-10-31

Archive `37752360ffd3f403ecc57ec7f74b4b3541538b82776061df7ff1f7c673da2b3`
(3,520,086 bytes), revision `1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738`, has
manifest SHA-256 `0e99afc4f2bde45e76c17186a36d58cb76524e61bb083d8d9bf331a08040630f`;
all 976 listed entries verified. It is staged under the user's scratch allocation as
`h2physics-jobs/live-37752360ffd3f403/repository`. Its 96-case plan includes
fragment flight, the core-flood reader and launcher fixes, but predates the last
`site_residual` repair in the flowing CSTR and omits the entire `src/h2physics/data`
package. Do not submit future work from this snapshot. A replacement capture is
being built from all tracked and nonignored source files, excluding only raw data.

The `13e720` corrected-CSTR candidate was captured locally with the site-residual,
Slurm/PBS, compute-local temporary directory, PYTHONPATH, and expected-case
selection fixes, but is also incomplete. Its expected archive SHA-256 is
`13e720cff1a902651db1adfd89259b9eb0c690e489979f9a663feaad6f450755`, size
3,521,722 bytes; manifest SHA-256 is
`171297f12990288d0d452fcf33bef0504efd342ea2fa2ca6810f0c8ee78a2fff` over 976
source entries. This local candidate is not a remotely verified complete source;
do not submit from it. Snapshots `341c`, `37752360`, and `13e720` are all incomplete.
`341c` and `37752360` have remote archive/manifest checks, but both omit
`src/h2physics/data`; `13e720` is only a local candidate in this record. None of
the three entered a scientific case. The corrected full capture is under
construction. The current Hangang plan contains 97 cases across 19 profiles and
36 modules. Latest repository inventories record 371 cases / 56 profiles / 105
modules; 1,455 public API definitions / 241 modules; 1,748 bound relative
imports with zero missing or unresolved; and 3,941 Markdown links / 340 files
with zero missing. These structural inventories are independent of case results.

## Latest Hangang first-wave results — 2026-10-31

- An earlier summary of this first wave was superseded by the outcome JSON
  audit: `1185448` and `1185452` entered and passed; `1185450` entered CSTR then
  failed on unavailable Cantera surface method `getPartialMolarIntEnergies`;
  `1185453` entered core-flood then failed importing its absent fixture before
  ingestion.

The passing jobs are case-level evidence only; they do not establish full
scientific qualification. The `341c`, `37752360`, and `13e720` snapshots above
remain incomplete. Build and verify a fresh complete snapshot before the next
launch.

The previous verified 2026-10-30 snapshot is present at
`$HOME/h2physics/source/repository-live-20261030-e84ba5fa/repository`.
Its source revision is `f4eb4c4a7e4352777d5fb6fde51e125f6be4bcc0`, the
archive is 3,716,225 bytes with SHA-256
`e84ba5fa596231b8582f07b0e4007bce8812fb4496b8a1871bfc5baf149186cd`, and the
1,047-entry source manifest has SHA-256
`4214eacbb432581c9eee301af89a743d070771cfbb9bf6e06428038226c445a7`.
The archive digest matched before extraction and every manifest entry passed
`sha256sum -c` on the Hangang login node. This is a static source-integrity
check only: no model cases, tests, benchmarks, installs, or PBS jobs were run.

The current snapshot, including the latest cryogenic MOF source reader and
finite-wall impact-trace integrity changes, is at
`$HOME/h2physics/source/repository-live-20261030-1ecfaef1/repository`. Source
revision: `782d9a7326f85a94bdbfaeb651fd380809fba724`. The archive is 3,725,556
bytes with SHA-256
`1ecfaef10c633d9f20fa6e48c32ae065ffe0f5ab8826bd7ca84d21ee4314bd03`; all 1,050
manifest entries passed remote `sha256sum -c` with manifest digest
`89ec64dc0d3b7080a987d4b40cd30889821119b6776b86f383bdfc70c338a43e`. The
out-of-tree `TRANSFER_RECEIPT.txt` records these values. No model case, scientific
test, benchmark, install or scheduler job was run or submitted.

The first installable snapshot contained 953 files in a 3,441,510-byte archive
with SHA-256 `5bc57ff245931a2fc942f50b08159ddc50f73865e4b0f55c0be6017588f92103`.
An earlier working-tree snapshot contains 964 files in a 3,428,289-byte archive
with SHA-256 `d3c9fc2249900f588492f89e02e3a0d02d19f101dd394fd93b14b40914134401`,
base Git revision `1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738`, and source-manifest
SHA-256 `be2146aeb0d4102a98748548983d68a71b08ec228dd64c06ad03d25392ff6b6f`.
The source manifest for that earlier snapshot was verified on the login node and
Python imports resolved to it. It predates the subsequently added
CLI-filter-comment option, joint uncertainty case, porous-reservoir module,
finite-separator callback guard, and later API/document updates. An earlier local
source-only archive contains 973 files (the operational note itself is excluded),
3,435,311 bytes, SHA-256
`10d6fa48fd3b117cdd9b542be416c82dd23f66013af76125d04222bc722fa463`. It was
not transferred because the shared connection closed during the last status
request; both older archives are superseded by the current pinned snapshot above.
Keep the raw BAM archive outside the source tree; its case is
synthetic and does not require publisher files.

The remote virtual environment currently reports Python 3.12.9, NumPy 2.5.4,
SciPy 1.18.1, pytest 9.2.0, packaging 26.3, Cantera 3.2.0, CoolProp 8.0.0,
fluids 1.3.1, openpyxl 3.1.5 and h5py 3.16.0. These pins describe the installed
environment; native projects such as HyRAM+, SLABx-LH2, LH2DT and FDS still
need their own version-compatible setup before their cases can be admitted.

An earlier wrapper connection check failed; on 2026-10-30 the user re-established
Hangang access and the prescribed CPU wrapper succeeded. The new immutable snapshot
above supersedes the previously stale local-only archives. The mixture V/U case is
registered in the Nurion plan only. The open-cylinder contract is in both Hangang
and Nurion plans.

## Runtime safeguards and current evidence

`scripts/hangang_core_setup.sh` caps OpenBLAS, OpenMP, MKL and Numba at one
thread per single-core PBS worker. This avoids inherited login-node BLAS settings
creating dozens of threads per Python process. The installed source imports under
Python 3.12.9 when these limits are active. The first uncapped import attempt
exhausted login-node thread resources and was stopped; it was not a model run.

`validation/hangang_plan.py` currently selects 96 deferred contracts across 19
profiles and 36 case modules, including
carrier-conversion, finite-target, BAM-parser, SLABx-LH2 parallel-snapshot,
joint-uncertainty, porous-reservoir, fuel-cell trial exchange, Brayton map
composition and operating-point, synchronized Cantera fuel-cell coupling,
cooled Brayton/bleed point, engine boundary-stream, crank-angle feed and shared-nozzle
contracts, BAM unit projection, porous-reservoir CoolProp binding, finite-wall parcel
impact sequencing, and source-bound facility-uncertainty contracts,
HyRAM source-transition, prescribed-flow open-cylinder, finite-mixture interval
and adaptive ODE, and pool accepted-edge contracts.
It also includes two accepted-edge phase-withdrawal ledger cases for finite relief,
all nine finite-relief-lift cases (including two accepted-edge withdrawal checks),
two adaptive finite-adsorption dynamics cases, two compressor anti-surge cases,
two fuel-cell reserve feedback cases, three finite cylinder-wall cases, three
staged turbine-cooling cases, and five Cantera/CoolProp hydrogen
fuel-compression cases. It also includes accident-to-consequence orchestration,
sensor calibration, oxygen threshold-deficit integration, PEACE raw-token intake,
piston heat-flux and crank-angle mapped-feed contracts. The PEACE parser case is
synthetic; its four source files are acquired and checksum-verified but have not
been mapped to observations or used to qualify a model.
The current plan also includes a variable-heat-capacity thermal target, finite-feed
catalytic CSTR, conditional fragment flight/ground-impact, and source-bound H2/N2
core-flood workbook ingestion. The three physics models are
implemented_unverified; the data reader checks publisher hashes but does not
normalize or fit the measurements. Confirm the uploaded source manifest contains
these latest contracts before generating a campaign; an earlier snapshot is not
a substitute.
`scripts/generate_hangang_campaign.py`
creates a hash-pinned PBS array and never submits it. By default it includes
the complete pinned set. Repeat `--case-id <identifier>` to generate a smaller
explicit batch if the site's per-user submission limit rejects the full array;
unknown and duplicate identifiers fail before a script is written. Each case
remains an independent array element, preserving parallel work within that
admitted batch. Pass
`--slurm-cli-filter-comment 'field=che;appl=in_house'` to pin the site's
`showappl` CLI-filter metadata in the generated script as
`#SBATCH --comment=field=che;appl=in_house`; PBS treats that directive as a
comment. The generic array writer keeps this annotation optional for existing
callers, while the Hangang campaign generator requires it explicitly. Its
validator admits only `field=<simple-token>;appl=<simple-token>` (letters,
digits, underscore, dot or hyphen), with no whitespace, extra fields or shell
syntax.

## Observed Hangang admission attempt

These values are observations from one failed/preflight campaign, not defaults
or guarantees for future allocations: `showappl` accepted HPC field `che` with
application `in_house`; the requested queue/account were `5thEx_cpu`/`na1620`.
The site rejected an array size of 16 under the selected QOS. Subsequent metadata
calls against `/scratch` and `/appsdata` hung, so no further job was submitted.
Recheck current scheduler policy and storage availability before any future
submission, and record new observations separately from the generic generator
contract.

No scientific case, model, benchmark or PBS job has run from these snapshots.
Manifest verification and imports succeeded on the Hangang login environment.
A 16-case array was rejected by the selected QOS, and later writes/listing under
both approved job-storage roots (`/scratch` and `/appsdata`) stalled. No retry
or job was submitted after that observation. The GPU shared connection was not
available at the last check. Scientific case acceptance remains pending on
compute nodes. Native providers such as HyRAM+, SLABx-LH2, LH2DT and FDS still
need their own version-compatible setup before their cases can be admitted.

## First-wave contract

The current first wave is a single-node, one-CPU-per-case array. Cases run in
independent PBS array elements, with BLAS/OpenMP thread caps and per-case result
receipts. The included SLABx-LH2 concurrency contract uses a synthetic,
thread-safe native fixture; it does not establish safety of the real provider's
process-global width state. Real parallel calls still require caller-provided
worker-isolation evidence.

## 2026-10-31 source snapshot and queue checkpoint

The immutable Hangang snapshot at
`/scratch/CLUSTER_USER/h2physics-jobs/live-68828c63d88db6edb0ede57c170ae94ed0239de55e2bc8f8bebae34445cafc80`
uses revision `f2086cad639364c8ccca9bddd86d5f0e6d156c1e`, archive SHA-256
`68828c63d88db6edb0ede57c170ae94ed0239de55e2bc8f8bebae34445cafc80`, and
manifest SHA-256
`a006207f9e45c8e54d543ffdb87f98c325d5c83a62023ac216cee8f2a55fb2df` (1,060
entries). Local and remote archive/member checks matched, all manifest checks
passed, and the archive contains no raw workbooks, PDFs, bytecode, or processed
data. Campaign files, results, and per-case output logs are siblings of the
immutable source directory.

The first eight admitted jobs, 1185822, 1185823, 1185825, 1185826, 1185827,
1185828, 1185830, and 1185831, all failed before case entry because the profile
looked for `/scratch/CLUSTER_USER/h2physics-jobs/.venv/bin/python`, which did not
exist. These are launcher failures, not model outcomes. The path now resolves
through a scoped symlink to the existing `/home01/CLUSTER_USER/h2physics/.venv`;
the verified interpreter is Python 3.12.9 with Cantera 3.2.0 and SciPy 1.18.1.
Pinned snapshot `src` remains first on each worker's `PYTHONPATH`.

Retries entered the deferred cases: 1185847 `carrier-reverse-cycle` passed;
1185848 `adsorption-dynamics-closed-lumped-energy` failed its input/callback
issuance contract and is awaiting a source fix; 1185853
`carrier-native-ammonia` passed; 1185854 `carrier-rejected-input` passed;
1185858 `carrier-finite-material` passed. Job 1185860
`carrier-original-binding` failed in its deferred case when enabling writes on a
bytes-backed cache raised an uncaught `ValueError`; the case now expects that
rejection and checks currentness on the unmodified result. QOS refusals
reported `QOSMaxSubmitJobPerUserLimit`; refused requests received no job IDs.
Continue with disjoint admissible cases as the per-user limit allows. Risk
profile cases remain deferred until the separately pinned native-risk
environment is installed and exposed to the worker profile.

## 2026-10-31 f2086ad deferred-contract outcomes

All outcomes below are scoped to immutable revision `f2086cad639364c8ccca9bddd86d5f0e6d156c1e` (archive SHA `68828c63d88db6edb0ede57c170ae94ed0239de55e2bc8f8bebae34445cafc80`, source manifest SHA `a006207f9e45c8e54d543ffdb87f98c325d5c83a62023ac216cee8f2a55fb2df`). They are deferred synthetic/API contracts or data-ingestion checks; passing them does not validate a physical model.

Passed: 1185847 carrier reverse cycle; 1185853 carrier native ammonia; 1185854 carrier rejected input; 1185858 carrier finite material; 1185863 carrier weak lifecycle; 1185864 carrier thermal reference; 1185866 carrier packet boundary; 1185867 thermal target variable capacity; 1185868 thermal target exposure history; 1185870 BAM synthetic text parser; 1185871 BAM synthetic unit projection; 1185873 core-flood branch-specific mobility; 1185885 engine boundary-stream ledger; 1185888 compressor anti-surge boundary support.

Contract/fixture failures: 1185848 adsorption closed-lumped-energy (input/callback issuance; source fix pending); 1185860 carrier original binding (attempt to enable writes on immutable bytes-backed cache was not caught; case correction pending); 1185874 oxygen threshold deficit (this source predates the adjacent-slice correction and raised `zip() argument 2 is shorter than argument 1`); 1185876 and 1185877 staged turbine ledger/pressure rejection (native phase precondition rejected the `gri30.yaml` Cantera phase); 1185884 Brayton compressor/turbine map pair (same native phase precondition); 1185886 open-control-volume forced-flow (fixture omitted reviewed mechanism metadata); 1185889 sensor calibration recovery (entrypoint omitted explicit `ValidationOutcome`). The sensor case now returns named outcome metrics after its calibration and boundary-limit assertions; this local fix is unverified pending retry. These are not physical-model validation results. Keep them pinned to this revision and retry only with corrected source.

Jobs 1185822, 1185823, 1185825, 1185826, 1185827, 1185828, 1185830, and 1185831 were launcher-only failures before case entry: profile Python path missing. The scoped venv symlink now resolves to the existing verified Python 3.12.9 environment. Every retry used a unique external stdout/stderr path under the sibling campaign directory. QOS refusals reported `QOSMaxSubmitJobPerUserLimit` and created no jobs. Risk-profile cases remain deferred until the reviewed isolated native-risk packages are installed and exposed to the worker.

### Supplemental 6882 outcome ledger — 2026-10-31

Deferred contract passes confirmed by `outcome.json`: 1185847 `carrier-reverse-cycle`; 1185853 `carrier-native-ammonia`; 1185854 `carrier-rejected-input`; 1185858 `carrier-finite-material`; 1185863 `carrier-weak-lifecycle`; 1185864 `carrier-thermal-reference`; 1185866 `carrier-packet-boundary`; 1185867 `thermal-target-variable-capacity`; 1185868 `thermal-target-exposure-history`; 1185870 `bam-jet-fire-text-parser`; 1185871 `bam-jet-fire-unit-boundary-projection`; 1185873 `core-flood-branch-specific-relative-mobility`; 1185885 `hydrogen-engine-boundary-stream-ledger`; and 1185888 `compressor-anti-surge-boundary-support`.

Deferred contract failures with no physical validation claim: 1185848 `adsorption-dynamics-closed-lumped-energy` (admitted inputs/callback freshness); 1185860 `carrier-original-binding` (case did not catch expected write-enable `ValueError` on immutable bytes); 1185874 `oxygen-threshold-deficit-integral` (old interval slicing raised a zip length mismatch; fix is only in later local source); 1185876/1185877 staged-cooling ledger/pressure rejection (Cantera phase precondition); 1185884 Brayton compressor/turbine map pair (same Cantera phase precondition); 1185886, 1185892, 1185893 engine flow/valve/crank cases (fixture lacks reviewed mechanism metadata); 1185889 sensor recovery (missing explicit `ValidationOutcome`); 1185895/1185896 hydrogen compression (Cantera 3.2 lacks `mean_molecular_weights`, fixed locally using `molecular_weights`). Pending fixes must be included in a new pinned snapshot before retry.

The earlier 1185822/23/25/26/27/28/30/31 attempts remain launcher-only failures caused by the missing profile interpreter path. The scoped venv symlink now resolves to the verified Hangang Python 3.12.9 environment; retries used unique external logs. QOS refusals have no job IDs and are recorded as `QOSMaxSubmitJobPerUserLimit`.

## Follow-up fixture corrections — pending fresh capture

Job 1185904 `parcel-population-finite-impact-sequence` failed its synthetic
contract because neither launch trace ended in an admitted ground crossing; the
impact sequence therefore had no event to process. The fixture now lowers both
launch heights and increases the downward speed, preserving distinct event order
and the declared flight-domain limits. The flight/impact model was not relaxed or
changed. Job 1185906's sensor-rejection case now returns an explicit outcome after
its rejection assertion. These are local corrections only; both need inclusion in
a new source snapshot and retry. No physical or sensor qualification is established.

## Follow-up cluster launcher correction — 2026-10-31

Jobs 1185918 and 1185919 failed in the finite-supply risk helper because the PBS
worker `PYTHONPATH` contained pinned `/src` but omitted pinned `/scripts`; the script
imports `check_equipment_network` from its sibling directory. `write_pbs_array()`
now emits pinned `/src` first, pinned `/scripts` second, and inherited entries last.
The `cluster-setup-script-pin` deferred source contract asserts that ordering. The
change awaits a fresh pinned capture and retry. No tests were run and no risk or
safety physics was validated by these launcher failures.

## Source corrections awaiting fresh capture

The one-cell porous-reservoir case exposed a schedule API contradiction: schedule
construction compared initial pressure count with time count, while the solver
requires initial pressure count to equal radial cell count. The constructor now
validates positive pressure values and well-flow/time alignment only; the run owner
checks the geometry-dependent count. The deferred case includes a flow/time
mismatch rejection fixture. Fuel-cell exchange currentness now binds original
mapping proxies instead of new dict copies, because mapping identity is part of the
content fingerprint. A currentness issue was reported for job 1185898; the remote
attempt metadata available at review is still running without `outcome.json`. Both
fixes require a fresh pinned snapshot and retry. No local tests/imports/calculations
were run and no physical validation is established.

## Hangang singleton campaign update — 2026-10-31

Across the earlier pinned campaign and the new 5f6de46 campaign, 27 deferred
software/API contracts are now confirmed passing. This is a contract count across
immutable revisions, not 24 physical-model validations or an independently
qualified model set.

The immutable source archive `aa9fa199bf6e852b5e1` transferred in 317 chunks;
the remote SHA-256 matched, all 1,060 manifest entries verified, and no forbidden
files were present. Job 1185986 completed the deferred synthetic
`parcel-population-finite-impact-sequence` contract in 9.86 s. This does not
qualify measured populations, simultaneous impacts, or wet-pool behavior. Job
1185990 entered the deferred `oxygen-threshold-deficit-integral` case and failed
only because the fixture compared binary floating-point integrals exactly. The
case now uses a 1e-14 absolute tolerance; this is a fixture correction pending a
new immutable capture and retry. No physical validation is established by either
job outcome.

Two additional deferred contracts were launched on the same immutable revision:
1185995 completed the synthetic fuel-cell synchronized-trial exchange contract,
including caller mapping isolation and retained-proxy replacement rejection; it
does not qualify a native fuel-cell stack or simultaneous solver coupling. Job
1185992 failed at adsorption input-currentness admission before entering the
integration. The local admission error now names changed payload fields without
printing their values, so the next remote run can isolate the unstable binding.
That diagnostic change awaits a fresh capture; the adsorption contract remains
unverified.

Further singleton results on the same pinned source: 1186006 carrier-original-
binding and 1186007–1186009 staged-cooling nominal/pressure/evidence contracts
completed. Jobs 1185998/1186000/1186001 failed before engine execution because
the case supplied a literal mechanism-path placeholder. The fixture now resolves
the installed `h2o2.yaml` through Cantera's data directories, hashes the installed
bytes, and does not copy the mechanism into the project. Job 1186003 reached the
native Brayton map route but exposed an unconditional `dataclasses.replace()` on
the retained native cycle result during `require_current()`. The result now
rechecks its retained mechanism and terminal state without attempting to mint a
second native receipt. Both fixes need a fresh capture and remote contract rerun.
No scientific engine or turbine-map qualification is established by these runs.

Job 1186012 reached the same engine-fixture placeholder failure as 1185998–1186001.
Jobs 1186018/1186019 found that the porous single-cell case omitted its required
typed `ValidationOutcome`, while the separate CoolProp provider-binding contract
completed. The single-cell case now returns explicit inventory/pressure/outer-flow
metrics and bounded synthetic-only notes. Job 1186041 completed the native fuel-
compression deferred API contract; it is not compressor qualification. These case
fixes are pending the next immutable source capture.

Jobs 1186046/1186047 passed the synthetic sensor calibration recovery and
rejection contracts; job 1186048 passed the native real-fluid compression API
contract. None establishes measured sensor calibration or compressor performance.
Job 1186052 is running the risk-source uncertainty contract with the separately
pinned LH2DT package. This result is pending.


## 2026-11-01 byte-pinned source transfer

The full base snapshot was transferred using the existing WSL `run.sh cpu` wrapper only. Base revision: `1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738`; archive size 14,294,926 bytes; archive SHA-256 `ff2758bbf353ea31b4336a43702f41f5bb47987b23989d6f9a16fa644aa8202c`; 1,449 manifest entries; complete manifest SHA-256 `fc76b2cdc49adfae1fc2b5af0953e3ff1cb881f11c0fa4ce3ee3467638d4747a`. Remote verification succeeded at `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-fc76b2cd`.

The first verification attempt hit OpenBLAS thread-creation limits while importing the validation package. No source mismatch was reported. Reverification with OpenBLAS/OMP/MKL/NumExpr thread counts set to one passed. The transfer helper now exposes a verify-only mode and caps those threads for manifest checks. No scheduler job was submitted from this base pin; the later exact-grid and receiver-boundary changes require a refreshed delta pin first.


## 2026-11-01 refreshed delta and deferred array

A 17-file delta was applied to base tree /scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-fc76b2cd. Remote full-tree verification passed at /scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-final-3d883a85, revision 1ea8d7c4d40c0dccb1a882b6d1edb7dc69812738, target manifest SHA-256 3d883a85642ad0f26bb8cb2d0e39947cb9b9b6ea448cf861e74df9dd1a4bcd4d. Delta archive size was 483,045 bytes; SHA-256 d7a746fad1c2f647dfd8218f2f6f2d24bedb004338ffb22f4f6c8063b1f9629a.

The immutable plan contains 316 Hangang cases, including:

- preferred-dispersion-receptor-alarm-contract
- preferred-dispersion-exact-receptor-grid-contract
- concentration-alarm-finite-stroke-valve-actuation-trace

Campaign script: /scratch/CLUSTER_USER/h2physics-jobs/campaigns/priority27-contracts-20261101.pbs; SHA-256 4bef2a7070d54f70ddf45c322f15a33874af340edf28181bf69da1054121f5b1. It requests queue 5thEx_cpu, account na1620, 30-minute wall time and field=che;appl=in_house metadata. Submission from the wrapper's default /home01 directory was rejected by the site's path filter; a retry from /scratch/CLUSTER_USER/h2physics-jobs/campaigns passed that path check but was refused with QOSMaxSubmitJobPerUserLimit. No job ID was returned and no case ran.

The immediately preceding queue snapshot showed four existing jobs (1190110, 1190136, 1190154, 1190164) in RUN state. They were not modified. Recheck QOS before the next submission; submit the same pinned script only when the account has capacity. The three cases remain unexecuted.

## 2026-11-01 priority 2–7 first parallel execution

The 1,471-file source snapshot was transferred through the approved `run.sh cpu` wrapper and verified at `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-0e11913f` (manifest SHA-256 `0e11913f628c2e19ec3c17edced8c84e00b778d3fcee7103c480562a8b97f787`). A four-file, 83,463-byte delta (SHA-256 `cf9f218dcf6c938acaf72a0d771c099acf917431698068e2fafd8b223b94a52d`) produced the final verified tree `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-a2d83ab6` (manifest SHA-256 `a2d83ab624b6e080a8b3a3dacb7eb101bc3db940da8c8a6b1244bd9e5e258b3a`). The PEM1 baseline member at `/scratch/CLUSTER_USER/h2physics-jobs/data/pem-ripple/2/PEM1_Initial.csv.gz` was independently checked against SHA-256 `46e2e7e08cb5d7eb371df30f7b3b6ee221f9c1e5ae46cd40c544b3c21bccfa90`.

One six-CPU PBS allocation, job `1190418`, ran the six targeted contracts in parallel. The pinned script SHA-256 was `f37e9bf63ad14536be6bba5bf39a09ff0e31396cd103d79574418d15fd16be81`; `bash -n` passed before submission. The job reached completed state. Per-case `attempt.json`, `outcome.json`, and allocation logs are under `/scratch/CLUSTER_USER/h2physics-jobs/results/1190418/`.

| Case | Outcome | Evidence boundary |
| --- | --- | --- |
| `preferred-dispersion-receptor-alarm-contract` | Passed | Metadata/API contract only; no provider field evaluated. |
| `preferred-dispersion-exact-receptor-grid-contract` | Passed | Exact-grid metadata contract only; no native result or concentration grid sampled. |
| `concentration-alarm-finite-stroke-valve-actuation-trace` | Failed, then fixed locally | Remote environment lacked optional `lh2dt`; case now uses the internal shared-valve adapter with the real CoolProp-backed nozzle model. |
| `two-vent-hydrogen-layer-concentration-alarm-handoff` | Failed, then fixed locally | NumPy time arrays were compared with scalar equality; the assertion now uses exact array equality. |
| `pem-ripple-iv-to-hydrogen-stack-diagnostic` | Passed | 20,040 source rows and hashes were checked; synthetic model callbacks mean no electrolysis performance validation. |
| `preferred-gas-dispersion-hyram-ignition-risk-ledger` | Failed, then fixed locally | The external risk package is not installed by the facility profile; the case now tests a caller-owned structural binding and explicitly disclaims external risk-engine execution. |

Three cases passed and three exposed integration-fixture issues. The latter three have been corrected locally; their refreshed source delta and parallel rerun are pending. None of the six cases establishes measured plume accuracy, detector placement/detection performance, valve flow qualification, electrolyzer performance, or risk-engine qualification. Existing jobs were not changed.

## 2026-11-01 priority 2–7 correction delta and QOS retry

The local fixes and updated run records were packaged as an eight-file, 252,885-byte delta (SHA-256 `e66f744d600e6eb7996bd239fb6de1620e10b53f6e3a3b73fe57a0f4fd0180cd`). The remote tree `/scratch/CLUSTER_USER/h2physics-jobs/verified-priorities-2-7-46209831` passed full manifest verification with SHA-256 `46209831a033dea24c7aaaa58398a5412fe44ea039852feff0c78f2e029a42df`. Targeted Ruff and syntax checks passed locally. The rerun script selects only the three corrected cases, requests three CPUs, and passed remote `bash -n`; its SHA-256 is `381ccea41672d0e0677345c5058c61ed89bbd5335d8e6448160e18993c34df47`.

The queue snapshot immediately before the single-allocation submission showed five existing user jobs running. `qsub` returned `QOSMaxSubmitJobPerUserLimit`; no job ID was issued and no corrected case reran. No existing job was modified. Retry after the site has capacity. The corrected risk contract still uses a caller-owned structural fixture and does not exercise `process-risk-consequence-toolkit`; the valve case uses the internal shared-valve adapter with the CoolProp-backed nozzle, not the external `lh2dt` package.


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
