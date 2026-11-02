# Conditional finite surface impact — coding only

Status: **implemented_unverified**. The adapter, example and ten deferred cases
have not been executed. Hangang is the active target for their scientific
execution; this document makes no physical-validation claim.

`h2physics.adapters.droplet_impact.FiniteSurfaceImpact` accepts original
`ParcelTrace` objects ending in `incident_ground_crossing`. It verifies the
last state against the retained native SciPy event/result and rechecks its
normal-H2 saturation states using the actual property provider. An incident
parcel is not labelled deposited merely because it crosses the ground plane.

The new physical calculation couples finite patch heat capacity, passive
collision/recoil, grounding impulse, phase enthalpy and an evidenced lumped
contact conductance. It solves the evaporated mass and resulting finite wall
temperature. It supplies no universal LH2 deposition/rebound, splash, wetting,
Leidenfrost, contact-time or heat-transfer correlation. Those coefficients and
their pressure/temperature/diameter/normal-speed/impact-Weber bounds are an
explicit `QualifiedImpactClosure`. Synthetic evidence is accepted as a labelled
reference calculation; an evidence ID alone does not establish experimental
qualification.

## Python contract

Supply an actual native saturation provider, a `SurfacePatch` and a
`QualifiedImpactClosure`, then call `model.run((incident_trace, ...))`.

- `SurfacePatch` declares effective recoil mass (kg), finite thermal capacity
  (J/K), initial/material temperature bounds (K), a finite horizontal radius
  (m), position, Cartesian z-up frame and initial-state clock coordinate. No
  incident can precede that state. A fixed-mount arrest, isolated
  intervals and dry-patch clearing into a separate at-rest receiver each need
  evidence. The original material owner is retained.
- `ImpactQualification` defines the admitted domain and evidence for lumped
  capacity, negligible external work during the impulsive event, and local
  saturation equilibrium. Initial, mechanically heated and final patch
  temperatures remain in the admitted domain.
- `ImpactOutcome` returns the deposition fraction of **remaining liquid**,
  normal restitution and tangential retention, vapor velocity relative to the
  intermediate recoil, total contact conductance (W/K), maximum contact time
  (s), signed interfacial internal-energy change (J), original result and
  evidence/origin. No coefficient has a built-in production value.
- `ImpactStep` retains original incident trace/context, actual native phase
  states, original outcome, all phase-root trials, generic SciPy root result
  where used, recoil/arrest/phase ledgers and an at-rest `DepositedBatch`.
  `SurfaceImpactError` preserves the original cause, completed prefix, original
  incident, context/outcome, trials and assembled failing step where available.

All states use kg, m, s, K, Pa absolute and a single explicit native energy/spin
basis. Only pure normal `Hydrogen` is admitted for the existing native pool
handoff. No pressure, phase or spin conversion is inferred. The original
flight mass/energy/momentum residuals must fit explicit admission budgets.

## Coupled mechanics and finite heat

For incident mass m and solved vapor mass x, the supplied deposition fraction
d gives deposited mass d(m-x) and rebound liquid (1-d)(m-x). The velocity
closure defines rebound velocity relative to intermediate patch recoil using
the incident normal/tangential components. Linear momentum determines that
finite recoil. The vapor has its explicitly supplied recoil-relative velocity.
Both outgoing streams must point away from the horizontal solid.

The fixed mount then arrests the finite patch and deposited liquid. Its
received impulse is recorded. Mount velocity and work are zero under this
declared rigid-mount closure; finite recoil kinetic energy is dissipated into
the finite patch. Collision dissipation and arrest dissipation are retained
separately. The closure cannot demand unprovided active mechanical work beyond
the declared numerical energy budget. Signed interfacial internal-energy
change is counted explicitly; contact angle or an unknown wetting energy is
not silently treated as evidence for it.

Let D(x) denote the resulting mechanical heat deposited into the patch and C
its finite thermal capacity. Its temperature before phase contact is
T*=T_initial+D(x)/C. During the declared contact, lumped finite-G exchange to
saturated H2 obeys C dT/dt=-G(T-T_sat). While liquid remains, the phase root is

\[
x(h_v-h_l)=C(T^*-T_{sat})[1-\exp(-G\tau/C)].
\]

Coefficients are held during this lumped event; a generic bracketed SciPy root
solves x. No second EOS, boiling coefficient table or copied impact solver is
introduced. The [native saturation provider](https://coolprop.org/coolprop/HighLevelAPI.html)
owns h, u, density and phase endpoints. The lumped solution follows a finite
capacity energy balance, with its spatial-uniformity assumption stated in
[MIT's transient heat-transfer notes](https://web.mit.edu/16.unified/www/FALL/thermodynamics/notes/node129.html).

If the contact could evaporate all incident mass, dryout is localized from
the same finite-capacity exponential. It stops heat transfer at x=m and ends
the contact at that earlier time. This is a physical finite-inventory bound,
not clipping an infeasible requested vapor fraction. Zero conductance gives
zero phase transfer. A surface initially below saturation is rejected: liquid
subcooling, freezing or condensation would require another admitted model.
There is no external heat refill between contacts. Surface temperature
carries forward; cleared deposited batches remain separate finite inventories.

## Energy and momentum ledger

The complete material set includes final deposited/rebound liquid and formed
vapor. Fluid stored energy uses native **internal energy**. Ambient pressure
work into the expanding fluid is explicitly

\[
W_{p,in}=-P x(1/\rho_v-1/\rho_l).
\]

The audited total-U change includes the finite patch, fluid phase change,
outgoing minus incident kinetic energy and interfacial energy, then subtracts
this pressure work. It is not a heat-only latent ledger. Linear momentum
includes the separately recorded impulse delivered to the fixed mount.
Gravity/support work, capillary deformation history and the intermediate
mechanical trajectory are excluded by the qualified impulsive/lumped-event
assumptions; contact time is not a resolved mechanical flight path.

The rebound and vapor are finite outgoing packets with retained mass, state,
velocity and event time. They are not complete atmospheric source histories;
neither a pulse width nor a dispersion plane is invented. A follow-up flight
model needs its own launch definition. Contact windows cannot overlap, and
absolute clock coordinates must resolve the finite contact/dryout duration.

## Sequential population history

`impact_population_sequence(population, impact_owner)` feeds original,
owner-issued unit-parcel ground-crossing traces to one finite-surface owner in
event-time order. Groups with represented multiplicity greater than one and
equal-time events are rejected because this API has neither parcel replication
nor simultaneous-impact mechanics. The result retains the population, impact
owner, event order and native impact trace; its ledger and issued steps are
rechecked before use. This does not create a deposition correlation or a pool
evolution model. See `PARCEL_POPULATION_IMPACT_SEQUENCE.md`.

## Existing native pool boundary

`prepare_native_fixed_area_pool(step, native_config, impact_owner=model, ...)` constructs actual
DynamicLH2PoolX 0.2.0rc2 initial-stock objects, zero continuing native inflow and
retains its native runner. It does not execute that runner. The original
deposited batch is saturated, stationary and available at contact completion;
initial stock is exactly that batch mass. Native API source hashes and original
function/class origins are checked.

The actual impact owner must recognize the exact accepted step object. At
acceptance it retains an immutable binding of its physical summaries, phase
states, batch fields and original native incident arrays. Changed summaries
or `dataclasses.replace` clones cannot initialize unrelated stock; handoff
checks them before accessing the optional native pool. This preserves accepted
result correspondence, not an independent experimental verification or a
security boundary against deliberate private-state tampering. The returned
initialization retains the actual impact owner and original step as well.

The spreading native route currently rejects nonzero initial liquid inventory.
The adapter therefore does not smear an impact event into an invented finite
arrival interval. The native fixed-area route admits initial inventory. Its
substrate heat law is a **separate explicitly owned continuation boundary**;
it cannot silently reset or stand in for this finite patch. The returned flag
`finite_patch_thermal_continuation_solved` is false. A simultaneous native
spreading/finite-patch thermal restart remains a receiving capability gap.

No postimpact footprint growth, wet-pool impact, splashing/secondary droplet
distribution, gas back-reaction, air condensation, RPT, combustion or ignition
is predicted. The public
[impact-regime research](https://arxiv.org/abs/1111.0435) illustrates the need
to distinguish contact and film-boiling regimes; no coefficients or regimes
from other liquids are applied to LH2 here.

## Deferred validation

The [example](../examples/droplet_impact.py) authors unqualified numerical
parameters and invokes actual parcel flight only inside explicitly called
functions. The [case catalog](../validation/cases/droplet_impact.py) defines
ten metadata-only cases under profile `droplet-impact`: coupled finite
wall/phase conservation, independent elastic two-body limit, zero conductance,
finite dryout, flight/root refinement, missing heat, failed-prefix retention,
integrated intercontact heat/global wall-energy accounting, issued aggregate-history
integrity, and actual native fixed-area initial inventory plus separate pool mass balance.
None has been run. Their native compatibility, root budgets and physical
acceptance remain pending; no measured H2 validation or executed coverage is
claimed.
