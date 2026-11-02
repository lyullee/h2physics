# Dark-fermentation observations and source consistency

`h2physics.data.fermentation.FermentationWorkbook` reads the acquired version-2
workbook into bounded immutable `ObservationTable` blocks. It reuses native
openpyxl, existing file checksums, the unit adapter and observation contracts.
The profile qualifies source ingestion and source-column comparisons; it does
not implement a biological reactor, fit Monod kinetics or validate a yield model.

```python
from h2physics.data.fermentation import (
    FermentationWorkbook,
    component_production_check,
)

with FermentationWorkbook(
    workbook_path,
    source_id="10.17632/2nwcdx9hst.2",
    study_id="10.17632/2nwcdx9hst.2/one-study",
    expected_sha256=acquisition_sha256,
) as source:
    for block in source.iter_blocks(block_rows=128):
        observations = block.observations
        consistency = component_production_check(block)
        # consistency compares columns from this same source export.
        # It supplies neither independent validation nor a molar H2 yield.
```

Blocks can only be constructed by the qualified reader. Each block seals its
observation content and source-row, raw-cell, formula, invalid-reason, reactor,
and issue metadata. Call `block.require_current()` before downstream use to
reject replacement or post-load mutation; the same-source component check does
this automatically.

The actual worksheet is `Data`, declared 831 by 24, with one header row and 830
data rows. Literal labels and units, including double spaces and the distinct
`HPR` versus `HPr_1` identifiers, are checked. The loader preserves each original
worksheet row and raw cell, source Nr identifier, reactor R, formulas and caches.
No source index is renumbered to fill Nr gaps. Strict decimal numeric strings are
decoded as serialization; commas and other ambiguous tokens are not guessed.
`None` and `--` remain distinct raw values with invalid masks/reasons. Numeric
zeros remain valid reported observations.

Each block belongs to one reactor label, even when a requested block size crosses
a source reactor boundary. The declared Duration days and HRT days scale to
seconds, but Duration remains a `reported_duration` coordinate with a per-reactor
basis. Its day-zero, event interpretation, sampling interval and cross-reactor
alignment are unqualified. Repeated or decreasing values stay in source order
and produce issues, not repaired clocks. `as_time_series()` refuses automatic
conversion. `first_row` and `last_row` select inclusive original worksheet rows;
windowed diagnostics apply only to the consumed window.

The source R labels are reactor identifiers. Their independence, replicate
conditions, shared forcing and batch histories are not established by the
metadata. All R values retain one `study_id` in `experiment_ids`, so the existing
experiment-splitting API cannot silently turn them into independent held-out
studies. `block.reactor_id` preserves within-study grouping. A qualified future
replicate/partition declaration requires evidence beyond the R column.

| Source role | Observation representation | Unresolved boundary |
|---|---|---|
| Temperature, pH | K; reported pH | Sensor/location, analytical method and pH activity convention |
| HRT | reported hydraulic-retention time, s | Working volume, liquid feed flow, mixing and averaging |
| BP | reported total gas-volume production rate, m3_reported/s | Gas reference P/T, wet/dry state, collection/averaging convention |
| CO2/CH4/H2 | reported gas volume fractions, 1 | Sampling, wet/dry and normalization to listed gases; not assumed mole fractions |
| HP/MP | reconstructed component gas-volume rates, m3_reported/s | Same gas-volume basis; not independent measurements or kg/s |
| HY | reconstructed reported specific gas volume, m3_reported/kg_reported | Added/consumed substrate/COD mass denominator and gas reference |
| HPR/MPR | reconstructed productivity, literal `source L/(L/d)` | Printed unit is ambiguous; physical normalization/volume not repaired |
| OLR (COD) | reported COD loading, kg_COD/(m3*s) | Liquid/reactor-volume denominator and pH-dependent feeding/averaging |
| COD in/out | reported COD concentration, kg_COD/m3 | Soluble/total, analytical and sampling alignment; not glucose mass |
| Acid-labelled fields, tVFA | reported component concentration, kg/m3 | Exact analyte/speciation/analytical basis; abbreviations retained |

The engineering scale changes are explicit: days use 86,400 seconds, L/d uses
1e-3/86,400 m3/s, vol% uses 0.01, and degrees Celsius use the existing K adapter.
Numerically 1 L/g equals 1 m3/kg; this does not qualify HY's gas or mass basis.
Similarly 1 g/L equals 1 kg/m3 without identifying COD as a chemical species or
an acid abbreviation as a molecular substrate. No standard-gas density, molar
mass, liquid flow, working volume, conversion extent or consumed mass is inferred.

The actual workbook contains no Excel formulas, but the gas production, yield
and productivity columns include publisher calculations stored as numbers.
HP/HY/HPR/MP/MPR therefore use `Origin.RECONSTRUCTED`. HRT/OLR use unresolved
operating/calculation provenance. Other fields retain reported-observation origin
without claiming independent instrument/analytical qualification. Formula cells
in a future compatible export remain literal runtime metadata: missing caches
stay invalid, and cached formulas in measured columns are masked as independent
measurements. No formulas, links, macros or included programs execute.

`component_production_check` is a useful bounded comparison operator. It computes
BP times each reported H2/CH4 volume fraction, the differences from HP/MP and the
listed gas-fraction closure. It requires the qualified quantity/unit/basis
contracts, propagates masks and retains source row/study identities with
reconstructed origin. The calculation is a same-export algebra check using a
common reported-volume convention. It does not infer unlisted gases, an ideal
gas law, wet/dry corrections or a biochemical reaction. A declared numerical
tolerance for this check is not a sensor-error bound or noise sigma.

The complete source audit finds an HP/MP inconsistency at worksheet row 239
(source Nr 241), while preserving both values. It also retains four repeated
Duration edges. No column swap, date correction, outlier deletion, missing-data
interpolation or replacement of derived values is performed. Per-reactor numeric
HPR/HP and MPR/MP proportionalities and the HY/OLR/HPR relation support their
calculated nature. Their scales cannot establish a physical reactor volume or
repair the printed HPR/MPR unit. Gas fractions closing numerically does not
establish that no other species or water vapour were present.

The metadata identifies pig manure and glucose qualitatively. It does not give
the feed composition/ratio, soluble/particulate/inert species mapping, biomass
inventory, growth/decay observations, mass-yield denominator or all feeding and
sampling histories. COD and concentration fields are sparse; COD out exceeding
COD in at a row does not by itself establish negative substrate consumption or
an aligned material balance. Source temperature is not heater power, heat loss,
reaction enthalpy or an energy-validation record. No kinetic or uncertainty
parameters are estimated from these records.

A next native biological model should own finite liquid/species/biomass and gas
states, feed/withdrawal boundaries, phase transfer, pH/acid-base closure or a
declared prescribed-pH boundary, and explicit initial/control histories. Rate and
growth/decay/yield callbacks need replaceable parameters and declared mass/COD/
molar bases. Reuse existing `ChemicalSpecies`/`StoichiometricReaction` checks once
species or empirical biomass composition is supplied; do not invent an elemental
formula for pig manure or turn a prescribed reaction extent into microbial
kinetics. COD-only lumped balances must state which elemental/energy claims they
cannot close.

Before comparing that model with gas data, provide an observation operator from
native gas species flows/inventory through the measured collection window,
reference P/T and wet/dry/normalization rules to reported BP and gas fractions.
HRT requires measured/declared working volume and liquid feeding before it can
constrain a feed boundary. pH-dependent feeding is a control history, so an
observed pH trace alone cannot identify inhibition or Monod growth separately.
Biomass/initial-state/feed/species/reference evidence is required for such a fit,
and a genuinely independent study/replicate partition is required for validation.

Default budgets bound compressed bytes (4 MB), expanded ZIP content (16 MB),
worksheet rows (10,000) and returned blocks (1,000 rows maximum). All source rows
survive, including declared blank rows. Read-only cached and formula views are
closed together. Source SHA is verified before entry and after context exit;
consume inside the context manager for that final stability check. Only the
existing optional `data` extra is needed; tests skip cleanly without openpyxl.

```powershell
.venv\Scripts\python -m pytest tests/test_fermentation_data.py -q
.venv\Scripts\python -X utf8 scripts/check_fermentation_data.py
```

The complete audit verifies the receipt, publisher checksum, pinned/supporting
metadata, all raw rows/cells, source formulas/caches, missingness, reactor clocks,
source algebra and source/test/script/shared-helper begin/end fingerprints. Its
detailed record remains in ignored `data/processed/dark-fermentation/2/audit.json`;
[the public aggregate report](../research/fermentation_data.md) contains original
counts, limitations and source hashes. Raw and normalized external observations
remain outside Git and distributions. This data qualification adds no biological
model family and leaves independent experimental validation unresolved.

Attribution: Roberto Hernández,
[Raw data, version 2](https://doi.org/10.17632/2nwcdx9hst.2),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The versioned
[repository snapshot](https://data.mendeley.com/public-api/datasets/2nwcdx9hst/snapshot/2)
and acquisition receipt supply rights and provenance.

The separate source-to-model boundary and prepared, not-sent gas-basis request are
documented in [`DARK_FERMENTATION_MODEL_LINK_GAP.md`](DARK_FERMENTATION_MODEL_LINK_GAP.md)
and [`requests/dark_fermentation_gas_basis_request.md`](../requests/dark_fermentation_gas_basis_request.md).
