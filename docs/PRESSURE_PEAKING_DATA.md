# USN unignited pressure-peaking observations

`h2physics.data.pressure_peaking` loads the acquired version-1 MAT/XLSX exports from
Agnieszka Lach and Andre Vagner Gaathaug,
[Hydrogen safety: Pressure Peaking Phenomena-unignited releases](https://doi.org/10.23642/usn.17932439.v1),
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
`research/data/pressure-unignited.toml` pins rights evidence, original file SHA-256,
publisher MD5, authors, source version and acquisition omissions. The external raw files
and any normalized caches remain outside Git and distributions.

The acquired set contains eight MAT and nine XLSX data files, plus two DOCX guides.
The source experiment numbers are filename identifiers, not a claim of independent
replication or complete measured/model boundary information. MAT files for source
experiments 00002 and 00009 remain omitted. MAT coverage is 00003/00004/00005/00006/
00007/00008/00010/00011; XLSX coverage is 00002/00003/00006/00007/00008/00009/00010,
with two separate sensor exports each for 00009 and 00010. No automatic pairing or clock
alignment follows from the matching numbers.

The executable offline audit and its actual row counts, checksums, SI stream fingerprints,
observed invalid values and clock issues are in `research/pressure_peaking_data.md`:

```powershell
.venv\Scripts\python scripts/check_pressure_peaking_data.py
.venv\Scripts\python -m pytest tests/test_pressure_peaking.py -q
```

The audit consumes every acquired data row and verifies SHA-256, publisher MD5 and size
for all nineteen attachments. It also verifies the saved repository metadata checksum.
An audit success means the recorded files passed this ingestion profile, not that their
scientific ambiguities were resolved or a physical model passed measured validation.

## MAT recorder interface

The source arrays called `SIGMAdimensions` and `GENdimensions` hold unit strings; the
arrays called `SIGMAunits` and `GENunits` hold channel labels. Both identities are retained.
The loader rejects changed shapes, labels, units, unsupported MAT variables, excessive
compressed/decoded size and invalid/non-increasing numerical recorder clocks.
MAT recorder and run objects are issued only by `load_pressure_mat`; bounded recorder
blocks are issued only from those recorder objects. Their source hashes and source-row
identities therefore cannot be attached to caller-invented arrays by direct construction
or copied through `dataclasses.replace`. This protects the declared acquisition lineage;
it does not establish that the publisher's measurements are scientifically complete or
that the independent recorder clocks are synchronized. The deferred adversarial contract
is `pressure-mat-loader-only-provenance` in `validation/cases/pressure_peaking.py` and
uses a small synthetic MAT fixture.

| Export | Acquired numeric columns | SI channels | Qualified interpretation |
|---|---|---|---|
| SIGMA | time in s, Mass Flow in g/s, Pressure at mass flow meter in bar | signed_mass_flow in kg/s, meter_reported_pressure in Pa | Signed instrument flow; meter/outlet pressure reference unresolved |
| GEN3i | time in s, P1 in kPa | exported_p1_reported_overpressure in Pa | Exported reported P1; guide/export column conflict unresolved |

The handling guide describes GEN3i column 3 as overpressure, while each acquired numeric
export has only two columns. Its four unit labels and 35 channel labels describe more
than the two exported columns; neither the trigger nor the other labelled signals is
reconstructed. The exact metadata are retained and the discrepancy is an explicit issue.
Reported pressure has a required measurement basis and is not exposed as absolute or
qualified differential pressure. No ambient pressure is added. Negative meter-pressure
values remain present, with their frequency in the audit.

```python
from pathlib import Path
import tomllib

from h2physics.data.pressure_peaking import load_pressure_mat

receipt = tomllib.loads(Path("research/data/pressure-unignited.toml").read_text("utf-8"))
item = next(f for f in receipt["files"] if f["name"] == "HTE242USN_00003_READ190621.mat")
run = load_pressure_mat(
    Path("data/raw") / item["relative_path"],
    source_id=f"{receipt['doi']}:{item['name']}",
    experiment_id="USN-source-experiment-00003",
    expected_sha256=item["sha256"],
)

for block in run.sigma.iter_blocks(block_rows=50_000, time_window_s=(20.0, 30.0)):
    series = block.series                       # existing immutable TimeSeries contract
    source_rows = block.source_rows              # original 1-based MATLAB rows
    observations = block.observations            # existing ObservationTable contract
```

`first_row`/`last_row` and `time_window_s` select closed intersections without interpolation,
sorting, extrapolation or resetting the source clock. `block.observations` materializes
source row strings only for that bounded block. Its rows contain recorder time followed
by SI values, with a per-row source identity, the declared source experiment grouping,
file hash, profile identity, matrix identity and independent recorder clock.

Compressed MATLAB v5 matrices require complete SciPy decoding. The default budgets are
100 MB compressed file size and 160 MB total decoded numeric matrices. `iter_blocks`
bounds subsequent SI conversion, masks and row identities; it is not a claim of streaming
decompression. No normalized multi-million-row table is retained by the all-file audit.

Finite signed mass-flow output remains numerically valid even when negative. This does
not designate it as a nonnegative accident source or an actual reverse release. Startup
and offset behavior need instrument qualification. Missing/nonfinite samples are masked;
neither a zero replacement nor a baseline correction is applied.

## Selected mass-flow boundary for existing safety models

`h2physics.adapters.project_pressure_peaking_flow_to_finite_source(...)` can bind a
selected nonnegative window from the exact CC BY 4.0 SIGMA MAT export
`HTE242USN_00003_READ190621.mat` (SHA-256
`f74643684fac53ec8e57893f6647b33fd0313da3cb5a1038c0b8c44ce425f1f0`) to the
existing `IntervalMassSource`. The reader reports signed Coriolis mass flow as
kg/s and preserves its recorder time in seconds. The caller chooses the source
window and left-hold, right-hold, or trapezoidal bin quadrature; the source uses
the exact recorder clock. Requested window edges must coincide exactly with
measured row timestamps; mid-sample, extrapolated or interpolated endpoints are
rejected. Any negative or missing flow in the selected interval rejects
projection; no clipping or absolute-value
transformation occurs. Pressure channels are not consumed.

The caller must separately support the flow-meter-to-release-plane mapping, the
representative gaseous-H2 state, and the finite source location. This is a
bounded source boundary for downstream safety calculations. It does not compare
measured and modeled pressure, reproduce enclosure pressure peaking, or qualify
a dispersion/overpressure model. Deferred Hangang contract
`usn-unignited-measured-flow-finite-source-contract` checks the source receipt
and reader-backed non-row-aligned window rejection; it does not issue a valid
finite source or run an accident model.

## XEN workbook interface

`load_pressure_concentration(...)` uses the same explicit `source_id`, `experiment_id`
and optional expected checksum arguments. It qualifies the single-sheet schema and returns
`PressureConcentrationWorkbook`, whose `iter_blocks(block_rows=2048, first_row=4,
last_row=None)` reads every selected original worksheet row. Metadata from source rows 1/2
and literal measurement headers from row 3 remain available on the returned object.
The two actually observed Celsius glyph variants are recognized; their literal headers
are preserved. Other header/unit changes require a profile review.

All seventeen columns survive as declared `Variable` objects in `block.observations`.
Percent values become fractions; Celsius becomes K; AH kPa becomes reported Pa; mV/mA/mW
become V/A/W. The transfer calibration in V/W, correction ratio, iteration, alarm, battery
and electrical diagnostic columns retain separate meanings. `Pt100` and `Tsens` are
instrument temperatures, not automatically room or gas temperatures. `AH` retains its
source label and unresolved pressure-like semantics. The firmware cell's Excel date
representation is retained as metadata; it is not used as an experiment date.

`Output (%)` becomes `reported_h2_concentration`, quantity `reported_concentration`,
unit `1`, with a basis that records XEN H2 mode, point-sensor observation and unresolved
volume/mole convention. It is not silently declared a well-mixed room volume fraction.
Negative and above-one values remain unchanged in the values array but fail the declared
physical fraction domain mask. Missing/nonnumeric cells remain NaN/masked; nonpositive K
temperatures and out-of-domain RH/battery fractions are masked separately. Source alarm
codes are preserved without an invented code interpretation or automatic deletion of rows.
The configured device/factory ID conflict in 00009CONC remains explicit.

Column B contains raw local time-of-day strings although the handling guide describes
seconds. `block.raw_clock_strings` retains those exact values; the observation table also
contains seconds since local midnight, with unresolved date/timezone. Every file/device
has its own clock ID. Clock duplicates, backward steps, invalid strings or a possible
midnight crossing remain issue-bearing observations. `block.as_time_series()` requires a
finite strictly increasing block clock and refuses detected violations, including a
violation at the preceding block boundary. It does not unwrap midnight, remove rows or
repair the chronology. Original worksheet row numbers establish identity because source
iteration counters can repeat.

## Scientific limits and continuation

SIGMA, GEN3i and each XEN export are independent recorder histories. A shared experiment
label, matching numerical zero or similar wall-clock time does not establish a common
material/event clock. There is no automatic synchronization API because the inspected
primary guides do not supply an evidence-bearing mapping. Use the existing common-clock
sampling functions only after independently qualifying and recording that mapping.

Required evidence still includes enclosure and vent geometry, actual opening/source
conditions, instrument locations and response, pressure references, the GEN3i column
discrepancy, sensor gas-fraction convention/calibration and common event clocks. A point
sensor is not an enclosure inventory operator, and a flow-meter pressure is not a nozzle
stagnation boundary. No baseline subtraction, concentration spatial averaging or measured
model validation is justified by this ingestion alone. The authored tests verify contracts,
unit conversions, bounded source-row selection, schema/hash/budget gates, masks and clock
failure retention using synthetic fixtures only.

The workbook receipt can be created only by `load_pressure_concentration` after
schema and source-hash qualification. Bounded concentration blocks can be created
only by that receipt's row iterator. Both issuance paths consume one-use tokens;
the receipt rechecks its captured source file and identity, while each block seals
its observation table, clock strings, clock identity and issues before
`as_time_series()` exposes a projection. The deferred synthetic XLSX contract is
`pressure-concentration-loader-provenance` in `validation/cases/pressure_peaking.py`.
