# H2-Stations operational inventory snapshot

This source is a small, machine-readable snapshot of public hydrogen refuelling station (HRS) registry metadata from the Clean Hydrogen Joint Undertaking's H2-Stations platform. The platform documentation states that its station data, API exports, and Excel exports are available under CC BY 4.0. Preserve source attribution and license when adapting or sharing data. The acquisition receipt in `research/data/h2-stations-hrs-inventory.toml` records the exact snapshot path, byte size, and SHA-256.

The downloaded workbook is a dated platform export, not a versioned research deposit. Its `Hrs` worksheet has 166 rows and seven columns: station name, operator, owner, street address, postal code, city, and country. This is suitable as a bounded facility-inventory candidate for station counts, geographic joins, and coverage summaries after a separate content-quality audit. The metadata does not describe station thermodynamic state or equipment performance.

## Scope and limits

The station-list workbook contains registry metadata only. It does not provide fueling pressure or temperature traces, mass-flow traces, hydrogen storage time histories, or other test measurements. The platform's current API v2 documentation describes availability, usage, hydrogen-storage, and pricing signals, as well as registered dispensers, nozzles, storage units, and products. API v2 requires an individually issued bearer token, so those live signals are not represented by the downloaded workbook or acquired here. The public map's static download is used as the reproducible snapshot source.

## Python reader

`h2physics.data.load_h2_stations_workbook()` checks caller-provided byte count
and SHA-256, verifies the reviewed sheet and header tokens, and retains each
source row number with its original cell values. It does not clean addresses,
infer pressure or capacity, assign coordinates, or decide whether a station is
currently operating.

```python
import tomllib
from pathlib import Path

from h2physics.data import load_h2_stations_workbook

manifest_path = Path("research/data/h2-stations-hrs-inventory.toml")
with manifest_path.open("rb") as stream:
    receipt = tomllib.load(stream)
file_receipt = receipt["files"][0]
snapshot = load_h2_stations_workbook(
    Path("data/raw") / file_receipt["relative_path"],
    expected_sha256=file_receipt["sha256"],
    expected_size_bytes=file_receipt["size_bytes"],
)
snapshot.require_current()
first_station = snapshot.records[0]
```

The reader uses the optional `data` extra (`openpyxl`) only when called. The
source-ingestion Hangang contract checks the receipt and schema; it does not
execute a refuelling or safety model.

Do not use this inventory as validation evidence for fueling protocol physics, dispenser thermal behavior, storage performance, accident scenarios, or safety models. Station records are operator-maintained and can be incomplete or stale. The API's live availability/status values are operational indicators, not measurements of physical dispensing conditions.

## Acquisition and reproducibility

Source page: <https://map.h2-stations.eu/>. The public station-list route is <https://map.h2-stations.eu/hrs-list>. Retrieved on 2026-10-31 as `data/raw/h2-stations/2026-10-31/hrs-list-2026-10-31.xlsx` (15,024 bytes; SHA-256 `87378bed700330ddad64c364b542a69ae34e14d71c800b241c9d92cf112ea02a`). The platform does not publish an immutable version identifier or a checksum for this export; the local receipt binds the acquired bytes. The raw workbook is stored under the repository's ignored raw-data path.

Required source credit can be rendered compactly in downstream materials as: “Clean Hydrogen Joint Undertaking, H2-Stations public HRS export, retrieved 2026-10-31; CC BY 4.0.” Consult the official licensing page for its complete attribution wording and terms: <https://docs.h2-stations.eu/for-data-users/#licensing>.

## Qualification contract

Before deriving indicators, retain each source row and add checks for duplicate station identifiers or names, missing/invalid country and location fields, update recency, fuel-pressure category semantics, and distinction between planned, operational, public, and private stations. Do not infer station operating status from a static row. A future token-authorized API snapshot needs its own retrieval time, request scope, response bytes/hash, version/schema capture, rights record, and separate quality audit for each live signal family.

## Source documentation

- [H2-Stations data-user guide](https://docs.h2-stations.eu/for-data-users/) documents station fields, read-only exports, access, and the CC BY 4.0 terms.
- [Export API v2 reference](https://docs.h2-stations.eu/for-data-users/api-v2/) describes station layouts and availability, usage, hydrogen-storage, and pricing status families. API v2 requires personal bearer-token authentication.
- [H2-Stations FAQ](https://docs.h2-stations.eu/faq/) identifies the operator-maintained nature of static station information and reiterates attribution requirements.
