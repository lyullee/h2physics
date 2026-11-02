# Native closed adsorption-bed verification

Parameter representation SHA-256: `d57921d9694a56b8f680ddd31cdd3ea1d869b55f7aa5e0ce087d77cfa0935d9c`. The full authored fixture is in the verification script.

Four equal finite-volume cells, H2/N2 loading LDF, dynamic wall, no ambient heat or face transfers. The initial native 1-bar equilibrium state receives a doubled gas inventory before t=0; it then relaxes in a closed system. Uniform conditions make this a kinetic/thermal and interface check, not a transport/grid study or PSA cycle.

- Maximum component-inventory residual: 8.32667268e-17 mol.
- Maximum total-energy residual: 4.41286829e-08 J.
- Final pressure: 170898.347 Pa.
- Final bed temperature: 300.108058 K.
- Explicit energy reference: `authored:gas-constant-Cv-from-0K;solid-wall-298.15K;native-binding-energy`.

The adapter retains the actual native Bed/rates implementation and exposes immutable SI snapshots. Face-transfer species and energy references must match. The current native fields function rejects bed temperatures ≤100 K or ≥1000 K; this warm verification does not authorize 20 K cryo-adsorption. See the separate extension request.
