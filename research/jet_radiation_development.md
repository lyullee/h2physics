# Jet-fire radiation development record

## Scope and ownership

This addition consumes `HyRAMFlameRun` and requires its existing full-source
acceptance. HyRAM retains nozzle, expansion, combustion, visible centerline and
emitted radiant-power ownership. The new adapter implements only a geometric
isotropic line-source receiver calculation and applies a caller-owned
atmospheric transmission callable. It does not modify the separate failed
jet-fire conservation/caloric gates.

## Equations and contracts

For visible centerline segment i of length ds_i, the prescribed emitted power is
`P_i = S_rad ds_i / sum(ds)`. At receiver r, scalar incident flux is the sum of
`tau_ri P_i / (4 pi R_ri^2)`, with R_ri measured from the segment midpoint.
Every input is finite; transmission is dimensionless and must remain inside
[0,1]; receivers inside the configured source exclusion distance are rejected.
The field reports a receiver-distance-weighted transmission diagnostic. It is
not a spatial integral of flux and does not claim emitted power intercepted by
the atmosphere or an enclosing surface.

This level assumes isotropic emission per arclength and point receivers in an
unobstructed calm environment. Independent radiometer data, line quadrature
refinement, angular emission, wind, shielding and target absorption remain
required. The module is `implemented_unverified`.

## Validation state

Four deferred cases describe clear-path behavior, attenuation scaling, native
centerline segment audit and source-neighborhood rejection. Discovery does not
execute them. No calculation, test or independent experimental comparison has
been run for this addition.
