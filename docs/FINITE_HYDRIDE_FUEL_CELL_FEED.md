# Finite-hydride desorption to fuel-cell H2 feed

`bind_finite_hydride_fuel_cell_feed()` maps one accepted interval from a
`FiniteHydrideTrace` to the existing `ThermochemicalFeed` and `FuelCellStep`
input types. The selected fuel-cell step must use the same clock and exact
start/end edges as the hydride interval. The adapter takes outward mass and
enthalpy as the negative changes in the hydride's cumulative external-gas
ledgers, then converts the accepted mass to the existing fuel-cell H2 species
using its molar-mass basis.

The source trace retains all original state samples and port ledgers. The
caller supplies one typed representative state at the fuel-cell feed boundary,
plus clock, state, transfer, and energy-reference evidence. The adapter calls
the existing fuel-cell caloric owner at that declared feed state and requires
a signed caller-owned conditioning-energy ledger to close from the integrated
hydride outlet enthalpy to that feed enthalpy. The returned receipt contains
the feed packet and a copy of the input step with that packet assigned to the
existing hydrogen inlet.

## Limits

This adapter does not simulate storage delivery, pressure regulation, heat
conditioning, fuel-cell operation, or a coupled transient. It does not infer a
representative feed state for a time-varying source. The original hydride trace
and every interval state remain attached to the receipt, while the caller owns
the mapping from the interval to the single `ThermochemicalFeed` state. The
feed packet uses the receiving fuel-cell caloric energy-basis identifier; the
explicit signed conditioning ledger accounts for the difference from the
hydride port's integrated enthalpy basis.

Deferred Hangang case:
`finite-hydride-fuel-cell-hydrogen-feed-handoff` under `finite-hydride`. It
checks interval/clock identity, exact signed mass and enthalpy ledger use,
species/molar-mass compatibility, state and energy evidence, and input-step
port assignment. It does not run the fuel-cell solver or establish system
qualification.
