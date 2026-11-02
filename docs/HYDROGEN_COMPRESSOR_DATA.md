# Hydrogen compressor evidence and data gap

This note separates public device/process evidence from reusable raw measurements.
No private station data is stored in the repository.

## Acquired experimental series

The MHC two-stage metal-hydride compressor record is already acquired as version 1.2
under CC BY 4.0 (`research/data/hydride-compressor.toml`). Its 29 experiments and
instrument exports support observation work for thermochemical compression. The
reader in `h2physics.data.hydride_compressor` preserves units, recorder identity,
missing fields and unresolved clock/pressure/flow bases. It is not a mechanical
diaphragm-compressor map and does not by itself validate pressure-vessel or station
equipment models.

## Commercial diaphragm field-data candidate

The 2026 field study at DOI `10.3390/technologies14090529` describes a 90 MPa station
diaphragm compressor and its condition-monitoring channels. Its data-availability
statement says the underlying records are internal to the research team and not public.
This candidate is therefore discovery-only in
`research/data/h2-diaphragm-field.toml`: no data were requested or downloaded, and no
article figure values were digitized for model use. The article's CC BY terms cover the
article; they do not grant rights to separate internal records.

A second field study, DOI `10.3390/hydrogen7040157`, describes long-term pressure,
temperature and mass-flow observations from a commercial high-load station compressor.
No public raw-data archive was located during this review. Raw-data availability and
redistribution terms for that record remain unverified, so it is not treated as an
acquired or reusable dataset.

## What is still needed for equipment qualification

For an independently useful mechanical-compressor comparison, acquire a rights-cleared
time series or map with explicit suction/discharge pressure basis, hydrogen composition,
mass flow, shaft/electrical power, speed, cooling and stage temperatures, valve/control
state, sensor locations, calibration uncertainty and synchronized clocks. Transient
startup, shutdown and capacity changes are needed for dynamic event models. The existing
public field-study discovery does not establish those fields or release terms. Aggregated
station performance summaries are not interchangeable with compressor-level operating
traces.

## Primary-source records

- Li et al., *Data Symmetry Enhancement-Based Abnormal State Detection of High-End
  Hydrogen Compressors Under No-Fault Samples*, Technologies 14(9), 529 (2026),
  [publisher article and DOI](https://doi.org/10.3390/technologies14090529).
- Wan et al., *Operating Characteristics of Diaphragm Compressors in Hydrogen Refueling
  Stations Based on Actual Operational Data*, Hydrogen 7(4), 157 (2026),
  [publisher article and DOI](https://doi.org/10.3390/hydrogen7040157).
- Fleming et al., *Experimental Dataset for a Two-Stage Metal Hydride Hydrogen
  Compressor*, Zenodo version 1.2, DOI `10.5281/zenodo.19036733`; the version, rights,
  archive checksum and schema audit are recorded in `research/data/hydride-compressor.toml`.
- NREL's [Hydrogen Station Composite Data Products](https://nrel.sitefinity.cloud/hydrogen/infrastructure-cdps-all)
  provide station-level aggregated performance and maintenance summaries; they do not
  replace an instrumented compressor's thermodynamic signal history.
