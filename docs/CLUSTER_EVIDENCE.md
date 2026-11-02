# Deferred campaign record collection

Status: **implemented_unverified infrastructure**. The collector has not been
executed. No case, result fixture, scheduler query, model, native import or
remote connection was run to develop it. Static syntax/lint inspection is not
runtime verification. Scientific execution remains deferred by user instruction.

`h2physics.cluster_evidence` reads existing, explicitly selected output from
`h2physics.cluster_validation`. It never imports a scientific case entrypoint,
executes a model, contacts PBS or selects the newest retry by modification time.
Inputs/outputs are Python objects. The JSON files it reads are the worker's
internal attempt/outcome audit records, not a model input or service API.

## Explicit campaign and runtime identity

Construct `RuntimeExpectation` with an actual `ClusterProfile`, the expected
complete `sys.version` string, absolute cluster environment prefix and exact
critical distribution versions. Package names are normalized for their standard
case/hyphen/underscore spelling; ambiguous aliases are rejected rather than
choosing a version. These are installed-distribution metadata checks. They do
not prove which native module bytes were selected by every callback. The
`ClusterProfile` separately pins the setup-script SHA-256; generated workers check
it before and after sourcing and the collector checks the recorded digest against
that profile pin. This covers the direct script bytes; transitive scripts, modules
and commands need separate pins or runtime evidence. Source-specific native audits
remain necessary.

Construct `CampaignExpectation` with the ordered actual `ValidationCase` objects,
runtime expectations keyed by profile, an explicit selected PBS job ID for every
case, the full40-character Git revision, plan SHA-256 and the original canonical
cluster results root. Actual jobs and paths are later inputs; none is invented
for the prepared campaign. Cluster paths must be normalized absolute POSIX strings
below `/`; duplicate separators, `.` segments, trailing separators, parent segments,
backslashes and control characters are rejected instead of silently canonicalized.
Retrying a case requires an explicit new job selection.

The local results root may be a copy or mount of the completed evidence. Its
physical path can differ from the original cluster path. Each report must retain
the expected original cluster working directory, case/index/job, source/plan,
profile/interpreter, environment, acceptance invariants and critical versions.
The setup-script digest is part of that identity and must match the plan-pinned
profile value.
The final outcome must agree with the original attempt identity and environment.

The API deliberately does not reconstruct a campaign plan with `runpy`, import
its source or infer identity from a directory name alone. Supply the expected
metadata from the pinned, trusted campaign definition.

## Collection and status meanings

Call `collect_campaign_evidence(expectation, results_root, budgets=...)` with
explicit `CollectionBudgets`: maximum report bytes, regular files, aggregate
artifact bytes and traversal paths per case. Hashing is streamed and traversal
is bounded. Native data files are never unpickled, loaded as arrays or executed.

The selected directory is `results_root / selected_job_id / case_identifier`.
Only that selection is considered. Status is one of:

| Record status | Meaning |
|---|---|
| `missing` | The explicitly selected case directory is absent |
| `incomplete` | The original attempt or atomically completed outcome is absent |
| `inconsistent` | Identity/schema/environment, path/budget, atomicity or changing-file evidence prevents reconciliation |
| `passed` | A consistent worker outcome reports that its declared case validator accepted |
| `rejected` | A consistent worker outcome reports physical/numerical rejection |
| `failed` | A consistent terminal outcome retains the original exception and traceback |

No incomplete job is assigned the last known successful status. Duplicate JSON
keys and unlabeled nonfinite/overflowed JSON numbers are rejected. Native
unreachable/infinite values may remain in artifact files; the worker's explicit
nonfinite metric labels remain intact. Numeric scientific meaning belongs to
the individual validator, not this collector.

Passing records need named metrics and retained limitations. Failed records keep
exception type/message/traceback; an empty assertion message is valid and does
not erase the traceback. Elapsed time must be finite and nonnegative. A leftover
outcome temporary file or records changing while artifacts are hashed prevents
reconciliation. Artifacts receive relative paths, byte sizes and SHA-256. Symbolic
links, nonregular files and directory redirection are rejected. Select quiescent
results; this is not an adversarial filesystem or cryptographic remote attestation
service.

`CampaignEvidence` reports counts, `all_records_complete` and
`all_cases_reported_passed` separately. Complete records can include rejected or
failed cases. A terminal record is not a live scheduler/process query and does
not independently prove that a job has exited. No automatic rerun is performed.

`scientific_qualification_established` is always false. Even every declared case
passing does not establish missing model physics, source/phase/reference
compatibility, independently measured accuracy, a full accident chain or public
release acceptance. Native outputs and numerical/experimental gates must be
reviewed at their actual scope. The last executed checkpoint remains unchanged
until those executions actually occur.

## Continuation workflow

After the later cluster connection, configure actual source/environment/queue
and generate the declared cases as described in NURION_VALIDATION_PLAN.md. Once
the relevant result records exist, explicitly select attempts, supply expected
runtime metadata and call this collector. Inspect every case status, original
traceback, limitations and native artifact audit. Missing/rejected/failed records
remain unresolved; do not replace them by an aggregate percentage.

The nonexecuting API example is `examples/cluster_evidence.py`. No results root,
fake passing files, job IDs, credentials or scheduler connection is created by
that example. Keep actual raw outputs under ignored evidence directories;
publishing source documentation does not publish private runtime inputs.
