# Buried hydrogen-blend pipeline release data

The curated Mendeley seed `buried-h2-blend-pipeline` points to the current version
2 record, DOI [10.17632/x8zkds4fyn.2](https://doi.org/10.17632/x8zkds4fyn.2),
published 2025-12-11 by Wenxin Guo. Cite the dataset as: Guo, W. (2025),
*Experimental Study on Leakage and Dispersion Dynamics of Buried hydrogen blended
natural gas Pipeline Under Delayed-Ignition Condition*, version 2, Mendeley Data,
https://doi.org/10.17632/x8zkds4fyn.2. The publisher metadata declares CC BY 4.0;
provide attribution and a license link, indicate changes, and do not imply author
endorsement. The publisher notes that separately identified third-party content
may have separate terms. The 12 CSVs are retained only under ignored `data/raw/`
and are excluded from source control and package manifests.

Version 1, DOI [10.17632/x8zkds4fyn.1](https://doi.org/10.17632/x8zkds4fyn.1),
is kept in a separate superseded receipt. The public Mendeley listings show twelve
CSV files in each version and matching publisher SHA-256 values for all twelve.
The current seed selects version 2; the V1 receipt preserves its metadata and
listing hashes for lineage.

`h2physics.data.resolve_dataset()` provides the typed repository metadata API and
public Mendeley listing adapter. Its license normalizer reads the human-readable
`short_name` before an opaque Mendeley license UUID, then checks the license URL
and returns the canonical CC BY 4.0 identity. The current V2 CSV attachments were
acquired to ignored `data/raw/buried-h2-blend-pipeline/2/`; all 12 local SHA-256
digests match the publisher's file listing (18,314 bytes total).

The CSVs are UTF-16, tab-separated, headerless numeric tables. Eleven files have
five positional fields and `hydrogenAll10%.csv` has six; some trailing cells are
empty. No data dictionary, field labels, units, time basis, geometry, sensor
locations, or experiment-independence description is present in the acquired file
listing. `load_buried_pipeline_numeric_table()` checks the source object's DOI,
version, repository metadata URL and SHA-256, the publisher listing URL and SHA-256,
and that the resolved attachment objects exactly match the retained publisher listing.
It then checks the unique listed filename, publisher-listed byte count, and attachment
SHA-256. A caller-built `Dataset` with the right DOI but altered metadata or file list
is rejected. It returns the
exact parsed text fields, one-based source row IDs, positional column labels, a
numeric array, and a validity mask. Column semantics and observation operators
remain deliberately unsupported until authoritative documentation is available.
The numeric arrays use immutable backing storage, so callers cannot restore
NumPy write access to the returned views; `require_current()` also checks the
retained source receipt and array content before downstream use.
The source-bound table is issued only by the checksum-validating loader, and its
column projection only by that table. Direct construction and dataclass replacement
cannot mint a new receipt carrying a substituted publisher digest; use the reader
operations to begin lineage from verified local file bytes.
`BuriedPipelineNumericTable.column_series("source_column_2")` produces a typed
one-column projection that keeps the anonymous source label, original row IDs,
exact decoded cell tokens, validity mask and publisher file digest together.
Rows shorter than the selected column retain an empty token and a false mask.
The projection is a convenient data-boundary object only: it supplies no unit,
clock, sensor, or physical-variable interpretation, and its `require_current()`
checks retained content consistency rather than scientific qualification.
The dataset is a candidate source for later review, not qualified model-validation
evidence. See `research/data/buried-h2-blend-pipeline.toml` and the separate `-v1`
receipt for source hashes, rights scope, and file-level checksums.

The loader contracts are registered as `buried-pipeline-v2-lossless-ingest` and
`buried-pipeline-v2-column-lineage-projection` under
the `buried-pipeline-data` Nurion profile. Its offline fixture must provide the
repository-backed V2 `Dataset` object and locally staged CSV path. The contract
checks source hash/identity/size, row/column preservation, forged-view rejection
and repository receipt/listing identity; the projection contract checks exact token,
mask, value and row-lineage preservation and refusal to re-enable writes. Neither
contract assigns
physical meanings or fit a model. It has not run.
