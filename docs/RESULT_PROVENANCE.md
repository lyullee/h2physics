# Producer-issued physical result provenance

`h2physics.adapters.result_provenance` supplies two read-only helpers for
producer result seals:

- `recorded_content_token(value)` records scalar values, numeric array bytes,
  dataclass fields, mapping order, callable/code identity and retained native
  tabular caches.
- `recorded_content_sha256(value)` hashes that token for later correspondence
  checks.

The helpers never invoke a physical model, property callback or native solver.
Object identity is intentionally part of mutable/native result records, so a
numerically identical reconstruction is not the original producer result.
Numeric arrays retain dtype, shape, writeability and byte content. Native tables
retain their original object identity, labels, dtypes and numeric bytes.
Object-valued arrays/tables are rejected because their hidden members cannot be
sealed by a portable numeric-byte digest.

PV-electrolysis and microbial-cell producers use this common token rule while
keeping separate domain admissions. A successful result owns its admission;
the producer keeps only a weak registration. This avoids an unbounded archive
of past results. `result.require_current()` checks the original result,
producer, retained content and current declared bindings. It does not establish
physics accuracy, independent validation, binary provenance or hidden closure
state. Strict producers may also reject a past result after their native scratch
state legitimately changes; that lifecycle is documented by the domain module.

Downstream modules should accept an original result through its public
`require_current()` method. They should not reconstruct domain objects, import
private seal registries or treat a matching SHA256 as authorization to mint a
new result. A downstream source snapshot may add quantity and boundary audits,
but those audits remain separate from the producer admission.

This increment received AST/lint review only. Runtime mutation, lifecycle and
installed-artifact checks remain in the deferred Nurion campaign.
