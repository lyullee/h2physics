# Finite microbial-electrolysis composition

**Status: implemented_unverified.** Code, an original native fixture and six
deferred HPC cases are prepared. No scientific calculation, native import,
installation, example, case discovery, pytest or benchmark was executed locally.

`FiniteMicrobialCell` connects finite substrate/biomass/product inventories to
actual Cantera cathode kinetics. It is a conditional isothermal fixed-pressure
batch level, with caller-qualified microbial kinetics, growth stoichiometry,
aqueous activities and anode potential. It supplies no default organism,
Monod law, empirical performance, Coulombic efficiency or biomass yield.

## Physical ownership and distinct interfaces

The existing `StoichiometricReaction` owns finite conversion and element,
charge and molar-mass admission. `FiniteThermochemicalCycle` owns actual
phase-specific formation-enthalpy/conditioning accounting and finite material
audits. Their original conversion/trace objects remain in each returned step.
The cell reuses common `ThermochemicalInventory`, `StackGeometry` and explicit
noncathode loss callables such as the existing `OhmicLoss`.

The existing `HydrogenStack.ReactionEnergy` describes positive water-splitting
reaction energies. It is deliberately not used to label substrate oxidation as
water electrolysis. Existing native ADM1 output uses measured component bases,
often kgCOD rather than physical species mass, and does not provide an anode
electron-recovery model. ADM1 cannot silently become MEC kinetics or a molar
substrate/biomass inventory. A caller may retain its own actual biological model
on `MicrobialKinetics.native_model`, but must supply an explicit valid rate/basis
mapping; that optional pointer does not certify MEC suitability.

The primary MEC literature distinguishes current, biomass, H2 generation,
harvest, methane and reoxidation sinks. In particular,
[the primary H2 oxidation study](https://doi.org/10.1021/es9025358) shows why
generated H2 cannot automatically mean recovered product. The current code
resolves one H2 cathode pathway only; it does not import that study's parameters
or claim its measured performance.

## Actual native cathode

`CanteraMicrobialCathode` parses the exact caller-supplied YAML twice with actual
Cantera3.2: one original graph and an independent owned graph. A matching
`MechanismBasis` SHA256, domain, rights/references and `CathodeEvidence` are
mandatory. Definitions, reaction multipliers, graph identities and site density
are fingerprinted using the existing native phase helper. No new gas/aqueous
EOS, Butler-Volmer equation or surface rate law is implemented in this module.

The admitted native graph has an explicit condensed electrolyte, pure H2 gas,
electron-cloud phase and ideal surface with exactly `2H+ + 2e <=> H2`.
Cantera owns electrochemical potential dependence and native rates. The
[official current API](https://cantera.org/3.2/python/kinetics.html#cantera.InterfaceKinetics.interface_current)
defines positive charge entering a selected phase, in A/m2 for a surface.
`get_net_production_rates` supplies native kmol/m2/s; the host converts to mol
and uses native/shared Faraday-constant compatibility for charge accounting.

Every query resets declared T, absolute P, all complete normalized bulk phase
compositions, electrolyte/conductor potentials and held surface coverages.
Native composition normalization is checked, not silently accepted. Actual
potential, phase current vectors, raw native production-rate arrays, phase-state
copies, surface object and root trials remain inspectable. Native objects are
mutable scratch state; result arrays preserve the evaluated points separately.
No phase-fit/domain failure is replaced with another mechanism.

This scope has fixed activities/pH and held coverages. It does not solve buffer
inventory, proton/membrane transport, acid/base equilibrium, dynamic coverage,
gas transfer, headspace pressure, double-layer capacitance or anode kinetics.
Native electron cloud is a constitutive phase, not a predicted finite charged
electrode inventory: quasisteady transferred charge must match the finite
biochemical/H2 electron ledger. A positive initial H2 stock is required for the
declared pure-H2 activity boundary; startup from an absent product phase is
outside this level.

## Finite microbiology and operation

Supply two actual shared balanced reactions over the exact same phase/species
order as the caloric provider:

- Catabolism consumes the named aqueous/liquid substrate, produces named
  gas-phase H2 and does not itself synthesize the named biomass.
- Growth consumes substrate and creates biomass formula units with explicit
  nutrient/water/product coefficients; its H2 coefficient is zero.

Biomass is finite mol of a declared dry formula unit, not kgCOD or an inferred
wet mass. The caller supplies a complete species electron-equivalent basis;
H2 has two equivalents/mol and both reactions must conserve that basis. The
code does not infer a growth yield or convert reported COD to physical moles.
Other reduced products must appear explicitly in the balanced reactions and
electron basis. There are no hidden electron-efficiency factors or losses.

`MicrobialKinetics.callback(state, parameters)` returns an actual
`MicrobialRates(catabolic_extent_mol_s, growth_extent_mol_s)`. Units are mol
extent/s for each exact reaction normalization. Finite molar inventory, liquid
kinetic volume, substrate/biomass identities, seconds and clock are supplied.
Temperature/substrate-concentration/biomass-concentration bounds, parameter
source and origin are mandatory. Positive rates require positive finite biomass.
No library default rate or concentration convention is chosen.

Each explicit contiguous stage supplies anode and electrolyte potentials in
one declared reference, a finite cathode-potential bracket, complete native
phase compositions, clock/evidence and circuit connection. The algorithm:

1. Evaluates the supplied biological rates at the stage's initial finite state.
2. Checks shared finite growth, then catabolic extents; unavailable substrate,
   water or nutrient fails without clipping or inventing feed.
3. For a connected positive catabolic rate, solves the actual native cathode
   potential for the required current; accepts actual native H2/electron flux,
   interphase charge closure and current residual within declared budgets.
4. Uses actual native H2 flux to set the shared catabolic extent and checks
   finite inventories again. No late positive native overshoot is clipped.
5. Applies both conversions through the existing finite thermochemical kernel.

Current and biology are held over each interval. This is explicit frozen-start
time discretization, not an adaptive kinetic ODE or an electroactive-biofilm
solver. Refinement and source-domain evidence are required before use.
Disconnected stages require zero catabolic rate and do not claim a native
open-circuit equilibrium solution. Connected zero-rate conditions must be
explicitly disconnected; no hidden controller is inferred.

The applied external voltage uses the prescribed anode potential minus the
native cathode potential plus separately evidenced noncathode loss callables.
Those losses must exclude cathode polarization already owned by Cantera.
The one-cell geometry is explicit; a multi-cell current/biomass distribution
is not assumed. Reverse/power-generating operation and negative losses fail.

## Thermal meaning, results and failures

The full net-reaction caloric provider must include compatible formation
enthalpies for actual aqueous substrate, liquid water, nutrients, biomass and
gas H2. Gas water cannot replace the declared liquid/aqueous medium. Native
cathode H2 and full-provider H2 molar masses and enthalpy references must agree.
The example's constant-cp aqueous values are authored numerical fixtures,
not a water/slurry/organism thermodynamic database.

At imposed common T/P, the existing kernel calculates net enthalpy change.
External electrical work is accounted from actual current and applied voltage;
the remaining signed heat is the **required** isothermal duty. It does not
predict temperature, available utilities, metabolic ATP/free-energy feasibility,
efficiency, shaft work or rigid-volume U/pressure. Algebraic duty closure alone
is not independent total-energy validation.

`MicrobialCellTrace` retains actual native cathode, kinetic source/model pointer,
caloric provider, finite kernel, actual one-cell `StackGeometry`, producer owner,
complete steps, generated H2, transported
electrons, electric work and required heat. Each step retains raw callback
context, native root/trials, native arrays and actual growth/catabolic conversions.
Initial H2 is separate from generated H2. There is no vent, sale/harvest,
receiver state or H2 recovery prediction.

### Original-result and geometry admission

The actual successful producer issues a trace admission only after its material,
charge, current and thermal checks. Geometry is preserved as `trace.geometry`,
with original series-cell count, active area and H2 molar mass; it is not inferred
later from production, capacity or a financial assumption. `trace.owner` retains
the actual `FiniteMicrobialCell`. `trace.admission` retains that owner, geometry,
actual thermochemical tolerances, current absolute/relative tolerance, maximum
root iterations, evidence, native cathode, kinetics, caloric provider and kernel.

```python
trace = model.run(initial, stages)
assert model.verify_result(trace) is trace
assert trace.require_current() is trace
actual_area_m2 = trace.geometry.active_area_m2
actual_tolerances = trace.admission.tolerances
```

These are producer identity/content checks, **not a second physical verification
solve**. The hook reads admitted owner definitions, exposed current native
phase/state/potential/coverage snapshots, cached native rates/currents, returned
root data, actual finite conversion/kernel traces and all material/charge/thermal
ledger fields. It also checks declared caloric/public native bindings, callback
identity/default arguments, kinetic parameters/domains, geometry and tolerances.
It does not call cathode current/rate evaluation, microbial kinetics, caloric
enthalpy queries, a root finder or the finite conversion driver.

Only the originally issued trace identity is admissible. `dataclasses.replace`,
including a numerically identical copy, does not receive a new producer seal.
An altered summary, geometry, status, owner, native cache or root is rejected.
The trace's `require_current` dispatches the actual producer implementation, so
a replaced structural object's `verify_result` method cannot confer provenance.
`MicrobialResultVerificationError` retains the rejected result, owner, available
admission and original chained cause when a check raises.

The owner has weak issued-admission registration and holds no strong list of all
past traces. Admission points weakly to the original trace; retaining the owner
does not keep abandoned traces alive. Admission is created by successful `run`,
never automatically by dataclass construction/replacement. Post-aggregation
admission failures also retain any constructed trace on `MicrobialCellError.trace`.

Native graphs remain mutable scratch objects. A later native query or caller
mutation that changes their retained state makes this strict current binding
stale; use separately owned graphs for concurrently current independent sources.
The verifier neither resets a phase nor recomputes a response to make an old
trace pass. Exact restoration of original data is observable as the same current
content; this is not a historical tamper log or a cryptographic attestation.
Arbitrary hidden closure/global state, opaque provider internals and external
biological-model state cannot be qualified from pointer identity alone. No fresh
predictive reproducibility or physical validity is inferred for those objects.

Consumers should check `trace.require_current()` before and after using physical
quantities. That preserves original generated-H2/required-duty semantics; it does
not create a harvest, sale, utility or measured-validation claim. The public
owner-level `model.require_current()` checks producer definitions and returns the
same owner; result-level current-state/cache admission requires the trace hook.

`MicrobialCellError` retains original `__cause__`, failed stage, last accepted
inventory, completed prefix, rate state/raw result, actual native graph/point/
trials and any returned kernel trace. Failed stages do not update inventory.
Admission/source mismatch before stepping remains an ordinary error. The
original example and six deferred cases are in
[examples/microbial_cell.py](../examples/microbial_cell.py) and
[validation/cases/microbial_cell.py](../validation/cases/microbial_cell.py).
The HPC profile is `microbial-cell`; actual Cantera3.2 and existing core
NumPy/SciPy are needed. No package is installed and no case has run locally.
The additional `microbial-original-result-binding` case prepares original identity,
geometry/tolerance retention, replacement/root/rate-array/declared-caloric/kernel
mutation rejection, native potential staleness and weak-registration lifetime
checks. It uses one actual run and does not replay a model inside verification.

## Acquired electrode-observation dataset

The public CORA dataset DOI [10.34810/data2866](https://doi.org/10.34810/data2866)
is available locally under ignored `data/raw/mec_data2866_1.0/`. Its publisher
record declares CC0 1.0 and the standard public dataset download returned the
version-1.0 archive. The candidate receipt records the archive and per-file
SHA-256 hashes, publisher OAI metadata digest, file inventory and ODS schema
audit. Raw data are kept outside Git and distributions; the publisher OAI DDI
exposes dataset-level rights but no per-file rights overrides.

The usable numerical content is limited to electrode LSV, paired Nyquist values
and six long-term current-density series. LSV gives current and potential but
does not provide geometric area; impedance data lack a frequency coordinate and
contain unresolved second-column labels. The current-density sheet has one
terminal time-only row, retained as incomplete. These measurements can support
electrode-level comparative analyses after an explicit mapping audit. They do
not include hydrogen output, Faradaic efficiency, substrate conversion or
microbial activity, so they cannot identify the finite microbial-cell model's
kinetics or validate its whole-cell balances.
