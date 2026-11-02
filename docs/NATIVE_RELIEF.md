# Native pressure-triggered relief with finite inventory

`h2physics.adapters.lh2dt_relief` connects the actual pinned LH2DT
`PressureReliefValve` to a finite native `HomogeneousTank`, using the existing
shared nozzle. It resolves physical upstream-pressure opening, hysteretic
reseating, finite mass and fluid/wall energy, and both source limits at events.
The thresholds are not a prescribed opening schedule.

This is an ideal binary protection/reference level. Set pressure, reseat
pressure, effective opening, downstream pressure, heat boundary and clock are
explicit caller inputs. It does not size or certify a relief device, reproduce a
manufacturer lift curve, or qualify a vessel or vent system.

## Native ownership and accepted state

The separately installed MIT LH2DT snapshot at revision
`b2f276333c1b1793c39f25763703d196d36742ec` supplies the actual tank equations,
wall storage, RK4 integration, state/flow/result factories and pressure-relief
hysteresis policy. `PressureReliefValve.evaluate` updates its internal latch on
every call. Calling it directly during RK stages, network roots or diagnostic
probes can open the latch at an unaccepted high pressure and leave it open at a
later trial in the hysteresis band. The source tests and replay retain that raw
native evaluation-order failure.

`Lh2dtReliefProtection.evaluate(left, right)` evaluates flow at the currently
accepted binary opening. It never calls the native latch update. Arbitrary trial
ordering therefore cannot change accepted protection state. The native pressure
policy runs only through `commit(absolute_time, left, right, clock_id=...)` on a
shallow copy of the actual native `PressureReliefValve`. A successful result
promotes that actual native copy atomically; a failed flow evaluation discards
it. No protected latch field is set or restored by host code.

`protection.native_origin` retains the original native component, and
`protection.native` is its current accepted native copy. Every event retains
actual `native_before` and `native_after` objects and actual native valve results.
Old accepted copies keep their old binary state. They share the same stateless
flow strategy/property objects; caller mutation of those native objects would
invalidate recorded traces. The snapshot-specific copy contract is checked, and
an unavailable capability raises an error without selecting another engine.
Clock identifiers supplied at commit and to the finite tank driver must be actual
nonempty strings. Invalid types are rejected at the API boundary before whitespace
or identity comparisons are attempted.

The native relief constructor requires `isinstance(valve, Valve)` and has no
public flow-strategy injection slot. `shared_native_relief` creates an actual
native `Valve` subclass whose **public `evaluate` method** delegates the existing
`Lh2dtSharedValve`. That shared valve delegates the one
`HomogeneousIsentropicNozzle`. No native valve equation, gas EOS or second choking
calculation is copied into this adapter. Native valve geometry metadata agrees
with the explicit `NozzleOpening`; native fixed pressure-sample settings do not
govern the shared nozzle's convergence.

## Python construction

Use the separately installed native package described in HANDOFF.md. Imports
remain optional and caller-owned; the adapter does not bundle LH2DT source or
install a package at import time. The following coefficients are original
synthetic verification inputs.

```python
from lh2dt.tank import HomogeneousTank, TankGeometry, TankState
from lh2dt.properties import ThermoState as NativeState
from lh2dt.streams import MassEnergyFlow
from lh2dt.valve import PressureReliefValve, Valve, ValveResult

from h2physics.adapters.lh2dt import Lh2dtProperties
from h2physics.adapters.lh2dt_properties import Lh2dtLowLevelProperties
from h2physics.adapters.lh2dt_relief import (
    Lh2dtReliefTankDriver, ReliefTankBoundary, shared_native_relief,
)
from h2physics.release import HomogeneousIsentropicNozzle, NozzleOpening
from h2physics.thermo import CoolPropProperties

properties = CoolPropProperties("Hydrogen")
native_properties = Lh2dtLowLevelProperties(properties, state_factory=NativeState)
bridge = Lh2dtProperties(native_properties, reference_id=properties.basis.reference_id)
opening = NozzleOpening("authored-PRV", 1e-6, 1., "declared-effective-orifice-area")
protection = shared_native_relief(
    native_valve_type=Valve, native_relief_factory=PressureReliefValve,
    result_factory=ValveResult, nozzle=HomogeneousIsentropicNozzle(properties),
    bridge=bridge, opening=opening,
    set_pressure_pa_absolute=2e5, reseat_pressure_pa_absolute=1.8e5,
    native_source_id="LH2DT:b2f276333c1b1793c39f25763703d196d36742ec",
)
tank = HomogeneousTank(TankGeometry(.01, 100., 1., 10.), native_properties)
gas = properties.state_pt(1.9e5, 300.)
mass = gas.density_kg_m3*.01
initial = TankState(mass, mass*gas.internal_energy_j_kg, 300.)

boundary = ReliefTankBoundary(
    "authored-operation-clock", 100., 130., properties.state_pt(1e5, 300.),
    ambient_temperature_k=lambda t: 300.,
    direct_wall_heat_w=lambda t, gas, wall: 100.-1.*(300.-wall),
    source_id="authored-constant-net-100W-wall-boundary",
)
driver = Lh2dtReliefTankDriver(
    tank, protection, flow_factory=MassEnergyFlow, state_factory=NativeState,
)
trace = driver.run(
    initial, duration_s=30., maximum_step_s=.25, start_time_s=100.,
    clock_id="authored-operation-clock", boundary=boundary,
    minimum_inventory_kg=1e-6,
)
print([(e.kind, e.time_s, e.pressure_pa) for e in trace.transitions])
print(trace.released_mass_kg[-1], trace.energy_residual_j[-1])
```

The wall boundary deliberately cancels the native ambient-UA contribution so
net external wall heat is exactly 100 W. It is a manufactured verification
boundary, not an inferred heat leak. Native fluid-to-wall heat and wall storage
remain active and unchanged. The example starts below set pressure, heats to an
opening event near 119.61 s, then vents and reseats near 120.69 s. Exact refined
values are in the replay record.

All pressures are Pa **absolute**. The sensed quantity is physical upstream tank
pressure, not pressure difference or a transmitter/recorder output. A gauge
setting needs an explicit pressure conversion before construction. Sensor lag
does not silently replace direct spring-relief actuation; an externally
controlled protection loop would need its own declared policy and clock.

## Physical and numerical event boundary

`Lh2dtReliefTankDriver` holds the accepted latch fixed while native
`HomogeneousTank.simulate` advances a candidate interval. If its endpoint crosses
the active set/reseat threshold, the host repeatedly calls the same native
integrator from the same accepted state with shorter intervals. It retains a
crossing-side bracket, meets the declared time and pressure budgets, accepts
that actual native tank result, and then commits the native latch. Post-event
integration starts with the new accepted opening.

Each localized transition stores pressure, threshold, lower/upper clock bounds,
actual tank state and pre/post source results. Both source limits share one
physical tank state and time; mass, fluid energy and wall temperature are not
reset. Opening and reseating produce source mass/withdrawal-power jumps. Do not
linearly interpolate a source across those jumps. Initial pressure trips are
explicit `initial_open` / `initial_reseat` events at the starting inventory.

Endpoint bracketing localizes a directional crossing in the candidate interval.
Interpreting it as the first physical event assumes at most one relevant crossing
there. An unresolved pressure excursion that crosses a threshold and returns
before the endpoint can be missed. This driver does not claim arbitrary
nonmonotonic first-event completeness or native dense output. Resolve the forcing
with an appropriate maximum step and independently check event/time refinement.
The authored constant-net-heat case supplies that evidence only for its stated
window and resolutions.

`ReliefEventSettings` defaults to 1e-8 s time brackets, 0.001 Pa pressure error,
1e-12 kg inventory-root error and a reviewed native interval floor of 1e-9 s.
Sub-floor unresolved intervals fail; no silent epsilon time shift or threshold
adjustment is applied. Final step partitioning avoids a sub-floor remainder
without enlarging the requested maximum step. Continuous callbacks receive the
absolute operation clock through each native interval's local-time translation.
Clock support and identities are checked; no measured clock alignment or source
extrapolation is performed.

The supported native policy is strictly hysteretic, binary, forward-only and
zero seat leakage. Reseat must be below set pressure, and the fixed downstream
pressure must be below reseat. Equal thresholds would require a chatter/sliding
policy; downstream at/above reseat needs further gating/closure work. These cases
are explicitly unavailable. Reverse and equal-pressure trial flow are zero, with
accepted latch state preserved. A new independent run needs a new or deliberately
continued protection object; accepted clock time cannot move backwards.

## Finite inventory and energy accounting

The actual native tank owns hydrogen mass, fluid internal energy and wall
temperature. Its rigid-volume energy is `U_fluid + C_wall*T_wall`; external
transport removes upstream enthalpy and external heat enters the wall. The one
shared nozzle separately partitions that stagnation enthalpy into nozzle-plane
static enthalpy and kinetic energy. The remote throttled port retains upstream
enthalpy; the nozzle-plane static state is not substituted for a mixed pipe
state or counted again as a second energy loss.

Each accepted interval retains its actual native `TankStepResult`, four actual
reviewed RK stages, source results and boundary heat. Independently read stage
mass, nozzle withdrawal enthalpy and wall heat are quadrature-checked against
the native boundary ledger. The four-stage check is an explicit pinned-RK4
capability, not an assumption about every future native integrator. A changed
callback/result sequence fails. Additional accepted-state trapezoids with
separate event limits check sampling convergence independently of those native
RK-stage ledgers.

`mass_residual_kg` and `energy_residual_j` compare actual finite inventory changes
against cumulative released mass, released stagnation enthalpy and external heat.
These arrays are immutable numerical diagnostics, not exact quadrature or an
automatic application certificate. `trace.intervals` retains native results;
`trace.native_tank`, `native_relief_origin` and `native_relief_final` retain actual
native objects. Caller mutation invalidates their relation to the recorded trace.
`ReliefTankTrace` is issued only by `Lh2dtReliefTankDriver.run()` after native
interval and ledger checks. Direct construction and `dataclasses.replace()` cloning
are rejected, so caller-built residual arrays cannot be submitted downstream as a
completed native relief run.

A separate positive `minimum_inventory_kg` root can end a venting run before
reseat. `trace.inventory_event` preserves its root bracket, positive mass,
native tank state and still-live source. `termination="inventory_floor"` does
not force the valve closed or claim exact physical exhaustion. Invalid trial
mass, native EOS/phase failures or unavailable event capabilities propagate as
`ReliefIntegrationError`. The failure receipt retains the actual tank and
protection owners, the last accepted tank state/time, accepted native intervals,
committed transitions, output axes and mass/energy/heat ledgers, the trial count,
termination metadata, and the original cause. An unaccepted failing candidate is
not appended to this prefix. The deferred `relief-lift-failure-prefix` contract
accepts one native interval and then supplies an invalid ambient-temperature
boundary, which the native tank rejects on its next interval. It checks this
accepted-prefix boundary and original error retention; it is not a reproduced
equipment/EOS failure or scientific validation result.

The current native homogeneous tank withdraws its **bulk mixture**. The verified
case is warm normal-H2 gas. A liquid-filled or stratified vessel needs a qualified
vapor pickup/phase-resolved port before this can represent its relief source.
No dip-tube position, liquid entrainment, phase fraction, vent-stack backpressure,
unknown opening or annual event frequency is inferred.

## Verification and receiving work

```powershell
.venv\Scripts\python -m pytest tests/test_lh2dt_relief.py -q
.venv\Scripts\python scripts/check_relief_integration.py
```

The source tests execute actual native objects for threshold hysteresis,
probe-order independence, failed-commit rollback by copy, one-way/zero flow,
initial actuation, source-plane energy ownership, zero-heat and constant-heat
analytic limits, a heat-driven open/reseat cycle, positive inventory termination
and temporal refinement. The replay checks the reviewed native source aggregate,
begin/end host/native fingerprints and three time steps. Full numbers and fixed
gates are in [research/native_relief.md](../research/native_relief.md).

Useful receiving capabilities are:

- Public native latch state/snapshot/restore and separate pure trial evaluation
  versus accepted commit, including explicit initialization of hysteresis memory.
- A public `Valve` flow-strategy protocol so the common nozzle can be injected
  without a type-constrained public subclass.
- Native accepted-step/event hooks and first-crossing/dense-output support with
  explicit pressure/mass event brackets and restart state.
- Phase-resolved relief ports, varying backpressure, seat leakage, finite lift/
  stroke and a separately evidenced manufacturer policy where those are needed.

No receiving repository is modified. Numerical/interface verification, measured
valve/tank validation, facility qualification, sizing and certification remain
separate statuses.

Primary sources: [native LH2DT](https://github.com/lyullee/lh2dt_models),
[NASA Glenn choking reference](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html),
and [ANL cryogenic relief thermodynamic context](https://www.phy.anl.gov/division/esh/Cryogenic/Appendix%202/appendix%202.htm).
The host adapter, event driver, authored cases and tests are original. Native
implementation code, external experimental data, figures and coefficient tables
are not copied into the distribution.
