# Request 029 — adsorption vessel, valve, relief and facility contracts

The host now provides source-only composition contracts. Receiving repositories
remain unchanged and all acceptance profiles are unexecuted.

## Adsorption vessels

Expose absolute-versus-excess uptake basis, adsorbent mass, accessible void,
species identity and original provider result. Couple provider-owned equilibrium
uptake to a versioned gas property state so free and adsorbed inventories can be
audited together. Dynamic fill, LDF/heat transfer and minimum delivery pressure
must remain separate levels with apparatus-qualified inputs.

Acceptance requires `finite-adsorption-vessel`, the original adsorption/property
suites and independent isotherm plus vessel-capacity data.

The host now also contains a single-species adaptive LDF vessel level in
`h2physics.storage.adsorption_dynamics`. It composes the existing absolute-uptake
provider with its frozen pure-gas EOS, site-specific rate constants and adsorption
internal energies, lumped solid/wall heat capacity, and caller-owned feed/outlet/
heat schedules. It reports pressure, temperature, free and adsorbed inventories,
and separate energy-transfer histories. The deferred `adsorption-dynamics-*`
cases exercise closed inventory/energy balances and a piecewise feed. These are
authored synthetic contracts only; no local numerical calculation was run.
The trace retains total (free plus adsorbed) moles, nonnegative cumulative feed
and outlet mole ledgers, and a directly reconstructed residual at every accepted
sample. The residual sign convention is inventory change minus feed gain plus
outlet loss; ledgers use mol and start from zero at the initial sample. Trace
construction rejects altered inventory or residual arrays that do not reconcile
with the retained site loadings and flow ledgers. Issued traces expose
`require_current()` to verify every retained array with the input, EOS,
equilibrium-provider and boundary-callback bindings before downstream use;
dataclass-replaced or detached traces are not accepted as issued results.
Multicomponent competitive dynamics, axial breakthrough and measured kinetic or
calorimetric qualification remain open. Rate, energy, boundary and material data
must be independently sourced before predictive use.

## Actuated valves

Expose finite stroke on an explicit clock and an evidence-bearing normalized
effective-area map. Retain original signed shared-nozzle results and reverse-flow
permission. Do not infer Cv/Kv conversion, actuator torque, stiction, leakage,
fail action or a refuelling controller.

Acceptance requires `valve-actuator`, original valve/nozzle suites and qualified
manufacturer actuator/flow evidence.

## Relief lift and pickup

Expose original set/reseat latch state, accepted-sample lift, seat leakage and
caller-owned vapor/liquid/bulk pickup with available mass. Hidden pressure
crossings, chatter, sizing and phase-selection physics need distinct evidence.

Acceptance requires `finite-relief-lift`, original relief/tank/nozzle suites and
qualified lift/leak/phase-withdrawal observations.

The host also has an accepted-edge withdrawal ledger that consumes two original
adjacent relief-lift results and applies an explicitly identified linear-rate
trapezoid to mass and transported enthalpy. It requires an unchanged pickup
phase, an explicit clock/source chain, caller-owned non-relief phase inventory
change and a closing before/after stock balance. This receipt is not tank
integration, native solver quadrature or within-edge depletion protection.
Acceptance requires an independent native inventory comparison and step
refinement evidence in addition to the original relief/tank/nozzle suites.
See `docs/RELIEF_WITHDRAWAL_LEDGER.md`.

## Facility continuity

Publish original `ConnectionTransfer` objects with fixed node/port identities.
Callers provide external material, heat, shaft and finite storage derivatives on
one explicit clock. Missing boundaries, reference mismatches and port reuse must
fail rather than being inferred.

Acceptance requires `facility-continuity`, every contributing equipment profile
and independent facility measurements. A closed ledger is not plant qualification.
