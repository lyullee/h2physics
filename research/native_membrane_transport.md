# Native porous-gas transport verification

Final scoped verification on the same executed inputs: Ruff passed and35 tests
passed in5.10s. The complete small native replay passed14 gates in1.565099s.
NumPy scalar endpoint/geometry/domain parameters are covered by a regression.
Effective native flux uses the bulk cross-sectional area convention; porosity
is already included. Later area/inventory coupling must not count it twice.

Actual Cantera3.2.0 (`4a8358e`), BSD-3-Clause native code. Installed h2o2.yaml contains GRI-Mech-origin thermochemistry and gas transport; the H2/N2/Ar selection is authored. No source mechanism, parameter table, measured membrane data or native code is bundled. No native source was modified.

Native DustyGas owns the coupled multicomponent/Knudsen/Darcy flux and ideal-gas EOS. The host reuses the existing audited native phase-copy helper and checks gas transport polynomial copying. Every calculation uses a new native DustyGas with explicitly declared porosity/tortuosity/pore radius/permeability; write-only native pore values are preserved by the immutable host parameter object.

Local replay elapsed1.565099s. Authored geometry: porosity0.4, tortuosity3, mean pore radius80nm, thickness2mm, explicit permeability2e-16m2. Endpoints360K; ordinary composition probe at101325Pa absolute. Coefficients are mathematical verification inputs, not a fitted or experimentally qualified membrane.

| Gate | Pass |
|---|---|
| actual native DustyGas/raw kmol and complete SI species arrays retained | True |
| native molecular masses give matching signed kg flux | True |
| zero state gradient gives exact zero flux | True |
| swapping endpoints reverses every signed flux | True |
| doubling separation halves native flux | True |
| coupled inert counterflux and nonzero total molar transport retained | True |
| native porosity/tortuosity factor checked without a squared convention | True |
| fixed physical 80nm pore low-pressure Knudsen oracle converges below1e-6 | True |
| explicit Darcy addition agrees with independent native-viscosity oracle | True |
| source state untouched and changed returned pore settings never reused | True |
| runtime-modified gas diffusion fits are rejected rather than replaced | True |
| native numerical failure preserves actual objects and original cause | True |
| native enthalpy diagnostics keep reference without inventing thermal closure | True |
| host/native input fingerprints unchanged and LF | True |

## Independent limiting checks

The Knudsen oracle keeps the80nm pore fixed and reduces equal endpoint pressure. Its coefficient is (2/3)*r*(porosity/tortuosity)*sqrt(8RT/(pi*M)); the molar concentration gradient comes from separate native endpoint densities and fractions. No submolecular radius is used to claim material applicability. The subnormal-radius case is only a native failure-retention test.

| Pressure Pa absolute | Relative max-norm Knudsen-limit error |
|---:|---:|
| 100000 | 0.377564682935 |
| 1000 | 0.00603062742169 |
| 1 | 6.06719973811e-06 |
| 0.01 | 6.06723623574e-08 |

At constant composition with105000/95000Pa endpoints, the explicit-permeability flux increment agrees with -c_i*kappa/mu*grad(P) to2.16840434497e-19mol/(m2s), using a separate native gas viscosity. This independently checks the extra Darcy term without replacing native gas transport or solving another EOS.

## Limits and continuation

The signed total species flux is relative to stationary porous solid and includes Darcy transport. It need not sum to zero; species can counterdiffuse. Native kmol/(m2s) is scaled by1000 to SI mol/(m2s), and kg flux uses native kg/kmol masses. The two-nearby-point closure is not a solved finite membrane profile or an area/time/inventory-based device. Product purity, recovery and selective solid solution-diffusion are not returned.

Admission requires normalized explicit X/Y and species order, neutral frozen single ideal gas, an explicit warm property/transport domain, isothermal endpoints, positive separation and valid pore geometry. Finite boundary inventories, axial profiles, reaction, adsorption, dense-gas corrections, condensation, scattering, thermal transpiration/Soret and solid/gas heat storage remain unresolved. Native endpoint partial enthalpies are diagnostics in the declared formation/phase reference; no heat balance or common stream is invented. H2 spin is unresolved. Future finite composition needs actual area/clock, component/energy ledgers and spatial refinement. Numerical verification is not measured membrane validation.

Mutable native diagnostic objects are retained for inspection. They are never reused internally. A caller changing their write-only pore settings cannot use the old immutable geometry record as proof of that new native configuration. Source state stays unchanged; changes of source thermo or transport definitions require new evidence. Native errors retain source/copies/DustyGas/raw completed flux and chained cause; there is no replacement provider.

## Sources and input fingerprints

Primary API/equation references: [Cantera3.2 Python transport](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport.molar_fluxes), [native DustyGas mathematical contract](https://cantera.org/3.2/cxx/dc/de6/classCantera_1_1DustyGasTransport.html). The implemented flux equations remain in Cantera; only independently authored limiting checks and unit/identity/admission logic are in this repository.

| Native input | Begin SHA256 | End SHA256 |
|---|---|---|
| h2o2.yaml | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 |
| compiled-native | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d |
| transport.pyi | b89dea0b0223fa6fe8a91a0ec07201ab2894323beec8cdbaed9a5bb988805b81 | b89dea0b0223fa6fe8a91a0ec07201ab2894323beec8cdbaed9a5bb988805b81 |
| Cantera-License.txt | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb |

| Host/reused source | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/cantera_membrane.py | c187e2f792e1942433bc86e0da20144ab48b42597031e9fb6d3d2d2653819085 | c187e2f792e1942433bc86e0da20144ab48b42597031e9fb6d3d2d2653819085 |
| tests/test_cantera_membrane.py | 018d48f8256f5e4441c210c9035dc3eae7d73b6b91c14ee87845823337220375 | 018d48f8256f5e4441c210c9035dc3eae7d73b6b91c14ee87845823337220375 |
| scripts/check_cantera_membrane.py | 59e361fe27e33a82eb00fb7246dc93e621b26ffd3935df7884510bc182ad7e41 | 59e361fe27e33a82eb00fb7246dc93e621b26ffd3935df7884510bc182ad7e41 |
| src/h2physics/adapters/cantera_volume.py | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 |
| src/h2physics/adapters/cantera.py | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 |
| src/h2physics/core.py | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 |
