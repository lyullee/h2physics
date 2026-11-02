# Shared spherical diffusion and finite microsphere verification

Actual local execution: CoolProp 8.0.0, SciPy 1.18.1; 2.248359s.

All cases and coefficients are authored numerical checks. No glass-specific fit, optical response, experimental validation or vessel qualification is claimed. The same finite-volume BDF core owns planar and spherical mobile/trap transport. Native gas objects and fugacity are reused from the existing finite-gas thermodynamics contract. No new EOS, nozzle or cavity trajectory ODE is implemented.

For a shell the analytic steady total rate is 4*pi*D*(c_inner-c_outer)/(1/r_inner-1/r_outer). Integrated radial face resistance recovers that rate. The independent startup reference transforms u=r*c and integrates its sine-series solution over the true shell volume; 200 modes at positive time were used. It is not the discrete solver used as its own oracle.

| Cells | Numerical wall mol | Absolute series error mol | Maximum wall residual mol |
|---:|---:|---:|---:|
| 20 | 5.53434085228 | 0.00812803558193 | 1.35559186099e-09 |
| 40 | 5.54043982003 | 0.00202906783231 | 8.44656428134e-10 |
| 80 | 5.54196180181 | 0.000507086047251 | 9.58871593237e-11 |

Cavity cases use inner/outer radii 10/11 micrometres, initial native 100000Pa(abs)/300K, D=1e-14m2/s, linear solubility coefficient=1e-5mol(H2)/(m3 Pa), and fixed-spin normal or para H2. These are demonstration inputs, not material properties. Absolute times start at100s. Most cases end at200s; charge ends400s with outside fugacity200000Pa; the prescribed warming ends120s at320K and uses zero solubility to isolate constant-inventory EOS heating. Sealed outer means zero flux, while ordinary release imposes zero outside fugacity. Both are explicit caller boundaries.

| Case | Initial gas mol | Final gas mol | Final P Pa(abs) | Final wall mol | Outward exterior mol |
|---|---:|---:|---:|---:|---:|
| normal-release-8 | 1.67833593081e-13 | 1.66046085274e-13 | 98934.3362721 | 6.43314211833e-16 | 1.14419359544e-15 |
| normal-release-16 | 1.67833593081e-13 | 1.66044898989e-13 | 98933.6290456 | 6.43174995436e-16 | 1.14551909663e-15 |
| normal-release-32 | 1.67833593081e-13 | 1.6604460246e-13 | 98933.4522639 | 6.43140146103e-16 | 1.14585047543e-15 |
| normal-charge | 1.67833593081e-13 | 1.71059915134e-13 | 101923.479402 | 2.13611148541e-15 | -5.36243353854e-15 |
| normal-closed-outer | 1.67833593081e-13 | 1.66572104406e-13 | 99247.9332496 | 1.26148867501e-15 | 0 |
| para-release | 1.67833635945e-13 | 1.66044942284e-13 | 98933.6298587 | 6.43174842014e-16 | 1.14551881843e-15 |
| prescribed-heating | 1.67833593081e-13 | 1.67833593081e-13 | 106668.185607 | 0 | 0 |

Cavity refinement ratio=4.00056286029. Maximum normalized defects: total 1.06135165831e-13, gas 1.92005421302e-15, wall 1.06587565501e-13. Independent native pressure-to-inventory reconstruction 6.01632807917e-16; fugacity relative disagreement 0.

| Gate | Pass |
|---|---|
| host source bytes unchanged during execution | True |
| spherical exact steady resistance relative error below 1e-10 | True |
| radial startup independent series converges at second order | True |
| finite-cavity mesh refinement ratio exceeds 3 | True |
| total mass-equivalent residual below 1e-10 of initial cavity | True |
| gas transfer residual below 1e-10 of initial cavity | True |
| wall transfer residual below 1e-10 of initial cavity | True |
| independent HEOS pressure-to-moles inversion error below 1e-8 | True |
| independent native fugacity agreement below 1e-10 | True |
| charge increases cavity moles | True |
| normal and para release decrease cavity moles | True |
| sealed outer stores wall H2 with zero exterior transfer | True |
| prescribed warming increases pressure at fixed cavity inventory | True |
| floor temperature and pressure domain violations reject | True |

Prescribed temperature is shared by wall and gas, without a computed thermostat duty or an energy closure claim. Geometry is rigid and single-sized. Deformation, burst, surface kinetics, optical enhancement, source-specific transport coefficients and actual thermal transients need independent evidence. A finite-inventory floor crossing rejects the requested window; it is not clipped or reported as a localized depletion event. Fixed-spin EOS does not predict spin conversion.

Public primary context: [hydrogen permeation through glass](https://doi.org/10.3389/fmats.2019.00342), [molecular diffusion measurements](https://doi.org/10.1063/1.324180); native [CoolProp API](https://coolprop.org/coolprop/LowLevelAPI.html). No source coefficients, tables, worked examples or implementation code are reproduced.

## Executed source identities

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/materials/finite_volume.py` | `b86cb583c00a0f18c8292a7d8a9511bd8f9ca5bf9f69e63a91fb0f96707b8e94` | `b86cb583c00a0f18c8292a7d8a9511bd8f9ca5bf9f69e63a91fb0f96707b8e94` |
| `src/h2physics/materials/transport.py` | `185851c40951affbb829432d75de43f67b751d3ad1f53d2445412e0251e42726` | `185851c40951affbb829432d75de43f67b751d3ad1f53d2445412e0251e42726` |
| `src/h2physics/materials/__init__.py` | `d07d1ec07b448621081978d3f62023f3e4ea735edaebb127f0aab46b6f26d3bc` | `d07d1ec07b448621081978d3f62023f3e4ea735edaebb127f0aab46b6f26d3bc` |
| `src/h2physics/storage/microsphere.py` | `aa618747e0abee22c163e36bf8f4468b413dfc613efcf90a8a83968afddbd137` | `aa618747e0abee22c163e36bf8f4468b413dfc613efcf90a8a83968afddbd137` |
| `src/h2physics/storage/__init__.py` | `13b3834a30d3407ba1bf3a042966667d89d6aa7a1ce89a2beeebc666fe57e8bf` | `13b3834a30d3407ba1bf3a042966667d89d6aa7a1ce89a2beeebc666fe57e8bf` |
| `src/h2physics/storage/finite_hydride.py` | `9fa148a4b1680bf2deccca71cad4d518973bd2c9a6b146bd7a48764ce86ea989` | `9fa148a4b1680bf2deccca71cad4d518973bd2c9a6b146bd7a48764ce86ea989` |
| `src/h2physics/thermo/coolprop.py` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` |
| `tests/test_microsphere.py` | `232a1f73015010db136044b1450ddf0b6d24f1a603e346532349bec728083ba8` | `232a1f73015010db136044b1450ddf0b6d24f1a603e346532349bec728083ba8` |
| `tests/test_curvilinear_diffusion.py` | `23735660db918b53de765f2cf23890d9b2f2ce7cafc013b53c8213b1b289492f` | `23735660db918b53de765f2cf23890d9b2f2ce7cafc013b53c8213b1b289492f` |
| `tests/test_materials.py` | `de85b8147a8c3929c070d0c754d0afe05da470de7d4d15b741fbf806938283eb` | `de85b8147a8c3929c070d0c754d0afe05da470de7d4d15b741fbf806938283eb` |
| `scripts/check_microsphere_storage.py` | `5cc93efd9bf9424844e9333ae8bdd3565b49e887927bffaf2c0f11523d1dd998` | `5cc93efd9bf9424844e9333ae8bdd3565b49e887927bffaf2c0f11523d1dd998` |
