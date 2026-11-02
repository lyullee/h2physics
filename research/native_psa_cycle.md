# Native warm scheduled multibed PSA

Original authored native/software verification. No acquired isotherm, measured apparatus fit or industrial purification rating is claimed. Native source MIT revisiona26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6 remains separately installed. Reproduce: `python scripts/check_psa_cycle.py`.

Four completed native-runner campaigns in134.514079s; native CSS campaign122.971305s. Every operation is integrated by the actual native runner/BDF/Jacobian machinery. Host Python objects are serialized only inside an explicit managed ignored workspace, which is removed after native artifacts are read and verified. No user JSON/HTTP protocol, copied solver, monkeypatch or alternate bed model is required.

Authored2bed/3cell/H2-N2 loading-LDF fixture:0.15m length,0.03m diameter, void0.4,300K; initial1.2bar(abs), feed3bar/.001mol/s/.8H2-.2N2, product boundary1.5bar, tail1bar. Linear native valve gains0.001mol/(s bar), requested purge/feed0.1 with native available-product/capacity limitation. Adsorbent capacities[.3,.8]mol/kg, affinities[.02,.08]/bar, binding[2000,3000]J/mol, LDF[.2,.1]/s are authored, not source material coefficients. Native six-second Skarstrom schedule uses four global slots1/2/1/2s. Each bed alternates FP/AD/BD/P with its companion on the same clock.

Startup uses2cycles, rtol1e-8/maxstep0.1s/native SciPy-FD Jacobian; fine usesrtol2e-9/0.05s. CSS usesnative complex-step Jacobian, rtol1e-7/0.2s, fixed maximum80cycles, minimum4cycles, CSS tolerance1e-4 and3consecutive cycles. All use native augmented species/enthalpy/ambient ledgers and strict0 accepted negative tolerance. Phase scope is warm ideal-gas without condensation; H2 spin is unresolved on this native constant-Cp reference. Pressure outputs are Pa absolute; native input pressure keys are explicitly bar absolute.

The gas energy is native Cv*T from0K, transported enthalpy Cp*T from0K, adsorbent/wall sensible storage is referenced to298.15K and binding storage is negative. This is not CoolProp/Cantera formation energy. Native vacuum-work diagnostics are utility estimates and are not added again as bed heat. Internal purge and equalization are not external feed/product streams.

| Quantity | Observed |
|---|---:|
| Maximum component defect mol | 1.02695629778e-15 |
| Maximum signed total-energy defect J | 7.48396115524e-07 |
| Closed native state defect | 0 |
| Product integral refinement relative | 9.74009211963e-08 |
| Final-cycle purity refinement absolute | 4.35679503585e-09 |
| Final cell-pressure refinement Pa | 0.00983024729067 |
| Startup last-cycle H2 product fraction | 0.836177032223 |
| Native CSS completed cycles | 56 |
| Native CSS worst scaled state change | 7.38884296129e-05 |
| Native CSS final H2 product fraction | 0.795325772674 |
| Native CSS final H2 export/feed ratio | 0.352604952911 |

The authored CSS product can be poorer than the supplied0.8H2 feed. This is retained, not repaired or optimized into a purification claim. Startup enrichment is not evidence of CSS performance. The overall startup-window ratio is not feed-origin tracer recovery; initial bed inventory can contribute to exports. Only the native-verified final CSS cycle is labeled recovery here.

| CSS final-cycle ledger | Component mol or energy J |
|---|---|
| Feed(H2,N2) | [0.0044744303928575535, 0.0011186075982143884] |
| Net product(H2,N2) | [0.0015777063179772954, 0.000406017046943416] |
| Tail(H2,N2) | [0.002896717475869892, 0.0007121912675308664] |
| feed_enthalpy_j | 48.6594305223 |
| product_enthalpy_j | 17.2714995549 |
| tail_enthalpy_j | 31.411408614 |
| ambient_heat_j | -0.0112457584402 |
| vacuum_work_j | 0.18237473742 |

| Gate | Pass |
|---|---|
| actual native runner/checkpoint/schedule and separate native audit Network retained | True |
| two physical beds/four global slots with finite pressure/composition changes | True |
| independent global component inventory defects <1e-8mol at every retained slot | True |
| independent U with signed boundary enthalpy and ambient defects <1e-4J | True |
| closed-valve native exact stationary limit <1e-9 state units | True |
| zero product/feed keeps purity and recovery undefined | True |
| native max-step/rtol refinement product integrals <1e-5relative and purity <1e-6 | True |
| refined endpoint cell pressures differ <2Pa | True |
| startup retained without CSS/recovery claim | True |
| actual native CSS criteria and three-cycle streak achieved within fixed80cycle limit | True |
| CSS purity/recovery use final-cycle molar exports only <1e-12 | True |
| CSS still preserves native closed release/experimental-qualification gate | True |
| H2-specific recovery requires actual native H2 reporting; N2 reporting rejected | True |
| actual native and host/test/script begin/end source identities unchanged | True |

## Actual object and integration limits

Pinned runner.run_case accepts file paths only and constructs its Network/OdeResult internally. No public or private standalone slot-integrator helper was found; the only solve_ivp call is inside run_case. The host repeatedly uses its publicstep_budget=1/cycle_budget=1/resume interface to retain the actual hash-checked native checkpoint after each slot. It does not reproduce schedule stepping or integration. The returned audit_network is a distinct actual native Network for PsaDynaBed admission/snapshots and inventory audits, not the original integrator instance. original_integrator_objects_available=False is explicit; native callable, raw return records, state arrays, schedule and checkpoint metadata are retained. Native-generated temporary source ZIP is neither loaded nor bundled and is removed with the workspace.

Receiving request018 must expose an object-based native runner accepting/returning the actual Network, state, native solver results and accepted-step/slot callbacks, explicit clock, stream and conservation contracts. The native mean_stream bridge currently requires CSS plus independent resolution/source/release qualifications; it is not invoked or bypassed here. Numerical CSS does not authorize a downstream release stream, manufacturer purity, plant capacity or experimental validation. Product receivers, PR thermodynamics, partial-pressure pellet states, cryogenic adsorption, arbitrary source clocks and source-qualified material/process parameters remain outside this first level. No receiving repository was changed or contacted.

Primary context: [Skarstrom original cycle patent](https://patents.google.com/patent/US2944627A/en), [native PSA-Dyna](https://github.com/lyullee/psa-dyna/tree/a26a8ef687c90cd4a5c18d38aaa4209ea5c5dcd6). Original composition and verification inputs contain no copied native implementation, published parameter table or source experimental records.

## Begin/end fingerprints

| Native source | Begin SHA256 | End SHA256 |
|---|---|---|
| ordered-native-Python | 171743500492bfa7c60b5a1aedc384508885116ab91f6a14327c802284187966 | 171743500492bfa7c60b5a1aedc384508885116ab91f6a14327c802284187966 |
| native-runner-engine | 28d12b9e164f339b464b5e06b00bed8eba97b94524d1b3b666fdab4e4383a64c | 28d12b9e164f339b464b5e06b00bed8eba97b94524d1b3b666fdab4e4383a64c |
| core.py | 104686045b7ae61ead32a0978f5fd58d801f3a599225c4070ffe1eb4e0023571 | 104686045b7ae61ead32a0978f5fd58d801f3a599225c4070ffe1eb4e0023571 |
| runner.py | 9926c0556e9537be136709bf44ff9a6f8bc4c9f6962831e3cfc191eaeb6ad4b4 | 9926c0556e9537be136709bf44ff9a6f8bc4c9f6962831e3cfc191eaeb6ad4b4 |
| schedules.py | cbd520992543b6c4d564d84c12a7ea2f94155f82789bdec2c50280b14ff63fdc | cbd520992543b6c4d564d84c12a7ea2f94155f82789bdec2c50280b14ff63fdc |
| numerics.py | c9169612c876b5095bd57392b2611ae0e992055ad7582ac79de43ef6e6830fd4 | c9169612c876b5095bd57392b2611ae0e992055ad7582ac79de43ef6e6830fd4 |
| vectorized.py | 0571c7a07ab5b245a18a47cc0df7fee4067daeded607acfe1a8cdc3fc97cfabe | 0571c7a07ab5b245a18a47cc0df7fee4067daeded607acfe1a8cdc3fc97cfabe |

| Host source/test/replay | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/psa_cycle.py | 3af66490b307c273a9669ac80c40f11d9fbac1ce2aa3bcb8546128ae417f9921 | 3af66490b307c273a9669ac80c40f11d9fbac1ce2aa3bcb8546128ae417f9921 |
| tests/test_psa_cycle.py | 2650bbc767d57380dfbaebeb5c4fd434da713de04a91b92cd080ee7f4ac4c204 | 2650bbc767d57380dfbaebeb5c4fd434da713de04a91b92cd080ee7f4ac4c204 |
| scripts/check_psa_cycle.py | c56ff124a1807f293aa71b6f30c2bae42cda749bba6e51487af3e51d688aa3d7 | c56ff124a1807f293aa71b6f30c2bae42cda749bba6e51487af3e51d688aa3d7 |
| src/h2physics/adapters/psa.py | 9a32b964062ba4307eea42f870c18d73ec7e7c36f3b7f8f5c0c4a6aed5601d3e | 9a32b964062ba4307eea42f870c18d73ec7e7c36f3b7f8f5c0c4a6aed5601d3e |
| src/h2physics/adsorption.py | e2eb29d0cefa5b1885b08585fafa73dd05e404a033018a881ed2ad797d2f7796 | e2eb29d0cefa5b1885b08585fafa73dd05e404a033018a881ed2ad797d2f7796 |
