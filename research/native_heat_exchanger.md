# Native finite two-fluid heat exchanger

## 2026-10-28 coding-only boundary increment

Status **implemented_unverified**. No native/project/model import or scientific
calculation, test/replay, example/case discovery/invocation, installation,
benchmark or job occurred. Only original installed/public source/API inspection
and AST/Ruff/LF review support this increment. Historical executed numbers below
belong to their recorded hashes rather than current source.

Native DynamicVaporizer derivatives, state advances, heat caps, one simultaneous
DynamicNetworkSimulator and existing signed heat quadrature remain the physical
owners. Added public exact native source/method provenance, original finite-side
identity/configuration/property/reference/domain seals and owner-issued
trace.require_current for deep coupling. Native EOS rho/U recovery is checked
against each actual conserved side inventory using unchanged acceptance budgets.
No new heat law, EOS, pressure-drop or RK solver was introduced.

All setup/native/post-run audit failures now retain original cause, available
simulator/network/side-node/core objects, raw returned rows, last native trial
(including an available first-side derivative if the second fails), and prior
audited point prefix. Native simulate returns all rows on success; on an internal
exception it offers no public completed-row streaming hook. That missing history
remains unavailable. Current absolute-clock projection budgets are retained and
guarded; unsupported large-epoch step loss is rejected without resetting clocks.

Four new deferred definitions in validation/cases/lh2dt_heat_exchanger.py/profile
`heat-exchanger-boundaries` cover closure, stale original results/native rows,
retained post-run topology failure and zero-conductance/clock/refinement limits.
The example defines original authored finite normal/para fluid/wall inputs,
without vendor qualification. No new family, flow topology, external bath,
spatial effectiveness or table/map validation is claimed. Final hashes follow.

### Static input fingerprints

AST/Ruff/LF/trailing-whitespace checks passed for both adapters, both examples
and both case files. The two new profiles define four cases each, eight total;
none was discovered or executed. Native source bytes were read before/after and
remain identical to the historical aggregate and individual hashes below.
Existing dependency rights/receipts are reused without installation or change.

| Current coding input | Before SHA256 | Current unexecuted SHA256 |
| --- | --- | --- |
| src/h2physics/adapters/lh2dt_heat_exchanger.py | `cdc09e3cabe738a224e6d9326f1a3e0a0667ba6042027eaaee8197a59fe66c5a` | `d8c8bc3cbfaee0f1a2e3e1a8b9538a2dae6e523572f7b9b0698c3045f9bf4a4b` |
| shared native-provenance/record helper: src/h2physics/adapters/lh2dt_compressor.py | `2dc2d23933c3cb40d9a763608ab2f074163f5bebe60cb52df63786e502b72939` | `73c8cb92b2079b340bcb07d9ad2d434bfa0290289b4d5a0d500e262cd924412f` |
| examples/lh2dt_heat_exchanger.py | new | `a44beaea9c632881dd8994f1d097f63664fb7dff4b189b7bf64bd6e29fd61bcc` |
| shared explicit native loading: examples/lh2dt_compressor.py | new | `b05b74997e7ada40267084811001122339a3cbcc6ff4861adee7952f16390dfd` |
| validation/cases/lh2dt_heat_exchanger.py | new | `38c422d317c78ed0cb80af97312f89381ea64b94062a63cdc78685ca20c962b8` |

Current report/document hashes are sent separately to avoid self-reference.

## Historical executed input record

Reproduce: `python scripts/check_heat_exchanger_integration.py` after installing the separately reviewed native snapshot.

Native LH2DT source `b2f276333c1b1793c39f25763703d196d36742ec`, CoolProp 8.0.0, SciPy 1.18.1; seven complete coupled integrations, 21.996 s local calculation. Each uses one actual DynamicNetworkSimulator and two actual DynamicVaporizer cores/states/derivatives.

Original synthetic closed case: left normal-H2 fluid 400 K /300000 Pa /0.01 m3, wall capacity 100 J/K, fluid-wall conductance 5 W/K; right para-H2 fluid 250 K /200000 Pa /0.02 m3, wall capacity 150 J/K, fluid-wall conductance 6 W/K. Each wall starts at its own fluid temperature. Both native ambient-UA slots are explicitly the same interwall conductance 2 W/K; each receives the other current finite wall temperature. No external bath, mass port or leakage is present. Each native fluid-wall heat cap is 1e6 W. The operating envelope is 200-650 K /1000-1e7 Pa /mass>1e-8 kg, and source clock starts 100 s. Coefficients are authored verification inputs, not manufacturer maps or experimental estimates.

The public composite DynamicNodeModel advances both native states at every common RK stage. Native advance/combine and derivative_from_flows functions own all physical balances and heat laws. Only the per-side heat integrals are appended. A private port-free native scheduling network carries a left-side representative thermodynamic boundary for its API; it is not an aggregate exchanger pressure/state. The physical side bases and outputs remain separate. The native ambient heat field means internal counterpart-wall heat in this composition; its global sum is explicitly zero.

| Quantity | Observed value |
|---|---:|
| Fine left final fluid / wall T | 366.645458835 / 360.755148219 K |
| Fine right final fluid / wall T | 268.069614615 / 275.164668199 K |
| Maximum side mass / energy defect | 0 kg / 9.82254277915e-11 J |
| Maximum global-U / opposite integrated heat defect | 1.30967237055e-10 / 0 J |
| Maximum native opposite heat-rate defect | 0 W |
| Independent analytic two-wall temperature error | 1.33974253913e-09 K |
| Independent whole-system equilibrium / max final error | 307.264634441 / 2.96438429359e-10 K |
| Fresh native PT mass / side-U defects | 1.30104260698e-18 kg / 6.73026079312e-11 J |
| Coarse/medium four-temperature differences from fine | [5.499697408595239e-07, 3.113649427177734e-08] K |
| Fine accepted-sample left/right heat errors | {'left': -0.007097421124854009, 'right': 0.007097421124854009} J |
| Reversal left-side heat range | -200 to 131.718788814 W |
| Fine actual stage clock bounds / pair derivative evaluations | (100.0, 120.0) s / 801 |

| Gate | Pass |
|---|---|
| actual native cores, states, derivatives and one simultaneous integrator retained | True |
| each sealed fluid mass remains fixed <1e-13 kg | True |
| each native fluid+wall energy defect <1e-5 J | True |
| closed pair global energy and integrated opposite heat <1e-5 J | True |
| native heat rates equal/opposite <1e-9 W | True |
| both finite fluids and walls respond | True |
| zero conductance gives independent stationary side inventories | True |
| independent analytic two-wall exponential <1e-8 K | True |
| fresh native fixed-density whole-system equilibrium <1e-5 K | True |
| independent fresh native PT reconstructed side mass/U <1e-12 kg /1e-5 J | True |
| finite initial fluid/wall storage reverses interwall heat | True |
| 0.5/0.25/0.125 s final four-temperature agreement <1e-3 K | True |
| finest accepted-sample independent heat quadrature <0.01 J | True |
| separate normal/para bases retained without mass/reference mixing | True |
| native and host/test/replay begin/end fingerprints unchanged | True |

Numerical/interface verification is distinct from measured validation. The model has two spatially uniform finite fluids and two walls. It does not solve counterflow/parallel-flow profiles, LMTD/NTU effectiveness, hydraulic pressure drop, process-port flow, thermal leakage, variable conductance/isolation or a vendor rating. Different material energy zeros cause no hidden transfer: side masses are fixed and their energy changes are audited separately before summing. Native EOS/phase/domain and per-side closure failures propagate.

Receiving work includes a native composite thermal-group boundary that does not need a representative hydraulic state, public heat-port separation from ambient fields, conservative process-port/leak ledgers, and accepted-step streaming hooks. Current trial evaluations are buffered then matched to actual accepted composite-state identity; no fixed RK call count is used for acceptance. No receiving repository is edited or messaged, and no external data/native code is bundled.

Primary references: [native LH2DT](https://github.com/lyullee/lh2dt_models), [native finite-fluid/wall balance](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/dynamic_vaporizer.py), [CoolProp native EOS](https://doi.org/10.1021/ie4033999). Original composition, analytic cases and tests; no heat law, native ODE, EOS implementation or coefficient table was copied.

## Begin/end fingerprints

- Native Python aggregate before: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`
- Native Python aggregate after: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`
- Native `dynamic_vaporizer.py`: `153a07dd99225043d23fdf7e122d7abeeb65546a0899b9388dcecca9c5e4068a`
- Native `dynamic_network.py`: `9a16013db2668e28b1d03b64cad4e407c87e6e9c61c87d25e43d53dfd8a45ff1`
- Native `network.py`: `d2437197f11fb3471eb571df8abf09b1c4b3cc81bccaffbbc5a2b8cc91ebe759`
- Native `properties.py`: `835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3`
- `src/h2physics/adapters/lh2dt_heat_exchanger.py`: `cdc09e3cabe738a224e6d9326f1a3e0a0667ba6042027eaaee8197a59fe66c5a`
- `tests/test_lh2dt_heat_exchanger.py`: `36f9a675d97ebef0be819b978249e0359eff33085948d4db69ea2734107012c4`
- `scripts/check_heat_exchanger_integration.py`: `6b88c621ebe61f00b12d60460ac5e93d3c5d6edf1632611a7243cca5cbddee7d`
- `src/h2physics/adapters/lh2dt_properties.py`: `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2`
- `src/h2physics/adapters/lh2dt.py`: `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed`
- `src/h2physics/thermo/coolprop.py`: `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b`
- `src/h2physics/dynamics.py`: `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd`

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/adapters/lh2dt_heat_exchanger.py` | `cdc09e3cabe738a224e6d9326f1a3e0a0667ba6042027eaaee8197a59fe66c5a` | `cdc09e3cabe738a224e6d9326f1a3e0a0667ba6042027eaaee8197a59fe66c5a` |
| `tests/test_lh2dt_heat_exchanger.py` | `36f9a675d97ebef0be819b978249e0359eff33085948d4db69ea2734107012c4` | `36f9a675d97ebef0be819b978249e0359eff33085948d4db69ea2734107012c4` |
| `scripts/check_heat_exchanger_integration.py` | `6b88c621ebe61f00b12d60460ac5e93d3c5d6edf1632611a7243cca5cbddee7d` | `6b88c621ebe61f00b12d60460ac5e93d3c5d6edf1632611a7243cca5cbddee7d` |
| `src/h2physics/adapters/lh2dt_properties.py` | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` |
| `src/h2physics/adapters/lh2dt.py` | `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed` | `0711da98a12a034d3af69b7f377f9b07b3cac1ad82d1a4336bfd0850d16d23ed` |
| `src/h2physics/thermo/coolprop.py` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` | `d6b2e7f663ab8815e3935294855ebb2d763ad27685e3056af46b0776694e4b8b` |
| `src/h2physics/dynamics.py` | `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd` | `d3964d476994dc12cee0113ee137cc1313c8e0d4f97dfd3167b487c8367e9abd` |
