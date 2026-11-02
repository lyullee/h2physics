# Open hydrogen Brayton reference

`h2physics.combustion.run_open_cycle_brayton()` evaluates one steady, single-
stream reference point. It injects a caller-owned native Cantera gas `ThermoPhase`
and uses that phase for all air/fuel properties and the combustor HP-equilibrium
calculation. Cantera documents the native `SPY`/`HPY` state pairs and
`equilibrate("HP")`; the API introduces no second equation of state or reaction
solver ([ThermoPhase API](https://cantera.org/3.2/python/thermo.html),
[Cantera Python tutorial](https://www.cantera.org/3.2/userguide/python-tutorial.html)).
The existing optional project dependency is Cantera 3.2 (`.[chemistry]`).
The native phase must use Cantera's `mass` basis: the cycle arithmetic uses
`enthalpy_mass` in J/kg and `entropy_mass` in J/kg/K as inputs to `HPY` and
`SPY`. Cantera also permits a molar basis for those state-pair setters, so the
runner now rejects `basis="molar"` instead of passing mass-specific quantities
with mismatched units. This requirement follows the documented
[`ThermoPhase.basis` and state-pair units](https://cantera.org/3.2/python/thermo.html).

## Model definition

The accounting basis is 1 kg of compressor-inlet air plus an explicitly specified
hydrogen-to-air mass ratio. The four main stations are air inlet, compressor
outlet, equilibrium combustor outlet and turbine exhaust; a separately recorded
hydrogen feed state supports the combustor mass/enthalpy ledger. The compressor
and turbine use caller-specified isentropic efficiencies. Combustor pressure
recovery is an explicit scalar fraction. Hydrogen is supplied at the combustor
inlet pressure, so upstream hydrogen compression is outside this boundary.
Combustion is adiabatic, constant-pressure HP equilibrium. Turbine expansion
retains the combustor outlet composition (frozen chemistry).

The result reports compressor/turbine/net work per kg of inlet air, H2 heating
input using a caller-supplied LHV and evidence ID, a thermal-efficiency ratio,
station properties/compositions, combustor enthalpy residual, open-cycle energy
residual and element mass-fraction residuals. The native phase remains available
on both a successful result and `OpenBraytonError`; the error also retains its
failed stage and prior completed station snapshots.
Direct `OpenBraytonRun` construction recomputes the reported work, efficiency,
combustor/cycle energy residuals and element residual vector from the retained
states and checks that the supplied native phase ends at the turbine station.

The native phase guard and elemental ledger use Cantera's species-array
`molecular_weights` property. Cantera 3.2 does not expose
`mean_molecular_weights`; a 2026-10-31 Hangang run caught this API-name mismatch
before any cycle calculation. The binding now matches the documented
[`ThermoPhase` API](https://cantera.org/3.2/python/thermo.html), and cases that
failed at that guard must be retried against a newer pinned source before their
contracts can be assessed. The run receipt also seals the native property basis,
so changing it from mass to molar after execution invalidates the captured
mechanism-state identity.

Inputs require explicit mechanism and process-window identities, inlet states,
oxygen-bearing air composition, pressure ratio, pressure recovery, isentropic efficiencies,
fuel ratio, LHV and evidence IDs. The mechanism identity is caller-declared; this
reference currently does not hash or license-qualify the mechanism bytes. Use a
reviewed mechanism under its own terms, and preserve its exact source/version in
the research record. No mechanism or dataset is redistributed here.

## Scope and limitations

This is a thermodynamic reference, not a turbine selection or performance model.
The base route has no maps, coupled shaft solver, mechanical losses, generator, fuel
compression, cooling bleed, dilution injection, wall heat, pressure-side cooling,
combustor stability, NOx, flashback, autoignition, transient startup, recuperation,
multiple spools or off-design control. It does not infer any compressor/turbine
efficiency or combustor pressure loss. It computes no absolute power without a
caller-supplied air mass flow. The thermal-efficiency metric uses declared LHV;
auxiliary work and any external heat input are not included.

`run_map_bound_open_cycle_brayton()` provides a separate one-point coupling for
caller-owned turbine maps. It accepts only the explicit
`inlet-over-exit-total-pressure` convention, uses the interpolated map efficiency,
and requires map pressure ratio to match the cycle stations. The caller supplies
air mass flow and a sourced factor converting actual turbine mass flow to the
map's corrected-flow basis; no generic correction convention is inferred. The
returned receipt binds that map point to the existing reference result and
rechecks source-grid and flow linkage. It reports compressor input, turbine gross,
and net gas-path power by multiplying the retained per-kilogram-of-air cycle ledger
by the declared inlet-air mass flow. Those are reference powers before mechanical,
generator, cooling, bleed, fuel-compression, or auxiliary terms. The separate
`balance_map_bound_brayton_shaft()` composition accepts explicit shaft mechanical
loss in watts and generator efficiency with evidence identities. It derives shaft
net and electrical power, rechecks every ledger term against the retained cycle,
and rejects a negative shaft balance. It does not infer losses or efficiency,
couple compressor/turbine maps, solve controls, or qualify a machine.

An external compressor engine can be joined through
`CompressorOperatingPoint` and `couple_compressor_to_map_bound_brayton()`.
Supply compressor specific work in J/kg of inlet air, inlet-air flow in kg/s,
and evidence identities for the operating point, process window, common shaft
speed and flow link. The composition checks the process-window and air-flow
basis against the turbine-bound cycle and reports turbine-minus-compressor
power as a shaft residual. It does not require that residual to be zero, search
for a matching speed, or adapt any particular compressor library automatically.
Its deferred hydrogen-engine contract includes window/flow mismatch rejection;
that contract has not run.

For hydrogen fuel pressure work, the separate
[`HydrogenCompressionInputs` one-stage reference](HYDROGEN_FUEL_COMPRESSION.md)
uses native Cantera ideal-gas H2 properties and can debit its shaft power from a
matched Brayton point. A separate [`CoolPropProperties` real-fluid route](HYDROGEN_FUEL_COMPRESSION.md)
is available for single-stage H2 property flashes within a caller-declared domain;
it does not convert the result into the Cantera cycle's property basis. Compressor
maps, multistage trains, intercooling and qualified equipment data remain outside
both single-stage references.

Output station objects directly validate their typed species and element bases
and retain mechanism/process-window identities. The phase itself is mutated during
the call and finishes at the turbine exhaust state; use an independent phase per
concurrent evaluation.

Four deferred contracts are assigned to the existing `hydrogen-engine` Nurion
profile. They have not run and establish neither model validation nor machine
qualification. Request035 remains active for a map-based, coupled single-shaft
implementation and comparison with license-compatible hydrogen-capable turbine
data.
Its detailed receiving API and parallel verification matrix are in
[`integration_request_034_035.md`](../research/integration_request_034_035.md).
