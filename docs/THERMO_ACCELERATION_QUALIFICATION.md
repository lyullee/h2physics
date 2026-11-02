# Executed CoolProp acceleration checks

The reference remains native CoolProp HEOS. Acceleration is selected explicitly
for a declared domain after direct-EOS error and performance checks. A property
table does not establish independent experimental EOS or facility validation.

## Gas-property table: local run, 2026-11-01

CoolProp 8.0.0 `BICUBIC&HEOS` passed the existing qualification case over normal
hydrogen at 0.1–90 MPa and 230–400 K. It evaluated 1004 PT states and 2000 PH/PS
inverse states, plus nine separately selected holdout paths. The relative error
budget was 0.005 (0.5%) for every checked property.

| Property | Largest relative difference from direct HEOS |
|---|---:|
| Density | 1.35e-6 |
| Specific enthalpy | 4.42e-7 |
| Specific internal energy | 1.13e-6 |
| Isobaric heat capacity | 1.50e-5 |
| Isochoric heat capacity | 2.25e-5 |
| Viscosity | 4.01e-4 |
| Thermal conductivity | 5.92e-4 |
| Speed of sound | 1.09e-5 |

The maximum holdout error was 2.74e-6. With the explicit
`derive_from_h_p_rho` dependent-energy policy, the largest internal-energy
adjustment was 1.61 J/kg and the maximum relative h−u−p/rho identity residual
was 7.53e-17. The adjustment and policy are retained in the issued report.
Out-of-domain states, an unsupported cold envelope, changed definitions,
replaced native states and forged/cloned reports were rejected.

The measured mixed PT/PH/PS workload averaged 520.30 microseconds per direct
HEOS call and 132.69 microseconds per tabular call: 3.92 times faster. These
timings include the wrapper and sampled workload; they exclude initial table
construction and do not demonstrate the same gain for a PT-only application.
One timing repetition was used, without controlled machine load. Requalify
and benchmark the actual deployment workload before selecting acceleration.

```python
from h2physics.thermo import CoolPropProperties, GasEnvelope, QualifiedGasTable

reference = CoolPropProperties("Hydrogen")
table = QualifiedGasTable(
    reference, GasEnvelope(1e5, 90e6, 230.0, 400.0),
    validation_points=1000, timing_repetitions=1,
    internal_energy_policy="derive_from_h_p_rho",
)
state = table.state_pt(5e6, 300.0)
useful_on_this_workload = table.qualification.meets_speedup_target(2.0)
```

## Isothermal pressure/density lookup: local run

The earlier 512-point result used an inconsistent log-linear inverse: forward
`log(P)` interpolation used linear density coordinates, while its inverse used
log-density coordinates. The stored grid digest alone does not identify that
query-method defect. This result is superseded by the corrected local replay below.

The query identity is now `isothermal-eos-table-v2`; the existing grid digest
continues to identify the same node data. Old qualified artifacts are rejected by
the existing receipt/table-identity guard: the former 0.05038% inverse-density
error does not describe the corrected query algorithm. Unqualified grid artifacts
can still load, returning no qualification; rerun direct-EOS qualification before
relying on their current accuracy. No stored receipt is silently relabeled.

The inverse now uses the same linear density coordinates as the forward pressure
interpolant. A direct algebraic counterexample with density nodes 1 and 4 and
pressure nodes 1 and 16 previously returned density 2 for pressure 4 although
forward pressure at density 2.5 was 4; it now recovers 2.5. Five tests passed,
covering this example, reciprocal roundtrips at multiple temperatures on nonuniform
density grids, exact nodes and outside-envelope rejection for both interpolation
modes. Two further persistence regressions passed: v1-qualified artifacts reject
under the v2 query identity, while unqualified v1 grids load with no receipt and
retain corrected roundtrips. The existing linear branch and separately interpolated sound speed are unchanged.

The corrected `IsothermalEOSTable` passed its existing 512 held-out direct-HEOS
checks over 0.05-20 kg/m3 and 260-360 K with a 41-by-11 log-linear grid, seed
20261031, CoolProp 8.0.0 HEOS Hydrogen. Maximum relative differences were
0.2976461% for pressure, 0.2971717% for inverse density and 0.0098197% for
isothermal sound speed, all within the explicit 1% budget. Outside-domain calls
were rejected. Measured speedup was 0.1777953: about 5.62 times slower than
direct HEOS on this workload. This pure-fluid timing does not establish whether
frozen-mixture tables would accelerate their substantially different native calls.
The table is not selected as a default acceleration path.

This table still interpolates source sound speed independently of its pressure
interpolant. Therefore its returned sound speed is generally not exactly
`sqrt(dP_interpolated/drho)` at fixed temperature. The current qualification does
not prove that derivative identity or qualify the table for the generalized Darcy
density integral plus independent momentum ODE. Those hydraulic and quasi-steady
network routes continue to require their existing direct CoolProp providers.
Future table admission must reuse this table with a consistent pressure/inverse/
derivative contract, handle interpolation-knot derivatives, retain native mixture
basis and phase/domain evidence, and compare whole flows and sonic gates against
direct CoolProp before measuring end-to-end benefit.

The artifact integrity replay also passed after repairing its corruption fixture.
The earlier absolute ZIP byte offset 64 altered container metadata without changing
numeric values, so its rejection expectation was invalid. The fixture now changes
byte 64 within pressure-array data, preserves the original qualification/semantic
hashes, and rewrites a valid ZIP with fresh CRCs. Loading rejects the stale
pressure-array checksum specifically. This verifies semantic content integrity;
benign container-header differences are not claimed to change table identity.

## Reproduction and source integrity

The executable cases are `validation/cases/thermo_tables.py` and
`validation/cases/isothermal_eos_table.py`. The former initially failed because
the qualification issuer was called with positional values despite accepting
keyword fields only. That production defect is corrected; all three cases
then passed. Detailed metrics remain available as Python `ValidationOutcome`
objects. The new fields do not turn timing success into an accuracy decision.

For reaction-species calorimetry, `CoolPropMolarEnthalpy` currently requires
direct HEOS. `coolprop_carrier_caloric` binds its actual native state ownership,
library/backend definitions and reference offsets to the common caloric source.
Its reaction-enthalpy table path requires separate qualification and is rejected
until that qualification exists. The fuel-cell example uses this common binding
and declares the actual normal-hydrogen spin basis.

Primary library reference: https://coolprop.org/coolprop/LowLevelAPI.html .

The normal-hydrogen gas-table envelope does not qualify a multi-species
reaction provider over the same pressures. Every constituent fluid must admit
the requested native state; melting-line or other native domain failures remain
explicit errors. No imposed-phase or handwritten EOS fallback is introduced.
