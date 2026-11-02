# Caloric pipe-network pressure waves

`CaloricPipeNetworkWaveModel` couples several one-dimensional, non-isothermal
gas-pipe wave segments at an explicitly declared graph. It is a higher network
fidelity level than `CaloricPipeWaveModel` for a single straight segment and a
thermal extension of `IsothermalPipeNetworkWaveModel`. Pipe cells evolve
density, axial momentum and total energy. Each segment reuses the conservative
Rusanov flux kernel from the single-pipe caloric solver.

## Junction closure

Each junction is modeled as a zero-volume, adiabatic, perfectly mixed node at
rest. It has one pressure and one temperature shared by all attached pipe ends.
At every explicit step those two values are obtained by solving the two
discrete balances from the same face fluxes applied to the pipes:

```text
sum_i A_i * m_dot_i(out of node) = 0
sum_i A_i * E_dot_i(out of node) = 0
```

The pressure and temperature brackets are caller inputs. A solve is rejected
when it fails, leaves a provider phase/domain, exceeds the explicit mass or
energy tolerance, or gives a negative perfect-mixing entropy production beyond
the declared tolerance. The implementation reports the residuals and entropy
production. It does not add hidden node storage or silently widen a bracket.

This closure deliberately chooses a simple plenum approximation. Research on
compressible Euler networks also studies coupling laws based on continuity of
total enthalpy and entropy mixing at junctions; these are different mathematical
conditions and are not represented by this API ([Lang and Mindt, 2018](https://doi.org/10.3934/nhm.2018008)).
Network flow discretizations likewise require explicit node conditions rather
than simply joining independent pipe solutions ([Gyrya and Zlotnik,
2019](https://doi.org/10.1016/j.apm.2018.07.051)).

## API outline

```python
import numpy as np

from h2physics.caloric_pipe_network_waves import (
    CaloricPipeNetworkEdge,
    CaloricPipeNetworkNode,
    CaloricPipeNetworkWaveModel,
)
from h2physics.core import Origin
from h2physics.thermo.coolprop import CoolPropProperties

eos = CoolPropProperties("Hydrogen")
nodes = (
    CaloricPipeNetworkNode(
        "west", (-20.0, 0.0, 0.0), "closed", "layout-owner", "west-wall",
        Origin.MEASURED,
    ),
    CaloricPipeNetworkNode(
        "tee", (0.0, 0.0, 0.0), "junction", "layout-owner", "tee-node",
        Origin.MEASURED,
        pressure_bounds_pa=(4.0e6, 12.0e6),
        temperature_bounds_k=(250.0, 350.0),
    ),
    CaloricPipeNetworkNode(
        "east", (20.0, 0.0, 0.0), "closed", "layout-owner", "east-wall",
        Origin.MEASURED,
    ),
    CaloricPipeNetworkNode(
        "north", (0.0, 20.0, 0.0), "closed", "layout-owner", "north-wall",
        Origin.MEASURED,
    ),
)
edges = (
    CaloricPipeNetworkEdge(
        "west-leg", "west", "tee", 20.0, 0.10, 64,
        "layout-owner", "west-geometry", Origin.MEASURED,
    ),
    CaloricPipeNetworkEdge(
        "east-leg", "tee", "east", 20.0, 0.10, 64,
        "layout-owner", "east-geometry", Origin.MEASURED,
    ),
    CaloricPipeNetworkEdge(
        "north-leg", "tee", "north", 20.0, 0.10, 64,
        "layout-owner", "north-geometry", Origin.MEASURED,
    ),
)
model = CaloricPipeNetworkWaveModel(
    nodes, edges, eos, clock_id="network-run-2026-01",
)
pressure = {edge.identifier: np.full(edge.cell_count, 8.0e6) for edge in edges}
temperature = {edge.identifier: np.full(edge.cell_count, 295.0) for edge in edges}
velocity = {edge.identifier: np.zeros(edge.cell_count) for edge in edges}
trace = model.simulate(
    initial_pressure_pa=pressure,
    initial_temperature_k=temperature,
    initial_velocity_m_s=velocity,
    time_samples_s=(0.0, 1e-3, 2e-3),
)
```

All initial-state maps must include each edge exactly once and provide one value
per cell. `time_samples_s` starts at zero; `clock_id` identifies the caller's
time basis. A reservoir terminal accepts one
`CaloricPipeReservoirBoundary` per node. Those boundaries are fixed external
states: their net mass and energy exchange are recorded, but no source
inventory is depleted. Closed nodes are reflective walls. The trace retains
edge/node topology, geometry and evidence IDs, boundary states, EOS identity,
clock, edge face fluxes, junction pressure/temperature, junction balance and
entropy diagnostics, and network mass/energy residuals.

An inventory-backed terminal uses `kind="finite_reservoir"` plus one
`FiniteCaloricPipeReservoir` in `simulate(..., finite_reservoirs={node_id: state})`.
The provider declares fixed volume, initial mass and internal energy, the
property basis and EOS identity, clock, node/source identities, admissible mass
bounds, pressure/temperature EOS-domain bounds and origin. The node's owner and
evidence must match the provider. Each internal substep applies the exact
outward Rusanov mass and total-energy rates already used at the pipe endpoint:

```text
m_next = m_current - dt * F_mass,out
U_next = U_current - dt * F_energy,out
```

Positive outward transfer therefore withdraws both stocks; reverse flow fills
the reservoir using the same signed rates. The provider recovers a stationary,
well-mixed state from `rho=m/V` and `u=U/m` through the network's same rho-u
EOS before the next flux evaluation, and validates every proposed stock before
the pipe or reservoir state is committed. A depleted/out-of-range mass, failed
EOS state, or pressure/temperature domain exit rejects the whole internal step
without clipping. Sonic or supersonic tank endpoint flow is rejected because
this boundary level does not model choking.

Trace histories retain endpoint mass, internal energy, recovered pressure and
temperature. When finite caloric endpoints are present, `total_mass_kg` and
`total_energy_j` include both pipe and rigid-reservoir stocks. The signed
internal exchange cancels from the combined residual; separate prescribed
pressure boundaries remain external exchanges, and fixed-wall heat remains an
external energy term. This endpoint is a single uniform gas state: no wall
thermal mass, stratification, phase change, valve/nozzle, or measured tank
qualification is inferred. It is distinct from the prescribed
`CaloricPipeReservoirBoundary` mode, which remains unchanged and has no
depleting inventory. Trace issuance calls `trace.require_current()`: it checks
the retained EOS identity/basis, verifies each finite node has one edge
endpoint, replays every recorded `(m,U)` pair through the same rho-u provider,
and compares the resulting pressure/temperature to retained histories.

## Finite-caloric-tank nozzle release

A finite caloric tank can also feed the shared `HomogeneousIsentropicNozzle`
through `finite_reservoir_nozzles={node_id: coupling}`. Construct a
`CaloricFiniteReservoirNozzleCoupling` for that tank, naming its node,
reservoir, unique incident edge, opening and opening fraction, back pressure,
source location, state owner, evidence, and origin. The location clock must
match the network clock and its coordinates must match the tank node. The
nozzle property provider must expose the exact same `PropertyBasis` as both the
tank EOS and network EOS. At each internal step the model recovers the tank's
admitted `(rho,u)` state, checks the nozzle provider's pressure, temperature,
gas phase and density against it, then evaluates the shared nozzle.

That one start-of-step `NozzleResult` is used for both withdrawals:

```text
m_next = m_current - dt * (F_pipe,out + nozzle.mass_flow)
U_next = U_current - dt * (F_pipe,E,out + nozzle.withdrawal_energy)
```

The solver validates the candidate pipe and tank states before committing the
step. It rejects a depleted tank, EOS-domain exit, or mismatch without
clipping. The existing prescribed fixed-state tank boundary and finite tank
without nozzle keep their original behavior. Trace outputs include per-node
cumulative nozzle mass and enthalpy-energy withdrawal; combined pipe-plus-tank
mass and energy residuals subtract these external debits with the proper sign.
Each accepted nozzle evaluation is retained on the native internal-step clock,
with a final endpoint sample. `trace.project_nozzle_source(node_id, ...)`
requires a caller representative `ThermoState` and separate quadrature/state
projection evidence. It fixes the projection to left-hold bins and checks that
their sum equals the exact mass debited by the network solver. The projection
creates a finite source record; it does not execute a dispersion model.

Deferred Hangang cases cover shared-provider choked and subcritical releases,
changing tank pressure and temperature, source projection equality, and
identity/domain/depletion rejection. Until those cases are run and independently
reviewed, this coupling remains `implemented_unverified`; it is not a validated
relief-device, vessel, or dispersion prediction.

## Per-edge friction and wall heat

The branched model can attach the existing `CaloricDarcyFrictionLaw` and
`CaloricPipeWallHeatBoundary` contracts to selected edges through
`darcy_friction_laws` and `wall_heat_boundaries` mappings. Mapping keys must be
known edge identifiers. Each supplied law must match the network clock; source
identity, owner, evidence and numeric wall settings are checked again after the
run. A missing key means that source is absent on that edge.

Darcy friction reuses the single-pipe frozen-factor momentum relaxation with
the Darcy factor convention. It changes momentum while leaving total energy
unchanged, so lost kinetic energy remains internal energy. The caller owns the
factor law and its evidence; the model does not insert a roughness correlation.
Fixed-wall heat uses `q''' = 4 h (T_wall - T) / D` as a volumetric source.
Positive values add energy to the gas. `cumulative_wall_heat_in_j` records the
signed discrete source integral, and the network energy residual subtracts this
external heat ledger. An explicit thermal timestep bound is enforced before
committing source updates. Neither feature adds gravity, wall thermal storage,
or calibrated transfer coefficients.

## Numerical and physical limits

- Each pipe is a constant-area, horizontal, one-dimensional Euler segment with
  first-order Rusanov face fluxes and a shared explicit CFL limit no greater
  than 0.5.
- One EOS object and one property basis are shared by every edge and node.
  Cell states must remain in the provider's homogeneous gas/supercritical domain.
- Junctions have no finite volume, momentum storage, thermal mass, heat loss,
  pressure loss, tee geometry, or mixing-loss coefficient. Pressure and
  temperature brackets are required. A failed node root aborts the run.
- Friction and fixed-wall heat transfer are optional caller-evidenced per-edge
  source laws. Finite reservoirs use one fixed-volume mixed state and explicit
  EOS-domain bounds. Gravity, wall thermal storage, pipe elasticity,
  valve/orifice, composition change, phase transition, leak models and detailed
  tank qualification are not included at this level.
- This result is not an LH2 source/dispersion model. The underlying segmented
  equations require a gas-domain EOS state; a cryogenic liquid feed needs a
  separately qualified flashing/source boundary.
- A closed software ledger and synthetic contract do not qualify CoolProp's
  hydrogen EOS for a pipeline, prove a junction law against measurements, or
  validate a facility network.

Six synthetic Hangang contracts are defined in
`validation/cases/caloric_pipe_network_waves.py`. They are deferred and have not
been executed. The model status remains `implemented_unverified` until those
contracts run on a pinned source and independent experimental comparison is
available.

## 2026-11-01 closed-end momentum orientation correction

A newly executed reservoir/nozzle case exposed unstable pipe primitives.
Diagnosis found that the closed right face used the left-face reflected/inside
Rusanov ordering. The right face now uses inside/reflected ordering, preserving
the correct dissipative momentum sign. The native CoolProp ±5 m/s short-step
regression passed all four endpoint comparisons with maximum momentum-density
error 1.78e-15 kg/m2/s and direction-mirror symmetry. Closed-wall mass/energy
checks alone would not detect the original sign error.

The original tank10MPa/pipe4MPa, CFL0.2, 0.02s pressure-jump/nozzle replay
subsequently completed in both the choked and back-pressure-limited regimes.
The earlier two-phase rejection no longer occurred after correcting wall
orientation. Phase, positivity and pressure/temperature gates were retained.
The distinct isothermal-network closed-boundary implementation was inspected
and does not share this reflected-state ordering path.


## 2026-11-01 executed nozzle balances and regression status

A second defect affected reported combined-system residuals rather than the
conserved updates. Nozzle mass and energy debits were already subtracted from
the finite tank. The residual must add those positive withdrawals to the stock
change. Subtracting them again reported minus twice the withdrawn quantity.
A separate 1 microsecond native-HEOS step isolated the error: nozzle mass was
3.45289101314e-8 kg and withdrawal energy 0.138296504533 J, while the old
reported residuals were -6.90578203069e-8 kg and -0.276593009038 J. Evaluating
stock change plus withdrawal gave -4.41733240647e-17 kg and 2.77883549504e-11 J.
The two nozzle terms in the residual now use the correct positive sign.

Local Python 3.12 / CoolProp 8.0.0 execution passed all three cases in
`validation/cases/caloric_reservoir_nozzle.py`:

- `hydrogen-caloric-network-closed-wall-momentum-reflection`: actual HEOS
  states at 4 MPa and 300 K, velocities +5/-5 m/s, and a 1 microsecond step.
  Four endpoint momentum-density comparisons had maximum error
  1.77635683940e-15 kg/(m2 s), with mirrored pressure/velocity solutions.
- `hydrogen-caloric-network-nozzle-blowdown-projection`: the original 24-cell,
  2 m pipe, 0.1 m3 tank, 3 mm nozzle with effective-area factor 0.8, maximum
  CFL 0.2, and 0.02 s window were retained. Both 101325 Pa and 8 MPa back
  pressures produced the intended choked/back-pressure-limited native regimes,
  positive mass/energy withdrawal, changing tank pressure/temperature, and
  accepted-step source projections. In the choked run 1853 source samples
  represented 0.000676511832075 kg and 2697.87082455 J withdrawal; tank pressure
  changed from 10 MPa to 9.75139496989 MPa and temperature from 300 K to
  299.055276579 K. The back-pressure-limited run's maximum combined residuals
  were 2.93710368526e-16 kg and 6.78483047523e-10 J. Both runs passed the
  declared 1e-7 kg / 0.1 J residual budgets and exact projection/debit comparison.
- `hydrogen-caloric-network-nozzle-identity-domain-depletion-rejections`:
  mismatched ParaHydrogen basis, the tight pressure domain, and a deliberately
  oversized 10 m opening all rejected. The last input forces a nonpositive
  candidate mass; its original mass-positivity cause is checked semantically.
  No clipping or phase/domain relaxation was introduced.

The executed network source SHA-256 was
`99c76a3b91f59c6d5e49edc01cdf0923e9f35f353735a58b8eec2376046e56fc`.
The executed case-file SHA-256 was
`73145eed94f96cbb141aa8c9cf3036315b9c3401ff189c57c462b871a21d6aa2`.
After execution, the report-only interval-mass list was replaced with its
sum/count/minimum/maximum to prevent console truncation. This did not alter
inputs, solver equations, budgets or assertions; the eight-minute numerical
replay was not repeated for that reporting change. The full positive case
reported 510.564 s wall time on this Windows host, a workload diagnostic rather
than a speed guarantee.

These are native-property numerical/component checks with prescribed geometry
and states. The initial tank/pipe pressure jump means tank evolution includes
pipe exchange as well as nozzle withdrawal. No independent measured blowdown,
pressure-wave, junction, valve-device or facility qualification follows. The
six separate network/junction contracts above have their own execution status.
