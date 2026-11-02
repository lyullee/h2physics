# Staged Brayton turbine cooling boundary

`h2physics.combustion.run_staged_turbine_cooling()` extends the existing native
Cantera open-Brayton state through caller-declared turbine stages. Each stage
expands the current frozen mixture to an absolute exit pressure, then admits its
own compressor-air flow and performs a perfect, enthalpy-weighted mix. The next
stage starts from that mixed composition and state. Cantera owns all gas property
flashes and the Brayton runner retains ownership of the combustor state.

## Python contract

`StagedTurbineCoolingInputs` binds an `OpenBraytonRun`, total compressor air and
hydrogen flow, ordered stage exit pressures, stage isentropic efficiencies,
coolant flow and coolant enthalpy rise per stage. The hydrogen-to-primary-air
ratio must agree with the retained native combustor run. Coolant flow is removed
from total air before combustion and added after the corresponding stage
expansion. The final stage pressure must match the Brayton exhaust boundary.
Each stage has a coolant source identity; common pressure-basis, efficiency and
feed schedule identities are required as well.

`TurbineCoolingStage` retains inlet, expanded and mixed station states, flow
rates, stage work, isentropic enthalpy, coolant enthalpy, coolant heat pickup and
mixing residual. `StagedTurbineCoolingRun.require_current()` checks the native
terminal state and retained issued result. Inputs are ordinary immutable Python
objects and accept arbitrary stage counts; persistence and JSON are not required.
Each stage's mixing residual is in watts and is checked against a relative budget
scaled to the inlet, coolant, and mixed-outlet enthalpy powers (with a 1 W
minimum numerical scale). It is not compared to a mass-flow value, which would
mix incompatible dimensions and could admit or reject a balance based on flow
units rather than energy conservation.

## Limits and evidence

The stage efficiency, pressure schedule, bleed rates and coolant enthalpy rise
are caller-owned. The model assumes adiabatic frozen-composition expansion inside
each stage, instantaneous complete mixing after injection, and no additional
pressure loss beyond the declared injection station. The heat-pickup ledger
records energy taken by coolant from hardware; it does not solve metal
temperature, conduction, convective coefficients, film effectiveness, passage
pressure losses, choking, local aerodynamics, blade stress, emissions or turbine
control. It is a station model, not blade-resolved CFD or a hardware design tool.

Deferred contracts cover two-stage mass/energy accounting, terminal pressure
rejection and per-stage evidence rejection. They use synthetic mechanism data
and are unexecuted. Independent experimental comparisons and real component
maps remain required before machine qualification. See [Request 035](../requests/035_hydrogen_gas_turbine_cycle.md).

## Thermodynamic implementation reference

The implementation delegates fixed-composition isentropic pressure changes and
enthalpy/pressure/composition state setting to Cantera's documented `SPY` and
`HPY` phase properties; the stage efficiency and mass-weighted mixing equations
are explicit caller-contract calculations in this package. See the
[Cantera 3.2 ThermoPhase property reference](https://www.cantera.org/stable/python/thermo.html).

The deferred fixture passes an instantiated Cantera `Solution` to
`run_open_cycle_brayton`, which accepts a native phase object. The staged-cooling
runner separately accepts a phase factory so it can preserve the Brayton run's
native owner. Passing a factory to the open-cycle function causes its native
phase guard to reject the callable before scenario assertions; this is a fixture
argument error, not a missing `SPY`/`HPY` capability in Cantera 3.2.

A later Hangang source exposed a separate Cantera 3.2 guard mismatch: the phase
provides species molar masses as `molecular_weights`, not
`mean_molecular_weights`. The open-Brayton guard and elemental ledger now use
the documented array property. Staged-cooling ledger and pressure-rejection
contracts still need a fresh pinned-source retry; the earlier results do not
evaluate these scenarios.
