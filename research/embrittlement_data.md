# HE-Austenite source qualification

Qualification date:2026-10-27. This is ingestion/semantic verification of an
already acquired literature compilation. It is not a new embrittlement model,
fracture-law fit, experimental re-extraction or independent material validation.

## Rights, identity and actual acquired scope

Muhammad Faizan, [HE-Austenite](https://doi.org/10.5281/zenodo.23107780), pinned
record23107780. Repository metadata and the data-specific license identify
CC BY4.0; publication tables underlying the compilation have separate rights.
External data, normalized observations, metadata prose and detailed source
tables are not redistributed. Source programs, figures and example calculations
were not copied or executed. This report contains original audit metadata only.

The receipt `research/data/austenite-embrittlement.toml` has SHA-256
`85b35007329799fc1a10fff6922a71b4a5a6ea564cab06994dfa24e86a0c19fb`.
Pinned repository metadata has SHA-256
`c8955a19bf400c3aea49b7e3599ceccc22142dfb3a93d7f2a1e3297d7caaf062`.
All9 acquired attachments/148911bytes match receipt SHA-256, size and publisher
MD5. The publisher lists23 assets;14 omitted programs/figures/raw JSON/other files
are retained as an explicit acquisition omission. The raw-to-normalized JSON
transformation cannot be audited from those unavailable bytes. File names say
v1.0 while the README and workbook identify v0.2; neither label overwrites the
pinned Zenodo identity.

| Acquired file | SHA-256 |
|---|---|
| main CSV | `a392282dd1585b6f6d84ce96a931c827e78587310c0a59d6c1409843f89dc5b7` |
| composition CSV | `07fbba9be6220e0613e98bfa889c0a7c43b98b7361d195584429cfc740e4f3b3` |
| record/composition map | `358ede7737c7792b7aaf88b3362b0cc0e7c061c8d6c686b8bf07ae40486c3354` |
| workbook | `c0e4a8ee6b20c3cf0db2af09447e9075f1b1c392353ee34fd62747be71c29f87` |
| data dictionary | `019a988672bd7aaad0ada92eaa8b3d4965bb950db5aa70cae4d835beef4aaa86` |
| README | `600da68e995e2fa9bb33a3aa477ba9b651b1c438ca87a5f78499d282be0319af` |
| CONTRIBUTING | `1b2e941bc8e1a7de3a80eea7e26a85d92573712f870f1f0914af8777c7f0622e` |
| data license | `ad94dcb83d0ca380f780ba302961fe7a26837c5e78cd58aa34bc7d7d7a16335b` |
| requirements | `9898258dad6808ea28b3387edacf81e2583bae79297c14d7c2954208ae54c8b2` |

## Complete data and workbook coverage

The main CSV has113 condition/property records and45 fields. Its23 numeric
profile columns contain1697 usable fields and902 blank numeric fields. The
remaining categorical/source fields are preserved exactly, including all notes,
material, heat, product/zone, exposure, test, reference and curator-derived roles.
Every record ID is unique; it is an author source-location ID, not a specimen ID.

| Reported property | Original records | Default absolute-value representation |
|---|---:|---|
| Reduction of area |74| distinct dimensionless fraction |
| Elongation |32| distinct dimensionless fraction |
| Tensile strength |2| Pa |
| Notched tensile strength |1| Pa |
| Plastic strain to failure |4| source absolute unit unresolved |

There are9 bibliography source labels, with handbooks/reference compilations
among them. Reference environments comprise48 air,28 helium,32 uncharged,4
nitrogen and1 argon; no blanket air comparison is inferred. In-situ gas tests
number54 and gas-precharged observations59. Zones are53 base metal,20 weld metal
and40 whole-joint records. Test labels are109 tensile and4 SSRT. Nominal and
heat-analysis labels are retained, not promoted to a common specimen analysis.
Only16 records carry a reported heat identifier. The24 curator `verified=yes`
flags are source metadata and do not establish host independent validation.

The composition CSV contains31 rows/17 fields,203 finite element values and
source/derivation metadata. All31 keys are used. The record map has102 rows/2
fields;11 main records remain explicitly unmapped. No unmatched key or duplicate
source ID is accepted. Main and linked composition tables remain separate views.

The workbook has14 CRC-checked ZIP members,338538 expanded bytes and6 sheets.
Its first45 Data fields match the main CSV semantically cell-for-cell; the two
additional Data columns are formula helpers. Native formulas and missing caches
are preserved without evaluation.

| Sheet | Native rows including header | Columns | Formula cells | Missing formula caches |
|---|---:|---:|---:|---:|
| Read me |12|1|0|0|
| Data |114|47|226|226|
| Summary |24|4|31|31|
| Data dictionary |31|4|0|0|
| Sources |10|4|0|0|
| Extraction log |21|3|0|0|

All257 workbook formulas lack caches; no source formula error cache is present.
None becomes an observation or zero. All source metadata rows, individual ZIP
member hashes, formulas/cache status and detailed discrepancies remain in the
ignored audit artifact. Workbook summaries and helpers are not independent data.

## Scientific applicability and unresolved source discrepancies

An ObservationTable view is property-specific and carries all original row IDs,
masks and separate structured records. It preserves reported gas-exposure Pa,
material hydrogen mass fraction, charging duration, source K and converted C,
nominal strain rate, paired property values, ratio and both compositional/index
roles. Raw strings remain available for every conversion and mask.

Forty linked-element cells disagree with the main CSV across15 records:15 Cr,
15 Ni,5 Mn and5 N cells. No linked composition overwrites the primary table.
Missing Mo/N and the source's derived zero assumptions remain different objects.
Material groups may repeat across conditions and properties; heat, weld deposit
or filler metadata does not supply an independent specimen/replicate count.

Both the source-labelled reported and calculated nickel-equivalent columns have
93 populated records, whereas the dictionary describes only3 reported values.
Their equality in79 records does not prove independent reported measurements;
the reported column's origin remains unresolved. Md30 has55 populated calculated
indices; no measured transformation temperature or phase-stability validation is
inferred. The source completeness prose is not used to invent or remove data.

All113 source K values differ by-0.05K from their separately reported C values
converted using273.15. Both are retained. This is a representation discrepancy,
not a noise estimate or permission to repair the source. Pressure absolute/gauge,
total/partial gas and H2 purity remain unresolved. One range midpoint is explicitly
derived. Precharge pressure/temperature/duration and later mechanical-test
conditions are separate; no material fugacity, hydrogen diffusion/trapping
parameter or exposure equivalence is calculated.

The four plastic-strain absolute values lack a resolved unit/definition in the
available dictionary; generic `% or MPa` is insufficient. Their ratios remain
dimensionless. Notch/geometry and fracture descriptions remain source text, not
a structured or predicted fracture mode. Ferrite number has only2 populated
records and is not ferrite volume fraction. No ferrite/ductility law, true-stress
curve, toughness or fatigue/crack-growth model follows from these fields.

The source identifies at least one handbook reprint of another included
measurement. Default experiment grouping is therefore the whole dependent
compilation; source labels, material groups and different properties are not
automatic held-out experiments. No underlying original-experiment crosswalk,
specimen count, uncertainty model or independent validation set is fabricated.

Stored absolute pairs exist for103 records;10 remain ratio-only. The explicit
same-export operator reproduces all103 ratios within the declared.002 arithmetic
budget, with maximum absolute residual0.000500000000000056. This is ingestion and
curator arithmetic verification. It does not independently validate the ratio
as a physical model target or establish an engineering acceptance threshold.

## Reproduction and continuation

```powershell
.venv\Scripts\python -m ruff check src/h2physics/data/embrittlement.py tests/test_embrittlement_data.py scripts/check_embrittlement_data.py
.venv\Scripts\python -X utf8 -m pytest tests/test_embrittlement_data.py tests/test_observations.py -q
.venv\Scripts\python -X utf8 scripts/check_embrittlement_data.py
```

Authored miniature fixtures cover source line/record identity including quoted
newlines, property-dependent unit conversion, unresolved plastic-strain units,
incomplete pairs, explicit signed masks, linked/primary conflicts, no inferred
zero, dependent partition rejection, block/filter stability, ratio disagreement,
schema/key/budget/hash gates, source mutation and native workbook formula/cache
handling. Optional workbook tests use `pytest.importorskip("openpyxl")`.

The next usable comparison is a source-conditioned paired-property/ratio
operator with explicit environment, material, loading and property definitions.
Before a mechanical law can be qualified, obtain original specimen/heat and
experiment lineage, phase/microstructure, notch/loading histories, H2 pressure/
purity basis, charging versus test conditions, analytical hydrogen definition,
fracture definition and uncertainty. Original source re-extraction and linked
composition reconciliation must be evidenced, not performed by silent repair.
No general catalogue, data receipt or model family was changed by this task.

Final verification: Ruff passed. The13 original source-profile tests plus3
common observation tests passed in4.18s. Final complete acquired-source replay
took2.5111624s; all9 files, publisher MD5s, receipt and metadata matched before/
after, every property had identical17-row/512-row block identities/values/masks,
all103 available ratio checks passed, and all14 workbook members/6 sheets were
consumed. No acquisition, external write, source program execution or model fit
was performed.

Ignored detailed artifact:
`data/processed/austenite-embrittlement/23107780/audit.json`, SHA-256
`a8f95f252b2d28e3854f6c9610b6cb133bb0aa34e9d92c5a3ca7bfde2ab0c263`.
The JSON is reproduction evidence, not the public API. Source/test/script and
reused contracts had identical begin/end bytes, all LF:

| Executed input | Begin and end SHA-256 |
|---|---|
| `src/h2physics/data/embrittlement.py` | `ade4fcb401b40bbfd0f970e74ee0097f8669bf0605b57494f703a69d98f0a525` |
| `tests/test_embrittlement_data.py` | `5c274d7d6bcbde28dd31110fa3f0ba4b0cc5fdafc423345e4571a52577232f4c` |
| `scripts/check_embrittlement_data.py` | `f99f0e2cb8ba55a9dc4564a5a7c4315408a78ab1d35b11f782a52de0d5126fb9` |
| reused `src/h2physics/data/pressure_peaking.py` | `44235ac1ffa7e447ebc58a42eba5368e8008af517f48bd3605fa41140507fa15` |
| reused `src/h2physics/observations.py` | `e0a6f1e26b5b6ca20fb31b8f7f19d5f86c6dbaffadfd37e2adc22de8bf6d1ba0` |
