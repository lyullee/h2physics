# Cantera gas-volume vent to finite H2 source

`bind_cantera_gas_volume_vent()` maps the native cumulative outlet ledgers from
one completed `GasVolumeTrace` into the shared `IntervalMassSource` contract.
The source bin edges use the original absolute Cantera clock; bin masses are
differences of the named vent's native CVODES mass integral. The receipt keeps
the output trace, original vent identity, source location, representative state,
evidence and explicit conservation budgets. `require_current()` rechecks the
trace arrays, native endpoint, phase fingerprint, source bins and energy ledger.

```python
from h2physics.adapters import bind_cantera_gas_volume_vent

handoff = bind_cantera_gas_volume_vent(
    trace,
    vent_boundary_id="relief-port",
    location=source_location,
    representative_state=mean_outlet_h2_state,
    boundary_projection_evidence_id="vent-to-source-plane",
    state_projection_evidence_id="mean-state-energy-projection",
    mass_tolerance_kg=mass_budget_kg,
    species_tolerance_kg=species_budget_kg,
    energy_tolerance_j=energy_budget_j,
)
handoff.require_current()
finite_source = handoff.source
```

This route is deliberately limited to a frozen, pure H2 volume with no feed
and exactly one vent. Those conditions make the named total vent mass equal the
H2 source mass without estimating species fractions from sparse snapshots.
Mass, species and total-energy residual arrays must fit caller-declared budgets.
The representative state must retain the same Cantera mechanism, source hash,
H2 spin declaration and native caloric reference; its mass-weighted enthalpy
must match the native integrated outlet enthalpy within a declared absolute and
relative budget. Spatial vent-to-source mapping remains caller evidence.

The deferred Hangang case
`cantera-gas-volume-vent-finite-source-handoff` is discovered through
`validation.cases.cantera_gas_volume_source` in the existing `counterflow-flame`
profile. Its authored pure-H2 mechanism and outlet are synthetic software
fixtures. This adapter does not create a pressure-driven valve or relief law,
model failure frequency, calculate a plume, or establish ignition or
consequence. Mixed-gas/finite-rate volumes are intentionally rejected because
the current native vent ledger does not retain named vent-species integrals.
