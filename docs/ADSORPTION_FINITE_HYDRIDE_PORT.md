# Adsorption outlet to finite-hydride gas port

`bind_adsorption_to_finite_hydride()` maps an accepted completed
`AdsorptionDynamicsTrace` H2 outlet ledger into the existing
`FiniteHydrideGasPortBoundary`. Each native interval uses its exact accepted
start/end times; the net H2 outlet mass increment becomes a constant flow over
that interval. The caller provides an inlet `ThermoState` and projection
evidence for every interval. Projected stream enthalpy must close the native
adsorption outlet enthalpy increment within the declared per-bin budget.

The caller declares the shared operation clock, time-axis mapping and
hydraulic transfer evidence. The adapter revalidates the adsorption owner on
every bed-port evaluation and preserves the stream property basis. It does not
infer a valve, pressure drop, line capacity or pressure evolution; the finite
hydride bed continues to own its existing storage and reaction calculations.

## Contract and accounting basis

The adapter accepts only a completed trace whose source vessel gas is exactly
single-component H2. The source and bed property bases must be compatible and
their declared H2 molar masses must agree. For interval `i`, the handoff uses
`Δn_i = cumulative_outlet_mol[i+1] - cumulative_outlet_mol[i]` and
`m_i = Δn_i M_H2`; a negative increment is rejected. The accepted duration
`Δt_i` is not resampled: `m_i / Δt_i` is the piecewise-constant mass rate over
the original interval. The final endpoint belongs to the final interval.

Each interval also requires one explicit single-phase H2 gas `ThermoState` on
the bed basis, with pressure and temperature exactly equal to the accepted
adsorption trace row for that interval. The current API therefore does not
silently treat a caller state as a downstream state after pressure loss,
cooling, heating, or other transfer. A future transfer mapping needs a typed
per-bin source-to-receiver state projection that records both endpoint states,
the physical mapping basis, and evidence; an evidence identifier alone does
not authorize changing pressure or temperature. Its `m_i h_i` is compared with the native outlet enthalpy
increment. A bin is rejected when the residual exceeds the caller's absolute
plus relative tolerance. The energy reference and state projection remain
caller-evidenced; this check does not establish that the physical transfer line
will deliver that state.

The shared clock, clock-alignment evidence, hydraulic-transfer evidence, and
one state-projection evidence identifier per source interval are mandatory.
The callback checks source ownership each time the finite-bed port is queried.
This boundary does not calculate valves, pressure losses, thermal conditioning,
transient line inventory, or pressure-flow behavior. Those require an explicit
upstream transport model and a separate coupling contract. The deferred case
uses synthetic inputs and only specifies software accounting invariants; it is
not experimental validation or facility qualification.

Deferred Hangang case: `adsorption-to-finite-hydride-gas-port-handoff` under
`finite-hydride`.
