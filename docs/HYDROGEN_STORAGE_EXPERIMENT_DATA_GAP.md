# Hydrogen storage experiment data: coverage and gaps

Audit date: 2026-11-01. This note records repository holdings and primary-source
leads for measured metal-hydride PCT/cycling and cryogenic hydrogen tank storage
time histories. It is a data-availability audit, not a model validation result.

## Existing measured records

| Record | What is present | Rights / local receipt | Scope and limitations |
| --- | --- | --- | --- |
| [AB2 hydride tank cycling](https://data.mendeley.com/datasets/8km9z62tct/1), DOI `10.17632/8km9z62tct.1` | Three workbooks, 59,809,253 bytes total; about 1 s measurements for flow-through absorption/desorption, including time, commanded/reported flow, pressure, five shell thermocouples and cumulative uptake/release fields. | Mendeley declares CC BY 4.0. Existing manifest records 3/3 local SHA-256 values matching the publisher checksums. | Genuine equipment cycling traces. Flow reference conditions, pressure basis, measurement uncertainty and shell-to-bed temperature relation are not fully established. Not an independent, qualified hydride model validation. |
| Hydride compressor experiments, DOI `10.5281/zenodo.19036733` | Existing receipt describes 29 experiment workbooks and raw logger channels with channel units and separate clocks. | Zenodo record declares CC BY 4.0. Existing archive receipt SHA-256 was rechecked locally and matched. | Measured compressor/equipment operation, not a PCT isotherm series. Recorder offset, calibration export, sensor placement and flow reference/calibration remain unresolved; no independent equipment qualification follows from possession of these files. |
| [LH2 cryo-neutron cell data](https://data.mendeley.com/datasets/z5zc7kk76g/2), DOI `10.17632/z5zc7kk76g.2` | Three selected CSVs: 5,391 DAQ rows at nominal 1 s, 1,165 image rows at nominal 10 s, and six image-window rate rows; selected total 499,266 bytes. | Mendeley declares CC BY 4.0. The existing receipt's three selected-member SHA-256 values were rechecked and matched. | Measured phase-change in a small conical neutron-imaging cell. It is not a pressure-vessel blowdown or storage-tank self-pressurization dataset. DAQ and image clocks are separate; time zone and phase-rate/error units remain unresolved. |
| PRESLHY LH2 discharge records, DOI `10.35097/1187` | Existing source record includes cold discharge experiment archives. Three selected 80 K ZIPs total 549,391,239 bytes; their local SHA-256 values match the recorded checksums. | KIT repository receipt identifies CC BY 4.0; file checksums are retained in the repository record. | Cryogenic hydrogen discharge/blowdown is useful for discharge model work, but does not supply a long-duration stationary storage heat-leak/self-pressurization history. Sensor temperature is not automatically bulk-fluid temperature; some flow channels were unavailable or require reconstruction. |

The exact byte total for the three selected PRESLHY archives is the sum of the
manifest values: 127,786,640 + 185,741,321 + 235,863,278 = 549,391,239 bytes.
The selected files and hashes are listed in the source receipt, rather than
duplicated here.

## PCT and storage tank gap

No source located in this audit provided all of: (1) a measured PCT/isotherm or
cycling record, (2) explicitly reusable dataset rights, (3) downloadable original
numeric observations with a documented schema and material/sample identity, and
(4) enough pressure/loading/temperature basis and measurement uncertainty to make
an independently interpretable validation case.

The repository's `hydride-pct-simulation` record is explicitly simulated. It may
support source-reader and regression work only; it is not experimental validation.
The Sandia ML-HydPARK Zenodo v0.0.5 record (DOI `10.5281/zenodo.10680097`)
declares CC BY 4.0 and provides a curated composition/capacity/thermodynamics
table, but not raw PCT runs, process time histories, measurement uncertainty,
or complete per-row experiment metadata. A checksum-bound, lossless reader now
exposes its source tokens for screening; this does not make the table a substitute
for PCT validation. See [ML-HydPARK screening interface](ML_HYDPARK_SCREENING.md).
The official DOE Hydrogen Storage Materials Database/HydPARK landing materials
describe a relevant literature database, but this audit did not establish a
reusable raw-file package and explicit data license for full experimental PCT
curves. No extraction from publications was attempted.

For cryogenic tank storage, NASA's [ZBOT overview](https://www.nasa.gov/glenn/glenn-expertise-space-exploration/physical-sciences-program/fluid-science/zero-boil-off-tank-zbot/)
describes self-pressurization and pressure-control experiments. Its experiment
data portal states that access is for authorized users, and ZBOT-1 used
perfluoro-n-pentane (PnP) as a simulant fluid. NASA's [ZBOT data portal](https://gipoc.grc.nasa.gov/wp/msg/zbot/)
is therefore neither an openly downloadable data package nor a hydrogen-fluid
validation source for this project. NASA MHTB/SHIIVER reports provide valuable
test descriptions and plotted results, but no openly licensed raw time-series
package was identified in the reviewed primary-source repositories. Plots and
report tables were not digitized.

## Decision and reopening criteria

Keep the acquired measured records within their documented physics scope. Do not
present simulated PCT workbooks, curated scalar materials databases, publication
plots, cryogenic simulant data, or discharge traces as direct measured LH2 tank
storage validation. Reopen this gap when a primary repository supplies the raw
machine-readable observations, explicit dataset-level rights, file inventory and
checksums, schema/units, sample and boundary conditions, and instrument
calibration/uncertainty needed for a named validation case. A dataset can still
be useful for qualitative comparison or method development before it meets that
threshold, provided the narrower evidence status is stated.

## Local evidence audit

On 2026-11-01, local SHA-256 values were recomputed against the existing receipts
for the three AB2 files, the hydride-compressor archive, three selected cryo-
neutron CSVs, and the three selected PRESLHY cold-discharge archives. All matched
the recorded source checksums. This hash audit confirms byte identity only; it
does not establish calibration, physical applicability, scientific validation,
or permission beyond each source's stated grant. No new raw data were downloaded
or added by this gap audit.
