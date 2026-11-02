# Native separated fuel-cell pressure/activity and thermal coupling

## Current implemented boundary

`h2physics.adapters.fuel_cell_compartments.SeparatedFuelCellCompartments` advances
three separate frozen native Cantera gas volumes for H2, O2 and water vapor. The
shared HydrogenStack supplies Faraday rates under prescribed current and stack
temperature. Native open-volume owners retain their EOS pressure, composition,
heat/internal-energy and transport ledgers. Species atom definitions and molar
masses are admitted against the native mechanism. Depletion fails at the native
inventory floor rather than silently reducing current.

`HydrogenStack.evaluate` currently takes current density and temperature; its
thermochemistry callback takes temperature only. The existing open-volume owner
integrates one reactor per call. Therefore separate native pressure trajectories
do not currently feed back into stack voltage, activity, heat or prescribed current.
Combined electrochemical energy closure is not claimed by the compartment wrapper.

The local `adapters.fuel_cell_trial.evaluate_fuel_cell_trial_exchange()` now
accepts a caller-projected synchronized H2/O2/H2O trial state, uses the existing
activity and stack APIs, and returns stoichiometric per-volume source rates with
unallocated energy explicit. This closes an exchange-data contract only: the
host cannot prove that trial values came from live native reactors, and it does
not integrate pressure/activity feedback or own depletion events. Its dedicated
`fuel-cell-synchronized-trial-exchange-ledger` contract is deferred.

## Local solver seam audit (2026-10-30)

The current host/native boundary does not expose a shared live state evaluation.
`CanteraOpenGasVolume.run()` constructs and advances one native `ReactorNet` per
call. Its `GasBoundaryRate` callback can be declared `time_only`; it does not
receive a synchronized set of other reactor states or a shared coupled RHS. The
fuel-cell adapter calls that method separately for H2, O2 and water vapor, so the
three traces are independent integrations even when output times match. The
electrical callback is queried from each integrator's time and returns prescribed
current/temperature; it does not inspect any channel's native trial state.
`FuelCellActivitySeries` only consumes completed traces. This layer therefore has
no basis for adding an in-solver pressure/activity callback without introducing a
new native integration owner.

The required receiving boundary is one native simultaneous integration owner that
retains distinct H2, O2 and product-water reactor objects and exposes, atomically
at each trial evaluation, their native species inventories/compositions, absolute
pressures, gas temperatures, phase identities and shared trial time, plus the
finite stack thermal state. A state-aware electrical/reaction callback must consume
that snapshot once and return the existing stack result together with each channel's
species source/sink and signed thermal source under explicit reference identities.
The owner must include those dependencies in the native RHS/Jacobian path; it must
not sample/interpolate completed traces or run staggered independent integrators.
If analytic Jacobians are unavailable, the receiving owner must state how its
native solver obtains consistent numerical Jacobians and handles callbacks at
domain boundaries without converting failed trials to accepted states.

The coupled driver must retain the original multi-reactor network, each trial and
accepted simultaneous state, requested and accepted clocks, and the first native
failure with the successfully completed prefix. It needs root-localized reactant
depletion/domain events and an explicit shutdown/current-limit policy. A pressure
threshold or HELPR initiation result is not itself a reactant depletion event.
The host must not synthesize the shared native owner from the current three
single-reactor runs.

## Local activity-aware finite schedule increment (2026-10-29)

`FuelCellStep.operating_state` now optionally binds the existing typed
`FuelCellOperatingState` directly to one finite schedule interval. The finite
driver applies the shared `fuel_cell_activity_correction` to the original
`ReactionEnergy`, then evaluates the existing `HydrogenStack` with that corrected
Gibbs energy. It requires exact temperature and product-water phase agreement,
retains the original operating-state object on the step result, and preserves the
original reaction enthalpy basis for the finite material/energy ledger. Omitting
the state preserves the existing temperature-only API.

The adapter still takes activities and partial pressures as caller-supplied
externally maintained boundary values. This addition neither derives fugacity
from evolving native compartment states nor feeds pressure/activity back through
a simultaneous solver; the driver, depletion/events and combined channel/stack
energy balance requested below remain open. The `electrochemical_activity`
acceptance contract now includes this finite-schedule path and is deferred to the
Nurion campaign; no scientific execution was performed locally.

## Post-run native-pressure receipt (2026-10-30)

`adapters.fuel_cell_activity_receipt.sample_fuel_cell_activity_receipt` now
provides a host-side handoff from one exact accepted output time shared by the
independent H2/O2/water-vapor native traces. Under its declared pure ideal-gas
channel assumption it forms dimensionless activities as `p / p_reference`,
retains the reference identities and source compartment trace, applies the
existing `fuel_cell_activity_correction`, and evaluates the existing stack at
explicitly supplied stack temperature and current. Construction and each
`require_current()` re-derive the state from the accepted sample, saved reference
pressures, shared correction and original stack; a content seal alone is not
accepted as evidence for caller-constructed results.

This is a sampled post-run operating point, not pressure-derived activity during
native solver stages. It does not replay the command callback, infer stack
temperature from gas temperatures, alter the native traces, or declare pressure
feedback or combined energy closure. Nonideal fugacity during synchronized native
trials, liquid product water, simultaneous native coupling and coupled
thermal/electrical closure remain open.
The returned `FuelCellOperatingState` can be explicitly attached to a later
finite `FuelCellStep` as a held, caller-selected operating state, using the
existing schedule owner; that use is still a sampled boundary approximation.
The corresponding acceptance case is deferred; no local scientific execution
was performed for this increment.

## Local caller-fugacity post-run increment (2026-10-30)

`adapters.FuelCellFugacityActivityProvider` now offers a caller-owned callback for
post-run activity reconstruction from each exact sampled pure-channel pressure and
explicit stack temperature. The callback receives `(species_id,
absolute_pressure_pa, temperature_k)` and returns fugacity in Pa. Sample and reference
fugacities are evaluated at the same temperature; their ratio is the dimensionless
activity. Ideal pressure ratios remain the default. The provider adds no EOS or
fugacity correlation, and its callback's hidden state and reference qualification
remain caller responsibilities. The existing post-run acceptance contract records
nonideal inputs and provider changes, but it is not executed. This seam does not
fulfill the receiving engine's synchronized native activity owner described below.

## Receiving API units, rate signs and failure receipt

To make the simultaneous-driver boundary interoperable with the existing host API,
the receiving implementation should expose a direct Python operation equivalent to
`run_coupled_fuel_cell(initial_state, commands, *, clock_id, output_times_s,
controls, tolerances)`. This names the contract only; the native owner chooses its
integrator and retains the actual Cantera reactors. It must not wrap the present
three independent `CanteraOpenGasVolume.run()` calls and call the result coupled.

All values use SI units and one absolute time basis. The shared trial snapshot and
accepted-state rows need the following minimum coordinates:

| Value | Unit | Required meaning |
| --- | --- | --- |
| `time_s` | s | Shared absolute trial/accepted clock; all reactor and stack state values refer to this instant |
| `stack_temperature_k` | K | Finite stack thermal state used by the same trial evaluation |
| `pressure_pa` | Pa absolute | Actual pressure from each distinct native gas reactor |
| `temperature_k` | K | Actual gas temperature of each reactor; do not substitute it for stack temperature |
| `species_moles_mol` | mol by species | Trial or accepted reactor inventory in the mechanism's declared species order |
| `volume_m3` | m³ | Native control-volume geometry used by that reactor |
| `mole_fractions` | dimensionless | Native trial gas composition, retained separately for H2, O2 and water-vapor compartments |
| `current_density_a_m2` | A/m² | Nonnegative magnitude passed to the existing `HydrogenStack.evaluate()` |
| `current_a` | A | Stack current after applying the existing active-area definition; do not multiply by series-cell count again |
| `activity` | dimensionless | Actual activity relative to a retained `reference_id`; not a dimensional partial pressure |
| `species_molar_rate_into_cv_mol_s` | mol/s per named whole control volume | Positive adds that species to the named control volume; negative removes it; this is not an areal rate |
| `heat_rate_into_cv_w` | W per named whole control volume | Positive heat enters the named gas compartment |
| `heat_rate_into_stack_w` | W for the whole stack | Positive heat enters the finite stack thermal state |
| `electrical_power_into_stack_w` | W for the whole stack | Positive electrical power is consumed by the stack; negative is exported, consistent with `StackResult.electric_input_w` |
| `reaction_energy_j_mol_h2` | J/mol H₂ | Existing `ReactionEnergy` reference and product-water phase; retain its `reference_id` |

For fuel-cell reaction extent, gas-side source rates must follow the declared
reaction stoichiometry with the above into-volume sign (H2 and O2 consumption are
negative; product-water generation is positive for a vapor compartment). If product
water is liquid or crosses a membrane/interface, report that as a separate phase or
boundary transfer with equal-and-opposite component rates at the two affected control
volumes. Do not silently combine liquid and vapor inventories. Every channel and
stack energy term must retain its originating `PropertyBasis`/enthalpy reference and
be counted once; `StackResult.unallocated_energy_rate_w` remains an unresolved
diagnostic until the receiver identifies the physical destinations of that power.

The native result must expose the exact accepted state rows and the native trial
state where the first failed RHS or event occurred. On exception, retain the original
cause, last trial state, successfully accepted prefix, active event/command and
whether termination was a controlled shutdown or solver/domain failure. A trial
callback value must never be inserted into the accepted history. A control policy
that limits current or shuts down must be a named, caller-selected rule with an
evidence identity; absent such a policy, depletion rejects the operation rather than
silently changing the requested current.

## Requested native Python contracts

1. Add an explicit immutable operating state containing stack T, separate anode and
   cathode absolute pressures, species activities/fugacities with reference states,
   product phase and water activity. Preserve the present temperature-only API as
   a declared compatibility level rather than silently changing its meaning.
2. Let thermochemistry and applicable polarization laws consume that operating state.
   Reuse the current reaction-energy and voltage-loss owners; do not copy another
   polarization/Faraday solver. Report every correction and its source/domain.
3. Provide a native simultaneous multi-reactor driver with actual compartment states
   available to the electrical/reaction boundary at each native solver evaluation.
   Retain independent reservoirs for H2 and O2; their coexistence in one artificial
   reactor is not an admissible substitute for membrane-separated device channels.
4. Couple current, native reaction species sinks/sources and one finite stack thermal
   state using a declared reaction/phase/enthalpy reference. Explicitly allocate
   electricity, stream enthalpy, sensible/reaction heat, coolant and product energy.
   Preserve native heat and species ledgers and reject double-counted reaction heat.
5. Supply depletion/domain event handling with accepted simultaneous states, native
   original solver objects, requested/accepted clocks and original failure causes.
   Event policy must explicitly specify shutdown/current limiting; never clamp an
   unavailable reactant into a hidden replacement reaction rate.

## Deferred acceptance evidence

The host can now create a post-run `FuelCellActivitySeries` from the exact shared
accepted pressure grid when the caller supplies temperature, current and
`ReactionEnergy` at every sample. This preserves a sampled operating trajectory
for later held-state schedule use. It remains a post-run projection and does not
fulfil the simultaneous-driver, pressure-feedback, event, or combined energy
requirements below.

Require zero-current isolated-compartment limits, ideal-gas pressure/inventory
reductions, Faraday charge and H/O element closure, pressure/activity correction
limits and signs, water-phase/reference consistency, complete electrical/thermal
energy balance, solver refinement and controlled depletion events. Retain both
the failed trial and accepted prefix for domain violations. Experimental operating
maps, membrane transport/crossover and source-qualified kinetics remain separate
qualification work. No local scientific execution was performed for this request.

## Native simultaneous implementation increment — 2026-10-30

`h2physics.adapters.cantera_fuel_cell.run_cantera_synchronized_fuel_cell()` now
creates three independently owned `ExtensibleIdealGasMoleReactor` objects inside one
Cantera 3.2 `ReactorNet`. The RHS reads each live phase after the network has restored
the same global trial vector to every reactor, then passes synchronized native
pressures/compositions through the existing activity, `ReactionEnergy`, and
`HydrogenStack` APIs. Species rates are added to the corresponding native mole state
and their Cantera partial-enthalpy/internal-energy terms are included in each channel
energy equation.

The finite stack temperature is an extra scalar state on the hydrogen reactor's
extended state vector, with an explicit caller heat capacity, reference temperature,
and coolant conductance. It uses no dummy gas phase. A caller callback must divide
the remaining device thermal power across H2, O2, water-vapor and stack nodes; its
signed sum must close electrical power against the native species-enthalpy transfer.
The callback and current-control policy remain caller-owned. At prescribed current,
the live pressure/composition changes the activity-corrected voltage and power; the
current changes only if the supplied policy uses those live states.

The deferred `cantera-native-synchronized-fuel-cell-thermal-coupling` contract is
recorded in `validation/cases/cantera_fuel_cell_coupled.py`. The pinned Cantera 3.2.0
source order and extension hook are documented in
`docs/CANTERA_FUEL_CELL_COUPLING.md`. No local imports, tests or calculations were
run. Runtime verification remains deferred to the HPC campaign. Reactant floors
retain the failing native trial and accepted output prefix. A separate caller-side
inventory reserve limiter is described below; neither helper localizes a native
depletion root or reports a controlled-shutdown event. Device data, membrane
crossover, liquid product water, thermal spatial gradients and independent
cell-stack qualification remain outside this level.

## Accepted-trial reactant reserve feedback — 2026-10-30

`h2physics.adapters.FuelCellReactantCurrentLimit` is an optional callable for the
existing `current_density(view)` seam. The caller supplies an unmodified requested-
current callback, distinct H2/O2 inventory reserves above the native failure floor,
a response horizon, explicit H2/O2 moles-per-electron values and evidence identities.
The policy admits only the water-vapor reaction stoichiometry already used by the
stack. It computes maximum current density from each live separated reactant
inventory, series-cell count and active area, then applies the more restrictive cap.
The synchronized driver checks that the limiter references its exact stack and
solver floor. Its current decays toward zero at either inventory reserve; at or
below a reserve it requests zero current. It does not replace the reaction, mutate
the native state, localize an event root or invent an event time.

The two deferred `fuel-cell-native` cases cover synthetic stoichiometric caps and
one synchronized native run with reserve protection. They have not run. This is a
caller-selected feedback policy, not a validated current controller or a substitute
for native root-localized depletion/shutdown support. External reactant withdrawal,
uncertain kinetics, response delays and measured protection behavior are not covered.
