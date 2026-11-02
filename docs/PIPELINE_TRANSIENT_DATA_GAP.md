# Experimental data gap: hydrogen pipeline pressure/flow transients

## Scope

The current pressure-wave and network-transient families need synchronized
pressure and mass-flow observations inside a hydrogen-carrying pipe. A record
with only an imposed source, leak discharge or downstream concentration does
not independently validate the pipe's axial pressure-wave propagation,
compressibility closure, wall interaction or linepack response.

## Reviewed public candidates

| Candidate | Evidence and rights | Decision |
|---|---|---|
| Buried hydrogen-blended natural-gas pipeline leak/dispersion, Guo, Mendeley Data V2, DOI `10.17632/x8zkds4fyn.2` | The publisher's versioned record explicitly declares CC BY 4.0. The repository has already staged all 12 listed CSVs outside Git and matched their publisher SHA-256 values (18,314 B total; receipt `research/data/buried-h2-blend-pipeline.toml`). The available schema audit identifies UTF-16, tab-separated, headerless numeric tables with five or six positional columns, but no data dictionary or units. | Keep as an acquired but unqualified candidate for buried H2-blend release/dispersion work. The measurements cannot be assigned to axial pipe pressure or mass flow from the available documentation, so this does not fill the pressure-wave/linepack evidence need. Do not fit or score a physical model against anonymous columns. |
| Open-ended rectangular-channel hydrogen release, DataverseNO DOI `10.23642/USN.26117989`, V1 / Figshare V2 | Official record identifies CC BY 4.0 and temporal mass-flow, filling-pressure and 29 sensor concentration data. This repository already acquired its 23 listed data files (49,243,504 B) under `research/data/hydrogen-channel.toml`, with a checksum-bound lossless reader and a finite measured-source projection. | Reuse only for its channel release/source/concentration scope. It is not a pipe-mounted pressure-wave or linepack dataset; another reader would duplicate existing work. |
| H2-SimNet hydrogen-blend transport-network data, Zenodo DOI `10.5281/zenodo.17871393`, V2 | Official record describes MATLAB/Simscape-generated pressure and mass-flow sensor histories, scenarios and a 509.2 MB ZIP. Its Rights section does not state a license. | Do not acquire, stage, or use the payload until the record or authors provide explicit data-reuse terms. It is simulated evidence, not measured validation in any case. |
| Large-scale pipe filling/emptying, Science Data Bank DOI `10.57760/sciencedb.13651` | Primary article describes synchronized 100 Hz flow and pressure signals for an air/water pipeline and says the data repository is openly accessible. The repository landing page inspected in this review does not state a dataset license; the article's CC BY license covers that article and does not establish a license for separate files. | Do not redistribute or stage raw attachments without data-specific rights. Even with clearance, this is a water/air two-phase transient, not hydrogen-gas evidence; use only as a separately scoped hydraulic code comparison. |

The literature review on hydrogen pipeline transport identifies the shortage of
experimental pure-hydrogen transient flow evidence, especially for rapid
compressible transients. See the [primary review](https://doi.org/10.1016/j.ijhydene.2024.04.140).
The absence of an admissible payload here is a current repository limitation,
not evidence that no such experiment exists.

The Guo V2 buried-pipeline release is the closest rights-cleared pipeline-scale
safety data currently staged in the repository, but its 12 attachments have no
field dictionary, units, clock definition, sensor locations or experiment
independence metadata. Its bytes and source identity are preserved without
assigning meanings to anonymous columns. It can become useful to a release or
dispersion observation operator only after the data owner supplies the channel
map; it cannot be promoted to in-pipe pressure/flow validation based on its
title or the publisher's CC BY 4.0 grant alone. See the
[`buried-pipeline dataset review`](BURIED_PIPELINE_DATA.md).

## Data needed for model qualification

A useful submission should include, at minimum: raw synchronized time and units;
gas composition; initial and boundary pressure/temperature; flow measurements
with calibration and uncertainty; multiple axial pressure taps with positions;
pipe inner diameter, length, wall material/thickness, roughness and support
conditions; valve/opening or isolation command history; sensor transfer
functions and clock offsets; calibration files; repeat-test identity; and
explicit CC0/CC BY data terms covering redistribution and derived observations.
Keep calibration and held-out transients separated by run or condition. The
acceptance request is in [Request 036](../requests/036_hydrogen_pipeline_transient_data.md).
