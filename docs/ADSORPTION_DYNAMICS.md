# Finite adsorption vessel dynamics

`h2physics.storage.integrate_adsorption_dynamics` adds an adaptive, lumped
single-species vessel model on top of the existing adsorption provider and gas
property contract. It is intended for hydrogen inventory studies where a caller
has a qualified absolute-uptake equilibrium provider, finite geometry, kinetic
coefficients, and thermal properties.

## Resolved state and closures

The solver advances free-gas moles, site-resolved adsorbed loading, and the total
stored internal energy. At each trial state it inverts the already-bound pure-gas
EOS for pressure, evaluates equilibrium site loading, and applies the linear
driving-force relation `dq_j/dt = k_j (q*_j - q_j)`. The caller supplies feed,
withdrawal, feed enthalpy, and heat rates through a Python callback. Outflow
enthalpy follows the vessel gas state. Gas internal energy, a lumped solid/wall
heat capacity, and caller-supplied site-specific adsorption energy determine
temperature from the total energy balance.

The component uses SI units: pressure Pa, temperature K, time s, amount mol,
loading mol/kg, rate constants 1/s, energy J, and heat W. Feed and withdrawal
rates are nonnegative; heat and adsorption energy are signed. Feed enthalpy and
outflow enthalpy must use the exact `PropertyBasis.reference_id` of the bound gas
EOS. `boundaries_s` provides exact integration segment edges so schedules can be
piecewise-defined without discontinuities inside a segment.

## Example API shape

```python
from h2physics.storage import (
    AdsorptionBoundaryRates,
    AdsorptionDynamicsInputs,
    integrate_adsorption_dynamics,
)

inputs = AdsorptionDynamicsInputs(
    vessel=finite_vessel,
    initial_pressure_pa=2.0e6,
    initial_temperature_k=298.15,
    initial_site_loadings_mol_kg=(0.4, 0.1),
    ldf_rate_constant_s=(0.02, 0.005),
    adsorption_energy_j_mol=(-6500.0, -9000.0),
    solid_wall_heat_capacity_j_k=2.0e4,
    reference_temperature_k=298.15,
    temperature_bounds_k=(180.0, 450.0),
    pressure_bounds_pa=(1.0e4, 8.0e7),
    start_time_s=0.0,
    end_time_s=100.0,
    boundaries_s=(0.0, 100.0),
    boundary_rates=my_boundary_callback,
    rate_evidence_id="material-rate-source",
    energy_evidence_id="calorimetry-source",
    run_id="case-01",
)
trace = integrate_adsorption_dynamics(inputs)
```

The snippet shows the parameter contract only; its illustrative numbers are not
qualified design data. `trace` retains accepted time, pressure, temperature,
free-gas inventory, site loading, total component inventory, cumulative feed and
outlet moles, stored energy and separate feed/outflow/heat energy histories.
`component_residual_mol` is recomputed at every accepted solver sample as
`total(t) - total(t0) - (feed(t) - feed(t0)) + (outlet(t) - outlet(t0))`.
Both mole ledgers start at zero and increase monotonically; inventory includes
free gas plus adsorbed uptake. `energy_residual_j` reports numerical first-law
closure and must be reviewed against an application-specific tolerance.
Call `trace.require_current()` before using a stored receipt downstream. The
issued result binds all retained histories and the admitted input/provider/callback
configuration; ordinary dataclass replacement cannot create another accepted
trace.

Bound provider callbacks are identified by their underlying function and owner,
not by Python's temporary bound-method wrapper object. Repeated lookup of the same
provider method therefore remains current; edits to the method code, captured
configuration, or provider owner's ordinary state still invalidate the input
receipt.

## Domain limits

The current implementation is limited to one gas species, fixed rigid volume,
one lumped temperature, absolute adsorption loadings, instantaneous gas thermal
equilibrium, and linear site-specific LDF coefficients. It does not model axial
bed gradients, breakthrough fronts, heat waves, pore diffusion, pressure drop,
competitive multicomponent adsorption, hysteresis, thermal-property variation,
adsorbent deformation, vessel stress, or an inferred adsorption heat. A provider
or kinetic law outside its published domain must reject the state. This API does
not replace the native adsorption-cycle engine or its measurement-based checks.

The deferred `adsorption-dynamics-*` cases are numerical contract checks only.
Independent equilibrium/kinetic measurements, calorimetry, vessel heat capacity,
wall coupling, and pressure/temperature histories are still needed before the
model can be used predictively. No local scientific execution was performed for
this implementation increment.
