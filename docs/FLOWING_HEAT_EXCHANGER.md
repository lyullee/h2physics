# Flowing heat-exchanger process ports

`FlowingHeatExchangerAdmission` binds two original process
`ConnectionTransfer` results to one original point of an
`Lh2dtFiniteHeatExchanger` trace. The native trace supplies finite fluid and wall
hold-up identity. Each process transfer supplies its own inlet/outlet state,
signed mass flow, enthalpy change and heat duty.

The caller declares the pressure loss and its source for each side. It must equal
the absolute-pressure difference already present in the original transfer;
extrapolation or a replacement pressure-drop correlation is not provided. Both
process energy balances and the sum of the two side duties plus explicitly
declared external heat must close.

The finite trace point is a capacity/state witness only. It is not treated as a
flowing hold-up derivative because the underlying native trace is a closed
two-inventory thermal integration. No residence-time, axial counterflow,
effectiveness/NTU, leakage, variable UA, phase-distribution or hydraulic solver
is inferred. A later native open-port integrator is needed to couple flow and
hold-up dynamics physically.

The result retains the original trace, point, native states and process-transfer
objects. `require_current()` rejects copied, relabelled or mutated ownership.
This source-only level is `implemented_unverified`; the
`flowing-heat-exchanger` Nurion profile and all original exchanger/equipment
suites remain pending.
