# AB2 tank observation API

`h2physics.data.hydride_tank.iter_hydride_tank_blocks` streams the acquired AB2
workbook profile into immutable `ObservationTable` blocks. It complements the
existing shell-only time-series reader when pressure/flow/derived-field provenance
or missing source rows matter. It does not add a second spreadsheet or unit engine.

```python
from datetime import datetime
from h2physics.data.hydride_tank import iter_hydride_tank_blocks

for block in iter_hydride_tank_blocks(
    workbook_path, worksheet_name,
    source_id="10.17632/8km9z62tct.1", experiment_id="chosen-run",
    clock_id="chosen-run/local", datetime_origin=datetime(2026, 6, 12, 10, 20, 7),
    expected_sha256=acquisition_sha256, block_rows=10_000,
):
    flow, valid = block.observations.column("mfc_reference_volume_flow")
    # flow has units m3_ref/s. A verified MFC reference state is still required
    # before conversion to kg/s using the existing standard-volume utility.
```

Use the actual source sheet's first datetime as the explicitly supplied local
origin. No timezone or alignment between runs is inferred. Every original row
survives, with row identity including the workbook hash, first twelve raw cells and
masks. Physical experiment grouping may be shared across distinct workbooks without
colliding source-row identities. Missing/nonincreasing
clocks remain available for diagnosis; the result is intentionally an observation
table rather than a repaired `TimeSeries`. Numeric counters and cached elapsed
times remain distinct from reconstructed Date-based elapsed time. Invalid or
nonphysical shell temperatures stay masked, with the original cell retained.
The iterator is the only block issuer; `block.require_current()` verifies that
the immutable observation table, source-row list and raw cells still match their
reader-issued content seal before a downstream consumer uses the lineage.

The source declares flow in standard litres per minute and shell temperatures in
degrees Celsius. Only scale changes to m3_ref/s and kelvin are made. Workbook
volume columns share the reference-litre calculation convention. The MFC's
reference pressure/temperature, pressure-column unit and absolute/gauge basis,
instrument uncertainty and actual bed temperature remain unresolved. Requesting
these observations as kg/s or absolute Pa through a compatible-variable check
fails. Flow direction is not inferred from its sign or the sheet name.

`hydride_summary_cells` separately returns four labelled source summary cells,
their cached values and their literal formulas as runtime metadata. Formulas,
links and macros are never executed. These are derived export fields; they can
select a partial-run total, and a desorption sheet has an absorption-labelled
summary. Source formula conventions do not establish sensor calibration. Do not
use the reported mass and the flow that generated it as independent fitting and
validation targets.

The reader checks a caller-supplied SHA-256, declared compressed-file byte budget,
reviewed header and final source stability. Blocks bound normalized arrays and row
strings; openpyxl still parses workbook metadata and compressed XML. Fully consume
the iterator for its final hash check. Raw workbook content remains outside Git and
distributions; callers are responsible for retaining acquisition attribution.

Run `python scripts/check_hydride_tank_data.py` after acquisition for the seven-sheet
audit, original row counts, missing clocks, sensor masks, cached clock differences,
summary selection and exact executed source fingerprints. See
[the result](../research/hydride_tank_data.md) and [finite storage](FINITE_HYDRIDE.md).
No shell-to-bed calibration, hydride kinetic fit or independent validation follows
from successful ingestion.

## Optional finite-bed heat-boundary bridge

`h2physics.adapters.bind_hydride_shell_temperature(block, sensor_name=..., clock_id=..., mapping_evidence_id=...)`
adapts one selected shell thermocouple into the existing
`FiniteHydrideHeatBoundary` callback contract. The caller must supply evidence
that explicitly maps that external shell sensor to the model's bath-temperature
boundary for the selected application. Without that evidence, this adapter must
not be used. It does not assert that shell temperature equals bed temperature.

The bridge retains the exact immutable observation block, file SHA-256, sensor,
model clock and mapping evidence identity. It uses piecewise-linear values only
between valid source samples; the native boundary rejects evaluation outside
that support. `require_current()` checks the block and the complete binding.
Missing sensor/time rows are omitted only from this forcing channel and the
source block itself remains row-preserving. It does not convert flow, use the
unresolved pressure values, or fit the existing hydride kinetic parameters.
Hangang case `ab2-shell-temperature-finite-hydride-boundary` uses a synthetic
workbook solely to exercise the contract; it is not an experiment replay or
physical validation. Raw public workbooks remain outside the repository; if a
future experiment replay is approved, stage the exact workbook and its
manifest-pinned SHA-256 separately.

Source: Ramadhan, Suwarno and Hijriawan,
[AB2 tank data, version 1](https://doi.org/10.17632/8km9z62tct.1), CC BY 4.0.
