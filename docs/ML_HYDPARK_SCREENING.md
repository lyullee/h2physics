# ML-HydPARK material screening table

## Source, license, and attribution

This reader is pinned to Sandia National Laboratories' [Zenodo v0.0.5 record](https://zenodo.org/records/10680097), DOI [10.5281/zenodo.10680097](https://doi.org/10.5281/zenodo.10680097). Zenodo's record API identifies the record as open and declares `CC-BY-4.0`. The sole attachment is `ML-HYDPARK_v0.0.5.csv` (100,494 bytes; publisher MD5 `d88e51ae01f93935a214326d3f37c560`). The local source SHA-256 is `41d1549a0b0b72355184cebe19d8da0b1ed18f87c7e1bf5527073a4246421af0`; the exact downloaded Zenodo record metadata SHA-256 is `1e45a2930e47955aeda566eedef8337eeee3786616c5e010b8ba153ee17a6e04`.

Attribution: Matthew Witman, Mark Allendorf, and Vitalie Stavila, *Database for machine learning of hydrogen storage materials properties*, Zenodo v0.0.5, 2024, [https://doi.org/10.5281/zenodo.10680097](https://doi.org/10.5281/zenodo.10680097), CC BY 4.0. This repository adds a read-only token-preservation interface and its source metadata receipt; the deposited data have not been edited or redistributed in the source tree. Any later redistribution must retain this attribution and license and clearly identify changes.

The source describes a cleaned and curated CSV of metal-hydride composition, capacity, and thermodynamic properties assembled from the DOE HydPARK database and literature. It notes that entries were removed or corrected as part of the curation. These are therefore curated material-property records, not primary raw measurement files or independent observations of a tank process. The downloaded table remains under ignored `data/raw/` and is excluded from Git and distributions by repository policy.

## Python interface and token-preservation contract

```python
from pathlib import Path
from h2physics.data import load_ml_hydpark_screening

table = load_ml_hydpark_screening(
    Path("data/raw/ml-hydpark-screening/0.0.5")
)
row = table.rows[0]
source_class = row.token("Material_Class")
source_capacity = row.token("Hydrogen_Weight_Percent")
table.require_current()
```

The loader accepts only the receipted file and its exact Zenodo metadata snapshot. It verifies version, DOI, open-access flag, CC BY 4.0 license identifier, attachment name/size/MD5, local CSV SHA-256, metadata SHA-256, exact header order, 13 fields per record, and the 772-record schema. `MLHydPARKRow.raw_tokens` retains each CSV value as text. `source_row_number` is a 1-based position in the CSV data-record sequence, not an asserted source material identity. `token()` requires an exact unique header token. Empty fields, original numeric formatting, row order and repeated `index` values are preserved. No pandas dependency is required.

The source header tokens are retained exactly:

```text
"", index, Material_Class, Composition_Formula, Hydrogen_Weight_Percent,
Heat_of_Formation_kJperMolH2, Temperature_oC,
Pressure_Atmospheres_Absolute, Entropy_of_Formation_JperMolH2perK,
Equilibrium_Pressure_25C, LnEquilibrium_Pressure_25C, HtoM, Reference
```

These names are source labels, not a completed data dictionary. The label `Pressure_Atmospheres_Absolute` provides a pressure basis in its name; other fields do not define all needed standards, denominators or reference conditions. In particular, no unstated unit is assigned to `Equilibrium_Pressure_25C` or `LnEquilibrium_Pressure_25C`, no composition formula is parsed, and no `HtoM` interpretation is imposed. Missing values stay empty strings.

## Use limits and deferred ingestion

This table is suitable for discovery, material screening and caller-controlled data science after independent review of each field and source reference. It is not a raw PCT dataset, kinetic or cycling time history, apparatus calibration record, or tank validation data. The reader does not normalize formulas, infer missing measurement conditions, resolve source citations, deduplicate rows, convert units, calculate target properties, fit constitutive parameters or compare model predictions.

The deferred `ml-hydpark-curated-material-screening-ingestion` case under `source-data-ingestion` checks only local bytes, metadata, CSV shape, and preservation of blank and duplicate tokens. Case discovery is wired into the Hangang plan; no cluster run is implied by this wiring. See [`research/data/ml-hydpark-screening.toml`](../research/data/ml-hydpark-screening.toml) for the acquired file receipt, metadata hash, attribution, and reviewed schema, and [`research/data/hydrogen-storage-experiment-data-gap.toml`](../research/data/hydrogen-storage-experiment-data-gap.toml) for the separate raw-experiment data gap.
