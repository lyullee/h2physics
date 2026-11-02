# Native finite mixture separator inventory and phase-selective withdrawal

## Source capability findings

The reviewed LH2DT `StratifiedTank` already owns pure-fluid liquid/vapor masses,
separate internal energies, wall storage, interface transfer and selective phase
ports. Its `simulate` accepts distinct liquid and vapor stream sequences and
returns native boundary mass/energy integrals. Its `_flow_balance` uses incoming
stream enthalpy and the current selected phase enthalpy on withdrawal. The host
`adapters/finite_separator.py` reuses this supported pure-fluid level.

The homogeneous native tank uses bulk outgoing enthalpy and therefore cannot
stand in for phase-selective separation. The host CoolProp mixture PQ/PH partition
returns native phase compositions, quality and phase-specific thermodynamic packets.
The bounded mixture density/U inverse currently admits a single gas branch; it is
not a total-volume/internal-energy two-phase flash with evolving component stocks.

## Required native Python contract

1. Define total component moles, total internal energy and fixed vessel volume as
   the finite mixture inventory. Keep mass/mole bases and energy reference explicit.
2. Provide a declared-domain native equilibrium flash from that inventory, retaining
   pressure/T, phase amounts, separate native compositions and phase-specific U/H,
   volume and component closure, solver diagnostics and root/branch identity.
3. Admit phase disappearance/appearance with explicit endpoint handling and native
   conservation. Do not extrapolate gas-only density/U roots through VLE regions.
4. Supply separate liquid/vapor inlet and withdrawal ports. Inflows retain their
   actual compositions/enthalpies; outflows use the selected current phase's native
   composition/enthalpy. No unchanged-total-composition second flash is admissible.
5. Reuse an existing native finite inventory integrator with heat/wall accounting,
   accepted state/time history and phase/depletion events. Preserve original native
   solver results and failed trial/accepted prefix; avoid a second host reactor ODE.
6. Expose direct Python inputs/results so the existing source, receiver, equipment
   and utility contracts can bind the native owner without a service/JSON layer.

## Deferred acceptance requirements

Check pure-fluid reduction against the supported native stratified/equilibrium
levels, phase-volume/component/U closure, lever-rule phase splits, selective
withdrawal component balances, enthalpy transport, adiabatic/zero-flow limits,
phase appearance/depletion, branch ambiguity rejection and time/space refinement.
Qualified mixture EOS parameters and actual separator observations remain separate
evidence requirements. No local scientific calculation was performed for this request.

## Current host-side seam status

`MixturePhasePartition` now accounts component-selective withdrawals from the exact
retained native phase compositions, validates directly constructed receipts against
those compositions and phase enthalpies, and supports q=0/q=1 endpoints by requiring
zero inventory/withdrawal in the absent phase. Its withdrawal receipt also exposes
per-component and per-phase outlet masses and phase enthalpy exports from the native
J/kg values, returning an explicit unavailable energy if a nonzero withdrawn phase
lacks an enthalpy. `MixturePhaseAmounts` now exposes one-packet phase volume and
internal energy from native phase density/enthalpy and common pressure; occupied
phases with missing properties fail closed. The deferred phase-partition contract
records these values. `MixtureInventoryStateAdmission` now accepts a native phase
packet only when it closes caller-declared species moles, fixed vessel volume and
total U within explicit budgets, retaining the exact provider object and sealed
source/branch result. It is an
admission seam only: it does not solve the target flash, detect phase events or
integrate accepted separator states. Those remain receiving-owner changes. The
new deferred admission contract has not run.

The host also exposes `thermo.flash_two_phase_inventory_vu()` as a bounded
single-state helper. For a fixed-composition provider it searches pressure and
vapor mole quality against caller-supplied component moles, fixed vessel volume
and total internal energy, using the existing native CoolProp PQ packet and the
admission above. Multiple in-domain seeds must converge to one clustered root.
This adds a reusable equilibrium-state calculation, but it does not support a
composition-changing state provider, evolve port/heat balances, retain a vessel
history, or locate phase events. It does not close the required native finite-
inventory integration contract.

The finite equilibrium-throttle result now retains the component-mass and total
enthalpy acceptance budgets. Its constructor recomputes component and phase-energy
residuals from the exact retained native partition and amount packet, and consumes
a one-time issuer token from the completed separation operation so a cloned
result cannot reseal altered summary values. The related deferred contract is
authored but remains unexecuted. This integrity guard does not provide the
changing-composition vessel flash or phase-event solver requested above.

## Receiving integration boundary

No current host-side integration is an acceptable substitute for the requested
native accepted-state solver. The current `MixtureInventoryStateAdmission`
validates one provider-issued equilibrium packet against declared total component
moles, vessel volume and total internal energy. It does not produce that packet
from the evolving vessel state. `separate_equilibrium_mixture()` performs a
single fixed-composition PH throttle and finite split; it is a valve/separator
endpoint calculation, not a vessel trajectory. `run_finite_pure_fluid_separator()`
reuses `StratifiedTank` accepted states and phase ports, but its bridge and state
are single-fluid Hydrogen/ParaHydrogen/OrthoHydrogen and cannot accept a changing
multi-component composition. Do not connect a host ODE to these property calls
and describe the result as native integration.

The receiving owner must expose a native evolving mixture state whose primary
inventory is a species-ordered component-mole vector plus total fluid internal
energy at fixed vessel volume. At every native derivative/state evaluation, its
own equilibrium provider must flash those current component amounts and energy,
and retain pressure, temperature, liquid/vapor component amounts and compositions,
phase properties and branch diagnostics. The provider cannot be the existing
`CoolPropMixtureProperties` fixed-overall-composition object unless its native
backend itself gains a state-composition input and returns the corresponding
phase packet for that input.

The minimum accepted-result seam is an original native run with an initial
state, ordered accepted `(time, state, phase_packet, step)` records, final state,
and owner-issued currentness check. Each accepted record must retain the exact
component/U inventory used for its flash, its native phase amounts/compositions,
port ledgers and diagnostics. The wrapper may independently audit these retained
rows; it must not regenerate accepted rows by replaying host-side `state_pt`,
`state_ph` or fixed-composition inverse calls. Native integration exceptions
must preserve the original cause, last native trial and any accepted prefix the
native public solver actually exposes; never invent an accepted prefix from trial
callbacks.

The phase-port API must be given to the native owner as separate liquid and vapor
inlet/withdrawal schedules. Inlet phase composition and enthalpy come from each
actual stream. Outflow component rates and enthalpy use the current flashed phase
composition and phase enthalpy inside the native derivative. The native step
must update component amounts and total energy before its next equilibrium flash,
so a withdrawal changes the following composition. Phase appearance/depletion
and branch changes require native event handling or explicit native endpoint
rules. Host-side phase partition, mixture inverse grids, and post-run packet
admission remain useful checks around this owner, but cannot own its state
integration or event localization.

## Current implementation increment

`h2physics.thermo.run_finite_mixture_vu_intervals()` now provides a first
executable finite-volume trajectory owner for caller-supplied finite intervals.
It issues a new immutable CoolProp mixture provider for each changed composition,
uses the existing bounded V/U flash at every accepted endpoint, accounts for
species-resolved inlets and phase-selective liquid/vapor withdrawals, and updates
total U from supplied integrated inlet enthalpy, outlet phase enthalpy, heat and
work. `FiniteMixtureVesselRun.require_current()` rechecks every accepted flash,
composition change and interval/cumulative balance. Public types and usage are
documented in `docs/FINITE_MIXTURE_INVENTORY.md`; the deferred contract is
`finite-mixture-vu-accepted-steps`.

This is explicit first-order interval marching with CoolProp as the native
equilibrium/property backend. It is not an external native adaptive integrator,
does not solve a continuous rate ODE, does not retain an unavailable external
solver's trial/failure prefix, and requires the caller to choose and refine
interval endpoints. The current branch is restricted to bounded two-phase
states. Phase events, wall heat capacity, automatic refinement, measured stream
boundaries and independent separator comparisons remain open. Therefore this
increment does not close every item in this request. Its contract is source-only
and awaits the configured Hangang replay.

## Adaptive host-integration increment

`h2physics.thermo.run_mixture_vessel_ode()` adds a separate SciPy `solve_ivp`
host-side route for continuous caller-supplied boundary-rate callbacks. It builds
a new fixed-composition CoolProp provider at each RHS trial, flashes the current
component/U state, integrates species and first-law ledgers, and localizes a
positive component floor plus caller-selected interior vapor-quality thresholds.
The result retains the accepted solver mesh, each composition-specific flash and
solver diagnostics. RHS/property failure retains the last trial plus only the
accepted prefix exposed by completed solve calls; hidden internal steps from a
failing callback are not fabricated.

This provides an adaptive host model level, not the receiving equipment's native
integrator requested above. SciPy owns the adaptive state progression, while
CoolProp owns thermodynamic properties and equilibrium. It remains bounded to the
declared two-phase flash domain; outside-domain branch switching, wall dynamics,
event behavior beyond the declared thresholds, and independent separator
qualification remain open. The deferred cases
`finite-mixture-ode-continuous-feed`,
`finite-mixture-ode-no-transfer-invariance`, and
`finite-mixture-ode-quality-event-localization` are source-only and await cluster
execution. The existing finite-interval runner remains available when callers
own the step endpoints and integrated transfer data.
