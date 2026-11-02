# WSKBIJ Large-Scale Hydrogen Explosion Summary

## Source and rights

The source is DataverseNO dataset [10.18710/WSKBIJ](https://doi.org/10.18710/WSKBIJ),
version 1.0. Its record declares CC0 1.0 and identifies public access to the
listed files. This project acquired three selected files: the 6,753-byte
`00_Readme.txt`, the 21,165-byte `Experimental_results_.xlsx` summary, and the
207,853,888-byte `Test001.txt` trace. Each file has a publisher MD5 and a local
SHA-256 pin in
[`research/data/large-scale-open-hydrogen-explosion.toml`](../research/data/large-scale-open-hydrogen-explosion.toml).
The raw files stay in ignored local storage and are staged separately for the
Hangang ingestion cases. The summary case reads only the README and workbook;
the distinct Test001 case streams the selected trace. No other test time series
or camera video is included.

The 2024–2025 campaign includes delayed ignition of high-pressure hydrogen jets
in open atmosphere with obstructed and unobstructed arrangements. The README
describes two upstream pressure measurements with 0–250 barg instrumentation,
mass flow measurement for tests 1–27, four equal-spaced x-axis explosion-pressure
sensors, and acquisition synchronization using the ignition trigger. It states
that ambient temperature, humidity, and wind were not recorded. These are source
descriptions; this package does not reconstruct conditions from them.

## Parsed summary

`h2physics.data.read_wskbij_experiment_summary(raw_root)` checks both files'
exact byte lengths, publisher MD5 values, local SHA-256 values, the README's
dataset/license identity, and the workbook's reviewed OOXML table header. It
returns one immutable row per experiment with:

- test number;
- reported nozzle diameter in mm;
- reported reservoir pressure in bar, retained without deciding absolute versus
  gauge basis;
- ignition-position code, retained as a code rather than converted to a point;
- four signed pressure sensor summary values in kPa.

The pressure summary values remain signed raw observations; the reader does not
clip them, classify negative values, or treat them as transient samples. The
Hangang case `large-scale-h2-explosion-summary-source-ingest` verifies only
source identity, byte receipts, and table ingestion. It is not model validation.

## Model-link boundary

The summary workbook is not a time history. Although the README states that the
pressure records share an ignition trigger and the sensors are equally spaced
along x, the subset does not provide the sensor coordinates, origin, full test
geometry, ambient history, or per-test source flow histories. It also does not
turn a scalar pressure summary into a sample supported by an exact model clock.
The current FDS source interface does not predict flame acceleration or
open-field explosion pressure. The repository therefore makes no quantitative
comparison or fit from these summary data.

Any later pressure-time comparison needs a selected public test trace, the
matching test conditions, pressure-channel calibration and sample clock, sensor
coordinates in a known frame, and a receiving physical model whose predicted
observable covers this experiment. This acquisition does not make those
requirements disappear.

## Selected raw Test001 trace

The 207,853,888-byte Test001.txt member is DataverseNO file ID 268129 (persistent ID doi:10.18710/WSKBIJ/PIQIIP). Its publisher MD5 is 6a2b1e93513c33d9400ba8abf4b9d082; the acquired raw-file SHA-256 and transfer gzip receipt are recorded in the TOML manifest. The summary case checks the manifest's complete three-file acquisition inventory and total bytes but opens only the README and workbook. The reader h2physics.data.read_wskbij_test001_trace(raw_root) verifies the trace's exact size and hashes, then yields rows incrementally without allocating the complete trace. It retains the absolute timestamp string separately from the sample-relative time column, four signed pressure channels in kPa, and PT1/PT2/MFR/trigger channels in their original voltage form. An optional trailing empty token is preserved where present.

The deferred Hangang case large-scale-h2-test001-pressure-trace-source-ingest consumes every row and reports source cadence and basic channel counts. It does not convert voltage, align the absolute timestamp to a plant clock, assign sensor coordinates, fit an explosion source, or compare pressure with FDS. The README calibration requires a channel offset that is not present as a row-specific value in this selected trace; ambient conditions and geometry mapping remain unresolved.
