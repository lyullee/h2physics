# Native finite biological process verification — 2026-10-27

Status: original host composition/audit with an actual separately installed
QSDsan ADM1/BioSTEAM continuous CSTR. Synthetic numerical verification only; no
workbook reconstruction, parameter fit, held-out biological validation, dedicated
fermentation plant, thermal closure or manufacturer qualification.

## Supported physical boundary

One native well-mixed10L liquid volume and5L headspace, prescribed308.15K,
native differential dissolvedH2, native acid/base equilibrium, native variable
absolute pressure and one-way gas extraction. Native ADM1 owns all19biochemical
processes and3gas-transfer processes, all substrate/biomass states and the actual
BDF solve. There is no host reaction-rate law, coefficient matrix, EOS or second
physical integrator. All actual native components/model/reactor/streams/System
and original SciPy OdeResult are retained. Public inputs are typed Python
objects and complete component mappings with SI clocks; no serialization is
required.

Actual accepted capability requires positive liquid throughput. An exactlyclosed
zero-liquid-feed run completes native BDF, then native QSDsan outlet conversion
raises RuntimeError because set_flow_by_concentration rejectsQ=0. The host raises
BiologicalAuditError with the completed actual solution/final accepted state; it
does not substitute an epsilon feed or promote this diagnostic to an accepted
closed-process capability. Gas extraction may independently be0 or blocked by
downstream pressure.

Native states use component measured bases. COD, C, N accounting is distinct from
physical H2 mass and molar flow. Native H2 i_mass=.1259972248959336kgH2/kgCOD and
chem_MW=2.01588kg/kmol give15.9996kgCOD/kmolH2. Gas inputs are explicit mol/m3,
native gas states kmol/m3; native pressurebar becomes hostPa absolute and native
days become absolute SI seconds. Gas-phase S_IC meansCO2. H2spin remains
unresolved. COD is not enthalpy; totalenergy/H/O/fullwetmass are not closed by
this level. The native saturated-water-vapor pressure approximation has no
coupled evaporation/water/latent-energy state.

## Rights, dependencies and rejected native baseline

Reviewed QSDsan1.5.3 wheel SHA256
`b91c5eff069a3703a47e0a2f9b26e8fe8fa875c1f50c7f1a59b5e34a96e33476`.
Actual installed QSDsan/BioSTEAM/Thermosteam LICENSE.txt files all grantNCSA.
BioSTEAM/Thermosteam PyPI metadata also saysMIT; the authoritative installed
license files control this review. Neither implementation nor bundled native
coefficient/data resources are copied into host source/distributions. All
66resolved optional distributions and artifact hashes are in
[biological_dependency.toml](biological_dependency.toml).

The main Python environment was unchanged. The first separate-target install
failed because numpoly1.3.9 requires unavailable MSVC14. A single compatible retry
uses the official pure Python numpoly1.2.14 wheel, satisfying native Chaospy
requirements. Git-based fixed-core installation began fetching unrelated nested
Bioindustrial-Park/How2STEAM submodules, so that job was cancelled and the same
immutable official commit was installed from its official source archive instead.
Logs/receipts remain ignored under artifacts/biological_feasibility. No original
native file was edited and no monkeypatch was used to repair native physics.

Actual published BioSTEAM2.54.0 passes mutable System._state as solver y0. An
authored finite .1day case returned native solver success but changed the first
trajectory coordinate by.2044544360 and failed the component ledger
(1.9958978e-6kg measured defect). The official fixed revision is
`0acb320455d3c6cdaace85bf6ca27a1256706918`; its version string also says2.54.0.
Its native _system.py SHA256 is
`0b2ce94ba718b78712d73480563350d861e301049d9017a9c15b92de1754aff9`.
The actual file hash is therefore an admission gate. Official archive SHA256
`cdb40ab8bf67921de2250d73d95148978f1ed6855bcb341816852b5201ec5705`.
The fixed native copies y0; the exact same initial-state gate then has0.0error.

Native profile: QSDsan1.5.3, fixed BioSTEAM2.54.0, Thermosteam0.54.2,
SciPy1.18.1, NumPy2.5.4, numpoly1.2.14, Python3.12.14, Windows.
NUMBA_DISABLE_JIT=1 is explicitly set for verification; actual native Python
functions/equations and native System/BDF remain owners. JIT-enabled fixed-profile
execution is not claimed verified. Native import/deprecation warnings remain
visible. Keep these targets separate from the host normal/SciPy1.16.3 suites;
prepending the target would shadow those suites' SciPy/NumPy versions.

## Authored verification cases and actual measurements

All values below are explicitly synthetic choices, not missing experimental
inputs inferred from the old workbook. Native default kinetics are used without
fit for the active-community case. Initial liquid kg(native basis)/m3:
S_su1, S_IC.1, S_IN.05, X_su.1, X_h2.01, H2O1000; every other native component
explicitly0. Initial gas mol/m3: H2=1e-6, CH4=30, CO2=10. Feed1e-4m3/day has
S_su1/S_IC.1/S_IN.05 and all other nonwater components explicitly0; native
WasteStream closes its water volume. Extraction coefficient1e-9m3/(sPa),
external pressure101325Pa absolute. Clock864000→872640s (native10→10.1days).
No biomass retention or prescribedpH controller.

Baseline BDF rtol1e-8/atol1e-11/maxstep300s and12801dense-output samples
(dt.675s); refinement2e-9/2e-12/150s and25601samples(dt.3375s). Component
acceptance budget1e-7kg+1e-6relative, invariant1e-8kg+1e-6relative; none were
loosened after failure. A1601sample ledger is intentionally rejected with
COD defect5.874563e-8kg. These sampled Simpson audits are not exact native
accepted-step ledgers. Native accepted step clocks and dense sample clocks remain
distinct.

| Quantity | Observed |
|---|---:|
| Native accepted trace points | 301 |
| Initial trajectory error | 0.0 |
| Initial/final absolute pressure Pa | 108113.54566882928 / 101391.72953411406 |
| Initial/final S_su kgCOD/m3 | 1.0 / 0.7955506424180973 |
| Native reaction H2 formed kg | 4.407144913560163e-05 |
| Native reaction H2 consumed kg | 4.146493517824932e-05 |
| Actual exported H2 kg | 5.990035882117767e-08 |
| Integrated dry export H2 mol fraction | 0.0020679068194756037 |
| Max component measured defect kg | 1.4887503193932155e-09 |
| COD boundary defect kg | 1.4316197749302505e-09 |
| C boundary defect kg | 3.589307710641712e-10 |
| N boundary defect kg | 6.437607563449068e-19 |
| Refined component measured defect kg | 1.0159460274460942e-09 |
| Endpoint liquid-coordinate refinement | 6.821015280378262e-10 |
| H2 export refinement relative | 1.686446213757237e-06 |
| Analytic inert CSTR concentration error kg/m3 | 2.591815650987428e-12 |
| Diagnostic closed COD/C/N inventory change kg | 2.4412837844267397e-18 |

The dry H2 fraction is onlyabout.21%; the result preserves H2 consumption by
native methanogens, rather than claiming a high-purity H2 plant. Finite-window
export includes any initial gas; it is not feed-origin recovery or calibrated
yield. Zero export returnsNone. Biomass/substrate and every native component
have signed inlet/liquid-outlet/dry-gas-outlet/biochemical ledgers. H2 physical
ledger passes1e-10kg. Independent COD/C/N totals use native weights and verify
the native stoichiometric nullspaces. An inert limit sets native kinetic/decay
and gas-transfer constants to0 through the actual model constructor; the
independent analytic CSTR exponential passes1e-10kg/m3 with native tightened
BDF1e-12/1e-14/900s.

Native _update_state zeros states below1e-16 in its mixed native units; this
includes negative trials. No exact positivity or individually observed trial
correction is claimed. The host clips nothing, rejects negative/nonfinite audited
states and nonfinite native rates/quadratures/residuals/weights, and enforces
inventory budgets. Pressure domains are checked after the native run at accepted
and sampled states, not localized events. Failures retain original native objects,
OdeResult, failing state/time/clock kind, audited prefix and original cause. A
secondary native synchronization failure is separately preserved as
restoration_error. Independent pressure_data review reproduced an actual native
rate_constants[0]=NaN (one nonfinite native rate, no new integration) and confirmed
explicit rejection. Dedicated API fault injection checks primary/secondary error
identity; those injected faults are not physical validation evidence.

## Final execution

- Native scoped tests before the encoding-only test repair: **18passed**,54.10s,15 visible native warnings. Preserved test SHA256 `f7eb93febd51581511482c77fce3787921553b7d32b65c5cbb0769309013da7d`.
- Final test source repairs only the published-baseline subprocess to launch `-X utf8` and decode explicitly asUTF-8. The repaired case passes **1test/17deselected**,2.08s under `python -X utf8`. AST comparison proves all other module/import/fixture/test nodes unchanged; the other17 native tests are not falsely claimed rerun after this encoding-only change.
- Final native replay: **18/18gates**, 53.395199099999445s under `python -X utf8`, with the final UTF-8 repaired test hash.
- Host without optional targets before the encoding-only repair: **7passed/11skipped**,3.84s. Final repaired host shards reported by the parent: mainSciPy1.18.1 **7passed/11skipped**,2.35s; compatibleSciPy1.16.3 **7passed/11skipped**,2.31s. Skips do not count as native execution.
- Ruff and git diff whitespace checks pass. All five host replay inputs plus three
  native package fingerprints match before/after and the final on-disk bytes.

The final replay performs7actual native integration attempts:4accepted
continuous runs (baseline, refined, inert and reverse-blocked) and3retained
rejections (closed output finalization, underresolved ledger and pressure domain).
The actual native NaN-rate negative gate reuses retained sampled states and adds
no integration.

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'artifacts\native_biological_core_fixed') + ';' + (Join-Path $PWD 'artifacts\native_biological_packages')
$env:NUMBA_DISABLE_JIT = '1'
.venv\Scripts\python -m pytest tests/test_biological.py -q
.venv\Scripts\python scripts/check_biological.py
```

The package installation/API detail is in
[NATIVE_BIOLOGICAL_PROCESS.md](../docs/NATIVE_BIOLOGICAL_PROCESS.md); the parent
maintains the shared optional requirements profile and receiving request019.
Durable ignored logs include test_biological-pre-utf8.py (preserved exact18-pass test), tests-utf8-focused.log, install.log (MSVCfailure), install-compatible.log,
fixed-core-install.log (cancelled submodules), fixed-archive-install.log,
probe-finite-pypi.log, probe-refinement-fixed.log, tests-freeze.log,
replay-freeze.log, replay-utf8-final.log and tests-host-freeze.log. The parent also reruns the small host shards with both main and compatible SciPy without injecting the biological target. The earlier replay JSON NumPybool
serialization failure was corrected in the script; only the final fully emitted
replay supplies these receipts. No physical tolerance changed for serialization.

## Final host/native fingerprints

Sorted package aggregate algorithm: relative POSIX filename +NUL+actual bytes of
each sorted .py/.tsv file. No third-party source is reproduced here.

| Input | SHA256 |
|---|---|
| src/h2physics/adapters/biological.py | `20efe83da0320fbf6ab0f55ce9cb62bed21559e2067e5cab75a983594946f0bd` |
| tests/test_biological.py | `6a9654aac98185bb64fa4914f7844cca07d08e344e2059ef192156edaa28d9f7` |
| scripts/check_biological.py | `d941546e6bc946eedc90b15853cb0676a2f44c68204ca36cee0e2441aabb0111` |
| docs/NATIVE_BIOLOGICAL_PROCESS.md | `bf3db31ec7cd818e1023ab9e73d54e1ad53b14311e7135ccf1811f5713b2ffea` |
| research/biological_dependency.toml | `dcf4584a90c5bbcb332299c2d63889b77038530bd6a8b3406037575046f353fe` |
| native:qsdsan | `f1d3da4179425a1aa719738f838e3050c6994d6358a8f2a4341b118a20f15ac1` |
| native:biosteam | `f3fbd02664878eb18ec3972c5683ba887f6bf2685833038fb879bdbe0a177cc1` |
| native:thermosteam | `3cfb9abb2b265669bc18e6ea2dd68a2c178fabe68a9d3d59feabb0dbdb4a4248` |

The report's own SHA256 is captured externally in the freeze notice to avoid a
self-referential hash. All owned files use UTF-8/LF. No shared code/catalog/docs,
other agent files, Git commits or remote writes were made by this task.

## Primary source and receiving contract

- [Official QSDsan source/license](https://github.com/QSD-Group/QSDsan),
  [versioned PyPI metadata](https://pypi.org/pypi/qsdsan/1.5.3/json).
- [Fixed official BioSTEAM source](https://github.com/BioSTEAMDevelopmentGroup/biosteam/tree/0acb320455d3c6cdaace85bf6ca27a1256706918)
  and [NCSA license](https://github.com/BioSTEAMDevelopmentGroup/biosteam/blob/0acb320455d3c6cdaace85bf6ca27a1256706918/LICENSE.txt).
- [Batstone etal.2002 ADM1 primary publication record](https://research.wur.nl/en/publications/the-iwa-anaerobic-digestion-model-no-1-adm1/).
- [Rosén/Jeppsson primary Lund report](https://lup.lub.lu.se/search/files/5715450/588082.pdf),
  especially§3.1.1 for COD/C/N closure and the ODE/DAE/gas-liquid treatment. The
  old iea.lth.se report URLs returned404; the institutional repository PDF is
  independently accessible. It is cited/read, not copied or redistributed.
- [Official native ADM1 API](https://qsdsan.com/en/latest/api/process_models/ADM1.html),
  [native reactor API](https://qsdsan.com/en/latest/api/unit_operations/dynamic/anaerobic_reactor.html).
  Current web pages describe1.6.0; installed version/source hashes govern this
  contract, not tutorial defaults or external worked examples.

Receiving request needs a public initialize/solve entry accepting native state
objects, returning the original integrating System/reactor/streams/OdeResult and
accepted initial/end states without mandatory output-stream conversion; a
zero-liquid-flow finalizer; explicit trial-threshold correction diagnostics;
accepted-step signed component/element/dry-gas export integrals; and explicit
thermal/water/H/O closure before claiming those balances. Field/culture/feed/
biomass/gas-reference/measurement-clock evidence is required before parameter
estimation or independent validation. A dedicated fermentative-H2 native process
must be separately evidenced; native ADM1 methane-path suppression is not
assumed to be a validated culture model.
