# Native vacuum insulation and wall heat

`h2physics.adapters.lh2dt_insulation` composes the existing MIT LH2DT
`VacuumInsulation`, `VacuumJacketedPipeEnvelope` and `LayeredTank` capabilities.
LH2DT owns radiation, distributed MLI/solid conduction, support conduction,
molecular residual-gas conduction, discrete penetration heat and tank integration.
The host supplies provenance, explicit wall/penetration allocations, signed heat
boundaries, absolute clocks and independent inventory checks.

The executable scientific check uses separately installed native revision
`b2f276333c1b1793c39f25763703d196d36742ec`, version 0.1.2, already reviewed in
`HANDOFF.md`. Original native objects remain inspectable. No native source,
heat-transfer coefficient, solver or property equation is replaced.

```powershell
.venv\Scripts\python scripts/check_insulation_integration.py
.venv\Scripts\python -m pytest tests/test_lh2dt_insulation.py -q
```

`--native-packages PATH` selects a separately installed native target. The script
requires the exact recorded aggregate module fingerprint and checks it again
before finalizing `research/native_insulation.md`. That report includes actual
numerical results, runtimes, failed cases and source/test/script/native fingerprints.
All verification parameters are authored synthetic inputs. No vendor rating,
measured heat-leak fit or experimental qualification follows from a passed check.

## Native boundary and parameter evidence

`Lh2dtVacuumInsulation(native, evidence=...)` retains an actual native
`VacuumInsulation` evaluator. `InsulationEvidence` requires:

- Geometry and area convention identity.
- Construction/closure evidence identity covering effective emissivity, MLI and
  support conductances, gas coefficient and localized paths.
- Residual-gas identity and evidence for absolute annulus pressure/domain.
- Inspectable source identities and parameter origin.

Temperatures are absolute K; area is m2; radiation uses the native effective
emissivity; distributed solid/support and local conductances use W/K; the native
gas coefficient uses W/(m2 K Pa). Vacuum input is absolute pressure in Pa, with an
explicit native maximum valid pressure. Gauge pressure is rejected. The molecular
pressure law is not extended to continuum gas, an ingress event or an unspecified
residual gas. Construction-specific coefficient evidence is required for application
qualification, even when a synthetic test supplies a finite domain bound.

`evaluate(warm_temperature_k, cold_temperature_k, vacuum_pressure_pa_abs)` returns
`InsulationHeat`. It retains the original native result, input temperatures/pressure,
evidence, individual signed paths, path-sum residual and the existing
`BoundaryPower(heat_w=...)` contract. Heat is positive into the designated cold-side
boundary. Reversed thermal gradients retain negative heat. Every finite native path
must have the expected sign, vanish at zero gradient and close its native total.
`InsulationClosureError.native` retains a failed output without assigning accepted
boundary power. Native parameter replacement requires explicit rebinding of the
adapter/evidence rather than silently retaining stale parameter provenance.

The native effective-UA output is a heat/delta-temperature diagnostic and equals
zero at exactly equal boundary temperatures. That value is not the differential
conductance or a replacement for the nonlinear radiation law.

## Areas and localized heat paths

`WallHeatAllocation` requires wall-zone identities, explicit geometric area
fractions, explicit fractions for every native localized path, and allocation
evidence. Each partition sums to one; invalid fractions are never normalized.
Distributed area fractions and discrete penetration fractions remain separate.

`boundary.partition(warm, wall_temperatures, pressure, allocation=...)` delegates
directly to native `layered_wall_heat_distribution`. The returned
`PartitionedInsulationHeat` retains native zone totals, zone identities/geometry,
actual wall temperatures, aggregate signed `BoundaryPower` and evidence. It does
not evaluate the law at an averaged wall temperature or place a neck according to
an inferred area weight. The current native implementation returns zone totals,
so per-zone decomposed path diagnostics remain a receiving request.

Native partition validation accepts a zero area fraction, but construction of that
zero-area zone then fails the native positive-area requirement. The integration
report preserves this actual failure. No zero-zone repair or silent renormalization
is applied. Use positive-area wall zones until the receiving implementation defines
the treatment of zero distributed area with possibly nonzero discrete penetration.

For the pipe envelope, the native radiation/gas reference area is the jacket inner
surface. The three declared diameters are fluid bore, process outer diameter and
jacket inner diameter; nominal pipe size is not an adequate replacement. The script
checks native area, wall volume, fluid volume and gap against direct geometry limits.
`DynamicHEMPipe` currently lacks a callable external heat interface. Connecting its
nonlinear insulation through a changing scalar UA would obscure the heat boundary,
so the executed dynamic composition uses the native layered tank's public heat hook.

## Native tank and state-dependent callbacks

```python
from h2physics.adapters.lh2dt_insulation import (
    InsulationEvidence, Lh2dtVacuumInsulation, WallHeatAllocation,
)
from h2physics.core import Origin

# native_insulation and native_tank are caller-owned actual LH2DT objects.
evidence = InsulationEvidence(
    "authored warm-reference geometry",
    "authored construction closures for verification",
    "helium; authored coefficient",
    "authored annulus pressure and bounded test domain",
    ("authored synthetic verification case",), Origin.SYNTHETIC,
)
boundary = Lh2dtVacuumInsulation(native_insulation, evidence=evidence)
allocation = WallHeatAllocation(
    ("lower", "upper"), (.4, .6),
    {"neck": (0., 1.)}, "surface and neck placement drawing",
)
callback = boundary.layered_wall_callback(
    allocation,
    warm_temperature_k=lambda absolute_time, native_thermo: 295.0,
    vacuum_pressure_pa_abs=lambda absolute_time, native_thermo: 0.001,
    clock_id="declared operation clock", start_time_s=100.0,
)
result = native_tank.simulate(
    initial_state, duration_s=1.0, time_step_s=0.05,
    ambient_temperature_K=295.0, wall_heat_callback=callback,
)
```

The example requires the exact geometry/path names present on the caller's native
objects. Application use requires supporting geometry/material/pressure records,
with measured origin only when those records establish it. Set built-in tank ambient heat explicitly to zero when
this callback owns the complete external boundary; otherwise separately account
for both inputs. An optional observer receives absolute time and the actual
partition result. Warm-temperature and vacuum-pressure functions receive actual
native thermodynamic/wall observations at every integration stage. On restart,
`start_time_s` declares the offset from the native local simulation clock.

The full native `HydrogenProperties("ParaHydrogen")` is explicitly selected for
the verification tank because `LayeredTank` needs the native specific-volume
derivative API. The earlier `Lh2dtLowLevelProperties` equipment facade intentionally
exposes a narrower tested subset and fails this requirement. That actual failure
is retained; the adapter neither implements a second derivative closure nor adds
an automatic property fallback. Property/spin/energy-reference identity remains
explicit at the inventory boundary.

`layered_inventory_reader(rigid_volume_m3=..., wall_heat_capacities_j_k=...,
basis=...)` returns existing `ConservedInventory` objects from actual native
layered states. It independently evaluates fluid internal energy as
`sum(cell_mass * cell_specific_enthalpy) - pressure * rigid_volume` and declared
constant-capacity wall storage in native wall order. This is an inventory identity,
not an EOS or tank solver. State pressure must already satisfy the native rigid-volume
constraint. Explicit capacities include any connected metal; a wrong capacity cannot
be repaired by adjusting the reported external heat. Existing `InventoryBalance`
keeps boundary heat, transported enthalpy and stored fluid/solid energy separate.

## Verification and remaining qualification

The actual native computation checks independent Stefan-Boltzmann scaling,
zero-gradient and reversed heat, the near-zero and bounded molecular gas-pressure
limits, geometry/penetration partitions, an analytic time-dependent wall-storage
limit, coupled fluid/wall heat, numerical refinement and signed inventory ledgers.
Accepted-sample quadrature independently recomputes the external heat rather than
reusing the native RK-stage integral. A wrong-wall-capacity case must fail. Exact
counts, errors and budgets are recorded only after actual successful calculations.

The [NIST 2022 CODATA constant](https://physics.nist.gov/cgi-bin/cuu/Value?sigma)
provides the independent radiation constant. Primary
[NASA insulation testing](https://ntrs.nasa.gov/citations/19990053342) and
[MLI repeatability work](https://ntrs.nasa.gov/citations/20180000366) motivate
construction/test-specific qualification. A
[NASA MLI venting model](https://ntrs.nasa.gov/citations/20180002393) resolves
continuum/kinetic regimes beyond the simple bounded native molecular law. No
published curves or test coefficients are copied or represented as validation data.

Remaining work includes measured calorimeter boundaries and uncertainty, material
and residual-gas coefficients, transient warm-jacket storage, MLI compression/aging,
vacuum ingress/condensation, continuum transport, public zero-area behavior and a
general signed heat hook for lumped equipment. The present level executes native
insulation physics and finite native wall/fluid accounting under explicit synthetic
assumptions; it does not qualify a complete installed vacuum jacket.
