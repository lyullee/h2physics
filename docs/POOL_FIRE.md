# Finite LH2 stock and supplied-geometry pool fire

Deposited-stock pool continuations expose `continuation.fire_seed(...)`, backed by
`PoolFireSeed.from_deposited_pool`. Supply `evidence_id`,
`ignition_transition_evidence_id`, `temperature_absolute_tolerance_k` and
`density_relative_tolerance`. This transfers the exact final unburned native stock,
fixed footprint, absolute endpoint, original saturated liquid/vapor states and
preignition evaporation source. It retains the original continuation as its parent.
The fire owner rechecks that parent before evaluating fire stages. Native endpoint
temperature and density must match the declared saturated fuel within the supplied
budgets. The admitted normal-hydrogen/spin/reference identity is preserved.

Ignition timing, burning flux, oxygen supply, flame geometry and conditioning heat
remain explicit inputs to the existing fire owner. The pool-to-fire transition
evidence declares the change of physical model; it does not establish continued
substrate heat or predict ignition. Preignition vapor is not burned again as pool
stock. This new handoff and its parent-mutation contract are authored but unexecuted.

Status: **implemented_unverified**. This increment was authored under the
2026-10-28 instruction to defer scientific execution until Nurion validation.
No local native run, pytest, replay, benchmark or experiment comparison was
performed for it. The eight future cases are definitions, not passes.

`h2physics.adapters.pool_fire.FinitePoolFire` composes the actual optional
Process Risk Consequence Toolkit (PRCT) 0.1.0 `fire.pool`, `fire.sphere` and
`fire.solid_flame` objects with the existing finite stoichiometric reaction
core. It consumes an explicitly established, fixed-area normal-LH2 stock,
conditions the consumed H2 to a declared gas/LHV reference, consumes a finite
O2 inventory, and retains native finite-consumption and radiation results.
Burning flux, flame geometry, radiation fraction and convective-export
fraction require caller evidence; the adapter supplies no H2 correlation or
default qualified value.

## Python composition

The API takes Python objects directly:

1. Load `PoolFireNative.from_installed()` from the reviewed optional PRCT
   installation. The existing risk dependency receipt/loader is reused; risk
   aggregation is not invoked. Native source and function/code/class bindings
   are checked before and after stages. Importing this adapter does not import
   the optional package or calculate fire physics.
2. Supply a `PoolFireSeed` with finite mass (kg), fixed area (m2), absolute
   clock (s), common coordinate frame/location (m), actual saturated liquid
   and vapor `ThermoState` objects and their thermodynamic owner. Only normal
   `Hydrogen`, one compatible `PropertyBasis`, equal absolute pressure and
   saturation temperature, liquid quality zero and vapor quality one are
   admitted. The gasification enthalpy must be positive.
3. Supply `H2CombustionReference`: an evidenced LHV (J/kg), normal-H2 gas state
   on that same pressure/reference, oxidizer-reference evidence, water-vapor
   product phase and explicit complete-combustion efficiency of one. The shared
   `StoichiometricReaction` must be neutral H2(g) + 0.5 O2(g) -> H2O(vapor),
   with self-consistent elemental and molar-mass bases. Initial O2 and optional
   water amounts are finite molar stocks.
4. Declare `DeclaredIgnition`, a finite `ExternalConditioningBudget` (J and W),
   contiguous `PoolFireStage` objects and facing `GroundVerticalReceptor`
   objects. Ignition, seed, stage and conditioning clocks meet exactly. All
   stages carry explicit net H2 consumption flux (kg/m2/s), supplied sphere
   diameter (m), energy fractions and evidence/origin IDs.
5. Call `model.run(...)`. `PoolFireTrace.steps` retains each native input,
   native result, shared `ReactionConversion`, phase/energy audit and receptor
   calculation. `PoolFireError` retains the original cause, actual model,
   failed stage, completed prefix, attempted native objects/results and any
   assembled failing step. No fallback flux or geometry is substituted.

`PoolFireTrace.require_current()` checks the original one-use result owner,
native provider bindings, finite reactant-source record, retained stage ledgers,
receptor radiation outputs, and the declared unverified scope flags. The pool-fire
to thermal-target adapter performs this check before and after extracting a
receptor history, and the target response rechecks the retained trace before
exposing its result. Copying the trace cannot reseal modified output. This is
integrity protection for stored results, not additional physical validation.

The authored [example](../examples/pool_fire.py) defines a model and schedule.
Its numbers are synthetic numerical fixtures, including its LHV scale; they
are not recommended hydrogen design parameters. No native calculation occurs
at module import. The example has not been executed.

## Finite mass, phase and energy boundaries

PRCT owns the finite constant-area, constant-flux consumption calculation for
each stage. Native active duration ends when the supplied stage window or
remaining fuel stock ends. Native active HRR is retained separately from
interval-average output. The host audits the native mass ledger, active-rate
integral, LHV energy integral and HRR-duration energy integral. It never copies
the native consumption or radiation implementations.

Each native-consumed kilogram is gasified, conditioned and fully combusted.
It is not also added to an unburned atmospheric release. The shared reaction
core enforces finite O2 availability and element/mass conservation; an
unavailable O2 stock fails the proposed stage. The host does not silently
limit the H2 flux and change the supplied native burning law. Complete
combustion is the only supported chemical fate. No finite-rate reaction,
entrainment, oxygen-delivery or flame-extinction prediction is implied.

On the common native enthalpy reference, required external phase and sensible
conditioning are recorded separately:

\[
Q_{latent}=m_b(h_{v,sat}-h_{l,sat}),\qquad
Q_{sensible}=m_b(h_{H2,ref}-h_{v,sat}).
\]

Both their accumulated energy and active-rate power must fit the declared
finite external conditioning budget. Cooling/recondensation reference paths
are rejected. This budget is an explicitly prescribed external heat boundary,
not a solved fire-to-pool heat-transfer mechanism or an inferred ambient heat
source. Latent heat is not deducted a second time from the LHV. LHV is declared
for the conditioned fuel/oxidizer reference and vapor water; product sensible
enthalpies, product temperature and a whole-system internal-energy invariant
are not solved. These are constant-pressure enthalpy transfers, not a claim
of closed pool/flame total-U conservation.

Native released chemical energy is allocated into caller-supplied radiation
and convective-export fractions. Their sum cannot exceed one. The remainder
is explicitly `unallocated_release_j`; it is not lost or silently assigned to
a wall/pool. `convective_export_j` denotes the declared hot-product/near-flame
energy boundary. It is **not** a receptor convective heat flux. The receptor
field `convective_flux_w_m2` remains `None`.

`fuel_to_flame` is an `IntervalMassSource` for the conditioned **reactant feed**
into the flame. It is not an admissible unburned dispersion source. Its finite
edges contain the native burnout time and a zero-rate tail where appropriate;
the source API forbids extrapolation. A zero prescribed flux is supported as
an imposed zero-consumption stage; thermal extinction/reignition is not solved.
Absolute-clock rounding that would destroy the active interval is rejected.

## Geometry and receptor radiation

The total radiant active power and supplied uniform sphere area determine its
surface emissive power. The actual native restricted sphere calculation then
owns view factor and incident flux; the actual native solid-flame call audits
the same supplied emissive power, native factor and transmissivity. Exposure
is incident flux times the native active duration (J/m2).

The only supported native geometry is a ground-tangent sphere with an outside,
ground-level, source-facing vertical receptor. Horizontal distance must exceed
the sphere radius. Source and receptor use one Cartesian frame whose third
axis is vertical; they share the ground elevation. Arbitrary receptor height,
orientation, occlusion, lifted flame, wind tilt, flame height/diameter
correlation, smoke or atmospheric-absorption prediction is unavailable.
Transmissivity and sphere diameter are evidenced caller inputs. The sphere
is a supplied geometry proxy, not a solved hydrogen flame shape. The existing
failed jet-flame level is unchanged.

## Existing native LH2 pool handoff

`PoolFireSeed.from_native_pool(run, evidence_id=...)` accepts only the original
admissible `NativePoolRun` with a final zero liquid-inflow rate. It transfers
the final liquid mass, area, time and phase states. The original actual pool
result and its complete preignition `IntervalMassSource` remain attached;
the source contents are fingerprinted and guarded. Earlier evaporated fuel is
not counted again as burning liquid.

The preignition pool solver stops at this handoff. Postignition area is held
fixed. There is no restart of its radial fields, continuing replenishment,
background evaporation, fire feedback, boiling-regime prediction or coupled
pool/flame dynamics. The deferred native-handoff case can fail at the original
native pool admission gates; this new layer cannot promote a rejected pool.

## Deferred validation and evidence

[`validation/cases/pool_fire.py`](../validation/cases/pool_fire.py) exposes eight
metadata-only cases under profile `pool-fire`: finite burnout and mass/energy
ledgers, native geometry/transmission limits, stage subdivision, unavailable
conditioning heat, finite O2 rejection, unsupported receptor geometry,
completed-prefix failure retention, and actual preignition native-pool handoff.
The common `ValidationCase`/`ValidationOutcome` API runs their entrypoints only
when a future validation worker invokes them. No cluster job was submitted.

Verification and hydrogen apparatus/field validation remain open. In
particular, none of the synthetic input labels constitutes evidence for H2
burning flux, radiation partition, flame geometry, incident exposure or a full
cryogenic accident chain. This level reports `implemented_unverified` and does
not increase executed/validated coverage.

## Sources and reuse

The separately installed [PRCT repository](https://github.com/lyullee/process-risk-consequence-toolkit)
provides the Apache-2.0 native calls. The existing
[`risk_dependency.toml`](../research/risk_dependency.toml) pins the 0.1.0 wheel,
source aggregate and reviewed notices; no native implementation or third-party
table is redistributed by this increment.

[NOAA Technical Memorandum NOS OR&R 43 (2013)](https://response.restoration.noaa.gov/sites/default/files/ALOHA_Tech_Doc.pdf)
sections 6.1 and 6.3 describe the underlying supplied solid-flame radiation and
geometric factor approach. This supports the radiation form and geometric
boundary; it does not establish hydrogen-specific empirical burning or
radiation parameters. Native pool-energy is a finite conservation primitive
with supplied consumption rate, not NOAA's complete pool-fire model. Existing
CoolProp normal-H2 states are reused through the shared property provider;
its [hydrogen EOS source](https://doi.org/10.1063/1.3160306) and
[native API](https://coolprop.org/coolprop/LowLevelAPI.html) retain their existing
phase/reference ownership.

For deposited-stock continuation, the fire seed admits the exact original final
mass, area, state, location and clock and rechecks its parent receipt. Native pool
temperature and density must be finite positive values, within the caller's
transition budgets, and the pool's ambient pressure must match the retained
saturated fuel pressure. Fire-owner configuration also binds seed evidence, origin
and original thermodynamic/preignition source identities. These admission checks
do not supply postignition pool heat feedback or a shared impact-wall thermal model.

`adapters.pool_energy_ledger.bind_native_pool_energy_ledger()` now defines the host
acceptance interface for a future native cumulative energy extension. It binds the
energy reference to the original deposited-state property basis and requires the
normal-hydrogen vapor phase identity before considering a ledger. It accepts
only native accepted-edge internal energy, inlet/outlet enthalpy, integrated heat,
pressure-volume work, pressure/volume state and heat-allocation fields. It checks
per-edge liquid mass/energy closure and, for an explicitly selected finite-wall
mode, the wall energy balance. Callers supply positive mass and energy residual
budgets; both are retained and rechecked. Prescribed semi-infinite substrate mode is labelled
as an external reservoir and cannot report a finite substrate U. Direct construction
captures the native accepted-edge energy fields in the receipt and rechecks them;
it cannot establish a ledger detached from those retained values. The currently
reviewed pool result does not expose these cumulative energy fields, so the adapter
raises `PoolEnergyCapabilityError`; it never integrates sparse heat flux at the host
layer. Request033 remains open for the native accepted-clock implementation and
dryout allocation rules. The host boundary also requires unapplied, dry-surface and
heat-cap rejection diagnostics to start at zero and remain nonnegative and
nondecreasing across accepted edges; these cumulative allocation fields are not
available from the current native result.
The complete Request033 receiving result contract and varied case matrix are in
[`integration_request_033.md`](../research/integration_request_033.md).
The accepted-edge record and balance-audit API is described in
[`POOL_ENERGY_NATIVE_CONTRACT.md`](POOL_ENERGY_NATIVE_CONTRACT.md). It does not
replace the absent native integrals or make the existing DynamicLH2PoolX result
bindable.

The exhaustive liquid-accident mass ledger is issued through its binding factory.
Direct construction rejects unissued branch totals before they can be consumed;
the deferred `liquid-accident-exhaustive-mass-ledger` contract covers this admission
and detached-copy rejection. Execution remains pending.

`liquid_accident_energy_diagnostics()` can now retain an optional
`PoolEnergyLedger` only when it belongs to the exact original pool continuation in
the exhaustive accident mass ledger. It keeps the pool control-volume receipt
separate from flash, flight and impact stage terms; it does not add their residuals
or mark global accident energy closed. Without a native pool energy ledger, both
pool energy terms remain explicitly unresolved. The deferred pairing contract
requires a project fixture backed by the eventual accepted-edge native fields.
Energy diagnostic receipts are issued only by this Python builder; direct
construction and copied receipts are rejected before stage-energy values are used.


## Trace issuer integrity

PoolFireTrace now uses an opaque one-use token minted inline only after the finite
pool-fire run has completed its accepted-step and energy audits. The former private
issuer class/factory could be imported and invoked to attach a self-created owner
object to a fabricated trace. The existing pool-fire baseline contract now rejects
a caller-created issuer token in addition to clone and freshness violations.

## Pool-fire receiver radiation to radial wall

`run_pool_fire_radial_wall()` connects one existing finite `PoolFireTrace` receptor history to the shared radiation-to-radial-wall core and the existing radial cylinder heat solver. It retains the selected receptor, source clock/frame and original fire owner. A caller-supplied dimensionless surface projection factor maps the modeled receptor-plane flux onto the wall; the factor has a required evidence ID. Caller material/geometry, absorptivity, inner boundary and circumferential-uniformity evidence remain explicit. The deferred contract is `pool-fire-radial-wall-handoff` in the existing Hangang `pool-fire` profile.

This path adds no pool-fire, view-factor, wall-conduction, fire-to-wall obstruction or equipment damage algorithm. The receptor-to-cylinder mapping is an application assumption and must be supported for the scenario; this wrapper does not infer a cylinder view factor from the receptor's planar radiation result.
