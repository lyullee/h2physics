# Native accepted-edge pool energy contract

`h2physics.adapters.pool_native_energy_contract` defines a Python-side
acceptance record for energy and mass terms published by a native pool solver.
The native solver remains responsible for evaporation, heat transfer, dryout,
event localization and finite-wall dynamics. The contract does not estimate any
of those processes and does not integrate sampled output rates.

## Calling boundary

The receiving solver must expose its immutable `accepted_energy_samples` and
issue one `PoolNativeEnergyEdge` for its declared initial state and every true
accepted integration edge. Each trace row must be the exact row object issued
by that result. Each edge retains the
native state object and the solver's stable step identity. Every cumulative
transfer must have been accumulated inside the solver's own accepted intervals,
including its event and thermal-age splits. Requested reporting samples are not
automatically accepted edges.

An edge reports liquid mass, internal energy, volume and boundary pressure;
cumulative liquid inlet and vapor outlet mass/enthalpy; cumulative heat into the
liquid; and cumulative pressure-volume work out. The native owner must also
separately report nonnegative cumulative unapplied, dry-surface and heat-cap
rejection allocations. Net heat and work may reverse where the physics permits;
their signs follow the named transfer direction.

The first edge is the exact initial state. All cumulative terms start at zero.
The trace audits liquid balances with

`R_m = m - m0 - Min + Mout`

and

`R_U = U - U0 - Hin + Hout - Qliquid + Wout`.

Finite-wall mode also requires original wall energy change and external heat at
every edge, with `R_wall = dUw - Qexternal + Qliquid`. The wall and liquid use the
same transferred-heat history, so it cancels once in the combined balance.
Prescribed-reservoir mode cannot claim finite wall storage or external wall
energy. Energy-reference and vapor-phase identities are explicit at trace level.

`PoolNativeEnergyTrace.verify_result(result)` only accepts the exact original
native result and checks the captured edge identities and balance terms again.
It does not replay the native integration. The existing
`bind_native_pool_energy_ledger()` remains the continuation-specific host binder;
older DynamicLH2PoolX results without native cumulative terms still fail closed.

## Current implementation boundary

This repository does not contain the DynamicLH2PoolX integration owner. The new
types define and audit its Python contract, but they do not add cumulative
integrals to that external solver. Until an upstream native result supplies
true accepted edges and interval-integrated values, the host binder must keep
raising `PoolEnergyCapabilityError`. The deferred contract case uses synthetic
terms to exercise only record admission and balance arithmetic; it is not pool
physics validation or evidence of upstream capability.
