# USN ignited pressure-peaking measured-flow boundary

## Source and rights

The source is Lach and Gaathaug, *Hydrogen Safety: Pressure Peaking Phenomena—ignited releases*, Figshare record [10.23642/usn.17934047.v1](https://doi.org/10.23642/usn.17934047.v1), licensed CC BY 4.0. The file-level source record is `research/data/pressure-ignited.toml`. This implementation uses the already acquired `HTE341USN0015READ191111.mat` (40,666,968 bytes; SHA-256 `3c03a1fbc0164622e0354505b9272d0deb44dffbfe1baaf33e591533b83be5a4`; Figshare file ID 32655707). Attribution remains required. Raw publisher attachments are kept outside release artifacts.

## Reader boundary

`h2physics.data.load_pressure_ignited_mat(...)` accepts this exact attachment and its reviewed profile. The common MATLAB-v5 decoder checks file bytes and SHA-256 before and after parsing, the complete variable-name inventory, numeric column counts, metadata cell size, and an explicit memory budget. The ignited profile retains the SIGMA matrix as 999,999 rows by 7 columns and GEN3i as 78,894 rows by 3 columns. The MAT file also contains a top-level numeric Tavg variable with shape 999,999 by 1. The publisher file-handling guide does not document this variable units, derivation, or alignment to the other recorders. The reader preserves its exact name and values as immutable raw data without assigning temperature semantics or using it in a projection. Unknown variable names and missing required fields are rejected with raw names in the error. It rejects deviations from the raw metadata vectors:

- SIGMA dimensions: `[s]`, `[g/s]`, `[bar]`, then four `[oC]` entries; labels: `time`, `Mass Flow`, `Pressure at Coriolis`, then four `Temperature` entries. The file-handling guide maps these channels to time, Coriolis mass flow, Coriolis pressure and thermocouples T1–T4. This supports selecting the mass-flow channel but does not establish pressure basis or physical placement.
- GEN3i dimensions: `s`, `v`, `kPa`; labels: `Time`, `T1`, `P1`. The guide identifies column 1 as time and column 3 as overpressure in kPa. The recorded second-column label `T1` and dimension `v` remain preserved, but the guide does not establish its meaning for this export; code therefore leaves it unresolved and unused. The recorder clocks are not aligned.

These vectors are checked against the acquired MAT metadata, rather than inferred from matrix width. The source's `[oC]` spelling is preserved as recorded.

`PressureIgnitedRun.iter_flow_blocks(...)` exposes only SIGMA measured mass flow with exact source row numbers and recorder times. The separate GEN3i matrix is retained for later evidence work, but this flow projection never reads it. The reader does not infer flow direction, pressure basis, release-plane conditions, ignition time, sensor response, or thermodynamic state.

## Finite-source projection

`h2physics.adapters.project_ignited_usn_flow(...)` converts the documented SIGMA flow channel from g/s to kg/s and can form measured `IntervalMassSource` bins using caller-selected `left_hold`, `right_hold`, or `trapezoid` quadrature. Requested endpoints must coincide with exact rows on that SIGMA clock. A negative measured value is retained by the reader and rejected by the projector; it is never clipped or treated as positive release. The caller must supply source location/release-plane evidence, a representative gaseous-hydrogen state and its evidence, clock placement, and quadrature selection. These choices do not imply that the selected source boundary represents the experiment without further review.

Deferred Hangang case `usn-ignited-measured-flow-finite-source-contract` requires the staged attachment at `/scratch/CLUSTER_USER/h2physics-source-attachments/pressure-ignited/1/HTE341USN0015READ191111.mat`. It checks receipt, schema, exact source rows, clock support and projection currentness using synthetic state/location placeholders. It is an API boundary check, not a nozzle, flame, dispersion, or enclosure-pressure validation.

## Separate overpressure evidence gap

No pressure or temperature signal enters the finite-source adapter. Comparing ignition or enclosure overpressure with a model requires experiment-specific sensor identity and location, recorder-clock synchronization, filtering/calibration and baseline definitions, ignition timing, release state and spatial boundary mapping. Those are not established by the acquired MAT and file guide, so the present code makes no overpressure comparison or model claim.
