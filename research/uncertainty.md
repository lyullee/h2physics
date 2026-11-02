# Native uncertainty propagation verification

Actual SciPy1.18.1, NumPy2.5.4, CoolProp8.0.0; 37.8502906s.

Authored independent uniform P10–30MPa, T280–330K and rigid free volume8–12L; normal hydrogen, existing native HEOS/default reference. No measured uncertainty, sensor/material covariance, vessel rating or facility qualification is implied.

| Output | QMC mean | Quadrature mean | QMC population variance | Quadrature variance | 5% | Median | 95% |
|---|---:|---:|---:|---:|---:|---:|---:|
| mass [kg] | 0.140895053878 | 0.140895053006 | 0.00165340235753 | 0.00165340193033 | 0.0789923909401 | 0.139478890754 | 0.209678466774 |
| internal_energy [J] | 382682.961278 | 382682.961454 | 11661091550.9 | 11661072658.5 | 216958.468267 | 380396.987251 | 566711.860883 |

Mean defect=6.18992391e-09relative; variance defect=1.62012819e-06relative; tensor10/14 change=6.53921362e-14relative; independent-seed4096/8192 maximum index change=3.24060247e-05.

| Output | Parameter | First order4096 | Total order4096 | First order8192 | Total order8192 |
|---|---|---:|---:|---:|---:|
| mass | pressure | 0.805380095324 | 0.817353953227 | 0.805405042828 | 0.817359850706 |
| mass | temperature | 0.022231853861 | 0.0237656995551 | 0.0222642598857 | 0.0237660603796 |
| mass | volume | 0.160065267075 | 0.17113522734 | 0.160088504705 | 0.171136725014 |
| internal_energy | pressure | 0.819274586743 | 0.830485651141 | 0.819253771052 | 0.830484802739 |
| internal_energy | temperature | 0.00204390627241 | 0.00238141144314 | 0.00203967999475 | 0.00238147691908 |
| internal_energy | volume | 0.167445856838 | 0.178405572795 | 0.16745224514 | 0.178402162826 |

Indices retain native finite-sample values without clipping. Quantiles are sample quadrature summaries, not confidence limits or annual frequencies. Actual native/model objects, full coordinate/response snapshots and raw ThermoState objects remain available in the Python results. No EOS/table/transport solver is duplicated.

Retained actual single-input/single-output native cause: `'numpy.float64' object does not support item assignment`. All48 model cases survive; no dummy dimension/output or alternate estimator is inserted.

| Numerical gate | Pass |
|---|---|
| host/native executed sources unchanged | True |
| all4096 native QMC coordinates retained without thinning | True |
| actual normal-H2 HEOS/native provider and immutable physical snapshots | True |
| two independent tensor orders agree below1e-10relative | True |
| native QMC means agree with independent quadrature below1e-5relative | True |
| native QMC variances agree below5e-4relative | True |
| native Saltelli cases retained at both4096/8192 base sizes | True |
| independent-seed/base2 index change below2e-3 | True |
| native additive/product first-order limits below1e-3 | True |
| native additive/product total-order limits below1e-3 | True |
| one-input-one-output native failure retains all actual cases | True |
| physical callback failure retains accepted prefix and cause | True |
| invalid returned response retains actual native ThermoState and raw values | True |

| Native input | Begin SHA256 | End SHA256 |
|---|---|---|
| SciPy sensitivity source | `ee3de0f5109fc3b1b3c6046240877c39c3dae755ba0f4b2655494400867d4b25` | `ee3de0f5109fc3b1b3c6046240877c39c3dae755ba0f4b2655494400867d4b25` |
| SciPy QMC source | `34b0f3345b6848880729b578c3da23d85df6b34da3617bc9e391808f1ca532d7` | `34b0f3345b6848880729b578c3da23d85df6b34da3617bc9e391808f1ca532d7` |
| CoolProp compiled library | `eba3061d6e3cf1435573156f61310389ea2e2c8918b893032d9ca5737ed56440` | `eba3061d6e3cf1435573156f61310389ea2e2c8918b893032d9ca5737ed56440` |

| Executed host input | Begin SHA256 | End SHA256 |
|---|---|---|
| `src/h2physics/uncertainty.py` | `6ed5e607d516c8464e652dd378b333e04f66ea82bbd8557f189673910c1154d2` | `6ed5e607d516c8464e652dd378b333e04f66ea82bbd8557f189673910c1154d2` |
| `tests/test_uncertainty.py` | `2ece4004a227037cf6103711bb5fc000556baaeaf24082f1d171c3cc95aee5f4` | `2ece4004a227037cf6103711bb5fc000556baaeaf24082f1d171c3cc95aee5f4` |
| `scripts/check_uncertainty.py` | `afb24357f9b5f6bb3832841cb1724e44b49c6f2ce238d8162799025860b7a783` | `afb24357f9b5f6bb3832841cb1724e44b49c6f2ce238d8162799025860b7a783` |
| `docs/UNCERTAINTY.md` | `e4190ece1201bf0a5ccc67e818a1aee532d2d431f569cf22a823cb7163083573` | `e4190ece1201bf0a5ccc67e818a1aee532d2d431f569cf22a823cb7163083573` |
| `src/h2physics/core.py` | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` |
| `src/h2physics/observations.py` | `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0` | `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0` |
| `src/h2physics/thermo/coolprop.py` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` |

Primary native statistical contracts: [SciPy sensitivity](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.sobol_indices.html), [native QMC](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html). Scientific references and limitations are in docs/UNCERTAINTY.md. No external raw dataset or implementation is bundled.
