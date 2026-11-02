# Direct-DC, solid-phase and fracture API follow-up

Status: coding-first increment, implemented_unverified. No request below is
implemented or validated merely by being written. No receiving repository was
edited or contacted. New scientific execution is deferred to Nurion by the user.

## Common electrochemical/pressure boundaries

Expose a typed reversible/reaction-energy pressure/reference record and actual
material enthalpy/phase identities. Distinguish source production pressure,
receiver pressure, Gibbs pressure contribution and unresolved external work.
The current direct-DC composition retains those declarations; it cannot close a
whole plant by silently assigning zero compression, pump or utility work.
Preserve actual reaction conversion, Faraday fate, native gas flashes and held-
point refinement. Required heat is not actual utility availability.

The native PV diode and stack polarization remain their owners. If extending
power conversion, represent the actual MPPT/DCconverter or ACinverter/rectifier
chain and its native parameters/voltage/current domains. Do not send AC power
straight into a DC stack or convert all MPPcurtailment into heat. Missing roots
and explicit blocking/off operation must remain distinct.

## Public phase-enthalpy kernel hooks

The solid reactor reuses existing FiniteThermochemicalCycle._h and _check_balance
inside the host. Publish stable public equivalents with the same reference,
phase, element and mass/heat semantics before treating them as long-term APIs.
Do not fork their equations into another reactor implementation.

A liquid-water/aqueous hydrolysis provider needs actual qualified phase caloric
properties, pressure/reference, solution/excess/reaction basis and finite donor
state. The existing native bridge for ideal gas/pure solids cannot acquire those
capabilities by relabeling steam. Material-specific rates, catalyst/loading and
thermal/phase validity are explicit source inputs, not fitted defaults supplied
by a generic chemical hydride label.

Preserve rate normalization in mol reaction extent/s, finite supplies, actual
limiting reactant, explicit reject/truncate policy and unresolved within-step
exhaustion. The held-beginning rate and endpoint heat solve need the planned
refinement/analytic/independent experiments before accuracy claims.

## Native fracture constitutive/geometry hooks

The current HELPR adapter reuses actual growth/fugacity calls with a caller SI
mode-I stress-intensity function and SciPy trajectory/events. It does not claim
the native pipe-specific LifeAssessment whole-trajectory driver. A receiving
native general driver should accept explicit geometry/SIF, material/environment,
cycle and physical-time histories and return original constitutive probes and
accepted/event/failure state without hiding unit conversions or rate arrest.

Keep Pa sqrt(m) versus MPa sqrt(m), mol fraction versus percent and fugacity
versus partial pressure distinct. Published hydrogen relations require their
actual material/P/T/R/frequency domain and independent validation. Native model
availability does not calibrate another alloy. Do not derive crack-growth or
fracture toughness from unrelated reduction-of-area data or fabricate a stress
law from pressure. Initiation, collapse, mixed modes, closure/overload and evolving
transport remain distinct model levels.

## Deferred execution

The22 written cases and PBS/Python scaffolding are unexecuted. After actual
Nurion connection, supply accepted Linux/native profiles, queue/account/resources
and fixed source/plan identity, then run the numerical/native/negative/refinement
and independent-data checks. Existing full regressions and artifact acceptance
also remain required; neither AST nor a generated scheduler script completes them.
