# Open-channel hydrogen release data

The curated V2 record is Henriksen, Fossum, Åkervik and Bjerketvedt, *Experimental
Data of Hydrogen Dispersion in an Open-ended Rectangular Channel*, Figshare, DOI
[10.23642/usn.26117989.v2](https://doi.org/10.23642/usn.26117989.v2). The record declares
CC BY 4.0. Attribute the dataset and link its license when reusing permitted files;
the publisher listing and file-level receipt remain authoritative for asset scope.
Acquired archives are held under ignored `data/raw/` and excluded from packages.

`h2physics.data.load_hydrogen_channel_case()` reads one publisher-listed ZIP after
checking its exact filename, byte count and the checksum algorithm declared by the
resolved `Dataset` attachment. It also requires the dataset key, metadata URL and
SHA-256 to match the pinned Figshare V2 record and reconstructs the full 23-file
name/URL/size/MD5 list from those retained metadata bytes. A caller-constructed
`Dataset` with changed or incomplete attachment records is rejected even if its DOI
and license labels match. The current Figshare listing uses MD5; the loader
retains that publisher checksum and also computes a local SHA-256 fingerprint. A
separately pinned SHA-256 can be supplied when available. It admits one safe CSV
member, records its SHA-256, keeps both original header rows,
retains the raw text for every data record, and exposes a numeric view with a validity
mask. Returned arrays use immutable backing storage; `require_current()` checks their
source-bound fingerprint. Result construction requires explicit numeric values and
a boolean mask and reconstructs both from the retained raw cells, so boolean arrays
cannot masquerade as measurements.
The source-bound `HydrogenChannelCase` is issued only by this validating archive
loader. Direct construction and dataclass replacement cannot reseal altered source
or publisher digests; callers should obtain cases from `load_hydrogen_channel_case()`.

`HydrogenChannelCase.publisher_experiment_label` optionally provides the short
file-to-test identifier recorded in the publisher's `ReadMe.txt`. Its mapping is
anchored to that acquired asset's SHA-256 in `research/data/hydrogen-channel.toml`.
Unknown file stems return `None`. These labels are identifiers only; they do not
describe operating conditions, sensor channels, clocks, units, or physical behavior.

```python
from pathlib import Path
from h2physics.data import DATASETS, load_hydrogen_channel_case, resolve_dataset

seed = next(item for item in DATASETS if item.key == "hydrogen-channel")
record = resolve_dataset(seed)
case = load_hydrogen_channel_case(
    Path("data/raw/hydrogen-channel/2/23_FFI_P101_T00005.zip"),
    dataset=record,
    file_name="23_FFI_P101_T00005.zip",
)
case.require_current()
```

This intake layer deliberately does not construct `TimeSeries` data. The source has
independent flow and sensor time columns, while the sensor clock unit is not stated
in its header. It also does not infer absolute pressure basis, sensor geometry,
concentration calibration, or physical interpretation of the second header row.
Use a separate evidence-backed mapping and clock declaration before any model
comparison. `scripts/check_channel_ingestion.py` remains a legacy exploratory route;
its optional sensor-time unit is a caller reconstruction and is not dataset evidence.

The offline acceptance contract is registered as
`hydrogen-channel-v2-source-bound-table` in the `hydrogen-channel-data` profile.
It checks archive and member integrity, exact raw row/header retention, mask
reconstruction, immutable arrays, rejection of an altered attachment record and
rejection of a copied case with a substituted source digest.
The project fixture reconstructs a Figshare record from original metadata bytes
that match the pinned metadata SHA-256 and requires the selected archive to match
its independent SHA-256. Stage `repository-metadata.json` and
`23_FFI_P101_T00005.zip` in the directory configured by the Hangang plan. The
fixture performs no network access and publisher files remain outside Git and
package artifacts. It is unexecuted and is an ingestion check, not a dispersion
validation.

## Measured-flow finite-source bridge

`h2physics.adapters.project_hydrogen_channel_finite_source(case, ...)` now
projects only the exact publisher-labelled `flow time [s]` and
`mass flow meter 1 [g/s]` columns into the existing `IntervalMassSource`
contract. It converts the declared g/s channel to kg/s, requires a caller
selected `left_hold`, `right_hold`, or `trapezoid` interval rule, and uses only
the first-to-last recorded flow-clock support. No endpoint extrapolation,
sensor-clock alignment, or missing-value fill is performed. The source carries
the archive/member SHA-256 identities and measured origin; its `require_current()`
reconstructs the mass bins from the retained case and checks the source receipt.

The caller supplies the source location/clock and one representative hydrogen
thermodynamic state. The dataset's filling-pressure bar channel is deliberately
not converted into that state because pressure basis and source-plane meaning
are unresolved. The resulting finite source can feed existing finite-source
facility-protection and consequence APIs, but does not itself produce a jet
trajectory or concentration field. Deferred Hangang contract
`hydrogen-channel-measured-finite-source-bridge` uses a fixture-backed source
case and remains unexecuted; it is not a dispersion-validation claim.
