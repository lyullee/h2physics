# Finite hydride to vessel failure history

`h2physics.adapters.history_from_finite_hydride()` projects the accepted gas
pressure samples in an issued `FiniteHydrideTrace` into the existing
`VesselFailureHistory` contract consumed by HELPR. The adapter contains no
failure criterion, crack mechanics, or new storage integration.

## Mapping contract

- The trace clock, pure-hydrogen property basis, and gas EOS source identity
  must match the typed failure context exactly.
- Each trace sample contributes its native **absolute** gas pressure in Pa.
  The downstream vessel model forms its pressure difference using its declared
  absolute external pressure; the adapter does not relabel pressure as gauge.
- Caller supplies one positive wall temperature in kelvin for every accepted
  trace time, with no interpolation or extrapolation. Hydride solid/bath
  temperature is not a vessel-shell temperature.
- Caller declares the shell identity, shell-temperature mapping evidence,
  geometry binding evidence, and history reconstruction evidence. Shell and
  geometry evidence must match the failure context.
- Provider-bound gas states are rechecked with `FiniteHydrideTrace.require_current()`
  and the issued history is reconstructed before HELPR uses it. A changed gas
  property provider or any altered loading sample rejects the history.

The mapped temperature is a single mechanical-region value. This path does not
derive a radial wall field, material constitutive law, flaw geometry, failure
probability, opening, or fragment state. Use the existing radial thermoelastic
bridge if a spatially resolved wall temperature/stress history is available.

Deferred Hangang contract: `finite-hydride-vessel-failure-history-handoff`
under `finite-hydride`. It checks the source-to-history interface only; HELPR
qualification and real-vessel evidence remain separate requirements.
