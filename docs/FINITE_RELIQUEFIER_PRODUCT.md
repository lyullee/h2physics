# Finite reliquefier product collection

`FiniteReliquefierProduct` adds explicit feed, collected-product, return and vent
ports around original `SteadyReliquefierResult` or `ReliquefierStep` objects. It
does not reproduce the native saturation, capacity, wall or EOS calculation.

The steady path integrates the original accepted mass flow and cooling duty over
one declared clock window. The dynamic path requires the original final
`ConservedInventory`, a caller-supplied initial inventory and a separately
provenanced integrated cold duty. It is a post-step accounting boundary; it does
not modify the native state for continuation.

Collected product is admitted only when the original selected state is entirely
liquid. Product, return, vent and device accumulation must close against feed.
Transported product enthalpy and a finite available-cooling budget are updated
separately. Original result and initial-ledger content are sealed and can be
rechecked with `require_current()`.

Native steady results and dynamic steps are issued only by their respective
LH2DT evaluation paths. Their retained output graphs are fingerprinted at
issuance and checked before product collection and again when a receipt is
revalidated. Direct result construction and post-issuance edits cannot be used
as native product evidence.
Collection receipts are also owner-issued and seal their own accounting fields,
so a copied receipt cannot replace the admitted mode or ledgers while preserving
the result's original provenance.

The model does not infer a separator, flash drum, vapor return pressure, vent
destination, chiller COP, thermodynamic cycle, electric demand, controller,
depletion root or manufacturer capacity. A two-phase outlet is not silently
split into pure phases. Independent apparatus/product evidence remains required.

The `reliquefier-product` Nurion profile is source-only and unexecuted.
