# Finite cylinder-wall thermal state

`CylinderWallThermal` adds one finite sensible-energy node to
`run_open_cylinder_segment()`. Cantera still owns the reacting ideal-gas phase,
flow devices, slider-crank volume, and the coupled native integration. The wall
is an additional scalar state attached to that same native reactor network; the
adapter adds no separate combustion or cylinder solver.

## Equations and signs

The caller supplies a fixed wall heat capacity `Cw`, initial and reference wall
temperatures, and a gas-wall conductance `UA`. Heat from gas to wall is
`Qgw = UA * (Tgas - Twall)`. The optional caller callback returns external heat
into the wall, `Qext`, in W. Thus the wall energy rate is `Qgw + Qext`, while
`-Qgw` is applied to the native cylinder gas. Internal gas/wall transfer cancels
from the combined balance; `Qext` remains an external term.

With constant wall heat capacity, the retained wall energy is
`Uw = Cw * (Twall - Tref)`. The trace reports the integrated gas-side contact
heat, integrated external wall heat, wall temperature and wall energy on the
same accepted output clock as the cylinder. Its combined sampled residual is

`ΔUgas + ΔUw + ∫P dV - Hin + Hout - Qext`.

The integrator accumulates gas/wall and external heat contributions as native
additional ODE states, rather than reconstructing these energy terms from sparse
output samples. The reported combined residual remains an output-sample audit;
it does not replace Cantera's internal solver tolerances.

## Python API

```python
from h2physics.combustion import CylinderWallThermal, run_open_cylinder_segment

wall = CylinderWallThermal(
    heat_capacity_j_k=wall_capacity_j_k,
    reference_temperature_k=298.15,
    initial_temperature_k=initial_wall_temperature_k,
    conductance_ua_w_k=gas_wall_ua_w_k,
    energy_reference_id="mechanism:declared-native-reference-v1",
    property_evidence_id="wall-capacity-source-revision",
    boundary_evidence_id="coolant-boundary-source-revision",
    external_heat_into_wall=lambda time_s, gas_k, wall_k: coolant_heat_into_wall(time_s, wall_k),
)
trace = run_open_cylinder_segment(
    phase_factory, mechanism_basis, initial_charge, geometry, boundary,
    absolute_clock_origin_s=t0,
    crank_start_rad=crank_start,
    crank_end_rad=crank_end,
    wall_thermal=wall,
)
trace.require_current()
print(trace.wall_temperature_k, trace.sampled_first_law_residual_j)
```

All temperatures are K, heat capacity J/K, conductance W/K, time s, and energy
J. The optional callback receives absolute run time, gas temperature and wall
temperature and returns signed watts into the wall. It must be deterministic,
remain valid over all internal native trial calls in the run window, and retain
its own evidence and state. The input seal fingerprints callback code,
defaults, closure contents, and ordinary bound-object state; mutating those
after trace issuance makes `trace.require_current()` fail. Mutable state reached
only through module globals, external services, or opaque extension objects
cannot be introspected reliably and remains the caller's responsibility; keep
those inputs immutable for the lifetime of the trace. Feed-stream
enthalpy-reference labels must match the
wall's declared `energy_reference_id` when feed streams are present. This label
records the caller's basis assertion; it cannot certify that the mechanism or
the external coolant data are qualified.

## Model limits and evidence

This is one uniform wall node with one effective gas-wall conductance. The model
has no spatial wall conduction, piston-head/ring separation, oil film, deposits,
temperature-dependent capacity, radiation unless explicitly included by the
external callback, or calibrated heat-transfer coefficient. It does not add a
heat-transfer correlation. The caller must select a physically supported UA and
boundary callback for the intended engine and operating domain.

The deferred `hydrogen-engine-wall-*` cases check coupled energy bookkeeping,
the zero-UA reduction, and a signed external heat boundary using `ohmech` from
the separately installed Cantera `h2o2.yaml` resource. The validation resolves
that filename through `cantera.get_data_directories()` and reads it in place;
the mechanism is not copied into or redistributed with this project. Its
existing source/license metadata remains attached to the mechanism basis.

The energy-ledger cases run a three-level output-grid probe at 72, 144, and 288
samples per crank revolution. They report each maximum absolute sampled
first-law residual and the finest observed value as a *candidate* tolerance
scale. A probe passes only when all values are finite and each refinement
strictly reduces the residual. This deliberately does not insert a guessed
joule limit or claim that the finest observed residual is a universal error
bound. The next validation stage should retain the raw three-value sequence,
review convergence behavior across the deferred run matrix, then set any
project acceptance budget from that evidence and a stated engineering use.
The probe assesses sampled-ledger convergence only; it does not demonstrate
solver-order convergence, model accuracy, or experimental qualification. The
cases remain unexecuted, and no engine-wall measurement qualification or
full-cycle closure is implied.

Cantera 3.2's public extensible-reactor API supports adding coupled state
equations while retaining `ReactorNet` integration. The implementation uses
that API and the documented ideal-gas control-volume temperature equation:
[Extensible reactor guide](https://cantera.org/3.2/userguide/extensible-reactor.html),
[ideal-gas reactor](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html).
