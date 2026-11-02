# LH2DT native physical state and property contract

Status: actionable property/state and phase-selective withdrawal request; local P4 contracts implemented.

Target: `lh2dt_models`. Reviewed baseline: `b2f276333c1b1793c39f25763703d196d36742ec`.

## Existing local implementation

`h2physics.core.PropertyBasis`, `ThermoState`, `Stream` and `MassPartition` define the
local physical meanings. `h2physics.adapters.lh2dt` already exchanges native state and
`MassEnergyFlow` objects. `scripts/check_lh2dt_integration.py` checks actual native
objects and a synthetic homogeneous-tank mass/energy boundary.

No JSON, HTTP endpoint or dependency on this host package is required. Structural
Protocols and the existing native dataclasses are sufficient.

## Requested receiving changes

1. Publish one declared property-provider Protocol for component constructors, including
   `from_pT`, `from_ph`, `from_ps`, `from_rho_u`, `from_prho`, `from_pu`, saturation,
   transport and any derivatives actually consumed by those components.
2. Expose immutable fluid/spin identity and energy-reference identity on the provider.
   Do not infer equivalence from fluid names alone.
3. Separate facility configuration from the reusable physical implementation and document
   the authoritative version when an application bundles modified model copies.
4. Keep native fields and Python factories stable or version intentional changes. Preserve
   the current absolute-Pa/K/J-per-kg semantics.
5. Add an optional injection path for a compatible fast property provider after reference
   and domain tests. There must be no silent phase extrapolation or fallback.

## Acceptance cases

- Native and adapted PT/PH/PS states agree for cold para-hydrogen and warm gas cases.
- Passing normal-H2 state into a para-H2 stream boundary is rejected without an explicit
  scientifically justified conversion.
- A native tank accepts the mapped `MassEnergyFlow` directly and closes mass and total energy.
- An injected property provider passes the relevant phase/critical-region and inverse-state
  tests, not only a warm PT spot check.
- Record exact revision, provider version and code hashes in the test receipt.

## Accident follow-up boundary

The implemented `h2physics.release` API distinguishes a solved source/throat state, upstream
stagnation state, isolation/termination, kinetic/static energy and source-plane history.
An arbitrary throat ratio or all-liquid-to-ground diagnostic assumption must not become
a qualified physical solution merely because an object contains the expected fields.

`Lh2dtBulkNozzleOutflow` and `scripts/check_release_integration.py` exercise actual native
mass/energy depletion with the shared equilibrium nozzle. The current native tank deliberately
overrides every negative flow's enthalpy with its homogeneous bulk enthalpy. This is consistent
with the checked bulk outlet, but prevents phase-selective extraction: supplying saturated
vapor or liquid enthalpy in `MassEnergyFlow` does not change native energy removal.

Add an explicit native withdrawal policy while retaining the current bulk default. A selected
liquid/vapor policy must obtain a basis-compatible extraction state from the declared native
provider, use that state's enthalpy for both the differential equation and boundary ledger,
and check phase availability. Do not silently honor an arbitrary foreign enthalpy on all
negative flows. Keep the selection structural/native Python, with no mandatory dependency
on this host library. The local `NozzleResult.upstream_stagnation` supplies the selected
outlet state once this native extension exists; exit static enthalpy is not reservoir energy.

Acceptance adds bulk/liquid/vapor energy differences at the same two-phase reservoir state,
phase-depletion termination under step refinement, compatible reference rejection, exact
agreement of derivative and boundary ledger and an unchanged bulk-mode regression. A
discontinuous isolation command must use one-sided integration windows or properly located
events, rather than letting an RK endpoint sample contaminate the preceding interval.

## Implemented native equipment/property continuation

The current local module also checks the existing `stratified_tank_node` liquid port. That
separate liquid/vapor inventory level already supports phase-specific withdrawal; the
homogeneous bulk-only limitation above remains specific to HomogeneousTank. Do not create
another equivalent phase-resolved tank to address this request.

`Lh2dtLowLevelProperties` now supplies a verified structural subset through one protected
HEOS state and actual native state factories. PT/PH/PS/PU/P-rho/rho-U, saturation and phase
viscosity are exercised, with separate complete-solver comparison. Exact-type constructors
such as the normal-flow operating boundary still need a capability-based provider contract
before they can use that facade. Unsupported methods must not trigger a hidden fallback.
The reference/spin identity and explicit quality endpoint policy/diagnostics must survive
provider selection. See NATIVE_EQUIPMENT.md and `research/native_property_provider.md`.
