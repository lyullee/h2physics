# Native tank / shared nozzle verification

Run `python scripts/check_release_integration.py` after installing the pinned optional native engine.
Native package: lh2dt_models 0.1.2; revision `b2f276333c1b1793c39f25763703d196d36742ec`.
Native Python-source SHA-256: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
CoolProp 8.0.0 HEOS ParaHydrogen; the exact reference identity is retained in native mapping.

Both cases use a rigid 0.1 m³ reservoir, wall capacity 20000 J/K, ambient UA 0.05 W/K, fluid/wall UA 0.2 W/K and ambient/initial wall at initial fluid temperature. The gas starts at 5 MPa, 300 K (1 mm opening, 5 s); the cryogenic case starts at 0.5 MPa with half the vessel volume liquid (2 mm opening, 2 s). Back pressure is 101325 Pa and the declared effective-area factor is 0.8.

| Case | Step s | Released kg | Final P Pa | Node trapezoid error kg | Tank mass residual kg | Tank energy residual J | Nozzle energy residual W |
|---|---:|---:|---:|---:|---:|---:|---:|
| warm_gas | 0.5 | 0.0094205885564 | 4829005.96624 | 8.60638403252e-09 | -1.31838984174e-16 | 1.57069734996e-09 | 1.81898940355e-12 |
| warm_gas | 0.25 | 0.00942058855641 | 4829005.96624 | 2.15159374692e-09 | 6.76542155631e-17 | 1.53158907779e-09 | 1.81898940355e-12 |
| warm_gas | 0.125 | 0.00942058855642 | 4829005.96624 | 5.37898402903e-10 | -8.84708972748e-17 | 2.19733919948e-09 | 1.81898940355e-12 |
| equilibrium_cryo_bulk | 0.5 | 0.0115929509941 | 498662.661129 | 2.39643190708e-10 | 1.90819582357e-17 | 6.86668499839e-11 | 1.13686837722e-13 |
| equilibrium_cryo_bulk | 0.25 | 0.0115929509941 | 498662.661129 | 5.99104862942e-11 | 7.2858385991e-17 | 9.47011358221e-11 | 0 |
| equilibrium_cryo_bulk | 0.125 | 0.0115929509941 | 498662.661129 | 1.49778731084e-11 | -1.82145964978e-16 | 2.55340637523e-10 | 1.13686837722e-13 |

The native RK4 boundary ledger closes; accepted-node trapezoid quadrature is a separate, lower-order check and its errors decrease approximately fourfold on halving the step. This does not establish independent physical validation.

| Case | Initial flow kg/s | Final flow kg/s | Initial nozzle P Pa | Final nozzle P Pa | Initial nozzle quality | Final nozzle quality |
|---|---:|---:|---:|---:|---:|---:|
| warm_gas | 0.00191254554372 | 0.00185603412091 | 2644923.8779 | 2555899.14993 | None | None |
| equilibrium_cryo_bulk | 0.00580452662871 | 0.00578842819967 | 316757.260683 | 315842.47124 | 0.15034453500851827 | 0.15061744535583693 |

Nozzle static enthalpy plus kinetic energy equals upstream stagnation enthalpy. Nozzle quality is not a ground-transfer fraction. Native LH2DT only supports bulk withdrawal in this check; phase-selective extraction remains request 001.

Isolation is verified by separate integration windows; the subsequent window has zero boundary mass throughout. RK stage/retry calls are never logged as accepted source times. The demonstration does not interpolate a jump or supply an atmospheric jet.

Source hashes (SHA-256):

- `src/h2physics/release.py`: `eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45`
- `src/h2physics/adapters/lh2dt.py`: `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed`
- `scripts/check_release_integration.py`: `3d22f38a612f7bb04c13c911bb9f6b1138b87eab1eae78e2a452768007b04ba4`
