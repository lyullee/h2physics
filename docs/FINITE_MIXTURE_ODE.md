# Adaptive bounded mixture vessel model

`h2physics.thermo.run_mixture_vessel_ode()` is the adaptive counterpart to the
finite-interval fixed-volume mixture model. The state is the species-ordered
component mole inventory and total fluid internal energy. The vessel volume is
fixed. At each trial, the runner builds a CoolProp HEOS provider for the current
overall composition and resolves the bounded two-phase V/U equilibrium state.

## Boundary API

The caller provides `MixtureBoundaryRates` from a pure Python callback receiving
`MixtureODEState(time_s, component_moles, internal_energy_j, provider, flash)`.
Liquid and vapor feeds are separate species-ordered molar-rate vectors with
separate integrated enthalpy rates. Phase outlets are total liquid/vapor molar
rates; the model calculates their component and energy removal from the current
flashed phase composition and native phase enthalpy. Heat and work rates are
signed into the vessel. The caller owns feed states, control law, rate
coefficients, provenance, and any evidence needed for the validity range.
Every feed enthalpy rate carries the same explicit energy-reference identity as
the vessel's initial internal energy and CoolProp provider template.

The continuous ODE integrates component inventories, total U, species-resolved
feed/outlet ledgers, inlet/outlet enthalpy, heat and work together. Every returned
adaptive solver point retains a composition-specific provider and its original
multi-seed V/U flash. `MixtureVesselODETrace.require_current()` rechecks all
retained packets and mass/energy balances.

The retained `solver_values` matrix is backed by immutable bytes. NumPy callers
cannot re-enable its write flag to alter the accepted inventory and energy
ledger beneath the trace freshness checks.

```python
from h2physics.thermo import (
    MixtureBoundaryRates,
    MixtureODEInputs,
    run_mixture_vessel_ode,
)

def boundary_rates(state):
    return MixtureBoundaryRates(
        liquid_feed_mol_s=feed_liquid_mol_s(state),
        vapor_feed_mol_s=feed_vapor_mol_s(state),
        liquid_feed_enthalpy_w=liquid_feed_enthalpy_w(state),
        vapor_feed_enthalpy_w=vapor_feed_enthalpy_w(state),
        liquid_outlet_mol_s=liquid_draw_mol_s(state),
        vapor_outlet_mol_s=vapor_draw_mol_s(state),
        heat_into_vessel_w=heat_w(state),
        work_into_vessel_w=work_w(state),
        evidence_id="project:boundary-law-v1",
        energy_reference_id="project:common-enthalpy-reference-v1",
    )

trace = run_mixture_vessel_ode(inputs)
trace.require_current()
```

## Integration and events

The time integrator is SciPy `solve_ivp` with explicit method, tolerance, maximum
step, and caller-declared integration boundaries. This is a host-side adaptive
driver, not a receiving solver's native integration. The registered terminal
events stop at an interior vapor-quality threshold or a positive component-mole
floor. Quality event thresholds must lie strictly inside the wider admitted
flash interval so the event root can be bracketed without asking the flash to
leave its domain. Branch changes and phase events beyond those thresholds fail
closed. RHS/property failures raise `MixtureVesselODEError`, which retains the
original cause, last trial state, solver diagnostics, and the previously accepted
prefix; it does not fabricate the hidden internal steps of a failing SciPy call.

Each RHS flashes a composition-specific V/U state, so the run can be expensive.
Use bounded time spans, physical rates, a reviewed flash domain, and conservative
step sizes. For a native receiving engine, accepted-step provenance, or externally
owned interval integrals, use the native owner or
`run_finite_mixture_vu_intervals()` instead. Neither API qualifies the EOS,
binary interaction parameters, stream data, vessel hardware, or separator design.

The `finite-mixture-ode-continuous-feed`,
`finite-mixture-ode-no-transfer-invariance`, and
`finite-mixture-ode-quality-event-localization` cases are deferred to cluster
execution. They are synthetic software contracts, not measured validation.

Hangang job `1186192` failed before adaptive ODE integration while creating its
initial H2/N2 native phase partition at 5 MPa and vapor mole quality 0.5. The
CoolProp phase compositions did not satisfy the declared absolute component
mole-fraction closure limit of `1e-7` (reported residual magnitudes were about
`1.3685e-5`). This is an EOS-backend packet rejection, not evidence of an event
root-localization defect. The closure limit remains unchanged; no accepted
ODE/event result exists for that attempt. A new pinned run must establish a
backend-supported initial state or an appropriate property route before the
event-localization contract can be considered exercised.

Diagnostics expose `attempted_rhs_calls`, counted at entry to every host RHS
callback, including the call that raises. `function_evaluations`, Jacobian and
LU counts retain SciPy's returned counters from completed solver calls; a failed
call cannot supply those native counters. Attempted RHS calls also include calls
used for numerical Jacobians, so the two counts need not coincide.

The initial equilibrium quality must lie strictly inside the terminal-quality
interval. Initial states on or beyond a terminal threshold are rejected before
RHS execution; they cannot silently complete without a directional crossing.
Choose a different admitted initial state or explicitly review the thresholds.

`trace.boundary_energy_history()` exposes immutable, named cumulative feed/outlet
enthalpy, heat, work and net-energy arrays with `time_s`. It reads the original
solver-integrated channels after the trace's freshness/balance audit; callers do
not need to decode state-vector indices or repeat numerical quadrature. Outlet
enthalpy is an export; heat and work carry the declared sign into the vessel.

`trace.component_inventory_history()` returns species names, the accepted clock,
and `(time, species)` arrays for retained component moles and cumulative inlet/
outlet moles. Liquid and vapor port totals are combined per species. The arrays
are immutable copies of the solver-integrated state and remain in molar units.

The same component-history mapping also exposes `molar_masses_kg_mol`,
`component_mass_kg`, `cumulative_inlet_component_mass_kg` and
`cumulative_outlet_component_mass_kg`. Each mass column is the corresponding
mole column times its retained template molar mass; species order is unchanged.
This is a unit/basis projection of the conserved inventory, not another solve.

Exact repeated component/U trial states reuse the immediately preceding native
flash even when the clock or cumulative boundary ledgers differ. Each callback
still receives a new `MixtureODEState` with its actual trial time. This one-entry
cache performs no interpolation, rounding or reuse across different inventories.

`equilibrium_flash_calls` counts entries into the bounded V/U flash, including
the initial flash and a flash that raises. It excludes exact cache hits. This
makes property-solve work visible alongside RHS attempts when benchmarking the
cluster campaign; neither counter is a wall-time speedup measurement.
