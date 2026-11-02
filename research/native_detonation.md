# Native CJ/shock verification record

2026-10-27; original authored software/physics verification. This is an
executable equilibrium CJ endpoint and frozen normal-shock level, using the
actual separately installed Caltech SDToolbox and Cantera 3.2. It is not
experimental validation, ZND structure, DDT prediction or facility qualification.
The public Python contract and equations are in
[NATIVE_DETONATION.md](../docs/NATIVE_DETONATION.md).

## Provenance and actual native feasibility

The authoritative [Caltech distribution](https://shepherd.caltech.edu/EDL/PublicResources/sdt/),
[license](https://shepherd.caltech.edu/EDL/PublicResources/sdt/LICENSE.txt)
and [jump-condition report](https://shepherd.caltech.edu/EDL/PublicResources/sdt/doc/ShockDetonation/ShockDetonation.pdf)
were inspected. The report fetched on this date identifies a January 2025
revision; the website labels an older archive date. Actual Python module
headers in the acquired official ZIP identify April 2026 and Cantera ≥3.0.
This mismatch is recorded rather than treating the website label as a precise
native version. No unrelated PyPI package was substituted.

The original ZIP is 4,549,452 bytes and contains 413 files. Only the ten
original Python package files and original archive license were extracted to
the ignored isolated target. Native source bytes were not edited. No native
demo, mechanism, measurement or coefficient file was installed into host source,
and no main-environment package was upgraded. The source receipt is
[detonation_dependency.toml](detonation_dependency.toml).

| Native input | SHA256 |
|---|---|
| Official SDToolbox.zip | c3de67d95e1586a1abea952d2d3767738e5e6c0a217183d5b9303b8f89adb4b0 |
| Original archive LICENCE.txt | ac5adf8d3a6fbcad70c5aab879e47a941e4008fa305776047df3480d7c3cbf3e |
| Official website LICENSE.txt | 9e161337eee43d727d26202f8a07807f19fb7108c88c3f266fc5cfab6b39642b |
| Native Python aggregate | fc28928f1c4320a7307559c55d5ca834ea4eee53464b8f58bac45c3765adbe7f |
| Native postshock.py | 45d68dbf1565bf10d7c61e57152be379831c8df0874f3d0fdd18f8d4995d7508 |
| Native thermo.py | 23e757ad9386a98148e4ba7e569f300295aed6c83732ddc88621b30bc0514797 |
| Installed Cantera h2o2.yaml | 0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4 |

The aggregate algorithm is SHA256 of sorted top-level native Python basenames
and their original bytes. The installed Cantera mechanism is loaded as text
from its actual package data location to avoid Windows Unicode native-file
lookup failure. It remains separately installed and is not bundled here.
Its ideal-gas phase is used; its Redlich–Kwong phase is not substituted.
Thermochemistry includes formation enthalpies and native entropy/reference
pressures. No independently supplied combustion heat is added.
The ten-species h2o2 fixture retains N2 without atomic nitrogen or nitrogen
oxides. Native equilibrium is restricted to that actual species set;
completion of chemically relevant product selection is not inferred from
successful caloric/element/sonic closure.

The actual native API supplies:

- `CJspeed(P1,T1,q,mech,fullOutput=True)`: speed, R² and real fitted curve;
  it requires a filename and does not return its internal phases.
- `CJ_calc(gas,gas1,ERRFT,ERRFV,density_ratio)`: real owned native phase and
  wave speed at the native fitted density ratio.
- `shk_calc(U1,gas,gas1,ERRFT,ERRFV)`: real owned frozen post-shock phase.
- `soundspeed_eq(gas)`: real native TP-equilibrium sound calculation.

The host does not reimplement any of those solves. A managed native-written
YAML bridge preserves exact native thermochemistry or rejects before CJ.
Actual ConstantCp YAML bound loss is a demonstrated rejected capability:
the failed bridge and reloaded phase remain in the exception. The
direct-object frozen shock does not need this bridge.

## Final executed checks

Environment: Python 3.12.14, Cantera 3.2.0, NumPy 2.5.4, SciPy 1.18.1. Commands:

```powershell
.venv/Scripts/python.exe -m ruff check src/h2physics/adapters/detonation.py tests/test_detonation.py scripts/check_detonation.py
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_detonation.py -q
.venv/Scripts/python.exe -X utf8 scripts/check_detonation.py
```

Final scoped tests: **21 passed in 10.06 s**, no skips. Ruff passed.
Final actual native replay: **18/18 gates passed in 4.6808551000 s**.
Durable ignored logs:
`artifacts/detonation_feasibility/tests-isolated-workspace-final.log` and
`artifacts/detonation_feasibility/replay-isolated-workspace-final.log`.
Every final replay source/test/script hash matched before/after, and both
native aggregate hashes matched the receipt.

The authored upstream is 300 K, 101325 Pa absolute and mole fractions
H2=0.2958579881656805, O2=0.14792899408284024,
N2=0.5562130177514792. These are synthetic premix inputs, not inferred from
the acquired BLEVE records. The mechanism envelope is 300–3400 K and
5e4–5e6 Pa absolute; the initial/final and visible independent probes are
checked against that declaration and actual native fit bounds.

| Baseline native CJ/audit quantity | Observed |
|---|---:|
| Tighter native fixed-ratio speed m/s | 1976.3189787733031 |
| Original native CJspeed fitted speed m/s | 1976.319384569055 |
| Product temperature K | 2964.6795592400636 |
| Product absolute pressure Pa | 1577915.2795906398 |
| Density ratio | 1.8019241904875873 |
| Product shock-frame velocity m/s | 1096.7825334752436 |
| Product laboratory velocity m/s | 879.5364452980596 |
| Momentum residual Pa | 7.350090891122818e-5 |
| Total-enthalpy residual J/kg | 0.002161123789846897 |
| Hugoniot residual J/kg | 0.0020938520901836455 |
| Maximum elemental mass-fraction residual | 3.6777247913732936e-12 |
| Entropy increase J/(kg K) | 1852.1533803863767 |
| Independent native SV-equilibrium sound m/s | 1096.7803205489304 |
| CJ sonic relative residual | 2.0176568376051307e-6 |
| Native sound relative difference | 9.95474205367497e-6 |

Mass flux is rho1 D and w2 is obtained from continuity. Its zero arithmetic
residual is not advertised as an independent native velocity prediction.
Pressure, h, u, entropy, species and elemental fractions are actual native
state properties; the energy and momentum residuals are independent checks.
Chemical reaction heat is already in native species thermochemistry.

Tightening native fixed-density jump tolerance 1e-8→1e-10 changes speed by
−2.8691283660e-7 m/s and reduces the caloric residual. Reducing the independent
SV density step 1e-3→1e-4 changes equilibrium sound by 1.1671528682e-5 m/s.
Neighboring native Hugoniot states at both density ratios surrounding the
native fit have larger speeds and pass the same jump gates; the neighboring
step is also reduced 1e-3→5e-4. These are fixed-native-fit thermochemical,
finite-difference and local-minimum checks. The native global CJ-search
grid/tolerances are not exposed and were not changed or claimed to converge.

For an authored native ConstantCp monatomic argon phase, gamma=5/3 follows
from the explicitly supplied native caloric input. At Mach 2 and3, independent
[normal-shock conservation relations](https://www.grc.nasa.gov/www/k-12/airplane/normal.html)
give pressure ratios 4.75 and 11, density ratios 16/7 and 3 and temperature
ratios 2.078125 and 11/3. Actual native solves' maximum relative errors are
1.7261747587e-12 and 1.8732793095e-12. Analytic expressions appear only in
verification, not in the physical solver.

The replay also checks actual native object/result identity, private source
state preservation, exact bridge thermo identity, entropy/compression,
element conservation, frozen-vs-equilibrium distinction, a 350 K/200000 Pa
initial native CJ case, and cleanup of the temporary mechanism bridge.
The narrow maxT 2800 K case completes actual native fit/CJ work, then rejects
the actual product state while retaining raw fit/CJ results, attempted phase,
copy audits, bridge, completed diagnostics and original domain exception.
Tests exercise initial cryogenic-domain rejection, missing species/O2,
un-normalized input rejection, negative/subsonic shock speed, actual native
thermochemistry mutation and ConstantCp native file-bound loss.

A narrow independent review found that annotated evidence arguments could be
omitted at runtime. Both native entry points now require actual
`DetonationEvidence` and reconstruct validated current fields before creating
any attempted native phase. None and corrupted-clock regressions cover both
entry points. The reviewer confirmed rejection with a retained TypeError
cause and zero attempted phases and reported no remaining concrete P1/P2 in
that narrow review. The final 20-test run includes these two regressions.

## Qualification boundary and receiving work

The native object evidence is substantial but incomplete by public API:
the complete CJspeed internal phase trajectories, transformed native sound
probes, fit iteration count and hard global iteration cap are unavailable.
All visible accepted/audit states are guarded; this is not proof that every
unexposed native trial stayed within thermo fit bounds. The native outer fit
loop can run without a public global iteration limit. Request 021 should seek
an owned-phase/no-file constructor, complete trial states and convergence
status, explicit grid/tolerance/iteration limits, and fit-domain hooks. The
current host neither patches native routines nor inserts a second CJ search.

No condensed equilibrium phase, real-gas shock, spin-resolved hydrogen,
finite-rate reaction zone, detonation initiation/cell size or spatial
overpressure field is solved. The declared pressure envelope is an explicit
computational restriction, not independent ideal-gas model validation.

The acquired [ELVHYS data DOI 10.18710/M5LOLM](https://doi.org/10.18710/M5LOLM)
concern LH2 pressurization/membrane BLEVE. Independent source qualification
found no homogeneous tube H2/oxidizer mole fractions, upstream tube initial
temperature, detonation identification or propagation speed. Containment
oxygen/ambient T cannot fill those missing inputs. Actual fast records are
10 microsecond grids; negative dynamic pressure signals and unresolved station
radius/diameter conventions prevent their promotion to absolute CJ states.
See the independent [data boundary](../docs/SHOCK_TUBE_DATA.md).
No acquired pressure peak was fitted to CJ pressure. Experimental chemical/CJ
validation and facility qualification remain open.

## Final Python fingerprints

| File | SHA256 at both final replay boundaries |
|---|---|
| src/h2physics/adapters/detonation.py | a9c0a16a8e8bcd226768e1d840c650a6d712b0a0faaca27ec4f0b31beca7c073 |
| tests/test_detonation.py | 02d2d3749f6b8fe53cd0491a407c19db8b72a8251f224b31c2a33791914aa50d |
| scripts/check_detonation.py | cd9ac9f68691279b3815557ac89e04f3382d7e6d6bcb84c3894a95dca6b2c457 |

All six owned text files use LF. The final six-file hashes are reported to the
parent after this record is written; its own hash is not recursively embedded.
No shared catalog, general documentation or request file was edited here.

## Concurrent campaign workspace correction

A first parallel full-suite main run had968passes/11skips and one cleanup
assertion failure; its compatible peer had969passes/11skips. An actual second
native bridge held open reproduces only the global workspace assertion, while
the isolated domain-failure case passes. Each production bridge already owns a
unique TemporaryDirectory and deletes its own files correctly.

Verification factories now choose a distinct repository-local ASCII UUID
workspace per model, with an optional explicit workspace argument. One regression
keeps a real first owner's native bridge open while a second owner's actual
domain-failure/native-state/cause/cleanup checks pass, then verifies first-owner
cleanup after exit. No production wave/equilibrium algorithm changed. Final
unsharded profiles each pass970cases/11optional biological skips with all242
Python source fingerprints unchanged. Native replay above uses the corrected
factory/test bytes and the original reviewed native source.
