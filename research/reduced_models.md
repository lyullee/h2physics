# Reduced-model verification

All parameters below are authored synthetic cases, not material fits. They test equations/numerics and do not establish experimental validity.

## Hydride analytic limit

At constant 300 K, Peq=100 kPa, f=200 kPa, k_abs=0.01/s and x0=0.1, the independent isothermal solution is x(t)=1−0.9 exp(−0.01t). The zero reaction-heat case isolates that kinetic limit.

| Relative tolerance | Max fraction error | Max reduced heat residual J |
|---:|---:|---:|
| 1e-06 | 1.15692847e-07 | 0 |
| 1e-08 | 1.11272613e-09 | 0 |
| 1e-10 | 1.40043532e-11 | 0 |

With positive reaction heat and no boundary heat, the adiabatic reduced energy residual is 1.6643753e-10 J. Hydrogen stored is capacity × fraction; the caller must supply the opposite gas-reservoir transfer. This is not a full gas/vessel energy ledger.

## Planar diffusion startup

L=1 m, D=0.1 m²/s, initially empty slab; left concentration=1, right=0 mol/m³. At t=1 s the exact average concentration follows the integrated Fourier series 0.5 − (4/pi²) sum over positive odd n of exp(−n² pi² D t/L²)/n².

| Cells | Average concentration error mol/m³ | Max inventory residual mol/m² |
|---:|---:|---:|
| 10 | 0.00249224653 | 8.46102494e-11 |
| 20 | 0.00061944891 | 1.00278052e-10 |
| 40 | 0.00015464178 | 6.55289969e-11 |
| 80 | 3.86470146e-05 | 3.59972296e-11 |

Successive grid error ratios: 4.02333, 4.0057, 4.00139.
Approximately fourfold reduction per doubled grid verifies the expected second-order spatial behavior.
Closed finite-trap equilibrium, reversed permeation and entity/H2 flux conversion are tested in the suite.

Electrolyzer/fuel-cell tests use one shared synthetic reaction-energy basis to check direction, Faraday stoichiometry, polarization limits and the power ledger. No empirical polarization calibration is claimed.
