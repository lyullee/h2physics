# Native equipment property-interface verification

Both paths use CoolProp HEOS ParaHydrogen. The reference is the pinned native LH2DT HydrogenProperties; the new structural facade returns the actual native ThermoState factory after one protected AbstractState flash. No EOS, property table, interpolation or hidden fallback is added.

Declared basis: `CoolProp:8.0.0:HEOS:ParaHydrogen:default`. Native revision `b2f276333c1b1793c39f25763703d196d36742ec`.
60 PT/PH/PS/PU/P-rho/rho-U queries cover liquid, vapor, warm gas and saturated/intermediate quality. Phase labels and quality also agree. Relative tolerance is 1e-8 with field-specific absolute floors below; viscosity and saturation pressure have separate comparisons. No experimental property accuracy is inferred.

| Field | Absolute floor | Largest absolute difference |
|---|---:|---:|
| pressure_Pa | 0.0001 | 9.18295118026e-05 |
| temperature_K | 1e-07 | 0 |
| density_kg_m3 | 1e-09 | 3.5527136788e-15 |
| specific_enthalpy_J_kg | 1e-05 | 1.72826094058e-06 |
| specific_internal_energy_J_kg | 1e-05 | 5.65545633435e-06 |
| specific_entropy_J_kgK | 1e-06 | 4.21096046921e-09 |

Largest fraction of a state-comparison gate: 0.083481374366.
Explicit quality roundoff budget: 1e-08; maximum observed adjustment 0; adjustment count after verification/timing 0.
The native state class has no raw-quality field; the facade retains maximum/count and the last adjusted host state. Unsupported native methods remain absent. Mixture viscosity is not invented; the native HEM pipe keeps its own declared mixture closure. This subset is for the explicitly checked equipment, not every native component or constructor that demands an exact HydrogenProperties type.

Mixed public-interface timing: 300 full native states per trial, three trials; median reference 0.219443399998 s, facade 0.00965419999557 s, ratio 22.7303557.
This measured run includes mapping/native object creation. It does not predict whole-network speedup; the coupled simulator is measured separately.

Host code SHA-256:

- `src/h2physics/adapters/lh2dt_properties.py`: `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2`
- `src/h2physics/thermo/coolprop.py`: `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b`
- `scripts/check_lh2dt_property_provider.py`: `2ac5efc95b4ae4de868ad0f91643bc92097e0716c8ddc67046790102c50288ad`
