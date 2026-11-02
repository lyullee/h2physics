# Supplementary implementation contract for Request032 — evolving-composition finite mixture separator

**Host-side interim capability added 2026-10-30:**
`h2physics.thermo.flash_two_phase_inventory_vu()` solves one fixed-composition
equilibrium V/U state by searching within caller bounds over pressure and vapor
quality using existing CoolProp PQ packets. It enforces component, volume and
energy closure and requires multiple starts to cluster. The bounded resolver is
not a native evolving separator, does not update composition or integrate ports,
and does not replace any requirement below.

**Target owner:** the native LH2DT storage/inventory layer named by
[`requests/032_finite_mixture_separator.md`](../requests/032_finite_mixture_separator.md).
**Local integration points:** `h2physics.adapters.finite_separator`,
`h2physics.adapters.mixture_flash_separator`,
`h2physics.thermo.mixture_phase_partition.MixtureInventoryStateAdmission`, and
the existing native CoolProp mixture phase packet APIs.

## Purpose and ownership

Add an accepted native finite-vessel operation whose evolving state is the
species-resolved component inventory and total internal energy at fixed vessel
volume. At every state evaluation, the receiving owner must flash those current
inventories to equilibrium using its native mixture EOS. It must then use the
resulting *current* liquid/vapor compositions and phase enthalpies in the native
phase-selective port balances.

This is not the existing fixed-composition PH throttle/separation endpoint and
not the pure-fluid `StratifiedTank` operation. Do not add a host SciPy ODE around
repeated CoolProp property calls. Keep equilibrium, phase events, accepted-step
integration and native failure semantics inside the receiving owner. The local
package will audit and compose the returned native receipt; it must not become a
second EOS or vessel solver.

## Proposed Python boundary

The following sketch names the required semantics. It is a protocol, not a
mandate to use these exact identifiers or inheritance structure.

```python
from typing import Protocol, Sequence

class MixtureInventory(Protocol):
    species: tuple[str, ...]                 # fixed declared species order
    component_moles: tuple[float, ...]       # mol, aligned to species
    total_internal_energy_j: float           # J, declared reference
    vessel_volume_m3: float                  # m^3, fixed for this level
    energy_reference_id: str

class NativeMixtureSeparator(Protocol):
    def simulate_inventory(
        self, initial: MixtureInventory, *, start_time_s: float,
        duration_s: float, maximum_step_s: float, clock_id: str,
        ports: "PhasePortSchedule", heat: "HeatSchedule",
        branch_policy: "BranchPolicy", tolerances: "InventoryTolerances",
    ) -> "NativeMixtureSeparatorResult": ...
```

`initial` is an inventory, not an overall mole-fraction state. Species order,
molar masses, basis, volume, absolute energy reference and initial clock must be
immutable for one run. Reject negative/nonfinite component amounts, zero total
inventory, invalid volume, incompatible references, or an undeclared species
order before starting integration.

### Native equilibrium packet

Every native flash used by an accepted state must retain a packet equivalent to:

| Field | Required meaning |
|---|---|
| `species`, `component_moles` | Exact input ordering and inventory used for this flash. |
| `total_internal_energy_j`, `vessel_volume_m3` | Exact flash targets and reference. |
| `pressure_pa`, `temperature_k` | Native equilibrium state on the declared branch. |
| `liquid_component_moles`, `vapor_component_moles` | Species-aligned phase amounts; absent phase is exactly zero. |
| `liquid_mole_fractions`, `vapor_mole_fractions` | Native phase compositions; absent-phase composition is explicitly unavailable, never fabricated. |
| `liquid` / `vapor` properties | Native phase mass, density, enthalpy, internal energy and phase volume where occupied. |
| `phase_state`, `quality` | Explicit single-phase or two-phase result; distinguish mole and mass quality. |
| `component_residuals_mol`, `volume_residual_m3`, `energy_residual_j` | Independently recomputable closures against the exact flash input. |
| `branch_id`, solver diagnostics | Selected root, convergence, iteration/evaluation counts, competing roots or ambiguity flags. |

The native phase packet must satisfy, within caller budgets,
`n_i = n_i,L + n_i,V`, `V = V_L + V_V`, and
`U = U_L + U_V` under one declared EOS energy reference. A solver may return a
single phase at an endpoint. It must not extrapolate the existing gas-only
bounded density/U inverse through a two-phase region.

### Phase port and heat schedules

Use separate liquid and vapor inlet and withdrawal streams. Each inlet retains
its species molar fractions (or exact species molar flow vector), mass/molar
flow basis, native inlet enthalpy, start/stop schedule, clock, identity and
evidence. An inlet's assigned phase is explicit. Each withdrawal declares a
selected current phase, flow basis, schedule and evidence. The native derivative
must derive withdrawn species from the *current flashed phase composition* and
withdrawal enthalpy from that phase's current native enthalpy. A caller-supplied
outlet composition or enthalpy is not allowed to override the native state.

Heat input is a signed schedule into the fluid/wall system. If finite wall storage
is supported, retain its component energy, initial state and boundary terms in
the same native result. Fixed-volume operation has no vessel `p dV` term; any
shaft/electrical work or other energy crossing must be a separately named,
signed boundary term. Do not count fluid-wall exchange as an external heat input
when both inventories are inside the audited boundary.

At each accepted endpoint, the native state update must first conserve each
species and total energy under its accepted interval fluxes, then flash the new
inventory for the next derivative evaluation. This makes selective withdrawal
change the following equilibrium composition. Reflashing the unchanged initial
overall composition is not a valid implementation.

### Phase events, time history and failures

The result should expose Python-native values equivalent to:

```python
class NativeMixtureSeparatorResult(Protocol):
    clock_id: str
    start_time_s: float
    end_time_s: float
    initial_inventory: MixtureInventory
    accepted: Sequence["AcceptedMixtureInventoryPoint"]
    final_inventory: MixtureInventory
    phase_events: Sequence["PhaseEvent"]
    complete: bool
    def require_current(self) -> "NativeMixtureSeparatorResult": ...
```

Each accepted point retains absolute time, exact component/U inventory, the
native flash packet used at that state, integrated inlet/outlet/heat/work terms,
per-component residuals, total mass residual, energy residual, native step
identity and local solver diagnostics. The output clock starts at the caller's
absolute `start_time_s`, is strictly increasing, ends exactly at the requested
endpoint on success, and has no extrapolated samples. Include an explicit
termination reason on incomplete runs.

Phase appearance/disappearance and configured inventory-floor events need native
event localization or a documented exact native endpoint rule. Event records
retain exact clock, event type, before/after phase state, branch identity,
inventory and residuals. Avoid divisions by zero at absent-phase endpoints. If
multiple stable roots or a branch switch cannot be resolved under the caller's
policy, fail closed with diagnostics; do not silently select the first sampled
root.

On failure, preserve the original cause, last native trial, native step/status,
and every accepted point the public solver actually exposes. Mark explicitly
whether an accepted prefix is available. If the native solver only publishes
accepted rows after successful return, report no accepted prefix on exception;
never synthesize one from derivative callbacks or trial states.

## Local adapter integration without another EOS

The receiving result should be adapted once into the existing typed local
boundary. Extend `MixtureInventoryStateAdmission` (or add a narrowly scoped
native-result admission alongside it) to accept the receiving owner's sealed
flash packet through a runtime-checkable protocol. The current class accepts
only a `CoolPropMixtureProperties` fixed-composition provider and therefore
cannot admit evolving-composition packets as-is. Reuse its explicit component,
volume and U residual budgets and issue semantics; do not make it solve the
flash. Preserve the exact receiving provider, branch receipt and packet identity.

Map accepted native rows to the existing `MixturePhasePartition`/
`MixturePhaseAmounts` concepts only where their provider contracts can retain
the true dynamic composition and native phase properties. Do not force a
changing-composition native owner into a frozen `CoolPropMixtureProperties`
instance or weaken provenance checks to accept hand-built values. Extend the
existing finite-separator trace pattern for source-guarded output, absolute
clock, inventory floors, original native rows, and mass/energy audits. Leave
`separate_equilibrium_mixture()` as a single PH throttle endpoint.

An optional downstream handoff may reuse `FiniteSeparatorTrace`-style Python
receipts and the existing component-mass/energy ledgers. Do not alter HyRAM,
SLABx-LH2 or other preferred provider selection as part of this request.

## Exact acceptance ledgers

For each species `i`, define positive `N_in,i` and `N_out,i` as cumulative
component moles crossing the declared vessel boundary. Retain and independently
recompute:

`r_i = n_i,end - n_i,start - N_in,i + N_out,i`.

Also retain total mass from the ordered species molar masses and its independent
boundary residual. This catches species reshuffling hidden by a zero total-mass
residual.

For energy, use one absolute reference and positive-in convention:

`r_U = (U_fluid + U_wall)_end - (U_fluid + U_wall)_start - H_in + H_out - Q_in - W_on`.

`H_in` and `H_out` are native time-integrated stream enthalpies; outflow values
must be evaluated from the currently selected phase at each accepted native
state. Retain heat and work terms separately. The host adapter recomputes every
residual from retained boundary integrals and accepted states and rejects missing
terms, duplicate coverage, reference mismatch, changed arrays, or residuals over
the caller's absolute/relative budgets.

## Parallel acceptance matrix

Implement the listed fixtures as independent verification cases pinned to the
same source revision and native dependency/build receipt. They are independent
jobs and can run concurrently in the authorized HPC campaign; use one native
process per case unless the receiving owner separately proves thread safety.
Record every case result and environment fingerprint. Concurrent execution is a
runtime strategy only: it does not relax the individual acceptance criteria.

| Case | Independent check | Acceptance condition |
|---|---|---|
| Pure-component reduction | One-species limit against the receiving owner's supported pure-fluid equilibrium/stratified level over overlapping states. | Pressure, phase, component inventory, volume and U agree within predeclared dimensional budgets; unsupported two-region details are excluded from the comparison. |
| Single-phase endpoints | Liquid-only and vapor-only inventories, including exact zero amount of the absent phase. | No invalid phase composition/property is fabricated; inventory and energy closures pass. |
| Two-phase flash grid | Declared states on both sides of phase envelope and through the supported two-phase range. | Component, volume and U residuals pass; root and phase-quality identities are retained; no out-of-domain extrapolation. |
| Phase split and lever reconstruction | Compare phase amounts/compositions to an independently evaluated native equilibrium split at fixed overall composition. | Each component's liquid+vapor moles reproduce the exact total; quality basis is explicit; native phase-volume and energy sums close. |
| Selective liquid withdrawal | Withdraw one declared liquid stream while retaining the evolving native liquid composition. | Per-species and total-mass ledgers close; next accepted flash changes composition consistently with removed liquid species. |
| Selective vapor withdrawal | Repeat for vapor withdrawal with a distinct composition. | Same closures pass using vapor composition/enthalpy; liquid values are not substituted. |
| Stream/energy limits | Closed adiabatic no-flow; inlet-only; outlet-only with phase enthalpy; independent heat-only cases. | Zero-flow state is invariant to integration tolerance; all other energy residuals close with signed terms and one reference. |
| Phase event localization | Initial endpoint, phase appearance, phase depletion and a configured inventory floor. | Event time is within declared localization tolerance, event direction and before/after states are correct, and no negative phase amount occurs. |
| Branch ambiguity | Construct a declared multi-root or unresolved branch condition. | Solver rejects or reports ambiguity under the selected branch policy; it never silently extrapolates or selects an undocumented root. |
| Time refinement | Repeat representative transient cases with successively reduced maximum step and event tolerance. | State, event time and integrated component/energy outputs converge under predeclared norms and tolerances. |
| Failure prefix | Force a real failure after at least one accepted native step. | Original cause/trial is retained; accepted prefix is present only if the public solver exposes it, and every reported row is an actual accepted native row. |
| Result integrity | Mutate/reconstruct an issued result, flash packet, provider branch receipt, boundary integral or clock after capture. | Freshness checks reject alteration; values from another run/provider cannot be resealed as this result. |

Do not combine the table into a single success count. Report each case's exact
status, revision, dependency, input fingerprint, output fingerprint and failure
reason. Verification cases establish implementation behavior; they do not
qualify the mixture EOS or validate a real vessel.

## Separate evidence required for validation

The code request does not provide EOS interaction parameters, mixture-specific
calibration, measured finite-separator trajectories, phase-selective outlet
composition/enthalpy observations, wall heat-transfer data or operating
uncertainty. Those remain separately sourced inputs and independent validation
work. Do not fit those values from synthetic fixtures or claim vessel
qualification from algebraic closure, native EOS self-consistency or successful
case execution alone.
