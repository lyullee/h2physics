# Native pressure-rise contents heat and conditional area

Reproduce: `python scripts/check_pifira_heat.py` with the separately installed inverse_heat extra/native target.

pifira0.3.0, CoolProp8.0.0, SciPy1.18.1; six native heat inversions and three-spin direct-EOS forward paths completed in 0.150009s. No native source or source data is bundled.

Original authored verification case: rigid0.04m3 vessel, initial liquid volume fill0.35 and pressure150000Pa(abs). Native initial mass is explicitly requested. Direct HEOS rho/U forward states use prescribed Q(t)=1000+20(t-100)W on absolute100–120s, independently yielding each pressure. Native inversion sees only that pressure history, fixed mass and actual TankSpec. Nine and33 output samples test interval-average power and total energy; no pressure or kinetic coefficient is fitted.

The public API takes Pa absolute. Native gauge coordinates subtract its recorded101325Pa API zero, then native routines add it back; this is a reversible native unit conversion, not an atmospheric offset inferred from a measured gauge sensor. Direct native/EOS U checks enforce material/energy-reference agreement. Every sampled fixed-density state must stay within the declared two-phase domain; unobserved between-sample paths, mass/volume closure and missing wall/loss/work boundaries are not inferred.

| Fluid | Samples | Fixed mass kg | Final P Pa(abs) | Max native/EOS U error J | Max forward-power error W |
|---|---:|---:|---:|---:|---:|
| Hydrogen | 9 | 1.01793407226 | 221679.579822 | 1.45519152284e-11 | 6.02540239925e-10 |
| Hydrogen | 33 | 1.01793407226 | 221679.579822 | 1.45519152284e-11 | 1.89766069525e-09 |
| ParaHydrogen | 9 | 1.01794092375 | 221709.048572 | 1.45519152284e-11 | 6.40284270048e-10 |
| ParaHydrogen | 33 | 1.01794092375 | 221709.048572 | 1.45519152284e-10 | 2.31671037909e-09 |
| OrthoHydrogen | 9 | 1.01801077942 | 221647.071249 | 5.82076609135e-11 | 2.7944224712e-10 |
| OrthoHydrogen | 33 | 1.01801077942 | 221647.071249 | 1.16415321827e-10 | 2.14208739635e-09 |

Independent analytic angular drive uses295K ambient,8e10K4 amplitude,32degree sigma and five centered angles[-120,-60,0,60,120]degrees. Native equivalent area is0.139996532851m2 for0.4m diameter and [0,0.6]m flame /[0,0.5]m wetted intervals on one declared axis; fit residual8.56113533973e-17. An offset[0.3,0.9]m flame intersects the same wetted region over0.2m; [0.8,1.4]m is disjoint and gives0m2 with explicit flux rejection. Doubling all absolute temperatures leaves the native area difference0m2. Explicit first-interval contents-equivalent flux is7187.67800538W/m2. It is not incident fire flux.

| Gate | Pass |
|---|---|
| three actual pure H2 spin providers /two sample grids retain native objects | True |
| independent forward-EOS interval power errors <1e-5 W | True |
| independent native-vs-direct-EOS total U errors <1e-5 J | True |
| two output grids preserve integrated total contents heat <1e-5 J | True |
| all native fixed-mass states stay explicitly two phase | True |
| native centered Gaussian sigma/area agree with independent analytic geometry | True |
| doubling absolute temperatures preserves shape/area | True |
| explicit offset intervals give0.2m overlap and disjoint intervals give zero area | True |
| native kW/m2 to SI W/m2 and explicit allocation retained | True |
| all attempted domain/statistic failures remain rejections | True |
| native and executed-host begin/end source bytes match | True |

This is numerical/native-reference verification. The heat result is signed contents internal-energy rate. It does not separate incident radiation/convection, wall storage, losses, work, vents or spin conversion. The area interpretation assumes the evidenced centered local positive Gaussian radiation shape and wetted axial boundary. Ordinary mean T does not establish mean T^4; fourth-power-equivalent/instantaneous statistics and exact source/clock/interval identities remain explicit. Native fit failure, excessive arc/tail/residual and unavailable phase/EOS states are rejected. No acquired thermal experiment is fitted or called validated.

Primary sources: [native pifira API](https://github.com/lyullee/pifira), [archived0.3.0 source](https://doi.org/10.5281/zenodo.22291661), [CoolProp low-level EOS](https://coolprop.org/coolprop/LowLevelAPI.html). The original host composition, forward cases and guards do not copy native implementation, published examples or experimental values.

## Executed source identities

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/adapters/pifira_heat.py` | `8d75faf8d087fe3b167e9e1445dccb7515fff58746db35e3bd244f55f64cbce2` | `8d75faf8d087fe3b167e9e1445dccb7515fff58746db35e3bd244f55f64cbce2` |
| `tests/test_pifira_heat.py` | `63ad799cf12507e7df8843ef9a18ef24457307efca3290bc82b674d8bae4a929` | `63ad799cf12507e7df8843ef9a18ef24457307efca3290bc82b674d8bae4a929` |
| `scripts/check_pifira_heat.py` | `f73e08398085d38213b306c99ae87fc0f94f47e6d6ed16493c14690c430af3df` | `f73e08398085d38213b306c99ae87fc0f94f47e6d6ed16493c14690c430af3df` |
| `src/h2physics/thermo/coolprop.py` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` |
| `src/h2physics/core.py` | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` | `4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68` |
| `research/pifira_dependency.toml` | `aa86fa369ff2c7c6044bd4982efd9d5961003e59dc09595287c193fbb252dfd7` | `aa86fa369ff2c7c6044bd4982efd9d5961003e59dc09595287c193fbb252dfd7` |

| Separately installed native file | Begin SHA-256 | End SHA-256 |
|---|---|---|
| pifira/__init__.py | `89e0ae894fd88cdaebd9ccd0f6487956165352fceda61791bf411e54303b930b` | `89e0ae894fd88cdaebd9ccd0f6487956165352fceda61791bf411e54303b930b` |
| pifira/effective_area.py | `90ad826da8f5d0ddd3cac2633708e9528ce12c74693dd1c025645fceca5ce1c2` | `90ad826da8f5d0ddd3cac2633708e9528ce12c74693dd1c025645fceca5ce1c2` |
| pifira/io.py | `78a680e455ef4a591a89ebbb6d22f1c118005b8219bc1dc938c218301c467871` | `78a680e455ef4a591a89ebbb6d22f1c118005b8219bc1dc938c218301c467871` |
| pifira/lh2/__init__.py | `ba0cd12e89bfe71a37402b413f756ed36ce299820474dd63e00ce39405a9005f` | `ba0cd12e89bfe71a37402b413f756ed36ce299820474dd63e00ce39405a9005f` |
| pifira/lh2/credit.py | `0474eb94132373d52a446dd3419bfc91b0ab175140acd55b02489c706b147d08` | `0474eb94132373d52a446dd3419bfc91b0ab175140acd55b02489c706b147d08` |
| pifira/lh2/nozzle.py | `2642db4a97c7bf30b197b54e2ab3c825fb5c6e42d22cc59a8900105aeb9a975e` | `2642db4a97c7bf30b197b54e2ab3c825fb5c6e42d22cc59a8900105aeb9a975e` |
| pifira/lh2/spin.py | `0cf345f138e0fd48f213f6a0e6db668af860b64637e9fa09813e5d9896b50b6f` | `0cf345f138e0fd48f213f6a0e6db668af860b64637e9fa09813e5d9896b50b6f` |
| pifira/pressure_rise.py | `34f017b49b750340f2ae922ffe693bb6f958c024bfa37e654b67c78ef77b38b4` | `34f017b49b750340f2ae922ffe693bb6f958c024bfa37e654b67c78ef77b38b4` |
| pifira/representative.py | `04b7556e8dc6efd7201461d8b9b814217abb57eeff4cd1269f7d38348e6a31f5` | `04b7556e8dc6efd7201461d8b9b814217abb57eeff4cd1269f7d38348e6a31f5` |
