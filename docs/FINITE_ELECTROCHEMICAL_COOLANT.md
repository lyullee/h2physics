# Finite electrochemical coolant

`FiniteThermalStack.run_with_coolant(initial_temperature_k, initial_coolant_state,
stages, reservoir=...)` extends the original shared thermal RHS with one liquid
coolant enthalpy state. `FiniteCoolantReservoir` declares fixed mass, absolute
pressure, a native property provider, temperature domain, physical clock, boundary
and evidence IDs. Its external heat callback receives `time_s`, `clock_id`, and
the current native coolant `state` and returns heat into coolant in W.

Stack heat exchange enters coolant with the opposite sign. Stored coolant energy
is mass times specific enthalpy change at imposed pressure. Native PH states must
remain liquid, have positive cp, retain their property basis and honor pressure,
enthalpy and temperature bounds. Phase changes and domain excursions reject.
The stage's prescribed coolant temperature is unused on this explicit finite
reservoir route. Existing prescribed-coolant runs preserve their three-state API.

The prescribed-coolant `ThermalStackTrace` is issued only by `FiniteThermalStack.run()`.
It binds the exact issuing owner and fingerprints the accepted stages and solver
arrays; direct construction, copying and later mutation are rejected. Cross-model
thermal handoffs recheck that receipt and require the same thermal owner.

Returned `FiniteCoolantStackTrace` retains the issuing thermal owner, reservoir, coolant endpoint states
and original stage results. Each stage preserves the native five-state result,
external coolant heat and independent coolant enthalpy residual. The native state
order is stack temperature, generated heat, stack-to-coolant heat, coolant specific
enthalpy, external coolant heat. `combined_energy_residual_j` sums the stack and
coolant residuals; the internal exchange cancels in that balance.
`require_current()` fingerprints original source/configuration metadata and native
trajectory arrays. Shared RHS callbacks are checked for configuration or held-stage
mutation. `FiniteCoolantStackError` retains the original cause, failed command,
completed stage prefix and any returned native result, without rolling back callbacks.

This implementation has not run. Its deferred `fuel-cell` case uses CoolProp
water and existing shared stack equations. The model has no coolant flow,
pressure dynamics, boiling, mass depletion, reaction crossover or controller.
The caller must identify a stack heat capacity that does not duplicate material
sensible energy modeled elsewhere.

`adapters.electrochemical_coolant_utility.ElectrochemicalCoolantHeatAdapter`
provides original finite-coolant heat duties to the shared HeatDuty API. The
explicit external-coolant selection retains actual external callback integrals;
internal-stack-to-coolant is tagged internal-transfer and excluded from external
utility quantities. Caller scope evidence, exact clock/window and original source
objects are required. Boundary duty alone does not imply purchased utility,
recoverability or COP. The adapter requires contiguous stage intervals, exact full
window coverage, present coolant endpoints and matching property bases. Coolant
traces are issued only by `run_with_coolant`; copying an existing trace cannot
reseal altered history. These deferred receipt/accounting contracts remain unexecuted.

The prescribed-coolant and finite-coolant RHS paths both bind the original held
stage, stack configuration, thermal capacity and conductance callback before
integration. Configuration changes during a callback are rejected. The finite
provider route also retains backend/version/enthalpy-flash binding and rechecks
after the final coolant state flash. Returned solver arrays must have the complete
three-state or five-state layout, finite entries and the exact requested stage
clock endpoints. These are source/result admission rules; the expanded deferred
mutation and invalid-input cases have not been executed.
