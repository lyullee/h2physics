# Linepack withdrawal to fuel-cell feed boundary

`bind_linepack_fuel_cell_feed()` projects one accepted `LinepackSourceHandoff`
bin into the existing `FuelCellStep` and `ThermochemicalFeed` input types. It
does not advance linepack or execute a fuel-cell calculation.

## Contract

- The target fuel-cell step must use the exact linepack interval edges and
  declared clock.
- Positive H2 mass is taken from the accepted linepack outlet ledger. The
  resulting feed amount is checked against the fuel-cell H2 species molar
  mass and stored in the existing fuel-cell energy-reference basis.
- The caller supplies a typed gas feed state, an interval-integrated source
  enthalpy and its reference ID, the exact target fuel-cell energy-basis ID,
  a signed reference offset, and signed conditioning energy. The closure is
  `H_source + reference_offset + conditioning_energy - H_feed = 0`.
- Clock, state mapping, transfer and energy mapping each require caller-owned
  evidence IDs. The immutable receipt replays the source and target projection.

The linepack owner provides a mass ledger but does not accumulate an energy
ledger. Its isothermal fixed-temperature model has pressure-varying endpoints,
so the adapter deliberately does not infer integrated withdrawal enthalpy from
the representative `IntervalMassSource.state`. The caller's enthalpy value
must represent the full interval under a declared property/reference basis.
This module contains no pressure regulator, pipe heat transfer, cooling, or
fuel-cell solver.

## Deferred case

Hangang case `linepack-fuel-cell-hydrogen-feed-handoff` is registered under
`gas-compressible-pipe`. It checks a synthetic constant-bin source enthalpy
contract and packet construction only. The case is deferred and has not been
executed. No measured linepack-to-stack transfer data or conditioning model is
claimed.
