# Native finite cryo-compressed storage

Original synthetic software/native-conservation verification, not a manufacturer map, storage rating, material calibration or independent apparatus validation. Reproduce: `python scripts/check_cryo_compressed.py`.

LH2DT0.1.2 pinnedb2f276333c1b1793c39f25763703d196d36742ec; CoolProp8.0.0, SciPy1.18.1; 15 completed native driver integrations (12 accepted audited traces, 3 rejected post-run audit regressions) in2.848788s.

Fixed0.01m3 homogeneous fluid; wallC100J/K, ambientUA1W/K, fluid/wallUA100W/K. Initial20MPa(abs)/25K with own-fluid initial wall. An explicit callback cancels the ambient term and supplies net1000W into the wall for100s on operation clock100–200s. This manufactured forcing is an analytic verification boundary, not a physical insulation or refrigeration rating. The supplied pressure-protection set100MPa/reseat99MPa is not reached in these sealed runs; receiver19MPa25K and effective area1e-8m2 are explicit. No tank ODE/EOS/nozzle/event code was replaced.

Declared authored domain20–350K,2–120MPa(abs), positive inventory floor0.01kg; cryogenic initialT<=80K and initialP>=2*own-native-criticalP. Allowed single-fluid classes are supercritical_liquid/supercritical/supercritical_gas. Solid exclusion remains a caller-evidenced application premise. Crossing Tcritical while P>Pcritical is not passage through the critical point or a two-phase transition. No normal/para/ortho conversion is inferred.

| Fluid | Initial mass kg | Initial rho kg/m3 | Native Tcritical K | Final fluid T K | Final P Pa(abs) | Final wall T K |
|---|---:|---:|---:|---:|---:|---:|
| Hydrogen | 0.825991731953 | 82.5991731953 | 33.1443326883 | 43.0295676153 | 39470064.0181 | 52.858337868 |
| ParaHydrogen | 0.825985934503 | 82.5985934503 | 32.9378550689 | 42.862964938 | 39449683.4503 | 52.6930267248 |
| OrthoHydrogen | 0.826326994491 | 82.6326994491 | 33.2198146217 | 43.1632403199 | 39788517.2455 | 52.9920779418 |

| Independent defect | Maximum |
|---|---:|
| mass_conservation_kg | 1.07925550007e-16 |
| energy_conservation_J | 3.34694050252e-10 |
| PT_mass_kg | 1.66677782687e-12 |
| PT_energy_J | 1.42788849189e-07 |
| Prho_energy_J | 1.0687392205e-05 |
| Prho_temperature_K | 2.10174988524e-09 |

Exact external-power total-energy error4.36557456851e-11J. Independent finite-fluid/wall equilibrium28.3784055575K; final maximumT error8.87823148332e-12K. Para-H2 coarse/medium versus fine differences(Tfluid K,P Pa,Twall K):[(4.4204043092577194e-08, 0.04793946444988251, 2.5591903138888483e-06), (2.067686466489249e-09, 0.002242445945739746, 1.197145991227444e-07)].

Independent native EOS inversion gates (1e-10kg,1e-4J,1e-7K) are separate from physical inventory conservation gates(1e-12kg,1e-5J,relative1e-10). A direct-Prho flash can return approximately2e-9K numerical temperature roundtrip error here, corresponding to approximately1e-5J; that is not a tank energy defect or an EOS-accuracy claim.

## Pressure events and finite inventory

Actual existing Lh2dtReliefTankDriver, transactional native PressureReliefValve and shared HomogeneousIsentropicNozzle are reused. Separate6s windows use set21MPa/reseat20.5MPa and the same 19MPa receiver; after opening real finite bulk withdrawal continues. A pressure event is not treated as a stop, valve isolation or vapor-selective pickup. Endpoint bracketing requires resolved first crossings and does not detect arbitrary hidden within-step nonmonotonic events.

| Native max step s | Open time s | Pressure Pa(abs) | Released mass kg | Released enthalpy J |
|---:|---:|---:|---:|---:|
| 0.5 | 105.689711545 | 21000000.0004 | 5.63570462927e-05 | 14.6183834682 |
| 0.25 | 105.689725272 | 21000000.0008 | 5.63545441687e-05 | 14.6177336951 |
| 0.125 | 105.689725965 | 21000000.0006 | 5.63544181222e-05 | 14.6177009825 |

Open-time differences vs finest:[1.442059874534607e-05, 6.92903995513916e-07]s. Floor case stops at 105.745045425s, mass0.825975934503kg against declared0.825975934503kg; valve/source remains open. Positive sub-floor native trial states are allowed only to localize the existing event; the final floor residual uses the explicit1e-12kg event budget. No accepted mass is clipped.

At20MPa the25K/300K para-H2 density ratio is5.7361666813; the150kPa saturated-liquid comparison has rho69.1574817769kg/m3. The builder rejects warm300K and low-pressure initializations instead of relabeling those other storage levels as cryo-compressed.

## Completed native runs with rejected post-run audits

| Regression | Completed native end s | Failing accepted time s | Prior audited points | Failing native wall K | Retained |
|---|---:|---:|---:|---:|---|
| smooth-ramp accepted wall endpoint | 101 | 101 | 1 | 27.0048830727 | True |
| independent state_pt raises | 101 | 100.5 | 1 | 28.935431696 | True |
| independent state_prho raises | 101 | 100.5 | 1 | 28.935431696 | True |

The smooth wall power1200*(t-100)^10W case uses ambient25K, wall domain maximum26K, and a single1s native interval100–101s. All actual RK stage inputs remain inside the wall domain but the accepted endpoint exits it. The post-run error retains the completed native trace, actual failing accepted state, its time, the immutable already audited prefix, optional constructed point and original chained exception. Deliberately raised independent PT/P-rho query failures are negative error-retention fixtures; they do not substitute for native physics in the successful verification cases. Residual-gate failures retain the same fields in tests.

| Gate | Pass |
|---|---|
| three actual native spin-specific tank/state/driver objects retained | True |
| sealed cryogenic25K to above native critical T without changing EOS/ODE | True |
| closed high-pressure paths remain above critical P | True |
| independent physical mass/U+wall ledgers <1e-12kg/1e-5J | True |
| fresh native PT reconstructs inventory <1e-10kg/1e-4J | True |
| fresh native Prho reconstructs U/T <1e-4J/1e-7K | True |
| independent constant net external heat exact total energy <1e-5J | True |
| native finite wall closed-equilibrium root <1e-6K | True |
| uniform zero-net-power state and signed cooling remain physical | True |
| native1/.5/.25s refinement <1Pa/.001K | True |
| actual shared relief open events meet fixed0.001Pa/1e-8s brackets | True |
| existing pressure-event time refinement <1e-4s | True |
| positive finite floor localized without valve closure or mass clipping | True |
| warm-gas/low-pressureLH2 domains are physically distinct | True |
| post-run failure retains raw trace/state/prior prefix/cause: smooth-ramp accepted wall endpoint | True |
| post-run failure retains raw trace/state/prior prefix/cause: independent state_pt raises | True |
| post-run failure retains raw trace/state/prior prefix/cause: independent state_prho raises | True |
| native and executed host/test/script begin/end fingerprints unchanged | True |

High-pressure warming is verified for the declared authored envelope. Initial fill/cooling plant, refueling, vacuum insulation construction, pressure-vessel strength/fatigue, spatial stratification, selective phase ports, evolving spin thermochemistry, real valve capacity and measured apparatus qualification remain open. Signed wall cooling is an explicit thermal boundary, not a predicted refrigeration cycle/COP. Native phase/domain/EOS failures propagate with actual objects; no ideal-gas or alternate tank fallback is used. An accepted-step/stop-at-first-pressure API remains useful receiving work.

Primary sources: [LLNL/DOE cryo-compressed storage report](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/progress07/vi_a_6_aceves.pdf), [NIST separate hydrogen EOS](https://doi.org/10.1063/1.3160306), [native LH2DT](https://github.com/lyullee/lh2dt_models), [CoolProp native library](https://doi.org/10.1021/ie4033999). Native engine remains separately installed MIT. No third-party implementation, coefficient table or external measurements are bundled.

## Begin/end fingerprints

| Native source | Begin SHA256 | End SHA256 |
|---|---|---|
| ordered-top-level-Python | 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 | 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 |
| tank.py | b921a604a9ee27b87db41737964bfe9ea111bc66a1a0ee7a237c646fba385c22 | b921a604a9ee27b87db41737964bfe9ea111bc66a1a0ee7a237c646fba385c22 |
| valve.py | 042c9cf014d78e69a0bc59982fcf4ac8752c657572b4d9e3371cd3e22c28d9e0 | 042c9cf014d78e69a0bc59982fcf4ac8752c657572b4d9e3371cd3e22c28d9e0 |
| properties.py | 835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3 | 835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3 |

| Host source/test/replay | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/cryo_compressed.py | ec64eecaea49317dccd4c41bc743b3d2d16b19691fe498baed15ea33ceafc814 | ec64eecaea49317dccd4c41bc743b3d2d16b19691fe498baed15ea33ceafc814 |
| tests/test_cryo_compressed.py | d8254e78b98fa62784d48490b09f158e360852ce4c2580004b439da67e08e331 | d8254e78b98fa62784d48490b09f158e360852ce4c2580004b439da67e08e331 |
| scripts/check_cryo_compressed.py | e337b3a16ad5149f4f61d818230e37f46825572bd6872024721a3215a62ed5da | e337b3a16ad5149f4f61d818230e37f46825572bd6872024721a3215a62ed5da |
| src/h2physics/adapters/lh2dt_relief.py | 4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282 | 4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282 |
| src/h2physics/adapters/lh2dt_properties.py | 818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2 | 818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2 |
| src/h2physics/adapters/lh2dt.py | 0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed | 0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed |
| src/h2physics/release.py | eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45 | eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45 |
| src/h2physics/thermo/coolprop.py | d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b | d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b |
| src/h2physics/dynamics.py | d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd | d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd |
