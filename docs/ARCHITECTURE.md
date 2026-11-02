# Architecture and Python contracts

## Current source status — 2026-11-01

The project is in active implementation with later scientific verification
assigned to Hangang. The current catalog records 82 model families: 20
implemented, 37 native-adapter-verified and 25 implemented-unverified. These are
first-level source labels; the 57/82 implementation-classified share does not
mean the families are complete or scientifically qualified. The latest
AST-generated public API index contains 1,807 top-level definitions across 362
Python modules. These counts describe repository structure, not verified runtime
behavior.

The user's latest instruction authorizes local scientific verification when
Hangang is slow or unavailable. Local checks and native replays now proceed
independently of remote campaign completion; each result records its actual
execution scope and preserves numerical versus measured-data validation status. Historical Nurion evidence remains in its pinned records and is not a
current execution target. Read [PROGRESS.md](PROGRESS.md) for exact admitted,
completed and pending HPC cases, and [HANDOFF.md](HANDOFF.md) plus
[IMPLEMENTATION_BACKLOG.md](IMPLEMENTATION_BACKLOG.md) for active tasks and open
model boundaries. The public-tree hygiene audit passed for 1,477 files on
2026-11-01; this checks content patterns only and is not a substitute for a
license or publication review. A same-day build audit found byte-identical
package source in the current wheel and sdist; see RELEASE_SOURCE_READINESS.md.

The hydrogen Brayton family now includes caller-supplied component maps,
bounded operating-point solves, bleed/cooling boundaries and a one-rotor
transient energy level around the Cantera reference. The rotor receives
caller-supplied turbine/compressor power; it does not calculate those powers
from maps or solve a governor, generator or multiple spools. Request035 remains
open for native integration and qualification beyond those host-side levels.

The physical state and its meaning are the common interface. Parameters are immutable
dataclasses; replaceable implementations satisfy typing.Protocol interfaces. Arrays carry
explicit column names and SI units. Analysis functions accept objects directly and return
inspectable results, diagnostics and evidence. Persistence is optional application code.

## Layers

The root package resolves public model exports on first access. Its original
81 exported names and underlying class/function identities are preserved;
`from h2physics import ...` remains supported. Metadata-only imports such as
`h2physics.cluster_validation` and `h2physics.catalog` no longer load NumPy,
SciPy or optional physical engines as a side effect. Type-checking imports and
the explicit export registry describe the same API. Cold-package import and
export-identity regressions cover this separation; actual model dependencies
still load when the model is requested.

Fluid thermophysical properties use the existing CoolProp providers rather than
an in-house property library. Production defaults must use native CoolProp or a
table qualified against that provider, with explicit fluid/spin identity, energy
reference, phase and domain limits. A native failure must propagate; an ideal-gas
or constant-property fallback must never hide it. Explicit analytical reference
closures may support numerical verification, but are not production defaults.
Conservation laws, heat-transfer correlations, solid material models and native
reacting-engine mechanisms retain their own physical roles; they do not constitute
a replacement fluid EOS. Reaction formation-reference offsets remain explicit
because native sensible-property references alone do not define reaction energy.

1. Core: physical identity, units, state/stream/time-series objects, parameters and diagnostics.
2. Properties: CoolProp reference states, optional mixtures/reactions, audited table providers.
3. Data: source records, rights, deterministic acquisition, raw checksums, explicit loaders.
4. Models: new scientifically distinct gaps and optional native existing-engine adapters.
5. Coupling: facility topology, source partitions, clocks, energy references and conservation.
6. Research: calibration, held-out comparisons, numerical refinement and uncertainty.

For fixed-composition real-gas mixtures, `CoolPropMixtureProperties` composes the
shared `GasComposition` with CoolProp HEOS. Composition and property basis are
fingerprinted; the provider re-applies its captured mole fractions before each
state flash. It uses documented PT/PQ/TQ mixture input pairs and supplies optional
PH/PS/P-density calls by a bounded scalar inversion over PT states, with explicit
temperature bounds and single-gas monotonicity gates. Its immutable `MixtureInverseGrid`
can be shared across provider instances only when composition fingerprint, property basis
and inverse domain match; every candidate root bracket is checked with fresh endpoint
states at the requested pressure. It never invents missing binary interactions. Cantera
remains the native owner for reacting ideal-gas mixtures and kinetics; the CoolProp adapter
is not a reaction or transport model.

`MixtureInverseGrid.write_npz(path)` and `MixtureInverseGrid.read_npz(path)` provide
pickle-free persistence for immutable bracket samples. Restoration reconstructs the typed
property basis and rechecks axes, monotonicity and content fingerprint. The archive is an
execution aid for bounded inverse solving, not a portable or qualified EOS table.

## Boundary rules

- Use Pa absolute, K, kg, m and s. Gauge and engineering units enter through an explicit adapter.
- Distinguish normal hydrogen, para-hydrogen and a specified spin mixture. A name conversion
  does not authorize an enthalpy-reference conversion.
- A stream is a transfer across a named boundary, not a complete accident source.
- Source histories need an opening, geometry, upstream inventory, event clock, phase
  partition, termination and property basis. Normal operating flow is insufficient.
- A liquid-to-ground history is a declared or calculated impact boundary; it is not implied
  by the presence of liquid at a pipe outlet.
- A pressure/throat result must come from the selected hydraulic closure. No arbitrary
  fixed pressure ratio is promoted to a solved critical state.
- Solver truth, measured observations and reconstructed or synthetic records remain distinct.
- Invalid data have masks and reasons. Missing values are not converted to zeros.
- Native adapters do not replace a missing engine with a different physical model.

## Reuse ownership

LH2DT owns cryogenic equipment dynamics. The station simulator owns high-pressure
refuelling dynamics. PSA-Dyna owns multibed separation. Pool and dispersion libraries
own their respective source/transport equations. PRISM owns scenario orchestration.
Monitoring, reliability and explanation packages consume explicit physical results;
their scores do not create missing release physics or calibrated annual frequencies.

Existing functions are composed through optional native adapters. If a receiving engine
cannot preserve a required contract, create a concrete extension request and retain the
unavailable status until an exact compatible revision passes the integration checks.

The common equilibrium nozzle is owned by `h2physics.release`: gas/liquid/two-phase
discharge are one physical kernel. PRISM remains the scenario orchestrator and request 006
specifies delegation of its equivalent HEM path. LH2DT remains the inventory integrator.
The current source history ends at the solved nozzle plane; unresolved atmospheric/ground
partition is explicit and prevents treating it as a complete consequence-model boundary.

The equipment layer declares signed port transfers and separate heat/shaft power. Native
LH2DT owns friction, maps, heat exchange, phase inventory, graph solution and integration.
The host checks every native stage through a structural graph view and retains actual native
results. A single-flash HEOS facade accelerates the verified native property subset without
another EOS. Phase-resolved liquid withdrawal uses the existing stratified native level;
it does not reinterpret a homogeneous bulk outlet as a liquid port. Native generic heat
ledger/accepted-step gaps are bridged explicitly and documented in request 007.

The stored-device driver partitions prescribed commands while the native integrator still
owns every step. Dynamic states have independently read mass, fluid energy and wall storage.
Each device closes its signed integrated boundary ledger across restarts, and every stage
declares its external heat. Accepted solutions match observed native objects by identity;
left/right command limits remain separate. Ambient/control callbacks receive the absolute
operation clock. DYNAMIC_INVENTORY.md defines the API and the unfinished trigger/depletion scope.

The supply builder now combines the phase-resolved reservoir and both stored downstream
devices in one native dynamic assembly. Models, states and factories remain caller-owned
objects. Each explicit operating mode has its own component and boundary-power contract;
an error cannot switch models. Ideal isolation is distinct from rotor/casing dynamics.
Accepted-sample source/power quadrature retains both command limits and its property/clock
basis. Native integrated inventories and independently recomputed external sampled ledgers
remain separate verification paths; neither implies experimental plant qualification.

An independent transition check exposed that native fixed-friction iteration can report
zero momentum without closing its final reported Darcy loss. `h2physics.hydraulics` now
owns one shared magnitude root with injected friction and an explicit residual gate.
The native bridge retains geometry, phase-viscosity responsibility and actual result
factories. The supply case declares the direct fluids continuous correlation; choosing it
is separate from numerical root convergence. Request 009 asks the native engines to
delegate this common solver and expose public correlation/viscosity capabilities.

Frequency-domain electrochemical observations use `ImpedanceSpectrum` and the same
ObservationTable/group/SVD machinery. A source-specific streaming PEM profile owns
unit/mask/protocol interpretation, retaining a separate cell clock and DC-context rows.
The optional actual impedance.py circuit factory owns the electrical prediction; the
host only maps real/imaginary components to the shared observation contract. Native
objects remain available for deep Python composition. Whole-cell R0×area can be passed
explicitly to the existing static ohmic callable, with no automatic mechanism assignment
or double-counting. The 144 initial spectra and conditional repeat/transfer comparisons
do not turn the static core into a transient thermal/crossover/degradation model.

The native pool boundary receives already-ground-reaching saturated liquid, an actual
native step object and an explicit finite absolute clock. DynamicLH2PoolX owns all pool
equations, radial numerics and contact-age memory. Host accounting compares original
step-input integrals with native storage/evaporation/escape/adjustment, separately from
the native reported residual. Normal/para identity is enforced. A reproduced input-event
roundoff failure is bridged only under an explicit recorded clock budget; request 010
specifies the native correction and property/checkpoint/source capabilities.

`IntervalMassSource` is a common finite-window mass/state contract. It preserves interval
integrals and distinguishes a constant-mean temporal representation from instantaneous
samples. Pool vapor remains after input isolation and can outlive the reported radius.
The current boundary does not assign an interval footprint or unresolved vertical momentum,
so it is not automatically a complete atmospheric source. No nozzle-to-ground fraction
or independent pool qualification is invented to connect missing pieces of the facility.

The gas-release atmospheric boundary reuses the same `NozzleResult` and an actual native
DEGALI expander. One explicit effective stream/pressure-area closure preserves momentum
and h+KE; virtual-plane position is declared rather than inferred. Native source factories
receive separate static relative enthalpy and absolute pure-H2 reference, mapped into a
declared vertical global section. Normal/para identity survives the complete transfer.

DEGALI retains profiles, entrainment, component phase enthalpies and spatial integration.
An explicit actual-native subclass corrects only the independent thermal profile's
vertical body-force source using its own radial integral. The protected Jacobian hook is
version/fingerprint checked by the reproduction script and targeted by request 011.
Host audits retain failed raw native predictions. A short normal-H2 jet passes numerical
gates; cold para-H2 energy fails after refinement and is rejected. Whole-mixture spatial
observations do not become gas-probe mole fractions or a finite-source material clock.

Measured spatial jet scans now share the non-time observation contract. A source-specific
profile owns units/cell identity, repeated sensor grids, masks and label/identity conflicts.
The same nozzle can be inverted at fixed T0/area to condition an equivalent inlet on a
measured flow; this does not turn a pipe sensor into a nozzle stagnation measurement.
The native source/jet chain and fixed coefficients remain reused.

A constant H2 component energy-reference transformation changes native flux E to
E+C*H2_mass_flux and shifts the source target consistently. It conditions the existing
native initializer without another root/physical solver. Host audits first recover the
original energy and retain their budgets. Native raw shifted energy and physical energy
remain explicitly distinct. Gas point observations project onto the computed curved
centreline, enforce a dry single-gas envelope, and declare Gaussian tails or masks.
Unbounded geometry is an explicit mode with no fictitious ground clearance. Field-accuracy
and numerical-conservation failures remain independent acceptance results.

The common reaction layer owns supplied stoichiometric extents and finite material
accounting, not equilibrium or kinetic integration. Species phase, element, charge and
molar-mass bases are explicit. Temperature-dependent duty requires species formation/
reference consistency; a pure-fluid sensible zero alone is insufficient. Functional
providers retain caller functions and the optional native Cantera caloric adapter retains
its actual phase. Native equilibrium/reactor engines remain the same owners.

Computed carrier observations preserve original rows and archive/member identities.
Dataset-level canonical pair comparison precedes admitting a reference heat: conflicting
values are withheld together rather than averaged or selected by file order. A row-local
molecular check cannot establish that cross-row qualification. The current data's single
gas-reference heat does not authorize liquid kinetics, another temperature or a material
source clock. CARRIER_REACTIONS.md defines the contract and remaining phase/kinetic work.

User preference chooses HyRAM+ for high-pressure gaseous-H2 dispersion and SLABx-LH2
for LH2-origin dispersion; DEGALI remains an explicit comparison provider. Selection is
based on declared release origin, including LH2 vapor, rather than current phase alone.
Each selected source pipeline owns choking/expansion once. HyRAM receives upstream
conditions, not an already choked shared-nozzle state. Failed material or applicability
gates retain raw native objects and do not select another engine automatically. The
current steady SLAB bridge cannot discard source variability or invent a footprint.

Native frozen ideal-gas properties now serve the same nozzle contract from explicitly
fingerprinted species thermochemistry and mass fractions. Mechanism-H2 spin identity
and formation enthalpy remain distinct from CoolProp normal/para sensible references.
The frozen mixture adapter retains the declared `GasComposition` identity and reports
its native molar mass; `ThermoState.heat_capacity_ratio` exposes that state's cp/cv
only when both derivatives are available. Neither value broadens EOS or flow-model
applicability.
An opt-in, evidence-identified off-simplex sum correction is recorded for native Jacobian
trial states; it is distinct from accepted-state floating-point roundoff and from chemical
composition normalization. Negative species are never repaired by that policy.

The finite open gas-volume reference delegates physical state derivatives and integration
to native Cantera. Public extensible hooks append boundary integrals only. Fixed native
feed states, continuous oriented rates, wall heat, finite trial-time support and actual
native object identity are explicit. This resolves material/thermal pressure response;
it does not substitute for preferred HyRAM spatial/stratified dispersion. Measured MAT/
XLSX source clocks and reported pressure/concentration bases stay unresolved until mapped
with evidence, rather than being silently attached to the thermodynamic model.

Native insulation heat enters existing signed power and conserved inventory
contracts. Distributed area and localized bridges have separate geometric
allocations; the actual layered-tank solver owns state integration. The current
low-level property facade lacks layered pressure-projection derivatives, so this
separate case explicitly selects original native properties and checks its energy
reference. No hidden provider fallback or constant-UA replacement is used.

Compression composes native fixed-ratio stages with prescribed cooling PT, while
retaining original states and transfers. Stage flow is an external operating-point
input, not a network capacity law. An ideal isolated zero-flow boundary creates no
transported outlet; no native rotor/startup model is inferred. Predicted cooling
hardware remains a receiving extension under request013.

Finite hydride storage adds new gas/solid conservation equations rather than new
uptake correlations or gas thermodynamics. The established kinetics and native gas
provider remain separate owners. Bound-H chemical energy is expressed on the gas
reference; reaction enthalpy and closed-system internal-energy change are distinct.
The AB2 observation profile retains source clocks and derived quantities separately,
so unqualified pressure/MFC/shell fields cannot silently calibrate this model.

Pressure protection now separates physical trial evaluation from accepted device
state. An actual native binary latch is promoted only after a successful native
transaction at an accepted physical event. A public native Valve subclass delegates
the existing shared valve/nozzle to satisfy the receiver's nominal type check.
Native tank equations and RK intervals remain the physical integrator; the host
owns bracketed event partition and independent boundary audits. This does not claim
complete detection of arbitrary hidden within-step pressure excursions.

Steady vent ports retain native PH transport state and explicitly selected hydraulic
closure. Signed reverse heat maps to common heat-into-transported-fluid power while
raw native orientation remains available. Independent final momentum and inverse-UA
checks can reject a trajectory whose enthalpy bookkeeping alone closes. Low-pressure/
density/Mach applicability and omitted kinetic/potential energy remain explicit; no
source/nozzle plane is invented by a transport connection.

Steady/finite recovery reuses native saturation cooling and fluid/wall storage.
External cold-reservoir heat, internal fluid-wall transfer and hydraulic isolation
have separate meanings. Net condensation, liquid hold-up and collected product are
separate boundaries; missing withdrawal/cycle power is not silently supplied.

Instrument indications sit above the physical process model. Exact native held-input
response acts on an explicitly declared quantity/unit/reference/location and clock.
Predictions retain raw/filtered/indicated fields, flags and deterministic bounds.
Direct spring relief senses physical upstream pressure; using a lagged sensor/PLC
signal requires a separately explicit controlled policy. Measured/calculated/injected
signals and calibration evidence keep their original roles through that coupling.

## Coupled thermal and reactive inventories

Spin conversion exposes a declared enthalpy reference and phase/rate evidence.
The current finite calorimeter is held-pressure total H with caller-qualified
frozen sensible Cp. Its chemical term is internal; no duplicated external
conversion power or evolving-spin pure-fluid-name substitution is introduced.

The finite heat exchanger holds two native fluids and two walls in one native
composite state/step. Every side keeps its own material/energy basis. Equal and
opposite native interwall heat changes side U+wall energy while global exchange
cancels. The closed scheduling boundary is not an aggregate physical pressure.
Future process ports need independent side transport and external heat ledgers.

Frozen and finite-rate gas use the same native volume. Boundary species and native
reaction production are separate numerical integrals; elements are conserved
without a reaction element source. Formation energy belongs to native U/h once.
Reactive phases own their native definitions. Exact source/owned hashes and a
one-time bounded coefficient-roundtrip audit distinguish faithful reconstruction
from later mutation. Phase-exposing callbacks keep exact per-RHS guards; explicit
time-only callbacks can use private definitions with accepted-output guards.

Observation profiles preserve recorder clock kind/calendar origin, physical
experiment group, source byte/member/row identities and unresolved pressure/flow
references. Selected copies cannot become independent experiments by changing a
filename. Process coupling follows declared compatible quantities and references.

## Safety prediction and diagnostic boundaries

An executed native consequence model can still be rejected. Native Flame keeps
separate source/transport/caloric/radiation gates; a passed radiation kernel does
not authorize its rejected source field. Diagnostic irradiance retains that state
and cannot silently become absorbed wall heat or a qualified exposure history.

Conditional peak blast takes explicitly evidenced participating energy and event
geometry. It does not infer a cloud/ignition/DDT or inherit a rejected gas field.
Contents heat takes fixed-mass/volume pressure observations and audits native U
against direct EOS. Its signed ΔU/Δt remains separate from incident heat, wall
storage, work and losses. Area/heat allocation requires exact source/clock/window
and explicit axial intervals; zero overlap cannot be replaced by an area floor.

Thermal observations retain reported coordinates rather than asserting seconds.
Candidate clock vectors, independent source indices, derived flux and sensor
temperatures keep their distinct roles before any physical integration or fitting.

## Shared radial transport and temperature-dependent constitutive terms

Material geometry supplies volumes, face areas and integrated resistances to
one mobile/trap finite-volume core. The legacy planar API delegates with unit
area; spherical storage adds a finite boundary inventory and native gas state
feedback. Total face moles, flux per area and mobile H versus H2 remain distinct.
Prescribed temperature supports transport studies without implying a heat-duty,
thermal stress or mechanical containment prediction.

Native cryo-compressed composition reuses tank/wall derivatives, the existing
pressure-event driver and shared nozzle. Phase and solid-exclusion domains are
declared; crossing the critical temperature at higher pressure does not imply
a critical-point or coexistence transition. Opening, stopping and depletion
remain different events with different state/command consequences.

Rotor U/Cv constitutive functions can improve thermal coupling without adding
another ODE. An absolute rotor contribution belongs on a nonrotating baseline;
a frozen-spin EOS requires a composition-relative correction. Enthalpy needs
an explicit PV mapping. Native empirical conversion admission does not establish
a complete evolving-spin EOS or long-term detailed balance. Observation algebra
similarly cannot turn reconstructed biological yields into independent kinetics.

## Optical and multiphase process boundaries

Spectral photon accounting and prescribed-yield finite chemistry share the
existing stoichiometric/caloric core. Incident versus absorbed response and
electron versus H2 counting are explicit. Optical arrays bind to their exact
wavelength grid/representation; changing array meaning cannot pass by keeping
its length. A steady exposure does not invent source termination on depletion.
Required thermal duty does not establish free-energy feasibility or actual yield.

Gas/solid equilibrium uses the native Mixture optimizer and extensive SI phase
amounts. Native gas and solid thermochemistry retain independent owned
definitions, common reference evidence and actual candidate identities. A
phase-equilibrium state, finite-rate gas reactor and supplied stoichiometric
extent solve different constraints; their energy/species roles are not merged.

Cyclic separation remains native schedule/valve/bed/integrator work. The
current file runner is reached through an explicit internal temporary bridge
while the public interface is Python objects. A reconstructed audit Network
cannot be advertised as the original integrator instance. Native reporting
species must match H2-specific performance claims. Source observations retain
derived roles and within-study/duplicate dependence before any fitting.

## Porous transport and staged reaction ownership

Cantera's native `DustyGas` owns coupled porous-gas transport. The host checks
geometry, normalized full composition, phase/reference identities and native
transport-copy fidelity; it does not implement another diffusion-matrix solver.
Each flux owns a fresh pore object because native pore setters are write-only.
The result uses bulk geometric area and the stationary-solid total species-flux
frame; its effective coefficients already include porosity/tortuosity.

The new gas/pure-solid caloric bridge reuses the existing audited phase-copy
paths and native gas enthalpy provider. Phase/species mapping, density evidence,
fit envelope, common formation reference and H2 spin identity survive transfer.
Access to native objects is retained, with binding/definition guards on reuse.

The staged thermochemical core composes existing finite reactions and additive
species calorimetry. It owns finite transfer order, clocks and H ledgers, while
native objects own properties. Carrier return, thermal return and full amount
return are independently audited. Prescribed component removal requires explicit
boundary evidence. It does not silently add a separator, work input or recovery
heat exchanger. Cached caloric arrays are copied before further property calls;
nonfinite extensive arithmetic cannot satisfy an acceptance comparison.

## Native biological inventory ownership

QSDsan ADM1/AnaerobicCSTR and BioSTEAM System own biological rates, biomass,
acid/base, liquid/headspace transfer, pressure/one-way extraction and BDF.
The host supplies explicit initial state, finite clock support, SI/native-day
conversion and independently sampled component/COD/C/N ledgers. Full energy,
wet-water and H/O atom closure are not claimed. Actual objects and original
OdeResult survive later audit failures; native threshold zeroing and closed-
output finalization limits remain explicit. Optional native environments are
isolated to avoid changing the declared host compatibility profile.

## Finite native device composition

The finite membrane device reuses the constitutive preparation/copy audit and
private native DustyGas. Signed native kmol/s enter the public native reactor
bulk-source hook; native mass/species/dilution and one ReactorNet own dynamics.
Gross area is applied once. Identical prescribed T requires explicit separate
thermostat duty; side U=transportedH+Q and combined species/U are independent
checks. Native raw trial extensions, requested sample states and hidden internal
accepted steps are distinct. A retained first trial failure cannot be erased
by a shorter native retry. Depletion rejection is not an event-root claim.

One port-capable finite hydride rate core now serves closed bed simulation and
thermal compression. Source and receiver use actual native homogeneous-vessel
fluid/wall derivatives; the shared nozzle owns pressure-driven flow. A common
integration couples those three finite inventories and clocked thermal/valve
stages, retaining per-body/global signed material/H/U/bath ledgers. Initial bound
hydrogen and campaign end loading are visible; delivered compression does not
by itself establish CSS or sustainable throughput.

Independent-input uncertainty wraps existing model callables rather than
reimplementing physics. Native SciPy owns sample generation and Sobol indices;
source-qualified marginal/independence/reset assumptions belong to the caller.
Actual raw responses, copied parameter/output batches and definition/coordinate
identities survive model and audit failures. Constant-output non-identifiability
and native arithmetic/shape failures cannot become accepted zero sensitivities.
Joint/correlated/posterior/time/structural uncertainty needs separate evidence.

## Native shock, receptor and risk ownership

Caltech SDToolbox owns CJ search/frozen-shock algorithms and Cantera owns
thermochemistry. The host retains actual exported/owned phase definitions,
visible native endpoint objects, raw fit/call outputs and independent jump/
sonic checks. A file-only native boundary does not become an original in-memory
fit-phase API; unavailable intermediate states/global controls remain explicit.
CJ endpoints do not create initiation/DDT/ZND or a facility overpressure field.

HyRAM owns dose/probit/CDF laws. Host history reduction requires explicit
incident/absorbed meaning, interpolation, additivity/no-recovery or positive-
phase assumptions. Native pressure model signatures determine whether impulse
is needed. Computed-result replay verification binds input/model/mean/evidence/
native source and actual calls to the response. Conditional source-field inputs
do not bypass the existing rejected source-to-Flame/dispersion boundaries.

The native conditional-risk engine owns branch multiplication/aggregation and
receipts. Host source/receptor/frame/clock/evidence bindings preserve actual
physical objects and reject changed computed harm or incomplete physical state.
Explicit frequency, partition and credit/dependence evidence remains external.
No model score/alarm count becomes an annual rate; no conditional case is
promoted to complete facility QRA. Native internal normalization is explicit
while the public surface stays Python objects without a mandatory wire format.

## Separate domains and physical observations

The finite O2 room delegates all thermodynamic dynamics to CanteraOpenGasVolume;
it only partitions admitted interval commands and audits original native traces.
Thermal physiology delegates to native JOS3 and preserves its actual implicit
boundary, rounded outputs, prepared-state history and unobserved warmup limits.
These two physical domains cannot be joined by copying temperature alone: H2-rich
convection, condensable air, humidity/phase, breathing/contact and reference
pressure need their own qualified boundary. The standalone native air diagnostic
is retained as a rejected candidate, not silently repaired or used by either.

Observed/predicted residuals reuse original TimeSeries/Variable/masks, actual
native instrumentation and native learned causal mode models. Whole episodes
separate fitting, normal calibration and held-out evaluation. Native function,
trained-state and original signal identity are admission evidence. A retained
prediction owner is not a claim that every arbitrary caller prediction has been
independently replayed; the declared observation operator remains essential.

## Coding-first unverified levels

New development status implemented_unverified separates written optional
compositions from actually executed levels. Existing scientific owners remain
unchanged: pvlib I-V, shared electrochemistry/stoichiometry/native gas state;
HELPR growth/fugacity with caller geometry and native SciPy integration; shared
phase-enthalpy/reaction kernels with finite solid supplies. Domain/status flags
must survive downstream use. No observer/risk consumer may inherit validation
from an imported native package or a prepared deferred case.

ValidationCase/ValidationOutcome are Python contracts. Case discovery is
metadata-only; computation occurs only in explicitly requested entrypoints.
The deferred source worker pins revision/plan/case/profile, records attempts and
atomic outcomes, and leaves missing jobs incomplete. It has no universal native
object serializer or implicit case acceptance. Case-specific scientific evidence
is still necessary. The PBS/template infrastructure is unexecuted itself.


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
Request025 records specific native APIs, evidence and coupling work. CORA DOI
10.34810/data2866 is acquired and schema-audited for limited electrode observations;
it does not identify complete-cell hydrogen output or biological activity. Raw
files remain outside public distributions pending file-exception review. See the
receipt `research/microbial_electrolysis_data_candidate.toml`.

The remaining planned families are obstacle-resolved dispersion and accepted
jet fire. Every partial family also retains the limits in MODEL_CATALOG.md;
70coded families are not70complete models. Last full installed-artifact audit
remains785dae7; later source/artifact acceptance is still deferred.


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

Current unexecuted API checkpoint: see CANTERA_FACTORY.md, HYDROGEN_ECONOMICS.md, MICROBIAL_CELL.md and MICROBIAL_OBSERVATIONS.md; execution status is recorded in PROGRESS.md.

Original-result provenance is a cross-cutting support layer, described in
[RESULT_PROVENANCE.md](RESULT_PROVENANCE.md). It fingerprints retained evidence
without owning domain equations. Each physical producer owns admission and
lifecycle policy, while economics/facility composition adds separate boundary
audits after requiring the original result.

Model selection is also caller-owned. The registry in MODEL_SELECTION.md binds
an exact catalog family, distinct physics level and provider factory. Selection
requires explicit status/capability/evidence gates and performs no ranking,
fallback, optional import or installation. This keeps application composition
separate from the physical solvers and their qualification evidence.

Finite adsorption capacity, valve stroke, relief lift and facility continuity
are composition layers over existing owners. They keep provider identity,
property/energy basis, port and clock explicit. None is a replacement EOS,
nozzle, adsorption isotherm, hydraulic network or event integrator.

Pump and compressor maps are admission envelopes around original equipment
results. Flowing heat-exchanger ports and reliquefier product collection are
post-result conservation compositions. Map/source evidence, clock, state,
ports and producer result identity remain explicit across each boundary.

## Model-level extensions — 2026-11-02

The new indoor conditional peaks have an ignition-delay axis, while
`PressureTimeHistory` represents one actual applied mechanical load. Their types
are intentionally separate. Finite mechanical expansion work, supplied pressure
ownership and linear generalized structural response retain separate boundaries.
Thermal cycles expose actual TESPy networks and current ExerPy physical-exergy
owners. Redox reuses the shared native multiphase/caloric and finite-reaction
owners. PAR combines a capacity domain with native gas thermochemistry, chimney
flow and catalyst thermal storage. Electrode data metrics retain independent
current, product, area and site bases. See [the extension record](ENHANCEMENTS_20261102.md)
and its individual manuals for APIs, tests, limitations and continuation.
