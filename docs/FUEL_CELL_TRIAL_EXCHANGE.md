# Synchronized fuel-cell trial exchange

`h2physics.adapters.fuel_cell_trial` composes one exact-time set of caller-
projected hydrogen, oxygen and water-vapor states with the existing
`FuelCellOperatingState`, `fuel_cell_activity_correction()`, and
`HydrogenStack.evaluate()` owners. It supplies a solver-neutral source-term
contract for an integration engine that can expose all three compartment
trial states at the same absolute time.

## Inputs and outputs

Construct a `FuelCellTrialGasState` per separated control volume. Each state
contains its role and species identifier, clock and exact trial time, absolute
pressure, gas temperature, volume, reactive-species mole fraction and inventory,
molar mass, dimensioned activity reference pressure, reference identity, and
source evidence. `FuelCellSynchronizedTrial` admits exactly the three roles only
when their sample clocks match. Stack temperature and nonnegative current density
remain independent values; channel gas temperatures are not used as stack
temperature.

Without a fugacity provider, ideal activity is `mole_fraction * absolute_pressure /
reference_pressure`. For non-ideal work, pass the existing
`FuelCellFugacityActivityProvider`; it supplies caller-owned fugacity values and
retains provider/evidence identity. Both routes feed the existing activity
correction. The stack is evaluated in fuel-cell mode with Faradaic efficiency one.
No voltage-loss, kinetics, or thermodynamic law is reimplemented here.

The returned `FuelCellTrialExchange` gives source rates **into** each separate
gas control volume. H2 and O2 rates are negative sinks, and vapor product water
is positive. The oxygen rate is one half the H2 molar rate with the same
negative sign. Molar masses must close this reaction mass ledger. Electrical
power retains `StackResult`'s fuel-cell sign (negative into the stack), and the
stack's `unallocated_energy_rate_w` is preserved as unresolved energy. No gas
compartment heat is fabricated and no reaction energy is counted twice.

## Integration boundary and limitations

Call `evaluate_fuel_cell_trial_exchange()` from a native RHS only after the
native integration owner has assembled all three actual trial states at one
time. This function does not create native reactors, integrate a state, couple
the channel derivatives, handle current limits or depletion events, retain an
accepted prefix, or localize a shutdown. It cannot prove that caller-supplied
state values originate from a genuine native solver. A receiving owner must
retain its original reactors and trial/failure diagnostics and must reject a
failed trial rather than copying it into accepted history.

The present open-volume adapter exposes one independent `ReactorNet` per run;
it does not provide the simultaneous trial interface needed to install this
callback in that solver. Therefore this exchange contract does not turn
`SeparatedFuelCellCompartments` into a pressure-feedback model. Liquid product
water, Faradaic inefficiency, membrane crossover, simultaneous stack thermal
storage, channel heat allocation, shutdown/current limiting, and combined
channel-stack energy closure remain outside this API.

`fuel-cell-synchronized-trial-exchange-ledger` is a synthetic deferred contract
for exact clock admission, activity references, stoichiometric mass rates,
result issuance, and unresolved-energy reporting. It is not a native solver
test, fuel-cell experiment comparison, or qualification. Do not claim Request031
complete until a receiving engine provides the simultaneous accepted-step owner
and its conservation/event evidence.

## Currentness fingerprint implementation note

The exchange seal must retain its original immutable mapping objects. Hashing new
`dict(...)` copies on every `require_current()` call changes mapping identity in the
shared identity-aware content receipt and falsely reports that an unchanged exchange
is stale. The current implementation fingerprints the retained mappings directly;
the deferred synthetic case's immediate currentness assertion covers this API path.
