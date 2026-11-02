# Catalytic plug-flow reactor

`CanteraCatalyticPFR` adds a spatially steady level to the existing finite
catalytic stirred-volume models. It adapts Cantera 3.2 `FlowReactor` and
`ReactorSurface`; it does not reproduce their reaction, surface-state, or
integration equations in project code. The caller supplies the mechanism bytes,
phase names, operating state, feed mass flow, cross-section, catalyst surface
area per gas volume, inlet coverages, axial output positions, numerical limits,
and the mechanism's applicability/rights evidence.

```python
from h2physics.adapters.cantera import (
    MechanismBasis, NativeMechanismSource, ReactiveState,
)
from h2physics.adapters.cantera_catalytic_pfr import CanteraCatalyticPFR

# `raw` must be the caller's exact, separately qualified mechanism bytes.
basis = MechanismBasis(
    identifier="qualified-site-kinetics-v1",
    source_sha256=sha256_of_raw,
    license_id="separately reviewed mechanism license",
    references=("source-specific scientific reference",),
    minimum_temperature_k=500.0, maximum_temperature_k=1400.0,
    minimum_pressure_pa=20_000.0, maximum_pressure_pa=2_000_000.0,
)
owner = CanteraCatalyticPFR(
    NativeMechanismSource(raw, "gas"), basis,
    gas_phase_name="gas", surface_phase_name="Pt_surf",
)
trace = owner.run(
    ReactiveState(900.0, 101_325.0, {"H2": 0.15, "O2": 0.05, "AR": 0.80}),
    initial_coverages={"PT(S)": 1.0},
    axial_position_m=(0.0, 0.001, 0.005, 0.01),
    cross_section_area_m2=1e-4,
    surface_area_to_volume_m_inv=2e4,
    mass_flow_rate_kg_s=2e-5,
    maximum_axial_step_m=1e-5,
    relative_tolerance=1e-9, absolute_tolerance=1e-15,
)
trace.require_current()
```

Each `CatalyticPFRPoint` contains the accepted axial position, native gas
temperature and pressure, density, flow speed, gas mole fractions and catalyst
coverages. Output arrays are immutable. `require_current()` checks the retained
native endpoint and mechanism identity against the issued trace. Use a distinct
owner and Cantera phases for each concurrent worker.

## Model boundary

The current level assumes a steady one-dimensional plug-flow stream, constant
cross-sectional area and pressure/frictionless adiabatic behavior as represented
by Cantera's native `FlowReactor`. Catalyst surface chemistry comes only from
the caller's native mechanism. This wrapper does not add pressure drop, axial
conduction, external heat exchange, finite catalyst heat capacity, pore-scale
mass/heat transport, deactivation, coking limits, catalyst life, plant controls,
or industrial yield estimates. Those require a separate physical boundary and
qualified input data.

The module does not bundle a mechanism or imply rights to one. `MechanismBasis`
is caller-supplied provenance and declared domain, not automatic license review
or scientific validation. The trace is a software result; measured reactor
comparison, mesh/convergence assessment, mechanism verification and process
qualification remain deferred to the parallel validation campaign.

Cantera's native basis is documented in the [FlowReactor API](https://cantera.org/3.2/python/zerodim.html#flowreactor),
[ReactorSurface API](https://cantera.org/3.2/python/zerodim.html#reactorsurface),
and its [surface-chemistry plug-flow example](https://cantera.org/3.2/examples/python/reactors/surf_pfr.html).
