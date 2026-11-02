# HySaM sampling-system source data

This note records a small, public measurement collection relevant to hydrogen
fuel sampling and high-pressure transfer instrumentation. The [Zenodo v1.0
record](https://doi.org/10.5281/zenodo.20590842) is published by The Hydrogen
and Fuel Cell Center on 2026-06-08. Its metadata API identifies an open dataset
under CC BY 4.0 and lists three XLSX attachments. Attribution is retained in
`research/data/hysam-sampling-system.toml` and in the Python reader.

All three files were acquired through the repository's bounded acquisition
API. The publisher MD5 checks matched, and local SHA-256 pins are recorded
below. Raw workbooks are kept under ignored `data/raw/hysam-sampling-system/v1.0/`;
they are not copied into source releases. The API metadata response hash is
`312afd497b04fb45bcad907802fae42039f1722961f361dce6a825c87b5e05e6`.

| Publisher file | Bytes | Publisher MD5 | Local SHA-256 | Worksheet shape |
|---|---:|---|---|---:|
| `20241023_Test_1_HySaM.xlsx` | 663,869 | `8eb7c14218ae25d4ffe410cbf440484f` | `fbdd81a7ec9c1191d69322f06087e8b30a33acc8b340b861a636173c08d9913a` | 6,601 × 23 |
| `20241023_Test_4_HySaM_CESAME.xlsx` | 75,292 | `ce0f85c5b12f55300bf8a5792e9221c8` | `bc9e5cbd23350b7320a96d627854cc5154f1b92ff987e087c957b1da691ea4aa` | 721 × 14 |
| `20241024_Test_9_HySaM.xlsx` | 283,636 | `9cb74d5b885ebfcf90589bfe41bbc806` | `f33d3e451b42b1d3aff905cc5deb1e9a2ed11eeaf7d4f0d559446a609bdc7563` | 2,161 × 21 |

Each workbook contains one worksheet. Its first column is labelled `Zeit` and
other columns use instrument-tag/value labels. These headers do not provide a
complete channel dictionary, measurement units, sensor calibration, pressure
basis, location mapping, or clock origin. The workbook filenames and workbook
times alone are not sufficient to establish a common run chronology. We retain
the publisher values without unit conversion or channel interpretation.

## Python access

`h2physics.data.hysam_sampling.load_hysam_workbook(path)` admits only the three
reviewed filenames and exact v1.0 byte pins. It checks publisher MD5 and local
SHA-256, requires one worksheet and the audited dimensions, and returns an
immutable source-bound `HySamWorkbook`. `require_current()` rejects changed or
replaced source bytes. Parsed cell values and exact workbook bytes are retained;
the reader does not translate channels into engineering units.

```python
from pathlib import Path

from h2physics.data.hysam_sampling import load_hysam_workbook

path = Path("data/raw/hysam-sampling-system/v1.0/20241023_Test_1_HySaM.xlsx")
workbook = load_hysam_workbook(path)
workbook.require_current()
print(workbook.headers)
print(workbook.rows[0])
```

The deferred Hangang contract `hysam-source-bound-workbook-schema` verifies
only source identity, checksums and worksheet schema from externally staged
bytes. It does not test a thermodynamic, transfer, quality or analyzer model.

## Qualification boundary

This is a promising source for later sampling-system transient and sensor
response work, but current metadata is insufficient to assign physical meaning
to the channels. Before any model comparison, obtain an authoritative channel
dictionary, explicit units and pressure reference, sensor calibration and
response characteristics, sampling-system layout, test/run descriptions, and
clock/date alignment. Until then, no parameters are fitted, no conditions are
normalized, and the acquired files are not a model-validation result.
