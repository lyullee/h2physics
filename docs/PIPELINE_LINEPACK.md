# Lumped isothermal pipeline linepack

`h2physics.pipeline_linepack.IsothermalLinepackState` represents one fixed-
volume, well-mixed gas-pipe segment. It advances the segment inventory over a
caller-defined interval with constant, nonnegative inlet and outlet mass
rates. The pressure is recalculated from the ideal-gas EOS after each step.

```python
from h2physics.pipeline_linepack import IsothermalLinepackState

state = IsothermalLinepackState.from_pressure(
    volume_m3=12.0,
    temperature_k=293.15,
    molecular_mass_kg_mol=0.00201588,
    pressure_pa=7.0e6,
)
state, ledger = state.advance(
    duration_s=30.0,
    inlet_mass_flow_kg_s=0.04,
    outlet_mass_flow_kg_s=0.01,
    minimum_mass_kg=0.1,
)
print(state.pressure_pa, ledger.mass_residual_kg)
```

The state is immutable. `advance()` returns a new state and a
`LinepackStepLedger` containing integrated port masses, endpoint inventory and
pressure, and the conservation residual. A withdrawal that reaches or crosses
the declared mass floor raises `ValueError`; the model does not silently clip
or redistribute a requested port flow. Callers can compose multiple segments
by passing each segment's accepted boundary rates into a network-level solver.

The thermodynamic closure is `p = m R T / V`, with caller-declared fixed
molecular mass and temperature. Therefore this API is an inventory-pressure
submodel, not a pipeline flow solver. It has no spatial pressure/velocity
field, friction or elevation coupling, compressible-wave dynamics, heat
transfer, species evolution, real-gas EOS, or flow controller. The separate
steady compressible-pipe momentum function remains the appropriate closure for
steady pressure-drop calculations. Do not interpret a lumped segment as a
pipeline transient qualification.

The deferred Hangang case `hydrogen-pipeline-lumped-isothermal-linepack` checks
injection, withdrawal, zero-net flow, pressure response, mass closure and
inventory-floor rejection. It uses synthetic caller parameters only and does
not compare with a measured linepack experiment.

For a typed bridge from one accepted withdrawal step into the common finite
source API, see [LINEPACK_SOURCE_HANDOFF.md](LINEPACK_SOURCE_HANDOFF.md). That
handoff requires gaseous H2 at the same ideal-gas molecular-mass and temperature
basis, and carries the exact integrated outlet mass. It does not introduce a
nozzle or dispersion calculation.

For a finite production batch from PV electrolysis, see
[`ELECTROLYSIS_LINEPACK.md`](ELECTROLYSIS_LINEPACK.md). It uses the same
fixed-volume isothermal closure and checks the source pressure against the
resulting linepack pressure.
