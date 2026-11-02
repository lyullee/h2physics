# Finite-capacity wall for caloric pipe waves

`LumpedPipeWall` couples one finite wall energy store to the single-segment
`CaloricPipeWaveModel`. The base gas solver remains the owner of compressible
mass, momentum and total-energy updates. At every requested outer interval the
wall temperature is frozen and supplied through its ordinary heat boundary;
the accepted integrated gas heat is then debited from wall energy.

## Equations and units

The wall is represented by a single, perfectly mixed temperature with total
heat capacity `C_wall` in J/K. Positive `Q_gas` means heat entered the gas:

```
Delta U_wall,gas = -Q_gas
T_wall,after_gas = T_wall,before - Q_gas / C_wall
```

When ambient exchange is enabled, a constant ambient temperature and total
conductance `UA` in W/K are applied after the gas exchange. This substep has an
exact exponential solution:

```
T_next = T_ambient + (T_after_gas - T_ambient) exp(-UA dt / C_wall)
Q_ambient = C_wall (T_next - T_after_gas)
```

The returned combined residual is `Delta E_gas + Delta U_wall - E_boundary -
Q_ambient`, where the gas boundary term is the existing signed pipe ledger.
Internal gas-to-wall transfer cancels from the combined balance.

## API and ownership

```python
from h2physics.caloric_pipe_finite_wall import (
    LumpedPipeWall, simulate_caloric_pipe_with_finite_wall,
)

wall = LumpedPipeWall(
    identifier="pipe-wall", state_owner_id="asset-owner",
    state_evidence_id="wall-inventory-source", clock_id="run-clock",
    initial_temperature_k=300.0, heat_capacity_j_k=8.0e4,
    gas_heat_transfer_coefficient_w_m2_k=12.0,
    ambient_temperature_k=295.0, ambient_ua_w_k=40.0,
    ambient_evidence_id="ambient-boundary-source",
)
trace = simulate_caloric_pipe_with_finite_wall(
    pipe_model, wall=wall, initial_pressure_pa=pressure_cells,
    initial_temperature_k=temperature_cells, initial_velocity_m_s=velocity_cells,
    time_samples_s=output_times_s, clock_id="run-clock",
)
```

The caller owns the wall material/inventory inputs, heat-transfer coefficient,
ambient condition and evidence IDs. `heat_capacity_j_k` describes the entire
represented pipe wall; it is not a per-length or volumetric quantity. Ambient
temperature and evidence must be supplied together, and positive ambient UA
requires them. The gas and wall share one explicit clock. The trace holds each
underlying issued `CaloricPipeWaveTrace`, so existing gas fields, EOS identity,
and solver ledgers remain available interval by interval.

## Fidelity and limits

This is a first-order operator split: gas evolution uses the wall temperature
at the beginning of an interval, then wall temperature is updated once from
the exact gas heat integral. Refine caller output intervals and compare results
before relying on a trajectory. The wall is one perfectly mixed node for the
whole pipe; there is no axial wall conduction, spatially varying wall capacity,
solid stress, phase change, insulation layer, or wall-temperature-dependent
material property. The current wrapper is for closed pipe endpoints and does
not compose reservoir, valve, friction or branched-network boundaries. It does
not qualify a hydrogen pipeline or replace site-specific validation.

The equations follow energy conservation for a lumped thermal capacitance and
Newtonian conductance. They are independently expressed in this package and
reuse the project's caloric Euler pipe solver; no third-party implementation
is embedded. The underlying gas flux reference and scope are documented in
[`CALORIC_PIPE_WAVES.md`](CALORIC_PIPE_WAVES.md).

## Deferred verification

The synthetic contract `hydrogen-caloric-pipe-finite-wall-energy-closure` is
registered under Hangang profile `gas-compressible-pipe`. It checks finite-wall
temperature response, gas/wall conservation, external ambient heat accounting,
and retention of one issued gas trace per outer interval. It has not been run.

The outer `time_s` array gives the run clock. Each retained inner gas trace
uses a local `0..dt` clock; tuple entry `i` corresponds exactly to outer interval
`[time_s[i], time_s[i+1]]`. Construction is restricted to completed runs, and
the trace replays wall temperature, energy-transfer arrays, combined residuals,
wall provenance, EOS identity and pipe geometry from its retained solver
traces.
