# Electrocatalyst measurement analysis

`h2physics.electrocatalyst_metrics` analyzes measured electrode quantities. It
complements the existing polarization laws; it does not introduce another
electrolyzer engine or infer material mechanisms from a straight fitted line.

## Potential and current bases

`corrected_overpotential_v` returns signed `E_measured - E_equilibrium - I R`.
Use amperes, volts and the **remaining uncompensated** resistance in ohms.
If an instrument already compensates part of the resistance, passing the full
resistance again would overcorrect the result. Both potentials must use the
same reference electrode scale. Anodic current is positive, cathodic negative.
The function does not convert reference electrodes or subtract an unspecified
equilibrium potential automatically.

`fit_tafel` fits the selected branch using
`abs(eta) = intercept + slope * log10(abs(j)/(1 A/m²))`.
The slope is in V/decade and the fitted exchange current is in A/m². The
current-density basis is explicitly `geometric` or `ECSA`; no implicit area
conversion is applied. The caller must supply a positive absolute-current
window, protocol identity and at least three branch-consistent samples.
There is no automatic choice of a favorable linear window.

Optional standard uncertainties in voltage produce a weighted least-squares
fit, assuming independent voltage errors and negligible current error. Otherwise
the covariance uses the residual variance with `n-2` degrees of freedom. Its
row/column order is intercept, slope. The result retains selected indices,
residuals, R² and the fitted window. Exchange current is an extrapolation of the
selected Tafel model, not necessarily a directly measured equilibrium current.

`transfer_coefficient_times_electrons(T)` returns
`ln(10) R T / (F slope)`, the product `alpha * n_effective` under the selected
kinetic convention. It does not equate the effective kinetic electron count to
the overall two-electron HER or four-electron OER charge balance. The slope
contains a voltage scale proportional to `RT/F`; an inverse-voltage expression
is dimensionally incompatible. For limitations of apparently linear fits, see
[Khadke et al., 2021](https://doi.org/10.1038/s41598-021-87951-z).
No paper data, figures or passages are included.

## Time-aligned product and charge

`compare_product_to_charge` takes a sampled signed current and collection-interval
edges plus product amounts in **moles per interval**. Current and product clocks
must have the same explicit identity. A time shift, collection loss correction,
gas residence delay or pressure/volume-to-moles conversion must be established
before calling the function. Collection intervals must lie inside current
support; no extrapolation or hidden time alignment occurs.

Current is piecewise linear and integrated at all sample and interval boundaries.
An interval containing a polarity reversal or zero charge is refused. Forward
and reverse production need separate intervals and reaction interpretation.
The result reports charge magnitude and `FE = z F n_product / abs(Q)` with
`z=2` for H₂ and `z=4` for O₂. A measured FE above one remains visible as a
balance/measurement diagnostic; it is not clipped into a plausible range.
Uncertainty in collected gas, crossover, dissolved product and residence time
is not removed by this charge accounting.

## Active-site turnover

`turnover_frequency_from_product` computes product mol/s divided by counted
active-site mol. A site-basis identifier is mandatory. Site mol is not catalyst
mass, the number of atoms, geometric area or the total bulk metal inventory
unless the measurement protocol explicitly establishes that relationship.
`turnover_frequency_from_current` additionally requires FE in [0,1] and the H₂
or O₂ product. HER uses two electrons per product molecule; OER uses four. This
predictive conversion refuses FE above one, while the measurement comparison
above retains it for investigation. Finite-input arithmetic that overflows is
rejected rather than returning an infinite result.

## Executable synthetic example

```python
import numpy as np
from h2physics.electrocatalyst_metrics import (
    corrected_overpotential_v, fit_tafel, turnover_frequency_from_current,
)

j = -np.geomspace(1.0, 1000.0, 13)  # A/m², geometric area, cathodic branch
area_m2 = 1e-4
remaining_resistance_ohm = 3.0
eta = -0.12 * np.log10(abs(j) / 0.02)  # authored kinetic-only fixture
measured_v = eta + j * area_m2 * remaining_resistance_ohm
corrected_v = corrected_overpotential_v(
    measured_v, 0.0, j * area_m2,
    remaining_uncompensated_resistance_ohm=remaining_resistance_ohm,
)
fit = fit_tafel(
    corrected_v, j, branch="cathodic", area_basis="geometric",
    protocol_id="synthetic demonstration", current_density_window_a_m2=(1.0, 1000.0),
)
print(fit.slope_v_decade, fit.exchange_current_density_a_m2)  # 0.12, 0.02
tof = turnover_frequency_from_current(
    -1.0, product="H2", faradaic_efficiency=0.8,
    active_site_amount_mol=1e-6, site_basis_id="synthetically declared sites",
)
print(tof)  # product molecules per counted site per second
```

The example verifies arithmetic, not a real catalyst fit. No new data license or
experimental calibration is implied by the synthetic coefficients.

## Reproduce and continue

Run `python -m pytest -q tests/test_electrocatalyst_metrics.py`. Checks cover
iR correction with cathodic sign, exact synthetic Tafel recovery, weighted
window exclusion of a transport region, covariance, interval-edge interpolation,
clock/support rejection, polarity reversal, 2e/4e product charge and site-mol
turnover, immutable outputs and numeric overflow rejection.

For measured-data research, retain the electrode reference/temperature, actual
uncompensated resistance, area measurement, selected fit regime, gas collection
calibration and active-site counting evidence. Fit-window sensitivity and
transport/capacitive-current analysis are separate from a passing least-squares
calculation. A mechanistic conclusion requires evidence beyond the fitted slope.
