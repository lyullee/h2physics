# Request032 receiver boundary status

The local `h2physics` package contains the receiving Python contracts for finite
mixture inventory, phase partition and admission, and the finite interval and
adaptive host-side runners. The native evolving-composition separator required
by Request032 is a separate owner in LH2DT's storage/inventory layer. That native
owner's implementation source and issued result types are not present in this
repository, so its accepted states, branch receipts, phase events, native failure
status and exposed accepted prefix cannot be integrated or audited here.

The local interval runner and SciPy ODE remain distinct host capabilities. The
canonical Request032 contract explicitly excludes either as a substitute for
native equilibrium and native accepted-step integration. Do not label those paths
as completion of the receiving-owner request.

## Receiving implementation handoff

When the native owner API is available, add a narrow adapter that consumes its
sealed result directly. It must retain the exact native owner, initial/final
inventory, accepted rows, flash/branch packet, native event and failure records,
clock, and energy reference. Independently recompute component-mole, total-mass,
phase-volume, fluid-plus-wall energy and boundary integral residuals from those
retained rows. It must reject a fixed-composition provider, regenerated/replayed
states, altered result identity, missing ledgers and rows not exposed by the native
solver. Keep the separate liquid/vapor ports and actual inlet stream composition
and enthalpy; evaluate withdrawals using each accepted row's current phase
composition and enthalpy. Detailed field definitions and acceptance matrix remain
in `requests/032_finite_mixture_separator.md` and
`research/integration_request_032.md`.

## Current status

Native receiving-owner integration: blocked on the external LH2DT owner API and
implementation source. Local single-state admission and host-side trajectories
remain useful checks, but are not evidence of native separator integration.
No scientific test, calculation or cluster job was run for this status note.
