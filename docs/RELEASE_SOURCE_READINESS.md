# Source release readiness — 2026-10-30

This is a static source/packaging audit, not a built-artifact inspection, scientific
test result or legal clearance. No build, native import or scientific execution was
performed in the initial source audit. Current source is not declared ready for a public release.

## Latest content-only re-audit — 2026-11-01

The current source tree passes `scripts/audit_public_tree.py` for 1,477
GitHub-bound paths. A fresh built wheel and source archive pass
`scripts/release_audit.py`: all 363 packaged Python modules in the wheel and
source distribution match the current package source, and no raw-data files,
private paths, credentials, or missing license notices were found. Exact build
hashes are recorded in `research/release_audit.md`. This closes only the current
content/package consistency gate. It does not clear every dataset's rights,
third-party component reuse, installed native execution, or scientific claims;
new package-source changes require a fresh build and audit.

Build follow-up: the latest isolated source/wheel build completed and the actual
archive-content gates passed. All 198 package Python files matched current source bytes
in both archives; no excluded raw PDF/workbook/ZIP/NPZ assets were admitted. [The
development artifact report](../research/release_audit.md) records exact archive hashes.
This closes that checkpoint's packaging-content gate only;
installed native replay, scientific validation and final rights review remain open.

## Concrete outstanding items

Follow-up corrections: the chemistry extra now selects `cantera>=3.2,<3.3` to
match the inspected finite-volume adapter. Public documentation now uses generic
`CLUSTER_USER`, `CLUSTER_LOGIN_HOST` and `ALLOCATION_ACCOUNT` placeholders in
place of discovered execution identities. The table below retains those original
findings as historical evidence; the recorded development build includes both
corrections. Installed native execution remains pending.

| Item | Actual source evidence | Required action |
|---|---|---|
| Cantera install-range mismatch corrected | `pyproject.toml` chemistry extra now selects `cantera>=3.2,<3.3`, matching the admitted native 3.2 adapter. | Exercise that exact installed version on Nurion before claiming native compatibility. |
| New native profile requirements | `validation/nurion_plan_example.py` declares explicit interpreter/setup/hash for 41 profiles; new cases in `finite-transfer`, `flowing-heat-exchanger`, `fuel-cell-native`, `finite-adsorption-vessel` and `model-selection` reuse these profiles. | Pin actual Nurion setup scripts and transitive/native versions before dispatch. PSA cycle cases require PSA-Dyna even though the finite-adsorption vessel route can otherwise be EOS-only. Joint uncertainty requires SciPy>=1.15. Native LH2DT source provenance must match its reviewed revision. Profile names alone do not install these capabilities. |
| Many new files remain untracked | `git status --short` lists new modules, cases, examples and documents, including `finite_separator.py`, `fuel_cell_compartments.py`, transient exchanger and research coupling files. | Preserve them and include every intended original source in the final reviewed Git/source snapshot. A commit-based remote snapshot cannot contain files omitted from that commit. No files were staged, discarded or committed during this audit. |
| Public execution placeholders corrected | Public handoff/progress documents use generic execution identity fields. All `docs/*.md` are included by MANIFEST.in. | Retain private campaign configuration outside public artifacts and repeat the content audit for the actual intended release. A marker scan does not guarantee that all personal data has been identified. |
| Development artifact audit present; installation pending | `research/release_audit.md` records actual inspected archive hashes and is intentionally excluded from the audited archives. | Repeat the build/audit after source changes, then install and execute in the selected clean native Nurion environment. Development archive inspection does not prove installed execution. |

## Packaging coverage and intentional exclusions

`pyproject.toml` discovers packages under `src`. New modules beneath the existing
`h2physics`, `adapters`, `research` and `thermo` packages therefore have a source
discovery path; they do not each need an entry in MANIFEST.in. Direct module import
is a valid public API even when an adapter is not re-exported by the broad adapters
`__init__.py`. Final documentation must use its actual supported import path.

MANIFEST.in includes project LICENSE/NOTICE/AGENTS/README files and recursively
includes documentation, extension requests, Python scripts/tests/examples/validation,
research Markdown/TOML receipts and requirements text. The new originals are covered
by those patterns for a source distribution. These top-level research assets are not
automatically wheel package data; repository/source-distribution documentation and
the Python wheel have different roles. Decide explicitly if a future wheel should
also ship manuals rather than assume recursive source inclusion does so.

`data`, `artifacts`, validation results, virtual environments and Git internals are
pruned. PDF, workbook, MAT, ZIP and NPZ files are globally excluded. This deliberately
excludes external raw observations and locally generated `MixtureInverseGrid` NPZ
archives. Runtime-generated/reloaded property tables remain user execution artifacts,
not missing packaged model assets. No new runtime module should require an excluded
archive at a repository-relative default path. The scoped `git ls-files` query found
no tracked PDF/NPZ/XLSX/MAT/ZIP/PEM/KEY files.

New scientific checks are deferred `validation/cases/*.py` definitions. The default
pytest `testpaths=["tests"]` does not discover these as executed tests; the pinned
Nurion plan must explicitly collect their metadata and execute their entrypoints.
Case registration and metadata counts supply planned coverage only.

## Native ownership and rights records

`LICENSE` and `NOTICE` identify original host source as Apache-2.0 and preserve the
separate ownership of external software/data. `research/preferred_dispersion_dependencies.toml`
records HyRAM 6.1 GPL-3.0-only, SLABx/SLABx-LH2 MIT, reviewed source/license hashes and
the compatible SciPy environment. `requirements/native-preferred-dispersion.txt`
pins the actual preferred provider revisions and SciPy 1.16.3. Their source is not
vendored by this host's artifact manifest. Separate installation does not itself
settle every combined-distribution licensing question; review the intended release
and preserve applicable notices.

`research/native_lh2dt.toml` pins LH2DT source revision and code hash; native source
records and DEPENDENCIES.md identify its MIT ownership. `research/native_psa.md`
identifies the reviewed MIT PSA-Dyna revision. New separator/exchanger/adsorption
operation modules call those native owners and do not copy their integration or
thermodynamic equations. CoolProp/Cantera mechanisms and component coefficients
remain in their separately installed libraries; new compartment fixtures select
installed species definitions and retain their actual mechanism file hash.

Raw external data and normalized observations remain outside distributions unless a
separate data release review admits them. CC BY attribution/version/hash receipts
must accompany derived research as applicable. Missing dataset/phase/geometry rights
cannot be fixed through prose changes or an Apache header on original adapter code.

## Release decision boundary

Before publication, resolve the concrete install/configuration and public-identity
items above, preserve the full source snapshot, and perform the fresh artifact and
native execution reviews on the chosen host. Do not label unrun models validated or
claim unrestricted legal safety. This audit leaves the original research objective,
native receiving requests and independent qualification work active.
