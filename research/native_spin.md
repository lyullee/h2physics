# Native ortho/para conversion and enthalpy coupling

Synthetic mathematical/native software checks; no catalyst, measured conversion rate, caloric mixture model or liquid-spin EOS is qualified.

LH2DT 0.1.2, pinned revision b2f276333c1b1793c39f25763703d196d36742ec; SciPy 1.18.1.

| Native source | SHA-256 |
|---|---|
| Ordered top-level native filename+bytes | 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 |
| ortho_para.py | 479ce6744f8ffd55776759239894e8146b017045c79368e69cc17129dd5cd251 |
| tank.py | b921a604a9ee27b87db41737964bfe9ea111bc66a1a0ee7a237c646fba385c22 |
| Installed MIT license | cd63f148087d189cedb2a388fed0bc3f1f0676df5f7ad1adfc8a8789f9570a72 |

Executed host source/test/script bytes:

| File | SHA-256 |
|---|---|
| src/h2physics/adapters/lh2dt_spin.py | 656143c5aef02ebff24a17e9d9b6436b30ee9538baaf703d6bd00e6b7151f2a9 |
| tests/test_lh2dt_spin.py | 6c0fd2dddb6b2c2cbc01b56f5d201809890aebac368831ba45e20c8ccb04522f |
| scripts/check_spin_integration.py | 6474e58251045853d6416c27a6d6cc31bcda449bdc2c503b49e414fca45b2f21 |

## Native rotor sums and independent limits

The actual native module uses even-J spin weight 1 and odd-J weight 3. The independent low-T two-level oracle is x_para=1/[1+9*exp(-2*theta/T)]; the 9 combines J=1 rotational degeneracy 3 with nuclear-spin weight 3. The high-T statistical limit is 1/4. The 10000 K row is a mathematical rotor limit only, outside the adapter's declared 1–1000 K domain and without a molecular-gas/dissociation applicability claim.

| Limit | Native para fraction | Independent absolute error |
|---|---:|---:|
| 10 K, low-T two-level limit | 0.99999965605214 | 0 |
| 10000 K, mathematical high-T / Jmax96 | 0.25 | 2.7755576e-17 |

| T K | Native Jmax24 | Native Jmax96 | Absolute difference |
|---:|---:|---:|---:|
| 10 | 0.99999965605214 | 0.99999965605214 | 0 |
| 20 | 0.99824367775378 | 0.99824367775378 | 0 |
| 50 | 0.7718791491738 | 0.7718791491738 | 0 |
| 100 | 0.38690191752301 | 0.38690191752301 | 0 |
| 300 | 0.25065752949324 | 0.25065752949324 | 0 |
| 1000 | 0.25000000000201 | 0.25000000000201 | 0 |

Retained cutoff rejection: Jmax1 at300 K gives 0.16411944447642, larger-cutoff target 0.25065752949324; difference=0.0865380850168 exceeds the fixed1e-10 gate.

## Exact native thermostat kinetics and heat

Synthetic k=1e-5 s^-1 and conversion enthalpy q=600000 J/kg per unit para fraction increase; mass0.01 kg, held pressure1000 Pa. These inputs are authored verification parameters, not catalyst or calorimetric data. x is the native mass-independent population fraction; equal isomer molar masses make it numerically the model's mass fraction.

A constant-pressure, constant-temperature thermostat keeps sensible H fixed. H_spin=M*[h_ref+q*(x_ref-x)]. Positive native conversion heat is an internal transfer. The required external thermostat heat is its negative, counted once. No frozen pure-fluid EOS zero participates in this ledger.

| T K | Initial para | Final para | Final native heat W | External heat integral J | Max analytic fraction error | Max H-ledger residual J |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.25 | 0.99820970754336 | 2.03821262492e-06 | -4489.25824526 | 0 | 7.5495166e-13 |
| 300 | 1 | 0.25069154958877 | -2.04120573174e-06 | 4495.85070247 | 0 | 4.5474735e-13 |

The reverse 300 K para-to-ortho case has negative conversion heat and requires positive thermostat heat. k=0 gives frozen native composition/rate and zero heat over1e7 s without inferring a different catalyst. Exact native constant-T advances also pass sample refinement and continuation checks in tests.

## Finite constant-pressure enthalpy calorimeter

Mass0.01 kg, held pressure1000 Pa, effective frozen-composition sensible Cp=1000 J/K, initial T20 K and para fraction0.25. This is a finite lumped calorimeter, not a rigid vessel, liquid-mixture EOS or pressure/volume solver. Constant q is a caller-evidenced reduced enthalpy gap; Cp excludes conversion enthalpy. The adiabatic algebraic constraint is H_sensible+H_spin=constant. Native kinetics supplies dx/dt at the resulting T; SciPy integrates that coupling, without copying a native rotor/rate solver.

| Maximum step s | rtol | Final para | Final T K | Max H residual J | RHS calls |
|---:|---:|---:|---:|---:|---:|
| 20000 | 1e-08 | 0.99174240905379 | 24.450454454323 | 2.7284841e-12 | 1565 |
| 10000 | 1e-10 | 0.99174240905379 | 24.450454454323 | 2.7284841e-12 | 2765 |
| 5000 | 1e-12 | 0.99174240905379 | 24.450454454323 | 2.7284841e-12 | 5165 |

Independent final equilibrium root=0.99174241021498; finite-time difference=1.16118303861e-09. Finest-two final T difference=0 K. Zero-conversion-gap reference analytic error=5.88418203051e-15. Reverse adiabatic conversion cools to 295.534729971 K. Shifting spin h_ref by2.3e7 J/kg and sensible H by-8e5 J changes T by 0 K; compositions also remain identical.

## Retained rejection evidence

| Attempt | Rejection |
|---|---|
| Boolean native rotational cutoff | The native rotational cutoff must be an integer, not a boolean |
| Negative native rate constructor | conversion_rate_constant_s must be finite and non-negative |
| Out-of-domain temperature | Temperature is outside the declared native spin domain |
| Out-of-range fraction | Para fraction must lie in [0, 1] |
| Negative native advance duration | Native spin step duration cannot be negative |
| Finite coupling exceeds declared T scope | Temperature is outside the declared native spin domain |

Read-only inspection of the pinned homogeneous/stratified/layered tank and dynamic-network files finds no use of the native spin state/rate/heat symbols. The ortho_para module exports standalone functions; native tank spin coupling is not implemented at this revision. The new calorimeter is explicitly an enthalpy coupling, not a claimed native tank capability.

## References, rights and limits

Primary statistical/energy context: [Popovas and Jorgensen, molecular-H2 partition functions](https://doi.org/10.1051/0004-6361/201527209), [Leachman et al., separate para/normal/ortho EOS](https://srd.nist.gov/jpcrdreprint/1.3160306.pdf), [pinned native API](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/ortho_para.py). The native source is separately installed under [MIT](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE); no third-party tables, coefficients, examples or implementation are copied.

The native rigid rotor omits centrifugal distortion, vibrational/electronic excitation, dissociation and phase-dependent conversion thermochemistry. The first-order rate and constant enthalpy gap are explicit supplied closures. Sensible Cp must be frozen-composition storage and must not include conversion heat a second time. Held pressure defines a constant-pressure H/heat path; no rigid-volume U, density, volume, phase split or boundary-work prediction is returned. A delta-U coupling would need an explicit spin-dependent delta-PV assumption/provider. A no-mole-change ideal-gas delta-PV=0 limit cannot be promoted to a general liquid result.

Actual native module/functions, parameters and composition states plus the actual SciPy coupled result remain available. Native exact-step endpoint roundoff clipping is retained; the host does not clip invalid fractions, infer a catalyst, relabel frozen CoolProp pure-fluid states, subtract arbitrary pure-fluid enthalpy zeros or silently select an evolving-spin EOS.

Elapsed local replay time: 10.998094 s.

Native and host/test/script begin/end byte guards passed.
