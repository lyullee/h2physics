# Native finite pure-fluid phase-selective operation

`adapters.finite_separator.run_finite_pure_fluid_separator()` reuses the actual
LH2DT `StratifiedTank` for separate liquid/vapor inventories, interface transfer,
walls, EOS and integration. Supply that native owner and initial state, its exact
`Lh2dtProperties` bridge, pure material ID, physical start/duration/step and
nonempty string clock identity, phase-flow callback, ambient temperature,
explicit phase-assignment evidence, per-phase domain callbacks, mass/energy budgets
and positive phase inventory floors.
Optional wall/fluid heat callbacks retain the native signature while receiving
absolute physical time. Commands must be continuous within the declared run.

`phase_flows(time_s, thermo)` returns `(liquid_flows, vapor_flows)` containing
original native `MassEnergyFlow` objects. Positive flow enters the assigned phase.
Withdrawal enthalpy comes from the current selected native phase, not an arbitrary
number supplied on an outgoing stream. Caller domain callbacks receive common
`ThermoState` values. Domain callbacks either return `None` after validation or
one boolean scalar; Python and NumPy false values reject the phase. Native trial
and accepted states must remain above the
explicit liquid/vapor inventory floors; no phase depletion is silently clipped.

`FiniteSeparatorTrace` is issued only after the native operation returns and the
host audits its endpoint and per-edge balances. Direct construction and
`dataclasses.replace()` cannot reuse an issued result. The trace retains native
rows, phase states, actual component mass, fluid and both-wall stored energies,
boundary integrals and independent mass/energy residuals. `require_current()`
checks original configuration, provenance and retained output content. Native
failure preserves evaluated boundary trials.
The reviewed native `simulate` keeps accepted rows local until successful return;
an exception does not expose that accepted prefix, and the host does not invent it.

This is pure-fluid two-region operation. It does not supply mixture component
separation, level control, nucleation or vessel hydraulics. Request032 specifies the
missing evolving-mixture total-volume/internal-energy flash and selective ports.
The native `MixturePhasePartition.withdraw_component_moles()` helper now accounts
phase-specific withdrawal from current native liquid/vapor composition and reports
component stocks before, withdrawn and after, retaining the native phase enthalpies.
It rejects mismatched phase totals and overdraw. Its `phase_mass_out_kg` and
`phase_enthalpy_out_j` properties expose component-molar-mass-derived outlet masses
and energy exports based on retained native J/kg values; unknown enthalpy remains
explicit as `None` when a corresponding phase is withdrawn. This does not recalculate
equilibrium from the changed total inventory, locate phase events, or advance a
separator; those remain native Request032 work. The deferred mixture phase case
specifies this ledger and remains unexecuted.

The native PQ/TQ partition admission checks each component balance as
`z_i - ((1-q)x_i + q y_i)` against the caller's absolute mole-fraction tolerance.
It does not renormalize or repair CoolProp phase compositions to force closure.
If a native packet fails, its error now includes the quality, tolerance, and each
component's overall/liquid/vapor fractions and residual so the provider mismatch
can be diagnosed without loosening the material-balance bound.

`MixturePhaseAmounts` also exposes equilibrium-packet phase volumes from retained
native phase densities, a residual against bulk mass/density, and phase internal
energies from `u = h - p/rho` with a residual against bulk `u`. An occupied phase
without required native properties raises; an absent endpoint phase contributes
exactly zero. These values use the native provider's property reference and describe
one equilibrium packet, not a vessel inventory flash or time history. Their deferred
contract has not run.

Each `MixturePhasePartition` and successful PH inverse receipt is issued once from
the native CoolProp phase flash/inverse.
Direct construction and dataclass cloning are rejected, and retained phase
properties, provider composition and state values are checked again before packet
accounting. This protects the provider-to-host receipt boundary; it does not supply
Request032's changing-composition inventory flash or finite-vessel integration.

`thermo.MixtureInventoryStateAdmission` accepts an already-produced native phase
packet against caller-declared component moles, fixed vessel volume and total U,
for the provider's frozen overall composition.
It checks exact provider-object/branch identity and each component, volume and energy
residual against explicit tolerances, then seals the exact admitted inputs and
summaries. It performs no inverse solve, phase event handling or time integration;
its purpose is to let the receiving native inventory solver hand a candidate state
to existing host workflows without the host inventing an equilibrium flash. The
deferred admission contract has not run. The detailed Request032 protocol and
parallel acceptance matrix are in
[`integration_request_032.md`](../research/integration_request_032.md).
The separate [`fixed V/U mixture flash`](MIXTURE_INVENTORY_FLASH.md) can solve a
single two-phase equilibrium state on an explicitly bounded pressure/quality branch;
it still does not provide the native evolving-inventory integrator requested there.
The shared native method source is [LH2DT StratifiedTank](https://github.com/lyullee/lh2dt_models).
The deferred `finite-transfer` case is authored only; no scientific execution or
independent qualification is established by this implementation.
