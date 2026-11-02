# Request 033 — Native fixed-area pool energy and finite-wall continuation

Receiving owner: DynamicLH2PoolX. Host consumers:
`h2physics.adapters.parcel_pool_chain` and `liquid_accident_energy`.

## Existing concrete boundary

The reviewed `run_fixed_area_pool(config, inflow, output_times_s)` accepts initial
liquid stock and returns `FixedAreaPoolResult.ledger` with cumulative inflow,
liquid stock, cumulative evaporation, instantaneous substrate heat flux and
instantaneous evaporation rate. It computes native normal-hydrogen saturation
properties. Its fixed-area semi-infinite conduction source is distinct from the
finite lumped impact patch. `initial_thermal_age_s` preserves declared substrate
age but does not transport the finite impact patch's energy state.

Inspection of the pinned DynamicLH2PoolX 0.2.0rc2 `dynamic_fixed_area.py` confirms
that `FixedAreaPoolLedger` exposes `time_s`, `cumulative_inflow_kg`,
`liquid_mass_kg`, `cumulative_evaporation_kg`, `substrate_heat_flux_W_m2`,
`evaporation_rate_kg_s`, liquid temperature/density and fixed geometry, plus
closure/status labels. `FixedAreaPoolResult` adds only a final mass residual,
solver identifier and disappearance times. The output rows are requested samples;
the owner integrates internally across requested and inflow-change boundaries but
does not return accepted-edge cumulative energy integrals or integration-stage
diagnostics. Neither type retains liquid U, inlet/vapor H, integrated applied or
rejected heat, pressure-volume work, a stable energy-reference/phase identity, or
a finite-wall state. Its semi-infinite `Substrate` holds thermal properties, not
a finite wall energy inventory. The current result types therefore cannot support
the energy ledger below without adding native-owner outputs.
This route is analytic rather than an adaptive ODE: `output_times_s` are requested
reporting samples, while inflow changes and disappearance brackets are internal
integration splits. If the owner adds cumulative terms at those reporting samples,
it must accumulate them inside the same native interval/event calculations; the
host will not relabel requested samples as solver-accepted stages. If a later owner
introduces adaptive accepted states, expose their native clock and terms separately.

The host initializes a pool only from the original admitted deposited batch and
an explicitly separate substrate owner. Cumulative evaporation is used for
conservative mass bins. It is not used to invent a substrate heat integral.
The host energy diagnostic reports original stage terms and explicitly leaves
global closure unresolved.

## Requested Python contract

Keep the existing `FixedAreaPoolResult.ledger` row type and add these Python
attributes to every accepted row (SI units, one row per requested accepted
edge). The host binder in `h2physics.adapters.pool_energy_ledger` consumes
these exact names; do not require an intermediate JSON or reconstructed
sparse-output object:

| Attribute | Meaning / sign |
| --- | --- |
| `liquid_internal_energy_j` | Liquid control-volume U on the original liquid property reference |
| `cumulative_liquid_inlet_enthalpy_j` | Inlet H transported into the liquid CV, positive inward |
| `cumulative_vapor_outlet_enthalpy_j` | Vapor H transported out of the liquid CV, positive outward |
| `cumulative_substrate_heat_into_liquid_j` | Heat delivered to liquid, positive inward |
| `cumulative_pressure_volume_work_out_j` | Boundary P dV work, positive outward |
| `boundary_pressure_pa`, `liquid_volume_m3` | Accepted-edge liquid boundary state used for work accounting |
| `cumulative_unapplied_heat_j` | Offered heat not applied to either liquid or substrate, nonnegative cumulative J |
| `cumulative_dry_surface_heat_j` | Heat assigned to dry surface after local dryout, nonnegative cumulative J |
| `cumulative_heat_cap_rejection_j` | Heat rejected by the native heat-flux/capacity limiter, nonnegative cumulative J |

Also expose stable native result identities `energy_reference_id` and
`vapor_phase_id` (or equivalent result-level values that the host can bind
without guessing). For finite-wall mode each accepted row additionally needs
`substrate_energy_change_j` relative to the initial wall and
`cumulative_external_heat_into_substrate_j`, positive inward. The first edge
is the declared initial state: every cumulative transfer/allocation and both
energy-change fields are exactly zero there. The three heat-allocation
cumulatives are nonnegative and nondecreasing. Do not assume monotonicity for
net heat transfer if the model permits heat reversal.

Use these conventions to independently reproduce the host residuals at each
edge: `R_liquid = U - U0 - Hin + Hout - Qsubstrate + Wout`; for finite walls,
`R_wall = dUw - Qexternal + Qsubstrate`. Publish native residuals using those
same signs, while retaining enough original native terms for the host to
recompute them. If the current solver cannot provide one of these values at
its actual accepted integration edges, report the missing capability and
defer binding; do not approximate it from output sampling.

Preserve the existing native owner and expose accepted-clock cumulative energy
fields directly from the native heat/evaporation integration:

- initial/final liquid internal energy, and cumulative liquid inlet enthalpy;
- cumulative vapor outlet enthalpy and an explicit phase/reference identity;
- cumulative substrate heat delivered to liquid, with any unapplied heat,
  dry-surface allocation and heat-capacity/heat-flux cap allocation stated;
- pressure-volume work sign convention, boundary pressure and volume history;
- substrate internal-energy change where a finite substrate model exists;
- independently recomputable per-edge energy residual, native integration
  diagnostics and the exact original heat/material/property owners.

Native mass reflection and dryout events must allocate heat consistently when
the stock is zero or partially exhausted. A semi-infinite substrate with
prescribed temperature is an external heat reservoir; label it accordingly and
do not report a fabricated finite substrate U. Native cumulative heat must use
the same event intervals/thermal-age integration as native evaporation. A host
quadrature of sparse instantaneous output flux is not an equivalent substitute.

For actual finite impact-wall continuation, add a separate explicitly selected
native finite substrate boundary accepting original wall temperature/energy,
capacity/material owner, contact-end clock and applied external heat. Return the
updated wall energy and pool heat. Do not reset the original wall to ambient,
reapply impact heat, or treat a newly declared substrate as the same wall.
The existing independently owned substrate route must remain available.

## Acceptance and integration

At each accepted edge verify the liquid control-volume equation using U storage,
inlet/outlet H transport and separately signed heat/work terms. For finite-wall
mode independently verify wall U and the combined pool/wall balance; transferred
heat cancels exactly once. Check zero heating, no-inflow initial stock, capped
heating, dryout inside an output interval, post-dryout behavior and thermal-age
continuation. Refine native steps/outputs without redefining the heat source.

Retain source/property/spin/phase reference and original native result on failure.
Common global accident closure additionally requires caller-defined boundaries
for initial flash vapor, prescribed parcel launch energy, rebound and unselected
liquid. Delivering this pool ledger alone must not mark that global closure true.

The local accident energy receipt now accepts an optional `PoolEnergyLedger` only
when it retains the exact same original deposited-stock continuation and clock
window as the exhaustive mass ledger. That host receipt keeps pool energy separate
from flash, flight and impact terms and continues to report global closure as false.
The current native pool owner does not expose the required cumulative fields, so
the new pairing case requires a future reviewed project fixture and remains
deferred.

The host fail-closed check is retained: `bind_native_pool_energy_ledger()` raises
`PoolEnergyCapabilityError` when these exact original-row fields are absent. Do not
replace that rejection with host quadrature of `substrate_heat_flux_W_m2`,
latent-heat-times-evaporation reconstruction, or sampled pressure/volume work.

This request remains an unimplemented receiving capability specification. It is
not evidence of native correctness, experimental validity or host global closure.

## Host-side Python contract support

`h2physics.adapters.pool_native_energy_contract` now provides immutable edge and
trace records for a receiving native implementation to report its accepted states
and already-integrated interval totals. The trace recomputes liquid mass and
energy balances and, in finite-wall mode, the wall balance. It retains the exact
native result, per-edge state object and native step identity, and rejects a
prescribed reservoir that claims finite-wall storage. It does not perform the
pool's thermal or mass integration, convert requested output samples into
accepted solver states, or add fields to DynamicLH2PoolX. The receiving owner is
still absent from this repository, so native capability and the fail-closed
host binder remain outstanding. Its synthetic deferred case tests only this
Python contract.
