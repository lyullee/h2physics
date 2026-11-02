# Cryogenic-room observations and oxygen-validation boundaries

`h2physics.data.oxygen_observations` provides a bounded profile of the newly
acquired ELVHYS4.2 cryogenic-room campaign. The name identifies the ODH evidence
review lane: **the source observes H2, not an O2 depletion history**. No oxygen
fraction, oxygen-deficiency threshold time or room-average concentration is
derived from these files.

The primary source is Wayne Rattigan, Janet Welch and Janni Vizma,
[ELVHYS4.2, DOI10.18710/JXJP0H](https://doi.org/10.18710/JXJP0H), DataverseNO.
The actual resolved version is1.1; indexed pages still describe1.0. Native
metadata explicitly declares CC0-1.0 and publishes each original file's MD5.
The receipt records native metadata SHA256, exact original names/URLs/sizes,
publisher checksums and acquired SHA256. Raw and normalized external records
remain ignored and excluded from distributions. No source prose, table, image,
calibration implementation or experimental numerical record is copied into Git.

## Python API

```python
from h2physics.data.oxygen_observations import CryogenicRoomCollection

source = CryogenicRoomCollection(
    "research/data/elvhys-cold-room.toml", "data/raw")
source.verify_sources()

for recorder in source.recorders:
    for block in recorder.iter_blocks(block_rows=4096):
        table = block.observations
        original_cells = block.raw_cells
        original_lines = block.raw_lines
        original_numbers = block.raw_values
        numeric_mask = block.numeric_valid
        physical_mask = block.valid
        source_lines = block.source_lines
```

The profile reuses the existing `ShockTubeRecorder` bounded physical-line CSV
iterator, source-hash checks and budgets, with separate source-specific schema
and conversions. It does not introduce another generic reader. Common
`ObservationTable`, `Variable`, origins, hashing and unit conversion remain the
contracts. Importing the profile needs no EOS, CFD, native ODH solver, h5py,
openpyxl or PDF parser.

`source.cases` parses the nominal case table from the original README at
runtime, retaining its source line, raw fields and hash. Nominal tanker gauge
pressure/nozzle diameter are distinct from measured release-rig/nozzle channels.
`source.positions` parses original sensor coordinates in metres in the stated
bottom-right-front frame, retaining source labels, roles, source lines and hash.
No global coordinate transform is inferred. The source's vertical-release
coordinate descriptions disagree in component order; the original table and
case descriptions remain separate. Exact source filenames, including the extra
leading zero in one case and seven-digit date tokens, are not repaired. Dates
also conflict between the README campaign narrative and metadata/filenames.

Four H2 header families (`H2Bottom2`, `H2Bottom7`, `H2Bottom9`, `H2Side7`) name
stations identified as temperature-only in the source coordinate table. Their
H2 output quantity/unit survives, but `.position` remains unavailable.
`.candidate_position` preserves the name-matched source row separately, with
an explicit role-conflict issue. No physical concentration location is silently
assigned from a temperature-only station.

Each row identity includes the DOI/version, source directory, original filename,
file SHA256 and physical source line. Line1 is the original header. The added
`source_index` is one-based data-row number, not a clock. `source_line_start` and
exclusive `source_line_stop` select an original-line window without resampling.
All arrays are read-only block-sized copies. A complete iterator verifies the
original file hash before and after reading. Mutation invalidates correspondence
with blocks already emitted.

## Clocks and distinct recorders

The original CSV header is `Time`, without a physical unit. Some pressure files
also contain `BlastTime` or the original spelling `Blast Time`. These are
exposed as `reported_time_coordinate` with
unit `source_time_unit_unresolved`. Published nominal sample rates and plausible
numerical step sizes are recorded as evidence; they do not silently establish
the clock unit, epoch, event zero or an exact cross-recorder mapping.

`block.as_time_series()` deliberately refuses conversion. A validated physical
seconds history requires additional independent source evidence and explicit
clock mapping outside this profile. Equal row numbers, equal numerical clock
values or source filenames do not establish simultaneous measurements.

The explicit blast clock is associated only with named blast-pressure outputs in that
header. Slow `Time` and blast clock remain distinct columns, with their own
missing/nonfinite masks. Wide rows can contain independent recorder data padded
to different lengths. The profile does not borrow the slow clock for blast
pressure or drop missing-clock rows to manufacture a single time series.

The source states that H2 concentrations were normalized and aligned to remove
sampling delay. The sampling tubes lead to instruments20m from the apparatus.
The export does not retain the original raw sensor signal, original delay or
an independently executable alignment rule. These processed H2 outputs have
`Origin.RECONSTRUCTED`. Do not fit a sensor lag to them while calling them an
unaltered recorder history.

## Quantities, masks and source roles

- H2 point-sampler outputs are source vol% converted to a volume fraction.
  Their basis retains normalization/alignment and sampling-line context. They
  are not O2, gas mass fraction, source feed or whole-room average. Outputs
  outside the source's0–100vol% range remain unchanged and masked.
- Thermocouples retain K; ambient weather temperature converts from Celsius.
  Peened wall, sampled-flow, nozzle and weather roles are distinct. A nozzle
  thermocouple is not automatically a bulk stagnation or phase state. Published
  temperature ranges and instrument descriptions disagree, so positivity masks
  do not certify calibration accuracy over every reported temperature.
- Release-rig/nozzle and box/blast pressures retain **gauge** meaning, converted
  from bar or mbar to Pa. Signed values remain signed. Ambient weather pressure
  converts from reported absolute mbar to Pa and retains its indication-only
  role. No ambient offset is silently added to a gauge reading.
- `FanFlowMeter` is ventilation air volume flow in L/min, converted to m3/s.
  It is not H2 release flow. Its actual/reference P/T and inlet/outlet boundary
  require evidence before mass conversion. An absent fan channel, including a
  clock-only FLMT file, does not become zero ventilation.
- `DPT`, `CJC1`, `CJC2`, `Var4`, `Var5` and other fields without a reviewed quantity/unit remain
  `reported_unknown` with unresolved units and origin. Their names do not
  authorize assigning pressure, valve state or an opening signal.
- Weather humidity converts percent to a fraction, wind direction degrees to
  radians, and wind speed retains m/s. Weather is publisher-labelled indication
  only; it is not a calibrated room sensor or an inferred thermodynamic boundary.

`numeric_valid` describes finite source numbers. `valid` also masks explicit
source-invalid cases, out-of-range H2 outputs, nonphysical absolute temperature/
pressure and conversion overflow. Blank, nonnumeric, nonfinite and formula-like
text remain raw with reasons. Nothing is filled, clipped, executed or smoothed.
Unknown physical roles retain explicit unresolved variables rather than a guessed
unit. These are ingestion/admission masks, not uncertainty estimates or noise sigma.
Finite unknown-role fields and indication-only weather outputs can remain valid
under this limited ingestion contract. Applications still need their own physical
admission gates; the source includes weather outputs above 100% RH and four
negative wind-speed values. No clipping or weather quality certification is applied.

The README lists48nominal cases, but numerical attachments exist for40case IDs.
Eight nominal cases have no numerical attachment; five ignited cases have no
FLMT attachment. Cases27and28 retain data despite the source marking them
invalid: physical channels are masked by default and original rows/numbers remain
available. Stations, samples and separate recorders are not experimental replicates.
All cases share one apparatus/campaign; fitting/held-out partitions must preserve
whole cases and independently justify shared-apparatus dependencies.

## Applicability to physical monitoring and ODH

The source can support point H2, point temperature, ventilation-output and
gauge-pressure comparisons **after** the corresponding input, clock and
observation operator are qualified. It does not supply measured H2 mass flow,
complete initial gas/liquid inventory, a bulk source enthalpy/spin state, the
raw concentration-alignment transformation, or measured room O2. Source pressure
and a nozzle diameter alone do not close those boundaries.

A homogeneous-room prediction cannot be validated against sparse axial point
samplers by labelling their average a room average. A local gas observation
also cannot be mapped directly to a cold two-phase bulk state. Forced-fan flow
and passive vent geometry represent distinct boundary conditions; a nominal
passive case is not zero air exchange. Pressure-peaking and ignited cases must
retain their own vent/combustion assumptions.

No observed O2 history is inferred as `ambient_O2*(1-H2)`. That would be a model
assumption about gas composition, humidity, mixing and observation basis, not
an independent oxygen measurement. The newly acquired records strengthen the
cryogenic H2 observation foundation without independently validating an ODH
solver, sensor alarm policy, cold-mixture EOS or complete source-to-room model.

The research report also records the existing26collection screening and new
primary-repository discovery attempts. A promising direct gas-O2 chamber dataset
has clear CC0 rights/checksums but inaccessible attachments; it is not described
as examined or acquired. Breathing-mask gas and liquid-phase biological oxygen
data are not substituted for enclosure observations.

```powershell
.venv\Scripts\python -m pytest tests/test_oxygen_observations.py -q
.venv\Scripts\python -X utf8 scripts/check_oxygen_observation_data.py --workers 2
```

The all-source replay checks the complete receipt/native metadata, each acquired
SHA256/MD5, every numerical row/column, units/roles/masks, separate reported-clock
coordinates and first8192row block stability with137versus4096row blocks.
Per-file atomic checkpoints support explicit `--resume` only when the receipt,
source and executed-code identities agree. Progress and detailed results remain
under ignored local directories. See [the qualification report](../research/oxygen_observation_data.md)
for executed counts, fingerprints and remaining evidence.

The executed complete replay read 195 CSV files for 40 actual case IDs, containing
8,150,693 recorder rows and 89,332,905 original cells. Of these, 85,607,986 were
finite numbers, 72,078,446 passed the profile's ingestion masks and 17,254,459
were masked. Counts include reported clock and unresolved-role cells; they are
not counts of independent experimental samples or qualified model comparisons.
All 198 attachments passed original SHA256 and publisher MD5 checks; source,
receipt and executed-code identities remained unchanged. The 18 original-fixture
tests and scoped Ruff checks passed. No measured O2 validation is claimed.


Source-bound block integrity: CryogenicRoomBlock instances are now issued only by
the checked recorder parser. Direct construction or dataclass replacement cannot
reuse a publisher-file identity with caller-supplied values. The deferred synthetic
contract lives in the shock-tube data case module and has not been executed. This
does not add oxygen measurements, synchronization evidence, or physical model claims.
