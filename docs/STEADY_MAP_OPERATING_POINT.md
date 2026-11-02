# Bounded steady gas-turbine map operating point

`h2physics.combustion.steady_map_solver` searches a caller-bounded steady
map-matched operating point while reusing the existing native Cantera Brayton
cycle and the admitted compressor/turbine map APIs. It does not implement a
second compressor/turbine thermodynamic cycle.

## Unknowns and closure equations

The solve vector is exactly:

1. compressor corrected speed;
2. compressor pressure ratio;
3. compressor-inlet air mass flow in kg/s.

The speed-link callback maps compressor corrected speed to turbine corrected
speed. Two corrected-flow callbacks convert actual compressor air flow and actual
turbine gas flow to their respective corrected kg/s map coordinates. Each callback
has a separate evidence identity. These conversions are not inferred from the
map axes.

The three residuals are:

| Residual | Definition |
|---|---|
| Compressor flow | Converted air flow minus interpolated compressor-map corrected flow |
| Turbine flow | Converted air-plus-declared-fuel flow minus interpolated turbine-map corrected flow |
| Shaft target | Turbine gross power minus compressor power, explicit mechanical loss, and caller target |

Cantera's `run_open_cycle_brayton()` calculates each trial's states and powers
after the selected map efficiencies are applied. Compressor and turbine map
interpolation reject points outside their supplied domains. The declared
pressure-ratio search interval is prechecked against the implied turbine expansion
map interval. Any turbine speed from the speed-link callback outside its map is
rejected.

Inputs contain multiple initial seeds and bounds for all three unknowns. Every
seed is solved independently with bounded nonlinear least squares. Only roots
meeting both map-flow tolerances and the shaft-target tolerance are retained.
Numerically distinct roots are returned together as `status="multiple"`; the
caller must inspect them. `unique_candidate` is available only when every seed
converges to the same clustered root. If one or more seeds fail, status is
`incomplete_search` even when another seed found a root. Optimizer convergence
alone is not accepted as physical closure.

```python
from h2physics.combustion.steady_map_solver import (
    MapOperatingSeed,
    SteadyMapSolveInputs,
    solve_steady_map_operating_point,
)

problem = SteadyMapSolveInputs(
    cycle_inputs=base_cycle,
    compressor_map=compressor_map,
    turbine_map=turbine_map,
    compressor_speed_bounds=(speed_min, speed_max),
    compressor_pressure_ratio_bounds=(ratio_min, ratio_max),
    air_mass_flow_bounds_kg_s=(air_flow_min, air_flow_max),
    seeds=(seed_a, seed_b),
    speed_link=caller_speed_link,
    compressor_corrected_flow=caller_compressor_flow_conversion,
    turbine_corrected_flow=caller_turbine_flow_conversion,
    speed_link_evidence_id="project:shaft-speed-relation-v1",
    compressor_flow_evidence_id="project:compressor-correction-v1",
    turbine_flow_evidence_id="project:turbine-correction-v1",
    shaft_loss_evidence_id="project:shaft-loss-v1",
    shaft_target_evidence_id="project:net-power-target-v1",
    shaft_mechanical_loss_w=declared_loss_w,
    shaft_residual_target_w=target_net_power_w,
)
result = solve_steady_map_operating_point(phase_factory, problem)
if result.status == "unique":
    operating_point = result.unique_candidate
```

The callback contract is pure and deterministic for a given point. Callers must
provide supported units, applicability ranges, uncertainty and source evidence;
string evidence IDs alone do not prove a conversion. The result retains optimizer
attempts, all distinct accepted roots, both source maps, the final existing
map-matched Brayton run, shaft loss and target terms. `require_current()` rechecks
maps, candidate runs and callback-derived residuals.

This point model has no cooling or bleed streams, fuel compression, gearbox or
generator conversion, surge/choke constraints, acceleration, transient controls,
off-design maps, multi-spool dynamics or experimentally qualified machine data.
The algebraic shaft target is only as complete as the caller-declared boundary.
The synthetic case `hydrogen-brayton-bounded-map-operating-point-solve` is deferred
in the `hydrogen-engine` profile and has not run. Cantera thermodynamic and reactor
ownership follows its public [3.2 Python API](https://cantera.org/3.2/python/thermo.html)
and [zero-dimensional API](https://cantera.org/3.2/python/zerodim.html); bounded
least squares uses SciPy's public [optimization API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).
