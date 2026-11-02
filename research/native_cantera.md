# Native chemistry and reacting-flow verification

Cantera 3.2.0; mechanism source SHA-256 `0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4`.
The installed h2o2/ohmech mechanism is an upstream GRI-Mech-derived example. Neither its mechanism file nor the dependency source is bundled here. Its use below verifies the adapter; it is not selection of a qualified hydrogen safety mechanism for every pressure/temperature. The declared test envelope is 300–3500 K and 0.01–2 MPa.

The C++ default data directory loses non-ASCII Windows path characters in this installation. Python reads the installed mechanism and supplies its unchanged text to the native Solution constructor. The public adapter accepts a native phase factory and does not require a serialization format.

## Equilibrium and closed reactors

Authored stoichiometric H2/O2/N2 mixture at 101325 Pa; these are synthetic verification cases. Conservation is checked within each mechanism's energy basis.

| Case | Final T K | Max energy residual J/kg | Max element fraction residual | 200 K rise bracket s |
|---|---:|---:|---:|---|
| equilibrium HP, T0=1000 | 2692.813 | 2.7373899e-05 | 8.0413454e-13 | — |
| equilibrium UV, T0=1000 | 2908.624 | 2.2235326e-08 | 2.553513e-15 | — |
| UV reactor T0=1000, rtol=1e-09 | 2908.624 | 0.1398462 | 6.6613381e-16 | [0.0003, 0.000305] |
| UV reactor T0=1000, rtol=1e-11 | 2908.624 | 0.13956507 | 5.2735594e-16 | [0.0003, 0.000305] |
| equilibrium HP, T0=1001 | 2693.182 | 2.7099741e-05 | 7.8792528e-13 | — |
| equilibrium UV, T0=1001 | 2908.823 | 3.2014214e-08 | 2.6645353e-15 | — |
| UV reactor T0=1001, rtol=1e-09 | 2908.823 | 0.0020917039 | 4.9960036e-16 | [0.00029, 0.000295] |
| UV reactor T0=1001, rtol=1e-11 | 2908.823 | 3.82422e-05 | 3.3306691e-16 | [0.00029, 0.000295] |

The installed mixture's fitted thermochemistry has an approximately -0.13955846 J/kg internal-energy jump across 1000 K after subtracting the smooth sensible change. A run initialized on that breakpoint retains a matching residual even with tighter integration tolerances. Coefficients and energy references are not altered. The 1001 K case separates solver convergence from that fit discontinuity.

## Freely propagating premixed flame

At 310 K and 101325 Pa, with multicomponent transport and Soret diffusion. Refinement below is numerical evidence, not experimental flame-speed validation.

| Width m | Slope / curvature | Points | Speed m/s | Relative mass-flux span |
|---:|---|---:|---:|---:|
| 0.03 | 0.1 / 0.15 | 106 | 2.2128797 | 3.8855994e-05 |
| 0.03 | 0.05 / 0.08 | 174 | 2.2107221 | 1.6857631e-06 |
| 0.05 | 0.05 / 0.08 | 179 | 2.2091102 | 1.6070866e-07 |

Coarse-to-fine speed change: 0.000975019; fine-grid domain-width change: 0.000729107.

No frequency, ignition probability, detonation transition or injury criterion is inferred from these calculations.
