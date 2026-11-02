# Hydrogen engine figure-data semantic mapping request

Prepared request for the authors and TUdatalib maintainers for public dataset
[10.48328/tudatalib-2291](https://doi.org/10.48328/tudatalib-2291). Not sent.
The eight small CC BY 4.0 bitstreams are acquired and source-hash-pinned, but the
HDF5 inventory is structural only. Please provide an authoritative sidecar/data
dictionary resolving these fields before any numeric observation is coupled to an
engine or thermal API:

- For `Fig2.h5`, specify crank-angle zero and reference (TDC/other), pressure sensor
  location, mixture/condition mapping, and whether mean/std summarize cycles,
  simulations, or another population. Clarify how the values relate to per-cycle
  pressure traces, if those exist.
- For `Fig3.h5`, define what lifetime is measured, its time origin, sensor/location,
  and the exact independent temperature/mixture condition for every pair.
- For `Fig5.h5`, identify the flame-map scalar quantity and units, coordinate origin
  and orientation, meaning/order of the three crank-angle indices, and image/map
  coordinate transform.
- For `Fig6.h5` and `Fig7.h5`, define reference and differential temperature
  equations, sensor locations, and each crank-angle/after-impingement coordinate
  reference and sample pairing.
- For `Fig8.h5`, identify the heat-flux sensing plane/location, time/angle origin,
  how flame power is defined, and whether its samples share the plotted angle grid.
- For `Fig9.h5`, provide coordinate and clock arrays, spatial locations, units and
  exact correspondence of flame-power and maximum-heat-flux samples.
- For all figures, provide the mixture/operating point, test/run/cycle ID, repeated
  sample count, averaging/filtering procedure and uncertainty definition.
- Confirm whether rights for the component datasets/third-party assets follow the
  record-level CC BY 4.0 grant; identify any excluded figures or fields. State
  separately the license/permission for the proposed sidecar and whether it may
  be redistributed with attribution; the record grant is not assumed to cover a
  newly authored sidecar or its embedded third-party content.

Please return a small versioned machine-readable sidecar keyed by exact HDF5 filename
and dataset path. Include file/member hash, units, quantity, coordinate/reference,
location, run/condition identity and rights note for each mapping. Do not replace the
original HDF5 bytes. If this sidecar cannot be provided, mark each field unresolved
rather than infer semantics from its publication figure title.

The project metadata API is
`https://tudatalib.ulb.tu-darmstadt.de/server/api/core/items/dbec6035-12f9-4ba6-b776-7b4ec4b11979`;
the acquired inventory identifies the exact ORIGINAL bitstreams and hashes. Any
new sidecar should have its own repository record/version and checksum. This request
seeks evidence only; it does not request or authorize a fitted engine correlation.
