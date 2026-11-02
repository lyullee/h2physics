# Wasserstoffatlas facility inventory source

This bounded reader ingests the official `Bestand.csv` inventory from the Wasserstoffatlas / Hydrogen Map record. It exposes each source row as `HydrogenMapFacility` while preserving reported text tokens, source lineage, and WKT geometry. The reader does not infer units, repair missing values, or execute a process or consequence model.

## Source and reuse

- Record: [Zenodo 10.5281/zenodo.10548190](https://doi.org/10.5281/zenodo.10548190), v6.
- File: `Bestand.csv`, 181,145 bytes; publisher MD5 `078c7049bbef5967194105c35e2af720`; SHA-256 `050e7b8a5a45d554640c2668ab87b6e9c3d0d4658e7ee4a572d7a0864092e8fe`.
- The record metadata declares CC0, while its file-level raw-data table explicitly assigns `Bestand.csv` [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This project follows the more specific file-level declaration and retains attribution; it does not claim a CC0 relicense.
- Attribution: Schumm, Leon; Birett, Falk; Hofrichter, Andreas; Heusgen, Valentin; Rahim, Stefan (2024), *Wasserstoffatlas (Hydrogen Map) Dataset*, v6, Zenodo, https://doi.org/10.5281/zenodo.10548190.
- The upstream inventory aggregates records from multiple providers. The `Quelle` field remains on each row; consult those providers for their original data and terms before redistributing or making provider-specific claims.
- The reader reshapes rows into typed Python records without changing source field values; this project added the reader and hash/schema checks.

## Data shape and limits

The reviewed CSV has 1,049 rows and 20 columns: record id and location label; end product and source year tokens; electricity/capacity and conversion-process tokens; status/type/name; emissions/sector/source/demand/use-sector; NUTS0–3 administrative codes; and point geometry WKT. Source strings are preserved exactly. The CSV does not establish normalized units or a single measurement basis for capacity, demand, or emissions. The reader does not infer a CRS or calculate distances from WKT.

The dataset supports infrastructure inventory and caller-directed screening. It does not validate production dynamics, storage, transport, dispersion, consequence or safety physics. Remote ingestion only checks byte and schema reproducibility.

## Python API

```python
from h2physics.data import read_hydrogen_map_inventory

inventory = read_hydrogen_map_inventory("data/raw/wasserstoffatlas-hydrogen-map/1/Bestand.csv")
for facility in inventory.rows:
    print(facility.facility_type, facility.geometry_wkt, facility.source_lineage)
inventory.require_current()  # Recheck exact publisher bytes and parsed rows.
```

Raw licensed source bytes are kept under the gitignored `data/raw/` tree. The manifest contains file identity and receipt, not a copy of the dataset.
