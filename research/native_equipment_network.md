# Native equipment and finite-inventory network verification

Native lh2dt_models 0.1.2, public MIT revision `b2f276333c1b1793c39f25763703d196d36742ec`.
Top-level native Python-source SHA-256: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
Declared property basis: `CoolProp:8.0.0:HEOS:ParaHydrogen:default` / ParaHydrogen.
The main case uses the verified single-flash native property facade, with explicit 1e-8 quality endpoint budget matching the reviewed native policy. A same-step original-provider trajectory is compared separately; no table/fallback is used.
All geometry, map, heat and operating inputs are authored synthetic values. No field-data calibration or experimental facility qualification is claimed.

Reproduce with `python scripts/check_equipment_network.py`. The exact optional native installation is documented in HANDOFF.md. The case factory exposes every parameter directly in Python.

The 0.3 m diameter, 0.3 m straight-length, 0.05 m head-depth vessel has separate initial liquid/vapor half volumes at 300000 Pa, 20/28 K. Wall capacities are 1000 J/K each, ambient conductances 0.1 W/K each, wall/fluid U values 1 W/(m² K), liquid/vapor interface conductances 100/50 W/K and wall axial conductance 0.1 W/K. A liquid phase port feeds the explicit 3000 rpm pressure-rise map, a 3 m × 3 mm line (roughness 1 µm, local loss 2), a 25 W/K / 50 kW-cap steady vaporizer with 5 K approach parameter and a 2 mm / 0.8 effective-area shared valve. The delivery boundary sets 150000 Pa; its reservoir temperature is not substituted for the transmitted stream temperature. All fluid states use ParaHydrogen.

| Component | Flow kg/s | Heat into fluid W | Shaft work into fluid W | Enthalpy/power residual W | Momentum residual Pa |
|---|---:|---:|---:|---:|---|
| pump | 0.00158023792884 | 0 | 17.0441673076 | -9.79009548985e-08 | 0 |
| heated-pipe | 0.00158023792885 | 4414.17621736 | 0 | -4.78112269775e-08 | -1.81898940355e-12 |
| valve | 0.00158023793129 | 0 | 0 | -9.09494701773e-13 | unavailable |

Native pump NPSH available/required: 294.992760485 / 0.5 m. Map/NPSH admissibility is checked, not inferred from mathematical convergence. Missing valve momentum is retained as unavailable, not zero. Energy accounting is the native steady enthalpy-only level; finite port kinetic/potential energy is outside that ledger.

A second graph with a declared 1000 m NPSH requirement still mathematically converges but has margin -705.007239515 m. Host checks reject that operating point despite closed mass/energy. This is an authored domain-failure case, not a pump degradation prediction.

| Pipe limit | Flow kg/s | Re | Relative Poiseuille error |
|---|---:|---:|---:|
| gas | 2.21785029091e-09 | 0.315921800599 | 8.589743139e-09 |
| homogeneous-mixture | 4.60256601422e-07 | 73.3730861312 | 3.5160674372e-09 |

Both limits use 1 m length, 1 mm diameter and 10 Pa pressure difference. The mixture uses an explicitly declared 0.2 equilibrium quality and the native quality-weighted viscosity closure. Agreement checks the laminar limit of that closure; it does not validate two-phase slip, distributed flashing or real pipe data.

Independent enthalpy-coordinate DOP853 vaporizer reference heat: 4414.35497498 W. It uses the same EOS and governing heat-transfer law through a different numerical integrator, not an independent physical experiment. The finest relative heat gate is 1e-4.

| Native enthalpy segments | Heat W | Relative reference error |
|---:|---:|---:|
| 64 | 4413.81657301 | 0.000121966169559 |
| 128 | 4414.17621725 | 4.04946436131e-05 |
| 256 | 4414.30210763 | 1.19762344607e-05 |
| 512 | 4414.34906757 | 1.33822694126e-06 |

A closed 0.1 s tank case exposes the original generic-network external-heat ledger omission: residual 5.51997240357 J. The explicit host heat bridge gives 5.83977310953e-12 J while retaining identical native phase equations/advance/combine callbacks. This is request 007; the receiving repository was not edited.

| Step s | Delivered kg over 2 s | Final tank P Pa | Maximum full mass residual kg | Maximum full energy residual J | Maximum tank energy residual J | Wall seconds | Checked solves |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.00309043537628 | 270167.595463 | 1.06648327322e-12 | 3.38175414072e-06 | 8.57625082062e-12 | 5.70819960001 | 10 |
| 0.5 | 0.00309042875325 | 270167.515496 | 1.07229394634e-12 | 3.18104230246e-06 | 6.87805368216e-12 | 12.5926122 | 20 |
| 0.25 | 0.00309043082741 | 270167.51011 | 9.27325057021e-13 | 2.98970735457e-06 | 7.14805992175e-12 | 23.1810026 | 40 |

At step 0.5 s the original provider takes 29.5172127 s versus 12.5926122 s for the single-flash facade (ratio 2.3440103). Relative delivered-mass/final-pressure differences are 4.20036726526e-12 / 9.13509093866e-14, each below the declared 1e-6 coupled gate. This is a measured complete solver path, not an extrapolated property-call benchmark.

Finest-two-step relative delivered-mass/final-pressure differences: 6.71155426683e-07 / 1.99379379083e-08; respective gates are 1e-6 / 1e-5. Every native RK stage and accepted solve passes host mass, enthalpy/power, reported momentum and declared operability checks. Only accepted points enter the predicted nozzle-plane SourceHistory; intermediate solves are diagnostic samples.

The full external ledger combines tank inventory change, tank ambient heat, pump/vaporizer power and delivered enthalpy/mass with the reviewed native RK4 weights. Its stage grouping is pinned to this exact native simulator revision. Valve nozzle quality is not a ground fraction. Finite line inventory, water hammer, stagnant/isolation transients, dynamic vaporizer inventory, arbitrary networks and independent equipment data remain outside this verification.

Host code SHA-256:

- `src/h2physics/equipment.py`: `071e2a1ccc2904d7bc39db8645487d79427fe4050ee908ece4eb1c325cdf0a36`
- `src/h2physics/adapters/lh2dt_equipment.py`: `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33`
- `src/h2physics/adapters/lh2dt_properties.py`: `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2`
- `src/h2physics/thermo/coolprop.py`: `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b`
- `scripts/check_equipment_network.py`: `ba1bbe6f246b5d6d4b5de190a10a0ec72f597503b44fc4afea291f8422519769`
