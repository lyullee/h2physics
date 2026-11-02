# Finite phase-resolved supply assembly verification

Native lh2dt_models 0.1.2, MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`.
Top-level native Python-source SHA-256: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
Reproduce with `python scripts/check_finite_supply.py` after the optional isolated installation in HANDOFF.md.

The public Python assembly builder receives actual native models, initial states, factories and separate branch power readers. All inputs here are authored synthetic values; no experimental facility qualification or manufacturer map is claimed. HEOS ParaHydrogen is used throughout.

The finite reservoir reuses the tank/phase/wall initial state and 3000 rpm map in `scripts/check_equipment_network.py`: D=0.3 m, straight length 0.3 m, head depth 0.05 m; half liquid/vapor volumes at common 300000 Pa and 20/28 K; walls 20/28 K; wall capacities 1000 J/K each. Ambient UAs 0.1 W/K each, wall/fluid U=1 W/(m2 K), liquid/vapor interface UAs=100/50 W/K, wall axial UA=0.1 W/K and wall split height=0.15 m. The native pressure domain is 10000–1250000 Pa. Authored map points (kg/s, Pa rise) are (0,600000), (0.004,450000), (0.008,0), efficiency 0.7 and required NPSH 0.5 m.

The line is a 5 m by 25 mm mixed volume with roughness 1 micrometre, wall C=100 J/K, fluid/wall UA=0.5 W/K and ambient UA=0.05 W/K. Initially 850000 Pa, 20.1 K; wall 30 K. The vaporizer volume is 0.0002 m3, wall C=200 J/K, fluid/wall UA=10 W/K, ambient UA=1 W/K, symmetric fluid heat cap=1000 W; initially 700000 Pa / quality 0.2 with wall 100 K. Ambient is 300 K. The separate 1 m by 1 mm HEM restriction has 1 micrometre roughness; line hydraulic half-segments are not also counted. The outlet shared nozzle is 0.5 mm with area factor 0.8 into a 150000 Pa reservoir. Reverse valve flow is disabled.

At 0.037 s the pump assembly switches from the actual mapped pump to an actual closed shared valve; at 0.073 s the outlet closes. Duration=0.15 s. The first switch is a declared ideal instantaneous stop/isolation limit. It does not model rotor rundown, deadhead heating, casing fluid storage or motor losses. A native failure cannot select this mode automatically. The exact property paths use explicit 1e-8 quality roundoff budgets.

The restriction now uses one bracketed Darcy kernel and the explicitly selected direct fluids 1.3.1 Churchill_1977 Darcy function; native HEM phase-weighted viscosity is retained. This is a declared friction-correlation change, not an assertion of improved experimental accuracy in transitional two-phase flow.
Installed friction-module SHA-256: `6e0327c701e8dc63a0fb2cc87a03cd3c4e25e2a86387b7f31d17b340e2e75a7c`.

A retained native heating state has Re=2296.11603356: the original reported momentum residual is 0 Pa but independent Darcy reconstruction gives 44.3085831657 Pa. Merely bracketing the original discontinuous friction law still leaves 43.9463981079 Pa and is rejected despite its root flag. The explicitly selected continuous law plus bracketed solver gives -5.68434188608e-14 Pa. These distinguish numerical convergence from the empirical closure choice; request 009 specifies consolidation.

| Step s | Accepted | Sampled delivered kg | Sampled shaft J | Sampled ambient J | External mass residual kg | External energy residual J | Max node mass residual kg | Max node energy residual J | Release after feed isolation kg | Wall s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 16 | 3.03518006117e-05 | 0.487764567039 | 40.3333558628 | -5.97106598276e-11 | -0.000224299892738 | 1.9597631894e-16 | 1.31548105742e-11 | 1.50964759511e-05 | 2.07025939997 |
| 0.005 | 32 | 3.03518442618e-05 | 0.487583420288 | 40.3333561903 | -1.60621458489e-11 | -5.82867592831e-05 | 1.75247728655e-16 | 1.33653088596e-11 | 1.50964759493e-05 | 2.65902300001 |
| 0.0025 | 61 | 3.0351856251e-05 | 0.487535701831 | 40.333356277 | -4.07342755582e-12 | -1.48761750633e-05 | 4.64309580367e-16 | 2.27178276191e-11 | 1.50964759489e-05 | 4.61701049999 |

The independent external comparison uses accepted-sample trapezoids for delivery mass/enthalpy and shaft work, preserving both command limits. Ambient power is independently recomputed from each actual wall temperature and its declared ambient UA, not read from the native derivative. Gates are 1e-8 kg / 0.01 J; quadrature errors decrease under refinement. Native per-node conservation uses the native integrated fluxes separately, with the driver defaults 1e-8 kg / 1e-4 J plus relative 1e-8 on changes/fluxes. It is not a second exact RK ledger or independent physical experiment.

Finest-two-run maximum final node mass/pressure relative differences: 1.37860389771e-10 / 1.60107183067e-09; gates 1e-6 each. Minimum declared pump NPSH margin: 293.564407192 m.

After feed isolation the tank's total mass remains constant while its phases and walls continue relaxing. The stored downstream devices still discharge until outlet closure. After both outside transfers stop, the complete assembly retains mass and its stored energy change equals external ambient heat. Each dynamic node closes independently.

The original property path at 0.005 s takes 21.4323832 s versus 2.65902300001 s for the single-flash facade (ratio 8.06024739). Maximum final node mass/pressure differences are 7.78266340262e-14 / 1.06259445687e-12, below the predeclared 1e-6 gates. This is a separate complete workload from earlier timings.

Negative checks reject omission of pump shaft work (residual 14.6266185229 W) and an out-of-map point (momentum residual -50000.0000126 Pa). The branch remains running on failure; no implicit isolation, clipped storage or alternate property solver is selected.

## Longer isolated heating and reverse transfer

The unchanged assembly is also advanced to 1 s at two steps, retaining the same 0.037/0.073 s commands. Heating eventually reverses the internal restriction flow; the outer ports remain closed. This checks beyond the short positive-pressure-gradient sequence. Only the single-flash path is used for this longer refinement pair.

| Step s | Accepted | Minimum internal flow kg/s | Maximum internal flow kg/s | Closed mass error kg | Closed energy/heat error J | Max node energy residual J | Independent Darcy residual Pa | Wall s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.00125 | 801 | -0.000520899942805 | 0.000754823897991 | 1.55431223448e-15 | 3.66640051652e-11 | 6.26272367299e-11 | 6.75208866596e-09 | 51.3863813 |
| 0.000625 | 1602 | -0.000520899884716 | 0.000755239813745 | 6.66133814775e-16 | 9.60653778748e-11 | 1.12052589429e-10 | 6.76664058119e-09 | 93.1603723 |

Long-pair maximum relative final node mass/pressure differences: 1.08694949263e-07 / 1.68223042496e-07; gates 1e-6 each. An initial native 0.0025/0.00125 s pair conserved inventory but failed the final-state gate. Its tighter pair passed that gate but a newly sampled transition point failed the independent Darcy check; both negative results prompted the explicit hydraulic correction above. All gates are retained for the corrected trajectory. The horizontal Darcy pressure loss is independently recomputed from actual signed mass flow, upstream density and reported friction at accepted points; its gate is 0.01 Pa. The native zero-speed setter is also checked to reject zero while retaining its prior speed, documenting the concrete request 008 limitation.

Independent equipment/plant experiments, wave/spatial refinement, pressure-trigger localization, phase/mass depletion, real actuator/rotor/casing dynamics, frosting and atmospheric/ground source partition remain unfinished. Results describe the declared mixed-volume and quasi-steady transfer level only.

Host code SHA-256:

- `src/h2physics/dynamics.py`: `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd`
- `src/h2physics/adapters/lh2dt_dynamics.py`: `24d47555c295cfd7850459933a2077b1c37bf5ffcffa292045b962cd93daec69`
- `src/h2physics/adapters/lh2dt_modes.py`: `743cad6831df1daaaf438a8d2f3b48ccf311a429b5773cdd8f05d86664d6d786`
- `src/h2physics/adapters/lh2dt_supply.py`: `200163e12dbe350cb981b3f4a5a9de26f6247f74870ebabb9edf29d51863b2d6`
- `src/h2physics/hydraulics.py`: `856d8ee8c3ce5781b5804c3c2351fc5133886e4c23807e6fe3835ec50ba4e2b7`
- `src/h2physics/adapters/lh2dt_hydraulics.py`: `3ff182e0a5b5cc802624f389a13d45a874c9867ca3b361ff9d6f33d1a418c46c`
- `scripts/check_equipment_network.py`: `ba1bbe6f246b5d6d4b5de190a10a0ec72f597503b44fc4afea291f8422519769`
- `scripts/check_finite_supply.py`: `2a0b4f4f65f487604b549d6eb900c85ee761d9fb3db814fb40966846ad822780`
