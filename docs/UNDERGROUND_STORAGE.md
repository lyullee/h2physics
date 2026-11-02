# Native underground cavern reference — implemented, unverified

This increment has not been executed. No native import/model calculation,
installation, pytest, replay, example, case or benchmark was run locally. The four
Nurion cases are dormant preparation. A native import, solver, physical-domain or
conservation failure must remain a failure. This adapter does not establish an
accepted underground-storage level or measured cavern validation.

## Actual owner and scientific addition

The optional owner is [Sandia UH2SC](https://github.com/sandialabs/uh2sc), pinned to
`d5057350df4d86c5c11a22e76beca24275518c8c`. Its actual `uh2sc.model.Model` combines a
finite warm gas cavern, a finite liquid-water surrogate, noninteracting water
vapor, an ideal adiabatic vertical well and transient axisymmetric ground heat
storage. This finite rock thermal history distinguishes the composition from a
renamed pressure-vessel wrapper. UH2SC owns every physical residual and time step;
the host adds independent inventories and admission. No native equation is copied
or repaired and no replacement tank/rock ODE or EOS is implemented.

The official [Sandia project presentation](https://www.osti.gov/servlets/purl/2540300)
provides native project context. Sandia's [subsurface-storage programme](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/storage/hydrogen-subsurface-storage/)
separates cavern/reservoir, geochemical and other subsurface work. This particular
adapter does not supply those broader capabilities. The [Environment Agency's
geomechanics report](https://www.gov.uk/government/publications/the-geomechanics-of-hydrogen-storage-in-salt-caverns-environmental-considerations)
documents a separate structural assessment problem; a thermal pressure envelope
here is not a geomechanical safety calculation.

The inspected pyproject declares1.0.0 while the native package's `__version__` is
0.0.0. Both labels are retained. Source/schema SHA checks identify the actual
revision; no version label is rewritten. Source installation/runtime compatibility
and transitive licensing remain to be resolved in the isolated Nurion profile.
The source is Revised BSD/BSD-3-Clause with HydDown-origin MIT notices. No native
source, input schema, worked example, coefficient table or model data is bundled.

## Python API and actual native objects

```python
owner = Uh2scUndergroundStorage(evidence, operating_domain, audit_budgets)
trace = owner.run(native_input_mapping, solver_options=explicit_native_solver_options)
native_model = trace.native_model
native_solver = native_model.solver
native_cavern = native_model.components["cavern"]
native_solutions = native_model.solutions
native_independent_outputs = native_model.independent_vars
```

The input is the actual native Python dictionary API, not mandatory YAML/JSON.
The model factory is injectable but must return a fresh actual complete `Model`,
with all explicitly supplied input fields preserved. Native test/single-component
modes and instance-method substitutions are rejected. Raw native return value,
logger records, actual state-vector arrays, independent outputs, components and
solver remain available. No fabricated native object is returned.

`UndergroundEvidence` specifies clock origin, frame, site/source and geometry,
rock, farfield, well-history, pure-water and omitted-mechanical-energy evidence.
Native relative seconds are retained alongside `start_time_s+native_time_s` on the
declared operation clock. Inputs and native definitions/source bytes are checked
before/after the run. The result remains `implemented_unverified` even if future
numerical audit gates pass. It has no annual-frequency or rupture-probability field.

## Restricted native scope and physical bases

This first audit supports one cylindrical cavern, one single-pipe ideal well,
one ground heat exchanger and pure normal `Hydrogen` with direct HEOS. The native
liquid called brine is actually pure `Water`; salinity and dissolved hydrogen are
not supplied. The water-vapor fraction needs an explicit dilute-approximation
budget. Para/ortho thermodynamics, evolving spin mixtures, cushion-gas mixtures,
porous reservoirs, capillarity and reaction/biology are excluded. Native ML/fitted
property replacement is rejected; the pinned native model-selection path currently
returns no fitted model. The host reuses existing `CoolPropProperties` directly,
without another EOS or changed caloric zeros.

All public pressure limits are Pa absolute. Gas/water/rock temperatures must remain
within the explicit supplied domain inside273.16–380K. Species mass and fluid
volumes must remain positive. The native operational ratios against supplied
overburden pressure are also preserved; they do not calculate salt creep, fracture,
permeability, subsidence or a leak probability. No operating pressure is silently
derived from depth. Well roughness/steel-conductivity inputs required by native
schema do not establish active friction or lateral well heat-transfer models.

The native well is an algebraic prescribed-flow, adiabatic static-column model.
It has no resolved finite wellbore gas inventory or lateral rock heat exchange.
Its signed flow is positive into the cavern and negative for withdrawal. Reservoir
temperature/fluid/pressure are explicit; `follow cavern` is an explicit native
prescribed-flow boundary, not a solved shared nozzle or compressor. No second
choking calculation is added. The real finite inventory is the cavern and water.
The well/cavern enthalpy cut is at the actual native cavern-side well endpoint.

Native mass-flow sample times must cover0 through the requested end plus one
maximum native time step, including native diagnostic evaluations. No extrapolation,
implicit missing interval or normalization of composition is admitted. The source
is an intact rigid cavern of fixed geometry; pressure/displacement or rupture
events do not change its geometry in this level.

## Ground boundary and independent ledgers

UH2SC resolves finite radial rock thermal storage with constant supplied density,
specific heat and conductivity, radial outer heat flow and conductances to a
constant farfield-temperature reservoir. This outer reservoir is an explicit
external heat boundary, not a claim that the entire Earth is a finite closed body.
The native scalar farfield temperature is not a resolved geothermal gradient.
The argument named `modeled_radial_thickness` reaches a constructor that uses
half that value as outer radius. Actual native grid coordinates and capacities
are retained; the wrapper does not relabel this argument as a verified thickness
or silently change its value. Native last-radius resistance remains unmodified.

Independent nodal dual-volume inventories use all `n+1` native ground temperatures,
midpoint control-volume faces, supplied rho/Cp and cylindrical volumes. Both end
node inventories are retained. Native capacities must agree with these geometric
inventories. The native `Cg[idx-1]`/`Qg[idx-1]` indexing is not copied into the audit.

Direct HEOS states give dry-H2 internal energy, pure liquid-water internal energy
and saturated water-vapor internal energy. Native dry pressure, total pressure,
vapor mass and volumes are independently checked against EOS density, water
saturation pressure and phase. Separate common default HEOS references for H2 and
H2O are retained and the same species reference is used at boundaries. No arbitrary
spin/reference conversion or native reported enthalpy is relabeled internal energy.

The result records independent hydrogen mass, total-water mass, fluid U, rock
thermal energy and combined thermal-energy residuals. The boundary ledger includes
signed H2/water mass, cavern-side enthalpy, heat into rock, outer heat out and heat
out to the farfield. Actual well flow is also compared with the integral of the
original supplied piecewise-linear mass-flow history. Native pressure blocking
cannot silently fulfill a different requested history.

Flux integrals use the native implicit-step right-endpoint convention; stored
well flow is a step mean. This is a native discretization audit, not a high-order
continuous-time measurement quadrature. Refine native time and rock spacing
independently before interpreting history accuracy. This is a thermal internal-
energy control-volume audit with explicit exclusion evidence for kinetic,
gravitational, creep/deformation and other mechanical-energy terms. It is not a
complete subsurface work/exergy balance. The ideal well already supplies its own
static-column thermodynamics; no second gravitational temperature law is added.

## Retained native concerns and failures

Static source inspection identified a ground residual loop starting at zero that
uses `Cg[idx-1]` and `Qg[idx-1]`. Its dynamic heat-capacity/flux indexing therefore
needs an independent check. Native cavern output named energy uses an enthalpy
inventory with an additional pressure/expansion convention; the host's independent
U audit does not assume it is exact. Native output may fail those gates. These are
retained static concerns, not locally reproduced numerical failures or corrected
native equations. No coefficient adjustment, omitted end-cell inventory, fitted
correction or alternate engine is used to make acceptance pass.

`UndergroundStorageError` retains the actual native model/solver and its original
solution prefix, raw run return, input object, audited snapshot prefix, last native
time, original exception and complete rejected trace when aggregation exists.
Early native termination, native error logging, incomplete support, invalid phases,
source changes and conservation failures reject the result. UH2SC does not expose
all historical per-step Newton tuples through its completed model API; these are
not fabricated. Native constructor/import failures before an object is returned
retain their cause and inputs, without pretending a model object exists.

Four deferred cases cover uniform equilibrium, nonzero finite rock exchange,
injection/withdrawal and time/space refinement. Nonzero-exchange acceptance is not
assumed. A rejected case writes native raw-prefix arrays and rejection diagnostics
then re-raises; it does not convert rejection to a passing facade test. Independent
apparatus/cavern data, saline properties, site geology, microbiology, well hydraulics,
leakage and coupled geomechanics remain qualification work.

## Selecting a native output series

`trace.native_output_series(description)` selects one unique column from the
original UH2SC independent-output descriptions. The returned
`UndergroundNativeSeries` carries the native and absolute accepted clocks, the
verbatim native description, original native source hashes and immutable values.
`require_current()` checks that the selected column and retained values still match
the admitted trace. The adapter does not parse a description into a new unit,
rename a field, interpolate it, or create a derived operating limit. For example,
the native total-pressure output can be selected for plotting or a downstream
comparison while remaining distinct from measured pressure data. This view adds no
site/geomechanical interpretation and its acceptance case remains deferred.

## Shared finite-source handoff

An admitted `UndergroundTrace` can create
`trace.withdrawal_projection(location=..., representative_state=...,
flow_rule=..., quadrature_evidence_id=..., state_projection_evidence_id=...,
end_reason=...)`. The returned `UndergroundWithdrawalProjection.source` is the
shared `IntervalMassSource` containing only the dry-H2 component withdrawing from
the cavern. It uses the trace's absolute operation-clock samples and requires the
caller-provided `SourceLocation.clock_id` to match the native operation clock.
The selected left-hold, right-hold or trapezoid rule is applied to the accepted
sample rates. A sampled sign change is split at the piecewise-linear zero inferred
between those samples; this is a projection boundary, not a new native solver
event or a resolved within-step trajectory.

The caller must provide a same-property-basis representative dry-H2 state and
evidence IDs for both quadrature and state projection, plus an explicit source
termination meaning. The receipt retains interval H2 mass, a separately computed
dry-H2 enthalpy-flow integral, the representative-state enthalpy projection and
their residual. Water vapor, mixed moist-gas thermodynamics, wellbore dynamics,
nozzle expansion and ambient release behavior are not included. Use
`projection.require_current()` before downstream transfer; this guard checks the
retained snapshot/source mapping and is not physical validation. The
injection/withdrawal deferred case covers this bridge and remains unexecuted.


## Trace issuer boundary

An UndergroundTrace now requires a one-use token minted only after the pinned
UH2SC run and independent audit have completed. Replacing or directly rebuilding a
trace cannot claim that native owner result. Its accepted-clock output-series and
withdrawal projections consume the owner-issued trace; the existing underground
deferred case checks dataclass replacement rejection. This is receipt provenance,
not physical validation.
