# Supplementary implementation contracts for Request034/035 — engine and turbine

This request defines two separate receiving-owner deliverables. They may share
reviewed property/mechanism utilities, clocks, provenance primitives and generic
ledger helpers, but must retain separate domain APIs, native states, validation
matrices and acceptance decisions. Do not merge a piston engine and gas turbine
into a generic cycle model. Current host boundaries are summarized in
[`ENGINE_CYCLE.md`](../docs/ENGINE_CYCLE.md) and
[`OPEN_BRAYTON_REFERENCE.md`](../docs/OPEN_BRAYTON_REFERENCE.md).

## Request034 — full-cycle hydrogen piston engine

### Owner boundary and result

The receiving engine owner should expose an object API equivalent to
`run_cycle(problem) -> EngineCycleRun` and `verify_result(run) -> same run`.
It must evolve a complete, explicitly declared cycle with intake, compression,
combustion/expansion and exhaust events. This extends the host's closed-charge
slider-crank segment; it must not relabel that segment as a full engine cycle.

The problem must retain the exact native chemistry/thermo owner and mechanism
identity/digest/license evidence; cylinder geometry and clearance; crank speed
and absolute crank/time origin; initial cylinder and port states; valve event/lift
or flow laws; hydrogen injection schedule and phase/state; spark energy/timing
law; wall/heat-transfer boundary model; friction and accessory boundaries if
included; solver settings; and applicability window. Every schedule must bind
quantity, units, source/map identity, support and clock. No implicit valve,
combustion, wall, friction or efficiency law is admissible.

The owner-issued immutable run must retain, at every common accepted sample,
crank angle, absolute time, cylinder volume, pressure, temperature, mass,
species inventory/composition, internal energy, valve states/flows, injection,
combustion progress and wall state for every modeled native owner. Each accepted
interval must report signed `integral(P dV)` and separate indicated work, heat
transfer, fuel chemical/enthalpy input, intake/exhaust enthalpy transport,
injected mass/species, blow-by if modeled, wall/material storage, friction and
auxiliary work. Include explicit H/O/element inventory closure, cylinder mass
closure, a first-law residual on one declared caloric reference and a cycle
closure residual. Keep unmodeled terms named and unresolved; do not balance them
with inferred efficiency. State the sign convention and distinguish indicated
gas work from brake/shaft output.

On native failure, a `Request034...Error` must preserve the original cause,
failed stage/target, last common accepted state, per-owner accepted output prefix,
failed trial separately from accepted data, and the exact native objects. Never
fabricate accepted Runge-Kutta stages or a completed cycle from a partial prefix.
The public verifier must bind the result to the exact owner/configuration,
recheck state arrays, clocks, event ordering, provenance and ledgers without
refitting or silently reintegrating.

### Independent case matrix and gates

Run the following as separate process-isolated cases, with each worker receiving
fresh native instances:

1. Motored closed-cycle limit: zero fuel/spark, reversible or declared adiabatic
   boundaries; verify crank/volume closure and pressure/work behavior against an
   independent idealized reference.
2. Zero-flow/event checks: closed valves, each valve opened independently and
   timing/lift perturbations; verify no mass crosses an inactive port and event
   brackets are retained.
3. Fuel/spark controls: independently vary injection mass and spark timing;
   include no-injection and no-spark limits, delayed ignition, and finite-fuel
   depletion without negative inventory.
4. Conservation suite: independently recompute per-step cylinder and element
   balances, intake/exhaust enthalpy, wall heat/storage and total energy; refine
   crank resolution and solver tolerances.
5. Adversarial suite: mismatched clocks/units, stale mechanism or boundary-map
   digest, unsupported schedule extrapolation, invalid species basis, event
   collision, altered native result, and injected failure after completed output
   samples with exact prefix/cause checks.
6. Parameter campaign: declared Cartesian or pairwise matrix over speed,
   compression ratio, equivalence ratio/fuel schedule, spark timing, valve timing,
   wall boundary and tolerance. Record case ID, source revision, setup hash,
   mechanism/license digest, native package versions, options, result hash and
   acceptance metrics per worker.

Acceptance additionally requires independent synchronized pressure/crank/fuel
flow/air flow/temperature/work observations with measurement operators,
uncertainty and cycle-clock alignment. Separate calibration from held-out
validation. Conservation and synthetic limits do not qualify an engine. Preserve
the host's existing `ClosedChargeEngineError` prefix semantics where applicable;
do not weaken or replace its segment API.

## Request035 — coupled hydrogen gas turbine

### Owner boundary and result

The receiving turbine owner should expose a distinct API equivalent to
`solve_coupled_turbine(problem) -> CoupledGasTurbineRun` and
`verify_result(run) -> same run`. It must solve a declared multi-component
hydrogen-capable gas-turbine operating point with compressor and turbine maps
coupled through a common shaft. It is a higher level than the existing single-
point open Brayton reference, optional one-point turbine-map binding, and
caller-supplied compressor operating point. Do not change those reference
boundaries or claim a coupled solution from a post-hoc shaft residual.

The problem must retain separate exact compressor-map and turbine-map owners,
their source/license/digest, coordinate definitions and units, corrected-flow
and corrected-speed conventions, interpolation/domain rules, surge/choke or
other validity boundaries, and map uncertainty. Retain the native gas-property/
combustion owner and mechanism evidence, ambient and inlet conditions, hydrogen
composition/pressure/temperature/flow and compression boundary, combustor
pressure loss/heat-release or equilibrium/kinetic model choice, cooling and
bleed streams, shaft topology/gearing/speed, bearing/mechanical-loss model,
generator/load model, control variables/limits, solver options and operating
window. Every correction factor or map scaling must be supplied with a source
and an explicit equation; do not infer generic correction conventions.

The immutable owner-issued run must expose each native station and component
state: inlet and outlet total/static pressure and temperature, mass flow and
composition; compressor corrected coordinates, map efficiency/work; combustor
fuel and air streams, outlet state and heat/reaction ledger; turbine corrected
coordinates, expansion ratio, efficiency/work; each cooling/bleed/reinjection
port; shaft speed, torque and power by component; mechanical loss, generator
input/output, load and control state. Include per-stream total mass and species
balances, combustor element balance, component enthalpy/energy changes, gas-path
compressor/turbine powers, shaft torque/power residual, mechanical-loss and
electrical ledgers, and an overall first-law residual on a stated reference and
sign convention. Keep fuel compression, bleed, cooling, auxiliaries and heat
outside the model boundary explicitly unresolved when absent; no double counting
between gas-path net work and shaft/electrical output.

On failure, a `Request035...Error` must preserve original cause, failed component
and residual/iterate, last jointly accepted operating point, exact map/property/
native objects and a per-owner prefix where a continuation or sweep has already
completed points. A nonconverged trial is not an accepted point. `verify_result`
must recheck map source/domain membership, corrected coordinates, common shaft
identity/speed, component linkage, mass/element/energy/power ledgers and exact
native ownership without searching for a different solution.

### Independent case matrix and gates

Execute a separate process-isolated Request035 campaign; no case may share a
mutable map/native phase instance with another worker:

1. Map limit cases: map-node recovery, interpolation interior points, each
   domain boundary and rejection beyond surge/choke or declared map bounds.
2. Shaft limits: zero load, zero mechanical loss, ideal generator, and explicit
   loss/load cases with independently recomputed torque and power balance.
3. Coupling cases: independently perturb compressor and turbine corrected speed,
   corrected flow, inlet state, shaft speed, fuel ratio and cooling/bleed flow;
   require common-shaft convergence and mass-flow consistency or a typed
   nonconvergence result.
4. Thermochemical cases: hydrogen composition/pressure/temperature variation,
   combustor pressure recovery and declared kinetic/equilibrium alternatives;
   independently recompute species, element, enthalpy and energy balances.
5. Adversarial suite: mismatched flow basis, units, clock/process window, shaft
   identity, map digest/license, unsupported interpolation, missing cooling
   return, stale mechanism, negative/invalid states, altered receipt, and failure
   prefix/cause preservation.
6. Parameter campaign: declared Cartesian or pairwise matrix across ambient
   conditions, shaft speed/load, fuel ratio, compressor/turbine map coordinates,
   pressure recovery, cooling/bleed settings and solver tolerances. Each worker
   records case ID, full map/mechanism/source revisions, setup/result hashes,
   native package versions and convergence/conservation metrics.

Acceptance requires map provenance and permission compatible with the intended
distribution, independently sourced hydrogen-capable component or machine data,
and measured operating points with synchronized pressures, temperatures, flows,
shaft speed/torque and electrical output plus uncertainty. Preserve separate
calibration and held-out validation sets. Map interpolation, convergence and
conservation alone do not qualify a turbine. Require the receiving project's
original regressions, both request-specific parallel matrices, clean-install/
installed-artifact replay and source/license audit before promoting either
request beyond implemented-unverified. Keep Request034 and Request035 acceptance
independent; success in one does not satisfy the other.
