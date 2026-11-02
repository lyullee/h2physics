# Linepack withdrawal to compressor inlet

`bind_linepack_compressor_inlet()` adapts one current
`LinepackSourceHandoff` to the existing
`HydrogenRealFluidCompressionInputs` type. It reuses the linepack outlet
interval and its integrated withdrawal mass, then sets compressor inlet flow
to that mass divided by the interval duration. It preserves the linepack
source's representative outlet pressure and temperature.

The caller provides a CoolProp HEOS hydrogen property owner, discharge target,
efficiency, operating-domain bounds, compressor process-window ID, and
explicit compressor property-provider identity plus evidence for the
source-clock mapping, state, transfer boundary, efficiency, domain, and inlet
conditioning. The adapter replays the HEOS state at the
source P/T and requires the supplied signed energy to close
`withdrawn_mass * (HEOS inlet enthalpy - linepack source enthalpy)`.

## Scope

The returned object contains compressor inputs; it does not run the compressor.
The linepack source is an interval representative state, not a time-resolved
pressure history. This bridge adds no suction-line pressure loss, valve,
conditioning, compressor, or linepack physics. The signed conditioning term is
a caller ledger for mapping the ideal-gas representative source state to the
HEOS inlet state; it does not claim that a specific heat exchanger or process
has been modeled.

Deferred Hangang case:
`hydrogen-linepack-compressor-inlet-handoff` under
`gas-compressible-pipe`. It checks interval/mass/flow identity, state
reprojection, the signed enthalpy ledger, required evidence, and receipt
currentness. The case has not run and establishes no pipeline or compressor
qualification.
