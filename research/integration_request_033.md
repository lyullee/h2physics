# Supplementary implementation contract for Request033 — accepted-clock LH2 pool/fire energy

## Purpose and owner

The host now defines `PoolEnergyLedger` and rejects a pool result that does not
publish cumulative native energy fields on every accepted output edge. It must not
integrate sparse heat-flux or evaporation samples to manufacture a control-volume
balance. The missing equations and accepted-step bookkeeping belong in the native
pool owner (DynamicLH2PoolX) and must be exposed by the original pool run. Host code
must continue using that solver rather than duplicating its spreading, conduction,
boiling or evaporation model.

## Proposed native Python result contract

Extend the native result with an immutable accepted-edge trace, conceptually:

```python
@dataclass(frozen=True)
class PoolEnergySample:
    time_s: float
    liquid_mass_kg: float
    liquid_internal_energy_j: float
    liquid_volume_m3: float
    boundary_pressure_pa: float
    substrate_mode: str
    substrate_internal_energy_change_j: float | None
    cumulative_inlet_mass_kg: float
    cumulative_outlet_mass_kg: float
    cumulative_inlet_enthalpy_j: float
    cumulative_outlet_enthalpy_j: float
    cumulative_heat_into_liquid_j: float
    cumulative_external_heat_into_substrate_j: float
    cumulative_pressure_volume_work_out_j: float
    cumulative_unapplied_heat_j: float
    cumulative_dry_surface_heat_j: float
    cumulative_heat_cap_rejection_j: float
    mass_residual_kg: float
    energy_residual_j: float
    substrate_energy_residual_j: float | None
```

The native run must expose `accepted_energy_samples` aligned one-to-one with its
initial state and every accepted solver output. Each entry retains source IDs,
fluid/spin and liquid/vapor phase IDs, energy-reference identity, substrate mode,
native step identity and the exact accepted state object. `verify_result(result)`
must return the same original run after checking native arrays, accepted state,
configuration and cumulative fields without replaying integration.

The cumulative quantities use one declared sign convention: inlet mass/enthalpy
and heat into the liquid are positive; outlet mass/enthalpy and pressure-volume
work out of the liquid are positive in their named directions. Inlet and outlet
enthalpy use the original phase/property basis; no saturated-vapor label may replace
the actual emitted phase. Prescribed-reservoir and finite-wall modes are distinct.
An external-reservoir mode cannot report a finite substrate internal-energy change.
A finite wall requires its own stored-energy change and balance at every accepted
edge. Raw trial stages must not be mistaken for accepted states.

`unapplied_heat`, `dry_surface_heat` and `heat_cap_rejection` are cumulative
nonnegative allocations. Their initial values are exactly zero and they must not
decrease. The native contract must identify where the requested heat went; the host
may not infer dryout, surface exposure or heat-cap behavior from a zero radius or
sparse last-substep flux.

## Numerical acceptance and parallel cases

Each case is a separate process/array element with pinned source, setup, native
revision and input receipts. At minimum execute:

1. Zero heat-driving and zero-source limits with exact unchanged inventory.
2. Constant-temperature/constant-boundary cases with independently recomputed
   mass, fluid energy and (when finite) wall energy at every accepted edge.
3. Piecewise source/feed and withdrawal schedules whose interval integrals are
   compared with native accepted mass changes; include events exactly on source
   boundaries and immediately to either side.
4. Prescribed-reservoir versus finite-wall modes; reject missing wall-energy fields
   and any reservoir result that claims finite-wall storage.
5. Zero, active and exceeded heat-cap limits, plus partial/fully dry surface
   intervals. Check cumulative allocation accounting at each edge.
6. Pool depletion and native failure cases. Preserve the exact accepted prefix and
   original exception; do not treat the failing trial as accepted.
7. Simultaneous spatial/time refinement of radial mesh and maximum step, recording
   mass, energy, escaped-domain inventory, wall U and each heat allocation as
   separate errors. Predeclare budgets before comparing runs.
8. Metamorphic cases for changed energy reference, changed phase identity,
   incompatible hydrogen spin, nonmonotone cumulative allocation and mutated native
   accepted arrays.

Check balances per accepted interval and cumulatively. Independently recompute
`m_liquid - m_initial - m_in + m_out` and the declared first-law residual using
native accepted states and integrated terms. A balance that closes only after
trapezoidal integration of sparse rates is a failure. Changing the output sample
request must not change cumulative integrals beyond the declared solver tolerance.
Independent heat-transfer/pool observations are still required for physical
validation; numerical closure alone only verifies the software ledger.

## Host integration gate

After the native fields exist, adapt
`adapters.pool_energy_ledger.bind_native_pool_energy_ledger()` to bind directly to
the native issued trace and its every-edge terms. Preserve the current fail-closed
`PoolEnergyCapabilityError` for older results. Keep this pool energy ledger separate
from flash, droplet flight, impact and fire stages; stage residuals cannot be summed
into global accident closure without explicit shared boundaries and a common energy
reference.

Acceptance requires the new native output contract, original pool regressions,
the varied parallel matrix, source/mechanism/installed-artifact audits and any
independent experiment comparison that has matching phase, boundary, geometry and
clock metadata. Until then, record the pool energy path as implemented-unverified;
do not claim accepted native energy or a validated LH2 fire consequence.
