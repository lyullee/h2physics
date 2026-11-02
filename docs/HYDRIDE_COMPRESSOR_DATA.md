# MHC compressor observation profile

`h2physics.data.hydride_compressor` reads the acquired MHC v1.2 archive through
Python objects, immutable `ObservationTable` blocks and explicit source schemas.
It qualifies ingestion of the 29 experiment workbooks. It does not supply hydride
kinetics, an equipment model, a parameter fit or independent model validation.

```python
from datetime import datetime
from h2physics.data.hydride_compressor import HydrideCompressorArchive

with HydrideCompressorArchive(archive_path) as archive:
    with archive.experiment(8) as experiment:
        for recorder_blocks in experiment.iter_blocks(
            experiment.raw_sheet,
            datetime_origin=datetime(1970, 1, 1),
            block_rows=2048,
        ):
            for block in recorder_blocks:
                observations = block.observations
                # Each recorder has its own clock basis and source-row identities.
                # Select the explicit schema/variable required by an observation
                # operator before comparing it with a physical model.
```

Use `HydrideCompressorArchive.experiment()` for source-backed analysis: that path
verifies the pinned outer archive before issuing a workbook snapshot, checks the
member digest/CRC, and rechecks outer bytes when the archive context closes. The
lower-level `HydrideCompressorWorkbook` constructor is intended for controlled
member snapshots and authored fixtures; it verifies the supplied member payload
against `member_sha256`, but its `archive_sha256` and member name are caller-provided
labels and do not independently prove that the member came from that outer archive.
Do not treat a directly constructed workbook as archive-verified unless the caller
has retained and checked that enclosing archive receipt separately.

The origin is a caller-declared naive calendar origin, not a UTC epoch assertion.
It changes the numeric coordinate of each calendar reading without aligning any
recorder. The origin and clock kind are part of variable compatibility, so tables
with different calendar origins cannot be joined as the same clock basis.
The common epoch in this example preserves calendar offsets. Resetting
each recorder to its first sample would hide those offsets and is not performed.
Duplicate, decreasing and missing clocks survive as observation rows. No
interpolation, synchronization, baseline correction, sign clipping or automatic
conversion into `TimeSeries` occurs. `start_row` and `stop_row` select an inclusive
window of original worksheet row numbers; `block_rows` bounds each returned grid
chunk. Every grid row survives, including empty formatted padding, which is not
counted as a physical measurement.

`archive.overview()` returns the source overview member/hash, literal source cells
and case-number mapping. `experiment.notes()` returns the pre-header source cells
for its protocol and qualification notes. These runtime source records should
remain with ignored local analysis artifacts. Case, archive member, worksheet,
logger export and sensor identities have distinct roles:

- Row IDs contain the outer archive hash, member path/hash, worksheet, recorder
  export group and original row number. Repeated sheet names and sensors cannot
  collide across members. All exports of one experiment share its experiment ID.
- `experiment.schemas(sheet)` preserves group/hardware/alias headers, column
  numbers, units and their evidence cell identities. Literal aliases and unknown
  Graphtec channels survive. Sensor names do not establish bed/shell positions or
  a spatial average. Geometry and an observation operator need separate evidence.
- `LoggerBlock.raw_cells` retains its clock fields followed by channel fields in
  schema order. `invalid_reasons` follows observation-column order, including the
  clock. Missing, string, nonfinite, nonphysical absolute-temperature and declared
  defective-sensor fields stay masked without dropping the row. Numeric invalid
  values and original fields remain accessible. Negative flow and reported
  pressure remain signed.
- `formula_cells` preserves literal formulas at profiled cells without evaluating
  them. Cached formula results in a raw measurement channel are masked as
  independent measurements. Selected-cycle exports carry `Origin.RECONSTRUCTED`;
  they are copies/selections of the same experiment and cannot be split into an
  independent held-out validation set against their raw parents.

The source declares different engineering units and reference roles:

| Source field | Observation quantity/unit | Qualification boundary |
|---|---|---|
| P-4, `bar` | reported pressure, Pa | Absolute/gauge basis unresolved |
| P-5/P-1/P-2/P-3, `barg` | reported pressure, Pa | Gauge output; reference atmosphere unresolved |
| HTF MF-1/MF-2, `l/min` | volume flow, m3/s | Liquid volume output; no density or mass conversion |
| MFC, `ln/min` or `nl/min` | reference volume flow, m3_ref/s | Normal reference P/T unresolved |
| Temperature, `°C` | temperature, K | Source sensor identity retained; no bed/shell mapping |
| Labview `Seconds` | source counter, s | Reported elapsed counter with unresolved epoch |

The runtime `Seconds` variable uses quantity `time`, unit `s` and a basis declaring
its source counter/epoch role. Neither a Pa scale nor a generic hydrogen heading
establishes a model's absolute pressure, gas mass flow, composition or inventory.
`Variable.require_compatible` rejects those changed quantity/unit/basis requests.
Different raw and selected export layouts are checked against the actual reviewed
schemas rather than filled from a generic template.

Experiment 1 is explicitly an argon thermal case. Its defective Picolog T-2_1 is
masked using the source note reference while its reported value remains available.
Experiment 2 is a thermal case without hydrogen; its fill gas remains unresolved.
Its additional AV thermometer calibration export has a separate calendar date and
clock. It is not merged with its AG experiment export or called a new physical
experiment. Source descriptions identify the capacity/compression cases as
hydrogen experiments without qualifying purity or spin composition.

Experiments 6 and 7 contain a loading-station export at M/N/O instead of the usual
three MFC columns. It has a time-of-day clock without a date. The profile returns
`source_time_of_day` in seconds since midnight, leaves rollover/date mapping
unresolved and never borrows the Labview date. Selected-cycle copies omit that
clock. The Flow-3 values are comma-containing strings; they remain raw and masked
as numeric data until decimal/thousands syntax has evidence. Missing units remain
unresolved reported fields. Experiment 3's explicit ISO-like Graphtec calendar
strings decode as supplied, and experiment 4 retains its two selected cycles and
the literal `nl/min` spelling.

The Date/Time fields also contain unformatted Excel serial dates/datetimes and
fractional-day times. These are decoded using the workbook's declared Excel epoch,
not a guessed calendar or recorder offset. This includes the experiment 8 Labview
date field and selected recorder fields in experiments 4, 19 and 22. Experiment
22's explicit day.month.year recorder strings use that reviewed format. The raw
field types, original values, declared encodings and epoch remain available. This
decodes source serialization only; source gaps, repeated/backward clocks, calendar
disagreements and time-of-day rollover remain unrepaired. The authored tests also
exercise the distinct 1904 workbook epoch.
Numeric calendar decoding is confined to the reviewed Date/Time columns. Generic
scalar counters and loading-station time-of-day numbers do not become Excel
calendar timestamps; an unreviewed elapsed-time recorder header is rejected.

Mass/heat balances, efficiencies and summary sheets are audited separately as
stored workbook content. Formula caches and parameters derived using the same
signals are not independent observation targets. The supplemental PCI workbook
may support separate material-characterization qualification, but is outside this
logger profile. Its presence does not qualify an equilibrium fit or demonstrate
an independent kinetic/thermal comparison. Protocol notes also matter: incomplete
histories, unrecorded phases, outlet paths and hardware changes cannot be repaired
by fitting sensor curves.

In the inspected mass-balance layout, the `Volume [L]` field is an apparatus-volume
input alongside material mass and bulk-density inputs; it is not an observed gas
throughput. Its `Normliterfactor L/mol` is an author-supplied calculation constant.
Neither field establishes the MFC calibration reference P/T or makes the calculated
absorbed hydrogen mass an independent measured target. No volume/mass conversion
is exported by this logger profile. Detailed qualification still needs instrument
reference conditions and calibration/uncertainty, pressure-reference evidence,
recorder clock mappings, sensor geometry/thermal roles, loading-station numeric
syntax and documented initial/incomplete-cycle histories. Those are receiving
evidence requirements; no external request or author contact has been made.

The default archive digest/size match the reviewed acquisition receipt. ZIP
preflight rejects unsafe paths, duplicate paths, symlinks, encryption and excessive
members/expansion. Limits bound outer bytes (450 MB), expanded outer directory
(500 MB), individual source members (25 MB), each expanded workbook (250 MB), each
inner member (60 MB), dimensions (100,000 rows/200 columns), and compression ratio
(2000). These are ingestion budgets, not scientific admissibility criteria.
Members are CRC-checked snapshots; archive context exit rechecks its SHA-256.
Consume within both context managers to close metadata streams and obtain that
final check. The complete workbook snapshot and openpyxl shared-string metadata
are resident for one experiment; this is bounded workbook decoding, not constant
memory XML for all purposes. Links, macros, CAD and included programs never run.
No new dependency is required beyond the existing optional `data` extra.

Run the local complete audit after acquisition:

```powershell
.venv\Scripts\python -m pytest tests/test_hydride_compressor_data.py -q
.venv\Scripts\python -X utf8 scripts/check_hydride_compressor_data.py
```

The audit runs at most two experiment snapshots concurrently (`--workers 1` or
`--workers 2`). It atomically saves an ignored per-experiment checkpoint after
each completed workbook. After an interrupted process, `--resume` accepts those
results only when host/test/script hashes, metadata and reverified source-member
identities match. It never turns a partial checkpoint into a complete report.
For long local jobs, retain stdout/stderr and use a detached hidden process so a
terminal-session lifetime does not erase in-memory progress. A vanished process
without the final report is not successful completion.

The script verifies the receipt/metadata, all file member hashes/CRC, all 29
workbooks and their worksheets, raw/selected/calibration schemas, clock and mask
anomalies, numeric/formula caches and source stability. It records source/test/
script hashes at begin/end. Detailed source cells and diagnostics stay in ignored
`data/processed/hydride-compressor/v1.2/profile-audit.json`; the original aggregate
audit is [in the research record](../research/hydride_compressor_data.md).
External raw and normalized observations stay outside Git and distributions.

Attribution: Lukas Fleming,
[Experimental Dataset for a Two-Stage Metal Hydride Hydrogen Compressor, v1.2](https://doi.org/10.5281/zenodo.19036733),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source metadata points
to [the tagged source repository](https://github.com/LukasFleming/MHC-Dataset/tree/v1.2).
The acquisition receipt retains the repository metadata hash, publisher checksum,
retrieval time and archive hash. Rights permission and successful ingestion leave
the independent validation status unresolved.

## Conditional comparison with the finite compressor model

`h2physics.adapters.compare_mhc_temperature_to_compressor_bed(...)` provides a
source-bound diagnostic between a measured raw logger temperature and
`HydrideCompressorTrace` bed solid temperature. It accepts a raw export only
from the pinned MHC v1.2 archive, retains the source row IDs, requires kelvin
values and source/member hashes, and samples model output only on retained time
support. It refuses extrapolation and rejects reconstructed selected-cycle and
calibration exports. The caller must supply independent evidence identifiers
for sensor-to-bed mapping, clock alignment, and model interpolation. MHC
channel labels alone do not locate sensors on the bed; no heat-transfer fit or
compressor validation is claimed. Deferred Hangang case
`mhc-compressor-temperature-observation-contract` checks manifest/API
availability, opens a three-row workbook window through the verified archive
reader without extracting any member, and confirms that reader-issued archive
blocks cannot be cloned or directly constructed with caller-supplied hashes.
