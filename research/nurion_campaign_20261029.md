# Nurion validation campaign: 2026-10-29

This record separates the submitted scientific checkpoint from later source changes.
It is an execution receipt, not a claim that any model passed validation.

## Submitted checkpoint

- Git revision: `985a32a4c4e7fb734a93a33194e9071022803690`
- Remote root: `/scratch/CLUSTER_USER/h2physics_nurion_20261029_985a32a`
- Validation job: `24229527[].pbs`
- Result collector: `24229528.pbs`, held on `afterany` of the validation array
- Workload: 183 unique deferred cases across 33 profiles
- Packing: eight PBS array elements, at most eight single-thread workers per element
- Resource request: one 64-CPU node per array element, 12-hour wall clock

The collector scans every outcome record after the array terminates and writes
`results/summary.json`. A failed worker remains visible as a failed or missing outcome;
the array wrapper does not turn a scientific failure into a passed result.

## Reproducible environment

The campaign uses the site Python 3.12.5 executable and a compute-node-local extraction
of a reviewed Linux wheel archive. The archive SHA-256 is
`785fb545f8d7bfaac73c174923fc55e3a38de1c46685ea2ec1eaccbcc7696ce4`.
Core imports checked before submission were NumPy 2.2.6, SciPy 1.16.3,
CoolProp 8.0.0, Cantera 3.0.1, HDF5, spreadsheet, hydraulic, tabular and impedance
packages. The archive is unpacked under each PBS job's node-local `TMPDIR`; it is not
installed from the network on a compute node.

The pinned plan SHA-256 is
`b63cc0598a2dcc42595ca5b57d810818f2704c6e646a466a11b630ccaace78de`.
Preflight required an exact clean source revision, matching plan and job hashes, 183
unique identifiers, importable dependencies and valid shell syntax.

## Scope boundary

This campaign validates only revision `985a32a`. The counterflow heat exchanger,
finite electrochemical thermal inventory and finite thermal target added concurrently
after submission are intentionally excluded. Their twelve deferred cases belong to a
later revision-specific campaign. This prevents results from being attributed to source
that the compute nodes did not receive.

No acceptance result is recorded here until the collector output is retrieved and
audited. Native-provider absence, domain rejection and numerical failure are evidence
to retain rather than reasons to substitute a different physical model silently.

## Recovery campaign for the Git-free worker

The first array and collector, `24229527[].pbs` and `24229528.pbs`, completed,
but the collector reported 0 of 183 outcomes. Worker logs showed that `git` was
unavailable on compute nodes, so all cases stopped before their scientific entrypoints.
Those jobs provide no model validation evidence.

The worker now supports an explicit SHA-256 manifest and source receipt, avoiding a
runtime Git dependency. The recovery campaign pins revision
`0082aa270da5f23c046e56ee7b0c96a5b6d16f84`, source manifest
`1c2d4491f0db9e6683ed6454a43ce1687e3a863bafdebd8031845ea7fcd68818`, and plan
`ca09db9ac797900b7848161afb29d88fcb8da7823ed2774c1495c83875219f67`. The explicit
plan contains 199 unique cases across 37 profiles, including sixteen additional
definitions added after the original 183-case pin. Eight array elements each request
one 64-CPU node and run at most eight single-thread case workers. A collector is held
with `afterany` and reports every observed outcome and every missing case.

The first recovery array was `24229537[].pbs`; its collector was `24229538.pbs`.
All eight array elements started, but worker dispatch failed before scientific case
entry. The explicit-manifest branch verified the snapshot but had not assigned the
`revision` local later used in `attempt.json`, producing `UnboundLocalError` for each
case. The array ended with0/199 outcomes and provides no scientific evidence. Its
collector ran afterany and recorded the empty set. The failure was reproduced in the
array stdout and fixed in revision `8cab6a0373a8484b691b7f52a6822321bcdff3b6` by
initializing the revision from the explicit pin before selecting Git or manifest mode.
All cluster resources were released; a replacement campaign is being prepared against
that new complete snapshot, with a new manifest/plan pin and worker preflight required
before resubmission.

Before the failed dispatch, the compute-local setup smoke test imported NumPy 2.2.6,
SciPy 1.16.3, CoolProp 8.0.0, Cantera 3.0.1, h5py and pandas. Shell syntax, plan
uniqueness, source-manifest verification and modified-file tamper detection passed.

The counterflow heat exchanger, finite electrochemical thermal inventory and finite
thermal target developed after the original campaign are included in these 199 cases.
The later HyRAM line-source receiver-radiation definitions are not included; preserve
them for the next source/plan revision. The correction only restores execution and pins
the exact code. A queued job is not validation, and each outcome still requires review.

## Corrected recovery submission: `502598f`

The corrected worker was committed and the next clean snapshot was pinned to
revision `502598ff41bea083f4e695070509e23fde83602f`. Its source manifest covers
725 files and has SHA-256
`b7ceb007526908320c7afdc3736d113b7299888691c996d1a261b54081f57ae3`.
The plan is SHA-256
`c2c0e795d785395cce6eba47a8322698c3dbaa00ab27b17859500dfbe7848645` and contains
199 unique cases across 37 profiles. Source/plan hashes, case count and the
compute-local Python 3.12.5 imports for NumPy, SciPy, CoolProp, Cantera, h5py and
pandas were checked before submission. PBS shell syntax also passed.

Validation array `24229556[].pbs` was submitted with collector
`24229557.pbs` held on `afterany`. At the initial status check the array was queued
and the collector held. The array later terminated with all199 case outcome files
present. A source-aware read of top-level outcome records found77 `passed` and
122 `failed`; these raw states do not establish accepted model families. The collector
`24229557.pbs` completed with exit status0 and wrote
`/scratch/CLUSTER_USER/h2physics_nurion_20261029_985a32a/results/recovery_502598f/summary.json`.
Its counts confirm199 observed,0 missing,77 passed and122 failed.

Preliminary failure categories are strongly environment/input-limited: 72 missing
Python modules, seven missing package metadata records, twelve explicit Cantera 3.2
requirements against the supplied 3.0.1 runtime, six absent relief fixtures, four
missing FDS executable declarations and two missing licensed source-root declarations.
Other failures include native integration/energy gates, incomplete source interfaces
and numerical/reference constraints. Two finite exchanger cases rejected on closure
or hot-side ordering, and one flame reference rejected on its flow condition. Preserve
their original tracebacks and results;
do not relabel them as passes. The next campaign needs profile-correct setup paths,
the source scripts directory on `PYTHONPATH`, matching Cantera and actual fixtures
before rerunning affected cases. No local scientific tests were started.

This pin excludes the later immutable counterflow-profile API, bounded measurement
sampling and its four deferred cases. Those require a later clean source and plan
revision. The file-level counts are reconciled; classify every failure and review each
passed invariant before assigning scientific family acceptance.

## Focused correction rerun: `1134c7b`

The previous remote source directory was a reduced validation-only tree and could not
accept the complete Git patch. A fresh archive from the exact local source snapshot was
transferred through the already-open KISTI wrapper and expanded in the dedicated
scratch campaign folder. All 727 SHA-256 manifest entries passed verification; source
revision, plan hash, PBS shell syntax and the existing Python 3.12.5 dependency archive
were checked before submission.

The focused plan contains five cases: three compressor-map checks and two spatial
counterflow heat-exchanger checks. Array `24229573[]` completed all five tasks and
collector `24229574.pbs` wrote a summary with zero exit status. The compressor map's
three authored checks and HX refinement case passed. The small-UA HX case failed:
`least_squares` terminated by `xtol` with normalized equation residual
`4.0638853913834715e-05`, above the declared `1e-9` gate. The exchanger solver has
since been changed to duty-scaled dimensionless unknowns while retaining the same
equation acceptance tolerance. This changed source requires a new pinned run; no
family-level accepted evidence was added from this five-case campaign.

## Receipt-fix and counterflow reader rerun: `31c0ea8`

The failed `20168b8` submission was diagnosed as a source-manifest false mismatch:
the generated `SOURCE_REVISION.txt` receipt was included in the manifest and changed
under text newline conversion. Source-manifest generation now excludes that receipt.
The new source pin is `31c0ea86f2f5c43b758d5fcb18dfe36b8d581422`; its 728-entry source
manifest SHA-256 is `8a5e9e9d7c4562020ec150b05bf6015201ca0ec3ad24c3a19b7d10c7c5997933`.
The Python plan SHA-256 is `b021df3b4063966e013c97021d9a23a686062ef090940bdbe69e20c0a2240695`.
Remote verification checked every manifest entry, the exact revision and plan, PBS
shell syntax, the acquired archive SHA-256, and all eight publisher BagIt payload
checksums before submission. Array `24229619[]` contained two cases: the rescaled
low-UA counterflow exchanger and source-bound ingestion of extinction, temperature
and H2/NH3/NO data. Collector `24229620.pbs` depends on array completion. Both array
cases completed with failures. The exchanger residual was `0.0833333726810391`; the
unknowns were expressed as inlet-relative offsets but the closure equations still
subtracted rounded absolute enthalpies. The data gate expected 13 source rows, but
workbook inspection shows eight measurements at rows 2-9 and five blank trailing
rows. Source metadata now records the actual eight observations, and energy closure
equations use relative offsets directly. The collector had not yet completed at this
log update. No scientific acceptance is inferred from these failed cases.

After this pin, the data API was extended to sixty normalized spatial optical
profiles, three spatial band-integral series and three wavelength spectra. The next
source pin must run the expanded ingestion case separately; these optical readers are
not covered by array `24229619[]`.

## Direct-offset and full reader rerun: `3c47086`

Revision `3c470862395e03cef21a803a6eb6d4e98f4c969e` uses direct relative-enthalpy
differences in the heat exchanger closure equations, corrects the measured ESR row
count to eight, and includes all six source-bound data reader paths. Its complete
728-entry manifest SHA-256 is
`634bf186cf13bfe88aad0b646150f41f4a9a736fbb452255ee527392087a2bd5`; plan SHA-256 is
`2fd1833bfaac40113b235ab1edca8f1a722d236a7a4e5670e0977de56e33625e`. The remote
manifest, plan, PBS shell syntax, archive digest and all publisher payload checksums
passed before submission. Array `24229638[]` ran the corrected low-UA exchanger and
full source-data ingestion gate. The exchanger passed with limiting duty
`1.7600134015083315e-6 W` in 15.40 s. The reader worker stayed at 13 s CPU across more
than four minutes of wall time and created no outcome file, so its array element was
stopped (PBS exit 271); collector `24229639.pbs` depends on array completion. The
reader now streams each worksheet once rather than requesting each cell repeatedly.
The optimized reader needs a new source-pinned Nurion case. One exchanger invariant
passed; this does not change accepted-family evidence or establish apparatus
validation.
