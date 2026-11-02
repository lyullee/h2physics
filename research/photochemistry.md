# Photon accounting and finite photochemical conversion

Actual local replay: SciPy1.18.1, Cantera3.2.0; 0.5888965s.

All spectra, optical coefficients and electron-equivalent yields are authored verification inputs. No catalyst coefficient, source experiment or universal charge-recombination law is fitted. The existing stoichiometric/caloric core owns finite conversion and native Cantera owns species enthalpies. Native files are separately installed and unchanged.

Public H2 rate uses two productive electron equivalents per H2. Yield explicitly refers to incident or absorbed photons and is bound to actual optical-input identity plus catalyst/medium/mass/T/P/geometry. The one-electron-per-absorbed-photon scope is checked per constant-response band. Incident yield is not multiplied by absorption again. A reported AQY whose denominator/electron convention is unresolved cannot be silently attached to this model.

The independent smooth source on350–700nm is E(lambda_nm)=1.5exp(-((lambda_nm-500)/100)^2)W/(m2 nm), area0.002m2; prescribed absorbed electron yield=0.3+0.1(lambda_nm-350)/350. Optical path1mm, alpha1200/m and reflectance0.08 are constant. Each numerical band holds irradiance/response fixed at its midpoint. Independent adaptive quadrature integrates the continuous formula, with no band assumption in its oracle.

Independent continuous H2 reference=2.43701999909e-07mol/s; quadrature estimate=2.70563571451e-21mol/s.

| Bands | Incident W | Incident mol photons/s | H2 mol/s | Absolute H2 error mol/s |
|---:|---:|---:|---:|---:|
| 12 | 0.521890564105 | 2.19203444027e-06 | 2.43861849377e-07 | 1.59849467743e-10 |
| 24 | 0.521584191804 | 2.19091742133e-06 | 2.43742440012e-07 | 4.04401027382e-11 |
| 48 | 0.521506801694 | 2.1906342632e-06 | 2.43712139446e-07 | 1.01395369389e-11 |
| 96 | 0.521487405164 | 2.19056323289e-06 | 2.43704536633e-07 | 2.5367232063e-12 |

Across declared limits: maximum optical power defect=0W, photon partition defect=0mol/s. Three original line wavelengths380/530/680nm with0.2/0.7/0.1W test discrete photon energy and equivalent incident/absorbed yield.

## Finite reaction and caloric requirement

An authored ideal-gas H2O→H2/O2 conversion uses0.1mol initial steam,300K/100000Pa(abs), and the explicit steady[100,1100]s exposure. This is a balance/formation-enthalpy verification case, not a liquid water reactor or evidence of achievable water splitting.

Produced H2=0.000243704536633mol; reaction extent=0.000121852268316mol; mass defect=-6.77626357803e-20kg. Incident/absorbed optical energy=521.487405164/335.264943772J. Actual native formation-enthalpy change=58.9382402422J; required signed isothermal thermal boundary=-276.32670353J. Independent native mixture-enthalpy defect=0J and first-law requirement defect=0J.

Required isothermal heat is a derived boundary requirement, not an available utility or a predicted temperature. First-law bookkeeping alone does not establish Gibbs/exergy feasibility, band alignment, carrier potentials, reaction kinetics, donor/product chemistry or solar-to-H2 efficiency. A finite feed that cannot support the requested fixed-yield exposure is rejected without clipping extent or inventing source termination. Thermochemistry absent means heat remains None.

| Verification gate | Pass |
|---|---|
| actual host source bytes and native mechanism unchanged | True |
| line photon molar amounts match independent exact SI constants | True |
| finite-band smooth-spectrum midpoint convergence ratio above3.8 | True |
| finest H2 rate relative quadrature disagreement below1e-4 | True |
| transparent thin opaque reflecting optical energy defect below1e-14W | True |
| spectral photon partition defect below1e-19mol/s | True |
| incident versus absorbed yield use same physical H2 count | True |
| existing finite stoichiometry conserves H/O mass below1e-15kg | True |
| native species calorimetry matches independent native mixture H below1e-9J | True |
| required signed isothermal heat matches independent first law below1e-9J | True |
| finite depletion rejects without capping light or losing budget | True |
| per-band incident photon excess retains rejected diagnostics | True |
| rejected diagnostic cannot drive finite conversion | True |
| optical wavelength-grid change rejects despite matching vector length | True |

Primary definitions: [IUPAC photocatalysis terminology](https://doi.org/10.1351/PAC-REC-09-09-36), [SI photon/amount constants](https://www.bipm.org/en/publications/si-brochure), [native species thermochemistry](https://cantera.org/3.2/python/thermo.html). Original formulas/tests reproduce no third-party prose, coefficient table or worked example.

## Executed identities

Native separately installed gri30.yaml SHA-256=06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345.

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/photochemistry.py` | `1ce482577b7e77ad29dff1f5fa472866df5034dbb7e244911b5d11a6ff535fb5` | `1ce482577b7e77ad29dff1f5fa472866df5034dbb7e244911b5d11a6ff535fb5` |
| `tests/test_photochemistry.py` | `6e6a356871a8ee270b4ae94e1f57835de0e0929ed0596d354a3cccced79799fa` | `6e6a356871a8ee270b4ae94e1f57835de0e0929ed0596d354a3cccced79799fa` |
| `scripts/check_photochemistry.py` | `ca48a181b5043265e060890810e51f03f61c64a43f86cf03dc69971661ee8c97` | `ca48a181b5043265e060890810e51f03f61c64a43f86cf03dc69971661ee8c97` |
| `src/h2physics/reactions.py` | `3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35` | `3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35` |
| `src/h2physics/adapters/cantera_thermo.py` | `f5bf30b7536c432fd84f9b7c4b81a72949dc936a9662a7c89f15ea8a62e8d027` | `f5bf30b7536c432fd84f9b7c4b81a72949dc936a9662a7c89f15ea8a62e8d027` |
| `src/h2physics/adapters/cantera.py` | `19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184` | `19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184` |
| `docs/PHOTOCHEMISTRY.md` | `f0ae789d50ff07c0dbced448ffc725051c0e3a17ff748cc4f6d8f756ee4e7b8b` | `f0ae789d50ff07c0dbced448ffc725051c0e3a17ff748cc4f6d8f756ee4e7b8b` |
