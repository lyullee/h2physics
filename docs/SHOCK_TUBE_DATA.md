# ELVHYS liquid-hydrogen rupture observations

`h2physics.data.shock_tube` reads the acquired version1.0 of
[DOI10.18710/M5LOLM](https://doi.org/10.18710/M5LOLM), by Eugenio Torres de
Ritter, Andreas Friedrich and Manuel Ignacio Ferraro Porcel de Peralta, KIT.
The pinned Dataverse metadata explicitly declares CC0-1.0. The repository
receipt, original checksums and authors remain attached to the qualification.
External observations and audit JSON stay ignored and outside distributions.

The actual experiment is a heated LH2 tube with a rupturing aluminium
membrane inside containment. Eight date-qualified runs have an unignited/inert
label and four have an ignited/oxidizing label. Repeated three-digit run codes
on different dates represent different runs. A station, recorder or sample is
not an independent experimental replicate. All runs share one apparatus and
campaign. The supplied numerical files do not establish premixed detonation,
DDT, ignition probability or a CJ velocity measurement.

## Python objects and bounded access

```python
from h2physics.data.shock_tube import ShockTubeCollection

collection = ShockTubeCollection(
    "research/data/elvhys-shock-tube.toml", "data/raw")
collection.verify_sources()  # All acquired SHA256/size checks, offline.
recorder = next(r for r in collection.recorders if r.kind == "PRESF")

for block in recorder.iter_blocks(block_rows=4096):
    observations = block.observations
    original_lines = block.raw_lines
    original_cells = block.raw_cells
    original_numeric_values = block.raw_values
    source_line_numbers = block.source_lines
    sensor_series = block.series
```

`ShockTubeRecorder` also accepts one reviewed, date-qualified file and an
optional expected SHA256. Every file has its own clock identity. Minutes are
converted to seconds by the common unit converter. The signed numerical clock
and its original engineering-unit text remain available. Its epoch, offset,
alignment procedure and relation to membrane rupture are unresolved. Two
files containing zero do not acquire a common physical clock by that fact.
No baseline, time shift, sorting, resampling or smoothing is applied.
Standalone recorder construction is useful for local signal inspection, but its
observations identify the input as `caller-supplied-local-file`; a filename and
matching header alone do not authenticate the study. The collection loader issues
the publisher study/run identity only after validating the acquired file record
against its pinned receipt. `ShockTubeRun` summaries are likewise constructed only
from the parsed metadata table; direct construction or field replacement cannot
claim its source digest and physical line identity.
`ShockTubeBlock` values are issued only by the reviewed recorder parser. Direct
construction and `dataclasses.replace` cannot attach a source digest and physical
line identities to caller-invented parsed measurements. This seals the ingestion
lineage for the returned block; it does not qualify the experiment's physical
interpretation. The deferred contract `shock-tube-block-loader-provenance` in
`validation/cases/shock_tube_data.py` uses a synthetic CSV fixture to check local
recorder attribution, run-summary issuance and immutable block provenance.

`iter_blocks(source_line_start=..., source_line_stop=...)` selects a physical
source-line interval. Line1 is the original header and data begin at line2;
the stop is exclusive. Selected rows retain their actual source lines and
full file/hash identities. Defaults bound each block to4096 rows, each record
to8192 characters, each file to1million data rows and each file to50MB.
Explicit budgets are validated. A file hash is checked before and after each
completed reading iterator, including bounded windows. Source mutation during
iteration invalidates correspondence with already emitted blocks.

An `ObservationTable` preserves invalid clocks and channel values through masks.
`TimeSeries` creation requires every selected clock to be finite and strictly
increasing. The predecessor source time is retained so a nonincreasing clock
at a block or selected-window boundary is rejected. Invalid observations are
never removed to manufacture a usable clock. Raw text, formula-like strings
and nonfinite numbers remain inspectable; CSV formula strings are not executed.

## Channel meanings and unresolved references

- `TEMP`, including the one `TEMPL` filename, contains five tube diode channels
  and two jet diodes in K. These are point instruments. The stated diode range
  is2–500K. Values outside it remain numerically unchanged with invalid masks
  and reasons. Zero-filled channels do not become physical0K observations.
- `PRESS` contains static tube, feed, counterpressure, containment, vacuum and
  flange pressures plus a differential-pressure channel. Bar and mbar are
  converted to Pa. Gauge values retain their gauge basis; ambient pressure is
  not added. Feed pressure has a header/README absolute-versus-gauge conflict.
  Counterpressure has a header-versus-instrument-range conflict. Differential
  pressure retains its sign; calibration/range and port-elevation conventions
  require further evidence.
- `PRESF` contains six tube stations and five containment pressure-wave stations.
  Although all export labels say `bar_a`, containment signals include signed
  negative values. The API therefore exposes `reported_pressure` with its exact
  label and unresolved dynamic baseline/calibration. Signed values remain valid
  numerical waveform observations. They are not qualified thermodynamic
  absolute-pressure states and cannot silently satisfy a `pressure` variable.
- `MICR` contains reported sound levels in dB for the last two runs. Weighting,
  reference pressure and averaging are unresolved. It is not a linear pressure
  trace or an independently resolved acoustic energy.

`collection.positions` parses the original README coordinates at runtime and
retains sensor ID, source line and supporting-file hash. Axial coordinates
reference the tube bottom flange. The reported radial entries for wall sensors
equal the stated tube inner diameter, so their geometric convention needs
clarification. They are preserved without a radius correction. Containment
pressure-station coordinates require the referenced D4.8 drawing, which is not
among the acquired attachments. No station distance is invented.

`collection.runs[run_id].conditions` exposes source-reported burst pressure,
initial containment O2 and initial containment temperature as reconstructed
summary observations. Membrane description and batch marker remain separate.
The parser retains combined membranes rather than substituting thickness from
the filename code. These summaries are not independent raw pressure or gas
measurements. Initial containment temperature is not initial tube-H2 temperature;
containment O2 does not supply a homogeneous tube H2/oxidizer composition,
humidity, residual gas, spin composition or a gas/liquid inventory.

The supporting campaign CSV contains non-UTF8 bytes. The profile uses an
explicit reversible Latin-1 byte mapping for that file and UTF8 for the README;
this does not assert that the publisher declared a character encoding. Source
bytes and hashes remain authoritative.

## Applicable comparisons and verification

The native `ObservationTable` and `TimeSeries` objects support comparisons of
a qualified prediction with the same station, channel quantity/reference and
independently justified recorder clock. Diode response and pressure sensor
processing may need explicit observation operators before transient comparisons.
No noise sigma, waveform propagation speed, pressure-zero correction or
cross-recorder synchronization is estimated here. Whole date-qualified runs
must remain grouped when selecting fitting and held-out cases; independence
across common apparatus and membrane batches remains a separate question.

An equilibrium fully reacted premixed-gas CJ calculation lacks the measured
upstream composition/temperature and the resolved BLEVE/transient physics needed
for these data. A transient pressure maximum must not be fitted to or labelled
as a measured CJ pressure. The profile improves data access and qualification;
it does not establish experimental validation of rupture, fire or detonation.

Run the offline replay with:

```powershell
.venv\Scripts\python scripts/check_shock_tube_data.py
```

The script checks all42 acquired attachments and their publisher checksums,
all38 numerical CSVs, actual source rows/masks/ranges and clock increments,
block-size stability for each file's first8192 rows, and source/code hashes
before/after. It records progress durably under ignored `artifacts/`.
The acquired scope is42/133 listed files;91 video attachments are omitted.
Original TPC5/TDMS/instrument workbooks and the D4.8 report are not supplied
by this acquired set. Exact results and source fingerprints are recorded in
[the qualification report](../research/shock_tube_data.md).
