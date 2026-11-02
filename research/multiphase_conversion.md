# Native gas/solid equilibrium conversion reference

Reproduce: `python scripts/check_cantera_multiphase.py` with optional Cantera3.2.

Actual Cantera3.2.0; five accepted equilibrium/reference solves plus native failure probes and independent audits took 2.42157s. No native source or thermochemical table is bundled or modified.

Original numerical feeds use SI mol at101325Pa. Rich case750K: gas CH4=.6,H2O=.12,CO2=.08,Ar=.2mol, graphite0mol. Steam-carbon case1100K: gas H2O=.7,CO2=.15,H2=.05,Ar=.1mol and graphite.18mol. The independent CO/CO2 subset case starts from1mol CO and zero graphite at800K. These compositions are authored verification inputs, not native worked examples, biomass/catalyst measurements or apparatus data.

The native engine is ct.Mixture, with one ideal-gas phase and neutral fixed-stoichiometry constant-volume solids. Native amounts are kmol; the public amounts/element counts are mol. H/U/G use J, S uses J/K and chemical potentials use J/mol. Thermochemical source identities and the caller-declared common NASA formation/third-law reference are retained per phase; the adapter cannot prove a caller's provenance claim. H2 spin is mechanism-unresolved, with no CoolProp/ParaHydrogen energy-zero substitution.

| Case | Constraint | Final T K | Gas mol | Graphite mol | H2 mol | CO mol | Heat into J | PV work out J |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| carbon appearance | TP | 750 | 1.18854670492 | 0.277951147207 | 0.36941724281 | 0.00767973191034 | 15954.3058928 | 1175.90500416 |
| carbon disappearance | TP | 1100 | 1.17997143849 | 0 | 0.283957639764 | 0.125985214769 | 22629.2292814 | 1645.90095958 |
| adiabatic conversion | HP | 799.436055093 | 1.11667476342 | 0 | 0.24818699632 | 0.0351626119367 | 0 | -1723.60581117 |

TP specifies a thermostat at constant pressure: Q_into=H_final-H_initial, with PV work out=P*(V_final-V_initial). HP specifies adiabatic constant-pressure equilibrium: Q=0, total H is retained. Independent first-law checks use delta_U+P*delta_V-Q. Formation energy already belongs to native H/U; no separate reaction heat is added. These finite equilibrium heats are J, not a measured rate, fire power or cycle efficiency.

| Case | Mass residual kg | Max element residual mol | H-constraint residual J | First-law residual J | Populated max affinity/RT |
|---|---:|---:|---:|---:|---:|
| appearance | -3.46944695195e-18 | 8.881784197e-16 | 0 | 3.63797880709e-12 | 5.47258784093e-09 |
| disappearance | 3.46944695195e-18 | 5.55111512313e-17 | 0 | -2.54658516496e-11 | 3.48929955196e-08 |
| HP | 1.73472347598e-17 | 1.11022302463e-15 | -5.55947190151e-06 | -5.55952738068e-06 | 9.41965570813e-09 |

Chemical-potential auditing independently fits elemental potentials to populated feasible species and checks mu-A.T*lambda. Species containing initially unavailable elements are excluded from this fit. Trace cutoff=max(1e-14mol,1e-10*initial totalmol) is explicit; omitted trace species are counted, not declared individually converged. Feasible pure solids below that amount threshold also require nonnegative formation affinity. A populated gas phase is required; an absent-gas tangent-plane stability calculation is not implemented.

Disappeared-carbon formation affinity/RT=5.14647142419. Boudouard native carbon=0.474873294054mol, independently derived extent=0.474873294054mol, error=2.22044604925e-16mol. Pure native chemical potentials at the same T/P define the mass-action constant; the closed-form finite-extent oracle does not call an equilibrium solver. Gas-only TP comparison preserves elements, not the graphite-versus-atomic-carbon feed enthalpy; max X error=4.28842517053e-11. HP rtol1e-10/1e-12 finalT difference=2.32594970839e-07K.

| Retained failure probe | Native returned | Final snapshot present | Actual partial/native T K | Original cause |
|---|---|---|---:|---|
| one-native-step-budget | False | False | 750 | CanteraError: ******************************************************************************* CanteraError thrown by MultiPhase::equilibrate: VCS solver failed. Return code: -1 ******************************************************************************* |
| zero-total-carbon-solid-candidate-HP | False | False | 750 | CanteraError: ******************************************************************************* CanteraError thrown by vcs_MultiPhaseEquil::equilibrate_HP: No convergence for T ******************************************************************************* |
| completed-native-HP-outside-host-envelope | True | True | 799.436055093 | ValueError: Temperature is outside the declared mechanism domain |

The zero-total-carbon H2/O2/Ar HP case with an explicit zero graphite candidate actually fails native temperature convergence. It is not replaced by a gas-only solve, another algorithm or a removed phase. The source of this native failure has not been independently established. The returned exception preserves the real partial Mixture, phases, initial snapshot and original cause; no final equilibrium is fabricated. A separate successful carbon/steam HP solve outside a deliberately narrow host envelope preserves its completed final snapshot. Cantera documents multiphase solver limitations. HP internal trial temperatures/iteration history are not exposed by this public API; only supplied and returned states are domain-admitted here. No claim of bounded internal trial extrapolation or a certified global convergence history is made.

| Verification gate | Pass |
|---|---|
| actual native Mixture owns every equilibrium solve | True |
| all reference states pass material/constraint/chemical audits | True |
| solid appears from zero feed | True |
| initial carbon disappears with positive absent-phase affinity | True |
| independent Boudouard mass-action extent error <1e-9 mol | True |
| native gas-only no-solid TP composition limit error <1e-7 | True |
| TP heat is separate from HP adiabatic enthalpy | True |
| independent HP tolerance replay T error <1e-4 K | True |
| native solver failures retain actual mixture/cause | True |
| post-completed native domain failure retains final candidate | True |
| source phase definitions and owned native phases are independent | True |
| host/test/script/docs and reused contracts unchanged | True |
| installed thermochemical sources/license/binary unchanged | True |
| new host inputs are LF text | True |

This is an equilibrium carbon/steam gasification reference and a generic gas/pure-solid core. It does not predict reaction times, particle transport, porous char reactivity, coke kinetics, catalyst behavior, ashes, biomass conversion, a validated solid-redox cycle or full process efficiency. Solids not supplied as candidates cannot appear. No independent measured comparison has been performed. Additional phase models, charged phases, absent-gas stability and coupled boundary dynamics require separately evidenced native capabilities.

Primary references: [native Mixture API and solver limitations](https://cantera.org/3.2/python/thermo.html#cantera.Mixture), [installed GRI30 provenance](https://cantera.org/3.2/examples/input/gri30.html), [native graphite definition and NASA source references](https://github.com/Cantera/cantera/blob/v3.2.0/data/graphite.yaml), [NASA thermochemical coefficient reference](https://ntrs.nasa.gov/citations/19940013151). Cantera BSD-3-Clause implementation rights and upstream thermochemical provenance are distinct; files remain separately installed, and no mechanism or printed coefficient table is redistributed here.

## Source fingerprints

New module/test/script/docs were checked as LF-only bytes; report is written with explicit LF.

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/cantera_multiphase.py | 28537882b48d67239a8b96694c6bae8699231c084e517d0513587d626147f5dc | 28537882b48d67239a8b96694c6bae8699231c084e517d0513587d626147f5dc |
| tests/test_cantera_multiphase.py | a135c4700b9e990e6d441ed9f2dca1f7e3b3ef7835a95c720ba76f35d4df3e97 | a135c4700b9e990e6d441ed9f2dca1f7e3b3ef7835a95c720ba76f35d4df3e97 |
| scripts/check_cantera_multiphase.py | 9d743e632afd2219a88ca1e294ec8456febdec23edd32ad0666a92aaf6d6e8a1 | 9d743e632afd2219a88ca1e294ec8456febdec23edd32ad0666a92aaf6d6e8a1 |
| docs/MULTIPHASE_CONVERSION.md | 391dda1ce37e29521720758cd155d6508486534abbd0e9ccd6ba913308c974cf | 391dda1ce37e29521720758cd155d6508486534abbd0e9ccd6ba913308c974cf |
| src/h2physics/adapters/cantera.py | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 | 19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184 |
| src/h2physics/adapters/cantera_volume.py | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 | e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1 |

| Installed input | Begin SHA256 | End SHA256 |
|---|---|---|
| gri30.yaml | 06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345 | 06650b1e0ee0012f6903d5328b1bb218cb6007d07f8ebe375d18f24811039345 |
| graphite.yaml | 6074b6dd691785403dee1eeebf8e583b747681c34a148746bab2256282939cbd | 6074b6dd691785403dee1eeebf8e583b747681c34a148746bab2256282939cbd |
| Cantera License.txt | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb | e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb |
| Cantera compiled extension | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d | 00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d |

| Phase | Source native definition | Owned native definition | Numeric roundtrip count /max relative |
|---|---|---|---|
| gas | c44de7b10143b80c53f4918a5c6d8cb7cac26d40e300e8b33a5b87d1d627e6b4 | ea099ee997c16d13758d541a2fae5a60dc1ca9cb8b51248e538dfa148bd6db22 | 103 /2.27738056333e-16 |
| carbon | f91b22b60a4ab34988d7e134669328ffd8bcf7c0067d5d7f11d8eadcdd322c2c | 3b4791e0bc5a3678ca64084cd99d9fd412f221d9ea3884dd35b0fc5a5545361b | 0 /0 |
