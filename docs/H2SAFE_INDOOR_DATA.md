# H2SAFE indoor-release observations

The `h2physics.data.load_h2safe_indoor_series(...)` reader exposes one
experiment from the acquired [H2SAFE indoor-release sensor archive](https://data.openei.org/submissions/8799).
The record is attributed to David Peaslee, Munjal Purnkant Shah, Ian Palin,
John Drumm, Umang Patel, James Stewart, Donggyu Jang, Adam Bailey, and William
Buttner and is identified by the repository as CC BY 4.0. Source records and
their current archive/metadata checksums are in `research/data/h2safe-indoor.toml`.
The publisher page presents both acquired files under the submission's CC BY 4.0
license. That rights review and its evidence URLs are recorded in the manifest;
the data provider does not publish file checksums, and a direct checksum/header
request was denied, so local size and SHA-256 pins serve as integrity receipts.

Pass the complete repository ZIP's expected SHA-256 and choose a fixed
repository-relative experiment name such as `Lab1_Small/test1.csv` or
`Lab2_Large/test3.csv`. The reader checks the full archive size and hash,
rejects members outside its reviewed allowlist, maps columns to that lab's
sensor IDs, and preserves the source tokens next to their numeric values.
Missing markers remain missing. Sensor coordinate tokens are retained as
reported and are not transformed.

The file format alone does not establish the sensor's reported concentration
basis or calibration. The source time unit, clock alignment,
sensor response, coordinate frame/units, release boundary, and room ventilation
conditions are not inferred by this loader. These data are observations for
future source qualification; ingestion does not validate dispersion physics or
constitute a detector performance assessment.

The repository's data-suitability review identifies the experiments as helium
surrogate releases. These rows therefore do not represent measured hydrogen
dispersion or hydrogen-sensor response, and cannot directly validate a hydrogen
release model. Any later surrogate use requires an explicit similarity argument
and independently supported sensor/species response; this reader makes neither.

The deferred Hangang case `h2safe-indoor-source-bound-experiment-ingestion`
reads the actual pinned archive. The raw data directory is excluded from the
source archive, so a cluster campaign must stage the ZIP and pass its path
explicitly. The reader adds no third-party runtime dependencies.
