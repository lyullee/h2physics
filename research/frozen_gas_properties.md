# Frozen gas property and shared-nozzle verification

Local execution: Cantera 3.2.0; original script scripts/check_cantera_properties.py. All states and nozzle cases below are synthetic software verification. They are not independent mixture-EOS or vent experiments.

## Independent constant-cp checks

The native species are constructed from arbitrary coefficients authored in this script. They are synthetic numerical fixtures, not a measured H2/N2 caloric model. The independent oracle uses ideal-mixture algebra with specified molar masses 2.016 and 28.014 kg/kmol, R = 8314.46261815324 J/(kmol K), mixing entropy and separate formation/reference offsets. Selected native fits intersect the declared domain at 220–2800 K and 0.01–2 MPa.

| Y(H2) | Back pressure Pa | Regime | Solved exit Pa | Pressure relative error | Mass-flow relative error | Energy residual W |
|---:|---:|---|---:|---:|---:|---:|
| 0.02 | 100000 | choked | 433391.8584 | 3.2640557e-14 | 7.1054274e-15 | 0 |
| 0.02 | 433391.8584 | back_pressure_limited | 433391.8584 | 6.6613381e-16 | 8.8817842e-16 | 0 |
| 0.02 | 700000 | back_pressure_limited | 700000 | 2.220446e-16 | 3.255618e-12 | 0 |
| 0.14 | 100000 | choked | 429800.0803 | 5.1625371e-14 | 1.110223e-15 | 1.8189894e-12 |
| 0.14 | 429800.0803 | back_pressure_limited | 429800.0803 | 2.220446e-16 | 1.3322676e-15 | 0 |
| 0.14 | 700000 | back_pressure_limited | 700000 | 4.4408921e-16 | 4.2505999e-12 | 1.8189894e-12 |
| 0.75 | 100000 | choked | 427398.891 | 2.6978419e-14 | 2.6645353e-14 | 0 |
| 0.75 | 427398.891 | back_pressure_limited | 427398.891 | 0 | 2.7755576e-14 | 0 |
| 0.75 | 700000 | back_pressure_limited | 700000 | 2.220446e-16 | 5.0717208e-12 | 0 |

Property grid: 72 PT states; 72 PH and 72 PS roundtrips after contaminating native state and unit basis. Exact boundary targets reuse the already evaluated native TPY endpoint; interior targets use native HP/SP inversion.

| Diagnostic | Maximum |
|---|---:|
| property_relative_error | 5.882334475e-15 |
| ph_temperature_relative_error | 2.220446049e-16 |
| ps_temperature_relative_error | 4.013456234e-13 |
| eos_energy_identity_j_kg | 1.862645149e-09 |

## Installed mechanism execution

Python reads each separately installed file and passes its unmodified UTF-8 text to the native Solution constructor, avoiding the observed C++ non-ASCII Windows path failure. No mechanism is copied into this repository. File hashes identify these exact installed inputs; they do not qualify another mechanism.

| Mechanism / phase | Source SHA-256 |
|---|---|
| h2o2.yaml / ohmech | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 |
| gri30.yaml / gri30 | 06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345 |

| Mechanism | P0 Pa | T0 K | Back pressure Pa | Regime | Exit Pa | Flow kg/s | Max PH/PS T relative error | Energy residual W |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| h2o2.yaml | 600000 | 850 | 100000 | choked | 319770.5553 | 0.006957057946 | 8.8817842e-16 | -9.094947e-13 |
| h2o2.yaml | 600000 | 850 | 550000 | back_pressure_limited | 550000 | 0.003986956525 | 8.8817842e-16 | 0 |
| gri30.yaml | 600000 | 850 | 100000 | choked | 319770.5553 | 0.006957057946 | 8.8817842e-16 | -9.094947e-13 |
| gri30.yaml | 600000 | 850 | 550000 | back_pressure_limited | 550000 | 0.003986956525 | 8.8817842e-16 | 0 |

## Evolving native enclosure and shared-nozzle callback

An actual CanteraOpenGasVolume run starts at absolute time 12.5 s, 500 K, 0.3 MPa and 0.5 m3 with mole fractions H2=0.1 and N2=0.9. A constant 0.001 kg/s pure-H2 feed enters at 500 K; the single common nozzle vents to 0.1 MPa through 8e-6 m2 effective area. Six output times end at 12.55 s. Native callbacks have declared support through 13 s. The property phase is separate from the active reactor phase.

This run explicitly budgets a 1e-7 mass-fraction sum correction for native CVODES trial states under policy native-CVODES-Jacobian-largest-species-trial-extension. This is a deliberate extension of the callback away from the physical composition simplex, not floating-point roundoff. Native finite-difference Jacobian probes can leave that simplex by about 1.5e-8; accepted-state ulp deviations are recorded separately below. Only the largest nonnegative species absorbs the sum residual; all raw values, selected species, changes and the budget are inspectable. Negative species, materially invalid sums and corrections above budget remain errors. The default property constructor permits no correction.

| Diagnostic | Observed |
|---|---:|
| Nozzle callback evaluations | 37 |
| Recorded composition sum corrections | 32 |
| Maximum absolute species correction | 1.478295675e-08 |
| Signed correction at maximum magnitude (exact float.hex) | -0x1.fbf0434000000p-27 |
| Maximum sampled accepted-state absolute sum deviation | 2.220446049e-16 |
| Signed accepted-state sum deviation at maximum magnitude (exact float.hex) | 0x1.0000000000000p-52 |
| Initial accepted Y(H2) | 0.007932573128 |
| Final accepted Y(H2) | 0.007986669869 |
| Integrated vent mass kg | 0.0001988699976 |
| Maximum mass residual kg | 1.256996894e-16 |
| Maximum species residual kg | 3.276224778e-13 |
| Maximum energy residual J | 1.264024e-06 |

The residuals compare native inventory changes with native appended boundary integrals. Independent constant-cp/nozzle checks appear above; this coupled run is integration/conservation evidence, not an enclosure experiment. The opt-in trial extension does not establish physical validity for off-simplex states.

## Scope and rights

The API retains actual caller-created native phases and supplies the existing HomogeneousIsentropicNozzle through PropertyProvider. TPY, HP and SP remain native; no EOS, choking solver, chemistry integrator or transport model is duplicated. The formation enthalpy, entropy and composition fingerprints remain in PropertyBasis. Native mechanism H2 is explicitly spin-unresolved, and normal/para/ortho-H2 thermodynamic claims are rejected.

The intersection of declared mechanism limits and selected species fit limits is enforced. The ideal-gas pressure envelope is a caller declaration, not real-gas validation. Viscosity/conductivity, equilibrium composition, cryogenic condensation, dissociation evolution, spin conversion, atmospheric source ownership and vent discharge-coefficient qualification are outside these checks.

The source hash is the caller's provenance assertion. A separate fingerprint records the actual native species thermochemistry and detects later definition edits, but cannot authenticate a claimed upstream source. Successful queries reset the native mass unit basis and all species; callers must synchronize direct concurrent access to the retained object.

Cantera is a separately installed BSD-3-Clause dependency: [license](https://github.com/Cantera/cantera/blob/v3.2.0/License.txt). The installed example inputs declare GRI-Mech-derived provenance. That distribution fact does not grant blanket redistribution rights for another mechanism. Neither mechanism files nor third-party examples/data are bundled.

Primary references: [native property API](https://cantera.org/3.2/python/thermo.html), [species caloric fits](https://cantera.org/3.2/reference/thermo/species-thermo.html), [ideal gas](https://cantera.org/3.2/reference/thermo/phase-thermo.html#ideal-gas), [NASA mass-flow relation](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html).

Elapsed local script time: 1.32364 s.
