# Underground cavern withdrawal to compressor inlet

`bind_underground_compressor_inlet()` maps one positive dry-H2 bin from an
admitted `UndergroundWithdrawalProjection` into the existing
`HydrogenRealFluidCompressionInputs` contract. It reuses the finite source bin's
exact edges and integrated mass to set a constant interval-average inlet flow.
The source representative pressure and temperature are replayed through the
caller-supplied CoolProp HEOS hydrogen provider, and must reproduce the exact
retained `ThermoState`.

The cavern projection retains two different interval enthalpy ledgers: the
native dry-H2 withdrawal integral and the enthalpy projected from the caller's
representative state. The adapter preserves both. Its signed energy-mapping
ledger must close native source enthalpy to the HEOS compressor inlet enthalpy.
The caller supplies the property-provider and process-window identities,
clock/state/transfer/energy evidence, compressor efficiency and property
domain.

## Limits

The receipt contains compressor inputs only; the compressor is not executed.
The native cavern model and withdrawal projection are not rerun. No wellbore
pressure loss, valve, pressure regulation, state conditioning, leakage, or
transient cavern-to-surface coupling is added. A signed energy-mapping ledger
is caller-owned and is not a heat exchanger model. Each source bin is handled
separately; no interval averaging beyond the existing projection is inferred.

Deferred Hangang case: `underground-cavern-compressor-inlet-handoff` under
`underground-storage`. It checks a native cavern withdrawal bin, mass-rate
closure, exact HEOS state replay, both enthalpy ledgers, signed energy mapping,
evidence, and receipt currentness. The case is unrun and provides no cavern,
well, or compressor qualification.
