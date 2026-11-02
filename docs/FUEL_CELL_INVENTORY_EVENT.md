# Held-current fuel-cell inventory events

`run_fuel_cell_until_reserve(owner, initial, commands, *,
hydrogen_reserve_mol, oxygen_reserve_mol, amount_tolerance_mol=1e-10,
feed_bindings=None)` stops at the first positive-time H2 or O2 inventory limit
inside an existing `FuelCellStep`. It returns `FuelCellInventoryEventRun` with
the original requested schedule, the executed prefix and the actual owner-issued
`FuelCellTrace`. Normal `FiniteFuelCell.run` keeps its existing failure policy.

Each admitted command holds temperature, current density and its optional
operating state fixed. Unity Faradaic efficiency is required by the existing
step type. The existing stack geometry and Faraday relation therefore determine
a linear consumption rate. This wrapper finds the exact algebraic crossing;
it adds no polarization, thermal, flow or thermodynamic solver. The prefix is
executed once by the original owner so its reaction, material, electric/thermal,
source and activity checks remain authoritative.

The native boundary order is preserved: withdraw from existing stock first,
then add the complete finite feed packets at the command start, then react.
Feed amounts are not prorated when the command ends early. An event within a
later step retains earlier executed commands unchanged. All requested commands
and source bindings remain attached; the native execution consumes only bindings
belonging to the executed prefix. Tail operations are retained as requests and
are not executed after the stop.

The receipt reports `reserve_event` or `horizon_complete`, the stop time, event
step index, limiting reactants and H2/O2 reserve residuals. Simultaneous limits,
idle intervals and zero reserves are supported. Very small floating-point
endpoint adjustments needed by the native strict finite-conversion bound are
reported as an explicit time bracket; inventories, current and feed amounts
are not clipped to manufacture a result.

Initial or post-boundary stock at/below either reserve is rejected. This API
supports strictly positive-time crossings and does not create zero-duration
native ledgers for instantaneous boundary operations. Schedule input errors
and failures of the original owner remain errors. `require_current()` checks
the retained owner trace, request, executed prefix, event ledgers and original
source identities. A caller cannot reconstruct or relabel a receipt as an
original issued run.

```python
from dataclasses import replace
from examples.fuel_cell import synthetic_problem
from h2physics.adapters import run_fuel_cell_until_reserve

cell, initial, commands = synthetic_problem()
demand = replace(commands[0], end_s=1000.0)
result = run_fuel_cell_until_reserve(
    cell, initial, (demand,),
    hydrogen_reserve_mol=0.001, oxygen_reserve_mol=0.0001,
)
result.require_current()
print(result.status, result.stop_time_s, result.event_residuals_mol)
```

The example uses authored electrical parameters and native CoolProp calorimetry.
Its root is a held-command inventory crossing. Event location for live
Cantera ReactorNet channels with evolving current, coupled pressure/thermal
states or crossover remains separate work. This API establishes no device
shutdown law or measured fuel-cell qualification.

Executable case: `validation/cases/fuel_cell_inventory_event.py`. Faraday core
reference and assumptions are recorded in `h2physics.electrochemistry` and
the finite fuel-cell documentation.


## Executed local cases — 2026-11-01

The original held-current owner returned H2 and O2 event times of
14.4727998185 s and 8.04044434361 s for the authored test inventories. Complete
start-boundary feed plus pre-withdrawal produced a 22.5132441621 s event.
Zero H2 reserve ended at 0 mol; mass residual was -2.14e-20 kg and energy
residual was 0 J. Eight invalid-request/mutation paths were rejected. Two
original source bindings were retained in the request while only the first
entered the actual native trace before the event.

Ties, idle periods, horizon completion, floating-point coincidence at the exact
horizon and retained unexecuted tails passed. The horizon comparison permits
only an eight-ULP arithmetic coincidence; it does not use a broad user amount
tolerance to trigger an earlier event. The native strict finite-conversion
endpoint bracket and amount residual remain explicit. Ruff and scoped source
checks passed. These are numerical checks with authored inputs.
