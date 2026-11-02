# Native PSA adsorption verification

Engine: PSA-Dyna 0.1.0, public MIT revision `a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6`.
Native core source SHA-256: `104686045b7ae61ead32a0978f5fd58d801f3a599225c4070ffe1eb4e0023571`.
Authored parameter representation SHA-256: `3feb1968d4175be89f41e8193307d2acfaaa5252aa54aa0e229e3eb88db64ba7`.

The fixture uses two species and two sites with coefficients authored for this unit/interface check. It is not a measured adsorbent parameter set. The adapter calls the installed native function without copying an isotherm implementation. Declared domain: 290–350 K, total partial pressure 0–1 MPa.

- Nine native/adapter states: maximum loading difference 0 mol/kg.
- Centered one-Pa pressure derivative: largest relative discrepancy 8.75774092e-10.
- Centered 0.001-K temperature derivative: largest relative discrepancy 6.77646283e-11.
- Loading-only working capacity H2/N2: (0.4360232549254169, 0.14829070427155253) mol/kg.

The pressure Jacobian is converted from per bar to per Pa, including off-diagonal competition terms. Species/site derivative axes are preserved. Negative pressure, wrong species order and out-of-domain T/P are rejected before native evaluation. No fugacity, pore/free-gas correction or uptake-basis transformation is inferred.

This verifies the equilibrium adapter. A nonisothermal bed, cyclic steady state, process purity/recovery and experimental adsorption validation are not established here.
