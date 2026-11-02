# SOE fault-operation source schema and targeted acquisition request

This is a prepared data-evidence request for the authors/repository maintainers of
Zenodo record [10.5281/zenodo.10648884](https://doi.org/10.5281/zenodo.10648884).
It has not been sent.

The record is CC BY 4.0 and lists eleven files totaling 1,092,175,741 bytes. Before
acquiring the full collection, please provide the following metadata and identify
the smallest suitable source attachments:

1. A file inventory linking each MAT file to a named fault condition, run/repeat,
   operating point and any included healthy baseline.
2. MATLAB version and MAT format, object/variable paths, class, dimensions,
   orientation, compression, and whether arrays contain raw measurements,
   resampled values, or derived/filtered channels.
3. Exact channel descriptions, units, sign conventions and scaling for cell/stack
   voltage and current, temperature, pressure, and flow. Please distinguish stack
   from per-cell voltage and identify the meaning of the six repeating units and
   the stated 80 cm² area.
4. Time coordinate units, origin, synchronization, sampling cadence, dropped-sample
   handling, trigger semantics, and timestamps or intervals for fault onset,
   transition, and recovery.
5. Sensor locations and calibration/uncertainty for temperature, pressure and
   flow; for gas flow, specify wet/dry basis, composition, reference temperature
   and pressure, and whether the quantity is standard or actual volume.
6. Humidity and steam-conversion definitions and electrode sides, plus the protocol
   identifying hydrogen starvation and silicon poisoning. Clarify whether fault
   labels identify commanded conditions or independently measured states.
7. Public download URLs, per-file byte sizes, publisher checksums, and confirmation
   that CC BY 4.0 applies to each requested file and any embedded third-party data.
   State separately the license/permission and attribution conditions for any
   newly authored schema sidecar, including permission to redistribute it.

For efficient review, first expose one small, complete representative file for each
fault and one matching healthy baseline, with the exact inventory and checksums. If
these define compatible channel/time semantics, then acquire additional repeats by
the same whitelist and digest contract. The public Zenodo API endpoint is
`https://zenodo.org/api/records/10648884`; retain the exact JSON bytes and
`files[].key`, `size`, `checksum`, and `links.self` values. Fetch file payloads only
from those record-provided HTTPS links after the minimum schema review; do not infer
an API endpoint or synthesize channel mappings from the article summary.

## Intended model boundary after the evidence arrives

Measured voltage/current at a known operating state could support a bounded
diagnostic comparator to the existing `HydrogenStack` electrochemical API, but only
after cell-vs-stack mapping, temperature, gas state, pressure and activity semantics
are established. Labeled time-series channels could separately support a measured
feature monitor in `h2physics.adapters.process_monitoring` after exact clock and
fault-label semantics are documented. Neither connection is currently authorized
by the public record summary alone. No fit, fault classifier, performance claim,
or model validation is admitted at this stage.
