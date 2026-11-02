# Conditional HyTunnel gas-jet comparison

This is a conditional external-data comparison, not facility qualification. Source temperature, effective inlet/area interpretation, dry air, free-field geometry and point-sample response remain assumptions. Upstream training/data overlap is not established.

[Source dataset](https://doi.org/10.5281/zenodo.4668554), version 4668554, Joachim Grune and Karsten Sempert, CC BY 4.0. Raw and normalized observations are not redistributed. Exact MIT native [DEGALI revision](https://github.com/lyullee/degali/tree/6ead182dc19039725a0b40811b48c6d39f947790), Python-module fingerprint `f84bb2c38e26a507a3e495005f38d8fed097d312f6a47932fe10d3cdb587220a`.

All four concentration workbooks: 42 worksheets, 5256 spatial sensor rows. Retained issue counts: `{'inconsistent_statistic_order': 36, 'missing_or_outside_volume_fraction_domain': 31, 'labelled_ambient_outside_room_envelope': 26, 'gas_identity_conflict_sheet_He_vs_H2_columns': 1}`. A source-sheet He/H2 conflict stays unresolved; the 1 mm / 1 g/s calm sheet has ambient header/value conflicts and is not repaired automatically. Repeated coordinate headers can move the sampling line and are retained. Zero readings are valid observations; negative readings and inconsistent summary order are masked, not clipped.

Reported source flow, ambient pressure and ambient temperature are averaged across distinct scan rows for each configuration; measured scan-row ranges remain reported. Source H2 stagnation temperature is assumed equal to that mean ambient temperature. The existing nozzle is inverted for an equivalent inlet pressure at measured nominal area and mass flow. This conditions the source and does not validate a flow prediction or infer a measured pressure at an uninstrumented nozzle. The pipe-pressure channel is retained only for comparison; unresolved line losses are not a fitted discharge coefficient.

The ambient virtual plane is explicitly colocated with the physical orifice. Native four-flux temperature/composition establishment and profile-integrated buoyancy are used without fitting entrainment coefficients. Dry phase air includes Ar. The global source-relative measurement plane has z=0; an explicitly unbounded model avoids inventing a ground elevation. Curved centreline projection uses the actual native piecewise-linear trajectory. The public analytic native Gaussian profile is explicitly continued beyond radial flux quadrature; every such tail point is flagged. No axial extrapolation, condensation-to-gas conversion or suction-probe aperture/response correction is hidden in the observer.

For numerical conditioning only, native flux energy is expressed as E+C*m_H2, where C is the ambient-plane source kinetic energy per unit mass. The source target receives the identical H2 reference shift. Native tables, physical profiles and root solver remain unchanged. All host energy gates convert back to the original physical reference and retain their original scale and limits. Unshifted native initialization and a doubled-shift state-invariance comparison are recorded independently.

Authored comparison targets: RMSE <= 0.02 volume fraction, maximum error <= 0.05, median centreline relative error <= 0.25; fine-pair predicted-field RMSE change <= 0.001. Complete observation coverage and native conservation are separate gates. The whole `d4_m5` configuration is reserved in the reporting split. No concentration parameter estimation is performed in either split. Maxima/minima are recorded fluctuations, not confidence intervals or error weights.

## d1_m5: development comparison

Source configuration `1 mm 5g H2 W = 0`; source table fingerprint `9225ce38c84be339c9ccb4419e2ee1b5f1a3d242d4d3132f353d7315fa9c56f3`. Distinct scan rows 17; mean inputs `{'ambient_pressure': 98600.0, 'ambient_temperature': 283.94411764705876, 'source_mass_flow': 0.005023673451250445, 'source_reported_pressure': 11559539.861564403, 'nominal_diameter': 0.001}`; scan ranges `{'ambient_pressure': (98600.0, 98600.0), 'ambient_temperature': (283.15, 284.65), 'source_mass_flow': (0.004995960000000001, 0.005122842105263157), 'source_reported_pressure': (11077799.999999998, 11833810.526315792), 'nominal_diameter': (0.001, 0.001)}`. Equivalent inlet pressure 10183796.6491 Pa (reconstructed); measured pipe pressure mean 11559539.8616 Pa. Source-flow inversion relative error -3.04478665e-12; 28 existing-kernel evaluations. Unshifted native initialization: `closed: {'mass': -8.995377917971628e-16, 'species': -8.632744010983091e-16, 'momentum': -1.2242567514146091e-15, 'energy': -3.849897834345973e-14}`. Explicit C 2043801.39198 J/kg-H2; C versus 2C maximum scaled state difference 9.46515961e-16, invariance gate PASS. Additional initialization failure: `none`.

| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |
|---:|---:|---|---:|---:|---:|---:|---:|
| 81 | 11.5212 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation | 153/153 | 10 | 0.0226180223 | 0.1440964 | 0.216715739 |
| 161 | 21.5603 | PASS | 153/153 | 10 | 0.0225445299 | 0.143500232 | 0.216228561 |
| 321 | 22.8892 | PASS | 153/153 | 10 | 0.0225270218 | 0.143375498 | 0.216111528 |

Finest audit `JetAudit(maximum_relative_species_error=1.2435186423998075e-07, maximum_relative_horizontal_momentum_error=1.3202169478023108e-07, source_total_energy_flux_w=222.2119886456222, maximum_energy_error_w=0.16703489432612173, energy_scale_w=20312.569596346377, reference_enthalpy_error_j_kg=-0.021889209281653166, initial_entrained_air_kg_s=0.025831701240890625, minimum_ground_clearance_m=None, failures=(), native_energy_gauge_shift_j_kg_h2=2043801.391981718)`. Fine-pair predicted-field RMSE change 3.11794551e-05; authored combined gate FAIL. Invalid prediction reasons `{}`. Predicted observation fingerprint `2f0201f29442fb3023041ce4393c7f451183b4440a7d12d789c6cc6ea0b36836`. Independent experimental/facility qualification remains false.

## d1_m1p5: development comparison

Source configuration `1 mm 1.5g H2 W = 0`; source table fingerprint `f9e699d8e18ad8bbc3ca1fcbf683ab2ca6ee0757673da4d829162750fa6bb697`. Distinct scan rows 13; mean inputs `{'ambient_pressure': 99600.0, 'ambient_temperature': 278.15000000000003, 'source_mass_flow': 0.0015171594011251907, 'source_reported_pressure': 3485751.608041081, 'nominal_diameter': 0.0010000000000000005}`; scan ranges `{'ambient_pressure': (99600.0, 99600.0), 'ambient_temperature': (278.15, 278.15), 'source_mass_flow': (0.0014897142857142858, 0.0015725714285714286), 'source_reported_pressure': (3429266.6666666665, 3615028.5714285704), 'nominal_diameter': (0.001, 0.001)}`. Equivalent inlet pressure 3019388.17159 Pa (reconstructed); measured pipe pressure mean 3485751.60804 Pa. Source-flow inversion relative error 8.79851747e-12; 31 existing-kernel evaluations. Unshifted native initialization: `closed: {'mass': -1.8227676335796615e-16, 'species': -2.8585056301097814e-16, 'momentum': -6.040998439178848e-16, 'energy': 5.903908065156315e-15}`. Explicit C 1878237.71576 J/kg-H2; C versus 2C maximum scaled state difference 8.74759053e-16, invariance gate PASS. Additional initialization failure: `none`.

| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |
|---:|---:|---|---:|---:|---:|---:|---:|
| 81 | 3.62837 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation | 117/117 | 10 | 0.00915334023 | 0.0654029608 | 0.0783727072 |
| 161 | 7.01063 | total enthalpy plus kinetic energy conservation | 117/117 | 10 | 0.00912753924 | 0.0650127458 | 0.0779679435 |
| 321 | 15.8058 | PASS | 117/117 | 10 | 0.00911955003 | 0.0649052767 | 0.0778718972 |

Finest audit `JetAudit(maximum_relative_species_error=2.77018189095257e-07, maximum_relative_horizontal_momentum_error=2.823446724087702e-07, source_total_energy_flux_w=17.45093174687935, maximum_energy_error_w=0.029567948262240407, energy_scale_w=5681.721084341412, reference_enthalpy_error_j_kg=-0.023539904970675707, initial_entrained_air_kg_s=0.007999816015909286, minimum_ground_clearance_m=None, failures=(), native_energy_gauge_shift_j_kg_h2=1878237.7157638797)`. Fine-pair predicted-field RMSE change 4.15190299e-05; authored combined gate FAIL. Invalid prediction reasons `{}`. Predicted observation fingerprint `cdba14da9321b89a143e691b36cd0866b2b9be8d2613c01b5c9af565cc1babd4`. Independent experimental/facility qualification remains false.

## d4_m1: development comparison

Source configuration `4 mm 1g H2 W=0`; source table fingerprint `a764c02fdf789cd131ea3082aabeeb44489ed7a95b2fb6601d0f7b70c55deeaf`. Distinct scan rows 13; mean inputs `{'ambient_pressure': 101000.0, 'ambient_temperature': 288.5269230769231, 'source_mass_flow': 0.0010172399447620746, 'source_reported_pressure': 375657.225746153, 'nominal_diameter': 0.004000000000000002}`; scan ranges `{'ambient_pressure': (101000.0, 101000.0), 'ambient_temperature': (288.15, 289.15), 'source_mass_flow': (0.0009926585365853658, 0.0010459459459459459), 'source_reported_pressure': (367239.99999999994, 383146.34146341454), 'nominal_diameter': (0.004, 0.004)}`. Equivalent inlet pressure 140617.846876 Pa (reconstructed); measured pipe pressure mean 375657.225746 Pa. Source-flow inversion relative error -2.36977105e-12; 29 existing-kernel evaluations. Unshifted native initialization: `conservative Gaussian establishment did not close: {'mass': -0.5258319884718846, 'species': 0.1976447913622817, 'momentum': 0.008851037744700361, 'energy': 0.009648007593980682}`. Explicit C 375781.220951 J/kg-H2; C versus 2C maximum scaled state difference 1.04300602e-15, invariance gate PASS. Additional initialization failure: `none`.

| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |
|---:|---:|---|---:|---:|---:|---:|---:|
| 81 | 4.30405 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation | 108/108 | 10 | 0.0137482647 | 0.0928963861 | 0.140549752 |
| 161 | 9.04582 | total enthalpy plus kinetic energy conservation | 108/108 | 10 | 0.0136909855 | 0.0926603886 | 0.139851723 |
| 321 | 20.7811 | total enthalpy plus kinetic energy conservation | 108/108 | 10 | 0.0136843184 | 0.0926480515 | 0.139741848 |

Full C versus 2C trajectory/observer RMSE change 5.20420235e-12; unchanged-reference native audit statuses False/False; full-path gauge-invariance gate PASS. Doubled-gauge physical maximum energy error 0.130957201 W.


Finest audit `JetAudit(maximum_relative_species_error=2.4018601472524584e-07, maximum_relative_horizontal_momentum_error=2.3714605526280286e-07, source_total_energy_flux_w=0.5724357291957535, maximum_energy_error_w=0.1309564010468517, energy_scale_w=763.9469011545339, reference_enthalpy_error_j_kg=-0.02080866089090705, initial_entrained_air_kg_s=0.007200494471698035, minimum_ground_clearance_m=None, failures=('total enthalpy plus kinetic energy conservation',), native_energy_gauge_shift_j_kg_h2=375781.2209509513)`. Fine-pair predicted-field RMSE change 1.39576327e-05; authored combined gate FAIL. Invalid prediction reasons `{}`. Predicted observation fingerprint `efc6f90c46785d4857c66fdf425d5669f709c288454dbfb3050861e7569f171f`. Independent experimental/facility qualification remains false.

## d4_m2p5: development comparison

Source configuration `4 mm 2.5g H2 W = 0`; source table fingerprint `ad4b6ce9ad992bd608ffd3925b916b6867729a010013a87ba24aa48867089518`. Distinct scan rows 15; mean inputs `{'ambient_pressure': 99700.0, 'ambient_temperature': 278.15, 'source_mass_flow': 0.0025002065109678015, 'source_reported_pressure': 702542.5910230122, 'nominal_diameter': 0.004000000000000002}`; scan ranges `{'ambient_pressure': (99700.0, 99700.0), 'ambient_temperature': (278.15, 278.15), 'source_mass_flow': (0.002480285714285714, 0.00251552), 'source_reported_pressure': (692128.5714285715, 711752.6315789474), 'nominal_diameter': (0.004, 0.004)}`. Equivalent inlet pressure 310126.226204 Pa (reconstructed); measured pipe pressure mean 702542.591023 Pa. Source-flow inversion relative error 1.99840144e-15; 30 existing-kernel evaluations. Unshifted native initialization: `conservative Gaussian establishment did not close: {'mass': -0.24292289154847765, 'species': 0.13555974340116297, 'momentum': 0.021503326487530075, 'energy': 0.0046767133290261}`. Explicit C 1093663.59015 J/kg-H2; C versus 2C maximum scaled state difference 2.02917069e-16, invariance gate PASS. Additional initialization failure: `none`.

| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |
|---:|---:|---|---:|---:|---:|---:|---:|
| 81 | 5.03374 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation | 135/135 | 10 | 0.0153695315 | 0.125965794 | 0.070736494 |
| 161 | 17.1051 | total enthalpy plus kinetic energy conservation | 135/135 | 10 | 0.0153459428 | 0.125797531 | 0.070311853 |
| 321 | 32.7825 | PASS | 135/135 | 10 | 0.0153382181 | 0.125629541 | 0.0702227916 |

Finest audit `JetAudit(maximum_relative_species_error=1.368391659827439e-07, maximum_relative_horizontal_momentum_error=1.388401580797447e-07, source_total_energy_flux_w=2.856002522690881, maximum_energy_error_w=0.021444067793447985, energy_scale_w=5465.9136552892605, reference_enthalpy_error_j_kg=-0.023539904970675707, initial_entrained_air_kg_s=0.01573562624229711, minimum_ground_clearance_m=None, failures=(), native_energy_gauge_shift_j_kg_h2=1093663.5901518075)`. Fine-pair predicted-field RMSE change 4.58821805e-05; authored combined gate FAIL. Invalid prediction reasons `{}`. Predicted observation fingerprint `86f5a9dadd4bf682857c2a4258bdec6ef09927a0b296327b077983fd1689ff06`. Independent experimental/facility qualification remains false.

## d4_m5: held out

Source configuration `4 mm 5g H2 W = 0`; source table fingerprint `06a31fa7866634b35213cd3509696a6f2b0c49066ca766c4a19020d615db6f62`. Distinct scan rows 22; mean inputs `{'ambient_pressure': 98981.81818181818, 'ambient_temperature': 279.92727272727274, 'source_mass_flow': 0.004975363826720051, 'source_reported_pressure': 1270486.1129647691, 'nominal_diameter': 0.004000000000000001}`; scan ranges `{'ambient_pressure': (98900.0, 99000.0), 'ambient_temperature': (279.15, 281.15), 'source_mass_flow': (0.004942363636363637, 0.005011782608695653), 'source_reported_pressure': (1252809.0909090908, 1286409.0909090908), 'nominal_diameter': (0.004, 0.004)}`. Equivalent inlet pressure 619382.901879 Pa (reconstructed); measured pipe pressure mean 1270486.11296 Pa. Source-flow inversion relative error -1.59317004e-13; 30 existing-kernel evaluations. Unshifted native initialization: `closed: {'mass': -2.0522775509426562e-16, 'species': -5.229939567400254e-16, 'momentum': -6.164150212196499e-16, 'energy': 1.5154144172094868e-13}`. Explicit C 1509651.9189 J/kg-H2; C versus 2C maximum scaled state difference 8.38590418e-16, invariance gate PASS. Additional initialization failure: `none`.

| Radial points | seconds | native audit | compared/valid measured | radial tail points | RMSE | max absolute error | median axial relative error |
|---:|---:|---|---:|---:|---:|---:|---:|
| 81 | 7.37276 | hydrogen species conservation; horizontal momentum conservation; total enthalpy plus kinetic energy conservation | 180/180 | 20 | 0.0290893359 | 0.180965584 | 0.0997221003 |
| 161 | 12.2212 | PASS | 180/180 | 20 | 0.0290406252 | 0.180855835 | 0.0996400715 |
| 321 | 24.6644 | PASS | 180/180 | 20 | 0.0290192865 | 0.180662725 | 0.100088239 |

Full C versus 2C trajectory/observer RMSE change 3.44046432e-12; unchanged-reference native audit statuses True/True; full-path gauge-invariance gate PASS. Doubled-gauge physical maximum energy error 0.0782165577 W.


Finest audit `JetAudit(maximum_relative_species_error=7.316899812605501e-08, maximum_relative_horizontal_momentum_error=7.560258546215607e-08, source_total_energy_flux_w=11.569536230961143, maximum_energy_error_w=0.07821737253424921, energy_scale_w=15010.565560202514, reference_enthalpy_error_j_kg=-0.023686509113758802, initial_entrained_air_kg_s=0.02883533541676289, minimum_ground_clearance_m=None, failures=(), native_energy_gauge_shift_j_kg_h2=1509651.918896857)`. Fine-pair predicted-field RMSE change 5.53938297e-05; authored combined gate FAIL. Invalid prediction reasons `{}`. Predicted observation fingerprint `40a727e078075933e64d3c64c6124e7655eaa5a71f6d5fcc7c56d94452e3b9c8`. Independent experimental/facility qualification remains false.

## Scope

The source-area/temperature/pressure inversion and virtual-plane placement are conditional assumptions; this is not a resolved supply-line loss or nozzle calibration. The selected native model is steady and calm. Wind/stratification/wall, finite-release material clocks, probe dynamics, ambient humidity and complete independent qualification remain open. The dataset's flow-velocity workbook is not a uniform wind boundary. Do not replace its spatially varying co/counter/cross flow by this calm prediction.

Host SHA-256:

- `src/h2physics/data/hytunnel.py`: `fecf834d96bff7ba5a71479ad7718135441dd73fb62ffcf8ac122ef7c2a3a5e6`
- `src/h2physics/release_inverse.py`: `2607fbc472cebaf7fadce56f8a9948b5f988b22eed3be2ab658b64ffa20470cc`
- `src/h2physics/jet_observations.py`: `69703ae7039288ff4a3f402e650aa139bbd7aa98687e7a49205ffe87d4f04c3d`
- `src/h2physics/adapters/degali.py`: `622cf7f5c9309f109c6e8eb06b342ef36fc86d5a863578136cebc62f1d05464d`
- `scripts/compare_hytunnel_jets.py`: `1d1ac09d978bba1138dd511dd3623eec494bff9d0cc2b4b2fc78f8ea5850812b`
