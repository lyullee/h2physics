# Published microbial-electrolysis process observations

The source workbook has been acquired and its publisher MD5 and local SHA-256
verified. Only package/XML schema metadata was inspected during acquisition.
The new observation loader and two deferred validation cases have **not run**.
No model fit, native cell calculation or scientific accuracy check was performed.

Source: Miriam Cerrillo, Laura Burgos, Joan Noguerol, Victor Riau and August
Bonmatí, [three-chamber MEC nutrient-recovery dataset](https://doi.org/10.5281/zenodo.13981041),
Zenodo record13981041, CC BY4.0. The attribution, metadata checksum, original
URL and publisher/local file checksums are in
`research/data/microbial-nutrient-recovery.toml`. The original workbook remains
ignored under data/raw; no numeric publication table is copied into code/docs.

## Acquired schema and origin

The494,528-byte workbook has three worksheets. ZIP/XML inspection found26package
members,4,871,120expanded bytes and no formula cells in these sheets. This is
container/schema evidence, not numerical validation.

| Worksheet | Source support | Interpretation |
|---|---|---|
| Reactor_data | A1:CW293 | Reported reactor/compartment context; column meanings/phase windows need separate qualification |
| Potentiostat_data | A1:B32121 | Publisher instrument recording, with reported day coordinate and milliampere current headers |
| Minteq_Results | A1:X79 | Publisher-computed speciation/precipitation output; not independent experimental measurements |

The collection is classified **mixed**, not wholly measured. The new loader
admits only Potentiostat_data. Its32119row slots are retained; this is not an
assertion that32119independent valid samples exist. A complete numeric/missing/
clock audit and apparatus qualification remain deferred.

## Python observation interface

`h2physics.data.microbial_observations.iter_microbial_current(raw_root,
block_rows=...)` yields `MicrobialCurrentBlock` containing an actual shared
`ObservationTable`, original cached source cells, original Excel row numbers,
invalid-token reasons and the pinned source SHA. Source bytes are read into a
bounded immutable snapshot and verified before opening a read-only cached-value
workbook. Formulas/macros/links are never executed. No model is imported or run
by the loader.

`MicrobialCurrentBlock` is issued only by the verified iterator. Its measured
table must retain the reviewed source identity, exact sheet row labels, and values
and masks reconstructed from the retained cached cells. Direct construction or
dataclass replacement cannot attach the pinned publisher digest to caller-created
observations. The corresponding provenance contract is deferred to the data
profile and has not been executed.

The common observation reader owns masks and SI conversion. The shared unit
registry now supports numeric day coordinates and A/mA/uA currents. The returned
variables are `reported_time_s` and `reported_current_a`. Repeated/backward
coordinates and negative currents are retained; no sorting, deduplication,
interpolation, omission, smoothing or absolute-value rectification occurs.
Nonfinite/nonnumeric/missing cells remain invalid, not physical zeros.

These are observations, **not an automatically synchronized TimeSeries**. The
clock epoch, device/phase alignment, current port, polarity, sampling/averaging,
electrode area, calibration and uncertainty remain unresolved. Group identity
denotes the source recording, not an independently confirmed experiment phase.
Current is not current density; the model's electrode area must not substitute
for missing experimental geometry. Current alone supplies neither work nor H2
yield, Faraday efficiency, cathode kinetics or validated microbial growth.
No such derived model input is produced by this loader.

The supplied source is a three-chamber nutrient-recovery process. A conditional
single-cell batch model may not represent its membrane, ion transport, pH,
harvest or operating history. Qualify the actual observation operator and source
support before fitting/attaching it to `FiniteMicrobialCell`. Producer-issued
model trace verification and public phase-factory source attestation are separate
contracts; neither grants this dataset physical compatibility.

## Later cluster checks

The two metadata-only cases in `validation.cases.microbial_observations` use
profile `microbial-observations` and require actual `H2_CLUSTER_DATA_RAW_ROOT`.
They check pinned original rows/masks/SI scaling and modified-source rejection.
The integrity case also checks direct block construction and tampered replacements.
They remain unexecuted and do not establish physical validity. The existing
data extra supplies openpyxl; no additional dependency is introduced.

A separate CORA catalyst dataset at DOI10.34810/data2866 is now acquired under
the publisher's record-level CC0 grant. Its 23 files and publisher manifest are
hashed under ignored `data/raw/`; schema review finds LSV and current-density
series but no complete MEC hydrogen-production record. EIS frequency coordinates
are missing, and public OAI metadata exposes no file-level rights-override fields.
Keep it out of public distributions until exceptions are resolved. It supports
limited electrode-observation research only, not whole-cell MEC calibration or
validation. See `docs/MICROBIAL_CELL.md` and the detailed acquisition receipt.

### Python source-bound reader

`h2physics.data.load_cora_mec_electrode_dataset(raw_root)` admits the three
reviewed ODS workbooks only after checking their SHA-256 hashes. It returns six
LSV `ObservationTable` series, six current-density series and eight paired EIS
traces. Source workbook, sheet row, one-based column, condition label and raw
numeric token strings remain accessible. LSV potential is kept relative to the
reported Ag/AgCl reference; no electrode-area conversion is inferred. Current
density and elapsed days are converted through the shared unit registry to
A/m² and seconds while raw tokens remain attached to each series. An incomplete
terminal record remains masked and appears in the issue list.

The EIS export has no frequency coordinate. Its paired values are exposed as
reported impedance coordinates, with the source's second-header error token
preserved. The reader does not provide frequency-dependent circuit fitting.
The source snapshot is code-pinned for repeatable parsing; raw files remain
ignored and outside public distributions while file-level rights exceptions
remain unreviewed. These reader and integrity checks are implementation only.
The typed series constructors enforce source binding for direct API callers:
the workbook/hash pair, observation-table provenance and source-sheet row
identities must agree. The dataset also checks complete reviewed LSV, density and
EIS row ranges, measurement-column order and workbook column groups. These guards
do not establish scientific validity or third-party rights clearance.
Each LSV/current-density series also reconstructs its converted observation values
and validity mask from the retained original coordinate/response tokens. A copied
series cannot retain the pinned workbook identity after its numeric rows are changed.
The source-bound series and dataset constructors are loader-issued only, so caller-built
token/value pairs cannot claim the reviewed workbook hashes. The standalone `MecDataIssue`
and `MecImpedanceTrace` records remain constructible for diagnostics; manually authored
instances are not a loader-audited dataset receipt.
The deferred `mec-electrode-data-provenance` and
`mec-electrode-data-integrity` cases are scheduled for Nurion; they have not
been run and establish no scientific model validation.

```python
from pathlib import Path

from h2physics.data import load_cora_mec_electrode_dataset

dataset = load_cora_mec_electrode_dataset(Path("data/raw"))
trace = dataset.lsv_series[0]
potential, valid = trace.observations.column("potential_v")
current, current_valid = trace.observations.column("current_a")
```

The caller should retain each returned validity mask and source identity when
comparing observations with a candidate model. The trace labels are source
conditions; they are not guaranteed independent runs or an admitted calibration
grouping.
