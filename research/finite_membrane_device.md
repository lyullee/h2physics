# Finite two-side native porous membrane reference

Reproduce: `python scripts/check_membrane_device.py` with optional Cantera3.2.

Actual Cantera3.2.0; seven accepted reference trajectories, a separate mutable-object guard probe and three retained failure probes took 11.5108s. No native implementation or dataset is bundled.

Original warm H2/N2/Ar inputs:330K,101325Pa; mole fractions left(.7,.2,.1),right(.4,.5,.1); both finite rigid volumes.02m3, gross membrane area.005m2, thickness.001m, pore radius50nm, porosity.35, native tortuosity factor2.5 and explicit zero permeability. All are authored fixtures, not measured membrane data. The native signed stationary-solid flux is multiplied by gross area once, with no extra epsilon or product-fraction normalization.

Existing constitutive preparation supplies independently owned actual native phases and a private DustyGas. Two native ExtensibleIdealGasReactors in one ReactorNet own finite mass/species/dilution; public bulk-source hook sdot uses kmol/s. No physical mass/species derivative is copied or replaced. CVODES also integrates appended species/H/thermostat ledgers. Both sides are frozen ideal gas with the same native NASA formation reference and mechanism-unresolved H2 spin; no pure-fluid caloric-zero substitution.

Native energy is off to prescribe the same T on both sides. Signed transferred partial H and required thermostat Q=(u-h) dotted with native species transfer are separate. Each rigid-side deltaU=Htransfer+Q closes; combined species/mass/U are conserved. This is not an adiabatic device or a prediction of membrane thermal flux, wall storage or heat-recovery performance.

| Actual check | Value |
|---|---:|
| left final pressure Pa at102s | 101256.352948 |
| right final pressure Pa at102s | 101393.647052 |
| left required thermostat Q J | 1.37294104509 |
| right required thermostat Q J | -1.37294104509 |
| short-time native source/area relative error | 4.54028121741e-08 |
| max side species residual kg | 9.82304108931e-18 |
| max combined mass residual kg | 6.72205346941e-18 |
| max side U-H-Q residual J | 3.84203779902e-12 |
| max combined U residual J | 5.45696821064e-12 |
| reversal inventory error kg | 1.38777878078e-17 |
| area-time scaling inventory error kg | 3.33934269126e-17 |
| maximum-step/tolerance refinement error kg | 1.69135538908e-17 |
| finite Knudsen exponential relative error | 6.94318217289e-10 |
| private pore reset flux error mol/m2/s | 0 |

The short-time derivative uses.0001s and the actual initial native flux times molecular weights and gross area. Refinement changes native maxstep.1→.025s, rtol1e-9→2e-11, atol1e-15→1e-17. The independent finite-volume analytic oracle uses the dilute Knudsen limit at.01Pa for20s: each concentration difference decays exponentially with rate A*D_eff/L*(1/V_left+1/V_right), preserving each total species amount. D_eff uses the published/native Knudsen limit. No equilibrium solver or second trajectory ODE generates that oracle.

| Native/accepted numerical admission | Observed maximum |
|---|---:|
| raw native trial Y sum deviation | 1.10971996037e-08 |
| sampled accepted Y sum deviation | 2.22044604925e-16 |
| raw native trial T deviation K | 4.91738319397e-06 |
| raw native trial relative volume deviation | 1.49011611938e-08 |
| actual evaluated absolute clock range s | (100.0, 102.09656612290382) |

Raw native NoNorm trial species concentrations are passed without host clipping or renormalization. The explicit constant-T numerical extension admits trial sum and relative T/V deviations up to1e-6; accepted sampled sum budget is1e-10 with exact prescribed T/volume. Native trial type is unobservable; extrema are not labeled proven FD probes. Native DustyGas uses a Tiny mean-mole-fraction floor internally; this is not epsilon inventory added to the two finite sides. Internal clipping/regularization history is not available through the API.

| Retained rejected probe | Accepted prefix length | Last accepted s | First triggering s | Native time s | Completed trace | First reason |
|---|---:|---:|---:|---:|---|---|
| right inventory guard | 2 | 100.001 | 100.73463229553937 | 100.714632372 | False | Finite side 1 reached its declared inventory limit |
| rejected native trial extension | 0 | None | 100.0 | 100 | False | Native trial left the declared unprojected composition/isothermal extension |
| post-completed independent audit | 3 | 102.0 | None | 102 | True | Finite membrane independent species/energy audit failed |

Inventory rejection uses a right-side limit99.99% of its initial native mass. It retains the actual first offending state/time and a previously accepted sample, not an exact depletion event root. A deliberately overstrict trial budget and a post-completed independent audit budget also fail visibly. All errors retain actual ReactorNet/reactors, native states/ledgers, accepted prefix and original cause. The first boundary error is sticky even if CVODES would retry. Native failure probes can print native small-step warnings; they are not hidden or repaired.

A separate completed probe is intentionally edited after return to verify pore reset and source-polynomial rejection; its edits invalidate that mutable object's recorded trace. The seven accepted reference trajectories are not edited. Each coupling checks source state/basis, owned/source thermo and transport polynomials, private kernel definition, reactor configuration and evidence binding. The private kernel has no user callbacks and its write-only pore values are reset before evaluating a changed state.

| Verification gate | Pass |
|---|---|
| both finite native reactors in one actual network | True |
| independent short-time native source units and gross area <2e-5 relative | True |
| finite pressure/composition feedback and counterdiffusion | True |
| equal states remain stationary | True |
| side species and combined mass close | True |
| each-side U=H+Q and combined U close | True |
| separate required thermostats cancel at common T | True |
| reversed sides swap inventories <1e-11 kg | True |
| gross area-time scaling <1e-11 kg | True |
| native maximum-step/tolerance refinement <1e-11 kg | True |
| independent finite Knudsen exponential limit <2e-7 relative | True |
| native raw trial and accepted deviations recorded separately | True |
| actual depletion/trial/audit failures retain raw objects and causes | True |
| private kernel pore reset and source polynomial guard | True |
| host/test/script/docs and reused sources unchanged | True |
| native data/license/binary unchanged | True |
| new host inputs are LF text | True |

No independent measured membrane/device comparison has been performed. Physical material selectivity, adsorption/storage, layer resolution, nonisothermal transport, heat capacity/conduction, supported depletion events/restarts, products/separation work and facility operation require additional native models and evidence. No production efficiency, validated recovery or complete thermal membrane is claimed.

Primary sources: [extensible native reactors](https://cantera.org/3.2/python/zerodim.html#extensiblereactor), [native ideal-gas control volume](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), [DustyGas API](https://cantera.org/3.2/python/transport.html#cantera.DustyGasTransport), [versioned hook units](https://github.com/Cantera/cantera/blob/v3.2.0/src/zeroD/IdealGasReactor.cpp). Cantera implementation is BSD-3-Clause; separately installed upstream thermochemical/transport provenance is retained. No mechanism/coefficients are redistributed.

## Source fingerprints

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/cantera_membrane_device.py | d3449656bb4674a5e318e75f8c57acefc5c2e7d970d692b118a849fdd098ed02 | d3449656bb4674a5e318e75f8c57acefc5c2e7d970d692b118a849fdd098ed02 |
| tests/test_cantera_membrane_device.py | 918fa5311fcd90b6b15c42e7d7958f818f5a77de28f17439861f86a213dbb3a9 | 918fa5311fcd90b6b15c42e7d7958f818f5a77de28f17439861f86a213dbb3a9 |
| scripts/check_membrane_device.py | 1013d72dde8408446b6e56f252abeffb31a0148289b8ec85ae2a58a21e91f3e2 | 1013d72dde8408446b6e56f252abeffb31a0148289b8ec85ae2a58a21e91f3e2 |
| docs/FINITE_MEMBRANE_DEVICE.md | c7f8d901badffba56962d7e8915068fd2063c28b0590c7a461a3827d7b33dc6a | c7f8d901badffba56962d7e8915068fd2063c28b0590c7a461a3827d7b33dc6a |
| src/h2physics/adapters/cantera_membrane.py | c187e2f792e1942433bc86e0da20144ab48b42597031e9fb6d3d2d2653819085 | c187e2f792e1942433bc86e0da20144ab48b42597031e9fb6d3d2d2653819085 |
| src/h2physics/adapters/cantera_volume.py | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 |
| src/h2physics/adapters/cantera.py | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 |
| src/h2physics/core.py | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 |

| Installed input | Begin SHA256 | End SHA256 |
|---|---|---|
| installed h2o2.yaml | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 |
| Cantera license | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb |
| Cantera compiled extension | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d |

Source phase exact hash: `a06505712a1a0b58e1e475ce15e131c29e2241672876c36460be829a7c96414b`. Owned phase exact hashes: `ce4922a25d48c1996e8b915e34d49e7783affcc9c003cfd7b86acc17c1b49da9`, `ce4922a25d48c1996e8b915e34d49e7783affcc9c003cfd7b86acc17c1b49da9`. New host/report text is LF; native source and compiled inputs are unchanged.
