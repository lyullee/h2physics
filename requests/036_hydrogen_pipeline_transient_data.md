# Request 036 — Licensed hydrogen pipeline pressure/flow transient data

## Need

The project implements isothermal gas-network inventories and is now adding a
finite-volume isothermal pressure-wave level, but lacks a rights-cleared,
independent measured H2 pipe dataset for axial pressure propagation and flow
transients. The existing open-channel release data can constrain a measured
source boundary only; it does not establish in-pipe wave behavior. Simulated
H2 network histories are not experimental validation.

An adjacent rights-cleared dataset is already staged: Guo, Mendeley Data V2,
[10.17632/x8zkds4fyn.2](https://doi.org/10.17632/x8zkds4fyn.2), which the
publisher licenses under CC BY 4.0. Its 12 CSV attachments are preserved with
publisher checksums in `research/data/buried-h2-blend-pipeline.toml`, but the
available files have only anonymous positional columns and no channel map,
units or clock definition. It is therefore a separate, unqualified buried-leak
candidate; it cannot satisfy this request's in-pipe pressure/flow measurement
requirement. The request remains open for a distinct dataset or an authoritative
field dictionary that establishes the needed pipe observations. The separate
source audit `docs/HYDROGEN_PIPELINE_TRANSIENT_DATA_GAP.md` records the current
Zenodo, GasLib/TRR154, Mendeley and NIST leads. It found open synthetic network
histories and adjacent measured sources, but no qualifying independent
experiment; no new payload was acquired.

## Requested data package

Please provide or identify one or more experimental pipe runs with explicit
CC0 or CC BY 4.0 (or a compatible license granting redistribution and
adaptation). The package should include:

1. Raw synchronized time histories of at least two axial absolute-pressure
   locations and an inlet/outlet mass-flow measurement. Preserve original
   samples, channel names, missing-value codes and clock information.
2. Pure H2 or fully specified H2-blend composition, initial/boundary pressure
   and temperature, valve or isolation trajectory, and run-level event times.
3. Pipe length, inner diameter, wall material/thickness, roughness, axial tap
   positions and relevant support/boundary conditions.
4. Instrument calibration, bandwidth, sampling rate, uncertainty and clock
   synchronization evidence.
5. Per-file publisher checksums, versioned DOI, citation/attribution text and
   unambiguous data license applying to the attachments.

## Python integration contract

The receiving implementation should add a checksum-required source reader that
preserves raw channel tokens and independent clock identity, and produces typed
observations with explicit units, pressure basis, sensor location and
uncertainty. It should bind to the existing `IsothermalSinglePhaseEOS` and
finite-volume pipe-wave APIs through a separate observation operator; the
reader must not silently derive pressure from concentration or flow. Keep the
dataset outside Git and distributions unless a separate release review admits
the payload.

## Acceptance evidence

- Source metadata, attachment license, version, attribution, file size and
  publisher checksum are recorded and independently audited.
- Reader tests reject altered files, schema changes, ambiguous pressure basis,
  nonmonotonic clocks and undeclared unit conversions.
- Hangang observation runs compare pressure histories by tap location and flow
  histories on their actual support, with prescribed sensor response and no
  extrapolation.
- Calibration and held-out runs are separated; report sensor uncertainty,
  timing error, pressure residuals, flow residuals, conservation residuals and
  numerical refinement separately.
- Report explicitly that a synthetic solver contract is software verification,
  not independent physical validation.
