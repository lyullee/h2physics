# Archived Nurion validation planning snapshots

This document is retained for historical Nurion source/job records and is not
the active execution plan. The user's current target is Hangang; do not prepare
or submit new Nurion jobs. Current source plans and any authorized calculations
must use `validation/hangang_plan.py` and the active Hangang connection rules in
`AGENTS.md`. Historical Nurion job results remain evidence only for their exact
recorded pins and cases.

[CLUSTER_PROFILE_REQUIREMENTS.md](CLUSTER_PROFILE_REQUIREMENTS.md) maps declared
profiles to explicit optional/native capabilities and source records. Regenerate
it with `scripts/cluster_profile_requirements.py` when case dependencies change;
the report does not install or verify a runtime.

Historical campaign note: calculations were once planned on Nurion and Hangang.
The current local-development/Hangang-only policy in `AGENTS.md` supersedes that
older planning text. Remote jobs must remain tied to exact source, plan and setup
hashes, and queued/running jobs are not results.

The current worktree is dirty and must be pinned by an exact source manifest before
any campaign. A first source-only snapshot has been transferred to Hangang through
the prescribed wrapper; its archive hash was checked, Python 3.12.9 and core/native
runtime dependencies were prepared, and an editable install/import smoke check
succeeded with one-thread BLAS limits. The local tree has changed since that
snapshot. Rebuild and verify the source snapshot before preparing or submitting
parallel case arrays. Do not add work to Nurion's unrelated pre-existing jobs.
Metadata inventory is not model evidence.

The generated inventory below is the last 304-case snapshot. Subsequent source
plans add sixteen deferred case modules (porous reservoir, fuel-cell trial, Brayton
map pair, engine boundary ledger, mixture separator history audit, HyRAM
source-transition audit, bounded mixture V/U flash and prescribed-flow open
cylinder, two bounded Brayton operating-point cases, the pool accepted-edge energy
contract, native pressure-valve contract, evolving-mixture interval/ODE models,
synchronized fuel-cell coupling, cooled Brayton/bleed, staged turbine cooling and
hydrogen fuel compression). The last generated snapshot expects 345 cases across
54 profiles and 94 case modules. Current source plans add ten deferred contracts
and five case modules, giving 355 cases across 54 profiles and 99 case modules,
pending regeneration. These include two phase-specific accepted-edge withdrawal, two
finite-adsorption dynamics, two compressor anti-surge, two reactant-reserve
current-limiting, three finite-cylinder-wall thermal, three staged turbine-cooling
and five hydrogen fuel-compression cases. The existing hydrogen-engine profile
now has 24 planned cases. Refresh the generated 304-case inventory on Python 3.12
before building a pinned campaign. None of the later cases has run.

## Fresh-code verification queue: geological adsorption provider

The deferred `geological-adsorption-excess-loader` case checks species-qualified signed source-loading retention, weighted reconstruction of each returned site, source-reported uncertainty/LOD/LLOQ retention without statistical propagation, typed receipt immutability, invalid-value rejection, duplicate-row rejection and unit-sum weights. It remains unexecuted and outside completed legacy pins. Re-pin the updated source and plan revision before including it in a user-authorized campaign.

## Synthetic source-block receipt cases

The `source-data-ingestion` profile includes `fermentation-block-issuer-integrity`,
`hydride-tank-block-issuer-integrity`, `tudatalib-engine-metadata-receipt`,
`hdf5-structure-inventory` and `bam-jet-fire-text-parser`. The
first two construct minimal synthetic XLSX archives with stdlib ZIP/XML, then
exercise reader issuance, direct-construction and dataclass-replacement rejection,
plus post-load mutation detection; their reader paths need the `data` extra
(`openpyxl`). The TUdatalib contract mocks item, ORIGINAL-bundle and bitstream
metadata responses and checks byte retention, official-host HTTPS links, pinned
DOI/license, and ambiguous bundle rejection without reading an attachment body.
The HDF5 contract builds a synthetic container and inventories its structure only;
acquired publisher files are neither staged nor parsed by the case. None of the four
cases validates process physics.

<!-- BEGIN GENERATED CASE INVENTORY -->
**Current metadata inventory:** 418 deferred case definitions across 59 declared environment profiles and 115 case modules.
These are authored plans, not executions or accepted scientific evidence. The inventory imports only each module's cases() metadata catalog; case entrypoints, models, native engines and schedulers are not run.

| Profile | Deferred cases |
|---|---:|
| biological-process | 1 |
| buried-pipeline-data | 2 |
| carrier-conversion | 7 |
| carrier-conversion-native | 1 |
| compressor-boundaries | 4 |
| compressor-map | 9 |
| counterflow-data | 1 |
| counterflow-flame | 10 |
| counterflow-heat-exchanger | 4 |
| detonation-native | 1 |
| droplet-impact | 13 |
| droplet-transport | 4 |
| electrochemical-thermal | 4 |
| facility-continuity | 7 |
| facility-protection | 19 |
| finite-adsorption-vessel | 16 |
| finite-hydride | 6 |
| finite-relief-lift | 10 |
| finite-transfer | 10 |
| flash-front | 4 |
| flowing-heat-exchanger | 7 |
| fracture-fatigue | 25 |
| fragment-trajectory | 2 |
| fuel-cell | 7 |
| fuel-cell-native | 7 |
| gas-composition | 10 |
| gas-compressible-pipe | 4 |
| heat-exchanger-boundaries | 5 |
| hydride-compressor | 1 |
| hydrogen-channel-data | 1 |
| hydrogen-economics | 7 |
| hydrogen-engine | 38 |
| hyram-overpressure | 2 |
| jet-fire-conservation | 7 |
| jet-fire-radiation | 5 |
| joint-uncertainty | 1 |
| material-transport | 9 |
| microbial-cell | 6 |
| microbial-economics | 6 |
| microbial-observations | 2 |
| mixture-vle | 5 |
| model-selection | 10 |
| obstacle-dispersion | 4 |
| oxygen-deficiency | 5 |
| photochemistry | 1 |
| pool-energy-contract | 1 |
| pool-fire | 10 |
| porous-reservoir | 4 |
| preferred-dispersion | 3 |
| pump-operation | 9 |
| pv-electrolysis | 16 |
| reliquefier-product | 8 |
| solid-reaction | 10 |
| solid-reaction-native | 1 |
| source-data-ingestion | 18 |
| thermal-target | 7 |
| thermal-utilities | 9 |
| underground-storage | 4 |
| valve-actuator | 8 |

**Associated deferred profiles for implemented-unverified families:**

| Catalog family | Deferred profiles |
|---|---|
| combustion.flash_fire | flash-front |
| combustion.gas_turbine | hydrogen-engine |
| combustion.jet_fire | jet-fire-conservation, jet-fire-radiation |
| combustion.laminar_flame | counterflow-flame, counterflow-data |
| combustion.piston_engine | hydrogen-engine |
| combustion.pool_fire | pool-fire, pool-energy-contract, thermal-target |
| dispersion.buoyant_layer | facility-protection |
| dispersion.compartment_network | oxygen-deficiency |
| dispersion.fixed_flow_snapshots | preferred-dispersion |
| dispersion.obstacle | obstacle-dispersion |
| effects.fragment_trajectory | fragment-trajectory |
| effects.rupture | fracture-fatigue |
| facility.detector_reliability | facility-protection |
| facility.monitoring | facility-protection |
| materials.diffusion | material-transport |
| materials.integrity | fracture-fatigue, thermal-utilities |
| production.energy_coupling | pv-electrolysis |
| production.microbial_cell | microbial-cell, microbial-observations |
| release.droplets | droplet-transport |
| release.impact | droplet-impact |
| research.economics | hydrogen-economics, microbial-economics |
| storage.adsorption_delivery_mass_flow | finite-adsorption-vessel |
| storage.extended_langmuir | finite-adsorption-vessel |
| storage.solid_reaction | solid-reaction, solid-reaction-native |
| storage.underground | underground-storage |

**Case IDs mapped to each unverified family (planned only):**

| Catalog family | Profile | Deferred case IDs |
|---|---|---|
| combustion.flash_fire | flash-front | flash-front-axial, flash-front-gaps, flash-front-binding, flash-front-native-refinement |
| combustion.gas_turbine | hydrogen-engine | hydrogen-brayton-reference, hydrogen-brayton-input-guards, hydrogen-brayton-summary-integrity, hydrogen-brayton-compressor-turbine-map-pair, hydrogen-brayton-bounded-map-operating-point-solve, hydrogen-brayton-operating-point-incomplete-seed-search, hydrogen-brayton-compressor-bleed-zero-limit, hydrogen-brayton-compressor-bleed-mixed-turbine, hydrogen-brayton-cooling-pressure-rejection, hydrogen-brayton-cooling-speed-link-rejection |
| combustion.jet_fire | jet-fire-conservation | jet-conservation-rejection, jet-conservation-quadrature, jet-conservation-domain, jet-conservation-binding, jet-conservation-radiation, jet-conservation-energy |
| combustion.jet_fire | jet-fire-radiation | jet-radiation-far-field, jet-radiation-attenuation, jet-radiation-refinement, jet-radiation-domain |
| combustion.laminar_flame | counterflow-flame | counterflow-native-profile, counterflow-strain-definitions, counterflow-profile-sampling, counterflow-pressure-admission |
| combustion.laminar_flame | counterflow-data | counterflow-extinction-data-ingest |
| combustion.piston_engine | hydrogen-engine | hydrogen-engine-slider-crank-geometry, hydrogen-engine-input-admission, hydrogen-engine-boundary-schedule-contract, hydrogen-engine-crank-schedule-conversion, hydrogen-engine-native-closed-charge, hydrogen-engine-piston-heat-flux-schedule, hydrogen-engine-failure-prefix, hydrogen-engine-boundary-stream-ledger, hydrogen-engine-open-control-volume-forced-flow, hydrogen-engine-native-pressure-valve-boundary, hydrogen-engine-crank-angle-fuel-delivery-native-flow, hydrogen-engine-open-cylinder-shared-nozzle-inlet, hydrogen-engine-wall-gas-coupling-energy-ledger, hydrogen-engine-wall-zero-UA-reduction, hydrogen-engine-wall-external-boundary-ledger |
| combustion.pool_fire | pool-fire | pool-fire-baseline, pool-fire-geometry, pool-fire-refinement, pool-fire-heat-budget, pool-fire-oxygen, pool-fire-geometry-rejection, pool-fire-prefix, pool-fire-native-pool |
| combustion.pool_fire | pool-energy-contract | native-pool-accepted-edge-energy-contract |
| combustion.pool_fire | thermal-target | thermal-target-pulse, thermal-target-lossless, thermal-target-refinement, thermal-target-domain |
| dispersion.buoyant_layer | facility-protection | two-vent-hydrogen-buoyant-layer-accumulation, two-vent-layer-dry-air-oxygen-composition-projection |
| dispersion.compartment_network | oxygen-deficiency | hydrogen-fixed-state-compartment-network-mixing-closure |
| dispersion.fixed_flow_snapshots | preferred-dispersion | hyram-finite-source-fixed-flow-snapshots |
| dispersion.obstacle | obstacle-dispersion | obstacle-zero-source, obstacle-finite-pulse, obstacle-obstacle-pair, obstacle-refinement |
| effects.fragment_trajectory | fragment-trajectory | conditional-fragment-flight-impact |
| effects.rupture | fracture-fatigue | vessel-native-capacity-units, vessel-thermal-initiation-refinement, vessel-native-finite-storage-binding, vessel-domains-failure-retention |
| facility.detector_reliability | facility-protection | kofn-detector-common-cause-reliability, kofn-detector-versioned-trial-evidence |
| facility.monitoring | facility-protection | facility-concentration-alarm, sensor-time-constant-calibration-recovery, sensor-time-constant-calibration-rejections, two-vent-layer-oxygen-deficit-sensor-alarm-handoff |
| materials.diffusion | material-transport | power-law-solubility-diffusion-boundary, quasi-steady-permeation-history, steady-permeation-surface-resistance, hydrogen-diffusion-surface-film-boundary, cylindrical-shell-hydrogen-diffusion, radial-hydrogen-diffusion-shell-api, diffusion-outward-h2-finite-source-handoff |
| materials.integrity | fracture-fatigue | fracture-paris-si-exponential, fracture-terminal-events-refinement, fracture-hydrogen-native-constitutive, fracture-arrest-restart-and-negatives, elastic-cylinder-pressure-boundaries, elastic-cylinder-pressure-samples, elastic-cylinder-uniform-thermoelasticity, cylinder-pressure-vessel-history-bridge, fracture-block-sample-summary, mendeley-ms1700-qp1180-normalized-permeation-ingest, mendeley-ahss1300-source-bound-observations, radial-hydrogen-concentration-eigenstrain, cylindrical-transport-eigenstrain-bridge |
| materials.integrity | thermal-utilities | thermal-declared-balance, thermal-negative-gates, thermal-native-HX, thermal-process-readers, thermal-native-devices, thermal-mutation-failure |
| production.energy_coupling | pv-electrolysis | pv-baseline, pv-dark-isolated, pv-no-root, pv-water-depletion, pv-delivery-pressure, pv-receiver-domain, pv-faradaic-heat, pv-faradaic-efficiency-bounds, pv-held-stage-refinement, pv-caloric-reference, pv-original-result, pv-profile-midpoint-stages, electrolysis-fuel-cell-single-batch-handoff, electrochemical-hydrogen-storage-metered-round-trip-ledger |
| production.microbial_cell | microbial-cell | microbial-native-charge, microbial-biomass-energy, microbial-disconnected, microbial-finite-failure, microbial-boundary-guards, microbial-original-result-binding |
| production.microbial_cell | microbial-observations | microbial-observation-current, microbial-observation-integrity |
| release.droplets | droplet-transport | parcel-constant-heat, parcel-ground-crossing, parcel-initial-flash |
| release.impact | droplet-impact | impact-baseline, impact-elastic, impact-zero-contact, impact-dryout, impact-refinement, impact-missing-heat, impact-prefix, impact-intercontact-heat, impact-native-pool, parcel-population-finite-impact-sequence |
| research.economics | hydrogen-economics | economics-native-direct, economics-finite-link, economics-undiscounted, economics-negative, economics-failure-retention, economics-public-projection, economics-source-cache |
| research.economics | microbial-economics | mec-economics-owner, mec-economics-link, mec-economics-guards, mec-economics-failure, mec-economics-public-projection, mec-economics-producer-mutation |
| storage.adsorption_delivery_mass_flow | finite-adsorption-vessel | adsorption-delivery-component-mass-flow |
| storage.extended_langmuir | finite-adsorption-vessel | competitive-extended-langmuir-multicomponent |
| storage.solid_reaction | solid-reaction | solid-baseline, solid-heat, solid-water-feed, solid-reference, solid-startup-gas, solid-finite-failure, solid-negative, solid-binding |
| storage.solid_reaction | solid-reaction-native | solid-native-caloric |
| storage.underground | underground-storage | underground-equilibrium, underground-rock-exchange, underground-injection-withdrawal, underground-refinement |

This current metadata count supersedes intermediate case totals in dated checkpoint notes below.
<!-- END GENERATED CASE INVENTORY -->

Refresh this metadata-only count after changing case modules or profile bindings with
python scripts/validation_inventory.py. It does not run scientific case entrypoints.

The last completed source-regression checkpoint is commit6eae06c:1088passes
with11optional biological skips in each recorded profile. Its source results
do not validate later code. Its new wheel/sdist were built, but further content/
installed execution checks were deferred at the user's request. The previous
fully inspected installed-artifact checkpoint is785dae7. Development modules
after6eae06c are explicitly implemented_unverified.

## Python contracts

`h2physics.cluster_validation.ValidationCase` names a whole scientific case,
native environment profile, importable entrypoint, Python parameters and
predeclared acceptance invariants. `validation.cases.*.cases()` only constructs
metadata: no native model, optimizer, solver or experiment is run while listing
cases. A case entrypoint receives an evidence work directory and its named
Python parameters. It returns `ValidationOutcome(accepted, metrics, limitations)`
or raises an original error. Empty/absent outcomes cannot count as success.
Parameters remain Python objects; no model JSON input or web service is required.

New cases cover native PV/electrolyzer operating points and finite inventories,
native fracture-growth laws with mechanical geometry/history, and finite solid
reaction species/energy/source limits. Each case must preserve original engine
objects in process and persist appropriate portable raw arrays/diagnostics in
its work directory. There is no universal serialization of native reactors,
compiled objects or callbacks. Case-specific audits must not pretend otherwise.

Native law, phase/reference, geometry, pressure, time/event, conservation and
refinement checks remain domain-specific. Data parsing, analytic limits,
independent experiment comparison and application qualification remain distinct.
A cluster job finishing is not itself a scientific acceptance criterion.

## Explicit cluster configuration

KISTI documents Nurion's PBS scheduler and its array/resource options in the
[scheduler guide](https://docs-ksc.gitbook.io/nurion-user-guide/undefined/running-jobs-through-scheduler-pbs)
and [keyword reference](https://docs-ksc.gitbook.io/nurion-user-guide-eng/appendix/appendix-1-main-keywords-for-job-scripts).
Those references do not establish a particular account's current queue,
limits, modules, architecture, allocation or site admission. Confirm them after
connection, before submitting anything. No queue/account/resource default is
invented here, and no login or submission command is executed by the library.

Prepare separate Linux/native environments as required by each case. Windows
dependency snapshots are historical reproduction records, not Nurion locks.
Keep native artifact/source/license records and selected numerical versions.
Do not mix an older native NumPy/Numba target into another profile implicitly.
The setup shell file is an explicit user-owned cluster environment definition;
its SHA-256 is pinned in the profile, checked before and after sourcing, and
retained in each worker record. The worker checks its selected interpreter and
records actual package versions. Installations or network downloads are not
hidden in scientific case execution. Files sourced transitively by that setup
script require separate pinning in setup logic or runtime records.

`ClusterProfile` requires the actual absolute POSIX interpreter and setup-script
paths, the exact setup-script SHA-256 and a numerical thread budget. `PBSResources` requires queue, accounting
string, one-node CPU allocation and walltime; an optional project is explicit.
`validation/nurion_plan_example.py` shows the required environment variables
and metadata-only case collection. Supply actual paths after connection. Do not
interpret its existence as a successful environment or scheduler check.

This worker validates the pinned source checkout: select that checkout through
an editable installation or explicit source path. An older installed wheel is
rejected even if the shell's working directory contains the requested Git commit.

`write_pbs_array` writes but never submits a PBS array. Pin the exact Git commit,
the SHA-256 of every environment setup script, and the SHA-256 of the actual Python plan file. Use the absolute repository, plan
and result paths on the cluster. A previously generated destination is not
overwritten. Generated scripts select the explicit interpreter per case and
set numerical thread budgets within allocated CPUs.

```python
from h2physics.cluster_validation import PBSResources, write_pbs_array

# CASES and PROFILES come from the explicitly configured Python plan.
# The path, queue/account/resource values below are supplied by the operator
# after connection; this example does not provide credentials or defaults.
resources = PBSResources(queue, accounting, nodes=1,
                         cpus_per_node=allocated_cpus, walltime=walltime)
pbs_path = write_pbs_array(
    CASES, PROFILES, resources, destination=local_script_path,
    cluster_repository=cluster_repository_path,
    cluster_plan_file=cluster_plan_path,
    cluster_result_directory=cluster_results_path,
    expected_revision=git_commit, expected_plan_sha256=plan_sha256,
    name="hydrogen-model-validation",
)
```

## Prepare a source snapshot (no submission)

After the campaign's code and Python plan are committed, create a source snapshot
outside the repository:

```powershell
python scripts/prepare_nurion_snapshot.py `
  --revision HEAD `
  --destination "<campaign-directory>"
```

The command requires a clean worktree, resolves a full Git commit, refuses to overwrite
an existing destination, packages only that commit, writes and verifies the source
revision/file-hash receipts, and emits the source-manifest and archive SHA-256 values.
The destination contains `repository/` and a root-layout `source.tar.gz`; transfer and
extract those only after selecting an authorized campaign. It never contacts a cluster,
generates a PBS job or submits work. Pin and hash the exact Python plan separately, then
use `write_pbs_array` to generate a scheduler script. A generated script is not a job
submission or scientific result.

Parallelism is across independent complete cases. This does not turn a serial
ODE into an MPI solver, split coupled steps across nodes or declare stronger
physics. Case grouping/resources can be tuned after learning the allocation
and cost characteristics. For many small cases, first choose a sensible packing
strategy rather than assuming one node per tiny assertion is efficient.

Compile/JIT native kernels in the compute-node environment, with a job-specific
cache under the supplied compute-local TMPDIR. Do not reuse an unrelated login-
node CPU cache as proof of compatibility. Keep thread pools within CPU allocation;
avoid multiplying process and BLAS/OpenMP thread counts accidentally.

## Worker evidence and completion rules

The worker entrypoint requires an explicit PBS job/array environment. It checks
Git revision, tracked-source cleanliness, plan SHA, array case/profile identity
and actual interpreter before a scientific entrypoint. It creates a unique
case work directory and an initial attempt record. Successful/rejected/failed
results are written atomically with timings, package versions, invariants and
limitations. Original tracebacks are retained on failure; no alternate engine
or missing-data fill is introduced. Nonfinite metric values are labeled, not
converted to zero. Internal machine logs do not replace the Python model API.

A killed or absent job without its completed outcome remains incomplete. Missing
cases, unsupported dependencies, failed source/phase/reference guards, rejected
physical premises and unqualified observations cannot become a partial successful
aggregate. No unexecuted case is marked passed. Dataset outputs/raw evidence
stay in ignored cluster result directories; do not add them to public Git by
default. Perform the deferred archive/installed/native/data checks against the
exact accepted revision before a later release acceptance claim.


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


Three new profiles are declared in validation/nurion_plan_example.py:
obstacle-dispersion, jet-fire-conservation and microbial-economics. FDS cases
additionally need the actual H2PHYSICS_FDS_BINARY and reviewed H2PHYSICS_FDS_SHA256
in their later setup environment. No binary, queue, paths or job IDs are guessed.

After actual results exist, RuntimeExpectation/CampaignExpectation with explicit
selected jobs and CollectionBudgets feed collect_campaign_evidence. It performs
no scheduler poll or case import. A complete record can still report a failed
or rejected validator; every reported case passing is not a physical or release
qualification. Expected negative jet diagnostics cannot validate jet fire.
The collector itself remains unexecuted and legacy regressions remain separate.

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

## Exact selection and finite process campaign addition

Add profiles `model-selection`, `fuel-cell`, `fuel-cell-native`,
`finite-transfer` and `thermal-utilities` from `validation/nurion_plan_example.py`.
They contribute27 definitions and bring the deferred campaign to133. Validate
no-fallback provider selection, fuel/product and energy closure, both finite
endpoint inventories and utility allocation without exchanger double counting.
This checkpoint did not discover or execute these cases.
The model-selection profile has since gained `selection-preferred-dispersion`: it
checks that high-pressure-gas and LH2-origin families map to the helper's exact
`hyram` and `slabx-lh2` provider IDs, then rejects a cross-origin provider request
without fallback. This metadata/factory-contract case is queued for a future source pin.

## Adsorption, actuation, relief and continuity campaign addition

Add profiles `finite-adsorption-vessel`, `valve-actuator`,
`finite-relief-lift` and `facility-continuity`. Their25 definitions take the
campaign to158. Run them with the contributing native/property suites. Provider
identity, phase/basis, clock, port uniqueness and retained nonclosure are gates.
No case was discovered or executed at this checkpoint.

## Pump, compressor, flowing-HX and reliquefier campaign addition

Add profiles `pump-operation`, `compressor-map`, `flowing-heat-exchanger` and
`reliquefier-product`. Their25 definitions bring the campaign to183. Execute
with each original native equipment/property suite and source-qualified map or
apparatus evidence. Extrapolated maps, stale results, invalid phase/ports and
unclosed product/cold budgets must remain failures. No case ran locally.

## Active user-authorized Nurion continuation — 2026-10-29

The user has now connected the existing KISTI shared session and directed that Nurion
verification proceed independently while implementation continues. All scientific
model runs and tests remain on Nurion; local work is limited to code/static review and
metadata-only plan preflight. Use only the user's existing connection wrapper and do
not attempt new authentication. The user explicitly authorized submission of this
verification continuation.

The current single data-ingestion case is pinned to source `643e4a8d1765a35170141b5a3a2af115340403cd`
with a 728-entry source-manifest digest and a plan digest recorded in `HANDOFF.md`.
The first worker failed before case execution because the plan exported a callable
instead of `CASES`; the corrected plan ran as `24229654.pbs`, and collector
`24229655.pbs` completed. Its summary is in `results/fixcheck_643e4a8/summary.json` on
Nurion, accessible through the existing session. The single ingestion case passed its
hash/schema/source-coordinate gates in 40.96 s. This does not include a flame solve,
model-data comparison, or pure-H2 evidence. The new PV-profile, inter-contact impact-
heat and elastic-cylinder cases were added after that source pin and belong in a later
combined campaign. No running or queued case is a result until its exact outcome is
captured and reviewed.

The following implementation pin is `c521f57cd960b4be460c5dc1eefa5788b47d8f0d`,
731-entry manifest `ab8883a04e1c67ab70eaf3851c622214c2f1e83105790dc18b490ebe75636f33`,
and metadata-only three-case plan `6743678c5f2c9da1d0bddd11c00f0cded4a6b0287516e7dcc9ef0241a9193968`.
The array `24229801[]` runs `impact-intercontact-heat`,
`elastic-cylinder-pressure-boundaries` and `pv-profile-midpoint-stages`; collector
`24229802.pbs` is held. The PV profile uses a separately transferred source-only
pvlib 0.16.1 payload with its BSD license retained; the reviewed source aggregate hash
was verified on both ends. PV element `[3]` exited before the case because setup looked
for the archive in the wrong incoming directory. The archive is now in the expected
path and a standalone retry script passed shell syntax checks. Element `[2]` passed in
7.37 s: pressure tractions, open/closed end stress and von Mises invariant matched the
authored elastic solution. This does not qualify vessel integrity, crack growth or
fatigue. Element `[1]` remains running. Submit the PV retry after the original array
exits, then collect all case outcomes separately from data ingestion and review
limitations before revising family-level coverage.

Status update: impact `[1]` passed in 29.58 s, cylinder `[2]` passed in 7.37 s, and PV
retry `24229849.pbs` passed in 38.52 s. Collector `24229850.pbs` exited 0 with three
passes, zero failures and no missing cases. A subsequent implementation added
`lame_stress_samples`, explicit pressure clock identity, and a bridge to existing
`VesselFailureHistory`, plus two deferred cases after the `c521f57` source pin. Those
cases have not run and must be included in a later user-authorized campaign. No new job
was submitted.

The current implementation also adds a uniform-temperature thermoelastic Lamé field
with caller-selected free or fixed axial expansion and explicit material data. Its
deferred case covers constitutive strain, pressure-boundary and support-force
invariants. It postdates all listed source pins and has not been executed; do not
include it in a prior result or change accepted coverage.

At the time of this intermediate status, impact `[1]` and cylinder `[2]` had passed,
and the PV retry had been queued. The later status above records the PV pass and
collector completion. The pressure-series additions are outside that source pin.

## New implementation cases awaiting a future submission request

The plan example now also registers `elastic-cylinder-pressure-samples`,
`cylinder-pressure-vessel-history-bridge`,
`elastic-cylinder-uniform-thermoelasticity`,
`elastic-cylinder-radial-thermoelasticity`,
`mec-electrode-data-provenance`, `mec-electrode-data-integrity` and
`oedi-4130x-fatigue-provenance`. They respectively
cover supplied-point pressure sampling, mapping into the existing HELPR history contract,
uniform-temperature response, a radial-temperature boundary-value solution and its
quasi-static pressure/temperature snapshot composition, CORA
source/schema plus tamper checks, OEDI workbook source/schema provenance, and a no-fit native
HELPR point-rate diagnostic against the admitted 45 MPa workbook series. The OEDI cases
require the separately staged XLSX path via their Python `source_path` parameter; the raw
workbook is excluded from source snapshots. The provenance case cross-checks the staged
file's SHA-256, MD5, byte size, URL and license against the repository TOML receipt as
well as the loader's code pins. It also checks the receipt dataset key, acquisition state,
rights permission and that the dataset is not marked scientifically validated. Set
`H2_DATA_OEDI_FATIGUE_ROOT` to its staged
directory before `validation/nurion_plan_example.py` collects cases; both OEDI case parameter
mappings then record that path. If the workbook is absent, the case fails immediately with a
staging instruction. The loader verifies its pinned SHA-256 and
MD5. The 4.5 MPa HyMatBase field is retained as a metadata discrepancy; identical file
bytes, the workbook cells and Sandia's study record support 45 MPa. The diagnostic uses an
explicit reconstructed 298.15 K / pure-H2 condition, does not pass the 1 Hz frequency to
HELPR, and records `gas_composition_interpretation_id` because the source does not report
test purity. The typed result and NPZ also retain the source condition, environment evidence,
fugacity basis and declared composition interpretation. The NPZ preserves HELPR raw returns
alongside the accepted SI growth-rate vector, both aligned to source rows. Failure receipts
resolve completed and failing rows back to observed Delta-K and growth-rate values. It also checks the failure-receipt
schema around an admitted owner using a synthetic error wrapper; it does not inject an
actual HELPR exception or validate failure propagation. The case applies no acceptance
threshold and makes no material/vessel qualification claim.
These cases postdate the listed source pins and have not run. No calculation has been
submitted for them; each needs a newly pinned combined campaign after the user separately
requests submission.

The same plan example registers `finite-cylinder-radial-heat-transfer` under
`thermal-utilities`. Its deferred handler covers adiabatic conservation, both boundary
heat-flow signs, prescribed-flux energy closure, variable-property convection, an
analytical logarithmic steady wall, two-sided radiative heating/cooling and surface balance,
temperature-profile lineage, and quasi-static
pressure/temperature/stress mapping on one clock, and cause retention for invalid radiation
input. It postdates the source pins above and
has not run. Include it only in a newly reviewed, separately authorized campaign; no
local model calculation was performed. It also forces a native BVP failure on its first
requested sample and checks retention of the source thermal history, underlying cause and
completed prefix; this remains an authored, unexecuted invariant.

The existing `selection-preferred-dispersion` contract also exercises gas and LH2
scenario wrappers with stand-ins: HyRAM call inputs, SLABx steady-source boundary
arguments, width-context selection, runner arguments, premise callback, returned object
and source-mass audit fields. These are adapter-plumbing checks only; registry fixtures
are `implemented_unverified`, and neither preferred engine is imported or numerically
executed. The expanded case remains deferred and has not run.
The `cluster-setup-script-pin` case checks that generated PBS text verifies the
profile setup-script digest before and after sourcing, rejects an unpinned script,
and contains no submission command. It remains deferred and unexecuted.
Its thermal companion additionally attempts to construct a result with a modified energy
residual and requires the record to reject the mismatch with the boundary-heat ledger.
The initial cumulative heat values are zero by contract. This check is authored only.
The same thermal case verifies non-string material/boundary identities are rejected during
record construction; no solver call is needed for that input-boundary check.
It also requires a non-string boundary-kind selector to raise the documented input error;
the new constructor validation is unexecuted.
The `elastic-cylinder-radial-thermoelasticity` case now also attempts to construct point
and history results with deliberately inconsistent von Mises arrays and requires both
result records to reject them. It also checks rejection of a temperature profile that does
not span the cylinder boundaries. The heat-transfer case checks that generated profile
mapping requires a nonblank evidence identity. These invariants are specified but unexecuted.

The HE-Austenite observation cases require `H2_DATA_AUSTENITE_ROOT` to point to the
separately staged nine-file dataset directory before case collection. Both case
parameter mappings retain that path. The provenance entrypoint checks the complete
receipt inventory, acquired-byte total, per-file size and SHA-256, publisher MD5, and
CC-BY rights while requiring `validation_qualified = false`. These are authored Nurion
custody checks only; neither case has executed.

The `gas-composition` profile now also checks the fixed H2/N2 real-gas provider
through CoolProp HEOS. Install the optional `thermo` dependency in that profile. The
deferred case checks composition/property identity, PT/PH/PS/P-density state round
trips over an explicit gas-phase temperature interval, enthalpy-energy identity and
rejection of an inverse request without bounds. It also composes the provider with the
common isentropic nozzle and checks returned basis, entropy, mass and energy ledgers.
The exact inverse-state cache contract checks repeated-state reuse, bounded size, explicit
clearing, and disabled-cache behavior at capacity zero. No timing threshold or speedup
claim is made by this metadata case.
It binds the same provider into `FrozenGasBinding` and rejects changed composition IDs,
species ordering or mole fractions before vessel inventory use, rejects provider
composition mutation after fingerprinting, and accepts the provider's single-phase
supercritical state in the common gas endpoint contract. It passes the binding into an
authored `FiniteAdsorptionVessel` fixture and checks property-basis retention and free+
adsorbed component closure. The authored isotherm fixture is plumbing/accounting evidence,
not an adsorption measurement.
These are synthetic/API-level checks; they do not qualify the H2/N2 EOS or release
prediction against experimental mixture data.

The gas-composition case uses a separate fixed H2/N2 gas composition for its real-gas EOS work; a 3-component H2/N2/H2O fixture is retained only for mole/mass bookkeeping. It prepares a 3-pressure by 9-temperature sampled inverse grid, then checks PH/PS/P-density round trips at an off-node pressure against independent calls through the same provider's full bounded inverse path. It checks immutable-copy isolation, fingerprint stability, malformed monotonicity rejection, and matching composition/property-basis/domain requirements for second-provider reuse. Per-inverse PT state reuse is also part of the implementation; the case reports grid preparation cost, median inverse wall time and actual PT flash counts over three repetitions for the grid and baseline paths. These metrics characterize this synthetic case only; use results to decide whether the optional grid is useful, and do not claim independent EOS validation. Grid preparation is deferred scientific execution and must run on Nurion; no Nurion work has been submitted.

The gas-composition outcome receipt now retains the exact inverse-grid fingerprint, composition SHA-256, property-basis reference, CoolProp version and pressure/temperature axes. It also reports maximum temperature deviation and separate absolute enthalpy, entropy and density deviations against the no-grid bounded path. Benchmark runs warm both paths, alternate execution order, disable inverse-result caching and report median time/flash counts over three repetitions; no acceptance threshold is asserted before those Nurion measurements are reviewed.

The gas-composition profile now also exercises the original LH2DT low-level
`from_rho_u` path with explicitly configured BoundedMixtureInventoryProperties.
Its environment therefore needs the same reviewed/pinned LH2DT native dependency
used by existing equipment cases, in addition to CoolProp/SciPy. A standalone
thermo-only environment is insufficient for that authored native integration seam.
No installation or execution of this profile occurred locally.

## Source-bound accident/consequence uncertainty bridge

The `joint-uncertainty` profile includes the synthetic deferred
`facility-accident-source-bound-uncertainty` contract. It reuses the existing
latent/joint QMC and `UncertainModel` propagation path, while each accepted row
retains the typed accident chain, exact source/dispersion handoff, consequence
receipt and scalar-reader response. A post-capture output mutation must invalidate
the joint result's freshness check. The fixture is software-plumbing evidence only;
it does not validate exposure/consequence physics, assign event frequency, or
establish a physical uncertainty law. This profile requires an actual
`H2_CLUSTER_JOINT_UNCERTAINTY_*` runtime configuration before campaign collection.
The case has been added to both Hangang and Nurion source plans and has not run.
