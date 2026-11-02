# Model-level extensions and research continuation — 2026-11-02/03

This record captures eight selected improvements developed and tested as
**0.2.0.dev0** after the 0.1.0 release. That implementation is packaged as
**0.2.0** without changing its equations or physical defaults; current source,
registry/archive identities and service outcomes are in
[publication status](PUBLICATION_STATUS.md) and the
[0.2.0 receipt](REGISTRY_ARCHIVE_RECEIPT_0_2_0.md). The historical development-wheel
checks below retain their actual version/basis. The 0.1.0 files, tag and deposit
are preserved. Original family counts and historical campaigns remain their own
snapshots; eight added levels are not eight independently qualified models.

## Implemented scope

| Work package | Direct Python location | Added calculation | Boundary and manual |
| --- | --- | --- | --- |
| R1 | `adapters.indoor_release` | Actual HyRAM indoor source/layering and conditional enclosure peaks | Peak is indexed by ignition delay, not blast-wave time; [manual](INDOOR_AND_DDT.md) |
| R2 | `combustion_screening` | Native reacting-mixture expansion, critical expansion and cell-width necessary-condition screens | Evidence, condition, geometry and uncertainty gates; no transition probability; [manual](INDOOR_AND_DDT.md) |
| R3 | `mechanical_rupture`, `pressure_loads` | CoolProp finite-stock isentropic work, energy allocation, explicit pressure provider and conditional weak acoustic pulse | No universal rupture efficiency or strong-shock/BLEVE curve; [manual](MECHANICAL_LOADS.md) |
| R4 | `materials.sdof` | Linear generalized displacement/velocity, load work and damping energy | Supplied actual-event net pressure; no invented plasticity or building qualification; [manual](MECHANICAL_LOADS.md) |
| R5 | `adapters.thermal_cycles`, `adapters.liquefaction_cycle` | Actual TESPy power and liquefaction networks, native ExerPy component/network physical exergy, cycle-to-stack example | Thermal utilities and electrical conversion remain explicit; [power/redox manual](THERMAL_CYCLES_AND_REDOX.md), [liquefaction manual](LIQUEFACTION_CYCLE.md) |
| R6 | `storage.redox_equilibrium` | Native finite gas/two-solid Gibbs equilibrium mapped to balanced extent, heat and declared relaxation rate | Restricted phase set; no universal intrinsic kinetics or oxygen-vacancy model; [manual](THERMAL_CYCLES_AND_REDOX.md) |
| R7 | `electrocatalyst_metrics` | Signed iR correction, Tafel fit, product/charge alignment, FE and active-site TOF | Measurement/site/electrode references supplied; [manual](ELECTROCATALYST_METRICS.md) |
| R8 | `adapters.par_device` | Natural draft, native reacting gas energy, catalyst thermal storage and finite H2/O2 removal | Requires a device capacity law and domain; cold startup is explicit; [manual](PAR_DEVICE.md) |

Fluid-property equations are not reimplemented. CoolProp owns nonreacting fluid
states and TESPy's fluid backend; Cantera owns reacting-mixture and solid
thermochemistry. Existing finite reaction, caloric, native phase and stack owners
are reused. Optional providers are installed separately; a missing provider does
not switch silently to a different physical model.

## Development decisions and corrections

Four independent implementation streams covered indoor/combustion screening,
cycles/redox, PAR, and mechanical/structural/electrode calculations. Cross-review
was followed by executed tests, rather than treating review comments as test
evidence. Important findings were retained:

- HyRAM's conditional enclosure pressure varies with release age at hypothetical
  ignition. A distinct result type prevents confusing it with the waveform
  required by a transient structural solver.
- A local HyRAM dependency directory also contained SciPy 1.16.3. Inserting it
  after importing SciPy 1.18.1 mixed native and Python solver modules. The
  genuine-native tests select the runtime before Python starts; the initial
  failure is documented without patching HyRAM or changing its physics.
- Structural integration splits at all load corners. An initial sparse-output
  test exposed an empty sampling segment; integration now advances that segment
  without requesting an empty dense-output array. Closed-form comparisons also
  constrain the integration step independently of output spacing.
- Finite electrode inputs could overflow into infinite derived metrics.
  Corrected-potential, charge/FE and site-turnover outputs now have explicit
  finite-result gates, with retained extreme-input rejection tests.
- Cold cooling water can consume physical exergy while absorbing heat. Its
  native exergy decrease is classified as an additional resource, while a net
  increase is a rejected-stream loss. Both signs are tested.
- Native Cantera mixture setup can rewrite a pure constant-volume solid's
  redundant serialized molar volume by one floating-point ulp. The shared
  fingerprint now retains exact native density, molecular weights and existing
  thermochemistry for that narrow EOS case. No tolerance or alternative EOS was
  introduced; changes to actual density/thermochemistry remain detectable.
- Clean installation exposed an older eager Excel-reader dependency that blocked
  unrelated physics imports without `openpyxl`. The workbook dependency now loads
  only when reading that workbook; a fresh-process regression blocks the extra
  explicitly. A separate native Cantera Windows path issue was resolved by
  reading the unmodified installed YAML with Python and passing the explicitly
  selected `species` section to the native parser. File hashes and species
  thermochemistry are unchanged.
- A PAR capacity law may close the first law while violating entropy production
  in hot, steam-rich gas. A native combined entropy diagnostic/refusal now
  complements the energy balance. It does not qualify an arbitrary calibration
  or predict ignition.

Scientific explanations and code are independently authored. Source-specific
figures, external tables, supplied reference documents, measured-data payloads,
native solver copies and private execution records are outside public Git and
distributions. Primary scientific and provider references appear in the manuals.
This is a scoped rights/provenance practice, not an absolute legal guarantee.

## Existing-regression control

A broader existing campaign was executed both at baseline commit
`901ace051cafcf0635cde7400a16b0a96b8be981` and in the candidate checkout under the
same local scientific environment. The 414 test outcomes matched exactly:
**348 passed, 61 failed, 5 skipped**, with no changed test outcome. These runs
are not described as an all-green regression campaign.

The 61 failures involved unavailable separately installed LH2DT, HyRAM,
process-risk-consequence-toolkit, QSDsan, DynamicLH2PoolX, pvlib, PSA, Degali,
HELPR or SDToolbox dependencies, or an absent ignored local campaign-output
directory. They are reproducibility/environment blockers in those older tests;
they do not supply physical-accuracy evidence. The newly exercised HyRAM path
has its own consistently selected runtime and genuine-native evidence. Existing
native internal physics was not revalidated to resolve the older blockers.

The compared files were the three input, formula, extreme and connection
campaign lanes, two representative-run files, and existing cold-import,
electrochemistry and core-thermo tests. Machine-local XML/logs retain all names
and causes outside public distributions. The separate affected multiphase and
caloric regression tests are rerun after the narrow fingerprint change.

## Reproduction

Use Python 3.12 and install from this checkout:

```text
python -m pip install -e ".[test,thermo,chemistry,cycles]"
python -m pytest -q tests/test_combustion_screening.py tests/test_indoor_release.py tests/test_mechanical_rupture.py tests/test_sdof.py tests/test_electrocatalyst_metrics.py tests/test_par_device.py tests/test_thermal_cycles.py tests/test_redox_equilibrium.py tests/test_liquefaction_cycle.py
python -m pytest -q tests/test_cantera_multiphase.py tests/test_cantera_caloric.py tests/test_electrochemistry.py tests/test_core_thermo.py tests/test_cold_package_imports.py
```

HyRAM+ 6.1 is a separately reviewed optional provider. Without it, two new
native-indoor cases explicitly skip. For the recorded local profile select its
SciPy 1.16.3 environment **before starting Python**, as described in the indoor
manual. Tests with genuine Cantera, CoolProp, TESPy and ExerPy do not use fake
native outputs to establish acceptance. The added GitHub workflow separates
host/native-connection tests and the isolated indoor-native profile.

Before publication, run the exact staged/working public-tree audit, generate
the API source index and link audit, build both archives, audit their package
source bytes and excluded content, and execute the installed wheel outside the
checkout. A source test is not evidence of an installed archive. Executed counts and installation results are recorded below.

## Continue scientific research

The implementation and software checks do not establish real-facility accuracy.
The next evidence is specific to each new level: enclosure measurements with
declared ignition age; source-qualified FA/DDT mixture/geometry and cell data;
mechanical energy partitions and receptor waveforms; structural generalized
parameters and limits; actual cycle/component maps and utility measurements;
solid phase/equilibrium/kinetic data; electrode reference, gas collection and
site-counting protocols; and independent PAR flow/temperature/removal cases.
Keep calibration and held-out comparisons separate. Reuse the existing APIs
when those inputs become available, rather than duplicating native engines.


## Final software verification scope

The nine new physics test files contain **91 distinct cases** across eight work
packages. All completed successfully across the main scientific environment and
the genuine HyRAM profile. A further fresh-process optional-dependency regression
was added, giving **92 new checks**. Existing related multiphase/caloric,
electrochemistry, core-thermo and cold-import checks supply 47 existing cases.

The main 138-case execution passed 136 and skipped two genuine-native indoor
cases. Both indoor cases then passed in the isolated native profile (9 passes
there, including seven already counted input checks). The added fifth cold-import
case passed separately. Thus the selected final source scope is **139 distinct
cases completed across profiles**, with no unresolved failure in this focused
scope. The broader 414-case environment-control result above remains separate.
The final sectioned-liquefaction source was replayed after its component change:
12 passed. Minimal-environment redox replay after native Unicode input correction:
5 passed; cold-import replay without the workbook extra: 5 passed.


## Installed distribution and manuals

The 0.2.0.dev0 wheel was installed with separately resolved core, thermo,
chemistry, cycle and test dependencies in a fresh Python 3.12 environment.
Its package path was verified to be inside `site-packages`; import version and
distribution metadata both report 0.2.0.dev0. The replay working directory and
test copies were outside the source checkout, with no source package copied
and no source `PYTHONPATH`. The environment deliberately has no workbook extra.

The installed full focused suite completed **137 passed, 2 skipped**, zero
failures/errors. The omitted cases are the two separately selected genuine
HyRAM indoor tests. The installed wheel also passed **9/9** indoor tests in the
independently selected native-runtime profile, including both omitted cases;
seven repeated input cases are not counted again. The selected source/installed scope contains 139 distinct
cases; repeated profile/fixture tests are not added to that denominator.

All executable Python blocks in the six new manuals were run successfully:
five manuals against the installed wheel, and the indoor/DDT manual in the
consistent native HyRAM source profile. Eight Python blocks completed. The
cycle-to-electrolysis example is also exercised by the installed tests. These
are synthetic demonstrations and scoped software/native-interface checks, not
experimental validation or complete facility safety acceptance.

The earlier clean-install failures (eager workbook import and non-ASCII native
file lookup) were retained as failed attempts before the fixes. The final publication procedure requires both archives from the final source,
checks with the existing byte-coherence/forbidden-content auditor, and exact
staged/working-tree and local document-path audits before the GitHub update.
The Git commit receipt records completion of these release gates. Installed scientific versions:
Python 3.12, NumPy 2.5.4, SciPy 1.18.1, CoolProp 8.0.0, Cantera 3.2.0,
TESPy 0.11.3, ExerPy 0.2.0; the separate indoor profile uses SciPy 1.16.3.

No new experimental dataset, intrinsic PAR calibration, global iron phase
qualification, strong-shock correlation or formal structure qualification is
claimed. The existing 0.1.0 PyPI/Zenodo publications remain versioned separately.
