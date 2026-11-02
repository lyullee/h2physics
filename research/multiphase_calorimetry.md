# Native gas and iron-oxide molar calorimetry

Reproduce: `python scripts/check_cantera_caloric.py` with optional Cantera3.2.

Actual native Cantera3.2.0; property/finite-reaction calculations and negative probes took 9.17597s. No native table, coefficient set or mechanism is bundled or modified.

Installed nasa_condensed.yaml contains FeO(s)300–1650K and Fe3O4(s)300–5000K, with no EOS/density for either. This authored fixture uses explicit constant-volume densities FeO5000 and Fe3O4 4800kg/m3, both Origin.SYNTHETIC. They are not measured properties or phase-stability evidence. The common demonstrated range is300–1650K; native ideal-gas h2o2 species supply H2O/H2/O2.

Native formation energy stays in H. All phases carry the caller-declared NASA formation reference and unresolved mechanism H2 spin identity. Matching metadata strings are not proof that arbitrary sources share a zero. Shared element atomic weights are checked. Gas partial h and pure-solid native h are divided by1000 from J/kmol to J/mol; native solid pressure corrections are retained.

| Actual numerical check | Result |
|---|---:|
| weighted SI species H minus actual native Mixture H J | -1.16415321827e-10 |
| native H-U-PV J | 3.27418092638e-11 |
| max solid deltaP*V enthalpy error J/mol | 8.91375862011e-11 |
| gas pressure-independence error J/mol | 0 |
| max finite-difference h derivative / native Cp relative error | 2.69603952837e-10 |
| minimum sampled native Cp J/mol/K | 28.8515656598 |
| reduction heat at1000K for extent.15mol J | 42724.3994539 |
| steam oxidation heat at1000K for extent.15mol J | -5545.09279679 |
| net water conversion heat J | 37179.3066572 |
| two-stage sum minus net water heat J | 8.0035533756e-11 |
| product-temperature roundtrip error K | 9.09494701773e-13 |
| product-temperature energy residual J | 0 |
| native state reset error J/mol | 0 |

The alternative actual native gas phase probe shifts both H2 NASA enthalpy constants by1000K, giving a raw H2 enthalpy change of8314.46261815J/mol at900K. Rebinding the exposed reused gas provider to that independent actual phase is rejected before returning a value under the recorded basis. Changes to its species order, native indices, MechanismBasis and basis_id are also rejected; restoring the original binding recovers all enthalpies within0J/mol. No source-global monkeypatch or replacement property function is used.

The extensive native Mixture audit uses1050K/350000Pa and finite SI mol Fe3O4=.37,FeO=.21,H2O=.6,H2=.13,O2=.08, without equilibrium. Pressure correction uses950K/101325→1100000Pa. Derivative checks use300.1,600,900,1400,1649.9K and a.01K centered step. These comparisons verify native caloric composition and units; native-Cp/finite-difference checks are not an independent thermochemical dataset.

Both finite reactions use the shared existing StoichiometricReaction.convert/conversion_heat_j contract. Initial Fe3O4=.4mol and H2O=1mol; supplied reduction/oxidation extents are.15mol at1000K. Returned solids match the starting composition, H2=.15mol,O2=.075mol, and steam is.85mol. The sum equals the net water-splitting enthalpy at the same T/P. This is finite prescribed isothermal calorimetry, not a prediction that the two reactions occur at that temperature. No reaction clock, equilibrium yield, actual cycle efficiency or hardware heat recovery is claimed.

The nonisothermal case uses existing product-temperature root finding: reduction extent.05mol, initial Fe3O4=.4mol/steam=.6mol at800K, with heat independently evaluated at the target1120K/200000Pa. No duplicate heat or trajectory solver is present.

| Deliberate rejected input | Retained reason |
|---|---|
| selected FeO(s) native fit, wider host envelope | State exceeds selected native species thermochemistry fit bounds |
| pressure domain | Pressure is outside the declared mechanism domain |
| infinite/nonphysical input | temperature must be finite and numeric |
| unrelated formation zero | Every phase needs the same explicit formation-energy reference |
| missing volume evidence | Declare density evidence for every solid and no other phase |
| finite inventory exceeded | Extent exceeds a finite reactant/product inventory |
| source definition mutation | Native phase definition changed; rebind its thermochemical evidence |
| owned runtime parameter mutation | Native phase definition changed; rebind its thermochemical evidence |
| actual native atomic-weight mismatch | Phase element atomic-weight bases differ |
| alternative actual native gas phase pointer | Reused native gas caloric binding changed; rebind its evidence |
| reused gas provider _indices binding | Reused native gas caloric binding changed; rebind its evidence |
| reused gas provider species binding | Reused native gas caloric binding changed; rebind its evidence |
| reused gas provider mechanism_basis binding | Reused native gas caloric binding changed; rebind its evidence |
| reused gas provider basis_id binding | Reused native gas caloric binding changed; rebind its evidence |

| Verification gate | Pass |
|---|---|
| actual native phases and existing gas enthalpy provider | True |
| native Mixture extensive H error <1e-8 J | True |
| independent native H-U-PV error <1e-8 J | True |
| solid native pressure correction error <1e-8 J/mol | True |
| gas h pressure independence <1e-9 J/mol | True |
| native Cp finite-difference error <1e-8 relative | True |
| finite two-stage mass and returned oxide inventories close | True |
| finite two-stage sum equals net water thermochemical heat <1e-8 J | True |
| existing product-temperature solve roundtrip <1e-8 K | True |
| native state/composition reuse resets <1e-10 J/mol | True |
| source objects are independent native copies | True |
| actual native alternative gas pointer and metadata binding guarded | True |
| all fourteen invalid/domain/reference/parameter probes rejected | True |
| host/test/script/docs and reused contracts unchanged | True |
| native sources/license/binary unchanged | True |
| new host inputs are LF text | True |

Every actual source/owned native definition is fingerprinted separately and checked exactly per query. Native reconstruction may alter notes/unit representation with audited tiny roundtrips; it does not merge their identities. State/composition reuse is reset. Source and owned objects, copy audits, factory parameters and explicit density evidence remain inspectable. Actual native gas/solid APIs supply the property values; no phase or property field is fabricated.

This generic constitutive bridge does not itself add a new reaction/cycle family or imply measured iron-cycle validation. Phase-stable oxide data/EOS, achievable extent and kinetics, carrier loss/sintering, gas separation/vacuum work, heat exchange/solar input, operating clock and independent experiments remain receiving requirements. Fit bounds are not stable-phase limits. There is no inferred liquid phase, evolving hydrogen spin EOS or arbitrary CoolProp energy-zero substitution.

Primary sources: [native thermo API](https://cantera.org/3.2/python/thermo.html), [versioned condensed-species provenance](https://github.com/Cantera/cantera/blob/v3.2.0/data/nasa_condensed.yaml), [NASA TM-4513](https://ntrs.nasa.gov/citations/19940013151). Cantera implementation is BSD-3-Clause; NASA's primary record identifies public distribution and US-government public use. Upstream thermochemical provenance and software rights remain distinct.

## Source fingerprints

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/cantera_caloric.py | 1b1cad4e3592143c9c103ec5870453677c034e68e953b16884f4b9b3184e672d | 1b1cad4e3592143c9c103ec5870453677c034e68e953b16884f4b9b3184e672d |
| tests/test_cantera_caloric.py | e58f794756cf445265cba982d96ea94113d4833601695ff934cb38d027e3d7ba | e58f794756cf445265cba982d96ea94113d4833601695ff934cb38d027e3d7ba |
| scripts/check_cantera_caloric.py | 86f6777730765063f5fe9a287022190e1d52fcdeff7727cfb9eebc6a07c8f60d | 86f6777730765063f5fe9a287022190e1d52fcdeff7727cfb9eebc6a07c8f60d |
| docs/MULTIPHASE_CALORIMETRY.md | 974d56ce3fac9778366fb8344839e4b6e301ebbcf0e25496ffbb141221e05c37 | 974d56ce3fac9778366fb8344839e4b6e301ebbcf0e25496ffbb141221e05c37 |
| src/h2physics/adapters/cantera.py | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 |
| src/h2physics/adapters/cantera_thermo.py | f5bf30b7536c432fd84f9b7c4b81a72949dc936a9662a7c89f15ea8a62e8d027 | f5bf30b7536c432fd84f9b7c4b81a72949dc936a9662a7c89f15ea8a62e8d027 |
| src/h2physics/adapters/cantera_multiphase.py | 28537882b48d67239a8b96694c6bae8699231c084e517d0513587d626147f5dc | 28537882b48d67239a8b96694c6bae8699231c084e517d0513587d626147f5dc |
| src/h2physics/adapters/cantera_volume.py | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 |
| src/h2physics/reactions.py | 3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35 | 3748b88bd70a2c0572faa32fd83be8c43a47b124d92dd905c1923d47963caf35 |

| Installed input | Begin SHA256 | End SHA256 |
|---|---|---|
| nasa_condensed.yaml | ae1756efa10f41fb7050cb6a22fcda8e20c2cbd337a093509ada3e57341aeeb9 | ae1756efa10f41fb7050cb6a22fcda8e20c2cbd337a093509ada3e57341aeeb9 |
| h2o2.yaml | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 |
| Cantera license | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb |
| Cantera compiled binary | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d |

| Phase | Source native definition | Owned native definition |
|---|---|---|
| Fe3O4 | 286b09d0ab9d4a8d38b38cac7959ce6d085e6201ce4eb0b070d3548c40b709d5 | 2263d7cabbd646df5dae641a32525f8fdea426c08bb87c78da54030b60d76974 |
| FeO | a4840413f4a54b3510c5ecb8bc1d156536a16f2cbf0f117ba07cb1f08cdab56b | 2b675c472dd49406147c16987434bdf0c5bb64a26cc5eb44e2140b9591b081e9 |
| gas | 397766ba113ef90eeed17015730c2fc5190bfb0f1359fd6a61fb8fc4a7df6d42 | 787b99b4fbcfe871c9fb16a06b74945a35d8998adf89957b7dc27877104356cd |
