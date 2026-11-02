# Bounded isothermal-EOS lookup table

`h2physics.thermo.IsothermalEOSTable` is a bounded, immutable implementation of
the `IsothermalSinglePhaseEOS` protocol for repeated pressure-wave property
queries. It stores pressure and isothermal characteristic speed on explicit
mass-density and temperature axes. It does not replace the direct HEOS
provider as a reference.

## Build a table

Create the table on the compute resource that will use it, with axes chosen to
cover the model's single-phase envelope:

```python
import numpy as np

from h2physics.thermo import CoolPropIsothermalEOS, IsothermalEOSTable

source = CoolPropIsothermalEOS("Hydrogen")
table = IsothermalEOSTable.from_eos(
    source,
    density_axis_kg_m3=np.geomspace(0.05, 20.0, 81),
    temperature_axis_k=np.linspace(260.0, 360.0, 21),
    interpolation="log_linear",
)
```

The builder calls the source EOS at every grid node. Axes must be positive,
finite, strictly increasing and have at least two nodes. Pressure and isothermal
sound speed are stored as `float64` arrays of shape
`(n_temperature, n_density)`. The table requires positive values and strictly
increasing pressure with density at every temperature, which makes inverse
`density_pt(p, T)` queries single-valued. Queries outside either tabulated
axis or the interpolated pressure range raise `ValueError`; the provider never
extrapolates.

Two interpolation strategies are available:

- `linear`: bilinear interpolation in density and temperature; inverse queries
  interpolate linearly in pressure and density.
- `log_linear`: bilinear interpolation of logarithmic positive property values
  using linear density and temperature coordinates. Inverse queries interpolate
  linear density against log pressure at the requested temperature. Positivity
  is preserved by construction; a geometrically spaced density grid does not
  change the interpolation coordinate to log density.

Both strategies return an estimate between table knots, not a new thermodynamic
EOS. The object retains its source EOS identity, interpolation mode and a
SHA-256 digest over the grid axes and property arrays. Its public `identity`
combines those values for reproducible model receipts.

The current query identity starts with `isothermal-eos-table-v2`. Version 2
corrects the log-linear inverse to use the same density coordinates as forward
pressure interpolation; the grid digest still describes the unchanged node
data. See [artifact compatibility](ISOTHERMAL_EOS_ARTIFACTS.md) before loading
older qualification receipts.

## Derivative consistency and hydraulic admission

The default `sound_speed_mode="sampled"` interpolates pressure and isothermal
characteristic speed independently from their respective source values. Its
returned speed is generally not exactly `sqrt(dP_interpolated/drho)` at fixed
temperature. Agreement with native CoolProp values at sampled points does not
prove that derivative identity.

An explicit `sound_speed_mode="pressure_derivative"` instead returns the square
root of the analytic density derivative of the existing pressure interpolant.
For `linear` pressure, that derivative is the temperature-weighted pressure
slope of the active density interval. For `log_linear`, it is the interpolated
pressure multiplied by the temperature-weighted log-pressure slope. Both use
linear density coordinates and leave pressure and inverse-density queries
unchanged. At an interior density knot, the derivative uses the interval to its
right; at the maximum density it uses the last interval to its left. Derivatives
can jump at knots; this is no claim of a smooth or exact native derivative.

The builder accepts this mode as an explicit keyword. The sampled native speed
array remains stored and hashed in either mode. The node digest is unchanged
when only the mode changes, but the derivative-mode query identity includes
`pressure-derivative:` and cannot reuse a sampled-mode qualification receipt.
Thirteen algebra, inverse-version and persistence checks passed, including
multi-temperature finite differences, one-sided knots and mode-bound receipts.
A small direct-CoolProp derivative-mode test also passed: Hydrogen, linear
pressure, 12 density nodes over 1–2 kg/m3 and temperature nodes 290/300/310 K,
with 16 held-out points and seed 20261101. Pressure, inverse density and speed
each met its declared 1% relative-error budget. That bounded test reports no
speed gain and does not qualify a wider domain. The larger sampled-mode result
below does not qualify the derivative query policy.

The generalized Darcy density-integral solver and quasi-steady pipe network
still admit their direct CoolProp providers and reject tables in either mode.
Derivative consistency alone does not qualify native mixture basis, phase/domain
evidence, whole-flow accuracy, sonic gates or end-to-end performance.

The pressure-wave API can accept the table through its EOS protocol, but API
acceptance is not whole-solver qualification. A table-based wave calculation
needs direct-CoolProp comparison of the actual solution and characteristic-speed
limits, in addition to the property-error receipt. No table acceleration is
selected automatically.

## Accuracy and performance receipt

Table generation alone does not assert accuracy or speed. Call
`qualify_isothermal_eos_table(table, source, ...)` with the same direct EOS
identity used to build the table. The routine creates a deterministic held-out
sample, compares `p(rho,T)`, `rho(p,T)` and isothermal sound speed against that
direct provider, and records maximum relative errors, sample seed/count, the
declared error budget, and reference/table per-query timings. The returned
`IsothermalEOSTableQualification.error_gate_passed` reports only whether this
sample met that caller-selected budget. The timing ratio is diagnostic and
machine/workload-specific; it is not an accuracy metric or speed guarantee.

The case `isothermal-eos-table-interpolation-accuracy` uses a single-phase
hydrogen grid and a seeded held-out sample. Its corrected local replay passed
512 held-out checks on a 41-by-11 log-linear grid over 0.05–20 kg/m3 and
260–360 K against CoolProp 8.0.0 HEOS Hydrogen. Maximum relative errors were
0.2976461% for pressure, 0.2971717% for inverse density and 0.0098197% for
isothermal speed, within the declared 1% budget. Measured speedup was 0.1777953,
about 5.62 times slower than direct HEOS for that workload; it is not a default
acceleration path. See [executed qualification](THERMO_ACCELERATION_QUALIFICATION.md)
for the inverse correction, timing limits and persistence regressions.

A passing result compares the table only with the matching CoolProp HEOS
release over the declared domain. It does not independently qualify HEOS,
validate the finite-volume solver, or establish facility performance. Refine
the density/temperature grid and repeat held-out comparisons before using the
table in a sensitivity-critical calculation. An explicitly selected wave run
uses `IsothermalPipeWaveModel(eos=table)` subject to the additional solution-level
qualification above.
