# Finite electrochemical thermal inventory

## Ownership and intended use

`HydrogenStack` remains the sole owner of polarization, charge conversion and
reaction-energy accounting. `FiniteThermalStack` only advances a lumped stack
temperature from that owner's unallocated energy, an explicit auxiliary heat
boundary and a signed coolant heat-transfer law. It is usable for electrolysis
and fuel-cell schedules without copying their material balances.

The public API accepts the existing stack object, a finite heat capacity, a
replaceable conductance callback, temperature bounds and piecewise-held operating
stages. This makes apparatus parameters replaceable without a wire format or a
second electrochemical solver.

## Sign and conservation contract

Positive `unallocated_energy_rate_w` enters the stack thermal inventory. Positive
auxiliary heat also enters it. Positive coolant heat leaves it; a negative value
records heat entering from a warmer coolant boundary. For every stage and full
trace:

`Delta U_stack = Q_generated + Q_auxiliary - Q_coolant`.

The finite inventory uses a declared constant heat capacity. Temperature and two
independent heat integrals are advanced by the same native SciPy integration.
The result retains the native solver object and the shared stack results at both
endpoints.

## Deferred validation

Four authored cases are defined under `validation/cases/electrochemical_thermal.py`:
adiabatic constant generation, analytic Newton cooling, signed heat reversal and
domain/clock rejection. They are code definitions only. Scientific execution is
deferred to the cluster profile `electrochemical-thermal`; no pass or validation
claim is made here.

## Explicit exclusions

This first level does not model coolant inventory or flow, spatial cell gradients,
liquid-water transport, crossover, degradation, controllers, startup phase change,
or apparatus-specific thermal properties. These require distinct data and physical
boundaries and cannot be inferred from a fitted heat capacity or conductance.
