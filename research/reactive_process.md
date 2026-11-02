# Native finite reacting gas process

Reproduce: `python scripts/check_reactive_process.py` with the optional chemistry extra.

Cantera 3.2.0; installed GRI30 has 53 species and 325 gas reactions. Three host native integrations plus one plain native reference took 35.716 s. Native kinetics/EOS/CVODES are unchanged; no mechanism is bundled.

Original verification inputs: rigid 0.001 m3 ideal-gas inventory, initially pure N2 at 1500 K and 101325 Pa. Fixed feed reservoir is 1500 K /200000 Pa, X(CH4,H2O,N2)=(0.2,0.5,0.3). Inlet and outlet are each prescribed 0.0001 kg/s on the absolute [0,0.2] s window; callbacks explicitly support [0,0.5] s. Outlet removes native well-mixed composition/enthalpy. No wall or work is present. A separate oxidative case uses X(CH4,H2O,O2,N2)=(0.2,0.5,0.05,0.25). These are authored numerical cases, not apparatus operating data, catalyst fits or independent experiments.

Coarse steam run: max step 0.01 s /rtol1e-8; fine: 0.0025 s /rtol1e-10; oxidative: 0.005 s /rtol1e-9; host atol1e-15. The plain IdealGasReactor reference has no host extension/appended ledger, uses the original native definitions, max step0.0025 s /rtol1e-10 /atol1e-16, and compares every output state.

Boundary-only species integrals remain separate from integrated native net chemical production. Species defects subtract both; elemental defects subtract boundary transport only. Native formation energy is already included in U and h, so no separate reaction power is added. Energy-ledger numerical conditioning uses the existing1e6 J scale; returned quantities are SI. No physical row is rescaled.

All reactive phases own independent native species thermo and reaction objects. The constructor preserves native thermo class, exact coefficients/bounds/reference pressure and runtime reaction multipliers. A one-time structural gate admits only native numeric unit-roundtrip error <=2e-15 relative with zero absolute allowance; prose note changes are counted. Element order may change, with both orders recorded and per-name atomic weights checked. Source and owned exact hashes are distinct. Actual owned definitions are checked exactly at accepted outputs. Phase-exposing callbacks additionally retain exact per-RHS checks; explicit time-only callbacks receive no native phase and use privately owned definitions.

| Quantity | Observed value |
|---|---:|
| Steam final T /P | 1495.89315332 K /104346.727353 Pa |
| Steam final H2 /CH4 mole fraction | 0.0038201187137 /0.0193084214613 |
| Steam integrated chemical H2 production | 6.64918466396e-08 kg |
| Steam net boundary H2 transfer | -1.88010314759e-09 kg |
| Oxidative final T /H2 mole fraction | 1520.7002654 K /0.0111937492822 |
| Maximum mass /species /element defect | 0 /4.25707335926e-17 /3.88542483235e-17 kg |
| Maximum U/enthalpy energy defect | 3.74210422649e-08 J |
| Independent source /constant inventory error | 1.42301535139e-19 /0 kg |
| Plain native full-trajectory T /P /Y error | 2.6674797482e-08 K /1.66488462128e-06 Pa /1.24618468756e-12 |
| Coarse/fine full-trajectory T /Y difference | 8.44004716782e-07 K /6.97105940681e-11 |
| Accepted-output sampled minimum mass fraction | -4.9192403901e-15 |
| Max native copy roundtrip /per-phase changed numeric counts | 2.27738056333e-16 /[103, 103, 103, 103, 103, 103, 103, 103, 103] |

| Gate | Pass |
|---|---|
| native gas chemistry and native ReactorNet remain actual objects | True |
| mass/species/element defects <1e-10 kg | True |
| native U and boundary enthalpy energy defect <1e-4 J | True |
| integrated native chemical production sums to mass <1e-10 kg | True |
| independent constant source integral and constant inventory <1e-10 kg | True |
| plain native unextended full trajectory <1e-3 K /0.2 Pa /1e-7 Y | True |
| coarse/fine full trajectory <1e-3 K /1e-7 Y | True |
| steam-only gas converts carbon feed and produces net H2 and CO | True |
| oxidative feed separately produces H2 with positive heat response | True |
| no external chemical-heat boundary or wall heat added | True |
| raw accepted-output composition; sampled minimum Y >=-1e-12 | True |
| private definitions audited <=2e-15 relative; exact owned hash retained | True |
| reaction H2 production distinct from boundary-only H2 removal | True |
| host/test/replay source bytes unchanged across run | True |

This is one gas-phase carbon/steam conversion reference for production research. GRI30 gas chemistry does not qualify a catalytic steam reformer or shift bed. Catalyst surfaces, solids/coke, porous transport, spatial residence profiles, pressure-driven capacity, wall inventory, phase changes, industrial yields and measured process qualification remain open. Imposed equal mass flows do not solve a compressor or valve. H2 spin remains unresolved on the native formation-energy zero; no CoolProp energy conversion is implied.

Primary references: [native control-volume equations](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), [public extension/flow APIs](https://cantera.org/3.2/python/zerodim.html), [native reaction-rate APIs](https://cantera.org/3.2/python/kinetics.html), [separately installed GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html). Cantera retains BSD-3-Clause and upstream mechanism provenance. No external code, coefficient table or mechanism text is copied into this repository or its distributions.

## Reproduction fingerprints

- Installed gri30.yaml SHA-256: `06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345`
- Source mechanism-phase SHA-256: `c44de7b10143b80c53f4918a5c6d8cb7cac26d40e300e8b33a5b87d1d627e6b4`
- Owned native phase SHA-256: `ea099ee997c16d13758d541a2fae5a60dc1ca9cb8b51248e538dfa148bd6db22`
- Source /owned element ordering: `('O', 'H', 'C', 'N', 'Ar')` /`('H', 'O', 'C', 'N', 'Ar')`

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/adapters/cantera_volume.py` | `e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1` | `e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1` |
| `scripts/check_reactive_process.py` | `c5e85e040c183e02763e782e75eeaf656863fcec15c3299876d9378eb543422a` | `c5e85e040c183e02763e782e75eeaf656863fcec15c3299876d9378eb543422a` |
| `tests/test_reactive_gas_volume.py` | `de7e5b3d438b1d57c315c85521d01675e2503c25e460756663a2eb95f1cbe2e9` | `de7e5b3d438b1d57c315c85521d01675e2503c25e460756663a2eb95f1cbe2e9` |
| `src/h2physics/adapters/cantera.py` | `19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184` | `19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184` |
