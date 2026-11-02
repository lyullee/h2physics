# Fire, failure, parcel and economic integration requests

This document requests future receiving-project work. No other repository has
been changed or contacted. All four local interfaces below are coding-only and
await execution and independent qualification.

## PRCT / DynamicLH2PoolX

Local owner: `h2physics.adapters.pool_fire`. Retain actual native pool burning,
sphere radiation and original pool result objects. A predictive postignition
model needs a public finite coupling contract: liquid mass/area/temperature,
vaporization, net burning flux, finite oxygen supply, surface heat, radiative and
convective exports, exact clocks and supported receptor geometry. Resolve whether
reported pool mass loss includes preignition evaporation; never subtract it twice.
Current local conditioning heat is a finite external budget, not solved fire
feedback. Accept source/energy/event/refinement and independently qualified LH2
fire observations before extending the present sphere reference model.

## HELPR / storage models

Local owner: `h2physics.adapters.vessel_failure`. Expose mechanical loading in
SI with an explicit absolute-versus-differential pressure convention, native
geometry/SIF/reference-stress/FAD results and material temperature qualification.
Keep mechanical wall temperature separate from gas temperature used in hydrogen
fatigue/environment models. Supply an actual crack-growth-to-flaw-history port
with its clock and geometry; do not infer flaw growth from a fixed-flaw capacity
curve. Thermal stress, creep, external pressure, through-wall geometry, breach
area, fragments and blast require distinct qualified physics. Preserve original
root failures and out-of-domain calls. Current results are failure initiation
criteria, not certified pressure-vessel assessment or accident source prediction.

### Failure-initiation to rupture-source handoff — missing receiving owner

`VesselFailurePrediction.initiation` is a conditional mechanical initiation result;
it is not a finite rupture opening or release stream. The current source seam has
no independently qualified owner that consumes the exact original prediction,
operation clock and accepted source state, declares a breach/opening evolution,
and returns mass plus thermodynamic-state/enthalpy output with native lineage and
failure-prefix retention. Implement that receiving owner before linking the result
to dispersion, fire or consequence models. Preserve the trigger identity and its
original native/root evidence; require the breach geometry, opening rule and any
post-initiation vessel evolution as explicit qualified inputs. Do not turn a HELPR
failure criterion into an opening area, discharge coefficient, blast or rupture
time, and do not restart an intact-vessel simulation after initiation by assumption.

## Parcel / surface / dispersion owners

Local owner: `h2physics.adapters.droplet_transport`. A future qualified heat
closure accepts an actual `ParcelState` and returns `BoilingHeat` with its native
result/evidence. It must declare carrier composition and phase evolution,
temperature/pressure/size/velocity bounds, reference states and numerical trial
semantics. Do not adopt the retained rejected standalone air-condensation result.
Native surface tension should gain a shared public property-provider contract;
the current explicit supplied tension must have source/domain evidence.

The terminal incident liquid state is not a deposited pool source. A surface
owner must resolve deposition/rebound/splash/vapor, vectors, phase enthalpies,
finite surface thermal energy and local clocks. Acceptance includes component
mass, enthalpy plus kinetic energy, impulse and step/parcel-size convergence;
otherwise `release.impact` remains planned. There is no default deposition ratio.

## PV / pyH2A / process owners

Local owner: `h2physics.adapters.hydrogen_economics`. Export complete physical
reporting windows, actual native state/step identity, generated/stock/sold product
and unresolved pressure/utility work explicitly. Annual inputs require declared
product gate, cost scope, currency/year, representativeness and reconciliation;
one day of PV output must not silently become an annual sales model. Retain the
native DCF denominator and original provider arrays/errors. Public detailed
cash-flow arrays would improve independent audits; do not recreate unavailable
native financial formulas in the adapter.

ProFAST1.0.6 is not adopted because inspected use/redistribution terms do not
support the intended public module. pyH2A0.0a8 is an optional reviewed candidate:
MIT code and CC-BY4.0 non-code resources need separate attribution. Exact supplied
year/depreciation-table availability must be checked, with no nearest-year
substitution. No current prices or qualified investment result is supplied.

## Deferred acceptance

The new lanes define19 cases:8pool fire,4vessel,5economics and2parcel. Together
with the previous22, the pending campaign contains41 cases. Run them later in
explicit Nurion dependency profiles, then inspect failures and native evidence.
No case, solver or scheduler has been executed for this wave.
