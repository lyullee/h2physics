# Finite gas / hydride inventory verification

Reproduce: `python scripts/check_finite_hydride.py` with the thermo extra. The source tests additionally use native Cantera constant-cp H2 for an independently derived finite-gas isothermal loading limit and the ideal-gas DeltaU=RT-DeltaHdes check.

Native CoolProp 8.0.0; SciPy 1.18.1; nine complete integrations including three refinements, 3.99916 s local wall time. Actual native property objects and actual SciPy OdeResults are retained. No gas EOS or kinetic correlation is duplicated; the existing HydrideKinetics/VanthoffPlateau/ArrheniusRate are composed.

All coefficients below are authored synthetic verification inputs, not fitted to an alloy: 0.002 kg H2 capacity; solid C=1000 J/K; DeltaHdes=24000 J/mol H2 at 300 K, 100000 Pa; DeltaS=80 J/(mol H2 K); absorption/desorption rates 0.01/0.02 s^-1 at zero activation energy; free gas volume 0.005 m3; gas-solid conductance 10 W/K; no ambient conductance. Normal and para fluids keep separate native caloric references. Default absorption starts at x=0.1, both temperatures 300 K and gas pressure 300000 Pa, absolute clock [100,200] s. The declared numerical envelope is 200-600 K /1000-1e7 Pa, not an experimental material envelope.

Bound-H energy per mole is native h_H2,ref minus DeltaHdes. Gas/solid interface enthalpy appears with opposite signs, and nominal reaction heat is diagnostic only: it is not added again to total U. At reference, closed absorption DeltaU=Pv_mol-DeltaHdes, including the pressure-work distinction from the isobaric reaction enthalpy. Condensed-phase PV and loading-dependent solid sensible heat are neglected. The constant-DeltaH plateau is matched at the reference only; full temperature-dependent free-energy/caloric consistency remains future qualification.

| Quantity | Observed value |
|---|---:|
| Closed uptake final x / gas mass | 0.439688003642 / 0.000530772882644 kg |
| Closed uptake final solid / gas T | 307.208113794 / 307.095779511 K |
| Closed uptake final pressure | 134561.004952 Pa |
| Reference DeltaHdes / absorption DeltaU | 24000 / -21504.2003643 J/mol H2 |
| Maximum closed mass / transfer defects | 2.16840434497e-19 / 1.19262238973e-18 kg |
| Maximum gas/solid/total-U defect | 9.7998054116e-10 J |
| Independent native PT reconstructed mass / U drift | 4.33680868994e-19 kg / 9.7747943073e-10 J |
| Fine nominal sorption heat, not added twice | 8088.29105642 J |
| Desorption transferred H2 | -0.00027123148397 kg |
| Positive gas-floor termination time | 101.821563741 s |
| Isothermal total thermostat heat / sampled difference | -7399.15293137 / -0.00179909169219 J |
| Two refinement-pair fraction / solid T / P differences | [1.27675647831893e-15, 3.2751579226442118e-15] / [6.252776074688882e-13, 5.684341886080801e-13] K / [2.1653249859809875e-08, 1.7462298274040222e-09] Pa |

| Gate | Pass |
|---|---|
| closed total hydrogen drift <1e-13 kg | True |
| independent uptake gas/solid ledger defects <1e-13 kg | True |
| each gas/solid/total-U/integrated-state defect <1e-5 J | True |
| independent native PT total mass/energy drift <1e-13 kg /1e-5 J | True |
| reference absorption DeltaU equals native Pv_mol-DeltaHdes <1e-8 J/mol | True |
| absorption warms and consumes finite gas, below complete loading | True |
| same model desorbs, returns H2 and cools solid | True |
| prescribed 400 W reverses uptake with independent 32000 J input | True |
| gas floor localized before requested end, retained positive inventory | True |
| zero kinetic limit remains stationary | True |
| isothermal native thermostat independent sampled heat <0.01 J | True |
| 1/0.5/0.25 s refinement fraction/T/P <1e-8 /1e-5 K /0.01 Pa | True |
| explicit normal/para identities retained | True |
| source fingerprints unchanged during native calculation | True |

This is software/numerical verification of one finite lumped level, not alloy calibration or measured validation. Acquired AB2 shell-temperature data still lack resolved pressure/MFC units and bases, free gas volume/porosity and bed-vs-shell observation roles. None of those values or mappings is inferred here. No raw/normalized external data, mechanism or third-party implementation is included.

The model is closed to external H2 ports and has one uniform gas state plus one solid temperature. Porous transport, powder expansion, wall storage, loading-dependent heat capacity, full free-energy equilibrium, connected process ports and independent apparatus qualification remain receiving/research work. Trial fraction/phase/domain violations fail without clipping. A positive gas-floor root is retained as termination, not advertised as an exact empty-bed or exhausted-gas event.

Primary context: [Brown et al. 2006](https://doi.org/10.1115/FUELCELL2006-97140), [Krane et al. 2021 primary preprint](https://arxiv.org/abs/2107.06095), [Leachman et al. hydrogen EOS](https://doi.org/10.1063/1.3160306), [CoolProp native API](https://coolprop.org/coolprop/LowLevelAPI.html). Conservation coupling, reference derivation, fixtures and tests are original; no source coefficient table, figure, implementation or worked example was copied.

## Source fingerprints

- `src/h2physics/storage/finite_hydride.py`: `9fa148a4b1680bf2deccca71cad4d518973bd2c9a6b146bd7a48764ce86ea989`
- `src/h2physics/storage/hydride.py`: `68948ff71692ab006a43e684d5e8c910d7a6effe63943263be4886747c624e0f`
- `src/h2physics/thermo/coolprop.py`: `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b`
- `tests/test_finite_hydride.py`: `4e0c8c819181f1487ccb046cb231d1abee93439da4e94ab272a5b0037a8af78e`
- `scripts/check_finite_hydride.py`: `18fb8049df009fdd5f4b2b527653cf61c1a76e26fa7920c135ccd0b6a7b181cb`
