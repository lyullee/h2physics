# Pool-fire development record — execution deferred

2026-10-28. Status: **implemented_unverified**. This record describes code and
static source/API inspection. It records no scientific execution, passing
native gate, calibrated H2 input or apparatus/field validation. Under the
latest user instruction, local pytest, scientific replay and benchmark jobs
were not started. Future Nurion validation remains pending.

The five owned files are the new adapter, `docs/POOL_FIRE.md`, this record,
`examples/pool_fire.py` and `validation/cases/pool_fire.py`. No shared physical
source, catalog, dependency receipt, requirements or external repository was
modified by this lane. The prior PV/electrolysis and verified native lanes
remain frozen.

## Actual API inspection and choice

The actual separate PRCT 0.1.0 installation exposes public `PoolInput`/`pool`,
`SphereInput`/`sphere` and `SolidFlameInput`/`solid_flame`. These retain strict,
frozen SI native inputs and native results. The first call owns finite fuel
consumption, remaining stock, active duration, active HRR and released energy
for a constant area and caller-supplied net consumption flux. The second owns
the restricted ground-tangent-sphere geometric factor and incident radiation;
the third transports supplied emissive power/factor/transmissivity. These are
used directly. No native equations, coefficient tables or implementations
were copied into host source.

Native `fireball` empirical size/duration correlations were excluded. The
available toolkit does not supply an admitted H2 net burning-flux or flame-
geometry correlation. The new adapter consequently requires evidence IDs and
origins for H2 flux, LHV, geometry, transmissivity and energy partition, and
uses synthetic authored values only in the explicitly unqualified example.
The existing failed jet-fire/native-jet-flame level is unchanged.

The existing `ConditionalRiskNative` loader is reused solely for artifact,
native-module and code-digest admission. This level calls the real fire API;
it does not compute a risk aggregate or annual event frequency. Additional
fire function/code/class bindings are retained and checked for rebinding.

## Finite composition and limits implemented

An actual normal-H2 saturated liquid/vapor state pair and original owner seed
the finite pool stock. Each native-consumed mass is explicitly gasified and
conditioned to a compatible normal-H2 gas/LHV reference. Its native enthalpy
increments consume a finite declared external energy budget and must fit its
declared active-power limit. No fire-to-pool heat feedback or inferred ambient
heat is supplied. This is a constant-pressure conditioning enthalpy boundary;
no closed pool/flame total-U solution is claimed.

The shared `StoichiometricReaction` converts the conditioned H2 with a finite
O2 stock to vapor water. Complete combustion/efficiency one is required. O2
depletion rejects the proposed stage with the native attempted result intact;
it does not silently change the prescribed flux. Initial water and remaining
O2 carry between contiguous stages. The native fuel mass, shared reaction
mass, native LHV energy, active HRR integral and caller energy partition have
separate retained residuals and acceptance budgets.

Radiative export drives the uniform supplied sphere surface emissive power.
The actual native sphere and solid-flame outputs are retained separately.
Exposure integrates the incident radiation over the native active duration,
including a finite burnout time. Convective export remains an energy ledger;
there is no receptor convection model. Unallocated chemical energy is explicit.
Product sensible thermodynamics, temperature, oxygen entrainment, flame mixing,
extinction/reignition physics, radiation feedback, background pool evaporation,
postignition spreading and replenishment remain unavailable.

The optional `PoolFireSeed.from_native_pool` path reuses an original admissible
`NativePoolRun`. Only its final remaining stock/area/time/phase state is handed
off. The original actual pool objects and complete preignition evaporation
source are retained and source contents are fingerprinted. Earlier vapor mass
is not consumed again. There is no radial-state restart or promoted rejected
pool output. The fire reactant `IntervalMassSource` is explicitly distinguished
from an unburned atmospheric dispersion source.

Failures retain their original exception cause, native input/result attempt,
stage, assembled failed step where available and completed accepted prefix.
The method returns the status and explicit unresolved-physics flags with every
trace; retaining an original native object does not make absent physics solved.

## Existing optional dependency receipt

The authoritative [upstream repository](https://github.com/lyullee/process-risk-consequence-toolkit)
and actual installed `ccps_consequence/fire.py` were inspected. The existing
[`risk_dependency.toml`](risk_dependency.toml) remains the unchanged artifact
and license receipt. No additional installation was needed. The separately
installed Apache-2.0 wheel, LICENSE, NOTICE and third-party notices remain
outside public host sources.

| Receipt item | SHA-256 |
| --- | --- |
| PRCT 0.1.0 wheel | `ca78d15bf1f0f38ba79d2381291059067380211658ca0dc2345584adb4adfd86` |
| All native top-level Python filename+bytes aggregate | `0d5239de3ba9a919a0a0b38a912fc86899d92f10da5e6a9e7a563d8abeec9152` |
| Actual native `fire.py` | `6c5713a1d03892a7ce24770f2edaca0d0e61123dc5d05d27dcf0245cb34b7da0` |
| Native LICENSE | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| Unchanged host risk dependency receipt | `9e8bb997527c23362a60480635a65d16618c4a2242acabad2e092dce9e2ede6c` |

The native fire source SHA is unchanged between API inspection and final
static freeze. Its source aggregate is independently reproduced by reading
sorted native `.py` basenames and bytes; the native module is not imported
to produce a scientific result. No external data or native implementation
was added to distributions.

[NOAA NOS OR&R 43 (2013)](https://response.restoration.noaa.gov/sites/default/files/ALOHA_Tech_Doc.pdf)
sections 6.1 and 6.3 are the public primary radiation/geometry basis referenced
by native PRCT. They do not qualify H2-specific rates or fractions. Native
normal-H2 EOS states retain the existing
[hydrogen EOS basis](https://doi.org/10.1063/1.3160306). Conservation and shared
stoichiometry establish the audit equations; source-specific material and
field evidence remain separate receiving work.

## Deferred cases, profile and static checks

`validation.cases.pool_fire:cases` defines **eight** cases, profile `pool-fire`.
Discovery metadata imports no native fire/pool model and performs no native
calculation. Each deferred entrypoint accepts the common keyword-only
`work_directory` plus Python parameters and returns `ValidationOutcome` only
when later invoked by a worker.

| Defined future case | Intended gate, not an executed result |
| --- | --- |
| pool-fire-baseline | Finite native burnout, H2/O2 mass, conditioning/LHV/HRR energy, source zero tail and retained objects |
| pool-fire-geometry | Native restricted sphere/solid-flame agreement, mirror and zero/unit transmission limits |
| pool-fire-refinement | Held-stage subdivision invariance of finite consumed mass, radiant energy and exposure |
| pool-fire-heat-budget | Unavailable external conditioning fails with actual attempted native result |
| pool-fire-oxygen | Insufficient finite O2 cannot support complete burning |
| pool-fire-geometry-rejection | Elevated receptor rejected outside actual native geometry |
| pool-fire-prefix | Native inside-sphere rejection retains one completed stage |
| pool-fire-native-pool | Actual preignition native pool handoff without reburning earlier evaporation |

The profile needs the existing pinned native PRCT dependency and its compatible
Pydantic target, existing CoolProp and the already reviewed DynamicLH2PoolX
dependency for the handoff case. SciPy/NumPy and shared reaction/source contracts
are existing host dependencies. No module import, example, case discovery,
entrypoint, native pool/fire calculation, pytest or benchmark was executed.
The adapter/example/case files were parsed with `ast.parse` and checked using
Ruff. These static checks passed; all three Python files use LF. They do not
prove that the future runtime environment, tolerances or physical gates pass.

## Input freeze

Before this increment the five owned paths were absent from the checkpoint;
they are new files, so there is no pre-existing model source SHA to replace.
The final Python/doc bytes below are the static freeze inputs. This report's
own hash is reported to the parent after writing it, avoiding a self-hash.

| Host input | Final SHA-256 |
| --- | --- |
| src/h2physics/adapters/pool_fire.py | `f3b8e77f8d4a8e1fa2d43e52390d85881cbac8f9d1f5b1bea65443415e2da958` |
| examples/pool_fire.py | `f891ff07deca1e89930002fa659df22946e308866f3e35deb277ff3b10d3f8af` |
| validation/cases/pool_fire.py | `03ae92ae95ae6d0517ad7500b5ffeec81eb653b5855ca9f5dc9958e3f2c304e6` |
| docs/POOL_FIRE.md | `e632ffb9b3b49ed4b09322bc81e30df59159d12614407d637826a4f652b19d8b` |

No passing test count, native gate count or runtime is assigned to this model.
It contributes one **implemented_unverified** increment and eight unexecuted
validation definitions. It does not increase the last actually executed
family coverage. Independent H2 burning/geometry/radiation experiments and a
conservative coupled heat-feedback/native pool restart contract remain open.
