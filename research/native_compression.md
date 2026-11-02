# Native compressor and staged cooling verification

## 2026-10-28 coding-only boundary increment

Status **implemented_unverified**. No native/project/model import, calculation,
test/replay, example/case discovery/invocation, benchmark, installation or job
was performed. Short original native source/API inspection and AST/Ruff/LF checks
support code review only. Historical calculations below apply to their original
recorded hashes and do not validate this increment.

Implemented public pinned `Lh2dtNativeProvenance`, owner-issued stage/train
`require_current`, weak result/witness registries, current native class/method/
property/reference/configuration seals and finite-source snapshot handoff.
Native ratio/efficiency remain replaceable for new points; earlier point guards
become stale when those parameters change. Same-provider PT checks now audit
native outlet/independent PS state alongside the existing shaft/enthalpy checks.
Original native pressure metadata is checked against actual absolute states.
Recognized tabular providers are not silently admitted as qualified HEOS.

The source witness is a caller-supplied native accepted row/current finite owner
state audit, not an independent reconstruction of native acceptance history and
not a withdrawal solver. It retains source mass/U, exact state/row, source identity
and declared absolute clock/projection budget. The surrounding dynamic owner
still owes each mass/enthalpy/shaft/receiver boundary integral. Native property
facades remain separate evidence. No native source, solver, coefficient or map
is copied or invented. Native and downstream result mutation must be rejected
before handoff; the objects remain available to inspect rather than restored.

Original failure causes/native attempt and completed serial stage/cooling prefix
are retained. Existing negative tests that deliberately rebind native methods may
now fail at provenance admission before their fabricated result is evaluated;
their previous passes are not asserted for current bytes. No test file was edited.

New definitions: examples/lh2dt_compressor.py; four deferred cases in
validation/cases/lh2dt_compressor.py, profile `compressor-boundaries` (point/stale/
finite-source/prefix). This is a boundary increment, **zero additional families**.
No case discovery or calculation was performed. Final source hashes follow.

### Static input fingerprints

AST/Ruff/LF/trailing-whitespace checks passed for the six changed Python inputs;
AST counted four definitions in each new equipment profile. Native package bytes
were read statically and still match `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`.
Existing `research/native_lh2dt.toml` and the earlier rights review remain the
dependency receipt; no environment or native source was changed.

| Current coding input | Before SHA256 | Current unexecuted SHA256 |
| --- | --- | --- |
| src/h2physics/adapters/lh2dt_compressor.py | `2dc2d23933c3cb40d9a763608ab2f074163f5bebe60cb52df63786e502b72939` | `73c8cb92b2079b340bcb07d9ad2d434bfa0290289b4d5a0d500e262cd924412f` |
| examples/lh2dt_compressor.py | new | `b05b74997e7ada40267084811001122339a3cbcc6ff4861adee7952f16390dfd` |
| validation/cases/lh2dt_compressor.py | new | `031efdfcbc1cce946c23758738ef0dbcb7c58210f19103289ba5e5eaee2bb295` |

Current report/document hashes are reported separately to avoid self-reference.

## Historical executed input record

This report contains synthetic thermodynamic and software checks. No compressor measurement or manufacturer map is fitted or validated.

LH2DT 0.1.2; CoolProp 8.0.0. Native revision b2f276333c1b1793c39f25763703d196d36742ec.

| Source fingerprint | SHA-256 |
|---|---|
| Installed native Python package, ordered filename+bytes | 5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61 |
| Native compressor.py | 1e08432ee688386955d6b49e11f1b1ef0d410519532102a94fa679c7951f15dd |
| Installed native MIT license | cd63f148087d189cedb2a388fed0bc3f1f0676df5f7ad1adfc8a8789f9570a72 |
| Installed archive receipt | 722522fd4bb2c55165a20d5d7622d025cb9b04feda2d538421786b552b99a618 |

Executed host source/test/script fingerprints, checked again before writing:

| Host file | SHA-256 |
|---|---|
| src/h2physics/adapters/lh2dt_compressor.py | 2dc2d23933c3cb40d9a763608ab2f074163f5bebe60cb52df63786e502b72939 |
| tests/test_lh2dt_compressor.py | 3c536bea82635abc5d4cc027b2a7379ca624547395865409c3fafffafcb7fd74 |
| scripts/check_compressor_integration.py | cc1798324c089ff56f8f81f8199028dc06cf1e187e8d9ef8370b0ca5244a751d |

## Independent ideal-gas limit

The actual installed native Compressor receives an authored test-only ideal property fixture with cp=12000 and R=3500 J/(kg K), h(300 K)=2.3e6 J/kg and s(300 K,100 kPa)=7000 J/(kg K). This synthetic gas is not a hydrogen property fit and is not exposed as a production provider. The independent oracle uses T2s=T1*ratio^(R/cp) and fluid work cp*(T2s-T1)/eta.

54 actual native points: ratios 1.05/2/5, efficiencies 0.6/0.8/1, inlet temperatures 250/300/600 K and mass flows 0.001/0.02 kg/s.

| Maximum diagnostic | Observed |
|---|---:|
| Outlet T relative error | 3.330669074e-16 |
| Shaft power relative error | 2.220446049e-15 |
| Enthalpy/shaft residual W | 2.910383046e-11 |

## Actual HEOS stages

Each pure-H2 spin identity has its own shared HEOS provider, native Lh2dtLowLevelProperties facade and actual native Compressor. Independent CoolProp high-level PS/PH queries check h2s, h2 and T2; they are the same EOS implementation through another interface, not an experimental EOS comparison.

Grid per fluid: inlet pressures 0.1/1/20 MPa, temperatures 280/400 K, ratios 2/4 and efficiencies 0.65/0.85 at 0.02 kg/s.

| Fluid / spin | Points | Max T relative difference | Max shaft relative difference | Max energy residual W | Exploratory 1e-5 W subgate |
|---|---:|---:|---:|---:|---|
| Hydrogen / normal | 24 | 2.718890668e-10 | 5.406485259e-10 | 8.186179912e-08 | passes |
| ParaHydrogen / para | 24 | 2.939563037e-10 | 3.208100452e-12 | 4.166792496e-05 | fails; raw residual retained |
| OrthoHydrogen / ortho | 24 | 1.93431049e-10 | 3.852486108e-10 | 4.60568117e-09 | passes |

Native EOS metadata limits; accepted states also satisfy the caller envelope.

| Fluid | Tmin K | Tmax K | pmax Pa |
|---|---:|---:|---:|
| Hydrogen | 13.957 | 1000 | 2e+09 |
| ParaHydrogen | 13.8033 | 1000 | 2e+09 |
| OrthoHydrogen | 14.008 | 1000 | 2e+09 |

The exploratory 1e-5 W energy subgate is retained independently from the existing common equipment 0.05 W absolute acceptance budget. The native PH flash's returned enthalpy is not replaced by its requested value and no energy-reference correction is applied. A subgate failure therefore remains visible even where the established common equipment contract passes.

## Serial compression and prescribed cooling

Three actual native stages each have ratio 3 and eta=0.8. The inlet is 1 MPa, 300 K at 0.025 kg/s. The comparison returns each cooler outlet to a prescribed 300 K with zero pressure loss; the final aftercooler is included. These states are supplied thermal boundaries, not predicted UA/coolant performance. Both layouts end at 27 MPa.

| Fluid | Layout | Shaft W | Heat into fluid W | Delivered T K | Total energy residual W |
|---|---|---:|---:|---:|---:|
| Hydrogen | adiabatic-serial | 235507.6795 | 0 | 929.9073973 | -1.164153218e-10 |
| Hydrogen | prescribed-inter-and-aftercooling | 156093.9085 | -152542.9592 | 300 | 1.182343112e-11 |
| ParaHydrogen | adiabatic-serial | 234448.6735 | 0 | 925.4061857 | 1.367880031e-09 |
| ParaHydrogen | prescribed-inter-and-aftercooling | 155591.9399 | -152076.3436 | 300 | 1.514308678e-10 |

A separate normal-H2 train uses efficiencies 0.8/0.75/0.7, prescribed cooler outlet temperatures 300/305/310 K and pressure losses 10/20/30 kPa. It delivers 26820000 Pa at 310 K; shaft=168199.7906 W, heat=-160978.7188 W, energy residual=2.364686225e-11 W. Pressure losses are supplied boundary values, not a calculated exchanger resistance law.

## Domain/mode/reference rejection evidence

| Attempt | Observed rejection |
|---|---|
| reverse flow | Reverse compressor flow is unsupported; no expander or bypass is inferred |
| undeclared zero-flow compression | Mass flow is outside the declared compressor envelope |
| isolated nonzero flow | Ideal isolated mode requires exactly zero flow |
| liquid inlet | Compression requires a single gas-phase state; liquid/two-phase states are rejected |
| wet inlet | Compression requires a single gas-phase state; liquid/two-phase states are rejected |
| saturated-vapor endpoint | Compression requires a single gas-phase state; liquid/two-phase states are rejected |
| liquidlike supercritical inlet | Compression requires a single gas-phase state; liquid/two-phase states are rejected |
| wrong spin | Property, spin-composition or energy-reference bases differ |
| wrong energy reference | Property, spin-composition or energy-reference bases differ |

A native point outside the declared 350 K discharge limit is retained and rejected: raw outlet T=445.5549298 K, raw shaft=21435.77426 W. No property/model fallback occurs.

## Local timings

Twelve repeated complete checked stage evaluations after one warmup. Each includes native stage execution, state/phase/reference checks, an independent PS audit and the common power ledger. These are local workload timings, not a general speed guarantee; concurrent jobs and platform affect them.

| Path | Mean seconds/stage |
|---|---:|
| shared-low-level-HEOS | 0.00077815 |
| native-high-level-HEOS | 0.0112125 |

## Scope, rights and receiving gaps

Actual native components, input/outlet/isentropic state objects, raw compressor results and prescribed-cooling native states remain available for deep Python coupling. Throughput is prescribed identically through the train, so zero steady mass residual is a declared no-leakage/no-inventory topology, not a measured prediction. Heat and shaft power are positive into the modeled fluid. Motor/electrical efficiency and utility/chiller power are outside the fluid ledger.

A passed thermodynamic point has no native map admissibility evidence: momentum and operating_point_admissible remain unavailable. No shaft speed, capacity, surge/choke, reverse operation, bypass, check valve, leakage, startup, casing/rotor storage or motor dynamics are inferred. Explicit isolated zero flow is an ideal external isolation boundary, not a resolved machine coast-down.

The installed Vaporizer only adds heat, while Reliquefier requires saturated states and is not a high-pressure gas intercooler. A native bidirectional gas heat-exchanger contract with coolant/UA/capacity/pressure-loss evidence is a receiving gap. Native compressor map/admissibility, network capacity closure and dynamic/isolation contracts are further receiving work. The host does not duplicate those missing equipment solvers.

Primary sources: [native compressor at checked revision](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/src/lh2dt/compressor.py), [native MIT license](https://github.com/lyullee/lh2dt_models/blob/b2f276333c1b1793c39f25763703d196d36742ec/LICENSE), [NASA isentropic relation](https://www.grc.nasa.gov/www/k-12/airplane/compexp.html), [CoolProp HEOS/API](https://coolprop.org/coolprop/LowLevelAPI.html), [hydrogen EOS reference](https://doi.org/10.1063/1.3160306). Native source and external data are not bundled; original fixtures and host integration code are authored here.

Elapsed local script time: 6.7313083 s.

Native and host source/test/script byte guards passed at run start and end.
