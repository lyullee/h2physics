# Open-cylinder flow and pressure-valve boundaries

`h2physics.combustion.run_open_cylinder_segment()` advances one reacting ideal-gas
cylinder interval with Cantera 3.2. It reuses `SliderCrank` and the absolute-time
`EngineBoundarySchedule` contract from the closed-charge engine.

Each `OpenCylinderInlet` owns a fixed `ReactiveState` for reservoir composition,
temperature and pressure, a source-bound nonnegative flow schedule in kg/s, and
caller-declared source and enthalpy-reference identities. Multiple fixed feeds can
represent separately supplied fuel and oxidizer. Cantera computes their native
reservoir enthalpy using the admitted mechanism. The caller must establish that
the declared enthalpy reference is consistent with that mechanism; the API records
this identity but cannot qualify it.

`open_cylinder_inlet_from_crank_angle()` maps caller-supplied nonnegative flow
samples against the declared constant-speed `SliderCrank` clock and builds the
same inlet boundary. This can represent a prescribed fixed-composition fuel feed
or valve-independent supply history. The schedule must cover the whole simulated
interval, so a bounded pulse includes explicit zero-flow values before and after
delivery. Cantera's native `MassFlowController` applies the feed into the changing
cylinder volume and its accepted gas state; the solver reports species and energy
transfer at requested samples. This does not represent injector hardware, nozzle
flow, spray breakup, in-cylinder stratification or a direct-injection model.

Each `OpenCylinderOutlet` supplies a nonnegative, absolute-time bulk extraction
schedule. Cantera's native mass-flow controller removes the cylinder's current
well-mixed composition. This remains useful where flow is externally prescribed.

For a pressure-responsive seam, `OpenCylinderValveInlet` and
`OpenCylinderValveOutlet` use Cantera 3.2's native `Valve` device. Each valve
requires a caller-owned coefficient `K` in kg/s/Pa, a source reference for that
coefficient, and a source-bound opening schedule with quantity
`valve_open_fraction`, units `1`, and values within [0, 1]. Cantera applies
`mdot = K * opening(t) * max(P_upstream - P_downstream, 0)`; flow cannot reverse.
The inlet has a fixed, provenance-tagged reservoir state; the outlet carries the
current well-mixed cylinder gas. The device and source inputs are retained in
the returned trace and included in currentness checks.

## Shared compressible nozzle inlet

`OpenCylinderNozzleInlet` reuses `HomogeneousIsentropicNozzle` from the shared
release kernel. The source is a stationary fixed-state gas reservoir; at every
native flow callback, the shared nozzle receives that retained source state and
the current Cantera cylinder pressure as its backpressure. Its existing
no-forward-pressure, choked, and backpressure-limited branches determine the
nonnegative mass rate. A `NozzleOpening` plus an absolute-time
`nozzle_open_fraction` schedule controls effective area. The schedule must span
the full cylinder interval and all its knots are inserted into the output clock.

This coupling admits only `CanteraFrozenGasProperties` and checks that its exact
native phase thermochemistry, mechanism declaration, frozen source composition,
source pressure, temperature, density and enthalpy match the fixed Cantera
reservoir. It performs no CoolProp-to-Cantera property conversion. The shared
nozzle owns the isentropic/choking calculation; a native Cantera
`MassFlowController` only adapts its returned rate into the reactor network.
The trace retains one `NozzleResult` per accepted output time, including regime,
exit state, velocity, mass flow and the shared nozzle's stagnation-energy
diagnostics. The existing inlet mass, species and enthalpy ledgers include the
native reservoir transfer. Since the nozzle assumes a stagnant upstream source,
Cantera receives source stagnation enthalpy through its MFC; the nozzle exit
kinetic-energy term is part of the shared nozzle energy result, but no jet
momentum force is applied inside the well-mixed cylinder.
If native integration fails, each accepted failure-prefix row retains its
nozzle-result tuple alongside the state and transfer-rate snapshot.

```python
from h2physics.adapters.cantera import ReactiveState
from h2physics.adapters.cantera_properties import CanteraFrozenGasProperties
from h2physics.combustion import (
    EngineBoundarySchedule,
    OpenCylinderBoundary,
    OpenCylinderNozzleInlet,
    run_open_cylinder_segment,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening

source_state = ReactiveState(temperature_k, source_pressure_pa, {"H2": 1.0})
property_phase = phase_factory()
property_phase.TPX = source_state.temperature_k, source_state.pressure_pa, dict(source_state.mole_fractions)
properties = CanteraFrozenGasProperties(property_phase, mechanism_basis, {"H2": 1.0})
nozzle = HomogeneousIsentropicNozzle(properties)
opening = NozzleOpening.circular(
    "project:inlet-port", diameter_m,
    effective_area_factor=caller_area_factor,
    area_basis_id="project:port-area-basis-v1",
)
nozzle_opening = EngineBoundarySchedule(
    quantity="nozzle_open_fraction", units="1", source_id="project:port-timing-v1",
    clock_origin_s=t0, time_s=absolute_times, values=open_fraction,
)
pressure_feed = OpenCylinderNozzleInlet(
    identifier="hydrogen-nozzle-feed", state=source_state, nozzle=nozzle,
    opening=opening, opening_schedule=nozzle_opening,
    source_reference="project:source-state-v1",
    enthalpy_reference="mechanism:declared-native-reference-v1",
)
trace = run_open_cylinder_segment(
    phase_factory, mechanism_basis, initial_charge, geometry,
    OpenCylinderBoundary((), (), nozzle_inlets=(pressure_feed,)),
    absolute_clock_origin_s=t0, crank_start_rad=start_angle, crank_end_rad=end_angle,
)
trace.require_current()
print(trace.nozzle_results[-1][0].regime, trace.inlet_enthalpy_transfer_j[-1])
```

The shared nozzle retains its phase-aware equilibrium/isentropic assumptions and
requires a single frozen gas property basis here. This inlet does not add nozzle
thrust, jet momentum coupling, injector geometry beyond the caller's effective
area declaration, spray, atomization, transient source blowdown, or measured
nozzle qualification. Nozzle optimization runs inside the native RHS callback,
so runtime cost depends on both the solver trial count and the shared nozzle's
property-search settings.

This linear pressure-drop device is a native numerical boundary law. Its
coefficient is not derived from valve area or a discharge coefficient. It does
not include compressible or choked nozzle flow, lift dynamics, seat geometry,
pressure-dependent opening, measured calibration, or timing inferred from a
cam profile. Those require a separately evidenced flow relation and event model.

```python
from h2physics.combustion import (
    EngineBoundarySchedule,
    OpenCylinderBoundary,
    OpenCylinderInlet,
    OpenCylinderOutlet,
    OpenCylinderValveOutlet,
    open_cylinder_inlet_from_crank_angle,
    run_open_cylinder_segment,
)

feed_rate = EngineBoundarySchedule(
    quantity="mass_flow", units="kg/s", source_id="project:feed-rate-v1",
    clock_origin_s=t0, time_s=times, values=feed_kg_s,
)
feed = OpenCylinderInlet(
    identifier="hydrogen-feed", state=feed_state, mass_flow=feed_rate,
    source_reference="project:feed-condition-v1",
    enthalpy_reference="mechanism:declared-native-reference-v1",
)
exhaust = OpenCylinderOutlet(
    identifier="exhaust-port", mass_flow=exhaust_rate,
    source_reference="project:exhaust-rate-v1",
)
opening = EngineBoundarySchedule(
    quantity="valve_open_fraction", units="1", source_id="project:exhaust-opening-v1",
    clock_origin_s=t0, time_s=times, values=opening_fraction,
)
valve_exhaust = OpenCylinderValveOutlet(
    identifier="pressure-exhaust", opening=opening,
    coefficient_kg_s_pa=caller_owned_K, coefficient_reference="source:valve-K-v1",
    source_reference="source:valve-opening-v1",
)
fuel_feed = open_cylinder_inlet_from_crank_angle(
    identifier="scheduled-fuel-feed", state=fuel_reservoir_state,
    crank_angle_rad=fuel_schedule_crank_angles,
    mass_flow_kg_s=fuel_schedule_kg_s, geometry=geometry,
    crank_start_rad=crank_start,
    absolute_clock_origin_s=t0,
    schedule_source_id="project:crank-angle-fuel-flow-v1",
    source_reference="project:fuel-reservoir-state-v1",
    enthalpy_reference="mechanism:declared-native-reference-v1",
)
run = run_open_cylinder_segment(
    phase_factory, mechanism_basis, initial_charge, geometry,
    OpenCylinderBoundary((fuel_feed, feed), (exhaust,), valve_outlets=(valve_exhaust,)),
    absolute_clock_origin_s=t0,
    crank_start_rad=crank_start,
    crank_end_rad=crank_end,
)
run.require_current()
```

The API retains the native reactor, network, wall, flow devices and reservoirs.
Output samples include species-resolved net transfer from inlet compositions and
well-mixed exhaust, total mass residual, inlet/outlet enthalpy transfer, and a
sampled pressure-volume first-law residual. These are trapezoidal diagnostics on
the requested crank samples and all schedule knots; they are not an augmented
accepted-step conservation certificate. A failed advance raises
`OpenCylinderEngineError` with the native owners and previously accepted output
prefix. `require_current()` rejects changed histories/schedules and a native phase
advanced beyond the issued trace.

At each requested sample, the accepted native reactor volume is compared with
the slider-crank volume at the matching crank angle. The residual allowance is
`absolute_tolerance + relative_tolerance * abs(V_geometry)`, using the same
scalar solver tolerances configured on `ReactorNet`; a rejection reports both
volumes, the residual, and the allowance. This is a finite numerical
consistency check for an integrated state, not an exact-geometry override: the
native accepted volume is retained in the trace. To reserve margin for
accumulated moving-wall volume error, ReactorNet runs at one tenth of the
caller-declared relative and absolute tolerances; the public geometry
acceptance budget remains the caller's full tolerance. This stricter native
solve can increase runtime. Review the reported residual against the model's
accuracy target.

An optional `CylinderWallThermal` adds one lumped wall temperature and energy
balance inside the same Cantera `ReactorNet`. The caller supplies wall heat
capacity, initial/reference temperatures, gas-wall UA, energy-reference ID and
an optional signed external/coolant heat callback. Gas-to-wall heat enters gas
and wall with opposite signs; the trace retains both cumulative transfers and
checks the combined gas/wall first-law balance. See
[finite cylinder-wall thermal state](ENGINE_WALL_THERMAL.md). This node adds no
heat-transfer correlation or spatial wall state.

The segment is not a full four-stroke model. It has no detailed valve flow law, spark,
direct-injection model, cylinder stratification, crevice,
blow-by, friction, output shaft, or cycle-closure solution. The sampled first-law
residual and pressure-volume integral do not establish indicated or brake power.
The deferred `hydrogen-engine-open-control-volume-forced-flow`,
`hydrogen-engine-native-pressure-valve-boundary`, and
`hydrogen-engine-crank-angle-fuel-delivery-native-flow` cases share a synthetic
native mechanism contract and remain unexecuted. Registration in cluster
profiles must be maintained independently from implementation status.

The open-control-volume, prescribed valve, crank-angle feed, shared-nozzle and
wall-coupling cases declare the installed Cantera `h2o2.yaml` `ohmech` phase as
their mechanism metadata: 200–3500 K and an explicit computational pressure
envelope of 10 kPa–100 MPa. The deferred host case requests the `h2o2.yaml`
resource name and resolves it through `cantera.get_data_directories()` before
hashing and reading it; do not stage or redistribute the YAML with this
repository. Cantera describes this file as a hydrogen/oxygen mechanism
extracted from GRI-Mech 3.0 and modified to include N2. The metadata string records
that it is Cantera-distributed while leaving upstream mechanism terms unasserted;
the declared envelope is not a claim of validated engine applicability. See
[Cantera's h2o2 input reference](https://www.cantera.org/3.2/examples/input/h2o2.html)
and [Cantera's input-file distribution notes](https://www.cantera.org/stable/userguide/input-tutorial.html).

Cantera owns the reaction, thermodynamic, native Valve and reactor integration behavior. The
implementation follows the public [Cantera 3.2 thermodynamic API](https://cantera.org/3.2/python/thermo.html),
[zero-dimensional reactor API](https://cantera.org/3.2/python/zerodim.html), and
[reactor interaction / valve law](https://cantera.org/3.2/reference/reactors/interactions.html#valves);
no Cantera source code is copied here. See also [Request 034](../requests/034_hydrogen_engine_cycle.md)
for missing engine fidelity and experimental acceptance evidence.
