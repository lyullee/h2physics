# Solid-reaction development checkpoint

Status on 2026-10-28: **implemented_unverified**. The user explicitly requested
parallel coding first and scientific testing only after the Nurion connection.
No local pytest, native calculation, example, scientific case, benchmark or
full suite was executed for these files. Static syntax/AST and Ruff inspection
are the only local checks. Case definitions, planned numerical assertions and
installed source inspection are not executed verification evidence.

## Existing owners and new responsibility

The existing `reactions.py` owns species/stoichiometric admission, elemental and
charge balance, molar-mass compatibility, finite extent bounds/conversion and
reaction calorimetry. `thermochemical.py` owns fixed-pressure finite stages,
donor feed/takeoff enthalpy, additive phase thermal conditioning and conversion
heat with element/mass/enthalpy audits. `CanteraMultiphaseMolarEnthalpy` owns
native phase copying, gas-provider reuse, solid pressure dependence, native
kmol-to-host-mol units, reference and native definition/domain guards.
The liquid carrier and reversible hydride responsibilities were not broadened.

The new `storage/solid_reaction.py` composes these actual objects. It adds
finite source debits, explicit packet scheduling, beginning-of-interval kinetic
evaluation, forward limiting-reactant policy, thermal root assembly and a
combined reactor/supply/export audit. It contains no alternative reaction-heat
or EOS law. Existing shared files and native installations were not modified;
there are no new dependencies.

The thermal root calls the actual `FiniteThermochemicalCycle.run` at each
candidate temperature and retains its `ThermochemicalTrace`/`ReactionConversion`
objects and original provider. Two existing host-private helpers, `_h` and
`_check_balance`, are reused for whole-system audit consistency. A later
receiving public helper facade would avoid coupling to those private names;
no duplicate ledger was introduced to work around them.

## Scientific basis and limits

[DOE chemical hydrogen storage](https://www.energy.gov/cmei/fuels/chemical-hydrogen-storage-materials)
distinguishes hydrolytic and thermal release and describes material-dependent
spent-product handling/pathways. That source does not qualify this module's
rate or material parameters. No generic Monod, Arrhenius, surface-area,
pressure-inhibition, passivation, slurry or NaBH4 relation was inferred.
The new API requires a balanced reaction, explicit phase/source identities,
actual caloric provider, kinetic callable/parameters and declared operating
assumptions. The synthetic fixtures' formulas, offsets and heat capacities are
original bookkeeping choices, not fitted or literature material data.

The fixed-pressure total-enthalpy boundary follows the
[primary Cantera constant-pressure energy statement](https://cantera.org/3.2/reference/reactors/constant-pressure-reactor.html).
The actual class remains the existing host finite-stage kernel, not a claim
that Cantera integrates a solid reactor. One common temperature, additive phase
h and externally maintained P exclude rigid-volume pressure evolution, finite
wall/utility capacity, phase heat-transfer lag and excess/dissolution enthalpy.
Feeds are finite packets at their actual donor temperature; exports retain the
previous or endpoint donor h according to operation order. Every supplied
reservoir's remaining amount and enthalpy enters the final global audit.

The callback returns mol extent/s for the exact reaction normalization, once
after adiabatic beginning-of-step mixing. Its finite-time approximation is
explicit frozen-start/operator splitting. Default overlarge steps reject;
opt-in truncation reports limiting reactants without claiming an exact depletion
time. A successful root would only find a declared bracketed endpoint. Positive
effective heat capacity, root uniqueness, phase stability and kinetic domain
need independent caller evidence and later numerical verification.

The current native caloric bridge is gas/pure-solid, so it does not qualify
aqueous hydrolysis. Liquid water, hydrate/speciation, catalyst and dissolved or
slurry product identities/rates/caloric references remain receiving inputs.
Thermodynamic data are not kinetic data. Neither measured hydride PCI datasets
nor pressure/temperature-only tank observations provide these missing chemical
hydride decomposition/hydrolysis properties.

The optional native case plans to use installed Cantera3.2 `nasa_condensed.yaml`
LiH(s)/Li(cr) and `h2o2.yaml` H2 through the existing actual caloric bridge.
Read-only source inspection confirms LiH(s) fit 300–961.8 K and Li(cr) fit
200–453.69 K; the authored case admits only 300–430 K and explicit absolute
pressure bounds. No phase-transition extrapolation is planned. Solid density
values and the constant rate are explicitly synthetic verification inputs,
not source-qualified lithium-hydride kinetics/EOS or a device design.

Relevant native documentation is the
[Cantera3.2 thermodynamic API](https://cantera.org/3.2/python/thermo.html).
The official [Cantera3.2 license](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/License.txt)
is BSD-3-Clause; the already reviewed dependency remains optional and is not
copied into host source. NASA's primary
[TM4513 record](https://ntrs.nasa.gov/citations/19940013151) describes formation
enthalpy offsets and marks the report US-government public-use material.
No coefficient table, publication prose, native implementation or source figure
is copied into this checkpoint. NASA thermochemistry does not establish the
synthetic solid densities, phase selection or an experimental validation claim.

## Deferred HPC cases and acceptance

`validation.cases.solid_reaction:cases` is a metadata-only case catalog using
the parent's `ValidationCase`/`ValidationOutcome` contracts. Imports and catalog
construction do not create native phases or call the reactor. Numerical work
occurs only in the explicit `validate_*` entrypoints later selected by the
authorized Nurion dispatcher. No local discovery/import of this new module was
used as a substitute for running the cases.

The core profile is `solid-reaction` (existing Python/NumPy/SciPy); the optional
native profile is `solid-reaction-native` (add the reviewed Cantera3.2 chemistry
environment). Neither name configures the remote interpreter, queue, account,
thread budget or licensed site resource. The parent controls those actual
cluster inputs and exact revision/plan hashes; no job was submitted here.

| Identifier | Planned independent acceptance |
|---|---|
| `solid-baseline` | 8/16/32-step frozen-rate recurrence matches its discrete analytic expression; exact exponential error decreases with first-order trend |
| `solid-heat` | An authored invariant-capacity enthalpy balance independently predicts the heated endpoint; no duplicate reaction heat |
| `solid-water-feed` | Finite warm water changes mixing/thermal endpoint, water limits extent, finite remaining source and exported/retained/generated H2 remain distinct |
| `solid-reference` | An element-linear formation-reference shift leaves the physical endpoint unchanged |
| `solid-startup-gas` | Exporting initial H2 at zero reaction rate is zero generated H2 |
| `solid-finite-failure` | A second draw from an exhausted source rejects and retains exactly the completed first step and committed source state |
| `solid-negative` | NaN/infinite/negative rates, out-of-bracket heat, overlarge rejected extent and foreign caloric basis fail with actual diagnostic context |
| `solid-binding` | Immutable parameter maps and re-bound callback identity cannot silently alter the admitted model |
| `solid-native-caloric` | Actual native LiH/Li/H2 objects feed the existing common-reference bridge and finite kernel; element/mass/enthalpy residuals meet declared fixture budgets |

The shared case audit plans finite residual checks, maximum element residual
below 1e-9 mol, mass residual below 1e-10 kg and enthalpy residual below 1e-5 J.
Those are declared fixture acceptance criteria, not observed errors or universal
physical uncertainty. Native domain failures or a failed criterion must remain
failures; the deferred dispatcher must not swap properties or relax budgets
automatically. An HPC report must record actual environment/native file hashes,
case source/parameter identity, acceptance/metrics, runtime and original failure.

The original example exposes `problem()` and `run_example()` with no native
objects constructed at import. Its command-line entry deliberately refuses
execution; the authorized HPC code may call the function explicitly. The
example has not been executed and its nominal arithmetic is not a result.

## Failure and boundary retention

Admission rechecks actual species elements/charge/mass, reaction order/phase,
common caloric basis, consumed solid and gas-phase H2 product. Hydrolysis must
identify exactly its consumed water phase. It rejects negative inventory,
undeclared species/supply, reference or donor pressure mismatch, noncontiguous
clocks, invalid rate and unauthorized provider/callback rebinding.

Runtime exceptions retain original `__cause__`, actual rate state/raw return,
requested/accepted extent, last accepted inventory, completed step prefix,
committed/trial supplies and available thermal kernel traces. Accepted feed
debits/exports and cumulative bookkeeping commit only after the complete step.
A whole-system audit failure retains its assembled trace when available.
The model never labels partial trials a successful final history.

The public trace keeps stoichiometrically generated H2 separate from exports,
which may include initially stored H2. It claims no recovery/purity, selective
membrane performance, receiver thermodynamics, equilibrium, refill/regeneration
or chemical hydride storage qualification. Experimental material properties,
kinetic source evidence and coupled thermal observations remain unresolved.

Exact final owned/shared input fingerprints and static-check commands are
reported to the parent at freeze; this file intentionally contains no claimed
HPC result. Overall family coverage, request numbering and release manifests
remain parent-owned integration work.
