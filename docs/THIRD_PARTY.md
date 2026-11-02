# Dependency and data notices

Original h2physics source is Apache-2.0. Dependencies are separately installed and their
code, binaries, mechanisms and data are not bundled in this project distribution.
The observed verification environment is pinned under `requirements/`.

| Dependency | Reviewed license / source | Role |
|---|---|---|
| NumPy | [BSD-3-Clause](https://github.com/numpy/numpy/blob/main/LICENSE.txt) | Arrays |
| SciPy | [BSD-3-Clause](https://github.com/scipy/scipy/blob/main/LICENSE.txt) | Integrators and sparse numerics |
| CoolProp | [MIT](https://github.com/CoolProp/CoolProp/blob/master/LICENSE) | Reference and tabular fluid properties |
| Cantera | [BSD-3-Clause](https://github.com/Cantera/cantera/blob/main/License.txt) | Chemistry and 1D reacting-flow solvers |
| openpyxl | [MIT](https://openpyxl.readthedocs.io/en/stable/) | Read-only workbook ingestion |
| h5py | [BSD-3-Clause](https://github.com/h5py/h5py/blob/master/LICENSE) | MAT/HDF5 schema inspection |
| LH2DT public snapshot | [MIT](https://github.com/lyullee/lh2dt_models/blob/main/LICENSE) | Optional isolated native integration check |
| PSA-Dyna public snapshot | [MIT](https://github.com/lyullee/psa-dyna/blob/main/LICENSE) | Optional native equilibrium and loading-LDF bed checks |
| impedance.py 1.7.1 | [MIT](https://github.com/ECSHackWeek/impedance.py/blob/v1.7.1/LICENSE) | Optional native small-signal equivalent-circuit prediction; source not bundled |
| pandas | [BSD-3-Clause](https://github.com/pandas-dev/pandas/blob/main/LICENSE) | Required by the selected native impedance import with modern Altair |
| Matplotlib / Altair | [Matplotlib license](https://matplotlib.org/stable/project/license.html) / [BSD-3-Clause](https://github.com/vega/altair/blob/main/LICENSE) | Native dependency imports and original derived research plots |
| DynamicLH2PoolX 0.2.0rc2 | [MIT at checked revision](https://github.com/lyullee/DynamicLH2PoolX/blob/6a700e8e183039bbb81803bacc416f6c9117ed71/LICENSE) | Optional native spreading/evaporation and actual source ledgers; no solver or experimental derivatives bundled |
| DEGALI 0.3.0 source snapshot | [MIT at checked revision](https://github.com/lyullee/degali/blob/6ead182dc19039725a0b40811b48c6d39f947790/LICENSE) | Optional actual gas expansion and calm-jet objects; source, reference code and experimental derivatives not bundled |
| PyAMG 5.3.0 | [MIT](https://github.com/pyamg/pyamg/blob/v5.3.0/LICENSE.txt) | Required by the checked native package's broad import; no host elliptic solver or copied code |
| pifira0.3.0 | [MIT](https://github.com/lyullee/pifira/blob/0d4924518fccd1cf93c677eaf10aa3d56319d8cb/LICENSE) | Optional native pressure-rise contents heat and conditional effective area; published wheel/license/source hashes in research/pifira_dependency.toml; no native code/data bundled |
| HyRAM+6.1 | [GPL-3.0-only native project](https://github.com/sandialabs/hyram) | Separately installed gas dispersion, rejected full-Flame diagnostics and public conditional blast correlation; native license/source hashes retained, no source/tables bundled |

The Cantera verification case loads the separately installed `h2o2.yaml`/`ohmech` example,
which declares GRI-Mech-derived reaction/thermochemistry provenance. Its source hash is
recorded in `research/native_cantera.md`. This is an adapter verification mechanism, not a
blanket scientific or rights qualification of another mechanism selected by a user.
No mechanism file is redistributed by h2physics.

Dataset authors, source URLs, version/update dates, CC0/CC BY 4.0/Etalab terms and file
hashes are retained in `research/data/`. Those terms apply to the data rather than changing
the original code license. Compilations and publications can contain independently held
third-party rights; uncertain records stay out of redistribution. Attribution is not removed.

When embedding any dependency or external dataset into a future distributable, review its
actual selected version and all required notices rather than relying only on this summary.
