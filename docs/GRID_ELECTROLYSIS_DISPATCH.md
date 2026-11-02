# Grid-power dispatch to electrolysis

`h2physics.adapters.grid_electrolysis_dispatch` maps held, caller-supplied AC
power intervals into held electrolysis current commands for the existing
`HydrogenStack` and `ThermalStackStage` interfaces. It fills the grid-fed
operating boundary while reusing the project's electrochemical and thermal
owners; it does not introduce a second polarization or heat solver.

## Python interface

Create a `GridPowerInterval` for every contiguous source-clock window. Supply
available AC power, separately identified fixed auxiliary AC load, clock and
source IDs. Call `dispatch_grid_power_to_electrolysis` with the existing stack,
prescribed coolant temperature, a maximum current density, a current-density
grid spacing, AC/DC conversion efficiency and evidence ID. The immutable
`GridElectrolysisSchedule` exposes per-interval stack results, AC/DC conversion
loss, auxiliary load, grid use, curtailed power, aggregate hydrogen production,
and `thermal_commands` for the existing `FiniteThermalStack.run` API.

```python
schedule = dispatch_grid_power_to_electrolysis(
    stack, intervals,
    coolant_temperature_k=333.15,
    maximum_current_density_a_m2=20_000,
    current_density_resolution_a_m2=100,
    rectifier_efficiency=0.96,
    evidence_id="meter-and-controller-record-17",
)
thermal_trace = thermal_owner.run(initial_temperature_k, schedule.thermal_commands)
```

The dispatcher enumerates the explicit current-density grid and selects its
highest feasible point per interval. It does not assume arbitrary caller loss
callbacks are monotone. Coarse spacing can curtail usable power, so users should
refine the spacing and compare dispatched current and H2 production. Auxiliary
load exceeding available power is rejected rather than hidden as an import.

## Scope and validation

The API is a static held-interval boundary calculation. It does not model AC
power-flow or frequency dynamics, transformer/rectifier transients, current
ramp limits, startup/shutdown, minimum turndown, degradation, water/oxygen/H2
stock, product compression, or plant-wide balance. A supplied power trace is
not itself evidence for stack polarization or production. The dispatch currently
uses unity Faradaic efficiency because the existing finite thermal stage
contract requires it; non-unity species and heat fate need a separate model.

The synthetic case `grid-ac-power-to-electrolysis-stack-dispatch` is registered
for Hangang execution and remains unrun until a pinned batch executes it. A
passing synthetic contract would verify software ledgers only, not validate a
grid-connected electrolyzer. Experimental qualification needs independently
licensed AC measurements, metered auxiliaries, stack I–V and thermal data on a
shared clock, and source-specific uncertainty.
