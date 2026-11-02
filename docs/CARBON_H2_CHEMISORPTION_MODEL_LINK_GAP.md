# Nanoporous-carbon hydrogen chemisorption: model-link gap

## Acquired source

Mendeley Data [10.17632/vyp4wbhxzr.1](https://doi.org/10.17632/vyp4wbhxzr.1),
“Physisorption and Total Chemisorption Isotherms in Nanoporous Carbon,” contains 19
small acquired files totaling 26,374 bytes under CC BY 4.0. The source record says
its CO2 physisorption measurements are at 273 K, N2 physisorption at 77 K, and H2
chemisorption at 973 K. File and metadata hashes are retained in
`research/data/carbon-chemisorption.toml`.
Attribution is retained for Stephen Tsz Tang Lam and the DOI. The repository does
not redistribute raw files; the dataset grant does not extend here to the associated
publication, figures or unreviewed third-party content.

Only `total_chemisorption_isotherms.csv` concerns H2. The schema audit records its
first columns as `Material`, `Pressure (torr)`, `Volume (STP cm3/g)` followed by
blank-labeled columns; it has 104 data rows. The other 18 files are CO2/N2
physisorption and are not hydrogen-loading observations.

## Why no pointwise adsorption comparison is admitted

The existing `h2physics.adsorption.ExtendedLangmuirIsotherm` consumes a declared
loading basis (mol/kg), exact species/material identity, absolute/total pressure
conditions and caller-evidenced model parameters. The source H2 table has a volume
loading at STP and torr pressure, but its local schema does not state the STP
temperature/pressure, whether pressure is absolute equilibrium pressure, whether
the quantity is total/absolute uptake or another retained-volume measure, or how
material labels map across the 15-column table. Those gaps block a source-derived
mol/kg conversion and a reproducible pointwise comparison.

The source record indicates 973 K, but row-level temperature, pretreatment,
equilibration, uncertainty and repeat meaning are not carried in the admitted CSV
schema. Total chemisorption may combine multiple binding modes; the current native
isotherm API supplies homogeneous Langmuir behavior and does not itself establish
that this is the appropriate physical form. No parameter fitting or extrapolation
is done. The Mendeley dataset is a measurement compilation for material behavior,
not a qualified hydrogen storage vessel model.

## Targeted evidence request

`requests/carbon_h2_chemisorption_basis_request.md` is a prepared, not-sent request
to the dataset author and repository maintainers. It asks for the exact STP
reference, pressure basis, material-column mapping, total/absolute/excess uptake
definition, run conditions, uncertainty, and equation/model-domain evidence. A
future reader can be considered after the sidecar is versioned, keyed to exact source
rows/files, and hashed. The Hangang case
`carbon-h2-chemisorption-model-link-gap` checks manifest facts only; it does not read
CSV values, convert units, fit, or evaluate an adsorption model.
