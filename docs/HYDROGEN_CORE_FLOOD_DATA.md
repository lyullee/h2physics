# Hydrogen and nitrogen core-flood data

## Source and reuse

The experimental workbook collection is published by Maksim Lysyy and Tore Føyen as [Steady state core flood data for hydrogen- and nitrogen-water systems](https://data.mendeley.com/datasets/rfhf7wjydn/1), DOI [10.17632/rfhf7wjydn.1](https://doi.org/10.17632/rfhf7wjydn.1). The publisher record identifies the collection as [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution is retained here; the source files are not copied into the repository. The acquired originals live in the ignored `data/raw/hydrogen-core-flood/1/` cache and are checked against publisher SHA-256 digests. The local reader is an independently written adapter; it does not redistribute workbook content.

When reusing adapted output, credit Maksim Lysyy and Tore Føyen, link the dataset record and CC BY 4.0, and identify the changes. This project's adaptation selects each workbook's `Kr` worksheet and preserves native cell labels and values. The publisher license record also notes that material identified as third-party content may require separate permission; no such content audit is claimed here.

## Experimental coverage

The publisher describes measurements for hydrogen/water primary drainage, imbibition, and secondary drainage, with a nitrogen/water primary drainage comparison. Each experiment is delivered as a separate workbook. Workbooks also carry source-specific saturation, production, and differential-pressure worksheets. Exact sheet names and tabular structures vary, so the API currently exposes only each exact `Kr` worksheet; all four original workbooks remain locally staged for separate, future source-bound readers.

The accompanying [2022 study](https://doi.org/10.1029/2022GL100364) describes these steady-state core experiments and uses history matching plus capillary-pressure information to extend model curves across mobile saturations. The Mendeley record describes its `Kr` worksheet as calculated relative permeability. This adapter therefore calls the returned content publisher-reported derived values, not raw sensor readings. The study reports phase and flow-history hysteresis, and explains that the nitrogen/hydrogen primary-drainage difference includes viscosity-ratio effects and experimental uncertainty; nitrogen values must remain a separate gas case rather than being silently used as hydrogen data.

## Python API

Resolve the source record with `h2physics.data.resolve_dataset` and the `hydrogen-core-flood` seed in `h2physics.data.DATASETS`. Stage the four publisher attachments under a local directory, then call:

```python
from h2physics.data import DATASETS, load_hydrogen_core_flood, resolve_dataset

seed = next(item for item in DATASETS if item.key == "hydrogen-core-flood")
record = resolve_dataset(seed)
observations = load_hydrogen_core_flood("data/raw/hydrogen-core-flood/1", dataset=record)
primary_h2 = observations.table("Primary_drainage_H2.xlsx")
print(primary_h2.headers)
```

Install the optional workbook dependencies with `pip install -e '.[data]'`. Each returned `CoreFloodTable` contains the exact publisher filename, attachment URL, verified byte digest, worksheet name, and ordered rows of native spreadsheet values. Select a table using its exact publisher filename. The loader verifies publisher metadata, CC BY 4.0 identity, all four listing entries, attachment byte lengths, and SHA-256 digests before parsing. Formulas are read as stored expressions; workbook calculation is not performed.

## Branch-specific interpolation and mobility adapter

`h2physics.adapters.build_core_flood_branch` creates an immutable `CoreFloodBranch` from exactly one verified `CoreFloodTable`. The adapter retains the three distinct identities separately: gas species (`gas_id="H2"` or `"N2"`), hysteresis branch (`"primary_drainage"`, `"imbibition"`, or `"secondary_drainage"`), and flowing relative phase (`"gas"` or `"water"`). The supplied gas species and branch must agree with the source attachment. A nitrogen table cannot be relabeled as hydrogen, and drainage/imbibition branches cannot be merged.

The caller must provide the exact saturation and relative-permeability headers, a declared role for each field, units, bases, supporting interpretation evidence, and positive dynamic viscosity in Pa s with its basis and evidence. Header lookup uses exact equality and rejects missing or repeated headings. Canonical `Krg` and `Krw` labels (including labels with a following unit or annotation) identify gas and water relative permeability respectively; the adapter rejects a conflicting selected phase even when the caller's role declaration says otherwise. Other header meanings remain caller-owned and are not inferred from text. Saturation field role must be declared as `water_saturation`; relative-permeability role must be `gas_relative_permeability` or `water_relative_permeability` and match `relative_phase`.

Declare already fractional coordinates with a dimensionless/fraction unit and omit scaling to retain factor 1. Percent or any other non-unit coordinate requires the caller to supply an explicit positive scale that converts that raw field to a fraction. `CoreFloodBranch` preserves the source values and records both scale factors. Saturation values must be strictly monotone in workbook order. `evaluate(saturation)` accepts a fractional query only inside the observed domain and uses straight-line interpolation between the two adjacent source samples; it does not extrapolate. Its `CoreFloodMobilityPoint` reports the relative permeability divided by the explicitly supplied viscosity, which is mobility per intrinsic-permeability factor (units `(Pa s)^-1`), along with both source row IDs, raw endpoint values, and interpolation weight. It does not invent absolute permeability.

## Caller-bounded empirical power-law summary

`fit_core_flood_power_law(branch, ...)` is a separate optional compression of one source-bound gas or water relative-permeability branch. The caller supplies irreducible water and residual gas saturation, each with an evidence ID; the adapter never derives endpoints from observed extrema. It fits `kr = kr_endpoint * Se**n` by unweighted bounded least squares using every retained source row, records the fit metrics and exact row IDs, and evaluates only inside the observed saturation interval. Gas and water use their distinct effective-saturation coordinates. This fit is a descriptive summary of publisher-reported derived values, not a raw-data refit, a field constitutive law, or an independent reservoir qualification. The deferred `core-flood-source-bound-power-law-curve-summary` case is synthetic and validates API contracts only; measured workbook fields still require separate semantic review.

Every branch and result has `require_current()` to check the original table and selected values against the sealed source fingerprint. This API is **implemented but unverified against real workbook field semantics**. The deferred case `core-flood-branch-specific-relative-mobility` uses synthetic rows and checks contracts only. Before constructing measured branches, a reviewer must confirm exact table headings, role interpretation, units, basis, and phase viscosity for each experimental condition. The four branches remain separate, and nitrogen primary drainage remains nitrogen data.

## Optional empirical power-law summary

`h2physics.adapters.fit_core_flood_power_law(branch, irreducible_water_saturation=..., residual_gas_saturation=..., endpoint_evidence=...)` optionally compresses one declared branch to `kr = kr_endpoint * Se**n`. The water-phase coordinate is `Se=(Sw-Swir)/(1-Swir-Sgr)`; the gas-phase coordinate is its complement. `Swir` and `Sgr` are required caller-owned values with an evidence identifier, must bracket all selected observations, and are never estimated from workbook endpoints. The fit uses every selected source row in unweighted least squares, stores its endpoint parameter, exponent, RMSE, maximum absolute residual, solver method/count, and exact source row IDs. It rejects relative permeability outside [0,1], degenerate endpoint intervals, and fewer than three samples. Evaluation is allowed only inside the measured table's saturation interval.

This is a source-bound empirical curve summary, not a replacement for the publisher's reported table or a claim that a Corey relation is the right geological law. The source worksheet is described as calculated relative permeability and may itself reflect prior history matching. Do not pool hysteresis branches, transfer nitrogen fit parameters to hydrogen, infer endpoint saturations from observed extrema, or use fit RMSE as independent validation. The deferred `core-flood-source-bound-power-law-curve-summary` case uses a synthetic exact curve and checks API contracts only; real workbook semantics still require domain review.

## Scientific limits

The adapter deliberately does not convert the tables to a common set of units, interpret ambiguous headings, normalize saturation, estimate uncertainty, or fit a constitutive relative-permeability law. Column names and cell values stay in workbook form. These experiments support later model development only after their definitions, fluid conditions, rock/core properties, and measurement processing have been reviewed. They do not by themselves qualify an underground hydrogen storage model.

The deferred case `mendeley-hydrogen-core-flood-source-bound-kr-tables` checks ingestion against separately staged publisher workbooks and the staged, hash-pinned snapshot/listing responses. Its fixture resolves the curated source metadata offline and fails if repository HTTP access is attempted. The campaign requires the four workbook attachments plus `metadata.json` and `file-listing.json` in the configured source directory; none are included in the source archive. It preserves publisher headers and native cell values and does not claim numerical reproduction or physical validation. Perform source interpretation and fit comparisons in a requested parallel Hangang validation campaign before adopting parameters.
