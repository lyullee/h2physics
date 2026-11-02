# Finite source-to-receiver hydrogen transfer

Status: **implemented_unverified**. This coding increment has not been imported
or executed locally. Native calculations, tests, examples, case discovery and
benchmarks remain deferred. Eight case definitions use profile `finite-transfer`.

`h2physics.adapters.lh2dt_finite_transfer.Lh2dtFiniteTransfer` connects two actual
finite LH2DT homogeneous tanks using the existing shared valve/nozzle. Both
source and receiver masses, fluid internal energies and wall temperatures evolve
under the same native network stages. Receiver pressure is recovered from its
finite mass/U EOS, rather than imposed as a constant reservoir. No filling flow,
temperature trajectory, efficiency or charging protocol is inferred.

## Native ownership and supported paths

The installed MIT LH2DT revision
`b2f276333c1b1793c39f25763703d196d36742ec` supplies `HomogeneousTank`,
`DynamicHEMPipe`, their native node factories, `SteadyNetwork` and
`DynamicNetworkSimulator`. The existing `Lh2dtDynamicEquipment` driver supplies
accepted-solution identity matching and inventory audits; `Lh2dtSharedValve`
delegates all flow to the existing `HomogeneousIsentropicNozzle`. No native
equation, RK step, EOS, friction/nozzle solver or parameter map is copied.

Two paths are explicit:

- Direct: finite source -> shared valve -> finite receiver. The intervening
  path has zero stored volume and no independent wall. This is not a hose model.
- Optional stored line: finite source -> valve -> zero-storage junction ->
  actual native inlet hydraulic half -> finite mixed line -> actual native
  outlet hydraulic half -> zero-storage junction -> valve -> finite receiver.
  Both original half-segments are retained and used; their resistance is neither
  dropped nor duplicated. They must be adiabatic and have zero elevation change
  at this level. The finite line's own fluid/wall heat and fixed ambient are
  native, caller-parameterized boundaries.

All material boundary nodes are dynamic finite inventories. The native network
calls them `boundaries` for numerical coupling; there is no external mass
reservoir in this composition. No pump, compressor or additional pressure work
is invented. A pressure difference drives transfer through the declared path.
Native HEM/transition/EOS failures remain failures, without an alternate flow law.

Ports are explicitly named. Homogeneous tanks withdraw their bulk state, including
the native ownership of outgoing enthalpy. This is not a liquid dip-tube or vapor
selection model. Spatial stratification, phase slip and a propagating hose
cooldown front are unresolved. The authored example/cases use warm normal-H2 gas;
they do not qualify cold flashing or apparatus-specific liquid-hydrogen transfer.

## Python inputs and clocks

Construct each `FiniteTransferBody` from its actual native model and initial
state, source/thermal evidence IDs and `HeatExchangerDomain` inventory/phase/T/P
bounds. Source and receiver use role `homogeneous-tank`; the optional intermediate
body uses `mixed-line`. All bodies and valves share the original native property
instance. Their explicit `PropertyBasis` preserves fluid/spin/energy reference.
The nozzle uses that original property view or its existing underlying provider;
matching a basis label alone does not admit an unrelated EOS owner.
All pressure values are Pa absolute; masses are kg; fluid/wall energy is J.

Each tank requires `TransferAmbient(original_time_series)`: one all-valid,
positive K channel with quantity `ambient_temperature`, resolved origin, source
and clock. Original data/clock/mask are revalidated and bound. Sampling is
explicit piecewise-linear interpolation strictly within support. Mask filling,
clock alignment and extrapolation are rejected. The native finite pipe-node API
uses its supplied fixed ambient parameter; a history is refused for that slot.
Thermal inputs and UAs are caller evidence, not fitted hose/tank performance.

`TransferStage(identifier, start_s, end_s, mode, opening_fractions, source_id)`
defines contiguous authored windows. Every valve fraction must be supplied.
`isolated` requires all fractions zero. A `transfer` stage may still deliver zero
mass if pressure or another opening prevents it. Each valve's existing explicit
`allow_reverse` setting controls reverse admission; signed net received mass is
never clipped or relabelled as positive delivery.

```python
from examples.finite_transfer import build_model, schedule

model = build_model(with_line=False)  # actual native objects; synthetic inputs
trace = model.run(
    schedule(model), clock_id="authored-transfer-clock",
    maximum_step_s=0.05, clock_tolerance_s=1e-10,
    isolate_on_completion=True,
)
trace.require_current()
```

This example is unexecuted. There is no mandatory file/serialization protocol.
`examples/finite_transfer.py` creates native objects lazily; imports define
functions only. The optional installation is selected by an explicit path.

Stage clocks use a grid reconstructed from the stage start and interval index,
not repeated addition of absolute time. Each requested interval is passed to
the existing driver and native simultaneous RK integrator. The actual native
local/absolute stage clocks are observed and retained. Positive full/half spans
must advance and satisfy the explicit projection budget; sub-nanosecond windows
are rejected. No recorder or native clock is reset to hide loss of precision.
One owner cannot run concurrently against its mutable native property objects.
Point times are the budget-checked host grid coordinates. Original native row
times and separately observed local/absolute stage clocks remain inspectable;
the declared projection budget is not an inferred alignment between recorders.

## Material, energy and stopping contracts

Each native accepted interval retains its original simulator/rows, checked
`DynamicEquipmentRun`, actual states, source-plane nozzle results and native
integrated signed mass/transport/ambient ledgers. Local balances are accumulated
with `math.fsum` into per-body `InventoryBalance` records. Independent topology
checks require:

```text
sum(delta mass_body) = 0
sum(integrated internal transported enthalpy_body) = 0
sum(delta(U_fluid + C_wall*T_wall) - integrated ambient heat_body) = 0
```

The existing inventory budgets gate both local and global checks. Fluid-wall
heat stays internal to each body's total U; ambient heat remains external.
Incoming receiver enthalpy includes the shared valve's downstream thermalization
of nozzle kinetic energy. No separate nozzle kinetic power is added again.
With a line, source withdrawal minus receiver net uptake equals the line mass
change within the conservation budget. Source withdrawal is not called delivery.

Optional `TransferStop(kind, threshold, evidence_id)` supports receiver pressure
at least a threshold, signed receiver net mass at least a threshold, or source
mass at most a threshold. It is checked at actual accepted samples. The result
retains the preceding/ending time bracket and actual threshold value/overshoot.
This does not locate a first crossing, rule out an excursion between samples,
or certify a protective controller. A hard phase/domain/inventory failure can
occur in an intermediate trial before the sampled condition is reached; it is
not clipped or converted into a successful endpoint.

`isolate_on_completion` is a required caller action. True explicitly closes the
valves at the retained accepted state and audits the post-isolation network,
recording both sides of the transition without changing inventories. Internal
pipe-junction numerical residuals retain their native tolerances; closed valve
flows themselves must be exactly zero. False ends numerical integration with
the actual current opening; it does not claim physical isolation or continued
future behavior. No automatic isolation occurs to conceal a failed trial.

## Ownership, failures and limits

`trace.require_current()` requires the original owner-issued object. It checks
source/native class/method provenance, body/geometry/domain/reference/thermal
histories, path/port topology, raw accepted-row data, summaries, ledgers and final
mode. Cloning/relabeling cached data does not create an accepted original trace.
Weak registries avoid retaining every trace; a retained trace intentionally owns
its native attempts/results. These are research correspondence guards, not a
security boundary against deliberate private tampering. Ordinary native EOS
working-state evolution remains permitted.

`FiniteTransferError` retains the original cause, all prior audited points and
mode transitions, original native attempts and any returned raw rows, last
accepted state objects, current valve openings, last native thermo request and
any pending stopping candidate. Native stage clocks are separate observations;
an EOS failure before a stage-clock callback is not assigned a fabricated time.
If native `simulate` raises before returning a row, there is no public accepted
row inside that interval to recover. Earlier complete intervals remain intact.

No SAE/ISO protocol, flow/temperature feedback law, pressure-ramp controller,
real actuator/leakage response, vehicle-tank rating, qualified hose heat transfer,
manufacturer map or apparatus calibration is claimed. Such uses require actual
boundaries, data and independent validation. This increment adds composition
within existing finite inventory levels, not another verified family.

Primary sources: [native dynamic network](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_network.py),
[native homogeneous tank](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/tank.py),
[native finite pipe](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_pipe.py),
[CoolProp SI/property interface](https://coolprop.org/coolprop/LowLevelAPI.html).
