# Microbial-cell implementation record

2026-10-28 status: **implemented_unverified**. User instruction is coding first,
with scientific execution deferred until Nurion connection. No native import,
install, scientific model/case/example, pytest, replay or benchmark was executed.
Only source/API/license reading and AST/Ruff/LF checks support this checkpoint.
Planned cases and synthetic formulas below are not results or fitted parameters.

## Scientific/native decision

The existing biological adapter was inspected. Its actual QSDsan ADM1 model
owns anaerobic liquid/headspace reactions and often reports kgCOD/native
measured basis. It lacks an anode electron current or qualified exoelectrogenic
growth law. Reinterpreting that output as physical substrate/biomass moles or
MEC current would violate its basis, so no such automatic bridge is introduced.
The new kinetic callback can retain an actual caller biological model object,
but all material/rate/basis mapping is explicit and caller qualified.

The existing HydrogenStack kernel's ReactionEnergy is explicitly for positive
water-splitting Gibbs/enthalpy energies. MEC substrate oxidation is not assigned
that type or a gas-water equivalent. Shared StackGeometry and noncathode
polarization-loss callables remain reusable, while actual Cantera surface
kinetics owns cathode current/potential/rates. No duplicate standalone electrical
or reaction solver is introduced.

Primary scientific context:

- [Logan et al., DOI10.1021/es801553z](https://doi.org/10.1021/es801553z)
  discusses microbial-electrolysis architectures and distinct biological and
  electrochemical inputs. No reported performance or coefficient is copied.
- [Lee and Rittmann, DOI10.1021/es9025358](https://doi.org/10.1021/es9025358)
  examines electron sinks and hydrogen reoxidation, supporting the distinction
  between generated H2, current and harvest. These processes are unresolved
  here rather than folded into an invented efficiency.
- [Cantera3.2 surface/current API](https://cantera.org/3.2/python/kinetics.html)
  defines actual interface_current as positive charge entering a phase and
  native surface production rates. The
  [native reaction definition API](https://cantera.org/3.2/yaml/reactions.html)
  and [phase definitions](https://cantera.org/3.2/yaml/phases.html) support
  explicit charge-transfer, electron-cloud and condensed-electrolyte phases.

Actual installed native type declarations and official example schemas were
read without import or calculation. The code uses the existing reviewed
Cantera3.2 optional dependency and
[BSD-3-Clause license](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/License.txt).
No new package/install/requirements change, native implementation, worked
example, source prose or empirical data table is included. The new YAML is an
original constant-cp/rate fixture with explicit synthetic identity, not a copy
of the native battery/SOFC examples or a qualified cathode mechanism.

## Executable composition prepared

`CanteraMicrobialCathode` requires an exact caller YAML SHA256 plus native
mechanism/domain/license and electrode/activity/caloric evidence. It parses
independent original/owned actual Interface graphs, using the existing
phase-definition fingerprint helper. One pure H2 gas, explicit condensed
electrolyte, electron conductor and one H2-producing reaction are admitted.
There is no automatic phase/water model substitution. Current/rate/state arrays
and actual native graph remain retained across successful and failed root trials.

`FiniteMicrobialCell` combines those actual native calls with existing shared
StoichiometricReaction and FiniteThermochemicalCycle objects. Two balanced
processes represent substrate-to-H2 catabolism and separate finite biomass
synthesis. Reaction extent limits reject unavailable substrate, water and
nutrients. Native gas H2 flux determines accepted catabolic extent after the
current root; all material conversions are done by the common finite kernel.
There is no late native flux clipping or inferred feed.

Explicit complete species reducing equivalents, conserved by both reactions,
connect substrate/biomass/product accounting to actual native transferred
electrons. Native kmol rates become mol and native/shared Faraday constants
must agree. Current, H2/electron flux and interphase charge are checked. The
single admitted cathode path deliberately has no unassigned Faradaic-loss
factor. Side reactions, methane, reoxidation and crossover need their own
qualified stoichiometry/native mechanisms before they can change recovery.

Kinetic callbacks require their own source, scalar parameters and explicit T,
substrate concentration and biomass concentration domains. Biomass is mol of
declared dry formula units, not COD or inferred wet mass. The illustrative
CH2O bookkeeping substrate and C5H7O2N formula do not identify a measured
organism/culture. Catabolic/growth coefficients and all rate/cp/offset values
are original synthetic arithmetic for later verification, not defaults or fits.

The model is an isothermal fixed-pressure batch with fixed native activities
and prescribed anode potential in one explicit reference. Electrolyte pH,
ionic/membrane transport, gas transfer, dynamic surface coverage, finite
electrode charge storage, oxygen ingress and full anode thermodynamics remain
unresolved. The current equality is quasisteady, not a double-layer model.
Positive rates require biomass; connected points require positive finite H2
stock for their pure-H2 gas activity boundary. Absent-product-phase startup
requires a different native boundary.

Net phase enthalpy includes explicit aqueous/liquid and biomass formation
references through the existing caloric provider. Actual native H2 mass and
enthalpy references are checked against that provider. Required signed heat
equals the isothermal kernel duty after actual electrical work; no available
utility, temperature trajectory, ATP model, entropy/free-energy feasibility
or energy efficiency is asserted. Raw native Interface state is scratch state;
copied point arrays and kernel traces preserve each accepted/trial evaluation.

## Deferred acceptance and environment

Six metadata-only ValidationCase definitions use profile `microbial-cell`.
Imports/cases() do not instantiate native phases or run a scientific method;
actual work occurs only in later authorized `validate_*` entrypoints. The
future profile needs Cantera3.2 plus the existing NumPy/SciPy core, with actual
interpreter/site resources/revision pins supplied by the parent. No cluster
credentials, connection or submission is requested by these files.

| Case | Planned acceptance |
|---|---|
| microbial-native-charge | Actual Interface/root identity, current/H2/electron/Faraday closure, generated versus initial H2 |
| microbial-biomass-energy | Finite biomass formula-unit stock, independent substrate allocation, complete reducing-equivalent and phase endpoint enthalpy accounting |
| microbial-disconnected | Explicit zero-rate disconnected cell preserves inventory, has zero work/H2 and claims no native open-circuit solve |
| microbial-finite-failure | Actual successful prefix survives unbracketed native potential; insufficient finite substrate rejects with cause |
| microbial-boundary-guards | Foreign references/clocks, incomplete normalization, unqualified T and zero inoculum cannot bypass admission |
| microbial-original-result-binding | Original geometry/owner/tolerance identity; cached/native/current-state and replacement rejection; weak registration lifetime without replay |

The original native fixture is in examples/microbial_cell.py. Its cathode
kinetic prefactor, electrolyte standard states/composition, molar volumes,
anode potential, extra ohmic coefficient, reaction enthalpies and biological
rates are synthetic. Native YAML parsing, source/owned graph handling,
potential-root signs and runtime compatibility remain unexecuted; a static
review cannot establish that those cases pass. No empirical MEC data were
acquired or claimed and no biological/thermal validation is reported.
The original YAML literal's static SHA256 is
`682d255f245522b90b430376db99259df0e30aa7ec53fffe7dfa02f1cd21e8e3`.
It was obtained from the AST string literal without importing the example or
parsing/instantiating a native mechanism; it is not an executed native audit.

Failures preserve the actual native objects, original cause, failed time/stage,
callback context/raw result, root trials, completed prefix and any returned
common kernel trace. No alternate mechanism/kinetics, invented efficiency or
gas/liquid property repair is used. The parent owns global catalog/doc/request
and deferred campaign integration. Existing shared/native/prior frozen files
were not modified; all owned files remain implemented_unverified.

## Original-result and geometry continuation

The result now retains actual StackGeometry and producer owner plus a
producer-issued admission holding geometry, original current/root and
thermochemical tolerances, evidence, kinetics, caloric provider and finite kernel.
Public `FiniteMicrobialCell.verify_result(trace)` and `trace.require_current()`
return the same original trace identity after recorded-content/current-state
checks. `FiniteMicrobialCell.require_current()` checks owner definitions only.
No native rate/current, kinetic, enthalpy, conversion or root solve is replayed.

The producer's registry is weak and admission points weakly to its original trace;
no unbounded strong list of past traces is stored on the owner. Registration is
issued only after actual successful run aggregation, never by result dataclass
construction/replacement. Replaced summaries/geometry/owner/native result data and
in-place mutable native/root/kernel caches are rejected. Current source/owned
native state, potential, site density and held coverages are sealed separately.
An actual changed scratch state makes the old current binding stale without
resetting or reexecuting it. No cryptographic or hidden-state/history attestation
is implied, and opaque callback/biological internals remain outside this scope.

Original root, phase/current arrays, conversions, material/charge/heat ledgers and
errors are preserved. The owner guard additionally binds the actual finite kernel,
kernel material matrices/tolerances and declared callable/default metadata.
Post-aggregation seal failure retains a constructed trace when one exists.
The economics consumer can use the public same-object hook and actual geometry;
no economics code or shared source was edited in this lane.

The existing five deferred scientific cases are preserved and one original-result
binding case is added: total six, profile microbial-cell. The new handler prepares
ordinary replacement/cache/root/geometry/caloric/kernel mutation guards, native
potential staleness and weak registration cleanup after one original physical run.
All six remain unrun. Only static AST/Ruff/LF/source review supports this change;
no case discovery, module/native execution, test/install/benchmark or job was run.
