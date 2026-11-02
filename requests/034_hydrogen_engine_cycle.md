# Request 034 — Hydrogen reciprocating engine cycle boundary

Status: partial local implementation exists at `h2physics.combustion` as an
implemented-unverified closed-charge moving-volume interval. This request covers
the remaining full-cycle, ignition/control and qualification level.

## Gap

The local `run_closed_charge_engine_segment` API covers a premixed H2/oxidizer
charge in a caller-selected crank-angle window, with slider-crank moving volume
and Cantera-owned homogeneous ideal-gas chemistry. It omits intake/exhaust,
fuel-delivery controls, spark timing/energy, flame propagation, wall capacity,
temperature-driven wall heat transfer, cycle closure and engine output. A
caller-prescribed piston-face heat-flux schedule is a limited boundary input,
not a wall thermal model. Its sampled pressure-volume integral is not brake or
shaft work. Existing constant-volume reactors and this limited segment must not
be presented as complete engine models. Gas-turbine cycle performance is also
outside the current catalog and requires a separate scope decision.

## Remaining requested Python boundary

Extend the local adapter only after accepted-step mass and energy ownership is
available for flows, valve events, fuel delivery and cycle closure. Delegate gas
thermodynamics and finite-rate chemistry to the pinned native Cantera release;
keep it optional and lazily imported. Do not add a second chemical kinetics or
EOS implementation.

The API should accept an explicit mechanism/phase identity, initial cylinder
state and composition, bore/stroke/connecting-rod geometry, compression ratio,
engine speed, cycle phasing, and declared intake/exhaust boundary schedules.
Combustion input must distinguish a spark-triggered premixed charge from a
specified direct-injection mass/enthalpy history; do not infer either from a
generic heat pulse. Every schedule needs units, source identity, absolute clock,
and support bounds. Unknown residual fraction, wall heat transfer, crevice,
blow-by, valve-flow and friction models remain caller-owned or explicit
unresolved terms.

Add intake/exhaust and fuel-delivery controls as explicit supported levels.
The host provides `EngineBoundarySchedule` as a source-bound, unit-tagged,
absolute-time vector with finite support, linear interpolation, and no
extrapolation. A distinct prescribed piston-face heat-flux level is coupled to
the native closed-charge moving wall: callers provide signed W/m² on the
declared schedule clock, and positive flux enters the cylinder. Cantera applies
the flux through its native `Wall`; schedule integration uses piston face area
and enters the sampled first-law summary. This does not infer a heat-transfer
coefficient or correlation, and it is not an accepted-internal-step energy
receipt. Other schedule values are not valve, injector or spark models.

A separate partial model level now connects fixed, source-bound inlet states and
prescribed mass-flow schedules to native Cantera reservoirs and controllers around
an `IdealGasReactor` with slider-crank moving-wall volume. Bulk outlet schedules
remove the instantaneous well-mixed cylinder composition. The implementation
retains native requested-sample states, schedule-based species transfers, sampled
mass/energy diagnostics, and a native-owner failure prefix. The boundary also
supports Cantera's native one-way linear pressure valve with a caller-evidenced
coefficient and a bounded source opening schedule. This law does not infer valve
geometry or discharge coefficient and does not represent compressible/choked
flow, valve lift, cam timing or calibration. It does not implement injection,
species-selective outlet composition, accepted-internal-step conservation
integrals, or a complete engine cycle; the remaining requirements below still apply.
The host also provides `EngineBoundaryStream` and
`integrate_engine_boundary_streams()` for caller-supplied mass-flow and specific-
enthalpy schedules. Intake/fuel contributions are signed into the cylinder;
exhaust is signed out. The paired schedules require a shared enthalpy reference,
identical knots and complete time support. This quadrature receipt remains a
prescribed-boundary summary and does not prove transfers on native accepted solver
steps or close an engine cycle.
Premixed-charge automatic ignition under a selected mechanism must remain separate
from timed spark-ignition behavior. If spark energy is implemented, state how it
enters the native energy balance; do not insert an empirical heat pulse without
an evidenced deposition model. Carry species and energy continuously through
compression, combustion, expansion, exhaust and intake, with event-aware native
integration and accepted-edge ledgers. Multi-cylinder, turbocharger, knock, flame
propagation, emissions and engine-out performance each need independent model
boundaries and evidence.

Return crank-angle and time histories of native state, volume, pressure,
temperature, species, wall heat, boundary mass/enthalpy, indicated work and
cycle closure. Preserve the original native objects and solver diagnostics on
success and failure. Define signs and reference states in the result type; make
mass, elemental and first-law residuals independently recomputable at accepted
cycle intervals. Failed or unconverged cycles must not be converted into
accepted cycle-averaged performance.

## Acceptance evidence

Before advertising an executable model, add deferred Nurion cases for geometry
limits, zero-speed rejection, crank-clock consistency, motored compression,
closed-cycle mass/element conservation, pressure-volume work sign, heat and
boundary energy closure, spark/injection schedule bounds, failed integration
preservation, and cycle refinement. Compare motored and fired pressure traces,
indicated work and timing with independently sourced, license-compatible
hydrogen-engine measurements. Record mechanism, initial conditions, geometry,
fuel basis, calibration procedure, uncertainty, and applicability limits. Keep
measured data separate from code and do not redistribute data unless its license
permits it.

This request defines unimplemented extensions to a limited executable seam. It is
not evidence of model correctness or experimental qualification.

## Finite lumped cylinder-wall thermal increment

`CylinderWallThermal` is now an optional argument to
`combustion.run_open_cylinder_segment()`. It adds one wall-temperature state to
the same Cantera 3.2 native reactor integration. Callers provide constant wall
heat capacity, reference and initial temperatures, a gas-wall UA, an energy
reference identity, and an optional signed external/coolant heat callback. The
gas-to-wall flux is applied with equal and opposite signs; native extra state
integrals retain gas/wall contact energy and external wall energy. The result
includes wall temperature, sensible energy, both heat histories and a combined
sampled first-law residual. No heat-transfer correlation, spatial wall profile,
or multi-layer head/liner model is included.

Deferred cases `hydrogen-engine-wall-gas-coupling-energy-ledger`,
`hydrogen-engine-wall-zero-UA-reduction`, and
`hydrogen-engine-wall-external-boundary-ledger` cover finite exchange, zero-UA
reduction and an explicitly signed external boundary. They remain unexecuted;
independent wall capacity/UA data, accepted-step convergence, and fired-engine
wall-temperature/heat-flux comparisons remain required.

The issued trace fingerprints callback code, defaults, closure contents and
ordinary bound-object configuration, so changes to those callback bindings
invalidate `require_current()`. Globals and opaque external resources remain
caller-owned immutable inputs. All four accepted wall histories are sealed, and
their terminal values are checked against the retained native reactor's wall
temperature and integrated heat states.

## Caller-prescribed piston-face heat flux

The closed-charge moving-cylinder API accepts an optional `heat_flux` /
`W/m2` `EngineBoundarySchedule`. Cantera's native moving piston wall applies the
signed source, with positive flux from the ambient reference side into the
cylinder and its area fixed by piston geometry. Schedule knots are retained in
the output clock, and the exact piecewise-linear boundary energy is included in
the sampled first-law residual. This is an imposed source contract only; it
does not model wall capacity, heat-transfer physics or fuel injection. The
`hydrogen-engine-piston-heat-flux-schedule` deferred case is registered for
Nurion and Hangang and remains unexecuted.

## Crank-angle mapped fixed-state fuel feed

`open_cylinder_inlet_from_crank_angle()` converts a caller-supplied,
nonnegative mass-flow profile from crank angle to absolute time using the
declared constant-speed slider-crank geometry. It creates the existing fixed-
state `OpenCylinderInlet`; Cantera's native mass-flow controller supplies that
feed to the reacting moving-volume cylinder, and the trace retains species,
mass and enthalpy diagnostics. A pulse schedule must explicitly span the full
segment, including zero-flow values outside delivery. This is a prescribed
reservoir feed with no injector, nozzle, spray, momentum, or stratification
physics. Deferred case `hydrogen-engine-crank-angle-fuel-delivery-native-flow`
checks the time mapping and native feed path; it remains unexecuted. Full-cycle
event handling and accepted-step conservation remain open.

## Shared compressible-nozzle source inlet

`OpenCylinderNozzleInlet` now couples the existing `HomogeneousIsentropicNozzle`
to the live Cantera cylinder pressure as its backpressure. The source is a
fixed-state native gas reservoir and its `CanteraFrozenGasProperties` provider
must use the exact same native phase/mechanism and source composition; no
property-basis conversion is performed. A caller-owned `NozzleOpening` and
bounded absolute-time opening schedule set effective area. The shared nozzle
keeps its no-forward-pressure, choked and backpressure-limited gates. Cantera's
native `MassFlowController` adapts the shared mass rate, while the trace retains
accepted nozzle results and existing source mass/species/enthalpy diagnostics.
No nozzle momentum force is applied to the well-mixed chamber. Deferred case
`hydrogen-engine-open-cylinder-shared-nozzle-inlet` checks regime gates,
source/trace ownership and native transfer; it remains unexecuted. RHS nozzle
optimization cost, source blowdown and full-cycle closure remain unresolved.
