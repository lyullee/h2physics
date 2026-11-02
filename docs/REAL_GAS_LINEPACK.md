# Real-gas isothermal linepack

## Frozen-mixture native execution — 2026-11-01

Actual construction exposed an invalid access to `PropertyBasis.provider` in
`CoolPropMixtureIsothermalEOS`; that attribute is not part of the shared basis.
The adapter now uses the actual energy-reference ID, fluid identity, retained
spin declaration and composition fingerprint for its portable EOS identity.
Separate definition snapshots retain native owners and callback identities.
Basis values are copied into that snapshot so in-place reference/spin changes
cannot change both sides of a comparison unnoticed. No EOS or mixing rule was
implemented locally, and an unresolved mixture H2 spin remains unresolved.

The existing native mixture-linepack and mixture-pressure-wave cases both
passed after the fix, as did seven focused definition tests (20.97 s) and
scoped Ruff. The linepack charge advanced from 7 MPa to 7.03907112464 MPa with
mass residual -1.13e-14 kg. The 12-cell wave case had mass residual 7.11e-15 kg,
maximum CFL 0.3163862 below its 0.35 limit, and reproduced selected pressure-
density samples through the same native provider. Reference/spin, composition,
native state and callback mutations were rejected; restoring original values
restored valid operation. This is frozen-composition numerical integration,
not changing-composition/phase-event or experimental mixture qualification.

`h2physics.real_gas_linepack.RealGasLinepackState` models one fixed-volume,
well-mixed gas inventory with caller-prescribed inlet and outlet mass rates.
It computes density from retained mass and volume, then evaluates pressure
through the caller-selected `IsothermalSinglePhaseEOS`. Use
`CoolPropIsothermalEOS("Hydrogen")` when a direct pure-fluid HEOS reference is
needed. A fixed gas blend can use `CoolPropMixtureIsothermalEOS` around an
immutable `CoolPropMixtureProperties` provider, retaining the selected species,
mole fractions and installed HEOS mixing parameters. An `IsothermalEOSTable`
can be used only after qualification over the intended pressure-density-
temperature envelope.

```python
from h2physics.real_gas_linepack import RealGasLinepackState
from h2physics.thermo.isothermal_eos import CoolPropIsothermalEOS

state = RealGasLinepackState.from_pressure(
    volume_m3=2.0,
    temperature_k=293.15,
    pressure_pa=7.0e6,
    eos=CoolPropIsothermalEOS("Hydrogen"),
    minimum_pressure_pa=1.0e6,
    maximum_pressure_pa=1.0e7,
)
next_state, ledger = state.advance(
    duration_s=20.0,
    inlet_mass_flow_kg_s=0.05,
    outlet_mass_flow_kg_s=0.01,
    minimum_mass_kg=0.01,
)
```

For a fixed-composition blend, construct `GasComposition` with caller-declared
mole fractions and molar masses, create `CoolPropMixtureProperties`, then pass
`CoolPropMixtureIsothermalEOS(properties)` as `eos`. That closure rejects
non-gas states and uses the provider's mass-density and isothermal derivative
paths. Composition remains constant through each linepack step; use a dynamic
mixture inventory model when species stocks or phase partition evolve.

The state retains the EOS identity used at issuance. Initial pressure is
resolved to density through the provider; the EOS then recalculates pressure
from each accepted inventory density and the fixed temperature. A mismatch
between forward and inverse EOS paths rejects initialization. Every step
rejects nonpositive inventory, a crossed mass floor, provider-domain failures,
and caller pressure bounds. No flow clipping is applied.

This is a real-gas lumped inventory closure, not a flow solver. It does not
resolve spatial pressure, velocity or friction; infer valve/compressor rates;
evolve composition; or calculate the heat required to maintain constant
temperature. Its port rates and thermal condition are prescribed by the caller.
Use the isothermal Euler network or caloric wave models when spatial pressure
and flow transients are required. Use the caloric finite-reservoir coupling
when stored internal energy and energy-conserving transfer are required.

The deferred Hangang cases `hydrogen-pipeline-real-gas-linepack-eos` and
`coolprop-isothermal-mixture-linepack` exercise pure-fluid and fixed-mixture
EOS inversion, mass closure, pressure response, inventory and provider bounds.
They are implementation contracts, not measured pipeline validation. No local
runtime check or physical calculation is claimed.
