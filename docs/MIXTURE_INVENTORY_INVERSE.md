# Bounded mixture density-energy inverse receipt

`MixtureInventoryInverse` records one successful fixed-composition native
CoolProp inversion for a caller-selected pressure branch. The report retains
the accepted state, sampled bracket, native root result, evaluation sequence,
residuals and caller branch-evidence identifier.

The receipt is issued only after the native provider completes the bounded
root and verifies its density and internal-energy budgets. Direct construction
and `dataclasses.replace()` cloning are rejected so a caller cannot turn
invented values into a provider-issued inverse result. Failed inversions remain
available through `MixtureInventoryInverseError` as failure diagnostics, not
successful state receipts.

This issuer guard establishes result provenance only. The branch is still
selected by caller evidence and sampled monotonicity; it does not prove global
uniqueness, phase-changing mixture behavior or independent EOS accuracy. The
rejection contract is deferred under the `gas-composition` profile.

The native phase-composition packet behind a two-phase inverse is also issued only
once by the CoolProp provider and checks its retained state, phase properties and
provider composition before use. Successful PH-branch reports are one-use solver
receipts; cloning or changing their residual, root summary or evaluation lineage is
rejected by `require_current()`. These guards preserve API provenance only and do
not replace the scheduled numerical or experimental qualification.
