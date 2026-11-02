# Linepack withdrawal to a finite source

## Native CoolProp route

The same `advance_linepack_to_source` API accepts an existing
`RealGasLinepackState` when `properties=` supplies the matched
`CoolPropProperties("Hydrogen")` provider. It delegates to
`advance_real_gas_linepack_to_source` and returns its
`RealGasLinepackSourceHandoff`. Native state, version, phase, density, identity
and receipt-currentness gates remain owned by that existing adapter. No
handwritten fluid-property calculation or fallback is introduced. See
REAL_GAS_LINEPACK_FUEL_CELL.md for the finite withdrawal and energy handoff
scope. One representative state still does not establish integrated enthalpy.

The following original route is an explicitly selected ideal analytical
reference. Supplying native `properties` to that ideal owner is rejected.

`h2physics.adapters.advance_linepack_to_source` couples one accepted step of
the existing lumped linepack model to the shared `IntervalMassSource` boundary.
The adapter calls `IsothermalLinepackState.advance`, retains its exact final
state and `LinepackStepLedger`, and uses the ledger's integrated outlet mass as
the source mass over the same start/end times. It does not create a separate
linepack or discharge physics model.

The caller provides a `SourceLocation`, origin, source evidence, and one
representative H2 `ThermoState`. The state must use basis fluid `H2`, be a gas,
match linepack temperature and ideal-gas density for the linepack molecular
mass (0.00201588 kg/mol), and have pressure within the accepted endpoint range. The caller's
`state_projection_evidence_id` records why that single state represents the
finite interval. The adapter preserves that property state and its energy
reference unchanged.

```python
from h2physics.adapters import advance_linepack_to_source

receipt = advance_linepack_to_source(
    linepack,
    duration_s=10.0,
    inlet_mass_flow_kg_s=0.0,
    outlet_mass_flow_kg_s=0.02,
    minimum_mass_kg=0.01,
    location=outlet_location,
    gas_state=representative_hydrogen_state,
    origin=origin,
    evidence_id="case-specific-outlet-evidence",
    state_projection_evidence_id="case-specific-interval-state-projection",
)
receipt.require_current()
finite_source = receipt.source
next_linepack = receipt.final
```

The receipt binds the exact input/final inventories, native port ledger,
representative state, source clock/location, and source fingerprint. It checks
that integrated inlet minus outlet equals the inventory change, the source
mass equals the outlet ledger, and no post-issuance edits have occurred. The
source is a finite interval-average boundary: within-interval pressure and
flow changes are not resolved. Existing nozzle or dispersion consumers may
apply their own declared models to the supplied source state; this adapter
does not infer an aperture, flow law, release direction effect, cloud, or
consequence.

The deferred Hangang case
`hydrogen-linepack-withdrawal-finite-source-handoff` uses an authored ideal H2
state to check integrated outlet mass and stale-source rejection. It requires
only the existing NumPy/SciPy core environment and is a software contract, not
experimental pipeline or dispersion validation.
