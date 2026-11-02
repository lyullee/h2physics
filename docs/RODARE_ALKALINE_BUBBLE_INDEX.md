# RODARE alkaline-bubble condition index reader

## Purpose and evidence boundary

`h2physics.data.load_rodare_alkaline_bubble_index()` reads the small public
condition index associated with RODARE dataset v1, DOI
[10.14278/rodare.4547](https://doi.org/10.14278/rodare.4547). The record declares
CC BY 4.0. The acquisition manifest records the canonical file URL, publisher
MD5, local SHA-256, file size, license evidence and attribution. Raw bytes remain
in the ignored local data cache and are not bundled with this Python package.

This file enumerates experiment conditions and links run IDs to electrode type,
cell pressure and applied current density. It is not a measurement table: no
cell voltage, overpotential, bubble size/coverage, electrolyte void fraction,
time trace or uncertainty is present. The source record describes a separate
HDF5 archive of about 8.6 GB. That archive has not been acquired or inspected,
so no measurement-derived parameter is admitted from this dataset.

## Loading and using the index

The defaults are the reviewed v1 size and checksum receipt. Pass a path to the
exact file named `Summary.csv`:

```python
from h2physics.data import load_rodare_alkaline_bubble_index

index = load_rodare_alkaline_bubble_index(
    "data/raw/rodare-alkaline-bubble-pressure/4547/Summary.csv"
)
index.require_current()

for condition in index.conditions:
    print(
        condition.measurement_id,
        condition.electrode_id,
        condition.pressure_bar_abs,
        condition.current_density_mA_cm2,
    )
```

Each row retains the publisher's source index, experiment ID, electrode label,
absolute pressure in bar, cathodic current-density sign and exact raw fields.
The reader enforces the reviewed 60-row electrode/pressure/current grid and
rejects altered bytes, changed headers and unsupported conditions. It does not
read the large HDF5 archive, perform fitting, or alter the shared electrolyzer
model.

## Validation contract

The deferred Hangang case `rodare-alkaline-bubble-condition-index-source-contract`
checks checksum-bound loading, the condition grid and rejection of a modified
file. It verifies ingestion and source identity only. It is not calibration,
independent validation, physical model verification or stack qualification.

## Attribution and source records

Hannes Rox et al. (2026), *Bubbles under pressure and their impact on electrode
potentials during alkaline water electrolysis*, RODARE v1, DOI
[10.14278/rodare.4547](https://doi.org/10.14278/rodare.4547), CC BY 4.0.
The exact acquisition receipts and limitations are maintained in
`research/data/pressurized-alkaline-bubble-electrode-potentials.toml`.
