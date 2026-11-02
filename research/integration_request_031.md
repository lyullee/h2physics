# Supplementary implementation contract for Request031 — simultaneous finite fuel-cell plant

## Purpose and ownership

The host package already contains a finite shared-stack operation, independent
native H2/O2/water-vapor compartment integrators, a post-run pressure-to-activity
bridge, a thermal allocation path, and diagnostics that retain unresolved combined
energy. Those pieces do not feed evolving compartment pressures into the reaction
model during integration. Do not close this gap by adding another host-side stack
or gas-vessel solver. The receiving Cantera/device owner must expose one accepted,
synchronized plant trajectory and its boundary integrals.

The missing level is a spatially lumped, transient, single-stack system with
separate finite gas inventories. It does not imply membrane transport, water
management, crossover, degradation, air machinery, product purification or plant
qualification unless the receiving owner supplies each as an explicit state/model.

## Proposed Python boundary

The receiving owner should expose an object-level API equivalent to:

```python
class CoupledFuelCellOwner(Protocol):
    def run(self, problem: CoupledFuelCellProblem) -> CoupledFuelCellRun: ...

    def verify_result(self, result: CoupledFuelCellRun) -> CoupledFuelCellRun: ...
```

`CoupledFuelCellProblem` must retain, by identity, the actual stack/caloric owner,
initial device/material/coolant state, independent finite compartment owners and
inventories, port-specific feed/withdrawal schedules, explicit absolute clock,
electrical/load schedule, heat/utility boundaries, activity or fugacity provider,
solver tolerances, and applicability evidence. The provider maps the instantaneous
native compartment state to dimensionless species activity at the same accepted
time and temperature. Ideal-gas ratios may be a named option; a non-ideal route
must call the selected property provider and retain its identity/reference. No
pressure or composition is interpolated from another run or prescribed channel.

`CoupledFuelCellRun` must be owner-issued and immutable to consumers. It must expose:

- Strictly increasing absolute accepted sample times with one common clock ID.
- Per-sample stack temperature, current/voltage/power, activity or fugacity inputs,
  compartment pressure, temperature, species moles, phase, and internal energy.
- Per-accepted-step integrated charge, Faradaic component extents, port mass and
  species transfer, electrical energy, reaction/caloric transfer, heat at each
  declared boundary, coolant/material storage change, and cumulative work terms
  whenever the owner models them.
- A component inventory residual for H, O and any explicitly represented species;
  a total-energy residual on one declared caloric reference and sign convention.
- Event brackets/accepted endpoint for current/voltage/temperature limits, finite
  inventory depletion, phase appearance/disappearance and scheduled switching.
- On failure, the original exception, last accepted common state, per-owner accepted
  prefix, failed trial, and all actual native solver objects. A failed trial must
  not be reported as an accepted state.
- A public `verify_result(result) -> result` check that verifies the exact owner,
  solver result, clock, accepted states, native arrays, ledgers and configuration
  without fitting, re-integrating, or changing any state.

Host adapters may then project that one run into the existing stack, compartment,
thermal, source and risk APIs. Projections must retain their parent run and may not
claim closure when an energy/component term is absent. No `pressure_feedback_resolved`
or `combined_energy_closed` claim may be caller-settable.

## Numerical and physical acceptance

The receiving implementation must supply a reviewed species/reaction basis and
explicit caloric references. It must independently verify Faraday charge-to-mole
conversion and each H/O atom balance over every accepted interval. Electrical work,
chemical/caloric transfer, gas internal-energy changes, material/coolant storage,
heat and modeled shaft/pump work must use a documented common sign convention.
Any unmodeled term remains a named unresolved residual; it cannot be balanced by
an inferred efficiency or hidden heat source.

Required authored numerical cases, executed as independent parallel workers:

1. Open-circuit/zero-current invariance with finite compartments and no reaction.
2. Ideal-activity constant-state case compared with the existing algebraic
   `FuelCellOperatingState` correction at identical T, P, composition and current.
3. Pressure-only perturbations in H2, O2 and product-water channels, independently
   varied, with the expected reaction-voltage direction and exact source states.
4. A finite-reactant case with a depletion event; the accepted prefix ends at the
   native event and no negative stock is admitted.
5. A heat/coolant case with analytic constant-capacity limiting behavior and an
   explicit integrated wall/coolant energy ledger.
6. A closed reaction/energy case with fixed references, independently recomputed
   species and energy residuals, then a solver-step/tolerance refinement.
7. Adversarial cases for mismatched clocks, mixed references, stale activity
   provider, altered native results, phase-domain rejection, and failed-prefix
   retention.

Run a Cartesian or declared pairwise campaign across load/current, initial H2/O2
pressure, feed limitation, stack/coolant initial temperature, heat boundary, and
solver tolerance. Each PBS array index records one case ID, complete source
revision/manifest, setup hash, native package/mechanism hashes, options, result
hashes and acceptance metrics. Use process isolation where any native/global state
is shared; do not parallelize different solves inside one native instance without
provider evidence.

Independent device validation requires synchronized measured current, voltage,
channel pressure, temperature, flow and clock/uncertainty records with a justified
measurement operator. Synthetic agreement and conservation do not validate cell
performance. Keep parameter estimation, held-out validation and qualification as
separate records.

## Host integration and release gate

The host package already has the receipt surfaces in `adapters.fuel_cell_compartments`,
`adapters.fuel_cell_activity_receipt`, `adapters.fuel_cell_compartment_energy` and
`electrochemical_thermal`. Extend those adapters only after the receiving owner
provides the synchronized run and public verifier. Preserve the existing separate
compartment route and label it prescribed/post-run. Keep failure closed when any
accepted component, energy, clock, phase or provenance term is missing.

Acceptance requires the receiving project's original stack/compartment regressions,
this varied parallel matrix, source/mechanism and installed-wheel audits, and the
independent device comparison where matched measurements exist. Until those gates
pass, mark the new coupled level implemented-unverified and do not promote current
post-run bridges to simultaneous feedback.
