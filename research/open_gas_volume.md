# Native open gas volume verification

Reproduce: `python scripts/check_cantera_volume.py` with the optional chemistry extra.

Native engine: Cantera 3.2.0; actual ExtensibleIdealGasReactor / ReactorNet / Reservoir / MassFlowController / Wall objects. No mechanism, raw experiment or native source is bundled.

The original synthetic case starts at absolute t=100 s: 0.5 m³ N2, 400 K, 101325 Pa; H2 feed 420 K with 0.001[1+0.5(t-100)] kg/s; fixed extraction 0.0004 kg/s. The wall has A=1 m², U=2 W/(m² K), Tenv=450 K and signed prescribed flux 5 cos(t-100) W/m². Output ends at 101 s; authored callbacks explicitly support [100,102] s, including native trial times.

Only native boundary-integral rows are appended. Physical temperature, mass, volume and species equations and CVODES integration remain native. The ledgers are integrated numerical estimates, not exact quadrature.

The pure-vent check uses native SV conservation independently of the physical integration. The feed-only check uses an independent authored source integral and native UVY inversion. Constant-cp analytic feed, vent, mixing and wall limits are additional unit tests.

Each appended energy integral uses 1e+06 J per native state unit; returned integrals and residuals remain SI J. Mass/species ledgers remain kg. Native physical rows, rtol/atol and every conservation/analytic acceptance budget are unchanged. Use `--energy-ledger-scale-j 1` to retain the original unscaled numerical reference. That reference can emit native initial `t+h=t` step-roundoff warnings at the absolute 100 s start; no warnings, clocks, solvers or energy references are suppressed or reset. The constant-feed test compares scaled/unscaled states and SI integrals against the same budgets. Measured before/after timings and warnings are in docs/OPEN_GAS_VOLUME.md.

| Quantity | Observed value |
|---|---:|
| Independently integrated source mass | 0.00125 kg |
| Coupled final mass | 0.427594138551 kg |
| Coupled final T / P | 407.429373995 K / 107309.350365 Pa |
| Coupled final H2 mass / mole fraction | 0.00292205613069 / 0.0391298984969 |
| Maximum mass / species residual | 3.30031141305e-16 / 9.0483176507e-15 kg |
| Maximum energy residual | 1.64064275054e-07 J |
| Feed-only independent native T / P error | -6.84104861648e-09 K / -1.80861388799e-06 Pa |
| Vent-only independent native T / P error | -2.72848410532e-12 K / -6.98491930962e-10 Pa |
| Independent sampled wall integral difference | -7.26798702999e-07 J |
| Independent sampled outlet integral difference | 1.54039490496e-07 J |
| Coarse/fine final max(T, P/1000) difference | 2.02987848752e-10 |
| Fine actual callback clock bounds | (100.0, 101.00295329345352) s |

Four-run native replay plus independent native inversions: 4.50005 s wall time on this run; timings are workload-sensitive.

| Gate | Pass |
|---|---|
| native nonreacting finite volume and original objects retained | True |
| independent linear source integral <1e-11 kg | True |
| independent final mass <1e-10 kg | True |
| native integrated mass and species residuals <1e-10 kg | True |
| native integrated energy residual <0.001 J | True |
| sealed feed independent native UVY T <1e-6 K and P <0.001 Pa | True |
| adiabatic vent independent native SV T <1e-6 K and P <0.001 Pa | True |
| independent sampled wall and outlet integrals <0.0001 J | True |
| 0.02/0.005 s final T and P/1000 agreement <1e-6 | True |
| actual absolute native clock preserved inside declared support | True |
| source hashes unchanged during computation | True |

These are software and numerical verification results. The well-mixed thermodynamic volume does not predict spatial concentration, stratification, ignition, explosion or outdoor dispersion. HyRAM+ remains the preferred high-pressure gaseous-hydrogen dispersion provider and SLABx-LH2 the preferred LH2-origin provider. No measured ventilation pressure/flow clocks have been inferred or aligned. The current H2 thermochemistry is mechanism-specific and spin-unresolved, with native formation-energy reference; there is no automatic CoolProp/normal/para energy conversion.

Feed reservoir thermo is fixed within one run. Finite upstream supply, bidirectional ports, discontinuous commands, exact depletion/event localization, source-state changes and wall storage remain future work. Callbacks may delegate the existing shared nozzle using a separate native frozen-mixture phase; this reproduction instead declares prescribed extraction and does not claim a solved vent opening.

Primary references: [native ideal-gas control volume equations](https://cantera.org/3.2/reference/reactors/ideal-gas-reactor.html), [native extension/flow/wall APIs](https://cantera.org/3.2/python/zerodim.html), [installed mechanism provenance](https://cantera.org/3.2/examples/input/h2o2.html). Original adapter, cases and tests; separately installed Cantera retains its BSD-3-Clause terms and upstream species provenance.

## Reproduction fingerprints

- Installed h2o2.yaml SHA-256: `0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4`
- Native enclosure thermo SHA-256: `b67a71ce877eaa8893def72ee0f7dcbb28195cdfacd66810e1ce9ec54e07a387`
- `src/h2physics/adapters/cantera_volume.py`: `e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1`
- `scripts/check_cantera_volume.py`: `12f86dca47f0a8a45ea3f0b3f3854644b7ad779f7c2eada949fbae32a85259df`
- `tests/test_cantera_volume.py`: `b609ceccb7856dad879874cb91974f42c812d087296eb9ceea73f5b1f96abf59`
