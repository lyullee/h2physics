# Cantera fuel-cell coolant boundary to HeatDuty

`bind_cantera_fuel_cell_coolant_heat()` projects the accepted cumulative
`stack_coolant_energy_into_j` ledger from a synchronized `CanteraFuelCellTrace`
into the existing `HeatDuty` API. Window endpoints must coincide with accepted
fuel-cell outputs on the exact physical clock. Interval joules are direct
differences of the cumulative native ledger and retain its original sign:
positive energy enters the stack from coolant.

The snapshot identifies the original coolant boundary and stack energy
reference. It reports the declared coolant temperature but does not establish
that heat is recoverable, transferable, or available to another process. No
heat exchanger or utility model is added.

Deferred Hangang case: `cantera-fuel-cell-coolant-heat-duty-handoff` under
`fuel-cell-native`.
