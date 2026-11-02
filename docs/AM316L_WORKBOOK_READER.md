# AM316L workbook source reader

## Source and reuse

`h2physics.data.am316l_workbooks.read_am316l_workbook(directory, file_name)`
accepts only the two acquired workbook members of the Zenodo v1 dataset:
`Tensile tests.xlsx` and `Hardness.xlsx`. The official [Zenodo record](https://zenodo.org/records/19813205)
identifies the dataset as CC BY 4.0; the source license is
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
Each snapshot retains the DOI `10.5281/zenodo.19813205`, source URL, file name,
publisher MD5, local pinned SHA-256, byte size, and dataset attribution. Reuse
or redistribution must retain that attribution and the source license notice.

## Preservation contract

The reader verifies both the publisher MD5 and the reviewed local SHA-256
before opening the workbook, rechecks them after snapshotting, and provides
`require_current()` for a later freshness check. It opens workbooks read-only
with formula text retained (`data_only=False`); formulas are never executed.
Worksheet order/names and the full rectangular cell value grid are preserved,
including blank cells, formulas, text labels, and original row/column
positions. `openpyxl` is imported only when this function is called and is part
of the existing optional `data` extra.

No units, sample identities, condition labels, charging quantities, curve
pairings, constitutive parameters, or statistical summaries are inferred. All
source row values remain in `worksheet.rows` at their original positions. If a
caller has independently reviewed the workbook and knows a header row, it may
pass `header_rows={worksheet_name: one_based_row_number}`; `header_values` then
copies that exact source row without renaming or interpreting cells. Without
such a mapping, the reader does not guess which row is a header.

## Deferred local-file cases

Two independently schedulable `source-data-ingestion` cases check the tensile
and hardness workbooks. The runner may pass `raw_data_root` pointing to the
staged directory that contains the manifest-relative workbook paths. Case
discovery copies optional `H2_AM316L_RAW_DATA_ROOT` into that parameter. If no
explicit path is passed, a local checkout uses
`research/data/payload/am-316l-hydrogen-embrittlement/`; if neither location is
present, the case fails with a request to stage the manifest-listed payload.
The case reports only source identity, worksheet names and stored dimensions.
It performs no data conversion, specimen pairing, fitting, or material-model
validation.

## Workbook schema status and limits

The source readme describes one tensile-results sheet plus six per-specimen
tensile traces in the tensile workbook, and six specimen sheets in the hardness
workbook. The repository's initial schema audit records the tensile trace
labels as index, position (mm), strength (MPa), and deformation, and the result
sheet as specimen identifiers, charge-rate labels, loading speed, geometry,
and tensile-property columns. Hardness sheets contain measurement date,
specimen/method, indenter readings, and hardness values. These are source
labels only: the sheet description does not establish all units, specimen
pairing rules, physical meaning of charge-rate labels, or a stress/strain basis
for constitutive fitting. The reader therefore preserves sheet names and cell
contents as source tokens. Any numeric mapping must be a separate,
evidence-backed layer before comparison with embrittlement, fracture, fatigue,
or vessel-integrity models.

Manifest and per-file checksums are maintained in
[`research/data/am-316l-hydrogen-embrittlement.toml`](../research/data/am-316l-hydrogen-embrittlement.toml).
