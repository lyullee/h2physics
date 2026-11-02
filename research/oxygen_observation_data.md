# Cryogenic-room observations: evidence and full-source audit

The source-specific Python profile adds usable, bounded `ObservationTable`
views of ELVHYS4.2 point H2, temperature, gauge-pressure, ventilation-flow and
weather outputs. It does not add measured room oxygen histories. The existing
26-collection screen and subsequent primary-repository search did not establish
an acquired, independently measured O2 depletion/recovery dataset with the
complete boundaries needed for direct ODH validation. This is data qualification,
not validation of an oxygen model, sensor policy, cold-mixture EOS or complete
release/room calculation.

## Source, rights and complete acquisition

Wayne Rattigan, Janet Welch and Janni Vizma (HSE),
[ELVHYS4.2, DOI10.18710/JXJP0H](https://doi.org/10.18710/JXJP0H), DataverseNO,
is explicitly CC0-1.0 in the first-party native metadata. On 2026-10-28 the
actual resolved version was 1.1, updated 2026-10-21; indexed 1.0 descriptions
were not substituted for the acquired version. The repository supplies original
file sizes, directory labels and MD5 checksums. The pinned receipt is
`research/data/elvhys-cold-room.toml`; native metadata and all external source
records remain under ignored `data/raw/elvhys-cold-room/1.1/`.

The existing repository acquisition API acquired the entire 198-file manifest:
1,429,209,739 bytes, 194 newly acquired and 4 already cached files, no omissions
or failed files. The durable local bulk process (PID258168) completed in
1324.4568419 s. No programs or macros were executed. The source has 195 CSV
recorders and three support files. Folder labels retain Dispersion (160 CSV),
Ignitions (20 CSV) and PressurePeakingPhenomena (15 CSV).

The three supports were read: the README and metadata CSV as text, and the
three-page sensor PDF by read-only extraction plus visual inspection of all
three rendered pages. The extraction/rendering tools were in the bundled
document runtime; no main-environment dependency was added. Original source
prose, numerical tables, figures, calibration code and normalized observations
are not copied into the public tree. Counts below are original audit summaries.

| Preserved input | SHA256 |
|---|---|
| Acquisition receipt | `e63eb742c1d6bd87f619976c2aa4fa161d627fe44133233092802e1c0a7f8ea7` |
| Native repository metadata | `85ce468734fa5be9ce8642668fc895917e59c3657aa89201e4f3ea8b23f41c96` |
| Original README | `c6166236c7087ba4a457990470a69c125df436ac20e67b4b35d94e3a3df3fc42` |
| Original metadata CSV | `84d71b9ee69b7814174a15a98243c7681da8cc1e9a8af7b7ebc1307e28e8d488` |
| Original sensor PDF | `bedb3115c22e7f080ab10beef6ed0f3269a0997929e56a6455e80e3acd2911b6` |

Every original numerical file's acquired SHA256, publisher MD5, size and exact
name are in the receipt and the ignored full audit. The profile requires a
complete successful receipt/native file-list correspondence, the declared CC0
rights, exact acquired version and paths confined to the source directory.
Original source hashes are checked before and after a complete read.

## Actual cases, recorders and physical support

The README lists 48 nominal cases; attachments contain 40 actual case IDs.
Nominal cases 1, 2, 32, 33, 34, 35, 37 and 39 have no numerical attachment.
Cases 27 and 28 have all five recorders despite explicit source-invalid labels;
the profile retains every original value and masks physical channels by default.
Ignited cases 36, 38, 40, 41 and 42 have four CSVs each and no FLMT attachment.
The remaining 35 cases each have all five recorder types. Separate stations,
recorders and rows are not experimental replicates. No replicate designation
or independent study count is invented from the case sequence.

| Recorder | Files | Original columns | Recorder rows | Source cells |
|---|---:|---:|---:|---:|
| CONC | 40 | 7, 16 or 17 | 1,444,394 | 23,446,907 |
| FLMT | 35 | 1, 2, 3 or 4 | 1,320,534 | 3,572,522 |
| MISC | 40 | 6 | 1,423,609 | 8,541,654 |
| PRES | 40 | 5 or 6 | 2,538,546 | 13,910,742 |
| TEMP | 40 | 28 | 1,423,610 | 39,861,080 |
| Total | 195 | source-specific | 8,150,693 | 89,332,905 |

The apparatus is a nominal 1 m3 enclosure with different forced/passive vent,
obstacle, pressure-peaking and ignited configurations. Nominal tanker pressure
and nozzle diameter are parsed from original case rows, distinct from actual
release-rig/nozzle pressure channels. The source describes nominal 2/8 barg
tanker cases, small release nozzles and larger pressure-peaking openings;
these descriptions do not determine H2 mass flow, stagnation enthalpy, spin
state, phase partition or a discharge coefficient. Passive opening descriptions
and the PDF schematic are not identical effective-flow-area specifications.
No interchangeable ventilation geometry or effective Cd is inferred.

The actual CSV schemas materially differ from the support's ideal sensor list:

- Thirty-five PRES files export two cube outputs as `Var4` and `Var5`, without
  usable field-specific identity/unit evidence. They remain unresolved, rather
  than being renamed to the advertised box-pressure instruments.
- Blast-pressure exports contain a second coordinate named `BlastTime` in four
  files and `Blast Time` in one. The slow `Time` column is padded independently.
- Six vertical-release FLMT exports contain only `Time`. They do not observe
  zero fan flow. Eleven FLMT files add unresolved `DPT`; two add unresolved
  `CJC1`/`CJC2`. None is automatically promoted to H2 feed or valve position.
- Four H2 header families name stations marked T-only in the source coordinate
  table. Their concentration quantity survives but physical location remains
  unresolved; a separate candidate coordinate preserves the source-name match.

Coordinates are retained in the source bottom-right-front frame viewed from
the H2 inlet, with the declared streamwise/lateral/vertical axes. The runtime
parser keeps the exact source coordinate row and sensor role. Vertical inlet
coordinates in the README narrative and coordinate table/PDF disagree in
component order; neither is silently repaired. Some original filenames have
extra leading zeros or seven-digit date tokens. The README campaign year and
metadata/filename year also conflict. These identities remain original strings.

## Quantities, origins, clocks and masks

H2 outputs are source vol% point-sampler results, converted to fraction. The
publisher reports normalization and sampling-delay alignment; the instruments
are connected by 20 m sampling lines. Consequently CONC values and their
reported coordinate have `Origin.RECONSTRUCTED`. The original raw signals,
delay histories and executable alignment transformation are absent. No Gaussian
sigma is derived from the quoted instrument accuracy or the spread of outputs.
H2 is not O2, H2 mass fraction, release flow or a whole-room concentration.

Temperatures retain K, except indication-only weather temperature converted
from Celsius. Point-flow, nozzle and peened-wall roles stay separate. Nozzle
voltage-to-temperature calibration is reported but its original curve is absent;
this is not a bulk stagnation/phase temperature. README and metadata instrument
models, ranges and errors disagree. A positive value below a quoted calibration
range is not certified by passing the positivity mask.

Named release/nozzle and blast outputs retain gauge-pressure meaning; weather
pressure is source absolute mbar. Conversion produces Pa without adding a
guessed ambient offset. Ventilation air `FanFlowMeter` converts L/min to m3/s;
actual/reference pressure and temperature are unresolved, so no air mass flow
or H2 source flow is derived. Weather remains an indication-only external
record, not a calibrated interior thermodynamic boundary.

All actual CSVs label their first coordinate `Time` without physical units.
Published nominal sample rates (20 Hz for most source channels; higher-rate
peaking and blast cases) and small numerical increments are supporting clues,
not an independently specified unit, epoch or cross-recorder mapping. The
profile retains `source_time_unit_unresolved` and always refuses automatic
`TimeSeries` conversion. It never borrows slow Time for blast pressure. Explicit
blast association applies only when that actual header has exactly one blast
coordinate. Original clock masks, padding and missing rows remain visible.

Across every pair of adjacent finite coordinate values, the full audit found
zero duplicate or decreasing steps. Reported Time has 7,014,969 finite and
1,135,724 missing/nonfinite cells; its finite adjacent increments range from
about 0.002 to 0.05 **source-coordinate units**. The two exact blast spellings
together contain 1,209,058 finite and 8,954 missing cells, with adjacent steps
about 0.00001 source-coordinate units. These checks do not establish seconds,
event synchronization, continuity across missing rows or a physical sensor delay.

Source-cell totals exclude the added reconstructed one-based source-row index.
They include clocks and unresolved-role fields. The complete scan found
85,607,986 finite numerical cells; 72,078,446 passed the limited ingestion
masks and 17,254,459 were masked. Reason counts below can overlap within a
single masked cell:

- 3,371,670 blank/missing and 353,249 nonfinite fields;
- 10,385,901 H2 outputs outside the source 0..100 vol% interval, including
  8,679,115 negative finite H2 outputs; no clipping or baseline correction;
- 1,494,600 nonphysical absolute-temperature outputs, in four temperature
  channels of the two high-rate peaking cases; raw values remain inspectable;
- 2,146,840 channel occurrences masked by the source-invalid case labels.

The source has 3,726,641 finite unresolved-role cells. Those cells, and weather
values that pass these limited masks, are not thereby model-ready. The audit
also retains indication-only humidity above 100% and four negative wind speeds.
Further application-specific physical/quality gates are required. Removing
out-of-range H2 values could censor a baseline or response distribution; the
profile supplies raw values and reasons rather than prescribing a fit.

Each `ObservationTable` row retains DOI/version, original source directory,
filename, SHA256 and physical line. Shared nominal case IDs group recorders;
they do not synchronize clocks. Original raw lines/cells/numbers, finite masks,
SI values, origins, channel roles, source/candidate coordinates and reason masks
remain available as bounded read-only block copies. The source-specific schema
reuses the frozen `ShockTubeRecorder` iterator and shared observation/unit/hash
contracts. No second generic CSV reader or physical model is implemented.

## Full-source replay and exact executable inputs

The durable two-worker replay (original PID265960) completed once in
195.0913613 s. It hashed every one of the 198 attachments and verified every
publisher MD5, then read all 195 numerical files and all original rows/cells.
Each recorder also passed original row/case identity checks, refusal of an
unresolved physical-time history and first-8192-row stability using 137-row
versus 4096-row blocks. All files exceed that prefix length. Maximum file rows
were 800,000; the all-source audit's declared budget was 2,000,000 rows/file.
Per-file atomic checkpoints preserve code/receipt/source identity and require
explicit `--resume`; the completed run was not restarted on a tool timeout.
Source/receipt/metadata and all nine executed Python input hashes were unchanged
between start and finish, and all executed Python sources had LF endings.

The ignored full result is
`data/processed/elvhys-cold-room/1.1/audit.json`, SHA256
`89070cdafa7e407dd5f5b04f43eba06a0dc9f30a574dc8d31312f5b010002426`.
It holds per-file/field ranges, missing/negative/zero/reason counts, original
sensor/clock associations, content signatures, complete input hashes and actual
case IDs. Durable logs remain in `artifacts/oxygen_observation_audit.*.log`;
per-file checkpoints remain ignored. No data artifact is a required public API.

| Executed source/test/script | Identical begin/end SHA256 |
|---|---|
| `src/h2physics/data/oxygen_observations.py` | `c62e4f79b83621091ba51bb1a171e99431a9ca11e7070c8c00c74e61b9c888a1` |
| `tests/test_oxygen_observations.py` | `c30663a6d82535f4d721545a1d0de533a55ae8ee94716560c2819de82b57af30` |
| `scripts/check_oxygen_observation_data.py` | `aa177d7815be5e5cce7c05ec9bbe0f3bfb9ac3ff6a51c82e9a42f222fd3941ec` |

The 18 original-fixture tests passed in 1.03 s; scoped Ruff lint and format
checks passed. Fixtures cover identity, signed flow/gauge meaning, independent
blast clocks, unresolved location/units, conversion overflow, invalid-case and
raw missing/formula/nonfinite preservation, bounded windows/block stability,
hash mutation, and exact receipt/native-manifest/rights/path admission. No
external numerical rows are copied into tests. Reproduce from the repository:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_oxygen_observations.py -q
.venv/Scripts/python.exe -m ruff check src/h2physics/data/oxygen_observations.py tests/test_oxygen_observations.py scripts/check_oxygen_observation_data.py
.venv/Scripts/python.exe -m ruff format --check src/h2physics/data/oxygen_observations.py tests/test_oxygen_observations.py scripts/check_oxygen_observation_data.py
.venv/Scripts/python.exe -X utf8 scripts/check_oxygen_observation_data.py --workers 2
```

## Existing records and further primary-source search

The existing 26 collections/268 successful attachments were screened from
their receipts, qualification reports and relevant schema support; prior
complete numerical audits were not repeated. Existing pressure-unignited data
retain point H2, signed release flow and pressure with distinct clocks/bases.
HyTunnel/mechanical-ventilation observations concern spatial jets and cannot be
silently promoted to a homogeneous initial inventory. Carpark thermal files
have ventilation outputs but unresolved clock units and no O2 history. ELVHYS4.3
has a containment O2 summary rather than co-clocked O2 dilution data. These are
useful partial physical observations, not independent oxygen histories.

The two previously acquired H2SAFE assets were inspected narrowly for missing
oxygen evidence: ZIP member/header inventory and its source description, not a
second full numeric scan. The first-party source is now
[NLR H2SAFE, DOI10.7799/17118570](https://data.nlr.gov/submissions/330).
The actual five tests use helium; concentration/time units remain undeclared
in the numerical headers, specific standard flow reference conditions and
pressure basis are incomplete, and no measured O2 history is present. Source
coordinates and HVAC descriptions do not establish H2 equivalence or a
complete initial-inventory/time mapping. Its older receipt was not modified.

The strongest direct oxygen candidate is Nida Qayyum, Andrew Cole, Pim Oomen,
Rami Khayat and Anna Grosberg,
[Dryad DOI10.5061/dryad.t1g1jwtg9](https://datadryad.org/dataset/doi:10.5061/dryad.t1g1jwtg9).
First-party version-6 metadata establishes CC0-1.0, two attachments totalling
235,065 bytes and original SHA256 checksums. Its metadata describes inlet and
chamber gas-O2 fractions with explicit seconds, as well as separate liquid O2
and biological measurements. These could support warm gas-chamber dilution
and response comparisons after actual schema/boundary qualification.

Both original attachment API downloads returned HTTP401; a public file-stream
attempt returned403. No attachment was acquired or examined. The failed
`research/data/oxygen-hypoxia-chamber.toml` receipt preserves explicit rights,
complete metadata/file-list checksums, both original file checksums and zero
successful bytes. The metadata SHA256 is
`a875d98d391a7c7d4a8d727f5bf094bdad424815ab4be3debe624c06e060a5ab`;
the original workbook checksum is
`f301464111d1feb33c1b28a192b8b9d868a352a6041d8f4b0da03eeccc152383`.
The authors' linked public model repository does not establish identity with
the missing full workbook; no training subset was substituted and no included
model was executed. Acquiring the two exact original files and validating
their published checksums is the next concrete direct-O2 evidence step.

Other primary records were considered without acquiring unsuitable attachments:

- [Figshare DOI10.6084/m9.figshare.29947679](https://doi.org/10.6084/m9.figshare.29947679)
  has clear CC BY 4.0 metadata and checksums, but the associated
  [primary paper](https://doi.org/10.1038/s41597-025-06508-1) places gas sampling
  inside volunteers' breathing masks under hypobaric conditions. These are not
  room-inventory/ventilation observations.
- [NIOSH's primary enclosure experiment record](https://stacks.cdc.gov/view/cdc/185705)
  documents N2 displacement/O2 recovery in a small enclosure. A versioned,
  checksum-bearing raw time-history dataset was not identified; no figures were
  digitized or experimental table copied.
- A [primary hypoxia-chamber monitoring paper](https://doi.org/10.3389/fphys.2022.891005)
  links public monitoring examples, but complete dataset version/rights and
  experimental boundary qualification were not established for acquisition.
- [Zenodo DOI10.5281/zenodo.14090025](https://doi.org/10.5281/zenodo.14090025)
  concerns condensation/He-N2 thermal-flow experiments rather than measured
  room oxygen histories. ELVHYS4.1 DOI10.18710/YGHHTR addresses oxygen-enriched
  condensed-phase hazards; neither was substituted for room dilution evidence.

## Admissible comparisons and receiving evidence gaps

An admissible later comparison must bind the actual case/vent configuration,
initial inventory and selected source history; qualify physical clocks and
processed-sampler response; map each model observable to a source-supported
point/frame; and use the correct gas/volume/gauge/temperature basis. The current
profile makes those missing inputs inspectable rather than filling them.
Measured nozzle pressure plus nominal geometry does not replace independently
qualified H2 release mass/enthalpy or liquid/vapour partition. Fan volume flow
does not close passive exchange or a finite air inventory. A sparse point-sensor
average does not become a measured room average.

In particular, calculating ambient_O2*(1-H2) would assume composition, mixing,
humidity and observation basis. It would be reconstructed model output, not an
independent O2 measurement or a direct ODH validation target. Native monitoring
and physiological calculations must retain their own source, receptor, clock,
state-domain and observation-operator contracts. This acquisition adds no new
model-family implementation or experimental validation claim.
