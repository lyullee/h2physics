# Native insulation, property capabilities and compression boundaries

Status: actionable local receiving request based on actual native execution. No receiving
implementation, external repository edit or message is claimed.

Target: MIT `lh2dt_models`, reviewed version 0.1.2 at
[`b2f276333c1b1793c39f25763703d196d36742ec`](https://github.com/lyullee/lh2dt_models/tree/b2f276333c1b1793c39f25763703d196d36742ec).
The shared low-level facade extension also concerns this host's property adapter.
Use native Python objects and structural capabilities; no serialization/service layer
or dependency on this host package is required in the receiving engine.

## Reproduction and existing host boundary

Run `scripts/check_insulation_integration.py` against the separately installed native
target described in `docs/NATIVE_INSULATION.md`. `research/native_insulation.md` records
parameters, native/source/test/script hashes, runtimes and retained failures. The native
aggregate Python fingerprint is
`5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.

The host's `Lh2dtVacuumInsulation` retains actual native `VacuumInsulation` objects.
`InsulationEvidence` declares geometry, construction closure, residual gas, absolute
annulus-pressure evidence and parameter origin. `WallHeatAllocation` keeps geometric
area fractions separate from every discrete penetration allocation. `InsulationHeat`
and `PartitionedInsulationHeat` expose signed `BoundaryPower` and original native
results. `LayeredVacuumWallBoundary` passes the actual wall/thermodynamic observation
and an explicit absolute operation clock into state-dependent boundary functions.
`layered_inventory_reader` and existing `ConservedInventory`/`InventoryBalance`
independently check fluid plus explicitly declared wall storage.

An actual three-wall native `LayeredTank` gains 2.11499817898 J over 0.4 s under the
authored heating boundary. A reversed boundary supplies -0.0867690875206 J. Maximum
independent energy residual is about 7.53e-11 J, and the finest accepted-sample external
heat integral differs from native RK integration by about 4.07e-9 J. These are synthetic
software/conservation checks, not qualified construction coefficients or measured heat
leak. They are useful receiving regression cases without authorizing a broader domain.

## 1. Define zero-area wall partitions and return their path accounting

Actual `VacuumInsulation.layered_wall_heat_distribution` accepts nonnegative area
fractions summing to one. Calling it with `(1, 0)` subsequently constructs an insulation
zone with zero area and raises `ValueError: area_m2 must be positive`. The failure occurs
even when the zero-area zone has no localized heat. It is reproduced in the report.

Define this case at the public partition boundary. Prefer support for a zero distributed
area while retaining explicitly allocated discrete paths: radiation, distributed
MLI/support and residual-gas terms must be zero for that zone, while an independently
specified neck/instrument bridge can still carry heat. Do not normalize fractions,
redistribute a penetration or discard its heat. If zero-area zones remain unsupported,
reject them in public input validation with a documented capability result, before
partial zone evaluation. In either policy retain the original failure as regression
evidence and version any change in accepted inputs.

Return a native partition result with stable zone IDs/order, area fractions, explicit
localized-path fractions, supplied temperatures/absolute pressure and per-zone path
terms plus totals. Keep a compatibility route for callers needing the existing tuple.
Expose public wall areas and heat capacities on `LayeredTank`, including connected metal,
so a caller can verify allocation and independent storage without protected attributes.

Minimal original acceptance cases:

- At equal wall temperatures, any accepted complete partition sums to the unpartitioned
  native heat within 1e-10 W absolute or 1e-12 relative. A heterogeneous partition uses
  each actual wall temperature; a law evaluated at mean temperature is insufficient.
- With total distributed solid conductance 0.03 W/K, all other distributed paths zero,
  area fractions `(1, 0)`, a 0.004 W/K neck allocated `(0, 1)`, warm T=290 K and wall
  T=`(30, 40)` K, a supported zero-area policy returns `(7.8, 1.0)` W. The second zone's
  distributed heat is exactly zero; its explicitly allocated neck remains present.
- With no discrete paths the same zero-area zone returns exactly zero heat, or the
  declared unsupported policy rejects the input before evaluating either zone.
- Reversed and equal thermal gradients retain negative and zero path heat respectively.
  Missing/unknown penetration IDs, negative fractions and sums other than one fail;
  no caller receives accepted power from a failed native result.

## 2. Add callable signed external heat to finite pipes

The checked `DynamicHEMPipe.derivative` and `derivative_from_flows` obtain ambient heat
only from the component's fixed `ambient_UA` and `ambient_temperature`. The dynamic node
does not expose a callable signed wall heat boundary. In contrast, `LayeredTank.simulate`
already accepts a public per-wall heat callback. The current host therefore executes
nonlinear insulation on the layered tank and does not turn it into a mutable pipe UA.

Add a native callable wall-heat capability to the finite pipe and its dynamic-network
node. A proposed semantic contract is `external_wall_heat(absolute_time_s, state, thermo)`
returning signed W into the wall, with optional native path diagnostics. Names may follow
receiving conventions, but state, units, clock and sign must be explicit. Preserve the
component's actual fluid/wall state and derivative/result classes and its integrator.

Make ownership explicit: either the callback replaces the built-in ambient boundary or
it is an identified additional source. Reject ambiguous double specification. Separate
wall-to-fluid internal heat from external heat in derivatives, accepted steps and
cumulative ledgers. Every RK stage must evaluate the callback at that stage's actual
wall state and time. Restarts/command partitions retain the absolute operation clock;
callback failure must propagate without selecting fixed UA, insulation or another model.
Keep direct two-boundary and network-flow derivative paths consistent.

Minimal original acceptance cases:

- For an isolated pipe with zero fluid/wall exchange, wall capacity 20 J/K and a constant
  external +5 W over 2 s, mass and fluid internal energy remain fixed; wall temperature
  rises 0.5 K and total storage rises 10 J. Reversing the heat gives the signed opposite.
- With finite fluid/wall exchange, independently sum fluid and wall storage against the
  same external integral; internal heat cancels. A deliberately doubled wall capacity in
  the independent reader fails the fixed ledger budget rather than altering reported heat.
- Connect the actual `VacuumJacketedPipeEnvelope.make_insulation` result using declared
  jacket-reference area, residual gas and absolute annulus pressure. Exercise nonlinear
  radiation and a state-dependent pressure law; record per-path heat and actual native
  input/result identities. Reproduce the constant-UA limit separately.
- Apply a smooth thermal boundary on absolute time 11-13 s and restart within that
  window. Restarted and uninterrupted states/heat agree under refinement without time
  resetting or double-counting command endpoints. The existing analytic layered-wall
  case is a clock/storage reference, not a replacement pipe solver.
- Retain existing fixed-UA results within their numerical tolerances when no new heat
  callback is selected. Fail above the insulation's declared molecular-pressure bound;
  do not extrapolate that gas closure into continuum or ingress/condensation physics.

## 3. Publish layered property capabilities and qualify the fast facade separately

The actual initial attempt to use `Lh2dtLowLevelProperties` with `LayeredTank` failed in
`project_pressure` because `specific_volume_derivatives_ph` is absent. The facade's
existing tested equipment subset does not promise that method. Successful insulation
computations explicitly select original native `HydrogenProperties("ParaHydrogen")`;
there is no implicit provider fallback or invented derivative.

Extend request 001 with constructor-time structural capability/domain requirements for
each selected layered model/closure. The checked layered implementation consumes PH/PT
states, saturation and transport, as well as these capabilities when relevant:

| Native capability | Required meaning / units |
|---|---|
| `specific_volume_derivatives_ph(state)` | dv/dp at fixed h, m3/(kg Pa); dv/dh at fixed p, m3/J |
| `saturation_enthalpy_pressure_derivative_J_kg_Pa(p, quality)` | Coexistence-branch dh/dp, J/(kg Pa); explicit liquid/vapor endpoint |
| `isobaric_heat_capacity_J_kgK(state)` | Phase-qualified cp, J/(kg K) |
| `isobaric_expansion_coefficient_1_K(state)` | Phase-qualified thermal expansion, 1/K |
| `thermal_conductivity_W_mK(state)`, `viscosity_Pa_s(state)` | Qualified phase transport, W/(m K), Pa s |
| Saturation pressure, triple/critical T and specific gas constant | Explicit SI values and provider fluid/spin/reference identity |

Capability presence alone is insufficient. Publish each derivative's supported phase,
pressure/temperature, saturation/critical handling and energy-reference basis. Unsupported
methods or branches must fail before integration with the missing capability/domain
identified. Neither exact-type checks nor native defaults should substitute another EOS.
Expose public wall area/capacity requirements alongside the property contract.

The host may extend its fast HEOS facade only after tests against the complete original
native provider and direct EOS calls. Do not expand that facade by duplicating equations
or routing absent methods to a hidden second provider. Keep phase identity, quality
roundoff policy and diagnostics visible. Preserve earlier equipment/nozzle regressions.

Minimal original acceptance cases:

- A provider missing `specific_volume_derivatives_ph` fails capability qualification
  before `LayeredTank.project_pressure`, retaining the exact missing-method diagnosis.
- Compare direct-EOS derivatives at 200 kPa/20 K compressed para-H2 liquid and
  200 kPa/45 K dry para-H2 gas; independently verify smooth single-phase derivatives
  by converged, domain-bounded perturbations. Fix relative and dimensional absolute
  budgets before running comparisons; never difference across an unresolved phase jump.
- Exercise both saturated endpoints at 200 kPa and the actual one-liquid/one-vapor,
  three-wall tank state used by the insulation check. Preserve the branch convention;
  intermediate-quality saturation derivatives and near-critical states are supported
  only with separately stated evidence, otherwise explicitly unavailable.
- Fast/reference layered initialization, pressure projection, rigid volume, wall/fluid
  state and signed heat/inventory histories agree under time/derivative refinement.
  Use the existing 1e-10 kg / 1e-7 J / 1e-9 relative insulation ledger budgets as regression
  targets, retaining the actual compared results and any failed additional domain cases.
- Normal/para/ortho or energy-reference mismatch is rejected. No derivative check may
  repair its input state by changing a reference, phase, quality or pressure basis.

## 4. Compressor operating maps, machine modes and predicted intercooling

Concrete companion evidence is `research/native_compression.md` and
`h2physics.adapters.lh2dt_compressor`. Its actual native `Compressor` is an adiabatic
fixed-ratio/efficiency thermodynamic point with prescribed positive throughput.
`Lh2dtCompressorStage`, `CompressorEnvelope`, `CompressorStageResult` and
`Lh2dtCompressionTrain` retain native state/results and common `ConnectionTransfer` /
`BoundaryPower` ledgers. `PrescribedIntercooling` supplies outlet T and pressure loss;
it does not predict a cooler's performance. Motor/electrical power is outside that
fluid enthalpy/shaft ledger.

The report exercises 54 ideal-gas-limit points and 72 normal/para/ortho HEOS points.
Three ratio-3, eta-0.8 stages at 1 MPa/300 K and 0.025 kg/s end at 27 MPa. For normal H2,
the adiabatic train requires about 235507.68 W and delivers 929.9074 K; prescribed
300 K inter/aftercooling gives about 156093.91 W shaft and -152542.96 W heat into fluid.
The cooled outlet states are imposed boundaries. The para-H2 exploratory 1e-5 W stage
energy subgate retains a 4.17e-5 W failure separately from the common 0.05 W equipment
gate; preserve both diagnostics when extending the receiving interface.

Request a native map/capacity capability that declares the machine basis, speed units,
mass versus actual/standard-volume flow convention, ratio/head definition, efficiency,
interpolation domain and surge/choke/admissibility evidence. Return actual native map
evaluation and pressure/flow/momentum residuals. The host's current
`operating_point_admissible=None` must stay unavailable until the selected model has
that evidence. A user-declared rectangular envelope or a successful PS/PH flash alone
does not establish a map or close network capacity.

Minimal original map acceptance can use an explicitly authored synthetic ratio map at
speeds `(100, 200)` rad/s and flows `(.01, .03)` kg/s, with ratio rows `(2.0, 1.8)` and
`(3.0, 2.7)` respectively and constant efficiency .8. Declared bilinear interpolation
returns ratio 2.375 at the withheld midpoint 150 rad/s / .02 kg/s. Reproduce the grid
knots; reject 250 rad/s and .04 kg/s without extrapolation or another model; and
independently close one composed network pressure/flow operating point. A
deliberately inadmissible supplied surge/choke marker fails despite a valid thermodynamic
outlet. Synthetic acceptance does not qualify a manufacturer machine map.

Extend request 008's native mode contract to compressors: distinguish running,
coastdown/stopped-but-open and isolated behavior. Current isolated mode requires exactly
zero flow and represents an ideal external isolation boundary, not speed decay or a check
valve. Resolved startup/shutdown requires supplied rotor inertia/loss torque, casing/fluid
inventory, thermal paths, motor work and passive/reverse-flow laws as applicable. Preserve
command clocks, actual native states and unavailable capabilities. A minimal isolated
regression retains zero mass/transport; a supplied finite-rotor synthetic case must close
rotor plus casing/fluid storage against declared work, heat and transported enthalpy under
time refinement. Missing inertia, map or valve data must leave that dynamic model unavailable.

Add a native bidirectional single-gas heat-exchanger level for predicted inter/aftercooling
with explicit hot/coolant states and flows, qualified UA or geometry/transport closure,
pressure-loss basis and capacity/domain evidence. The installed heat-only `Vaporizer`
and saturation-specific `Reliquefier` are not equivalent high-pressure gas intercoolers.
Keep a separately named prescribed-outlet boundary available without relabeling it as a
predicted exchanger. Record coolant-side heat and utility/electrical power separately.

Minimal original exchanger acceptance includes UA=0 with unchanged hot-stream enthalpy,
equal-temperature zero heat, declared heat reversal when stream ordering reverses, and
equal/opposite stream heat within the common equipment ledger gate. A finite-UA case
must obey both streams' enthalpy balances and stated temperature/phase feasibility;
missing coolant/closure inputs or an unsupported phase fails. Increasing UA approaches
the separately declared thermal limit, rather than automatically imposing 300 K.

## Acceptance status and rights

These are requested receiving acceptance cases, not reports of completed receiving work.
First reproduce the pinned baseline and its failures, then version the receiving change
and retain native/reference comparisons and hashes. Do not relax prior budgets to make a
new provider, partition or machine mode appear successful. Actual experimental/vendor
qualification requires separately rights-reviewed data, apparatus/source mapping and
predeclared comparison targets. No source code, published table or private equipment
parameters are supplied by this request, and no external action is authorized by it.
