# Native synchronized fuel-cell coupling

## Python entry point

`h2physics.adapters.cantera_fuel_cell.run_cantera_synchronized_fuel_cell()` advances
three independent, rigid ideal-gas Cantera mole reactors for hydrogen, oxygen, and
water vapor in one `ReactorNet`. The stack temperature is an additional scalar state
on the hydrogen reactor's extended state vector. It is not represented by an
artificial gas reactor.

Inputs are direct Python objects:

- `CanteraFuelCellChannel` binds a unique Cantera `Solution`, reactive species,
  fixed volume, absolute activity reference pressure, shared enthalpy-reference
  identity, and evidence identity for each separated channel.
- The existing `HydrogenStack`, `ReactionEnergy`, and optional
  `FuelCellFugacityActivityProvider` supply voltage, Faraday extent, activity
  correction, and caller-owned fugacity.
- `StackThermalParameters` declares a finite lumped heat capacity, energy-reference
  temperature, initial temperature, coolant temperature/conductance, and evidence.
- `current_density(view)` is the user's current schedule/control policy. It receives
  the live trial pressures, temperature, and reactive-species inventory. A constant
  current is an explicit policy too. No current limit is implicit, and shutdown
  policy remains caller-owned; the optional reserve feedback helper is described below.
- `thermal_partition(view, exchange, native_species_enthalpy_rate_w)` must return
  `FuelCellThermalPartition`. Its signed rates into H2, O2, vapor water, and stack
  must sum to electrical power into the stack minus the native Cantera species
  enthalpy-transfer rate. The adapter does not guess how that energy is split.

Pressure and composition are read at each native RHS evaluation and converted to
dimensionless activities by the existing fuel-cell exchange API. At a prescribed
current this changes reversible voltage, cell voltage, and electric power; current
changes only if the supplied controller chooses to depend on the live trial view.
An explicit caller fugacity provider can replace ideal pressure-ratio activities.
The water-product contract is vapor only.

Cantera's mole-reactor state uses kmol and its partial-molar enthalpy/internal-energy
arrays use J/kmol. The adapter converts the HydrogenStack's mol/s source rates to
kmol/s and adds the corresponding native species and open-boundary energy terms to
each reactor RHS. Each accepted output snapshot retains the three native inventories,
thermodynamic state, per-channel component/energy integrals, stack thermal state,
current exchange, and caller partition. Successful runs report separate component,
channel energy, stack energy, and whole-device energy residuals.

## Why the states are synchronized

This implementation targets Cantera 3.2.0. Its `ReactorNet::eval()` stores the
current trial time, restores the complete global trial vector to all reactors, and
then evaluates reactor RHS functions in order. The source's `updateState(y)` loops
over the full reactor collection before the RHS loop begins. Cantera's
`ExtensibleReactor.after_eval` is the public hook that augments the native reactor
equations. See the official [Cantera 3.2 zero-dimensional reactor documentation](https://cantera.org/3.2/python/zerodim.html),
the tagged [`ReactorNet.cpp` RHS ordering](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/ReactorNet.cpp#L509-L529),
the tagged [`ReactorNet.cpp` state restoration](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/ReactorNet.cpp#L584-L590),
and the tagged [`MoleReactor.cpp` state and energy equations](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/MoleReactor.cpp#L150-L265).

These source paths show the implementation order in the pinned upstream version;
they do not replace runtime verification against the exact installed Cantera 3.2
build. Reactor RHS evaluations may occur more than once at a trial state, including
for solver/Jacobian work. The adapter memoizes the stack callback for an identical
time/state vector and rejects callback-definition changes during a run.
The freshness error distinguishes the current-density callback from the
thermal-partition callback so a rejected native run identifies which binding
changed. Synthetic constant-current policies are module-level functions to
avoid capturing mutable runner-local state.

## Accepted and failed states

The trace retains the caller-requested accepted output grid after native `advance`
calls. A callback/domain/native error is preserved as
`CanteraFuelCellIntegrationError.cause`, with the accepted output prefix and the
last synchronized trial snapshot when Cantera exposed one. No trial is appended to
the accepted history.

Reactant floors fail closed. The driver does not activate a replacement reaction
or claim root-localized depletion/shutdown. `FuelCellReactantCurrentLimit` is an
optional caller-selected `current_density(view)` policy. It caps current from the
live H2 and O2 inventories above declared reserves, using the admitted water-forming
stoichiometry, stack series count, active area and a caller response horizon. It
requires the exact driver floor and stack identity. Its feedback tapers current to
zero at either reserve and protects the reserve under the closed-channel reaction
model; it is not a native event locator, does not return an event time, and is not a
validated controller. Without that policy, the first trial at/below the declared
floor remains a failure boundary with the native trial and accepted output prefix.
Zero current is admitted by the shared trial-exchange API and creates no species
source, but it does not imply a restart or automatic control policy.

## Scope and deferred verification

This code is a zero-dimensional compartment/stack coupling level. It has no membrane
crossover, liquid-water pathway, spatial temperature distribution, aging, startup,
or measured polarization/current-control law. The user owns the H2/O2/H2O mechanisms,
species energy references, reference pressures/fugacities, current callback, thermal
partition, thermal boundary, and evidence identities. Equal energy-reference IDs
are an explicit caller declaration, not proof that independently authored mechanism
thermochemistry agrees with `ReactionEnergy`.

The synthetic case `cantera-native-synchronized-fuel-cell-thermal-coupling` is
deferred to the Cantera 3.2 `fuel-cell-native` cluster profile. It has not been run.
Its accepted output grid and energy ledgers are solver/API checks only; experimental
device validation, refinement, depletion-event localization, and physical
qualification remain open.
