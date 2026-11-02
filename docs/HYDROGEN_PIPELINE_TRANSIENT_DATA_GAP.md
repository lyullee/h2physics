# Hydrogen pipeline pressure/flow transient data search

## Decision

No newly identified source satisfies Request036's measured-data gate: time-aligned
absolute-pressure traces at two or more axial taps, inlet/outlet mass flow, a
known pure-H2 or fully specified blend, pipe geometry and initial/boundary
conditions, instrument metadata, a versioned file receipt, and an explicit
redistribution license. No file was downloaded in this search. This is a
bounded public-source search result, not proof that such data do not exist.

The inventory of examined public sources and immutable source metadata is in
`research/data/hydrogen-pipeline-transient-data-gap.toml`. It distinguishes
measured-but-incomplete sources from synthetic transient inputs and rejects
both as independent experimental validation.

## Repository and catalog leads

### H2-SimNet: hydrogen-blend transient sensor series, simulated

The open Zenodo v2 record [H2-SimNet](https://doi.org/10.5281/zenodo.17871393)
describes multivariate pressure and mass-flow histories for a simulated
hydrogen-blend transport network. Its official Zenodo API reports `access_right
= open`, `license = cc-by-4.0`, and a single 509,236,976-byte
`H2-SimNet-Dataset.zip` with publisher MD5
`15bc64a3afc9e2990c9db66eb37617de`. The repository description says the histories
were generated using MATLAB/Simscape, with CSV and Parquet representations;
they are not measured pipeline data. It may be considered later for a
simulation-input or anomaly-detection interoperability exercise, but not for
physical model validation. The archive was not downloaded because it does not
meet Request036's experimental-evidence purpose; inner archive members and
exact channel schema were therefore not audited.

### GasLib transient extensions: network schedules, not H2 field measurements

The [TRR154 Instationary Gas Networks repository](https://github.com/TRR154/InstationaryGasNetworks)
and [Transient Data page](https://www.trr154.fau.de/transient-data/) expose XML
`.bcd` boundary records containing time-dependent pressure and/or flow and
`.state` snapshots, with XSD schemas. Its README describes the inputs as an
extension to GasLib network instances. The [GasLib source page](https://gaslib.zib.de/)
states that its networks are benchmark instances, mostly based on distorted
real-network descriptions and stationary nominations; they are not a package
of sensor observations from a transient experiment. GasLib is an open solver
benchmark source, not independent observation evidence for hydrogen pipe-wave
accuracy. The repository declares Apache-2.0, while GasLib independently
declares CC BY 3.0; review the applicable scope and attribution of each file
before any redistribution. Nothing was downloaded.

### Portuguese H2-blend corridor results: hourly steady-state optimization

Mendeley Data record [Impact of Natural Gas Composition on Green Hydrogen
Blending Capacity in the Portuguese High-Pressure Gas Network](https://data.mendeley.com/datasets/568k39mky7/1)
is described as CC BY 4.0 and supplies hourly steady-state optimization
results for a five-segment, six-node corridor. Its variables are model outputs
from an NLP study, not experimental sensor readings; hourly snapshots do not
provide transient pressure-wave propagation or synchronized measured flow.
This is potentially useful as a separate network scenario/model-reproduction
lead, not Request036 validation. No file was downloaded.

### Existing measured leak dataset: useful source boundary, wrong observation plane

The project's existing [Guo buried H2-blend pipeline record](../research/data/buried-h2-blend-pipeline.toml)
has CC BY 4.0 files and measured leak/cloud observations. The available numeric
columns still lack a field dictionary, units, clock semantics and an
observation map; the record does not provide the requested pair of in-pipe
pressure taps and line-flow trace. Do not reinterpret anonymous columns to
close Request036.

### NIST transient-flow metrology: facility information, no matching raw run

The [NIST Transient Flow Facility](https://www.nist.gov/programs-projects/transient-flow-facility)
reproduces high-pressure dispenser flow/temperature/pressure transients for
meter testing. The public project page is a facility description, not an
experiment repository; its available field-test-standard record documents
helium tests at the facility and hydrogen dispenser field work, but does not
publish the pipe-wave dataset required here. No raw files or file license were
found on the reviewed pages.

## Reproducibility and next action

Searches covered official Zenodo, GasLib/TRR154, Mendeley Data, and NIST pages
plus the 2024 peer-reviewed pipeline-methods review cited in the request. The
review also identifies scarcity of experimental unsteady pure-hydrogen pipe
flow data. Search terms included hydrogen pipeline transient pressure/flow,
pipeline wave experiment, blend-network transient dataset, and repository/API
records. No figures were digitized and no model-generated series was labeled
experimental.

Request036 remains open. Reopen ingestion only after a custodian supplies a
machine-readable experimental package with file-level license, immutable
version/checksums, measured pipe geometry and tap locations, synchronized
pressure/flow channels with units, and run boundary/clock/instrument metadata.
The required reader and held-out observation comparison contract are already
specified in `requests/036_hydrogen_pipeline_transient_data.md`.

## Primary records

- [H2-SimNet Zenodo v2 record](https://zenodo.org/records/17871393) and [official Zenodo API](https://zenodo.org/api/records/17871393).
- [TRR154 transient network data page](https://www.trr154.fau.de/transient-data/) and [source repository](https://github.com/TRR154/InstationaryGasNetworks).
- [GasLib network instances and source/license statement](https://gaslib.zib.de/).
- [Mendeley Portuguese blend-corridor data record](https://data.mendeley.com/datasets/568k39mky7/1).
- [Existing Guo buried-pipeline CC BY 4.0 record](https://doi.org/10.17632/x8zkds4fyn.2).
- [NIST Transient Flow Facility](https://www.nist.gov/programs-projects/transient-flow-facility).
- [Hydrogen gas transport in pipelines: experimental-method review](https://doi.org/10.1016/j.ijhydene.2024.04.140).
