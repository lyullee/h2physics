# Development history and evidence ledger

This document reconstructs the decisions and executed evidence available at the 2026-11-02 research checkpoint. Dates describe recorded development, not public release dates. A package build, upload or DOI assignment needs its own receipt; none is inferred here. Use [Research continuation](RESEARCH_CONTINUATION.md) to resume without the development conversation.

The detailed [working log](DEVELOPMENT_LOG.md) remains historical evidence. Later, explicitly scoped campaign reports supersede approximate early progress estimates. Do not erase a failed or limited result simply because a later, different example passed.

## 1. Project purpose and implementation roles

The package composes hydrogen equipment, storage, production, material transport, accidental release, dispersion interfaces, combustion/effects and facility support through direct Python APIs. Parameters, callbacks, physical states and arrays remain inspectable. No HTTP service or serialization layer is required.

Project-owned equations cover scientifically distinct needs. Separately installed domain engines supply capabilities that already exist elsewhere. Host adapters bind their actual results and check material, units, phase, caloric reference and clock support; they are not duplicate implementations of the engines.

The [architecture](ARCHITECTURE.md), [API index](PUBLIC_API_INDEX.md), [catalogue](MODEL_CATALOG.md) and [model-selection contract](MODEL_SELECTION.md) define individual model levels. A family name is broader than a single equation or callable.

## 2. Count reconciliation

| Number | Recorded meaning | Not implied |
| --- | --- | --- |
| 82 | Engineering catalogue families at the checkpoint | 82 independently validated physical models |
| 78 | Selected topic-family scope of the staged campaigns | All equations or optional resolutions counted separately |
| 78 first-level entries | Census found a substantive calculation or native-call entrypoint in every selected family | Every higher-fidelity extension, dataset qualification or receiving-engine feature finished |
| 72 | Selected families with a positive normal module handoff | Full-system physical qualification |
| 4 | Own-model closures compared with measured data | Four formally qualified model families |

Four catalogue entries are outside the 78-family campaign list: `thermo.acceleration`, `storage.extended_langmuir`, `storage.adsorption_delivery_mass_flow` and `dispersion.fixed_flow_snapshots`. This is a scope decision, not evidence that they lack code.

Historical labels such as implemented, native-adapter-verified and implemented-unverified describe implementation evidence at their recorded revisions. Earlier catalogue ratios and whole-programme estimates must not be used as current completion percentages. The family tables in the focused reports identify actual checks.

## 3. Architectural decisions

| Decision | Reason | Continuation rule |
| --- | --- | --- |
| Native CoolProp or qualified provider-derived tables | Avoid conflicting local fluid-property libraries | Preserve backend, fluid/spin, reference and phase domains; no silent ideal fallback |
| Optional native engines | Avoid overlapping equivalent solvers | Request missing receiving capability instead of fabricating a result |
| HyRAM gas / SLABx-LH2 liquid-origin preference | Make provider ownership explicit | Failed preferred execution remains a failure, not an automatic switch |
| Finite material and energy ledgers | A rate alone does not define finite inventory or a product | Retain accepted windows, inventory floors, signed heat/work and termination |
| Explicit material/reference/clock identity | Plausible numbers can describe incompatible systems | Require explicit conditioning and mapping evidence |
| Python-first composition | Research needs direct model access | Keep typed inputs, Protocols and inspectable results; persistence is optional |
| Separate evidence statuses | Compilation, analytic agreement and experimental agreement answer different questions | Never promote a software pass to physical validation |
| External observations outside distributions | Dataset, code and embedded component rights differ | Publish original loaders, metadata and aggregates; exclude raw bundles by default |

## 4. Foundation and source inventories

The foundation established package structure, SI conventions, physical-basis objects, immutable numeric arrays, optional dependencies, checksum-bound acquisition and observation schemas. Source inventories preceded quantitative comparisons. A public URL, downloaded file or parsed workbook was not treated as a qualified experiment.

Loaders preserve source row identities, masks, irregular clocks and unresolved unit conventions. They do not silently replace missing measurements, normalize unknown quantities or remove inconvenient observations. Explicit ideal or constant-property closures remain analytical test references; production properties use their declared native owner.

## 5. Model and adapter expansion

Recorded work through 2026-10-29 added finite equipment states, native tank/pipe/pump/vaporizer composition, storage and carrier operations, reacting volumes and selected material/safety levels. Shared conservation kernels were reused when the resolution was unchanged. Distinct physics or numerical resolution remained a separately named model level.

Accepted withdrawal, manufactured hydrogen, an accident source, a heat duty and a priced quantity were kept as different boundaries. A source needs location/opening, phase, time support and termination; nominal process flow does not supply those implicitly. Native accepted states were distinguished from interpolation samples.

## 6. Finite coupling and ownership, 2026-10-30–31

Work shifted toward genuine producer-to-consumer paths: inventory to source/receiver, reaction heat to utility ledgers, material flux to release boundaries, sensor output to alarm/isolation and supplied consequence to conditional risk. Source/version ownership and changed-result detection became explicit.

Operating windows replaced ambiguous time assumptions. Partial failures retain completed intervals and rejected candidates. They do not return a successful-looking incomplete calculation. Conditional risk requires explicit branch and frequency evidence; a mission failure probability or monitoring score is not automatically an annual event frequency.

Parallel execution preparation introduced source manifests, setup/plan revisions and case receipts. Source transfer, queued work and completed execution are different records. Historical remote results apply only to their exact source/environment. Public continuation uses generic configuration and user-managed credentials, not original execution identities.

## 7. Native property integration, 2026-11-01

The CoolProp migration extended to mixture linepack, same-level quasi-steady pipe momentum, reservoir/nozzle paths and shared caloric references. Endpoint inventories and native Darcy relationships were kept consistent; changing density alone would not establish a consistent real-fluid momentum law.

Interpolation retained direct-provider qualification, bounded domains and no extrapolation. A table was not promoted as a faster default when the measured workload was slower. Sampled acoustic speed and the derivative of a pressure interpolant were separated because they are different numerical closures.

Linepack-to-fuel-cell and electrolysis-to-linepack paths retained source enthalpy, reference offsets and explicit conditioning energy. Their accounting does not infer a regulator, compressor, receiver trajectory or heat-transfer process.

Measurement transcription, phase consistency and prediction accuracy were kept separate. Source conflicts remained visible instead of being corrected to improve agreement. Historical diagnostics of existing property engines do not become validation of newly authored host physics.

## 8. Staged verification, 2026-11-02

| Stage | Final executed evidence | Scope | Report |
| --- | --- | --- | --- |
| Input rejection | 162 passes: 161 malformed-input cases plus one manifest check; 78/78 families | Representative input contracts, not every argument | [Input](INPUT_CONTRACT_CAMPAIGN.md) |
| Nominal calculations | 67 passes across 66 families | 30 equation families, 35 supporting, one identity; 12 native cores excluded | [Calculations](FORMULA_CONTRACT_CAMPAIGN.md) |
| Extreme/boundary values | 108 passes across 66 families | 29 model numerical, 31 supporting, one calculated-domain refusal, one endpoint mapping, four domain-edge-only; 12 native cores excluded | [Extremes](EXTREME_CONTRACT_CAMPAIGN.md) |
| Module connections | 57 selected passes | 55 positive cases plus two rejection gates; 72 normal families, two boundary-only, two blocked/unavailable, two terminal | [Connections](CONNECTION_CONTRACT_CAMPAIGN.md) |
| Existing-feature regression | 50 selected passes in 12 original files | Selected original behavior, not full-repository qualification | [Basic replay](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) |
| Representative input to output | Six example passes | Tank transfer, hydride, pipe, PV, photochemistry and release-to-alarm | [Basic replay](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) |

The connection scope was subsequently limited to basic delivery, units, material identity and clocks. Deeper checks already executed in the 57-case historical run are preserved, but must not be relabelled as 57 basic-only checks or used to authorize new deep campaigns.

The final passing batches contain no failures/errors/skips. This does not erase retained failed native baselines or imply excluded tests passed. Each campaign records source pins and dependency assumptions. New source changes need their own selected replay; old totals are not evidence for every future revision.

## 9. Corrections exposed by execution

Nominal checks corrected pool-fire result snapshots that included temporary serialization-container identity and a flash-front seal that used a nonexistent time field instead of the declared arrival field. Actual unchanged results and intended altered-result refusals were checked afterwards.

Extreme tests exposed finite inputs producing nonfinite stack outputs and a raw solubility exponent overflow. Computed quantities are now checked, and the solubility closure translates overflow into a descriptive domain error. No silent clamping or new physical law was introduced.

Fixture corrections remain distinct from product corrections. Examples include an absent test saturation method, too few biological samples, a missing kg/kmol conversion, incorrect result names and native flash rounding at an exact envelope edge. Such errors do not prove the physical equation was wrong.

### Eight connection-stage host repairs

| File under `src/h2physics` | Correction |
| --- | --- |
| `adapters/facility_consequence.py` | Stable semantic code fingerprints; ignore temporary class mapping wrappers while detecting captured method/default/closure changes. Eight focused callback checks passed. |
| `storage/adsorption_dynamics.py` | Bind actual function and owner configuration rather than ephemeral method/metaclass wrapper identity. |
| `storage/finite_hydride.py` | Admit native field reflash roundoff at relative 1e-12, retaining exact basis/phase/quality checks and a separate issued-state content seal. |
| `adapters/adsorption_finite_hydride_port.py` | Separate numerical P/T roundtrip matching from exact post-issuance state integrity. |
| `adapters/cantera_fuel_cell.py` | Use indexed scalar writes in native callback buffers instead of unsupported list-slice assignment. |
| `adapters/diffusion_finite_source.py` | Recognize explicit hydrogen aliases and gas-family phase labels consistently in admission and currentness checks. |
| `materials/radial_thermoelastic.py` | Select displacement/derivative from a free-axial BVP that contains an additional state. |
| `combustion/turbine_map.py` | Restore reachable component-map seal initialization and place the point guard on the correct result type. |

External solver source was not patched. A new provider evaluation may differ by floating-point ulps; the original issued state's stored contents remain a separate integrity concern. Future changes should preserve this distinction.

## 10. Six connection exceptions

| Family | Recorded status | Meaning |
| --- | --- | --- |
| `combustion.jet_fire` | Rejection boundary only | A genuine selected flame/radiation result was refused; no accepted exposure handoff is claimed |
| `dispersion.outdoor` | Rejection boundary only | A qualified isolated runtime was used, but the chosen native result was refused |
| `storage.underground` | Native compatibility blocker | A root array reached a scalar CoolProp update; [request 038](../requests/038_uh2sc_coolprop_scalar_compatibility.md) records the receiving fix |
| `dispersion.obstacle` | External runtime unavailable | No genuine FDS executable/output was available |
| `production.biological` | Terminal result | No existing selected downstream consumer was found |
| `production.gasification` | Terminal result | No existing selected downstream consumer was found |

These are not six absent model implementations. Fabricated accepted results, automatic alternative engines and generic constructors were not used to fill the denominator.

## 11. Measured-data comparisons

Four own-model closures were compared with measured data. Coefficient-estimation data and evaluation data were separated by complete curves, temperatures, batches or operating conditions. None was promoted to formal qualification.

| Target | Separation | Evaluation result | Limitation |
| --- | --- | --- | --- |
| Effective permeance | 64 points at 350/450°C; all 32 at 400°C held out | Mean absolute relative error 2.15–4.06% across four membranes | Effective D*S/L only; individual D/S/thickness and uncertainty unresolved |
| Normalized hydride kinetics | 100 D/E/F/G curves; 44 H curves held out | Mean curve RMSE 4.49 percentage points absorption, 4.86 desorption | Capacity normalization, mean forcing, pressure/time interpretation and bounded parameters |
| PEM loss closures | First curves: 46 contexts; second curves: 56 | RMSE 23.102 mV, MAE 15.197 mV | Temperature proxy, same-cell repeats and exchange estimates at an upper bound |
| Fixed-coefficient nozzle | 13 low-flow scan rows calibrate; 22 high-flow rows held out | Mean absolute relative error 29.83%, underprediction | Ambient-temperature proxy, pressure losses and coefficient transfer |

A fraction RMSE of 0.0449 means 4.49 percentage points on a 0–100% display, not 4.49% relative error. Scan rows, curves and independent experiments are different statistical units. These unlike errors are not combined into a single overall accuracy.

Data sources are [Pd membranes](https://doi.org/10.5281/zenodo.10691625), [AB2 kinetics](https://doi.org/10.5281/zenodo.16458050), [PEM measurements](https://doi.org/10.5281/zenodo.19361280) and [HyTunnel](https://doi.org/10.5281/zenodo.4668554). Their source grants, versions, hashes and remaining conditions are documented in [Physical comparison](PHYSICAL_VALIDATION_CAMPAIGN.md). Original observations and per-row results remain outside distributions.

## 12. Numerical and admission findings retained

- The broader radial stress reference still fails its field assertions at its original default tolerance. Explicit tighter free/fixed runs meet the reference; the original result is not relabelled as a pass.
- A broader engine interval reached native trial-clock/volume gates. The positive interface example uses declared support and a shorter interval, not a qualified whole operating envelope.
- A deposited-pool baseline dried out and was correctly input-limited. A separate declared positive-stock input supports the accepted handoff.
- A failure-root baseline without a failed flag remains refused. A separately declared already-overlimit initial state supports a positive fragment connection.
- One existing arithmetic-guard warning remains in the basic compartment example; finite outputs and basic checks pass. No additional deep work was added in that stage.

## 13. Public continuation and release evidence

Public documentation retains original API descriptions, assumptions, methods and aggregate findings. Raw observations, native package trees, machine-local receipts and generated outputs are excluded by default. Historical artifact filenames identify outputs to recreate; they are not promises that every clone contains the local cache.

A release needs its own exact commit/version, archive hashes, clean-install result, source/dependency notices, public-tree audit and confirmed publication URLs. A prepared metadata file, login session or successful development build is not evidence that GitHub, PyPI or Zenodo publication occurred. Continue with [Research continuation](RESEARCH_CONTINUATION.md) and [Rights and provenance](RIGHTS_AND_PROVENANCE.md).

## Publication follow-up

Version 0.1.0 is public on GitHub, PyPI and Zenodo. The [service receipt](REGISTRY_ARCHIVE_RECEIPT_0_1_0.md) records source revision, distinct distribution hashes, scoped installation checks and DOI. These release-engineering checks do not change the scientific evidence or qualification limits recorded above. Use [publication status](PUBLICATION_STATUS.md) and current CITATION.cff for actual service links and version citation.
