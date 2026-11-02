# Hydride PCT source workbook reader

## Scope

This reader opens the five simulated metal-hydride pressure–concentration–temperature
workbooks in Mendeley Data release [10.17632/trpnk55pmz.1](https://doi.org/10.17632/trpnk55pmz.1),
version 1, released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
It binds each supported workbook to its exact filename, byte count and SHA-256 receipt
in `src/h2physics/data/hydride_pct.py`. Raw workbooks are acquired separately and kept
under ignored `data/raw/` storage; they are not packaged with source distributions.

The implementation exposes source provenance and workbook cells. It deliberately does
not determine pressure basis, convert pressure to fugacity, interpret concentration
denominators, fit an isotherm, or claim model validation. The release is identified as
simulated, so a future comparison can only establish source-specific implementation
replay after its generating-model lineage is understood.

## Use

Install the optional workbook reader dependency and acquire the source release using
the repository's data acquisition workflow:

```powershell
.venv\Scripts\python -m pip install -e ".[data]"
.venv\Scripts\python scripts/acquire_data.py --keys hydride-pct-simulation
```

Then open an exact receipted workbook and stream one sheet without materializing its
rows or resolving formula cells:

```python
from pathlib import Path

from h2physics.data.hydride_pct import load_hydride_pct_workbook

path = Path("data/raw/hydride-pct-simulation/1/Ti1.15Fe Simulated Isotherm data.xlsx")
workbook = load_hydride_pct_workbook(path)
print(workbook.material_label, workbook.source_sha256)
for row in workbook.iter_rows("ABS"):
    raw_excel_values = row.values
    # Keep source labels and formula strings attached to the worksheet identity.
```

The workbook object and row/sheet snapshots are immutable. Each iterator checks that
the source still matches its byte receipt before and after streaming. `data_only=False`
preserves formula strings instead of replacing them with cached results. Sheet names
are explicitly limited to `ABS` and `DES`; the initial three rows and worksheet sizes
are retained as source schema evidence. The optional `receipt=` argument is for a
separately reviewed workbook from the same licensed release format and must identify
its own exact name, byte count, checksum, and source material.

## Deferred source case

`validation/cases/hydride_pct_source_reader.py` defines
`hydride-pct-xlsx-source-preservation`. When run after acquisition, it streams the
receipted files and reports workbook/sheet/row counts plus formula-cell preservation.
It does not calculate thermodynamic quantities or validate hydride equilibrium.

## Model-link limitations

The dataset record and source headers do not establish whether the reported bar values
are gauge or absolute pressure. The `NL/kg` reference conditions and denominator are
not resolved, and the two `wt%` workbooks do not define the loading basis needed by the
equilibrium API. Material, branch, column, temperature and formula identities therefore
remain tied to their original workbook and sheet. Consult
`research/data/hydride-pct-simulation.toml` before proposing any mapping to
`storage.hydride_equilibrium.VanthoffPlateau`; the release is not an independent
experimental validation set.
