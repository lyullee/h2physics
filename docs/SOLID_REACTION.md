# Finite solid decomposition and hydrolysis

**Status: implemented_unverified.** Source assembly and deferred validation cases
are written. No local model calculation, pytest, native check or benchmark was
run for this development lane. Numerical acceptance and material validation are
pending; the queued Python definitions do not establish either.

`h2physics.storage.solid_reaction.FiniteSolidReactionReactor` combines finite
reactor species, finite feed reservoirs, prescribed component takeoff, an explicit
caller kinetic law and a solved thermal endpoint. It supports one forward
solid-consuming reaction producing gas-phase H2, with explicit `decomposition`
or `hydrolysis` mode. No NaBH4, LiH or other hydride kinetic/material parameters
are defaults. The generic composition is useful only with caller-qualified
stoichiometry, phase calorimetry, kinetic law and operating boundaries.

Chemical-storage pathways and spent-product phases are material dependent;
[DOE's primary overview](https://www.energy.gov/cmei/fuels/chemical-hydrogen-storage-materials)
describes thermal and water-reactive routes. That overview supplies context,
not parameters for this module. Reversible gas/solid sorption remains the
existing finite-hydride model; liquid carrier conversions and prescribed
thermochemical cycles retain their existing owners.

## Existing physical ownership

The new class calls `StoichiometricReaction` for elemental/charge/molar-mass
admission and finite extent bounds. Every mixing, reaction and component-takeoff
operation uses the existing `FiniteThermochemicalCycle`, `PrescribedConversion`
and its actual `ReactionConversion` objects. It does not reproduce their
reaction-heat or phase-enthalpy equations.

Supply an actual `MolarEnthalpyProvider` with exactly the reaction's species,
order, elements, molar masses and phase identities. Every species enthalpy must
include a compatible formation/reference offset. Independent sensible-heat zeros
cannot define a reaction heat. `FunctionalMolarEnthalpy` accepts explicit
caller functions and domains; `CanteraMultiphaseMolarEnthalpy` reuses actual
native gas/solid phase thermochemistry, retains original/owned native objects
and applies its existing definition/reference/domain checks.

The current Cantera bridge supports ideal gas and pure stoichiometric solids.
It does **not** supply an aqueous slurry, dissolved ions, liquid water,
dissolution/excess enthalpy or phase-selection model. Hydrolysis must identify
the actual consumed H2O phase and supply its qualified caloric/rate basis.
Changing liquid water to ideal-gas steam would change the declared reaction;
the module does not perform that substitution.

## State, schedule and rate API

Use existing `ThermochemicalInventory` objects for reactor and supplies. Amounts
are finite mol, pressure is absolute Pa, temperature is K, and `energy_basis_id`
must equal the actual provider basis. A `SolidSupply` has its own source ID,
origin and initial inventory. `SolidFeedDraw` requests component moles from that
finite source. Sequential draws debit the actual remainder; unfulfilled draws
fail rather than becoming an unlimited inlet.

`SolidReactionKinetics` contains the existing balanced reaction, a callable,
named scalar parameters, kinetic/source IDs and origin. The callable signature
is `rate(state: SolidRateState, parameters) -> float` in **mol reaction extent/s**,
not mol H2/s, conversion fraction/s or rate per catalyst mass. Normalizing a
stoichiometric equation changes the extent/rate normalization. Parameter units
and catalyst/loading/material applicability belong to the declared rate source.
They are never inferred from parameter names.

The rate receives actual post-mixing inventory, time in seconds, clock identity,
cumulative accepted extent and current forward extent limit. The model evaluates
it once per supplied interval. Parameters and supplied inventory maps are copied
and read-only. The actual callable and provider remain on the returned trace;
rebinding their identity/species/reference/coefficients requires a new model.
Callbacks must not mutate hidden parameter state or depend on undocumented
external clocks; this is not automatically provable for arbitrary Python code.
`SolidReactionTrace` can only be issued by a reactor run; copying a trace with
`dataclasses.replace()` does not preserve that run receipt. The existing deferred
`solid-binding` contract records the rejection; it has not been executed.

Each `SolidReactionStep` declares a unique ID, increasing seconds interval,
clock ID, heat input in J, finite positive temperature bracket, evidence ID,
finite feed draws and optional component withdrawals. Intervals must be
contiguous on one clock. Positive heat enters the reactor; negative heat is
prescribed rejection. No utility capacity, UA, controller or heat recovery is
predicted by prescribing this heat.

The explicit order is:

1. Withdraw requested existing components at the reactor's previous temperature.
2. Add finite feed packets at each donor's declared temperature and pressure;
   solve adiabatic additive-enthalpy mixing through the existing kernel.
3. Evaluate the caller's forward rate at that mixed state; hold it for the
   interval and request `rate * dt` reaction extent.
4. Apply the explicit finite-extent policy, then use the shared kernel and
   bounded SciPy Brent root to find the endpoint temperature matching supplied
   heat. The final native/kernel query is retained at the accepted root.
5. Remove requested endpoint components with their actual endpoint donor
   enthalpy. This can export newly produced H2.

Packet feeds/takeoffs are imposed beginning/end operations, not continuously
resolved valves. The rate approximation is explicit frozen-start integration
with operator splitting; it needs time-step refinement, especially with thermal
feedback, feeds, inhibition or near depletion. It is not a native kinetic ODE,
equilibrium calculation or automatic adaptive stepper.

The default `limit_policy="reject"` refuses a requested extent larger than the
current reactant bound. Explicit `"truncate"` accepts the finite bound and
records requested/accepted extent, `inventory_limited` and limiting species.
That is a declared depletion approximation, not an event-time solution. Negative,
nonfinite and overflowing rates/extents fail. No reverse reaction or regenerated
spent material is silently introduced.

## Thermal and export meaning

The reactor is homogeneous at one common temperature with externally maintained
constant pressure. The existing kernel sums species enthalpies for their
declared phases. Formation enthalpy creates reaction heating/cooling once;
there is no second empirical reaction-heat source. The constant-pressure
enthalpy boundary is consistent with the
[primary Cantera first-law description](https://cantera.org/3.2/reference/reactors/constant-pressure-reactor.html).
The class does not claim to use Cantera's reactor integrator.

Finite supplies retain their declared temperature/pressure while component
amounts decrease. The combined audit includes initial/final reactor and supply
enthalpies plus all exported donor enthalpy and supplied heat. Pressure-volume
boundary work is implicit in this fixed-pressure enthalpy formulation. This
is not a rigid tank's U/volume/pressure solution, and no kinetic, potential,
shaft or finite utility energy is supplied. No heat exchange between separate
solid/liquid/gas temperatures is predicted. Phase-specific h values do not
make this a multiple-temperature thermal model.

The scalar root finds a bracketed endpoint; it does not certify uniqueness,
positive effective heat capacity, thermodynamic stability or validity of a
caller's arbitrary caloric function. Caller evidence must admit the bracket
and phase domain. No root beyond that bracket or failed native fit is replaced
with another property model.

Takeoff is prescribed by component, not a predicted separator or membrane.
`hydrogen_generated_mol` sums only positive stoichiometric generation from
accepted extent. `exported_mol` can include startup H2 or other components;
no automatic recovery/purity or product-quality claim follows. An export ledger
does not predict a downstream receiver temperature, pressure or finite capacity.

## Results, failures and deferred verification

`SolidReactionTrace` retains initial/final reactor, original/remaining supplies,
actual completed steps, species/elements, generated H2, component exports,
exported enthalpy, signed heat and whole-system element/mass/enthalpy residuals.
Each step retains mixed state, evaluated rate state, requested/accepted extent,
mixing/reaction temperature trials, SciPy root result and actual shared kernel
traces/conversions. Arrays are copied and read-only.

Runtime `SolidReactionError` keeps the original exception as `__cause__`, last
accepted state, completed prefix, committed and trial supply states, phase,
raw rate, requested/accepted extent and actual thermal trials. Kernel errors
remain inspectable. Whole-system audit failure retains each computed elemental,
mass and enthalpy residual directly on the exception; unavailable residuals are
`None`. An accepted trace is issued only after the audit passes. A failed step
does not commit partial feed debits or exports.
Admission errors before stepping are ordinary `TypeError`/`ValueError`.

The original example is [examples/solid_reaction.py](../examples/solid_reaction.py).
`problem()` builds synthetic objects; `run_example()` would execute them and
has deliberately not been called locally. The deferred catalog is
[validation/cases/solid_reaction.py](../validation/cases/solid_reaction.py).
`cases()` returns metadata-only `ValidationCase` definitions; only the later
authorized HPC dispatcher calls `validate_*` entrypoints.

Eight core cases prepare analytic first-order refinement, independently
calculated thermal endpoint, warm finite-water feed/limiting reactant/takeoff,
element-linear reference shifts, startup-gas separation, exhausted supply and
failure retention, negative/domain gates, and identity/immutable-parameter
checks. A ninth optional chemistry case composes actual Cantera LiH(s), Li(cr)
and H2 phases through the existing caloric bridge within a declared 300–430 K
envelope. Its solid densities and rate are synthetic; even a future successful
run would establish native composition checks, not material qualification.

No case has run and no accuracy/performance/pass count is reported. See
[the development record](../research/solid_reaction_development.md) for exact
scope, inputs and the pending HPC acceptance plan.

The original signed heat command can feed the shared thermal-duty accounting
through `HeatDuty.bind(trace, SolidReactionHeatAdapter(), window)`. This keeps
the heat-port energy ledger intact while requiring a separate declared utility
availability and transfer boundary. See
[SOLID_REACTION_HEAT_HANDOFF.md](SOLID_REACTION_HEAT_HANDOFF.md); the deferred
`solid-reaction-heat-utility-handoff` contract has not been executed.
The separate `solid-reaction-hydrogen-finite-source-handoff` projects only
species-resolved H2 takeoff into a generic finite release source, subject to
same-state and enthalpy-reference checks. It adds no separation, outlet,
pressure-control or dispersion model; see
[SOLID_REACTION_H2_SOURCE.md](SOLID_REACTION_H2_SOURCE.md).
