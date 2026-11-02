# Bath cryogenic hydrogen adsorption data

## Source and rights

The University of Bath Research Data Archive record [10.15125/BATH-00099](https://doi.org/10.15125/BATH-00099), version 1, describes cryocharging and cryokinetics measurements for MIL-101 (Cr) and AX-21. The record states “No restrictions” and identifies the University of Bath as rights holder. Cite Bimbo and Ting (2015), *Data for cryocharging and cryokinetics analysis of hydrogen storage in MIL-101 (Cr) and AX-21*, DOI 10.15125/BATH-00099. The adapter uses only the two spreadsheet measurement files listed in `research/data/bath-cryo-kinetics.toml`. Origin projects, microscopy images, and ImageJ assets are excluded.

## Reader scope

`h2physics.data.bath_cryo_kinetics.load_bath_kinetic_workbook` requires the exact staged workbook SHA-256, expected sheet names, and named columns. It returns immutable row observations with time in the source unit minutes, whole-sample excess uptake in micromols, pressure in MPa, and sample temperature in K. Raw source rows and units are retained; the reader does not calibrate or convert uptake, pressure, or time. Isotherm workbook bytes are staged and hashed, but are not yet parsed by this reader.

Deferred Hangang case `bath-cryo-kinetics-source-schema-gap` checks provenance and the kinetic workbook schema. It does not fit or run an adsorption model.

## Model boundary

The existing `storage.adsorption_dynamics` model represents a finite adsorber and requires absolute site loading in mol/kg and a mass/energy-balanced vessel state. The kinetic sheets provide whole-sample excess uptake but no dry sample mass or explicit mapping from each kinetic run to the isotherm sample basis. Therefore those observations cannot currently be used as finite-adsorber state or fitted model parameters. Keep excess uptake as excess uptake; do not infer absolute loading from the separate wt.% isotherm workbook without an evidenced sample mapping and conversion model.

To qualify a future bridge, obtain series-specific dry mass and sample identity, the excess-to-absolute basis or a supported dynamic excess model, and the initial bed/gas inventory and thermal/equilibrium inputs required by the existing vessel model.
