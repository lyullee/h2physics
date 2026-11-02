# Saturated parcel transport — coding only

Population admission retains full original flight heat, momentum, mass and native
array contents through a content fingerprint. Per-group mass closure and strictly
increasing accepted times are checked independently, and changed launch options or
population declarations during a callback reject. Deposited-pool continuation uses
content fingerprints rather than truncated native object representations. The new
integrity contracts remain deferred; no execution is implied.

`h2physics.adapters.droplet_transport.SaturatedParcelFlight` couples native
CoolProp saturated liquid/vapor states, `fluids.drag.drag_sphere` and SciPy
`solve_ivp`. This new module has not been executed. Two authored reference
cases are staged for a later cluster campaign. The existing `thermo` and
`hydraulics` extras provide CoolProp and fluids; SciPy is a core dependency.
No dependency is imported or model run merely by reading the case metadata.

Supply a property provider, pressure, a `ParcelBoundary` and a callable returning
`BoilingHeat`. The heat closure owns its applicability and original evidence.
There is no built-in atmospheric hydrogen evaporation correlation: air phase
change near cryogenic liquid must first have a qualified closure. Surface
tension and the spherical-drop Weber, Reynolds and neglected Laplace-pressure
budgets are explicit inputs. The fixed carrier field needs dilute, isolated,
heavy-particle force qualification; it is not depleted by the parcel.

The liquid remains saturated at one pressure. Heat creates vapor using the
native phase enthalpy difference. Isotropic escaping vapor carries the parcel
velocity; drag and gravity accelerate the remaining mass. The solver integrates
vapor mass, heat, drag work, vapor enthalpy/kinetic/gravitational energy,
vapor momentum and external impulse alongside position, velocity and mass.
Stored energy uses liquid internal energy plus kinetic and gravitational energy.
Ambient pressure work into the shrinking parcel is recorded as `-P*DeltaV`;
escaping vapor carries enthalpy plus kinetic and gravitational energy. Thus the
energy residual explicitly subtracts heat, drag work and ambient pressure work
from the stored-energy change plus outgoing vapor energy. Final mass,
total-energy and momentum residuals are reported. Native solver
objects and original heat results remain available, including internal trial
evaluations; trial evaluations must not be mistaken for accepted time histories.
Owner boundary, phase states, latent heat, pressure, provider and heat callback
are bound at run start. Mutation during a callback rejects the run with its
original evidence rather than relabeling mixed-input results.

`ParcelTrace` is issued only by a completed `SaturatedParcelFlight.run()` through
a one-use token. `require_current()` fingerprints the original boundary, accepted
and trial records, SciPy state/event arrays, and every mass/energy/momentum output;
it also reconstructs summaries from the retained native solution before population
or finite-impact consumers admit the trace. Direct construction, token replay and
post-issuance summary/native-array changes are rejected. The existing deferred
`droplet-transport` cases cover those receipt boundaries; this does not add a new
physical model or case.

`run` requires explicit interval, initial state, positive residual mass floor,
maximum step and numerical tolerances. The 17 absolute tolerances correspond to
position (3), velocity (3), liquid mass, vapor mass, heat, drag work, vapor total
energy, vapor momentum (3), external impulse (3).
Units follow these quantities in SI; consumers should use the named trace fields.

An optional horizontal plane stops downward flight. The remaining mass is
**incident liquid**, not a deposited pool source. No splash/deposition fraction,
surface vaporization, rebound or surface heat is inferred. A positive mass-floor
event retains its liquid; it does not claim complete evaporation. Inadmissible
native solver trials fail with their original cause and prior trial records;
there is no hidden negative-mass clipping or solver fallback.

Initial flashing, subcooled heating, deformation/breakup, multiple interacting
drops, air condensation, changing pressure and spin conversion remain open.
The catalog family therefore remains a partial, unverified implementation.

## Initial equilibrium flash handoff

`flash_initial_liquid_release(properties, upstream_state, *,
downstream_pressure_pa, total_release_mass_kg,
phase_equilibrium_evidence_id)` uses the existing provider's `state_ph` and saturated
endpoints to partition a finite upstream liquid release after a caller-declared
isenthalpic pressure drop. The returned `ParcelInitialFlash` records the upstream and
downstream states, equilibrium quality, saturated endpoint states, flash-vapor mass,
remaining liquid mass, and mass/enthalpy residuals. Pass
`flash.launch_liquid_mass_kg` as the initial mass to `SaturatedParcelFlight.run` when
the premise applies. It refuses a downstream state outside an explicitly resolved
two-phase region and requires evidence for the instantaneous equilibrium-throttle
assumption. This is an initial partition only: no flashing jet, phase slip, flash-vapor
momentum, aerosol yield, droplet-size distribution or deposition is inferred.
The deferred `parcel-initial-flash` contract covers pure-fluid PH quality, mass and
endpoint-enthalpy closure and the single-phase/evidence gates; it has not run.

Initial flash admission additionally requires an upstream liquid state and a strictly
lower downstream pressure. The native PH result must reproduce upstream enthalpy,
and the quality-weighted saturated endpoint enthalpy must close the partition.
The authored hydrogen reference uses 0.8 MPa upstream saturation; no scientific
execution of that reference is claimed.

## Finite vapor-source handoff

`h2physics.adapters.vapor_source_from_parcel_trace` can expose accepted
evaporation increments through `IntervalMassSource`, allowing direct use of
existing finite-source consumers. It does not add another vapor-generation
law. Since the parcel trajectory is moving but the source contract has a fixed
location, callers must explicitly document the spatial aggregation represented
by that location. See [PARCEL_VAPOR_SOURCE_HANDOFF.md](PARCEL_VAPOR_SOURCE_HANDOFF.md)
for the typed API and limits. The deferred
`parcel-vapor-interval-source-handoff` Hangang case checks bin mass identity
and freshness only; no calculation has been run for it.

Native API references: [fluids sphere drag](https://fluids.readthedocs.io/fluids.drag.html),
[CoolProp low-level API](https://coolprop.org/coolprop/LowLevelAPI.html),
[SciPy integration](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).
No external drag-correlation coefficient tables or publication prose are copied.
