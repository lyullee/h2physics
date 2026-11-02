# DataverseNO large-scale H2 explosions: FDS observation link gap

## Primary record and rights

The source is Lach, *Replication dataset for: Large-Scale Hydrogen Explosion Experiments: Obstructed Releases in open atmosphere*, DataverseNO version 1, [DOI 10.18710/WSKBIJ](https://doi.org/10.18710/WSKBIJ). The primary record declares CC0 1.0 and lists 59 public files totaling about 96.86 GB. Its description identifies 2024–2025 delayed-ignition high-pressure hydrogen jet experiments with obstructed and unobstructed releases, varying nozzle size, obstacle distance and ignition position, plus high-speed video and high-frequency pressure measurements. See `research/data/large-scale-open-hydrogen-explosion.toml` for the dataset receipt and selected publisher file records.

## Selected files and access status

The 6.6 KB `00_Readme.txt` (MD5 `5642ccb734e8449bf52c0be83e4d0f23`) and the
20.7 KB `Experimental_results_.xlsx` (MD5 `73ee4f29ca08612f46b7a37980cbe4df`)
were acquired from the official DataverseNO per-file API after the record page
timed out. Local SHA-256 and exact byte lengths are pinned in the manifest.
They contain source description and per-test summary rows. No other test trace
or multi-gigabyte camera video was acquired. The README, workbook, and
Test001 trace are the three selected raw files and remain in ignored local
storage; the summary case reads only the README and workbook, while separate
ingestion cases cover Test001. The exact acquisition boundary and parsed schema
are documented in [`LARGE_SCALE_H2_EXPLOSION_SUMMARY.md`](LARGE_SCALE_H2_EXPLOSION_SUMMARY.md).

## Existing boundary and required evidence

The existing `HydrogenCFDSource` in the obstacle-resolved FDS adapter can represent an explicitly specified post-expansion H2 mass-rate boundary around a declared obstacle mesh, and the native result exposes receptor H2 volume fraction. A future limited pre-ignition comparison could be considered if the raw TXT/workbook defines measured rates, experiment IDs, geometry, sensor positions, units, clock alignment and sensor calibration. The measured source must also map to an evidenced post-expansion inlet patch and temperature appropriate for the low-Mach model.

The selected workbook rows include four signed pressure summary values in kPa,
but they are not time samples and the workbook does not supply pressure-sensor
coordinates. Ambient conditions are absent; mass-flow instrumentation was used
only for tests 1–27. The dataset's pressure and delayed-ignition outcomes do
not map to the host FDS adapter's current acceptance boundary: it does not
implement jet choking/nozzle expansion, combustion, flame acceleration or
explosion overpressure. No pressure or camera comparison is admitted.
`large-scale-h2-explosion-summary-source-ingest` reads the selected source bytes
and verifies their schema and receipts. The separate
`large-scale-h2-explosion-fds-observation-link-gap` case records the remaining
physics and geometry limitations. Attribution is retained as good practice;
embedded third-party rights within individual files remain unreviewed.

## Test001 source history now selected

A source-bound reader and deferred ingestion contract cover the official raw Test001.txt trace (file ID 268129, PID doi:10.18710/WSKBIJ/PIQIIP). The reader hash-checks the exact raw member and streams rows; it preserves signed kPa pressure channels and raw PT1/PT2/MFR/trigger voltage values. The case reports schema, cadence and channel completeness only. Absolute timestamp text is kept separate from sample seconds. A pressure-time or FDS comparison remains blocked by sensor coordinates/calibration, full geometry and ignition mapping, ambient conditions, source-flow interpretation and missing compatible explosion physics. The staged file is checked against the publisher MD5 and pinned SHA-256 by that case.
