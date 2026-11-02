# Python API reference

Root-level public imports are lazy: requesting a model returns the original
object from its implementation module and caches that binding. Metadata tooling
can import `h2physics.cluster_validation` without importing numerical engines.
The documented direct submodule imports and `from h2physics import ...` calls
retain their previous meanings.

## Native fluid properties

`solve_isothermal_compressible_gas_flow(..., eos=CoolPropIsothermalEOS(...))`
uses native pressure-dependent density and isothermal derivatives with a declared
held viscosity. Its result keeps a real pressure reconstruction residual and a
separate momentum-integral residual with explicit units; native specific gas
constant is `None`. Omitting `eos` requires an explicit molecular mass and
selects the analytical reference. See HYDRAULICS.md for domain/sonic gates.

The existing `IsothermalPipeCell.from_pressure(..., eos=...)` factory constructs
native quasi-steady network cells without an ideal density calculation.
`IsothermalGasPipeNetwork` uses the same generalized Darcy function and existing
mass ODE. All cells must agree in fluid/spin/version and temperature; distinct
native instances are allowed with their individual definitions retained.
`simulate(..., maximum_step_s=...)` controls the actual integration step limit;
changing output sample times alone is not time-step refinement. Native trace
`require_current()` checks source definitions and retained states/flows.
See ISOTHERMAL_GAS_PIPE_NETWORK.md and the executable
`examples/isothermal_gas_pipe_network.py` for held-viscosity and friction inputs.

Install `h2physics[thermo]` for fluid-property calculations. Use
`h2physics.thermo.CoolPropProperties` for pure-fluid states,
`CoolPropMixtureProperties` for declared mixtures, and `CoolPropMolarEnthalpy`
for species enthalpies with explicit reaction-reference offsets. Existing
CoolProp-derived acceleration tables require their recorded domain and error
qualification; native failures never trigger an ideal-gas fallback.

`IsothermalPipeWaveModel` now defaults to `CoolPropIsothermalEOS("Hydrogen")`.
Its default therefore requires the thermo dependency. Supply another explicitly
qualified EOS through `eos=` when needed. `IdealHydrogenIsothermalEOS` is an
explicit analytical verification reference. Legacy ideal-only linepack and
quasi-steady network types retain their stated mathematical meaning; for native
linepack use `real_gas_linepack.RealGasLinepackState` with the existing CoolProp
EOS. Do not relabel an ideal state as a real-fluid state across a coupling.

The existing `charge_linepack_from_compressor`,
`charge_linepack_from_adsorption_product` and `charge_linepack_from_electrolysis`
APIs also accept the native `RealGasLinepackState`. They reuse its inventory
advance and preserve their original boundary scopes. The unified
`advance_linepack_to_source(..., properties=matched_coolprop_provider)` delegates
native inputs to the existing real-gas source adapter; its result is a
`RealGasLinepackSourceHandoff`, while explicit analytical inputs return the
legacy handoff type. Native source projection still does not infer an interval
enthalpy integral from one representative state.

## Axial annular-cylinder diffusion

`h2physics.materials.AxialAnnulusDiffusion` is a caller-configured axial-only
facade over the shared `DiffusionMesh.planar` and `DiffusionDomain`. Supply an
explicit `HydrogenCarrier`, positive ordered `inner_radius_m` and
`outer_radius_m`, `length_m`, integer `cells`, a temperature-dependent
`diffusivity_m2_s` callback and optional `TrapPopulation` tuple. The facade
retains these inputs, exposes its planar mesh and delegates `simulate()` to the
shared finite-volume owner. Annulus area is calculated as
`pi * (outer_radius_m - inner_radius_m) * (outer_radius_m + inner_radius_m)`;
face areas are constant and cell volumes are area times axial width. The API
does not model radial gradients, r-z coupling, heat or stress effects, changing
cross-section, or coefficient applicability. Its metadata-only Hangang contract
is `axial-annulus-diffusion-geometry-contract`; no physical calculation is
claimed.

## Preferred dispersion receptor alarm handoff

`h2physics.adapters.preferred_dispersion_alarm` binds an accepted
`FacilityDispersionHandoff` from the selected HyRAM+ high-pressure-gas or
SLABx-LH2 liquid-hydrogen-origin route to the existing sampled first-order gas
sensor and concentration alarm engines. The caller declares the expected
`HydrogenReleaseFamily`, source domain (`SourceLocation.source_id`), receptor
frame and clock, receptor concentration mapping evidence, and evidence that a
steady value applies over the exact source window. The bridge rejects family,
domain, frame, clock, or variable source-rate mismatches and retains the
original provider execution. Spatial sampling and interpolation remain
caller-owned; no transient plume, SIS behavior, or safety credit is inferred.
See [`PREFERRED_DISPERSION_ALARM.md`](PREFERRED_DISPERSION_ALARM.md). The
metadata-only Hangang contract is
`preferred-dispersion-receptor-alarm-contract`; no science execution has been
claimed.

`h2physics.adapters.preferred_dispersion_grid` adds
`PreferredDispersionConcentrationGrid` and
`sample_preferred_dispersion_receptor_exact(...)`. The caller exports a finite
static 3D H2 mole-fraction grid tied by object identity to the accepted native
provider result. The sampler requires exact node coordinates, metre axes,
matching source family/domain/frame/clock, and explicit grid/steady-window
evidence; it does not interpolate or extrapolate. Deferred metadata-only
Hangang contract: `preferred-dispersion-exact-receptor-grid-contract` under
`preferred-dispersion`; provider-specific export semantics and scientific
validation remain separate.

`h2physics.adapters.alarm_valve_actuation.execute_alarm_valve_isolation(...)`
composes confirmed concentration-alarm evidence and an existing isolation
schedule with the finite-stroke valve model. It returns the retained
actuated-valve trace and preserves alarm/schedule/actuator lineage. This is a
prescribed response replay, not an online SIS or safety-credit model. Deferred
Hangang case: `concentration-alarm-finite-stroke-valve-actuation-trace` under
`facility-protection`.

## Additional cross-model contracts

`h2physics.adapters.buoyant_layer_h2_alarm` passes the existing two-vent
upper-layer hydrogen mole-fraction trace into the first-order sensor and sampled
alarm components. The caller must explicitly map layer zone to detector
location and clock; this adds no detector or dispersion physics and grants no
protection credit. Its deferred Hangang contract is
`two-vent-hydrogen-layer-concentration-alarm-handoff`.

`h2physics.adapters.pem_ripple_stack` maps checksum-bound, single-cell PEM
current-ripple IV observations to the shared `HydrogenStack` polarization
interface. Cell area, temperature, operating applicability and their evidence
remain caller-owned. The bridge is a diagnostic input path and does not fit or
validate stack parameters. Its deferred Hangang case is
`pem-ripple-iv-to-hydrogen-stack-diagnostic`.

`h2physics.adapters.preferred_dispersion_risk_ledger` joins an admitted HyRAM
high-pressure-gas release handoff to the existing ignition-risk branch only
when the retained source release rate matches the risk binding. It preserves
the native frequency object and performs no ignition or risk calculation. The
SLABx-LH2 path is excluded until this ignition-table applicability is
established. Its deferred Hangang case is
`preferred-gas-dispersion-hyram-ignition-risk-ledger`.

## Finite gas-source snapshots for a fixed-flow receiver

`h2physics.adapters.run_hyram_finite_source_snapshots()` accepts an existing
left-hold `NozzleSourceProjection` and an injected `HyRAMFixedFlowReceiver`.
The receiver must accept a caller-owned H2 source rate and return its admitted
source-plane rate in `HyRAMFixedFlowRun`; the host then checks rate closure
independently from the receiver's solver status. Each positive bin is a separate
steady snapshot and zero bins have no run. The result explicitly reports
`plume_memory_included == False`. The project's `run_hyram_gas_jet()` does not
implement fixed-flow ingestion and must not be presented as doing so. See
[`HYRAM_FINITE_SOURCE_SNAPSHOTS.md`](HYRAM_FINITE_SOURCE_SNAPSHOTS.md).

## HyRAM ignition to conditional-risk branch handoff

`h2physics.adapters.hyram_ignition_risk` provides `bind_hyram_ignition_to_risk`
and `HyRAMIgnitionRiskBinding`. It maps release-relative immediate/delayed
ignition probabilities to a three-way branch partition while preserving the
caller-owned native LOC frequency object. Branch IDs, probability-factor IDs,
partition evidence and per-branch `ConditionalHarmBinding` values are explicit.
The adapter does not load HyRAM or evaluate risk. See
[`HYRAM_IGNITION_RISK_HANDOFF.md`](HYRAM_IGNITION_RISK_HANDOFF.md).

## Isothermal EOS closure for gas waves

`h2physics.thermo.isothermal_eos` provides `IsothermalSinglePhaseEOS` and
`CoolPropIsothermalEOS`. It evaluates mass density from pressure/temperature,
pressure from density/temperature, and isothermal characteristic speed from
CoolProp's isothermal compressibility. It rejects non-gas homogeneous states
and does not substitute adiabatic speed of sound. See [the EOS boundary and
limits](ISOTHERMAL_EOS.md).

`h2physics.real_gas_linepack.RealGasLinepackState` is a fixed-volume,
fixed-temperature gas inventory that evaluates pressure through the retained
`IsothermalSinglePhaseEOS`, including `CoolPropIsothermalEOS`. Its step ledger
checks the integrated port masses against the inventory change. It does not
resolve spatial flow or the heat needed to hold temperature; see
[`REAL_GAS_LINEPACK.md`](REAL_GAS_LINEPACK.md).

`CoolPropMixtureIsothermalEOS(properties)` adapts one immutable,
fixed-composition `CoolPropMixtureProperties` provider to the same protocol.
It uses the mixture's retained HEOS composition and binary interaction settings,
mass-density closure and isothermal compressibility; it rejects non-gas states.
Pass it to `RealGasLinepackState.from_pressure(...)` for a frozen H2-blend
inventory. Composition change, spatial flow and thermal evolution remain with
separate models. The deferred case is
`coolprop-isothermal-mixture-linepack`.

`h2physics.thermo.IsothermalEOSTable.from_eos(...)` samples this protocol on
caller-supplied positive density and temperature axes. The immutable table
provides `density_pt`, `pressure_rho_t` and
`isothermal_sound_speed_rho_t`, with `linear` or positivity-preserving
`log_linear` interpolation and no extrapolation. Both use linear density and
temperature coordinates; `log_linear` interpolates log-positive-property values.
The default `sound_speed_mode="sampled"` interpolates native characteristic
speed independently of pressure. Explicit `sound_speed_mode="pressure_derivative"`
returns `sqrt(dP_interpolated/drho)` using the pressure interpolant's analytic
derivative, with the right interval at internal density knots and the left
interval at the final endpoint. Changing the mode retains the node digest but
changes the full query identity and requires its own qualification. Both modes
remain outside the generalized Darcy and quasi-steady network admission. Call
`qualify_isothermal_eos_table(table, direct_source, ...)` for a seeded,
held-out pressure/density/characteristic-speed comparison and per-query timing
receipt. Construction is not qualification; a passing comparison only measures
agreement with the retained source EOS identity over the sampled envelope. See
[the table guide and limits](ISOTHERMAL_EOS_TABLE.md).
Persist reusable grids with `save_isothermal_eos_table(...)` and recover them
with `load_isothermal_eos_table(...)`. The bounded NPZ embeds canonical TOML
metadata and integrity checks; loading returns the immutable table plus an
optional historical qualification receipt and never regenerates EOS values.
Sampled-mode artifacts retain schema 1; derivative-mode artifacts use schema 2
with an explicit policy. Old v1 query receipts are rejected under the corrected
v2 inverse identity; unqualified historical grids require fresh qualification.
See [the artifact guide](ISOTHERMAL_EOS_ARTIFACTS.md).

## Pressure regulation

`h2physics.adapters.pressure_regulator.ProportionalIntegralPressureRegulator`
converts caller-owned downstream absolute-pressure samples into bounded
`ValveCommand` intervals. Its typed state preserves integral memory, clock and
sensor ownership; conditional-integration anti-windup and caller limits are
explicit. Feed contiguous commands to the existing finite-stroke valve model.
The controller supplies no pressure, valve-flow, sensor-dynamics or facility
response physics. See [`PRESSURE_REGULATOR.md`](PRESSURE_REGULATOR.md).

## Hydrogen ignition probabilities from the native HyRAM+ table

`hyram_default_hydrogen_ignition_table()` captures the installed HyRAM+ default
hydrogen lookup into a typed, content-hashed `HyRAMIgnitionTable`.
`evaluate_hyram_ignition_probability(release_rate_kg_s, table=...)` calls the
native `hyram.qra.ignition_probs` threshold kernel and returns immediate,
delayed and summed release-relative probabilities with the package version and
native source hash. User tables can be provided directly with evidence IDs;
no HyRAM defaults are copied into this project. This is not a facility-specific
ignition or risk model. HyRAM+ is optional and GPL-3.0-only; see the
[adapter scope and limits](HYRAM_IGNITION_PROBABILITY.md).

## Solid-reaction heat port to utility accounting

`HeatDuty.bind(trace, SolidReactionHeatAdapter(), window)` projects exact
caller-prescribed signed heat inputs from an admitted finite solid-reaction
trace into the shared thermal utility API. It checks contiguous command time,
one caloric reference, step-to-total heat closure, and the source's existing
mass/element/enthalpy budgets. It reconstructs inventory energy through the
trace's retained public molar-enthalpy provider at each inventory state. The
duty is an external heat boundary; it does
not claim a heater exists or that the heat is available from another process.
See [solid reaction heat handoff](SOLID_REACTION_HEAT_HANDOFF.md).

## Solid-reaction H2 takeoff to a finite release source

`source_from_solid_reaction_hydrogen(trace, ...)` projects actual accepted H2
withdrawals into `IntervalMassSource` bins. It requires exactly one neutral
gaseous H2 species, no material co-withdrawal beyond the native amount budget,
matching product pressure/temperature and caloric reference, and agreement
between provider molar enthalpy and the supplied H2 `ThermoState`. It uses
exported takeoff, not gross reaction generation. See
[solid reaction H2 source](SOLID_REACTION_H2_SOURCE.md).

## Slab diffusion flux to a finite H2 source

`source_from_diffusion_result(result, ...)` converts the native integrated
right-face mobile-hydrogen flux per area into finite source mass bins using an
explicit surface area and the existing carrier molar mass. It accepts only
outward interval flux; atomic-H transport additionally requires evidence for
H2 recombination. Time origin, fixed source plane and H2 state projection are
explicit because the diffusion result does not model those downstream states.
See [diffusion finite-source handoff](DIFFUSION_FINITE_SOURCE_HANDOFF.md).

## Parcel evaporation to a finite vapor source

`h2physics.adapters.vapor_source_from_parcel_trace(...)` converts the native
cumulative evaporation of an owner-issued `ParcelTrace` into the existing
`IntervalMassSource` interface. It preserves accepted solver times, the exact
vapor `ThermoState`, origin, source evidence and clock/frame identity. The
caller supplies a `SourceLocation` plus explicit evidence for projecting a
moving parcel onto that fixed location. The result checks source mass bins and
issuer freshness on every `require_current()` call. This is a source-boundary
adapter; it does not model downstream dispersion or transfer parcel momentum
to a gas cloud. See [parcel vapor source handoff](PARCEL_VAPOR_SOURCE_HANDOFF.md).

## Linepack withdrawal to a finite release source

`h2physics.adapters.advance_linepack_to_source(...)` advances one existing
`IsothermalLinepackState` step and issues a `LinepackSourceHandoff` whose
`IntervalMassSource` contains the exact integrated outlet mass and interval
clock. The supplied representative gas `ThermoState` must be single-phase H2,
share the linepack temperature and ideal-gas density basis, and use a pressure
inside the accepted endpoint range. Its interval projection evidence is
caller-owned. The receipt checks the original state, ledger, source and
freshness. This creates a finite boundary for existing source consumers; it
does not infer a leak/nozzle law or transient pressure trajectory. See
[linepack source handoff](LINEPACK_SOURCE_HANDOFF.md).

## Compressor discharge to a finite release source

`h2physics.adapters.bind_compressor_discharge_source(...)` carries an
accepted pure-H2 HEOS compressor outlet state into a caller-bounded
`IntervalMassSource`. The caller supplies the leak flow, physical time window,
location and evidence; the adapter checks throughput and mass/enthalpy ledgers.
It does not calculate leak flow, a nozzle state or dispersion. See
[compressor discharge finite-source boundary](COMPRESSOR_DISCHARGE_SOURCE.md).

## Lumped pipeline linepack

`h2physics.pipeline_linepack.IsothermalLinepackState` models a fixed-volume,
well-mixed ideal-gas segment with caller-prescribed interval inlet/outlet rates.
`from_pressure(...)` builds the initial mass and pressure; `advance(...)` returns
a new immutable state and `LinepackStepLedger` with interval mass closure. It
assumes fixed temperature and composition and does not model pipeline waves,
friction or heat transfer. See [pipeline linepack](PIPELINE_LINEPACK.md).

## Segmented transient gas-pipe inventory

`h2physics.isothermal_gas_pipe_network.IsothermalGasPipeNetwork` advances
multiple fixed-volume isothermal ideal-gas inventories coupled by the existing
steady compressible Darcy closure. Signed cell boundary rates are caller-owned;
link flows reverse with pressure ordering. Results retain immutable mass and
pressure profiles, link rates, total-mass residuals, and any localized cell
inventory-floor event. The temperature and composition are fixed, and links
are quasi-steady: no wave, momentum-storage or energy equation is implied. See
[segmented pipe network](ISOTHERMAL_GAS_PIPE_NETWORK.md).

## Isothermal pipeline pressure waves

`h2physics.isothermal_pipe_waves.IsothermalPipeWaveModel` advances cell-average
density and momentum for one constant-area, fixed-temperature segment.
Pass the shared `IsothermalSinglePhaseEOS` hooks for `rho(p,T)`, `p(rho,T)` and
isothermal `c_T(rho,T)`; the default is ideal hydrogen, with the direct-HEOS
CoolProp provider available for a homogeneous gas/supercritical envelope. The
first-order Rusanov update uses a CFL-limited explicit substep and returns
immutable pressure, velocity, density, signed face-flow and mass-ledger arrays.
Ends are closed by default. Optional `FiniteReservoirPressureBoundary` objects
bind caller-owned pressure/time/state histories at either end; the pipe EOS
maps and validates each boundary state, and subsonic ghost characteristics
retain signed boundary flow plus cumulative mass closure. The pressure trace
does not evolve reservoir depletion or add a valve/nozzle law. See
[isothermal pipe waves](ISOTHERMAL_PIPE_WAVES.md) and
[reservoir boundary contract](PIPE_WAVE_RESERVOIR_BOUNDARIES.md).

`h2physics.adapters.isothermal_pipe_observations` maps caller-owned absolute
pressure and signed mass-flow histories to one retained pipe-wave trace. It
requires declared clock, source and sensor-mapping identities; measurement
times must be exact solver samples, while spatial interpolation is bounded to
the represented pipe support. Its uncertainty-scaled residual summaries are
diagnostics only. See [pipeline-wave observations](PIPELINE_WAVE_OBSERVATIONS.md);
no qualified measured H2 pipeline transient dataset is currently available.

`h2physics.isothermal_pipe_network_waves.IsothermalPipeNetworkWaveModel` advances
a connected horizontal graph of pipe finite volumes under a shared fixed-T
`IsothermalSinglePhaseEOS`. Explicit node/edge geometry and provenance are
required. Degree-three-or-higher junctions enforce caller-bounded common
pressure and zero summed outward Rusanov mass flux; terminal wall nodes close
the network. See [branched pipe waves](BRANCHED_ISOTHERMAL_PIPE_WAVES.md) for
the characteristic closure and limits. This host solver is implemented but
unverified; eleven deferred synthetic Hangang contracts across the network
and finite-inventory state modules are not validation evidence. Two contracts
exercise prescribed-pressure history nodes, the pipe-side exchange ledger,
and metadata/support rejection. The boundary
history is caller-owned and does not model source reservoir inventory or
depletion; see [network reservoir boundaries](BRANCHED_ISOTHERMAL_PIPE_WAVES.md)
and [`examples/isothermal_pipe_network_reservoir.py`](../examples/isothermal_pipe_network_reservoir.py).

For an inventory-coupled endpoint, declare the node as `kind="finite_reservoir"`
and pass a `FiniteIsothermalPipeReservoir` in the `finite_reservoirs` map.
Its current pressure comes from mass, fixed volume, fixed temperature and the
shared isothermal EOS. The exact endpoint Rusanov rate advances reservoir mass
and pipe mass with opposite signs. `trace.finite_inventory_mass_kg` and
`trace.finite_inventory_pressure_pa` retain endpoint histories and provenance;
`trace.total_mass_kg` and `trace.global_mass_balance_residual_kg` close pipe plus
finite inventory against any separate prescribed-pressure boundary exchanges.
The prescribed-history `FiniteReservoirPressureBoundary` remains a different
contract with no reservoir inventory balance. See
[`finite inventory reservoir notes`](FINITE_ISOTHERMAL_PIPE_RESERVOIR.md) and
[`examples/isothermal_pipe_network_finite_reservoir.py`](../examples/isothermal_pipe_network_finite_reservoir.py).

## H2SAFE indoor-release observations

`h2physics.data.load_h2safe_indoor_series(path, experiment=...,
expected_sha256=...)` reads one named experiment from the pinned H2SAFE ZIP.
The immutable result retains the archive checksum, repository/license
identities, sensor-position tokens, channel labels, row tokens, and numeric
values with missing observations. Concentration units, sensor calibration,
clock basis, and coordinate interpretation remain unresolved. See
[H2SAFE data notes](H2SAFE_INDOOR_DATA.md).

## High-pressure ignited-jet condition matrix

`h2physics.data.load_ignited_hydrogen_jet_matrix(path)` validates the
DataverseNO X044QK CC0 matrix attachment by exact byte size, MD5 and SHA-256,
then returns 40 source-row-bound experiment conditions. Pressure and
pressure-derived MFR fields retain source-stated units, and pressure basis
remains unresolved. `matrix.summary()` reports source-column extrema only. The
reader does not decode the separate 39 raw histories or six video bundles and
does not calibrate channels. Its deferred Hangang contract checks source
ingestion and summary accounting, not dispersion or overpressure validity. See
[the X044QK data note](IGNITED_HYDROGEN_JET_DATA.md).

`h2physics.adapters.project_ignited_jet_average_source(matrix, experiment_number, ...)`
maps one row's publisher-reported average pressure-derived H2 MFR and declared
release duration to a single finite `IntervalMassSource` bin. The caller supplies
the exact source location, pure-H2 representative state, source clock/start and
separate flow-acceptance and clock-mapping evidence. The adapter carries the
source's average mass flow unchanged and performs no pressure conversion or
nozzle calculation; a constant mean-rate bin cannot reconstruct the missing
flow transient. `IgnitedJetFiniteSourceProjection` retains the matrix, selected
row, source hash and resulting finite source. This prepares a bounded
safety-source input, not dispersion, ignition or overpressure validation. See
[X044QK source notes](IGNITED_HYDROGEN_JET_DATA.md).

## Core-flood branch-specific relative permeability

`h2physics.adapters.build_core_flood_branch(table, ...)` binds one source `Kr`
worksheet to explicit `gas_id`, hysteresis `branch`, flowing `relative_phase`,
exact column headers and field roles, unit/basis/evidence declarations, and a
positive dynamic viscosity in Pa s. It returns a sealed `CoreFloodBranch`;
`evaluate(fractional_water_saturation)` returns a `CoreFloodMobilityPoint` with
piecewise-linear within-domain relative permeability, mobility per intrinsic
permeability factor, raw endpoint values, interpolation weight and source row IDs.
Fraction/percent scale factors are explicit and recorded. No extrapolation,
unit guessing, or branch merge is performed. Optional
`fit_core_flood_power_law(branch, irreducible_water_saturation=...,
residual_gas_saturation=..., endpoint_evidence=...)` produces a sealed,
source-row-bound Corey-type empirical summary with fitted endpoint relative
permeability, exponent and unweighted residual metrics. The endpoints are
explicit caller inputs, the fit uses all rows on one selected branch, and
evaluation is limited to that branch's observed saturation range. This curve
compression does not qualify a reservoir constitutive law. Both APIs remain
unverified against real workbook field semantics; deferred cases use synthetic
data only. See [HYDROGEN_CORE_FLOOD_DATA.md](HYDROGEN_CORE_FLOOD_DATA.md).

## Cryogenic MOF adsorption source observations

`h2physics.data.load_cryo_mof_isotherm(path, dataset=receipt,
expected_sha256=...)` reads one H2 isotherm CSV only after verifying its pinned
dataset identity, exact listed filename, publisher size/checksum and acquisition
SHA-256. `CryoMOFIsothermTable` preserves both adsorption/desorption branches,
source row IDs, raw pressure/uptake tokens and immutable normalized numeric views.
The 20 K coordinate stays normalized pressure and its uptake stays reference
volume with unresolved STP conditions. At 77/87 K the bar-labeled pressure ratio
is scaled to reported Pa with unresolved pressure basis; mmol/g is represented as
mol/kg without asserting excess or absolute uptake. Missing cells remain missing,
and `require_current()` rejects source mutation. This reader does not fit an
isotherm or validate a bed/tank model. See [CRYO_MOF_DATA.md](CRYO_MOF_DATA.md).

`h2physics.adapters.compare_cryo_mof_with_langmuir(table, model, ...)` provides
a pointwise forward diagnostic for exact 77/87 K source rows against the existing
`ExtendedLangmuirIsotherm`. It requires separate caller evidence that the parsed
pressure values in Pa are absolute H2 pressures, that the reported mol/kg values
are absolute H2 loading on the model's exact material-mass basis, and that the
source material identity matches the model. The adapter binds the source table,
model owner, evidence IDs, and source row IDs; `require_current()` rechecks the
bytes and reproduces predictions. It does not fit parameters or interpolate.
The 20 K normalized-pressure/reference-volume representation is deliberately
rejected. This is a diagnostic of declared interpretations, not adsorption or
storage validation.

## Hydrogen concentration sensor time-constant fit

`h2physics.adapters.fit_first_order_sensor_time_constant(...)` estimates the
single response time constant of the existing first-order sensor from aligned
sampled truth and indication histories. Clock, basis, units, episode/source
records, origin, initial indication and search bounds are explicit. The returned
receipt carries the fitted `FirstOrderConcentrationSensorConfig`, source samples
and residual summary, and can be supplied to
`evaluate_first_order_concentration_sensor()`. It does not fit gain, bias, delay,
noise or uncertainty and does not qualify a detector. See
[sensor calibration](SENSOR_CALIBRATION.md).

`h2physics.detector_reliability.evaluate_kofn_detector_reliability(...)`
calculates a heterogeneous k-of-n fail-to-alarm probability over an explicit
mission, conditional on supplied per-detector independent failure probabilities
and a separate common-cause event probability. It does not infer detector
reliability inputs, failure rates or proof-test coverage. See
[common-cause detector reliability](DETECTOR_RELIABILITY.md).

For aligned observed demand windows, `record_kofn_trial_evidence(...)` issues an
immutable, source-versioned table of simultaneous detector outcomes, and
`summarize_kofn_trials(...)` returns empirical event frequencies without
assuming channel independence. The caller supplies source ID/version/checksum,
equal mission duration, detector order, vote rule and unique demand-window IDs.
The attached source hash is provenance supplied by the caller; the adapter does
not fetch the source file or establish that trials are independent.

`interval_for_kofn_trials(evidence, outcome=..., confidence_level=...,
independence_evidence_id=...)` calculates a two-sided exact binomial interval
from those counts when the caller has evidence for independent, identically
designed demand windows. It requires the caller to declare that evidence and
does not verify the sampling assumption. It cannot be interpreted as an annual
rate, future reliability or SIL result. See
[detector reliability](DETECTOR_RELIABILITY.md).

## Facility accident consequence handoff

`h2physics.adapters.run_facility_accident_consequence(chain, evaluator, *,
method_evidence_id=...)` runs an accepted finite-source/preferred-dispersion chain
before passing its exact `FacilityDispersionHandoff` to a caller-owned consequence
evaluator. `FacilityAccidentConsequenceRun` retains the original scenario result,
handoff and existing typed consequence receipt. Chain, handoff or consequence
failures remain failures and retain their stage/context; no consequence physics or
risk probability is inferred. See
[FACILITY_ACCIDENT_CONSEQUENCE.md](FACILITY_ACCIDENT_CONSEQUENCE.md).
The prepared chain captures its declared graph and coupling identity and
exposes `require_current()` to reject post-assembly reconfiguration. See
[FACILITY_ACCIDENT_CHAIN.md](FACILITY_ACCIDENT_CHAIN.md).

## Concentration alarm to valve isolation

`h2physics.adapters.schedule_alarm_valve_isolation(alarm_evidence,
source_commands, ...)` splits the caller's `ValveCommand` schedule at the
confirmed alarm sample plus an explicit latency, then appends a zero-stroke
`isolate` command through the caller-selected horizon. It accepts either one
source-bound concentration alarm or a voted alarm, requires an explicit matching
clock, and preserves the source plan. `AlarmValveIsolationSchedule.require_current()`
checks the original event and command composition. This is schedule composition
only; it adds no online interlock, reliability credit, actuator response or flow
model. See [alarm-to-valve isolation](ALARM_VALVE_ISOLATION.md).

## Oxygen threshold-deficit integral

`h2physics.adapters.integrate_oxygen_threshold_deficit(screen)` integrates the
positive difference between the selected criterion threshold and the oxygen
quantity over its explicitly admitted piecewise-linear sample trace. The typed
result retains interval contributions, total, quantity and units (`mole_fraction*s`
or `Pa*s`) and rechecks the original oxygen-room snapshots. This is an engineering
threshold-deficit metric, not a human-response dose or probability. See
[OXYGEN_DEFICIENCY.md](OXYGEN_DEFICIENCY.md).

## Bounded two-phase mixture inventory flash

`h2physics.thermo.flash_two_phase_inventory_vu(...)` finds one fixed-composition
CoolProp equilibrium packet that matches a declared vessel volume and total
internal energy. It uses native PQ phase packets inside explicit pressure and
vapor-mole-quality bounds and requires at least two caller-supplied branch seeds.
Every seed must converge to the same root within declared clustering tolerances;
distinct roots or failed seeds raise `MixtureInventoryFlashError`. The result
retains native root diagnostics and rechecks species moles, phase volume and total
internal energy through `MixtureInventoryStateAdmission`. `seed_unique_within_search`
means only that the supplied starts converged to the same root; it is not a global
uniqueness guarantee. This static-state API does not advance a separator, integrate
ports, or locate phase events. See [MIXTURE_INVENTORY_FLASH.md](MIXTURE_INVENTORY_FLASH.md)
for this resolver and [finite mixture vessel](FINITE_MIXTURE_INVENTORY.md) for the
separate explicit interval marcher. The host-side adaptive counterpart is
`run_mixture_vessel_ode()`; see [FINITE_MIXTURE_ODE.md](FINITE_MIXTURE_ODE.md).
Receiving-native integration and unrestricted phase appearance remain open under Request032.

`h2physics.thermo.run_finite_mixture_vu_intervals(...)` advances a fixed-volume,
two-phase mixture over caller-declared finite intervals. Each interval supplies
integrated component feeds, phase-selective withdrawals, enthalpy transfers,
heat and pressure-volume work. The outlet uses the retained left-end phase packet;
then the updated component stocks and internal energy are re-flashed with a newly
constructed CoolProp provider at the same volume. Results retain endpoint packets
and interval/cumulative balance ledgers. This is an explicit first-order stepper
with no continuous rate-law integration, phase-event root localization or wall
state. See [finite mixture vessel](FINITE_MIXTURE_INVENTORY.md) and Request032.

## AHSS 1300 measured permeation workbook

`h2physics.data.load_ahss1300_permeation(path, dataset=receipt)` loads the pinned
Mendeley version-1 CC BY 4.0 workbook after matching its publisher metadata, file-list
snapshot and XLSX SHA-256. It returns both worksheets in source order as immutable
time/value pairs with original worksheet row IDs, material and temperature labels,
source author/license and source hash. Install the `data` extra for `openpyxl`.
Actual XML inspection identifies the current header as microamperes;
`current_unit` is `"uA"`. `current_ampere(sheet_name)` returns an immutable
SI-current array using the exact 1e-6 conversion. Both sheets have row-1
headers, with 1260 and 599 observations; the material label is in E3. The API
does not convert current to hydrogen flux, fit diffusivity, or qualify the
steel without exposed area and boundary/initial-state evidence. See `HYDROGEN_EIGENSTRAIN.md` and
`DATA_QUALIFICATION.md` for related transport input requirements.

## Hydrogen-channel measured flow to finite safety source

`h2physics.adapters.project_hydrogen_channel_finite_source(case, ...)` binds
the exact `flow time [s]` and `mass flow meter 1 [g/s]` columns from a
reader-issued `HydrogenChannelCase` to the existing `IntervalMassSource` type.
It converts g/s to kg/s and requires an explicit interval quadrature and
caller-supplied representative H2 `ThermoState` plus `SourceLocation`. The
result retains archive/member SHA-256 values and can be passed to existing
finite-source safety and facility-protection APIs. It does not align sensor
clocks, use ambiguous filling-pressure values, fill missing data, extrapolate,
or calculate dispersion concentrations. See `HYDROGEN_CHANNEL_DATA.md`.

## PEACE alkaline short-stack source observations

`h2physics.data.load_peace_alkaline_raw_file(...)` verifies the declared raw
experiment filename, byte count, publisher MD5 and manifest SHA-256 before
decoding the source CSV. `load_peace_alkaline_column_descriptions(...)` binds
the separate description table through its own four-part receipt. Passing both
to `project_peace_alkaline_observations(raw, descriptions)` returns an immutable
`PEACEObservationBlock`: source-row indices, time tokens, publisher-described
total current/power/voltage, five temperatures, reported pressure, H2 flow and
H2 quality. It retains exact source IDs, labels, description text and both file
hashes. Values remain strings, so no normal-volume conversion, calibration,
clock alignment, or cell-versus-stack interpretation is implied. The result is
a source projection, not a numeric `ObservationTable` or model-validation set.
`normalize_peace_alkaline_channels(block)` adds typed numeric views only for
explicit A, kW, V, °C and bar descriptions (A, W, V, K and reported Pa); each
view retains its raw series and unresolved semantic boundaries. Time, Nm3/h and
quality remain source tokens.
`h2physics.adapters.bind_peace_alkaline_electrolysis_profile(...)` binds a
caller-selected same-row temperature channel with the reported total current
and voltage, then evaluates only those points through the existing
`HydrogenStack` model. The caller declares electrical scope, compatible active
area and series-cell count, and temperature mapping; incomplete rows are
recorded and no interpolation, extrapolation or parameter fitting occurs. The
returned `PEACEElectrolysisTrace` retains the exact model owner and source
hashes; `require_current()` verifies inputs and reproduces each result.
Residuals are diagnostics only and do not resolve whether publisher totals mean
stack or cell quantities.
Loader-issued seals and source reconstruction reject direct construction,
replacement or later mutation of the source/map/projection wrappers. See
`PEACE_ALKALINE_DATA.md`.

## BAM hydrogen-jet-fire numeric channels

`h2physics.data.load_bam_jet_fire_unit_view(...)` reads one permitted measurement
member through the existing DOI/license/archive/member hash checks, then returns
a sealed `BAMJetFireUnitProjection`. Explicit `Time [s]`, `Massenstrom… [kg/h]`,
`[V]`, and `[Bar]`/`[bar]` labels receive seconds, kg/s, volts, or reported Pa
views. Each view retains its exact label and source tokens. Celsius-looking
channels, dimensionless labels and unrecognized channels stay raw when meaning
is unclear. Pressure basis, flow sign/calibration and sensor-voltage mapping
remain unresolved. See `BAM_HYDROGEN_JET_FIRE_DATA.md` and
`BAM_THERMAL_TARGET_MAPPING_GAP.md`; this is ingestion support, not fire-model
validation. A finite source number that overflows during unit conversion is
rejected rather than exposed as a nonfinite normalized channel value.

`h2physics.adapters.compare_bam_plate_temperature_to_target(projection, trace, ...)`
compares one exact fire-reference-plate `[°C]` channel against the existing
`ThermalTargetTrace`. The caller must provide distinct evidence for interpreting
the channel as absolute Celsius, mapping that thermocouple to the modeled target,
aligning the relative source/model clocks, and linearly sampling between retained
model trace points. A selected source-time window and clock offset are explicit;
rows outside target support are rejected rather than extrapolated. The result
retains the rights-bearing BAM unit projection, raw tokens, archive/member hashes,
model trace owner and residuals, and `require_current()` rechecks both owners.
It does not infer incident flux, solve a target model, calibrate a thermocouple,
or establish fire/thermal-target validity. See
[`BAM_THERMAL_TARGET_MAPPING_GAP.md`](BAM_THERMAL_TARGET_MAPPING_GAP.md).

## Pressure and uniform-temperature thick-cylinder stress

`materials.thermoelastic_lame_stress_field` composes the existing pressure-only
Lamé field with a caller-supplied homogeneous isotropic material and spatially
uniform wall-temperature change. `IsotropicThermoelasticMaterial` accepts `E`,
`nu`, linear expansion coefficient, material identity and property-evidence identity.
`UniformCylinderTemperature` requires positive absolute reference/current temperatures,
a condition and evidence identity, and an explicit `free` or `fixed` axial restraint.
The result preserves the pressure/material/thermal identities,
returns radial, hoop, axial and von Mises stress at requested radii, and reports the
net support reaction for the fixed-length case. Do not use it for radial thermal
gradients, end transitions, temperature-dependent properties, plasticity or vessel
qualification; its deferred case has not run. Full derivation and scope are in
`research/elastic_cylinder_development.md`.

## Measured-flow inversion and spatial jet observations

`release_inverse.infer_nozzle_stagnation_pressure` calls the one shared nozzle at fixed
declared T0/area and a supplied absolute pressure bracket. It checks a sampled monotone
single-gas path, target bracketing and final flow closure. `NozzlePressureInference` has
reconstructed origin, an actual `NozzleResult`, equivalent pressure, input evidence,
sampled P/flow, evaluation/iteration counts and mass error. This is source conditioning,
not a measured nozzle pressure or an independent flow-validation result.

`data.hytunnel.load_hytunnel_jet_workbook` returns immutable spatial `ObservationTable`
objects, source hashes, source-row/channel/cell identities and issues. Repeated coordinate
headers, mean/max/min, valid zeros, missing/negative values, statistic-order errors and
gas/ambient-label conflicts remain distinct. `AmbientColumnOverride` needs explicit
per-sheet evidence and marks dependent conditions reconstructed. No override is applied
in the recorded comparison. Pipe overpressure is not silently a nozzle stagnation state.

`adapters.degali.hydrogen_energy_gauge_type` returns an actual native subclass expressing
E as E+C*H2_mass_flux with an identical source-target reference. Native physical tables,
profiles and solvers stay native. Host audits recover the original physical energy and
keep their original scale/limits. `NativeJetRun.physical_energy_flux_w` is read-only.
`JetAudit.native_energy_gauge_shift_j_kg_h2` records the selected numerical reference.
`JetPlane.ground_vertical_coordinate_m=None` explicitly declares an unbounded model;
clearance is then None, without inventing physical source height. The default is zero.

`jet_observations.observe_native_gas_jet` accepts actual native runs, Cartesian points,
frame/origin/evidence and an explicit radial-tail policy. It uses the computed curved
centreline and native radial/state interpolation. The returned `JetPointPrediction`
contains immutable observations and per-point invalid reasons. Dry gas, 200-300 K and
at most 200 kPa are required for mole fraction as the reported sample gas-volume fraction.
Condensing mixture Y remains separate. No axial extrapolation or implicit tail padding
occurs; diagnostic use of a failed audit is explicit. HYTUNNEL_JETS.md contains examples,
the public full comparison, provenance and applicable limitations.

## Native gas-plane and steady-jet composition

`h2physics.adapters.degali.expand_nozzle_gas` accepts an existing `NozzleResult`,
`PropertyProvider`, actual native expander, explicit `SourceLocation`, position basis
and `SHARED_AREA` pressure-area policy. It returns `ExpandedGasPlane`, retaining the
native expansion and one shared nozzle. It checks gas phase, matching spin/reference,
receiving PH state, continuity, effective-area momentum and static-plus-kinetic energy.
No second choking calculation or liquid/ground fraction is introduced.

`JetPlane` declares an orthonormal vertical section in a global frame.
`axisymmetric_boundary` supplies the actual native source/enthalpy factories with a
static enthalpy difference and a separate absolute real-H2 ambient reference. The
receiving pure-H2 ideal reference must be supplied explicitly to `run_axisymmetric_jet`.
`profile_integrated_buoyancy_type(native_type)` returns an actual native calm-only
subclass using that profile's integrated buoyancy; it is an explicit policy using a
reviewed protected Jacobian hook, without patching global or installed code.

`run_axisymmetric_jet(model, boundary, ideal_reference_enthalpy_j_kg=...,
solver_options=..., tolerances=JetTolerances(), require_closed=True)` preserves
native model/result objects, checks four-flux establishment, species, horizontal
momentum, enthalpy-plus-KE, reference and ground clearance. A failed completed result
remains at `JetCouplingError.run`; diagnostic acceptance never sets validation true.
Malformed native arrays/fields retain the actual output at `error.native` without
constructing a misleading physical audit.
`NativeJetRun.radial_observations` returns an immutable spatial `ObservationTable` for
whole-mixture hydrogen mass fraction, bulk density and T. It does not fabricate time,
gas-phase mole fraction or conservative interpolation. Read NATIVE_JETS.md for the
complete working example, failed cold energy case and finite-source limitations.

## Physical identity and state

`PropertyBasis(fluid, reference_id, spin_composition)` identifies the fluid and energy zero.
`require_compatible(other)` rejects a different basis. `ThermoState` stores absolute
pressure, temperature, density, specific h/u/s, phase and optional transport/heat-capacity
properties. Its `enthalpy_identity_residual_j_kg` exposes h-u-p/rho without correcting it.

`PropertyProvider` is a structural Protocol with `basis`, `state_pt`, `state_ph` and
`state_ps`. User-supplied providers can satisfy it without inheriting a framework class.
`Stream` couples a state to a named component/port and signed mass transfer rate.
`MassPartition` enforces conservation of gas, airborne liquid and ground-reaching liquid.

## Thermodynamics

```python
from h2physics.thermo import CoolPropProperties

properties = CoolPropProperties("ParaHydrogen")
state = properties.saturated(150_000.0, vapor_mass_fraction=0.2)
gas = properties.state_pt(5_000_000.0, 300.0)
same = properties.state_ph(gas.pressure_pa, gas.enthalpy_j_kg)
```

The low-level provider reuses one protected AbstractState per instance. The default HEOS
path remains the reference. `QualifiedGasTable` requires an explicit warm-gas envelope,
property-error limits and an energy-identity gate. The current full-envelope benchmark
with inverse inputs fails the strict native-table energy gate; read the recorded result
before selecting a table. The explicit `internal_energy_policy="derive_from_h_p_rho"`
option derives only u and separately reports its adjustment and EOS error. The full
mixed-input comparison passed the declared sampled gates under that option; it does not
establish complete differential consistency or independent EOS accuracy. Passing a small
set of points is not evidence for another envelope.

## Observations and ingestion

`TimeSeries` owns immutable arrays for time, values and validity and retains channel names,
SI units, physical quantities, origin, source and clock. No interpolation, synchronization
or invalid-to-zero conversion occurs automatically.
Reference/measurement `basis_ids` also survive ingestion. Reference-dependent channels
require a matching basis when read through `channel_values`.

```python
from pathlib import Path
from h2physics.core import Origin
from h2physics.data.loaders import Column, load_csv_file

loaded = load_csv_file(
    Path("measurements.csv"),
    columns=(Column("PT", "tank_pressure", "pressure", "bar", "gauge", 101_325.0),),
    time_column="time_s", time_unit="s", clock_id="experiment-01",
    origin=Origin.MEASURED, source_id="reviewed-source-01",
)
pressure, valid = loaded.series.channel_values("tank_pressure", quantity="pressure")
```

`load_delimited` accepts a Python text stream; `load_csv_member` reads a selected archive
member without extracting or executing it. Missing-time omission requires an explicit policy.
`convert_to_si` supports declared quantity-specific conversions. Standard-volume gas flow
requires an explicit reference gas state through `standard_volume_to_mass_flow`.

`data.excel.load_excel_sheet` accepts a declared `ExcelClock` and `Column` objects.
Datetime clocks require an explicit origin; cached formula values are used without execution.
`data.pif.read_property_file` reads the numeric single-line property-file subset. Its
`acoustic_columns` checks declared units and retains unknown values. Neither reader silently
sorts, aligns, normalizes or infers experimental conditions.

The separately admitted Zenodo compilation can be loaded with
`h2physics.data.hydrogen_sound_speed.load_hydrogen_acoustic_dataset(archive_path, metadata_path)`.
It requires the exact reviewed archive and metadata hashes, reads the numeric `.txt` subset
without executing the publisher's bundled reader, and records source row IDs. For a pointwise
diagnostic, use `h2physics.adapters.hydrogen_acoustic_eos.compare_acoustic_file_with_eos(dataset,
member_path, CoolPropProperties(...))`. Select an exact member path and a provider whose spin
basis matches the source metadata. The result records EOS predictions, residuals and excluded
rows and can recheck its source/model binding with `require_current()`. It does not fit EOS
parameters or infer missing source conditions. Historical training overlap is unresolved, so
the comparison is not independent validation; see `HYDROGEN_SOUND_SPEED_DATA.md`.

## Data acquisition

```python
from pathlib import Path
from h2physics.data import DATASETS, acquire_dataset, resolve_dataset

seed = next(item for item in DATASETS if item.key == "hydrogen-channel")
dataset = resolve_dataset(seed)
report = acquire_dataset(dataset, Path("data/raw"), maximum_total_bytes=100_000_000)
```

Repository metadata may arrive in its published JSON/HTML representation; it is internal
acquisition evidence, not the library's modeling interface. Return values are Python objects.
`acquisition_permitted` reflects the initial explicit-license policy, not validation status.
Acquisition receipts preserve omitted and failed files, attribution and file hashes.
`audit_cached_dataset` verifies completed cache files without downloading missing ones or
counting partial files. Etalab-2.0 is admitted with source/update-date attribution.
Receipt replay requires a publisher-issued record returned by
`resolve_dataset(seed)`: `replay_receipt(path, raw_root, dataset=dataset)`.
A manually constructed or dataclass-replaced `Dataset` cannot authorize replay.

The SOE fault-operation record remains metadata-only. Its eleven MATLAB files are
not locally acquired, and channel/fault/time semantics are not established; there
is no source-to-`HydrogenStack` or process-monitoring adapter. See
`SOE_FAULT_OPERATION_DATA.md` and the prepared acquisition request. The deferred
Hangang case verifies the gap manifest without fetching data.

Hydrogen engine HDF5 attachments are retained through their source manifest, while
the existing HDF5 API exposes structure/attributes without loading numeric dataset
values. No figure field is linked to an engine pressure or wall-thermal API until
the documented quantity, location, coordinate and aggregation meanings are supplied.
The deferred metadata case and author request are described in
`HYDROGEN_ENGINE_DATA_LINK_GAP.md`.

The acquired brookite photocatalysis archive has native-header AQY and a reviewed
specific-rate column, but neither is automatically replayed as a photon yield.
`PhotonYield` requires an exact spectral supply fingerprint, geometry, conditions,
and an incident-versus-absorbed electron-equivalent basis; the dataset does not
currently provide row-matched evidence for that bundle. The gap contract is
`tio2-brookite-aqy-model-link-evidence-gap`; the prepared author request is
`requests/photocatalysis_aqy_condition_mapping.md`.
Before creating a cache
directory or downloading bytes it compares the receipt's rights, DOI/version,
metadata digest, supporting metadata, and every attachment name, URL, size and
publisher checksum to that `Dataset`. The editable receipt records prior
acquisition; it cannot authorize new URLs or reuse rights by itself.

For an offline workflow that already has staged Mendeley metadata response bytes,
`dataset_from_mendeley_bytes(seed, snapshot_bytes=..., file_listing_bytes=...,
expected_snapshot_sha256=..., expected_listing_sha256=...)` parses those exact
responses and preserves them in a `Dataset`. The expected digests must come from
an independently pinned source record. This parser deliberately does **not** issue
the private repository marker used by receipt replay; only `resolve_dataset(seed)`
can authorize `replay_receipt`. A source-specific loader must still check its own
publisher identity, metadata/listing digests, and attachment digests before using
the staged files.

For an offline Figshare v2 workflow, `dataset_from_figshare_bytes(seed,
snapshot_bytes=..., expected_snapshot_sha256=...)` parses exact metadata bytes
after checking an independently pinned SHA-256. Like the staged Mendeley parser,
it does not authorize acquisition-receipt replay; a source-specific loader must
validate its own metadata identity and attachment hashes.

`h2physics.data.load_peace_alkaline_raw_file(path, expected_filename=...,
expected_size_bytes=..., expected_publisher_md5=..., expected_sha256=...)` verifies a
manifest-bound raw experiment file before parsing. Its `SourceTokenTable` retains exact
bytes, preamble, headers and semicolon-delimited cells; `require_current()` rejects
changed source bytes. `read_raw_token_table()` remains available for decoded synthetic
or caller-provided text. Both APIs preserve comma-decimal tokens as strings and do not
assign units or map sensors to physical observations. The PEACE raw files are licensed
CC BY 4.0 and kept in ignored raw storage; see
[dataset rights and schema](PEACE_ALKALINE_DATA.md).

## Native LH2DT coupling

`from_lh2dt_state` and `to_lh2dt_state` convert named state fields using a declared basis.
`Lh2dtProperties(native_provider, reference_id=...)` exposes the local property Protocol.
`to_lh2dt_flow(stream, expected_basis=..., factory=MassEnergyFlow)` returns the actual
native flow object. Native solvers are not reimplemented or bundled.

Run `scripts/check_lh2dt_integration.py` after installing the pinned source package into
`artifacts/native_packages`. The script exercises native states and a synthetic tank case.

## Storage, material, electrochemical and reacting models

The detailed [user guide](USER_GUIDE_KO.md) describes parameters, signs, clocks, limitations
and executable examples. Main native interfaces are:

| Interface | Input | Output / ownership |
|---|---|---|
| `storage.VanthoffPlateau` | T, fraction, absorption/desorption branch | Equilibrium hydrogen fugacity; source-specific parameters required |
| `storage.HydrideBed.rates` | `HydrideState`, `HydrideBoundary` | Fraction/T rates, signed uptake and reduced heat terms |
| `storage.HydrideBed.simulate` | time array, initial state, boundary callable | Immutable trajectory and independent boundary-heat quadrature |
| `storage.PorousReservoir.from_property_provider` / `.run` | caller-defined radial geometry, sampled well schedule, shared `PropertyProvider` (including CoolProp HEOS) or explicit density/viscosity callbacks, optional outer pressure | Implicit single-phase pressure history, per-cell inventory and well/outer-boundary mass ledger; direct provider mode requires gas-like states with defined viscosity |
| `materials.PowerLawSolubility` | fugacity, T, explicit carrier | Surface concentration in mol(entity)/m³ |
| `materials.steady_permeation` | solubility, D, thickness, two fugacities, T | Entity/mass/H2-equivalent fluxes |
| `materials.DiffusionSlab.simulate` | arrays, temperature and surface callables | Mobile/trapped fields and boundary/inventory ledgers |
| `electrochemistry.HydrogenStack.evaluate` | current density, T, mode, efficiency | Polarization terms and signed electricity/H2/reaction-energy rates |
| `adapters.evaluate_fuel_cell_trial_exchange` | exact-time H2/O2/H2O trial states, shared stack, reaction energy | Stoichiometric channel source rates and explicit unresolved stack energy; no integrator |
| `adapters.run_cantera_synchronized_fuel_cell` | distinct native H2/O2/H2O ideal-gas phases, stack, caller current controller, thermal model and explicit heat partition | One Cantera 3.2 `ReactorNet`, finite scalar stack temperature, accepted snapshots and component/channel/stack/device energy audits |
| `combustion.run_map_matched_brayton` | caller-owned compressor/turbine maps, speed/flow-link evidence, open-Brayton inputs | Existing Cantera cycle with mapped efficiencies and reported shaft residual; no common-speed solve |
| `combustion.solve_steady_map_operating_point` | bounded multi-start three-unknown map/shaft closure around the existing Brayton cycle | All converged roots and every seed attempt; incomplete or multiple searches withhold a unique answer |
| `combustion.run_cooled_brayton_point` | existing Brayton inputs, caller compressor/turbine maps, explicit air/fuel/bleed rates, cooling path and map correction evidence | Cantera primary combustion plus one compressor-bleed mix at the turbine inlet, frozen expansion, mass/species/energy and shaft ledgers |
| `combustion.run_staged_turbine_cooling` | an issued `OpenBraytonRun`, total air/H2 flows, ordered stage exit pressures and efficiencies, per-stage coolant flows/heat pickup and evidence IDs | Native Cantera frozen expansion at each declared stage, followed by explicit coolant mixing; stage-wise mass/work/heat ledgers and retained terminal state |
| `combustion.run_hydrogen_compression` | Cantera ideal-gas H2 phase, absolute inlet/discharge pressures, temperature, flow, caller efficiency and source evidence | Native isentropic reference and efficiency-adjusted one-stage outlet, shaft-power/enthalpy ledger; optional exact-point linkage to an `OpenBraytonRun` |
| `combustion.run_real_fluid_hydrogen_compression` | Existing `CoolPropProperties` HEOS hydrogen provider and caller T/P domain, absolute pressures, flow, efficiency and evidence | Native PT inlet, PS isentropic reference and PH outlet, single-phase/domain guards, provider/version/basis identity and the shared shaft/energy ledger |
| `combustion.integrate_shaft_transient` | Explicit turbine/compressor shaft-power and load-torque schedules, rotor inertia and evidence identities | One-spool kinetic-energy ODE, integrated component/load/loss work, residual and terminal minimum/maximum-speed events |
| `adapters.cantera.CanteraGas.equilibrium` | `ReactiveState`, HP/UV | Native-library solution snapshot and conservation diagnostics |
| `CanteraGas.closed_reactor` | initial state, times, time-step limit | Chemistry snapshots and energy/element diagnostics |
| `CanteraGas.free_flame` | state, `FlameSettings` | Actual editable Cantera flame object plus immutable summary |

Callbacks operate directly in Python and may close over arrays, material objects or native
equipment providers. Their physical identity, parameter provenance and valid domain remain
the caller's responsibility. No hidden network or serialized model protocol is involved.
The synchronized fuel-cell exchange remains a trial callback payload by itself; the native
Cantera driver now calls it from one shared three-reactor RHS and adds a finite stack scalar
state. The native driver requires caller-owned current and heat-allocation callbacks.
`adapters.FuelCellReactantCurrentLimit` can wrap a demand callback and conservatively taper
current to caller-declared H2/O2 inventory reserves over an explicit response horizon. It is
accepted-trial feedback, not root-localized depletion or validated shutdown control.
See [Cantera fuel-cell coupling](CANTERA_FUEL_CELL_COUPLING.md) and
[FUEL_CELL_TRIAL_EXCHANGE.md](FUEL_CELL_TRIAL_EXCHANGE.md). The Brayton map-pair API reports
a selected-point shaft residual without solving a common-speed operating point; see
[BRAYTON_COMPRESSOR_MAP.md](BRAYTON_COMPRESSOR_MAP.md).

## Non-time observations and fitting

`observations.ObservationTable` holds arrays with `Variable` identities, masks, source-row
and experiment-group identities, per-column origins and a content fingerprint. It does
not invent a time coordinate. `load_observation_table` and `load_polarization_grid` produce
native tables with explicit unit declarations. `reported_pressure` preserves unresolved
semantics despite canonical Pa scaling; it cannot satisfy an absolute-pressure variable.

`split_experiments` separates whole groups. `research.fit_observations` calls a native
prediction function with an immutable parameter mapping and records bounded estimates,
input/model identities, omitted rows and scaled-Jacobian diagnostics. `assess_held_out`
rejects overlap with fitted groups/rows. Fits of unresolved/computed curves require the
explicit curve-reproduction purpose; they do not become independent experimental validation.
See [observation/fitting guide](OBSERVATIONS_AND_FITTING.md) for precise semantics.

## Native PSA-Dyna

`adapters.psa.PsaDynaEquilibrium` accepts the installed native equilibrium callable and
material dictionary. It exposes the `adsorption.AdsorptionProvider` Protocol, preserving
species, material/domain, uptake definition, parameters and derivative axes while converting
bar inputs/Jacobians to Pa. `loading_working_capacity` returns a loading difference only.

`PsaDynaBed` accepts an actual loading-LDF native Bed with an explicit absolute-uptake and
energy-reference basis. Its SI snapshot and native RHS remain accessible in Python.
`BedFaceTransfers` carries component molar/enthalpy transfers per cell face. No PSA schedule,
free-gas correction, cryogenic property closure or energy-reference conversion is invented.
See [native adsorption guide](NATIVE_ADSORPTION.md) and request 005.

`storage.AdsorptionDynamicsInputs` and `integrate_adsorption_dynamics()` add an
adaptive single-species finite vessel with site-resolved LDF uptake, lumped thermal
storage and explicit feed/outlet/heat callbacks. The existing equilibrium provider
and gas EOS remain the property owners. This level is not a spatial bed or a
multicomponent cycle. See [finite adsorption dynamics](ADSORPTION_DYNAMICS.md).
The completed single-species H2 outlet can be projected to the shared finite
source contract through `bind_adsorption_dynamics_to_finite_source()` when
caller-supplied clock and representative-state evidence closes its integrated
enthalpy budget; see [adsorption source projection](ADSORPTION_DYNAMICS_SOURCE.md).

`adsorption.ExtendedLangmuirIsotherm` supplies a caller-parameterized
competitive multicomponent equilibrium provider with per-site capacities and
analytic pressure/optional temperature derivatives. It requires absolute
uptake semantics and remains an idealized isotherm; see
[competitive Langmuir model](EXTENDED_LANGMUIR.md).

## Release and source-plane histories

`release.HomogeneousIsentropicNozzle(properties, search=NozzleSearch(...))` accepts one
`ThermoState` as upstream stagnation state. `solve(state, back_pressure_pa=...,
opening=NozzleOpening(...), opening_fraction=...)` returns `NozzleResult`: upstream,
optional exit state, regime, effective area, mass flux/flow, velocity and search diagnostics.
Its properties expose reservoir withdrawal energy, exit static/kinetic energy and residual,
and thrust under the declared effective-area closure. Gas/liquid/two-phase labels select
state conditions, not separate equivalent solvers.

`SourceLocation` retains source/clock/spatial identities, position and unit direction.
`SourceHistory` retains increasing native sample times, matching results and an explicit
end reason. Its `mass_flow_series()` returns a predicted read-only `TimeSeries`; it does
not supply a phase-to-ground partition or an implicit interpolation/integration rule.

`adapters.lh2dt.Lh2dtBulkNozzleOutflow` is a native flow callback for the existing homogeneous
tank. Scalar or callable back pressure and opening fraction are supported; `sample(t,
native_state)` yields a source result. Phase-selective withdrawal is blocked by the current
native tank energy policy and requires request 001. See [release guide](RELEASE_AND_SOURCE.md),
request 006 and `scripts/check_release_integration.py` for actual coupling and event windows.

## Explicit observation sampling and DisCha data

`load_excel_sheet` now accepts a binary stream as well as a path, separate `header_row`
and `clock_header_row`, and `data_start_row`. `data.preslhy.load_discha_workbook` and
`load_discha_member` apply a checked source-specific layout and retain a workbook hash,
independent recorded series and author-synchronized/original clocks. Pressure basis and
gauge reference are required declarations. Humidity needs an explicit optional scale.

`data.sampling.bin_means(series, edges_s, clock_id=..., minimum_samples=...)` returns
`BinnedSeries` with readonly counts/edges and reconstructed means/masks. `linear_sample`
requires the same clock and a maximum gap; invalid brackets and extrapolation stay masked.
No clock offset, sample independence or statistical uncertainty is inferred.

`data.load_rodare_alkaline_bubble_index(path)` reads the checksum-pinned RODARE
version-1 `Summary.csv` condition index. It returns immutable run/electrode IDs,
absolute cell pressure and signed current density after checking the exact header,
publisher digest and reviewed 60-condition grid. The file has no voltage, bubble
or electrolyte gas-fraction response, so this API does not supply calibration or
validation data for the alkaline bubble-loss model. See
[RODARE condition-index guide](RODARE_ALKALINE_BUBBLE_INDEX.md) and
[measurement-data boundary](PRESSURIZED_ALKALINE_BUBBLE_DATA.md).

`CoolPropProperties(..., quality_roundoff_tolerance=0.)` remains strict by default. An
explicit nonzero budget, capped at 1e-6, permits only a bounded quality endpoint adjustment
and retains `ThermoState.raw_vapor_mass_fraction`. No enthalpy/density correction is made.
Nozzle diagnostics retain the maximum adjustment and count of optional single-phase sonic
refinements. See PRESLHY_COMPARISON.md and RELEASE_AND_SOURCE.md for the full meaning.

## Equipment and native network composition

`equipment.BoundaryPower` carries heat/shaft power positive into the fluid.
`ConnectionTransfer` preserves signed connection flow, actual upstream/downstream-transmitted
states and node/port IDs. Its energy residual is the declared steady enthalpy-only balance.

`adapters.Lh2dtEquipmentNetwork` receives an actual native graph and state factory, with
explicit per-link power readers and provider/reference compatibility. `solve` returns
`EquipmentNetworkSnapshot`: read-only local state/ledger mappings, native solution and
actual `native_component_results`. `EquipmentClosureError.snapshot` retains failed points;
`require_closed=False` allows explicit diagnostic exploration. Missing momentum stays None.

`Lh2dtSharedValve` returns native-compatible fields plus `.native` and `.nozzle`, delegating
all equilibrium flow physics to the shared kernel. Native downstream mixed enthalpy and
nozzle static/kinetic energy remain distinct. `stratified_node_with_heat_ledger` exposes
the existing phase node's two external heat terms without changing its differential equations.
`checked_native(on_solve=...)` validates every native solve; callbacks are diagnostic solves,
not implicitly accepted time samples. The case profile asserts the native accepted-step grouping.

`Lh2dtLowLevelProperties` supplies the verified native flash/saturation/viscosity subset
through one protected HEOS provider and an injected actual native state factory. No tables
or hidden unsupported-method fallback are used. Heat-capacity, conductivity and molar
metadata methods outside that subset are not advertised. Optional host methods now include PU, P-rho, rho-U,
`saturated_at_temperature` and pure-phase/endpoint `phase_viscosity`.
See NATIVE_EQUIPMENT.md and the two new `check_*` scripts for exact construction and limits.

## Stored-device dynamics and command transitions

`dynamics.ConservedInventory` holds fluid mass, fluid internal energy, solid storage and
the explicit property basis. `InventoryBalance` checks each stored change and its integrated
mass/enthalpy/external-heat ledger. `InventoryTolerances` scales against changes and fluxes.
`ScheduledEquipmentCommand(identifier, time_s, apply)` supplies a native Python actuator action.

`adapters.Lh2dtDynamicEquipment(network, nodes, simulator_factory=..., tolerances=...)`
accepts `Lh2dtInventoryNode(native_node, inventory_reader)` bindings. The optional
`lumped_inventory_reader(C_wall, basis)` reads the native pipe/vaporizer fields. Other
native state layouts use an explicit custom reader. All physical equations and integration
remain native. `run(duration_s, time_step_s, clock_id=..., start_time_s=0., commands=(),
continuous_command=None, pressure_solver_max_nfev=300)` returns `DynamicEquipmentRun`.

Accepted `DynamicEquipmentStep` objects retain absolute times, per-node inventories and
balances, checked `equipment` snapshots and the actual native row. Command transitions
retain both before/after hydraulic limits at the same time. An accepted endpoint at a
command time is its left limit; use the transition for its right limit. Accepted native
solutions are selected by identity instead of an assumed RK-stage count. Derivatives must
declare external heat. Failures preserve diagnostics or propagate without clipping storage.
See DYNAMIC_INVENTORY.md for construction, exact clocks, restart semantics and limits.

## Native modes, supply assembly and explicit sampled integrals

`Lh2dtEquipmentMode(component, power_reader)` and `Lh2dtModeSwitch(bridge, modes,
mode_id=...)` select a declared native component through `set_mode`. The returned
`EquipmentModeEvaluation` retains `native`, `mode_id` and `boundary_power`, forwarding
native fields. Each mode shares the exact native property instance and supplies its own
power reader. Errors never select an alternate mode.

`assemble_lh2dt_supply` receives actual native tank/line/vaporizer/pump/restriction/valve
objects, initial states, native factories, delivery state and explicit branch power readers.
It builds the liquid-port topology and returns `Lh2dtSupplyAssembly`: `network`, `driver`,
commandable `pump`, original `outlet`, readonly `node_ids` and `native_models` mappings.
`stratified_inventory_reader(C_lower, C_upper, basis)` reads both fluid regions and walls.
The isolated branch is caller-supplied; an ideal closed valve is not a resolved rotor model.

`integrate_equipment_rate(run, reader, rate_unit=..., integral_unit=...)` applies explicit
piecewise-linear trapezoids to accepted graph snapshots, retaining both limits at each
command. `SampledEquipmentIntegral` retains value, property basis, declared units, clock,
window, interval count and method. Signed rates are not clipped. This is sampled quadrature,
not the native RK-stage ledger; refine it separately. FINITE_SUPPLY.md gives direct Python
construction, replacement, exact result access and the synthetic short/long verification.

## Converged shared Darcy boundary

`hydraulics.solve_darcy_flow(DarcyGeometry(...), density_kg_m3=..., viscosity_pa_s=...,
driving_pressure_pa=..., friction_law=...)` solves positive magnitude and checks final
pressure loss. `DarcyFlowResult` retains flow, velocity, Re, friction, pressure residual
and root diagnostics. `HydraulicConvergenceError.result` preserves an unclosed result,
including a numerical root flag that cannot certify a discontinuous-law gap.

`Lh2dtDarcyPipe` bridges live native geometry/heat/elevation, an explicit viscosity reader,
friction callback/identity and actual native result factory. `DarcyPipeEvaluation.native`
retains that object and `.hydraulic` the optional common-kernel diagnostic. Native HEM
viscosity remains separately owned. The selected friction closure is explicit; no failure
changes it. See HYDRAULICS.md for convention, independent references and the retained failure.

## Complex spectra and native impedance operators

`impedance.ImpedanceSpectrum` holds read-only frequency/complex-Z/mask arrays, unique
source-point IDs, whole-sweep experiment ID, source, response origin, optional separate
frequency origin and context. `.cartesian_observations()` returns the shared
`FREQUENCY`, `COMPONENT` (0=real, 1=imag) and `IMPEDANCE` contract with explicit
exp(+j omega t) whole-cell basis. Correlated projections remain in one experiment group.

`data.pem.load_pem_csv` streams the reviewed source schema with explicit cell/source,
protocol types/counters, active area and phase sign. `PemExperiment.report` retains full
member hash/row count and selected numeric-mask statistics. `pem_spectra` returns
`PemSpectrum` objects with reconstructed DC context, source row IDs and actual gap;
all sweep/DC rules are explicit configurable arguments. See PEM_IMPEDANCE.md for
defaults, exact conversions, source-specific 120 s replay and retained missing context.

`adapters.NativeCircuitOperator(factory, circuit=..., parameter_names=..., parameter_units=None)` accepts the
actual optional native factory. `.evaluate(frequency_hz, parameters)` returns
`NativeCircuitEvaluation(native, frequency_hz, impedance_ohm, parameter_names,
parameter_units)`. It checks native order/output, retains native units and compares them
to an expected contract when `parameter_units` is supplied. Calling the operator
with a Cartesian table/parameter mapping is directly compatible with `fit_observations`
and `assess_held_out`; no serializer or native fit flag is needed. Full measured replay,
bounds, SVD, repeat and coefficient-transfer diagnostics are in `fit_pem_impedance.py`.
R0×area can explicitly feed the shared `OhmicLoss`, subject to operating-point and
physical interpretation limits. No new stack, equivalent-circuit or process solver is owned here.

## Native pools and conservative emitted-mass intervals

`adapters.DeclaredGroundInflow` binds an actual native step history to a finite absolute
window, saturated-liquid state/basis, source location, origin, evidence and termination.
`NativeDynamicPool(runner, reference_properties, engine_id=..., tolerances=...)` accepts
the actual optional runner and config. `.run(..., output_times_s=..., vapor_location=...)`
returns `NativePoolRun`: actual native result/config/input, independently recomputed
`PoolSampleAudit` rows, explicit saturation states and any diagnostic issues.
`PoolCouplingError.native` preserves failures; `require_closed=False` enables inspection
but does not allow inadmissible results to emit a source. Current native fluid is normal
Hydrogen only. No jet deposition, initial radial inventory or restart is inferred.

`PoolTolerances` separates accounting, property, numerical-adjustment, escape and optional
event-clock budgets. The default clock budget is zero. An explicitly positive budget
enables the native input proxy; all corrections and the original native input are retained.
This addresses a reproduced near-knot event/rate inconsistency without another integrator.
See NATIVE_POOL.md and request 010 for the precise limit and receiving fix.

`NativePoolRun.evaporation_source()` creates `sources.IntervalMassSource` from native
cumulative differences. It carries read-only `edges_s`, per-bin `mass_kg`, constant state,
origin, location/evidence and window termination. `mean_rates_kg_s`, `total_mass_kg`,
`enthalpy_transfer_j`, `mass_between(..., clock_id=...)` and `rebin(..., clock_id=...)`
use an explicit constant-mean interval representation. Rebinning preserves the full
window and emitted mass; extrapolation and clock changes fail. Endpoint rates/areas are
not interchangeable with interval means. This is a mass/state boundary, with unresolved
within-bin geometry and momentum retained as missing physical work.

`adapters.PoolNativeEnergyTrace` audits accepted-edge energy records emitted by the
original native pool result. Each edge retains the native accepted state and step
identity; liquid mass, first-law and optional finite-wall balances are recomputed
from cumulative integrals created inside the solver. Synthetic Python records check
the contract only. DynamicLH2PoolX does not currently expose the required integrals,
so its existing result remains rejected.

## Finite reactions and supplied-conversion heat

`reactions.ChemicalSpecies(identifier, elements, molar_mass_kg_mol, phase, charge=0)`
retains an immutable composition. `StoichiometricReaction(identifier, species,
coefficients)` verifies element/charge/mass conservation. `.extent_limits_mol(initial)`
returns reverse/forward finite limits; `.convert(initial, extent_mol)` returns
`ReactionConversion` with read-only molar arrays, named final amounts, mass residual and
explicit endpoint roundoff correction. Missing declared species start at zero; foreign
species or inventory violations fail.

`ReferenceReactionHeat` binds J/mol extent to a reaction's phases, a single T/P, source,
method and measured/computed/synthetic origin. `.heat_j(conversion, temperature_k=...,
pressure_pa=...)` rejects another reaction or extrapolated state. Negative extent reverses
its heat and material signs together.

`MolarEnthalpyProvider` supplies `species`, `basis_id` and
`enthalpies_j_mol(T, P)`. `FunctionalMolarEnthalpy` holds caller functions with one common
formation/reference basis and bounded T/P. `conversion_heat_j(conversion, provider,
inlet_temperature_k=..., outlet_temperature_k=..., pressure_pa=...)` returns H_out-H_in.
`solve_product_temperature(..., supplied_heat_j=..., bracket_k=...)` solves the prescribed
extent's constant-pressure enthalpy balance and retains its residual/reference. It cannot
infer conversion, equilibrium or kinetics from a heat alone.

`adapters.cantera_thermo.CanteraMolarEnthalpy(phase_factory, mechanism_basis,
species_names)` derives actual native ideal-gas species and exposes `native_phase`;
J/kmol is converted once to J/mol. Existing native equilibrium/reactor paths are reused
when those different problems are required. The native provider is stateful; use one per
concurrent worker.

`adapters.rdkit.molecule_from_smiles(..., identifier=..., phase=...)` returns a
`MolecularIdentity` with actual native molecule, canonical identity, species and version.
`data.lohc.load_qm9_lohc_archive` checks the versioned release hash and reads one table.
Use `audit_qm9_lohc_dataset(archive)` for model inputs: it withholds conflicting pair
heats while retaining every original row. `audit_lohc_reaction` is only a row-local check.
See CARRIER_REACTIONS.md for the complete executable example, units and source limits.

## Preferred dispersion providers

`dispersion.HydrogenReleaseFamily` declares high-pressure gas or LH2 release origin.
`preferred_dispersion_provider` selects HyRAM or SLABx-LH2 with no fallback.
`adapters.hyram.run_hyram_gas_jet` injects actual native factories, upstream/ambient
states, opening, location/evidence and solver options; `HyRAMJetRun` retains the Jet,
read-only centreline, upstream/entry H2 flows and separate initialization/transport
residuals. Default rejection retains the native result in `HyRAMJetError`.
`adapters.slabx_lh2.steady_vapor_pool_boundary` connects a constant-rate finite vapor
IntervalMassSource and an explicit fixed footprint to an actual native pool source.
`run_slabx_lh2` retains trajectory/used source, checks the completed native premise and
rejects failed/nonfinite/changed-source cases with `SLABLH2Error`. Read
PREFERRED_DISPERSION.md for exact callable/native inputs, ownership, clocks and limits.

## Parallel pressure/mixture/control-volume additions

`data.pressure_peaking.load_pressure_mat` returns separate SIGMA/GEN3i recorder views;
`iter_blocks` bounds SI conversion and source-row identities. The full numeric MAT decode
is memory-budgeted. `load_pressure_concentration` streams original XLSX metadata, all
17 columns, literal clocks and masked source cells. No pressure-basis conversion or
recorder synchronization is implicit. Read PRESSURE_PEAKING_DATA.md.

`adapters.cantera_properties.CanteraFrozenGasProperties` supplies PT/PH/PS to the shared
PropertyProvider and existing nozzle using an actual native ideal-gas phase. Composition,
native species thermochemistry, reference and unresolved H2 partition are fingerprinted.
Strict composition is default. Optional composition_sum_tolerance plus an explicit
composition_correction_id records a largest-species sum correction for native off-simplex
trial states; negative species are not clipped. Read FROZEN_GAS_PROPERTIES.md.

`adapters.cantera_volume.CanteraOpenGasVolume` composes actual native frozen or reacting gas
reactors, bounded `GasFeed`/`GasVent`/`GasHeatBoundary` objects and an absolute clock.
It retains `GasVolumeTrace.native` objects and signed boundary integrals against finite
mass/species/energy inventories. A vent callback can use the one shared nozzle with a
separate frozen-property phase. It is a 0D thermodynamic reference, with no spatial layers;
read OPEN_GAS_VOLUME.md for examples and exact scope/support/domain limits.
Explicit `chemistry="finite_rate"` adds native reaction-species and independent
element ledgers through the same reactor core. `GasBoundaryRate.phase_access`
selects native-phase or time-only callbacks. Reactive phases own native definitions;
`NativePhaseCopyAudit` preserves source/owned hashes and bounded coefficient
roundtrip evidence. Read REACTIVE_PROCESS.md before applying a gas mechanism.
The completed frozen pure-H2/no-feed/single-vent case can project its named native
mass and outlet-enthalpy integrals to `IntervalMassSource` with an explicit
same-mechanism representative state; see [the vent-source adapter](CANTERA_GAS_VOLUME_SOURCE.md).

## Native insulation, compression and finite hydride storage

`adapters.CompressorAntiSurgeGuard` compares an original `MappedCompressorTrace`
with a source-hashed corrected-speed surge line and caller-declared minimum
corrected-flow margin. It preserves violating points and rejects line
extrapolation. This is a static feasibility check; it does not model surge
dynamics or recycle control. See [compressor anti-surge boundary](COMPRESSOR_ANTI_SURGE.md).

`adapters.lh2dt_insulation.Lh2dtVacuumInsulation` keeps the native heat-law object.
`InsulationEvidence` and `WallHeatAllocation` declare parameter origin, absolute
annulus pressure, wall geometry and discrete penetration allocation. Signed
`BoundaryPower`, actual native results and per-path heat survive evaluation.
`layered_wall_callback` supplies the actual native wall state and explicit clock;
`layered_inventory_reader` closes fluid plus wall energy through existing inventories.
See NATIVE_INSULATION.md for executable composition and retained native gaps.

`adapters.lh2dt_compressor.Lh2dtCompressorStage` and `Lh2dtCompressionTrain` reuse
actual native stages and shared property/state objects. `CompressorEnvelope` is a
declared envelope, not a measured map. `PrescribedIntercooling` supplies outlet PT
and pressure loss; signed duty follows from native enthalpies. Results retain
actual stages, native operating points, power and connection transfers. Throughput
is imposed; native capacity, motor/startup and heat-exchanger hardware are unresolved.
See NATIVE_COMPRESSION.md for the complete example and established error budget.

`storage.finite_hydride.FiniteHydrideBed` extends the existing hydride kinetics with
finite closed gas/solid H2 and two thermal inventories. Inject native gas DU/PT,
fugacity and optional isothermal derivative callbacks via `HydrideGasThermodynamics`.
`BoundHydrogenEnergyReference` makes the bound-H chemical energy explicit on the
native gas zero. Opposite material-enthalpy fluxes close total internal energy;
nominal sorption enthalpy is not added twice. `FiniteHydrideHeatBoundary` declares
clock/support and a state-dependent native Python callback. Traces retain native
EOS objects and the SciPy solution, independent ledgers and gas-floor termination.
See FINITE_HYDRIDE.md; this closed level has no external gas ports or shell operator.

`data.hydride_tank.iter_hydride_tank_blocks` exposes all source rows and first twelve
raw cells as immutable observation blocks, retaining missing clocks and unresolved
MFC/pressure bases. `hydride_summary_cells` separates derived caches/formulas from
measured channels. No formula execution or inferred mass conversion is performed.
See HYDRIDE_DATA.md before connecting the acquired experiments to finite storage.

`adapters.bind_hydride_shell_temperature()` can expose one selected measured
`shell_1`…`shell_5` channel as an existing `FiniteHydrideHeatBoundary`. The caller
must provide a nonempty evidence identity that explicitly authorizes this shell
sensor as the modeled bath boundary. The source `HydrideTankBlock`, source hash,
sensor, clock and mapping evidence remain attached; piecewise-linear evaluation
is limited to the valid measured clock support, and `require_current()` checks
the retained block. No bed-temperature inference, flow-to-mass conversion,
pressure conversion, kinetic fit or hydride validation is implied. The synthetic
Hangang case `ab2-shell-temperature-finite-hydride-boundary` checks this adapter
contract only. See [HYDRIDE_DATA.md](HYDRIDE_DATA.md).

## Pressure protection, vents, recovery and instruments

`adapters.lh2dt_relief.shared_native_relief` composes an actual native Valve
subclass/PressureReliefValve with the one shared nozzle. `Lh2dtReliefProtection`
separates pure accepted-mode trials from transactional native latch commits.
`Lh2dtReliefTankDriver`, `ReliefTankBoundary` and `ReliefEventSettings` partition
actual native tank integration at bracketed pressure opening/reseat and a positive
inventory floor. `ReliefTankTrace` keeps actual native intervals, pre/post event
sources, promoted native objects and independent released-mass/enthalpy/heat ledgers.
See NATIVE_RELIEF.md for construction, initial-state and event-completeness limits.
`adapters.integrate_relief_withdrawal_edge()` integrates one adjacent pair of
original finite-lift results using an explicitly named endpoint trapezoid and
checks selected phase stock against a caller-supplied other-phase change. It does
not provide native quadrature or localize depletion within an edge.

`adapters.lh2dt_vent.Lh2dtVentStack` executes the actual native stack and an explicitly
selected original/shared hydraulic pipe. `VentEnvelope` declares pressure/density/
low-Mach limits; viscosity and sound-speed capability remain native/injected.
`VentResult` retains original/selected native objects, raw oriented heat, common
physical heat power, PH transport outlet, final Darcy/gravity residual and an
independent inverse-UA audit. It is enthalpy-only transport, with omitted-energy
scope explicit. No critical plane, atmospheric velocity or source area is inferred.
See NATIVE_VENT.md before selecting parameters or connecting a dispersion engine.

`adapters.lh2dt_reliquefier.Lh2dtSteadyReliquefier` exposes actual native capacity-
limited cooling toward an explicit saturation-quality target. `Lh2dtDynamicReliquefier`
retains native fluid/wall mass/U, derivatives, steps and dynamic nodes. `ColdSideBoundary`
is an explicit absolute-clock reservoir boundary. Results distinguish total liquid
outflow, net liquid increase and stored liquid; none automatically denotes collected
product. External reservoir heat is not electrical refrigeration power or COP.
See NATIVE_RELIQUEFACTION.md for steady/finite/flowing composition and cap semantics.

`adapters.lh2dt_instrumentation.Lh2dtTransmitter` uses actual native transmitter
initialize/advance/read calls. `TransmitterEvidence` declares variable/unit/basis,
location, calibration/response source and parameter origin. `run` requires a complete
selected process channel plus explicit native initial state/time/location. Outputs
are endpoint left limits for left-held inputs, with native states/readings and
predicted indications/range flags/bounds. Native bounds are not statistical sigma;
measured logger pressure cannot silently become another location's absolute process
pressure. See NATIVE_INSTRUMENTATION.md and request014 for continuation capabilities.

## Spin, finite heat exchange and compressor data

`adapters.lh2dt_spin.Lh2dtOrthoPara` delegates native equilibrium, conversion rate,
held-temperature advance and heat. `SpinEvidence` declares parameter origin and
phase scope; `SpinDomain` checks rotor cutoff convergence. `SpinEnthalpyReference`
defines the chemical enthalpy zero. `Lh2dtSpinCalorimeter` couples the same native
rate to caller-qualified frozen sensible heat capacity in a finite constant-pressure
enthalpy inventory. It is not a rigid-volume pressure/EOS model. Read NATIVE_SPIN.md.

`adapters.lh2dt_heat_exchanger.Lh2dtFiniteHeatExchanger` holds two actual native
fluid/wall inventories in one simultaneous native integration.
`FiniteHeatExchangerSide`, `HeatExchangerCoupling` and `HeatExchangerDomain`
declare separate native states/bases, conductance evidence and admissible states.
`HeatExchangerTrace` retains native states, signed interwall heat and independent
side/global energy ledgers. No process port or representative aggregate pressure
is exposed as a physical prediction. Read NATIVE_HEAT_EXCHANGER.md.

`data.hydride_compressor.HydrideCompressorArchive` opens the acquired versioned
archive with explicit size/member/hash budgets. Its experiment context returns
source-specific logger schemas, immutable `ObservationTable` blocks and original
row/experiment identities. Calendar origin, recorder clock, signed signals, masks,
formulas and selected-cycle provenance remain explicit. No automatic clock alignment,
pressure-reference or normal-flow-to-mass conversion is performed. Read
HYDRIDE_COMPRESSOR_DATA.md before connecting data to storage/compression models.

## Native fire diagnostics, conditional blast and inverse heat

`adapters.jet_radiation.line_source_irradiance` consumes an already admitted
`HyRAMFlameRun`, allocates its native emitted radiative power by visible
centerline arc length, and evaluates point-receiver incident scalar irradiance
with an explicitly supplied atmospheric transmissivity. `LineRadiationPolicy`
requires the source exclusion distance, coordinate frame, atmospheric model and
application domain. The result is not absorbed surface heat and does not add
shadowing, wind tilt, target orientation or injury. It is implemented but
unverified. Only the evaluator can issue its field; direct construction and
dataclass cloning cannot reseal altered irradiance. See JET_RADIATION.md and the
deferred `jet-fire-radiation` cases.

`adapters.hyram_flame.run_hyram_flame` executes actual native Flame/source/radiation
factories with `SteadyFlameWindow` and `FlameAuditPolicy`. `HyRAMFlameRun` keeps
native fields, independent fuel-origin/energy/caloric audits and acceptance gates.
Default physical failure raises `HyRAMFlameAdmissibilityError` with its native
result. Diagnostic irradiance remains explicitly unaccepted; it is not an absorbed
surface boundary. Read NATIVE_JET_FIRE.md, including the replay's intentional exit1.

`adapters.hyram_overpressure.HyRAMBauwensOverpressure` directly calls the actual
native public standalone correlation. `DetonableHydrogenEnergy`, `OverpressureEvent`,
`OverpressureEnvironment` and `BauwensCorrelationDomain` declare participation,
reference, frame/clock and domain. Results keep native class/function/raw output;
they are conditional peak rise and numerical threshold radius, without inferred
cloud, ignition, impulse or a qualified safe distance. Read NATIVE_OVERPRESSURE.md.

`adapters.pifira_heat.PifiraClosedVesselHeat` retains actual native module/TankSpec
and direct-HEOS properties. `ClosedHeatEvidence`/`ClosedHeatDomain` declare scope;
`run` requires complete Pa-absolute pressure and explicit fixed mass/evidence.
`ContentsHeatTrace` records signed contents ΔU/Δt and native/EOS energy defects.
`pifira_effective_area` uses native angular fitting with `EffectiveAreaEvidence`
and explicit `AxialContactGeometry`. Offset/disjoint axial intervals retain their
meaning; zero area is not divided into flux. `ContentsEquivalentFlux` keeps native
unit conversion, both source objects and allocation evidence. Read NATIVE_FIRE_HEAT.md.

`data.thermal_effects.ThermalEffectsFile` slices actual HDF5 source vectors with
bounded blocks and original indices. Quantity/reference, masks, orientation,
unclocked signals and candidate clock relationships remain explicit. Default
reported time is not seconds and cannot become TimeSeries automatically.
Caller clock associations are reconstructed declarations, not measured evidence.
Read THERMAL_EFFECTS_DATA.md before integrating heat, mass or exposure.

## Cryogenic pressure storage, rotor constitutive terms and spherical membranes

`adapters.cryo_compressed.CryoCompressedStorage` composes actual LH2DT tank/wall,
native HEOS property and existing pressure-event objects.
`CryoCompressedGeometry`, `CryoCompressedDomain` and `CryoCompressedEvidence`
declare finite storage, single-fluid/solid-exclusion and parameter boundaries.
`CryoCompressedTrace` retains actual native driver/protection/trace, independent
EOS states and mass/U/wall/event evidence. The shared nozzle owns relief flow.
Opening and positive-floor termination are distinct from stopping at a pressure.
Read CRYO_COMPRESSED_STORAGE.md; no refrigeration cycle or vessel rating is inferred.

`adapters.pifira_spin.PifiraSpinBridge` delegates actual native rotor U/Cv and
strict natural spin kinetics. `RotorEnergyReference`, `RotorEvidence`,
`RotorCutoffPolicy`, `MilenkoAdmission` and `SpinMedium` retain reference,
phase/density scope and primary/native admission differences. Constitutive
terms keep absolute rotor storage separate from frozen-composition corrections;
enthalpy mapping requires `SpinPVAssumption`. There is no new trajectory ODE
or evolving-spin liquid EOS. Read NATIVE_SPIN_THERMOCHEMISTRY.md before energy coupling.

`materials.DiffusionDomain` is the shared planar/spherical mobile/trap solver.
`DiffusionMesh` supplies true volumes, surface areas and integrated homogeneous
radial resistance. `FiniteSurfaceInventory` supplies an amount in mol of the
wall carrier and a boundary callback. `TransportBoundary` requires one owner
per face. `TransportResult` retains actual SciPy output, fields, amounts and
total-molar ledgers. The existing `DiffusionSlab` preserves its mol/m2 API by
delegating to the unit-area shared mesh.

`storage.MicrosphereStorage` couples that kernel to the existing native
`HydrideGasThermodynamics` density/T/fugacity capability. `MicrosphereDomain`
checks gas phase, T/P and positive moles. Inputs include qualified D(T),
`PowerLawSolubility`, geometry, prescribed uniform temperature and one exterior
fugacity or explicit `SurfaceCondition` callback. `MicrosphereResult` retains
cavity states, wall storage, gas/exterior transfers, mass and clock/evidence.
This is prescribed-temperature transport; no heat-duty or stress prediction
is implied. Read MICROSPHERE_STORAGE.md for units and executable examples.

`data.fermentation.FermentationWorkbook` streams the reviewed version2 worksheet
into per-reactor `FermentationBlock` objects with `ObservationTable`, original
cells/row identities, missing-value reasons and independent clock bases.
`component_production_check` checks same-export volume-rate algebra, retaining
reconstructed origin. It does not supply independent gas yield, biological
kinetics, a gas reference state or inferred reactor volume. Automatic TimeSeries
conversion is rejected. Read FERMENTATION_DATA.md and request017 before fitting.

## Photon, multiphase and cyclic separation contracts

`photochemistry.PhotonSupply` accepts explicit flat wavelength bins or discrete
line powers. `BeerLambertPath` binds per-band absorption/reflection to the exact
spectral grid/representation. `PhotoConditions` and `PhotonYield` bind the
prescribed incident/absorbed electron-equivalent response to actual light and
catalyst/medium/mass/T/P/geometry evidence. `photon_hydrogen_rate` retains optical
and photon ledgers and enforces its per-band single-electron budget. Diagnostic
failure does not authorize finite conversion. `SteadyPhotoWindow` and
`convert_photon_exposure` reuse `StoichiometricReaction` and optional compatible
native/functional enthalpy, without another reaction integrator. The thermal
result is an isothermal boundary requirement, not a predicted utility or proof
of thermodynamic feasibility. `assess_photo_gibbs_energy` can integrate a
caller-supplied `J/mol reaction` affinity path over the exact extent and return a
photon-only necessary energy bound against absorbed joules; the caller owns
chemical-potential values, phases, path resolution and evidence. A passing bound
does not imply sufficient photon exergy, heat/work coupling, kinetics or device
performance. Read PHOTOCHEMISTRY.md.

`data.photocatalysis.PhotocatalysisArchive` streams all reviewed TXT members
with native line/column/header identities, independent x grids, categorical
labels, masks and duplicate/study groups. `PhotocatalysisMappingEvidence`
separates caller-reviewed source column/unit meaning from raw observations.
Reported rate/AQY mappings are reconstructed; unknown optical and errorbar
meanings remain unknown. They do not construct photon supplies or fitted
kinetics. Read PHOTOCATALYSIS_DATA.md before a model comparison.

`adapters.cantera_multiphase.CanteraMultiphaseEquilibrium` uses actual Mixture
equilibrium and independently owned native phases. `EquilibriumPhase` binds
source/reference/domain, `MultiphaseFeed` preserves finite SI amounts and
`MultiphaseSettings` selects the native solver explicitly. Results retain
source/owned phase copy audits, snapshots, extensive material/energy/PV and
threshold-qualified chemical-potential evidence. `MultiphaseEquilibriumError`
keeps partial/completed actual native objects and cause. Native HP candidate
failure is preserved without deleting a phase or substituting a gas solve.
Read MULTIPHASE_CONVERSION.md; equilibrium is not gasification kinetics.

`adapters.psa_cycle.PsaDynaCycle` accepts native Python case mappings with
`PsaCycleNative`, `PsaCycleEvidence` and existing adsorption basis/domain. It
executes the actual native scheduled multibed runner and verifies every retained
slot checkpoint through the existing `PsaDynaBed`. `PsaCycleRun` keeps state/
clock/ledger/schedule/native metadata and a separately identified audit Network.
The current native entry point requires internal managed file I/O; original
integrator Network/OdeResult and arbitrary Python callbacks are unavailable.
Host H2 metrics require native H2 reporting. Startup export/feed ratio, native
state CSS and a qualified cyclic recovery remain distinct. Read NATIVE_PSA_CYCLE.md
and request018 for original-object and reference/stream requirements.

## Porous transport and finite thermal conversion

`adapters.cantera_membrane.CanteraDustyGasTransport.flux(left, right, geometry)`
returns actual native `DustyGas`, immutable endpoints, raw kmol/(m2 s) and signed
SI species mol/(m2 s). `MembraneEndpoint` requires exact full species order and
already normalized X or Y; `PorousTransportGeometry` requires explicit porosity,
tortuosity, pore radius, permeability and thickness. The stationary-solid total
flux includes Darcy flow. It cannot be normalized as a product composition.
See NATIVE_MEMBRANE_TRANSPORT.md for construction and applicability.

`adapters.cantera_caloric.CanteraMultiphaseMolarEnthalpy` implements the existing
`MolarEnthalpyProvider`. Supply native `EquilibriumPhase` factories, phase/species/
host alias mappings and `SolidDensityEvidence`; gas and solid references must
be compatible. The actual privately owned phases and gas caloric providers
remain accessible and guarded. See MULTIPHASE_CALORIMETRY.md.

`thermochemical.FiniteThermochemicalCycle(provider, evidence).run(initial, stages,
carrier_species=..., require_full_inventory_closed=...)` reuses shared finite
`StoichiometricReaction` conversions. Each `ThermochemicalStage` applies finite
pre-withdrawal, finite feeds at their supplied T, endpoint conditioning and
prescribed reaction extent, in that order. The trace retains actual provider,
shared conversions, stage/global element/mass/H ledgers, carrier/T/full-inventory
closure flags and positive/negative heat totals. `ThermochemicalCycleError`
retains stage, previous state, accepted prefix, partial conversions and cause.
No reaction rate, separator performance or heat-recovery credit is inferred.
See THERMOCHEMICAL_CYCLES.md for a complete Python example.

## Native isothermal biological process

`adapters.biological.QsdSanNative.from_installed()` admits the separately
installed reviewed source; `QsdSanAdm1Digester` takes actual components/ADM1,
`Adm1Geometry`, `BiologicalEvidence`, full liquid/headspace initial mappings,
constant feed and `BiologicalAudit`. `run(start_time_s=..., end_time_s=...,
sample_count=...)` retains actual System/reactor/model/components/OdeResult,
separate native accepted and dense sample clocks, component/COD/C/N and H2
formation/consumption/export ledgers. Native measured-basis kg can be COD
rather than real mass. Energy/wet-water/full-H/O closure is unavailable.
Pressure/sample audit failures retain actual native trajectories and cause;
secondary restoration errors cannot replace the primary failure. See
NATIVE_BIOLOGICAL_PROCESS.md for complete inputs, units and isolated installation.

## Finite membrane, hydride ports and independent-input analysis

`adapters.cantera_membrane_device.CanteraFiniteMembraneDevice(transport).run(...)`
uses the existing `CanteraDustyGasTransport` and explicit finite volumes, gross
area, clock support and integration settings. The actual native reactors and
one ReactorNet retain signed species transfer, partial-H and required thermostat
Q; sampled side U/species and combined inventories are checked independently.
Both sides have the same prescribed T; energy-off is accompanied by required
heat rather than an adiabatic claim. See FINITE_MEMBRANE_DEVICE.md.

`storage.finite_hydride.FiniteHydrideBed.snapshot_from_inventory(...)` and
`.rates(snapshot, heat, gas_mass_flow_kg_s=..., gas_enthalpy_flow_w=...)` expose the
same existing rate/reference core used by closed simulation. External net gas
flow is separate from total gas derivative including sorption. Its fixed-T mode
retains variable-mass thermostat duty. `storage.hydride_compressor` composes that
core with actual finite native vessel derivatives and the shared nozzle in one
integration. Stages, geometry, heat, valve openings, clocks, initial states and
native/evidence objects are supplied directly; no JSON/server is required.
See HYDRIDE_COMPRESSOR.md for construction, ledgers, events and startup limits.

`uncertainty.ParameterDistribution` binds a `Variable`, frozen native SciPy law,
source/origin, physical admission and an immutable native-definition snapshot.
`IndependentParameterSpace` requires an independence source. `UncertainModel`
accepts a callable returning a declared mapping or `ModelOutput(values, raw)`.
`independent_qmc_design`, `propagate` and `sobol_sensitivity` preserve actual
coordinates/cases/native statistical results. No failed case is replaced or
dropped. Coordinate changes inside a callback reject before stale result binding;
invalid returned responses retain failed raw objects and values. Constant,
underflow and native scalar-shape failure meanings remain distinct.
See UNCERTAINTY.md and install the optional uncertainty extra for its engine floor.

`data.embrittlement.EmbrittlementCollection.iter_blocks(...)` returns typed
`ObservationTable` plus complete records; `composition_observations` preserves
the separately linked composition representation, and `paired_property_check`
checks same-export arithmetic. Property, reference atmosphere, exposure and
material roles remain explicit. See EMBRITTLEMENT_DATA.md for units/dependence.

## Safety endpoints and actual native consequence objects

`adapters.detonation` uses actual native Caltech SDToolbox/Cantera objects for
CJ equilibrium endpoints and frozen shocks. Inputs include the actual source
phase, explicit thermochemical basis/admission and `DetonationEvidence`;
missing evidence rejects before native work. Managed native-file bridging and
unavailable internal fit/sound states are explicit. See NATIVE_DETONATION.md.

`adapters.hyram_exposure.HyRAMExposure` accepts `ExposureHistory` or
`PressurePeak` and explicit `NativeHarmSelection`. It returns actual native
calls/scalars, dose/fluence/peak/impulse, original input/selection, coordinate/
clock/support metadata and source/evaluation signatures. `verify_result`
reexecutes the existing native path and preserves the original object on success;
replaced summaries/model/mean/raw records are rejected with actual replay/cause.
See NATIVE_EXPOSURE.md. Absorbed-dose-only diagnostics cannot supply harm.

`adapters.conditional_risk.ConditionalRiskNative.from_installed()` exposes
actual native request/context/output/receipt classes. `conditional_risk(...)`
takes native typed `RiskInput`/`Context`, original `IntervalMassSource`, explicit
`RiskReceptor`, branch `ConditionalHarmBinding` and `RiskBindingEvidence`.
Computed harm is audited through its owner before binding. Actual source state/
location/basis types and nested physical contracts are checked. All objects,
source/field windows and native evidence/credit ownership survive composition.
No frequency or source-to-field physics is inferred. See CONDITIONAL_RISK.md.

`data.shock_tube` supplies source-specific bounded views of actual BLEVE signal
CSV files and run metadata. Pressure is reported output with unresolved source
reference conflicts, and clocks stay recorder-specific. Duplicate/masked data
cannot be silently repaired into a native source or exposure waveform. Read
SHOCK_TUBE_DATA.md for actual names, schemas, masks and admitted conversions.

## Oxygen, thermal physiology and learned residual consumers

`CanteraOxygenRoom.run` composes the existing native finite gas-volume owner
with actual `OxygenFeedAdmission`/`IntervalMassSource` objects, compatible native
formation/caloric reference, exact command partitions and existing vents/walls.
It returns actual native traces/networks, O2kg/mol, wet/dry mole fraction,
pO2Pa and signed mass/species/U/pressure/source ledgers. `OxygenCriterion`
requires explicit quantity, low-side comparator and pressure/elevation evidence;
its sampled reconstruction is not a physiological response or exact event root.

`NativeJOS3.prepare_neutral(ThermalSubject)` returns an actual prepared native
object; `JOS3ThermalResponse.run` copies a prepared object and consumes contiguous
`ThermalInterval`/`OrdinaryAirEnvironment` records under `ThermalRunEvidence` and
`ThermalDomain`. Host snapshots use K; original native outputs retain degC and
rounding. Native capacities, objects, node/channel indices and original failures
survive. The native global rate limiter/custom heat boundary is not admitted.
No injury probability or cold-H2 convection is derived from these states.

`residual_batch` binds original same-clock TimeSeries, explicit Variables,
physical locations/scales and retained prediction owners to actual native
SignalBatch/ObservationTable. `NativeResidualMonitor.fit`, `.calibrate` and
`.evaluate` keep disjoint whole-run groups and actual native learned/scaler/
threshold state. Masked/gapped/unseen-mode samples abstain. A monitoring score
has the configured residual-reference meaning, not a leak identity or risk rate.
Detailed interfaces and executable examples are in the three domain manuals.

## Unverified development interfaces

The following APIs are code, not executed scientific evidence:

- PVElectrolysis.operating_point/run: actual optional pvlib I-V + existing
  HydrogenStack polarization/Faraday, shared conversion, finite stocks and native
  receiver. Product pressure, Gibbs inclusion and unresolved external work are
  explicit; direct DC is not a hidden AC/rectifier/MPPT path.
- HelprFatigueLaw and finite fracture composition: actual HELPR constitutive
  objects, caller SI SIF, ordered load/cycle/environment, SciPy integration and
  explicit size/fracture/arrest criteria. No growth/fugacity equation is copied.
- FiniteSolidReactionReactor: actual shared ThermochemicalCycle/conversion,
  supplied rate/enthalpy basis, finite feed reservoirs, optional takeoff and
  solved fixed-P thermal endpoint. No material-specific kinetics or liquid-water
  property database is guessed.

The three manuals describe exact constructors, callback units, objects retained
on success/failure and unresolved physics. Examples and ValidationCase handlers
are unexecuted. cluster_validation provides Python metadata/results and writes
unsubmitted PBS arrays; it does not connect, install, submit or run on discovery.


## Parallel coding continuation — 2026-10-28

Four additional partial families have code: conditional finite pool fire,
HELPR vessel-failure initiation, physical-window/native hydrogen economics,
and saturated parcel transport. All are `implemented_unverified`. Coding
inventory is66/72 (about92%):21 partial implemented,38 historically checked
native adapters,7 unverified and6 planned. Last executed coverage remains59/72
(about82%) at6eae06c; full-programme effort remains an uncertain30-40%.
No local scientific execution, benchmark, test, build or remote submission was
performed for this continuation. Old1088pass results do not validate new code.

The new19 deferred cases comprise8pool fire,4vessel,5economics and2parcel cases;
the combined pending campaign has41 cases. Native HELPR vessel cases reuse the
fracture profile. Pool, economics and parcel profiles require separately declared
cluster interpreters/setup files; the example plan has no guessed login/queue.
No cluster connection or `qsub` was attempted.

Read [POOL_FIRE.md](POOL_FIRE.md), [VESSEL_FAILURE.md](VESSEL_FAILURE.md), [HYDROGEN_ECONOMICS.md](HYDROGEN_ECONOMICS.md) and
[DROPLET_TRANSPORT.md](DROPLET_TRANSPORT.md) for contracts. Incident liquid is not pool deposition;
wall-failure initiation is not a hole or blast; supplied ignition/burn flux is
not a predictive pool-fire solver; explicit annual financial inputs are not
inferred product sales. ProFAST was rejected on redistribution/use terms;
optional pyH2A is statically reviewed and remains unexecuted. Request024
records native API and qualified-data work for other sessions.


## Cavern, microbial cell, impact and material front — coding checkpoint

Four further partial first levels now have code: actual UH2SC cavern/rock audits,
native-electrode finite microbial electrolysis, finite surface-impact phase and
mechanical energy, and a native premixed material-path front reference. All are
`implemented_unverified`. Code inventory is70/72 (about97%):21 partial implemented,
38 historical native-adapter checks,11 unverified and2 planned. Last executed
coverage remains59/72 (about82%) at6eae06c. Full-programme effort remains an
uncertain30-40%; more code does not establish independent physical validity.

New21 deferred cases comprise4underground,5microbial,8impact and4front cases.
The combined pending campaign is62 case definitions. No model, example, case,
test, replay, benchmark, build, installed replay or cluster job was executed.
The static syntax/lint/source/license review is not numerical acceptance.

UH2SC's suspected GHE indexing/capacity/energy conventions are retained for strict
independent rejection rather than patched. Its well is ideal/prescribed-flow,
not a finite well inventory. MEC organism/activity/thermochemical data remain
qualified caller inputs. Impact contact/outcome data and a continuous finite-wall
pool handoff are unresolved. The front is a material-frame discrete reference,
not lab flame propagation, obstacle flow or a person heat-injury prediction.
Preferred HyRAM gas and SLABx-LH2 liquid-origin ownership remains unchanged.

Read UNDERGROUND_STORAGE.md, MICROBIAL_CELL.md, DROPLET_IMPACT.md and FLASH_FRONT.md.
Request025 records specific native APIs, evidence and coupling work. CORA DOI
10.34810/data2866 is now acquired and schema-audited; its electrode observations
do not measure full-cell MEC hydrogen output or biological activity. Raw assets
remain excluded from public distributions pending file-exception review; details
and hashes are in `research/microbial_electrolysis_data_candidate.toml`.

At this historical checkpoint, obstacle-resolved dispersion and accepted jet fire were listed as planned. The current catalog marks zero families as planned; every partial family retains its limits in MODEL_CATALOG.md. Historical code counts here do not indicate complete models. Later source/artifact acceptance is still deferred.


## New unexecuted integration interfaces

Read [OBSTACLE_DISPERSION.md](OBSTACLE_DISPERSION.md) for actual optional FDS
case/mesh/source/process/ledger interfaces, [JET_FIRE_CONSERVATION.md](JET_FIRE_CONSERVATION.md)
for rejected-native-path energy diagnostics, [MICROBIAL_ECONOMICS.md](MICROBIAL_ECONOMICS.md)
for the actual MEC-to-existing-cost-owner bridge, and [CLUSTER_EVIDENCE.md](CLUSTER_EVIDENCE.md)
for read-only selected-result reconciliation. These source additions have not
been executed. The76pending case definitions do not establish model accuracy.

Request026 specifies native reacting-establishment/chemistry/radiating-energy,
CFD build/runtime/source boundaries, a provider-neutral cost protocol, public
MEC geometry/result verification and separate campaign acceptance. Source/plan,
clock, material, phase and energy-reference ownership remain explicit. Preferred
HyRAM/SLABx ownership is unchanged; no failed native prediction is promoted.

Current unexecuted API checkpoint: see CANTERA_FACTORY.md, HYDROGEN_ECONOMICS.md, MICROBIAL_CELL.md and MICROBIAL_OBSERVATIONS.md; execution status is recorded in PROGRESS.md.

Producer-issued physical results share the read-only fingerprint primitives in
[RESULT_PROVENANCE.md](RESULT_PROVENANCE.md). Domain producers retain their own
admission and lifecycle rules; downstream code calls `result.require_current()`
instead of minting a result from matching field values.

Exact caller-owned provider registries are documented in
[MODEL_SELECTION.md](MODEL_SELECTION.md). `ModelRequest` names one family,
physics level and provider and explicitly admits status, capabilities and
evidence. `ModelSelection.build()` calls only that exact registered factory;
missing or failed providers never trigger an alternative.

New unexecuted composition contracts are documented in
[FINITE_FUEL_CELL.md](FINITE_FUEL_CELL.md),
[FINITE_TRANSFER.md](FINITE_TRANSFER.md) and
[THERMAL_UTILITIES.md](THERMAL_UTILITIES.md). They reuse the shared
electrochemistry/thermochemical kernels, native LH2DT inventory network and
already reported heat duties. They do not introduce a polarization law,
refuelling protocol, utility solver, COP or automatic annualization.

`FiniteAdsorptionVessel` combines provider-owned absolute uptake with free gas
from an admitted property provider. `FiniteStrokeValve` composes an explicit
stroke clock and evidence-bearing effective-area map with the shared valve.
`FiniteLiftRelief` adds accepted-sample lift, leakage and caller-owned phase
pickup without replacing the native latch/nozzle. `FacilityContinuityAudit`
checks original equipment transfers against declared node storage and external
rates. All four are unexecuted and infer no control law or missing boundary.

`FiniteSpeedPump` and `MappedCompressor` admit original native results against
caller-supplied evidence-bearing maps and explicit speed clocks.
`FlowingHeatExchangerAdmission` binds two original process transfers to a finite
closed-side witness without introducing another UA/NTU solver.
`FiniteReliquefierProduct` records feed/product/return/vent allocation and debits
an explicit cold budget. These source-only APIs infer no vendor performance,
controller, COP, separator or spatial exchanger physics.

## Hydrogen concentration-induced cylinder stress

Use `HydrogenConcentrationEigenstrainProfile` and `radial_hydrogen_eigenstrain_cylinder()` for a caller-supplied radial concentration mapped to isotropic linear eigenstrain. Results are solver-issued and support `require_current()`; negative and nonfinite concentrations are rejected. See [HYDROGEN_EIGENSTRAIN.md](HYDROGEN_EIGENSTRAIN.md).

For an exact-time quasi-static sequence, use `radial_hydrogen_eigenstrain_history()` with one pressure load, temperature profile, and hydrogen profile per time. `RadialHydrogenEigenstrainStressHistory.sample_at()` returns only supplied clock samples. A failed solve raises `RadialHydrogenEigenstrainHistoryError` with the successful prefix; no temporal interpolation or diffusion/stress feedback is added.

`h2physics.adapters.bind_cylindrical_transport_to_eigenstrain()` joins an original cylindrical `TransportResult` to that stress-history API. It requires caller-supplied surface concentrations at each transport time, exact matching cylinder bounds, explicit carrier-basis/coefficient evidence, clock-join evidence, and a separate axial-uniformity assumption. `TransportEigenstrainBinding.require_current()` rechecks both retained histories. Trapped concentration, inferred surface values, and transport/mechanical feedback are excluded.

`h2physics.adapters.audit_mixture_separator_history()` audits phase-resolved mixture-vessel records accepted by an external native owner. Each time point must retain an admitted CoolProp phase packet and exact cumulative per-species inlet/outlet moles plus net energy into a fixed-volume vessel. The audit checks component and internal-energy closure against explicit tolerances and preserves each residual. Its issued receipt retains the accepted points and revalidates their nested inventory admissions and balance summaries through `require_current()`. This audit does not create an evolving flash or independently establish that an external solver produced the records. The companion `run_finite_mixture_vu_intervals()` handles caller-supplied finite intervals; the separate host-side `run_mixture_vessel_ode()` integrates continuous rates and localizes declared interior thresholds. Native receiving-solver integration and unrestricted phase appearance remain open under Request032. See [Mixture separator history audit](MIXTURE_SEPARATOR_HISTORY_AUDIT.md). The Hangang contract is deferred and unexecuted.

`h2physics.adapters.capture_hyram_radial_plane()` and `audit_hyram_source_transition()` receive same-run expanded-plug and Gaussian-entry snapshots from an external HyRAM provider and check H₂ and mixture mass, axial momentum, and excess total energy with separate residual and quadrature budgets. Missing transfer terms or property profiles remain `incomplete`. The host audit does not call or modify HyRAM and cannot establish that a caller's snapshots came from the declared native run. See [HyRAM source-transition audit](HYRAM_SOURCE_TRANSITION.md) and [Request 012](../requests/012_preferred_dispersion_boundaries.md). The synthetic case is deferred.

For accepted native HyRAM+ flame radiation, `h2physics.adapters.incident_history_from_hyram_radiation()` converts one indexed global observer's native scalar irradiance into a one-interval, left-held `ExposureHistory`. The caller supplies the absolute interval, receptor identity and basis; the interval is constrained to the source's evidenced steady window. Source ID, clock, coordinates, and source/steady evidence are carried through. It does not infer a transient, receiver orientation, absorption, or a harm result. The Hangang case is `hyram-native-radiation-exposure-handoff` in profile `jet-fire-conservation`; point `H2_HANGANG_HYRAM_PACKAGES` to the separately staged HyRAM6.1 installation before pinning/running native cases. See [native exposure](NATIVE_EXPOSURE.md).

For native HyRAM Bauwens peak pressure, `h2physics.adapters.pressure_peak_from_hyram_overpressure()` binds a current owner-issued peak to `PressurePeak`, preserving gauge rise and input evidence. Its caller supplies a clock interval containing the event snapshot; no impulse, waveform, or arrival time is inferred. Deferred Hangang case: `hyram-bauwens-native-exposure-handoff` under profile `hyram-overpressure`, using the same separately staged HyRAM6.1 path.

For the finite LH₂ pool-fire provider, `h2physics.adapters.exposure_history_from_pool_fire()` maps one current trace receptor's stage-resolved incident flux into `ExposureHistory`, including the zero-flux inactive stage tails. It preserves the fire clock and evidence while carrying no injury model. Deferred Hangang case: `pool-fire-exposure-history-handoff` under profile `pool-fire`, configured through `H2_HANGANG_POOL_PACKAGES`; this route does not require HyRAM.

For oxygen deficiency, `h2physics.adapters.evaluate_oxygen_deficit_alarm()` takes a current `OxygenRoomResult`, explicit dry-air reference and evidence, plus the existing typed sensor and alarm configurations. It maps output to `max(reference_dry_O2 - room_dry_O2, 0)` and runs the existing first-order sensor and sampled alarm APIs. It returns `OxygenDeficitAlarmHandoff`, whose `require_current()` revalidates the room owner, sensor, alarm, and source alignment; confirmed rising transitions are exposed as existing `ConcentrationAlarmEvidence` objects for facility-protection replay. Reference level, detector response, trip/reset thresholds and confirmation logic remain caller inputs. Deferred Hangang case: `oxygen-room-deficit-detector-alarm-handoff` under `oxygen-deficiency`.

For an upper-layer-only signal, `h2physics.adapters.evaluate_layer_oxygen_deficit_alarm()` takes a current `LayerOxygenProjection`, caller-declared reference fraction/evidence, explicit reference-to-projection clock and location mapping evidence, source origin and evidence, and the existing typed first-order sensor/alarm configurations. The concentration basis is built with `layer_oxygen_deficit_basis(reference_evidence_id)` and must match both configurations. The result retains the exact projection/timestamp tuple, computes `max(reference_O2 - upper_layer_O2, 0)`, reuses the existing sensor/alarm engines, and exposes their source-bound confirmed-trip evidence. `require_current()` checks projection values, the derived deficit, clock/location IDs, sensor/alarm configurations, traces and evidence. The mapping evidence asserts applicability; this API performs no clock conversion or location interpolation and makes no room-average, exposure-duration, safety-certification or human-response claim. Deferred Hangang case: `two-vent-layer-oxygen-deficit-sensor-alarm-handoff` under `facility-protection`; see [upper-layer oxygen alarm handoff](LAYER_OXYGEN_ALARM_HANDOFF.md).

For a wall-coupled native Cantera catalytic reactor, `HeatDuty.bind(trace, CanteraCatalyticWallHeatAdapter(), window)` converts exact accepted cumulative wall-energy increments into signed `HeatSnapshot` bins for the thermal-utility ledger. The adapter requires an exact sample window, a current native trace and a retained thermal wall; isothermal thermostat demand is rejected. It records the fixed wall as an imposed external device and makes no utility availability claim. Deferred Hangang case: `cantera-catalytic-wall-heat-utility-handoff` under `counterflow-flame`.

For a homogeneous Cantera reactor composition, `evaluate_cantera_species_alarm()` binds one declared gas-phase mole-fraction species to the existing first-order sensor and sampled alarm APIs. The caller declares the site, clock, source evidence, origin, operating mode and episode because `ReactorTrace` contains no spatial release or detector-location model. Its `CanteraSpeciesAlarmHandoff.require_current()` revalidates the live reactor and links rising alarm evidence to the exact trace. Deferred Hangang case: `cantera-reactor-hydrogen-sensor-alarm-handoff` under `counterflow-flame`.

For finite hydride discharge, `nozzle_history_from_hydride_trace()` evaluates the existing shared nozzle at each retained bed gas state and returns `HydrideNozzleSource`, which preserves the original trace, clock, location, outlet opening and source evidence. The caller selects the mass-flow quadrature and cites a closure-tolerance basis; every nozzle interval must close against the accepted bed gas-port mass within that declared budget. Mismatched source histories are rejected without rescaling either ledger. The resulting `SourceHistory` can then be projected through existing finite-source APIs. Deferred Hangang case: `finite-hydride-nozzle-source-handoff` under `finite-hydride`.

## Engine boundary schedule ledger

`h2physics.combustion.EngineBoundaryStream` pairs an absolute-time, nonnegative mass-flow schedule with a specific-enthalpy schedule on the same knots. `integrate_engine_boundary_streams()` integrates intake and direct fuel streams into a declared cylinder control volume and exhaust streams out of it, with a common caller-owned enthalpy reference. Mass uses exact trapezoidal integration; the product of linearly interpolated flow and enthalpy is integrated exactly by midpoint Simpson quadrature. The result is source-issued and `require_current()` detects changed inputs.

This is scheduled boundary accounting only. It does not calculate valve or injector flow, connect the histories to the native cylinder solver, or prove transfer at accepted solver steps. It cannot close the engine first law or full cycle. See [Engine boundary ledger](ENGINE_BOUNDARY_LEDGER.md) and [Request 034](../requests/034_hydrogen_engine_cycle.md). Its Hangang contract is deferred and unexecuted.

## Prescribed-flow open-cylinder segment

`h2physics.combustion.OpenCylinderInlet` binds a fixed `ReactiveState`, source references and a nonnegative absolute-time mass-flow schedule to one native Cantera reservoir. `open_cylinder_inlet_from_crank_angle()` converts caller-provided nonnegative fuel/feed rates from crank angle to that same absolute clock using the declared constant-speed `SliderCrank`; the native `MassFlowController` then applies them to the reacting moving-volume cylinder. This is prescribed fixed-state feed, not injector or nozzle physics. `OpenCylinderOutlet` prescribes a nonnegative bulk extraction rate; the native mass-flow controller removes the current well-mixed cylinder composition. `run_open_cylinder_segment()` composes these boundaries with `SliderCrank`, an `IdealGasReactor`, `ReactorNet` and a moving native `Wall`. It retains sampled species-transfer, mass and enthalpy diagnostics, native owners, stale-input guards and the accepted requested-sample prefix on failure.

`OpenCylinderNozzleInlet` composes a fixed-state source with the shared `HomogeneousIsentropicNozzle` using live native cylinder pressure as backpressure. It requires `CanteraFrozenGasProperties` with exact source/cylinder phase thermochemistry and mechanism identity; no EOS conversion is introduced. Cantera's native `MassFlowController` adapts the shared nozzle rate. The trace retains accepted nozzle results plus its existing source mass, species and stagnation-enthalpy transfers. Choked, backpressure-limited, closed and no-forward-pressure regimes remain those of the shared nozzle; jet momentum is not coupled into the well-mixed reactor. See [Open-cylinder flow and nozzle boundaries](ENGINE_OPEN_CYLINDER.md) and [Request 034](../requests/034_hydrogen_engine_cycle.md). The shared-nozzle/native-cylinder case is deferred.

Pressure-responsive `OpenCylinderValveInlet` and `OpenCylinderValveOutlet` add an optional native Cantera `Valve` with a caller-evidenced coefficient in kg/s/Pa and a source-bound [0, 1] opening schedule. The built-in law is one-way and linear in pressure difference; it is not a compressible nozzle or calibrated valve model. The prescribed-rate boundaries remain supported. An optional `CylinderWallThermal` adds a caller-parameterized finite wall state to the same native integration, with lumped capacity, gas-wall UA, optional external heat callback and gas/wall energy ledgers. Transfer and pressure-volume histories are sampled diagnostics, not a native accepted-step first-law certificate or complete engine cycle. Spark, flame, spatial wall thermal fields, braking work, multi-cylinder operation and measured-engine qualification remain open. See [Open-cylinder engine segment](ENGINE_OPEN_CYLINDER.md), [Finite cylinder-wall thermal state](ENGINE_WALL_THERMAL.md), [Engine boundary ledger](ENGINE_BOUNDARY_LEDGER.md) and [Request 034](../requests/034_hydrogen_engine_cycle.md). The forced-flow, pressure-valve and wall cases are deferred to Hangang.

## Bounded Brayton map operating point

`h2physics.combustion.SteadyMapSolveInputs` declares exactly three unknowns—compressor corrected speed, compressor pressure ratio and inlet-air flow—and three residuals: compressor corrected flow, turbine corrected flow and net shaft power minus explicit loss/target. A caller supplies speed-link and corrected-flow callbacks with evidence IDs and bounds inside both map domains. Every trial delegates equilibrium and cycle thermodynamics to the native Cantera Brayton runner. Multi-start results retain each seed and distinct root; `unique_candidate` is available only if every seed converged to the same clustered root. `incomplete_search` is reported when any seed did not converge. Separate Cantera ideal-gas and CoolProp HEOS real-fluid single-stage H2 compressor paths are available; only the Cantera path links to Brayton, because real-fluid/Cantera property-basis conversion is not qualified. Compressor maps/trains, cooling, machinery qualification, controls, off-design operation and plant boundaries remain open. See [steady operating point](STEADY_MAP_OPERATING_POINT.md) and [Request 035](../requests/035_hydrogen_gas_turbine_cycle.md). Its synthetic contract is registered for Hangang and remains unexecuted.

`h2physics.storage.PorousReservoirSchedule` accepts exactly one of `well_mass_flow_kg_s` or `well_pressure_pa`. The pressure series uses the reservoir clock and pressure bounds and drives the inner radial face through the existing single-phase Darcy transmissibility. Positive flow is into the reservoir. Each implicit step evaluates the mean scheduled well pressure against the converged first-cell pressure; injection density/viscosity use `well_temperature_k` (default: first-cell temperature), while withdrawal properties come from the reservoir donor state. This is a finite-volume boundary coupling, not a wellbore, tubing, skin, multiphase, or calibrated deliverability model. The `porous-reservoir-pressure-driven-well` contract is deferred and unexecuted. See [single-phase radial porous-reservoir model](POROUS_RESERVOIR.md).

`h2physics.hydraulics.solve_isothermal_compressible_gas_flow()` solves one steady horizontal isothermal ideal-gas pipe state from absolute inlet/outlet pressures, geometry, temperature, molecular mass, viscosity and a caller-owned Darcy friction law. It retains axial velocity change and pressure-varying density, solves the Reynolds-dependent friction closure, and verifies the downstream pressure residual. Positive flow is high-to-low pressure; reverse flow uses swapped endpoints. Elevation, heat exchange, local losses, real-gas EOS, choking and transient line inventory are excluded. Its constant-friction contract is deferred under Hangang profile `gas-compressible-pipe`; it is not hydrogen pressure-loss validation. See [shared hydraulics](HYDRAULICS.md).

`h2physics.fragment_trajectory.HydrostaticIdealGasDensityProfile` is a callable density provider for the existing fragment solver. It accepts one base pressure/temperature/altitude, constant lapse rate/gravity, molecular mass and a closed altitude domain; it calculates hydrostatic ideal-gas density and rejects extrapolation or nonpositive states. Its `signature` is retained in the flight result currentness digest. This is an explicitly parameterized atmosphere layer, not bundled standard-atmosphere or weather data. See [conditional fragment flight](FRAGMENT_TRAJECTORY.md); its synthetic integration case is deferred.

`h2physics.fragment_energy_bound.bound_fragment_speed_from_elastic_energy` integrates the existing thick-cylinder Lamé field to provide a linear-elastic strain-energy ceiling and corresponding speed bound for one caller-selected fragment mass. Caller inputs include differential pressure, wall length, elastic constants, energy fraction, fragment mass and evidence IDs. It does not infer rupture or actual launch conditions. See [fragment energy ceiling](FRAGMENT_ENERGY_BOUND.md).

`h2physics.adapters.bind_compression_to_mixture_receiver()` converts an issued
real-fluid `HydrogenRealFluidCompressionRun` into a typed vapor inlet
`MixtureVesselInterval`. It requires a current accepted finite-mixture receiver
state, exact CoolProp hydrogen-fluid mapping and release, one declared enthalpy
reference, and discharge pressure above receiver pressure. The caller supplies the interval
clock and boundary evidence; transferred moles and inlet enthalpy are derived
from compressor mass flow and its accepted outlet state. It does not calculate
valve flow, receiver pressure history, or transient compressor behavior. See
[compressor-to-storage handoff](COMPRESSION_STORAGE_HANDOFF.md); the integration
case is deferred for Hangang.

`h2physics.adapters.bind_cantera_membrane_thermostat_heat()` maps the original
finite Cantera membrane's two signed cumulative thermostat ledgers to separate
left/right `HeatDuty` objects. It requires exact output-sample endpoints on
the membrane clock and checks the retained native terminal states for
currentness. It reports imposed boundary duty only; see
[membrane thermostat duty handoff](CANTERA_MEMBRANE_HEAT_DUTY.md).

`h2physics.adapters.pump_operation_to_process_connections()` maps each
accepted finite-speed LH2DT pump point to the shared `ConnectionTransfer`
contract, retaining sampled absolute receiver pressure, mass flow, shaft work,
outlet enthalpy, exact provider basis and pump clock. It does not infer motor
electricity or interpolate/integrate between samples. See
[pump-to-process connection](PUMP_PROCESS_CONNECTION.md).

`h2physics.adapters.product_delivery_from_finite_transfer()` binds a current
finite LH2 transfer trace to an explicitly evidenced terminal receiver/product
custody boundary. It returns accepted interval kg, average kg/s and a typed
`TimeSeries` retaining the trace clock and property-reference basis. Reverse
mass returns are rejected. See [finite-transfer product receipt](FINITE_TRANSFER_PRODUCT.md).

`h2physics.adapters.run_jet_radiation_radial_wall()` connects one accepted
HyRAM receiver irradiance to the existing finite radial wall model using the
source's evidenced steady window and caller-supplied absorptivity, geometry
and circumferential-uniformity evidence. It retains the native radiation and
wall-energy receipts; see [HyRAM radiation to radial wall](JET_RADIATION_RADIAL_WALL.md).

### Finite relief source handoff

See [RELIEF_FINITE_SOURCE.md](RELIEF_FINITE_SOURCE.md) and public exports ReliefFiniteSourceHandoff /
elief_source_from_accepted_withdrawals. The bridge carries accepted-edge inventory-closed relief withdrawals into IntervalMassSource, with explicit representative-state enthalpy closure; it adds no source-flow or dispersion solver.


### Pool-fire radiation to radial wall

`h2physics.adapters.run_pool_fire_radial_wall()` composes the selected finite pool-fire receptor history with the common `RadiationRadialWallCore` and existing radial cylinder heat solver. Supply explicit surface projection, wall geometry/material, absorptivity and uniform-circumference evidence. Deferred Hangang case: `pool-fire-radial-wall-handoff` under the existing `pool-fire` profile. See [POOL_FIRE.md](POOL_FIRE.md).

### Elastic vessel energy bound to fragment flight

`h2physics.adapters.run_elastic_bound_fragment_flight()` reuses the current elastic-cylinder speed ceiling and fragment-flight solver, rejecting caller launch states above the assigned kinetic-energy bound. Event time, clock, frame and cylinder-to-launch evidence are required. It infers no rupture or fragment state. Deferred case: `elastic-bound-fragment-flight-handoff`; see [fragment trajectory API](FRAGMENT_TRAJECTORY.md).

### HELPR failure event to conditional fragment flight

`h2physics.adapters.run_vessel_failure_fragment_flight()` preserves an owner-issued HELPR initiation while routing its exact load/time into the existing elastic fragment-energy and trajectory API. The caller supplies the shell-to-cylinder mapping and every launch/environment assumption. It predicts no opening or fragments. Deferred case: `vessel-failure-fragment-flight-handoff` under `fracture-fatigue`; see [VESSEL_FAILURE.md](VESSEL_FAILURE.md).
# Finite hydride to vessel failure history

`adapters.history_from_finite_hydride()` maps accepted finite-hydride pure-H2
absolute pressure samples to the existing HELPR history input. The caller
provides one shell-temperature sample per accepted time and explicit shell and
geometry mappings; hydride solid temperature is not treated as vessel-wall
temperature. The adapter preserves the EOS property basis and clock, and does
not add a failure criterion. Deferred Hangang case:
`finite-hydride-vessel-failure-history-handoff` under `finite-hydride`; see
[the contract](FINITE_HYDRIDE_VESSEL_FAILURE.md).
## Electrolysis output to a compressor inlet

`adapters.bind_electrolysis_compressor_inlet()` connects an admitted finite PV
electrolysis H2 trace to the existing real-fluid compressor input contract. It
checks exact product P/T, EOS basis and source clock, then caps caller-declared
withdrawal by net H2 produced. It models no regulator, conditioning or dynamic
receiver pressure. Deferred case:
`pv-electrolysis-real-fluid-compressor-inlet-handoff` under `pv-electrolysis`;
see [the adapter contract](ELECTROLYSIS_COMPRESSOR_INLET.md).

`adapters.charge_linepack_from_electrolysis(initial, producer, ...)` maps one
completed finite producer batch over a separate post-production transfer window
into the existing fixed-volume isothermal linepack ledger. It requires a shared
clock, matching start time, exact H2 mass basis, caller-evidenced minimum source
pressure and temperature bounds for the transfer window, and explicit loss.
The receipt retains source-side initial/post-production/withdrawn/lost/retained/
post-transfer H2 moles, but does not mutate the original producer trace or
calculate a post-transfer source thermodynamic state.
Its caller-signed energy ledger maps the producer enthalpy reference to a
declared linepack reference and closes integrated source transfer enthalpy,
reference offset, conditioning energy and caller-declared linepack energy change
within supplied tolerances. No internal-energy, compressor, valve,
heat-transfer, pressure-loss or transient-flow model is run. Deferred case
`pv-electrolysis-isothermal-linepack-charge-handoff` is registered but unrun;
see [the adapter contract](ELECTROLYSIS_LINEPACK.md).
## Adsorption product to linepack

`h2physics.adapters.charge_linepack_from_adsorption_product` maps an accepted
`AdsorptionProductMassFlow` into one fixed-composition H2 linepack interval.
Supply explicit start/end times, inventory floor, clock mapping, hydrogen
basis, and transfer-boundary evidence. The receipt retains source and
destination ledgers and exposes `require_current()`. Scope and limitations are documented in
[ADSORPTION_LINEPACK.md](ADSORPTION_LINEPACK.md).
## Cantera fuel-cell coolant energy to HeatDuty

`adapters.bind_cantera_fuel_cell_coolant_heat()` projects exact accepted
cumulative coolant-to-stack joules into signed `HeatDuty` intervals on an
explicit clock/window. Positive values mean heat enters the stack from
coolant. The receipt does not claim recoverable utility heat or an exchanger.
Deferred case: `cantera-fuel-cell-coolant-heat-duty-handoff` under
`fuel-cell-native`; see [the adapter contract](CANTERA_FUEL_CELL_COOLANT_DUTY.md).

## Adsorption outlet to finite-hydride inlet

`bind_adsorption_to_finite_hydride(trace, bed_gas, ...)` maps each accepted
H2 outlet bin into the existing finite-bed gas-port boundary. The caller supplies
a shared-clock mapping, hydraulic transfer evidence, and one gas-state
projection per source interval. Per-bin mass and enthalpy are checked against
the accepted native adsorption ledger. See
[ADSORPTION_FINITE_HYDRIDE_PORT.md](ADSORPTION_FINITE_HYDRIDE_PORT.md).

## Reliquefier product to native separator inlet

`bind_reliquefier_product_to_separator` converts an accepted collected
all-liquid `ReliquefierProductReceipt` into the native finite separator's
liquid-flow callback. The caller supplies clock alignment, receiver assignment,
and transfer-boundary evidence covering pressure/thermal feasibility. It
preserves product mass and specific enthalpy; it does not model line losses,
flashing, or conditioning. See
[RELIQUEFIER_SEPARATOR_INLET.md](RELIQUEFIER_SEPARATOR_INLET.md).

## Finite separator pressure history to HELPR

`history_from_finite_separator` maps accepted pure-H2 separator pressure/time
samples into the existing HELPR `VesselFailureHistory`. Supply one independently
mapped shell-wall temperature and external absolute pressure per accepted row,
plus exact clock, geometry, pressure-basis, and provenance evidence. HELPR
revalidates the native trace before consuming the projection. Fluid temperature
is never treated as wall temperature. See
[FINITE_SEPARATOR_VESSEL_FAILURE.md](FINITE_SEPARATOR_VESSEL_FAILURE.md).

## HyRAM radiation to lumped thermal target

`incident_heat_history_from_hyram_radiation` composes an accepted HyRAM
observer's scalar irradiance through the existing `IncidentHeatHistory` and
lumped thermal-target API. The caller supplies target-surface mapping and
irradiance-projection evidence; target properties remain explicit. See
[HYRAM_LUMPED_THERMAL_TARGET.md](HYRAM_LUMPED_THERMAL_TARGET.md).

## Real-fluid compressor to finite-hydride gas port

`bind_compressor_to_finite_hydride` maps one accepted CoolProp HEOS H2
compressor point into the existing finite-hydride gas port. It rechecks the
receiver-provider state at the compressor discharge and preserves one explicit
constant-flow time interval, mass, and enthalpy. The clock mapping, line/valve
transfer boundary, and state projection remain caller-owned. See
[COMPRESSOR_FINITE_HYDRIDE_PORT.md](COMPRESSOR_FINITE_HYDRIDE_PORT.md).

## Finite-hydride desorption to mechanical compressor

`bind_finite_hydride_to_compressor` couples accepted finite-bed external
withdrawal ledgers to one existing HEOS hydrogen compressor run per interval.
It preserves the exact selected bed-edge state and checks positive compressor
mass/enthalpy inputs against the negative outward bed-ledger increments. Each
interval requires clock, direct-transfer and state-projection evidence. See
[FINITE_HYDRIDE_COMPRESSOR_INLET.md](FINITE_HYDRIDE_COMPRESSOR_INLET.md).
The compressor input has no timestamps; its process-window ID plus caller
clock evidence is the only temporal correspondence.

## Finite-hydride desorption to fuel-cell H2 feed

`bind_finite_hydride_fuel_cell_feed` maps one accepted hydride outlet interval
to the existing fuel-cell `ThermochemicalFeed` and a copied `FuelCellStep` with
the packet assigned to the declared H2 inlet. Source mass and enthalpy come
from exact negative changes in the hydride's integrated external-gas ledgers;
the step clock and edges must match exactly. The caller supplies the receiving
feed state and a signed energy-reference conditioning ledger. No fuel-cell or
conditioning solver is added. See
[FINITE_HYDRIDE_FUEL_CELL_FEED.md](FINITE_HYDRIDE_FUEL_CELL_FEED.md).

## Real-fluid compressor to isothermal linepack

`charge_linepack_from_compressor` applies one accepted HEOS compressor mass
interval through the existing ideal-H2 linepack `advance()` method. It requires
the discharge to exceed final linepack pressure and an explicit signed thermal
conditioning-energy ledger for the real-fluid state mapped to linepack pressure
and fixed temperature. See [COMPRESSOR_LINEPACK.md](COMPRESSOR_LINEPACK.md).

## Linepack withdrawal to compressor inlet

`bind_linepack_compressor_inlet` projects one accepted `LinepackSourceHandoff`
into the existing `HydrogenRealFluidCompressionInputs` API. The finite source
interval fixes compressor inlet mass flow and preserves its H2 pressure and
temperature. A CoolProp HEOS state replay plus a caller-owned signed enthalpy
conditioning ledger is required. The adapter returns inputs only; it does not
run the compressor or infer pressure loss or heat transfer. See
[LINEPACK_COMPRESSOR_INLET.md](LINEPACK_COMPRESSOR_INLET.md).

## Underground cavern withdrawal to compressor inlet

`bind_underground_compressor_inlet` maps one admitted UH2SC dry-H2 source bin
into the existing HEOS compressor input type. The source bin's exact interval
mass determines inlet flow; the caller representative state is replayed by
CoolProp and its native-vs-projected enthalpy difference is preserved in an
explicit signed mapping ledger. It returns inputs only and adds no well,
pressure-loss, or compressor solver. See
[UNDERGROUND_COMPRESSOR_INLET.md](UNDERGROUND_COMPRESSOR_INLET.md).

## Linepack withdrawal to fuel-cell H2 feed

`bind_linepack_fuel_cell_feed` maps one exact accepted linepack withdrawal bin
to an existing `FuelCellStep` and `ThermochemicalFeed`. It requires caller-
integrated source enthalpy and reference ID because the linepack owner provides
mass but no energy integral. The target caloric energy-basis ID, signed
reference offset, and conditioning energy are explicit and close as
`H_source + offset + conditioning - H_feed = 0`. The adapter issues an input
packet only. See
[LINEPACK_FUEL_CELL_FEED.md](LINEPACK_FUEL_CELL_FEED.md).
# Cryogenic source observations

`h2physics.data.load_cryo_neutron_phase_change_run(path)` reads the hash-pinned three-file NIST cryogenic phase-change subset into `CryoNeutronPhaseChangeRun`. DAQ and image clocks remain independent, and rate labels are not unit-converted. The loader checks file pins and source identity; see `docs/CRYO_NEUTRON_PHASE_CHANGE_DATA.md`.
# Grid-fed electrolysis dispatch

`h2physics.adapters.grid_electrolysis_dispatch` exposes
`GridPowerInterval`, `GridElectrolysisStep`, `GridElectrolysisSchedule`, and
`dispatch_grid_power_to_electrolysis`. It reuses `HydrogenStack` for electrical
power and hydrogen rate and returns held `ThermalStackStage` commands that can
be passed to `FiniteThermalStack.run`; it does not run or couple that solver.
The current-density discretization, conversion efficiency, bus auxiliary load,
clock, input identity, and evidence ID are caller inputs. Per-stage AC, stack
DC, conversion-loss, auxiliary and curtailment values remain available for
inspection. See [the focused usage and limits](GRID_ELECTROLYSIS_DISPATCH.md).


## Two-vent hydrogen buoyant-layer model

`h2physics.TwoVentHydrogenLayerConfig` and `run_two_vent_hydrogen_layer(...)` model a steady vertical hydrogen source in a still-air, two-vent enclosure. The result returns interface height, upper-layer hydrogen mole/mass fractions, both vent flows, pressure difference, and hydrogen mass/vent-continuity residuals. It uses fixed ambient temperature and an ideal-gas mixture; see [TWO_VENT_HYDROGEN_LAYER.md](TWO_VENT_HYDROGEN_LAYER.md) for the standalone construction and limitations.

# Finite pipe-reservoir nozzle sink

`FiniteReservoirNozzleCoupling` connects a finite isothermal network endpoint to the shared `HomogeneousIsentropicNozzle`. Each substep's start-state nozzle flow is debited alongside the exact pipe Rusanov endpoint flux; the end-state sample is diagnostic. `IsothermalPipeNetworkTrace.project_nozzle_source()` uses left-hold quadrature and checks source-mass closure against the reservoir leak ledger. Explicit EOS-to-caloric mapping, density tolerance, opening, back pressure, source location, clock and evidence are required. This prepares a nozzle-plane finite source but does not execute HyRAM dispersion. Deferred cases: `hydrogen-pipeline-finite-reservoir-nozzle-sink-closure` and `hydrogen-pipeline-finite-reservoir-nozzle-mapping-rejections` under `gas-compressible-pipe`; see [finite pipe-reservoir nozzle sink](FINITE_PIPE_RESERVOIR_NOZZLE_SINK.md).

`CaloricFiniteReservoirNozzleCoupling` attaches the shared `HomogeneousIsentropicNozzle` directly to a finite-volume caloric network tank. Unlike the isothermal adapter, it obtains every upstream state from the tank's accepted `m,U,V` through the network rho-u EOS and requires an exact `PropertyBasis` match with the nozzle provider. The same start-of-step nozzle result supplies both the tank mass debit and `withdrawal_energy_w` debit. The trace retains internal-clock `SourceHistory`, cumulative mass/energy debits and combined pipe+tank closures. `CaloricPipeNetworkWaveTrace.project_nozzle_source()` requires representative-state and projection evidence and accepts only left-hold quadrature whose integrated mass equals the solver debit. This creates a finite nozzle-plane source and does not execute dispersion. Deferred cases: `hydrogen-caloric-network-nozzle-blowdown-projection` and `hydrogen-caloric-network-nozzle-identity-domain-depletion-rejections`; see [caloric network nozzle coupling](CALORIC_PIPE_NETWORK_WAVES.md#finite-caloric-tank-nozzle-release).

## Caloric compressible pipe waves

`h2physics.caloric_pipe_waves.CaloricPipeWaveModel` advances cell-average
mass, axial momentum and total energy for one uniform-area gas pipe using
first-order Rusanov fluxes and the explicit bound `dt <= CFL*dx/max(|u|+a)`.
It accepts any EOS object exposing `basis`, `state_pt(P,T)` and
`state_rho_u(rho,e)`; `CoolPropProperties` is compatible for single-phase
states. Liquid, two-phase and unknown phases reject without fallback. Closed
reflective walls are default; `CaloricPipeReservoirBoundary` optionally supplies
a fixed, caller-evidenced `ThermoState` ghost state with owner, evidence and clock
IDs. That boundary does not deplete a finite inventory. The immutable,
run-issued `CaloricPipeWaveTrace` retains P/T/rho/velocity/internal energy,
face mass and total-energy rates, signed integrated boundary transfers,
cumulative signed wall heat, output-interval Darcy-factor diagnostics, and
global mass/energy residuals. Optional `CaloricDarcyFrictionLaw` providers use
the Darcy factor convention and retain owner/evidence/clock identity;
`CaloricPipeWallHeatBoundary` specifies fixed `T_w` and `h`, with positive
heat into the gas. Stationary-wall friction does not remove total energy; only
wall heat contributes external energy. The caloric model is a distinct
non-isothermal energy-conserving level from `IsothermalPipeWaveModel`; it remains
`implemented_unverified`. Deferred Hangang cases
`hydrogen-pipeline-caloric-euler-closed-wave-ledgers` and
`hydrogen-pipeline-caloric-euler-reservoir-boundary` and
`hydrogen-pipeline-caloric-euler-source-ledgers` are registered under
`gas-compressible-pipe` and remain unrun. Wall storage, finite
reservoir depletion, phase change, junctions, valves, gravity, and measured-pipe
qualification are outside this level; see [caloric pipe waves](CALORIC_PIPE_WAVES.md).

The trace also retains `pipe_length_m`, `internal_diameter_m`, `area_m2`,
`clock_id`, `eos_identity`, `left_boundary_id`/`right_boundary_id`, and the
corresponding state owner and evidence IDs (closed ends have no boundary
provenance IDs). These fields allow downstream consumers to reconstruct the
run geometry and align ledgers to a caller-declared clock.

### Finite-capacity caloric pipe wall

`h2physics.caloric_pipe_finite_wall.LumpedPipeWall` and
`simulate_caloric_pipe_with_finite_wall()` add one caller-owned thermal-capacity
node to a `CaloricPipeWaveModel`. Each requested outer interval holds wall
temperature constant during the gas solve, then updates it from the gas solver's
integrated heat ledger. Optional constant-UA ambient exchange uses an exact
exponential wall update. `FiniteWallCaloricPipeTrace` retains wall states,
integrated gas/ambient heat, combined energy residuals and every underlying gas
trace. This is first-order operator splitting; reduce outer interval size to
check temporal sensitivity. Capacity is total J/K for one perfectly mixed wall
node representing the complete pipe. The current wrapper handles closed ends;
it excludes axial wall conduction, reservoir boundaries, friction, branches,
phase change and measured-pipeline qualification. Deferred case
`hydrogen-caloric-pipe-finite-wall-energy-closure` is registered under
`gas-compressible-pipe`; see [finite-capacity caloric pipe wall](CALORIC_PIPE_FINITE_WALL.md).

## Caloric branched pipe-network waves

`h2physics.CaloricPipeNetworkNode`, `CaloricPipeNetworkEdge`, and
`CaloricPipeNetworkWaveModel` provide a branched extension of the caloric
Euler pipe level. Each edge has independent cell count and geometry. The model
advances all edges on one explicit CFL-limited clock and retains per-edge
pressure, temperature, density, velocity and exact face mass/energy rates.
`CaloricPipeNetworkWaveTrace` also retains junction pressure/temperature,
mass/energy residuals, entropy-generation checks, graph topology, geometry and
source evidence.

Each internal node uses an explicit zero-volume, adiabatic perfect-mixing
approximation: one resting node state with a common pressure and temperature.
The node values solve the signed mass and total-energy balances using the same
Rusanov fluxes that advance the attached pipes. Both solve brackets and residual
tolerances are explicit caller parameters. This is distinct from detailed tee
losses or characteristic/entropy-preserving Euler-network coupling laws. Fixed
terminal reservoirs use caller-evidenced `CaloricPipeReservoirBoundary` states
and are not depleted. A separate `kind="finite_reservoir"` endpoint uses a
`FiniteCaloricPipeReservoir` with caller-declared fixed volume, initial mass and
internal energy, EOS/basis identity, mass bounds, pressure/temperature domain
bounds, clock and source provenance. Its mass and U stocks advance from the
same signed endpoint Rusanov rates applied to the pipe face; each proposed stock
is rho-u-flashed and domain-checked before commit. `finite_reservoir_mass_kg`,
`finite_reservoir_internal_energy_j`, `finite_reservoir_pressure_pa` and
`finite_reservoir_temperature_k` retain histories. For this mode, total mass and
energy include pipe plus reservoir stock, so their mutual exchange cancels in
the global ledger. `trace.require_current()` replays each retained reservoir
m/U point through the run's EOS and confirms the derived pressure/temperature.
Prescribed fixed-state and finite-inventory endpoints remain separate boundary
modes. Read [caloric pipe-network waves](CALORIC_PIPE_NETWORK_WAVES.md)
for equations and limits. Six deferred Hangang contracts are registered under
`gas-compressible-pipe`; no scientific run has been claimed.

## Spatial catalytic plug-flow reforming

`h2physics.adapters.CanteraCatalyticPFR` wraps Cantera 3.2 `FlowReactor` and
`ReactorSurface` for one steady ideal-gas stream over a caller-supplied catalytic
surface mechanism. The caller provides a source-bound mechanism, explicit
temperature/pressure envelope, inlet mixture, initial surface coverages,
cross-section, surface-to-volume ratio, mass flow, axial output coordinates and
solver tolerances. Its immutable trace retains native gas/surface objects and
one source-bound state at each requested coordinate. This fidelity level is
distinct from the existing stirred reactor models and remains unverified. It
assumes frictionless adiabatic flow and does not model pressure drop, catalyst
thermal storage, pore transport, deactivation or industrial yield. See
[spatial catalytic plug-flow guide](CATALYTIC_PLUG_FLOW.md); the software
contract is deferred to Hangang.

## Generic cascade refuelling sequence

`h2physics.adapters.GenericCascadeRefillSequencer` selects one enabled source
bank from caller-ordered `CascadeBankStage` entries using measured absolute
bank/receiver pressures, caller-defined switch thresholds and minimum headroom.
It retains sensor, owner, clock and sample evidence and advances stages
monotonically. The output contains mutually exclusive `CascadeBankPermit`
values that can be composed with the existing PI regulator and finite-stroke
valve. It computes no flow, valve position, temperature, thermal behavior or
standard-specific fueling procedure. See [cascade refill guide](CASCADE_REFILL.md);
the synthetic software contract is deferred to Hangang.
# Alkaline bubble-loss correction

The optional `h2physics.adapters.alkaline_bubbles` module adds caller-calibrated
electrode coverage and electrolyte void losses around the existing
`HydrogenStack` electrolysis result. It does not modify the shared Faraday rate
or thermochemistry and must not be combined with a base loss that already
contains the same bubble effect.

```python
from h2physics.adapters import (
    AlkalineBubbleCondition, AlkalineBubbleModel, evaluate_alkaline_bubbles,
)

model = AlkalineBubbleModel(
    anode_coverage=lambda condition: anode_theta(condition),
    cathode_coverage=lambda condition: cathode_theta(condition),
    electrolyte_void_fraction=lambda condition: gas_void(condition),
    bubble_free_area_resistance_ohm_m2=lambda condition: bubble_free_area_resistance(condition),
    anode_tafel_slope_v_decade=lambda condition: anode_slope(condition),
    cathode_tafel_slope_v_decade=lambda condition: cathode_slope(condition),
    coverage_evidence_id="coverage-source-version",
    void_fraction_evidence_id="void-source-version",
    electrolyte_resistance_evidence_id="conductivity-source-version",
    tafel_slope_evidence_id="kinetics-source-version",
    correlation_evidence_id="correlation-choice-record",
)
result = evaluate_alkaline_bubbles(
    stack, model, 8_000.0, 353.15, absolute_pressure_pa=6.0e5,
    electrolyte_concentration_mol_m3=6_000.0,
    electrolyte_composition_id="versioned-electrolyte-composition",
    anode_id="anode-record", cathode_id="cathode-record",
)
```

Every callback receives an `AlkalineBubbleCondition` containing geometric
current density (A/m²), temperature (K), and required absolute pressure (Pa).
Optional electrolyte concentration (mol/m³) must be paired with a composition
identity; anode/cathode IDs are another optional pair. No pressure or solution
condition is silently defaulted. The result retains the shared base result and
exposes separate per-cell coverage and void voltage terms, corrected stack voltage and additional electrical power. See
[`ALKALINE_BUBBLE_LOSSES.md`](ALKALINE_BUBBLE_LOSSES.md) for equations, sources,
data limits and model scope.

## Fixed-state H2 compartment networks

`h2physics.compartment_network` provides `WellMixedCompartment`,
`CompartmentMolarTransfer`, `CompartmentNetworkModel`, and
`simulate_hydrogen_compartment_network()`. The model advances H2 and inert
carrier mole fractions across caller-declared rooms and directed molar streams.
Each room has fixed ideal-gas volume, absolute pressure and temperature, so the
model derives a fixed total mole inventory and requires balanced total molar
inflow/outflow on every interval. Piecewise-constant species mixing is advanced
by an exact matrix exponential. The trace retains H2/carrier inventories,
external species in/out and independent residuals, common clock and source IDs.
Flow rates are prescribed: pressure-driven ventilation, buoyancy, pressure or
thermal response, stratification and exposure/consequence are not calculated.
The deferred synthetic case is registered under `oxygen-deficiency`; see
[`HYDROGEN_COMPARTMENT_NETWORK.md`](HYDROGEN_COMPARTMENT_NETWORK.md).

## PEM ripple data ingestion

`h2physics.data` exposes `load_pem_ripple_archive()` and one-member readers for
unaveraged IV curves, per-cell continuous traces and publisher-reported fit
records. The reader checks the exact Mendeley v2 archive size/SHA-256, streams
each requested member without extraction, and retains each member digest. IV
values remain in the source's A/V units. Continuous records preserve exact
source tokens through `iter_source_rows()`, while `timestamp_offset_ms` and
`interval_s` retain timezone-naive clock offsets and suspension gaps. Reported
fits remain derived records and are never treated as observations. See
[`PEM_RIPPLE_DEGRADATION.md`](PEM_RIPPLE_DEGRADATION.md) for rights, instructions
and unresolved model-link inputs.

## AEM electrolysis crossover workbook ingestion

`h2physics.data.load_aem_electrolysis_workbook(directory)` returns a source-
bound `AEMElectrolysisWorkbook` with six `AEMWorksheetSnapshot` records. Values,
formula text, cell types and number formats remain in workbook order and can be
referenced by original one-based row/column or A1 address through
`AEMWorkbookCell`. The reader verifies the Zenodo DOI/version, CC BY 4.0
metadata snapshot, workbook size, publisher MD5 and local SHA-256. It performs
no unit conversion, fit or crossover/polarization model evaluation. Deferred
case `aem-water-electrolysis-crossover-ingestion` checks only source identity,
worksheet schema and cell lineage. See
[`AEM_ELECTROLYSIS_CROSSOVER.md`](AEM_ELECTROLYSIS_CROSSOVER.md).

## Metered electrochemical storage round trip

`h2physics.adapters.account_electrochemical_storage_round_trip()` combines an
already admitted `HydrogenInventoryHandoff` with integrated charge and
discharge `ElectricalBoundaryMeter` readings. It requires one physical clock,
one electrical-energy basis, a shared system boundary and non-overlapping
charge/discharge windows that cover their complete native traces. Its result
reports boundary-meter and native-stack energy separately, plus the existing
H2 produced/delivered/consumed/remaining/loss ledger. It infers no compression,
auxiliary, AC conversion or other plant loads: meter completeness is caller
evidence. The deferred metadata contract is
`electrochemical-hydrogen-storage-metered-round-trip-ledger`; it is not device
performance validation. See
[`ELECTROCHEMICAL_STORAGE_ROUND_TRIP.md`](ELECTROCHEMICAL_STORAGE_ROUND_TRIP.md).

## CoolProp reaction-species enthalpy

`h2physics.thermo.CoolPropMolarEnthalpy(species, fluids,
reference_offsets_j_mol, basis_id=..., temperature_bounds_k=...,
pressure_bounds_pa=...)` implements the existing molar-enthalpy protocol.
It owns one protected CoolProp HEOS state per fluid, checks declared phases and
returns an ordered NumPy vector in J/mol. Offsets must establish a common
formation reference; unrelated native EOS zeros do not define reaction heat.
`CoolPropProperties.molar_mass_kg_mol` exposes the native fluid molar mass.
No locally fitted caloric correlation or silent fallback is used.

## Acoustic EOS phase diagnostics

`AcousticEOSPoint.source_phase` preserves the source label; `predicted_phase`
retains the native PT flash phase. `phase_matches` is True/False for supported
liquid/gas families and None for unclassified phases. Residuals retain phase
conflicts; consumers must inspect phase flags before interpreting EOS accuracy.

## Native real-gas linepack to fuel-cell feed

`h2physics.adapters.advance_real_gas_linepack_to_source` uses the existing
real-gas inventory and native CoolProp state owners. Pass its issued
`RealGasLinepackSourceHandoff` to `bind_linepack_fuel_cell_feed`; provide an
explicit conditioned inlet state and integrated source-energy ledger. See
[full contract](REAL_GAS_LINEPACK_FUEL_CELL.md) and the registered synthetic case.


## Native CoolProp caloric ownership

`h2physics.adapters.coolprop_carrier_caloric(provider, phase_reference_id=...,
hydrogen_partition_id=..., source_id=..., origin=...)` binds an existing
`CoolPropMolarEnthalpy` to the shared `CarrierCaloricSource`. It records actual
native state pointers and the provider's `definition_signature()` without
performing a state solve. Backend, version, reference-offset or native-owner
replacement invalidates already issued results. Recreate the provider/owner
for a changed definition. Direct HEOS is required for reaction calorimetry;
unqualified tabular reaction backends are rejected. Gas-property acceleration
is available separately through the qualified mass-property table contract.

## Held-current inventory-event execution

`h2physics.adapters.run_fuel_cell_until_reserve` returns the original finite
owner trace through its first positive-time H2/O2 reserve crossing, retaining
the requested tail and actual executed prefix. See
[scope and boundary policy](FUEL_CELL_INVENTORY_EVENT.md). It does not locate
events for the continuously coupled native ReactorNet driver.
