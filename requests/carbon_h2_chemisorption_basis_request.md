# Nanoporous-carbon hydrogen chemisorption isotherm mapping request

Prepared request for Stephen Tsz Tang Lam and Mendeley Data maintainers for
[10.17632/vyp4wbhxzr.1](https://doi.org/10.17632/vyp4wbhxzr.1), CC BY 4.0. Not sent.
The 26,374-byte collection is acquired and hash-pinned. Before any source row is sent
to the existing `ExtendedLangmuirIsotherm`, please provide a small sidecar defining
the `total_chemisorption_isotherms.csv` table exactly:

1. Give the STP reference pressure and temperature for `Volume (STP cm3/g)` and the
exact gas-volume-to-amount convention used by the source.
2. Confirm whether each `Pressure (torr)` is absolute equilibrium hydrogen pressure,
and specify the measurement/recording method and pressure-reference convention.
3. Identify every material column and its exact sample code/ID, including how the
15-column table represents eight material isotherms, blanks, headings or replicates.
4. State whether the uptake is total/absolute, surface excess, or another measure;
identify gas-phase hold-up/dead-volume corrections and whether the quantity includes
reversible and irreversible chemisorption together.
5. Confirm the H2 temperature per row/material (the record description says 973 K),
sample pretreatment/degassing, equilibration criterion, and whether each row is an
independent equilibrium observation or a processed/averaged point.
6. Provide pointwise uncertainty, replicate population, material bulk/surface-area
basis as applicable, and any measurement covariance or detection limits.
7. Clarify the intended H2 isotherm equation/physical domain (homogeneous Langmuir,
heterogeneous Sips, dissociative, or total multi-mechanism uptake) and whether the
archived rows are independent of any published regression parameters.
8. Return per-file checksum/size and confirm that the CC BY 4.0 grant covers the
requested sidecar.

The table schema audit shows the first three labels as `Material`, `Pressure (torr)`
and `Volume (STP cm3/g)` with additional blank-labeled columns; do not infer omitted
headers from an article figure. A future sidecar should be keyed to exact CSV row,
material label and SHA-256, and should preserve the original Mendeley data unchanged.
This request does not ask for a fitted model or nuclear-system storage performance
claim.
