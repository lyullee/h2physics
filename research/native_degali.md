# Native gas-plane and calm-jet integration

Authored numerical cases; no independent experimental validation or facility qualification.

Native MIT [DEGALI snapshot](https://github.com/lyullee/degali/tree/6ead182dc19039725a0b40811b48c6d39f947790), package version 0.3.0, Python-module path/byte SHA-256 `f84bb2c38e26a507a3e495005f38d8fed097d312f6a47932fe10d3cdb587220a`. The PyPI 0.1.0 release is not assumed equivalent to this source snapshot.

## Model and gates

The one shared isentropic nozzle supplies the native ambient-plane expander. Its effective stream area is explicitly also the pressure-force area. The caller places a horizontal virtual plane 2 m above declared ground; its axial offset is not predicted. The upstream pressure is 2 MPa absolute, ambient pressure 101325 Pa, nominal opening 2 mm and effective area factor 0.8. Normal H2 starts at 300 K; para-H2 at 100 K. Ambient phase air is dry at 293.15 K and includes argon.

The native temperature/mass-fraction profile, equilibrium air condensation, temperature-dependent component enthalpy, four-flux establishment and consistent phase ambient are explicit. Entrainment coefficients remain 1.16 / 0.28 / 0.082 (profile spreading / momentum entrainment / plume cap), radial limit 5 widths. Fuel cp comes from the pure-fluid ambient reference; declared air cp is 1005 J/kg/K. Radiation, coflow and the experimental nonideal-mixture-volume correction are off.

An original thin native subclass replaces only the vertical flux source by the actual native radial buoyancy integral. The current upstream analytic density-profile force is inconsistent with its independent temperature/composition profile. All profiles, Jacobian, remaining sources and spatial integration remain native. No density-profile root failure triggers a hidden fallback or fitted coefficient.

Default host limits: H2 species 1e-6, horizontal momentum 1e-6, energy 1e-5 and establishment 1e-7, all relative. Energy is scaled by mdot*(abs(h_source_model)+v_source^2/2), separately reporting absolute W and net energy. Native reference interpolation is checked against the public pure-H2 ideal enthalpy query within 1 J/kg. Refinement targets: endpoint Y relative 0.0005, endpoint T 0.1 K, and sampled vertical-force integral relative 0.005. These thresholds were declared before the authoritative runs.

A separate preliminary DOP853/161-point/2e-8 diagnostic completed normal H2 but its para-H2 run was interrupted after more than 300 observed CPU seconds without a completed solution. That diagnostic is not a passed result. The declared authoritative sequence uses RK45 and records its actual residuals.

The first RK45 sequence failed the para-H2 energy gate at 321 points (0.523570536 W against a 0.237922351 W budget), while species and horizontal momentum passed. An additional 641-point / 0.00125 m / 2e-7 run is therefore included for that unresolved case. The conservation and endpoint targets are unchanged.

## Hydrogen

Mass flow 0.00309566981064 kg/s; ambient-plane T 158.001612362 K, v 1981.70520578 m/s, diameter 0.00357770838537 m. Momentum residual -7.40740802e-12 N; total-specific-energy residual 0 J/kg.

Retained native density-profile initialization: `conservative Gaussian establishment did not close: {'mass': 0.1374440724980697, 'species': -0.2958585983675419, 'momentum': 0.05573965780356307, 'energy': -0.006902874439438918}`.

| Radial points | max step / m | rtol | seconds | species rel | horizontal M rel | energy error / W | energy scale / W | gate |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 81 | 0.01 | 2e-06 | 1.60514 | 5.47946499e-06 | 5.71630039e-06 | 0.119979933 | 11826.7414 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation |
| 161 | 0.005 | 2e-07 | 3.78058 | 2.36897216e-07 | 2.47982235e-07 | 0.0758479273 | 11826.7414 | PASS |
| 321 | 0.0025 | 2e-07 | 7.58392 | 1.11462135e-08 | 1.16105988e-08 | 0.0251697664 | 11826.7414 | PASS |

Finest run points: 193; establishment S 0.0221817919893 m; end S 0.5 m. Initial ambient entrainment 0.0168790104719 kg/s; minimum evaluated-envelope ground clearance 1.70771759 m. Enthalpy-gauge difference -0.0184204513 J/kg.

Source HEOS static h 2003066.19175 J/kg; ambient real H2 reference 3860321.98735 J/kg; ambient ideal H2 reference 3859902.7789 J/kg. Native model source h -1856836.60557 J/kg and net source h+KE flux 330.435373392 W. Finest four-flux establishment residuals `{'mass': 5.210767185564645e-16, 'species': 7.004637049831142e-16, 'momentum': 1.0134552450413509e-15, 'energy': 1.7202582846112363e-15}`.

161 to 321-point/step refinement: endpoint whole-mixture Y relative change 9.0964778e-05, T change 6.64433679e-06 K. Sampled vertical momentum/force-integral relative difference 1.23608121e-07. The original analytic force minus actual integrated force at establishment is -0.000826119404 N/m. Combined numerical gate: PASS.

Predicted native centreline observations (S, r, whole-mixture Y, bulk rho, T): `[[0.1, 0.0, 0.07464982799806556, 0.6028475424564931, 293.04147799305], [0.3, 0.0, 0.02419980925714761, 0.9053445609235657, 294.5496110668661], [0.5, 0.0, 0.014398330976905665, 1.0058956093120703, 294.23127362598115]]`. Fingerprint `43804693ea1e6ffa577fe26353317a901ed66b16d37e4bc820e1b86be2b45956`.

## ParaHydrogen

Mass flow 0.00555184683009 kg/s; ambient-plane T 43.0999787881 K, v 1119.00434308 m/s, diameter 0.00330782942256 m. Momentum residual -6.9926287e-12 N; total-specific-energy residual 0 J/kg.

Retained native density-profile initialization: `conservative Gaussian establishment did not close: {'mass': 0.0011896575538770768, 'species': -0.004708679167055186, 'momentum': 0.00047725433967385673, 'energy': -0.0030088990064018753}`.

| Radial points | max step / m | rtol | seconds | species rel | horizontal M rel | energy error / W | energy scale / W | gate |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 81 | 0.01 | 2e-06 | 4.99715 | 1.03421201e-06 | 1.11817453e-06 | 2.52508032 | 23792.2351 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation |
| 161 | 0.005 | 2e-07 | 14.6139 | 6.47391419e-08 | 6.98686699e-08 | 2.76919676 | 23792.2351 | total enthalpy plus kinetic energy conservation |
| 321 | 0.0025 | 2e-07 | 14.6985 | 2.23279835e-09 | 2.41165416e-09 | 0.523570536 | 23792.2351 | total enthalpy plus kinetic energy conservation |
| 641 | 0.00125 | 2e-07 | 29.9631 | 3.14894196e-09 | 3.39669083e-09 | 0.345730287 | 23792.2351 | total enthalpy plus kinetic energy conservation |

Finest run points: 464; establishment S 0.0205085424199 m; end S 0.5 m. Initial ambient entrainment 0.0157044572813 kg/s; minimum evaluated-envelope ground clearance 1.7116572 m. Enthalpy-gauge difference 0.0341606978 J/kg.

Source HEOS static h 694137.04858 J/kg; ambient real H2 reference 4353925.3508 J/kg; ambient ideal H2 reference 4353514.88454 J/kg. Native model source h -3659377.8018 J/kg and net source h+KE flux -16840.3750282 W. Finest four-flux establishment residuals `{'mass': 3.2643934089135125e-16, 'species': 3.124588139879871e-16, 'momentum': 5.718616330727028e-16, 'energy': -4.320543694522394e-16}`.

321 to 641-point/step refinement: endpoint whole-mixture Y relative change 2.26214098e-05, T change 0.00148851088 K. Sampled vertical momentum/force-integral relative difference 4.37394428e-07. The original analytic force minus actual integrated force at establishment is -0.00129428741 N/m. Combined numerical gate: FAIL.

Predicted native centreline observations (S, r, whole-mixture Y, bulk rho, T): `[[0.1, 0.0, 0.11871457558765632, 1.0640389043340712, 128.22482879367888], [0.3, 0.0, 0.04147213345630635, 1.1143201911278215, 203.76622573501675], [0.5, 0.0, 0.025075353084614924, 1.138790299433798, 232.11610726279983]]`. Fingerprint `9482d09f91afd82aa43f90bccbc6d9469bbcf8b13057478f5dd75f2318040cad`.

## Scope and remaining work

Mass entrainment is ambient material, not loss of hydrogen. Complete-mixture Y includes condensate and is not gas-phase mole fraction. Native interpolation is used for section samples and does not claim conservative interpolation. The phase model uses component enthalpy/phase tables and a mixture volume closure, not a complete real multicomponent EOS. Native low-temperature tables and their continuations remain model limitations. No explicit gravitational-potential-energy term, spin conversion, crosswind, obstacle, ground impact or finite-release material clock is added. Passing this short steady calm case cannot qualify a transient pool plume, a measurement operator, hazard distance or facility design.

Request 011 records native force consistency, public section-flux/source contracts, reference bookkeeping, state injection and phase-aware observations. These checks do not transfer upstream experimental validation to the authored coupled case.

Host SHA-256:

- `src/h2physics/adapters/degali.py`: `622cf7f5c9309f109c6e8eb06b342ef36fc86d5a863578136cebc62f1d05464d`
- `scripts/check_degali_integration.py`: `249cfd2b59ca763a8c651ed66734259d8f865bd5c6ac22ba298ef519f3fa3eb3`
