# SOE fault-operation dataset: acquisition and schema gap

## Public source

Zenodo record [10.5281/zenodo.10648884](https://doi.org/10.5281/zenodo.10648884),
“SOE operation under 4 faulty conditions,” is listed as open CC BY 4.0. Its record
describes polarization, temperature, pressure and flow-rate measurements from an
electrolyzer with six repeating elements and 80 cm² active area. Named conditions are
hydrogen starvation, high steam conversion, humidity at the oxygen electrode, and
silicon poisoning of the fuel electrode. The record lists eleven files totaling
1,092,175,741 bytes; no payload is acquired in this repository.

## Why no reader-to-model adapter is admitted yet

The source manifest confirms the 11-file listing and license, but not the file contents.
The nine MAT files have no audited variable names, shapes, time axes or row/column
meaning. No source evidence links each file to the four fault conditions or to a healthy
baseline. The summary does not declare voltage and current as cell-level or stack-level,
flow as mass or volume, flow reference conditions, sensor locations, clocks, calibration,
fault onset, or repeat identity. The 990-byte `FirstLine_split.mat` and the
`Repeating_unit_voltage_Comments.png` also need schema/rights review before interpreting
or reusing them.

Existing candidate interfaces are `HydrogenStack` for electrochemical voltage/current
comparison and `h2physics.adapters.process_monitoring` for causal multichannel monitoring.
Neither is linked to these source files: without condition mapping, channel units and
clock/operating-state context, a mapping would require inference. The existing
`soe-fault-operation-data-schema-gap` Hangang case verifies the recorded metadata gap
only; it reads no payload, performs no model calculation and makes no performance or
fault-diagnosis claim.

## Concrete acquisition request

The prepared request in [`requests/soe_fault_operation_data_request.md`](../requests/soe_fault_operation_data_request.md)
has not been sent. It asks the authors/repository maintainers for:

- a file-to-run/fault/baseline inventory and the smallest complete representative subset;
- MAT format/version, object paths, array shape/orientation and raw-versus-derived status;
- voltage/current level, units, sign and active-area mapping;
- pressure/temperature sensor location and calibration;
- flow quantity, wet/dry/composition basis, and reference pressure/temperature;
- synchronized time semantics, sampling cadence, and fault start/recovery annotations;
- per-file sizes, publisher checksums and confirmation of file-level rights.

The authoritative metadata endpoint is
[`https://zenodo.org/api/records/10648884`](https://zenodo.org/api/records/10648884).
The file-list endpoint is
[`https://zenodo.org/api/records/10648884/files`](https://zenodo.org/api/records/10648884/files).
Preserve exact response bytes and file keys, sizes, checksums and publisher `links.self`;
download only an explicitly whitelisted small representative subset after schema/rights
review. Do not infer content URLs or bulk-download 1.09 GB before the mapping is resolved.

If a future source subset establishes a common state/clock and cell-versus-stack semantics,
add a pointwise comparator to the existing provider or monitoring API with exact file and
member digests. Keep fault classification and parameter fitting out until their labels,
measurement definitions and independent operating references are evidenced.
