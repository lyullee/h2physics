# Sequential unit-parcel impacts on one finite surface

`h2physics.adapters.impact_population_sequence(population, impact_owner)` connects
the existing parcel-flight population output to one existing `FiniteSurfaceImpact`
owner. It collects every original ground-crossing group whose represented count is
exactly one, orders those accepted event states by time, and submits the distinct
flight traces in one call to the native surface owner. That existing owner advances
its finite wall temperature between contacts and applies its declared inter-contact
heat boundary. No separate impact equation or patch thermal solver is added.

The returned `PopulationImpactSequence` retains the exact population, owner, native
impact result, group order and event times. It verifies each step against the
owner-issued impact record, checks that aggregate incident mass matches the full
incident subset of the population, and rechecks the owner's combined mass and energy
budgets. A representative group with count greater than one is rejected; one
trajectory is never multiplied into multiple impacts. Equal-time contacts are also
rejected because this owner supports ordered contact events, not simultaneous impact
mechanics. Overlapping finite contacts fail through the existing owner and preserve
its completed-step prefix in `PopulationImpactSequenceError`.

Other population groups with non-impact terminal states remain outside the surface
sequence and are not counted as incident contacts. The sequence does not calculate
deposition, splash, liquid pooling, wet-surface impacts, or impact distributions.
The impact closure must still be applicable and evidenced for each parcel. Existing
flight and impact numerical/experimental qualification remains pending.

The synthetic deferred case is enrolled in both Hangang and Nurion source plans
under `droplet-impact`. It checks two distinct unit parcels on one finite patch and
rejection of representative multiplicity. Its launch elevations and downward
velocities are chosen to produce separate ground-crossing events within the finite
flight window while remaining within the fixture's declared Reynolds and Weber
limits. Job 1185904 showed the earlier, higher/slow launch setup produced no
admitted impact event; the fixture coordinates were corrected without changing
the flight or impact models. The corrected source is unverified pending a fresh
snapshot and retry.
