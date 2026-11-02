# Compressor discharge finite-source boundary

`h2physics.adapters.bind_compressor_discharge_source()` adapts one accepted
`HydrogenRealFluidCompressionRun` into the existing `IntervalMassSource`
contract. It preserves the compressor's pure-H2 HEOS discharge state and
requires the caller to supply the release location, release-clock interval,
leak mass flow, origin, and separate evidence identifiers for clock mapping and
the release-flow boundary.

The adapter checks that the caller's leak flow is positive and does not exceed
the compressor's accepted hydrogen throughput. It replays the compressor
property owner at the exact outlet pressure and temperature and checks the
pressure, temperature, density, enthalpy, entropy, and compatible property
basis before emitting the source. Released mass is the supplied flow multiplied
by the supplied interval; the source energy ledger uses the preserved outlet
specific enthalpy. The emitted receipt is owner-issued, one-shot, and checks
that its source and evidence-bound payload remain current.

## Use and limits

Use this boundary when an upstream compressor result must enter an existing
finite-source chain. The time mapping and leak flow are input assumptions and
must have traceable evidence appropriate to the scenario. This adapter does not
derive leak flow from an orifice or valve, model pressure decay in a receiver,
calculate a nozzle state, or predict dispersion, ignition, radiation, or
overpressure. Those effects require their own declared models and evidence.

The deferred Hangang case is
`compressor-discharge-finite-release-source-handoff` in
`validation/cases/compressor_discharge_source.py`. It checks source identity,
state and mass/enthalpy conservation, rate bounds, evidence binding, and
reissuance rejection. Until that case has run on the pinned Hangang source, the
adapter has not passed runtime validation. Even a passing synthetic case would
establish software contract behavior only, not leak-model accuracy.
