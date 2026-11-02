# Preferred dispersion providers

User selection: **HyRAM+ for high-pressure gaseous hydrogen; SLABx-LH2 for
liquid-hydrogen-origin dispersion**. The release family is an explicit physical origin,
not inferred from current pressure or phase: vapor from an LH2 pool still belongs to the
LH2-origin path. DEGALI remains an explicit comparison/research provider. No failed,
missing or out-of-domain preferred engine triggers an automatic substitute.

This changes provider priority. It does not transfer validation or make every source
boundary compatible. The current catalogue has 81 families; current implementation
levels are reported in MODEL_CATALOG.md and execution evidence is in PROGRESS.md.
Adding alternative engines within one family
does not add families to that count.

## Versions and installation

The checked releases are HyRAM+ 6.1, SLABx 1.0.8 at revision
`820e368ba6454aad8627dac5967115d9648c80c7`, and SLABx-LH2 0.2.0 at revision
`1ef613102819de1c2feebd062aff3b49997e1927`. The latter is not the older PyPI 0.1.5.
Exact compatible requirements are `requirements/native-preferred-dispersion.txt`.
Use them in a dedicated Python environment with the host installed; these are deep
Python adapters and need no JSON files, server or interprocess transport.

```powershell
conda env create -f environment.yml
conda activate h2physics-py312
python -m pip install -r requirements/native-preferred-dispersion.txt
```

The local replay uses separately installed ignored targets:

```powershell
.venv\Scripts\python scripts/check_preferred_dispersion.py --hyram-packages artifacts/native_hyram_packages --slabx-packages artifacts/native_slabx_packages
```

HyRAM 6.1's dopri5 solout callback raises a TypeError with the default SciPy 1.18.1
environment. SciPy 1.16.3 runs the checked native case. Neither the native solver nor
SciPy callbacks are patched. The main host environment remains unchanged. Historical
PRISM exact pins still require the compatibility changes in request 002.

## Ownership and Python API

`dispersion.preferred_dispersion_provider(release_family)` returns the preferred engine
identity. The caller supplies an explicit `HydrogenReleaseFamily`. This selection is
separate from installation, numerical acceptance and source-specific validation.

`dispersion.DispersionScenario(family, inputs)` is a lazy, direct Python request.
It copies the input mapping into a read-only proxy; a supplied `solver_options`
mapping is copied separately and also made read-only. Nested option containers are
fingerprinted at construction and checked again before provider invocation, so a
mutation cannot silently change the call after the scenario was prepared. Native
domain objects and callbacks retain their caller-owned identity. The scenario exposes `provider_id`, and
`run()` dispatches only to the route for the declared origin. It returns a
`DispersionExecution` receipt with the provider identity, source evidence,
reported acceptance flag and actual adapter result. Receipt construction checks that
acceptance and evidence IDs agree with the retained native result/source boundary;
evidence IDs must be explicit. `require_accepted` must be a real Python `bool` at
scenario construction and direct route invocation; integer and string truthy/falsy
substitutes are rejected before provider work begins. The underlying direct HyRAM
and SLABx-LH2 run/project entrypoints enforce the same boolean contract, so callers
cannot bypass the guard by skipping the scenario facade. Executions are issued only
by `DispersionScenario.run()`;
direct construction and dataclass replacement cannot claim that a preferred provider
was run. A failed request raises
`DispersionExecutionError` chained from its original error and retains any
provider failure result. Call `execution.require_current()` before downstream use;
it fingerprints the retained provider result and receipt declarations so later
mutation cannot silently preserve stale acceptance/evidence. This is a data-integrity
check only and does not rerun the provider or establish scientific validity. The
issuer guard proves call provenance within this Python process; it does not prove that
the supplied provider implementation is genuine, current, or scientifically valid. A
mapping with a gas family cannot call the LH2 adapter
and vice versa. The convenience functions
`run_preferred_gas_dispersion` and `run_preferred_lh2_dispersion` expose the
same routes as typed keyword APIs; native callbacks and physical objects remain
caller-owned. These wrappers do not adapt source physics between the providers.

`adapters.hyram.run_hyram_gas_jet` takes actual native Fluid/Orifice/Jet factories,
upstream and ambient `ThermoState`, `NozzleOpening`, `SourceLocation`, source evidence
and explicit solver options. The current checked route is stationary normal Hydrogen,
P0 > 2 Pambient, calm Air and the global x/z plane. HyRAM owns orifice flow, notional
expansion, Gaussian establishment and jet integration. It receives upstream conditions,
not a previously choked shared-nozzle result. The actual native Jet and read-only
centreline snapshots remain directly accessible. `HyRAMJetRun.require_current()`
checks the retained native flow and Gaussian section arrays against the original
admission receipt. Downstream finite-source projections invoke this freshness gate
before reuse; changing native flow or flux arrays invalidates the captured admission
rather than inheriting its previous accepted flag. This detects mutation and does
not repeat the solver or validate field accuracy. Direct `HyRAMJetRun` construction
also recomputes the Gaussian entry rate, maximum transport drift, maximum source-flux
residual and accepted gate from retained native arrays. Forged summary scalars or an
inconsistent accepted flag are rejected.
The preferred wrapper takes those factories as `fluid_factory`, `orifice_factory`
and `jet_factory`, then forwards the declared upstream/ambient states and opening
without pre-running the shared nozzle. It preserves the existing mass rejection and
diagnostic controls.
The HyRAM finite-source projection seals its declared mass/enthalpy budgets and
ledger scalars at construction; downstream reuse rejects changes to those receipt
values as well as source/native mutation. The deferred contract includes a budget
mutation negative case and remains unexecuted.

The host integrates the declared native Gaussian H2 flux analytically and compares it
to native upstream flow. Gaussian-entry mismatch and subsequent ODE transport drift are
reported separately. Failure raises `HyRAMJetError` with its raw native result;
`require_accepted=False` is an explicit diagnostic run, not a qualified prediction.
Energy, experimental field accuracy, wind, impingement and ground interaction are not
proved by this mass gate.

`adapters.slabx_lh2.steady_vapor_pool_boundary` maps an existing finite
`IntervalMassSource` to an actual native EvaporatingPool. The checked boundary requires
pure normal-H2 vapor at the declared atmospheric pressure, a ground-relative upward
flux, explicit fixed footprint/evidence and equal interval mean rates. It preserves
temperature, mass rate and duration; absolute source origin is retained separately from
the native relative clock. Varying rates/areas are not silently averaged. Current
temperature/phase/property assumptions are those of the chosen native emission backend;
this boundary does not prove conservation of native regenerated density/enthalpy.

`run_slabx_lh2` takes actual atmosphere/emission/water objects, runner, post-run premise
checker and native width-coupling context factory. The completed native trajectory,
requested/used source and diagnostics remain available. Nonfinite or exceeded w_c/u,
changed fixed source area and source-inventory mismatch are rejected by default, with
the failed native object in `SLABLH2Error`. Water/ice behavior must be selected explicitly;
the replay uses the native idempotent correction around its native CoolProp backend.
The native width patch is process-global, so parallel workers need its documented
process isolation. That concurrency limitation does not impose a service API.

The present LH2 bridge is a steady resolved-vapor footprint over a finite duration.
Liquid jets, unresolved droplets/impact, dynamic footprints and nonstationary emissions
remain additional native-boundary work. The user preference does not justify discarding
those source requirements or hiding a failed applicability gate.
The preferred wrapper accepts the same explicit vapor source, footprint evidence, native
atmosphere/thermo objects, runner, premise checker and width-context factory as the direct
adapter. It does not produce the vapor source from an LH2 leak or couple to pool spreading.

For source histories whose interval rates differ, `run_preferred_lh2_quasi_steady_slices`
offers an explicitly separate screening path. It runs one ordinary native steady SLABx-LH2
case per positive-mass `IntervalMassSource` bin, keeps the parent clock edges and interval
masses, and leaves zero-mass bins without a run. The returned `SLABLH2SnapshotSeries` marks
`plume_memory_included` as false and exposes both per-bin gates and `all_snapshots_accepted`.
Each interval begins an independent native plume calculation;
the snapshots must not be stitched together or interpreted as a transient concentration field.
This API makes the existing steady engine usable for time-sliced screening while leaving a
native time-dependent plume-source implementation as a receiving-project extension.
The API accepts either one fixed footprint/state or per-bin footprints and explicitly supplied
`ThermoState` projections. Per-bin state changes require one caller-owned evidence ID per active
bin and a compatible property basis; the receipt retains those state and footprint choices.
Each run audits requested settings against both the constructed native pool and SLAB's final
used source, including resolved temperature after any native boiling-point clamp. Dimensioned
`SLABLH2SourceTolerances` gate rate, duration, area, temperature and mass independently.
The completed-run receipt rechecks its source-boundary seal after runner and premise
callbacks return, so callback-side edits cannot be recaptured as a fresh baseline. The
series receipt also requires each retained native bin to use the exact absolute parent
clock edges; matching rate, duration, and mass do not authorize shifting a steady result
to another release window. Deferred contracts cover callback mutation and this clock
alignment guard; neither has been executed.

`SLABLH2SnapshotSeries.source_bin_ledger` exposes one typed record per original parent
interval, including zero-mass bins. Each entry joins its exact source window, parent
clock/evidence, interval mass and mean rate to the corresponding condition, native run
and acceptance status. `require_current()` delegates to the retained series integrity
guard. This is a source/run ledger for organizing independent steady snapshots; it does
not turn the snapshots into time-resolved plume data or include plume memory. The
deferred `selection-preferred-dispersion` contract checks exact alignment and mutation
rejection; it has not been executed.

`run_preferred_lh2_quasi_steady_slices` also accepts a caller-owned
`concurrent.futures.Executor` for parallel execution of its independent positive-mass
bins. The caller must provide a nonempty worker-isolation evidence ID; the adapter
never creates or sizes an executor. Source windows and boundaries are prepared in
parent order before submission, and completed runs are reassembled into their original
interval slots even when worker completion order differs. If a task fails, the error
retains every aligned completed run and all failed bins while preserving the legacy
completed-prefix view. This is useful for independent snapshot screening only. The
native SLAB width-coupling state is process-global, so the caller must ensure that the
selected executor/provider arrangement isolates it. The synthetic deferred case
`slabx-caller-executor-snapshots` checks orchestration and receipt mechanics; it does
not establish real provider thread/process safety.

The unresolved HyRAM plug-to-Gaussian H2 mass gap stays fail-closed. The host now
provides `adapters.hyram_transition.capture_hyram_radial_plane()` and
`audit_hyram_source_transition()` to seal caller-supplied same-run radial snapshots
and audit H2/mixture mass, axial momentum and excess-energy balances with independent
residual and quadrature-error budgets. Unknown source, entrainment, force, energy,
or plane-property inputs remain `incomplete`. This audit does not modify HyRAM's
initialization, supply the native snapshots, or establish measurement accuracy.
Its synthetic `hyram-plug-to-gaussian-transition-ledger` case is listed in both
Hangang and Nurion plans and remains unexecuted. The source matrix and native
snapshot contracts remain specified in
[`research/hyram_gaussian_entry_receiving_plan.md`](../research/hyram_gaussian_entry_receiving_plan.md)
and [`integration_request_012.md`](../research/integration_request_012.md). No host
scaling or fitted correction is allowed.

## Actual numerical evidence

Read `research/preferred_dispersion.md`. The authored HyRAM case executes, but its
Gaussian entry carries about 0.76687 of the native upstream H2 flow: about 23.31% is
missing at this interface under the strict host mass contract. Subsequent ODE H2 flux
drift is about 1.63e-10 kg/s. This isolates an initialization mismatch from integration
drift; it is not a blanket judgment of HyRAM's experimental evidence. No lambda fitting
or scalar output correction is applied. The default host gate rejects that case.

The authored LH2 vapor case emits 0.02 kg over 20 s. At 5 m/s wind, source inventory,
fixed area and the post-run premise gate pass. At 0.2 m/s, the native model also warns
about its wind domain and returns max w_c/u about 3.67; the host rejects the trajectory.
These are software/source/applicability checks, not independent concentration validation.

## Sources, rights and receiving work

HyRAM+ [official source](https://github.com/sandialabs/hyram) and
[native Python API](https://github.com/sandialabs/hyram/blob/master/src/hyram/README.md)
are GPL-3.0-only; the separately installed engine retains those terms. SLABx
[source and license](https://github.com/lyullee/slabx) and
[SLABx-LH2](https://github.com/lyullee/slabx-lh2) retain their MIT licenses.
This host does not copy or bundle their implementation or upstream observations.
Do not label a combined redistribution of a GPL engine as entirely Apache-2.0.
Source selection, scientific suitability and license obligations remain distinct.

Request 012 records the reproducible HyRAM/SciPy and source-interface gaps, the steady
SLAB source limitation, native object/flux contracts and acceptance cases. It is stored
locally for another session; no receiving repository was edited or contacted.


SLABLH2Run receipts are issued only by the actual run adapter. Direct construction
or dataclass replacement cannot turn caller-supplied trajectories and applicability
mappings into native execution evidence; downstream preferred dispersion retains the
issued receipt's currentness check. The issuer contract is enrolled in the model-selection
profile and remains unexecuted.
