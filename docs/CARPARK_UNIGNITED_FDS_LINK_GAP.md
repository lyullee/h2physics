# USN carpark unignited data: FDS boundary linkage gap

## Source, rights and audited scope

The source is Lach and Gaathaug, USN Figshare dataset [10.23642/usn.14405903](https://doi.org/10.23642/usn.14405903), version 2, CC BY 4.0. `research/data/carpark-unignited.toml` records the version, source metadata digest, publisher file receipts and acquisition state. Twenty-two of 23 listed files (the experiment MAT files and readme template) are cached locally; the separately listed file-handling guide remains unacquired. No guide text or figure is used here.

One exact file, `Exp03.mat` (3,174,901 bytes, SHA-256 `2c74d3575c00fe84757ffcd9580f36f29bd3be43af58f1c9814a1544ac799cb4`), received a metadata-only MATLAB v7.3/HDF5 inspection with the existing `inspect_hdf5_metadata` API. No experiment arrays were loaded. The source has an `MFM` structure with 49,999-row `mfr` and `time` channels; its unit cells label mass-flow rate `g/s`, pressure `bar` and density `kg/m^3`. `Vent` contains 49,999-row time and volume-flow channels, with volume flow labeled `m^3/h`. `S` contains 38 sensor entries; its source unit cells label sensor time `sec` and concentration `%vol`, alongside transfer, temperature, humidity, IDs and positions. These statements are limited to the selected file's metadata; they do not assert that every MAT experiment has identical fields.

## Candidate existing boundary and unresolved evidence

The existing obstacle-resolved API accepts an explicitly prescribed H2 mass-rate history through `HydrogenCFDSource`, and records concentration at caller-declared `CFDReceptor` positions. The observed fields suggest a possible USN flow-source to FDS receptor diagnostic. However, the selected MAT metadata does not supply enough evidence to construct that input without caller inference:

- `MFM.time` has no declared unit or zero/origin in its own metadata. Its clock's relation to the separate sensor, `Tank`, and `Vent` recorders is unknown. The sensor clock's `sec` label does not establish a synchronization transform.
- `S.pos` contains positions, but its coordinate unit, axis convention, container frame and registration are not declared in the acquired readme. Numeric scale alone is not used to infer metres or millimetres.
- The MAT unit label establishes mass-flow `g/s`, but not flow sign convention/direction, nozzle plane, post-expansion hydrogen temperature or inlet patch for the existing FDS source.
- The gas-sensor label `%vol` is preserved, but calibration, sensor response and equivalence to the FDS volume-fraction output need source evidence and row/clock mapping.
- The source readme identifies instrument families and MATLAB processing; it does not resolve these experiment-specific boundary and synchronization details. The file-handling guide is absent from the acquired scope.

For these reasons, there is no new MAT reader or flow adapter in this change. Metadata-only Hangang case `usn-carpark-unignited-fds-boundary-evidence-gap` verifies the CC BY receipt and the one-file audit record; it does not ingest values or execute FDS. A later bridge needs an authorized, versioned experiment-to-MAT schema/sidecar for time bases, sensor coordinates, source direction/plane, state and calibration before it can compare concentrations with FDS.
