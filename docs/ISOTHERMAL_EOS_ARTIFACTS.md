# Reusable isothermal EOS table artifacts

`IsothermalEOSTable` can be persisted after its grid is generated so callers
can load and reuse the immutable interpolator without calling CoolProp again.
The persistence API is available from `h2physics.thermo`:

```python
from h2physics.thermo import (
    load_isothermal_eos_table,
    save_isothermal_eos_table,
)

# `table` is built using the desired source EOS and rho-T axes.
save_isothermal_eos_table(
    table,
    "artifacts/hydrogen-rho-t.npz",
    maximum_artifact_bytes=128 * 1024 * 1024,
)

table, historical_receipt = load_isothermal_eos_table(
    "artifacts/hydrogen-rho-t.npz",
    expected_source_eos_identity=table.source_eos_identity,
)
```

Pass `qualification=receipt` when an existing `IsothermalEOSTableQualification`
receipt is available and matches this exact grid.

## Artifact contract

The artifact is one uncompressed `.npz` container with four numeric `float64`
arrays and an embedded UTF-8 TOML manifest. It is published through a same-file-
system temporary file, flush/fsync, then atomic replacement. There is no pickle,
JSON payload, executable object reconstruction or source-EOS query during load.
The manifest has an explicit schema version and includes the EOS identity,
interpolation mode, table shape, no-extrapolation policy, per-array SHA-256
values, and the reconstructed table digest. A caller may require an exact EOS
identity at load time. Unknown/missing members, compressed members, oversized
containers, oversized arrays, invalid shapes, bad checksums, unknown schema
fields and mismatched receipt identity are rejected.

The default load/save bound is 128 MiB and the node ceiling is two million
rho-T cells. Applications with smaller artifact budgets should lower
`maximum_artifact_bytes`. Queries remain bounded by the table's explicit
density/temperature grid and pressure envelope; persistence does not enable
extrapolation.

## Qualification receipts

The `qualification` argument is optional. When supplied, the writer requires
that the receipt's source EOS identity, table identity, grid digest and
interpolation mode match the saved table. The receipt values are included in
the same canonical TOML manifest. Loading returns `(table, receipt)`; absent
receipts return `(table, None)`. A returned receipt is historical evidence
from the source artifact, not a fresh CoolProp comparison and not a claim that
the loaded environment has rerun qualification. Applications that require
current verification should compare the returned table with the specified EOS
again using `qualify_isothermal_eos_table`.

### Query-version compatibility

The current table query identity is `isothermal-eos-table-v2`; its grid digest
continues to identify node data independently of the query implementation.
Version 2 corrects the log-linear inverse to use linear density coordinates,
matching forward log-pressure interpolation. A receipt issued for the old v1
query identity is rejected by the exact receipt/table-identity check even when
its node-array checksums still match. Do not relabel the historical receipt or
treat its inverse-density error as evidence for the corrected algorithm.

An old artifact saved without a qualification receipt can still load as the
current table with `receipt is None`, because the stored node grid is unchanged.
Reuse those nodes only after running current direct-CoolProp qualification for
the intended domain. Loading alone neither recreates a receipt nor admits the
table to a solver. See [table applicability](ISOTHERMAL_EOS_TABLE.md) for the
characteristic-speed policy and remaining hydraulic qualification.

### Characteristic-speed policy and schema

The default `sound_speed_mode="sampled"` retains the exact existing v2 query
identity and writes schema 1 without a mode field. Schema-1 artifacts load with
that same sampled policy. The optional `sound_speed_mode="pressure_derivative"`
writes schema 2 with an explicit mode field, reconstructs that policy on load,
and adds `pressure-derivative:` to the query identity. Older schema-1-only readers
cannot load schema 2. The grid digest still binds the same axes and both sampled
property arrays; it is not a replacement for the policy-bearing query identity.

Qualification receipts must match the full current query identity in addition
to the source, interpolation and grid digest. A receipt for sampled speed cannot
qualify derivative speed, or conversely, even with identical node arrays.
Mode-bound round trips and cross-policy receipt rejection passed the focused
algebra/persistence checks. Current generalized Darcy and quasi-steady network
routes reject both policies pending their separate physical admission work.

The case `isothermal-eos-table-artifact-roundtrip-integrity`
exercises both receipt-present and receipt-absent round trips, source/table
identity mismatch, byte corruption, bounded storage and no-extrapolation.
Its local replay passed after the corruption fixture was changed to modify an
actual pressure-array data byte while preserving stale semantic hashes and
writing valid ZIP CRCs. The loader rejected the pressure-array checksum; benign
container-header changes are not claimed to alter table identity. Two further
persistence regressions passed for v1-qualified rejection and unqualified-grid
reuse. These checks establish persistence integrity only; direct-CoolProp
accuracy and workload timing are recorded separately in
[executed qualification](THERMO_ACCELERATION_QUALIFICATION.md).
